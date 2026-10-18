# Tracking data (exploratory extension)

Added 18 Oct 2026. Exploratory: no protocol was committed before these runs, so none of this is a confirmatory result. Definitions were fixed in the script headers before the first run, and each script was run once (`results/exploratory_*.json` are not overwritten: the scripts stop if the file exists).

## Why

The thesis uses event data (StatsBomb Open Data). Two of the three methods suggested as "what elite clubs use" need tracking data (positions of all 22 players over time): pitch control and ghosting / sequence models of player movement. StatsBomb 360 freeze frames are snapshots of the visible area without velocities, so they cannot support either. Expected Threat (xT) needs only events and is part of the report (`src/report/xt_model.py`, `src/report/xthreat.py`).

## Data

Bassek, M., Rein, R., Weber, H. & Memmert, D. (2025). An integrated dataset of spatiotemporal and event data in elite soccer. *Scientific Data* 12, 195. https://doi.org/10.1038/s41597-025-04505-y. Files on figshare (article 28196177), licence CC BY 4.0, released with the authorisation of the DFL.

- 7 matches, season 2022/23: 2 Bundesliga (1. FC Köln - FC Bayern München 1:2, VfL Bochum - Bayer 04 Leverkusen 3:0) and 5 2. Bundesliga, all with Fortuna Düsseldorf at home.
- Positions of every player and the ball at 25 Hz (optical tracking), ball in play / possession flags, official DFL events (passes with outcome, shots with xG).
- About 2.6 GB of XML. Kept outside the repo, like the StatsBomb files: `C:\Users\ecole\dfl_tracking` (raw) and `C:\Users\ecole\dfl_tracking\npz` (compact arrays written by the loader).
- Not a sample of any league: five of seven matches share one home team.

Other open tracking data checked: Metrica Sports sample data (3 anonymised matches, no formal licence, asks for attribution); SkillCorner open data (10 A-League 2024/25 matches, broadcast tracking at 10 fps, players off screen are extrapolated); PFF FC 2022 World Cup (64 matches, broadcast tracking, access through a form, terms not public on the announcement page). The DFL set was chosen because it is full-pitch optical tracking with events on the same matches and an explicit open licence.

## Commands (PowerShell, from the repo folder)

```
python -X utf8 src/tracking/dfl_load.py C:\Users\ecole\dfl_tracking          # once, about 2 minutes; skips matches done
python -X utf8 src/tracking/pitch_control.py C:\Users\ecole\dfl_tracking     # -> results/exploratory_pitch_control.json
python -X utf8 src/tracking/ghosting.py C:\Users\ecole\dfl_tracking          # -> results/exploratory_ghosting.json (needs torch)
```
The app shows the matches in the section Context -> Tracking lab when the folder exists (or set `OPPREPORT_TRACKING`).

## Event-tracking sync

DFL passes carry only the operator's time. A pass is placed at the frame, within +/- 1.5 s of that time, where the ball is closest to the passer; passes where that distance is over 2 m are left out of the pass check. DFL gives its own computed frame for shots: the sync differs from it by a median of 0.2 to 0.9 s depending on the match. This is a limit of the pass check.

## Results

- Pitch control pass check: 4,492 open-play passes, 80% completed. AUC: pitch control 0.89 (95% 0.88-0.90), nearest-player margin 0.85 (0.84-0.86), shorter pass 0.46 (0.44-0.48). Pitch control minus margin +0.04 (0.034-0.045): it adds, a little. Caution: the end point is where the next player touches the ball, which favours both models, so the absolute AUCs are optimistic; blocked passes end short, which pushes the length AUC below 0.5. The comparison between models is fair.
- Space (descriptive): the team in possession controls 18-27% of the opponent half, the defending team 13-24% of its own half (every 2 s of play, 14 team-matches).
- Ghosting (3 s ahead, train 5 / test 2 matches): mean position error, stays put 7.4 m, constant velocity 5.2 m, ridge 3.7 m, LSTM 4.4 m; back-line height error 4.3 / 2.7 / 1.9 / 2.3 m. The LSTM beats the naive baselines, not the linear model.

See `results/exploratory_pitch_control.json` and `results/exploratory_ghosting.json`; summary in CLAUDE.md section 6 (18 Oct).
