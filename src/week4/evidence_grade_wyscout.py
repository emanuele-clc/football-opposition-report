"""Evidence grade on Wyscout 2017/18 (RQ1; protocol: docs/protocol_evidence_grade_wyscout.md). Same measures, thresholds and code as
evidence_grade.py (imported); only the data and the set of graded statements change.
Usage (from the repo root; wy_dir = folder with one converted league per country, see the protocol):
    python -X utf8 src/week4/evidence_grade_wyscout.py smoke   <wy_dir> <work_dir>             # 2 dev teams x 8 matches, prints counts only
    python -X utf8 src/week4/evidence_grade_wyscout.py extract <wy_dir> <work_dir>             # all 98 teams -> <work_dir>/teams/*.pkl (skips teams done)
    python -X utf8 src/week4/evidence_grade_wyscout.py analyse <work_dir> --set dev|confirm   # -> results/evidence_grade_wyscout_dev.json | _wyscout.json
The analyse step refuses to run if the protocol or this script differ from the last commit, the commit is not on origin/main, or the result file exists."""

import sys, os, json, glob, pickle, collections, subprocess
import numpy as np, pandas as pd

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E

sys.argv = ARGV
REPO = E.REPO
COUNTRIES = {"England": "Premier League", "France": "Ligue 1", "Germany": "Bundesliga", "Italy": "Serie A", "Spain": "La Liga"}
DEV = ["Barcelona", "Napoli"]
NOT_TESTABLE = {
    "D24": "needs pressures",
    "D25": "needs pressures",
    "A32": "needs pressures",
    "D28": "needs xG",
    "A30": "needs xG",
}
# grade only the statements Wyscout supports (protocol, Statements graded)
E.CLAIMS = {c: d for c, d in E.CLAIMS.items() if c not in NOT_TESTABLE}
E.SCALAR = [c for c in E.CLAIMS if c[0] in "SRPTDA"]
LETTERS = "ABCD"
PROTOCOL = "docs/protocol_evidence_grade_wyscout.md"
SB_RESULT = os.path.join(REPO, "results", "evidence_grade_corrected.json")


