# Matches needed: after how many matches can each statement be trusted? (exploratory)

Written on 16 November 2026, before any run of `src/analysis/exploratory_trust_n.py` on the confirmatory teams (one development run, see below). This study is **exploratory**: it adds an explanation next to the A-D grade and does not change the grade, its thresholds or its results.

## Question
The evidence grade (`docs/protocol_evidence_grade.md`) says whether a type of statement can be trusted, as one letter for the whole season. An analyst preparing a match in October has seen only a few of the opponent's matches and asks a more practical question: **after how many matches does this statement describe the team's style more than chance?** This study turns the discrimination D of each statement into a number of matches, checks whether that number holds on the first matches of real seasons, and writes a fixed text that explains each grade.

## What was already seen before this protocol (declared)
- The grade results (`results/evidence_grade_corrected.json`, 70 confirmatory teams): D, skill and their intervals per statement.
- An exploratory derivation check (November 2026, local notes, not in the repo) showed that under a simple model D is the reliability of a season mean, `n* = sigma^2 / tau^2` can be recovered from D, and the skill predicted from D matches the observed skill (Pearson r = 0.96 over 32 statements). It already pointed at D24 (below the curve) and K33, K34 (above; not included here). **Section "Off-curve statements" below is therefore descriptive and not a test.**
- No D on the first n matches of a season was computed on the confirmatory teams. On 16 November the script was run on the 9 development teams to check the code (`results/exploratory_trust_n_dev.json`): with 9 teams the first-n D is very noisy (median |gap| 0.14 at n = 5, 0.07 at n = 8 and 12, 0.02 at n = 20; formula does not hold by the rule below). After that run only the code was changed (a text rule for equal numbers of matches); no threshold, level or grid value.

## Data
- The **70 confirmatory teams** of the evidence grade, StatsBomb 2015/16, with the correction of note 1 of `docs/protocol_evidence_grade.md`. Per-match values as extracted for the grade (one pickle per team, `evidence_grade.py extract`). No new extraction.
- D, skill and their intervals: read from `results/evidence_grade_corrected.json`, not recomputed.
- Development: the 9 development teams (`results/evidence_grade_dev.json`) are used once to check the code. Their output is kept as `results/exploratory_trust_n_dev.json` and labelled development.

## Statements
The 30 scalar statements of the grade: S01-S06, R09-R13, P14-P17, T18-T22, D23-D28, A29-A32.
- F07, F08 (family shares) have no D: not included.
- K33, K34 (main-player shares) are not included: the season leader and the leader so far are different constructions (see the derivation check), so the formula does not apply. Their grade and D stay as in the grade results.

## Measures (fixed)
**1. Matches for a statement to separate teams (n\*).** Under the model "match value = team style + match noise", with tau^2 the variance of styles between teams and sigma^2 the noise of one match:
- reliability of the mean of n matches: `R(n) = n / (n + n*)`, with `n* = sigma^2 / tau^2`;
- the grade's D is, up to a small term, the reliability of a full season: `D = R(N) + (1 - R(N)) / N`.

For each statement:
- `N` = forecasts / teams + 5 (mean number of matches per team for that statement, from the result file);
- `R_N = (N D - 1) / (N - 1)`; if `R_N <= 0` the statement is "never reliable";
- `n* = N (1 - R_N) / R_N`.

**2. Matches needed.** `n(R) = n* R / (1 - R)` for two levels fixed now:
- **R = 0.50, "starts to say something":** style and chance weigh the same. Equivalently, from about n* matches on, the team's own mean predicts its next match better than the league mean.
- **R = 0.75, "reliable":** three quarters of the observed difference between teams is style.
- If `n(R)` is greater than N, the label is "not within one season".

**3. Check on the first n matches (the test of this protocol).** For n in {3, 5, 8, 12, 20}:
- D_obs(n) = `discrimination()` of `evidence_grade.py`, unchanged (500 bootstrap draws, seed 7), on the **first n matches by date** of each of the 70 teams;
- D_pred(n) = `R(n) + (1 - R(n)) / n`, with R(n) from the n\* of measure 1;
- gap(n) = D_obs(n) - D_pred(n), per statement.

Reading (fixed in advance):
- **The formula holds** if, for every n in {5, 8, 12, 20}, the median |gap| over the 30 statements is at most **0.10**. n = 3 is reported but does not enter the reading: too noisy.
- A statement is flagged **"uncertain estimate"** if |gap(12)| > **0.20**.
- If the formula does not hold, the app uses the observed curve instead: R_obs(n) = (n D_obs(n) - 1) / (n - 1) (the same correction as in measure 1), and matches needed = the smallest n in the grid with R_obs(n) >= R, otherwise "more than 20". This fallback is fixed now.

**4. Off-curve statements (descriptive).** Predicted skill from D: `skill_pred = (1 - n* H) / (1 + n*)`, with `H` the mean of 1/k over the forecasts of the grade (k = 5 ... N - 1 past matches). A statement is **below the curve** if the upper bound of its observed skill interval is below skill_pred, **above the curve** if the lower bound is above. Below the curve is read as "the past predicts the next match worse than its D implies": a possible change of style during the season, or league differences that D pools and the forecast does not. Reported with the last-5 comparison of the grade, no further test.

**5. Text of the grade (fixed rules, no language model).** Each part of the text comes from one number:
- D >= 0.7 / 0.5-0.7 / < 0.5: "teams differ a lot / somewhat / little in this number (mostly chance)";
- skill interval lower bound >= 0.10 / > 0 / otherwise: "the season so far predicts the next match much better / a little better / not better than the league average";
- matches needed (measure 2 or the fallback of measure 3) and the number of matches the analyst has seen: "starts to say something after about X matches, reliable after about Y; you have seen Z";
- the flags of measures 3 and 4, when present ("uncertain estimate", "may change during the season").

**6. Sensitivity (secondary, fixed now).** The same numbers are also reported for the levels R = 0.60 and 0.80, and the reading of measure 3 is also reported with the thresholds 0.05 and 0.15 for the median |gap|. Only the primary values (0.50, 0.75, 0.10, 0.20) enter the app and the text; the others show how much the conclusions depend on the conventions.

## Output
`results/exploratory_trust_n.json` (and `_dev.json`): per statement N, R_N, n\*, matches for R = 0.50 and 0.75, D_obs(n) and gap(n) for every n, flags, skill_pred and the off-curve label; the median |gap| per n and the reading of measure 3. The app shows the text of measure 5 next to each grade letter.

## Procedure
1. The script is written and checked on the 9 development teams (`--set dev`). Only the code is fixed after this step, no threshold.
2. This protocol and the script are committed and pushed. The script refuses to run on the confirmatory set if they differ from the last commit, the commit is not on origin/main, or the result file exists.
3. One run on the 70 confirmatory teams; the result file is committed unedited.

## Known weaknesses
- The model assumes the style does not change during the season and that matches are independent. A change of coach or system makes the number of matches too optimistic; measure 3 (first matches only) and measure 4 are the checks.
- D pools four leagues, the forecast does not: league differences can make D look better than the forecast (a possible reason for D24).
- One number per type of statement, not per team: a team with a very stable or very unusual style may need fewer or more matches.
- The two levels (0.50, 0.75) and the thresholds of measure 3 (0.10, 0.20) are conventions chosen before the run.
- The first n matches of a season are early-season matches (new signings, early fixtures): this is what an analyst sees in autumn, but it can differ from a random set of n matches.
- Exploratory: the same 70 team-seasons were used for the grade.
