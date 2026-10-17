# Opposition report app (local)

A local web app over the files that `src/oppreport.py` writes. FastAPI backend (`app/backend/server.py`) + React frontend (`app/frontend`).
No new estimates: every number comes from `report_/restarts_/setpieces_/transitions_<Team>.json` and the clip CSVs.

## Run
One script does everything (stops an app already on the port, installs what is missing, rebuilds the frontend, clears the app cache, runs the tests, starts the app):
```powershell
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1                      # data in $env:OPPREPORT_DATA, else examples\
powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1 -DataDir <folder> -Port 8770 -SaltaTest
```
Step by step:
```powershell
pip install -r requirements.txt
cd app\frontend; npm install; npm run build; cd ..\..
python -X utf8 app\run.py                                   # example teams in examples\
python -X utf8 app\run.py --data-dir <data_folder>  # all teams processed there (e.g. the 10 thesis teams)
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
- **Game plan**: pick the opponent (and optionally your team): most used starting formations drawn on the pitch against each other, last 5 formations, how they play in six lines, and hints from fixed rules on where the opponent (and your team) rank among the teams in the folder, each with the numbers that triggered it and the section to check. Also what happened in their past matches and how your team did against a high press. Hints, not advice: no rule was tested for whether following it changes results. Rules in `app/backend/gameplan.py`.
- **Game plan → Key players** (needs `ev/`): top 3 per role from all matches, with shirt numbers: who the build-up goes through, who moves the ball into the final third, main threat (xG), corner and free-kick takers, who loses the ball in the own half (goalkeepers marked).
- **Game plan → When they score and concede** (needs `ev/`): goals and xG per match by 15-minute slot. The goals add up to the match scores for all 10 thesis teams (checked in `tests/test_app_api.py`).
- **Game plan → Watch first**: with your team chosen, their five matches against opponents whose PPDA in that match was closest to yours and with your back line, each with a link to its clips; without your team, their five most recent matches.
- **Game plan → Print match plan**: the page on paper for the staff.
- **Game plan → Coach brief**: the same hints written as a short plan by phase (with the ball, without the ball, transitions, set pieces) with three priorities; pick a question to read the matching part. Written by fixed templates from the numbers, offline: no language model, no external service, no cost.
- **Defending**: how the team defends without the ball (StatsBomb events only): pressures per match on a pitch grid with the mean height of the defensive actions, PPDA, shots and xG conceded, last 5 matches, ranks against the other teams. From `src/report/defending.py`.
- **Matchups**: the team's past matches split by opponent pressing (opponent PPDA in that match, above or below the median), opponent back line (three/five or four, from the starting formation) and home/away; per-match xG, shots, balls lost in the own half, pass completion under pressure, points, with the difference and its 95% interval and a verdict (clear / uncertain / group too small). Descriptive, not a recommendation of formation or style. From `src/report/matchups.py`.
- **Add team** (only with a data folder that has `matches/` and `ev/`): runs `src/oppreport.py` for a chosen team and shows its log.
- **Theme and print**: dark by default, light with the sun button (or `?theme=light` in the address); printing uses a white page.

Replays need the raw event files (`ev/` in the data folder). On `examples/` the app shows the families' average start and end instead.

## Test
`python -X utf8 tests/test_app_api.py [data folder]` checks the API against the pipeline files (ranks, clip lists, CSV export, review round trip).

## Development
Run `python -X utf8 app\run.py --no-browser` and, in another terminal, `cd app\frontend; npm run dev` (Vite proxies `/api` and `/sheets`).

Data: StatsBomb Open Data (non-commercial licence). Ranks against teams from other leagues and seasons are a rough guide.
