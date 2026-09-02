"""Step 0: refresh ALL daily-derived columns in PAPER_2_PANEL from the new
5-model daily measure, and rebuild the energy subsample panel.

build_kl_5models.py already replaced kl_raw/kl_weighted; here we also refresh
the auxiliary daily columns (n_posts, misinfo_count, misinfo_prevalence,
mean_ensemble_score, total_engagement, mean_engagement, low_count_flag) so the
whole panel is internally consistent with the new ensemble, then carve out the
energy subsample exactly as energy_mini_nn_and_econometrics.ipynb does.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

BASE = Path('/home/jameskrice/Downloads/Paper 2')
PANEL = BASE / 'PAPER_2_PANEL.parquet'
DAILY = BASE / 'daily_misinfo_kl_measure_5models.parquet'
ENERGY_PARQUET = BASE / 'PAPER_2_PANEL_energy.parquet'
ENERGY_CSV = BASE / 'PAPER_2_PANEL_energy.csv'

DAILY_COLS = ['kl_raw', 'kl_weighted', 'n_posts', 'misinfo_count',
              'misinfo_prevalence', 'mean_ensemble_score', 'total_engagement',
              'mean_engagement', 'low_count_flag']

INCLUDE = (r'(renewable|solar|wind|hydro|geothermal|biofuel|bioenergy|'
           r'renewable fuels|oil\s*&\s*gas|petroleum|coal|refining|exploration|'
           r'drilling|oil related services|integrated oil\s*&\s*gas|'
           r'oil\s*&\s*gas transportation)')
EXCLUDE = r'(integrated telecommunications|integrated hardware|utilities)'


def main() -> None:
    print('Loading panel ...', flush=True)
    panel = pd.read_parquet(PANEL)
    print(f'  {panel.shape}', flush=True)

    daily = pd.read_parquet(DAILY)
    daily_m = daily[['Date'] + DAILY_COLS].copy()
    daily_m['Date'] = pd.to_datetime(daily_m['Date']).dt.date

    panel = panel.drop(columns=[c for c in DAILY_COLS if c in panel.columns])
    panel['Date'] = pd.to_datetime(panel['Date']).dt.date
    panel = panel.merge(daily_m, on='Date', how='left')
    print(f'  refreshed {len(DAILY_COLS)} daily cols; kl_raw non-null '
          f'{panel["kl_raw"].notna().mean()*100:.1f}%; shape {panel.shape}', flush=True)

    tmp = PANEL.with_suffix('.parquet.tmp')
    panel.to_parquet(tmp, index=False)
    tmp.replace(PANEL)
    print(f'  wrote {PANEL.name}', flush=True)

    # ---- energy subsample (RIC-level: any day classified energy) ----
    trbc = panel['TRBC Industry Name'].fillna('').str.lower()
    is_energy = trbc.str.contains(INCLUDE, regex=True) & ~trbc.str.contains(EXCLUDE, regex=True)
    energy_rics = set(panel.assign(_e=is_energy).groupby('RIC')['_e'].any().pipe(lambda s: s[s].index))
    energy = panel[panel['RIC'].isin(energy_rics)].copy()
    print(f'\nEnergy subsample: {energy.shape[0]:,} rows, {energy["RIC"].nunique():,} firms', flush=True)

    energy.to_parquet(ENERGY_PARQUET, index=False)
    energy.to_csv(ENERGY_CSV, index=False)
    print(f'  wrote {ENERGY_PARQUET.name} ({ENERGY_PARQUET.stat().st_size/1e6:.0f} MB) '
          f'and {ENERGY_CSV.name} ({ENERGY_CSV.stat().st_size/1e6:.0f} MB)', flush=True)
    print('\nDONE.', flush=True)


if __name__ == '__main__':
    main()
