# Automated Football Opposition Report

Master's thesis prototype · Emanuele Colecchia · FH OÖ Hagenberg  
Presentation: 21 October 2026 · Supervisor: TBD  
Data: **StatsBomb Open Data** — non-commercial licence, must cite StatsBomb.

## In one sentence
Take event data from a football team, find recurring possession patterns,
measure their **stability** and **predictability** with uncertainty intervals,
and test whether **exploitability** exists on corner kicks.

## Repository structure
```
src/week1/       download, goal kicks, corners (L3)
src/week2/       sequence extraction and clustering (L2)
src/week3/       robustness: match-bootstrap, sensitivity, predictability, null baselines
src/week4/       held-out validation, replication on new teams, exploratory analyses
src/report/      automated opposition report generator (L2)
examples/        example reports (HTML)
results/         JSON + CSV outputs (no raw event files)
figures/         PNG charts (IT and EN labels)
data_info/       competitions.json + match lists only (event files ~2.3 GB, not included)
slides/          Canva AI prompts + 20-min speech (Word)
docs/            Methodology protocol + pre-registered protocols (held-out validation, replication)
```

## How to run
```bash
pip install numpy pandas scikit-learn matplotlib scipy statsbombpy
# 1 — download
python src/week1/download_data.py 9 281 "Bayer Leverkusen"   # Bundesliga 2023/24
python src/week1/download_data.py 2 27  "Leicester City"      # PL 2015/16
python src/week1/download_data.py 11 27 "Barcelona"           # La Liga 2015/16 (events only)
python src/week1/download_data.py 2 27  "Arsenal"            # PL 2015/16 (events only)
# 2 — L1: goal kicks & corners
python src/week1/goalkicks_leverkusen.py .
FIG_LANG=en python src/week1/corners_leverkusen.py .
python src/week1/team_events_only.py matches/2_27.json "Leicester City" .
# 3 — L2: sequences & clustering
python src/week2/sequences_clustering.py matches/9_281.json "Bayer Leverkusen" .
FIG_LANG=en python src/week2/final_L2.py matches/9_281.json "Bayer Leverkusen" .
python src/week2/compare_teams.py matches/9_281.json "Bayer Leverkusen" matches/2_27.json "Leicester City" .
# 4 — robustness (week 3)
python src/week3/robustness_L2.py matches/9_281.json "Bayer Leverkusen" .
python src/week3/robustness_L2.py matches/2_27.json "Leicester City" .
python src/week3/stability_null_baseline.py matches/9_281.json "Bayer Leverkusen" .
python src/week3/stability_null_baseline.py matches/2_27.json "Leicester City" .
# 5 — held-out validation and replication (week 4; run ONCE per team, after committing docs/protocol_*.md)
python src/week4/validate_holdout.py matches/9_281.json "Bayer Leverkusen" . --confirm
python src/week4/validate_holdout.py matches/2_27.json "Leicester City" . --confirm
python src/week4/validate_replication.py matches/11_27.json "Barcelona" . --confirm
python src/week4/validate_replication.py matches/2_27.json "Arsenal" . --confirm
# 5b — replication on 10 teams: seeded selection, run (download + E1 + validation, once per team), summary (docs/protocol_replication10.md)
python src/week4/select_teams.py data_info docs/replication10_selection.json
python src/week4/run_new_teams.py docs/replication10_selection.json --confirm
python src/week4/summarize_replication10.py docs/replication10_selection.json .
# 6 — exploratory analyses, not pre-registered (repeat for each team)
python src/week4/exploratory_cv_all_matches.py matches/11_27.json "Barcelona" .
python src/week4/exploratory_ablation.py matches/11_27.json "Barcelona" .
python src/week4/exploratory_context.py matches/11_27.json "Barcelona" .
# 7 — automated opposition report (run it for all teams twice so each report finds the others as reference)
python src/report/make_report.py matches/11_27.json "Barcelona" .
```
On Windows add `-X utf8` after `python` (data files are UTF-8).
All scripts use a fixed seed. Results are reproducible on the same data.

