"""Fewer variables: which statements say the same thing? (exploratory, docs/protocol_redundancy.md)

Season value per team and statement, standardised within each league, Spearman correlation over the 70 confirmatory teams,
redundant pairs (|rho| >= 0.80), one statement kept per group, core / secondary / set aside.

Usage (from the repo root; data_dir = folder with data_info/ and ev/, work_dir = the grade extraction):
    python -X utf8 src/analysis/exploratory_redundancy.py <data_dir> <work_dir> [--dev]
--dev: the 9 development teams, only to check the code (results/..._dev.json)."""

import sys, os, json, itertools
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as EG  # noqa: E402

PROTOCOL = "docs/protocol_redundancy.md"
SCRIPT = "src/analysis/exploratory_redundancy.py"
OUT = os.path.join(EG.REPO, "results", "exploratory_redundancy.json")
RHO = 0.80
RELATED = 0.60
B, SEED = 2000, 19
ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


def main(data_dir, work, dev=False):
    out = OUT.replace('.json', '_dev.json') if dev else OUT
    if not dev:
        EG.guard(OUT, [PROTOCOL, SCRIPT])
    TEAMS = EG.load_teams(work)
    EG.drop_missing(TEAMS, data_dir)
    subjects = sorted(t for t in TEAMS if (t in EG.DEV) == dev and t not in EG.EXCLUDED)
    if len(TEAMS) != 80 or len(subjects) != (9 if dev else 70):
        sys.exit("expected 80 extracted teams and 70 subjects")
    claims = EG.SCALAR
    official = json.load(open(os.path.join(EG.REPO, "results", "evidence_grade_corrected.json"), encoding="utf-8"))["statements"]

    # season values, standardised within each league
    X = np.full((len(subjects), len(claims)), np.nan)
    league = np.array([TEAMS[t]["league"] for t in subjects])
    for i, t in enumerate(subjects):
        for j, c in enumerate(claims):
            nums, dens = EG.arrays(TEAMS[t], c)
            if dens.sum() > 0:
                X[i, j] = nums.sum() / dens.sum()
    for lg in set(league):
        r = league == lg
        X[r] = (X[r] - np.nanmean(X[r], 0)) / np.nanstd(X[r], 0, ddof=1)

    def rho(a, b):
        ok = ~np.isnan(a) & ~np.isnan(b)
        return stats.spearmanr(a[ok], b[ok])[0]

    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(subjects), (B, len(subjects)))
    matrix, pairs, related = {}, [], []
    for a, b in itertools.combinations(range(len(claims)), 2):
        r = float(rho(X[:, a], X[:, b]))
        matrix[f"{claims[a]}-{claims[b]}"] = round(r, 3)
        if abs(r) >= RELATED:
            boot = [rho(X[d, a], X[d, b]) for d in draws]
            ci = [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]
            row = {"a": claims[a], "b": claims[b], "rho": round(r, 3), "ci": [round(v, 3) for v in ci]}
            (pairs if abs(r) >= RHO else related).append(row)

    # groups = connected components of the redundant pairs
    parent = {c: c for c in claims}

    def find(c):
        while parent[c] != c:
            c = parent[c]
        return c

    for p in pairs:
        parent[find(p["a"])] = find(p["b"])
    groups = {}
    for c in claims:
        groups.setdefault(find(c), []).append(c)

    def rank(c):
        o = official[c]
        return (ORDER[o["grade"]], -(o.get("skill") or -9), -(o.get("D") or -9))

    label = {}
    group_list = []
    for members in groups.values():
        kept = min(members, key=rank)
        if len(members) > 1:
            group_list.append({"members": sorted(members), "kept": kept})
        for c in members:
            g = official[c]["grade"]
            if c != kept:
                label[c] = {"label": "set aside", "reason": f"redundant with {kept}"}
            elif g in ("A", "B"):
                label[c] = {"label": "core", "reason": f"grade {g}"}
            elif g == "C":
                label[c] = {"label": "secondary", "reason": "grade C: only as a hint"}
            else:
                label[c] = {"label": "set aside", "reason": "grade D"}
    for c in EG.CLAIMS:
        if c not in label:
            label[c] = {"label": "not tested", "reason": "family share or main player: no single season value"}
        label[c]["statement"] = EG.CLAIMS[c]
        label[c]["grade"] = official[c]["grade"]

    core = [c for c in claims if label[c]["label"] == "core"]
    res = {
        "protocol": PROTOCOL,
        "exploratory": True,
        "n_teams": len(subjects),
        "redundant_pairs": sorted(pairs, key=lambda p: -abs(p["rho"])),
        "related_pairs": sorted(related, key=lambda p: -abs(p["rho"])),
        "groups": group_list,
        "labels": label,
        "core": core,
        "counts": {k: sum(v["label"] == k for v in label.values()) for k in ("core", "secondary", "set aside", "not tested")},
        "matrix": matrix,
    }
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("redundant pairs:", [(p["a"], p["b"], p["rho"]) for p in res["redundant_pairs"]])
    print("counts:", res["counts"], "| core:", core, "->", out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    main(*a, dev="--dev" in sys.argv)
