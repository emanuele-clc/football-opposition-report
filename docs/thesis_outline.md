# Thesis outline (working draft)

Written 22 October 2026, before the supervisor (relatore) is assigned. It contains no new analysis: every number below is copied from a file in `results/` or `docs/`, named next to it. Writing starts in January 2027; this outline is the skeleton to write into and to show the supervisor.

**Working title:** Automated Football Opposition Report: what open event data can and cannot tell an analyst

**One-sentence thesis:** An opposition report built automatically from open event data can describe how a team builds up in a reproducible way, but each statement in it deserves a different level of trust, and that level can be measured.

**Shape, after the 21 October feedback ("too many things in too little time"):** two contributions and one prototype. Everything else (corners L3, xT, tracking) goes to short appendices, labelled exploratory.

| Contribution | Chapter | Status |
|---|---|---|
| C1. Critical evaluation of automatically discovered build-up families (pre-registered, held-out, 10 teams, negative results declared) | 4-5 | Done |
| C2. Evidence grade: every statement type of the report graded A-D by next-match forecast skill and between-team discrimination, on 70 unseen teams | 6 | Done; related work to finish |
| Prototype: report and local app that show the grade and the uncertainty next to each number | 7 | Done; analyst review missing |

---

## 1. Introduction (about 6 pages)
- **Problem.** Opposition analysis turns a few matches of video into statements ("they play goal kicks short", "they press high"). These statements are rarely checked: how stable are they, and do they hold in the next match? (Mackenzie & Cushion 2013; Lames & McGarry 2007.)
- **Research questions.**
  - RQ1: Can the open-play build-up of a team be summarised by automatically discovered sequence families that reappear on unseen matches?
  - RQ2: Are these families distinct structures, and do they add information over a simple rule?
  - RQ3: How far can each type of statement in an opposition report be trusted for the next match?
  - RQ4 (design): Can the results be packaged in a tool that states its own uncertainty?
- **Contributions:** C1, C2 and the prototype, as in the table above.
- **Method in one paragraph:** open data, protocols committed before each confirmatory run, held-out matches, negative results reported.
- **What the thesis does not do:** recommend tactics, predict results, evaluate players, claim club use.

