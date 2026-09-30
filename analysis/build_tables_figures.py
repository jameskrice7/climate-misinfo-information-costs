"""Generate LaTeX tables and PNG figures for the v2 (firm-day exposure IV) analysis.

Tables under results/tables/ in the same threeparttable style as the paper.
Figures under results/figures/ as PNG.
"""
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Replication-package layout (paths were absolute on the author's machine)
REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "pipeline"          # work/firmday_misinfo.parquet
OUT = REPO / "results"
TBL = OUT / "tables"
FIG = OUT / "figures"
TBL.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

r = json.load(open(OUT / "econ_results_v2.json"))


def stars(p):
    if p is None or (isinstance(p, float) and np.isnan(p)): return ""
    return "$^{***}$" if p < 0.01 else "$^{**}$" if p < 0.05 else "$^{*}$" if p < 0.10 else ""


def fmt(x, digits=4):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "--"
    return f"{x:+.{digits}f}" if isinstance(x, float) else str(x)


def fmtN(n):
    return f"{n:,}" if n is not None else "--"


# ---------- Table 1: CORE MAIN MODELS (firm vs two-way) ----------
core = r["core"]
rows = []
for tag, depname in (("I_Spread", "Spread\\%"),
                     ("II_CAPM",  "CAPM $\\beta$"),
                     ("III_FF",   "ExcessReturn")):
    for iv, ivname in (("fd_mean_exposure",       "$\\mathrm{Exp}^{\\text{mean}}$"),
                       ("log_fd_sum_exposure",    "$\\log(1+\\mathrm{Exp}^{\\text{sum}})$"),
                       ("fd_mean_misinformation", "$M^{\\text{mean}}$"),
                       ("fd_mean_relevance",      "$R^{\\text{mean}}$")):
        a = core[f"{tag}_{iv}_firm"]
        b = core[f"{tag}_{iv}_twoway"]
        rows.append([depname, ivname,
                     f"{a['coef']:+.4f}{stars(a['p'])}",
                     f"({a['se']:.4f})",
                     f"{b['coef']:+.4f}{stars(b['p'])}",
                     f"({b['se']:.4f})",
                     fmtN(a['N']),
                     f"{a['r2_within']:.3f}"])

tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Energy subsample, firm-day exposure IV: Models I--III}
\label{tab:v2_core}
\begin{threeparttable}
\begin{tabular}{l l c c c c r r}
\toprule
 & & \multicolumn{2}{c}{Firm-clustered SE} & \multicolumn{2}{c}{Two-way clustered (RIC + Date) SE} & & \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
Outcome & IV & Coef. & (SE) & Coef. & (SE) & $N$ & $R^2_{\text{within}}$ \\
\midrule""")
last_dep = None
for row in rows:
    if last_dep is not None and row[0] != last_dep:
        tex.append(r"\addlinespace")
    last_dep = row[0]
    dep = row[0] if row[0] != last_dep else ""
    # use group header only on first row of each dep
    tex.append(" & ".join(row) + r" \\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} All three models add two-way fixed effects (RIC and year-month).
Controls are (Model I) log volume, log market cap, intraday volatility, $|\text{order flow}|$,
log turnover, CPI inflation, GDP growth, unemployment; (Model II) log volume, log market cap,
quoted spread, dividend yield, intraday volatility and the macro controls; (Model III) the
Fama--French five factors plus the Model~II controls. Numeric controls are winsorized at the
1st and 99th percentiles; the misinformation IVs are not winsorized. $\mathrm{Exp}^{\text{mean}}$
is the firm-day mean of per-post climate-relevance--weighted misinformation exposure;
$\mathrm{Exp}^{\text{sum}}$ is its sum across the day's climate posts;
$M^{\text{mean}}$ is the mean of the per-post misinformation sub-score;
$R^{\text{mean}}$ is the mean per-post sector-relevance sub-score.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_core.tex").write_text("\n".join(tex))


# ---------- Table 2: SIGN-FLIP DECOMPOSITION ----------
sf = r["signflip"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Energy subsample sign-flip decomposition (two-way clustered SE)}
\label{tab:v2_signflip}
\begin{threeparttable}
\begin{tabular}{l r r r r r r}
\toprule
 & \multicolumn{2}{c}{Model I: Spread\%} & \multicolumn{2}{c}{Model II: CAPM $\beta$} & \multicolumn{2}{c}{Model III: ExcessReturn} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}
Subsample & Coef. & $N$ & Coef. & $N$ & Coef. & $N$ \\
\midrule""")
def cell(d):
    if not d or "coef" not in d: return "-- & --"
    return f"{d['coef']:+.4f}{stars(d['p'])} & {fmtN(d['N'])}"
