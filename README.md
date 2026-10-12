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
src/week3/       robustness: match-bootstrap, sensitivity, predictability
results/         JSON + CSV outputs (no raw event files)
figures/         PNG charts (IT and EN labels)
data_info/       competitions.json + match lists only (event files ~2.3 GB, not included)
slides/          Canva AI prompts + 20-min speech (Word)
docs/            Methodology protocol
```

## How to run
```bash
pip install numpy pandas scikit-learn matplotlib scipy statsbombpy
# 1 — download
python src/week1/download_data.py 9 281 "Bayer Leverkusen"   # Bundesliga 2023/24
python src/week1/download_data.py 2 27  "Leicester City"      # PL 2015/16
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
```
On Windows add `-X utf8` after `python` (data files are UTF-8).
All scripts use a fixed seed. Results are reproducible on the same data.

## Results summary (exploration data only — last 30% untouched)

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

## Declared researcher degrees of freedom
1. Phase split at x = 45 (tested 35–55)
2. k = 5 (build-up) and k = 3 (advanced): chosen by match-bootstrap on Leverkusen exploration
3. First representation discarded (12 zones × 0/1 + 29 PCA → stability < 0.60)
4. 70/30 time split by match date; validation untouched
5. Corner zones and defensive set-up categories are author-defined

## Key limitations
- Silhouette ≈ 0.18: stable slices of a continuum
- Week 2 bootstrap was on sequences; week 3 adds match-level resampling
- Different leagues and eras (Bundesliga 23/24 vs PL 15/16)
- Leverkusen advanced stability is not distinguishable from a Gaussian null (0.88 vs 0.84)
- Build-up predictability significant; advanced phase not significant for either team
- Exploitability not significant: crude definitions, near-empty cells, median 9 defenders visible (not 11)
- StatsBomb Open Data, non-commercial licence

## Related work (closest)
- Yeung & Bunker, StatsBomb Conference 2023 — possession clustering with 360 frames
- Amezouwui et al. 2025 — mixture model on possession sequences
- Umemoto & Fujii, StatsBomb Conference 2023 — defensive positioning with 360 frames
- TacticAI (Google DeepMind & Liverpool FC, Nature Comms 2024) — corners, graph neural network, proprietary tracking data

## Citation
StatsBomb (2024). StatsBomb Open Data. https://github.com/statsbomb/open-data