## 2. Background and related work (about 12 pages)
- 2.1 Performance analysis and opposition scouting: what analysts produce, and the reliability debate (Mackenzie & Cushion 2013; Lames & McGarry 2007; Hughes et al. 2001; O'Donoghue 2005).
- 2.2 Event data and possession sequences: StatsBomb, play patterns, possessions.
- 2.3 Clustering of play patterns and team style (Deb et al. 2023 *to read in full*; Fernandez-Navarro et al. 2018 on style and context).
- 2.4 Properties of metrics: discrimination and stability (Franks et al. 2016; ElHabr 2023; Matteo et al. 2026 *to read in full*); matches needed (Barišić et al. 2021); skill scores (Murphy 1988).
- 2.5 Forecasting team statistics (arXiv 2001.09097; Ötting 2020).
- 2.6 Gap: no published study, to our knowledge, grades the statements of an opposition report by out-of-sample forecast skill. Wording from `docs/related_work_evidence_grade.md`; confirm with the database search first.
- Source: `docs/related_work_evidence_grade.md`.

## 3. Data (about 5 pages)
- StatsBomb Open Data, non-commercial licence, cite StatsBomb.
- Report teams: Bayer Leverkusen 2023/24 (34 matches) and 9 teams from 2015/16 (PL, La Liga, Serie A, Ligue 1). Four were chosen by hand; six were drawn with seed 20261013, stratified by league (`docs/replication10_selection.json`).
- Evidence-grade data: complete 2015/16 seasons of four leagues, 1,517 matches and 80 teams; 9 development teams and 70 confirmatory teams (`docs/protocol_evidence_grade.md`).
- Second provider: Wyscout public data, Barcelona 2017/18, 36 matches in both datasets.
- Data issues found and how they were handled:
  - team name mismatch: Marseille and Caen, 20 team-matches, Note 1 in `docs/protocol_evidence_grade.md`;
  - truncated downloads;
  - 2015/16 data are older than current collection.
- Train/held-out split: first 70% of matches by date for exploration, last 30% held out.

## 4. Method: build-up families (about 10 pages)
- Sequence definition: an open-play possession with at least 3 passes; restarts from corners, free kicks and kick-off are excluded.
- 11 features: start/end position, width, net progression, path length, directness, passes, long-pass share, width SD, duration.
- Two phases: build-up (start x < 45, k = 5) and advanced (x ≥ 45, k = 3). K-Means with n_init 20 and random_state 0. Labels B1.., A1.. ordered by mean start x; numbers, not tactical names.
- Stability: mean best-match Jaccard, bootstrap over matches. Null models: shuffled features, single Gaussian, copula.
- Predictability: logistic regression (C = 0.5) on play pattern, minute, half and previous family; gain in log-loss over the family-frequency baseline.
- Hypotheses H1, H2, H3 and the decision rules, quoted from the protocols: `docs/protocol.md`, `protocol_holdout.md`, `protocol_replication.md`, `protocol_replication10.md`, `protocol_simple_rule.md`.
- Researcher degrees of freedom, declared (`docs/results.md`, section "Declared researcher degrees of freedom"): the x = 45 split, the choice of k, the discarded first representation, threshold calibration on the first two teams.

## 5. Results: are the families real and useful? (about 14 pages)
Each section gives a result, its source file, and what it does and does not show.
- **5.1 Held-out validation (RQ1, pre-registered).** H1 and H2 pass in 8 of 10 teams (Wilson 95% [0.49, 0.94]); the rule was at least 7 of 10. The two failures are Barcelona (+0.024) and Sassuolo (+0.035). H2 passes in 10 of 10 but is lenient. H3: build-up 6 of 8, advanced 2 of 8. Source: `results/replication10_summary.json`, `results/holdout_<team>.json`.
- **5.2 What drives the predictability (exploratory).** Play pattern alone gives almost all of the gain (+0.135 to +0.176). Minute, half, previous family, score and venue add nothing (-0.008 to -0.028). Source: `results/exploratory_ablation_*.json`, `exploratory_context_*.json`.
- **5.3 Are they clusters? (RQ2).**
  - E1: stability above the Gaussian null by at least 0.10 in 4 of 10 teams.
  - Copula null (exploratory): silhouette above the null in 10 of 10 teams, but only by +0.016 to +0.034; Jaccard above the null in 6 of 10.
  - Conclusion: slices of a continuum. Source: `results/null_baseline_*.json`, `exploratory_cluster_test_*.json`.
- **5.4 Families vs a one-variable rule (RQ2, pre-registered, negative).** Families better in 0 of 10 teams in both phases; the simple rule better in 5 of 10. Source: `results/simplerule_*.json`.
- **5.5 Matches needed (descriptive).** Passes per sequence and long-pass share need about 8-10 matches. Shot rate and own-half share do not separate teams even with 15. Source: `results/samplesize_*.json`.
- **5.6 Second provider on the same matches (exploratory).** Families fitted on StatsBomb and applied to Wyscout: build-up shares within 2.4 points, advanced within 4.4. Long-pass share, short goal kicks and losses are not comparable across providers. Source: `results/exploratory_provider_samematch_Barcelona.json`.
- **5.7 Summary.** The families are a reproducible description driven by how sequences start. They are not distinct tactical clusters and not a better shot predictor.

## 6. Evidence grade: how far can each statement be trusted? (about 14 pages)
- **6.1 Question and design.** 34 statement types (S01-K34). Forecast skill against a league-average baseline, and discrimination (Franks). Calibration of the 80% interval and matches needed are reported but not graded. Grade rule A-D. Protocol committed before the run. Source: `docs/protocol_evidence_grade.md`.
- **6.2 Development run and the correction (Note 1).** PPDA had skill -0.18 with discrimination 0.82; the cause was the name mismatch. The correction rule was fixed before the corrected run, and both files are kept.
- **6.3 Results on 70 unseen teams.** Source: `results/evidence_grade_corrected.json`.
  - Grades: 4 A, 13 B, 15 C, 2 D.
  - A: passes per sequence (skill 0.36), long-pass share (0.24), sequence duration (0.24), short goal kicks (0.22).
  - D: throw-ins in own half ended in own half; corners ending in a shot.
  - Family shares (F07, F08): C. Weak forecast skill (0.06, 0.07); discrimination not applicable.
  - Many defensive and transition statements: C. They separate teams over a season but do not forecast the next match better than the league average (for example PPDA 0.016, pressures per match -0.002).
  - Last 5 matches: worse than the season so far for 32 of 34 statements.
  - Calibration: the 80% interval is about right for 30 of 34.
- **6.4 Sanity checks.** SC2 passed. SC1 failed: counter-press discrimination was high (0.71), not low as expected. Reported, not changed.
- **6.5 Second provider label.** Barcelona 2017/18, Wyscout: 6 same, 18 differ, 10 not testable. Source: `results/evidence_provider_Barcelona.json`.
- **6.6 What it means for the analyst.** Season trends beat the last 5. Most numbers describe a season better than they predict a match. The grade is shown in the tool next to each number.
- **6.7 Limits.** One season and one provider for the grade. Weak baseline. No opponent or venue adjustment. Thresholds are conventions. 34 tests with no multiplicity correction. The full list is in "Known weaknesses" of the protocol.

## 7. Prototype: a report that states its uncertainty (about 10 pages)
- **7.1 Requirements** from the analyst workflow: main facts first; every number traceable to clips; export for the video tool; print.
- **7.2 Pipeline and outputs:** `src/oppreport.py`, the sheets, clip CSVs, Sportscode/Nacsport-style XML (never tested in a real video tool), generic CSV adapter with round-trip test.
- **7.3 Local app:**
  - replays;
  - families;
  - restarts, set pieces, transitions, defending;
  - game plan hints (fixed rules, not tested advice);
  - grades shown next to the ranks;
  - teams with fewer than 8 matches not ranked;
  - three languages.
  - Figures: `docs/img/overview.png`, `clips.png`, `replay.gif`.
- **7.4 Honesty by design:** intervals, "not ranked", cautions always visible, no tactical names, negative results declared in the interface.
- **7.5 Reproducibility:** `tests/reproduce_results.py` (41/41 identical), `tests/reproduce_sheets.py`, API tests on all teams.
- **7.6 Evaluation:**
  - Done: technical tests only.
  - Missing: the analyst review (`docs/analyst_review_kit.md`). Before the first review, decide which sequences are judged (now the 3 most typical per family, which favours "yes").
  - Say plainly if no review was possible.
- **7.7 Known defects found and fixed:**
  - Replay showed the opponent's possession in 45 of 18,618 sequences (22 Oct; display only).
  - Earlier null-baseline file was wrong and was corrected.

## 8. Discussion (about 8 pages)
- Answers to RQ1-RQ4 in plain words.
- What can and cannot be claimed (CLAUDE.md section 7, quoted almost verbatim).
- Threats to validity: team selection (four chosen by hand); nine of ten teams from one season; held-out matches reused for H1-H3 and the simple rule; author-defined thresholds; one provider.
- Why the negative results matter for practice: a report should say which statements to trust.

## 9. Conclusion and future work (about 3 pages)
- Analyst review; club data through the adapter; opponent-adjusted forecasts; other seasons and providers for the grade; tracking data.

## Appendices
- A. Protocols, verbatim (all `docs/protocol_*.md`), with commit hashes and dates.
- B. Declared researcher degrees of freedom and data issues.
- C. Exploratory side studies, one page each, labelled exploratory:
  - **L3 corners:** null and weak. Leverkusen p = 0.17; pooled tournaments p = 0.41; low power. Source: `results/results_corners.json`, `results_pooled_corners.json`.
  - **xT model and threat sheet (descriptive):** `src/report/xt_grid.json`.
  - **Tracking (DFL open data, 7 matches, not the report teams):**
    - ghosting: ridge 3.7 m beats the LSTM at 4.4 m (`results/exploratory_ghosting.json`);
    - pitch control: pass AUC 0.89, +0.04 over a nearest-player margin (`results/exploratory_pitch_control.json`).
- D. User guide of the app and reproduction commands (`docs/pipeline.md`, `docs/analyst_guide.md`).

---

## Open items before or during writing
1. Read in full Matteo et al. 2026 and Deb et al. 2023. Run the database search and the forward citations of Franks et al. 2016, and record hit counts (`docs/related_work_evidence_grade.md`, "Next steps").
2. L3: decide with the supervisor whether it stays in Appendix C as a weak null or is redesigned.
3. Analyst review: decide which sequences are judged, commit that procedure, then find a reviewer.
4. Make the figures for chapters 5 and 6 from the result files only (no reruns):
   - per-team gain with CI;
   - E1 margins;
   - simple-rule comparison;
   - grade table;
   - last-5 vs season.
5. Ask the supervisor: expected length, citation style, and whether the prototype chapter counts as a contribution or as an appendix.