ORDER = [("Renewable","Renewables"), ("Fossil","Fossil fuels"),
         ("US","United States"), ("UK","United Kingdom"), ("EU","European Union"),
         ("CN","China"), ("JP","Japan"),
         ("Pre2019","Pre-2019"), ("Post2019","Post-2019")]
for key, label in ORDER:
    a = sf.get(f"{key}_I_Spread", {})
    b = sf.get(f"{key}_II_CAPM",  {})
    c = sf.get(f"{key}_III_FF",   {})
    tex.append(f"{label} & {cell(a)} & {cell(b)} & {cell(c)} \\\\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} Each cell is the OLS coefficient on $\mathrm{Exp}^{\text{mean}}$ in the
specification of Table~\ref{tab:v2_core}, estimated on the indicated subsample of the energy panel.
Standard errors are clustered on RIC and Date. Cells where $N<1{,}000$ are omitted.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_signflip.tex").write_text("\n".join(tex))


# ---------- Table 3: LAG SPEC ----------
lag = r["lag"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Contemporaneous vs.\ one-day lag of firm-day misinformation exposure (two-way clustered SE)}
\label{tab:v2_lag}
\begin{threeparttable}
\begin{tabular}{l r r r r}
\toprule
 & \multicolumn{2}{c}{Contemporaneous IV} & \multicolumn{2}{c}{One-day lagged IV} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
Outcome & Coef. & (SE) & Coef. & (SE) \\
\midrule""")
for tag, depname in (("I_Spread","Spread\\%"),("II_CAPM","CAPM $\\beta$"),("III_FF","ExcessReturn")):
    a = lag[f"{tag}_contemp"]; b = lag[f"{tag}_lag1"]
    tex.append(f"{depname} & {a['coef']:+.4f}{stars(a['p'])} & ({a['se']:.4f}) & {b['coef']:+.4f}{stars(b['p'])} & ({b['se']:.4f}) \\\\")
tex.append(r"\midrule")
tex.append(f"$N$ & \\multicolumn{{4}}{{c}}{{{fmtN(lag['I_Spread_contemp']['N'])} (Model I); slightly fewer for II/III}} \\\\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} Both columns estimated on the same firm-day sample, restricting to
observations with non-missing lagged exposure. Specifications and controls as in Table~\ref{tab:v2_core}.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_lag.tex").write_text("\n".join(tex))


# ---------- Table 4: COMPARISON WITH ORIGINAL KL ----------
cmp = r["comparison_with_original"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Same-sample comparison of the new firm-day IV with the original daily KL index (two-way clustered SE)}
\label{tab:v2_compare_kl}
\begin{threeparttable}
\begin{tabular}{l c c c c c c}
\toprule
 & \multicolumn{2}{c}{Model I: Spread\%} & \multicolumn{2}{c}{Model II: CAPM $\beta$} & \multicolumn{2}{c}{Model III: ExcessReturn} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}
IV & Coef. & (SE) & Coef. & (SE) & Coef. & (SE) \\
\midrule""")
def row(iv, label):
    a = cmp.get(f"I_Spread_{iv}",{}); b = cmp.get(f"II_CAPM_{iv}",{}); c = cmp.get(f"III_FF_{iv}",{})
    def C(d): return f"{d['coef']:+.4f}{stars(d['p'])} & ({d['se']:.4f})" if d else "-- & --"
    return f"{label} & {C(a)} & {C(b)} & {C(c)} \\\\"
tex.append(row("kl_raw",          "Daily KL (raw)"))
tex.append(row("kl_weighted",     "Daily KL (engagement-weighted)"))
tex.append(row("fd_mean_exposure","Firm-day exposure $\\mathrm{Exp}^{\\text{mean}}$"))
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} All three rows are estimated on the same energy-subsample firm-day rows
(observations with non-missing values for all three IVs). Pairwise sample correlations are
$r=0.10$ between $\mathrm{Exp}^{\text{mean}}$ and engagement-weighted KL, $r=0.20$ between the
per-post mean misinformation sub-score and engagement-weighted KL. Cluster-robust SE on RIC and Date.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_compare_kl.tex").write_text("\n".join(tex))


# ---------- Table 5: SUBPERIOD ----------
sub = r["subperiod"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Subperiod splits: pre-2019 vs.\ 2019--2025 (two-way clustered SE)}
\label{tab:v2_subperiod}
\begin{threeparttable}
\begin{tabular}{l c c c c}
\toprule
 & \multicolumn{2}{c}{2012--2018} & \multicolumn{2}{c}{2019--2025} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
