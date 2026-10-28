"""RQ2: does a next-match forecast that knows the opponent and the venue beat the team's season average?
Development step (exploratory): only the 9 StatsBomb development teams of the evidence grade are forecast; the other teams enter as opponents and
league baseline, exactly as in the grade. Reads the per-match values already extracted by evidence_grade.py (StatsBomb) and
evidence_grade_wyscout.py (Wyscout).
Confirmatory step (protocol docs/protocol_opponent_forecast.md): k = 5 and the venue term, run once per provider on teams not used in development.
Usage:
    python -X utf8 src/week4/forecast_opponent.py dev <sb_work_dir> <sb_data_dir>              # -> results/exploratory_opponent_forecast_dev.json
    python -X utf8 src/week4/forecast_opponent.py confirm statsbomb <sb_work_dir> <sb_data_dir>  # 70 teams -> results/opponent_forecast_statsbomb.json
    python -X utf8 src/week4/forecast_opponent.py confirm wyscout <wy_work_dir> <wy_dir>         # 96 teams -> results/opponent_forecast_wyscout.json
Definitions (fixed before the first run; k and the venue term are what the development step chooses):
- statements: the scalar statements of the grade (families and main players excluded: there the opponent has no clear meaning).
- for team X, match t (from the 6th, as in the grade), date d, opponent Y:
  F    = X's season so far (sum of numerators / sum of denominators of X's matches before t), the grade's forecast;
  L    = league value before d: all team-matches of the league before d (ratio of sums);
  A_Y  = what Y's opponents did against Y before d: their numerators / denominators in Y's matches before d;
  w_Y  = n_Y / (n_Y + k), n_Y = Y's matches before d (shrinks the opponent effect when Y has played little);
  V    = (H - A) / 2, H and A = league value of home and away team-matches before d; + V if X is at home, - V away;
  F_adj = F + w_Y (A_Y - L) [+ V]; shares are kept in [0, 1], other values at >= 0.
- measure: improvement = 1 - sum w (y - F_adj)^2 / sum w (y - F)^2, w = denominator of match t (as the grade's skill); 95% interval by bootstrap
  over teams (2000, seed 2029). Also the grade's skill against the league average B for F and for F_adj."""

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


def home_of_statsbomb(repo):
    H = {}
    for key in E.LEAGUES:
        for g in json.load(open(os.path.join(repo, "data_info", f"{key}.json"), encoding="utf-8")):
            H[g["match_id"]] = g["home_team"]["home_team_name"]
    return H


def index(TEAMS):
    """Per league: for every statement, every team-match as (team, match id, date, num, den); and the two teams of every match."""
    by = collections.defaultdict(list)
    for R in TEAMS.values():
        by[R["league"]].append(R)
    out = {}
    for lg, Rs in by.items():
        teams_of = collections.defaultdict(list)
        for R in Rs:
            for m in R["ids"]:
                teams_of[m].append(R["team"])
        out[lg] = dict(teams=Rs, teams_of=teams_of)
    return out


def rows(TEAMS, subjects, home, claims, k, venue):
    IX = index(TEAMS)
    out = []
    for name in subjects:
        R = TEAMS[name]
        lg = IX[R["league"]]
        dates = np.array(R["dates"])
        for c in claims:
            # league table of team-matches for this statement
            tm = []
            for U in lg["teams"]:
                nu, de = E.arrays(U, c)
                for i, m in enumerate(U["ids"]):
                    tm.append((U["team"], m, U["dates"][i], nu[i], de[i], home.get(m) == U["team"]))
            T = pd.DataFrame(tm, columns=["team", "m", "date", "num", "den", "home"])
            nums, dens = E.arrays(R, c)
            for t in range(E.MIN_PAST, len(dates)):
                d, m = dates[t], R["ids"][t]
                if dens[:t].sum() <= 0 or dens[t] <= 0:
                    continue
                opp = [x for x in lg["teams_of"][m] if x != name]
                if len(opp) != 1:
                    continue
                Y = opp[0]
                past = T[T.date < d]
                oth = past[past.team != name]
                if oth.den.sum() <= 0:
                    continue
                F = nums[:t].sum() / dens[:t].sum()
                B = oth.num.sum() / oth.den.sum()
                L = past.num.sum() / past.den.sum()
                ym = set(past[past.team == Y].m)  # Y's matches before d
                ag = past[past.m.isin(ym) & (past.team != Y)]
                nY = len(ym)
                Fa = F
                if ag.den.sum() > 0:
                    Fa += nY / (nY + k) * (ag.num.sum() / ag.den.sum() - L)
                if venue:
                    h, a = past[past.home], past[~past.home]
                    if h.den.sum() > 0 and a.den.sum() > 0:
                        V = (h.num.sum() / h.den.sum() - a.num.sum() / a.den.sum()) / 2
                        Fa += V if home.get(m) == name else -V
                Fa = min(max(Fa, 0.0), 1.0) if c in SHARES else max(Fa, 0.0)
                out.append(dict(team=name, claim=c, w=float(dens[t]), y=float(nums[t] / dens[t]), F=F, Fa=Fa, B=B))
    return pd.DataFrame(out)


