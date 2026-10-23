"""CPU-only publication analysis of the distributed, fixed classifications.

Run from any directory. No classification code is imported or invoked.
Each specification is saved immediately, including unsuccessful diagnostics.
"""
from __future__ import annotations
import itertools
import json
import os
from pathlib import Path
import time
import warnings

os.environ.setdefault('NUMBA_NUM_THREADS','4')
os.environ.setdefault('OMP_NUM_THREADS','4')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/publication'
OUT.mkdir(parents=True,exist_ok=True)
MARKETS={'SS':'Mainland China','SZ':'Mainland China','HK':'Hong Kong',
 'TW':'Taiwan','TWO':'Taiwan','T':'Japan','JK':'Indonesia','KL':'Malaysia',
 'SA':'Brazil','L':'United Kingdom','N':'United States','OQ':'United States',
 'O':'United States','PA':'France','DE':'Germany','AS':'Netherlands'}
X='fd_mean_exposure'
CURRENT=['log_volume','log_mktcap','range_pct']
PRIOR=['lag_log_volume','lag_log_mktcap','lag_range_pct']
FULL=['log_volume','log_mktcap','IntradayVolatility','abs_vwap_gap',
      'log_turnover','cpi_inflation','gdp_growth','unemployment']

def json_safe(value):
    if isinstance(value,dict): return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list): return [json_safe(v) for v in value]
    if isinstance(value,(float,np.floating)) and not np.isfinite(value): return None
    return value

def save_results(path,value):
    path.write_text(json.dumps(json_safe(value),indent=2,default=str,allow_nan=False),encoding='utf-8')

def load_panel():
    p=pd.read_parquet(ROOT/'data/PAPER_2_PANEL_energy.parquet')
    f=pd.read_parquet(ROOT/'pipeline/work/firmday_misinfo.parquet')
    p['Date']=pd.to_datetime(p.Date); f['Date']=pd.to_datetime(f.Date)
    assert not p.duplicated(['RIC','Date']).any()
    assert not f.duplicated(['RIC','Date']).any()
    p=p.merge(f,on=['RIC','Date'],how='left',validate='one_to_one')
    p['exposure_matched']=p.fd_n_posts.notna()
    p['in_support']=p.Date.between(f.Date.min(),f.Date.max())
    for c in f.columns.difference(['RIC','Date']): p[c]=p[c].fillna(0.)
    p['Market']=p.RIC.str.rsplit('.',n=1).str[-1].map(MARKETS)
    assert p.Market.notna().all()
    p['Sector']=p['TRBC Industry Name']
    p['YearMonth']=p.Date.dt.strftime('%Y-%m')
    p['MarketDate']=p.Market+'_'+p.Date.dt.strftime('%Y-%m-%d')
    p['SectorMonth']=p.Sector+'_'+p.YearMonth
    p['Issuer']=p['Company Common Name']
    p['log_volume']=np.log1p(p.Volume.where(p.Volume>=0))
    p['log_mktcap']=np.log(p['Company Market Cap'].where(p['Company Market Cap']>0))
    p['log_turnover']=np.log1p(p.Turnover.where(p.Turnover>=0))
    p['abs_vwap_gap']=p.OrderFlow.abs()
    p['range_pct']=100*(p['Price High']-p['Price Low'])/p['Price Close'].where(p['Price Close']>0)
    p['vwap_deviation_pct']=p.PriceImpact
    p['log_exposure_sum']=np.log1p(p.fd_sum_exposure)
    p['log_posts']=np.log1p(p.fd_n_posts)
    p['positive_exposure']=(p[X]>0).astype(float)
    p['log_spread']=np.log(p.SpreadPercent.where(p.SpreadPercent>0))
    p['post2019']=(p.Date>='2019-01-01').astype(float)
    p['exposure_post2019']=p[X]*p.post2019
    p=p.replace([np.inf,-np.inf],np.nan).sort_values(['RIC','Date']).reset_index(drop=True)
    # A session requires an observed positive close and positive trading volume.
    # Shift on this grid before outcome-specific complete-case selection.
    active=(p.Volume>0)&(p['Price Close']>0)
    a=p.loc[active,['RIC','Date',X,'log_volume','log_mktcap','range_pct']].copy()
    for c in [X,'log_volume','log_mktcap','range_pct']:
        a['lag_'+c]=a.groupby('RIC',sort=False)[c].shift(1)
    a['lag_date']=a.groupby('RIC',sort=False).Date.shift(1)
    a['lead_exposure']=a.groupby('RIC',sort=False)[X].shift(-1)
    a['lead_date']=a.groupby('RIC',sort=False).Date.shift(-1)
    # Very long suspensions are not treated as one-session exposure shocks.
    invalid=(a.Date-a.lag_date).dt.days.gt(10)
    for c in ['lag_'+x for x in [X,'log_volume','log_mktcap','range_pct']]: a.loc[invalid,c]=np.nan
    a.loc[(a.lead_date-a.Date).dt.days.gt(10),'lead_exposure']=np.nan
    p=p.merge(a[['RIC','Date','lag_'+X,*PRIOR,'lag_date','lead_exposure','lead_date']],
              on=['RIC','Date'],how='left',validate='one_to_one')
    p['lag_exposure']=p['lag_'+X]
    # A zero outside the observed corpus window is unavailable exposure,
    # whereas an unmatched date inside that window is a zero-content day.
    p.loc[~p.lag_date.between(f.Date.min(),f.Date.max()),'lag_exposure']=np.nan
    p.loc[~p.lead_date.between(f.Date.min(),f.Date.max()),'lead_exposure']=np.nan
    # Calendar-day lag is retained only to diagnose calendar/sample differences.
    l=p[['RIC','Date',X]].copy(); l.Date+=pd.Timedelta(days=1)
    p=p.merge(l.rename(columns={X:'calendar_lag'}),on=['RIC','Date'],how='left',validate='one_to_one')
    p['valid_quote']=(p.BID>0)&(p.ASK>=p.BID)&(p.SpreadPercent>0)&active
    p['analysis_eligible']=p.in_support&p.valid_quote
    return p

