# Test: do the families explain shots better than a simple rule?

Written on 16 October 2026, before any run of `compare_simple_rules.py` on the held-out matches. A dry run of the code on a pseudo split inside the exploration matches of one team (Barcelona) was done only to check that the script works.

## Question
The families (K-Means, 5 in the build-up, 3 in the advanced phase) are the core of the method. Do they explain whether a sequence ends in a shot better than the simplest partition with the same number of cells? If not, the clustering adds a description but no information over a one-variable rule.

## What is compared
- **Families:** K-Means fitted on the exploration matches, frozen, applied to the held-out matches (same as H3).
- **Primary comparator, "end-position rule":** k equal-frequency bins of the position where the sequence ends (x1), with the bin edges taken from the exploration matches, k = 5 (build-up) and k = 3 (advanced). Chosen before the dry run as the most obvious single variable for shots.
- **Descriptive comparators:** the same with bins of net progression (net_x) and of number of passes (n_pass). Not part of the decision.
- **Model for every partition:** logistic regression on the cell dummies, C = 0.5, trained on the exploration matches; outcome = sequence ends in a shot; evaluated on the held-out matches (10-11 per team) with log-loss. Baseline: exploration shot rate.

## Hypothesis H4 and rule
- Per team and phase, the per-sequence log-loss difference d = loss(end-position rule) minus loss(families); positive means families better. 95% interval from bootstrap over matches (1000 resamples, seed 2028).
- Verdict per team and phase: **families better** if the interval is above zero; **simple rule better** if below zero; otherwise **no difference**.
- "The families add information beyond the end-position rule" is **supported** for a phase if the verdict is "families better" in at least **7 of the 10 teams**; otherwise it is **not shown**. Both phases are reported separately. The counts of the three verdicts are always reported.
- If it is not shown for the build-up, the thesis states that the clustering describes how teams build up but does not explain shots better than an end-position rule, and the report presents the families as a description only.
- Each team is run once; result files `results/simplerule_<team>.json` are committed unedited. Nothing in the comparison is changed after seeing results.

## Known weaknesses
- The held-out matches of the ten teams were already used for H1-H3. The comparison is new but the data are not fresh.
- The outcome is "ends in a shot", not xG. Shot rates are low (about 1 in 5 in the build-up and advanced phases), so the intervals are wide.
- With 10-11 matches per team, "no difference" does not mean "equivalent".
- One primary comparator only; other simple rules could do better or worse. The threshold of 7 of 10 follows the earlier protocols and is a convention.
- No correction for multiple comparisons across teams and phases.
- The families and the end-position rule use partly the same information (x1 is one of the 11 features of the families).
