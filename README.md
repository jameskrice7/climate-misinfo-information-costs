# The Information Costs of Climate Misinformation

Evidence from Global Financial Data

James Rice, University of Essex. Prepared for Energy Economics, 23 October 2026.

The paper connects politically produced climate misinformation to quoted liquidity in energy equities. Positive spread associations are observed under monthly and local market-day controls; the association changes sign and is imprecise after sector-month conditions are absorbed. These conditional findings are reported together. The attached manuscript's literature review, theoretical structure, APA6 formatting and integrated descriptive appendix are preserved, with targeted empirical corrections using the completed saved estimates.

## Paper and submission

- [Identified paper PDF](paper/Rice_2026_Information_Costs_of_Climate_Misinformation.pdf)
- [Complete Energy Economics submission ZIP](paper/submission/Energy_Economics_Submission.zip)
- [Submission files and instructions](paper/submission/README.md)
- [Analysis audit and remaining evidence gaps](ANALYSIS_AUDIT.md)
- [Machine-readable results](results/publication/analysis_results.json)
- [Coefficient CSV](results/publication/coefficients.csv)
- [Input and code hashes](results/publication/provenance.json)

## Reproduce the submitted analysis

Use Python 3.12. From the repository root:

```sh
python -m pip install -r requirements-publication.txt
python analysis/run_publication.py --compile
```

The command audits the inputs, fits all 37 specifications, creates a blank human-annotation sample, generates financial robustness assets, applies the targeted manuscript revision and compiles PDFs. It does not execute classification. Omit `--compile` to regenerate analysis and assets without LaTeX. PDF compilation requires `pdflatex` and `biber` for the original APA6 bibliography. Financial-model runtime on the Windows preparation machine was approximately 18 minutes.

To revise or compile the manuscript using the already completed analysis, without loading financial data or fitting any model:

```sh
python analysis/prepare_manuscript_revision.py
python analysis/run_publication.py --compile-only
python paper/submission/package_submission.py
```

The unchanged attachment is retained under `paper/source/`. The editorial script preserves the literature review exactly, restores the original layout and reports the before/after word counts and unchanged saved-results hash in `paper/submission/editorial_revision_checks.json`. Source-supplied financial assembly tables, corpus descriptions and owner-network figures are retained as documented inputs; their presence does not imply they were regenerated from access-controlled platform records.

The analysis stack is pinned in `requirements.txt`; publication QA requirements are in `requirements-publication.txt`. `analysis/qa_submission.py` uses Poppler to check PDF text and render final pages. Editable highlights are created by `paper/submission/create_highlights.py` using python-docx; their content is also available as plain text.

## Inputs

- `data/PAPER_2_PANEL_energy.parquet`: 726,890 financial rows for 204 securities and 198 company names, January 2012 to December 2025.
- `pipeline/work/firmday_misinfo.parquet`: 714,227 saved security-day content records, 3 January 2012 to 13 October 2025.
- `pipeline/work/firms.parquet` and `industry_profile.parquet`: security and sector profiles.
- `pipeline/out/post_industry/*.parquet`: fixed classification outputs; 1,959,707 attempted judgments, 398 invalid outputs excluded. Valid classifications cover 217,954 distinct posts.
- `pipeline/work/post_industry_pairs.parquet`: internal post/sector keys. Internal post IDs do not encode timestamps.

The product score is sector relevance multiplied by climate-or-energy misinformation and divided by 100. Its daily average is assigned by sector/date, so securities in the same sector do not provide independent content measurements. It measures available classified content rather than observed investor exposure. The main sample excludes dates outside the content window and uses an exchange-suffix listing-market crosswalk.

## Measurement and inference

The outcome is `SpreadPercent = 200*(ASK-BID)/(ASK+BID)`. The input field `OrderFlow` is exactly `VWAP-MidPrice`, and `PriceImpact` is exactly `100*abs(VWAP-MidPrice)/MidPrice`. Neither is treated as transaction order flow or per-dollar price impact in the submitted analysis.

The principal model uses prior-session volume, capitalization and price range, security effects, market-by-date effects and sector-by-month effects. Sector/date uncertainty is accompanied by security/date clustering, date-score HAC and an enumerated sector score-sign sensitivity. Nine sector clusters remain a limitation. Numerical warnings are retained; unavailable standard errors are JSON null values.

## Classification and access-controlled inputs

Persisted scores were produced by Qwen3.6-35B-A3B-FP8 using `pipeline/prompts_industry.py`. The first-2,000-judgment inspection informed rubric development; it is not independent held-out validation. Statistical replication uses persisted scores and never invokes a model server.

Raw Facebook text and the post-date crosswalk are not distributed. An authorized crosswalk with `post_id` and `post_date` permits `analysis/threshold_aggregates.py` to calculate subset conditional means and common-denominator contributions without reclassification. Without the crosswalk it fails explicitly; it does not fabricate dates or reuse a saved placebo as fresh evidence. Independent human validation requires original post context. The blank annotation sheet contains no human labels; its separate sampling key contains model-based strata.

The monthly-model scripts `analysis/analysis_energy_v2.py`, `full_readouts_v2.py` and `build_tables_figures.py` remain for computational reference. They are not the submitted paper's entry point. Some require access-controlled post data; their saved tables should not be mistaken for freshly regenerated publication checks.

## Data rights and citation

The financial panel originates from licensed Refinitiv data and other documented sources. Raw Meta Content Library text and identifying source metadata are not redistributed. See `LICENSE` for the code/data distinction and the supplement for the scope of reproducibility. Cite using `CITATION.cff`.
