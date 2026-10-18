"""EXPLORATORY (not a hypothesis test). Same matches, two providers: how much does the report change when the events come from Wyscout instead of StatsBomb?
The earlier check (results/exploratory_provider_wyscout_napoli.json) compared different seasons; here the matches are the same, so differences come from the data, not the team.
Usage:
    python -X utf8 src/week4/exploratory_provider_samematch.py <sb matches.json> <sb data dir> <wyscout dir> "<Team>" <work dir> <out.json>
    e.g. matches/11_1.json C:/Users/ecole/sbdata C:/Users/ecole/wyscout_open Barcelona C:/tmp/prov results/exploratory_provider_samematch_Barcelona.json
Wyscout dir must contain events_<Country>.json, matches_<Country>.json, teams.json, players.json (Pappalardo et al. 2019, CC BY 4.0); country from --country (default Spain).
Definitions (fixed before the first run):
- Same matches: a Wyscout match of the team is paired with the StatsBomb match whose date is within 1 day (UTC vs local date); unpaired matches are dropped from both.
- Three versions of the same matches:
  A  StatsBomb direct (provider possessions and play patterns) = reference;
  B  StatsBomb exported to the generic CSV without possession_id (src/adapters/statsbomb_to_generic_csv.py --no-possession): only the possession reconstruction differs from A;
  C  Wyscout via src/adapters/wyscout_to_generic_csv.py (reconstructed possessions, Wyscout event definitions).
  B vs A = cost of reconstructing possessions; C vs B = provider definitions (coordinates, event types, restarts) with the same reconstruction.
- Style: sequences per match, build-up share (x0 < 45), passes per sequence, long-pass share, duration, shot rate.
- Families: fitted on A exactly as make_report.py (per phase StandardScaler + KMeans k=5/3, n_init=20, random_state=0, ordered by mean x0);
  B and C sequences are assigned to A's families with A's scaler and centroids (frozen). Reported: share per family and the largest absolute difference from A.
- Per match: Pearson correlation between A and C of sequences per match and of passes per sequence (does Wyscout rank the matches the same way?).
- Restarts (restarts.py): count and share with a short first pass (< 30 m) per kind. Set pieces (setpieces.py): corners and free kicks.
  Transitions (transitions.py): losses and recoveries per match. Goals: team goals per match from shots vs the StatsBomb score.
- No pass/fail rule: ratios are reported as they come. Do not tune the adapter on these matches and rerun to make the numbers closer
  (any adapter change found here must be documented and the comparison rerun in full, with the old file kept in git history)."""
import sys, os, json, datetime
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
a = [x for x in sys.argv[1:] if not x.startswith("--")]
if len(a) != 6: sys.exit(__doc__)
SB_MF, SB_BASE, WY, TEAM, WORK, OUT = os.path.abspath(a[0]), os.path.abspath(a[1]), os.path.abspath(a[2]), a[3], os.path.abspath(a[4]), a[5]
COUNTRY = next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--country=")), "Spain")
if not os.path.exists(SB_MF): SB_MF = os.path.join(SB_BASE, a[0])
here = os.path.dirname(os.path.abspath(__file__)); src = os.path.join(here, "..")
sys.argv = ["x", SB_MF, TEAM, SB_BASE]; sys.path[:0] = [os.path.join(src, "week2"), os.path.join(src, "adapters"), os.path.join(src, "report")]
import sequences_clustering as S, generic_csv as G, statsbomb_to_generic_csv as E, wyscout_to_generic_csv as W, restarts as RS, setpieces as SP, transitions as TR
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]; CUT = 45; K = {"build-up": 5, "advanced": 3}
os.makedirs(WORK, exist_ok=True)

