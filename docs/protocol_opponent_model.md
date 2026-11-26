# Opponent style groups: does a statement change with the style of the opponent? (exploratory, proposal B)

Written on 26 November 2026, before any run of `src/analysis/exploratory_opponent_model.py` on the confirmatory teams. **Exploratory**: it extends RQ2 (`docs/protocol_opponent_forecast.md`) and adds a measure of stability next to the A-D grade. It does not change the grade, the RQ2 result or their files. It replaces the draft of 19 November (single-opponent mixed model only), which was never run.

## Why groups
RQ2 moves the forecast by what the next opponent usually allows, with a weight `n_Y / (n_Y + 5)` chosen by hand. In a league a team meets each opponent only twice, so the effect of one opponent rests on very few matches. The analyst (D. Gallo, email of 25 November 2026) suggested grouping teams that attack in a similar way and checking how the defensive numbers change against each group, and the reverse (groups by how teams defend, offensive numbers). The supervisor agreed (26 November 2026): aggregating similar teams gives more data and more reliable forecasts. Her earlier notes (16 November) still hold: only pre-match information, a mixed-effects model as the reference, the random forest only as a check, opponent information from past matches only.

## Questions
1. **Q1 (stability).** For each statement, does knowing the style group of the next opponent forecast the next match better than the team's season so far? If yes, the statement "changes with the opponent's style"; if not, it is "stable" with respect to style.
2. **Q2.** Is the group model at least as good as the RQ2 forecast (single opponent, k = 5) and as a mixed model with the single opponent? If yes, the groups can replace the single opponent in the app, with a reading an analyst understands ("against teams that build up short...").
3. **Q3.** Does a random forest on the same pre-match information add anything over the group model?
4. **Q4 (descriptive).** For each statement, how much of the variance of one match value is the team, the opponent's style group, the rest of the opponent, the venue and chance; and how the statement moves against each group.

Score state and sending-offs happen during the match: they explain, they do not forecast, and are not used (sending-offs: `docs/protocol_red_cards.md`).

## What was already seen before this protocol (declared)
- The grade (`results/evidence_grade_corrected.json`), RQ2 (`results/opponent_forecast_statsbomb.json`, `..._wyscout.json`, `results/exploratory_opponent_forecast_dev.json`), the red cards and redundancy results.
- The supervisor's note: RQ2 with opponent and venue raises the skill of PPDA from 0.02 to 0.28, of pressures in the final third from 0.04 to 0.15, of defensive height from 0.04 to 0.19.
- No clustering of teams and no mixed model or random forest was fitted on any team before this protocol (the 19 November development run stopped before any result). The script is run once on the 9 development teams (`results/exploratory_opponent_model_dev.json`) **only to check that the code runs**; nothing below is changed after that run, except bugs in the code (declared in the commit if any).

## Data
The 80 extracted teams of the grade (StatsBomb 2015/16: Premier League, La Liga, Serie A, Ligue 1), per-match values from `evidence_grade.py extract`, with the correction of note 1 of the grade protocol. Forecast subjects: the **70 confirmatory teams**. All 80 teams enter the league values, the groups and the models, as team and as opponent. Wyscout is not used.

## Style groups (fixed)
- **Attacking style** of a team: its season-so-far value of S02 (passes per sequence), S03 (long-pass share), R09 (goal kicks: first pass short), R12 (keeper: first pass short). Grades A, A, A, B; S06 and A32 are left out because they are redundant with S02 (`results/exploratory_redundancy.json`).
- **Defensive style**: its season-so-far value of D23 (PPDA), D25 (pressures in the final third), D26 (height of defensive actions).
- At every forecast date d, separately for each league and each style: the values of the 20 teams over their matches before d, standardised across the teams of the league (z-score; a team with no value yet gets 0), then **k-means with k = 3** (20 starts, seed 2031). k = 3 is fixed in advance: with 20 teams it gives groups of about 6-7 teams, enough matches per group, and the analyst expected coarse groups. As a check only, the mean silhouette of k = 2, 3, 4, 5 on whole-season values is reported.
- Group numbers are arbitrary at each date; the models are refitted at each date, so only "same group or not" matters.
- There is only one season per league in the open data, so the previous season cannot be used for the first rounds: forecasts start from the team's 6th match, as in the grade, and the groups of the first rounds rest on few matches (declared weakness). With a club's data, the previous season would be used.

