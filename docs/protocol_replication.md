# Replication protocol (L2) on two new teams

Written on 12 October 2026, **before** any event data of these teams was analysed. Only the match lists (names, number of matches) were looked at. The commit date of this file is the timestamp.

## Teams
| Team | Competition | Matches | Exploration (first 70% by date) | Held-out |
|---|---|---|---|---|
| Barcelona | La Liga 2015/16 (open data 11/27) | 38 | 27 | 11 |
| Arsenal | Premier League 2015/16 (open data 2/27) | 38 | 27 | 11 |

Chosen for data completeness (full season, events only, no 360) and style contrast with the first two teams (Barcelona: possession-dominant; Arsenal: intermediate). Not chosen on any outcome.

## What is frozen (no tuning on the new teams)
Phase cut x = 45; k = 5 (build-up) and k = 3 (advanced); the 11 features; K-Means settings (n_init = 20, random_state = 0); predictability model (logistic regression, C = 0.5, inputs: play pattern, minute, half, previous family). Families are fitted separately for each team on its exploration matches, then frozen and applied to its held-out matches. Script: `src/week4/validate_replication.py`.

## Exploration check (E1, descriptive)
Run `src/week3/stability_null_baseline.py` on the exploration matches. E1 holds for a team if the build-up mean Jaccard exceeds both the shuffle and the Gaussian null by at least 0.10. (The 0.10 margin comes from the first two teams: Leverkusen +0.24 / Leicester +0.12 over the Gaussian null.) E1 is reported either way and does not decide whether the held-out run happens.

## Hypotheses on held-out matches
- **H1 (build-up)**: out-of-sample predictability gain (log-loss vs frequency baseline) positive, 95% match-bootstrap interval (1000 resamples, seed 2026) excluding zero.
- **H2 (build-up)**: no family changes its share by more than 10 percentage points between exploration and held-out, and the silhouette of the frozen assignment on held-out data is at least 0.10.
- **H3 (both phases, separately)**: families carry information about shots. Model: logistic regression on family membership, trained on exploration, evaluated on held-out; gain in log-loss for shot / no shot vs the exploration shot rate; 95% match-bootstrap interval (1000 resamples, seed 2027) excluding zero. A model on the raw features is reported as a descriptive comparison only.

## Decision rule
- **Build-up claim holds for a team** if H1 and H2 both pass. Replicated if it holds for both new teams, partially replicated for one, not replicated for none. The claim across all four teams is reported as x out of 4.
- **H3** is reported per team and per phase. "Families carry shot information" is supported for a phase if H3 passes for both teams, partially for one, not supported otherwise.
- Each team is run once. Result files are committed unedited, whatever the outcome. Cut, k, features, thresholds and seeds are not changed after seeing results. Further analyses are labelled exploratory.

## Known weaknesses
- No correction for multiple comparisons: H1, H2, H3 are tested per team and per phase.
- Margin in E1 and the other thresholds were calibrated on the first two teams.
- Events only, season 2015/16: no 360 data, and a different era from Leverkusen 2023/24.
- 11 held-out matches per team: wide intervals, so a non-confirmation is weak evidence against.
- Family shot differences can come partly from the features that define the families (a raw-feature model will usually do better); H3 shows the families keep part of that information, not that they add to it.
- Stability, predictability and shot association do not show tactical meaning; that needs expert review.