# pair matches by date
sb = [g for g in json.load(open(SB_MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
wy_csv = os.path.join(WORK, "wyscout_all.csv")
if not os.path.exists(wy_csv):
    W.main(os.path.join(WY, f"events_{COUNTRY}.json"), os.path.join(WY, f"matches_{COUNTRY}.json"), os.path.join(WY, "teams.json"), os.path.join(WY, "players.json"), TEAM, wy_csv)
wdf = pd.read_csv(wy_csv); wdates = wdf.groupby("match_id").match_date.first().to_dict()
D = lambda s: datetime.date.fromisoformat(str(s)[:10]); pairs = {}
for g in sb:
    near = [m for m, d in wdates.items() if abs((D(d) - D(g["match_date"])).days) <= 1]
    if len(near) == 1: pairs[g["match_id"]] = near[0]
print(f"{len(sb)} StatsBomb matches, {len(wdates)} Wyscout matches, {len(pairs)} paired")
sb_keep = os.path.join(WORK, "sb_matches.json"); json.dump([g for g in sb if g["match_id"] in pairs], open(sb_keep, "w", encoding="utf-8"))
date_of = {g["match_id"]: g["match_date"] for g in sb}; score = {g["match_id"]: g["home_score"] if g["home_team"]["home_team_name"] == TEAM else g["away_score"] for g in sb}

# build the three versions
dirs = {"A": (sb_keep, SB_BASE)}
dB = os.path.join(WORK, "B"); E.export(sb_keep, TEAM, SB_BASE, os.path.join(WORK, "B.csv"), possession=False); G.convert(os.path.join(WORK, "B.csv"), dB, "120x80")
dirs["B"] = (os.path.join(dB, "matches", "generic.json"), dB)
dC = os.path.join(WORK, "C"); wdf[wdf.match_id.isin(set(pairs.values()))].to_csv(os.path.join(WORK, "C.csv"), index=False); G.convert(os.path.join(WORK, "C.csv"), dC, "100")
dirs["C"] = (os.path.join(dC, "matches", "generic.json"), dC)
inv = {v: k for k, v in pairs.items()}   # wyscout id -> statsbomb id

def run(v):
    mf, base = dirs[v]
    for M in (S, RS, SP, TR): M.MF, M.BASE = mf, base
    seq = S.extract()[0]; rs = RS.extract()[0]; sp = SP.extract()[0]; tl, tr = TR.extract()[:2]
    goals = {}
    for g in json.load(open(mf, encoding="utf-8")):
        n = sum(e["type"]["name"] == "Shot" and e["team"]["name"] == TEAM and e["shot"]["outcome"]["name"] == "Goal" for e in json.load(open(f"{base}/ev/{g['match_id']}.json", encoding="utf-8")))
        goals[inv.get(g["match_id"], g["match_id"])] = int(n)
    for d in (seq, rs, sp, tl, tr):
        if len(d): d["sbm"] = [inv.get(m, m) for m in d.match]
    seq["w0"] = (seq.y0 - 40).abs(); seq["w1"] = (seq.y1 - 40).abs()
    return dict(seq=seq, rs=rs, sp=sp, tl=tl, tr=tr, goals=goals)

R = {v: run(v) for v in "ABC"}; n = len(pairs); res = {"note": "EXPLORATORY: same matches from two providers (definitions in the script header). A = StatsBomb with provider possessions, B = StatsBomb with reconstructed possessions, C = Wyscout (reconstructed). B vs A = reconstruction, C vs B = provider.",
       "sources": "StatsBomb Open Data; Wyscout public data, Pappalardo et al. 2019 (CC BY 4.0)", "team": TEAM, "matches": n, "pairs": {str(k): int(v) for k, v in pairs.items()}}
res["style"] = {v: dict(sequences=int(len(R[v]["seq"])), per_match=len(R[v]["seq"]) / n, buildup_share=float((R[v]["seq"].x0 < CUT).mean()), passes=float(R[v]["seq"].n_pass.mean()),
                         long=float(R[v]["seq"].long_share.mean()), dur=float(R[v]["seq"].dur.mean()), shot=float(R[v]["seq"].shot.mean())) for v in "ABC"}

# families: fit on A, assign B and C with A's scaler and centroids
res["families"] = {}
for ph, k in K.items():
    sel = lambda d: d[d.x0 < CUT] if ph == "build-up" else d[d.x0 >= CUT]
    a_ = sel(R["A"]["seq"]); sc = StandardScaler().fit(a_[COLS].values); km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(a_[COLS].values))
    order = sorted(range(k), key=lambda c: (a_.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum())); name = {c: f"{'B' if ph == 'build-up' else 'A'}{i + 1}" for i, c in enumerate(order)}
    sh = {}
    for v in "ABC":
        lab = km.predict(sc.transform(sel(R[v]["seq"])[COLS].values)); sh[v] = {name[c]: float((lab == c).mean()) for c in order}
    res["families"][ph] = dict(shares=sh, max_abs_diff={v: max(abs(sh[v][f] - sh["A"][f]) for f in sh["A"]) for v in "BC"})

# per match agreement A vs C
pm = {}
for v in "AC":
    s = R[v]["seq"]; pm[v] = s.groupby("sbm").agg(n=("n_pass", "size"), passes=("n_pass", "mean"))
j = pm["A"].join(pm["C"], lsuffix="_A", rsuffix="_C", how="inner")
res["per_match_corr_A_C"] = dict(sequences=float(np.corrcoef(j.n_A, j.n_C)[0, 1]), passes=float(np.corrcoef(j.passes_A, j.passes_C)[0, 1]), matches=int(len(j)))

res["restarts"] = {v: {kd: dict(n=int((R[v]["rs"].kind == kd).sum()), short=float(R[v]["rs"][R[v]["rs"].kind == kd].short.mean()) if (R[v]["rs"].kind == kd).any() else None)
                       for kd in sorted(R["A"]["rs"].kind.unique())} for v in "ABC"}
res["setpieces"] = {v: {kd: int((R[v]["sp"].kind == kd).sum()) for kd in sorted(R["A"]["sp"].kind.unique())} for v in "ABC"}
res["transitions"] = {v: dict(losses_per_match=len(R[v]["tl"]) / n, recoveries_per_match=len(R[v]["tr"]) / n) for v in "ABC"}
res["goals"] = {"score_total": int(sum(score[m] for m in pairs))}
for v in "ABC": res["goals"][v] = dict(total=int(sum(R[v]["goals"].get(m, 0) for m in pairs)), matches_equal_to_score=int(sum(R[v]["goals"].get(m, 0) == score[m] for m in pairs)))
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# printout
st = res["style"]; print(f"\n{'':22}{'A SB':>9}{'B SB-rec':>10}{'C Wyscout':>11}{'C/A':>7}")
for c in ("per_match", "buildup_share", "passes", "long", "dur", "shot"): print(f"{c:22}" + "".join(f"{st[v][c]:>{w}.3f}" for v, w in zip("ABC", (9, 10, 11))) + f"{st['C'][c] / st['A'][c]:>7.2f}")
for ph, f in res["families"].items():
    print(f"\n{ph} family shares (fitted on A):"); [print(f"  {fam}: " + "  ".join(f"{v} {f['shares'][v][fam]:.3f}" for v in "ABC")) for fam in f["shares"]["A"]]
    print(f"  largest difference from A: B {f['max_abs_diff']['B']:.3f}, C {f['max_abs_diff']['C']:.3f}")
print(f"\nper match A vs C: correlation of sequences {res['per_match_corr_A_C']['sequences']:.2f}, of passes per sequence {res['per_match_corr_A_C']['passes']:.2f}")
for kd in res["restarts"]["A"]: print(f"{kd:22}" + "  ".join(f"{v} n={res['restarts'][v][kd]['n']} short={res['restarts'][v][kd]['short'] if res['restarts'][v][kd]['short'] is None else round(res['restarts'][v][kd]['short'], 2)}" for v in "ABC"))
print("set pieces", res["setpieces"]); print("transitions", {v: {k_: round(x, 1) for k_, x in d.items()} for v, d in res["transitions"].items()}); print("goals", res["goals"]); print("->", OUT)
