"""Smoke test of the app API on the example files (no raw events needed).
Usage:  python -X utf8 tests/test_app_api.py [data_dir]
Checks that every team in the folder loads, that the ranks agree with the JSON files they come from, that clip lists and the CSV export
match the clip CSVs row for row, and that the review sheet round-trips without touching the original file."""
import csv, io, json, os, sys, tempfile, shutil
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
src = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "examples")
tmp = tempfile.mkdtemp(); data = os.path.join(tmp, "data"); shutil.copytree(src, data, ignore=shutil.ignore_patterns("ev", "matches", "app_cache"))
os.environ["OPPREPORT_DATA"] = data
sys.path.insert(0, os.path.join(root, "app", "backend"))
from fastapi.testclient import TestClient
import server
c = TestClient(server.app); fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

teams = c.get("/api/teams").json()
check(len(teams) > 0, f"{len(teams)} teams in {src}")
for t in teams:
    k = t["key"]; d = c.get(f"/api/teams/{k}").json()
    rep = json.load(open(os.path.join(data, f"report_{k}.json"), encoding="utf-8"))
    r = {x["id"]: x for x in d["ranks"]}
    check(abs(r["passes"]["value"] - rep["style"]["team"]["passes"]) < 1e-12, f"{t['team']}: passes per sequence equals report JSON")
    check(all(1 <= x["rank"] <= x["of"] == len(teams) for x in d["ranks"]), f"{t['team']}: ranks within 1..{len(teams)}")
    for kind, f in server.CLIPS.items():
        p = os.path.join(data, f"{f}_{k}.csv")
        if not os.path.exists(p): continue
        rows = list(csv.DictReader(open(p, encoding="utf-8", newline="")))
        api_rows = c.get(f"/api/teams/{k}/clips/{kind}").json()["rows"]
        check(len(api_rows) == len(rows), f"{t['team']}: {kind} clip list has {len(rows)} rows")
        fam = rows[0]["family"]
        exp = [x for x in rows if x["family"] == fam]
        got = list(csv.DictReader(io.StringIO(c.get(f"/api/teams/{k}/export/{kind}.csv", params={"family": fam}).text)))
        check(got == exp, f"{t['team']}: CSV export for {fam} identical to the clip CSV rows")
    if os.path.exists(os.path.join(data, f"review_{k}.csv")):
        before = open(os.path.join(data, f"review_{k}.csv"), encoding="utf-8").read()
        rv = c.get(f"/api/teams/{k}/review").json(); n = len(rv["rows"])
        res = c.post(f"/api/teams/{k}/review", json={"verdicts": ["yes"] + [""] * (n - 1), "comments": [""] * n, "answers": ["test"] * 5, "reviewer": "test", "role": "test"})
        filled = list(csv.DictReader(open(os.path.join(data, f"review_{k}_filled.csv"), encoding="utf-8", newline="")))
        check(res.status_code == 200 and filled[0]["coherent_with_family"] == "yes" and len(filled) == n, f"{t['team']}: review saved to review_{k}_filled.csv")
        check(open(os.path.join(data, f"review_{k}.csv"), encoding="utf-8").read() == before, f"{t['team']}: original review sheet unchanged")
check(c.get("/api/teams/Nobody").status_code == 404, "unknown team gives 404")
check(c.get("/..%2F..%2Fsrc%2Foppreport.py").text.lstrip().lower().startswith("<!doctype") or not os.path.isdir(server.DIST), "no file served from outside the frontend build")
shutil.rmtree(tmp)
print(f"\n{'ALL OK' if not fails else f'{len(fails)} FAILED'}")
sys.exit(1 if fails else 0)
