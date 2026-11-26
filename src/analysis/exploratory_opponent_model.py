"""Proposal B: does a statement change with the style of the opponent? (exploratory, docs/protocol_opponent_model.md)

Teams are put in 3 style groups per league (k-means on season-so-far values, matches before the forecast date only):
  attacking style  S02, S03, R09, R12   -> used for the statements without the ball (D23-D28, T20-T22)
  defensive style  D23, D25, D26        -> used for the statements with the ball (the other 21)
Five forecasts of the same match, all with data before its date only:
  F  season so far (the grade's forecast)
  R  RQ2: F + n_Y/(n_Y+5) (A_Y - L) + V                      (forecast_opponent.py)
  G  mixed model y = mu + venue + g[group of the opponent] + team (random), refitted at each date
  M  mixed model y = mu + venue + team (random) + opponent (random)
  RF random forest on y - F, trained on the first half of the season
Compared on the second half of the season (from the league's middle date on).

Usage (from the repo root; data_dir = folder with data_info/ and ev/, work_dir = the grade extraction):
    python -X utf8 src/analysis/exploratory_opponent_model.py <data_dir> <work_dir> [--dev]
--dev: the 9 development teams, only to check the code (results/..._dev.json)."""

import sys, os, json, collections, time
import numpy as np, pandas as pd
from scipy.optimize import minimize
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E  # noqa: E402

sys.argv = ARGV
from forecast_opponent import home_of_statsbomb, SHARES  # noqa: E402

PROTOCOL = "docs/protocol_opponent_model.md"
SCRIPT = "src/analysis/exploratory_opponent_model.py"
OUT = os.path.join(E.REPO, "results", "exploratory_opponent_model.json")
K_RQ2 = 5
SEED = 2031
K_GROUPS = 3
STYLE = {"attack": ["S02", "S03", "R09", "R12"], "defence": ["D23", "D25", "D26"]}
WITHOUT_BALL = {"D23", "D24", "D25", "D26", "D27", "D28", "T20", "T21", "T22"}  # paired with the opponent's attacking groups
FEATURES = ["F", "L5", "nX", "oppA", "nY", "home", "Vd", "Lg", "gY"]  # + "z_<style statement>" of the opponent
RF_PARAMS = dict(n_estimators=500, min_samples_leaf=20, max_features=1 / 3, random_state=SEED, n_jobs=-1)
BETTER_SHARE, WORSE_SHARE = 0.20, 0.10


def side_of(c):
    return "attack" if c in WITHOUT_BALL else "defence"


# ---------------------------------------------------------------- mixed model (REML, Henderson's equations)
def fit_mixed(y, w, X, blocks, start=None):
    """y = X beta + sum_k Z_k u_k + e,  u_k ~ N(0, s2 lam_k I), e ~ N(0, s2 / w).
    blocks = list of (index array, number of levels). Profiled REML: -2l = (n - p) log Q + log|C*|."""
    n, p = X.shape
    Z = np.zeros((n, sum(nl for _, nl in blocks)))
    off, sizes = 0, []
    for ix, nl in blocks:
        Z[np.arange(n), off + ix] = 1
        off += nl
        sizes.append(nl)
    Xw, Zw = X * w[:, None], Z * w[:, None]
    XWX, XWZ, ZWZ = X.T @ Xw, X.T @ Zw, Z.T @ Zw
    XWy, ZWy, yWy = Xw.T @ y, Zw.T @ y, float(y @ (w * y))
    q = Z.shape[1]

    def solve(par):
        s = np.exp(np.concatenate([np.full(nl, pk / 2) for pk, nl in zip(par, sizes)]))  # Lambda^(1/2)
        C = np.block([[XWX, XWZ * s], [(XWZ * s).T, ZWZ * np.outer(s, s) + np.eye(q)]])
        rhs = np.r_[XWy, s * ZWy]
        L = np.linalg.cholesky(C + 1e-10 * np.eye(len(C)))
        th = np.linalg.solve(L.T, np.linalg.solve(L, rhs))
        Q = max(yWy - th @ rhs, 1e-300)
        return Q, 2 * np.log(np.diag(L)).sum(), th, s

    def obj(par):
        Q, logdet, _, _ = solve(par)
        return (n - p) * np.log(Q) + logdet

    x0 = np.array(start if start is not None else [np.log(0.1)] * len(blocks))
    r = minimize(obj, x0, method="L-BFGS-B", bounds=[(-25, 10)] * len(blocks))
    Q, _, th, s = solve(r.x)
    u = s * th[p:]
    s2 = Q / (n - p)
    us, off = [], 0
    for nl in sizes:
        us.append(u[off:off + nl])
        off += nl
    return {"beta": th[:p], "u": us, "s2": s2, "lam": np.exp(r.x), "par": r.x}


