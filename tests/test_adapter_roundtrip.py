"""Prova dell'adattatore: StatsBomb -> CSV generico -> generic_csv.py -> estrazione delle sequenze, confrontata con l'estrazione diretta.
Uso:  python -X utf8 tests/test_adapter_roundtrip.py <matches.json> "<Squadra>" <cartella_dati> [cartella_lavoro]
Due casi: con possession_id e restart (deve riprodurre le sequenze), senza possession_id (possessioni ricostruite: si misura lo scostamento).
Controlla anche le schede uscite da fermo, palle inattive (con nomi dei giocatori e xG) e transizioni.
Esce con codice 1 se nel primo caso meno del 99% delle sequenze/azioni e' riprodotto o le caratteristiche differiscono."""

import sys, os, tempfile
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "src")
a = sys.argv[1:]
if len(a) < 3:
    sys.exit(__doc__)
MF, TEAM, BASE = os.path.abspath(a[0]), a[1], os.path.abspath(a[2])
WORK = os.path.abspath(a[3]) if len(a) > 3 else tempfile.mkdtemp(prefix="roundtrip_")
sys.argv = ["x", MF, TEAM, BASE]
sys.path[:0] = [os.path.join(src, "week2"), os.path.join(src, "adapters"), os.path.join(src, "report")]
import sequences_clustering as S, generic_csv as G, statsbomb_to_generic_csv as E, restarts as RS, setpieces as SP, transitions as TR

KEY = ["match", "tempo", "minuto", "sec"]
FEAT = ["x0", "y0", "x1", "y1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur", "shot"]


def run(name, possession):
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    csv = os.path.join(d, "events.csv")
    E.export(MF, TEAM, BASE, csv, possession=possession)
    G.convert(csv, d, "120x80")
    out = {}
    for M in (S, RS, SP, TR):
        M.MF, M.BASE = os.path.join(d, "matches", "generic.json"), d
        out[M.__name__] = M.extract()[:2] if M is TR else M.extract()[0]
        M.MF, M.BASE = MF, BASE
    return out


ref, nm = S.extract()
ref = ref.drop_duplicates(KEY)
ok = True
ref_rs, ref_sp = RS.extract()[0], SP.extract()[0]
ref_tl, ref_tr = TR.extract()[:2]
for name, poss in (("with_possession_id", True), ("reconstructed", False)):
    o = run(name, poss)
    df = o["sequences_clustering"].drop_duplicates(KEY)
    m = ref.merge(df, on=KEY, suffixes=("", "_g"))
    diff = max(float(np.abs(m[c].astype(float) - m[c + "_g"].astype(float)).max()) for c in FEAT) if len(m) else np.nan
    same = int(
        (np.abs(m[[c for c in FEAT]].astype(float).values - m[[c + "_g" for c in FEAT]].astype(float).values) < 1e-6)
        .all(1)
        .sum()
    )
    print(
        f"\n{name}: {len(df)} sequenze (diretto {len(ref)}), ritrovate {len(m)} ({len(m) / len(ref):.1%}), di cui identiche {same}, in piu' {len(df) - len(m)}"
    )
    print(
        f"  passaggi per sequenza {df.n_pass.mean():.2f} (diretto {ref.n_pass.mean():.2f}) | tiro {df.shot.mean():.1%} (diretto {ref.shot.mean():.1%}) | massima differenza sulle caratteristiche ritrovate {diff:.2g}"
    )
    if poss and (len(m) / len(ref) < 0.99 or same < len(m)):
        ok = False
    for lab, a_, b_, cols in (
        (
            "uscite da fermo",
            ref_rs,
            o["restarts"],
            ["kind", "short", "side", "opp_half", "final_third", "shot", "lost_own_half", "receiver"],
        ),
        ("palle inattive", ref_sp, o["setpieces"], ["kind", "zone", "shot", "goal", "xg", "taker", "receiver"]),
        ("perdite", ref_tl, o["transitions"][0], ["x", "y", "regain5", "conceded10"]),
        ("recuperi", ref_tr, o["transitions"][1], ["x", "y", "shot10", "shot", "final_third"]),
    ):
        k2 = ["match", "tempo", "minuto", "sec"]
        mm = a_.merge(b_, on=k2, suffixes=("", "_g"))
        eq = int(sum(all((str(r[c]) == str(r[c + "_g"])) for c in cols) for _, r in mm.iterrows()))
        print(f"  {lab}: {len(b_)} (diretto {len(a_)}), ritrovate {len(mm)}, identiche in tutte le colonne {eq}")
        if poss and (len(mm) / max(len(a_), 1) < 0.99 or eq / max(len(mm), 1) < 0.99):
            ok = False
print("\nOK" if ok else "\nFALLITO: con possession_id le sequenze non sono riprodotte")
sys.exit(0 if ok else 1)
