"""After how many matches can each statement be trusted? (exploratory, proposal A)

The grade's D is the reliability of a season mean. From it we get n* = noise of one match / spread of styles,
and from n* the number of matches needed for a reliability R:  n(R) = n* R / (1 - R).
Then a check: D computed on the first n matches of each team (n = 3, 5, 8, 12, 20) against what the formula says.
Also: skill predicted from D (off-curve statements, descriptive) and a fixed text that explains each grade.
Protocol: docs/protocol_trust_n.md. Nothing here changes the grade.

Usage (from the repo root, work_dir = folder of evidence_grade.py extract):
    python -X utf8 src/analysis/exploratory_trust_n.py <work_dir> --set dev
    python -X utf8 src/analysis/exploratory_trust_n.py <work_dir> --set confirm --corrected <data_dir>"""

import sys, os, json
import numpy as np

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E

sys.argv = ARGV
REPO = E.REPO
PROTOCOL = "docs/protocol_trust_n.md"
SCRIPT = "src/analysis/exploratory_trust_n.py"

STATEMENTS = list(E.SCALAR)  # the 30 statements with one number per match (K33, K34 not included: protocol)
GRID = [3, 5, 8, 12, 20]  # first n matches of each team
READ_N = [5, 8, 12, 20]  # n = 3 is reported but does not enter the reading
LEVELS = {"starts": 0.50, "reliable": 0.75}  # primary
LEVELS_SENS = [0.60, 0.80]  # sensitivity, secondary
GAP_OK = 0.10  # formula holds if median |gap| <= this at every n of READ_N
GAP_SENS = [0.05, 0.15]
GAP_FLAG = 0.20  # statement flagged if |gap| at 12 matches is above this
SEED = 7  # as the grade's discrimination


def n_star_from_D(D, N):
    # D = R + (1 - R) / N  ->  R = (N D - 1) / (N - 1);  n* = N (1 - R) / R
    R = (N * D - 1) / (N - 1)
    if R <= 0:
        return R, None
    return R, N * (1 - R) / R


def needed(n_star, R):
    return None if n_star is None else n_star * R / (1 - R)


def d_pred(n, n_star):
    # what D on n matches should be if the formula is right
    R = n / (n + n_star)
    return R + (1 - R) / n


def d_first_n(TEAMS, subjects, c, n):
    # D of the grade, unchanged, on the first n matches (by date) of every team
    short = {name: {**TEAMS[name], "V": TEAMS[name]["V"][:n]} for name in subjects}
    return E.discrimination(short, subjects, c, np.random.default_rng(SEED))[0]


def first_n_reaching(R_obs, R):
    # fallback of the protocol: smallest n of the grid where the observed reliability reaches R
    for n in GRID:
        if R_obs[str(n)] is not None and R_obs[str(n)] >= R:
            return n
    return None


def skill_from_D(n_star, N):
    # pooled skill of the season-so-far forecast, forecasts from k = 5 past matches to N - 1
    H = np.mean([1 / k for k in range(E.MIN_PAST, int(round(N)))])
    return (1 - n_star * H) / (1 + n_star)


def text(v, r):
    # fixed rules, no language model; {seen} is filled in by the app with the matches the analyst has seen
    D = v["D"]
    lo = v["skill_ci"][0]
    if D >= 0.7:
        parts = ["teams differ a lot in this number"]
    elif D >= 0.5:
        parts = ["teams differ somewhat in this number"]
    else:
        parts = ["teams differ little in this number: it is mostly chance"]
    if lo >= 0.10:
        parts.append("the season so far predicts the next match much better than the league average")
    elif lo > 0:
        parts.append("the season so far predicts the next match a little better than the league average")
    else:
        parts.append("the season so far does not predict the next match better than the league average")
    a, b = r.get("matches_starts"), r.get("matches_reliable")
    never = "within a season" if r.get("source") == "formula" else "within 20 matches"
    if a is None:
        parts.append(f"it does not become reliable {never}")
    elif b is None:
        parts.append(f"starts to say something after about {a} matches, not reliable {never}; you have seen {{seen}}")
    elif a == b:
        parts.append(f"reliable after about {b} matches; you have seen {{seen}}")
    else:
        parts.append(f"starts to say something after about {a} matches, reliable after about {b}; you have seen {{seen}}")
    if r.get("flag_uncertain"):
        parts.append("this estimate is uncertain on the first matches of a season")
    if r.get("curve") == "below":
        parts.append("it predicts worse than its spread suggests: it may change during the season")
    return "; ".join(parts)


def rounded(x, N):
    # matches as a whole number; None if not within one season
    if x is None or x > N:
        return None
    return max(1, int(round(x)))


