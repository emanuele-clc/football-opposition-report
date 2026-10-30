# Thesis outline (working draft)

First written 22 October 2026; updated 30 October 2026 to the current research questions (RQ1 and RQ2 as in the README). It contains no new analysis: every number below is copied from a file in `results/` or `docs/`, named next to it. Writing starts in January 2027; this outline is the skeleton to write into and to discuss with the supervisors.

**Working title:** Automated Football Opposition Report: how far can each statement be trusted?

**One-sentence thesis:** An opposition report built automatically from event data can state, next to every number, how far that number can be trusted for the next match, and this level of trust can be measured, checked on a second data provider and improved by taking the next opponent and the venue into account.

**Shape, after the 21 October feedback ("too many things in too little time"):** two research questions and one prototype. The earlier study of build-up families is the motivation (one chapter); corners (L3), xT and tracking go to short appendices, labelled exploratory.

| Part | Chapter | Status |
|---|---|---|
| Motivation: critical evaluation of automatically discovered build-up families (pre-registered, held-out, 10 teams, negative results declared) | 4 | Done |
| RQ1. Evidence grade: every statement type graded A-D by next-match forecast skill and between-team discrimination, on 70 unseen StatsBomb teams, then on 96 Wyscout teams | 5 | Done; related work to finish |
| RQ2. Opponent- and venue-adjusted forecast: does it beat the season average, and does it change the grades? | 6 | Done |
| Prototype: report and local app that show the grade and the uncertainty next to each number, for each provider separately | 7 | Done |
| RQ3 (optional). Do the grades help analysts decide what to rely on? | 8 | Not done: needs analysts |

---

## 1. Introduction (about 6 pages)
- **Problem.** Opposition analysis turns a few matches into statements ("they play goal kicks short", "PPDA 12.6"). Analysts act on them, but nobody measures whether they hold in the next match. A number from five matches can look as solid as one from thirty (Mackenzie & Cushion 2013; Lames & McGarry 2007).
- **Research questions.**
  - RQ1: Which statements of an opposition report are reliable for the next match, and do the grades hold on a second data provider?
  - RQ2: Does a forecast that accounts for the next opponent and the venue (using only matches already played) beat the season average, and does it change which statements are reliable?
  - RQ3 (optional): Do the grades help analysts decide what to rely on?
- **Contributions:** the evidence grade (RQ1), the adjusted forecast (RQ2), and a prototype that shows both.
- **Method in one paragraph:** open data, protocols committed before each confirmatory run, unseen teams, result files committed unedited, negative results reported.
- **What the thesis does not do:** recommend tactics, predict results, evaluate players, claim club use.