Outcome & Coef. (SE) & $N$ & Coef. (SE) & $N$ \\
\midrule""")
for tag, name in (("I_Spread","Spread\\%"),("II_CAPM","CAPM $\\beta$"),("III_FF","ExcessReturn")):
    a = sub.get(f"2012-2018_{tag}", {}); b = sub.get(f"2019-2025_{tag}", {})
    def C(d): return f"{d['coef']:+.4f}{stars(d['p'])} ({d['se']:.4f}) & {fmtN(d['N'])}" if d else "-- & --"
    tex.append(f"{name} & {C(a)} & {C(b)} \\\\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} The IV is $\mathrm{Exp}^{\text{mean}}$. Two-way clustered standard errors on RIC and Date.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_subperiod.tex").write_text("\n".join(tex))


# ---------- Table 6: PLACEBO ----------
plc = r["placebo"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Placebo: high-relevance vs.\ low-relevance climate posts (two-way clustered SE)}
\label{tab:v2_placebo}
\begin{threeparttable}
\begin{tabular}{l c c c}
\toprule
IV & Spread\% & CAPM $\beta$ & ExcessReturn \\
\midrule""")
def R(tag, label):
    a = plc.get(f"{tag}_I_Spread", {})
    b = plc.get(f"{tag}_II_CAPM",  {})
    c = plc.get(f"{tag}_III_FF",   {})
    def C(d): return f"{d['coef']:+.4f}{stars(d['p'])}" if d else "--"
    return f"{label} & {C(a)} & {C(b)} & {C(c)} \\\\"
tex.append(R("relevant",            "Posts with sector-relevance $\\geq 50$ (treated)"))
tex.append(R("irrelevant_placebo",  "Posts with sector-relevance $<10$ (placebo)"))
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} The IV in each row is the firm-day mean exposure computed using only those
classified posts whose per-post sector-relevance falls into the indicated band, then merged into the
energy panel and used in the Table~\ref{tab:v2_core} specification.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
if "skipped" in plc:   # no post data: keep the shipped table rather than overwrite it with dashes
    print("placebo table kept as shipped (placebo needs non-redistributed post data)")
else:
    (TBL / "tab_v2_placebo.tex").write_text("\n".join(tex))


