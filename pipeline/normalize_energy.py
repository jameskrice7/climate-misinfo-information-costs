"""One-time normalization into compact tables.

  work/firms.parquet  - one row per unique RIC (firm profile)        [from energy file]
  work/posts.parquet  - one row per unique post_id (text + meta)     [from small post_x_industry]
  work/pairs.parquet  - 43.5M rows (rid, post_id, RIC)               [from energy file, narrow cols]

posts is sourced from post_x_industry.parquet (464MB) which is a verified superset
of all energy post_ids, avoiding a wide GROUP BY over the 78GB file.
"""
import duckdb, time, os

ENERGY = "energy_panel_posts.parquet"
SMALL = "post_x_industry.parquet"
OUT = "work"
os.makedirs(OUT, exist_ok=True)
os.makedirs(f"{OUT}/duck_tmp", exist_ok=True)

con = duckdb.connect()
con.execute("PRAGMA threads=6")
con.execute("PRAGMA memory_limit='40GB'")
con.execute("PRAGMA preserve_insertion_order=false")
con.execute("PRAGMA temp_directory='work/duck_tmp'")
con.execute("PRAGMA max_temp_directory_size='1500GB'")

t = time.time()

print("[1/3] firms.parquet ...", flush=True)
con.execute(f"""
COPY (
  SELECT RIC,
    any_value("Company Common Name")     AS company_name,
    any_value("TRBC Industry Name")      AS industry,
    any_value("Country of Headquarters") AS country,
    any_value(Region)                    AS region
  FROM '{ENERGY}' GROUP BY RIC
) TO '{OUT}/firms.parquet' (FORMAT parquet);
""")
print("   firms done %.0fs" % (time.time()-t), flush=True)

print("[2/3] posts.parquet (from small file, energy post_ids only) ...", flush=True)
con.execute(f"""
COPY (
  WITH energy_pids AS (SELECT DISTINCT post_id FROM '{ENERGY}')
  SELECT s.post_id,
    any_value(s.text)                          AS text,
    any_value(s."link_attachment.caption")     AS link_caption,
    any_value(s."link_attachment.name")        AS link_name,
    any_value(s."link_attachment.description")  AS link_description,
    any_value(s.content_type)                  AS content_type,
    any_value(s.lang)                          AS lang,
    any_value(CAST(s.creation_time AS DATE))   AS post_date
  FROM '{SMALL}' s
  SEMI JOIN energy_pids e ON s.post_id = e.post_id
  GROUP BY s.post_id
) TO '{OUT}/posts.parquet' (FORMAT parquet);
""")
print("   posts done %.0fs" % (time.time()-t), flush=True)

print("[3/3] pairs.parquet (narrow cols, rid = order by RIC, post_id) ...", flush=True)
con.execute(f"""
COPY (
  SELECT row_number() OVER (ORDER BY RIC, post_id) - 1 AS rid, post_id, RIC
  FROM (SELECT RIC, post_id FROM '{ENERGY}')
) TO '{OUT}/pairs.parquet' (FORMAT parquet, ROW_GROUP_SIZE 1000000);
""")
print("   pairs done %.0fs" % (time.time()-t), flush=True)

for f in ["firms", "posts", "pairs"]:
    n = con.execute(f"SELECT count(*) FROM '{OUT}/{f}.parquet'").fetchone()[0]
    sz = os.path.getsize(f"{OUT}/{f}.parquet")/1e6
    print(f"   {f}: {n:,} rows, {sz:.1f} MB", flush=True)
print("TOTAL %.0fs" % (time.time()-t), flush=True)
