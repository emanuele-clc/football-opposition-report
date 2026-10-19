"""Evidence grade, part 2 (protocol: docs/protocol_evidence_grade.md, section 'Second provider'): are the statements the same when the events come from Wyscout?
Same 36 Barcelona 2017/18 matches in StatsBomb and Wyscout public data. Label only: it does not change the grade. Run after the confirmatory run
(needs the between-team SD from results/evidence_grade.json).
Usage:
    python -X utf8 src/week4/evidence_provider.py <sb matches.json> <sb data dir> <wyscout dir> <work dir>
    e.g. C:/Users/ecole/sbdata/matches/11_1.json C:/Users/ecole/sbdata C:/Users/ecole/wyscout_open C:/Users/ecole/evidence_work/provider
Output: results/evidence_provider_Barcelona.json (refuses to overwrite). --check: code check only (first 5 matches, prints no value, writes nothing). Wyscout data: Pappalardo et al. 2019 (CC BY 4.0)."""
import sys, os, json, datetime
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
a = [x for x in sys.argv[1:] if not x.startswith("--")]
if len(a) != 4: sys.exit(__doc__)
SB_MF, SB_BASE, WY, WORK = (os.path.abspath(x) for x in a); TEAM = "Barcelona"
here = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(here, "..", ".."))
sys.path[:0] = [here, os.path.join(REPO, "src", "adapters")]
import evidence_grade as E, generic_csv as G, wyscout_to_generic_csv as W
OUT = os.path.join(REPO, "results", "evidence_provider_Barcelona.json"); GRADES = os.path.join(REPO, "results", "evidence_grade.json")
CHECK = "--check" in sys.argv
if os.path.exists(OUT) and not CHECK: sys.exit(f"{OUT} already exists: the run is done once.")
if not os.path.exists(GRADES) and not CHECK: sys.exit("Run the confirmatory evidence grade first (results/evidence_grade.json).")
SD = {c: 1.0 for c in E.CLAIMS} if CHECK else {c: r.get("sd_between_teams") for c, r in json.load(open(GRADES, encoding="utf-8"))["statements"].items()}
TESTABLE = ["S01", "S02", "S03", "S04", "S05", "S06", "F07", "F08", "R09", "R10", "R11", "R12", "R13", "P14", "P15", "P16", "P17", "T18", "T19", "T20", "T21", "T22", "A29", "K34"]
SEEN = {"S01", "S02", "S03", "S04", "S05", "S06", "F07", "F08", "R09", "R12", "P14", "T18"}   # compared on these matches on 18 Oct (exploratory)
os.makedirs(WORK, exist_ok=True)