def improvement(d, seed=2029, B=2000):
    return E.ratio_ci(d, E.se("Fa"), E.se("F"), B, seed, True)


def summary(fr):
    res = {}
    for c, d in fr.groupby("claim", sort=False):
        imp, ci = improvement(d)
        res[c] = dict(
            statement=E.CLAIMS[c],
            forecasts=int(len(d)),
            improvement=imp,
            improvement_ci=ci,
            skill_season=E.ratio_ci(d, E.se("F"), E.se("B"), 2000, 2029, True)[0],
            skill_adjusted=E.ratio_ci(d, E.se("Fa"), E.se("B"), 2000, 2029, True)[0],
        )
    return res


K, VENUE = 5, True  # chosen in the development step (protocol_opponent_forecast.md)
PROTOCOL = "docs/protocol_opponent_forecast.md"


def guard(out):
    import subprocess

    files = [PROTOCOL, "src/week4/forecast_opponent.py", "src/week4/evidence_grade.py", "src/week4/evidence_grade_wyscout.py"]
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)
    if os.path.exists(out):
        sys.exit(f"{out} already exists: the run is done once.")
    if git("ls-files", "--error-unmatch", *files).returncode:
        sys.exit("Commit the protocol and the scripts first.")
    if git("diff", "--quiet", "HEAD", "--", *files).returncode:
        sys.exit("The protocol or the scripts differ from the last commit: commit them first.")
    c = git("log", "-1", "--format=%H", "--", files[0]).stdout.strip()
    if git("merge-base", "--is-ancestor", c, "origin/main").returncode:
        sys.exit("The protocol commit is not on origin/main: push it first.")


def regrade(s, grades):
    """Grade with the adjusted forecast: forecast verdict from the skill of F_adj against the league average (same thresholds), discrimination
    unchanged (it does not depend on the forecast). Families and main players keep their grade."""
    out = {}
    for c, v in s.items():
        g = grades[c]
        fc = "strong" if v["skill_adjusted_ci"][0] >= 0.10 else ("weak" if v["skill_adjusted_ci"][0] > 0 else "none")
        new = E.grade(fc, g["discrimination"])
        out[c] = dict(before=g["grade"], after=new, forecast=[g["forecast"], fc], discrimination=g["discrimination"])
    return out


