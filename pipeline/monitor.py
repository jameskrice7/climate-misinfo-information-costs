"""Progress monitor for the (post x industry) classification run.

Prints rows done, % complete, recent throughput, ETA, and shard count.
"""
import glob, os, time
import pyarrow.parquet as pq

OUTDIR = "out/post_industry"
TOTAL = 1_959_707

def main():
    shards = sorted(glob.glob(f"{OUTDIR}/shard_*.parquet"))
    done = 0
    last_mtime = 0
    for s in shards:
        try:
            md = pq.read_metadata(s)
            done += md.num_rows
            mt = os.path.getmtime(s)
            if mt > last_mtime: last_mtime = mt
        except Exception:
            pass
    pct = 100.0 * done / TOTAL
    age = time.time() - last_mtime if last_mtime else float("inf")
    # very rough rate: avg over (last shard mtime - first shard mtime)
    rate_msg = ""
    if len(shards) >= 2:
        try:
            first = os.path.getmtime(shards[0])
            spread = last_mtime - first
            if spread > 0:
                rate = (done - pq.read_metadata(shards[0]).num_rows) / spread
                eta_h = (TOTAL - done) / rate / 3600 if rate > 0 else float("inf")
                rate_msg = f"  ~{rate:.1f} rows/s  ETA {eta_h:.1f}h"
        except Exception:
            pass
    print(f"shards={len(shards)}  rows_done={done:,}/{TOTAL:,}  ({pct:.2f}%)  "
          f"last_shard_age={age:.0f}s{rate_msg}")

if __name__ == "__main__":
    main()
