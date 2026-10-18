"""Pitch control (Spearman 2018, "Beyond Expected Goals", MIT Sloan; simplified as in L. Shaw's Friends-of-Tracking code) on the DFL open tracking data.
EXPLORATORY. Usage:  python pitch_control.py <dfl_dir> [out=results/exploratory_pitch_control.json]      (needs <dfl_dir>/npz from dfl_load.py)
Model (all parameters from the literature, fixed before the first run, never fitted to these matches):
- player velocity: central difference of positions over +/- 5 frames (0.4 s), speed capped at 12 m/s.
- time to intercept a target: reaction 0.7 s moving with the current velocity, then straight at 5 m/s; arrival is uncertain: P(arrived by T) =
  1 / (1 + exp(-pi / sqrt(3) / 0.45 * (T - tti))). Ball travels from its position to the target at 15 m/s.
- control: from the ball's arrival, each player gains control at rate 4.3 per s while arrived (goalkeepers 3 x 4.3, as in Shaw), times the share still uncontrolled;
  integrated in 0.04 s steps for at most 10 s or until less than 1% is uncontrolled. Pitch control of a team = sum over its players.
Analysis A, can the model tell completed from failed passes (the check Spearman used)?
- passes: DFL Play events (passes and crosses) from open play, kept when the passer is within 2 m of the ball at the synced frame (dfl_load.py) and the ball is in play.
- where the pass ended: first frame 0.3 to 5 s after the pass where a player other than the passer is within 1 m of the ball, or the ball goes out of play;
  the ball position there. Completed = DFL evaluation 'successfullyCompleted' or 'successful'. Passes with no such frame are dropped.
- predictors, all from the positions at the pass frame: (1) pitch control of the passing team at the end point; (2) nearest-player margin (distance of the
  nearest opponent minus distance of the nearest team-mate to the end point, the Voronoi idea); (3) minus the pass length.
- measure: AUC (chance that a completed pass scores higher than a failed one; 0.5 = no information). 95% bootstrap over matches (7 matches, 1000 resamples, seed 0)
  for each AUC and for the differences (1)-(2) and (1)-(3). Reading fixed in advance: pitch control 'adds' over a predictor if the interval of the difference is above 0.
Analysis B (descriptive): every 2 s of play (ball in play), on a 32 x 21 grid, the share of the opponent half that the team in possession controls (control > 0.5),
and the share of its own half the defending team controls; per team and match.
Data: Bassek et al. 2025, Scientific Data 12:195, CC BY 4.0. 7 matches of 2022/23 (5 with Fortuna Düsseldorf): not a sample of any league."""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REACT, VMAX, SIGMA, LAM, BALL_V, DT, TMAX = 0.7, 5.0, 0.45, 4.3, 15.0, 0.04, 10.0
K = np.pi / np.sqrt(3) / SIGMA


