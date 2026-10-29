# Related work for the evidence grade (first search)

Written 21 October 2026. This was a **first web search, not a systematic review**. I used a general web search, not Scopus, Web of Science or SPORTDiscus. For paywalled papers I read only the abstract or the publisher record. Before the thesis says "new", the papers marked *to read* must be read in full and the database search in the last section must be done.

## What the evidence grade does (for comparison)
For each of 34 statement types of an opposition report (team level, mostly tactical: restarts, set pieces, transitions, pressing, build-up families, key players), it measures:
1. **forecast skill** for the next match: the team's season so far against a baseline, which is the league average of the other teams up to that date;
2. **discrimination** across teams (Franks et al.);
3. **calibration** of an 80% interval for the next match;
4. **matches needed**.

It turns these into a grade A-D. The protocol was committed before the run, the code was developed on 9 teams, and it was confirmed once on 70 unseen teams. A second provider (Wyscout) is used as a label check.

## Closest work found

| Work | What it does | Same as ours | Different from ours |
|---|---|---|---|
| Franks, D'Amour, Cervone & Bornn, "Meta-analytics: tools for understanding the statistical properties of sports metrics", JQAS 12(4), 2016 ([arXiv 1609.09830](https://arxiv.org/abs/1609.09830)) | Defines discrimination, stability and independence for metrics; applied to NBA and NHL | Our discrimination measure is theirs | Player level, box-score metrics; no next-game forecast, no baseline, no interval calibration, no grading of report statements (checked in the full text) |
| T. ElHabr, "Meta-analytics for soccer", blog, 2023 ([link](https://tonyelhabr.rbind.io/posts/soccer-meta-analytics/)) | Franks discrimination and stability on 15 player stats, big 5 leagues 2018-2023 | Soccer, same meta-metrics | Blog, player level, no team tactical statements, no forecast |
| Matteo et al., "Understanding the statistical properties of performance indicators in Australian Football", J. Sports Sci. 44(14), 1867-1876, 2026 ([doi 10.1080/02640414.2026.2703355](https://doi.org/10.1080/02640414.2026.2703355); data: [La Trobe record](https://researchdata.edu.au/meta-metrics-australian-football/4020311)) | Franks discrimination and stability on 33 player and team metrics, AFL 2015-2023; counts discriminate and are stable, percentages less so, especially at team level | **Closest recent work**: rates indicators by their statistical properties, also at team level | Other sport; stability is measured across seasons (Franks), not as a next-match forecast against a baseline; no calibration, no grade in a tool (from the abstract; full text *to read*) |
| Lames & McGarry, "On the search for reliable performance indicators in game sports", IJPAS 7(1), 2007 | Argues that performance indicators are unreliable by nature because performance in game sports is unstable | Asks the same question (can indicators be trusted?) | Conceptual, no measurement per indicator. Our grade answers it empirically, statement by statement |
| Hughes, Evans & Wells, 2001, normative profiles; O'Donoghue, "Normative profiles of sports performance", IJPAS 5(1), 2005 | How many matches give a stable profile, and how to show the spread of performances | Our "matches needed" belongs to this line | Profiles, not forecasts; no baseline; no grading. *To read*: Hughes et al. 2001 (not found online) |
| Barišić, Mikulić, Nemčić, Sporiš & Dajaković, "Determination of stability of performance indicators in football", conference paper, 2021 ([CROSBI](https://www.bib.irb.hr/1148691)) | Croatian league 2014/15, cumulative means: 7-18 matches needed, depending on the indicator | Matches needed per indicator, team level, football | Simple counts (shots, crosses, cards), one league, no forecast, no out-of-sample test |
| Mackenzie & Cushion, "Performance analysis in football: a critical review", J. Sports Sci. 31(6), 2013 | Says reliability and validity of variables get too little attention, and that context is missing | Motivation | Review, no measurements |
| Fernandez-Navarro, Fradua, Zubillaga & McRobert, "Influence of contextual variables on styles of play in soccer", IJPAS 18(3), 2018 | Match status, venue and opponent change style scores (EPL 2015/16) | Same season and league type; context effects | Explains style by context; does not forecast the next match or grade statements |
| Deb, Fernandez-Navarro, McRobert & Jarman, "Finding repeatable progressive pass clusters...", J. Sports Analytics 9(4), 2023 ([open access](https://researchonline.ljmu.ac.uk/id/eprint/22645/)) | K-means pass clusters made repeatable (SeCo framework), used for opposition profiling at WC 2022 | **Close to the families part of the thesis** (clusters used to profile opponents, repeatability) | Pass clusters, not possession families; checks cluster repeatability, not next-match forecast. *To read in full, and cite in the families chapter* |
| Carleton, stabilization points (Baseball Prospectus, about 2007-2013) | Split-half reliability: the sample size at which a stat is half signal and half noise | Same logic as "matches needed" | Baseball, player level, blog tradition |
| Murphy, "Skill scores based on the mean square error...", Monthly Weather Review, 1988 | Skill score = 1 - MSE(forecast) / MSE(reference) | Our forecast skill is this score, with the league average as the reference | Meteorology. Cite as the origin of the measure, not as a competitor |
| Forecasting match statistics, e.g. "Forecasting football matches by predicting match statistics" ([arXiv 2001.09097](https://arxiv.org/abs/2001.09097)) | Predicts shots, corners and similar statistics from team ratings, compared against the sample mean | Next-match forecast of team statistics against a simple baseline | Goal is predicting results (betting), not checking report statements; few statistics, no tactical ones |
| NFL play-call prediction (e.g. Ötting 2020, [arXiv 2003.10791](https://arxiv.org/abs/2003.10791)) | Predicts run or pass from past tendencies | Opponent tendencies used for forecasting | Other sport, one decision type, no grading |

## What looks new (to confirm with the database search)
In this search I found **no study** that:
- takes the **statements of an opposition report** (team level, tactical: goal kicks, corners, pressing, transitions, families, key players) as the unit of evaluation;
- tests each one **prospectively on the next match against a league-average baseline**;
- reports the **calibration** of the interval shown next to the number;
- runs on teams **never analysed before**, with a protocol committed before the run;
- turns the result into a **grade shown in the tool next to each number**.

Each of these pieces exists somewhere: discrimination (Franks), matches needed (Hughes, O'Donoghue, Barišić), the skill score (Murphy), forecasting statistics (match prediction papers). The contribution is putting them together for the statements an analyst actually reads, and the result (4 A, 13 B, 15 C, 2 D; last 5 matches worse than the season for 32 of 34). The safest wording for the thesis is: *"to our knowledge, no study has graded the statements of an opposition report by their out-of-sample forecast skill"*. Avoid "first ever".

## Risks
- The **Australian Football 2026 paper** (Matteo et al.) is the main risk. From the abstract it uses only Franks discrimination and stability, with no next-match forecast and no calibration. Read the full text to confirm. Its finding that percentages are less stable at team level should be compared with our discrimination results before citing it as agreement.
- Clubs and providers may run similar checks internally and not publish them. That cannot be ruled out; say "in the published literature".
- Possible missing literature: the German *Spielanalyse* tradition (Lames and colleagues, e.g. the Bundesliga stability study "Performance of performance indicators in football"), and studies on the reliability of tracking-based KPIs.

## Next steps
1. Read in full: the Australian Football 2026 paper, Franks et al. (done for what matters here), Deb et al. 2023, Lames & McGarry 2007, O'Donoghue 2005, Hughes et al. 2001, and the Lames Bundesliga stability paper.
2. Database search (Google Scholar, Scopus, SPORTDiscus), years 2000-2026, with these terms: "performance indicator" AND (reliability OR stability OR "test-retest" OR "meta-analytics" OR "discrimination") AND (football OR soccer); "opposition analysis" OR "opposition scouting" AND (validity OR reliability OR forecast); "next match" AND "team statistics" AND forecast; "skill score" AND sport. Note down the number of hits and how many were kept, so the search can be reported in the thesis.
3. Forward citations of Franks et al. 2016 in Google Scholar ("cited by"). This is the fastest way to find anything that applies meta-metrics to football teams.

---

# Second search (24 October 2026)

Still **not a systematic review**: no Scopus, Web of Science or SPORTDiscus (no access from here). What was done:
1. **Forward citations of Franks et al. 2016** via the Semantic Scholar API (arXiv 1609.09830): **56 citing papers**, screened by title and venue. Kept 4 (below); the rest are player valuation, NBA/NHL/NFL player models, or other topics.
2. **Web searches** (general search engine), terms: team performance indicators + reliability / stability / next-match prediction / meta-analytics; opposition analysis or scouting report + validity / reliability; recent form vs season average; playing-style consistency; skill score / calibration in sport; automated opposition reports. Bibliographic details checked on Crossref.

## New relevant work

| Work | What it does | Same as ours | Different from ours |
|---|---|---|---|
| Russomanno, Linke, Geromiller & Lames, "Performance of performance indicators in football", Proc. IACSS 2019, AISC 1028, 36-44, Springer ([doi 10.1007/978-3-030-35048-2_5](https://doi.org/10.1007/978-3-030-35048-2_5)) | Bundesliga 2016/17 (279 matches, from the search snippet): day-to-day stability of team indicators and how well season averages predict final rank | **Closest in football**: team level, stability across match days, the Lames line of work | Predicts the final table, not the next match; no baseline skill score, no calibration, no grades. Abstract not retrieved: *to read* (paywall) |
| Garrido et al., "Consistency and identifiability of football teams: a network science perspective", Sci. Rep. 10, 19735, 2020 ([doi 10.1038/s41598-020-76835-3](https://doi.org/10.1038/s41598-020-76835-3)) | LaLiga 2018/19 passing networks: *consistency* = correlation between matches of the same team; *identifiability* = how different from other teams | Same two ideas as stability and discrimination, at team level, in football | Passing networks only, within one season, no next-match forecast against a baseline, no calibration, no grades for report statements |
| Liu, Gómez, Gonçalves & Sampaio, "Technical performance and match-to-match variation in elite football teams", J. Sports Sci. 34, 509-518, 2016 ([doi 10.1080/02640414.2015.1117121](https://doi.org/10.1080/02640414.2015.1117121)); Yi, Gómez, Liu & Sampaio, Kinesiology 51(2), 170-181, 2019 (Champions League 2009/10-2016/17) | Coefficient of variation of team technical indicators across matches; link between variability and success | Match-to-match variability of team indicators | Describe variability; do not forecast the next match or grade indicators |
| Heuer, "Identification of relevant performance indicators in round-robin tournaments", arXiv 2003.03774, 2020 | Bundesliga: rates indicators by how well they reflect team strength and forecast future results, net of finite-sample noise; packing rate best | Rates indicators by forecasting quality, with noise from finite samples | Forecasts results/strength, not the indicator itself; no tactical report statements; no calibration |
| Deb, Fernández-Navarro, McRobert & Jarman, J. Sports Analytics 9(4), 289-303, **2023** (read in full, open access) | SeCo framework: *repeatability* = concordance of k-means solutions over bootstrap resamples; clusters then used to profile WC 2022 opponents | Clustering for opponent profiling, stability of clusters (cite in the families chapter) | Repeatability is about the clustering run, **not held-out or future matches**; no check that profiles predict later behaviour. Our held-out validation and simple-rule test go further on this point |
| Zhou & Guan, "From metrics to decisions in NBA analytics: a critical integrative review and decision-readiness framework", arXiv 2609.27245, 2026 (cites Franks) | Six "gates" to match each decision claim to the evidence it needs (point-in-time validity, uncertainty, portability, ...) | Same spirit: each claim needs evidence matched to it | Conceptual review, NBA, no empirical grading of statements |
| Davis, Bransen, Devos et al., "Methodology and evaluation in sports analytics: challenges, approaches, and lessons learned", Machine Learning, 2024 ([doi 10.1007/s10994-024-06585-0](https://doi.org/10.1007/s10994-024-06585-0)) | How to evaluate sports indicators and models: dependencies in the data, how to split evaluation data | Supports splitting by match/time and evaluating indicators, not only models | Methodology paper, no grading |
| Chang & Chuang, "Simple versus complex metrics in single-game baseball prediction: a temporal validation study", J. Sports Analytics 12, 2026 ([doi 10.1177/22150218261493344](https://doi.org/10.1177/22150218261493344)) (cites Franks) | Temporal validation of simple vs complex metrics for single games | Out-of-sample, time-ordered test; simple vs complex (like our simple-rule test) | Baseball, game outcome. Abstract not retrieved: *to read* |
| Bergkamp, Meijer, den Hartigh, Frencken & Niessen, Psych. Sport Exerc. 63, 102257, 2022 ([doi 10.1016/j.psychsport.2022.102257](https://doi.org/10.1016/j.psychsport.2022.102257)) | Reliability and predictive validity of ratings by 96 coaches and scouts | Motivation: human judgements in scouting are rarely checked for reliability | Player scouting, human raters |

Also found, background only: Murphy-style skill and calibration used for match-outcome forecasts (FiveThirtyEight "checking our work"; Brier decomposition papers) - these are about outcome probabilities, not report statements. Commercial "opposition dossier" products claim validation but publish no method.

## Conclusion after the second search
Nothing found that grades the statements of an opposition report by next-match forecast skill against a baseline, interval calibration and discrimination, on unseen teams, with a protocol first. The closest pieces are now: **Franks 2016** (discrimination), **Russomanno et al. 2019** and **Garrido et al. 2020** (team-level stability and identifiability in football), **Heuer 2020** (indicators rated by forecasting quality), **Matteo et al. 2026** (meta-metrics at team level, AFL). The wording "to our knowledge" stays; still avoid "first".

## Scopus search (27 October 2026)
Scopus, FH OÖ institutional access, field TITLE-ABS-KEY unless stated, no year limit, run on 27 Oct 2026. Titles screened (first author and year in the results list); abstracts only for possible hits. This is a structured search, not yet a full systematic review: abstracts of the kept papers still need to be read.

| # | Query | Hits | Kept / notes |
|---|---|---|---|
| S1 | `(football OR soccer) AND ("performance indicator*" OR "match statistic*" OR "key performance indicator*") AND (reliab* OR stabil* OR discriminat* OR repeatab*)` | 99 | Matteo et al. 2026 (already listed). The rest use "discriminate" for winning vs losing teams (e.g. Castellano et al. 2012) or "reliability" for inter-operator data reliability (e.g. Liu et al. 2013, OPTA): different questions |
| S2 | `(football OR soccer OR sport*) AND ("performance indicator*" OR "match statistic*" OR "team statistic*" OR metric*) AND ("next match*" OR "subsequent match*" OR "future match*" OR "out-of-sample" OR "match-to-match" OR "game-to-game")` | 50 | Liu et al. 2016 (match-to-match variation, already listed). Others: match-outcome prediction, physical load variability |
| S3 | `("opposition analysis" OR "opposition report*" OR "scouting report*" OR "opponent analysis" OR "opposition scouting" OR "match preparation") AND (football OR soccer OR sport*)` | 113 | Plakias 2025 (opponent and real-time analysis, game-theory practice), Clijmans et al. 2023 (intrinsic playing style beyond the past opponents), Gu et al. 2025 (systematic review of playing-style identification). None evaluates whether report statements hold in the next match |
| S4 | `("meta-analytics" OR "meta-metric*" OR metametric* OR "stabilization point*" OR "signal and noise" OR "signal-to-noise") AND (sport* OR football OR soccer OR basketball OR hockey OR baseball)` | not shown on the page | Top hits: Franks et al. 2016 and Matteo et al. 2026; the rest are physiology/test reliability |
| S5 | Forward citations of Franks et al.: `REFTITLE("statistical properties of sports metrics")` | 44 | Davis et al. 2024 (already listed). Others: player valuation, plus-minus, xG/EPV, hot hand. None grades report statements |
| S6 | `(football OR soccer) AND ("playing style*" OR "style of play" OR "team style*" OR tactical) AND (stabil* OR consisten* OR repeatab* OR "sample size" OR "number of matches") AND (predict* OR forecast* OR reliab*)` | 52 | Zhong et al. 2026 (styles and outcome prediction, UCL). Others: player variability, outcome prediction |

**Result:** the Scopus search confirms the web searches. No paper found grades the statements of an opposition report by next-match forecast skill against a baseline, combined with discrimination, on unseen teams with a protocol fixed first. New papers to read: Clijmans et al. 2023, Plakias 2025, Gu et al. 2025 (review). Wording unchanged: "to our knowledge"; avoid "first".

## Third search (29 October 2026): literature for the new RQ1 and RQ2
After the 28 Oct meeting the research questions changed (RQ1: do the grades hold on a second provider; RQ2: does a forecast that knows the opponent and the venue beat the season average). General web search only; full texts were not available from here for Matteo et al. 2026 (publisher returns 403) and Russomanno et al. 2019 (Springer, abstract only).

### RQ1: same statements on two providers
| Work | What it says | Use in the thesis |
|---|---|---|
| Bischofberger, Baca & Schikuta, "Event detection in football: Improving the reliability of match analysis", PLOS ONE 19(4), e0298107, 2024 ([doi 10.1371/journal.pone.0298107](https://doi.org/10.1371/journal.pone.0298107), read) | Providers define events differently and rarely publish the definitions: Wyscout counts crosses as passes, Stats Perform does not and requires a pass to be intentional; "recovery" means different sets of actions; "studies which seemingly use the same categories of events are not necessarily comparable". Wyscout timestamps found misaligned | **Main citation for why values differ across providers** (our Barcelona check: 18 of 24 values differ). Does not measure agreement on the same matches |
| Liu, Hopkins, Gómez & Molinuevo, "Inter-operator reliability of live football match statistics from OPTA Sportsdata", IJPAS 13(3), 2013 | High agreement between Opta operators (ICC 0.88-1.00) | Reliability *within* one provider is high; our question is *between* providers. Cite to separate the two |
| Pappalardo et al., "A public data set of spatio-temporal match events in soccer competitions", Sci. Data 6, 236, 2019 | The Wyscout data used for RQ1 | Data source. The paper describes the tags but no inter-annotator check was found |
| MartinOnData, "Which xG data should you trust?", Python Football Review #017, 20 Nov 2025 ([link](https://www.pythonfootball.com/p/which-xg-data-should-you-trust), blog, read) | xG of Opta, StatsBomb, Wyscout, Understat on big-5 leagues 2017/18-2021/22: match-level correlations lower for Wyscout pairs (0.86-0.88); cumulative season signals converge (all pairs above 0.97 by the end of the season) | **Same pattern as our RQ1 at a different level**: single values disagree, season-level signals agree. Grey literature: cite as supporting observation only, and only for xG (which we could not test on Wyscout) |
| "OpenSTARLab: Open Approach for Spatio-Temporal Agent Data Analysis in Soccer", arXiv 2502.02785, 2025 (authors to check) | Maps event types across providers (e.g. StatsBomb "Ground Pass" = Wyscout "Simple Pass") | Shows that a common format is needed; our generic CSV plays this role |

**Gap for RQ1:** nothing found that computes a reliability measure (forecast skill, discrimination) for the same statement types on two providers and compares the results. Published work compares *values* (or operators within a provider), not whether the *trust* in a statement carries over. Wording: "to our knowledge".

### RQ2: opponent and venue in the forecast
| Work | What it says | Use in the thesis |
|---|---|---|
| Lago-Peñas & Dellal 2010; Lago 2009 ("The influence of match location, quality of opposition and match status on possession strategies", J. Sports Sci. 27(13)) | Possession depends on venue, opponent quality and score | Background for why a team's numbers move with the opponent and the venue (our largest gains: PPDA, shots) |
| Lago-Peñas & Lago-Ballesteros, "Game location and team quality effects on performance profiles in professional soccer", J. Sports Sci. Med. 10(3), 2011 | Home/away and team quality change the profile of performance indicators | Same: supports adding a venue term |
| Fernandez-Navarro et al. 2018 (already listed) | Opponent and venue change style scores | Same |
| Maher, "Modelling association football scores", Statistica Neerlandica 36, 1982; Dixon & Coles 1997 | Team attack and defence parameters plus a home effect, for goals | The additive structure "team + opponent + venue" of our F_adj comes from this tradition; we apply it to report statements, not goals |
| "Forecasting football matches by predicting match statistics", arXiv 2001.09097 (already listed) | Predicts match statistics with team ratings | Closest for forecasting statistics with the opponent in the model; goal is the result, not checking report statements |
| Clijmans, Van Roy & Davis, "Looking beyond the past: analyzing the intrinsic playing style of soccer teams", ECML PKDD 2022, LNCS ([doi 10.1007/978-3-031-26422-1_23](https://doi.org/10.1007/978-3-031-26422-1_23)) | Markov-chain model of a team's offensive style, to generalise past behaviour (EPL 2019/20) | Listed in the Scopus search as 2023: the publication year is 2022. From the abstract it does **not** adjust for the opponents faced; full text to check before writing that |
| He, Araújo, Davids, Kee & Komar, Adaptive Behavior, 2023 | Style flexibility, reactivity to the opponent, imposition | Conceptual support: some behaviours depend on the opponent, others are imposed (our result: goal kicks, keeper, throw-ins do not improve with the opponent term) |

**Gap for RQ2:** opponent and venue effects on indicators are well known, and opponent-adjusted ratings exist for results. Nothing found that tests, out of sample and statement by statement, whether an opponent- and venue-adjusted forecast changes which statements of an opposition report can be trusted.

Bibliographic details of Lago 2009, Lago-Peñas & Dellal 2010, Lago-Peñas & Lago-Ballesteros 2011, Liu et al. 2013, Maher 1982 and Dixon & Coles 1997 are from memory and search snippets: check them on Crossref before they go into the thesis.

### RQ3 (optional): evaluation with analysts (search of 29 October 2026)
| Work | What it says | Use in the thesis |
|---|---|---|
| Brooke, "SUS: a 'quick and dirty' usability scale", in *Usability Evaluation in Industry*, Taylor & Francis, 1996 (from memory, to check) | The ten-item System Usability Scale, 0-100 | Standard short usability measure for the tool |
| Bangor, Kortum & Miller, "Determining what individual SUS scores mean: adding an adjective rating scale", J. Usability Studies 4(3), 114-123, 2009 ([PDF](https://uxpajournal.org/wp-content/uploads/sites/7/pdf/JUS_Bangor_May2009.pdf)) | Adjective scale correlates with SUS (r = 0.82); quartiles of study means from a large benchmark (cut points about 62.6, 70.5, 77.8) | How to read a SUS score; with 3-5 analysts report the scores, not a mean with a test |
| Stein, Janetzko et al., "Bring it to the pitch: combining video and movement data to enhance team sport analysis", IEEE TVCG 24(1), 2018 ([record](https://kops.uni-konstanz.de/handle/123456789/41137)); Stein et al. 2015 "Visual soccer analytics"; "Where to go" (Konstanz group) | Football visual analytics evaluated through expert studies with analysts and coaches (often 2-3 experts) | Precedent: small expert studies are the norm in this field; gives the format (task, think aloud, feedback) |
| Wright, Atkins, Jones / Bateman & Jones / Jowett et al. line of work; "Strategies for maintaining the coach-analyst relationship... COMPASS model", 2019 ([PMC6748348](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6748348/)) | Interviews with professional analysts: trust and honesty are the key attributes; analysts rarely lead feedback | Motivation for RQ3: an analyst must be able to defend a number to the coach; the grade is meant to help that |
| "Danish association football coaches' perception of performance analysis", IJPAS, 2021 ([doi 10.1080/24748668.2021.2012040](https://www.tandfonline.com/doi/full/10.1080/24748668.2021.2012040)) | Coaches with an analyst use video and information more in preparation | Context for who would use the tool (clubs with and without analysts) |
| "Data-driven scouting in football: a multiple case study" ([ResearchGate](https://www.researchgate.net/publication/415366695_Data-Driven_Scouting_in_Football_A_Multiple_Case_Study)) | Data complement, never replace, human judgement because of uncertainty and context | Supports the framing "where to look", not advice |

**Gap for RQ3:** no study found that measures whether showing the reliability of each number changes what analysts trust or use. SUS studies of sports apps exist but with fans or general users, not analysts. Wording if RQ3 is done: "a pilot with N analysts", never a general claim.

### Still to read (updated)
- Matteo et al. 2026 and Russomanno et al. 2019: need the university library (not reachable from here). Unchanged priority.
- Lago-Peñas & Lago-Ballesteros 2011 (open access, J. Sports Sci. Med.) and Clijmans et al. 2022 full text.
- For RQ3 (optional): usability literature (SUS, studies with sports analysts), not searched yet.

## Still to do
1. Download through the university and read in full: **Matteo et al. 2026** (publisher blocks access from here), **Russomanno et al. 2019**, Chang & Chuang 2026, Liu et al. 2016.
2. ~~One Scopus search~~ done 27 Oct 2026 (section above); still to do: read the abstracts of the kept papers and add SPORTDiscus or Web of Science if the thesis needs a full systematic review.
3. Check Lames & McGarry 2007, O'Donoghue 2005 in full (unchanged from the first search).