def effect_coding(g, k=K_GROUPS):
    # k groups -> k-1 columns that sum to zero over the groups
    X = np.zeros((len(g), k - 1))
    for j in range(k - 1):
        X[:, j] = (g == j).astype(float) - (g == k - 1).astype(float)
    return X


def group_effects(beta):
    b = list(beta)
    return np.array(b + [-sum(b)])


# ---------------------------------------------------------------- tables and groups
def league_table(TEAMS, lg, c, home):
    rows = []
    teams_of = collections.defaultdict(list)
    for R in TEAMS.values():
        if R["league"] == lg:
            for m in R["ids"]:
                teams_of[m].append(R["team"])
    for R in TEAMS.values():
        if R["league"] != lg:
            continue
        nu, de = E.arrays(R, c)
        for i, m in enumerate(R["ids"]):
            opp = [x for x in teams_of[m] if x != R["team"]]
            rows.append((R["team"], opp[0] if len(opp) == 1 else None, m, R["dates"][i], i, float(nu[i]), float(de[i]), home.get(m) == R["team"]))
    return pd.DataFrame(rows, columns=["team", "opp", "m", "date", "i", "num", "den", "home"])


class Styles:
    """Season-so-far style values of every team of a league and their k-means groups, cached by date."""

    def __init__(self, TEAMS, lg, home):
        self.names = sorted(R["team"] for R in TEAMS.values() if R["league"] == lg)
        self.tables = {s: {c: league_table(TEAMS, lg, c, home) for c in cs} for s, cs in STYLE.items()}
        self.cache = {}

    def profile(self, side, d=None):
        cols = {}
        for c, T in self.tables[side].items():
            T = T if d is None else T[T.date < d]
            g = T.groupby("team")[["num", "den"]].sum()
            v = (g.num / g.den).where(g.den > 0)
            cols[c] = v.reindex(self.names)
        P = pd.DataFrame(cols)
        Z = (P - P.mean()) / P.std(ddof=0).replace(0, np.nan)
        return P, Z.fillna(0.0)

    def groups(self, side, d=None):
        key = (side, d)
        if key not in self.cache:
            P, Z = self.profile(side, d)
            lab = KMeans(K_GROUPS, n_init=20, random_state=SEED).fit_predict(Z.values)
            self.cache[key] = (dict(zip(self.names, lab)), Z, P)
        return self.cache[key]


