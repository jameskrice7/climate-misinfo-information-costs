# The Information Costs of Climate Misinformation — Replication Package

**Paper:** James Rice, *The Information Costs of Climate Misinformation: Evidence
from Global Financial Data*, Department of Government, University of Essex
(September 2026). The paper is in [`paper/`](paper/).

The paper asks whether firm-day exposure to sector-specific climate
misinformation moves the trading costs of 204 listed climate-transition firms
(2012–2025, 726,890 firm-days). Exposure is measured by a single open-weight
LLM, **Qwen3.6-35B-A3B-FP8**, which scored each of 217,954 English-language
Facebook climate posts against each of the nine TRBC energy sub-industries in
the panel (1,959,707 post × sub-industry judgments).

This version replaces the earlier five-model-ensemble package, which used a
market-wide daily KL-divergence index on a 19.2M-row global panel. That
package remains in this repository's git history.

---

## Contents

```
paper/
  Rice_2026_Information_Costs_of_Climate_Misinformation.pdf   the paper
data/
  PAPER_2_PANEL_energy.parquet    firm-day panel: 204 firms, 726,890 rows x 59 columns
pipeline/                         the classification pipeline (run from this folder)
  prompts_industry.py             the rubric: system prompt + JSON schema
  classify_industry.py            async client: one judgment per (post, sub-industry)
  serve_vllm.sh, launch_vllm.py   the vLLM server (Qwen3.6-35B-A3B-FP8, temperature 0)
  launch_classifier.py, watchdog.py, monitor.py   daemons for the ~10-day run
  retry_errors.py                 re-asks pairs whose JSON failed to parse
  normalize_energy.py             builds work/ from the post x panel file
  expand.py                       (post, sub-industry) scores -> (firm, post) rows
  aggregate_firmday.py            (firm, post) rows -> the firm-day exposure index
  CLASSIFICATION_NOTES.md         design notes written during the run
  work/
    firmday_misinfo.parquet       THE FIRM-DAY EXPOSURE INDEX (714,227 firm-days)
    post_industry_pairs.parquet   the 1,959,707 (post, sub-industry) pairs judged
    firms.parquet                 the 204 firms: RIC, name, sub-industry, country, region
    industry_profile.parquet      the nine sub-industry profiles shown to the model
  out/post_industry/              POST-LEVEL CLASSIFICATIONS, 980 shards
  logs/                           classifier, expansion and watchdog logs of the run
analysis/
  analysis_energy_v2.py           Models I-III and every robustness block
  full_readouts_v2.py             full coefficient readouts and the price-impact test
  build_tables_figures.py         LaTeX tables and figures from the results JSON
results/                          the outputs reported in the paper
  tables/*.tex, figures/*.png, full_readouts_v2.json, analysis_v2.log
```

## Reproducing the analysis

Requirements: Python 3.12 and the pinned packages in `requirements.txt`. The
two-way clustered standard errors depend on `pyfixest==0.40.1`.

```bash
pip install -r requirements.txt
python analysis/analysis_energy_v2.py     # -> results/econ_results_v2.json   (~2 min)
python analysis/full_readouts_v2.py       # -> results/full_readouts_v2.json + full readout tables
python analysis/build_tables_figures.py   # -> results/tables/*.tex, results/figures/*.png
```

Run them from anywhere; paths resolve relative to the repository. Each script
merges `pipeline/work/firmday_misinfo.parquet` onto
`data/PAPER_2_PANEL_energy.parquet` by `(RIC, Date)`. Firm-days with no
matched post get zero exposure.

| Paper | File in `results/` | Script |
|---|---|---|
| Table 1, headline coefficients | `tables/tab_v2_core.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Table 2, Model I full readout | `tables/tab_v2_full_modelI.tex` | `full_readouts_v2.py` |
| Table 3, price impact (joint test of H1) | `tables/tab_v2_priceimpact.tex` | `full_readouts_v2.py` |
| Table 4, one-day lag | `tables/tab_v2_lag.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Table 5, placebo (sector-irrelevant posts) | `tables/tab_v2_placebo.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` (see below) |
| Table 6, subperiods | `tables/tab_v2_subperiod.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Tables 7–8, Models II–III full readouts | `tables/tab_v2_full_modelII.tex`, `tab_v2_full_modelIII.tex` | `full_readouts_v2.py` |
| Table 25, exposure-index descriptives | `tables/tab_v2_descriptive.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Table 26 / Figure 8, heterogeneity | `tables/tab_v2_signflip.tex`, `figures/fig_v2_signflip_coef.png` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Table 27, triple interaction | `tables/tab_v2_triple.tex` | `analysis_energy_v2.py` → `build_tables_figures.py` |
| Figure 7, exposure distribution | `figures/fig_v2_iv_distribution.png` | `build_tables_figures.py` |
| Supplementary: new index vs. old KL index | `tables/tab_v2_compare_kl.tex`, `figures/fig_v2_new_vs_old.png` | `analysis_energy_v2.py` → `build_tables_figures.py` |

