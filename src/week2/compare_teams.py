"""Settimana 2 - confronto descrittivo tra due squadre sulle sole partite di esplorazione (prime 70%).
Uso: python compare_teams.py <matchesA.json> "<SquadraA>" <matchesB.json> "<SquadraB>" [cartella_dati=.]"""

import sys, json, numpy as np

BASE = sys.argv[5] if len(sys.argv) > 5 else "."
out = {}
for mf, team in [(sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])]:
    sys.argv = ["x", mf, team, BASE]
    import importlib, sequences_clustering as S

    importlib.reload(S)
    df, nm = S.extract()
    ex = df[df.gi < int(round(nm * 0.7))]
    rng = np.random.default_rng(0)

    def ci(v):
        v = np.asarray(v, float)
        return [float(x) for x in np.percentile([rng.choice(v, len(v)).mean() for _ in range(1000)], [2.5, 97.5])]

    out[team] = dict(
        partite=int(ex.gi.nunique()),
        sequenze=int(len(ex)),
        quota_costruzione=float((ex.x0 < 45).mean()),
        quota_costruzione_ci=ci((ex.x0 < 45).astype(float)),
        passaggi=float(ex.n_pass.mean()),
        passaggi_ci=ci(ex.n_pass),
        lanci_lunghi=float(ex.long_share.mean()),
        lanci_lunghi_ci=ci(ex.long_share),
        direttezza=float(ex.directness.mean()),
        direttezza_ci=ci(ex.directness),
        durata=float(ex.dur.mean()),
        durata_ci=ci(ex.dur),
        quota_tiro=float(ex.shot.mean()),
        quota_tiro_ci=ci(ex.shot),
        quota_lunghe=float((ex.n_pass >= 10).mean()),
    )
json.dump(out, open(f"{BASE}/L2_confronto_squadre.json", "w"), indent=1)
for t, d in out.items():
    print(t, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items() if not k.endswith("_ci")})
for k in ("quota_costruzione", "passaggi", "lanci_lunghi", "direttezza", "durata", "quota_tiro"):
    print(k, {t: [round(x, 3) for x in d[k + "_ci"]] for t, d in out.items()})