## Results summary (weeks 1-3: exploration data only; held-out and replication results further down)

### L2 — Sequence families

**Bayer Leverkusen 2023/24** (34 matches, with 360 frames, 24 exploration)

| | Build-up (k=5) | Advanced (k=3) |
|---|---|---|
| Sequences | 619 | 553 |
| Stability — match bootstrap mean Jaccard | **0.82** (min 0.75) | **0.89** (min 0.88) |
| Silhouette | 0.18 | 0.19 |
| Entropy | 2.25 / 2.32 bits | 1.58 / 1.58 bits |
| Predictability gain (log-loss vs baseline) | **+0.114** (95% CI 0.080–0.150) | +0.007 (n.s.) |

**Leicester City 2015/16** (38 matches, events only, 27 exploration)

| | Build-up (k=5) | Advanced (k=3) |
|---|---|---|
| Sequences | 616 | 548 |
| Stability — match bootstrap mean Jaccard | 0.70 (min 0.60) | **0.86** (min 0.83) |
| Predictability gain | **+0.158** (95% CI 0.120–0.198) | +0.028 (n.s.) |

**Style comparison (95% bootstrap CI)**

| Metric | Leverkusen | Leicester |
|---|---|---|
| Passes per sequence | 10.7 (10.2–11.2) | 5.6 (5.4–5.8) |
| Long-pass share | 11% | 22% |
| Duration | 31 s | 18 s |
| Shot rate | 17.5% (15.4–19.7) | 12.0% (10.2–13.9) |

### L3 — Corner exploitability (not significant so far)

| Dataset | Corners w/ 360 | Exploitability | p-value |
|---|---|---|---|
| Leverkusen only | 148 | 0.026 xG/corner | 0.17 |
| Euro 2020 + 2024 + WC 2022 | 846 | 0.007 xG/corner | 0.41 |

Crude zone/set-up definitions; null result reported honestly.

### Robustness checks (week 3, Leverkusen)
- **Cut sensitivity** (x = 35–55): stability ≥ 0.75 at x = 40–55 for build-up
- **k sensitivity**: k = 5 gives best balance of Jaccard and silhouette for build-up
- **Method comparison**: GMM and Ward give similar silhouette (~0.18–0.19); ARI between methods 0.50–0.70 (moderate agreement, confirming the continuum)

### Stability vs null baselines (week 3, match-bootstrap, same pipeline)
Mean Jaccard of the observed partition vs two structure-free nulls (shuffled features; Gaussian with same mean/covariance).

| | Observed | Shuffle | Gaussian |
|---|---|---|---|
| Leverkusen build-up (k=5) | 0.80 | 0.48 | 0.56 |
| Leverkusen advanced (k=3) | 0.88 | 0.40 | 0.84 |
| Leicester build-up (k=5) | 0.69 | 0.43 | 0.57 |
| Leicester advanced (k=3) | 0.85 | 0.44 | 0.62 |

Build-up (both teams) and Leicester advanced are clearly above both nulls. Leverkusen advanced is **not** clearly above the Gaussian null: treat it as a slicing of a continuum, not demonstrated structure. Script: `src/week3/stability_null_baseline.py` (on Windows run with `python -X utf8`).

## Held-out validation (week 4)
Protocol: `docs/protocol_holdout.md` (committed before running). Script: `src/week4/validate_holdout.py`. Status: **run once on 12 October 2026**, results unedited in `results/holdout_*.json`.
```bash
python src/week4/validate_holdout.py matches/9_281.json "Bayer Leverkusen" . --confirm
python src/week4/validate_holdout.py matches/2_27.json "Leicester City" . --confirm
```

Results on held-out matches (Leverkusen 10, Leicester 11), model frozen on exploration:

