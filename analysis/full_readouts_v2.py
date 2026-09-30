"""Full PanelOLS readout tables for the firm-day exposure paper (main-12).

Re-estimates the three core models on the climate-transition (energy) panel
with the firm-day exposure IV, and writes three full coefficient readout
tables in the style of main-11's Tables (pin_results / capm_results /
ff_results): every control coefficient, SE and p-value, plus the fit block.

Each table reports two IV variants side by side, mirroring main-11's
raw/weighted layout:
    block 1: fd_mean_exposure        (Exp^mean)
    block 2: log_fd_sum_exposure     (log(1+Exp^sum))
Standard errors are two-way clustered (RIC + Date), the paper's stated
inference standard; firm-clustered IV rows are reported in the notes JSON.

Also estimates the price-impact illiquidity check that completes H1's joint
test: PriceImpact on the same Model I control set, contemporaneous and at a
one-day lag of the exposure IV.

Outputs:
  results/tables/tab_v2_full_modelI.tex
  results/tables/tab_v2_full_modelII.tex
  results/tables/tab_v2_full_modelIII.tex
  results/tables/tab_v2_priceimpact.tex
  results/full_readouts_v2.json
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyfixest as pf

# Replication-package layout (paths were absolute on the author's machine)
REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "pipeline"          # work/firmday_misinfo.parquet
REPL = REPO                       # data/PAPER_2_PANEL_energy.parquet
OUT = REPO / "results"
TBL = OUT / "tables"
t0 = time.time()

# ---------------- load + merge (identical to analysis_energy_v2.py) --------
print("loading panel ...", flush=True)
panel = pd.read_parquet(REPL / "data" / "PAPER_2_PANEL_energy.parquet")
panel.rename(columns={"Company Market Cap": "MktCap",
                      "Dividend yield": "DivYield"}, inplace=True)
panel["Date"] = pd.to_datetime(panel["Date"]).dt.date
fd = pd.read_parquet(ROOT / "work" / "firmday_misinfo.parquet")
fd["Date"] = pd.to_datetime(fd["Date"]).dt.date
panel = panel.merge(fd, on=["RIC", "Date"], how="left")
for c in ["fd_n_posts", "fd_mean_relevance", "fd_mean_misinformation",
          "fd_mean_exposure", "fd_max_exposure", "fd_sum_exposure",
          "fd_share_misinfo"]:
    panel[c] = panel[c].fillna(0.0)

num_cols = panel.select_dtypes(include="number").columns
panel[num_cols] = panel[num_cols].replace([np.inf, -np.inf], np.nan)
panel["log_volume"] = np.log1p(panel["Volume"].clip(lower=0))
panel["log_mktcap"] = np.log(panel["MktCap"].clip(lower=1))
panel["log_turnover"] = np.log1p(panel["Turnover"].clip(lower=0))
panel["abs_orderflow"] = panel["OrderFlow"].abs()
panel["YearMonth"] = pd.to_datetime(panel["Date"]).dt.to_period("M").astype(str)
panel["log_fd_sum_exposure"] = np.log1p(panel["fd_sum_exposure"].clip(lower=0))

IV_VARS = ["fd_mean_exposure", "log_fd_sum_exposure", "fd_mean_misinformation",
           "fd_mean_relevance"]


def prep(df, dep, kind, extra=()):
    d = df.copy()
    cols_needed = {dep, "RIC", "YearMonth", "Date", "Region", "TRBC Industry Name"}
    if kind == "pin":
        ctrls = ["log_volume", "log_mktcap", "IntradayVolatility",
                 "abs_orderflow", "log_turnover", "cpi_inflation",
                 "gdp_growth", "unemployment"]
    elif kind == "capm":
        ctrls = ["log_volume", "log_mktcap", "SpreadPercent", "DivYield",
                 "IntradayVolatility", "cpi_inflation", "gdp_growth",
                 "unemployment"]
    else:
        ctrls = ["FF_MktRF", "FF_SMB", "FF_HML", "FF_RMW", "FF_CMA",
                 "log_volume", "log_mktcap", "SpreadPercent", "DivYield",
                 "IntradayVolatility", "cpi_inflation", "gdp_growth",
                 "unemployment"]
    cols_needed |= set(ctrls) | set(IV_VARS) | set(extra)
    if "kl_weighted" in d.columns:
        cols_needed.add("kl_weighted"); cols_needed.add("kl_raw")
    d = d[[c for c in cols_needed if c in d.columns]].dropna()
    skip = set(IV_VARS)
    for c in d.select_dtypes(include=[np.number]).columns:
        if c in skip:
            continue
        lo, hi = d[c].quantile([0.01, 0.99])
        d[c] = d[c].clip(lo, hi)
    return d


F_PIN  = "SpreadPercent ~ {iv} + log_volume + log_mktcap + IntradayVolatility + abs_orderflow + log_turnover + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"
F_CAPM = "CAPM_Beta     ~ {iv} + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"
F_FF   = "ExcessReturn  ~ {iv} + FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"


def wald_F(m):
    """Joint Wald F for all slope coefficients under the fitted vcov."""
    b = m.coef().values
    V = m._vcov
    k = len(b)
    try:
        stat = float(b @ np.linalg.solve(V, b)) / k
    except np.linalg.LinAlgError:
        stat = np.nan
    return stat


def full_fit(formula, data, vcov):
    m = pf.feols(formula, data=data, vcov=vcov)
    t = m.tidy()
    out = {
        "terms": {ix: {"coef": float(r["Estimate"]),
                       "se": float(r["Std. Error"]),
                       "p": float(r["Pr(>|t|)"])} for ix, r in t.iterrows()},
        "N": int(m._N), "r2": float(m._r2),
        "r2_within": float(m._r2_within),
        "adj_r2_within": float(m._adj_r2_within),
        "F": wald_F(m),
    }
    return out


# ---------------- run --------------------------------------------------------
specs = {
    "I":   ("pin",  F_PIN,  "SpreadPercent"),
    "II":  ("capm", F_CAPM, "CAPM_Beta"),
    "III": ("ff",   F_FF,   "ExcessReturn"),
}
results = {}
for tag, (kind, F, dep) in specs.items():
    d = prep(panel, dep, kind)
    print(f"Model {tag}: N={len(d):,}", flush=True)
    for iv in ("fd_mean_exposure", "log_fd_sum_exposure"):
        results[f"{tag}_{iv}_twoway"] = full_fit(F.format(iv=iv), d,
                                                 {"CRV1": "RIC+Date"})
        results[f"{tag}_{iv}_firm"] = full_fit(F.format(iv=iv), d,
                                               {"CRV1": "RIC"})

# ---------------- price-impact check (joint test of H1) ----------------------
F_PI = ("PriceImpact ~ {iv} + log_volume + log_mktcap + IntradayVolatility"
        " + abs_orderflow + log_turnover + cpi_inflation + gdp_growth"
        " + unemployment | RIC + YearMonth")
dpi = prep(panel, "PriceImpact", "pin")
print(f"Price impact: N={len(dpi):,}", flush=True)
for iv in ("fd_mean_exposure", "log_fd_sum_exposure"):
    results[f"PI_{iv}_twoway"] = full_fit(F_PI.format(iv=iv), dpi,
                                          {"CRV1": "RIC+Date"})
    results[f"PI_{iv}_firm"] = full_fit(F_PI.format(iv=iv), dpi,
                                        {"CRV1": "RIC"})

# lag-1 exposure on the restricted sample with both exposures observed,
# mirroring the lag analysis for the spread (analysis_energy_v2.py step 5)
lag = panel[["RIC", "Date", "fd_mean_exposure"]].copy()
lag["Date_dt"] = pd.to_datetime(lag["Date"]) + pd.Timedelta(days=1)
lag = lag.rename(columns={"fd_mean_exposure": "fd_mean_exposure_lag1"})
panel["Date_dt"] = pd.to_datetime(panel["Date"])
panel_l = panel.merge(lag[["RIC", "Date_dt", "fd_mean_exposure_lag1"]],
                      on=["RIC", "Date_dt"], how="left")
for dep, key in (("PriceImpact", "PI"), ("SpreadPercent", "I")):
    d = prep(panel_l, dep, "pin", extra=("fd_mean_exposure_lag1",))
    d = d.dropna(subset=["fd_mean_exposure_lag1"])
    F_dep = F_PI if dep == "PriceImpact" else F_PIN
    results[f"{key}_lag_contemp_twoway"] = full_fit(
        F_dep.format(iv="fd_mean_exposure"), d, {"CRV1": "RIC+Date"})
    results[f"{key}_lag_lag1_twoway"] = full_fit(
        F_dep.format(iv="fd_mean_exposure_lag1"), d, {"CRV1": "RIC+Date"})
    a = results[f"{key}_lag_contemp_twoway"]["terms"]["fd_mean_exposure"]
    b = results[f"{key}_lag_lag1_twoway"]["terms"]["fd_mean_exposure_lag1"]
    print(f"  {dep}: contemp={a['coef']:+.4f}(p={a['p']:.3f}) "
          f"lag1={b['coef']:+.4f}(p={b['p']:.3f}) "
          f"N={results[f'{key}_lag_contemp_twoway']['N']:,}", flush=True)

with open(OUT / "full_readouts_v2.json", "w") as f:
    json.dump(results, f, indent=2)

# ---------------- render -----------------------------------------------------
LABELS = {
    "FF_MktRF": r"FF\_MktRF", "FF_SMB": r"FF\_SMB", "FF_HML": r"FF\_HML",
    "FF_RMW": r"FF\_RMW", "FF_CMA": r"FF\_CMA",
    "log_volume": "Log Volume", "log_mktcap": "Log Market Cap",
    "IntradayVolatility": "Intraday Volatility",
    "abs_orderflow": r"$|$Order Flow$|$", "log_turnover": "Log Turnover",
    "SpreadPercent": "Spread Percent", "DivYield": "Dividend Yield",
    "cpi_inflation": "CPI Inflation", "gdp_growth": "GDP Growth",
    "unemployment": "Unemployment",
}


def stars(p):
    return "^{***}" if p < 0.01 else "^{**}" if p < 0.05 else "^{*}" if p < 0.10 else ""


def cell(c, p):
    s = stars(p)
    return f"${c:+.4f}{s}$" if s else f"${c:+.4f}$"


def fmt_p(p):
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def render(tag, caption, label, dep_note, extra_rows=(), extra_note="", fname=None):
    a = results[f"{tag}_fd_mean_exposure_twoway"]
    b = results[f"{tag}_log_fd_sum_exposure_twoway"]
    term_order = [k for k in a["terms"] if k != "fd_mean_exposure"]
    rows = []
    ta, tb = a["terms"]["fd_mean_exposure"], b["terms"]["log_fd_sum_exposure"]
    rows.append(
        f"Exposure term & {cell(ta['coef'], ta['p'])} & {ta['se']:.4f} & {fmt_p(ta['p'])}"
        f" & {cell(tb['coef'], tb['p'])} & {tb['se']:.4f} & {fmt_p(tb['p'])} \\\\")
    rows.extend(extra_rows)
    for k in term_order:
        ra = a["terms"][k]
        rb = b["terms"].get(k, ra)
        lab = LABELS.get(k, k)
        rows.append(
            f"{lab} & {cell(ra['coef'], ra['p'])} & {ra['se']:.4f} & {fmt_p(ra['p'])}"
            f" & {cell(rb['coef'], rb['p'])} & {rb['se']:.4f} & {fmt_p(rb['p'])} \\\\")
    body = "\n".join(rows)
    tex = rf"""\begin{{table}}[htbp]