def all_teams(wy_dir):
    T = []
    for country, lg in COUNTRIES.items():
        base = os.path.join(wy_dir, country)
        ms = json.load(open(os.path.join(base, "matches", "generic.json"), encoding="utf-8"))
        for t in sorted({x for g in ms for x in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])}):
            own = [g for g in ms if t in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
            T.append(dict(team=t, league=lg, base=base, matches=sorted(own, key=lambda g: g["match_date"])))
    return T


def extract(work, teams, max_matches=None):
    os.makedirs(os.path.join(work, "teams"), exist_ok=True)
    tmp = os.path.join(work, "one_match.json")
    for i, t in enumerate(teams):
        out = os.path.join(work, "teams", f"{t['league']}__{t['team']}".replace(" ", "_") + ".pkl")
        if os.path.exists(out):
            continue
        ms = t["matches"][:max_matches] if max_matches else t["matches"]
        R = dict(team=t["team"], league=t["league"], dates=[], ids=[], V=[], recv=[], ctak=[], seq=[])
        for mi, g in enumerate(ms):
            V, recv, ctak, seq = E.match_values(g, t["team"], t["base"], tmp)
            R["dates"].append(g["match_date"])
            R["ids"].append(g["match_id"])
            R["V"].append(V)
            R["recv"].append(recv)
            R["ctak"].append(ctak)
            R["seq"].append(seq.assign(mi=mi))
        R["seq"] = pd.concat(R["seq"], ignore_index=True)
        pickle.dump(R, open(out, "wb"))
        print(f"[{i + 1}/{len(teams)}] {t['team']} ({t['league']}): {len(ms)} matches, {len(R['seq'])} sequences", flush=True)


def load_teams(work):
    T = {}
    for f in sorted(glob.glob(os.path.join(work, "teams", "*.pkl"))):
        R = pickle.load(open(f, "rb"))
        if R["team"] in T:
            sys.exit(f"two teams named {R['team']}: names must be unique across leagues")
        T[R["team"]] = R
    return T


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


def kappa_linear(a, b):
    """Cohen's kappa with linear weights on the letters A-D."""
    idx = {l: i for i, l in enumerate(LETTERS)}
    x, y = np.array([idx[v] for v in a]), np.array([idx[v] for v in b])
    k = len(LETTERS)
    w = 1 - np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    O = np.zeros((k, k))
    for i, j in zip(x, y):
        O[i, j] += 1
    O /= O.sum()
    Ex = np.outer(O.sum(1), O.sum(0))
    po, pe = (w * O).sum(), (w * Ex).sum()
    return float((po - pe) / (1 - pe)) if pe < 1 else None


def compare(wy, sb):
    rows = {}
    for c, r in wy.items():
        s = sb[c]
        rows[c] = dict(
            statement=r["statement"],
            statsbomb=s["grade"],
            wyscout=r["grade"],
            letters_apart=abs(LETTERS.index(s["grade"]) - LETTERS.index(r["grade"])),
            forecast=[s["forecast"], r["forecast"]],
            discrimination=[s["discrimination"], r["discrimination"]],
            skill=[s.get("skill"), r.get("skill")],
            D=[s.get("D"), r.get("D")],
        )
    n = len(rows)
    same = sum(v["letters_apart"] == 0 for v in rows.values())
    within1 = sum(v["letters_apart"] <= 1 for v in rows.values())
    far = sorted(c for c, v in rows.items() if v["letters_apart"] >= 2)
    share = same / n
    verdict = (
        "hold"
        if share >= 0.70 and not far
        else ("partly hold" if share >= 0.50 else "do not hold")
    )  # reading fixed in the protocol
    return dict(
        n_statements=n,
        same_letter=same,
        same_letter_share=share,
        same_letter_wilson95=wilson(same, n),
        within_one_letter=within1,
        two_or_more_apart=far,
        same_forecast_verdict=sum(v["forecast"][0] == v["forecast"][1] for v in rows.values()),
        same_discrimination_level=sum(v["discrimination"][0] == v["discrimination"][1] for v in rows.values()),
        weighted_kappa=kappa_linear([v["statsbomb"] for v in rows.values()], [v["wyscout"] for v in rows.values()]),
        verdict=verdict,
        changed={c: v for c, v in rows.items() if v["letters_apart"] > 0},
        all=rows,
    )


def guard(out):
    files = [PROTOCOL, "src/week4/evidence_grade_wyscout.py", "src/week4/evidence_grade.py"]
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)
    if os.path.exists(out):
        sys.exit(f"{out} already exists: the run is done once (protocol, Procedure).")
    if git("ls-files", "--error-unmatch", *files).returncode:
        sys.exit("Commit the protocol and the scripts first.")
    if git("diff", "--quiet", "HEAD", "--", *files).returncode:
        sys.exit("The protocol or the scripts differ from the last commit: commit them first.")
    c = git("log", "-1", "--format=%H", "--", files[0]).stdout.strip()
    if git("merge-base", "--is-ancestor", c, "origin/main").returncode:
        sys.exit("The protocol commit is not on origin/main: push it first.")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] not in ("smoke", "extract", "analyse"):
        sys.exit(__doc__)
    if a[0] == "extract":
        T = all_teams(a[1])
        print(f"{len(T)} teams in {len(COUNTRIES)} leagues", flush=True)
        extract(a[2], T)
    elif a[0] == "smoke":  # code check only: counts, never a value
        work = os.path.join(a[2], "smoke")
        T = [dict(t, league="smoke") for t in all_teams(a[1]) if t["team"] in DEV]  # one 'league', so the baseline exists
        extract(work, T, max_matches=8)
        TEAMS = load_teams(work)
        fr = E.all_forecasts(TEAMS, list(TEAMS))
        print("forecast rows per statement:", dict(fr.groupby("claim").size()))
        print("statements without forecast rows:", sorted(set(E.CLAIMS) - set(fr.claim)))
        for c in E.SCALAR + list(E.LEAD):
            E.discrimination(TEAMS, list(TEAMS), c, np.random.default_rng(7))
        print(f"smoke test passed: {len(E.CLAIMS)} statements (no values printed)")
    else:
        which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else ""
        if which not in ("dev", "confirm"):
            sys.exit("--set dev or --set confirm")
        out = os.path.join(REPO, "results", f"evidence_grade_wyscout{'_dev' if which == 'dev' else ''}.json")
        guard(out)
        TEAMS = load_teams(a[1])
        subjects = [t for t in TEAMS if t in DEV] if which == "dev" else [t for t in TEAMS if t not in DEV]
        exp = 2 if which == "dev" else 96
        if len(subjects) != exp or len(TEAMS) != 98:
            sys.exit(f"expected 98 extracted teams and {exp} subjects, found {len(TEAMS)} and {len(subjects)}: run extract first")
        res = E.analyse(TEAMS, subjects, which)
        res["protocol"] = PROTOCOL
        res["data"] = "Wyscout public data 2017/18, five leagues (Pappalardo et al. 2019, CC BY 4.0); possessions reconstructed"
        res["not_testable"] = NOT_TESTABLE
        if which == "confirm":
            res["comparison_with_statsbomb"] = compare(
                res["statements"], json.load(open(SB_RESULT, encoding="utf-8"))["statements"]
            )
            cp = res["comparison_with_statsbomb"]
            print(
                f"same letter {cp['same_letter']}/{cp['n_statements']} {cp['same_letter_wilson95']}, two or more apart {cp['two_or_more_apart']}, "
                f"kappa {cp['weighted_kappa']} -> grades {cp['verdict']}"
            )
        json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("grades:", res["grades"], "| sanity checks:", res["sanity_checks"], "->", out)
