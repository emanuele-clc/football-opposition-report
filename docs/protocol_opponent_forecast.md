# Opponent- and venue-adjusted forecast (RQ2): does knowing the next opponent and the venue improve the next-match forecast?

Written on 28 October 2026, before any confirmatory run of `src/week4/forecast_opponent.py`. Before this protocol: one development run on the 9 StatsBomb development teams of the evidence grade (`results/exploratory_opponent_forecast_dev.json`, exploratory), which chose k and the venue term; a code check of the confirmatory path on the 2 Wyscout development teams (output not kept).

## Question
The evidence grade forecasts a team's next match with its season so far and ignores who it plays and where. The grade protocol calls this a floor: an analyst would adjust. RQ2: **does a forecast that also uses the next opponent and the venue predict the next match better than the season average, and does it change which statements can be trusted?**

## Data
- StatsBomb 2015/16, four leagues: the **70 confirmatory teams** of the evidence grade, with the correction of note 1 of `docs/protocol_evidence_grade.md` (team-matches without the team's events dropped). Per-match values as extracted for the grade.
- Wyscout 2017/18, five leagues: the **96 confirmatory teams** of `docs/protocol_evidence_grade_wyscout.md`. Per-match values as extracted for that grade.
- Development teams (9 StatsBomb, 2 Wyscout) are not forecast. As in the grade, all teams of a league enter the league values and as opponents.
- None of the 166 teams was forecast with the adjusted forecast before this protocol.

## Statements
The scalar statements of the grade: 30 on StatsBomb (S01-S06, R09-R13, P14-P17, T18-T22, D23-D28, A29-A32), 25 on Wyscout (the same without D24, D25, D28, A30, A32). Families (F07, F08) and main players (K33, K34) are not adjusted and keep their grade.

## Forecast (fixed; definitions in the header of the script)
For team X, match t (from the 6th match, as in the grade), date d, opponent Y:
- F = X's season so far (the grade's forecast).
- L = league value before d (all team-matches of the league before d, ratio of sums).
- A_Y = what Y's opponents did against Y before d (ratio of sums over Y's matches before d).
- w_Y = n_Y / (n_Y + 5), n_Y = Y's matches before d.
- V = (H - A) / 2, with H and A the league values of home and away team-matches before d; + V if X is at home, - V if away.
- **F_adj = F + w_Y (A_Y - L) + V**, kept in [0, 1] for shares and >= 0 otherwise.

k = 5 and the venue term were chosen in the development run: with the venue term, k = 5 gave the highest median improvement over the 30 statements (+0.102; k = 3: +0.102, k = 10: +0.099, k = 1: +0.099, k = 20: +0.089; without the venue term at most +0.059).

## Measures
- **Improvement** per statement = 1 - sum w (y - F_adj)^2 / sum w (y - F)^2, w = denominator of match t (as the grade's skill); 95% interval by bootstrap over teams (2000 resamples, seed 2029). Verdict: **adjusted better** if the lower bound > 0, **adjusted worse** if the upper bound < 0, otherwise **no difference**.
- **Answer per provider (reading fixed in advance):** the adjusted forecast **helps** if it is better for at least 50% of the statements and worse for at most 10%; **helps for some statements** if it is better for at least 20%; otherwise it **does not help**. The thresholds are conventions chosen before the run.
- **Grades with the adjusted forecast (secondary):** the forecast verdict is recomputed from the skill of F_adj against the league average B (same thresholds: strong if the lower bound >= 0.10, weak if > 0), discrimination is unchanged (it does not depend on the forecast), same grade rule. Reported: the statements whose letter changes, and the new count of A-D.
- Also reported: median improvement over the statements; statements better on both providers.

## Procedure
1. This protocol and the script are committed and pushed. The script refuses to run if they differ from the last commit, the commit is not on origin/main, or the result file exists.
2. One run per provider, once: `results/opponent_forecast_statsbomb.json`, `results/opponent_forecast_wyscout.json`, committed unedited.

## Known weaknesses
- The opponent effect is the opponent's average against all its past opponents; it ignores how the opponent's style matches X's (no interaction).
- The venue term is the same for every team of a league.
- Early in the season the opponent effect is small (shrinkage) and noisy.
- The development run chose k among five values and the venue term on 9 teams: the confirmatory improvement may be smaller.
- Thresholds are conventions; 30 and 25 statements, no correction for multiple comparisons.
- A better forecast does not say that an analyst using it prepares better.
