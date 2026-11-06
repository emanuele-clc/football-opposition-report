"""Week 2 - final L2 method: families in two phases (build-up x0 < 45, advanced x0 >= 45), their stability, profiles and a figure.
Usage: python final_L2.py <matches.json> "<Team>" [data_folder=.]
Only the exploration matches (first 70%) are used here; the choices made on them are declared in the thesis.
Writes L2_results_<Team>.json, L2_profili_<Team>.csv, L2_sequenze_<Team>.csv and fig_L2_<Team>.png in the data folder."""

import sys, os, json, collections
import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

CUT = 45
K = {"costruzione": 5, "avanzata": 3}
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
FN = S.TEAM.replace(" ", "_")


def collapse(zones):
    # A1 A1 B2 B2 C2 -> A1 B2 C2
    out = []
    for z in zones:
        if not out or z != out[-1]:
            out.append(z)
    return out


df, n_matches = S.extract()
k0 = int(round(n_matches * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()  # distance from the middle of the pitch
ex["w1"] = (ex.y1 - 40).abs()
ex["side0"] = np.where(ex.y0 < 40, "sx", "dx")
ex["fase"] = np.where(ex.x0 < CUT, "costruzione", "avanzata")
ex["cl"] = ""

profiles = []
stability = {}
for phase, k in K.items():
    sub = ex[ex.fase == phase]
    X = StandardScaler().fit_transform(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(X)
    lab = km.labels_
    jac, ari, ari_ci = S.jaccard_stability(X, lab, k, B=200, seed=1)
    stability[phase] = {
        "k": k,
        "n": int(len(sub)),
        "silhouette": float(silhouette_score(X, lab)),
        "ari": ari,
        "ari_ci": ari_ci,
        "jaccard": [float(v) for v in jac],
    }

    # name the families by mean start x (then by size): C1, C2, ... for build-up, A1, A2, ... for advanced
    letter = "C" if phase == "costruzione" else "A"
    order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
    name = {}
    for i, c in enumerate(order):
        name[c] = f"{letter}{i + 1}"
    ex.loc[sub.index, "cl"] = [name[l] for l in lab]
    ex.loc[sub.index, "dist"] = np.linalg.norm(X - km.cluster_centers_[lab], axis=1)  # how typical the sequence is

    for c in order:
        m = sub[lab == c]
        # most common runs of 3 zones (each counted once per sequence)
        trigrams = collections.Counter()
        for zs in m.zones:
            zc = collapse(zs)
            seen = set()
            for i in range(len(zc) - 2):
                seen.add(tuple(zc[i : i + 3]))
            trigrams.update(seen)
        top = []
        for t, n in trigrams.most_common(3):
            top.append((" > ".join(S.ZN[z] for z in t), round(n / len(m), 2)))

        profiles.append(
            {
                "cl": name[c],
                "fase": phase,
                "n": int(len(m)),
                "quota_fase": round(len(m) / len(sub), 2),
                "quota_totale": round(len(m) / len(ex), 2),
                "jaccard": round(float(jac[c]), 2),
                "x0": round(m.x0.mean(), 1),
                "x1": round(m.x1.mean(), 1),
                "larg_inizio": round(m.w0.mean(), 1),
                "larg_fine": round(m.w1.mean(), 1),
                "passaggi": round(m.n_pass.mean(), 1),
                "lanci_lunghi": round(m.long_share.mean(), 2),
                "direttezza": round(m.directness.mean(), 2),
                "durata_s": round(m.dur.mean(), 1),
                "lato_sx": round((m.side0 == "sx").mean(), 2),
                "tiro": round(m.shot.mean(), 3),
                "inizio": m.play_pattern.value_counts(normalize=True).round(2).to_dict(),
                "trigrammi": top,
            }
        )

# files
paths = [" > ".join(S.ZN[z] for z in collapse(zs)) for zs in ex.zones]
ex.assign(zone_percorso=paths).drop(columns=["zones", "path"]).to_csv(f"{S.BASE}/L2_sequenze_{FN}.csv", index=False)
result = {"stabilita": stability, "profili": profiles, "n_sequenze": int(len(ex)), "n_partite_esplorazione": int(k0)}
json.dump(result, open(f"{S.BASE}/L2_results_{FN}.json", "w"), indent=1, default=float)
pd.DataFrame(profiles).drop(columns=["inizio", "trigrammi"]).to_csv(f"{S.BASE}/L2_profili_{FN}.csv", index=False)

for phase in K:
    st = stability[phase]
    print(phase, "k", st["k"], "n", st["n"], "silhouette", round(st["silhouette"], 3), "ARI", round(st["ari"], 3), "Jaccard", [round(x, 2) for x in st["jaccard"]])
for p in profiles:
    print(p)

# figure: one small pitch per family, 25 example paths and the mean arrow (red)
fig, axs = plt.subplots(2, 5, figsize=(16, 6.4))
for ax in axs.ravel():
    ax.axis("off")
for p in profiles:
    fam = p["cl"]
    row = 0 if fam[0] == "C" else 1
    ax = axs[row, int(fam[1]) - 1]
    ax.axis("on")
    ax.set_xlim(0, 120)
    ax.set_ylim(80, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#E8F3E8")
    ax.axvline(60, color="white", lw=1)
    m = ex[ex.cl == fam]
    for path in m.sample(min(25, len(m)), random_state=0).path:
        P = np.array(path)
        ax.plot(P[:, 0], P[:, 1], color="#1F3A5F", alpha=0.18, lw=1)
    ax.annotate(
        "",
        xy=(m.x1.mean(), m.y1.mean()),
        xytext=(m.x0.mean(), m.y0.mean()),
        arrowprops=dict(arrowstyle="->", color="#B3262D", lw=2.4),
    )
    ax.set_title(f"{fam}  (n={p['n']}, stabilita' {p['jaccard']:.2f})", fontsize=9)
plt.suptitle(
    f"{S.TEAM}: famiglie di sequenze (esplorazione). Riga alta: costruzione (inizio nella propria meta' campo). Riga bassa: fase avanzata. Freccia rossa = percorso medio",
    fontsize=10,
)
plt.tight_layout()
plt.savefig(f"{S.BASE}/fig_L2_{FN}.png", dpi=140)