def prepare(p,dep,terms,controls,winsor=True):
    cols=list(dict.fromkeys([dep,*terms,*controls,'RIC','Date','Market','Sector',
      'YearMonth','MarketDate','SectorMonth','Issuer','exposure_matched']))
    d=p[cols].dropna(subset=[dep,*terms,*controls]).copy().reset_index(drop=True)
    limits={}
    if winsor:
        for c in [dep,*controls]:
            lo,hi=d[c].quantile([.01,.99]); d[c]=d[c].clip(lo,hi)
            limits[c]=[float(lo),float(hi)]
    return d,limits

def influence_hac(m,d,term,lags=(5,20,60)):
    j=list(m._coefnames).index(term)
    influence=m._scores @ m._bread[:,j]
    daily=pd.Series(influence).groupby(d.Date.to_numpy()).sum().sort_index().to_numpy()
    result={}
    for L in lags:
        v=float(daily@daily)
        for k in range(1,min(L,len(daily)-1)+1):
            v+=2*(1-k/(L+1))*float(daily[k:]@daily[:-k])
        se=float(np.sqrt(max(v,0)))
        b=float(m.coef()[term])
        result[str(L)]={'se':se,'p':float(2*stats.norm.sf(abs(b/se))) if se else None}
    return result

def sector_score_signs(m,d,term):
    """Enumerated null-imposed sector score-sign sensitivity, not an exact test.

    Its reference distribution needs independent, symmetric sector scores;
    cross-sector dependence is assessed separately using date-score HAC.
    """
    j=list(m._coefnames).index(term)
    x=m._X[:,j]; z=np.delete(m._X,j,axis=1); y=m._Y.ravel()
    if z.shape[1]:
        x=x-z@np.linalg.lstsq(z,x,rcond=None)[0]
        u0=y-z@np.linalg.lstsq(z,y,rcond=None)[0]
    else: u0=y
    scores=pd.Series(x*u0).groupby(d.Sector.to_numpy()).sum().to_numpy()
    signs=np.array(list(itertools.product([-1.,1.],repeat=len(scores))))
    observed=abs(float(scores.sum()))
    p=float(np.mean(np.abs(signs@scores)>=observed-1e-12))
    return {'p':p,'sectors':len(scores),'assignments':len(signs),
      'assumption':'independent symmetric sector scores; diagnostic reference distribution'}

