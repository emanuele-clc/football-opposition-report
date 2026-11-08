"""RQ2: if the forecast knows the opponent and home/away, is it better than the season average?

The grade uses the team's season so far (F). Here F is moved a bit depending on what the opponent usually allows:
  F_adj = F + w_Y (A_Y - L) [+ V]
A_Y = what Y's opponents did against Y, L = league value, w_Y = less weight if Y played few matches, V = home advantage.
Then I check if F_adj has a smaller error than F. Protocol: docs/protocol_opponent_forecast.md.

Usage:
    python -X utf8 src/analysis/forecast_opponent.py dev <sb_work_dir> <sb_data_dir>
    python -X utf8 src/analysis/forecast_opponent.py confirm statsbomb <sb_work_dir> <sb_data_dir>
    python -X utf8 src/analysis/forecast_opponent.py confirm wyscout <wy_work_dir> <wy_dir>"""

import sys, os, json, collections
import numpy as np, pandas as pd

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E

sys.argv = ARGV
REPO = E.REPO
SCALAR = list(E.SCALAR)
SHARES = {"S03", "S04", "S05", "R09", "R10", "R11", "R12", "R13", "P15", "P16", "P17", "T19", "T20", "T21", "T22", "A32"}
K_GRID = [1, 3, 5, 10, 20]
K, VENUE = 5, True  # chosen in the development step
PROTOCOL = "docs/protocol_opponent_forecast.md"


def home_of_statsbomb(repo):
    home = {}
    for key in E.LEAGUES:
        for g in json.load(open(os.path.join(repo, "data_info", f"{key}.json"), encoding="utf-8")):
            home[g["match_id"]] = g["home_team"]["home_team_name"]
    return home


def rows(TEAMS, subjects, home, claims, k, venue):
    # per league: the teams, and the two teams of every match
    league_teams = collections.defaultdict(list)
    for R in TEAMS.values():
        league_teams[R["league"]].append(R)
    teams_of = {}
    for lg, Rs in league_teams.items():
        teams_of[lg] = collections.defaultdict(list)
        for R in Rs:
            for m in R["ids"]:
                teams_of[lg][m].append(R["team"])

    out = []
    for name in subjects:
        R = TEAMS[name]
        lg = R["league"]
        dates = np.array(R["dates"])
        for c in claims:
            # every team-match of the league for this statement
            table = []
            for U in league_teams[lg]:
                nu, de = E.arrays(U, c)
                for i, m in enumerate(U["ids"]):
                    table.append((U["team"], m, U["dates"][i], nu[i], de[i], home.get(m) == U["team"]))
            T = pd.DataFrame(table, columns=["team", "m", "date", "num", "den", "home"])
            nums, dens = E.arrays(R, c)

            for t in range(E.MIN_PAST, len(dates)):
                d = dates[t]
                m = R["ids"][t]
                if dens[:t].sum() <= 0 or dens[t] <= 0:
                    continue
                opp = [x for x in teams_of[lg][m] if x != name]
                if len(opp) != 1:
                    continue
                Y = opp[0]
                past = T[T.date < d]
                others = past[past.team != name]
                if others.den.sum() <= 0:
                    continue
                F = nums[:t].sum() / dens[:t].sum()
                B = others.num.sum() / others.den.sum()  # league average without X (the grade's baseline)
                L = past.num.sum() / past.den.sum()

                # opponent effect: what teams did against Y, compared with the league
                y_matches = set(past[past.team == Y].m)
                against_y = past[past.m.isin(y_matches) & (past.team != Y)]
                nY = len(y_matches)
                Fa = F
                if against_y.den.sum() > 0:
                    Fa += nY / (nY + k) * (against_y.num.sum() / against_y.den.sum() - L)
                # venue effect
                if venue:
                    h = past[past.home]
                    a = past[~past.home]
                    if h.den.sum() > 0 and a.den.sum() > 0:
                        V = (h.num.sum() / h.den.sum() - a.num.sum() / a.den.sum()) / 2
                        if home.get(m) == name:
                            Fa += V
                        else:
                            Fa -= V
                if c in SHARES:
                    Fa = min(max(Fa, 0.0), 1.0)
                else:
                    Fa = max(Fa, 0.0)
                out.append({"team": name, "claim": c, "w": float(dens[t]), "y": float(nums[t] / dens[t]), "F": F, "Fa": Fa, "B": B})
    return pd.DataFrame(out)


def summary(fr):
    res = {}
    for c, d in fr.groupby("claim", sort=False):
        imp, ci = E.ratio_ci(d, E.se("Fa"), E.se("F"), 2000, 2029, True)
        res[c] = {
            "statement": E.CLAIMS[c],
            "forecasts": int(len(d)),
            "improvement": imp,
            "improvement_ci": ci,
            "skill_season": E.ratio_ci(d, E.se("F"), E.se("B"), 2000, 2029, True)[0],
            "skill_adjusted": E.ratio_ci(d, E.se("Fa"), E.se("B"), 2000, 2029, True)[0],
        }
    return res


def regrade(s, grades):
    # grade again with the adjusted forecast (same thresholds); discrimination does not change
    out = {}
    for c, v in s.items():
        g = grades[c]
        lo = v["skill_adjusted_ci"][0]
        if lo >= 0.10:
            fc = "strong"
        elif lo > 0:
            fc = "weak"
        else:
            fc = "none"
        out[c] = {"before": g["grade"], "after": E.grade(fc, g["discrimination"]), "forecast": [g["forecast"], fc], "discrimination": g["discrimination"]}
    return out


