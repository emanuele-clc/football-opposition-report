# Methodological protocol (frozen on exploration data)

## Phase split
x = 45 (sequences starting in own half = build-up; further forward = advanced phase).
Tested 35–55: stability ≥ 0.75 for Leverkusen at x = 40–55.

## Number of groups (k)
k = 5 (build-up), k = 3 (advanced phase).
Chosen by match-bootstrap Jaccard on Leverkusen exploration matches.

## Features (11 continuous variables)
x0, w0 (|y0 – 40|), x1, w1 (|y1 – 40|), net_x, path_len, directness,
n_pass, long_share, width_std, dur.
Left and right are mirrored so a left build-up = right build-up.

## Discarded representation
12 zones × 0/1 + 29 PCA components → stability below 0.6 for all k in {3…8}.

## Stability thresholds
Jaccard ≥ 0.75: stable. 0.60–0.75: probable. < 0.60: unstable.
Week 2: bootstrap on sequences. Week 3: bootstrap resamples matches.

## Validation split
Matches sorted by date; first 70% = exploration, last 30% = validation (untouched).

## Corner zones (author-defined)
- Short/outside box: end_x < 102 or lateral distance < 18
- Near post: lateral distance 18–30
- Centre: 30–50
- Far post: > 50
To be repeated with at least two alternative cutoff sets.

## Defensive set-up (from 360 freeze frames)
Outfield defenders visible in box (x ≥ 102, 18 ≤ y ≤ 62, not keeper, not teammate).
Near-loaded: near ≥ far + 2. Far-loaded: far ≥ near + 2. Balanced: otherwise.
