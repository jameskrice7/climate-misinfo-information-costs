"""Expand (post x industry) scores -> 43.5M (firm, post) rows.

Memory-frugal version: writes one parquet *part* per RIC (firm) so duckdb never
buffers the full 43.5M result. Final deliverable is the directory
out/energy_scored/ (parquet dataset), readable by duckdb/pyarrow as a single
table via read_parquet('out/energy_scored/*.parquet').

Reads:
  out/post_industry/shard_*.parquet  - LLM scores by (post_id, industry)
  work/pairs.parquet                 - (rid, post_id, RIC)
  work/firms.parquet                 - (RIC, industry, ...)

Per part columns:
  rid, post_id, RIC, industry, relevance, misinformation, misinfo_type,
  exposure, rationale
"""
import duckdb, glob, os, sys, time

WORK = "work"
SHARD_GLOB = "out/post_industry/shard_*.parquet"
OUTDIR = "out/energy_scored"


def main():
    shards = sorted(glob.glob(SHARD_GLOB))
    if not shards:
        print("no shards found at", SHARD_GLOB, file=sys.stderr); sys.exit(1)
    print(f"input shards: {len(shards)}", flush=True)
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs("work/duck_tmp", exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    con.execute("PRAGMA memory_limit='12GB'")
    con.execute("PRAGMA preserve_insertion_order=false")
    con.execute("PRAGMA temp_directory='work/duck_tmp'")
    con.execute("PRAGMA max_temp_directory_size='400GB'")

    # 1. Build a small scores lookup view (1.96M rows, fits comfortably).
    print("staging scores...", flush=True)
    t0 = time.time()
    con.execute(f"""
    CREATE TABLE scores AS
    SELECT post_id, industry, relevance, misinformation, misinfo_type,
           exposure, rationale
    FROM read_parquet('{SHARD_GLOB}')
    WHERE relevance >= 0;
    """)
    n_scores = con.execute("SELECT count(*) FROM scores").fetchone()[0]
    print(f"  scores: {n_scores:,} rows in {time.time()-t0:.0f}s", flush=True)

    # 2. Load firms (small; 204 rows).
    con.execute(f"CREATE TABLE firms AS SELECT RIC, industry FROM '{WORK}/firms.parquet';")

    # 3. Stream per-RIC: pairs filtered by RIC, joined to scores via post_id+industry.
    #    Output one parquet file per RIC -> bounded memory.
    rics = [r[0] for r in con.execute("SELECT RIC FROM firms ORDER BY RIC").fetchall()]
    print(f"writing per-RIC parquet parts: {len(rics)} firms", flush=True)
    total = 0
    bt = time.time()
    for i, ric in enumerate(rics):
        safe = ric.replace("/", "_").replace(":", "_")
        out = f"{OUTDIR}/part_{i:04d}_{safe}.parquet"
        if os.path.exists(out):
            n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
            total += n
            continue
        tmp = out + ".tmp"
        con.execute(f"""
        COPY (
          SELECT p.rid, p.post_id, p.RIC, f.industry,
                 s.relevance, s.misinformation, s.misinfo_type,
                 s.exposure, s.rationale
          FROM '{WORK}/pairs.parquet' p
          JOIN firms f  ON p.RIC = f.RIC
          JOIN scores s ON p.post_id = s.post_id AND f.industry = s.industry
          WHERE p.RIC = ?
        ) TO '{tmp}' (FORMAT parquet);
        """, [ric])
        os.replace(tmp, out)
        n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        total += n
        dt = time.time() - bt
        rate = total / dt if dt > 0 else 0
        eta_s = (len(rics) - (i + 1)) * dt / (i + 1) if (i + 1) > 0 else 0
        print(f"  [{i+1:3d}/{len(rics)}] {ric:20s} {n:>10,} rows | total {total:>12,} | "
              f"{rate:>6.0f} rows/s | ETA {eta_s/60:.1f}min", flush=True)

    # 4. Manifest summary
    size_mb = sum(os.path.getsize(os.path.join(OUTDIR, f))
                  for f in os.listdir(OUTDIR) if f.endswith(".parquet")) / 1e6
    print(f"DONE: {total:,} rows across {len(rics)} parquet parts, {size_mb:.0f} MB total, "
          f"elapsed {time.time()-t0:.0f}s", flush=True)
    print(f"Read as one table: duckdb.read_parquet('{OUTDIR}/*.parquet')", flush=True)


if __name__ == "__main__":
    main()
