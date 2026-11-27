"""Proposal B on a second provider: the opponent style groups on Wyscout 2017/18 (exploratory, docs/protocol_opponent_model_wyscout.md)

Same method as exploratory_opponent_model.py (its functions are imported, nothing is re-implemented); only the data change:
  25 statements Wyscout can compute (no pressures, no xG), defensive style = D23 and D26 only, five leagues, 96 subjects.
At the end the labels are compared with the StatsBomb result (results/exploratory_opponent_model.json).

Usage (from the repo root; wy_work = the Wyscout grade extraction, wy_dir = the converted leagues):
    python -X utf8 src/analysis/exploratory_opponent_model_wyscout.py <wy_work> <wy_dir> [--dev]
--dev: Barcelona and Napoli only, to check the code (results/..._dev.json)."""

import sys, os, json, time
import numpy as np

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E  # noqa: E402
import evidence_grade_wyscout as W  # noqa: E402  (keeps only the statements Wyscout can compute, in E too)
import exploratory_opponent_model as OM  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402

sys.argv = ARGV
PROTOCOL = "docs/protocol_opponent_model_wyscout.md"
SCRIPT = "src/analysis/exploratory_opponent_model_wyscout.py"
OUT = os.path.join(E.REPO, "results", "exploratory_opponent_model_wyscout.json")
SB_RESULT = os.path.join(E.REPO, "results", "exploratory_opponent_model.json")

# forced differences (protocol, Method): no pressures -> defensive style without D25; five Wyscout leagues
OM.STYLE = {"attack": ["S02", "S03", "R09", "R12"], "defence": ["D23", "D26"]}
E.LEAGUES = {c: lg for c, lg in W.COUNTRIES.items()}
SAME_SHARE, PART_SHARE = 0.70, 0.50


def label(r):
    return "changes" if r["G_vs_F"]["verdict"] == "better" else "stable"


