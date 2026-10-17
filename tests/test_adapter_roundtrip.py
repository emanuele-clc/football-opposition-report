"""Prova dell'adattatore: StatsBomb -> CSV generico -> generic_csv.py -> estrazione delle sequenze, confrontata con l'estrazione diretta.
Uso:  python -X utf8 tests/test_adapter_roundtrip.py <matches.json> "<Squadra>" <cartella_dati> [cartella_lavoro]
Due casi: con possession_id e restart (deve riprodurre le sequenze), senza possession_id (possessioni ricostruite: si misura lo scostamento).
Esce con codice 1 se nel primo caso meno del 99% delle sequenze e' riprodotto o le caratteristiche differiscono."""
import sys, os, tempfile
import numpy as np
here = os.path.dirname(os.path.abspath(__file__)); src = os.path.join(here, "..", "src")
a = sys.argv[1:]
if len(a) < 3: sys.exit(__doc__)
MF, TEAM, BASE = os.path.abspath(a[0]), a[1], os.path.abspath(a[2]); WORK = os.path.abspath(a[3]) if len(a) > 3 else tempfile.mkdtemp(prefix="roundtrip_")
sys.argv = ["x", MF, TEAM, BASE]; sys.path[:0] = [os.path.join(src, "week2"), os.path.join(src, "adapters")]
import sequences_clustering as S, generic_csv as G, statsbomb_to_generic_csv as E
KEY = ["match", "tempo", "minuto", "sec"]; FEAT = ["x0", "y0", "x1", "y1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur", "shot"]

def run(name, possession):
    d = os.path.join(WORK, name); os.makedirs(d, exist_ok=True); csv = os.path.join(d, "events.csv")
    E.export(MF, TEAM, BASE, csv, possession=possession); G.convert(csv, d, "120x80")
    S.MF, S.BASE = os.path.join(d, "matches", "generic.json"), d; df, _ = S.extract(); S.MF, S.BASE = MF, BASE; return df

ref, nm = S.extract(); ref = ref.drop_duplicates(KEY); out = {}; ok = True
for name, poss in (("with_possession_id", True), ("reconstructed", False)):
    df = run(name, poss).drop_duplicates(KEY); m = ref.merge(df, on=KEY, suffixes=("", "_g"))
    diff = max(float(np.abs(m[c].astype(float) - m[c + "_g"].astype(float)).max()) for c in FEAT) if len(m) else np.nan
    same = int((np.abs(m[[c for c in FEAT]].astype(float).values - m[[c + "_g" for c in FEAT]].astype(float).values) < 1e-6).all(1).sum())
    print(f"\n{name}: {len(df)} sequenze (diretto {len(ref)}), ritrovate {len(m)} ({len(m) / len(ref):.1%}), di cui identiche {same}, in piu' {len(df) - len(m)}")
    print(f"  passaggi per sequenza {df.n_pass.mean():.2f} (diretto {ref.n_pass.mean():.2f}) | tiro {df.shot.mean():.1%} (diretto {ref.shot.mean():.1%}) | massima differenza sulle caratteristiche ritrovate {diff:.2g}")
    if poss and (len(m) / len(ref) < 0.99 or same < len(m)): ok = False
print("\nOK" if ok else "\nFALLITO: con possession_id le sequenze non sono riprodotte"); sys.exit(0 if ok else 1)