| | Predictability gain (log-loss), 95% CI | Max change in family share | Silhouette (frozen) | H1 / H2 |
|---|---|---|---|---|
| Leverkusen build-up | +0.099 [+0.062, +0.137] | 0.06 | 0.18 | pass / pass |
| Leicester build-up | +0.185 [+0.137, +0.236] | 0.03 | 0.16 | pass / pass |
| Leverkusen advanced | -0.004 [-0.034, +0.029] | 0.07 | 0.17 | not confirmed / pass (not in criterion) |
| Leicester advanced | +0.034 [-0.012, +0.079] | 0.10 | 0.19 | not confirmed / pass (not in criterion) |

By the pre-registered rule the build-up claim is **confirmed for both teams**. The advanced phase shows no out-of-sample predictability, consistent with exploration. This tests stability over time within the same teams and seasons, not generalisation to other teams, and does not show tactical meaning.

## Replication on two new teams (week 4)
Protocol: `docs/protocol_replication.md` (committed before running). Script: `src/week4/validate_replication.py`. Teams: Barcelona (La Liga 2015/16) and Arsenal (Premier League 2015/16), 27 exploration + 11 held-out matches each, settings frozen from the first two teams. Run once; results unedited in `results/holdout_Barcelona.json` and `results/holdout_Arsenal.json` (the script uses the same file naming as the first held-out run).

| | H1 predictability gain, 95% CI | H2 (max share change / silhouette) | H3 shots, gain 95% CI |
|---|---|---|---|
| Arsenal build-up | +0.113 [+0.077, +0.143] pass | 0.06 / 0.17 pass | +0.035 [+0.017, +0.057] pass |
| Barcelona build-up | +0.024 [-0.034, +0.077] **not confirmed** | 0.06 / 0.15 pass | +0.038 [+0.023, +0.055] pass |
| Arsenal advanced | +0.045 [+0.003, +0.084] (not in criterion) | 0.06 / 0.18 pass | +0.013 [-0.001, +0.030] not confirmed |
| Barcelona advanced | +0.068 [+0.005, +0.130] (not in criterion) | 0.02 / 0.18 pass | +0.015 [+0.003, +0.031] pass |

By the pre-registered rule the build-up claim (H1 and H2) holds for Arsenal and not for Barcelona: **partially replicated, 3 out of 4 teams** counting Leverkusen and Leicester. H2 (families reproduced) holds for all four teams. H3 was only run on the two new teams: shot information in the build-up families is supported for both teams, in the advanced phase for one of two. The advanced-phase H1 results are outside the pre-registered criterion, have lower bounds close to zero and are not interpreted as confirmation.

### Exploration check E1 (stability vs null baselines, new teams)
Mean Jaccard, match-bootstrap, exploration matches. E1 criterion (descriptive): build-up above both nulls by at least 0.10.

| | Observed | Shuffle | Gaussian | E1 |
|---|---|---|---|---|
| Barcelona build-up (k=5) | 0.69 | 0.36 | 0.54 | holds (+0.15) |
| Arsenal build-up (k=5) | 0.69 | 0.44 | 0.63 | does not hold (+0.06) |
| Barcelona advanced (k=3) | 0.85 | 0.49 | 0.75 | (not in criterion) |
| Arsenal advanced (k=3) | 0.83 | 0.44 | 0.85 | (not in criterion) |

### Summary across the four teams (build-up)
| Team | Stability margin over Gaussian null | H1 held-out predictability | H2 families reproduced | H3 shots |
|---|---|---|---|---|
| Leverkusen | +0.24 | pass | pass | not tested |
| Leicester | +0.12 | pass | pass | not tested |
| Barcelona | +0.15 | not confirmed | pass | pass |
| Arsenal | +0.06 | pass | pass | pass |

The size of the stability margin does not line up with held-out predictability (Barcelona has a clear margin and fails H1; Arsenal has the smallest margin and passes). With four teams this is an observation, not a finding. The held-out results (H1, H2) carry more weight than the stability comparison alone.

### Exploratory, not pre-registered: predictability over all matches
Grouped 6-fold cross-validation over all matches (families refitted inside each fold; folds do not respect time order, so slightly optimistic). Script: `src/week4/exploratory_cv_all_matches.py`.

