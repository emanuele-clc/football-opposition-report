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