def confirm(provider, TEAMS, subjects, home, claims, grades, out):
    fr = rows(TEAMS, subjects, home, claims, K, VENUE)
    s = summary(fr)
    for c, d in fr.groupby("claim", sort=False):
        s[c]["skill_adjusted_ci"] = E.ratio_ci(d, E.se("Fa"), E.se("B"), 2000, 2029, True)[1]
        s[c]["verdict"] = (
            "adjusted better" if s[c]["improvement_ci"][0] > 0 else ("adjusted worse" if s[c]["improvement_ci"][1] < 0 else "no difference")
        )
    n = len(s)
    better = sum(v["verdict"] == "adjusted better" for v in s.values())
    worse = sum(v["verdict"] == "adjusted worse" for v in s.values())
    answer = (
        "helps" if better >= 0.5 * n and worse <= 0.1 * n else ("helps for some statements" if better >= 0.2 * n else "does not help")
    )  # reading fixed in the protocol
    rg = regrade(s, grades)
    res = dict(
        protocol=PROTOCOL,
        provider=provider,
        k=K,
        venue=VENUE,
        n_teams=len(subjects),
        n_statements=n,
        adjusted_better=better,
        adjusted_worse=worse,
        answer=answer,
        median_improvement=float(np.median([v["improvement"] for v in s.values()])),
        grades_changed={c: v for c, v in rg.items() if v["before"] != v["after"]},
        grades_after=dict(collections.Counter(v["after"] for v in rg.values())),
        statements=s,
        regrade=rg,
    )
    for c, v in s.items():
        print(f"{c} {v['statement'][:44]:44} improvement {v['improvement']:+.3f} [{v['improvement_ci'][0]:+.3f}, {v['improvement_ci'][1]:+.3f}] {v['verdict']:15} grade {rg[c]['before']} -> {rg[c]['after']}")
    print(f"{provider}: better {better}, worse {worse} of {n} -> {answer}; grades changed {list(res['grades_changed'])}")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("->", out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) == 4 and a[0] == "confirm" and a[1] in ("statsbomb", "wyscout"):
        prov = a[1]
        out = os.path.join(REPO, "results", f"opponent_forecast_{prov}.json")
        guard(out)
        if prov == "statsbomb":  # <sb_work_dir> <events data dir>
            TEAMS = E.load_teams(a[2])
            E.drop_missing(TEAMS, a[3])
            subjects = [t for t in TEAMS if t not in E.DEV + E.EXCLUDED]
            assert len(subjects) == 70 and len(TEAMS) == 80
            home = home_of_statsbomb(REPO)
            claims = SCALAR
            grades = json.load(open(os.path.join(REPO, "results", "evidence_grade_corrected.json"), encoding="utf-8"))["statements"]
        else:  # <wy_work_dir> <wy_dir>
            import evidence_grade_wyscout as W  # restricts E.CLAIMS to the statements Wyscout supports

            TEAMS = W.load_teams(a[2])
            subjects = [t for t in TEAMS if t not in W.DEV]
            assert len(subjects) == 96 and len(TEAMS) == 98
            home = {}
            for country in W.COUNTRIES:
                for g in json.load(open(os.path.join(a[3], country, "matches", "generic.json"), encoding="utf-8")):
                    home[g["match_id"]] = g["home_team"]["home_team_name"]
            claims = [c for c in E.SCALAR]
            grades = json.load(open(os.path.join(REPO, "results", "evidence_grade_wyscout.json"), encoding="utf-8"))["statements"]
        confirm(prov, TEAMS, subjects, home, claims, grades, out)
        sys.exit(0)
    if len(a) != 3 or a[0] != "dev":
        sys.exit(__doc__)
    TEAMS = E.load_teams(a[1])
    E.drop_missing(TEAMS, a[2])  # correction of 19 Oct (grade protocol, note 1)
    home = home_of_statsbomb(REPO)
    subjects = [t for t in TEAMS if t in E.DEV]
    out = dict(
        note="EXPLORATORY development step for RQ2 on the 9 StatsBomb development teams; chooses k and the venue term. Not a test.",
        grid={},
    )
    for venue in (False, True):
        for k in K_GRID:
            fr = rows(TEAMS, subjects, home, SCALAR, k, venue)
            s = summary(fr)
            pooled = float(np.median([v["improvement"] for v in s.values()]))  # statements have different units: median, not a pooled sum
            key = f"k={k}, venue={'yes' if venue else 'no'}"
            out["grid"][key] = dict(pooled_improvement=pooled, statements=s)
            better = sum(v["improvement_ci"][0] > 0 for v in s.values())
            worse = sum(v["improvement_ci"][1] < 0 for v in s.values())
            print(f"{key:20} pooled {pooled:+.4f} | clearly better {better}, clearly worse {worse} of {len(s)}", flush=True)
    fn = os.path.join(REPO, "results", "exploratory_opponent_forecast_dev.json")
    json.dump(out, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("->", fn)