def main(work, wy_dir, dev=False):
    out = OUT.replace(".json", "_dev.json") if dev else OUT
    if not dev:
        E.guard(OUT, [PROTOCOL, SCRIPT, "src/analysis/exploratory_opponent_model.py", "src/analysis/forecast_opponent.py",
                      "src/analysis/evidence_grade.py", "src/analysis/evidence_grade_wyscout.py"])
    elif os.path.exists(out):
        sys.exit(f"{out} already exists")
    TEAMS = W.load_teams(work)
    subjects = [t for t in TEAMS if (t in W.DEV) == dev]
    if len(TEAMS) != 98 or len(subjects) != (2 if dev else 96):
        sys.exit("expected 98 extracted teams and 96 subjects")
    home = {}
    for country in W.COUNTRIES:
        for g in json.load(open(os.path.join(wy_dir, country, "matches", "generic.json"), encoding="utf-8")):
            home[g["match_id"]] = g["home_team"]["home_team_name"]
    claims = list(E.SCALAR)
    assert len(claims) == 25, claims
    t0 = time.time()
    log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)  # noqa: E731
    styles = {lg: OM.Styles(TEAMS, lg, home) for lg in E.LEAGUES.values()}

    res = {}
    for c in claims:
        fr = OM.rows_for(TEAMS, subjects, home, c, styles, log)
        feats = OM.FEATURES + [f"z_{s}" for s in OM.STYLE[OM.side_of(c)]]
        train, test = fr[fr.half == "first"], fr[fr.half == "second"].copy()
        rf = RandomForestRegressor(**OM.RF_PARAMS).fit(train[feats], train.y - train.F, sample_weight=train.w)
        test["RF"] = test.F + rf.predict(test[feats])
        test["RF"] = test.RF.clip(0, 1) if c in OM.SHARES else test.RF.clip(lower=0)
        shares, groups = OM.whole_season(TEAMS, home, c, styles)
        r = {
            "statement": E.CLAIMS[c], "opponent_style": OM.side_of(c),
            "forecasts_test": int(len(test)), "forecasts_train": int(len(train)),
            **{k: OM.compare(test, *k.split("_vs_")) for k in ("G_vs_F", "G_vs_R", "G_vs_M", "RF_vs_G", "R_vs_F", "M_vs_F")},
            "skill_vs_league": {k: E.ratio_ci(test, E.se(k), E.se("B"), 2000, OM.SEED, True)[0] for k in ("F", "R", "G", "M", "RF")},
            "shares": shares, "groups": groups,
        }
        if r["RF_vs_G"]["verdict"] == "better":
            pi = permutation_importance(rf, test[feats], test.y - test.F, sample_weight=test.w, n_repeats=10, random_state=OM.SEED)
            r["rf_importance"] = dict(zip(feats, map(float, pi.importances_mean)))
        r["label"] = "changes with the opponent's style" if label(r) == "changes" else "stable with respect to style"
        res[c] = r
        log(f"{c} {r['statement'][:36]:36} G-F {r['G_vs_F']['improvement']:+.3f} {r['G_vs_F']['verdict']:13} "
            f"G-R {r['G_vs_R']['improvement']:+.3f} {r['G_vs_R']['verdict']:13} RF-G {r['RF_vs_G']['improvement']:+.3f} "
            f"{r['RF_vs_G']['verdict']:13}")

    n = len(res)
    wGR, wGM = OM.count(res, "G_vs_R", "worse"), OM.count(res, "G_vs_M", "worse")
    bRG, wRG = OM.count(res, "RF_vs_G", "better"), OM.count(res, "RF_vs_G", "worse")
    q2_ok = wGR <= OM.WORSE_SHARE * n and wGM <= OM.WORSE_SHARE * n
    q3_ok = bRG >= OM.BETTER_SHARE * n and wRG <= OM.WORSE_SHARE * n
    q2 = "the groups can replace the single opponent" if q2_ok else "keep the single opponent: the group model is worse for too many statements"
    q3 = ("the random forest adds something over the group model" if q3_ok
          else "the random forest does not add enough: the readable group model is enough")

    # replication against StatsBomb (protocol, Reading)
    sb = json.load(open(SB_RESULT, encoding="utf-8"))
    both = [c for c in res if c in sb["statements"]]
    same = [c for c in both if label(res[c]) == label(sb["statements"][c])]
    share = len(same) / len(both)
    r1 = "replicates" if share >= SAME_SHARE else ("partly replicates" if share >= PART_SHARE else "does not replicate")
    replication = {
        "statements_compared": len(both), "same_label": len(same), "share": share, "wilson_95": W.wilson(len(same), len(both)),
        "R1_reading": r1,
        "changed": {c: {"statsbomb": label(sb["statements"][c]), "wyscout": label(res[c]),
                        "G_vs_F_statsbomb": sb["statements"][c]["G_vs_F"]["improvement"],
                        "G_vs_F_wyscout": res[c]["G_vs_F"]["improvement"]} for c in both if c not in same},
        "R2_Q2": {"statsbomb": sb["Q2_groups_vs_single_opponent"]["reading"], "wyscout": q2,
                  "reading": "same" if sb["Q2_groups_vs_single_opponent"]["reading"] == q2 else "different"},
        "R2_Q3": {"statsbomb": sb["Q3_forest_vs_groups"]["reading"], "wyscout": q3,
                  "reading": "same" if sb["Q3_forest_vs_groups"]["reading"] == q3 else "different"},
    }
    summary = {
        "protocol": PROTOCOL, "exploratory": True, "development_run": dev, "provider": "wyscout",
        "n_teams": len(subjects), "n_statements": n, "k_groups": OM.K_GROUPS, "style_statements": OM.STYLE,
        "Q1_changes_with_style": [c for c, v in res.items() if label(v) == "changes"],
        "Q1_stable": [c for c, v in res.items() if label(v) != "changes"],
        "Q2_groups_vs_single_opponent": {"worse_than_R": wGR, "worse_than_M": wGM, "better_than_R": OM.count(res, "G_vs_R", "better"),
                                         "better_than_M": OM.count(res, "G_vs_M", "better"), "reading": q2},
        "Q3_forest_vs_groups": {"better": bRG, "worse": wRG, "reading": q3},
        "median_improvement": {k: float(np.median([v[k]["improvement"] for v in res.values()]))
                               for k in ("G_vs_F", "G_vs_R", "G_vs_M", "RF_vs_G", "R_vs_F", "M_vs_F")},
        "silhouette_whole_season": OM.silhouettes(styles),
        "replication": replication,
        "statements": res,
    }
    json.dump(summary, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    log(f"Q1: {len(summary['Q1_changes_with_style'])} of {n} change | R1: {len(same)}/{len(both)} same label, {r1} | "
        f"Q2 {replication['R2_Q2']['reading']} | Q3 {replication['R2_Q3']['reading']} -> {out}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    main(*a, dev="--dev" in sys.argv)
