# The Information Costs of Climate Misinformation

Replication materials for *"The Information Costs of Climate Misinformation:
Evidence from Global Financial Data"* (James K. Rice, University of Essex).

The paper asks whether daily variation in the **distributional character** of
climate misinformation moves firm-level information costs. Misinformation is
measured not by prevalence but by a **KL divergence** of the day's
misinformation-score distribution from a stable background distribution,
constructed from a five-model LLM ensemble. That index is merged onto a global
firm-day panel and used as the regressor of interest.

## Repository layout

```
Code/
  main_analysis.py        THE main-analysis script. Reproduces every headline
                          regression from the panel + the KL index, writing all
                          numbers to output/main_results/econ_results.json.
  build_kl_index.py       Rebuilds the daily KL index from per-post ensemble
                          classifications (needs the raw post-level file, which
                          is not distributed — see "What is not included").
  refresh_panel.py        Refreshes all daily-derived panel columns from the
                          daily measure and carves out the energy subsample.

Data/
  panel_parts/            PAPER_2_PANEL.parquet, split into 95 MB parts.
                          Run rebuild_panel.py before analysis. See below.
  rebuild_panel.py        Reassembles the full panel from panel_parts/.
  PAPER_2_PANEL_energy.parquet          Energy-exposed subsample (81.8 MB).
  daily_misinfo_kl_measure_5models.parquet
                          The daily KL index itself (5,148 days).

Results/
  econ_results.json       All headline regression output.
  desc_results.json       Ensemble descriptives, model agreement, KL summary.
  dk_results.json         Driscoll–Kraay standard errors.
  energy_dl.json          Energy-subsample distributed-lag results.
  extras.json             Amihud illiquidity, shock days, event study.
  attention.json          Attention-quintile splits.
  std_effects_fullstd.json  Fully standardized effects.
  01_econometrics.log     Console log of the original run.
  *.png                   Figures.
```

## The panel is stored in parts

`PAPER_2_PANEL.parquet` is **2,177 MB** — 19,183,738 firm-day rows × 59
columns. That exceeds GitHub's 100 MB per-file limit, and also Git LFS's 2 GB
per-file limit, so it cannot be stored here as a single file. It is split into
`Data/panel_parts/` as parquet parts of at most 95 MB each, one per source row
group, plus a `manifest.json`.

Reassemble it before running the analysis:

```bash
python Data/rebuild_panel.py            # -> Data/PAPER_2_PANEL.parquet
python Data/rebuild_panel.py --verify   # slower; also checks part checksums
```

Needs ~2.2 GB of free disk. The reassembled panel has the same row order and
the same values as the original; only the compression codec differs (zstd in
the parts, Snappy in the original), which changes the bytes on disk but not the
data. Each part was compared against its source row group with pyarrow's
`Table.equals` when the split was made, and all 19 matched exactly. `--verify`
checks each part's SHA-256 against `manifest.json`, confirming your copy is
byte-identical to what was published here.

## How to replicate

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python Data/rebuild_panel.py
python Code/main_analysis.py
```

`main_analysis.py` expects the panel at `Data/PAPER_2_PANEL.parquet` and writes
to `output/main_results/econ_results.json`. Requires Python ≥ 3.10, pandas,
numpy, and `pyfixest==0.40.1` (the pinned version matters — fixed-effect
estimation details changed across releases).

## The KL index

The index is built from ~265,000 classified climate-related social media posts.
Each post is scored by five models, and the per-post ensemble score is the
confidence-weighted mean over the models that returned a valid label:

| Model | Misinfo prevalence | Mean confidence | Invalid labels |
|---|---|---|---|
| GPT-4.1-nano | 2.68% | 73.4 | 10 |
| GPT-4.1 | 4.07% | 98.4 | 9 |
| Qwen2.5-7B | 4.34% | 88.9 | 43,164 |
| Nemotron-Nano-8B | 7.36% | 94.4 | 101 |
| Phi-3.5-mini | 5.19% | 94.8 | 381 |

Invalid or garbled labels are treated as **missing for that model on that
post**, not as "not misinformation" — so error-heavy days are not artificially
pushed toward zero and the daily series stays continuous with no gaps. This
matters most for Qwen2.5-7B, which failed to return a parseable label on ~16%
of posts.

Daily scores are histogrammed into B = 20 bins over [0, 1] and compared against
a pooled background distribution P by KL divergence, with Laplace smoothing
(ε = 1e-10) for empty bins. Two variants are produced:

- `kl_raw` — every post contributes equally.
- `kl_weighted` — posts weighted by engagement (likes + shares + comments +
  reactions + 1).

Coverage is 5,148 days, 2009-12-03 to 2025-10-13; 434 days are flagged
`low_count_flag`. Summary: `kl_raw` mean 0.188 (median 0.113),
`kl_weighted` mean 0.487 (median 0.196); the two correlate at ρ = 0.50.

## Specifications reproduced

`main_analysis.py` runs the full set: core full-panel readouts (Model I
bid-ask spread, Model II CAPM beta, Model III Fama-French 5-factor excess
return); standardized effects; region splits (English US+UK / non-English
CN+JP / EU); placebo; Asia-lag (contemporaneous vs. previous day); subperiod
(2012-2018 vs. 2019-2025); low-count exclusions; true two-way (firm + date)
clustered variants of the core, region, climate and triple-interaction
specifications; and energy-subsample readouts with a sign-flip decomposition by
type, region and period. The main regressions run on N = 12,678,294 firm-days.

## What is not included

- **Raw social media post data** (text, IDs, engagement at post level) is not
  redistributed. Only the constructed daily index is included, so
  `build_kl_index.py` is present for transparency rather than as a runnable
  step — its output is already in
  `Data/daily_misinfo_kl_measure_5models.parquet`.
- Market data (prices, volumes, spreads, market caps) is licensed from the
  data vendor. The derived firm-day panel is provided for academic replication;
  users are responsible for their own compliance with the vendor's terms.
- The paper manuscript.

`build_kl_index.py` and `refresh_panel.py` contain absolute paths from the
original working machine (`/home/jameskrice/Downloads/Paper 2`). They are
preserved as-run for transparency; adjust the `BASE` path before reusing them.
`main_analysis.py` uses portable paths relative to the repository root and runs
as-is.

## Citation

See `CITATION.cff`.

## Licence

Code is MIT-licensed. See `LICENSE` for the terms and for the note on data.
