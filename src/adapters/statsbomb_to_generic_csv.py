"""Exports StatsBomb events to the generic CSV (docs/data_format.md). Used to test the adapter (tests/test_adapter_roundtrip.py)
and as an example of mapping a provider.
Usage:  python statsbomb_to_generic_csv.py <matches.json> "<Team>" <data_folder> <out.csv> [--no-possession] [--no-restart]
Output coordinates: 120 x 80 (as StatsBomb), so the conversion must use --coords 120x80."""

import sys, os, json
import pandas as pd

TYPE = {
    "Pass": "pass",
    "Carry": "carry",
    "Shot": "shot",
    "Dribble": "dribble",
    "Duel": "duel",
    "Interception": "interception",
    "Foul Committed": "foul",
    "Clearance": "clearance",
    "Ball Recovery": "ball_recovery",
    "Block": "block",
}
RESTART = {
    "From Goal Kick": "goal_kick",
    "From Throw In": "throw_in",
    "From Corner": "corner",
    "From Free Kick": "free_kick",
    "From Kick Off": "kick_off",
    "From Keeper": "keeper",
}


def export(mf, team, base, out, possession=True, restart=True):
    ms = sorted(
        [
            g
            for g in json.load(open(mf, encoding="utf-8"))
            if team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])
        ],
        key=lambda g: g["match_date"],
    )
    rows = []
    for g in ms:
        seen = set()
        for e in json.load(open(f"{base}/ev/{g['match_id']}.json", encoding="utf-8")):
            t = TYPE.get(e["type"]["name"], "other")
            loc = e.get("location") or [None, None]
            end = (e.get("pass") or e.get("carry") or {}).get("end_location") or [None, None]
            first = e["possession"] not in seen
            seen.add(e["possession"])
            r = dict(
                match_id=g["match_id"],
                match_date=g["match_date"],
                home_team=g["home_team"]["home_team_name"],
                away_team=g["away_team"]["away_team_name"],
                period=e["period"],
                minute=e["minute"],
                second=e["second"],
                team=e["team"]["name"],
                event_type=t,
                x=loc[0],
                y=loc[1],
                end_x=end[0],
                end_y=end[1],
                pass_length=e["pass"].get("length") if t == "pass" else None,
                shot_goal=int(e["shot"]["outcome"]["name"] == "Goal") if t == "shot" else None,
                player=(e.get("player") or {}).get("name"),
                recipient=(e["pass"].get("recipient") or {}).get("name") if t == "pass" else None,
                xg=e["shot"].get("statsbomb_xg") if t == "shot" else None,
                pass_outcome=("incomplete" if "outcome" in e["pass"] else "complete") if t == "pass" else None,
            )
            if possession:
                r["possession_id"] = e["possession"]
            if restart:
                r["restart"] = RESTART.get(e["play_pattern"]["name"], "") if first else ""
            rows.append(r)
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")
    print(f"{len(ms)} partite, {len(rows)} eventi -> {out}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 4:
        sys.exit(__doc__)
    export(a[0], a[1], a[2], a[3], "--no-possession" not in sys.argv, "--no-restart" not in sys.argv)