| Team | Build-up gain, 95% CI | Advanced gain, 95% CI |
|---|---|---|
| Barcelona | +0.131 [+0.107, +0.153] | +0.069 [+0.046, +0.091] |
| Arsenal | +0.123 [+0.096, +0.146] | +0.078 [+0.038, +0.113] |
| Leverkusen | +0.125 [+0.087, +0.159] | +0.001 [-0.020, +0.023] |
| Leicester | +0.164 [+0.132, +0.198] | +0.043 [+0.017, +0.067] |

With all matches, Barcelona's build-up gain is in line with the other teams, and its last 30% of matches also give about +0.14 inside the cross-validation. The non-confirmation of H1 on the 11 held-out matches is therefore not explained by those matches being unpredictable; it may come from a model trained only on the first 27 matches (change over the season) or from sampling noise, and these data cannot tell which.

### L3 corners: what the test could detect (Leverkusen, 148 corners with 360)
Average xG per corner is 0.046. Under no real effect, the exploitability statistic already averages 0.015 (selecting the best setup on the same data biases it upwards) and its 95th percentile is 0.033, i.e. about 70% of the average xG per corner. Observed: 0.026 (p = 0.17). So the test could only flag very large effects. Most corners fall in one cell: 116 of 148 are in the "centre" zone, and only 9 have a "far-post load" setup. Out of sample (41 corners), the setup chosen as best on training data did worse (xG 0.069 vs 0.046 for the others). The null result is therefore weak evidence of absence.

### Exploratory, not pre-registered: what drives the predictability
Same cross-validation as above. Build-up gain with different inputs (log-loss gain over the family-frequency baseline). Scripts: `src/week4/exploratory_ablation.py`, `src/week4/exploratory_context.py`.

| Team | Full model | Play pattern only | Minute + half only | Previous family only | Full context added on top of play pattern |
|---|---|---|---|---|---|
| Barcelona | +0.131 | +0.139 | -0.001 | -0.009 | -0.010 |
| Arsenal | +0.123 | +0.139 | 0.000 | -0.016 | -0.028 |
| Leverkusen | +0.125 | +0.135 | -0.007 | -0.001 | -0.008 |
| Leicester | +0.164 | +0.176 | +0.002 | -0.011 | -0.022 |

Practically all of the predictability comes from how the sequence starts (play pattern). Score state, home/away, minute, half and the previous family add nothing (the advanced phase gives the same picture, with smaller gains). The gain is real but should be described as "families depend on how the sequence starts", not as tactical predictability from match context. This is partly by construction: the start position is one of the 11 features that define the families.

## Automated opposition report
`src/report/make_report.py` turns the validated settings into a report for one team: style with intervals and a comparison with reference teams, the families with share, profile, shot rate, per-match variation and stability, a structure check against structure-free baselines, and how sequence start types map to families. Output: a self-contained HTML file (print to PDF from the browser) plus a JSON with all numbers. Examples in `examples/`. It is descriptive: it does not recommend tactics, family names are numbered labels, and coaches have not yet validated their tactical meaning.

## Replication on 10 teams (week 4)
Protocol: `docs/protocol_replication10.md` (committed before running). Six new teams drawn at random with a fixed seed (20261013), stratified by league (La Liga, Serie A, Ligue 1, season 2015/16, two primary teams each), added to the four teams already analysed. Scripts: `src/week4/select_teams.py`, `run_new_teams.py`, `summarize_replication10.py`. Each team run once; results in `results/holdout_<team>.json`, `results/null_baseline_<team>.json` and `results/replication10_summary.json`.

