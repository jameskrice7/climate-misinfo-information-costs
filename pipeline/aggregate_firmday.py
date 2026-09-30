"""Aggregate out/energy_scored/ (43.5M firm x post rows) to firm-day means.

For each (RIC, Date) emit the day's mean/max/sum/count over the climate posts
that the LLM scored against the firm's industry. The post's Date is the
classification join key (matches firm-day) -- we recover it via posts.parquet.

Output: work/firmday_misinfo.parquet
  RIC, Date,
  fd_n_posts,
  fd_mean_relevance, fd_mean_misinformation, fd_mean_exposure,
  fd_max_exposure, fd_sum_exposure,
  fd_share_misinfo  (share of posts with misinformation >= 25)
"""
import duckdb, time

con = duckdb.connect()
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='10GB'")
con.execute("PRAGMA preserve_insertion_order=false")
con.execute("PRAGMA temp_directory='work/duck_tmp'")

t = time.time()
print("aggregating ...", flush=True)
con.execute("""
COPY (
  WITH scored AS (
    SELECT s.RIC, s.post_id, s.relevance, s.misinformation, s.exposure
    FROM read_parquet('out/energy_scored/*.parquet') s
  ),
  with_date AS (
    SELECT s.RIC,
           CAST(p.post_date AS DATE) AS Date,
           s.relevance, s.misinformation, s.exposure
    FROM scored s
    JOIN 'work/posts.parquet' p ON s.post_id = p.post_id
  )
  SELECT RIC, Date,
    COUNT(*)                                        AS fd_n_posts,
    AVG(relevance)                                  AS fd_mean_relevance,
    AVG(misinformation)                             AS fd_mean_misinformation,
    AVG(exposure)                                   AS fd_mean_exposure,
    MAX(exposure)                                   AS fd_max_exposure,
    SUM(exposure)                                   AS fd_sum_exposure,
    AVG(CASE WHEN misinformation >= 25 THEN 1.0 ELSE 0.0 END) AS fd_share_misinfo
  FROM with_date
  GROUP BY RIC, Date
) TO 'work/firmday_misinfo.parquet' (FORMAT parquet);
""")
n = con.execute("SELECT count(*) FROM 'work/firmday_misinfo.parquet'").fetchone()[0]
print(f"firmday rows: {n:,}  elapsed {time.time()-t:.0f}s", flush=True)

# quick sanity
print("--- sample ---", flush=True)
for r in con.execute("""SELECT RIC, Date, fd_n_posts,
       round(fd_mean_relevance,2), round(fd_mean_misinformation,2),
       round(fd_mean_exposure,2), round(fd_max_exposure,2), round(fd_sum_exposure,1)
   FROM 'work/firmday_misinfo.parquet'
   WHERE fd_n_posts > 50 ORDER BY fd_sum_exposure DESC LIMIT 5""").fetchall():
    print("  ", r)
print("--- per-firm dates coverage ---", flush=True)
r = con.execute("""SELECT count(distinct RIC), count(distinct Date),
                          avg(fd_n_posts), min(fd_n_posts), max(fd_n_posts)
                   FROM 'work/firmday_misinfo.parquet'""").fetchone()
print(f"  firms={r[0]} dates={r[1]} avg_posts/day={r[2]:.1f} min={r[3]} max={r[4]}", flush=True)
