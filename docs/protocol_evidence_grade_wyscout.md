# Evidence grade on a second provider (RQ1): do the grades hold on Wyscout?

Written on 28 October 2026, before any run of `src/week4/evidence_grade_wyscout.py` on real numbers. Before this protocol was committed: the Wyscout adapter was extended (defensive actions, pass outcome; `docs/data_format.md`) and checked on the 36 Barcelona 2017/18 matches present in both providers (values of one team only, no forecast, no discrimination, no grade); the five leagues were converted and counted (matches, teams, events per type); a smoke test printed row counts only.

## Question
The evidence grade (protocol `docs/protocol_evidence_grade.md`, results `results/evidence_grade_corrected.json`) was computed on StatsBomb 2015/16, four leagues, 70 teams. A grade is only useful to an analyst if it does not depend on the data provider the club uses. RQ1, second part: **when the same statements, with the same method and the same thresholds, are graded on Wyscout data of other seasons and teams, do they get the same grade?**

A different grade does not say which provider is right. It says that the grade of that statement depends on the data (provider definitions, season, teams), and the tool must state which data a grade was computed on.

## Data
- Wyscout public soccer-logs (Pappalardo et al. 2019, Scientific Data 6:236, CC BY 4.0), season 2017/18: Premier League, Ligue 1, Bundesliga, Serie A, La Liga. 1,826 matches, 98 teams, 34-38 matches each. Converted with `src/adapters/wyscout_to_generic_csv.py` (team `ALL`) and `src/adapters/generic_csv.py` to `C:\Users\ecole\wyscout_generic\<country>`. No possession identifiers in this data: possessions are reconstructed (the same for every team; biased, see `docs/data_format.md`).
- **Development set (2 teams):** Barcelona (La Liga) and Napoli (Serie A), whose Wyscout matches were already looked at (18 Oct, 28 Oct; Napoli report on 17 Oct). Used to check the code, reported as development, never pooled with the confirmatory set.
- **Confirmatory set (96 teams):** every other team of the five leagues. No value of these teams was looked at.
- All 98 teams are extracted, because the league baseline needs the rest of the league.

## Statements graded
The 34 statement types of the original protocol, computed per match by the same code (`evidence_grade.match_values`, imported). **29 are computable from Wyscout:** S01-S06, F07-F08, R09-R13, P14-P17, T18-T22, D23, D26, D27, A29, A31, K33, K34. **5 are not** and are reported as "not testable": D24 and D25 (pressures), A32 (completion under pressure), D28 and A30 (xG). Known definition differences (do not change the method; they are why a grade may differ):
- PPDA (D23) and defensive height (D26): Wyscout defensive actions are mapped as in the adapter header; Wyscout has about twice as many duels as StatsBomb and no Ball Recovery or Block.
- possessions are reconstructed, so S01-S06, F07-F08 and the restart statements use reconstructed possessions.
- xT (A31) uses the grid fitted on StatsBomb (`src/report/xt_grid.json`), applied to Wyscout coordinates; Wyscout records few carries.
- goal kicks have no real start position in this data (six-yard box, side unknown).

## Measures and grade
Identical to `docs/protocol_evidence_grade.md`: forecast skill against the league average of the other teams (matches before the date), weighted by the denominator, pooled, 95% interval by bootstrap over teams (2000, seed 2029); strong if lower bound >= 0.10, weak if > 0; discrimination D (500 / 1000 resamples, seeds 7 and 8), high >= 0.7, medium >= 0.5; the same grade rule A-D; calibration, matches needed and last 5 reported, not graded. Families fitted on the first half of each team's matches. The two sanity checks SC1 and SC2 are reported again.

## Comparison with StatsBomb (the answer to RQ1)
For each of the 29 statement types: StatsBomb grade (`results/evidence_grade_corrected.json`) vs Wyscout grade.
- **Primary:** share of the 29 with the **same letter**, with a 95% Wilson interval (the statements are not independent: the interval is indicative).
- Secondary: share within one letter (A-B, B-C, C-D); agreement of the two parts separately (forecast verdict strong / weak / none; discrimination level high / medium / low, families n/a); weighted Cohen's kappa (linear weights) on the letters; the list of statements whose grade changed, with both skills and both D.
- **Reading fixed in advance:** the grades **hold** if at least 70% of the 29 have the same letter and none moves by two or more letters (e.g. A to C); **partly hold** if at least 50% have the same letter; otherwise **do not hold**. The thresholds are conventions chosen before the run, not derived.

## Procedure
1. This protocol and the script are committed and pushed before step 2. The script refuses the dev and confirm runs if they differ from the last commit, the commit is not on origin/main, or the result file exists.
2. Development run on the 2 development teams (`--set dev`): `results/evidence_grade_wyscout_dev.json`, only to check the output. A code bug found here is fixed in a separate commit described in a dated note at the end of this file, before step 3; nothing else in the protocol changes.
3. Confirmatory run once on the 96 teams (`--set confirm`): `results/evidence_grade_wyscout.json`, committed unedited, including the comparison.

## Known weaknesses
- Provider, season (2017/18 vs 2015/16), leagues (five vs four) and teams all change at once: a changed grade cannot be attributed to one of them.
- Reconstructed possessions for every Wyscout statement that uses possessions.
- Five statement types cannot be graded on Wyscout; they keep only the StatsBomb grade.
- Thresholds are conventions; 29 statement types, no correction for multiple comparisons; grades are descriptive.
- Barcelona and Napoli were looked at before; they are kept out of the confirmatory set.
