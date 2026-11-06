"""RQ1: the evidence grade on Wyscout 2017/18. Protocol: docs/protocol_evidence_grade_wyscout.md.
Same measures, thresholds and code as evidence_grade.py (imported); only the data and the list of statements change.
Usage (from the repo root; wy_dir = one converted league per country, see the protocol):
    python -X utf8 src/analysis/evidence_grade_wyscout.py extract <wy_dir> <work_dir>          # all 98 teams -> <work_dir>/teams/*.pkl
    python -X utf8 src/analysis/evidence_grade_wyscout.py analyse <work_dir> --set dev|confirm
The smoke test (2 teams x 8 matches) is in archive/smoke_grade.py. The analyse step stops if the protocol or the scripts are not committed and pushed, or if the result file already exists."""

import sys, os, json, glob, pickle
import numpy as np, pandas as pd

ARGV = sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as E

sys.argv = ARGV
REPO = E.REPO
COUNTRIES = {"England": "Premier League", "France": "Ligue 1", "Germany": "Bundesliga", "Italy": "Serie A", "Spain": "La Liga"}
DEV = ["Barcelona", "Napoli"]
# Wyscout has no pressures and no xG: these statements are not graded
NOT_TESTABLE = {
    "D24": "needs pressures",
    "D25": "needs pressures",
    "A32": "needs pressures",
    "D28": "needs xG",
    "A30": "needs xG",
}
# remove them from evidence_grade.py too, so all its functions work on the remaining statements
E.CLAIMS = {c: d for c, d in E.CLAIMS.items() if c not in NOT_TESTABLE}
E.SCALAR = [c for c in E.CLAIMS if c[0] in "SRPTDA"]
LETTERS = "ABCD"
PROTOCOL = "docs/protocol_evidence_grade_wyscout.md"
SB_RESULT = os.path.join(REPO, "results", "evidence_grade_corrected.json")


def all_teams(wy_dir):
    teams = []
    for country, league in COUNTRIES.items():
        base = os.path.join(wy_dir, country)
        ms = json.load(open(os.path.join(base, "matches", "generic.json"), encoding="utf-8"))
        names = set()
        for g in ms:
            names.add(g["home_team"]["home_team_name"])
            names.add(g["away_team"]["away_team_name"])
        for t in sorted(names):
            own = [g for g in ms if t in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
            own.sort(key=lambda g: g["match_date"])
            teams.append({"team": t, "league": league, "base": base, "matches": own})
    return teams


def extract(work, teams, max_matches=None):
    # as evidence_grade.extract, but each team has its own data folder and the file name has the league
    os.makedirs(os.path.join(work, "teams"), exist_ok=True)
    tmp = os.path.join(work, "one_match.json")
    for i, t in enumerate(teams):
        out = os.path.join(work, "teams", f"{t['league']}__{t['team']}".replace(" ", "_") + ".pkl")
        if os.path.exists(out):
            continue
        ms = t["matches"][:max_matches] if max_matches else t["matches"]
        R = {"team": t["team"], "league": t["league"], "dates": [], "ids": [], "V": [], "recv": [], "ctak": [], "seq": []}
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
    TEAMS = {}
    for f in sorted(glob.glob(os.path.join(work, "teams", "*.pkl"))):
        R = pickle.load(open(f, "rb"))
        if R["team"] in TEAMS:
            sys.exit(f"two teams named {R['team']}: names must be unique across leagues")
        TEAMS[R["team"]] = R
    return TEAMS


def wilson(k, n, z=1.96):
    # 95% Wilson interval of a proportion k / n
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(centre - half), float(centre + half)]


def kappa_linear(a, b):
    # Cohen's kappa with linear weights: one letter apart counts 2/3 of an agreement, A vs D counts 0
    x = [LETTERS.index(v) for v in a]
    y = [LETTERS.index(v) for v in b]
    k = len(LETTERS)
    w = 1 - np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    O = np.zeros((k, k))
    for i, j in zip(x, y):
        O[i, j] += 1
    O /= O.sum()
    expected = np.outer(O.sum(1), O.sum(0))
    po = (w * O).sum()
    pe = (w * expected).sum()
    if pe < 1:
        return float((po - pe) / (1 - pe))
    return None


