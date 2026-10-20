"""Every API endpoint for every team in a data folder: no server error, and JSON that a browser can read (no NaN/Infinity).
Usage:  python -X utf8 tests/test_all_teams.py [data_dir] [--fast]
Runs on the folder itself (read-only for the data; the app may write its cache in <data>/app_cache). --fast skips the endpoints
that read raw events (replay, paths, similar, pressing, network), which are slow on a full folder.
A 404 with a message is accepted (e.g. no events for replays, a sheet the team does not have); a 5xx or an unreadable JSON is a failure.
Added 18 Oct 2026 after a 2-match team (Valencia 2017/18) broke /api/teams/<key> with NaN intervals."""

import json, os, sys, time

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
fast = "--fast" in sys.argv
os.environ["OPPREPORT_DATA"] = os.path.abspath(args[0]) if args else os.path.join(root, "examples")
sys.path.insert(0, os.path.join(root, "app", "backend"))
from fastapi.testclient import TestClient
import server

c = TestClient(server.app, raise_server_exceptions=False)
fails, calls = [], 0


def strict(text):
    def bad(x):
        raise ValueError(f"{x} in JSON")

    return json.loads(text, parse_constant=bad)


def get(path, params=None, binary=False):
    global calls
    calls += 1
    r = c.get(path, params=params)
    if r.status_code >= 500:
        fails.append(f"{path} {params or ''} -> {r.status_code}")
        return None
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        fails.append(f"{path} {params or ''} -> {r.status_code} {r.text[:120]}")
        return None
    if binary or not r.headers.get("content-type", "").startswith("application/json"):
        return r
    try:
        return strict(r.text)
    except ValueError as e:
        fails.append(f"{path} {params or ''} -> {e}")
        return None


t0 = time.time()
teams = get("/api/teams") or []
print(f"{len(teams)} teams in {server.DATA}{' (fast)' if fast else ''}")
get("/api/info")
get("/api/stylemap")
get("/api/sources")
keys = [t["key"] for t in teams]
for i, t in enumerate(teams):
    k = t["key"]
    before = len(fails)
    d = get(f"/api/teams/{k}")
    if d is None:
        print(f"FAIL {t['team']}: team data")
        continue
    for kind in d.get("clips", []):
        rows = (get(f"/api/teams/{k}/clips/{kind}") or {}).get("rows", [])
        get(f"/api/teams/{k}/export/{kind}.csv", binary=True)
        if rows and not fast:
            r0 = rows[0]
            q = {x: r0[x] for x in ("match", "half", "minute", "second")}
            get(f"/api/teams/{k}/replay", q)
            if kind == "sequences":
                get(f"/api/teams/{k}/similar", q)
    get(f"/api/teams/{k}/gameplan")
    other = next((x for x in keys if x != k), None)
    if other:
        get(f"/api/teams/{k}/gameplan", {"mine": other})
    get(f"/api/teams/{k}/gameplan/events")
    w = get(f"/api/teams/{k}/without")
    if w and w.get("players"):
        get(f"/api/teams/{k}/without", {"player": w["players"][0]["player"]})
    get(f"/api/teams/{k}/review")
    for s in d.get("sheets", []):
        get(f"/sheets/{s}_{k}.html", binary=True)
    if not fast:
        get(f"/api/teams/{k}/paths")
        get(f"/api/teams/{k}/pressing")
        get(f"/api/teams/{k}/network")
    print(
        ("ok   " if len(fails) == before else "FAIL ")
        + f"{t['team']} ({d.get('matches')} matches)"
        + ("" if len(fails) == before else ": " + "; ".join(fails[before:])[:300]),
        flush=True,
    )
print(f"\n{calls} calls in {time.time() - t0:.0f} s")
print("ALL OK" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