# ---------------------------------------------------------------- forecasts
def rows_for(TEAMS, subjects, home, c, styles, log):
    out = []
    side = side_of(c)
    by_league = collections.defaultdict(list)
    for s in subjects:
        by_league[TEAMS[s]["league"]].append(s)
    for lg, subs in by_league.items():
        T = league_table(TEAMS, lg, c, home)
        names = styles[lg].names
        idx = {t: j for j, t in enumerate(names)}
        mid = sorted(T.date.unique())[len(T.date.unique()) // 2]  # the league's middle date
        targets = T[T.team.isin(subs) & (T.i >= E.MIN_PAST) & (T.den > 0) & T.opp.notna()]
        parG = parM = None
        for d, todo in targets.groupby("date"):
            past = T[(T.date < d) & (T.den > 0) & T.opp.notna()]
            if past.den.sum() <= 0:
                continue
            lab, Zs, _ = styles[lg].groups(side, d)
            y, w = (past.num / past.den).values, past.den.values
            h = np.where(past.home, 0.5, -0.5)
            ti, oi = past.team.map(idx).values, past.opp.map(idx).values
            gp = past.opp.map(lab).values.astype(int)
            fitG = fit_mixed(y, w, np.column_stack([np.ones(len(y)), h, effect_coding(gp)]), [(ti, len(names))], parG)
            fitM = fit_mixed(y, w, np.column_stack([np.ones(len(y)), h]), [(ti, len(names)), (oi, len(names))], parM)
            parG, parM = fitG["par"], fitM["par"]
            gfx = group_effects(fitG["beta"][2:])
            L = past.num.sum() / past.den.sum()
            h_, a_ = past[past.home], past[~past.home]
            Vd = (h_.num.sum() / h_.den.sum() - a_.num.sum() / a_.den.sum()) / 2 if h_.den.sum() > 0 and a_.den.sum() > 0 else 0.0
            for r in todo.itertuples():
                mine = T[(T.team == r.team) & (T.date < d)].sort_values("date")
                if mine.den.sum() <= 0:
                    continue
                F = mine.num.sum() / mine.den.sum()
                l5 = mine.tail(5)
                L5 = l5.num.sum() / l5.den.sum() if l5.den.sum() > 0 else F
                others = past[past.team != r.team]
                B = others.num.sum() / others.den.sum()
                y_m = set(past[past.team == r.opp].m)
                vs_y = past[past.m.isin(y_m) & (past.team != r.opp)]
                nY = len(y_m)
                oppA = vs_y.num.sum() / vs_y.den.sum() - L if vs_y.den.sum() > 0 else 0.0
                hs = 1.0 if r.home else -1.0
                Rq = F + (nY / (nY + K_RQ2) * oppA if vs_y.den.sum() > 0 else 0.0) + hs * Vd
                gY = float(gfx[lab[r.opp]])
                G = fitG["beta"][0] + fitG["beta"][1] * hs / 2 + gY + fitG["u"][0][idx[r.team]]
                M = fitM["beta"][0] + fitM["beta"][1] * hs / 2 + fitM["u"][0][idx[r.team]] + fitM["u"][1][idx[r.opp]]
                lo, hi = (0.0, 1.0) if c in SHARES else (0.0, np.inf)
                Rq, G, M = (min(max(v, lo), hi) for v in (Rq, G, M))
                row = {"team": r.team, "claim": c, "league": lg, "date": d, "half": "second" if d >= mid else "first",
                       "w": r.den, "y": r.num / r.den, "B": B, "F": F, "R": Rq, "G": G, "M": M,
                       "L5": L5, "nX": len(mine), "oppA": oppA, "nY": nY, "home": hs, "Vd": Vd, "Lg": L, "gY": gY}
                row.update({f"z_{s}": float(Zs.loc[r.opp, s]) for s in STYLE[side]})
                out.append(row)
        log(f"  {c} {lg}: {sum(1 for o in out if o['league'] == lg)} forecasts")
    return pd.DataFrame(out)


# ---------------------------------------------------------------- whole season (Q4, descriptive)
def whole_season(TEAMS, home, c, styles):
    side = side_of(c)
    per, leagues = [], {}
    for lg in E.LEAGUES.values():
        T = league_table(TEAMS, lg, c, home)
        T = T[(T.den > 0) & T.opp.notna()]
        names = styles[lg].names
        idx = {t: j for j, t in enumerate(names)}
        lab, _, P = styles[lg].groups(side, None)
        g = T.opp.map(lab).values.astype(int)
        X = np.column_stack([np.ones(len(T)), np.where(T.home, 0.5, -0.5), effect_coding(g)])
        f = fit_mixed((T.num / T.den).values, T.den.values, X,
                      [(T.team.map(idx).values, len(names)), (T.opp.map(idx).values, len(names))])
        gfx = group_effects(f["beta"][2:])
        parts = {"team": f["lam"][0] * f["s2"], "style_group": float(np.var(gfx[g])),
                 "rest_of_opponent": f["lam"][1] * f["s2"], "venue": f["beta"][1] ** 2 / 4,
                 "chance": f["s2"] / np.median(T.den)}
        tot = sum(parts.values())
        sh = {k: v / tot for k, v in parts.items()}
        sh["style_part_of_opponent"] = parts["style_group"] / (parts["style_group"] + parts["rest_of_opponent"]) \
            if parts["style_group"] + parts["rest_of_opponent"] > 0 else 0.0
        per.append(sh)
        leagues[lg] = [{"group": j, "effect": float(gfx[j]),
                        "teams": sorted(t for t, v in lab.items() if v == j),
                        "style_means": {s: float(P.loc[[t for t, v in lab.items() if v == j], s].mean()) for s in STYLE[side]}}
                       for j in range(K_GROUPS)]
    return {k: float(np.median([p[k] for p in per])) for k in per[0]}, leagues


def silhouettes(styles):
    out = {}
    for lg, S in styles.items():
        for side in STYLE:
            _, Z = S.profile(side, None)
            out[f"{lg} {side}"] = {k: float(silhouette_score(Z.values, KMeans(k, n_init=20, random_state=SEED).fit_predict(Z.values)))
                                   for k in (2, 3, 4, 5)}
    return out


# ---------------------------------------------------------------- comparison
def compare(d, new, old):
    v, ci = E.ratio_ci(d, E.se(new), E.se(old), 2000, SEED, True)
    verdict = "better" if ci[0] > 0 else ("worse" if ci[1] < 0 else "no difference")
    return {"improvement": v, "ci": ci, "verdict": verdict}


def count(res, key, verdict):
    return sum(v[key]["verdict"] == verdict for v in res.values())


def main(data_dir, work, dev=False):
    out = OUT.replace(".json", "_dev.json") if dev else OUT
    if not dev:
        E.guard(OUT, [PROTOCOL, SCRIPT, "src/analysis/forecast_opponent.py", "src/analysis/evidence_grade.py"])
    elif os.path.exists(out):
        sys.exit(f"{out} already exists")
    TEAMS = E.load_teams(work)
    E.drop_missing(TEAMS, data_dir)
    subjects = [t for t in TEAMS if (t in E.DEV) == dev and t not in E.EXCLUDED]
    if len(TEAMS) != 80 or len(subjects) != (9 if dev else 70):
        sys.exit("expected 80 extracted teams and 70 subjects")
    home = home_of_statsbomb(E.REPO)
    t0 = time.time()
    log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)  # noqa: E731
    styles = {lg: Styles(TEAMS, lg, home) for lg in E.LEAGUES.values()}

    res = {}
    for c in E.SCALAR:
        fr = rows_for(TEAMS, subjects, home, c, styles, log)
        feats = FEATURES + [f"z_{s}" for s in STYLE[side_of(c)]]
        train, test = fr[fr.half == "first"], fr[fr.half == "second"].copy()
        rf = RandomForestRegressor(**RF_PARAMS).fit(train[feats], train.y - train.F, sample_weight=train.w)
        test["RF"] = test.F + rf.predict(test[feats])
        test["RF"] = test.RF.clip(0, 1) if c in SHARES else test.RF.clip(lower=0)
        shares, groups = whole_season(TEAMS, home, c, styles)
        r = {
            "statement": E.CLAIMS[c], "opponent_style": side_of(c),
            "forecasts_test": int(len(test)), "forecasts_train": int(len(train)),
            "G_vs_F": compare(test, "G", "F"),
            "G_vs_R": compare(test, "G", "R"),
            "G_vs_M": compare(test, "G", "M"),
            "RF_vs_G": compare(test, "RF", "G"),
            "R_vs_F": compare(test, "R", "F"),
            "M_vs_F": compare(test, "M", "F"),
            "skill_vs_league": {k: E.ratio_ci(test, E.se(k), E.se("B"), 2000, SEED, True)[0] for k in ("F", "R", "G", "M", "RF")},
            "shares": shares, "groups": groups,
        }
        if r["RF_vs_G"]["verdict"] == "better":
            pi = permutation_importance(rf, test[feats], test.y - test.F, sample_weight=test.w, n_repeats=10, random_state=SEED)
            r["rf_importance"] = dict(zip(feats, map(float, pi.importances_mean)))
        r["label"] = "changes with the opponent's style" if r["G_vs_F"]["verdict"] == "better" else "stable with respect to style"
        res[c] = r
        log(f"{c} {r['statement'][:36]:36} G-F {r['G_vs_F']['improvement']:+.3f} {r['G_vs_F']['verdict']:13} "
            f"G-R {r['G_vs_R']['improvement']:+.3f} {r['G_vs_R']['verdict']:13} RF-G {r['RF_vs_G']['improvement']:+.3f} "
            f"{r['RF_vs_G']['verdict']:13} group share {shares['style_group']:.3f}")

    n = len(res)
    wGR, wGM = count(res, "G_vs_R", "worse"), count(res, "G_vs_M", "worse")
    bRG, wRG = count(res, "RF_vs_G", "better"), count(res, "RF_vs_G", "worse")
    q2 = ("the groups can replace the single opponent" if wGR <= WORSE_SHARE * n and wGM <= WORSE_SHARE * n
          else "keep the single opponent: the group model is worse for too many statements")
    q3 = ("the random forest adds something over the group model" if bRG >= BETTER_SHARE * n and wRG <= WORSE_SHARE * n
          else "the random forest does not add enough: the readable group model is enough")
    summary = {
        "protocol": PROTOCOL, "exploratory": True, "development_run": dev,
        "n_teams": len(subjects), "n_statements": n, "k_groups": K_GROUPS, "style_statements": STYLE,
        "Q1_changes_with_style": [c for c, v in res.items() if v["G_vs_F"]["verdict"] == "better"],
        "Q1_stable": [c for c, v in res.items() if v["G_vs_F"]["verdict"] != "better"],
        "Q2_groups_vs_single_opponent": {"worse_than_R": wGR, "worse_than_M": wGM,
                                         "better_than_R": count(res, "G_vs_R", "better"), "better_than_M": count(res, "G_vs_M", "better"), "reading": q2},
        "Q3_forest_vs_groups": {"better": bRG, "worse": wRG, "reading": q3},
        "median_improvement": {k: float(np.median([v[k]["improvement"] for v in res.values()]))
                               for k in ("G_vs_F", "G_vs_R", "G_vs_M", "RF_vs_G", "R_vs_F", "M_vs_F")},
        "silhouette_whole_season": silhouettes(styles),
        "statements": res,
    }
    json.dump(summary, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    log(f"Q1: {len(summary['Q1_changes_with_style'])} of {n} change with style | Q2: {q2} | Q3: {q3} -> {out}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    main(*a, dev="--dev" in sys.argv)
