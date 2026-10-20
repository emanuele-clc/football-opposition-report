"""Selezione delle squadre per la replica su 10 squadre (protocollo: docs/protocol_replication10.md).
Regola fissata prima: stagioni complete 2015/2016 di La Liga, Serie A e Ligue 1 (competizioni con almeno 300 partite disponibili), squadre con almeno 30 partite,
escluse le 4 squadre gia' usate. Sorteggio stratificato per campionato con seed fisso: 2 squadre primarie + 1 di riserva per campionato (la riserva si usa solo
per un guasto tecnico, mai per un risultato). Uso: python select_teams.py [data_info=data_info] [uscita=docs/replication10_selection.json]"""

import sys, json, glob, os, collections
import numpy as np

SEED = 20261013
N_PRIMARY, N_RESERVE = 2, 1
USED = {"Bayer Leverkusen", "Leicester City", "Barcelona", "Arsenal"}
STRATA = ["La Liga", "Serie A", "Ligue 1"]
SEASON = "2015/2016"
di = sys.argv[1] if len(sys.argv) > 1 else "data_info"
outp = sys.argv[2] if len(sys.argv) > 2 else "docs/replication10_selection.json"
comp = {(c["competition_id"], c["season_id"]): c for c in json.load(open(f"{di}/competitions.json", encoding="utf-8"))}
rng = np.random.default_rng(SEED)
teams = []
for name in STRATA:
    cands = []
    for f in sorted(glob.glob(f"{di}/[0-9]*_*.json")):
        cid, sid = map(int, os.path.basename(f)[:-5].split("_"))
        c = comp.get((cid, sid))
        if c is None or c["competition_name"] != name or c["season_name"] != SEASON:
            continue
        ms = json.load(open(f, encoding="utf-8"))
        if len(ms) < 300:
            continue
        cnt = collections.Counter(
            t
            for g in ms
            if g.get("match_status") == "available"
            for t in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])
        )
        cands += [(t, cid, sid, n) for t, n in cnt.items() if n >= 30 and t not in USED]
    cands.sort(key=lambda x: x[0])
    order = rng.permutation(len(cands))
    for rank, i in enumerate(order[: N_PRIMARY + N_RESERVE]):
        t, cid, sid, n = cands[i]
        teams.append(
            dict(
                team=t,
                league=name,
                season=SEASON,
                competition_id=cid,
                season_id=sid,
                matches=n,
                role="primary" if rank < N_PRIMARY else "reserve",
                candidates_in_stratum=len(cands),
            )
        )
os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
json.dump(
    dict(seed=SEED, rule=__doc__.split("Uso:")[0].strip(), already_used=sorted(USED), teams=teams),
    open(outp, "w", encoding="utf-8"),
    indent=1,
    ensure_ascii=False,
)
for t in teams:
    print(
        f"{t['role']:8s} {t['league']:8s} {t['team']:28s} ({t['matches']} partite, {t['candidates_in_stratum']} candidate nello strato)"
    )
print("salvato", outp)
