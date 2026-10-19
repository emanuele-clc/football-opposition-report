# Evidence grade: how far can each statement of an opposition report be trusted?

Written on 19 October 2026, before any run of `src/week4/evidence_grade.py` on real numbers. Only a smoke test was run before this protocol was committed: it executes the code on 2 development teams and 8 matches and prints counts of rows, never a metric, a skill or a grade.

## Question
An opposition report is a list of statements: "their goal kicks go short 40% of the time", "PPDA 12.6", "B2 is a quarter of their build-up", "Wirtz receives most build-up passes". Analysts act on them, but nobody measures whether they hold. This study gives every type of statement in our report a grade from two measured properties:

1. **Forecast:** does the number computed from a team's past matches describe its *next* match better than assuming the team is an average team of its league?
2. **Discrimination:** over a full season, does the number separate teams, or is most of the variation between teams sampling noise? (Franks, D'Amour, Cervone and Bornn 2016, "Meta-analytics".)

Two more properties are reported without entering the grade: how well calibrated an 80% prediction interval for the next match is, and how many matches the number needs.

The study grades the *type of statement* (e.g. "share of short goal kicks"), not one team's value. It does not test whether acting on a statement helps win.

## Data
- StatsBomb Open Data, complete 2015/2016 seasons of Premier League, La Liga, Serie A and Ligue 1 (1,517 matches, 80 teams, 37-38 matches each), events already on disk (`ev/`, list in `data_info/`).
- **Development set (9 teams):** the thesis teams of these seasons (Leicester City, Arsenal, Barcelona, Atlético Madrid, Real Madrid, Napoli, Sassuolo, Gazélec Ajaccio, Bordeaux). Used to check the code, then reported as development, never pooled with the confirmatory set.
- **Confirmatory set (70 teams):** every other team of the four leagues, except Juventus (its events were used in a check on 18 Oct). These teams were never the subject of an analysis. Known contacts with their data: their matches against the thesis teams entered the thesis teams' sheets as opponent events; on 18 Oct the pipeline was run on teams with 2-4 matches on disk as a technical pass/fail check. None of their own season values was studied.
- Bayer Leverkusen 2023/24 is excluded: no league data for the baseline.
- All 80 teams are extracted, because the baseline needs the rest of the league.

## Statements graded (fixed before the run)
Each statement is computed per match as a numerator and a denominator, with the definitions of the script that produces it in the report (same code, imported). A season value is sum of numerators / sum of denominators, which is exactly how the report computes it.

| id | statement | from | numerator / denominator per match |
|---|---|---|---|
| S01 | open-play sequences per match | sequences_clustering | sequences / 1 |
| S02 | passes per sequence | sequences_clustering | passes / sequences |
| S03 | long-pass share of a sequence | sequences_clustering | sum of per-sequence long share / sequences |
| S04 | share of sequences starting in own build-up zone (x < 45) | sequences_clustering | / sequences |
| S05 | shot rate per sequence | sequences_clustering | sequences with a shot / sequences |
| S06 | sequence duration (s) | sequences_clustering | sum of durations / sequences |
| F07 | share of each build-up family (k = 5) | report method | sequences in the family / build-up sequences |
| F08 | share of each advanced family (k = 3) | report method | sequences in the family / advanced sequences |
| R09 | goal kicks: first pass short (< 30 m) | restarts | / goal-kick possessions |
| R10 | goal kicks: reached the opponent half | restarts | / goal-kick possessions |
| R11 | goal kicks: ended in own half | restarts | / goal-kick possessions |
| R12 | keeper distributions: first pass short | restarts | / keeper possessions |
| R13 | throw-ins in own half: ended in own half | restarts | / throw-ins in own half |
| P14 | corners per match | setpieces | corners / 1 |
| P15 | corners played short / outside the box | setpieces | / corners |
| P16 | corners to the far post | setpieces | / corners |
| P17 | corners ending in a shot | setpieces | / corners |
| T18 | open-play losses per match | transitions | losses / 1 |
| T19 | losses in own third | transitions | / losses |
| T20 | counter-press regains within 5 s | transitions | / losses |
| T21 | recoveries in the final third | transitions | / recoveries |
| T22 | recoveries followed by a shot within 10 s | transitions | / recoveries |
| D23 | PPDA | defending | opponent passes / defensive actions (same areas as the sheet) |
| D24 | pressures per match | defending | pressures / 1 |
| D25 | pressures in the final third | defending | / pressures |
| D26 | height of defensive actions (mean x) | defending | sum of x / defensive actions |
| D27 | shots conceded per match | defending | shots / 1 |
| D28 | xG conceded per match | defending | xG / 1 |
| A29 | shots per match | events (mirror of D27) | shots / 1 |
| A30 | xG per match | events (mirror of D28) | xG / 1 |
| A31 | xT added per match | xthreat | xT / 1 |
| A32 | pass completion under pressure in own half | keyplayers | completed / passes under pressure |
| K33 | share of build-up receptions of the main receiver | keyplayers definition | receptions of the leader / build-up receptions |
| K34 | share of corners taken by the main taker | setpieces | corners of the leader / corners |

Families (F07, F08): fitted as in the report (StandardScaler + K-Means on the 11 features, n_init 20, random_state 0, ordered by mean start x) on the first half of the team's matches (floor(n/2)) and frozen. Each family of each team is one item. Leaders (K33, K34): the player with the most receptions / corners so far.

## Measures
**Forecast skill (enters the grade).** For each team and each match t with at least 5 earlier matches of the team (families: t after the fitting half):
- report forecast F = season so far (matches before t), sum of numerators / sum of denominators;
- baseline B = the same statement computed on all other teams of the same league, matches played before the date of t (for families: the other teams' sequences assigned to this team's frozen families; for leaders: the mean, over the other teams with 5+ matches, of their own leader's share so far);
- observed y = numerator / denominator of match t; matches with denominator 0, or with no data so far, are skipped.
- Skill = 1 - sum w (y - F)^2 / sum w (y - B)^2, with w = denominator of match t (a match with more goal kicks says more about the goal-kick share). Pooled over teams, matches and, for F07/F08, families.
- 95% interval: bootstrap over teams (2000 resamples, seed 2029).
- Verdict: **strong** if the lower bound >= 0.10; **weak** if the lower bound > 0 and < 0.10; **none** otherwise.

**Discrimination (enters the grade).** Season value of each confirmatory team (all its matches). Sampling variance of each team's value: bootstrap over its matches (500 resamples, seed 7; leaders fixed to the season leader). D = 1 - mean sampling variance / variance of the season values across teams. 95% interval by bootstrap over teams (1000, seed 8), reported; the grade uses the point value. **High** if D >= 0.7, **medium** if 0.5 <= D < 0.7, **low** otherwise. Not computed for F07/F08 (each team has its own families; there is no common quantity across teams): marked n/a.

**Calibration (reported, not graded).** 80% prediction interval for the next match: F +/- t(0.90, h-1) * sqrt(s^2 (1/den_t + 1/sum den_past)), with h past matches with denominator > 0 and s^2 = sum den_s (y_s - F)^2 / (h - 1); needs h >= 3. Coverage = share of next-match values inside. Label: "about right" 0.75-0.85, "too narrow" below, "too wide" above. Interval of coverage by bootstrap over teams.

**Matches needed (reported, not graded).** For n = 3, 5, 8, 10, 15, 20: per team, 300 random draws of n matches (seed 11), 90th percentile of |value from n matches - season value|; median over teams divided by the between-team SD. Matches needed = the smallest n with ratio <= 0.5 (">20" if none). Same criterion as `sample_size.py`. n/a for families.

**Last 5 vs season so far (secondary).** The report shows "last 5" next to the season value. Skill of the last-5 forecast relative to the season-so-far forecast, on the same forecasts, interval over teams: last 5 better / worse / no difference.

## Grade (decision rule)
- **A:** forecast strong and discrimination high.
- **B:** forecast at least weak and discrimination at least medium, not A. Families (D n/a): B if forecast strong.
- **C:** only one of the two (forecast at least weak, discrimination at least medium). Families: C if forecast weak.
- **D:** neither.

Every grade is reported and will be shown in the report and app next to the statement as computed, including D. A D statement is kept in the report with the label, not removed (removing it would hide a negative result).

## Pre-registered sanity checks
Two expectations from earlier work, written down so that a failure is visible:
- SC1: T20 (counter-press share) has low discrimination (it was 17-19% for all teams tested).
- SC2: S02 (passes per sequence) has high discrimination and a strong forecast (it separated teams in the sample-size study).

If a sanity check fails it is reported and discussed; nothing is changed to make it pass.

## Procedure
1. This protocol and the script are committed and pushed before step 2. The script refuses both runs if the protocol or the script differ from the last commit or the commit is not on origin/main, and refuses to overwrite an existing result.
2. Development run on the 9 development teams (`--set dev`), only to check the output: `results/evidence_grade_dev.json`. Nothing in this protocol is changed after it; a code bug found here is fixed in a separate commit described in a dated note at the end of this file, before step 3.
3. Confirmatory run once on the 70 teams: `results/evidence_grade.json`, committed unedited.

## Second provider (part 2, label only)
After step 3, `src/week4/evidence_provider.py` computes the statements that the generic CSV supports (S01-S06, F07-F08, R09-R13, P14-P17, T18-T22, A29, K34; not K33, because the generic CSV has no pass outcome) on the 36 Barcelona 2017/18 matches present in both StatsBomb and Wyscout public data (pairing as in `exploratory_provider_samematch.py`). Label per statement: **same in Wyscout** if |season value Wyscout - StatsBomb| <= 0.5 x between-team SD of the confirmatory set, otherwise **differs**; families: largest share difference <= 0.10. Per-match Pearson correlation reported. Statements not computable from Wyscout: "not testable". The label does not change the grade. Not blind: S01-S06, F07-F08, R09, R12 and P14 (and losses per match, T18) were already compared on these matches on 18 Oct (`results/exploratory_provider_samematch_Barcelona.json`); those labels are marked "seen before".

## Known weaknesses
- One season (2015/16) and one provider for the grade; 2015/16 data are older than current StatsBomb collection.
- The baseline "average team of the league" is a weak opponent for statements where all teams are alike; a strong forecast against it means "knowing this team helps", not "the forecast is accurate".
- Next-match values with small denominators (3-6 goal kicks, 4-8 corners) are noisy; low skill can come from the match, not the statement.
- No adjustment for opponent, venue or line-up: an analyst would adjust, so the forecast is a floor.
- Thresholds (0.10, 0.5, 0.7, 0.75-0.85) are conventions chosen before the run, not derived.
- 34 statement types, no correction for multiple comparisons; grades are descriptive.
- Discrimination mixes league and team differences (four leagues pooled).
- Family shares in the history before the fitting point are in-sample (as in the report).
