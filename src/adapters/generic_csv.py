"""Adattatore: eventi in CSV generico -> formato che la pipeline L2 gia' legge (matches.json + ev/<id>.json in stile StatsBomb).
Cosi' qualunque fornitore di dati si collega mappando le sue colonne al CSV generico (vedi docs/data_format.md).
Uso:  python generic_csv.py eventi.csv cartella_uscita [--coords 100|120x80] [--validate-only]
Colonne obbligatorie: match_id, match_date, home_team, away_team, period, minute, second, team, event_type, x, y
Colonne facoltative:  end_x, end_y, possession_id, restart, pass_length, shot_goal, player, recipient, xg, pass_outcome
- event_type: pass, carry, shot, dribble; azioni difensive duel, interception, foul, clearance, ball_recovery, block (servono alla scheda difensiva:
  PPDA, altezza delle azioni difensive); qualunque altro valore = altro. Le azioni difensive non contano per le possessioni ricostruite.
- pass_outcome: complete / incomplete (vuoto = complete). Senza questa colonna tutti i passaggi contano come riusciti. minute e' cumulativo (secondo tempo parte da 45), period 1 o 2.
- x da 0 (propria porta) a 100 (porta avversaria), y da 0 a 100; la squadra che compie l'evento attacca sempre da sinistra a destra (--coords 100, default). Con --coords 120x80 si usano le misure 120 x 80.
- possession_id: se manca, viene ricostruito (nuova possessione quando un'altra squadra compie un pass/carry/shot/dribble, quando c'e' una ripresa, o cambia il tempo).
- restart: sul primo evento di una ripresa: goal_kick, throw_in, corner, free_kick, kick_off, penalty, keeper (portiere che rimette in gioco dopo una presa; altrimenti vuoto). Senza questa colonna tutte le possessioni sono 'gioco normale' e le riprese da fermo NON si escludono.
- pass_length: in metri nella griglia 120x80; se manca si calcola dalle coordinate."""

import sys, os, json
import numpy as np, pandas as pd

REQ = ["match_id", "match_date", "home_team", "away_team", "period", "minute", "second", "team", "event_type", "x", "y"]
TYPE = {"pass": "Pass", "carry": "Carry", "shot": "Shot", "dribble": "Dribble"}
DEFT = {
    "duel": "Duel",
    "interception": "Interception",
    "foul": "Foul Committed",
    "clearance": "Clearance",
    "ball_recovery": "Ball Recovery",
    "block": "Block",
}  # added 28 Oct 2026: defensive actions, same names as StatsBomb
RESTART = {
    "goal_kick": "From Goal Kick",
    "throw_in": "From Throw In",
    "corner": "From Corner",
    "free_kick": "From Free Kick",
    "kick_off": "From Kick Off",
    "penalty": "From Free Kick",
    "keeper": "From Keeper",
}
CTRL = {"pass", "carry", "shot", "dribble"}


def validate(df):
    problems = []
    miss = [c for c in REQ if c not in df.columns]
    if miss:
        return [f"colonne mancanti: {miss}"], None
    d = df.copy()
    d["event_type"] = d.event_type.astype(str).str.lower().str.strip()
    d.loc[~d.event_type.isin(CTRL | set(DEFT)), "event_type"] = "altro"
    for c in ("period", "minute", "second"):
        bad = pd.to_numeric(d[c], errors="coerce").isna().sum()
        if bad:
            problems.append(f"{bad} valori non numerici in '{c}'")
    ctrl_rows = d[d.event_type.isin(CTRL)]
    for c in ("x", "y"):
        bad = pd.to_numeric(ctrl_rows[c], errors="coerce").isna().sum()
        if bad:
            problems.append(f"{bad} eventi pass/carry/shot/dribble senza '{c}': non utilizzabili")
    if not set(d.period.unique()) <= {1, 2, 3, 4, 5}:
        problems.append(f"valori di period inattesi: {sorted(d.period.unique())}")
    p = d[d.event_type == "pass"]
    if len(p) and ("end_x" not in d.columns or p.end_x.isna().mean() > 0.05):
        problems.append("molti passaggi senza end_x/end_y: servono per lunghezza e traiettoria")
    if "restart" not in d.columns:
        problems.append(
            "AVVISO: manca la colonna 'restart': le riprese da fermo (rinvii, rimesse, corner) non si possono escludere"
        )
    if "possession_id" not in d.columns:
        problems.append("AVVISO: manca 'possession_id': le possessioni saranno ricostruite con un'euristica")
    mx = pd.to_numeric(d.x, errors="coerce").max()
    if mx > 105 and mx <= 120:
        problems.append("AVVISO: x arriva oltre 105: forse le coordinate sono 120x80, usare --coords 120x80")
    return problems, d


