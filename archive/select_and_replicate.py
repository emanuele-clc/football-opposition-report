"""ARCHIVE (done once, 13 Oct 2026): the draw of the 6 new teams and the first run of the 10-team replication.
    python archive/select_and_replicate.py select [data_info] [out]          draw the 6 new teams (seed 20261013) -> docs/replication10_selection.json
    python archive/select_and_replicate.py replicate <selection.json> --confirm [--only "Team"] [--reserves] [--print-only]
                                                                       download + E1 + validation, once per team (run from the data folder)
Moved here from src/analysis/ten_teams.py on 6 Nov 2026 (same code; the selection file it writes is identical to the committed one)."""

import sys, os, json, glob, collections, subprocess
import numpy as np

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "analysis")


def run_logged(cmd, log):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    open(log, "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
    return r


def show(cmd):
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


# ---------------------------------------------------------------- select
# the rule as it was written in the selection file on 13 Oct 2026
RULE = (
    "Selezione delle squadre per la replica su 10 squadre (protocollo: docs/protocol_replication10.md).\n"
    "Regola fissata prima: stagioni complete 2015/2016 di La Liga, Serie A e Ligue 1 (competizioni con almeno 300 partite disponibili), squadre con almeno 30 partite,\n"
    "escluse le 4 squadre gia' usate. Sorteggio stratificato per campionato con seed fisso: 2 squadre primarie + 1 di riserva per campionato (la riserva si usa solo\n"
    "per un guasto tecnico, mai per un risultato)."
)


def select(data_info, out):
    seed = 20261013
    used = {"Bayer Leverkusen", "Leicester City", "Barcelona", "Arsenal"}
    comps = {}
    for c in json.load(open(f"{data_info}/competitions.json", encoding="utf-8")):
        comps[(c["competition_id"], c["season_id"])] = c
    rng = np.random.default_rng(seed)
    teams = []
    for league in ["La Liga", "Serie A", "Ligue 1"]:
        candidates = []
        for f in sorted(glob.glob(f"{data_info}/[0-9]*_*.json")):
            cid, sid = map(int, os.path.basename(f)[:-5].split("_"))
            c = comps.get((cid, sid))
            if c is None or c["competition_name"] != league or c["season_name"] != "2015/2016":
                continue
            ms = json.load(open(f, encoding="utf-8"))
            if len(ms) < 300:
                continue
            count = collections.Counter()
            for g in ms:
                if g.get("match_status") == "available":
                    count[g["home_team"]["home_team_name"]] += 1
                    count[g["away_team"]["away_team_name"]] += 1
            for t, n in count.items():
                if n >= 30 and t not in used:
                    candidates.append((t, cid, sid, n))
        candidates.sort(key=lambda x: x[0])
        order = rng.permutation(len(candidates))
        for rank, i in enumerate(order[:3]):  # 2 primary + 1 reserve
            t, cid, sid, n = candidates[i]
            teams.append(
                {
                    "team": t,
                    "league": league,
                    "season": "2015/2016",
                    "competition_id": cid,
                    "season_id": sid,
                    "matches": n,
                    "role": "primary" if rank < 2 else "reserve",
                    "candidates_in_stratum": len(candidates),
                }
            )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    result = {"seed": seed, "rule": RULE, "already_used": sorted(used), "teams": teams}
    json.dump(result, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for t in teams:
        print(f"{t['role']:8s} {t['league']:8s} {t['team']:28s} ({t['matches']} partite, {t['candidates_in_stratum']} candidate nello strato)")
    print("salvato", out)


# ---------------------------------------------------------------- replicate
def replicate(selection, flags, only):
    if "--confirm" not in flags and "--print-only" not in flags:
        sys.exit("Needs --confirm (after committing docs/protocol_replication10.md) or --print-only.")
    print_only = "--print-only" in flags
    py = [sys.executable, "-X", "utf8"]
    os.makedirs("run_logs", exist_ok=True)
    for t in selection["teams"]:
        if only and t["team"] != only:
            continue
        if not only and t["role"] != "primary" and "--reserves" not in flags:
            continue
        team = t["team"]
        fn = team.replace(" ", "_")
        mf = f"matches/{t['competition_id']}_{t['season_id']}.json"
        steps = [
            ("download", py + [os.path.join(HERE, "download_data.py"), str(t["competition_id"]), str(t["season_id"]), team]),
            ("E1", py + [os.path.join(HERE, "families.py"), "null", mf, team, "."]),
            ("validazione", py + [os.path.join(HERE, "validate_replication.py"), mf, team, ".", "--confirm"]),
        ]
        print(f"\n=== {team} ({t['league']}, {t['role']}) ===")
        if os.path.exists(f"holdout_{fn}.json") and not print_only:
            print("gia' validata, salto")
            continue
        for label, cmd in steps:
            print(f"[{label}]", show(cmd))
            if print_only:
                continue
            r = run_logged(cmd, f"run_logs/{fn}_{label}.log")
            print("\n".join(r.stdout.strip().splitlines()[-4:]))
            if r.returncode != 0:
                print(f"ERRORE nel passo {label}: vedi run_logs/{fn}_{label}.log")
                break


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        args.remove(only)
    if args and args[0] == "select":
        select(args[1] if len(args) > 1 else "data_info", args[2] if len(args) > 2 else "docs/replication10_selection.json")
    elif len(args) == 2 and args[0] == "replicate":
        replicate(json.load(open(args[1], encoding="utf-8")), flags, only)
    else:
        sys.exit(__doc__)