def velocities(xy):
    v = np.full_like(xy, np.nan); v[:, 5:-5] = (xy[:, 10:] - xy[:, :-10]) / 0.4
    s = np.linalg.norm(v, axis=2, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"): return np.where(s > 12, v / s * 12, v)


def control(pos, vel, team, gk, ball, targets):
    """pos, vel: (P, 2); team: (P,) 1 = attacking, 0 = defending; gk: (P,) bool; ball: (2,); targets: (G, 2). Returns attacking control (G,)."""
    ok = np.isfinite(pos).all(1) & np.isfinite(vel).all(1); pos, vel, team, gk = pos[ok], vel[ok], team[ok], gk[ok]
    r = pos + vel * REACT
    tti = REACT + np.linalg.norm(targets[None, :, :] - r[:, None, :], axis=2) / VMAX           # (P, G)
    t_ball = np.linalg.norm(targets - ball[None, :], axis=1) / BALL_V                          # (G,)
    lam = np.where(gk, 3 * LAM, LAM)[:, None]
    pc = np.zeros((len(pos), len(targets))); t = t_ball.copy()
    for _ in range(int(TMAX / DT)):
        left = 1 - pc.sum(0)
        if left.max() < 0.01: break
        p_arr = 1 / (1 + np.exp(-K * (t[None, :] - tti)))
        pc += np.maximum(left[None, :] * p_arr * lam * DT, 0); t += DT
    tot = pc.sum(0); att = pc[team == 1].sum(0)
    return np.where(tot > 0, att / np.maximum(tot, 1e-9), 0.5)


def auc(score, y):
    score, y = np.asarray(score), np.asarray(y); o = np.argsort(score, kind="mergesort"); r = np.empty(len(score)); r[o] = np.arange(1, len(score) + 1)
    _, inv, cnt = np.unique(score, return_inverse=True, return_counts=True); sums = np.bincount(inv, r); r = (sums / cnt)[inv]  # ties get the mean rank
    n1 = y.sum(); n0 = len(y) - n1; return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def oriented(a, meta, h, team_id):
    """Sign that makes team_id attack towards +x in half h."""
    d = meta["halves"][str(h)]["dir"]; return d if team_id == meta["home"] else -d


def load(path):
    a = np.load(path); meta = json.load(open(path[:-4] + "_events.json", encoding="utf-8")); return a, meta


def run(dfl):
    rows, desc = [], []
    for path in sorted(glob.glob(f"{dfl}/npz/*.npz")):
        a, meta = load(path); mid = meta["match"]; P = meta["players"]
        for h in (1, 2):
            xy = a[f"xy_{h}"].astype(float); vel = velocities(xy); ball = a[f"ball_{h}"].astype(float); alive = a[f"alive_{h}"]; poss = a[f"poss_{h}"]
            pids = list(a[f"pids_{h}"]); n0 = int(a[f"N0_{h}"]); F = xy.shape[1]
            tid = np.array([P[p]["team"] for p in pids]); gk = np.array([P[p]["pos"] == "TW" for p in pids])
            # Analysis A
            for e in meta["events"]:
                if e["kind"] != "pass" or e["half"] != h or not e["open_play"] or e.get("sync_dist", 99) > 2: continue
                f = e["frame"] - n0
                if not (5 <= f < F - 130) or alive[f] != 1 or e["player"] not in pids: continue
                i_p = pids.index(e["player"]); end = None
                for g in range(f + 8, f + 126):
                    if alive[g] != 1: end = g; break
                    d = np.linalg.norm(xy[:, g] - ball[g, :2], axis=1); d[i_p] = np.inf
                    if np.nanmin(d) <= 1.0: end = g; break
                if end is None or not np.isfinite(ball[end, :2]).all(): continue
                s = oriented(a, meta, h, e["team"]); att = (tid == e["team"]).astype(int)
                pos, v, b0, tgt = xy[:, f] * s, vel[:, f] * s, ball[f, :2] * s, ball[end, :2] * s
                pc = float(control(pos, v, att, gk, b0, tgt[None, :])[0])
                dist = np.linalg.norm(pos - tgt, axis=1); ok = np.isfinite(dist)
                mate = np.where(ok & (att == 1) & (np.arange(len(pids)) != i_p), dist, np.inf).min(); opp = np.where(ok & (att == 0), dist, np.inf).min()
                rows.append(dict(match=mid, completed=int(e["outcome"] in ("successfullyCompleted", "successful")), pc=pc, margin=float(opp - mate),
                                 length=float(np.linalg.norm(tgt - b0)), x_end=float(tgt[0])))
            # Analysis B
            gx, gy = np.meshgrid(np.linspace(-52.5 + 105 / 64, 52.5 - 105 / 64, 32), np.linspace(-34 + 68 / 42, 34 - 68 / 42, 21), indexing="ij"); G = np.c_[gx.ravel(), gy.ravel()]
            for f in range(5, F - 5, 50):
                if alive[f] != 1 or poss[f] not in (1, 2) or not np.isfinite(ball[f, :2]).all(): continue
                team_on = meta["home"] if poss[f] == 1 else meta["guest"]; s = oriented(a, meta, h, team_on); att = (tid == team_on).astype(int)
                c = control(xy[:, f] * s, vel[:, f] * s, att, gk, ball[f, :2] * s, G)
                desc.append(dict(match=mid, team=team_on, opp_half=float((c[G[:, 0] > 0] > 0.5).mean()), def_own_half=float((c[G[:, 0] < 0] < 0.5).mean())))
        print(mid, len(rows), "passes so far,", len(desc), "frames")
    return rows, desc


def boot_auc(rows, keys, B=1000, seed=0):
    ms = sorted({r["match"] for r in rows}); by = {m: [r for r in rows if r["match"] == m] for m in ms}; rng = np.random.default_rng(seed); out = {k: [] for k in keys}
    for _ in range(B):
        rr = [r for m in rng.choice(ms, len(ms)) for r in by[m]]; y = np.array([r["completed"] for r in rr])
        for k, f in keys.items(): out[k].append(f(rr, y))
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in out.items()}


if __name__ == "__main__":
    dfl = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "exploratory_pitch_control.json")
    if os.path.exists(out): sys.exit(f"{out} exists: exploratory result already produced, not rerun (delete it only if the code had a bug, and say so).")
    rows, desc = run(dfl); y = np.array([r["completed"] for r in rows])
    S = {"pc": lambda rr, y: auc([r["pc"] for r in rr], y), "margin": lambda rr, y: auc([r["margin"] for r in rr], y), "length": lambda rr, y: auc([-r["length"] for r in rr], y)}
    D = {"pc_minus_margin": lambda rr, y: S["pc"](rr, y) - S["margin"](rr, y), "pc_minus_length": lambda rr, y: S["pc"](rr, y) - S["length"](rr, y)}
    point = {k: f(rows, y) for k, f in {**S, **D}.items()}; ci = boot_auc(rows, {**S, **D})
    teams = {}
    for path in glob.glob(f"{dfl}/npz/*_events.json"):
        m = json.load(open(path, encoding="utf-8")); teams[m["home"]] = m["home_name"]; teams[m["guest"]] = m["guest_name"]
    per = {}
    for d in desc:
        k = (d["match"], d["team"]); per.setdefault(k, []).append(d)
    B = [dict(match=m, team=teams[t], frames=len(v), opp_half_controlled=float(np.mean([x["opp_half"] for x in v])),
              own_half_controlled_when_defending=float(np.mean([x["def_own_half"] for x in desc if x["match"] == m and x["team"] != t]))) for (m, t), v in sorted(per.items())]
    res = {"status": "exploratory", "data": "DFL open tracking + events, Bassek et al. 2025 (CC BY 4.0), 7 matches 2022/23",
           "params": dict(reaction_s=REACT, max_speed=VMAX, sigma=SIGMA, lambda_=LAM, ball_speed=BALL_V, dt=DT),
           "A_pass_check": dict(passes=len(rows), completed_share=float(y.mean()), auc={k: dict(value=point[k], ci=ci[k]) for k in point},
                                pc_adds_over_margin=bool(ci["pc_minus_margin"][0] > 0), pc_adds_over_length=bool(ci["pc_minus_length"][0] > 0),
                                brier_pc=float(np.mean((np.array([r["pc"] for r in rows]) - y) ** 2)), brier_base_rate=float(np.mean((y.mean() - y) ** 2))),
           "B_space": B}
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False); print(json.dumps(res["A_pass_check"], indent=1))