## Statements and pairing (fixed)
The 30 scalar statements of the grade. Each is paired with the style of the opponent that faces it:
- **Without the ball** (paired with the opponent's **attacking** groups): D23-D28, T20-T22 (9 statements).
- **With the ball** (paired with the opponent's **defensive** groups): S01-S06, R09-R13, P14-P17, T18-T19, A29-A32 (21 statements).

## Forecasts (fixed; all use only team-matches of the league before the date d of the forecast match)
For team X, match t (from the 6th match), opponent Y, venue h = +1/2 home, -1/2 away:
- **F** = X's season so far (the grade's forecast).
- **R** = RQ2: F + n_Y/(n_Y + 5) (A_Y - L) + V (as in `forecast_opponent.py`).
- **G (group model)** = mixed model on all league team-matches before d: `y = mu + v h + g[group of the opponent] + a_team + e`; g fixed (3 levels, sum to zero), a random (normal, own variance), e with variance sigma^2 / w (w = denominator of the match). Variance by REML, refitted at every date; the opponent group of every past row is the group of that opponent at date d. Forecast = mu + v h_X + g[group of Y] + a_X.
- **M (single-opponent model)** = the same with a random opponent effect b_opponent instead of g. Reference for Q2.
- **RF** = F + random forest prediction of y - F. Features (all from before d): F, X's last 5, X's past matches, A_Y - L, Y's past matches, venue (+1/-1), league home-away difference V, league value L, the effect g of Y's group estimated by G at date d, and Y's standardised style values (group numbers themselves change from date to date, so they are not used as a feature). Fixed settings: 500 trees, at least 20 forecasts per leaf, one third of the features per split, seed 2031, weights w. One forest per statement, trained on the forecasts of the **first half** of the season.
- Shares are kept in [0, 1], counts >= 0.

## Measures (fixed)
All comparisons on the **second half** of the season (forecasts from the league's middle date on), the same rows for every forecast.
- **Improvement of P over Q** = 1 - sum w (y - P)^2 / sum w (y - Q)^2; 95% interval by bootstrap over teams (2000 resamples, seed 2031). **Better** if the lower bound > 0, **worse** if the upper bound < 0, otherwise **no difference**. Pairs: G vs F (Q1), G vs R and G vs M (Q2), RF vs G (Q3), R vs F and M vs F for reference.
- Skill against the league average B (as in the grade) of F, R, G, M and RF.
- **Q4, whole season, descriptive:** per league, groups from whole-season values and the model `y = mu + v h + g[group] + a_team + b_opponent + e` (a, b random). Shares of the variance of one match value: team (tau_a^2), style group (variance of the fitted g over the rows), rest of the opponent (tau_b^2), venue (v^2 / 4), chance (sigma^2 / median w), each divided by their sum; median over the four leagues. Also the style part of the opponent = group / (group + rest of the opponent), and for each league the group effects g with the mean style values of each group, so that the groups can be named (for example "short build-up" or "direct").
- If RF is better than G for a statement: permutation importance on the second half (10 repeats, seed 2031). It explains the model, not football causes.

## Reading (fixed in advance)
- **Q1:** a statement **changes with the opponent's style** if G is better than F; otherwise it is **stable with respect to style**. In the app, the first kind says that the number should be read together with the next opponent's group.
- **Q2:** "the groups can replace the single opponent" if G is worse than R for **at most 10%** of the statements (3 of 30) and worse than M for at most 10%; otherwise the single opponent stays.
- **Q3:** "the random forest adds something" if it is better than G for **at least 20%** of the statements (6 of 30) and worse for at most 10%; otherwise "the readable group model is enough".
- Thresholds are conventions chosen before the run.

## Output
`results/exploratory_opponent_model.json`: per statement the comparisons, the skills, the Q4 shares and group effects, the Q1 label, the importance when computed; the silhouettes; the readings of Q1-Q3.

## Procedure
Protocol and script committed and pushed first; one development run (code check); one run on the 70 teams; result committed unedited. The script refuses to run if the result file exists or if the protocol or the scripts differ from the pushed commit.

## Known weaknesses
- One season per league: the groups of the first rounds rest on few matches, and teams can change style during the season.
- k = 3 is a convention; groups of 20 teams are coarse, as the analyst expected.
- The style of a team is measured by its raw season-so-far values, which also depend on whom it has played.
- The group effect is the same for every team (no interaction: a short build-up may suffer a high press more than a direct team).
- The noise term assumes variance proportional to 1 / w; for per-match counts all w = 1.
- The random forest is trained on the first half and tested on the second half of the same season.
- 30 statements, no correction for multiple comparisons. Exploratory, same team-seasons as the grade and RQ2.
