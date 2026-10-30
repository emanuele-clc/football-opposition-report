# Future work: ideas not done in the thesis

Written 22 October 2026 for discussion with the supervisors; updated 30 October 2026. Two ideas of the first list have since been done and are now the thesis research questions: 1.1 is RQ2 and 1.2 is the second part of RQ1 (marked **Done** below, with their results). Everything else has not been run: these are proposals, with what each would show and what it would cost. Rough cost: S = one or two days, M = about a week, L = several weeks or depends on other people. Any idea that tests a hypothesis needs a protocol committed before the run, as for the rest of the thesis.

## 1. Research on the evidence grade (main contribution)

| # | Idea | What it would show | Cost | Notes |
|---|---|---|---|---|
| 1.1 | **Done (RQ2).** Opponent- and venue-adjusted forecasts, compared with the season forecast. | Better in 21 of 30 statements on StatsBomb (70 teams) and 18 of 25 on Wyscout (96 teams), worse in 2 and 1; PPDA moves from C to A on both providers. | – | `docs/protocol_opponent_forecast.md`, `results/opponent_forecast_*.json`. Still open: an interaction between the two teams' styles. |
| 1.2 | **Done (RQ1, second part).** The grade repeated on Wyscout 2017/18, five leagues. | Same letter in 21 of 29 statements (72%; rule fixed beforehand 70%), none two letters apart: the grades hold, just. | – | `docs/protocol_evidence_grade_wyscout.md`, `results/evidence_grade_wyscout.json`. Still open: another season with the same provider, to separate provider and season effects. |
| 1.3 | **Why last 5 matches mislead.** The season so far beats the last 5 for 32 of 34 statements. Test weighted forecasts (more weight to recent matches, but not only the last 5). | Whether any recency weighting helps, or whether "use the season" is the rule for analysts. | S-M | Directly useful for practice. |
| 1.4 | **Grade for individual families.** F07/F08 (family shares) got C, with discrimination not applicable. Find a common measure across teams (for example the share of sequences close to a shared reference set) so discrimination can be computed. | Whether family shares can ever be more than C. | M | Methodological; needs care to avoid fitting on test teams. |
| 1.5 | **Literature, systematic.** Database search (Scholar, Scopus, SPORTDiscus), forward citations of Franks et al. 2016, full reading of Matteo et al. 2026 and Deb et al. 2023. | Whether "to our knowledge, first" holds. | S | Must be done before submission anyway (`docs/related_work_evidence_grade.md`). |

## 2. Validation with people

| # | Idea | What it would show | Cost | Notes |
|---|---|---|---|---|
| 2.1 | **Analyst review** (kit ready: `docs/analyst_review_kit.md`, Review page in the app). | Whether families make sense to a practitioner; which parts of the report they would use. | L (needs people) | LASK Linz only with the supervisor's consent. |
| 2.2 | **Judge random sequences, not only typical ones.** Today the 3 sequences judged per family are the 3 closest to the family centre, which favours "yes". Add, for example, 3 sequences drawn at random from the family, with a fixed seed. | A fairer test of whether the families hold beyond their centre. | S | Decide and commit before the first review. |
| 2.3 | **Several reviewers, agreement.** With 3 or more reviewers, measure agreement (for example Fleiss' kappa) on the yes/partly/no judgements. | Whether the families are seen the same way by different analysts. | L | Depends on 2.1. |
| 2.4 | **Time-saving study.** Same task (prepare a one-page opponent brief) with and without the tool, timed. | The claim "it saves time", which today cannot be made. | L | Needs analysts and a small design. |

## 3. App and tool

| # | Idea | What it would show | Cost | Notes |
|---|---|---|---|---|
| 3.1 | **"Time machine" page.** A slider over the matchdays. For each date it shows the report built only from earlier matches, with the 80% interval, then the actual value of the next match (inside or outside) and the league-average forecast. Play animates the season. | It shows the evidence grade at work: A statements usually hit, D statements do not, and the last 5 matches mislead. It also gives a test bench for 1.1 and 1.3, where a new forecast is one more row. | M | Display of the existing procedure on the report teams: not a new test, the grades do not change. Strong for presentations. |
| 3.2 | **Provenance of every number.** Click a number to see the script, the result file, the protocol and the commit it comes from. | Reproducibility made visible; useful to examiners and other researchers. | S-M | |
| 3.3 | **Only-trusted-statements mode.** The coach sheet and key points can be limited to A/B statements, with C/D available on demand. | An application of the grade to the report itself. | S | Needs a careful default: hiding C/D must not hide negative results. |
| 3.4 | **Keyboard shortcuts** for clips and replays (play/pause, next clip, mark yes/partly/no). | Faster use for analysts; found in the design critique of 22 Oct. | S | |
| 3.5 | **Test the XML export in a real video tool** (Sportscode, Nacsport). | Whether the clip export works in practice; today it is untested. | S (needs access to the software) | |
| 3.6 | **Club data through the adapter.** Map a real club or provider export to the generic CSV (`src/adapters/generic_csv.py`) and run the round-trip check. | Whether the tool works outside open data. | M (needs data) | |
| 3.7 | **Reference set option for CSV reports.** With `--csv` the report has no other teams to rank against; allow choosing a reference folder. | Ranks for club data. | S | |

## 4. Other analyses (kept out of the thesis core)

| # | Idea | What it would show | Cost | Notes |
|---|---|---|---|---|
| 4.1 | **L3 corners redesign.** Data-driven zones, one continuous predictor, protocol first; Euro 2020/WC 2022 for exploration, Euro 2024 held out. | Whether corner set-ups are exploitable, with a test that has power (today p = 0.17 / 0.41, low power). | M | Option A in CLAUDE.md; decide with the supervisor. |
| 4.2 | **Tracking on the report teams.** Pitch control and defender ghosting are now only on 7 DFL matches of other teams. With tracking for the report teams, add off-ball information (for example the defensive line). | Whether off-ball data changes the families or the grade. | L (needs data) | Today's tracking results say nothing about the 10 teams. |
| 4.3 | **Families by tracking context.** Split build-up families by the opponent's pressing shape from tracking. | Whether the families mean different things against different blocks. | L | Depends on 4.2. |

## 5. Maintenance found during the work

| # | Item | Cost |
|---|---|---|
| 5.1 | Team names that differ between the match list and the event file ("Marseille" vs "Olympique de Marseille", "Caen" vs "Stade Malherbe Caen"): handled in the evidence grade, not yet in the report pipeline. A report on these teams would show empty matches. | S |
| 5.2 | The app reads every report in the data folder: a folder cleanup or an "include in reference" switch would avoid accidental reference teams (now teams below 8 matches are excluded automatically). | S |

## Suggested order
1. Before submission: 1.5 (literature), 2.2 then 2.1 (review), 5.1.
2. If there is time: 3.1 (time machine), because it shows the main contribution.
3. After the thesis or as a follow-up paper: 1.3 (recency-weighted forecasts), the open points of 1.1 and 1.2, 2.3-2.4 (studies with analysts).