\centering
\caption{{{caption}}}
\label{{{label}}}
\begin{{threeparttable}}
\small
\setlength{{\tabcolsep}}{{4pt}}
\begin{{tabular}}{{l r r r r r r}}
\toprule
 & \multicolumn{{3}}{{c}}{{$\mathrm{{Exp}}^{{\text{{mean}}}}$}} & \multicolumn{{3}}{{c}}{{$\log(1+\mathrm{{Exp}}^{{\text{{sum}}}})$}} \\
\cmidrule(lr){{2-4}}\cmidrule(lr){{5-7}}
Term & Coef. & SE & $p$ & Coef. & SE & $p$ \\
\midrule
{body}
\midrule
Observations & & & {a['N']:,} & & & {b['N']:,} \\
$R^2$ & & & {a['r2']:.3f} & & & {b['r2']:.3f} \\
Within $R^2$ & & & {a['r2_within']:.3f} & & & {b['r2_within']:.3f} \\
Adj.\ Within $R^2$ & & & {a['adj_r2_within']:.3f} & & & {b['adj_r2_within']:.3f} \\
Wald $F$ (joint) & & & {a['F']:,.2f} & & & {b['F']:,.2f} \\
Firm FE & & & Yes & & & Yes \\
Year-Month FE & & & Yes & & & Yes \\
SE clustering & & & Firm $+$ Date & & & Firm $+$ Date \\
\bottomrule
\end{{tabular}}
\begin{{tablenotes}}
\small
\item \textit{{Notes:}} {dep_note} The two column blocks replace the exposure
term with the firm-day mean exposure $\mathrm{{Exp}}^{{\text{{mean}}}}_{{i,t}}$ and its
concave volume variant $\log(1+\mathrm{{Exp}}^{{\text{{sum}}}}_{{i,t}})$; control
coefficients are nearly identical across the two blocks, as expected by
Frisch--Waugh--Lovell when two variants of a sparse firm-day regressor have
negligible partial correlation with the controls. Standard errors are CRV1
two-way clustered by firm (RIC) and calendar date. Continuous controls are
winsorized at the 1st and 99th percentiles; the exposure regressors are not
winsorized. $^{{*}}p<0.10$, $^{{**}}p<0.05$, $^{{***}}p<0.01$.
{extra_note}\end{{tablenotes}}
\end{{threeparttable}}
\end{{table}}
"""
    path = TBL / (fname or f"tab_v2_full_model{tag}.tex")
    path.write_text(tex)
    print(f"wrote {path}", flush=True)


render("I",
       "Climate-Transition Panel, PanelOLS Full Readout: Model I (Percent Quoted Spread)",
       "tab:v2_full_modelI",
       "Dependent variable: percent quoted bid--ask spread, Equation~\\ref{eq:pin_reg}, "
       "204-firm climate-transition panel.")
render("II",
       "Climate-Transition Panel, PanelOLS Full Readout: Model II (CAPM Beta)",
       "tab:v2_full_modelII",
       "Dependent variable: 252-day rolling CAPM beta, Equation~\\ref{eq:beta_misinfo}, "
       "204-firm climate-transition panel.")
render("III",
       "Climate-Transition Panel, PanelOLS Full Readout: Model III (Fama--French Excess Return)",
       "tab:v2_full_modelIII",
       "Dependent variable: daily Fama--French five-factor excess return, "
       "Equation~\\ref{eq:ff5_aug}, 204-firm climate-transition panel.")

tl = results["PI_lag_lag1_twoway"]["terms"]["fd_mean_exposure_lag1"]
lag_row = (f"Exposure term (lag 1)\\tnote{{a}} & {cell(tl['coef'], tl['p'])} & "
           f"{tl['se']:.4f} & {fmt_p(tl['p'])} & & & \\\\")
render("PI",
       "Climate-Transition Panel, PanelOLS Full Readout: Price Impact (Joint Test of H1)",
       "tab:v2_priceimpact",
       "Dependent variable: per-dollar price impact, estimated with the Model~I "
       "control set and fixed effects (Equation~\\ref{eq:pin_reg} with "
       "PriceImpact as the outcome), 204-firm climate-transition panel.",
       extra_rows=[lag_row],
       extra_note=("\\item[a] The lag-1 row replaces the contemporaneous exposure with "
                   "its one-day lag on the restricted sample of "
                   f"{results['PI_lag_lag1_twoway']['N']:,} firm-days for which both "
                   "exposures are observed, mirroring the lag specification of "
                   "Table~\\ref{tab:v2_lag}.\n"),
       fname="tab_v2_priceimpact.tex")

print(f"done in {(time.time()-t0)/60:.1f} min", flush=True)
