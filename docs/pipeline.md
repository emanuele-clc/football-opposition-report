# Running the analysis pipeline

Commands for every step of the thesis analyses (moved here from the README on 21 October 2026). For the report and the app, see the README.

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
python src/week4/run_cluster_tests.py docs/replication10_selection.json   # exploratory cluster test on the 10 teams
# 6 — exploratory analyses, not pre-registered (repeat for each team)
python src/week4/exploratory_cv_all_matches.py matches/11_27.json "Barcelona" .
python src/week4/exploratory_ablation.py matches/11_27.json "Barcelona" .
python src/week4/exploratory_context.py matches/11_27.json "Barcelona" .
# 7 — automated opposition report (run it for all teams twice so each report finds the others as reference)
python src/report/make_report.py matches/11_27.json "Barcelona" .
```
On Windows add `-X utf8` after `python` (data files are UTF-8).
All scripts use a fixed seed. Results are reproducible on the same data.

## Reproducibility checks
`python -X utf8 tests/reproduce_results.py <data_dir> <new_work_dir>` reruns the held-out validation, the simple-rule comparison, the null baselines, the sample-size study and the 10-team summary with the committed code and seeds in a separate folder, and compares every file with `results/` (nothing in `results/` is overwritten; this checks the numbers, it is not a second validation). Run on 17 October 2026: **41 of 41 files identical**. With `--only-new --tournaments <folder with Euro 2020/2024 and World Cup 2022 data>` it reruns only the exploratory method comparison and sensitivity (`exploratory_robustness_<Team>.json`) and the pooled corners (`results_pooled_corners.json`): **11 of 11 identical** (17 October 2026). `python -X utf8 tests/reproduce_sheets.py <data_dir>` reruns the defending, matchup and key-player sheets of the 10 teams in an empty folder: **30 of 30 identical** (17 October 2026).
`python -X utf8 tests/test_adapter_roundtrip.py <matches.json> "<Team>" <data_dir>` checks the generic CSV adapter (sequences, restart sheet and set-piece sheet; see `docs/data_format.md`).
