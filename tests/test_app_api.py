"""Smoke test of the app API on the example files (no raw events needed).
Usage:  python -X utf8 tests/test_app_api.py [data_dir]
Checks that every team in the folder loads, that the ranks agree with the JSON files they come from, that clip lists and the CSV export
match the clip CSVs row for row, and that the review sheet round-trips without touching the original file."""

import csv, io, json, os, sys, tempfile, shutil

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
src = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "examples")
tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "data")
shutil.copytree(src, data, ignore=shutil.ignore_patterns("ev", "matches", "app_cache"))
os.environ["OPPREPORT_DATA"] = data
sys.path.insert(0, os.path.join(root, "app", "backend"))
from fastapi.testclient import TestClient
import server

c = TestClient(server.app)
fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


teams = c.get("/api/teams").json()
check(len(teams) > 0, f"{len(teams)} teams in {src}")
for t in teams:
    k = t["key"]
    d = c.get(f"/api/teams/{k}").json()
    rep = json.load(open(os.path.join(data, f"report_{k}.json"), encoding="utf-8"))
    r = {x["id"]: x for x in d["ranks"]}
    check(
        abs(r["passes"]["value"] - rep["style"]["team"]["passes"]) < 1e-12,
        f"{t['team']}: passes per sequence equals report JSON",
    )
    check(
        all(1 <= x["rank"] <= x["of"] == len(teams) for x in d["ranks"]), f"{t['team']}: ranks within 1..{len(teams)}"
    )
    for kind, f in server.CLIPS.items():
        p = os.path.join(data, f"{f}_{k}.csv")
        if not os.path.exists(p):
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8", newline="")))
        api_rows = c.get(f"/api/teams/{k}/clips/{kind}").json()["rows"]
        check(len(api_rows) == len(rows), f"{t['team']}: {kind} clip list has {len(rows)} rows")
        fam = rows[0]["family"]
        exp = [x for x in rows if x["family"] == fam]
        got = list(csv.DictReader(io.StringIO(c.get(f"/api/teams/{k}/export/{kind}.csv", params={"family": fam}).text)))
        check(got == exp, f"{t['team']}: CSV export for {fam} identical to the clip CSV rows")
    if os.path.exists(os.path.join(data, f"defending_{k}.json")):
        de = json.load(open(os.path.join(data, f"defending_{k}.json"), encoding="utf-8"))
        check(abs(r["ppda"]["value"] - de["ppda"]["value"]) < 1e-12, f"{t['team']}: PPDA rank equals defending JSON")
    if os.path.exists(os.path.join(data, f"matchups_{k}.json")):
        mu = d["matchups"]
        v = mu["splits"]["venue"]
        pr = mu["splits"]["opp_press"]
        check(
            v["n_a"] + v["n_b"] == pr["n_a"] + pr["n_b"] == len(mu["per_match"]) == mu["matches"],
            f"{t['team']}: matchup groups add up to {mu['matches']} matches",
        )
        check(
            all(
                m["verdict"] == "small group"
                for s in mu["splits"].values()
                if min(s["n_a"], s["n_b"]) < mu["min_group"]
                for m in s["metrics"]
            ),
            f"{t['team']}: small groups never called clear",
        )
    if os.path.exists(os.path.join(data, f"review_{k}.csv")):
        before = open(os.path.join(data, f"review_{k}.csv"), encoding="utf-8").read()
        rv = c.get(f"/api/teams/{k}/review").json()
        n = len(rv["rows"])
        res = c.post(
            f"/api/teams/{k}/review",
            json={
                "verdicts": ["yes"] + [""] * (n - 1),
                "comments": [""] * n,
                "answers": ["test"] * 5,
                "reviewer": "test",
                "role": "test",
            },
        )
        filled = list(csv.DictReader(open(os.path.join(data, f"review_{k}_filled.csv"), encoding="utf-8", newline="")))
        check(
            res.status_code == 200 and filled[0]["coherent_with_family"] == "yes" and len(filled) == n,
            f"{t['team']}: review saved to review_{k}_filled.csv",
        )
        check(
            open(os.path.join(data, f"review_{k}.csv"), encoding="utf-8").read() == before,
            f"{t['team']}: original review sheet unchanged",
        )
    gp = c.get(f"/api/teams/{k}/gameplan").json()
    check(
        all(
            e["value"] == r[e["id"]]["value"] and e["rank"] == r[e["id"]]["rank"]
            for h in gp["hints"]
            for e in h["evidence"]
        ),
        f"{t['team']}: game plan hints show the same values and ranks as the ranking",
    )
    if d.get("matchups") and (
        os.path.exists(os.path.join(data, f"keyplayers_{k}.json")) or os.path.isdir(os.path.join(src, "ev"))
    ):
        kp = (
            c.get(f"/api/teams/{k}/gameplan/events").json()
            if os.path.exists(os.path.join(data, f"keyplayers_{k}.json"))
            else server.plan_rules.events_view(t["team"], server.team_matches(k), os.path.join(src, "ev"))
        )
        tl = kp["timeline"]
        gf = sum(int(m["score"].split("-")[0]) for m in d["matchups"]["per_match"])
        ga = sum(int(m["score"].split("-")[1]) for m in d["matchups"]["per_match"])
        check(
            (sum(x["goals_for"] for x in tl), sum(x["goals_against"] for x in tl)) == (gf, ga),
            f"{t['team']}: timeline goals {gf}-{ga} equal the match scores",
        )
        if "goals" in kp:
            check(
                (sum(g["side"] == "for" for g in kp["goals"]), sum(g["side"] == "against" for g in kp["goals"]))
                == (gf, ga),
                f"{t['team']}: goal list has {gf} scored and {ga} conceded",
            )
    if os.path.exists(os.path.join(data, f"keyplayers_{k}.json")) and d.get("matchups"):
        wp = c.get(f"/api/teams/{k}/without").json()["players"]
        p0 = next((p for p in wp if p["usable"]), wp[0])
        w = c.get(f"/api/teams/{k}/without", params={"player": p0["player"]}).json()
        check(
            w["n_with"] + w["n_without"] == d["matchups"]["matches"] and w["n_with"] == p0["starts"],
            f"{t['team']}: without {p0['player']}: {w['n_with']} + {w['n_without']} matches",
        )
        check(
            all(m["verdict"] == "small group" for m in w["metrics"]) if min(w["n_with"], w["n_without"]) < 6 else True,
            f"{t['team']}: small groups never called clear (without a player)",
        )
    if gp.get("foul_zones"):
        check(
            len(gp["foul_zones"]["zones"]) == 9 and (gp["breaks"] is None or len(gp["breaks"]["zones"]) == 12),
            f"{t['team']}: foul zones and break map present",
        )
    other = next((x["key"] for x in teams if x["key"] != k), None)
    if other:
        gp2 = c.get(f"/api/teams/{k}/gameplan", params={"mine": other}).json()
        check(
            gp2["mine"] == teams[[x["key"] for x in teams].index(other)]["team"]
            and all(h["side"] == "opp" or len(h["evidence"]) > 0 for h in gp2["hints"]),
            f"{t['team']}: game plan with your team",
        )
check(
    all(len(c.get(f"/api/teams/{x['key']}/gameplan").json()["brief"]["phases"]) == 4 for x in teams),
    "coach brief has the four phases for every team",
)
sm = c.get("/api/stylemap").json()
check(
    len(sm["teams"]) == len(teams) and all(len(t["nearest"]) == min(3, len(teams) - 1) for t in sm["teams"]),
    f"style map places {len(teams)} teams with their nearest teams",
)
check(c.get("/api/teams/Nobody").status_code == 404, "unknown team gives 404")
check(
    c.get("/..%2F..%2Fsrc%2Foppreport.py").text.lstrip().lower().startswith("<!doctype")
    or not os.path.isdir(server.DIST),
    "no file served from outside the frontend build",
)
shutil.rmtree(tmp)
print(f"\n{'ALL OK' if not fails else f'{len(fails)} FAILED'}")
sys.exit(1 if fails else 0)
