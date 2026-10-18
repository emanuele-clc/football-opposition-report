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
| restart | strongly recommended | on the first event of a restart: `goal_kick`, `throw_in`, `corner`, `free_kick`, `kick_off`, `penalty`, `keeper` (goalkeeper puts the ball back in play after holding it) |
| pass_length | optional | length in metres on a 120 x 80 pitch; computed from coordinates if missing |
| shot_goal | optional | 1 if the shot was a goal |
| player | optional | player performing the event (enables takers and receivers in the sheets) |
| recipient | optional | for passes: player who received it |
| xg | optional | for shots: expected goals from the provider |

Convention: the team performing an event always attacks from left to right. If the provider uses real pitch coordinates (e.g. 105 x 68 m) rescale them to 0-100 first. With 120 x 80 coordinates use `--coords 120x80`.

Check a file before converting: `python src/adapters/generic_csv.py events.csv --validate-only`.

## Why possession_id and restart matter
The report analyses open-play possessions with at least 3 passes. Without `restart`, corners, free kicks and kick-offs are not excluded. Without `possession_id`, possessions are reconstructed with a heuristic (a new possession starts at a restart, at the half, or when the other team makes two consecutive controlling actions or a shot).

Measured on one team (Barcelona 2015/16, 38 matches, StatsBomb data exported to this format; `tests/test_adapter_roundtrip.py`):
- with `possession_id` and `restart`: 1867 sequences reproduced out of 1867 (1 extra); features identical;
- with reconstructed possessions: 2182 sequences instead of 1867, 1534 of the 1867 (82%) reproduced identically, passes per sequence 8.3 instead of 9.3, shot rate 13.6% instead of 15.2%.
- restart and set-piece sheets: with `possession_id` 1083 of 1085 restart possessions and 368 of 368 set pieces reproduced (Bayer Leverkusen 2023/24: 863 of 863 and 310 of 310, including player names and xG); with reconstructed possessions all are found but about 6% of restart possessions and 3% of set pieces differ in at least one outcome.

- transition sheet: it does not use `possession_id` (it reads the order of actions): 1899 of 1899 losses and 2144 of 2149 recoveries identical with or without it (Leverkusen).

The few extra sequences with `possession_id` (1 for Barcelona, 4 for Leverkusen) are possessions that StatsBomb labels with the play pattern 'Other', which the generic format cannot express.

So with reconstructed possessions the numbers are usable for a rough picture but are biased and not comparable with numbers from provider-supplied possessions. Prefer the provider's possession identifiers.

## Second provider tested: Wyscout public data
`src/adapters/wyscout_to_generic_csv.py` converts the Wyscout public soccer-logs (Pappalardo et al. 2019, Scientific Data, CC BY 4.0; figshare collection 4415000) to this format. Tested on Napoli, Serie A 2017/18 (38 matches, 69,547 events): the full report, restart, set-piece and transition sheets run unchanged.
- The data has no possession identifiers and no xG: possessions are reconstructed (biased, see above) and xG columns stay empty.
- Goal kicks have a placeholder start position ((0,0) or (100,100)); the adapter puts them in the six-yard box (x 5, y 50). Before this fix only 6% of goal kicks looked short (StatsBomb, Napoli 2015/16: 45%): check every restart definition when adding a provider.
- Keeper distributions are inferred (a pass by the keeper right after a save or a run off the line), so they are undercounted.
- Use for a rough picture; do not mix ranks from this provider with StatsBomb teams.

Same matches from both providers (exploratory; Barcelona, La Liga 2017/18, the 36 matches in both datasets; `src/week4/exploratory_provider_samematch.py`, `results/exploratory_provider_samematch_Barcelona.json`). A = StatsBomb with its possessions, B = StatsBomb with reconstructed possessions, C = Wyscout:
- families fitted on A and applied unchanged to B and C: build-up shares within 3.5 points (B) and 2.4 points (C) of A; advanced within 6.1 (B) and 4.4 (C);
- sequences per match 51.0 / 58.5 / 53.6; passes per sequence 9.0 / 8.2 / 8.6; shot rate 13.7% / 12.2% / 12.8%; per match, A and C correlate 0.86 (sequences) and 0.95 (passes per sequence);
- larger gaps, all in C: long-pass share 0.21 vs 0.15; short first pass from goal kicks 23% vs 39% and from throw-ins 79-85% vs 91-96%; keeper restarts 56 vs 115; losses and recoveries per match 46-50 vs 62. Corners 202 vs 201.
- goals from shots: 90 in all three versions (the score says 93: three own goals, which are not shots).
So on these matches the family shares barely move between providers, while pass lengths, keeper restarts and transitions do: those sheets are not comparable across providers.

## Mapping hints (from memory; check against your provider's documentation)
- Opta-style feeds: positions on a 0-100 scale in the attacking direction of the team; pass end coordinates are usually event qualifiers; restarts appear as qualifiers or event types (goal kick, throw-in, corner).
- Wyscout-style feeds: positions on a 0-100 scale; the clock is often given per half, so convert to a cumulative minute; restarts appear as sub-event types.
- Always ask the provider for: coordinate system and attacking direction, whether the clock is cumulative, how possessions and restarts are marked.

## Video times
To get video times in the clip list, give a file `offsets.csv` with columns `match_id, half1_start, half2_start`: the video second at which the first and the second half kick off. Pass it with `--video-offsets offsets.csv` (example: `examples/offsets_example.csv`, one Barcelona match). Video time = half start + match clock (minus 2700 s in the second half). Matches missing from the file get an empty video time.

## What to ask a club
Provider and export format; coordinate convention; whether possession identifiers and restart markers are included; at least 30 matches of the opponent or of the league for reference; what can be published; whether a confidentiality agreement is needed.