# pair matches by date (as exploratory_provider_samematch.py)
sb = sorted([g for g in json.load(open(SB_MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
wy_csv = os.path.join(WORK, "wyscout_all.csv")
if not os.path.exists(wy_csv):
    W.main(os.path.join(WY, "events_Spain.json"), os.path.join(WY, "matches_Spain.json"), os.path.join(WY, "teams.json"), os.path.join(WY, "players.json"), TEAM, wy_csv)
wdf = pd.read_csv(wy_csv); wdates = wdf.groupby("match_id").match_date.first().to_dict(); D = lambda s: datetime.date.fromisoformat(str(s)[:10]); pairs = {}
for g in sb:
    near = [m for m, d in wdates.items() if abs((D(d) - D(g["match_date"])).days) <= 1]
    if len(near) == 1: pairs[g["match_id"]] = near[0]
dC = os.path.join(WORK, "C")
if not os.path.exists(dC): wdf[wdf.match_id.isin(set(pairs.values()))].to_csv(os.path.join(WORK, "C.csv"), index=False); G.convert(os.path.join(WORK, "C.csv"), dC, "100")
wms = {g["match_id"]: g for g in json.load(open(os.path.join(dC, "matches", "generic.json"), encoding="utf-8"))}
print(f"{len(sb)} StatsBomb matches, {len(pairs)} paired with Wyscout")


def values(games, base):
    tmp = os.path.join(WORK, "one_match.json"); V, recv, ctak, seq = [], [], [], []
    for mi, g in enumerate(games):
        v, r, c, s = E.match_values(g, TEAM, base, tmp, full=False); V.append(v); ctak.append(c); seq.append(s.assign(mi=mi))
    return V, ctak, pd.concat(seq, ignore_index=True)


paired = [g for g in sb if g["match_id"] in pairs][:5 if CHECK else None]
A = values(paired, SB_BASE); C = values([wms[pairs[g["match_id"]]] for g in paired], dC)
res = dict(protocol="docs/protocol_evidence_grade.md (Second provider)", team=TEAM, season="2017/2018", matches=len(pairs), statements={},
           sources="StatsBomb Open Data; Wyscout public data, Pappalardo et al. 2019 (CC BY 4.0)")
for c in TESTABLE:
    r = dict(statement=E.CLAIMS[c], seen_before=c in SEEN)
    if c in E.FAM:   # families fitted on the StatsBomb season, frozen, applied to Wyscout
        ph = E.FAM[c]; sel = lambda s: s[(s.x0 < E.CUT) if ph == "build-up" else (s.x0 >= E.CUT)]; sa, sw = sel(A[2]), sel(C[2]); k = E.K[ph]
        sc = StandardScaler().fit(sa[E.COLS].values); km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(sa[E.COLS].values))
        order = sorted(range(k), key=lambda q: (sa.x0.values[km.labels_ == q].mean(), -(km.labels_ == q).sum()))
        la, lw = km.labels_, km.predict(sc.transform(sw[E.COLS].values))
        r["shares"] = {f"{'B' if ph == 'build-up' else 'A'}{i + 1}": dict(statsbomb=float((la == q).mean()), wyscout=float((lw == q).mean())) for i, q in enumerate(order)}
        r["largest_difference"] = max(abs(v["statsbomb"] - v["wyscout"]) for v in r["shares"].values()); r["label"] = "same in Wyscout" if r["largest_difference"] <= 0.10 else "differs"
    else:
        if c == "K34":
            ld = E.leader(A[1]); ser = lambda X: (np.array([cn[ld] for cn in X[1]], float), np.array([sum(cn.values()) for cn in X[1]], float)) if ld else (np.zeros(1), np.zeros(1))
            r["leader_statsbomb"], r["leader_wyscout"] = ld, E.leader(C[1])
        else: ser = lambda X: (np.array([v[c][0] for v in X[0]]), np.array([v[c][1] for v in X[0]]))
        (na, da), (nw, dw) = ser(A), ser(C)
        r["statsbomb"] = float(na.sum() / da.sum()) if da.sum() else None; r["wyscout"] = float(nw.sum() / dw.sum()) if dw.sum() else None
        ok = (da > 0) & (dw > 0)
        r["per_match_r"] = float(np.corrcoef(na[ok] / da[ok], nw[ok] / dw[ok])[0, 1]) if ok.sum() >= 3 else None
        if r["statsbomb"] is None or r["wyscout"] is None or not SD.get(c): r["label"] = "not testable"
        else:
            r["difference_over_sd"] = abs(r["wyscout"] - r["statsbomb"]) / SD[c]; r["label"] = "same in Wyscout" if r["difference_over_sd"] <= 0.5 else "differs"
    res["statements"][c] = r
    if not CHECK: print(f"{c} {r['statement'][:48]:48} {r['label']}{' (seen before)' if r['seen_before'] else ''}")
if CHECK: sys.exit(f"check passed: {len(res['statements'])} statements computed on {len(paired)} matches (no values printed, nothing written)")
for c in E.CLAIMS:
    if c not in TESTABLE: res["statements"][c] = dict(statement=E.CLAIMS[c], label="not testable", why="needs Pressure/Duel events, xG or pass outcomes (not in the generic CSV)")
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False); print("->", OUT)
