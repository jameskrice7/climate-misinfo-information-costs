"""Rebuild the daily misinformation KL index on the 5-model ensemble and merge
it into PAPER_2_PANEL.

Replicates EXACTLY the method in construct_daily_misinfo_measure.ipynb
(confidence-weighted per-post ensemble -> B=20-bin background P -> daily KL),
changing only the model set from {gpt-4.1-nano, gpt-4.1, bert, roberta} to:

    gpt-4.1-nano, gpt-4.1, qwen25_7b, nemotron_nano_8b, phi35_mini

Two indices are produced, identical in spirit to before:
  * kl_raw       — each post contributes equally (unweighted daily histogram)
  * kl_weighted  — each post weighted by engagement (likes+shares+comments+reactions+1)

ERROR / garbled labels (qwen 43k, phi 381, nemotron 99 + a few corrupt strings)
are treated as MISSING for that model on that post, NOT as 'not misinfo'.
The per-post ensemble is the mean over only the models that returned a valid
label, so error-heavy days are not artificially pushed toward 0 — the daily
index stays continuous with no gaps.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.special import rel_entr

BASE = Path('/home/jameskrice/Downloads/Paper 2')
SRC = BASE / 'local_llm_classification' / 'gpt_classifications_with_metadata_plus_llms.parquet'
PANEL = BASE / 'PAPER_2_PANEL.parquet'
DAILY_OUT = BASE / 'daily_misinfo_kl_measure_5models.parquet'
DAILY_OUT_CSV = BASE / 'daily_misinfo_kl_measure_5models.csv'
KL_BACKUP = BASE / 'PAPER_2_PANEL_old_kl_backup.parquet'   # Date-level backup of dropped cols

# 2 GPT models + the 3 local LLMs that replaced the BERT family.
MODELS = {
    'gpt-4.1-nano':     ('gpt-4.1-nano_classification',     'gpt-4.1-nano_confidence'),
    'gpt-4.1':          ('gpt-4.1_classification',          'gpt-4.1_confidence'),
    'qwen25_7b':        ('qwen25_7b_classification',        'qwen25_7b_confidence'),
    'nemotron_nano_8b': ('nemotron_nano_8b_classification', 'nemotron_nano_8b_confidence'),
    'phi35_mini':       ('phi35_mini_classification',       'phi35_mini_confidence'),
}
K = len(MODELS)

B = 20            # bins (matches original)
EPSILON = 1e-10   # Laplace smoothing for zero-prob bins (matches original)
bin_edges = np.linspace(0, 1, B + 1)


def classify_label(series: pd.Series):
    """Return (is_misinfo: bool, is_valid: bool) per row.

    valid  = an interpretable judgement was returned
    is_misinfo = MISINFORMATION; NOT_MIS* variants are valid not-misinfo;
    ERROR and garbled tokens (MISINIRONMENT, MISINFINITY, ...) are invalid.
    """
    s = series.astype(str).str.upper().str.strip()
    is_mis = s.eq('MISINFORMATION')
    is_not = s.str.startswith('NOT_MIS')      # NOT_MISINFORMATION / NOT_MISFORMATION / NOT_MISINIFICATION
    is_valid = is_mis | is_not
    return is_mis, is_valid


def main() -> None:
    print('Loading classifications ...', flush=True)
    need = ['post_id', 'creation_time',
            'statistics.like_count', 'statistics.share_count',
            'statistics.comment_count', 'statistics.reaction_count']
    for cls, conf in MODELS.values():
        need += [cls, conf]
    df = pd.read_parquet(SRC, columns=need)
    print(f'  {len(df):,} posts', flush=True)

    df['creation_time'] = pd.to_datetime(df['creation_time'], utc=True)
    df['date'] = df['creation_time'].dt.date

    # ---- per-post confidence-weighted ensemble (NaN where a model is invalid) ----
    score_cols = []
    for name, (cls_col, conf_col) in MODELS.items():
        is_mis, is_valid = classify_label(df[cls_col])
        conf = (df[conf_col].clip(0, 100).fillna(50) / 100.0)
        s = np.where(is_mis, conf, 0.0)            # not-misinfo -> 0
        s = np.where(is_valid.to_numpy(), s, np.nan)  # invalid -> NaN (dropped from mean)
        df[f'{name}_score'] = s
        score_cols.append(f'{name}_score')
        print(f'  {name:18s} valid={is_valid.sum():>7,}  misinfo={is_mis.sum():>6,}  '
              f'invalid={(~is_valid).sum():>6,}', flush=True)

    # mean over valid models only (pandas .mean skips NaN)
    df['ensemble_score'] = df[score_cols].mean(axis=1)
    df['n_valid_models'] = df[score_cols].notna().sum(axis=1)

    n_all_missing = int((df['n_valid_models'] == 0).sum())
    print(f'\nPosts with NO valid model (dropped from index): {n_all_missing:,}', flush=True)
    print('n_valid_models distribution:')
    print(df['n_valid_models'].value_counts().sort_index().to_string(), flush=True)

    # engagement weight (Laplace +1), exactly as original
    df['engagement_weight'] = (
        df['statistics.like_count'].fillna(0)
        + df['statistics.share_count'].fillna(0)
        + df['statistics.comment_count'].fillna(0)
        + df['statistics.reaction_count'].fillna(0)
        + 1
    )

    # work only on posts that got a score
    dfv = df[df['ensemble_score'].notna()].copy()
    print(f'\nScored posts used for histograms: {len(dfv):,}', flush=True)
    print('Ensemble score: mean=%.4f median=%.4f zero=%.1f%% >0=%.1f%%' % (
        dfv['ensemble_score'].mean(), dfv['ensemble_score'].median(),
        (dfv['ensemble_score'] == 0).mean() * 100,
        (dfv['ensemble_score'] > 0).mean() * 100), flush=True)

    # ---- background distributions P (raw + engagement-weighted) ----
    bg_counts_raw, _ = np.histogram(dfv['ensemble_score'], bins=bin_edges)
    bg_raw = bg_counts_raw / bg_counts_raw.sum()
    bg_raw = np.maximum(bg_raw, EPSILON); bg_raw = bg_raw / bg_raw.sum()

    bin_idx = np.clip(np.digitize(dfv['ensemble_score'].to_numpy(), bin_edges) - 1, 0, B - 1)
    ew = dfv['engagement_weight'].to_numpy()
    bg_counts_wt = np.bincount(bin_idx, weights=ew, minlength=B)
    bg_wt = bg_counts_wt / bg_counts_wt.sum()
    bg_wt = np.maximum(bg_wt, EPSILON); bg_wt = bg_wt / bg_wt.sum()

    # ---- daily KL ----
    records = []
    for d, day_df in dfv.groupby('date', sort=True):
        n = len(day_df)
        es = day_df['ensemble_score'].to_numpy()
        w = day_df['engagement_weight'].to_numpy()

        cnt_raw, _ = np.histogram(es, bins=bin_edges)
        q_raw = cnt_raw / cnt_raw.sum() if cnt_raw.sum() > 0 else np.ones(B) / B
        q_raw = np.maximum(q_raw, EPSILON); q_raw = q_raw / q_raw.sum()
        kl_raw = float(np.sum(rel_entr(q_raw, bg_raw)))

        di = np.clip(np.digitize(es, bin_edges) - 1, 0, B - 1)
        cnt_wt = np.bincount(di, weights=w, minlength=B)
        q_wt = cnt_wt / cnt_wt.sum() if cnt_wt.sum() > 0 else np.ones(B) / B
        q_wt = np.maximum(q_wt, EPSILON); q_wt = q_wt / q_wt.sum()
        kl_weighted = float(np.sum(rel_entr(q_wt, bg_wt)))

        misinfo_count = int((es >= 0.5).sum())
        total_engagement = float(w.sum() - n)   # subtract Laplace +1
        records.append({
            'Date': d.strftime('%Y-%m-%d'),
            'kl_raw': kl_raw,
            'kl_weighted': kl_weighted,
            'n_posts': n,
            'misinfo_count': misinfo_count,
            'misinfo_prevalence': misinfo_count / n if n else 0.0,
            'mean_ensemble_score': float(es.mean()),
            'total_engagement': total_engagement,
            'mean_engagement': total_engagement / n if n else 0.0,
            'low_count_flag': int(n < 5),
        })

    daily = pd.DataFrame(records)
    daily['Date'] = daily['Date'].astype(str)
    print(f'\nDaily measure: {len(daily)} days  {daily.Date.min()} -> {daily.Date.max()}', flush=True)
    print(daily[['kl_raw', 'kl_weighted', 'n_posts', 'misinfo_prevalence']].describe().round(4).to_string(), flush=True)

    daily.to_parquet(DAILY_OUT, index=False)
    daily.to_csv(DAILY_OUT_CSV, index=False)
    print(f'\nWrote {DAILY_OUT.name} and {DAILY_OUT_CSV.name}', flush=True)

    # ---- merge into PAPER_2_PANEL (drop old kl_raw/kl_weighted, add new) ----
    print('\nLoading panel ...', flush=True)
    panel = pd.read_parquet(PANEL)
    print(f'  panel {panel.shape}', flush=True)

    old_kl = [c for c in ['kl_raw', 'kl_weighted'] if c in panel.columns]
    if old_kl:
        # tiny Date-level backup of the columns we are dropping (reversible).
        # Guard: don't clobber an existing good backup with all-NaN columns.
        nonnull = int(panel[old_kl].notna().any(axis=1).sum())
        if KL_BACKUP.exists() and nonnull == 0:
            print(f'  panel kl cols are all-NaN; keeping existing backup {KL_BACKUP.name}', flush=True)
        else:
            bk = panel[['Date'] + old_kl].drop_duplicates('Date').reset_index(drop=True)
            bk.to_parquet(KL_BACKUP, index=False)
            print(f'  backed up old {old_kl} ({len(bk)} dates) -> {KL_BACKUP.name}', flush=True)
        panel = panel.drop(columns=old_kl)

    # Panel Date is datetime.date; daily Date is 'YYYY-MM-DD' string. Match on
    # a normalized datetime.date key so the join actually lands.
    daily_m = daily[['Date', 'kl_raw', 'kl_weighted']].copy()
    daily_m['Date'] = pd.to_datetime(daily_m['Date']).dt.date
    panel['Date'] = pd.to_datetime(panel['Date']).dt.date
    panel = panel.merge(daily_m, on='Date', how='left')
    cov = panel['kl_raw'].notna().mean() * 100
    print(f'  merged; kl_raw non-null on {cov:.1f}% of panel rows; shape {panel.shape}', flush=True)

    tmp = PANEL.with_suffix('.parquet.tmp')
    panel.to_parquet(tmp, index=False)
    tmp.replace(PANEL)
    print(f'  wrote {PANEL.name} ({PANEL.stat().st_size/1e6:.0f} MB)', flush=True)
    print('\nDONE.', flush=True)


if __name__ == '__main__':
    main()
