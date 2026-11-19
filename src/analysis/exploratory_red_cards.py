"""Red cards: do matches played with ten men change the grades? (exploratory, docs/protocol_red_cards.md)

Two variants against the official grade: E drops team-matches with >= 15 uneven minutes, T recomputes them on the events before
the first sending-off. Same grade code (evidence_grade.analyse) and seeds.

Usage (from the repo root; data_dir = folder with data_info/ and ev/, work_dir = the grade extraction):
    python -X utf8 src/analysis/exploratory_red_cards.py <data_dir> <work_dir> [--dev]
--dev: the 9 development teams, only to check the code (results/..._dev.json)."""

import sys, os, json, copy, tempfile, collections
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_grade as EG  # noqa: E402  (also puts src/report on the path)
from minutes import match_minutes, elapsed_fn  # noqa: E402

PROTOCOL = "docs/protocol_red_cards.md"
SCRIPT = "src/analysis/exploratory_red_cards.py"
OUT = os.path.join(EG.REPO, "results", "exploratory_red_cards.json")
UNEVEN_MIN = 15 * 60
PER_MATCH = ["S01", "P14", "T18", "D24", "D27", "D28", "A29", "A30", "A31"]
DELTA = 0.05
MAX_SENSITIVE = 3


def keep_matches(R, keep):
    new_index = {i: j for j, i in enumerate(keep)}
    for k in ("dates", "ids", "V", "recv", "ctak"):
        R[k] = [R[k][i] for i in keep]
    seq = R["seq"][R["seq"].mi.isin(keep)]
    R["seq"] = seq.assign(mi=seq.mi.map(new_index))