def derive_possession(g, min_ctrl=2):
    """Nuova possessione quando: cambia il tempo, c'e' una ripresa, oppure un'altra squadra compie almeno min_ctrl azioni di controllo consecutive (o un tiro).
    Un tocco isolato dell'avversario (rinvio, deviazione) non interrompe la possessione. Euristica: la qualita' va verificata (tests/test_adapter_roundtrip.py).
    """
    team = g.team.values
    typ = g.event_type.values
    per = g.period.values
    n = len(g)
    ctrl = [i for i in range(n) if typ[i] in CTRL]
    nxt = {ctrl[k]: ctrl[k + 1] if k + 1 < len(ctrl) else None for k in range(len(ctrl))}
    rs = g["restart"].values if "restart" in g.columns else [None] * n
    pid, cur, out = 0, None, []
    for i in range(n):
        newp = i == 0 or per[i] != per[i - 1]
        has_rs = rs[i] is not None and not (isinstance(rs[i], float) and np.isnan(rs[i])) and rs[i] != ""
        if not newp and has_rs:
            newp = True
        elif not newp and typ[i] in CTRL and team[i] != cur:
            j = nxt.get(i)
            run = 1 + (1 if (j is not None and team[j] == team[i] and per[j] == per[i]) else 0)
            newp = typ[i] == "shot" or run >= min_ctrl
        if newp:
            pid += 1
            if typ[i] in CTRL:
                cur = team[i]
            elif has_rs:
                cur = team[i]
        out.append(pid)
    return out


def convert(csv_path, out_dir, coords="100"):
    df = pd.read_csv(csv_path)
    problems, d = validate(df)
    for p in problems:
        print(p)
    if d is None:
        sys.exit(1)
    sx, sy = (1.2, 0.8) if coords == "100" else (1.0, 1.0)
    d = d.sort_values(["match_id", "period", "minute", "second"], kind="stable").reset_index(drop=True)
    os.makedirs(f"{out_dir}/matches", exist_ok=True)
    os.makedirs(f"{out_dir}/ev", exist_ok=True)
    matches = []
    for mid, g in d.groupby("match_id", sort=False):
        g = g.reset_index(drop=True)
        has_p = "possession_id" in g.columns and g.possession_id.notna().all()
        g["_pid"] = g.possession_id.astype(int).values if has_p else derive_possession(g)
        rs = (
            g["restart"].astype(object).where(g["restart"].notna(), None)
            if "restart" in g.columns
            else pd.Series([None] * len(g))
        )
        first = {}
        owner = {}
        for i, r in g.iterrows():
            first.setdefault(r._pid, i)
            if r.event_type in CTRL:
                owner.setdefault(r._pid, r.team)
        evs = []
        for i, r in g.iterrows():
            e = {
                "index": i,
                "period": int(r.period),
                "minute": int(r.minute),
                "second": int(r.second),
                "team": {"name": r.team},
                "possession": int(r._pid),
                "possession_team": {"name": owner.get(r._pid, r.team)},
                "type": {"name": TYPE.get(r.event_type, DEFT.get(r.event_type, "Other"))},
                "location": [None, None] if pd.isna(r.x) else [float(r.x) * sx, float(r.y) * sy],
            }
            rest = rs.iloc[i] if first[r._pid] == i else None
            pp_first = (
                RESTART.get(str(rs.iloc[first[r._pid]]).lower(), "Regular Play")
                if rs.iloc[first[r._pid]] not in (None, "")
                else "Regular Play"
            )
            e["play_pattern"] = {"name": pp_first}
            if r.event_type in ("pass", "carry") and "end_x" in g.columns and pd.notna(r.end_x):
                end = [float(r.end_x) * sx, float(r.end_y) * sy]
                if r.event_type == "pass":
                    L = (
                        float(r.pass_length)
                        if "pass_length" in g.columns and pd.notna(r.pass_length)
                        else float(np.hypot(end[0] - e["location"][0], end[1] - e["location"][1]))
                    )
                    e["pass"] = {"end_location": end, "length": L}
                else:
                    e["carry"] = {"end_location": end}
            elif r.event_type == "pass":
                e["pass"] = {"end_location": e["location"], "length": 0.0}
            elif r.event_type == "carry":
                e["carry"] = {"end_location": e["location"]}
            if r.event_type == "shot":
                e["shot"] = {"outcome": {"name": "Goal" if "shot_goal" in g.columns and r.shot_goal == 1 else "Other"}}
            if (
                r.event_type == "pass"
                and "pass_outcome" in g.columns
                and str(r.pass_outcome).strip().lower() == "incomplete"
            ):
                e["pass"]["outcome"] = {"name": "Incomplete"}
            if r.event_type == "shot" and "xg" in g.columns and pd.notna(r.xg):
                e["shot"]["statsbomb_xg"] = float(r.xg)
            if "player" in g.columns and pd.notna(r.player):
                e["player"] = {"name": str(r.player)}
            if r.event_type == "pass" and "recipient" in g.columns and pd.notna(r.recipient):
                e["pass"]["recipient"] = {"name": str(r.recipient)}
            evs.append(e)
        json.dump(evs, open(f"{out_dir}/ev/{mid}.json", "w", encoding="utf-8"))
        r0 = g.iloc[0]
        matches.append(
            {
                "match_id": mid if not str(mid).isdigit() else int(mid),
                "match_date": str(r0.match_date),
                "home_team": {"home_team_name": r0.home_team},
                "away_team": {"away_team_name": r0.away_team},
            }
        )
    json.dump(matches, open(f"{out_dir}/matches/generic.json", "w", encoding="utf-8"))
    print(f"convertite {len(matches)} partite in {out_dir}")
    return len(problems)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    fl = [x for x in sys.argv[1:] if x.startswith("--")]
    if len(a) < 1:
        sys.exit(__doc__)
    if "--validate-only" in fl:
        pr, _ = validate(pd.read_csv(a[0]))
        print("\n".join(pr) if pr else "nessun problema trovato")
        sys.exit(0)
    if len(a) < 2:
        sys.exit(__doc__)
    convert(a[0], a[1], "120x80" if "--coords" in fl or any("120x80" in x for x in sys.argv) else "100")
