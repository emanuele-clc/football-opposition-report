# Running the analysis pipeline

Commands for every step of the thesis analyses (moved here from the README on 21 October 2026). For the report and the app, see the README.

```bash
pip install numpy pandas scikit-learn matplotlib scipy statsbombpy
# 1 — download
python src/analysis/download_data.py 9 281 "Bayer Leverkusen"   # Bundesliga 2023/24
python src/analysis/download_data.py 2 27  "Leicester City"      # PL 2015/16
python src/analysis/download_data.py 11 27 "Barcelona"           # La Liga 2015/16 (events only)
python src/analysis/download_data.py 2 27  "Arsenal"            # PL 2015/16 (events only)
# 2 — L1: corners
FIG_LANG=en python src/analysis/corners.py leverkusen .
# archive/ was removed on 8 Nov 2026: the one-off scripts below are in git commit 7d6a28f (git show 7d6a28f:archive/<file>)
# 3 — L2: sequences & clustering
python archive/choose_k.py matches/9_281.json "Bayer Leverkusen" .   # choice of k (done once)
FIG_LANG=en python src/analysis/families.py final matches/9_281.json "Bayer Leverkusen" .
# 4 — robustness (week 3)
python src/analysis/families.py robustness matches/9_281.json "Bayer Leverkusen" .
python src/analysis/families.py robustness matches/2_27.json "Leicester City" .
python src/analysis/families.py null matches/9_281.json "Bayer Leverkusen" .
python src/analysis/families.py null matches/2_27.json "Leicester City" .
# 5 — held-out validation and replication (week 4; run ONCE per team, after committing docs/protocol_*.md)
python src/analysis/validate_replication.py matches/9_281.json "Bayer Leverkusen" . --confirm --no-h3
python src/analysis/validate_replication.py matches/2_27.json "Leicester City" . --confirm --no-h3
python src/analysis/validate_replication.py matches/11_27.json "Barcelona" . --confirm
python src/analysis/validate_replication.py matches/2_27.json "Arsenal" . --confirm
# 5b — replication on 10 teams: seeded selection, run (download + E1 + validation, once per team), summary (docs/protocol_replication10.md)
python archive/select_and_replicate.py select data_info docs/replication10_selection.json   # done once
python archive/select_and_replicate.py replicate docs/replication10_selection.json --confirm   # done once
python src/analysis/ten_teams.py summary replication docs/replication10_selection.json .
python src/analysis/ten_teams.py run simplerule docs/replication10_selection.json --confirm   # families vs simple rule (docs/protocol_simple_rule.md)
python src/analysis/ten_teams.py summary simplerule docs/replication10_selection.json .
python src/analysis/ten_teams.py run samplesize docs/replication10_selection.json            # how many matches are needed
python src/analysis/ten_teams.py summary samplesize docs/replication10_selection.json .
python src/analysis/ten_teams.py run clustertest docs/replication10_selection.json           # exploratory copula test on the 10 teams
# 6 — exploratory analyses, not pre-registered (repeat for each team)
python src/analysis/exploratory_predictability.py cv matches/11_27.json "Barcelona" .
python src/analysis/exploratory_predictability.py ablation matches/11_27.json "Barcelona" .
python src/analysis/exploratory_predictability.py context matches/11_27.json "Barcelona" .
python src/analysis/exploratory_clusters.py methods matches/11_27.json "Barcelona" .
# 7 — automated opposition report (run it for all teams twice so each report finds the others as reference)
python src/report/make_report.py matches/11_27.json "Barcelona" .
```
Removed on 6 November 2026 (superseded, code still in the git history before that date): `week1/goalkicks_leverkusen.py` (goal kicks are now in `src/report/restarts.py`), `week1/team_events_only.py` (first events-only test, which produced `results/results_Leicester_City.json`), `week2/compare_teams.py` (two-team comparison, which produced `results/L2_confronto_squadre.json`; the report now compares with reference teams), `week4/run_robustness.py` (only a loop; `tests/reproduce_results.py` reruns the same script), `week4/plot_robustness.py` (figures of the robustness checks, already in figures/).
Merged on 6 November 2026, same code and same outputs (checked: results 51/51 identical, the exploratory files identical): `validate_holdout.py` = `validate_replication.py --no-h3`; `select_teams.py`, `run_new_teams.py`, `summarize_replication10.py`, `run_simple_rule.py`, `run_sample_size.py`, `run_cluster_tests.py` -> `ten_teams.py`; `exploratory_cv_all_matches.py`, `exploratory_ablation.py`, `exploratory_context.py` -> `exploratory_predictability.py`; `exploratory_cluster_test.py`, `exploratory_robustness.py` -> `exploratory_clusters.py`. The protocols keep the old names: the files are in the git history at the commit of each protocol.
Moved on 6 November 2026: the folders `src/week1`-`src/week4` became one folder, `src/analysis/`. Also merged then, same outputs (checked): `week2/final_L2.py`, `week3/robustness_L2.py`, `week3/stability_null_baseline.py` -> `families.py final | robustness | null`; `week1/corners_leverkusen.py`, `week1/pooled_corners.py` -> `corners.py leverkusen | pooled`.
On Windows add `-X utf8` after `python` (data files are UTF-8).
All scripts use a fixed seed. Results are reproducible on the same data.

## Reproducibility checks
`python -X utf8 tests/reproduce_results.py <data_dir> <new_work_dir>` reruns the held-out validation, the simple-rule comparison, the null baselines, the sample-size study and the 10-team summary with the committed code and seeds in a separate folder, and compares every file with `results/` (nothing in `results/` is overwritten; this checks the numbers, it is not a second validation). Run on 17 October 2026: **41 of 41 files identical**. With `--only-new --tournaments <folder with Euro 2020/2024 and World Cup 2022 data>` it reruns only the exploratory method comparison and sensitivity (`exploratory_robustness_<Team>.json`) and the pooled corners (`results_pooled_corners.json`): **11 of 11 identical** (17 October 2026). `python -X utf8 tests/reproduce_sheets.py <data_dir>` reruns the defending, matchup and key-player sheets of the 10 teams in an empty folder: **30 of 30 identical** (17 October 2026).
`python -X utf8 tests/test_adapter_roundtrip.py <matches.json> "<Team>" <data_dir>` checks the generic CSV adapter (sequences, restart sheet and set-piece sheet; see `docs/data_format.md`).
