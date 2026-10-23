"""Generate every numerical manuscript passage, table, and data figure."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import logging
logging.getLogger('fontTools').setLevel(logging.WARNING)
from publication_analysis import ROOT, OUT, X, load_panel, PRIOR

SRC=ROOT/'paper/submission/source'
for sub in ['generated','tables','figures']: (SRC/sub).mkdir(parents=True,exist_ok=True)
r=json.loads((OUT/'analysis_results.json').read_text(encoding='utf-8'))
assert 'seconds' in r['run'], 'The full analysis must finish before document generation.'
s=r['specifications']; primary=s['primary']; b=primary['sector_date'][X]
def fmt(v,n=4): return f'{v:.{n}f}'
def prob(v): return '$<0.001$' if v<.001 else f'{v:.3f}'
def esc(v):
    return str(v).replace('&',r'\&').replace('_',r'\_').replace('%',r'\%')
def write(file,text): (SRC/file).write_text(text+'\n',encoding='utf-8')
def stat(model,term=None):
    m=s[model]; term=term or next(iter(m['sector_date']))
    z=m['sector_date'][term]
    return [fmt(z['Estimate']),fmt(z['Std. Error']),prob(z['Pr(>|t|)']),f"{m['N']:,}"]
def table(file,caption,label,headers,rows,note,width='0.43\\linewidth',size='small'):
    spec='p{'+width+'}'+'r'*(len(headers)-1)
    lines=[r'\begin{table}[htbp]',r'\centering',r'\caption{'+caption+'}',
      r'\label{'+label+'}',r'\begin{minipage}{\linewidth}','\\'+size,
      r'\setlength{\tabcolsep}{4pt}',r'\begingroup\centering',r'\begin{tabular}{'+spec+'}',r'\toprule',
      ' & '.join(headers)+r' \\',r'\midrule']
    lines+=[' & '.join(map(str,row))+r' \\' for row in rows]
    lines +=[r'\bottomrule',r'\end{tabular}\par\endgroup',r'\par\vspace{0.5em}\footnotesize '+note,
       r'\end{minipage}',r'\end{table}']
    write('tables/'+file,'\n'.join(lines))

sd=primary['exposure_sd']; B=b['Estimate']; ci=(b['2.5%'],b['97.5%'])
abs_effect=B*sd*100; lo,hi=[v*sd*100 for v in ci]
abstract=(f"Does climate misinformation predict trading costs in energy equities? This paper combines "
 "a sector-specific content index from 217,954 English-language Facebook posts with daily financial data. "
 f"The principal sample contains {primary['N']:,} observations on {primary['securities']} securities in nine "
 "energy sub-industries during January 2012--October 2025. A fixed language-model rubric scores "
 "misinformation and sector relevance separately. Positive spread associations under monthly controls "
 "change sign when market-by-date and sector-by-month fixed effects are included on a common sample. "
 "The principal specification uses prior-session financial controls and yields a coefficient of "
 f"{B:.4f} percentage points per index point (approximate 95\\% sector/date-clustered interval "
 f"[{ci[0]:.4f}, {ci[1]:.4f}]). A sample-standard-deviation difference in content corresponds to "
 f"{abs_effect:.3f} basis points in spread, with an interval of [{lo:.3f}, {hi:.3f}]. "
 "Alternative inference and timing checks do not establish a stable positive liquidity-cost association. "
 "The observational design, nine sector clusters, unvalidated classifier accuracy, and absence of "
 "observed investor exposure limit interpretation. The findings show why sector-level content measures "
 "require local market controls and explicit measurement checks before being interpreted as the "
 "financial costs of climate misinformation.")
write('generated/abstract.tex',abstract)
write('generated/introduction_results.tex',
 f"The principal estimation sample contains {primary['N']:,} security-days on {primary['securities']} "
 f"securities from {primary['issuers']} distinct company names. On the common-sample nested comparison, "
 f"the content coefficient is {s['common_month']['sector_date'][X]['Estimate']:.4f} with security/month "
 f"effects and {s['common_marketdate_sectormonth']['sector_date'][X]['Estimate']:.4f} with security, "
 "market-day, and sector-month effects. The principal estimate with prior-session controls is "
 f"{B:.4f} (sector/date-clustered $p={b['Pr(>|t|)']:.3f}$). The contrast shows that the positive monthly "
 "association is sensitive to the treatment of sector-level conditions. It does not establish that "
 "misinformation has no effect on liquidity: the conditional comparison, content measurement, and "
 "uncertainty estimates all have substantive limits.")
write('generated/sample_text.tex',
 f"After support, quote, trading-activity, and required-control filters, the principal sample has "
 f"{primary['N']:,} observations on {primary['securities']} securities and {primary['dates']:,} observed "
 f"dates. The raw spread median is {primary['dep_median']:.3f}\\%, while its winsorized mean is "
 f"{primary['dep_mean']:.3f}\\%. The content index has sample standard deviation {sd:.3f} on its 0--100 "
 f"scale; after residualizing against the principal controls and fixed effects, its standard deviation "
 f"is {primary['residual_exposure_sd']:.3f}. Sample construction and sector composition are reported "
 "in the supplementary material.")
lag=s['session_all']['sector_date']['lag_exposure']; lead=s['timing_lead']['sector_date']['lead_exposure']
post=s['period_interaction']['sector_date']['exposure_post2019']
write('generated/results_text.tex',
 r'\subsection{The fixed-effect comparison}'+'\n'+
 f"Table~\\ref{{tab:fe}} compares four specifications on the same {s['common_month']['N']:,} complete-case "
 "observations. All include contemporaneous volume, capitalization, and the daily price range. "
 f"The security/month coefficient is {s['common_month']['sector_date'][X]['Estimate']:.4f}. Adding daily "
 f"effects yields {s['common_date']['sector_date'][X]['Estimate']:.4f}; market-day effects yield "
 f"{s['common_marketdate']['sector_date'][X]['Estimate']:.4f}. The sign changes to "
 f"{s['common_marketdate_sectormonth']['sector_date'][X]['Estimate']:.4f} when sector-month effects are "
 "included. This sign change occurs without changing the observations or financial tail caps. "
 "It is therefore a specification difference, rather than a consequence of comparing different "
 "complete-case samples. Figure~\\ref{fig:specifications} displays the estimates and uncertainty.\n\n"
 "The positive local-market-day association and its disappearance after sector-month controls "
 "suggest that slower sector-level co-movement matters to the monthly result. This comparison "
 "does not identify whether that component reflects confounding sector conditions or a persistent "
 "information channel absorbed by the sector-month effects. It establishes sensitivity of the "
 "descriptive coefficient, rather than proving that the more saturated model isolates a causal effect.\n\n"
 r'\subsection{Principal estimate and economic scale}'+'\n'+
 f"Table~\\ref{{tab:primary}} reports the model with prior-session controls. The coefficient is "
 f"{B:.5f}, with sector/date standard error {b['Std. Error']:.5f} and an approximate 95\\% interval "
 f"[{ci[0]:.5f}, {ci[1]:.5f}]. It is not distinguishable from zero at conventional levels "
 f"($p={b['Pr(>|t|)']:.3f}$). Scaling by the sample standard deviation of content gives "
 f"{abs_effect:.3f} basis points, with an interval [{lo:.3f}, {hi:.3f}], compared with a "
 f"winsorized mean spread of {primary['dep_mean']*100:.2f} basis points. These are conditional "
 "associations in the fitted sample, not the estimated consequences of an intervention.\n\n"
 f"Security/date clustering gives $p={primary['firm_date'][X]['Pr(>|t|)']:.3f}$, while date-score HAC "
 f"gives $p={primary['date_score_hac']['20']['p']:.3f}$ at bandwidth 20. The sector score-sign diagnostic "
 f"gives {primary['sector_score_signs']['p']:.3f}. These calculations use distinct assumptions and "
 "cannot repair endogeneity, but none supplies evidence for a positive coefficient in this model. "
 "The supplement reports all three HAC bandwidths and the exposure-variation contribution of each sector.\n\n"
 r'\subsection{Timing and sensitivity}'+'\n'+
 f"Table~\\ref{{tab:timing}} compares current content, previous-session content, previous-calendar-day "
 "content, and a future-session lead on a common sample. The previous-session estimate on the "
 f"larger available timing sample is {lag['Estimate']:.4f} ($p={lag['Pr(>|t|)']:.3f}$). The future-session "
 f"lead in the common sample is {lead['Estimate']:.4f} ($p={lead['Pr(>|t|)']:.3f}$). The lead comparison "
 "does not establish reverse causality or validate the lag; persistent information conditions and "
 "serially correlated content can generate both. The estimates do not establish a distinctive "
 "positive delayed response after the local market and sector controls.\n\n"
 "The supplementary tables report transformations of the spread, alternative content measures, "
 "the matched-post-only sample, joint adjustment for post volume and relevance, and sector/market "
 "leave-out checks. Raw-spread and log-spread coefficients do not have a common numerical scale, "
 "and their signs must not be selected to support a preferred mechanism. "
 f"The formal post-2019 slope interaction is {post['Estimate']:.4f} "
 f"($p={post['Pr(>|t|)']:.3f}$); it is a direct test of a slope difference, "
 "rather than a comparison of whether two separate subperiod probabilities cross 0.05. "
 "All these checks are descriptive sensitivity analyses, with no independent causal interpretation.")

models=[('common_month','Security and month'),('common_date','Security and date'),
 ('common_marketdate','Security and market-day'),
 ('common_marketdate_sectormonth','Security, market-day, sector-month')]
rows=[]
for name,label in models:
    z=s[name]['sector_date'][X]
    rows.append([esc(label),fmt(z['Estimate']),fmt(z['Std. Error']),prob(z['Pr(>|t|)'])])
table('fixed_effects.tex','Nested fixed-effect comparison on a common sample','tab:fe',
 ['Fixed effects','Coefficient','SE','$p$'],rows,
 f"All models use {s['common_month']['N']:,} observations, the same contemporaneous controls and tail caps. "
 "The outcome is the quoted spread in percentage points. SE and reference probabilities cluster by sector and date (nine sectors).",width='0.49\\linewidth')
table('primary.tex','Principal spread regression with prior-session controls','tab:primary',
 ['Variable','Coefficient','Sector/date SE','$p$'],
 [[label,*[fmt(primary['sector_date'][key]['Estimate']),fmt(primary['sector_date'][key]['Std. Error']),prob(primary['sector_date'][key]['Pr(>|t|)'])]]
 for key,label in [(X,'Composite content'),('lag_log_volume','Prior log volume'),
 ('lag_log_mktcap','Prior log capitalization'),('lag_range_pct','Prior daily range')]],
 f"N={primary['N']:,}; {primary['securities']} securities; {primary['dates']:,} dates. "
 "Security, market-day and sector-month effects are absorbed. Coefficients are in percentage-point spread units. "
 f"Within $R^2={primary['r2_within']:.3f}$. Prior refers to the previous observed active session.",width='0.41\\linewidth')
timings=[('timing_current','Current content',X),('timing_session','Previous active session','lag_exposure'),
 ('timing_calendar','Previous calendar day','calendar_lag'),('timing_lead','Next active session','lead_exposure')]
table('timing.tex','Timing comparison on a common sample','tab:timing',['Content timing','Coefficient','SE','$p$'],
 [[lab,*stat(name,term)[:3]] for name,lab,term in timings],
 f"Each model uses {s['timing_current']['N']:,} observations and the principal fixed effects and prior controls. "
 "Exposure outside the corpus window is unavailable; session gaps over ten days are excluded. Sector/date inference.")
market=pd.read_csv(OUT/'market_composition.csv')
table('markets.tex','Listing-market composition of the principal sample','tab:markets',
 ['Listing market','Securities','Security-days','Mean spread'],
 [[esc(row.Market),str(row.securities),f'{row.observations:,}',fmt(row.mean_spread,3)] for row in market.itertuples()],
 "Market comes from the listing-exchange suffix. Mean spreads are raw percentages before tail capping. "
 "Market-day effects absorb all observed local securities together; counts do not measure independent shocks.")
sectors=pd.read_csv(OUT/'sector_composition.csv')
table('sectors.tex','Sector composition of the principal sample','tab:sectors',
 ['Energy sub-industry','Securities','Observations','Mean content'],
 [[esc(row.Sector),str(row.securities),f'{row.observations:,}',fmt(row.mean_exposure,3)] for row in sectors.itertuples()],
 "Counts describe the principal estimation sample. Content is common within sector and date; observations are security-days.",width='0.50\\linewidth')
p=load_panel(); flow=[]
flow.append(['Financial input',f'{len(p):,}'])
q=p.loc[p.in_support]; flow.append(['Within content window',f'{len(q):,}'])
q=q.loc[q.valid_quote]; flow.append(['Positive valid quotes and active trading',f'{len(q):,}'])
flow.append(['Contemporaneous-control complete cases',f"{s['common_month']['N']:,}"])
flow.append(['Prior-session-control complete cases',f"{primary['N']:,}"])
table('sample_flow.tex','Estimation sample construction','tab:flow',['Filter','Security-days'],flow,
 "The two complete-case rows are alternative control choices applied to the same eligible quote sample, not sequential filters. "
 "Content window is 3 January 2012 to 13 October 2025. Active trading requires positive volume and a positive close.",width='0.72\\linewidth')
inferences=[['Security/date clusters',fmt(primary['firm_date'][X]['Std. Error'],5),prob(primary['firm_date'][X]['Pr(>|t|)'])],
 ['Sector/date clusters',fmt(b['Std. Error'],5),prob(b['Pr(>|t|)'])]]
inferences.extend([[f'Date-score HAC, bandwidth {L}',fmt(z['se'],5),prob(z['p'])] for L,z in primary['date_score_hac'].items()])
inferences.append(['Sector score signs','---',prob(primary['sector_score_signs']['p'])])
table('inference.tex','Alternative inference for the principal coefficient','tab:inference',
 ['Reference calculation','SE','$p$'],inferences,
 "The coefficient and observations are identical in every row. Sector/date clustering has nine sectors. "
 "HAC uses ordered observed dates and a normal reference. Score signs enumerate 512 combinations and require "
 "independent symmetric sector scores; this is a diagnostic, not exact randomization inference.",width='0.57\\linewidth')
variants=[('primary','Mean composite'),('variant_log_exposure_sum','Log of one plus composite sum'),
 ('variant_fd_mean_misinformation','Mean misinformation score'),('variant_fd_mean_relevance','Mean relevance score'),
 ('variant_fd_share_misinfo','Share with misinformation at least 25'),('variant_positive_exposure','Positive composite indicator'),
 ('attention_adjusted','Composite with volume and relevance controls')]
table('variants.tex','Alternative content measures and attention adjustment','tab:variants',
 ['Content regressor','Coefficient','SE','$p$'],[[lab,*stat(name)[:3]] for name,lab in variants],
 "Principal controls and fixed effects throughout. Regressor units differ across rows; raw coefficient sizes are not comparable. "
 "The final row adds log one plus post count and mean relevance jointly. Sector/date inference.",width='0.48\\linewidth')
sens=[('primary_nocontrol','No financial controls'),('primary_unwinsorized','Unwinsorized spread and controls'),
 ('primary_logspread','Log spread'),('primary_matched_posts','Matched-post dates only'),
 ('session_all','Previous-session content'),('vwap_deviation','VWAP-midpoint percentage gap')]
table('sensitivity.tex','Outcome, sample, and timing sensitivity','tab:sensitivity',
 ['Specification','Coefficient','SE','$p$','N'],[[lab,*stat(name)] for name,lab in sens],
 "Unless stated otherwise the outcome is a percentage-point spread. Log spread and the VWAP gap have different units/interpretations. "
 "No gap outcome is interpreted as transaction price impact. Sector/date inference.",width='0.40\\linewidth',size='footnotesize')
leave=[(name,name.removeprefix('omit_')) for name in s if name.startswith('omit_')]
leave +=[(name,'Market: '+name.removeprefix('omitmarket_')) for name in s if name.startswith('omitmarket_')]
table('leaveout.tex','Leave-out diagnostics with fixed full-sample tail caps','tab:leaveout',
 ['Omitted sector or market','Coefficient','SE','$p$'],[[esc(lab),*stat(name)[:3]] for name,lab in leave],
 "All specifications retain the principal controls and fixed effects. Leaving out a sector leaves eight sector clusters. "
 "The full principal sample supplies tail caps; they are not recomputed within each leave-out sample.",width='0.51\\linewidth',size='footnotesize')
table('controls.tex','Financial control definitions and tail caps','tab:controls',
 ['Variable','Lower cap','Upper cap'],
 [[lab,fmt(primary['winsor_limits'][key][0],4),fmt(primary['winsor_limits'][key][1],4)] for key,lab in
 [('SpreadPercent','Quoted spread, percent'),('lag_log_volume','Prior log one plus volume'),
 ('lag_log_mktcap','Prior log market capitalization'),('lag_range_pct','Prior range as percent of close')]],
 "Principal sample first and ninety-ninth percentile caps. Exposure scores are not capped.",width='0.55\\linewidth')
audit=json.loads((OUT/'input_audit.json').read_text())
c=audit['misinformation_cross_sector_consistency']
write('generated/audit_text.tex',
 f"The valid-score corpus has cross-sector disagreement in misinformation scores for {c['share_disagreement']*100:.2f}\\% "
 f"of posts. For {c['share_crossing_50']*100:.2f}\\%, the score crosses the threshold of 50 across sectors. "
 f"The mean within-post score range is {c['mean_range']:.3f} points. Although the rubric requests industry-independent "
 "misinformation judgments, these observations show some context sensitivity. This diagnostic neither measures "
 "misclassification against ground truth nor supports a claim that the remaining agreement is accurate.")
omit=[s[name]['sector_date'][X]['Estimate'] for name,lab in leave if name.startswith('omit_')]
write('generated/supplement_results.tex',
 f"Across the nine sector leave-out fits, coefficients range from {min(omit):.4f} to {max(omit):.4f}. "
 "These estimates assess concentration of the fitted association rather than supply nine independent confirmation tests. "
 f"The matrix condition number of the principal within-transformed regressor matrix is "
 f"{primary['matrix_condition_number']:.2f}. Its independently residualized coefficient equals "
 f"{primary['fwl_coefficient']:.8f}, matching the fitted coefficient to numerical precision. "
 "A machine-readable results file records coefficients for every included control, the fixed-effect formula, "
 "tail caps, uncertainty estimates, and all model warnings.")

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
 'axes.spines.right':False,'pdf.fonttype':42})
names=[name for name,_ in models]+['primary']
labels=['Security + month','Security + date','Security + market-day',
 'Market-day + sector-month','Principal: prior-session controls']
fig,ax=plt.subplots(figsize=(7.2,3.7)); ys=np.arange(len(names))[::-1]
for y,name in zip(ys,names):
    z=s[name]['sector_date'][X]; crit=stats.t.ppf(.975,s[name]['sectors']-1)
    ax.errorbar(z['Estimate']*100,y,xerr=crit*z['Std. Error']*100,
      fmt='o',color='#14566f',capsize=4,ms=5)
ax.axvline(0,color='0.4',lw=.8); ax.set_yticks(ys,labels)
ax.set_xlabel('Spread basis points per content-index point')
ax.grid(axis='x',alpha=.18); fig.tight_layout()
fig.savefig(SRC/'figures/specification_comparison.pdf'); fig.savefig(SRC/'figures/specification_comparison.png',dpi=200);plt.close(fig)
short={'Oil & Gas Exploration and Production':'Exploration and production',
 'Oil & Gas Refining and Marketing':'Refining and marketing',
 'Oil & Gas Transportation Services':'Transportation services',
 'Oil Related Services and Equipment':'Services and equipment',
 'Renewable Energy Equipment & Services':'Renewable equipment and services'}
only=[(name,lab) for name,lab in leave if name.startswith('omit_')]
fig,ax=plt.subplots(figsize=(7.2,4.5)); ys=np.arange(len(only))[::-1]
for y,(name,lab) in zip(ys,only):
    z=s[name]['sector_date'][X]; crit=stats.t.ppf(.975,s[name]['sectors']-1)
    ax.errorbar(100*z['Estimate'],y,xerr=100*crit*z['Std. Error'],fmt='o',color='#14566f',capsize=3)
ax.axvline(0,color='0.4',lw=.8); ax.axvline(B*100,color='#b15b36',lw=.8,ls='--')
ax.set_yticks(ys,[short.get(lab,lab) for _,lab in only]);ax.set_xlabel('Spread basis points per content-index point')
ax.grid(axis='x',alpha=.18);fig.tight_layout()
fig.savefig(SRC/'figures/leave_sector_out.pdf');fig.savefig(SRC/'figures/leave_sector_out.png',dpi=200);plt.close(fig)

# Human-readable coefficients and an immutable provenance manifest.
flat=[]
for name,m in s.items():
    for term,z in m['sector_date'].items():
        flat.append({'model':name,'term':term,'coefficient':z['Estimate'],'sector_date_se':z['Std. Error'],
          'sector_date_p':z['Pr(>|t|)'],'lower95':z['2.5%'],'upper95':z['97.5%'],'N':m['N']})
pd.DataFrame(flat).to_csv(OUT/'coefficients.csv',index=False)
inputs=[ROOT/'data/PAPER_2_PANEL_energy.parquet',ROOT/'pipeline/work/firmday_misinfo.parquet',
 ROOT/'pipeline/work/firms.parquet',ROOT/'analysis/publication_analysis.py']
inputs.extend(sorted((ROOT/'pipeline/out/post_industry').glob('*.parquet')))
inputs.extend([ROOT/'pipeline/work/post_industry_pairs.parquet',ROOT/'pipeline/work/industry_profile.parquet'])
manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
(OUT/'provenance.json').write_text(json.dumps({'sha256':manifest,'versions':r['run']},indent=2),encoding='utf-8')
print(f'Generated {len(flat)} coefficient rows and manuscript components. Abstract words: {len(abstract.split())}')