def compare(wy, sb):
    # letter by letter: StatsBomb grade vs Wyscout grade
    rows = {}
    for c, r in wy.items():
        s = sb[c]
        rows[c] = {
            "statement": r["statement"],
            "statsbomb": s["grade"],
            "wyscout": r["grade"],
            "letters_apart": abs(LETTERS.index(s["grade"]) - LETTERS.index(r["grade"])),
            "forecast": [s["forecast"], r["forecast"]],
            "discrimination": [s["discrimination"], r["discrimination"]],
            "skill": [s.get("skill"), r.get("skill")],
            "D": [s.get("D"), r.get("D")],
        }
    n = len(rows)
    same = sum(v["letters_apart"] == 0 for v in rows.values())
    within1 = sum(v["letters_apart"] <= 1 for v in rows.values())
    far = sorted(c for c, v in rows.items() if v["letters_apart"] >= 2)
    share = same / n
    # reading fixed in the protocol
    if share >= 0.70 and not far:
        verdict = "hold"
    elif share >= 0.50:
        verdict = "partly hold"
    else:
        verdict = "do not hold"
    return {
        "n_statements": n,
        "same_letter": same,
        "same_letter_share": share,
        "same_letter_wilson95": wilson(same, n),
        "within_one_letter": within1,
        "two_or_more_apart": far,
        "same_forecast_verdict": sum(v["forecast"][0] == v["forecast"][1] for v in rows.values()),
        "same_discrimination_level": sum(v["discrimination"][0] == v["discrimination"][1] for v in rows.values()),
        "weighted_kappa": kappa_linear([v["statsbomb"] for v in rows.values()], [v["wyscout"] for v in rows.values()]),
        "verdict": verdict,
        "changed": {c: v for c, v in rows.items() if v["letters_apart"] > 0},
        "all": rows,
    }


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] not in ("extract", "analyse"):
        sys.exit(__doc__)

    if a[0] == "extract":
        T = all_teams(a[1])
        print(f"{len(T)} teams in {len(COUNTRIES)} leagues", flush=True)
        extract(a[2], T)

    else:
        which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else ""
        if which not in ("dev", "confirm"):
            sys.exit("--set dev or --set confirm")
        out = os.path.join(REPO, "results", f"evidence_grade_wyscout{'_dev' if which == 'dev' else ''}.json")
        E.guard(out, [PROTOCOL, "src/analysis/evidence_grade_wyscout.py", "src/analysis/evidence_grade.py"])
        TEAMS = load_teams(a[1])
        if which == "dev":
            subjects = [t for t in TEAMS if t in DEV]
            expected = 2
        else:
            subjects = [t for t in TEAMS if t not in DEV]
            expected = 96
        if len(subjects) != expected or len(TEAMS) != 98:
            sys.exit(f"expected 98 extracted teams and {expected} subjects, found {len(TEAMS)} and {len(subjects)}: run extract first")

        res = E.analyse(TEAMS, subjects, which)
        res["protocol"] = PROTOCOL
        res["data"] = "Wyscout public data 2017/18, five leagues (Pappalardo et al. 2019, CC BY 4.0); possessions reconstructed"
        res["not_testable"] = NOT_TESTABLE
        if which == "confirm":
            sb = json.load(open(SB_RESULT, encoding="utf-8"))["statements"]
            cp = compare(res["statements"], sb)
            res["comparison_with_statsbomb"] = cp
            print(
                f"same letter {cp['same_letter']}/{cp['n_statements']} {cp['same_letter_wilson95']}, two or more apart {cp['two_or_more_apart']}, "
                f"kappa {cp['weighted_kappa']} -> grades {cp['verdict']}"
            )
        json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("grades:", res["grades"], "| sanity checks:", res["sanity_checks"], "->", out)