def main(data_dir, work, dev=False):
    out = OUT.replace('.json', '_dev.json') if dev else OUT
    if not dev:
        EG.guard(OUT, [PROTOCOL, SCRIPT, "src/report/minutes.py"])
    TEAMS = EG.load_teams(work)
    EG.drop_missing(TEAMS, data_dir)
    subjects = [t for t in TEAMS if (t in EG.DEV) == dev and t not in EG.EXCLUDED]
    if len(TEAMS) != 80 or len(subjects) != (9 if dev else 70):
        sys.exit("expected 80 extracted teams and 70 subjects")
    games = {g["match_id"]: g for t in EG.all_teams(data_dir) for g in t["matches"]}

    # sending-offs of every team-match
    info = {}
    for name, R in TEAMS.items():
        for m in R["ids"]:
            ev = EG._load(open(os.path.join(data_dir, "ev", f"{m}.json"), encoding="utf-8"))
            mm = match_minutes(ev, name)
            info[(name, m)] = {"length": mm["length"], "even": mm["even_until"], "reds": mm["reds"]}
    with_red = [k for k, v in info.items() if v["reds"]]
    uneven = [k for k, v in info.items() if v["length"] - v["even"] >= UNEVEN_MIN]
    print(f"team-matches with a sending-off: {len(with_red)} ({sum(k[0] in subjects for k in with_red)} of subjects); "
          f">= 15 uneven minutes: {len(uneven)}", flush=True)

    # variant E
    TE = copy.deepcopy(TEAMS)
    for name, R in TE.items():
        keep_matches(R, [i for i, m in enumerate(R["ids"]) if (name, m) not in set(uneven)])
    print("variant E", flush=True)
    resE = EG.analyse(TE, subjects, "red-cards-E")

    # variant T
    TT = copy.deepcopy(TEAMS)
    tmpdir = tempfile.mkdtemp(prefix="redcards_")
    os.makedirs(os.path.join(tmpdir, "ev"))
    tmp = os.path.join(tmpdir, "one_match.json")
    n_cut = n_drop = 0
    for name, R in TT.items():
        keep = []
        for i, m in enumerate(R["ids"]):
            v = info[(name, m)]
            if not v["reds"]:
                keep.append(i)
                continue
            if v["even"] < 60:
                n_drop += 1
                continue
            ev = EG._load(open(os.path.join(data_dir, "ev", f"{m}.json"), encoding="utf-8"))
            elapsed, _ = elapsed_fn(ev)
            cut = [e for e in ev if elapsed(e) is None or elapsed(e) < v["even"]]
            fn = os.path.join(tmpdir, "ev", f"{m}.json")
            json.dump(cut, open(fn, "w", encoding="utf-8"))
            EG._cache.clear()
            V, recv, ctak, seq = EG.match_values(games[m], name, tmpdir, tmp)
            os.remove(fn)
            frac = v["even"] / v["length"]
            for c in PER_MATCH:
                if c in V:
                    V[c] = (V[c][0], frac)
            R["V"][i], R["recv"][i], R["ctak"][i] = V, recv, ctak
            R["seq"] = R["seq"][R["seq"].mi != i]
            R["seq"] = EG.pd.concat([R["seq"], seq.assign(mi=i)], ignore_index=True)
            n_cut += 1
            keep.append(i)
        if len(keep) < len(R["ids"]):
            keep_matches(R, keep)
    print(f"variant T: {n_cut} team-matches cut, {n_drop} dropped (sending-off in the first minute)", flush=True)
    resT = EG.analyse(TT, subjects, "red-cards-T")

    # baseline: the same code on the unchanged data (for the 70 teams it must equal results/evidence_grade_corrected.json)
    base = EG.analyse(TEAMS, subjects, "baseline")["statements"]
    official = base
    same_as_file = None
    if not dev:
        ref = json.load(open(os.path.join(EG.REPO, "results", "evidence_grade_corrected.json"), encoding="utf-8"))["statements"]
        same_as_file = all(ref[c]["grade"] == base[c]["grade"] and abs((ref[c].get("skill") or 0) - (base[c].get("skill") or 0)) < 1e-9
                           and abs((ref[c].get("D") or 0) - (base[c].get("D") or 0)) < 1e-9 for c in EG.CLAIMS)
        print("baseline equals the official grade file:", same_as_file, flush=True)
    rows, sensitive = {}, []
    for c in EG.CLAIMS:
        o, e, t = official[c], resE["statements"][c], resT["statements"][c]
        r = {"statement": o["statement"], "official": {k: o.get(k) for k in ("skill", "D", "grade")}}
        for lab, x in (("E", e), ("T", t)):
            r[lab] = {k: x.get(k) for k in ("skill", "skill_ci", "D", "grade", "forecasts")}
            r[lab]["d_skill"] = None if x.get("skill") is None or o.get("skill") is None else x["skill"] - o["skill"]
            r[lab]["d_D"] = None if x.get("D") is None or o.get("D") is None else x["D"] - o["D"]
            r[lab]["grade_changed"] = x["grade"] != o["grade"]
        big_T = any(abs(r["T"][k]) > DELTA for k in ("d_skill", "d_D") if r["T"][k] is not None)
        r["sensitive"] = (r["E"]["grade_changed"] and r["T"]["grade_changed"]) or big_T
        if r["sensitive"]:
            sensitive.append(c)
        rows[c] = r
    reading = ("matches with ten men do not change the grades in a meaningful way" if len(sensitive) <= MAX_SENSITIVE
               else "some statements are sensitive to red cards: show both values, the official grade stays the reference")
    res = {
        "protocol": PROTOCOL,
        "exploratory": True,
        "baseline_equals_official_file": same_as_file,
        "team_matches_with_sending_off": {"all_80": len(with_red), "subjects": sum(k[0] in subjects for k in with_red)},
        "team_matches_uneven_15min": {"all_80": len(uneven), "subjects": sum(k[0] in subjects for k in uneven)},
        "variant_T": {"cut": n_cut, "dropped": n_drop},
        "sensitive": sensitive,
        "reading": reading,
        "statements": rows,
        "sending_offs": [{"team": k[0], "match": int(k[1]), "minute": r["minute"], "side": r["side"], "player": r["player"]}
                         for k in with_red for r in info[k]["reds"]],
    }
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    print("sensitive:", sensitive, "|", reading, "->", out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    main(*a, dev="--dev" in sys.argv)