| Team | League | Build-up gain (H1) | H1 | H2 | H3 build-up / advanced | E1 margin over null |
|---|---|---|---|---|---|---|
| Bayer Leverkusen | Bundesliga 23/24 | +0.099 | pass | pass | not tested | +0.24 |
| Leicester City | Premier League 15/16 | +0.185 | pass | pass | not tested | +0.13 |
| Barcelona | La Liga 15/16 | +0.024 | **no** | pass | pass / pass | +0.15 |
| Arsenal | Premier League 15/16 | +0.113 | pass | pass | pass / no | +0.06 |
| Atlético Madrid | La Liga 15/16 | +0.098 | pass | pass | pass / no | +0.03 |
| Real Madrid | La Liga 15/16 | +0.103 | pass | pass | pass / pass | +0.00 |
| Napoli | Serie A 15/16 | +0.105 | pass | pass | pass / no | +0.11 |
| Sassuolo | Serie A 15/16 | +0.035 | **no** | pass | no / no | -0.01 |
| Gazélec Ajaccio | Ligue 1 15/16 | +0.100 | pass | pass | pass / no | +0.00 |
| Bordeaux | Ligue 1 15/16 | +0.091 | pass | pass | no / no | +0.08 |

**Result by the pre-registered rule.** H1 and H2 pass in **8 of 10 teams** (95% Wilson interval 0.49 to 0.94); the rule (at least 7 of 10) is met. H3 for the build-up passes in 6 of the 8 teams where it was tested (rule: at least 6 of 8); in the advanced phase in 2 of 8 (reported only). H1 fails for Barcelona and Sassuolo.

**How far this goes.** (1) The build-up gain comes from how sequences start (play pattern), see the ablation above; this is a regularity of the families, not tactical predictability from match context. (2) The stability margin over a single Gaussian blob (E1, margin of at least 0.10) holds in only 4 of 10 teams (Leverkusen, Leicester, Barcelona, Napoli), and the advanced phase is often at the level of the structure-free null: for many teams the families are slices of a continuum, not separate clusters. (3) H2 passes everywhere but is a lenient test: its silhouette threshold (0.10) is below what structure-free data already gives (0.12-0.14 in the null baselines), and a frozen partition of a stable distribution keeps stable shares. (4) A model on the raw features predicts shots better than the families (+0.05 to +0.11 against +0.01 to +0.05), so the families keep only part of that information.

## Declared researcher degrees of freedom
1. Phase split at x = 45 (tested 35–55)
2. k = 5 (build-up) and k = 3 (advanced): chosen by match-bootstrap on Leverkusen exploration
3. First representation discarded (12 zones × 0/1 + 29 PCA → stability < 0.60)
4. 70/30 time split by match date; validation untouched
5. Corner zones and defensive set-up categories are author-defined
6. Replication teams (Barcelona, Arsenal) chosen for data completeness and style contrast; thresholds in the protocols were calibrated on the first two teams
7. Report reliability labels (stable at 0.75, moderate at 0.60) and the 0.10 structure margin are author conventions

## Key limitations
- Silhouette ≈ 0.18: stable slices of a continuum
- Week 2 bootstrap was on sequences; week 3 adds match-level resampling
- Different leagues and eras (Bundesliga 23/24 vs PL 15/16)
- Leverkusen advanced stability is not distinguishable from a Gaussian null (0.88 vs 0.84)
- Held-out build-up predictability (H1 and H2) confirmed in 8 of 10 teams (not Barcelona, Sassuolo), but it comes from how sequences start; context adds nothing
- Stability above a structure-free Gaussian null (margin 0.10) in only 4 of 10 teams; the H2 silhouette threshold is lenient; the families are better described as slices of a continuum than as distinct clusters
- Tactical meaning of the families not validated by coaches; ten teams, nine from 2015/16, only six drawn at random
- Exploitability not significant: crude definitions, near-empty cells, median 9 defenders visible (not 11)
- StatsBomb Open Data, non-commercial licence

## Related work (closest)
- Yeung & Bunker, StatsBomb Conference 2023 — possession clustering with 360 frames
- Amezouwui et al. 2025 — mixture model on possession sequences
- Umemoto & Fujii, StatsBomb Conference 2023 — defensive positioning with 360 frames
- TacticAI (Google DeepMind & Liverpool FC, Nature Comms 2024) — corners, graph neural network, proprietary tracking data

## Citation
StatsBomb (2024). StatsBomb Open Data. https://github.com/statsbomb/open-data
