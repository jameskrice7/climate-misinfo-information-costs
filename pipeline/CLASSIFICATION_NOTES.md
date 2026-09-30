# Firm-aware climate-post classification (energy subsample)

Local classification of the energy subsample using **Qwen3.6-35B-A3B-FP8**
served by vLLM on the DGX Spark (GB10). Three daemons survive across shell
sessions: `vllm.pid`, `classifier.pid`, `watchdog.pid` (logs under `logs/`).

## The metric
Each LLM judgment produces, on continuous 0–100 scales:

- **relevance** — how materially the climate post relates to the matched
  energy sub-sector, given its operations, fuel type, geographies, value chain.
- **misinformation** — degree the post contains false / misleading / pseudo-
  scientific *climate-or-energy* claims (politically-charged but non-climate
  falsehoods are explicitly out of scope and score 0).
- **misinfo_type** — categorical tag (none / denial / pseudoscience /
  misleading_framing / greenwashing / conspiracy / other).
- **rationale** — one short sentence.

Persisted composite (deterministic, computed in the worker):

- **exposure = relevance × misinformation / 100** — single continuous 0–100
  index. High only when a post is *both* sector-relevant *and* misinformation-
  laden. Raw components are kept so any other composite can be recomputed.

## Why (post × industry) instead of (post × firm)
On GB10 + vLLM 0.21, only the TRITON FP8-MoE backend is supported (DeepGEMM
and FlashInfer-TRTLLM both reject sm_121 as unsupported), giving ~2.3 rows/s
on Qwen3.6-35B-A3B-FP8. A literal per-row run on the 43,549,365 (firm, post)
pairs would take ~220 days; the energy subsample contains only **9 TRBC
industries**, so scoring at `(post, industry)` granularity yields **1,959,707
unique LLM calls** (~10 days at the measured rate) without losing per-firm
variation across industries. Every (firm, post) row inherits the score of its
firm's industry — firms in different industries get different scores;
firms in the same industry on the same date share a score, which is the
intended approximation given the LLM is reasoning at the industry level
(operations, fuel type, geographies) rather than at the company-specific
level.

## Pipeline
1. `normalize_energy.py` → `work/{firms.parquet, posts.parquet, pairs.parquet}`
   (one pass over the 78GB file; firms + posts cardinality verified).
2. Industry tables: `work/post_industry_pairs.parquet` (1.96M unique
   `(rid_i, post_id, industry)` rows) and `work/industry_profile.parquet`
   (9 rows: `industry, n_firms, countries, regions, example_firms`).
3. `serve_vllm.sh` → vLLM OpenAI-compatible server with the FP8 MoE on the
   GB10 (`--moe-backend triton`, xgrammar-enforced JSON output).
   `launch_vllm.py` daemonizes it.
4. `classify_industry.py` → async client (concurrency 128) streams windows
   of 2,000 rids, writes atomic shard parquets under `out/post_industry/`,
   resumes by skipping any shard that already exists.
   `launch_classifier.py` daemonizes it.
5. `watchdog.py` → polls every 60s; restarts vLLM (with 10-min grace for
   startup) or the classifier if either dies.
6. `expand.py` → after the run completes, joins industry shards to
   `work/pairs.parquet` + `work/firms.parquet` and writes the 43,549,365-row
   deliverable `out/energy_scored.parquet`
   (`rid, post_id, RIC, industry, relevance, misinformation, misinfo_type,
   exposure, rationale`).
7. `monitor.py` → progress, recent rate, ETA.

## Operations
- Stop everything: `kill $(cat watchdog.pid classifier.pid vllm.pid)`
  (kill watchdog first so it doesn't restart the others).
- Resume after stop: relaunch in order — `python3 launch_vllm.py` (wait until
  `curl -s localhost:8000/v1/models` returns `qwen`), then
  `python3 launch_classifier.py`, then `python3 watchdog.py`.
- Sanity-check progress: `.venv_tools/bin/python monitor.py`.
- Spot-check quality: open any `out/post_industry/shard_*.parquet`; look at
  `relevance`, `misinformation`, and `rationale`.
