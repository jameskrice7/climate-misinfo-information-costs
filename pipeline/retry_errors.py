"""Find rows where the LLM failed (relevance < 0) in out/post_industry shards,
re-call vLLM for each, and rewrite the shards in place.
"""
import asyncio, glob, json, os, time
import pyarrow.parquet as pq, pyarrow as pa
import httpx
from prompts_industry import SYSTEM_PROMPT, RESPONSE_SCHEMA, build_user_prompt

SERVER = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "qwen"
MAX_TOKENS = 220
CONCURRENCY = 16    # errors are sparse; modest concurrency is plenty
REQ_TIMEOUT = 240


async def call_one(client, sem, messages):
    body = {
        "model": MODEL, "messages": messages, "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "score", "schema": RESPONSE_SCHEMA, "strict": True}},
    }
    async with sem:
        for attempt in range(6):
            try:
                r = await client.post(SERVER, json=body, timeout=REQ_TIMEOUT)
                r.raise_for_status()
                obj = json.loads(r.json()["choices"][0]["message"]["content"])
                rel = max(0, min(100, int(obj["relevance"])))
                mis = max(0, min(100, int(obj["misinformation"])))
                return {
                    "relevance": rel,
                    "misinformation": mis,
                    "misinfo_type": str(obj.get("misinfo_type", "none"))[:32],
                    "exposure": round(rel * mis / 100.0, 2),
                    "rationale": str(obj.get("rationale", ""))[:240],
                    "ok": True,
                }
            except Exception as e:
                if attempt == 5:
                    return {"relevance": -1, "misinformation": -1, "misinfo_type": "error",
                            "exposure": -1.0, "rationale": f"ERR:{type(e).__name__}", "ok": False}
                await asyncio.sleep(2.0 * (attempt + 1))


async def main():
    inds = {r["industry"]: r for r in pq.read_table("work/industry_profile.parquet").to_pylist()}
    posts = {r["post_id"]: r for r in pq.read_table("work/posts.parquet").to_pylist()}
    sem = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY + 16, max_keepalive_connections=CONCURRENCY + 16)

    shards = sorted(glob.glob("out/post_industry/shard_*.parquet"))
    n_err_total = 0
    n_fixed = 0
    t0 = time.time()
    async with httpx.AsyncClient(limits=limits) as client:
        for sp in shards:
            t = pq.read_table(sp)
            rels = t.column("relevance").to_pylist()
            bad_idx = [i for i, r in enumerate(rels) if r is None or r < 0]
            if not bad_idx:
                continue
            n_err_total += len(bad_idx)
            rows = t.to_pylist()
            tasks = []
            for i in bad_idx:
                row = rows[i]
                ip = inds.get(row["industry"], {"industry": row["industry"]})
                post = posts.get(int(row["post_id"]), {})
                msgs = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(ip, post)},
                ]
                tasks.append(call_one(client, sem, msgs))
            results = await asyncio.gather(*tasks)
            for i, res in zip(bad_idx, results):
                if res["ok"]:
                    n_fixed += 1
                for k in ("relevance", "misinformation", "misinfo_type", "exposure", "rationale"):
                    rows[i][k] = res[k]
            # rewrite shard atomically
            cols = {k: [r[k] for r in rows] for k in t.column_names}
            new = pa.table(cols, schema=t.schema)
            tmp = sp + ".tmp"
            pq.write_table(new, tmp)
            os.replace(tmp, sp)
            print(f"  {os.path.basename(sp)}: retried {len(bad_idx)}, fixed {sum(1 for r in results if r['ok'])}", flush=True)
    print(f"DONE: errors found={n_err_total}, fixed={n_fixed}, elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