def analyse(TEAMS, subjects, grade):
    out = {}
    gaps = {str(n): [] for n in GRID}
    for c in STATEMENTS:
        v = grade["statements"][c]
        N = v["forecasts"] / v["teams"] + E.MIN_PAST
        R_N, ns = n_star_from_D(v["D"], N)
        r = {"statement": v["statement"], "grade": v["grade"], "D": v["D"], "N": N, "R_N": R_N, "n_star": ns}
        D_obs = {str(n): d_first_n(TEAMS, subjects, c, n) for n in GRID}
        r["D_first_n"] = D_obs
        r["R_first_n"] = {k: ((int(k) * d - 1) / (int(k) - 1) if np.isfinite(d) else None) for k, d in D_obs.items()}
        if ns is not None:
            r["D_pred_first_n"] = {str(n): d_pred(n, ns) for n in GRID}
            r["gap"] = {str(n): D_obs[str(n)] - d_pred(n, ns) for n in GRID}
            for n in GRID:
                if np.isfinite(r["gap"][str(n)]):
                    gaps[str(n)].append(abs(r["gap"][str(n)]))
            r["flag_uncertain"] = bool(abs(r["gap"]["12"]) > GAP_FLAG)
            r["skill_pred"] = skill_from_D(ns, N)
            lo, hi = v["skill_ci"]
            r["skill"], r["skill_ci"] = v["skill"], v["skill_ci"]
            r["curve"] = "below" if hi < r["skill_pred"] else "above" if lo > r["skill_pred"] else "on"
            r["last5_vs_season"] = v.get("last5_vs_season")
        for name, R in list(LEVELS.items()) + [(f"sens_{R}", R) for R in LEVELS_SENS]:
            r[f"matches_{name}_exact"] = needed(ns, R)
            r[f"matches_{name}_observed"] = first_n_reaching(r["R_first_n"], R)
        out[c] = r

    median_gap = {n: (float(np.median(g)) if g else None) for n, g in gaps.items()}
    reading = {str(t): all(median_gap[str(n)] is not None and median_gap[str(n)] <= t for n in READ_N) for t in [GAP_OK] + GAP_SENS}
    holds = reading[str(GAP_OK)]

    # numbers shown in the app: formula if it holds, otherwise the observed curve (protocol, measure 3)
    for c, r in out.items():
        for name in LEVELS:
            if holds:
                r[f"matches_{name}"] = rounded(r[f"matches_{name}_exact"], r["N"])
            else:
                r[f"matches_{name}"] = r[f"matches_{name}_observed"]
        r["source"] = "formula" if holds else "observed first-n curve"
        r["text"] = text(grade["statements"][c], r)
        print(
            f"{c} {r['statement'][:44]:44} {r['grade']}  D {r['D']:.2f}  n* {r['n_star'] if r['n_star'] is None else round(r['n_star'], 1)!s:>5}  "
            f"0.50: {r['matches_starts']!s:>4}  0.75: {r['matches_reliable']!s:>4}  gap12 {r.get('gap', {}).get('12', float('nan')):+.2f}  curve {r.get('curve', '-')}",
            flush=True,
        )
    return {
        "protocol": PROTOCOL,
        "exploratory": True,
        "levels": LEVELS,
        "levels_sensitivity": LEVELS_SENS,
        "grid_first_n": GRID,
        "median_abs_gap": median_gap,
        "formula_holds": holds,
        "formula_holds_sensitivity": reading,
        "statements": out,
        "note": "Exploratory. Numbers of matches per type of statement, not per team. The grade is unchanged.",
    }


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else ""
    if not a or which not in ("dev", "confirm"):
        sys.exit(__doc__)
    work = a[0]
    TEAMS = E.load_teams(work)
    if which == "dev":
        subjects = [t for t in TEAMS if t in E.DEV]
        grade = json.load(open(os.path.join(REPO, "results", "evidence_grade_dev.json"), encoding="utf-8"))
        out = os.path.join(REPO, "results", "exploratory_trust_n_dev.json")
    else:
        if "--corrected" not in sys.argv:
            sys.exit("--corrected <data_dir> is needed for the confirmatory set (grade protocol, note 1)")
        out = os.path.join(REPO, "results", "exploratory_trust_n.json")
        E.guard(out, [PROTOCOL, SCRIPT])
        dropped = E.drop_missing(TEAMS, sys.argv[sys.argv.index("--corrected") + 1])
        print("dropped team-matches (team name not in the events):", {t: len(v) for t, v in dropped.items()})
        subjects = [t for t in TEAMS if t not in E.DEV + E.EXCLUDED]
        grade = json.load(open(os.path.join(REPO, "results", "evidence_grade_corrected.json"), encoding="utf-8"))
    if sorted(subjects) != sorted(grade["teams"]):
        sys.exit(f"the teams differ from the grade's ({len(subjects)} vs {len(grade['teams'])})")
    res = analyse(TEAMS, subjects, grade)
    res["set"] = which
    res["n_teams"] = len(subjects)
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("median |gap| by n:", {k: (None if g is None else round(g, 3)) for k, g in res["median_abs_gap"].items()}, "| formula holds:", res["formula_holds"], "->", out)
