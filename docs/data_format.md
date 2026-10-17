# Input data format (generic CSV)

The report pipeline reads StatsBomb-style events. To use data from any other provider, map it to one CSV with one row per event; `src/adapters/generic_csv.py` converts it and `src/oppreport.py` does everything in one command.

## Columns
| Column | Required | Meaning |
|---|---|---|
| match_id | yes | match identifier |
| match_date | yes | date, e.g. 2026-03-14 |
| home_team, away_team | yes | team names (the team you analyse must be spelled identically everywhere) |
| period | yes | 1 or 2 |
| minute, second | yes | match clock; **minute is cumulative** (the second half starts at 45) |
| team | yes | team that performs the event |
| event_type | yes | `pass`, `carry`, `shot`, `dribble`; anything else counts as `other` |
| x, y | yes for pass/carry/shot/dribble | position; with the default `--coords 100`, x from 0 (own goal) to 100 (opponent goal) and y from 0 to 100 |
| end_x, end_y | passes and carries | end position, same scale |
| possession_id | strongly recommended | possession identifier; if missing it is reconstructed (see below) |
| restart | strongly recommended | on the first event of a restart: `goal_kick`, `throw_in`, `corner`, `free_kick`, `kick_off`, `penalty` |
| pass_length | optional | length in metres on a 120 x 80 pitch; computed from coordinates if missing |
| shot_goal | optional | 1 if the shot was a goal |

Convention: the team performing an event always attacks from left to right. If the provider uses real pitch coordinates (e.g. 105 x 68 m) rescale them to 0-100 first. With 120 x 80 coordinates use `--coords 120x80`.

Check a file before converting: `python src/adapters/generic_csv.py events.csv --validate-only`.

## Why possession_id and restart matter
The report analyses open-play possessions with at least 3 passes. Without `restart`, corners, free kicks and kick-offs are not excluded. Without `possession_id`, possessions are reconstructed with a heuristic (a new possession starts at a restart, at the half, or when the other team makes two consecutive controlling actions or a shot).

Measured on one team (Barcelona 2015/16, 38 matches, StatsBomb data exported to this format; `tests/test_adapter_roundtrip.py`):
- with `possession_id` and `restart`: 1867 sequences reproduced out of 1867 (1 extra); features identical;
- with reconstructed possessions: 2170 sequences instead of 1867, 1507 of the 1867 (81%) reproduced identically, passes per sequence 8.3 instead of 9.3, shot rate 13.6% instead of 15.2%.

So with reconstructed possessions the numbers are usable for a rough picture but are biased and not comparable with numbers from provider-supplied possessions. Prefer the provider's possession identifiers.

## Mapping hints (from memory; check against your provider's documentation)
- Opta-style feeds: positions on a 0-100 scale in the attacking direction of the team; pass end coordinates are usually event qualifiers; restarts appear as qualifiers or event types (goal kick, throw-in, corner).
- Wyscout-style feeds: positions on a 0-100 scale; the clock is often given per half, so convert to a cumulative minute; restarts appear as sub-event types.
- Always ask the provider for: coordinate system and attacking direction, whether the clock is cumulative, how possessions and restarts are marked.

## Video times
To get video times in the clip list, give a file `offsets.csv` with columns `match_id, half1_start, half2_start`: the video second at which the first and the second half kick off. Pass it with `--video-offsets offsets.csv` (example: `examples/offsets_example.csv`, one Barcelona match). Video time = half start + match clock (minus 2700 s in the second half). Matches missing from the file get an empty video time.

## What to ask a club
Provider and export format; coordinate convention; whether possession identifiers and restart markers are included; at least 30 matches of the opponent or of the league for reference; what can be published; whether a confidentiality agreement is needed.
