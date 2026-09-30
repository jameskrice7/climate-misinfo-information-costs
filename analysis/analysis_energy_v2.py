"""Energy-subsample analysis with the firm-day LLM exposure IV.

Replicates the *energy-relevant* portion of main_analysis.py, replacing the
market-wide daily KL index with a per-firm-day misinformation-exposure score
derived from Qwen3.6-35B-A3B-FP8 classifying every climate post against the
firm's TRBC industry. Produces:

  results/econ_results_v2.json   - all coefficients, SEs, p, N
  results/tables/*.tex           - LaTeX table fragments
  results/figures/*.png          - figures

Runs (all on the energy subsample):
  Main I/II/III     - SpreadPercent, CAPM_Beta, ExcessReturn ~ new IV
  Two-way clustered - SE clustered by RIC + Date
  Standardized      - z-score effects
  Sign-flip         - Renewables / Fossil / Region / Period
  Subperiod         - 2012-2018 vs 2019-2025
  Lag               - contemporaneous vs lag-1 IV
  Comparison        - new IV vs original kl_weighted in same spec
  IV variants       - fd_mean_exposure, fd_sum_exposure, fd_share_misinfo,
                      fd_mean_misinformation
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyfixest as pf

# Replication-package layout (paths were absolute on the author's machine)
REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "pipeline"          # classification pipeline: work/, out/
REPL = REPO                       # data/PAPER_2_PANEL_energy.parquet
OUT = REPO / "results"
os.chdir(ROOT)                    # the placebo block's DuckDB paths are relative to the pipeline
TBL = OUT / "tables"
FIG = OUT / "figures"
for d in (OUT, TBL, FIG):
    d.mkdir(parents=True, exist_ok=True)

RESULTS_PATH = OUT / "econ_results_v2.json"
results: dict = {}
t0 = time.time()


def save():
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)


# ================================================================
# Load + merge
# ================================================================
print("loading energy panel + firm-day IV ...", flush=True)
panel = pd.read_parquet(REPL / "data" / "PAPER_2_PANEL_energy.parquet")
panel.rename(columns={"Company Market Cap": "MktCap",
                      "Dividend yield": "DivYield"}, inplace=True)
panel["Date"] = pd.to_datetime(panel["Date"]).dt.date
fd = pd.read_parquet(ROOT / "work" / "firmday_misinfo.parquet")
fd["Date"] = pd.to_datetime(fd["Date"]).dt.date
panel = panel.merge(fd, on=["RIC", "Date"], how="left")
# fill firm-days without any matched posts with zeros (no exposure)
for c in ["fd_n_posts", "fd_mean_relevance", "fd_mean_misinformation",
          "fd_mean_exposure", "fd_max_exposure", "fd_sum_exposure",
          "fd_share_misinfo"]:
    panel[c] = panel[c].fillna(0.0)
print(f"  panel rows {len(panel):,} | with_posts {(panel.fd_n_posts>0).sum():,} "
      f"({(panel.fd_n_posts>0).mean()*100:.1f}%)", flush=True)


# Derived transforms ---------------------------------------------------------
num_cols = panel.select_dtypes(include="number").columns
panel[num_cols] = panel[num_cols].replace([np.inf, -np.inf], np.nan)
panel["log_volume"] = np.log1p(panel["Volume"].clip(lower=0))
panel["log_mktcap"] = np.log(panel["MktCap"].clip(lower=1))
panel["log_turnover"] = np.log1p(panel["Turnover"].clip(lower=0))
panel["abs_orderflow"] = panel["OrderFlow"].abs()
panel["YearMonth"] = pd.to_datetime(panel["Date"]).dt.to_period("M").astype(str)
panel["TRBC_Industry"] = panel["TRBC Industry Name"]
panel["Date_dt"] = pd.to_datetime(panel["Date"])
# log(1+x) versions of the exposure IVs to tame skew
panel["log_fd_sum_exposure"] = np.log1p(panel["fd_sum_exposure"].clip(lower=0))
panel["log_fd_n_posts"] = np.log1p(panel["fd_n_posts"].clip(lower=0))


# ================================================================
# Prep helper - winsorize controls (not the IV)
# ================================================================
WINS = ["SpreadPercent", "IntradayVolatility", "PriceImpact", "CAPM_Beta",
        "DailyReturn", "ExcessReturn", "abs_orderflow", "log_volume",
        "log_mktcap", "DivYield", "log_turnover",
        "FF_MktRF", "FF_SMB", "FF_HML", "FF_RMW", "FF_CMA"]

IV_VARS = ["fd_mean_exposure", "fd_sum_exposure",
           "fd_mean_misinformation", "fd_mean_relevance",
           "fd_max_exposure", "fd_share_misinfo",
           "log_fd_sum_exposure", "fd_n_posts", "log_fd_n_posts"]


def prep(df, dep, kind, extra=()):
    d = df.copy()
    cols_needed = {dep, "RIC", "YearMonth", "Date", "Region", "TRBC_Industry"}
    if kind == "pin":
        ctrls = ["log_volume", "log_mktcap", "IntradayVolatility",
                 "abs_orderflow", "log_turnover", "cpi_inflation",
                 "gdp_growth", "unemployment"]
    elif kind == "capm":
        ctrls = ["log_volume", "log_mktcap", "SpreadPercent", "DivYield",
                 "IntradayVolatility", "cpi_inflation", "gdp_growth",
                 "unemployment"]
    else:  # ff
        ctrls = ["FF_MktRF", "FF_SMB", "FF_HML", "FF_RMW", "FF_CMA",
                 "log_volume", "log_mktcap", "SpreadPercent", "DivYield",
                 "IntradayVolatility", "cpi_inflation", "gdp_growth",
                 "unemployment"]
    cols_needed |= set(ctrls) | set(IV_VARS) | set(extra)
    if "kl_weighted" in d.columns:
        cols_needed.add("kl_weighted"); cols_needed.add("kl_raw")
    d = d[[c for c in cols_needed if c in d.columns]].dropna()
    # winsorize numeric controls (NOT the IVs themselves)
    skip = set(IV_VARS) | {"kl_weighted", "kl_raw"}
    for c in d.select_dtypes(include=[np.number]).columns:
        if c in skip:
            continue
        lo, hi = d[c].quantile([0.01, 0.99])
        d[c] = d[c].clip(lo, hi)
    return d


# Spec templates
F_PIN  = "SpreadPercent ~ {iv} + log_volume + log_mktcap + IntradayVolatility + abs_orderflow + log_turnover + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"
F_CAPM = "CAPM_Beta     ~ {iv} + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"
F_FF   = "ExcessReturn  ~ {iv} + FF_MktRF + FF_SMB + FF_HML + FF_RMW + FF_CMA + log_volume + log_mktcap + SpreadPercent + DivYield + IntradayVolatility + cpi_inflation + gdp_growth + unemployment | RIC + YearMonth"


def fit(formula, data, term, vcov_kind):
    """vcov_kind: 'firm' or 'twoway'."""
    if vcov_kind == "firm":
        m = pf.feols(formula, data=data, vcov={"CRV1": "RIC"})
    else:
        m = pf.feols(formula, data=data, vcov={"CRV1": "RIC+Date"})
    return {
        "coef": float(m.coef()[term]),
        "se":   float(m.se()[term]),
        "t":    float(m.tstat()[term]),
        "p":    float(m.pvalue()[term]),
        "N":    int(m._N),
        "r2":   float(m._r2),
        "r2_within": float(m._r2_within),
    }


# ================================================================
# 1. CORE: I, II, III x IV variants x clustering
# ================================================================
print("\n=== CORE MAIN MODELS (energy subsample) ===", flush=True)
dp = prep(panel, "SpreadPercent", "pin")
dc = prep(panel, "CAPM_Beta", "capm")
df = prep(panel, "ExcessReturn", "ff")
print(f"  N rows after dropna: PIN={len(dp):,} CAPM={len(dc):,} FF={len(df):,}", flush=True)

core = {}
for iv in ["fd_mean_exposure", "log_fd_sum_exposure",
           "fd_mean_misinformation", "fd_mean_relevance"]:
    for vname, vk in (("firm", "firm"), ("twoway", "twoway")):
        core[f"I_Spread_{iv}_{vname}"]  = fit(F_PIN.format(iv=iv),  dp, iv, vk)
        core[f"II_CAPM_{iv}_{vname}"]   = fit(F_CAPM.format(iv=iv), dc, iv, vk)
        core[f"III_FF_{iv}_{vname}"]    = fit(F_FF.format(iv=iv),   df, iv, vk)
    a = core[f"I_Spread_{iv}_twoway"]
    b = core[f"II_CAPM_{iv}_twoway"]
    c = core[f"III_FF_{iv}_twoway"]
    print(f"  {iv:24s} | I={a['coef']:+.4e}(p={a['p']:.3f}) "
          f"II={b['coef']:+.4e}(p={b['p']:.3f}) "
          f"III={c['coef']:+.4e}(p={c['p']:.3f})", flush=True)
results["core"] = core
save()


# ================================================================
# 2. STANDARDIZED EFFECTS (z-scored IV)
# ================================================================
print("\n=== STANDARDIZED EFFECTS ===", flush=True)
std_out = {}
for iv in ["fd_mean_exposure", "log_fd_sum_exposure",
           "fd_mean_misinformation", "fd_mean_relevance"]:
    for tag, d, dep, kind, F in (("I", dp, "SpreadPercent", "pin", F_PIN),
                                 ("II", dc, "CAPM_Beta", "capm", F_CAPM),
                                 ("III", df, "ExcessReturn", "ff", F_FF)):
        dd = d.copy()
        dd[f"{iv}_z"] = (dd[iv] - dd[iv].mean()) / dd[iv].std(ddof=0)
        std_out[f"{tag}_{iv}"] = fit(F.format(iv=f"{iv}_z"), dd, f"{iv}_z", "twoway")
results["standardized"] = std_out
save()


# ================================================================
# 3. SIGN-FLIP DECOMPOSITION
# ================================================================
print("\n=== SIGN-FLIP DECOMPOSITION ===", flush=True)
renewable_ind = {"Renewable Energy Equipment & Services", "Renewable Fuels"}
fossil_ind = {"Coal", "Oil & Gas Refining and Marketing",
              "Oil & Gas Exploration and Production",
              "Oil Related Services and Equipment",
              "Oil & Gas Transportation Services",
              "Integrated Oil & Gas", "Oil & Gas Drilling"}
panel["energy_type"] = "Other"
panel.loc[panel["TRBC_Industry"].isin(renewable_ind), "energy_type"] = "Renewable"
panel.loc[panel["TRBC_Industry"].isin(fossil_ind), "energy_type"] = "Fossil"

sf = {}
for tag, mask in [("Renewable", panel["energy_type"] == "Renewable"),
                  ("Fossil",   panel["energy_type"] == "Fossil"),
                  ("US",       panel["Region"] == "US"),
                  ("UK",       panel["Region"] == "UK"),
                  ("EU",       panel["Region"] == "EU"),
                  ("CN",       panel["Region"] == "CN"),
                  ("JP",       panel["Region"] == "JP"),
                  ("Pre2019",  pd.to_datetime(panel["Date"]) <= "2018-12-31"),
                  ("Post2019", pd.to_datetime(panel["Date"]) >= "2019-01-01")]:
    sub = panel[mask]
    for tag_m, kind, F, dep in (("I_Spread", "pin", F_PIN, "SpreadPercent"),
                                ("II_CAPM",  "capm", F_CAPM, "CAPM_Beta"),
                                ("III_FF",   "ff",   F_FF, "ExcessReturn")):
        d = prep(sub, dep, kind)
        if len(d) < 1000:
            continue
        try:
            r = fit(F.format(iv="fd_mean_exposure"), d, "fd_mean_exposure", "twoway")
            sf[f"{tag}_{tag_m}"] = r
        except Exception as e:
            sf[f"{tag}_{tag_m}"] = {"err": str(e)}
    s = sf.get(f"{tag}_I_Spread", {})
    print(f"  {tag:10s} I_Spread coef={s.get('coef')!r}  p={s.get('p')!r}  N={s.get('N')!r}", flush=True)
results["signflip"] = sf
save()


# ================================================================
# 4. SUBPERIOD SPLITS (full energy panel)
# ================================================================
print("\n=== SUBPERIOD ===", flush=True)
sub_out = {}
for nm, lo, hi in [("2012-2018", "2012-01-01", "2018-12-31"),
                   ("2019-2025", "2019-01-01", "2025-12-31")]:
    mask = (pd.to_datetime(panel["Date"]) >= lo) & (pd.to_datetime(panel["Date"]) <= hi)
    sub = panel[mask]
    for tag_m, kind, F, dep in (("I_Spread", "pin", F_PIN, "SpreadPercent"),
                                ("II_CAPM",  "capm", F_CAPM, "CAPM_Beta"),
                                ("III_FF",   "ff",   F_FF, "ExcessReturn")):
        d = prep(sub, dep, kind)
        if len(d) < 1000:
            continue
        sub_out[f"{nm}_{tag_m}"] = fit(F.format(iv="fd_mean_exposure"), d, "fd_mean_exposure", "twoway")
        s = sub_out[f"{nm}_{tag_m}"]
        print(f"  {nm} {tag_m:10s} coef={s['coef']:+.4e} p={s['p']:.3f} N={s['N']:,}", flush=True)
results["subperiod"] = sub_out
save()


# ================================================================
# 5. LAG SPEC: contemporaneous vs lag-1
# ================================================================
print("\n=== LAG SPECIFICATION ===", flush=True)
lag = panel[["RIC", "Date", "fd_mean_exposure", "log_fd_sum_exposure"]].copy()
lag["Date_dt"] = pd.to_datetime(lag["Date"])
lag["Date_dt_next"] = lag["Date_dt"] + pd.Timedelta(days=1)
lag1 = lag.rename(columns={
    "fd_mean_exposure": "fd_mean_exposure_lag1",
    "log_fd_sum_exposure": "log_fd_sum_exposure_lag1",
})[["RIC", "Date_dt_next", "fd_mean_exposure_lag1", "log_fd_sum_exposure_lag1"]]
lag1.rename(columns={"Date_dt_next": "Date_dt"}, inplace=True)
panel["Date_dt"] = pd.to_datetime(panel["Date"])
panel_l = panel.merge(lag1, on=["RIC", "Date_dt"], how="left")
lag_out = {}
for tag_m, kind, F, dep in (("I_Spread", "pin", F_PIN, "SpreadPercent"),
                            ("II_CAPM",  "capm", F_CAPM, "CAPM_Beta"),
                            ("III_FF",   "ff",   F_FF, "ExcessReturn")):
    d = prep(panel_l, dep, kind, extra=("fd_mean_exposure_lag1",))
    d = d.dropna(subset=["fd_mean_exposure_lag1"])
    lag_out[f"{tag_m}_contemp"] = fit(F.format(iv="fd_mean_exposure"),       d, "fd_mean_exposure",       "twoway")
    lag_out[f"{tag_m}_lag1"]    = fit(F.format(iv="fd_mean_exposure_lag1"),  d, "fd_mean_exposure_lag1",  "twoway")
    a = lag_out[f"{tag_m}_contemp"]; b = lag_out[f"{tag_m}_lag1"]
    print(f"  {tag_m:10s} contemp={a['coef']:+.4e}(p={a['p']:.3f}) lag1={b['coef']:+.4e}(p={b['p']:.3f}) N={a['N']:,}", flush=True)
results["lag"] = lag_out
save()


# ================================================================
# 6. PLACEBO within energy: high-relevance vs low-relevance posts
#    Compare the model where the IV is the exposure of posts deemed
#    "highly relevant to the firm's sector" (fd_mean_relevance) to
#    one where the IV is irrelevant-post share -- a placebo since
#    irrelevant climate posts shouldn't move firm-day spreads.
# ================================================================
print("\n=== PLACEBO (relevance high vs low) ===", flush=True)
plc = {}
# The placebo re-aggregates post-level scores by calendar date, which needs the
# firm x post expansion (pipeline/expand.py) and the post dates in work/posts.parquet.
# posts.parquet holds Meta Content Library post text and is not redistributed, so
# without it this block is skipped and the shipped results/tables/tab_v2_placebo.tex
# stands as the record.
PLACEBO_INPUTS = (Path("out/energy_scored"), Path("work/posts.parquet"))
if not all(p.exists() for p in PLACEBO_INPUTS):
    print("  skipped: needs out/energy_scored/ and work/posts.parquet (not redistributed)", flush=True)
    plc["skipped"] = "needs Meta Content Library post data (work/posts.parquet)"
else:
    # IV is the contribution of relevant-only posts (proxied by relevance score itself
    # above a threshold). Simpler: re-aggregate using only the subset where relevance>=50
    # and only rel<10 as placebo.
    print("  building placebo aggregates ...", flush=True)
    import duckdb
    con = duckdb.connect()
    con.execute("PRAGMA threads=4"); con.execute("PRAGMA memory_limit='8GB'")
    con.execute("""
    CREATE TABLE plc_relevant AS
    WITH scored AS (SELECT RIC, post_id, relevance, misinformation, exposure
                    FROM read_parquet('out/energy_scored/*.parquet')
                    WHERE relevance >= 50),
         wd AS (SELECT s.RIC, CAST(p.post_date AS DATE) AS Date, s.exposure
                FROM scored s JOIN 'work/posts.parquet' p ON s.post_id=p.post_id)
    SELECT RIC, Date, AVG(exposure) AS fd_mean_exposure_rel
    FROM wd GROUP BY RIC, Date;
    """)
    con.execute("""
    CREATE TABLE plc_irrelevant AS
    WITH scored AS (SELECT RIC, post_id, relevance, misinformation, exposure
                    FROM read_parquet('out/energy_scored/*.parquet')
                    WHERE relevance < 10),
         wd AS (SELECT s.RIC, CAST(p.post_date AS DATE) AS Date, s.exposure
                FROM scored s JOIN 'work/posts.parquet' p ON s.post_id=p.post_id)
    SELECT RIC, Date, AVG(exposure) AS fd_mean_exposure_irrel
    FROM wd GROUP BY RIC, Date;
    """)
    rel = con.execute("SELECT * FROM plc_relevant").df()
    irr = con.execute("SELECT * FROM plc_irrelevant").df()
    rel["Date"] = pd.to_datetime(rel["Date"]).dt.date
    irr["Date"] = pd.to_datetime(irr["Date"]).dt.date
    pp = panel.merge(rel, on=["RIC","Date"], how="left").merge(irr, on=["RIC","Date"], how="left")
    pp["fd_mean_exposure_rel"]   = pp["fd_mean_exposure_rel"].fillna(0.0)
    pp["fd_mean_exposure_irrel"] = pp["fd_mean_exposure_irrel"].fillna(0.0)

    for tag, iv in (("relevant", "fd_mean_exposure_rel"),
                    ("irrelevant_placebo", "fd_mean_exposure_irrel")):
        for tag_m, kind, F, dep in (("I_Spread", "pin", F_PIN, "SpreadPercent"),
                                    ("II_CAPM",  "capm", F_CAPM, "CAPM_Beta"),
                                    ("III_FF",   "ff",   F_FF, "ExcessReturn")):
            d = prep(pp, dep, kind, extra=(iv,))
            plc[f"{tag}_{tag_m}"] = fit(F.format(iv=iv), d, iv, "twoway")
        print(f"  {tag:18s} I_Spread={plc[f'{tag}_I_Spread']['coef']:+.4e} "
              f"(p={plc[f'{tag}_I_Spread']['p']:.3f})", flush=True)
results["placebo"] = plc
save()


# ================================================================
# 7. COMPARISON WITH ORIGINAL kl_weighted (same spec, same sample)
# ================================================================
print("\n=== COMPARISON WITH ORIGINAL kl_weighted ===", flush=True)
cmp = {}
for tag_m, kind, F, dep, d in (("I_Spread", "pin", F_PIN, "SpreadPercent", dp),
                               ("II_CAPM",  "capm", F_CAPM, "CAPM_Beta",   dc),
                               ("III_FF",   "ff",   F_FF, "ExcessReturn",  df)):
    if "kl_weighted" in d.columns:
        cmp[f"{tag_m}_kl_weighted"] = fit(F.format(iv="kl_weighted"), d, "kl_weighted", "twoway")
        cmp[f"{tag_m}_kl_raw"]      = fit(F.format(iv="kl_raw"),      d, "kl_raw",      "twoway")
    cmp[f"{tag_m}_fd_mean_exposure"] = fit(F.format(iv="fd_mean_exposure"), d, "fd_mean_exposure", "twoway")
results["comparison_with_original"] = cmp
save()


# ================================================================
# 8. TRIPLE-INTERACTION (Energy type x Region x Period) on new IV
# ================================================================
print("\n=== TRIPLE INTERACTION (Fossil x English x Post2019) ===", flush=True)
def run_triple(dep, kind, F):
    d = prep(panel, dep, kind)
    meta = panel[["RIC", "Date", "TRBC_Industry", "Region"]].drop_duplicates(["RIC","Date"])
    d = d.merge(meta, on=["RIC","Date"], how="left", suffixes=("","_y"))
    d["Fossil"]    = d["TRBC_Industry"].isin(fossil_ind).astype(int)
    d["Renewable"] = d["TRBC_Industry"].isin(renewable_ind).astype(int)
    d["EnglishReg"] = d["Region"].isin(["US","UK"]).astype(int)
    d["Post2019"]   = (pd.to_datetime(d["Date"]) >= "2019-01-01").astype(int)
    d["iv_x_fossil"]    = d["fd_mean_exposure"] * d["Fossil"]
    d["iv_x_eng"]       = d["fd_mean_exposure"] * d["EnglishReg"]
    d["iv_x_post"]      = d["fd_mean_exposure"] * d["Post2019"]
    d["iv_x_fossil_eng"]  = d["fd_mean_exposure"] * d["Fossil"] * d["EnglishReg"]
    d["iv_x_fossil_post"] = d["fd_mean_exposure"] * d["Fossil"] * d["Post2019"]
    d["iv_x_eng_post"]    = d["fd_mean_exposure"] * d["EnglishReg"] * d["Post2019"]
    d["iv_x_fossil_eng_post"] = d["fd_mean_exposure"] * d["Fossil"] * d["EnglishReg"] * d["Post2019"]
    base = F.format(iv="fd_mean_exposure")
    formula = base.replace("fd_mean_exposure",
        "fd_mean_exposure + iv_x_fossil + iv_x_eng + iv_x_post + iv_x_fossil_eng + iv_x_fossil_post + iv_x_eng_post + iv_x_fossil_eng_post")
    m = pf.feols(formula, data=d, vcov={"CRV1": "RIC+Date"})
    terms = ["fd_mean_exposure", "iv_x_fossil", "iv_x_eng", "iv_x_post",
             "iv_x_fossil_eng", "iv_x_fossil_post", "iv_x_eng_post",
             "iv_x_fossil_eng_post"]
    return {"N": int(d.shape[0]), **{t: {"coef": float(m.coef()[t]),
                                          "se": float(m.se()[t]),
                                          "p": float(m.pvalue()[t])} for t in terms}}

results["triple_spread"] = run_triple("SpreadPercent", "pin", F_PIN)
results["triple_ff"]     = run_triple("ExcessReturn", "ff", F_FF)
save()


# ================================================================
# 9. Descriptive stats of the new IV
# ================================================================
print("\n=== DESCRIPTIVE STATS OF NEW IV ===", flush=True)
desc = {}
for c in ["fd_n_posts", "fd_mean_relevance", "fd_mean_misinformation",
          "fd_mean_exposure", "fd_max_exposure", "fd_sum_exposure",
          "fd_share_misinfo", "log_fd_sum_exposure"]:
    v = panel[c].dropna()
    desc[c] = {"mean": float(v.mean()), "sd": float(v.std()),
               "p50": float(v.quantile(0.5)),
               "p90": float(v.quantile(0.9)),
               "p99": float(v.quantile(0.99)),
               "max": float(v.max()),
               "share_zero": float((v == 0).mean())}
results["descriptive"] = desc
# Correlation between new IV and old IV
overlap = panel.dropna(subset=["fd_mean_exposure", "kl_weighted"])
results["iv_correlation"] = {
    "n": int(len(overlap)),
    "corr_mean_exposure_kl_weighted": float(overlap["fd_mean_exposure"].corr(overlap["kl_weighted"])),
    "corr_sum_exposure_kl_weighted":  float(overlap["log_fd_sum_exposure"].corr(overlap["kl_weighted"])),
    "corr_mean_misinfo_kl_weighted":  float(overlap["fd_mean_misinformation"].corr(overlap["kl_weighted"])),
}
print("  IV-IV correlation:", results["iv_correlation"], flush=True)
save()

print(f"\nALL DONE in {(time.time()-t0)/60:.1f} min -> {RESULTS_PATH}", flush=True)
