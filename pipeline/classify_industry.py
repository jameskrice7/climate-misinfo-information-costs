"""Resumable async classifier at (post, industry) granularity.

Inputs:
  work/post_industry_pairs.parquet  (rid_i, post_id, industry)  ~1.96M rows
  work/posts.parquet                (post_id, text, ...)
  work/industry_profile.parquet     (industry, n_firms, countries, regions, example_firms)

Output shards: out/post_industry/shard_{lo}-{hi}.parquet with columns
  rid_i, post_id, industry, relevance, misinformation, misinfo_type, exposure, rationale

Resume: any shard file that already exists is skipped.
"""
import argparse, asyncio, json, os, time
import pyarrow.parquet as pq
import pyarrow as pa
import httpx
from prompts_industry import SYSTEM_PROMPT, RESPONSE_SCHEMA, build_user_prompt

WORK = "work"
OUTDIR = "out/post_industry"
SERVER = os.environ.get("VLLM_URL", "http://127.0.0.1:8000/v1/chat/completions")
MODEL = os.environ.get("VLLM_MODEL", "qwen")
WINDOW = int(os.environ.get("WINDOW", "20000"))      # rids_i per shard
CONCURRENCY = int(os.environ.get("CONCURRENCY", "128"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "200"))
REQ_TIMEOUT = float(os.environ.get("REQ_TIMEOUT", "240"))


def load_lookups():
    inds = {}
    for r in pq.read_table(f"{WORK}/industry_profile.parquet").to_pylist():
        inds[r["industry"]] = r
    posts = {r["post_id"]: r for r in pq.read_table(f"{WORK}/posts.parquet").to_pylist()}
    return inds, posts


def load_pairs():
    t = pq.read_table(f"{WORK}/post_industry_pairs.parquet").sort_by("rid_i")
    return (t.column("rid_i").to_numpy(),
            t.column("post_id").to_numpy(),
            t.column("industry").to_pylist())


def shard_path(lo, hi):
    return f"{OUTDIR}/shard_{lo:08d}-{hi:08d}.parquet"


async def call_one(client, sem, messages, rid_i, post_id, industry):
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "score", "schema": RESPONSE_SCHEMA, "strict": True}},
    }
    async with sem:
        for attempt in range(5):
            try:
                r = await client.post(SERVER, json=body, timeout=REQ_TIMEOUT)
                r.raise_for_status()
                obj = json.loads(r.json()["choices"][0]["message"]["content"])
                rel = max(0, min(100, int(obj["relevance"])))
                mis = max(0, min(100, int(obj["misinformation"])))
                return {
                    "rid_i": int(rid_i),
                    "post_id": int(post_id),
                    "industry": industry,
                    "relevance": rel,
                    "misinformation": mis,
                    "misinfo_type": str(obj.get("misinfo_type", "none"))[:32],
                    "exposure": round(rel * mis / 100.0, 2),
                    "rationale": str(obj.get("rationale", ""))[:240],
                    "ok": True,
                }
            except Exception as e:
                if attempt == 4:
                    return {"rid_i": int(rid_i), "post_id": int(post_id), "industry": industry,
                            "relevance": -1, "misinformation": -1, "misinfo_type": "error",
                            "exposure": -1.0, "rationale": f"ERR:{type(e).__name__}", "ok": False}
                await asyncio.sleep(1.5 * (attempt + 1))


def write_shard(results, lo, hi):
    results.sort(key=lambda x: x["rid_i"])
    cols = {k: [r[k] for r in results] for k in
            ["rid_i", "post_id", "industry", "relevance", "misinformation",
             "misinfo_type", "exposure", "rationale"]}
    tbl = pa.table(cols)
    path = shard_path(lo, hi)
    tmp = path + ".tmp"
    pq.write_table(tbl, tmp)
    os.replace(tmp, path)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    print("loading lookups...", flush=True)
    inds, posts = load_lookups()
    print(f"  industries={len(inds)} posts={len(posts)}", flush=True)
    print("loading pairs...", flush=True)
    rids, pids, indlist = load_pairs()
    N = len(rids)
    print(f"  pairs={N:,}", flush=True)

    end = N if args.limit == 0 else min(N, args.start + args.limit)
    sem = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY + 32, max_keepalive_connections=CONCURRENCY + 32)
    t0 = time.time()
    done_rows = 0
    async with httpx.AsyncClient(limits=limits) as client:
        pos = args.start
        while pos < end:
            lo = pos
            hi = min(pos + WINDOW, end)
            lo_rid, hi_rid = int(rids[lo]), int(rids[hi - 1])
            sp = shard_path(lo_rid, hi_rid)
            if os.path.exists(sp):
                pos = hi
                continue
            wt = time.time()
            tasks = []
            for i in range(lo, hi):
                ind = indlist[i]
                post = posts.get(int(pids[i]), {})
                ip = inds.get(ind, {"industry": ind})
                msgs = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(ip, post)},
                ]
                tasks.append(call_one(client, sem, msgs, rids[i], pids[i], ind))
            results = await asyncio.gather(*tasks)
            nbad = sum(1 for r in results if not r["ok"])
            write_shard(results, lo_rid, hi_rid)
            done_rows += len(results)
            dt = time.time() - wt
            rate = len(results) / dt if dt > 0 else 0
            elapsed = time.time() - t0
            overall = done_rows / elapsed if elapsed > 0 else 0
            remaining = (end - hi) / overall / 3600 if overall > 0 else float("inf")
            print(f"[{hi:,}/{end:,}] win {rate:.1f}/s | overall {overall:.1f}/s | "
                  f"bad={nbad} | ETA {remaining:.1f}h", flush=True)
            pos = hi
    print(f"DONE {done_rows:,} rows in {(time.time()-t0)/3600:.2f}h", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
