"""Read-only audit of the distributed analysis inputs; no model inference."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'publication'
OUT.mkdir(parents=True, exist_ok=True)
p = pd.read_parquet(ROOT / 'data/PAPER_2_PANEL_energy.parquet')
f = pd.read_parquet(ROOT / 'pipeline/work/firmday_misinfo.parquet')
p['Date'] = pd.to_datetime(p.Date)
f['Date'] = pd.to_datetime(f.Date)
assert not p.duplicated(['RIC','Date']).any()
assert not f.duplicated(['RIC','Date']).any()
market_map = {'SS':'Mainland China','SZ':'Mainland China','HK':'Hong Kong',
              'TW':'Taiwan','TWO':'Taiwan','T':'Japan','JK':'Indonesia',
              'KL':'Malaysia','SA':'Brazil','L':'United Kingdom',
              'N':'United States','OQ':'United States','O':'United States',
              'PA':'France','DE':'Germany','AS':'Netherlands'}
p['ListingMarket'] = p.RIC.str.rsplit('.',n=1).str[-1].map(market_map)
assert p.ListingMarket.notna().all()
firm = p.drop_duplicates('RIC')[['RIC','Company Common Name','TRBC Industry Name',
            'Country of Headquarters','Region','ListingMarket']]
firm.to_csv(OUT/'security_market_audit.csv', index=False)
def identity(observed, predicted):
    ok = np.isfinite(observed) & np.isfinite(predicted)
    diff = (observed[ok]-predicted[ok]).abs()
    return {'n':int(ok.sum()),'max_abs_error':float(diff.max()),
            'fraction_close':float(np.isclose(observed[ok],predicted[ok],rtol=1e-7,atol=1e-8).mean())}
joined = p.merge(f,on=['RIC','Date'],how='left',validate='one_to_one')
last = f.Date.max()
audit = {
  'panel_rows':len(p),'securities':p.RIC.nunique(),
  'company_names':p['Company Common Name'].nunique(),
  'panel_min':str(p.Date.min().date()),'panel_max':str(p.Date.max().date()),
  'exposure_min':str(f.Date.min().date()),'exposure_max':str(last.date()),
  'panel_rows_after_exposure_end':int((p.Date>last).sum()),
  'spread_observed_after_exposure_end':int(((p.Date>last)&p.SpreadPercent.notna()).sum()),
  'crossed_quotes':int((p.ASK<p.BID).sum()),'nonpositive_spreads':int((p.SpreadPercent<=0).sum()),
  'market_security_counts':firm.ListingMarket.value_counts().to_dict(),
  'region_market_crosswalk':firm.groupby(['Region','ListingMarket']).size().to_dict(),
  'spread_identity':identity(p.SpreadPercent,200*(p.ASK-p.BID)/(p.ASK+p.BID)),
  'priceimpact_vs_orderflow_mid':identity(p.PriceImpact,100*p.OrderFlow.abs()/p.MidPrice),
  'priceimpact_vs_orderflow_close':identity(p.PriceImpact,100*p.OrderFlow.abs()/p.Close_trade),
  'priceimpact_vs_orderflow_vwap':identity(p.PriceImpact,100*p.OrderFlow.abs()/p.VWAP),
  'orderflow_vs_vwap_minus_mid':identity(p.OrderFlow,p.VWAP-p.MidPrice),
  'orderflow_vs_vwap_minus_close':identity(p.OrderFlow,p.VWAP-p.Close_trade),
  'intradayvolatility_vs_range':identity(p.IntradayVolatility,100*(p.High_trade-p.Low_trade)/p.Low_trade),
  'buyer_indicator_values':p.BuyerInitiated.value_counts().to_dict(),
}
fd = joined.loc[joined.fd_n_posts.notna()].copy()
variation = fd.groupby(['TRBC Industry Name','Date']).fd_mean_exposure.agg(['min','max','count'])
audit['maximum_exposure_range_within_sector_date']=float((variation['max']-variation['min']).max())
audit['sector_date_cells']=len(variation)
audit['exposure_nunique_dates']=f.Date.nunique()
con=duckdb.connect()
glob=(ROOT/'pipeline/out/post_industry/*.parquet').as_posix()
scores=con.execute(f"SELECT count(*) n, count(DISTINCT post_id) posts, count(DISTINCT industry) industries, count(*) FILTER(WHERE relevance<0) errors, count(*) FILTER(WHERE relevance>=0 AND abs(exposure-relevance*misinformation/100.)>1e-8) product_errors FROM read_parquet('{glob}')").df().iloc[0].to_dict()
audit['scores']=scores
agreement=con.execute(f"""WITH a AS (SELECT post_id, min(misinformation) lo,max(misinformation) hi,
 count(*) n, count(DISTINCT misinformation) k FROM read_parquet('{glob}') WHERE relevance>=0 GROUP BY post_id)
 SELECT count(*) n, avg(hi-lo) mean_range, avg(CASE WHEN hi>lo THEN 1. ELSE 0. END) share_disagreement,
 avg(CASE WHEN lo<50 AND hi>=50 THEN 1. ELSE 0. END) share_crossing_50 FROM a""").df().iloc[0].to_dict()
audit['misinformation_cross_sector_consistency']=agreement
# JSON keys must be strings; crosswalk is emitted separately as CSV.
audit['region_market_crosswalk']=[{'stored_region':a,'listing_market':b,'securities':n}
  for (a,b),n in audit['region_market_crosswalk'].items()]
(OUT/'input_audit.json').write_text(json.dumps(audit,indent=2,default=lambda x:int(x)),encoding='utf-8')
print(json.dumps(audit,indent=2,default=lambda x:int(x)),flush=True)
