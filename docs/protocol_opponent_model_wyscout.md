# Opponent style groups on a second provider: does the result of proposal B replicate on Wyscout? (exploratory)

Written on 27 November 2026, before any run of `src/analysis/exploratory_opponent_model_wyscout.py`. **Exploratory**, like the original (`docs/protocol_opponent_model.md`, result `results/exploratory_opponent_model.json`, commit fd927fc). It does not change the grades, RQ2 or the StatsBomb result.

## Why
The StatsBomb run gave: 23 of 30 statements change with the style group of the next opponent (stable: R10, R11, R12, P15, P16, P17, A32); the groups do not replace the single opponent for forecasting; the random forest adds little (better in 6 of 30, median +0.004). That is one provider and one season per league. Before the result is shown to the analyst it is repeated, **with the same method and no change of model**, on other data: Wyscout 2017/18, five leagues, other teams and another season. Trying other models after seeing the StatsBomb numbers was considered and not done: the bottleneck is chance in a single match (median share of chance about two thirds) and two matches per opponent, not the model.

## Question
**R1 (main).** Does each statement get the same label (changes with the opponent's style / stable) on Wyscout as on StatsBomb?
**R2.** Do the readings of Q2 (groups vs single opponent) and Q3 (random forest vs groups) of the original protocol come out the same?

## What was already seen before this protocol (declared)
- The whole StatsBomb result of proposal B (labels, effects, groups, silhouettes), shown in the app on 27 November.
- On Wyscout, the same team-seasons were already used for the grade (`results/evidence_grade_wyscout.json`) and RQ2 (`results/opponent_forecast_wyscout.json`: the single-opponent forecast helps for 18 of 25 statements). No clustering, mixed model or random forest was ever fitted on Wyscout data.

## Data (fixed)
- Wyscout public data 2017/18 (Pappalardo et al. 2019, CC BY 4.0): Premier League, Ligue 1, Bundesliga, Serie A, La Liga; the 98 extracted teams of the Wyscout grade (`C:\Users\ecole\evidence_work\wyscout`, `evidence_grade_wyscout.py extract`), home team from the converted match lists (`C:\Users\ecole\wyscout_generic\<country>\matches\generic.json`), as in RQ2 on Wyscout.
- Forecast subjects: the **96 confirmatory teams** of the Wyscout grade. Barcelona and Napoli (development teams of the Wyscout grade) are used only for the development run. All 98 teams enter the league values, the groups and the models.

## Method (identical to `docs/protocol_opponent_model.md`, except the points below)
The script imports the functions of the StatsBomb script and changes only the data and the lists below; groups (k-means, k = 3, 20 starts, seed 2031, past matches only, standardised within the league), the five forecasts F, R (k = 5), G, M, RF (same features and settings, trained on the first half), comparisons on the second half (bootstrap over teams, 2000, seed 2031), Q4 shares and group effects, silhouettes: all unchanged.

Forced differences (Wyscout has no pressures and no xG; `docs/protocol_evidence_grade_wyscout.md`):
- **Statements:** the 25 scalar statements Wyscout can compute: S01-S06, R09-R13, P14-P17, T18-T22, D23, D26, D27, A29, A31. Not available: D24, D25, D28, A30, A32.
- **Without the ball** (paired with the opponent's attacking groups): D23, D26, D27, T20, T21, T22 (6). **With the ball** (paired with the defensive groups): the other 19.
- **Attacking style:** S02, S03, R09, R12 (as on StatsBomb). **Defensive style:** D23 and D26 only (D25 needs pressures).
- The Bundesliga has 18 teams (groups of about 6).
- Known definition differences of the provider (reconstructed possessions, about twice as many duels in the defensive actions of PPDA and defensive height, goal kicks without a start position) are those of the Wyscout grade.

## Reading (fixed in advance)
- **R1.** On the 25 statements present in both: share with the **same label** on both providers, with a 95% Wilson interval (indicative: the statements are not independent). The StatsBomb labels are taken from `results/exploratory_opponent_model.json` unchanged (StatsBomb used the defensive groups with D25; declared). The result **replicates** if at least 70% of the 25 have the same label (18 of 25), **partly replicates** if at least 50% (13 of 25), otherwise **does not replicate**. Same conventions as the Wyscout grade.
- **R2.** Q2 and Q3 are read with the thresholds of the original protocol on 25 statements: Q2 "groups can replace the single opponent" if G is worse than R for at most 10% (2 of 25) and worse than M for at most 10%; Q3 "the random forest adds something" if better than G for at least 20% (5 of 25) and worse for at most 10%. Each reading is **the same** or **different** from StatsBomb.
- Also reported, not read: the list of statements whose label changed; for every statement both improvements G vs F; the Wyscout groups and effects per league.

## Output
`results/exploratory_opponent_model_wyscout.json`: the same fields as the StatsBomb result, plus `replication` (R1 counts, share, interval, reading, list of changed labels; R2 readings).

## Procedure
Protocol and script committed and pushed first; one development run on Barcelona and Napoli (`--dev`, `results/exploratory_opponent_model_wyscout_dev.json`), only to check that the code runs; a bug found there is fixed in a separate commit, nothing else changes; one run on the 96 teams; result committed unedited. The script refuses to run if the result file exists or if the protocol or the scripts differ from the pushed commit.

## Known weaknesses
- Provider, season, leagues and teams change at once: a different label cannot be attributed to one of them.
- The defensive groups use two values instead of three, so the 19 "with the ball" statements are paired with slightly different groups than on StatsBomb.
- PPDA and defensive height are defined on different defensive actions in the two providers.
- One season per league again; the groups of the first rounds rest on few matches.
- 25 statements, no correction for multiple comparisons; thresholds are conventions.