`results/econ_results_v2.json` is not shipped; the first script regenerates it.
The descriptive appendix tables on the financial panel (Tables 9–18) and on
the post corpus (Tables 19–24, Figures 3–5) come from the author's earlier
data-assembly code and the Meta Content Library records, and are not
regenerated here. Their figures are included in `results/` for reference.

**The placebo (Table 5) needs data that cannot be redistributed.** It
re-aggregates post-level scores by calendar date, which requires the post
creation dates in `pipeline/work/posts.parquet`. That file holds Meta Content
Library post text. Without it, `analysis_energy_v2.py` skips the placebo
block, says so, and leaves the shipped `tab_v2_placebo.tex` in place. With MCL
access, rebuild `work/posts.parquet` with `pipeline/normalize_energy.py`,
then run `pipeline/expand.py` before the analysis.

## The exposure index

`pipeline/work/firmday_misinfo.parquet` has one row per (firm, trading day)
with at least one paired post:

| Column | Meaning |
|---|---|
| `RIC`, `Date` | firm and calendar date |
| `fd_n_posts` | climate posts paired with the firm that day |
| `fd_mean_exposure` | **Exp^mean**, the headline regressor: mean of per-post exposure |
| `fd_sum_exposure` | Exp^sum; the paper uses log(1 + Exp^sum) |
| `fd_mean_misinformation` | M^mean, the mean misinformation sub-score |
| `fd_mean_relevance` | R^mean, the mean sector-relevance sub-score |
| `fd_max_exposure` | the day's highest per-post exposure |
| `fd_share_misinfo` | share of posts with misinformation ≥ 25 |

Per-post exposure is `relevance × misinformation / 100` on a 0–100 scale. It
is non-zero only for a post that is both relevant to the firm's sub-industry
and contains climate-or-energy misinformation. Firms in the same sub-industry
share a value on a given day; firms in different sub-industries do not.

## The classifier

- **Model:** `Qwen/Qwen3.6-35B-A3B-FP8`, Hugging Face revision
  `95a723d08a9490559dae23d0cff1d9466213d989`: 35B-parameter mixture of
  experts with about 3B active parameters.
- **Serving:** vLLM 0.21 on one NVIDIA GB10 (DGX Spark), FP8 weights with the
  Triton MoE backend (`pipeline/serve_vllm.sh`).
- **Decoding:** temperature 0 with xgrammar-enforced JSON, so every judgment
  is deterministic and schema-valid.
- **Rubric:** `pipeline/prompts_industry.py`. Each judgment sees the
  sub-industry profile (name, countries and regions of its firms, example
  firms) and one post (text, date, content type, link caption and
  description). It returns relevance (0–100), misinformation (0–100),
  `misinfo_type` and a one-sentence rationale.
- **Scope:** misinformation is limited to climate and energy claims.
  Non-climate falsehoods score 0, and satire or parody of denial scores 0–15.
  These rules were added after a held-out spot-check of the first 2,000
  judgments (paper, Appendix E).
- **Unit:** one call per (post, sub-industry) pair, 1,959,707 calls over about
  ten days. Every (firm, post) row inherits its sub-industry's score, which
  gives 43.5M firm × post rows. 398 judgments (0.02%) still failed to parse
  after five retries and are left out of every average.

The post-level classifications in `pipeline/out/post_industry/` have columns
`rid_i, post_id, industry, relevance, misinformation, misinfo_type, exposure,
rationale`. The rationale is the model's own one-sentence explanation. The
398 failed judgments stay in the shards with `relevance < 0`; `expand.py`
drops them (`WHERE relevance >= 0`), so filter them out the same way when
using the shards directly.

Re-running the classifier needs the post text (`work/posts.parquet`, not
distributed), a GPU that holds the 37.5 GB of FP8 weights plus a KV cache, and vLLM
0.21 in its own environment (`.venv_vllm`, as `serve_vllm.sh` expects). The
order is: `normalize_energy.py`, then `launch_vllm.py`, `launch_classifier.py`
and `watchdog.py`, then `retry_errors.py`, `expand.py` and
`aggregate_firmday.py`. Run all of them from `pipeline/`.

## Data and privacy

- **Not redistributed:** the raw Facebook post text and post metadata (page
  or profile names and IDs, engagement counts). They fall under the Meta
  Content Library terms of use. Neither are the model weights, which are
  available from Hugging Face.
- **Included:** the model's post-level scores keyed by MCL post ID, the
  firm-day exposure index, and the firm-day financial panel.
- **The financial panel** is derived from licensed market data (Refinitiv),
  FRED, the World Bank and the Kenneth French Data Library. It is provided for
  academic replication only; see `LICENSE`.

## Citation

See `CITATION.cff`.
