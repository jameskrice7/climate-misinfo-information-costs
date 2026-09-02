"""main_analysis.py — single-script replication of the main analysis for
"The Information Costs of Climate Misinformation: Evidence from Global
Financial Data" (James Rice, University of Essex).

This is THE main-analysis script. It reproduces every headline regression in
the paper from the firm-day panel and the daily climate-misinformation KL
index (5-model ensemble), and writes all numbers to
    output/main_results/econ_results.json

Specifications are reproduced verbatim from the working pipeline; only the
KL index values feed in as the regressor of interest (`kl_raw`, `kl_weighted`).

Pipeline reproduced:
  * core full-panel readouts (Models I/II/III: Spread, CAPM beta, FF5 ER)
  * standardized effects, region splits, placebo, Asia-lag, subperiod, low-count
  * true two-way (firm + date) clustered core / region / climate / triple-interaction
  * energy-subsample readouts + sign-flip decomposition (type/region/period)

Inputs (in ../data/):
  * PAPER_2_PANEL.parquet         firm-day panel with KL index merged in
  * PAPER_2_PANEL_energy.parquet  energy-exposed subsample
The KL index itself is ../data/daily_misinfo_kl_measure_5models.{parquet,csv}
(already merged into the panels). Raw Facebook post data is NOT distributed;
only the constructed daily index is included. See ../README.md.

Requirements: python>=3.10, pandas, numpy, pyfixest==0.40.1
Run:  python code/main_analysis.py
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyfixest as pf

# ---- portable paths (relative to this file) ----------------------------------
HERE = Path(__file__).resolve().parent          # .../code
ROOT = HERE.parent                              # replication root
DATA = ROOT / 'data'
OUT = ROOT / 'output' / 'main_results'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = OUT / 'econ_results.json'
results: dict = {}
t_start = time.time()


def save():
    with open(RESULTS_PATH, 'w') as f:
        json.dump(results, f, indent=2, default=str)


def stars(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''


# ===================================================================
# Load panel & derive variables (PAPER_2_PANEL conventions)
# ===================================================================
print('Loading panel ...', flush=True)
COLS = ['RIC', 'Date', 'Region', 'TRBC Industry Name',
        'BuyerInitiated', 'SellerInitiated', 'OrderFlow',
        'SpreadPercent', 'BidAskSpread', 'IntradayVolatility', 'PriceImpact',
        'Volume', 'Turnover', 'CAPM_Beta', 'DailyReturn', 'ExcessReturn',
        'FF_MktRF', 'FF_SMB', 'FF_HML', 'FF_RMW', 'FF_CMA', 'FF_RF',
        'Company Market Cap', 'Dividend yield', 'Price Close',
        'cpi_inflation', 'gdp_growth', 'unemployment',
        'kl_raw', 'kl_weighted', 'low_count_flag']
panel = pd.read_parquet(DATA / 'PAPER_2_PANEL.parquet', columns=COLS)
panel.rename(columns={'Company Market Cap': 'MktCap', 'Dividend yield': 'DivYield'}, inplace=True)
num_cols = panel.select_dtypes(include='number').columns
panel[num_cols] = panel[num_cols].replace([np.inf, -np.inf], np.nan)
panel['log_volume'] = np.log1p(panel['Volume'].clip(lower=0))
panel['log_mktcap'] = np.log(panel['MktCap'].clip(lower=1))
panel['log_turnover'] = np.log1p(panel['Turnover'].clip(lower=0))
panel['abs_order_flow'] = panel['OrderFlow'].abs()
panel['Date_dt'] = pd.to_datetime(panel['Date'])
panel['year_month'] = panel['Date_dt'].dt.to_period('M').astype(str)
print(f'  panel {panel.shape}; kl_raw non-null {panel.kl_raw.notna().mean()*100:.1f}%', flush=True)


# ===================================================================
# 1. CORE FULL READOUTS  (winsorize controls, NOT kl)
# ===================================================================
WINS = ['SpreadPercent', 'IntradayVolatility', 'PriceImpact', 'CAPM_Beta',
        'DailyReturn', 'ExcessReturn', 'abs_order_flow', 'log_volume',
        'log_mktcap', 'DivYield', 'log_turnover',
        'FF_MktRF', 'FF_SMB', 'FF_HML', 'FF_RMW', 'FF_CMA']
core = panel.copy()
for c in WINS:
    q = core[c].quantile([0.01, 0.99])
    core[c] = core[c].clip(q.iloc[0], q.iloc[1])

CTRL_PIN = 'log_volume + log_mktcap + IntradayVolatility + abs_order_flow + log_turnover + cpi_inflation + gdp_growth + unemployment'
CTRL_CAPM = 'log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment'
CTRL_FF = 'FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment'
CORE_SPECS = {
    'pin':  ('SpreadPercent', CTRL_PIN),
    'capm': ('CAPM_Beta',     CTRL_CAPM),
    'ff':   ('ExcessReturn',  CTRL_FF),
}


def readout(model, klterm):
    tidy = model.tidy()
    coefs = {}
    for name, row in tidy.iterrows():
        coefs[name] = {'coef': float(row['Estimate']), 'se': float(row['Std. Error']),
                       'p': float(row['Pr(>|t|)'])}
    diag = {'N': int(model._N), 'r2': float(model._r2),
            'r2_within': float(model._r2_within), 'adj_r2_within': float(model._adj_r2_within)}
    try:
        w = model.wald_test()
        diag['fstat'] = float(w['statistic']) if isinstance(w, dict) else float(np.asarray(w).ravel()[0])
    except Exception as e:
        diag['fstat'] = None
        diag['fstat_err'] = str(e)
    return {'kl_term': klterm, 'coefs': coefs, **diag}


print('\n=== CORE FULL READOUTS ===', flush=True)
core_out = {}
for tag, (dep, ctrl) in CORE_SPECS.items():
    for kl in ['kl_raw', 'kl_weighted']:
        f = f'{dep} ~ {kl} + {ctrl} | RIC + year_month'
        m = pf.feols(f, data=core, vcov={'CRV1': 'RIC'})
        core_out[f'{tag}_{kl}'] = readout(m, kl)
        k = core_out[f'{tag}_{kl}']['coefs'][kl]
        print(f'  {tag:4s} {kl:12s} coef={k["coef"]:+.6f} se={k["se"]:.6f} p={k["p"]:.4f} '
              f'N={core_out[f"{tag}_{kl}"]["N"]:,} R2={core_out[f"{tag}_{kl}"]["r2"]:.3f}', flush=True)
results['core_readouts'] = core_out
save()


# ===================================================================
# reviewer_response prepare(): subset+dropna, winsorize ALL numerics incl kl
# ===================================================================
def prep_rr(df, dep, kind):
    d = df.copy()
    d['YearMonth'] = pd.to_datetime(d['Date']).dt.to_period('M').astype(str)
    d['log_volume'] = np.log1p(d['Volume'].clip(lower=0))
    d['log_mktcap'] = np.log1p(d['MktCap'].clip(lower=0))
    d['log_turnover'] = np.log1p(d['Turnover'].clip(lower=0))
    d['abs_orderflow'] = d['OrderFlow'].abs()
    if kind == 'pin':
        cols = [dep, 'kl_raw', 'kl_weighted', 'log_volume', 'log_mktcap', 'IntradayVolatility',
                'abs_orderflow', 'log_turnover', 'cpi_inflation', 'gdp_growth', 'unemployment',
                'RIC', 'YearMonth', 'Date']
    elif kind == 'capm':
        cols = [dep, 'kl_raw', 'kl_weighted', 'log_volume', 'log_mktcap', 'SpreadPercent',
                'DivYield', 'IntradayVolatility', 'cpi_inflation', 'gdp_growth', 'unemployment',
                'RIC', 'YearMonth', 'Date']
    else:
        cols = [dep, 'kl_raw', 'kl_weighted', 'FF_MktRF', 'FF_SMB', 'FF_HML', 'FF_RMW', 'FF_CMA',
                'log_volume', 'log_mktcap', 'SpreadPercent', 'DivYield', 'IntradayVolatility',
                'cpi_inflation', 'gdp_growth', 'unemployment', 'RIC', 'YearMonth', 'Date']
    d = d[[c for c in cols if c in d.columns]].dropna()
    for c in d.select_dtypes(include=[np.number]).columns:
        lo, hi = d[c].quantile([0.01, 0.99])
        d[c] = d[c].clip(lo, hi)
    return d


F_PIN = 'SpreadPercent ~ {kl} + log_volume + log_mktcap + IntradayVolatility + abs_orderflow + log_turnover + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth'
F_FF = 'ExcessReturn ~ {kl} + FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth'


def fit_kl(formula, data, kl):
    m = pf.feols(formula.format(kl=kl), data=data, vcov={'CRV1': 'RIC'})
    return {'coef': float(m.coef()[kl]), 'se': float(m.se()[kl]), 'p': float(m.pvalue()[kl]),
            'N': int(m._N), 'r2': float(m._r2), 'r2_within': float(m._r2_within)}


# ----- standardized effects (Model I) -----
print('\n=== STD EFFECTS ===', flush=True)
fd = prep_rr(panel, 'SpreadPercent', 'pin')
std = fd.copy()
for v in ['kl_raw', 'log_volume', 'log_mktcap', 'IntradayVolatility', 'abs_orderflow',
          'log_turnover', 'cpi_inflation', 'gdp_growth', 'unemployment']:
    std[f'{v}_z'] = (std[v] - std[v].mean()) / std[v].std()
m_std = pf.feols('SpreadPercent ~ kl_raw_z + log_volume_z + log_mktcap_z + IntradayVolatility_z + '
                 'abs_orderflow_z + log_turnover_z + cpi_inflation_z + gdp_growth_z + unemployment_z | RIC + YearMonth',
                 data=std, vcov={'CRV1': 'RIC'})
results['std_effects'] = {v: {'coef': float(m_std.coef()[f'{v}_z']), 'se': float(m_std.se()[f'{v}_z']),
                              'p': float(m_std.pvalue()[f'{v}_z'])}
                          for v in ['kl_raw', 'log_volume', 'log_mktcap', 'IntradayVolatility',
                                    'abs_orderflow', 'log_turnover', 'cpi_inflation', 'gdp_growth', 'unemployment']}
results['std_effects']['N'] = int(m_std._N)
print('  kl_raw_z', results['std_effects']['kl_raw'], flush=True)
save()

# ----- region splits (Model I raw+wt, + FF wt) -----
print('\n=== REGION SPLITS ===', flush=True)
region = {}
for label, regs in [('English (US+UK)', ['US', 'UK']), ('Non-English (CN+JP)', ['CN', 'JP']), ('EU', ['EU'])]:
    sub = panel[panel['Region'].isin(regs)]
    d = prep_rr(sub, 'SpreadPercent', 'pin')
    row = {'N': int(len(d)), 'firms': int(sub['RIC'].nunique())}
    row['raw'] = fit_kl(F_PIN, d, 'kl_raw')
    row['wt'] = fit_kl(F_PIN, d, 'kl_weighted')
    region[label] = row
    print(f'  {label}: raw={row["raw"]["coef"]:+.6f}(p={row["raw"]["p"]:.3f}) '
          f'wt={row["wt"]["coef"]:+.6f}(p={row["wt"]["p"]:.3f}) N={row["N"]:,}', flush=True)
results['region_modelI'] = region
save()

# ----- placebo (Model I raw+wt) -----
print('\n=== PLACEBO ===', flush=True)
placebo_inds = ['Pharmaceuticals', 'Software', 'IT Services & Consulting',
                'Medical Equipment, Supplies & Distribution', 'Computer Hardware',
                'Communications & Networking', 'Hotels, Motels & Cruise Lines',
                'Apparel & Accessories', 'Textiles & Leather Goods', 'Business Support Services']
plc = panel[panel['TRBC Industry Name'].isin(placebo_inds)]
dpl = prep_rr(plc, 'SpreadPercent', 'pin')
results['placebo'] = {'N': int(len(dpl)), 'firms': int(plc['RIC'].nunique()),
                      'raw': fit_kl(F_PIN, dpl, 'kl_raw'), 'wt': fit_kl(F_PIN, dpl, 'kl_weighted')}
print('  placebo', results['placebo']['raw'], results['placebo']['wt'], flush=True)
save()

# ----- subperiod + low-count (weighted Model I) -----
print('\n=== SUBPERIOD / LOW-COUNT ===', flush=True)
fd['Date_dt'] = pd.to_datetime(fd['Date'])
sub_res = {}
for nm, lo, hi in [('2012-2018', '2012-01-01', '2018-12-31'), ('2019-2025', '2019-01-01', '2025-12-31')]:
    s = fd[(fd['Date_dt'] >= lo) & (fd['Date_dt'] <= hi)]
    sub_res[nm] = fit_kl(F_PIN, s, 'kl_weighted')
    print(f'  {nm}: wt={sub_res[nm]["coef"]:+.6f} p={sub_res[nm]["p"]:.4f}', flush=True)
# low-count exclusion: need low_count_flag per date
lc = panel[['Date', 'low_count_flag']].drop_duplicates('Date')
fd2 = fd.merge(lc, on='Date', how='left')
fd2 = fd2[fd2['low_count_flag'] != True]
sub_res['lowcount_excl_raw'] = fit_kl(F_PIN, fd2, 'kl_raw')
sub_res['lowcount_excl_wt'] = fit_kl(F_PIN, fd2, 'kl_weighted')
results['subperiod'] = sub_res
save()

# ----- asia lag (CN+JP, contemporaneous vs previous-calendar-day weighted KL) -----
print('\n=== ASIA LAG ===', flush=True)
asia = panel[panel['Region'].isin(['CN', 'JP'])].copy()
daily_kl = panel[['Date', 'kl_weighted']].drop_duplicates('Date').copy()
daily_kl['Date_dt'] = pd.to_datetime(daily_kl['Date'])
daily_kl_lag = daily_kl.copy()
daily_kl_lag['Date_dt'] = daily_kl_lag['Date_dt'] + pd.Timedelta(days=1)
daily_kl_lag = daily_kl_lag[['Date_dt', 'kl_weighted']].rename(columns={'kl_weighted': 'kl_weighted_lag1'})
asia['Date_dt'] = pd.to_datetime(asia['Date'])
asia = asia.merge(daily_kl_lag, on='Date_dt', how='left')
da = prep_rr(asia, 'SpreadPercent', 'pin')
# bring lag in (prep_rr drops it); re-merge by Date
da = da.merge(asia[['RIC', 'Date', 'kl_weighted_lag1']].drop_duplicates(['RIC', 'Date']), on=['RIC', 'Date'], how='left')
da = da.dropna(subset=['kl_weighted_lag1'])
m_con = pf.feols(F_PIN.format(kl='kl_weighted'), data=da, vcov={'CRV1': 'RIC'})
m_lag = pf.feols(F_PIN.format(kl='kl_weighted_lag1'), data=da, vcov={'CRV1': 'RIC'})
results['asia_lag'] = {
    'N': int(m_con._N),
    'contemporaneous': {'coef': float(m_con.coef()['kl_weighted']), 'se': float(m_con.se()['kl_weighted']), 'p': float(m_con.pvalue()['kl_weighted'])},
    'previous_day': {'coef': float(m_lag.coef()['kl_weighted_lag1']), 'se': float(m_lag.se()['kl_weighted_lag1']), 'p': float(m_lag.pvalue()['kl_weighted_lag1'])},
}
print('  asia', results['asia_lag'], flush=True)
save()


# ===================================================================
# run_revision prepare(): winsorize all numerics EXCEPT kl
# ===================================================================
renewable_ind = {'Renewable Energy Equipment & Services', 'Renewable Fuels'}
fossil_ind = {'Coal', 'Oil & Gas Refining and Marketing', 'Oil & Gas Exploration and Production',
              'Oil Related Services and Equipment', 'Oil & Gas Transportation Services',
              'Integrated Oil & Gas', 'Oil & Gas Drilling'}
climate_ind = renewable_ind | fossil_ind


def prep_rev(df, dep, kind, extra=()):
    d = df.copy()
    d['YearMonth'] = pd.to_datetime(d['Date']).dt.to_period('M').astype(str)
    d['log_volume'] = np.log1p(d['Volume'].clip(lower=0))
    d['log_mktcap'] = np.log1p(d['MktCap'].clip(lower=0))
    d['log_turnover'] = np.log1p(d['Turnover'].clip(lower=0))
    d['abs_orderflow'] = d['OrderFlow'].abs()
    if kind == 'pin':
        ctrls = ['log_volume', 'log_mktcap', 'IntradayVolatility', 'abs_orderflow', 'log_turnover',
                 'cpi_inflation', 'gdp_growth', 'unemployment']
    else:
        ctrls = ['FF_MktRF', 'FF_SMB', 'FF_HML', 'FF_RMW', 'FF_CMA', 'log_volume', 'log_mktcap',
                 'SpreadPercent', 'DivYield', 'IntradayVolatility', 'cpi_inflation', 'gdp_growth', 'unemployment']
    cols = [dep, 'kl_weighted', 'kl_raw'] + ctrls + ['RIC', 'YearMonth', 'Date', 'Region', 'TRBC Industry Name', 'MktCap'] + list(extra)
    d = d[[c for c in cols if c in d.columns]].dropna()
    for c in d.select_dtypes(include=[np.number]).columns:
        if c in ('kl_weighted', 'kl_raw'):
            continue
        lo, hi = d[c].quantile([0.01, 0.99])
        d[c] = d[c].clip(lo, hi)
    return d


def fit_2way(formula, data, term):
    m = pf.feols(formula, data=data, vcov={'CRV1': 'RIC+Date'})
    return {'coef': float(m.coef()[term]), 'se': float(m.se()[term]),
            'p': float(m.pvalue()[term]), 'N': int(data.shape[0])}


RF_PIN = 'SpreadPercent ~ {kl} + log_volume + log_mktcap + IntradayVolatility + abs_orderflow + log_turnover + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth'
RF_FF = 'ExcessReturn ~ {kl} + FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth'

print('\n=== TWO-WAY CLUSTERED (raw + weighted) ===', flush=True)
tw = {}
pin_rev = prep_rev(panel, 'SpreadPercent', 'pin')
ff_rev = prep_rev(panel, 'ExcessReturn', 'ff')


def prep_capm_rev(df):
    d = df.copy()
    d['YearMonth'] = pd.to_datetime(d['Date']).dt.to_period('M').astype(str)
    d['log_volume'] = np.log1p(d['Volume'].clip(lower=0)); d['log_mktcap'] = np.log1p(d['MktCap'].clip(lower=0))
    cols = ['CAPM_Beta', 'kl_weighted', 'kl_raw', 'log_volume', 'log_mktcap', 'SpreadPercent', 'DivYield',
            'IntradayVolatility', 'cpi_inflation', 'gdp_growth', 'unemployment', 'RIC', 'YearMonth', 'Date']
    d = d[[c for c in cols if c in d.columns]].dropna()
    for c in d.select_dtypes(include=[np.number]).columns:
        if c in ('kl_weighted', 'kl_raw'):
            continue
        lo, hi = d[c].quantile([0.01, 0.99]); d[c] = d[c].clip(lo, hi)
    return d


capm_rev = prep_capm_rev(panel)
RF_CAPM = 'CAPM_Beta ~ {kl} + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth'
for kl in ['kl_weighted', 'kl_raw']:
    tw[f'ModelI_Spread_{kl}'] = fit_2way(RF_PIN.format(kl=kl), pin_rev, kl)
    tw[f'ModelII_CAPM_{kl}'] = fit_2way(RF_CAPM.format(kl=kl), capm_rev, kl)
    tw[f'ModelIII_FF_{kl}'] = fit_2way(RF_FF.format(kl=kl), ff_rev, kl)
    print(f'  {kl}: I={tw[f"ModelI_Spread_{kl}"]["coef"]:+.5f}(p={tw[f"ModelI_Spread_{kl}"]["p"]:.3f}) '
          f'II={tw[f"ModelII_CAPM_{kl}"]["coef"]:+.5f} III={tw[f"ModelIII_FF_{kl}"]["coef"]:+.5f}', flush=True)
# region / placebo / climate-only / EN x climate two-way (weighted)
for label, mask in [
    ('EN', panel['Region'].isin(['US', 'UK'])),
    ('Asia', panel['Region'].isin(['CN', 'JP'])),
    ('EU', panel['Region'].isin(['EU'])),
    ('placebo', panel['TRBC Industry Name'].isin(placebo_inds)),
    ('climate_only', panel['TRBC Industry Name'].isin(climate_ind)),
    ('EN_climate', panel['Region'].isin(['US', 'UK']) & panel['TRBC Industry Name'].isin(climate_ind)),
]:
    sub = panel[mask]
    dpin = prep_rev(sub, 'SpreadPercent', 'pin')
    if len(dpin) >= 1000:
        tw[f'{label}_Spread'] = fit_2way(RF_PIN.format(kl='kl_weighted'), dpin, 'kl_weighted')
    dff = prep_rev(sub, 'ExcessReturn', 'ff')
    if len(dff) >= 1000:
        tw[f'{label}_FF'] = fit_2way(RF_FF.format(kl='kl_weighted'), dff, 'kl_weighted')
    print(f'  [2way] {label}: Spread={tw.get(f"{label}_Spread",{}).get("coef")} FF={tw.get(f"{label}_FF",{}).get("coef")}', flush=True)
results['twoway'] = tw
save()

# ----- triple interaction (weighted), Spread + FF -----
print('\n=== TRIPLE INTERACTION ===', flush=True)
def run_triple(dep, kind, basef):
    d = prep_rev(panel, dep, kind, extra=())
    # rebuild flags on the prepared frame
    d = d.merge(panel[['RIC', 'Date', 'TRBC Industry Name', 'Region']].drop_duplicates(['RIC', 'Date']),
                on=['RIC', 'Date'], how='left', suffixes=('', '_y'))
    d['ClimateExp'] = d['TRBC Industry Name'].isin(climate_ind).astype(int)
    d['EnglishRegion'] = d['Region'].isin(['US', 'UK']).astype(int)
    d['Post2019'] = (pd.to_datetime(d['Date']) >= '2019-01-01').astype(int)
    d['kl_x_clim'] = d['kl_weighted'] * d['ClimateExp']
    d['kl_x_eng'] = d['kl_weighted'] * d['EnglishRegion']
    d['kl_x_post'] = d['kl_weighted'] * d['Post2019']
    d['kl_x_clim_eng'] = d['kl_weighted'] * d['ClimateExp'] * d['EnglishRegion']
    d['kl_x_clim_post'] = d['kl_weighted'] * d['ClimateExp'] * d['Post2019']
    d['kl_x_eng_post'] = d['kl_weighted'] * d['EnglishRegion'] * d['Post2019']
    d['kl_x_clim_eng_post'] = d['kl_weighted'] * d['ClimateExp'] * d['EnglishRegion'] * d['Post2019']
    m = pf.feols(basef, data=d, vcov={'CRV1': 'RIC+Date'})
    terms = ['kl_weighted', 'kl_x_clim', 'kl_x_eng', 'kl_x_post', 'kl_x_clim_eng',
             'kl_x_clim_post', 'kl_x_eng_post', 'kl_x_clim_eng_post']
    return {'N': int(d.shape[0]), **{t: {'coef': float(m.coef()[t]), 'se': float(m.se()[t]),
                                         'p': float(m.pvalue()[t])} for t in terms}}

triple_terms = '+ kl_x_clim + kl_x_eng + kl_x_post + kl_x_clim_eng + kl_x_clim_post + kl_x_eng_post + kl_x_clim_eng_post'
basef_pin = ('SpreadPercent ~ kl_weighted ' + triple_terms +
             ' + log_volume + log_mktcap + IntradayVolatility + abs_orderflow + log_turnover + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth')
basef_ff = ('ExcessReturn ~ kl_weighted ' + triple_terms +
            ' + FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth')
results['triple_spread'] = run_triple('SpreadPercent', 'pin', basef_pin)
results['triple_ff'] = run_triple('ExcessReturn', 'ff', basef_ff)
print('  triple done', flush=True)
save()


# ===================================================================
# ENERGY: full readouts (core spec) + sign-flip decomposition
# ===================================================================
print('\n=== ENERGY READOUTS + SIGN-FLIP ===', flush=True)
energy = pd.read_parquet(DATA / 'PAPER_2_PANEL_energy.parquet')
energy.rename(columns={'Company Market Cap': 'MktCap', 'Dividend yield': 'DivYield'}, inplace=True)
en = energy.copy()
en[en.select_dtypes(include='number').columns] = en.select_dtypes(include='number').replace([np.inf, -np.inf], np.nan)
en['log_volume'] = np.log1p(en['Volume'].clip(lower=0))
en['log_mktcap'] = np.log(en['MktCap'].clip(lower=1))
en['log_turnover'] = np.log1p(en['Turnover'].clip(lower=0))
en['abs_order_flow'] = en['OrderFlow'].abs()
en['year_month'] = pd.to_datetime(en['Date']).dt.to_period('M').astype(str)
for c in [w for w in WINS if w in en.columns]:
    q = en[c].quantile([0.01, 0.99]); en[c] = en[c].clip(q.iloc[0], q.iloc[1])
energy_out = {}
for tag, (dep, ctrl) in CORE_SPECS.items():
    for kl in ['kl_raw', 'kl_weighted']:
        f = f'{dep} ~ {kl} + {ctrl} | RIC + year_month'
        m = pf.feols(f, data=en, vcov={'CRV1': 'RIC'})
        energy_out[f'{tag}_{kl}'] = readout(m, kl)
        kk = energy_out[f'{tag}_{kl}']['coefs'][kl]
        print(f'  energy {tag:4s} {kl:12s} coef={kk["coef"]:+.6f} p={kk["p"]:.4f} N={energy_out[f"{tag}_{kl}"]["N"]:,}', flush=True)
results['energy_readouts'] = energy_out
save()

# sign-flip decomposition (FF weighted, two-way) by type/region/period
energy['energy_type'] = 'Other'
energy.loc[energy['TRBC Industry Name'].isin(renewable_ind), 'energy_type'] = 'Renewable'
energy.loc[energy['TRBC Industry Name'].isin(fossil_ind), 'energy_type'] = 'Fossil'
sf = {}
for key, mask in [('Renewable', energy['energy_type'] == 'Renewable'),
                  ('Fossil', energy['energy_type'] == 'Fossil'),
                  ('US', energy['Region'] == 'US'),
                  ('CN', energy['Region'] == 'CN'),
                  ('Pre_2019', pd.to_datetime(energy['Date']) <= '2018-12-31'),
                  ('Post_2019', pd.to_datetime(energy['Date']) >= '2019-01-01')]:
    d = prep_rev(energy[mask], 'ExcessReturn', 'ff')
    if len(d) < 1000:
        continue
    sf[key] = fit_2way(RF_FF.format(kl='kl_weighted'), d, 'kl_weighted')
    print(f'  signflip {key}: {sf[key]["coef"]:+.5f} (p={sf[key]["p"]:.4f}, N={sf[key]["N"]:,})', flush=True)
results['energy_signflip'] = sf
save()

print(f'\nALL DONE in {(time.time()-t_start)/60:.1f} min -> {RESULTS_PATH}', flush=True)