# ---------- Table 7: TRIPLE INTERACTION ----------
trip = r["triple_spread"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Triple interaction: Fossil $\times$ English-region $\times$ Post-2019 (Model~I, Spread\%, two-way clustered SE)}
\label{tab:v2_triple}
\begin{threeparttable}
\begin{tabular}{l r r}
\toprule
Term & Coef. & SE \\
\midrule""")
names = {
    "fd_mean_exposure":         "$\\mathrm{Exp}^{\\text{mean}}$",
    "iv_x_fossil":              "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\mathbb{1}\\{\\text{Fossil}\\}$",
    "iv_x_eng":                 "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\mathbb{1}\\{\\text{English region}\\}$",
    "iv_x_post":                "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\mathbb{1}\\{\\text{Post-2019}\\}$",
    "iv_x_fossil_eng":          "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\text{Fossil}\\!\\times\\!\\text{English}$",
    "iv_x_fossil_post":         "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\text{Fossil}\\!\\times\\!\\text{Post-2019}$",
    "iv_x_eng_post":            "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\text{English}\\!\\times\\!\\text{Post-2019}$",
    "iv_x_fossil_eng_post":     "$\\mathrm{Exp}^{\\text{mean}}\\!\\times\\!\\text{Fossil}\\!\\times\\!\\text{English}\\!\\times\\!\\text{Post-2019}$",
}
for k, lbl in names.items():
    v = trip.get(k, {})
    tex.append(f"{lbl} & {v['coef']:+.4f}{stars(v['p'])} & ({v['se']:.4f}) \\\\")
tex.append(r"\midrule")
tex.append(f"$N$ & {fmtN(trip['N'])} & \\\\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} Estimation by Model~I; controls and fixed effects as in
Table~\ref{tab:v2_core}. ``English region'' is US or UK. ``Fossil'' identifies the seven fossil
TRBC sub-industries; ``Renewable'' firms are the complement within the energy panel.
$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_triple.tex").write_text("\n".join(tex))


# ---------- Table 8: Descriptive stats of IV ----------
desc = r["descriptive"]
tex = []
tex.append(r"""\begin{table}[htbp]
\centering
\caption{Descriptive statistics of the firm-day misinformation-exposure IV (energy subsample, 714,227 firm-days with $\geq 1$ climate post)}
\label{tab:v2_descriptive}
\begin{threeparttable}
\begin{tabular}{l r r r r r r}
\toprule
Variable & Mean & SD & $p_{50}$ & $p_{90}$ & $p_{99}$ & Share zero \\
\midrule""")
LABELS = {
    "fd_n_posts":              "\\# climate posts paired to the firm-day",
    "fd_mean_relevance":       "Mean per-post sector relevance $R^{\\text{mean}}$",
    "fd_mean_misinformation":  "Mean per-post climate misinformation $M^{\\text{mean}}$",
    "fd_mean_exposure":        "Firm-day mean exposure $\\mathrm{Exp}^{\\text{mean}}$",
    "fd_max_exposure":         "Firm-day max exposure $\\mathrm{Exp}^{\\text{max}}$",
    "fd_sum_exposure":         "Firm-day sum exposure $\\mathrm{Exp}^{\\text{sum}}$",
    "fd_share_misinfo":        "Share of posts with $M\\geq 25$",
    "log_fd_sum_exposure":     "$\\log(1+\\mathrm{Exp}^{\\text{sum}})$",
}
for k, label in LABELS.items():
    v = desc[k]
    tex.append(f"{label} & {v['mean']:.3f} & {v['sd']:.3f} & {v['p50']:.3f} & {v['p90']:.3f} & {v['p99']:.3f} & {v['share_zero']:.3f} \\\\")
tex.append(r"""\bottomrule
\end{tabular}
\begin{tablenotes}\small
\item \textit{Notes:} Sample is firm-days in the energy panel for which at least one English-language Facebook
climate post on the same calendar date was scored against the firm's TRBC industry. ``Share zero'' is the
fraction of firm-days for which the variable evaluates to exactly 0 (typically because no posts in the day's
classification batch were judged sector-relevant or misinformation-laden).
\end{tablenotes}
\end{threeparttable}
\end{table}""")
(TBL / "tab_v2_descriptive.tex").write_text("\n".join(tex))


# ===========================================================
# FIGURES
# ===========================================================

# Read firm-day data + panel for figures
print("loading panel for figures ...", flush=True)
panel = pd.read_parquet(REPO / "data" / "PAPER_2_PANEL_energy.parquet")
panel.rename(columns={"Company Market Cap": "MktCap"}, inplace=True)
panel["Date"] = pd.to_datetime(panel["Date"]).dt.date
fd = pd.read_parquet(ROOT / "work" / "firmday_misinfo.parquet")
fd["Date"] = pd.to_datetime(fd["Date"]).dt.date
mp = panel.merge(fd, on=["RIC", "Date"], how="left")
for c in ["fd_n_posts","fd_mean_exposure","fd_sum_exposure","fd_mean_misinformation","fd_mean_relevance"]:
    mp[c] = mp[c].fillna(0.0)


# Fig 1: time series of mean firm-day exposure (industry-averaged) overlaid with daily KL
mp["Date_dt"] = pd.to_datetime(mp["Date"])
ts = mp.groupby("Date_dt").agg(
    mean_exp=("fd_mean_exposure", "mean"),
    mean_misinfo=("fd_mean_misinformation", "mean"),
    kl=("kl_weighted", "mean"),
).reset_index()
ts["mean_exp_ma"] = ts["mean_exp"].rolling(30, min_periods=1).mean()
ts["kl_ma"] = ts["kl"].rolling(30, min_periods=1).mean()

fig, ax1 = plt.subplots(figsize=(11, 4.5))
ax1.plot(ts["Date_dt"], ts["mean_exp_ma"], color="#1f4e79", lw=1.4, label=r"Firm-day exposure (30-day MA)")
ax1.set_ylabel(r"Firm-day misinformation exposure $\mathrm{Exp}^{\text{mean}}$")
ax1.set_xlabel("Date")
ax1.grid(True, alpha=0.3)
ax2 = ax1.twinx()
ax2.plot(ts["Date_dt"], ts["kl_ma"], color="#b35806", lw=1.0, alpha=0.85, label="Engagement-weighted daily KL (30-day MA)")
ax2.set_ylabel("Engagement-weighted KL")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", framealpha=0.9, fontsize=9)
plt.title(r"Two misinformation regressors, 2012--2025 (energy panel, daily mean across firms)")
plt.tight_layout()
plt.savefig(FIG / "fig_v2_iv_timeseries.png", dpi=160)
plt.close()


# Fig 2: distribution of firm-day exposure
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
nonzero = mp[mp["fd_mean_exposure"] > 0]["fd_mean_exposure"]
axes[0].hist(nonzero, bins=80, color="#1f4e79", alpha=0.85)
axes[0].set_xlabel(r"$\mathrm{Exp}^{\text{mean}}$ (non-zero firm-days)")
axes[0].set_ylabel("Frequency")
axes[0].set_title("Firm-day mean exposure")
axes[0].grid(True, alpha=0.3)
nz_sum = mp[mp["fd_sum_exposure"] > 0]["fd_sum_exposure"]
axes[1].hist(np.log1p(nz_sum), bins=80, color="#b35806", alpha=0.85)
axes[1].set_xlabel(r"$\log(1+\mathrm{Exp}^{\text{sum}})$")
axes[1].set_ylabel("Frequency")
axes[1].set_title("Firm-day sum exposure (log scale)")
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig_v2_iv_distribution.png", dpi=160)
plt.close()


# Fig 3: per-industry mean exposure over time
fig, ax = plt.subplots(figsize=(11, 5))
industries = ["Coal", "Integrated Oil & Gas",
              "Oil & Gas Exploration and Production",
              "Renewable Energy Equipment & Services",
              "Renewable Fuels"]
colors = ["#1b1b1b", "#7a3f00", "#c75d00", "#1e7e34", "#52a673"]
for ind, col in zip(industries, colors):
    sub = mp[mp["TRBC Industry Name"] == ind].copy()
    if len(sub) == 0: continue
    sub["Date_dt"] = pd.to_datetime(sub["Date"])
    g = sub.groupby("Date_dt")["fd_mean_exposure"].mean().rolling(60, min_periods=1).mean()
    ax.plot(g.index, g.values, lw=1.2, label=ind, color=col, alpha=0.9)
ax.set_xlabel("Date")
ax.set_ylabel(r"Firm-day mean exposure (60-day MA)")
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
ax.grid(True, alpha=0.3)
plt.title("Misinformation exposure by energy sub-industry, 2012--2025")
plt.tight_layout()
plt.savefig(FIG / "fig_v2_exposure_by_industry.png", dpi=160)
plt.close()


# Fig 4: sign-flip coefficient plot
sf = r["signflip"]
labels = ["Renewables","Fossil","US","UK","EU","CN","JP","Pre-2019","Post-2019"]
keys = ["Renewable","Fossil","US","UK","EU","CN","JP","Pre2019","Post2019"]
models = [("I_Spread","Spread%"), ("II_CAPM","CAPM β"), ("III_FF","Excess Return")]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for i, (m_tag, m_lbl) in enumerate(models):
    coefs = []; ses = []
    for k in keys:
        d = sf.get(f"{k}_{m_tag}", {})
        if d and "coef" in d and not (isinstance(d.get("se"), float) and np.isnan(d.get("se", 0))):
            coefs.append(d["coef"]); ses.append(d["se"])
        else:
            coefs.append(np.nan); ses.append(np.nan)
    y = np.arange(len(labels))[::-1]
    axes[i].errorbar(coefs, y, xerr=[1.96*s if not np.isnan(s) else 0 for s in ses],
                     fmt="o", color="#1f4e79", capsize=3)
    axes[i].axvline(0, color="grey", lw=0.6, ls="--")
    axes[i].set_yticks(y); axes[i].set_yticklabels(labels)
    axes[i].set_title(m_lbl)
    axes[i].grid(True, alpha=0.3)
    axes[i].set_xlabel(r"Coef. on $\mathrm{Exp}^{\text{mean}}$")
plt.suptitle("Sign-flip decomposition of the firm-day exposure IV (two-way clustered 95% CI)")
plt.tight_layout()
plt.savefig(FIG / "fig_v2_signflip_coef.png", dpi=160)
plt.close()


# Fig 5: scatter of new IV vs old kl_weighted (random subsample)
samp = mp.sample(n=min(40000, len(mp)), random_state=0)
samp = samp.dropna(subset=["fd_mean_exposure","kl_weighted"])
samp = samp[(samp["fd_mean_exposure"] > 0)]
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(samp["kl_weighted"], samp["fd_mean_exposure"], s=2, alpha=0.18, color="#1f4e79")
ax.set_xlabel("Engagement-weighted daily KL (original IV)")
ax.set_ylabel(r"Firm-day exposure $\mathrm{Exp}^{\text{mean}}$ (new IV)")
ax.set_title(f"New vs.\\ old misinformation regressors  ($n={len(samp):,}$, $r=0.10$)")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig_v2_new_vs_old.png", dpi=160)
plt.close()


print("Wrote:")
for f in sorted(TBL.iterdir()): print(" ", f)
for f in sorted(FIG.iterdir()): print(" ", f)
