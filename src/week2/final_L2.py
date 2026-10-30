"""Week 2 - final L2: clustering in two phases (build-up x0<45 and advanced x0>=45), stability per group, profiles and figure.
Usage: python final_L2.py <matches.json> "<Team>" [data_folder=.]   (needs sequences_clustering.py in the same folder)
Choices made ONLY on the first 70% of matches (exploration), looking at stability and silhouette: to be declared in the thesis (researcher degrees of freedom).
The last matches stay reserved for validation and are not used here."""

import sys, json, collections
import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, ".")
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

CUT = 45
K = {"costruzione": 5, "avanzata": 3}
df, nm = S.extract()
k0 = int(round(nm * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()
ex["w1"] = (ex.y1 - 40).abs()
ex["side0"] = np.where(ex.y0 < 40, "sx", "dx")
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
ex["fase"] = np.where(ex.x0 < CUT, "costruzione", "avanzata")
ex["cl"] = ""
prof = []
stab = {}
for fase, k in K.items():
    sub = ex[ex.fase == fase]
    Xs = StandardScaler().fit_transform(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(Xs)
    lab = km.labels_
    sj, ari, ari_ci = S.jaccard_stability(Xs, lab, k, B=200, seed=1)
    stab[fase] = dict(
        k=k,
        n=int(len(sub)),
        silhouette=float(silhouette_score(Xs, lab)),
        ari=ari,
        ari_ci=ari_ci,
        jaccard=[float(v) for v in sj],
    )
    # ordina i gruppi per x0 medio crescente e poi dimensione
    order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
    rank = {c: i + 1 for i, c in enumerate(order)}
    ex.loc[sub.index, "cl"] = [f"{'C' if fase == 'costruzione' else 'A'}{rank[l]}" for l in lab]
    ex.loc[sub.index, "dist"] = np.linalg.norm(
        Xs - km.cluster_centers_[lab], axis=1
    )  # distance from the group centre (typicality)
    for c in order:
        m = sub[lab == c]
        name = f"{'C' if fase == 'costruzione' else 'A'}{rank[c]}"
        tri = collections.Counter()
        for zs in m.zones:
            zc = [z for i, z in enumerate(zs) if i == 0 or z != zs[i - 1]]  # consecutive equal zones collapsed
            seen = set(tuple(zc[i : i + 3]) for i in range(len(zc) - 2))
            tri.update(seen)
        top = [(" > ".join(S.ZN[z] for z in t), round(n / len(m), 2)) for t, n in tri.most_common(3)]
        pp = m.play_pattern.value_counts(normalize=True).round(2).to_dict()
        prof.append(
            dict(
                cl=name,
                fase=fase,
                n=int(len(m)),
                quota_fase=round(len(m) / len(sub), 2),
                quota_totale=round(len(m) / len(ex), 2),
                jaccard=round(float(sj[c]), 2),
                x0=round(m.x0.mean(), 1),
                x1=round(m.x1.mean(), 1),
                larg_inizio=round(m.w0.mean(), 1),
                larg_fine=round(m.w1.mean(), 1),
                passaggi=round(m.n_pass.mean(), 1),
                lanci_lunghi=round(m.long_share.mean(), 2),
                direttezza=round(m.directness.mean(), 2),
                durata_s=round(m.dur.mean(), 1),
                lato_sx=round((m.side0 == "sx").mean(), 2),
                tiro=round(m.shot.mean(), 3),
                inizio=pp,
                trigrammi=top,
            )
        )
ex.assign(
    zone_percorso=ex.zones.apply(lambda zs: " > ".join(S.ZN[z] for i, z in enumerate(zs) if i == 0 or z != zs[i - 1]))
).drop(columns=["zones", "path"]).to_csv(f"{S.BASE}/L2_sequenze_{S.TEAM.replace(' ','_')}.csv", index=False)
json.dump(
    dict(stabilita=stab, profili=prof, n_sequenze=int(len(ex)), n_partite_esplorazione=int(k0)),
    open(f"{S.BASE}/L2_results_{S.TEAM.replace(' ','_')}.json", "w"),
    indent=1,
    default=float,
)
pd.DataFrame(prof).drop(columns=["inizio", "trigrammi"]).to_csv(
    f"{S.BASE}/L2_profili_{S.TEAM.replace(' ','_')}.csv", index=False
)
for fase in K:
    print(
        fase,
        {
            k: (round(v, 3) if isinstance(v, float) else v)
            for k, v in stab[fase].items()
            if k not in ("jaccard", "ari_ci")
        },
        "Jaccard",
        [round(x, 2) for x in stab[fase]["jaccard"]],
    )
for p in prof:
    print(p)
# figure: 8 mini-pitches with 25 paths per group and the mean arrow
names = [p["cl"] for p in prof]
fig, axs = plt.subplots(2, 5, figsize=(16, 6.4))
rng = np.random.default_rng(0)
for ax in axs.ravel():
    ax.axis("off")
for i, nme in enumerate(names):
    ax = axs[0 if nme[0] == "C" else 1, (int(nme[1]) - 1)]
    ax.axis("on")
    m = ex[ex.cl == nme]
    ax.set_xlim(0, 120)
    ax.set_ylim(80, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#E8F3E8")
    for xx in (60,):
        ax.axvline(xx, color="white", lw=1)
    for p in m.sample(min(25, len(m)), random_state=0).path:
        P = np.array(p)
        ax.plot(P[:, 0], P[:, 1], color="#1F3A5F", alpha=0.18, lw=1)
    ax.annotate(
        "",
        xy=(m.x1.mean(), m.y1.mean()),
        xytext=(m.x0.mean(), m.y0.mean()),
        arrowprops=dict(arrowstyle="->", color="#B3262D", lw=2.4),
    )
    pr = [p for p in prof if p["cl"] == nme][0]
    ax.set_title(f"{nme}  (n={pr['n']}, stabilita' {pr['jaccard']:.2f})", fontsize=9)
plt.suptitle(
    f"{S.TEAM}: famiglie di sequenze (esplorazione). Riga alta: costruzione (inizio nella propria meta' campo). Riga bassa: fase avanzata. Freccia rossa = percorso medio",
    fontsize=10,
)
plt.tight_layout()
plt.savefig(f"{S.BASE}/fig_L2_{S.TEAM.replace(' ','_')}.png", dpi=140)