def run_fit(name,p,dep='SpreadPercent',terms=(X,),controls=CURRENT,
            fe='RIC + Date',winsor=True,deep=False):
    d,limits=prepare(p,dep,terms,controls,winsor)
    formula=dep+' ~ '+' + '.join([*terms,*controls])+' | '+fe
    print(f'FIT {name}: N={len(d):,} {formula}',flush=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        m=pf.feols(formula,d,vcov={'CRV1':'RIC+Date'},fixef_rm='none',
          fixef_tol=1e-9,solver='np.linalg.lstsq')
        firm={str(i):{k:float(v) for k,v in r.items()} for i,r in m.tidy().iterrows()}
        m.vcov({'CRV1':'Sector+Date'})
        sector={str(i):{k:float(v) for k,v in r.items()} for i,r in m.tidy().iterrows()}
    out={'formula':formula,'N':int(m._N),'securities':d.RIC.nunique(),
      'issuers':d.Issuer.nunique(),'sectors':d.Sector.nunique(),'dates':d.Date.nunique(),
      'firm_date':firm,'sector_date':sector,'winsor_limits':limits,
      'r2_within':float(m._r2_within),'dep_mean':float(d[dep].mean()),
      'dep_median':float(d[dep].median()),'warnings':[str(w.message) for w in caught],
      'exposure_sd':float(d[terms[0]].std()),'controls':controls,'fe':fe,
      'first_date':str(d.Date.min().date()),'last_date':str(d.Date.max().date())}
    if deep:
        out['date_score_hac']=influence_hac(m,d,terms[0])
        out['sector_score_signs']=sector_score_signs(m,d,terms[0])
        j=list(m._coefnames).index(terms[0]); z=np.delete(m._X,j,axis=1); x=m._X[:,j]
        xr=x-z@np.linalg.lstsq(z,x,rcond=None)[0] if z.shape[1] else x
        leverage=pd.Series(xr*xr).groupby(d.Sector.to_numpy()).sum()
        out['sector_identification_shares']=(leverage/leverage.sum()).to_dict()
        out['residual_exposure_sd']=float(np.std(xr))
        out['fwl_coefficient']=float((xr @ m._Y.ravel())/(xr@xr))
        out['matrix_condition_number']=float(np.linalg.cond(m._X))
    print(f"  {terms[0]} b={m.coef().get(terms[0],np.nan):+.7f} "
          f"p(sector/date)={sector[terms[0]]['Pr(>|t|)']:.5f}",flush=True)
    return out

def main():
    t=time.time(); p=load_panel(); res={'specifications':{},'run':{'classification_invoked':False}}
    path=OUT/'analysis_results.json'
    def fit(name,data,**kw):
        res['specifications'][name]=run_fit(name,data,**kw)
        save_results(path,res)
    # Literal published specification, including its extraneous legacy-index
    # complete-case restriction, is a computational benchmark only.
    literal=p.dropna(subset=['kl_raw','kl_weighted',X,'fd_sum_exposure',
      'fd_mean_misinformation','fd_mean_relevance','fd_max_exposure','fd_share_misinfo','fd_n_posts'])
    fit('benchmark_month',literal,controls=FULL,fe='RIC + YearMonth')
    valid=p.loc[p.analysis_eligible].copy()
    fit('support_month',valid,controls=FULL,fe='RIC + YearMonth')
    # All nested contemporaneous-control FE comparisons use one common sample.
    common=valid.dropna(subset=['SpreadPercent',X,*CURRENT]).copy()
    fit('common_month',common,fe='RIC + YearMonth')
    fit('common_date',common,deep=True)
    fit('common_marketdate',common,fe='RIC + MarketDate',deep=True)
    fit('common_marketdate_sectormonth',common,fe='RIC + MarketDate + SectorMonth',deep=True)
    # Primary model: only prior-session controls, never contemporaneous flows.
    primary=valid.dropna(subset=['SpreadPercent',X,*PRIOR]).copy()
    fit('primary',primary,controls=PRIOR,fe='RIC + MarketDate + SectorMonth',deep=True)
    fit('primary_nocontrol',primary,controls=[],fe='RIC + MarketDate + SectorMonth')
    fit('primary_unwinsorized',primary,controls=PRIOR,fe='RIC + MarketDate + SectorMonth',winsor=False)
    fit('primary_logspread',primary,dep='log_spread',controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    fit('primary_matched_posts',primary.loc[primary.exposure_matched],controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    # Common sample for timing: leads are a falsification diagnostic, not causal.
    timing=primary.dropna(subset=['lag_exposure','calendar_lag','lead_exposure']).copy()
    for name,term in [('timing_current',X),('timing_session','lag_exposure'),
                      ('timing_calendar','calendar_lag'),('timing_lead','lead_exposure')]:
        fit(name,timing,terms=[term],controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    fit('timing_joint',timing,terms=[X,'lag_exposure','lead_exposure'],controls=PRIOR,
        fe='RIC + MarketDate + SectorMonth')
    fit('session_all',primary.dropna(subset=['lag_exposure']),terms=['lag_exposure'],controls=PRIOR,
        fe='RIC + MarketDate + SectorMonth')
    for term in ['log_exposure_sum','fd_mean_misinformation','fd_mean_relevance',
                 'fd_share_misinfo','positive_exposure']:
        fit('variant_'+term,primary,terms=[term],controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    fit('attention_adjusted',primary,terms=[X,'log_posts','fd_mean_relevance'],controls=PRIOR,
        fe='RIC + MarketDate + SectorMonth')
    fit('period_interaction',primary,terms=[X,'exposure_post2019'],controls=PRIOR,
        fe='RIC + MarketDate + SectorMonth')
    # Leave-one-sector-out diagnostics hold full-sample tail caps fixed.
    fixed,_=prepare(primary,'SpreadPercent',[X],PRIOR,True)
    for sector in sorted(primary.Sector.unique()):
        fit('omit_'+sector,fixed.loc[fixed.Sector!=sector],controls=PRIOR,
            fe='RIC + MarketDate + SectorMonth',winsor=False)
    for market in ['Mainland China','Indonesia','United States']:
        fit('omitmarket_'+market,fixed.loc[fixed.Market!=market],controls=PRIOR,
            fe='RIC + MarketDate + SectorMonth',winsor=False)
    # A VWAP-midquote gap is an alternative price-dispersion outcome; it is
    # never labelled transaction price impact and absolute gap is not a control.
    fit('vwap_deviation',primary,dep='vwap_deviation_pct',controls=PRIOR,
        fe='RIC + MarketDate + SectorMonth')
    # No factor-derived outcomes are used: stored regional factors do not match
    # the actual listing markets for a material fraction of securities.
    res['run'].update({'seconds':time.time()-t,'python':os.sys.version,'pyfixest':pf.__version__,
      'exposure_end':str(p.loc[p.exposure_matched,'Date'].max().date()),
      'eligible_rows':len(valid),'primary_complete_cases':len(primary),
      'no_post_days_in_support':int((p.in_support&~p.exposure_matched).sum()),
      'missing_post_dates':'Post IDs are internal integers. No date map is distributed; post-level relevance thresholds cannot be reaggregated.',
      'primary_descriptive':primary[['SpreadPercent',X,*PRIOR,'fd_n_posts','fd_mean_misinformation','fd_mean_relevance']].describe().to_dict()})
    # Tables of sample composition and primary data are all regenerated.
    primary.groupby('Market').agg(securities=('RIC','nunique'),observations=('RIC','size'),
      mean_spread=('SpreadPercent','mean'),mean_exposure=(X,'mean')).to_csv(OUT/'market_composition.csv')
    primary.groupby('Sector').agg(securities=('RIC','nunique'),observations=('RIC','size'),
      mean_spread=('SpreadPercent','mean'),mean_exposure=(X,'mean')).to_csv(OUT/'sector_composition.csv')
    primary.to_parquet(OUT/'analysis_sample.parquet',index=False)
    save_results(path,res)
    print(f'DONE in {time.time()-t:.1f}s',flush=True)

def refresh_timing():
    """Refresh timing checks after an explicit corpus-boundary change."""
    path=OUT/'analysis_results.json'
    res=json.loads(path.read_text(encoding='utf-8'))
    p=load_panel()
    primary=p.loc[p.analysis_eligible].dropna(subset=['SpreadPercent',X,*PRIOR]).copy()
    timing=primary.dropna(subset=['lag_exposure','calendar_lag','lead_exposure']).copy()
    for name,term in [('timing_current',X),('timing_session','lag_exposure'),
                      ('timing_calendar','calendar_lag'),('timing_lead','lead_exposure')]:
        res['specifications'][name]=run_fit(name,timing,terms=[term],controls=PRIOR,
            fe='RIC + MarketDate + SectorMonth')
    res['specifications']['timing_joint']=run_fit('timing_joint',timing,
        terms=[X,'lag_exposure','lead_exposure'],controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    res['specifications']['session_all']=run_fit('session_all',primary.dropna(subset=['lag_exposure']),
        terms=['lag_exposure'],controls=PRIOR,fe='RIC + MarketDate + SectorMonth')
    res['run']['timing_boundary_rule']='Lag and lead exposure must have a source session within the corpus window.'
    save_results(path,res)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--refresh-timing',action='store_true')
    if ap.parse_args().refresh_timing: refresh_timing()
    else: main()
