"""Reaggregate fixed scores if an authorised post-date crosswalk is supplied.

No classification is performed. A crosswalk with only post_id,post_date is
sufficient; post text is neither read nor written. Does not manufacture dates
from internal integer IDs, and never reuses saved estimates if input is absent.
"""
from pathlib import Path
import argparse
import duckdb

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--post-dates',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    if not args.post_dates.is_file():
        raise FileNotFoundError('A real post_id/post_date crosswalk is required; no result was generated.')
    root=Path(__file__).resolve().parents[1]
    con=duckdb.connect()
    con.execute('SET threads=4')
    datepath=args.post_dates.resolve().as_posix().replace("'","''")
    source=(root/'pipeline/out/post_industry/*.parquet').as_posix().replace("'","''")
    dates=con.execute(f"SELECT post_id,CAST(post_date AS DATE) post_date FROM read_parquet('{datepath}')").df()
    if dates.post_id.duplicated().any() or dates.post_date.isna().any():
        raise ValueError('The crosswalk must be unique and dates nonmissing.')
    con.register('dates',dates)
    missing=con.execute(f"SELECT count(*) FROM (SELECT DISTINCT post_id FROM read_parquet('{source}') WHERE relevance>=0) s ANTI JOIN dates d USING(post_id)").fetchone()[0]
    if missing: raise ValueError(f'{missing} scored posts have no date; aborting rather than filling missing with zero.')
    selects=[]
    for threshold in [10,25,50,75]:
        selects.extend([
          f'count(*) FILTER(WHERE relevance>={threshold}) AS n_relevant_{threshold}',
          f'avg(exposure) FILTER(WHERE relevance>={threshold}) AS conditional_mean_{threshold}',
          f'avg(CASE WHEN relevance>={threshold} THEN exposure ELSE 0 END) AS contribution_{threshold}'
        ])
    q=f"""SELECT industry,post_date AS Date,count(*) n_valid,avg(exposure) mean_exposure,
      avg(CASE WHEN relevance<10 THEN exposure ELSE 0 END) irrelevant_contribution,
      {','.join(selects)} FROM read_parquet('{source}') s JOIN dates USING(post_id)
      WHERE relevance>=0 GROUP BY industry,post_date"""
    out=con.execute(q).df()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    out.to_parquet(args.output,index=False)
    print(f'Wrote {len(out):,} sector-day rows; conditional means remain missing when no posts qualify.')

if __name__=='__main__': main()
