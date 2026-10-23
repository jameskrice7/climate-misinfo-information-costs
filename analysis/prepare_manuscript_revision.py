"""Targeted editorial revision of the attached manuscript using saved estimates.

No financial data are loaded, no model is fitted, and no classification runs.
The attached source, literature review, bibliography and visual assets are the
basis of the document. Numerical edits read the completed analysis JSON only.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'paper/source'
SRC=ROOT/'paper/submission/source'
RESULTS=ROOT/'results/publication/analysis_results.json'

def main():
    saved_hash=hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    s=json.loads(RESULTS.read_text(encoding='utf-8'))['specifications']
    original=(BASE/'main-13.tex').read_text(encoding='utf-8')
    t=original
    changes=[]
    def paragraph(prefix,new):
        nonlocal t
        matches=[p for p in t.split('\n\n') if p.startswith(prefix)]
        if len(matches)!=1: raise ValueError((prefix,len(matches)))
        t=t.replace(matches[0],new.strip(),1); changes.append(prefix)
    def block(start,end,new):
        nonlocal t
        a=t.index(start);b=t.index(end,a)
        t=t[:a]+new.strip()+'\n\n'+t[b:];changes.append(start)
    # Keep the original article class, margins, colour links, APA6 references,
    # theory illustration and integrated appendix.
    t=t.replace('\\author[1]{James Rice}\n\\affil[1]{Department of Government, University of Essex}\n\\date{\\today}',
      '\\ifdefined\\AuthorVersion\n\\author[1]{James Rice}\n\\affil[1]{Department of Government, University of Essex}\n\\else\n\\author{}\n\\fi\n\\date{}')
    abstract=r'''Climate misinformation can alter the information environment in which investors and liquidity providers trade. This paper examines that relationship in a panel of 204 listed climate-transition securities, using sector-specific exposure constructed from 217,954 English-language Facebook climate posts classified against nine energy sub-industries. Greater exposure is positively associated with quoted bid--ask spreads under monthly and local market-day controls. On a common sample of 486,655 security-days, the market-day estimate is $+0.0129$ percentage points per index point ($p=0.033$ under sector/date clustering), a pattern consistent with information-verification costs. The association changes sign and is imprecise after sector-month conditions are absorbed; with prior-session financial controls, the estimate is $-0.0014$ ($p=0.533$). Timing and alternative-outcome checks do not establish an additional robust response. The findings connect the political production of climate misinformation to the trading environment of energy equities while locating the positive spread association in shared sector conditions. The contribution is a sector-sensitive measure and a transparent account of where the liquidity association is observed, rather than a causal estimate of misinformation costs.'''
    a=t.index('\\begin{abstract}'); b=t.index('\\end{abstract}',a)
    t=t[:a]+'\\begin{abstract}\n\n'+abstract+'\n'+t[b:]
    (SRC/'generated/abstract.tex').write_text(abstract+'\n',encoding='utf-8')
    paragraph('The theory distinguishes two causal channels.',r'''The theory distinguishes two competing channels. Under adverse selection, false claims about climate science, carbon policy, and the viability of low-carbon technologies make the implications for fossil-fuel and renewable firms harder to assess. Traders able to verify those claims gain an informational advantage over those who cannot. Liquidity providers then face greater expected losses when trading climate-transition equities with better-informed counterparties and may widen spreads. Under liquidity fragility, viral climate-policy and energy narratives instead draw noise traders into the affected sub-industries, potentially narrowing spreads as the uninformed share rises. H1 tests the narrowing-spread prediction. Section~\ref{sec:theory} develops the mechanisms and distinguishes their theoretical implications from the information available in daily quote data.''')
    paragraph('The empirical analysis uses 726,890',r'''The empirical analysis starts with 726,890 security-day observations on 204 listed climate-transition securities, representing 198 distinct company names, from January 2012 to December 2025. Financial estimation is restricted to the content index's observed window, January 2012--October 2025. The primary outcome is the percent quoted bid--ask spread. The exposure measure is constructed by classifying 217,954 English-language Facebook climate posts from the Meta Content Library against nine TRBC energy sub-industries. Each security inherits its sub-industry's exposure on each date, producing within-day cross-sectional variation while preserving the political and economic content of the posts. Correctly mapped listing-market effects, sector-month controls and prior-session characteristics assess how locally the spread association can be identified.''')
    paragraph('Greater sector-specific misinformation exposure is associated',r'''Greater sector-specific misinformation exposure is positively associated with quoted spreads in the monthly and local market-day specifications. The latter coefficient is $+0.0129$ ($p=0.033$ under sector/date clustering), supporting the view that the climate-information environment and trading costs move together. This positive association is not stable after sector-month conditions are absorbed: on the same sample the coefficient becomes $-0.0033$ ($p=0.117$), and the prior-session-control specification yields $-0.0014$ ($p=0.533$). The evidence therefore identifies a positive association in the broader sector information environment while placing a clear boundary on a daily misinformation-specific interpretation. The null estimates are part of that finding, rather than evidence that climate misinformation is financially irrelevant.''')
    paragraph('The paper makes three contributions.',r'''The paper makes three contributions. First, it extends market-microstructure theory to politically produced climate misinformation and makes the competing adverse-selection and participation predictions explicit. Second, it provides a high-frequency sector-sensitive exposure measure that maps political misinformation to the sub-industries whose values depend on the contested information. Third, it shows that a positive association remains after local market-day conditions are absorbed, while sector-month controls materially change the identifying comparison. Together, these contributions connect the political production of misinformation to the liquidity of climate-transition equities and clarify which part of the relationship the observational evidence supports.''')
    t=t.replace('reports the main estimates, placebo, and robustness checks','reports the main estimates, relevance checks, and robustness comparisons')
    t=t.replace('A wider spread therefore indicates lower market liquidity and greater adverse-selection pressure.',
      'A wider spread indicates lower quoted liquidity and is consistent with greater adverse-selection pressure, although it can also reflect inventory risk and other trading costs.')
    paragraph('The first two pathways are distinguished',r'''The first two pathways imply different signs for the spread response. Adverse selection predicts wider quotes, whereas liquidity fragility predicts narrower quotes alongside weaker capacity to absorb informed trading. H1 therefore states that \emph{higher security-day exposure to sector-specific climate misinformation is associated with narrower percent quoted spreads.} The statistical test uses the sign and precision of the spread coefficient across increasingly local comparisons. The positive coefficient in a baseline specification counts against H1 in that specification; an imprecise coefficient in a more saturated model does not justify a general rejection. The daily VWAP--midquote gap is examined as a complementary price-dispersion measure, but does not measure per-dollar transaction price impact and cannot complete a joint mechanism test.''')
    paragraph('Rolling CAPM beta and Fama--French five-factor excess returns provide',r'''Rolling CAPM beta and Fama--French five-factor excess returns provide benchmark outcomes rather than alternative measures of liquidity (\cite{DeLongShleiferSummersWaldmann1990}; \cite{PastorVeronesi2012}). The climate-finance literature implies that financial responses depend on which climate news and disagreement is relevant to a security (\cite{engle2020hedging}; \cite{bolton2021climate}; \cite{HongLiXu2019}; \cite{pankratz2023climate}). Their interpretation also depends on an appropriate regional factor mapping. The supplied factor-derived outcomes are retained as descriptive diagnostics, with their mapping limitation stated explicitly; they are not used to establish changes in systematic risk or return premia. Liquidity, timing and sector-condition comparisons supply the substantive empirical tests.''')
    paragraph('The unit of analysis is the firm-day.',r'''The unit of analysis is the security-day. The financial input contains 726,890 observations on 204 listed climate-transition securities from January 2012 to December 2025. These securities---fossil-fuel incumbents and renewable challengers---are selected from a broader 19,183,738-security-day universe using nine TRBC energy sub-industries. The financial panel supplies daily quotes, trading characteristics and descriptive risk-and-return variables from Refinitiv Workspace, FRED, the World Bank and the Kenneth French Data Library. The climate-misinformation corpus supplies the 217,954 unique English-language Facebook posts used to construct the exposure measure. The observed index covers 3 January 2012--13 October 2025, and dates outside that support are excluded rather than coded as unexposed. Appendix Tables~\ref{tab:panel_g}--\ref{tab:panel_n} and~\ref{tab:qwen_type} describe the corpus and its classifications. Appendix Tables~\ref{tab:panel_a}--\ref{tab:panel_f} document the supplied financial assembly, while the estimation-sample tables distinguish those inputs from the complete-case regressions. Processing is implemented in Python, following the transparency principles of \textcite{ChristensenMiguel2018}.''')
    paragraph('The financial data come from a firm-level panel',r'''The financial data come from a panel of 204 listed climate-transition securities sourced from Refinitiv Workspace via the Eikon Python API. The sample is defined by membership in nine TRBC energy sub-industries spanning the fossil-fuel value chain (Coal, Integrated Oil \& Gas, Oil \& Gas Drilling, Oil \& Gas Exploration and Production, Oil \& Gas Refining and Marketing, Oil \& Gas Transportation Services, Oil Related Services and Equipment) and the renewable transition (Renewable Energy Equipment \& Services, Renewable Fuels). Actual listing markets include mainland China, Hong Kong, Taiwan, Japan, Indonesia, Malaysia, Brazil, the United States, the United Kingdom, France, Germany and the Netherlands. Security identifiers are kept distinct: multiple share classes and cross-listings do not become independent firms. Daily prices, volume, turnover, capitalization, dividends, bid--ask quotes and VWAP describe the trading environment (\cite{Karpoff1987}; \cite{Parkinson1980}). The percent quoted spread is the bid--ask difference divided by the quote midpoint and expressed in percent. It is the primary liquidity outcome; it does not identify effective execution costs or the private-information component of the spread on its own.''')
    paragraph('One practical concern is timing.',r'''One practical concern is timing. The Shanghai trading day ends before the New York session begins, so a same-date merge can associate posts made after an Asian close with that day's quotes. The timing checks distinguish the previous calendar day from the previous observed session with positive volume and a positive close. Session lags are formed before selecting complete cases on the spread, and source dates outside the corpus window or gaps exceeding ten calendar days are excluded. Static characteristics are merged by security. Listing market is assigned using the exchange suffix of the RIC, separating, for example, Indonesian .JK, Brazilian .SA and Taiwanese .TW listings from US and Japanese markets. The complete market crosswalk accompanies the replication materials. This assignment supplies the local market-day fixed effects, while headquarters country remains a separate characteristic.''')
    paragraph('Macroeconomic controls come from the FRED API',r'''The financial input also contains regional macroeconomic series from FRED and the World Bank: GDP growth, the supplied unemployment-labelled series, and CPI inflation (\cite{FederalReserveBankofStLouis2025}; \cite{WorldBank2025}). These are carried forward from lower-frequency observations (\cite{StockWatson2008}):
\begin{equation}
M_{r,d}=M_{r,q(d)},\qquad q(d)=\max\{q:\mathrm{start}(q)\leq d\}.
\end{equation}
The supplied region groups are not equivalent to actual listing markets. The substantive spread specifications therefore use market-day effects instead of relying on this regional macro mapping. In particular, the unemployment-labelled input is documented without assigning it a structural unemployment interpretation.''')
    t=t.replace('so that each firm-day observation carries the most recent available value (\\cite{StockWatson2008}). The interpolated macro panel merges with the firm-level data on calendar date and region, with full coverage for all three controls.',
      'so that each security-day carries a lower-frequency regional value (\\cite{StockWatson2008}). These supplied series are documented as input characteristics. Because the stored region groups are not equivalent to actual listing markets, the substantive spread specifications use local market-day effects instead of relying on the regional macro mapping. In particular, the unemployment-labelled input is not assigned a structural unemployment interpretation.')
    paragraph('Daily Fama--French five-factor returns',r'''Daily Fama--French five-factor returns---market excess return (MktRF), size (SMB), value (HML), profitability (RMW), and investment (CMA)---are supplied from the Kenneth French Data Library.\footnote{Data available at \url{https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html}.} The input includes regional factors and corresponding risk-free rates. Their descriptive coverage is reported in the appendix. Factor-derived outcomes require a correct association between each security and its relevant market. They are therefore retained as supplied-data benchmarks, with no claim that correcting a fixed-effect market label reconstructs a valid risk-free-rate series or regional factor exposure.''')
    paragraph('The rolling beta is available for',r'''The rolling beta is a slow-moving measure by construction, and thin or non-synchronous trading can bias a conventional OLS beta (\cite{ScholesWilliams1977}; \cite{Dimson1979}). These issues matter alongside market matching: a low estimated beta need not imply low fundamental climate risk. Appendix Table~\ref{tab:beta_region_mktcap} reports supplied betas by stored region group and capitalization quintile as a description of the input. Since those groups do not identify actual listing markets, neither their differences nor the factor-derived regression coefficients establish cross-country differences in systematic risk. The quoted-spread analysis instead uses directly observed quotes and separately assigned market-day effects.''')
    paragraph('The merged climate-transition panel is uniquely indexed',r'''The merged climate-transition panel is uniquely indexed by security and date, with no duplicates. Mainland China and Indonesia contribute the largest security counts, followed by the United States. Appendix Table~\ref{tab:energy_desc_coverage} documents the full financial input; Table~\ref{tab:markets} reports actual listing markets in the 485,800-observation prior-control sample, while the nested contemporaneous-control comparison has 486,655 observations. The prior-control sample contains 202 securities and 197 distinct company names. Missing quotes, nonpositive trading activity and required financial controls determine complete-case coverage. Retaining a long calendar panel does not itself eliminate survivorship or selection concerns.''')
    # Keep original corpus paragraphs and score construction, correcting only
    # development-validation claims, score availability and numerical identities.
    t=t.replace('held-out spot-check','rubric-development spot-check')
    t=t.replace('The classifier was validated on a rubric-development spot-check',
                'The classifier was assessed during rubric development using a spot-check')
    t=t.replace('locally hosted, deterministic classifier whose outputs are reproducible bit-for-bit',
                'locally hosted classifier with fixed decoding settings and persisted outputs')
    t=t.replace('At 1.96 million judgments, the 35-billion-parameter model can distinguish',
                'At 1.96 million judgments, the 35-billion-parameter model is tasked with distinguishing')
    t=t.replace('without the prohibitive runtime cost of repeated ensemble inference.',
                'using one explicit rubric. Independent human annotation remains necessary to quantify classification accuracy.')
    t=t.replace('---each of the 217,954 paired posts judged against each of the nine TRBC energy sub-industries---',
      '---covering the nine TRBC energy sub-industries and 217,954 posts with valid output---')
    t=t.replace('served in 8-bit floating-point precision on a single NVIDIA Grace--Blackwell GB10 system-on-chip running the vLLM 0.21 inference engine.',
                'served in 8-bit floating-point precision using the vLLM 0.21 inference engine.')
    t=t.replace('so each (post, sub-industry) judgment is deterministic, schema-valid, and reproducible',
                'with persisted structured outputs for each (post, sub-industry) judgment')
    t=t.replace('The classification was carried out over approximately ten days of single-GPU runtime, and 398',
                'A total of 398')
    t=t.replace('is correctly classified at $M_{p,s}=0$', 'receives $M_{p,s}=0$')
    t=t.replace('where $P_t$ is the set of climate posts whose Meta-recorded creation date matches calendar date $t$,',
                'where $P_t$ contains the valid scored climate posts for the relevant sector whose Meta-recorded creation date matches calendar date $t$,')
    t=t.replace('a rubric-development spot-check (Section~\\ref{sec:LLM}) rather than a hand-coded gold-standard sample',
                'a rubric-development spot-check (Section~\\ref{sec:LLM}), which informed the rubric and is not an independent held-out or hand-coded gold-standard sample')
    block('\\section{Empirical Strategy}','\\section{Results}',EMPIRICAL)
    block('\\section{Results}','\\section{Discussion}',RESULTS_TEXT)
    block('\\section{Discussion}','\\printbibliography',DISCUSSION)
    # Appendices retain the supplied literature, corpus tables, network figures
    # and original layout. Stored groups are labelled as such rather than countries.
    t=t.replace('Section~\\ref{sec:firmday_validation} describes and validates the firm-day exposure index',
                'Section~\\ref{sec:firmday_validation} describes the exposure index and rubric-development checks')
    t=t.replace('The equity universe spans five geographic regions with heterogeneous market structures and data availability.',
      'The supplied equity assembly uses five stored region groups. These are input labels, not a validated listing-market classification; the spread analysis uses the exchange-based crosswalk instead.')
    t=t.replace('Coverage by region. Share\\%', 'Coverage by stored region group. Share\\%')
    t=t.replace('China contributes the largest share of observations (41.2\\%), followed by the United States (31.7\\%) and Japan (23.8\\%), while the UK and EU together account for approximately 3.4\\% of the sample.',
      'The stored CN group contributes 41.2\\% of input observations, the US group 31.7\\% and the JP group 23.8\\%; UK and EU groups account for the remainder. These percentages describe the supplied grouping, not corrected listing-market shares.')
    t=t.replace('The percent quoted spread and price impact are the liquidity outcomes used in the main analysis.',
      'The percent quoted spread is the main liquidity outcome. PriceImpact is a supplied field name for the absolute VWAP--midpoint percentage gap, not transaction price impact.')
    t=t.replace('include the percent quoted spread and per-dollar price impact used as the primary and companion liquidity outcomes.',
      'include the percent quoted spread used as the primary liquidity outcome and supplied daily price-gap fields.')
    t=t.replace('buyer- and seller-initiated trade indicators, volume-weighted average price (VWAP), and price impact.',
      'supplied buyer/seller indicators, volume-weighted average price (VWAP), and the absolute VWAP--midpoint percentage gap. Source field names do not identify signed order-flow quantities or per-dollar transaction impact.')
    t=t.replace('Composition by Region (Unique Firms)', 'Composition by Stored Region Group (Unique Securities)')
    t=t.replace('Unique firms (RICs)', 'Unique securities (RICs)')
    t=t.replace('Unique firms &', 'Unique securities &')
    t=t.replace('Shares are calculated over the 204 unique firms in the climate-transition sample.',
      'Shares describe the supplied region groups for 204 securities, not actual listing markets. The market crosswalk and corrected market composition are reported separately.')
    t=t.replace('The constant RIC count of 5,375 per year confirms a balanced panel structure,',
      'The constant RIC count of 5,375 per year describes the supplied calendar grid, rather than demonstrating a survivor-bias-free investment universe,')
    t=t.replace('composition is concentrated in US and Chinese firms, making firm-level fixed effects and clustered inference essential.',
      'actual listing composition is concentrated in mainland China and Indonesia, making local market-day effects and inference at the sector assignment level important.')
    t=t.replace('Coverage statistics for the climate-transition panel used in the fixed-effects regressions.',
      'Coverage statistics for the full financial input, before the content-window, quote, trading and complete-case filters. These are not regression sample sizes.')
    t=t.replace('USD (thousands)', 'source currency')
    t=t.replace('& USD &', '& source currency &')
    t=t.replace('Unemployment & \\%', 'Stored unemployment series & \\%')
    t=t.replace('unemployment & 726,890', 'unemployment (stored) & 726,890')
    t=t.replace('The within-year movement reflects climate-political intensity rather than raw volume:',
      'The within-year movement is not proportional to raw post volume:')
    t=t.replace('Two further facts about the Qwen-classified corpus motivate the engagement-weighting logic used in the main text.',
      'Two further facts about the supplied corpus summaries motivate distinguishing the amount of content from its engagement. The financial index itself is not engagement-weighted.')
    t=t.replace('the held-out spot-check that fixed the classification rubric',
                'the rubric-development spot-check that informed the classification rubric')
    t=t.replace('the rubric-development spot-check used to validate\nthe classifier',
                'the rubric-development spot-check used to assess\nthe classifier')
    a=t.index('\\subsection{Within-Classifier Placebo}')
    b=t.index('\\FloatBarrier\n\\section{Heterogeneity',a)
    t=t[:a]+APPENDIX_PLACEBO+'\n\n'+t[b:]
    a=t.index('\\section{Heterogeneity and Interaction Checks}')
    b=t.index('\\FloatBarrier\n\\section{Summary}',a)
    t=t[:a]+APPENDIX_HETEROGENEITY+'\n\n'+t[b:]
    # Add the completed diagnostics to the integrated appendix without replacing
    # its existing corpus and financial description.
    where=t.index('\\FloatBarrier\n\\section{Summary}')
    t=t[:where]+r'''\FloatBarrier
\section{Additional Specification and Inference Checks}
\label{sec:appendix_robustness}
\input{tables/inference.tex}
\input{tables/variants.tex}
\input{tables/sensitivity.tex}
\input{tables/controls.tex}
The nine-sector structure motivates comparing sector/date clustering with date-score HAC and the sector score-sign diagnostic. Their assumptions and finite-sample limits are set out in the supplementary material. The full set of completed coefficient estimates is retained, including numerical warnings. In the attention-adjusted model the post-volume control has an undefined sector/date standard error; the exposure coefficient and all coefficients in the fully conditional model have finite reported uncertainty. The absence of a robust positive coefficient in the saturated models limits an independent daily misinformation interpretation without erasing the positive broader association documented in the main text.

'''+t[where:]
    # The corrected market/sample tables supplement the original assembly
    # summaries instead of replacing the appendix with a new document.
    where=t.index('\\section{Descriptive Statistics and Supporting Tables}')
    t=t[:where]+r'''\input{tables/markets.tex}
\input{tables/sample_flow.tex}
\FloatBarrier
'''+t[where:]
    paragraph('The financial and exposure sections document the breadth',r'''The financial and exposure sections document coverage, composition and the construction of the exposure index: its distributional properties, the rubric-development spot-check, and the distinction between content availability and observed investor attention. The conditional-mean decomposition explains why relevance subsets need not reproduce the all-post association, while the empirical checks distinguish market-day conditions from sector-month conditions. Read together, the appendix connects the competing-liquidity framework in Section~\ref{sec:theory} to the positive associations and their empirical boundaries in Section~\ref{sec:results}.''')
    # Ethics, data scope and AI disclosure are journal declarations, with no
    # discussion of document history or local hardware in the manuscript.
    where=t.index('\\printbibliography')
    t=t[:where]+DECLARATIONS+'\n\n'+t[where:]
    t='\n'.join(line.rstrip() for line in t.splitlines()).rstrip()+'\n'
    (SRC/'main.tex').write_text(t,encoding='utf-8')
    bibliography=(BASE/'references.bib').read_text(encoding='utf-8')
    modern=(SRC/'references.bib').read_text(encoding='utf-8')
    # Explicitly add only references used for the inference extension.
    for key in ['Petersen2009','CameronMiller2015','MacKinnonNielsenWebb2023']:
        if not re.search(r'@\w+\{'+key+r',',bibliography):
            entries=list(re.finditer(r'(?m)^@\w+\{([^,]+),',modern))
            for i,m in enumerate(entries):
                if m.group(1)==key:
                    bibliography+='\n\n'+modern[m.start():entries[i+1].start() if i+1<len(entries) else len(modern)].strip()
    # Bibliography was restored from the attachment on the first execution;
    # stable additions below also make repeated editorial builds deterministic.
    for key,entry in MODERN_REFERENCES.items():
        if key not in bibliography: bibliography+='\n\n'+entry
    bibliography='\n'.join(line.rstrip() for line in bibliography.splitlines()).rstrip()+'\n'
    (SRC/'references.bib').write_text(bibliography,encoding='utf-8')
    write_empirical_tables(s)
    q=(BASE/'tables/tab_v2_descriptive.tex').read_text(encoding='utf-8')
    q=q.replace('misinformation-exposure IV','misinformation-exposure index')
    q=q.replace('\\begin{tabular}{l r r r r r r}',
      r'\footnotesize\setlength{\tabcolsep}{3pt}\begin{tabular}{p{0.39\textwidth}rrrrrr}',1)
    (SRC/'tables/tab_v2_descriptive.tex').write_text(q,encoding='utf-8')
    # Restore all original figure assets and non-regression table fragments.
    for folder in ['figures','tables']:
        for file in (BASE/folder).glob('*'):
            target=SRC/folder/file.name
            if not target.exists():shutil.copy2(file,target)
    lit=lambda q:q[q.index('\\section{Literature Review}'):q.index('\\section{Theory:')]
    citations=lambda q:set(k.strip() for v in re.findall(r'\\(?:cite|textcite|parencite)\{([^}]+)\}',q) for k in v.split(','))
    body=lambda q:q.split('\\appendix')[0]
    report={'analysis_rerun':False,'saved_results_sha256_before':saved_hash,
      'saved_results_sha256_after':hashlib.sha256(RESULTS.read_bytes()).hexdigest(),
      'literature_review_unchanged':lit(original)==lit(t),
      'original_body_words':len(body(original).split()),'revised_body_words':len(body(t).split()),
      'original_total_words':len(original.split()),'revised_total_words':len(t.split()),
      'original_cited_works':len(citations(original)),'revised_cited_works':len(citations(t)),
      'omitted_citation_keys':sorted(citations(original)-citations(t)),
      'targeted_paragraphs_and_blocks':changes}
    assert report['saved_results_sha256_before']==report['saved_results_sha256_after']
    assert report['literature_review_unchanged']
    (ROOT/'paper/submission/editorial_revision_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='targeted_paragraphs_and_blocks'},indent=2))

EMPIRICAL=r'''\section{Empirical Strategy}
\label{sec:model}

The empirical strategy separates the main quoted-liquidity design from benchmark risk-and-return diagnostics. The baseline tests the spread prediction using within-security changes in the sector-specific misinformation index. A nested comparison then introduces daily and local market-day effects, followed by sector-month effects. These comparisons make the identifying variation explicit rather than allowing a change in sample to explain a coefficient difference. The factor-derived diagnostics remain secondary because the supplied regional mapping limits their financial interpretation.

\subsection{Design 1: Market Liquidity}
The baseline spread specification is:
\begin{equation}
\text{SpreadPercent}_{i,t}=\beta_1\mathrm{Exp}^{\mathrm{mean}}_{i,t}+\boldsymbol\gamma'\mathbf X_{i,t}+\alpha_i+\delta_{q(t)}+\varepsilon_{i,t}.
\label{eq:spread_reg}
\end{equation}
Here $\mathbf X_{i,t}$ contains log one plus trading volume, log market capitalization and the daily high--low price range divided by the closing price and expressed in percent. $\alpha_i$ denotes security fixed effects and $\delta_{q(t)}$ year-month effects. All logged variables are natural logarithms. Continuous financial controls and outcomes are winsorized at the first and ninety-ninth percentiles; exposure scores are not winsorized. The quoted spread is reconstructed as $200(A-B)/(A+B)$, where $A$ and $B$ are the daily ask and bid. Positive bid, non-crossed positive spread, positive volume and positive close are required.

The nested comparison replaces year-month effects first with calendar-date effects and then with listing-market-by-date effects. The latter absorb daily news, trading conditions and other shocks shared by securities in the same local market. All four contemporaneous-control specifications use the same 486,655 observations, controls and tail caps. The final nested specification adds sub-industry-by-month effects, separating daily exposure variation from the monthly information and valuation environment of the sector:
\begin{equation}
\text{SpreadPercent}_{i,t}=\beta_1\mathrm{Exp}^{\mathrm{mean}}_{i,t}+\boldsymbol\gamma'\mathbf X_{i,t}+\alpha_i+\lambda_{m(i),t}+\mu_{s(i),q(t)}+\varepsilon_{i,t}.
\label{eq:saturated}
\end{equation}
The fully conditional model additionally replaces contemporaneous financial controls with their values at the previous observed active trading session, denoted $\mathbf X_{i,t^-}$. This comparison uses 485,800 observations. It reduces direct conditioning on current trading activity, which may itself respond to the information environment, but does not make exposure exogenous. Its different control timing is shown separately from the common-sample nested comparison.

The companion price-dispersion outcome is $100|\mathrm{VWAP}_{i,t}-\mathrm{MidPrice}_{i,t}|/\mathrm{MidPrice}_{i,t}$. The supplied fields called OrderFlow and PriceImpact equal the signed VWAP--midpoint difference and its absolute percentage transformation. These identities do not recover signed traded quantities or per-dollar transaction price impact. The gap regression therefore describes another aspect of prices without identifying the information content of a trade. Variant regressors separate composite exposure, its volume transformation, average misinformation, average relevance and positive-content frequency.

\subsection{Design 2: Benchmark Risk and Return Outcomes}
\subsubsection{Model II: Rolling CAPM Beta}
The systematic-risk benchmark relates the supplied rolling CAPM beta to exposure:
\begin{equation}
\hat\beta_{i,t}=\lambda\mathrm{Exp}^{\mathrm{mean}}_{i,t}+\boldsymbol\gamma'\mathbf X_{i,t}+\alpha_i+\delta_{q(t)}+\varepsilon_{i,t}.
\label{eq:beta_misinfo}
\end{equation}
The beta is computed over 252 trading observations with at least 126 observations per window. In principle, $\lambda$ asks whether information conditions co-move with the security's covariance with a relevant market factor. In the supplied input, the regional factor assignment is not equivalent to the corrected listing-market crosswalk. Accordingly, the saved estimates are descriptive diagnostics and cannot identify a climate-misinformation response in correctly matched systematic risk. Their null findings are retained without treating them as proof of unchanged fundamental risk.

\subsubsection{Model III: Augmented Fama--French Five-Factor Model}
The Fama--French benchmark decomposes excess returns as:
\begin{equation}
R^e_{i,t}=\beta_{m,i}\mathrm{MktRF}_t+\beta_{s,i}\mathrm{SMB}_t+\beta_{v,i}\mathrm{HML}_t+\beta_{p,i}\mathrm{RMW}_t+\beta_{c,i}\mathrm{CMA}_t+\varepsilon_{i,t}.
\label{eq:ff5}
\end{equation}
The augmented specification introduces the exposure index:
\begin{equation}
R^e_{i,t}=\sum_k\beta_kF_{k,t}+\phi\mathrm{Exp}^{\mathrm{mean}}_{i,t}+\boldsymbol\gamma'\mathbf X_{i,t}+\alpha_i+\delta_{q(t)}+\varepsilon_{i,t}.
\label{eq:ff5_aug}
\end{equation}
The factors capture market excess return, size, value, profitability and investment (\cite{fama1993}; \cite{fama2015}). A coefficient on exposure in this regression is a conditional return association, not by itself a test that misinformation is a priced risk factor. The supplied factor mapping imposes the same diagnostic limitation as Model II. These benchmarks retain their role in distinguishing the research question about trading conditions from a claim about expected-return premia.

\subsection{Identification Strategy}
Identification in the baseline rests on within-security, within-month variation. Security effects absorb time-invariant characteristics, including sub-industry, listing market and stable disclosure differences. Month effects absorb shocks common to that calendar month. The sector-specific exposure construction also supplies cross-sectional variation within a date. That variation permits market-day fixed effects without absorbing the index completely. Sector-day effects would absorb it, since securities in the same sector and date inherit the same value. The index therefore makes a local comparison feasible while also defining the limit of what the panel identifies.

Sector-month effects change the economic comparison rather than simply adding another precision adjustment. Without them, the coefficient can reflect a sector's sustained information and valuation conditions within the month. With them, it is identified from more transitory deviations in that environment. A change in the coefficient can arise because those controls remove confounding sector conditions or absorb a persistent information channel. The observational data do not distinguish these explanations. The positive broader association and the null saturated association must therefore be reported together.

Inference reflects assignment at the sub-industry/day level. Standard errors cluster by sub-industry and calendar date, allowing dependence among different securities in a sector over time and among sectors on a date (\cite{Moulton1990}; \cite{Petersen2009}). With nine sector clusters, $t_8$ reference probabilities and confidence intervals are approximate (\cite{CameronMiller2015}; \cite{MacKinnonNielsenWebb2023}). Security/date clustering is reported alongside it. Date-score HAC with bandwidths of 5, 20 and 60 observed dates and an enumerated sector score-sign sensitivity provide additional reference calculations; the latter requires independent symmetric sector scores and is not exact randomization inference (\cite{DriscollKraay1998}). Full definitions appear in the supplement.

The main limitation is that no exogenous shock separates exposure from daily sector-specific news, policy developments or changing investor beliefs. Lagging content improves the description of temporal ordering but does not remove persistent confounding. A future-content lead is informative about timing specificity without constituting a causal test. Relevance subsets similarly assess measurement composition, rather than supplying an externally validated placebo. The analysis uses these distinctions to establish where the positive spread association is supported and where it remains unresolved.'''

RESULTS_TEXT=r'''\section{Results}
\label{sec:results}

The results connect sector-specific climate misinformation to quoted trading conditions in the climate-transition sample. The central positive finding is that the association with wider spreads survives local market-day controls. The next comparison establishes its boundary: adding sector-month effects changes the sign and leaves an imprecise coefficient. Both findings are reported in Table~\ref{tab:v2_core}, using the completed estimates and pyfixest 0.40.1. The nested contemporaneous-control models share a sample, so the coefficient change cannot be attributed to changing observations or tail caps.

\input{tables/tab_v2_core.tex}

\subsection{Model I: Misinformation and Quoted Spreads (H1)}
\label{sec:results_modelI}

Greater sector-relevant climate misinformation is positively associated with quoted spreads under security/month effects ($+0.0041$, sector/date $p=0.073$). The sign remains positive with date effects ($+0.0145$, $p=0.102$) and with correctly mapped local market-day effects ($+0.0129$, $p=0.033$). The latter result is especially informative for the question posed by the paper: securities with different sector content scores face different quoted trading conditions even after their shared local trading environment is absorbed. It is a conditional association rather than an identified effect, but it shows that the positive pattern is not confined to a specification that leaves all daily market-wide movements uncontrolled.

\input{tables/tab_v2_full_modelI.tex}

The financial control coefficients are consistent with familiar liquidity relationships. In the market-day model, log trading volume is negatively associated with spreads ($-0.2952$, $p<0.001$), capitalization also enters negatively ($-0.0941$, $p=0.040$), and the daily price range enters positively ($+0.0676$, $p<0.001$). More active trading and larger capitalization are associated with tighter quotes, while a larger range is associated with higher trading costs (\cite{stoll2000friction}; \cite{chordia2000commonality}; \cite{AmihudMendelson1986}). These are partial associations and do not isolate inventory costs or the private-information content of order flow (\cite{Kyle1985}; \cite{easley1996}; \cite{Hasbrouck1991}). The result supports using the spread as a direct description of quoted liquidity while keeping its components conceptually distinct.

Sector-month controls materially qualify the exposure result. On the same 486,655 observations, the content coefficient becomes $-0.0033$ ($p=0.117$). The fully conditional model with prior-session controls yields $-0.00143$, sector/date standard error $0.00220$, $p=0.533$, and an approximate 95\% interval of $[-0.00650,0.00364]$. It uses 485,800 observations on 202 securities from 197 distinct company names. These estimates do not establish an independent daily spread-widening response within the sector's monthly environment. Equally, they do not establish that the broader positive association is spurious: the sector-month effect can absorb sustained information conditions as well as confounding valuation changes. The empirical finding is a distinction between those two comparisons, not a choice to suppress one of them.

The economic scale is modest. The fully conditional sample's content standard deviation is $0.710$, and its winsorized mean spread is $0.473\%$, or 47.29 basis points. Scaling the fully conditional coefficient by that content standard deviation gives $-0.102$ basis points, with an approximate interval of $[-0.462,0.258]$. This scaling describes a fitted association; it is not the consequence of exposing an investor to misinformation. The index's standard deviation after residualizing the controls and fixed effects is $0.297$, showing that the local comparison retains measurable content variation even though it yields an imprecise coefficient.

For H1, the positive monthly and market-day coefficients run against the narrower-spread prediction and are compatible with the adverse-selection account in Section~\ref{sec:theory} (\cite{GlostenMilgrom1985}; \cite{EasleyOHara1992}). The saturated estimates do not justify a general rejection of H1 or a definitive selection of adverse selection over participation. This distinction preserves the substantive positive result without claiming that a quoted-spread regression alone identifies why liquidity suppliers change their quotes.

\subsubsection{Complementary Price Dispersion}
\label{sec:results_priceimpact}
The companion outcome is the absolute VWAP--midquote gap in percent, rather than per-dollar transaction price impact. Its exposure coefficient under the fully conditional specification is $+0.00105$ ($p=0.760$; $N=485{,}798$). The estimate supplies no separate statistically discernible gap response. Its positive point estimate is compatible with several information and trading-cost mechanisms but cannot identify adverse selection. No inference about market depth or the response of prices to a dollar of signed trading is drawn from this variable.

This measurement distinction matters to interpreting the theoretical argument. Quoted spreads describe the prices posted by liquidity suppliers; the daily VWAP gap describes the relation between a trade-price average and a quote midpoint. Neither its sampling time nor an individual order's direction is identified here. The two measures can be reported together as descriptions of the trading environment, but do not constitute the spread/transaction-impact test required to separate the mechanisms uniquely. The null gap finding is therefore retained as a limit on mechanism evidence, not recast as support for either channel.

\subsubsection{Lag Specification}
\label{sec:results_lag}
Table~\ref{tab:timing} compares contemporaneous exposure, the previous observed active session, the exact previous calendar day, and the next active session on a common sample of 388,227 observations. The session-grid construction retains the distinction between a Friday-to-Monday transition and an exact calendar-day join. No session lag is formed across a source date outside the content window or a gap exceeding ten calendar days.

\input{tables/timing.tex}

In the common sample, current exposure has coefficient $+0.0001$ ($p=0.962$), previous-session exposure $-0.0016$ ($p=0.468$), and previous-calendar-day exposure $-0.0017$ ($p=0.330$). The next-session lead is positive but imprecise ($+0.0078$, $p=0.135$). On the larger available session-lag sample of 485,759 observations the coefficient is $-0.0010$ ($p=0.652$). These checks do not establish an additional delayed widening response after local market-day and sector-month conditions are absorbed. They retain temporal information without equating a lag with causal ordering. Serially correlated content and sector news can influence both leads and lags.

\subsubsection{Sector Relevance and Content Composition}
\label{sec:results_placebo}
The climate-specific question requires distinguishing sector relevance from the misinformation component of content. The completed sensitivity estimates report the composite, log content sum, misinformation score, relevance score, positive-content indicator and the share scoring at least 25 on misinformation. Under the fully conditional specification, none establishes a positive spread association at conventional levels. Adding log post count and mean relevance jointly leaves the composite coefficient small and imprecise ($-0.0013$, $p=0.591$). Table~\ref{tab:variants} in the appendix reports these findings without selecting a preferred content measure by its probability value.

A relevance-threshold subset changes both the posts entering an average and its denominator. For a high-relevance share $q$ and conditional mean $\bar e^H$, its contribution to the all-post mean is $q\bar e^H$. A conditional-mean regression can therefore have a different sign from an all-post regression without an algebraic contradiction. If no post qualifies, the conditional mean is undefined even though its contribution is zero. Appendix~\ref{sec:firmday_validation} explains this distinction. The distributed inputs do not contain the post-ID/date crosswalk needed to reconstruct those thresholded daily series, so no unregenerated irrelevant-content placebo is used to claim specificity.

\subsubsection{Subperiod Stability}
\label{sec:results_subperiod}
The corpus becomes substantially larger after 2019, while measured exposure diverges across fossil-fuel and renewable sub-industries. Figure~\ref{fig:v2_exposure_by_industry} documents that distributional pattern. It is substantively relevant to the information conditions facing energy securities: contested claims do not apply uniformly across technologies, operations or policy exposures. It motivates keeping the sector dimension in the content measure and in the econometric comparison.

The formal post-2019 slope interaction in the fully conditional model is $-0.0019$ ($p=0.687$). The data therefore do not establish that the spread association strengthened after 2019 once market-day and sector-month conditions are accounted for. A change in corpus scale can affect composition and measurement precision without implying a changed financial response. The positive result under broader controls and the distributional divergence across sectors are accordingly reported as different findings, not treated as interchangeable evidence for a stronger post-2019 mechanism.

\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/fig_v2_exposure_by_industry.png}
\caption{Mean measured exposure by climate-transition sub-industry (60-day moving average). Fossil-fuel and renewable sub-industries exhibit different content patterns. This distributional contrast does not itself establish a difference in spread-response coefficients.}
\label{fig:v2_exposure_by_industry}
\end{figure}

\subsection{Model II: Misinformation and Systematic Risk (CAPM Beta)}
\label{sec:results_modelII}
The saved factor-derived diagnostic has a small, imprecise coefficient on mean exposure ($-0.0007$, security/date $p=0.53$, $N=384{,}017$). The log content-sum and misinformation-score variants are also imprecise. Table~\ref{tab:v2_full_modelII} retains the full diagnostic readout so that the risk benchmark is transparent. The input's regional factor mapping is not equivalent to actual listing markets, however, and these coefficients are not presented as validated cross-market estimates of systematic risk. A null diagnostic cannot establish that misinformation leaves correctly measured covariance risk unchanged.

\input{tables/tab_v2_full_modelII.tex}

The distinction is consistent with the different time scales involved. A rolling 252-observation beta changes slowly, whereas the content index and quoted spreads vary daily. Volume, size, dividends, volatility and economic conditions can affect a rolling estimate in ways that differ from their association with a daily quote (\cite{StockWatson2002}; \cite{BakerBloomDavis2016}). The benchmark therefore helps define the scope of the paper: the positive evidence concerns quoted trading conditions under specified controls, rather than a general finding about changes in market risk.

\subsection{Model III: Fama--French Excess Returns}
\label{sec:results_modelIII}
The supplied excess-return diagnostic is negative for mean exposure ($-0.0224$) but loses precision when security and date are both clustered ($p=0.151$, $N=382{,}890$). Firm-only clustering produces a smaller standard error without changing the coefficient. Table~\ref{tab:v2_full_modelIII} retains this comparison. The probability-value difference illustrates why date-level dependence matters; it does not establish a return effect. The supplied regional factor and risk-free-rate mapping further limits a cross-market excess-return interpretation.

\input{tables/tab_v2_full_modelIII.tex}

The benchmark provides no independent return-pricing claim. More generally, a daily content coefficient added to a factor regression need not identify a priced risk factor, and an insignificant coefficient need not imply that information quality has no valuation consequences. Keeping risk, returns and quoted liquidity conceptually separate allows the positive spread association to be stated directly, while leaving the corresponding null and imprecise results visible.'''

DISCUSSION=r'''\section{Discussion}
\label{sec:discussion}

The findings support a substantive connection between the climate-information environment and quoted liquidity in energy equities. In the local market-day specification, a higher sector-relevant misinformation score is associated with wider quoted spreads. This is the direction predicted when traders differ in their ability to verify climate claims and liquidity suppliers face greater information risk. The positive estimate remains after shared local trading conditions are absorbed, giving the result more substance than an uncontrolled correlation between social-media activity and financial markets. Its interpretation is an association within a specified comparison, rather than a causal cost estimate.

The theoretical contribution is to bring politically produced misinformation into a framework usually applied to the distribution of financial information. Claims about climate science, carbon restrictions, subsidies or the viability of low-carbon technologies can be costly to verify. Investors with more expertise or better access to credible information may interpret those claims differently, giving liquidity providers a reason to adjust quotes (\cite{GlostenMilgrom1985}; \cite{GrossmanStiglitz1980}; \cite{GoldsteinYang2017}). The data are consistent with that account under monthly and market-day controls. They do not observe a trader's verification decision, investor sophistication or order direction, so they do not identify that mechanism uniquely. Maintaining the distinction between a theoretical channel and its directly observed implications strengthens the contribution.

Sector-month controls locate the limit of the evidence. After those conditions are absorbed, the coefficient changes sign and is imprecise, both with contemporaneous and prior-session financial controls. This does not support a stable independent daily widening response. It also changes the economic object being estimated: shared monthly sector conditions may include genuine information-verification pressures alongside commodity-price changes, policy news and valuation uncertainty. Removing that component is a demanding local comparison, not a demonstration that the remaining coefficient alone measures the total information costs of climate misinformation. The paper therefore reports the positive broader association and the null local association together. Neither can substitute for a design that separates exogenous misinformation from the news environment in which it circulates.

The political-economy implication is most direct at the sub-industry level. Fossil-fuel chains and renewable technologies face different claims about demand, regulation and technological feasibility. A coal-security trader and a renewable-fuels trader can therefore face different relevant narratives on the same date. The sector-sensitive measure represents that distinction rather than assigning every security the same daily content value. The observed fossil--renewable exposure divergence is informative about the distribution of contested content, even though the formal post-2019 interaction does not establish a stronger liquidity response. This is a measurement contribution with substantive content, rather than merely a choice of regression fixed effects.

The wider literature gives that distinction practical significance. Misinformation can affect beliefs, trust and collective action, while energy investment depends on expectations about policy and technology (\cite{cobb2025politics}; \cite{farrell2016network}; \cite{engle2020hedging}; \cite{bolton2021climate}). A liquid secondary market can matter to financial conditions surrounding the transition, but this paper does not observe the cost of financing a new project or an issuer's investment decision. The evidence speaks to posted trading terms in listed equities. Connecting those terms to primary financing or real investment would require additional data and an identified transmission mechanism. The market-liquidity contribution is useful on its own without making that additional claim.

The corpus also highlights why the supply of misinformation and its audience should be kept distinct. The reach-based arguments of \textcite{acemoglu2010spread} and \textcite{VosoughiRoyAral2018} motivate attention to diffusion, but the daily index averages classified content without weighting it by observed investor exposure. The supplied engagement and owner-network summaries document a heavy-tailed public information environment; they do not show which investors saw a post. Likewise, volume and relevance variants do not establish a positive coefficient in the fully conditional model. The appropriate interpretation is that sector-sensitive content captures a plausible information environment whose financial association depends on the comparison, not that a high post score constitutes a measured dose of investor misinformation.

Three limitations remain particularly relevant. First, the English-language, keyword-selected corpus has uneven geographic and temporal coverage. This matters in markets such as mainland China and Indonesia, which account for many sample securities, and cannot be solved by relabelling the content as globally representative. Second, rubric-development checks helped define the classifier but do not supply independent precision, recall or human agreement. The content measure is reproducible from persisted scores, while its external accuracy remains a separate empirical question (\cite{grimmer2022text}; \cite{gilardi2023chatgpt}). Third, nine sector-level information series limit cluster-based inference despite the large number of security-day rows. The alternative covariance and leave-out checks describe that uncertainty transparently instead of treating sample size as independent information.

For research on the political economy of climate finance, these results provide a clear basis for further work. Sector-specific classification retains the political and economic content needed for a meaningful market comparison. Correctly assigned market-day effects establish that the positive association is not simply a common local-market movement. Sector-month controls then show that the evidence does not isolate an additional daily misinformation response. Those are complementary findings. An event study or instrument grounded in a defensible information shock, together with local-close timestamps and direct investor-flow data, would be needed to distinguish persistent information conditions from a causal trading-cost effect.

\section{Conclusions}
\label{sec:conclusion}

Climate misinformation is associated with wider quoted spreads in the monthly and local market-day specifications for climate-transition equities. The positive local market-day estimate establishes a connection between sector-relevant climate content and trading conditions after shared local daily shocks are absorbed. The finding is consistent with information-verification costs and supports bringing the political production of climate misinformation into research on market liquidity. Its empirical boundary is equally clear: adding sector-month controls changes the sign and leaves an imprecise coefficient, including in the model with prior-session financial controls.

Four conclusions follow. First, the construction of the content measure matters. Classifying posts separately against nine energy sub-industries preserves differences in the political information relevant to fossil-fuel and renewable securities. The resulting within-date variation makes a local market-day comparison possible. It does not create independent treatment at the level of each security, and inference must respect the sector assignment.

Second, the positive spread association is conditional on the sector comparison. It is statistically discernible under local market-day effects but does not persist as a robust positive coefficient after sector-month conditions are removed. The evidence therefore supports an association in the broader sector information environment while leaving a distinct daily causal response unresolved. The null result narrows the claim without requiring that climate misinformation be considered economically unimportant.

Third, the complementary VWAP-gap and timing checks provide no separate robust response under the fully conditional design. The gap is not per-dollar transaction price impact, and a lag is not an exogenous information shock. The risk and excess-return diagnostics are also inconclusive and constrained by their supplied factor mapping. They are retained as boundaries on the financial interpretation rather than used to amplify the main result.

Fourth, the corpus and sub-industry profiles document an uneven climate-information environment. The increase in content volume after 2019 and the fossil--renewable exposure divergence motivate sector-sensitive measurement, but the formal slope interaction does not establish a strengthened spread relationship. This distinction keeps a substantive distributional finding separate from a claim about changing financial sensitivity.

The paper contributes a sector-sensitive bridge between the political production of climate misinformation and the quoted trading environment of energy equities. Future work can build on that bridge through independent multilingual validation, exchange-local information timing, defensible exogenous events and direct measures of investor participation. Applying the same construction to other domains of politically contested knowledge---public health, technology and financial regulation---would also test how broadly the relationship extends (\cite{lins2017social}; \cite{taber2006motivated}). The present evidence establishes where the positive liquidity association is observed and states clearly where the data do not support a stronger claim.'''

APPENDIX_PLACEBO=r'''\subsection{Within-Classifier Relevance Checks}
The natural relevance check compares highly sector-relevant posts with those assigned a low relevance score. A high-relevance conditional mean and its contribution to the all-post mean are different regressors. If $H_p=1\{R_{p,s}\geq c\}$, $q^H$ is the qualifying-post share and $\bar e^H$ its mean exposure, then $C^H=q^H\bar e^H$ and $E=C^H+C^L$. This decomposition permits different coefficient signs without an algebraic contradiction. It does not establish the empirical cause of a difference. An empty qualifying subset has an undefined conditional mean, whereas its all-post contribution is zero.

The fixed score files and saved daily index are available, but the internal post-ID/date crosswalk required to reaggregate thresholded daily subsets is not distributed. The supplied aggregation code preserves missing conditional means, reports common-denominator contributions at four relevance thresholds and fails explicitly if the crosswalk is absent. No irrelevant-post placebo is treated as newly reproduced support for specificity. The completed mean-relevance, misinformation-score, positive-content and volume-adjusted regressions are reported in Table~\ref{tab:variants}; these remain internal measurement checks, not independent validation of classifier accuracy.'''

APPENDIX_HETEROGENEITY=r'''\section{Heterogeneity and Interaction Checks}
\label{sec:appendix_heterogeneity}
\subsection{Sector and Listing-Market Sensitivity}
\label{sec:results_signflip}
The leave-out comparisons retain the fully conditional model and the full sample's tail caps while omitting each energy sub-industry in turn. Table~\ref{tab:leaveout} also reports omission of the three largest listing markets. This assesses whether a particular sector or market supplies the fitted association without changing financial tail treatment within every subsample. All use the completed saved estimates.
\input{tables/leaveout.tex}
Across sector omissions, coefficients range from approximately $-0.0028$ to $0.0000$. The intervals remain imprecise, and the table does not establish a robust positive coefficient under the fully conditional design. These checks identify the scope of that null result, rather than overwrite the positive association under broader controls. Figure~\ref{fig:leaveout} displays the sector comparisons.
\begin{figure}[htbp]\centering
\includegraphics[width=\linewidth]{figures/leave_sector_out.pdf}
\caption{Exposure coefficients after omitting one sector at a time, using the fully conditional model and fixed full-sample tail caps. Bars are approximate 95\% sector/date-clustered intervals, with seven reference degrees of freedom.}
\label{fig:leaveout}\end{figure}
\subsection{Temporal Interaction}
\label{sec:results_triple}
The completed temporal check interacts the exposure index with a post-2019 indicator while retaining security, market-day and sector-month effects and prior-session financial controls. The interaction is $-0.0019$ with $p=0.687$. This directly tests a slope difference. It does not show a strengthened spread association after 2019, even though the amount and sector distribution of classified content change. Stored region-group interactions are not interpreted as language-market effects because the input groups do not map cleanly to actual listing markets.'''

DECLARATIONS=r'''\section*{Ethics and data availability}
The source research received institutional ethics approval for the Meta Content Library analysis. The replication materials supply the financial analysis, fixed classifications, saved estimates, source tables and figure assets. Raw Meta Content Library records and post text are access-controlled; financial observations originate from licensed Refinitiv data. The financial robustness tables reproduce from the documented fixed inputs. Reconstructing the supplied corpus engagement summaries and owner-network figures requires authorized platform records. An author-identified repository link is supplied with the title page.
\section*{Declaration of generative AI and AI-assisted technologies}
OpenAI Codex (GPT-6) assisted with analysis-code development, reproducible visualization and targeted manuscript editing. Numerical estimates are generated by the documented statistical computations from fixed inputs. Language-model classification is described as a research method in Section~\ref{sec:LLM}. Scientific interpretation, verification and submission remain the author's responsibility.'''

MODERN_REFERENCES={
'Petersen2009':r'''@article{Petersen2009, author={Petersen, Mitchell A.}, title={Estimating Standard Errors in Finance Panel Data Sets: Comparing Approaches}, journal={The Review of Financial Studies}, year={2009}, volume={22}, number={1}, pages={435--480}, doi={10.1093/rfs/hhn053}}''',
'CameronMiller2015':r'''@article{CameronMiller2015, author={Cameron, A. Colin and Miller, Douglas L.}, title={A Practitioner's Guide to Cluster-Robust Inference}, journal={Journal of Human Resources}, year={2015}, volume={50}, number={2}, pages={317--372}, doi={10.3368/jhr.50.2.317}}''',
'MacKinnonNielsenWebb2023':r'''@article{MacKinnonNielsenWebb2023, author={MacKinnon, James G. and Nielsen, Morten {\O}rregaard and Webb, Matthew D.}, title={Cluster-robust inference: A guide to empirical practice}, journal={Journal of Econometrics}, year={2023}, volume={232}, number={2}, pages={272--299}, doi={10.1016/j.jeconom.2022.04.001}}'''}

def write_empirical_tables(s):
    def p(v):return '$<0.001$' if v<.001 else f'{v:.3f}'
    rows=[]
    for name,label in [('common_month','Security + month'),('common_date','Security + date'),
      ('common_marketdate','Security + market-day'),('common_marketdate_sectormonth','+ sector-month'),
      ('primary','Sector-month + prior controls')]:
        m=s[name];z=m['sector_date']['fd_mean_exposure']
        rows.append(f"{label} & {z['Estimate']:+.4f} & {z['Std. Error']:.4f} & {p(z['Pr(>|t|)'])} & {m['N']:,} \\\\")
    core=r'''\begin{table}[htbp]\centering\footnotesize
\caption{Exposure and quoted spreads across fixed-effect specifications}
\label{tab:v2_core}
\begin{threeparttable}\begin{tabular}{l r r r r}\toprule
Specification & Coefficient & SE & $p$ & $N$ \\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\begin{tablenotes}\small\item The first four rows use identical observations, contemporaneous controls and tail caps. The final row uses prior-session controls. The outcome is the quoted spread in percentage points; uncertainty clusters by sector/date, with nine sectors. Market-day effects use actual listing markets. The positive and imprecise estimates are retained together.\end{tablenotes}
\end{threeparttable}\end{table}'''
    (SRC/'tables/tab_v2_core.tex').write_text(core+'\n',encoding='utf-8')
    m=s['common_marketdate'];rows=[]
    for key,label in [('fd_mean_exposure','Mean sector-specific exposure'),('log_volume','Log one plus volume'),
                      ('log_mktcap','Log market capitalization'),('range_pct','Daily price range (percent)')]:
        z=m['sector_date'][key];rows.append(f"{label} & {z['Estimate']:+.4f} & {z['Std. Error']:.4f} & {p(z['Pr(>|t|)'])} \\\\")
    table=r'''\begin{table}[htbp]\centering\footnotesize
\caption{Model I: Quoted spreads with local market-day controls}
\label{tab:v2_full_modelI}\begin{threeparttable}
\begin{tabular}{l r r r}\toprule Variable & Coefficient & SE & $p$ \\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\begin{tablenotes}\small\item $N=486{,}655$. Security and listing-market/date effects are absorbed. Financial variables are winsorized at the first and ninety-ninth percentiles; content scores are unchanged. SEs cluster by sector and date, with approximate $t_8$ reference probabilities. This model does not absorb sector-month conditions; that comparison is shown explicitly in Table~\ref{tab:v2_core}.\end{tablenotes}
\end{threeparttable}\end{table}'''
    (SRC/'tables/tab_v2_full_modelI.tex').write_text(table+'\n',encoding='utf-8')
    # Keep original benchmark readouts, but state their mapping limitations and
    # correct the price-gap label instead of presenting it as signed order flow.
    for model in ['II','III']:
        name=f'tab_v2_full_model{model}.tex'
        q=(BASE/'tables'/name).read_text(encoding='utf-8')
        q=q.replace('\\item \\textit{Notes:}',r'\item \textit{Scope:} Supplied factor-derived diagnostic. The regional factor mapping is not validated by the listing-market correction, so this table does not establish cross-market risk or return effects.\par'+ '\n'+r'\item \textit{Notes:}')
        q=q.replace('Order Flow','VWAP--midpoint gap').replace('order flow','VWAP--midpoint gap')
        (SRC/'tables'/name).write_text(q,encoding='utf-8')

if __name__=='__main__':main()
