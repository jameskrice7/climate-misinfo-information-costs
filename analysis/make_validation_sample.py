"""Select a score-stratified sample for later independent human annotation.

This exports no post text and creates no human labels. Labels must be supplied
by independent annotators with authorised access to original post context.
"""
from pathlib import Path
import duckdb
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def main():
    con=duckdb.connect(); con.execute('SET threads=4')
    source=(ROOT/'pipeline/out/post_industry/*.parquet').as_posix()
    d=con.execute(f"SELECT post_id,median(misinformation) model_median,min(misinformation) model_min,max(misinformation) model_max FROM read_parquet('{source}') WHERE relevance>=0 GROUP BY post_id").df()
    d['stratum']=pd.cut(d.model_median,[-1,0,25,50,75,100],labels=['zero','low','framing','false','extreme'])
    parts=[g.sample(min(100,len(g)),random_state=20261023) for _,g in d.groupby('stratum',observed=True)]
    sample=pd.concat(parts).sort_values('post_id')
    # The blind annotation sheet hides all model information.
    blind=sample[['post_id']].copy()
    for col in ['human_climate_claim','human_false_or_misleading','human_satire_or_refutation',
                'human_relevance_sector','annotator_id','notes']: blind[col]=''
    out=ROOT/'results/publication';out.mkdir(parents=True,exist_ok=True)
    blind.to_csv(out/'human_validation_blank.csv',index=False)
    sample.to_csv(out/'human_validation_sampling_key.csv',index=False)
    print(f'{len(sample)} rows; annotation sheet has no labels. Scores are held in a separate sampling key.')

if __name__=='__main__': main()