def confirm(provider, TEAMS, subjects, home, claims, grades, out):
    fr = rows(TEAMS, subjects, home, claims, K, VENUE)
    s = summary(fr)
    for c, d in fr.groupby("claim", sort=False):
        s[c]["skill_adjusted_ci"] = E.ratio_ci(d, E.se("Fa"), E.se("B"), 2000, 2029, True)[1]
        lo, hi = s[c]["improvement_ci"]
        if lo > 0:
            s[c]["verdict"] = "adjusted better"
        elif hi < 0:
            s[c]["verdict"] = "adjusted worse"
        else:
            s[c]["verdict"] = "no difference"
    n = len(s)
    better = sum(v["verdict"] == "adjusted better" for v in s.values())
    worse = sum(v["verdict"] == "adjusted worse" for v in s.values())
    # reading fixed in the protocol
    if better >= 0.5 * n and worse <= 0.1 * n:
        answer = "helps"
    elif better >= 0.2 * n:
        answer = "helps for some statements"
    else:
        answer = "does not help"
    rg = regrade(s, grades)
    res = {
        "protocol": PROTOCOL,
        "provider": provider,
        "k": K,
        "venue": VENUE,
        "n_teams": len(subjects),
        "n_statements": n,
        "adjusted_better": better,
        "adjusted_worse": worse,
        "answer": answer,
        "median_improvement": float(np.median([v["improvement"] for v in s.values()])),
        "grades_changed": {c: v for c, v in rg.items() if v["before"] != v["after"]},
        "grades_after": dict(collections.Counter(v["after"] for v in rg.values())),
        "statements": s,
        "regrade": rg,
    }
    for c, v in s.items():
        ci = v["improvement_ci"]
        print(f"{c} {v['statement'][:44]:44} improvement {v['improvement']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] {v['verdict']:15} grade {rg[c]['before']} -> {rg[c]['after']}")
    print(f"{provider}: better {better}, worse {worse} of {n} -> {answer}; grades changed {list(res['grades_changed'])}")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("->", out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]

    if len(a) == 4 and a[0] == "confirm" and a[1] in ("statsbomb", "wyscout"):
        provider = a[1]
        out = os.path.join(REPO, "results", f"opponent_forecast_{provider}.json")
        E.guard(out, [PROTOCOL, "src/analysis/forecast_opponent.py", "src/analysis/evidence_grade.py", "src/analysis/evidence_grade_wyscout.py"])
        if provider == "statsbomb":  # <sb_work_dir> <events data dir>
            TEAMS = E.load_teams(a[2])
            E.drop_missing(TEAMS, a[3])
            subjects = [t for t in TEAMS if t not in E.DEV + E.EXCLUDED]
            assert len(subjects) == 70 and len(TEAMS) == 80
            home = home_of_statsbomb(REPO)
            claims = SCALAR
            grades_file = "evidence_grade_corrected.json"
        else:  # <wy_work_dir> <wy_dir>
            import evidence_grade_wyscout as W  # this also keeps only the statements Wyscout supports

            TEAMS = W.load_teams(a[2])
            subjects = [t for t in TEAMS if t not in W.DEV]
            assert len(subjects) == 96 and len(TEAMS) == 98
            home = {}
            for country in W.COUNTRIES:
                for g in json.load(open(os.path.join(a[3], country, "matches", "generic.json"), encoding="utf-8")):
                    home[g["match_id"]] = g["home_team"]["home_team_name"]
            claims = list(E.SCALAR)
            grades_file = "evidence_grade_wyscout.json"
        grades = json.load(open(os.path.join(REPO, "results", grades_file), encoding="utf-8"))["statements"]
        confirm(provider, TEAMS, subjects, home, claims, grades, out)
        sys.exit(0)

    if len(a) != 3 or a[0] != "dev":
        sys.exit(__doc__)
    # development step (exploratory): only the 9 development teams, try every k with and without venue
    TEAMS = E.load_teams(a[1])
    E.drop_missing(TEAMS, a[2])
    home = home_of_statsbomb(REPO)
    subjects = [t for t in TEAMS if t in E.DEV]
    out = {"note": "EXPLORATORY development step for RQ2 on the 9 StatsBomb development teams; chooses k and the venue term. Not a test.", "grid": {}}
    for venue in (False, True):
        for k in K_GRID:
            s = summary(rows(TEAMS, subjects, home, SCALAR, k, venue))
            pooled = float(np.median([v["improvement"] for v in s.values()]))  # units differ between statements: median
            key = f"k={k}, venue={'yes' if venue else 'no'}"
            out["grid"][key] = {"pooled_improvement": pooled, "statements": s}
            better = sum(v["improvement_ci"][0] > 0 for v in s.values())
            worse = sum(v["improvement_ci"][1] < 0 for v in s.values())
            print(f"{key:20} pooled {pooled:+.4f} | clearly better {better}, clearly worse {worse} of {len(s)}", flush=True)
    fn = os.path.join(REPO, "results", "exploratory_opponent_forecast_dev.json")
    json.dump(out, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("->", fn)
