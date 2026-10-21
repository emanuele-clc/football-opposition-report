# Automated Football Opposition Report

Master's thesis prototype · Emanuele Colecchia · UNICAL / FH OÖ Hagenberg · Supervisor: Prof. Pichler  
Data: [StatsBomb Open Data](https://github.com/statsbomb/open-data) (non-commercial licence).

From a team's event data, the tool describes how the team builds up, restarts, takes set pieces and handles transitions, and links every number to the clips behind it. Each number comes with an interval and a warning when the sample is small. The method's own tests, including the negative ones, are reported.

## What it does
- **Build-up patterns:** open-play possessions are grouped into numbered families (B1-B5 in the build-up, A1-A3 further up the pitch), each with its share, shot rate and stability.
- **Sheets:** restarts (goal kicks, keeper, throw-ins), set pieces, transitions, defending, key players, expected threat (xT). Every value is ranked against the other teams.
- **Clips:** every possession with match and time, as CSV or as XML for video tools (Sportscode / Nacsport style).
- **Local app:** replays on the pitch, filters, comparison between teams, clip export, analyst review sheet.

## Main results (10 teams)
| Question | Answer |
|---|---|
| Do the build-up families reappear in unseen matches? | Yes in **8 of 10** teams (pre-registered, held-out matches) |
| What makes them predictable? | Almost only how the possession starts; minute, score and venue add nothing |
| Are they distinct clusters? | Weakly: close to structure-free data, better seen as slices of a continuum |
| Do they explain shots better than a simple rule? | **No**, in 0 of 10 teams (pre-registered) |
| Corners (L3): is a set-up exploitable? | Not shown (p = 0.17 and 0.41), but the test could only detect very large effects |
| How far can each report statement be trusted? | Graded A-D on 70 new teams: 4 A, 13 B, 15 C, 2 D (`results/evidence_grade_corrected.json`) |

Ten teams: Leverkusen 2023/24, plus nine teams from the 2015/16 Premier League, La Liga, Serie A and Ligue 1. Not tested on club data, and not yet reviewed by an analyst. Details and all tables: [`docs/results.md`](docs/results.md).

## Quick start (Windows, PowerShell)
First time: install Python 3.13 and Node.js, then
```powershell
pip install -r requirements.txt
```
**Start the app** (it builds, tests and opens http://127.0.0.1:8765; Ctrl+C stops it):
```powershell
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1                          # data in $env:OPPREPORT_DATA, else the 4 example teams
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1 -DataDir <data_folder>   # your own teams (replays need the raw events in <data_folder>\ev)
```
**Make the report for one team:**
```powershell
cd <data_folder>                                                              # downloads go into the current folder
python -X utf8 <repo>\src\week1\download_data.py 9 281 "Bayer Leverkusen"     # StatsBomb events -> matches\ and ev\
python -X utf8 <repo>\src\oppreport.py --statsbomb matches\9_281.json --data-dir . --team "Bayer Leverkusen" --out reports
python -X utf8 <repo>\src\oppreport.py --csv events.csv --team "Team name" --out reports   # any other provider
```
Always use `python -X utf8` on Windows (team names have accents). Output: one HTML page per sheet (`prep_<Team>.html` is the one-page summary) and the clip lists. Data format for other providers: [`docs/data_format.md`](docs/data_format.md).

## Reproducibility
Every confirmatory test was written down in `docs/protocol_*.md` and committed before it was run once; result files in `results/` are committed unedited.
```powershell
python -X utf8 tests\reproduce_results.py <data_dir> <new_work_dir>   # reruns the tests, compares with results\ (41/41 identical)
python -X utf8 tests\reproduce_sheets.py <data_dir>                    # reruns the report sheets (50/50 identical)
python -X utf8 tests\test_app_api.py                                   # app checks
```
All analysis commands, step by step: [`docs/pipeline.md`](docs/pipeline.md).

## Repository
```
src/         analysis (week1-4), report sheets (report/), provider adapters, tracking (exploratory), oppreport.py
app/         local web app (FastAPI + React), see app/README.md
tests/       reproducibility and app tests
docs/        protocols, results, data format, analyst guide
results/     result files of every run (JSON)
examples/    example outputs for 4 teams (also the app's default data)
data_info/   competition and match lists (raw events are not included)
```

## Limits
- Descriptive: the report shows where to look, not what will work. Family names are numbers until an analyst names them from video.
- Ten teams, nine of them from one season (2015/16), one provider for the main results.
- Never tried on real club data. The XML export has not been tested in a real video tool.

## Citation
StatsBomb (2024). StatsBomb Open Data. https://github.com/statsbomb/open-data
