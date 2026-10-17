# Opposition report app (local)

A local web app over the files that `src/oppreport.py` writes. FastAPI backend (`app/backend/server.py`) + React frontend (`app/frontend`).
No new estimates: every number comes from `report_/restarts_/setpieces_/transitions_<Team>.json` and the clip CSVs.

## Run
One script does everything (stops an app already on the port, installs what is missing, rebuilds the frontend, clears the app cache, runs the tests, starts the app):
```powershell
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1                      # data in C:\Users\ecole\sbdata
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1 -DataDir <folder> -Port 8770 -SaltaTest
```
Step by step:
```powershell
pip install -r requirements.txt
cd app\frontend; npm install; npm run build; cd ..\..
python -X utf8 app\run.py                                   # example teams in examples\
python -X utf8 app\run.py --data-dir C:\Users\ecole\sbdata  # all teams processed there (10 thesis teams)
```
Opens http://127.0.0.1:8765. Ctrl+C stops it.

## What it does
- **Overview**: the team's typical build-up replayed pass by pass on the pitch (actual possessions rebuilt from the StatsBomb events), five key points where the team is furthest from the other teams, family stickers (hover to turn over, click to replay), every fact placed among all teams in the folder, reliability and how to read.
- **Build-up / Advanced**: share strip, replay of each family's typical sequences, start type -> family, every number per family, typical sequences with a play button.
- **Restarts, Set pieces, Transitions**: interactive sheets with replays of recent goal kicks, corners, high recoveries and losses (transitions show 6 s before to 10 s after, opponent in red); last-5 values outside the season interval are highlighted.
- **Clips**: filter by label, opponent, half, shot; click a row to watch it; export CSV or video-tool XML (zip, via `src/report/clips_to_xml.py`; XML import still untested in Sportscode/Nacsport).
- **Families → All sequences**: every sequence of a family drawn over the pitch (computed once from the events, cached in `<data>/app_cache`).
- **Compare**: two teams on the same scales, every fact as a row of dots, and their build-up replays side by side (families are fitted per team: same label, different groups).
- **Review**: the analyst sheet inside the app (yes / partly / no per sequence with its replay, five questions). Saves `review_<Team>_filled.csv` (readable by `src/report/summarize_review.py`) and `review_<Team>_answers.json`; the original sheet is not changed.
- **Clips → Match video**: load the match video file in the browser, set the kick-off of each half, and each clip jumps to its moment (3 s early). Offsets stay in the browser.
- **Tour**: the presentation button walks through the sections and then the next team every 15 s; Esc stops it.
- **Restarts → Where the first pass goes** (pressing map): every first pass of goal kicks, keeper distributions and throw-ins, coloured by how the possession ended, with first receivers and a Watch button. Same definitions as the restart sheet (the shares match `restarts_<Team>.json`).
- **Families → Pass network**: who passes to whom inside a family, players at their average position, shirt numbers with a key.
- **GIF** button on every replay: downloads the replay as an animated GIF to send to the players.
- **Overview → What changed in the last 5 matches**: restart figures where the last 5 matches fall outside the season interval (a hint to check on video).
- **Compare → Style map**: every team in the folder placed by its numbers (first two principal components of the standardised facts), with the closest teams. Descriptive; mixed leagues and seasons.
- **Clips → More like this**: the 8 sequences of the season closest to the selected one (start, end, path, passes, duration), click to replay.
- **Add team** (only with a data folder that has `matches/` and `ev/`): runs `src/oppreport.py` for a chosen team and shows its log.
- **Theme and print**: dark by default, light with the sun button (or `?theme=light` in the address); printing uses a white page.

Replays need the raw event files (`ev/` in the data folder). On `examples/` the app shows the families' average start and end instead.

## Test
`python -X utf8 tests/test_app_api.py [data folder]` checks the API against the pipeline files (ranks, clip lists, CSV export, review round trip).

## Development
Run `python -X utf8 app\run.py --no-browser` and, in another terminal, `cd app\frontend; npm run dev` (Vite proxies `/api` and `/sheets`).

Data: StatsBomb Open Data (non-commercial licence). Ranks against teams from other leagues and seasons are a rough guide.
