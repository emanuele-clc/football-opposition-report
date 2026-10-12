# Held-out validation protocol (L2)

Written on 12 October 2026, **before** any held-out match was analysed. The commit date of this file is the timestamp.

## What is being tested
Whether the sequence families found on the exploration matches (first 70% by date) still behave as found when applied, unchanged, to the held-out matches (last 30%).

| Team | Matches | Exploration | Held-out |
|---|---|---|---|
| Bayer Leverkusen 2023/24 | 34 | 24 | 10 |
| Leicester City 2015/16 | 38 | 27 | 11 |

## What is frozen
Everything is fitted on exploration matches only and never refitted on held-out ones: phase cut (x = 45), k (5 build-up, 3 advanced), the 11 features, the scaler, the K-Means centres (n_init = 20, random_state = 0), the ordering of the families, and the predictability model (logistic regression, C = 0.5, same inputs as week 3: play pattern, minute, half, previous family). Held-out sequences are only assigned to the nearest frozen centre.

Note: the extraction function reads all matches, but held-out sequences are filtered out before any analysis in weeks 1-3. Script: `src/week4/validate_holdout.py` (refuses to open held-out matches without `--confirm`).

## Hypotheses and pass criteria
**H1 (primary): out-of-sample predictability, build-up phase.** The log-loss gain of the model over the frequency baseline (baseline = family frequencies on exploration) is positive on held-out matches, with the 95% match-bootstrap interval (1000 resamples, seed 2026) excluding zero.

**H2 (secondary): the families are reproduced, build-up phase.** Both must hold: (a) no family changes its share of build-up sequences by more than 10 percentage points between exploration and held-out; (b) the silhouette of the frozen assignment on held-out data is at least 0.10 (exploration value: about 0.18).

**Advanced phase.** Same statistics are reported, but it is **not** part of the success criterion: exploration showed weak evidence of structure (Leverkusen stability 0.88 vs Gaussian null 0.84; predictability gain not significant).

## Decision rule
- L2 build-up claim is **confirmed** if H1 and H2 pass for both teams, **partially confirmed** if they pass for one team only, **not confirmed** otherwise.
- Each team is run once. The results file is committed unedited, whatever the outcome. Thresholds, k, cut and features are not changed after seeing held-out results. Any further analysis is labelled exploratory.
- The refit ARI (K-Means refitted on held-out data vs the frozen assignment) is reported as a descriptive number only.

## Known weaknesses of this test
- Same teams and seasons: this tests generalisation over time within a team, not across teams or seasons.
- Small samples (10 and 11 matches): intervals will be wide. A non-confirmation is weak evidence against the families; a confirmation is moderate evidence for them.
- Thresholds were set after seeing exploration results and after a dry run of the script on exploration data only (pseudo split inside the exploration matches). They were not set by looking at held-out data.
- Stability and predictability do not show tactical meaning; that requires expert review or links to outcomes (shots, xG).
