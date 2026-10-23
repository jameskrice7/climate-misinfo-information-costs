# Analysis audit and interpretation

The submitted paper is **Climate misinformation and quoted liquidity in energy equities**, prepared for **Energy Economics**. The analysis uses the fixed scores; it does not execute classification or require a GPU.

## Main conclusion

The positive monthly association is not stable to local market-day and sector-month controls. On 486,655 identical complete-case observations with the same contemporaneous controls and tail caps, the composite coefficient changes from **0.0041269** with security/month effects to **−0.0033435** with security, market-day and sector-month effects. These estimates are different conditional associations, not two causal estimates of the same identified effect.

The principal model uses prior-session financial controls and **485,800 security-days, 202 securities, 197 company names and nine sectors**. Its coefficient is **−0.00143194 percentage points per index point**, sector/date SE **0.00219825**, approximate 95% interval **[−0.00650111, 0.00363724]**, **p=0.53305**. Date-score HAC and the enumerated sector score-sign sensitivity do not establish a positive coefficient. Insignificance is not evidence of exactly zero effect.

## Material issues addressed

1. **Market mapping.** The stored Region field groups 62 Indonesian, eight Brazilian, five Hong Kong, one Malaysian and one Dutch listing with the US; 12 Taiwanese listings are grouped with Japan. The new analysis uses a checked exchange-suffix market mapping. Derived regional factors and macro controls are not used in the submitted models.
2. **Financial measurement.** Every nonmissing `OrderFlow` equals `VWAP − MidPrice`; every nonmissing `PriceImpact` equals `100 × abs(VWAP − MidPrice)/MidPrice`. These do not measure signed order imbalance or per-dollar price impact. The unsupported joint mechanism test and its interpretation are removed. The gap appears only as an explicitly named supplementary price-dispersion outcome.
3. **Temporal support.** Scores end on 13 October 2025, whereas the financial panel continues to December. Financial records outside the score window are excluded. Within-window unmatched-post dates can be zero, with a matched-post-only sensitivity.
4. **Timing.** Exact calendar-day joins and previous-observed-active-session lags are distinguished. The session grid is constructed before missing-outcome filtering, including Monday/weekend transitions. Long suspensions and source dates outside the score window are excluded from the exposure lag/lead.
5. **Assignment and inference.** Scores vary by sector/day, not independently by security/day. Sector/date clustering, date-score HAC, sector score-sign sensitivity, residual-variation shares and leave-out analyses address that fact. Nine sector clusters remain a limitation.
6. **Sample restrictions.** Complete cases depend only on variables required by the specified model, with explicit quote/trading/support filters. Unrelated legacy KL-index completeness no longer determines the submitted sample. Nested FE models use exactly the same observations and caps.
7. **Controls and scale.** The main model uses prior-session volume, capitalization and price range. Current activity controls, no financial controls, uncapped outcomes and log spread are shown as sensitivities. Effects and confidence intervals are expressed in basis points for an observed content standard deviation.
8. **Subperiod claims.** A post-2019 slope interaction tests a difference directly; comparing two significance thresholds is not used as evidence of a change.
9. **Scientific framing.** There is no causal information-cost claim, observed-investor-exposure claim, identified adverse-selection claim or assertion of externally validated classifier accuracy.

## Relevance-threshold inconsistency

The supplied high-relevance calculation has a different denominator and content subset from the composite average. A high-relevance conditional mean is multiplied by the qualifying-post share to obtain its contribution to the all-post mean. A sign reversal is therefore possible without an algebraic contradiction; zero-filling empty subsets introduces an additional extensive-margin change. This explains why the two regressors are not interchangeable, but **does not establish the empirical cause of the supplied reversal**.

The repository does not distribute a post-ID/date crosswalk. Post IDs are internal integers, not timestamps. Therefore it is not possible to independently reaggregate thresholded daily measures here. `analysis/threshold_aggregates.py` supplies the correct conditional means and all-post contributions at four thresholds if an authorized crosswalk is supplied. It explicitly fails for missing inputs. The submitted paper does not use an unregenerated placebo as support for specificity.

## Remaining evidence gaps

- The 2,000-judgment inspection informed rubric development; it is not independent held-out validation. A blank stratified annotation sheet and separate sampling key are supplied. No human annotations or accuracy metrics were invented.
- Raw post text, context, audience geography and local-close posting timestamps are unavailable in the distributed inputs. Transaction-level order direction and depth are also unavailable.
- Daily sector-specific confounding is unresolved. Sector/day effects would absorb the index. No natural experiment or instrument is manufactured.
- The supplied security universe is not demonstrated to be random or free of survivorship selection.
- Multiway covariance is not guaranteed positive semidefinite. Warnings are retained. One post-volume-control SE is unavailable in the attention-adjusted model; all principal-model coefficients and SEs are finite. The reported exposure coefficient in that supplementary model remains finite. JSON uses `null` for undefined uncertainty values.

## Verification

- 37 specifications and 160 coefficient rows are saved under `results/publication/`.
- Six substantive checks cover market assignment, quote/gap identities, support and unique keys, session lags, sector assignment and independent Frisch–Waugh–Lovell numerical agreement.
- All manuscript tables and data figures are generated from the saved model results.
- Anonymous PDFs are checked for identifying text, unresolved references, nonfinite printed results and prohibited draft/hardware wording, then rendered for visual inspection.

Energy Economics is an ambitious submission target because the paper concerns information conditions in energy-equity trading. The stronger analysis changes the conclusion and does not guarantee external review. Independent classification validation and credible causal variation would still materially strengthen the project.