## 2. Background and related work (about 12 pages)
- 2.1 Performance analysis and opposition scouting: what analysts produce, and the reliability debate (Mackenzie & Cushion 2013; Lames & McGarry 2007; Hughes et al. 2001; O'Donoghue 2005).
- 2.2 Event data and possession sequences: StatsBomb and Wyscout, play patterns, possessions; differences between providers.
- 2.3 Clustering of play patterns and team style (Deb et al. 2023 *to read in full*; Fernandez-Navarro et al. 2018 on style and context).
- 2.4 Properties of metrics: discrimination and stability (Franks et al. 2016; ElHabr 2023; Matteo et al. 2026 *to read in full*); matches needed (Barišić et al. 2021); skill scores (Murphy 1988).
- 2.5 Forecasting team statistics and opponent effects (arXiv 2001.09097; Ötting 2020).
- 2.6 Gap: no published study, to our knowledge, grades the statements of an opposition report by out-of-sample forecast skill. Wording from `docs/related_work_evidence_grade.md`; confirm with the database search first.

## 3. Data (about 5 pages)
- StatsBomb Open Data (non-commercial licence): complete 2015/16 seasons of four leagues, 1,517 matches and 80 teams; 9 development teams and 70 confirmatory teams (`docs/protocol_evidence_grade.md`). Bayer Leverkusen 2023/24 for the report examples.
- Wyscout public data (Pappalardo et al. 2019, CC BY 4.0): 2017/18, five leagues, 1,826 matches and 98 teams; 2 development teams and 96 confirmatory teams. No possession identifiers: possessions are rebuilt from the event order (`docs/protocol_evidence_grade_wyscout.md`, `docs/data_format.md`).
- Families study: Leverkusen 2023/24 and 9 teams from 2015/16; four chosen by hand, six drawn with seed 20261013, stratified by league (`docs/replication10_selection.json`).
- Data issues and how they were handled: team name mismatch (Marseille and Caen, 20 team-matches, Note 1 in `docs/protocol_evidence_grade.md`); truncated downloads; definition differences between providers (Wyscout: no pressures, no xG, about twice as many duels).

## 4. Motivation: are the build-up families real and useful? (about 10 pages)
- Method: open-play possessions with at least 3 passes, 11 features, two phases (build-up x < 45, k = 5; advanced, k = 3), K-Means; first 70% of matches for exploration, last 30% held out. Protocols: `docs/protocol.md`, `protocol_holdout.md`, `protocol_replication.md`, `protocol_replication10.md`, `protocol_simple_rule.md`.
- Held-out validation (pre-registered): H1 and H2 pass in 8 of 10 teams (Wilson 95% [0.49, 0.94]); the rule was at least 7 of 10. Source: `results/replication10_summary.json`.
- What drives the predictability (exploratory): play pattern alone gives almost all of the gain (+0.135 to +0.176). Source: `results/exploratory_ablation_*.json`, `exploratory_context_*.json`.
- Are they clusters? Copula null: silhouette above the null in 10 of 10 teams but only by +0.016 to +0.034: slices of a continuum. Source: `results/exploratory_cluster_test_*.json`.
- Families vs a one-variable rule (pre-registered, negative): families better in 0 of 10 teams. Source: `results/simplerule_*.json`.
- Matches needed (descriptive): passes per sequence and long-pass share need about 8-10 matches. Source: `results/samplesize_*.json`.
- **Why it matters:** the report's main analysis is reproducible but not a better predictor than a simple rule. This moved the thesis from "find the opponent's patterns" to "say how much each number can be trusted".
- Declared researcher degrees of freedom: `docs/results.md`.

## 5. RQ1: the evidence grade (about 14 pages)
- **5.1 Design.** 34 statement types. Forecast skill against the league average, and discrimination (Franks et al. 2016). Calibration of the 80% interval and matches needed are reported but not graded. Grade rule A-D. Protocol committed before the run: `docs/protocol_evidence_grade.md`.
- **5.2 Development run and the correction (Note 1).** PPDA had skill -0.18 with discrimination 0.82; the cause was the name mismatch. The correction rule was fixed before the corrected run, and both files are kept.
- **5.3 Results on 70 unseen StatsBomb teams.** Source: `results/evidence_grade_corrected.json`.
  - Grades: 4 A, 13 B, 15 C, 2 D.
  - A: passes per sequence (skill 0.36), long-pass share (0.24), sequence duration (0.24), short goal kicks (0.22).
  - Many defensive and transition statements: C. They separate teams over a season but do not forecast the next match better than the league average (for example PPDA 0.016).
  - Last 5 matches: worse than the season so far for 32 of 34 statements. Calibration: the 80% interval is about right for 30 of 34.
  - Sanity checks: SC2 passed; SC1 failed (counter-press discrimination 0.71, not low as expected). Reported, not changed.
- **5.4 Second provider (pre-registered).** Same statements, method and thresholds on Wyscout 2017/18, 96 teams: 5 A, 11 B, 10 C, 3 D on the 29 testable statements; 5 not testable (pressures, xG). Same letter in 21 of 29 (72%, Wilson 95% [0.54, 0.85]); the rule fixed beforehand was at least 70% and none two letters apart: none is. Verdict: **the grades hold, just**. Source: `results/evidence_grade_wyscout.json`, protocol `docs/protocol_evidence_grade_wyscout.md`.
- **5.5 Grades transfer, values do not.** On the same 36 Barcelona matches in both providers, only a few values agree (`results/evidence_provider_Barcelona.json`, `results/exploratory_provider_samematch_Barcelona.json`): values and ranks must never mix providers.
- **5.6 Limits.** Provider, season, leagues and teams change at once on Wyscout; reconstructed possessions; thresholds are conventions; many statements, no multiplicity correction.

## 6. RQ2: forecasts that know the next opponent and the venue (about 10 pages)
- **6.1 Design.** Forecast = season so far + shrunk opponent effect (what the opponent's opponents did against it) + league venue term; k = 5 and the venue term chosen on development teams only. Improvement = reduction of squared error against the season forecast, bootstrap over teams. Protocol: `docs/protocol_opponent_forecast.md`.
- **6.2 Results.** Sources: `results/opponent_forecast_statsbomb.json`, `results/opponent_forecast_wyscout.json`.
  - StatsBomb (70 teams, 30 statements): better in 21, worse in 2; median improvement 0.081. Answer: **helps**.
  - Wyscout (96 teams, 25 statements): better in 18, worse in 1; median improvement 0.063. Answer: **helps**.
  - Largest gains for pressing (PPDA) and shots; PPDA moves from C to A on both providers.
- **6.3 Grades with the adjusted forecast (secondary).** StatsBomb: 18 of 30 letters change (A from 4 to 14, C from 13 to 3). Wyscout: 11 of 25 change (A from 5 to 13). Discrimination is unchanged; the change comes only from the forecast.
- **6.4 Limits.** No interaction between the two teams' styles; the same venue term for a whole league; a better forecast does not show that an analyst prepares better.

## 7. Prototype: a report that states its uncertainty (about 10 pages)
- **7.1 Requirements** from the analyst workflow: main facts first; every number traceable to clips; export for the video tool; print.
- **7.2 Pipeline and outputs:** `src/oppreport.py`, the sheets, clip CSVs, MP4 clips cut from the match video, Sportscode/Nacsport-style XML (never tested in a real video tool), generic CSV adapter with round-trip test.
- **7.3 Local app:** replays (with 360 freeze frames where available), families, restarts, set pieces, transitions, defending, game plan hints (fixed rules, not tested advice), grades next to the ranks, three languages.
  - Two versions, StatsBomb and Wyscout, chosen with a switch: values and ranks never mix providers, and each version shows the grades computed on its own data.
  - Figures: `docs/img/overview.png`, `clips.png`, `replay.gif`.
- **7.4 Honesty by design:** intervals, "not ranked" below 8 matches, cautions always visible, no tactical names, negative results declared in the interface, "not testable" instead of fake zeros on Wyscout.
- **7.5 Reproducibility:** `tests/reproduce_results.py` (41/41 identical), `tests/reproduce_sheets.py` (50/50), API tests on all teams, replay and clip checks.
- **7.6 Known defects found and fixed:** the replay showed the opponent's possession in 45 of 18,618 sequences (22 Oct; display only); an earlier null-baseline file was wrong and was corrected.

## 8. RQ3 (optional): analyst review
- Kit ready: `docs/analyst_review_kit.md` and the Review page of the app (the report uses professional open data, so the reviewer needs no data of their own).
- Before the first review, decide which sequences are judged (now the 3 most typical per family, which favours "yes") and commit it.
- If no review is possible, say so plainly and keep RQ3 as future work.

## 9. Discussion (about 8 pages)
- Answers to RQ1 and RQ2 (and RQ3 if done) in plain words.
- What can and cannot be claimed: the grades say how far a statement forecast the next match on open data; they do not say that a club would use the tool, that it saves time, or which tactics work.
- Threats to validity: one season per provider; thresholds are conventions; families study on ten teams, nine from one season; the held-out matches of the families study were reused for several tests.
- Why the negative results matter for practice: a report should say which statements to trust.

## 10. Conclusion and future work (about 3 pages)
- See `docs/future_work.md`: analyst review, club data through the adapter, recency-weighted forecasts, other seasons, tracking data.

## Appendices
- A. Protocols, verbatim (all `docs/protocol_*.md`), with commit hashes and dates.
- B. Declared researcher degrees of freedom and data issues.
- C. Exploratory side studies, one page each, labelled exploratory:
  - **L3 corners:** null and weak. Leverkusen p = 0.17; pooled tournaments p = 0.41; low power. Source: `results/results_corners.json`, `results_pooled_corners.json`.
  - **xT model and threat sheet (descriptive):** `src/report/xt_grid.json`.
  - **Tracking (DFL open data, 7 matches, not the report teams):** ghosting, ridge 3.7 m beats the LSTM at 4.4 m (`results/exploratory_ghosting.json`); pitch control, pass AUC 0.89, +0.04 over a nearest-player margin (`results/exploratory_pitch_control.json`).
- D. User guide of the app and reproduction commands (`docs/pipeline.md`, `docs/analyst_guide.md`).

---

## Open items before or during writing
1. Read in full Matteo et al. 2026 and Deb et al. 2023. Run the database search and the forward citations of Franks et al. 2016, and record hit counts (`docs/related_work_evidence_grade.md`).
2. L3: decide with the supervisors whether it stays in Appendix C as a weak null or is dropped.
3. Analyst review (RQ3): decide which sequences are judged, commit that procedure, then find reviewers.
4. Make the figures from the result files only (no reruns): grade table for both providers, letters that change between providers, improvement per statement for RQ2, last 5 vs season, families gain with CI.
5. Ask the supervisors: expected length, citation style, and whether the prototype chapter counts as a contribution or as an appendix.
