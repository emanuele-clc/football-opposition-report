"""The families of sequences on the exploration matches (first 70%). Three commands:
  final       families in two phases (build-up x0 < 45, k = 5; advanced, k = 3), stability, profiles, figure
              -> L2_results_<Team>.json, L2_profili_<Team>.csv, L2_sequenze_<Team>.csv, fig_L2_<Team>.png
  robustness  how much the families change with another cut, another k, another algorithm; can the family be predicted?
              -> robustness_<Team>.json
  null        are the families more stable than K-Means on data with no groups? (E1) -> null_baseline_<Team>.json
Usage: python families.py final|robustness|null <matches.json> "<Team>" [data_folder=.]
The choices made here (cut 45, k = 5 and 3) were made on the exploration matches only and are declared in the thesis."""

import sys, os, json, collections, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
if len(sys.argv) < 4 or sys.argv[1] not in ("final", "robustness", "null"):
    sys.exit(__doc__)
WHAT = sys.argv[1]
sys.argv = [sys.argv[0]] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
FN = S.TEAM.replace(" ", "_")

# exploration matches only
df, n_matches = S.extract()
k0 = int(round(n_matches * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()  # distance from the middle of the pitch
ex["w1"] = (ex.y1 - 40).abs()


def best_jaccard(labels, new, c, k):
    # how well group c is found again among the new groups
    a = labels == c
    best = 0
    for j in range(k):
        best = max(best, (a & (new == j)).sum() / (a | (new == j)).sum())
    return best


def collapse(zones):
    # A1 A1 B2 B2 C2 -> A1 B2 C2
    out = []
    for z in zones:
        if not out or z != out[-1]:
            out.append(z)
    return out


# ---------------------------------------------------------------- final
def final():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    K = {"costruzione": 5, "avanzata": 3}
    ex["side0"] = np.where(ex.y0 < 40, "sx", "dx")
    ex["fase"] = np.where(ex.x0 < 45, "costruzione", "avanzata")
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
        # names C1, C2, ... (build-up) and A1, A2, ... (advanced), ordered by mean start x, then size
        letter = "C" if phase == "costruzione" else "A"
        order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
        name = {}
        for i, c in enumerate(order):
            name[c] = f"{letter}{i + 1}"
        ex.loc[sub.index, "cl"] = [name[l] for l in lab]
        ex.loc[sub.index, "dist"] = np.linalg.norm(X - km.cluster_centers_[lab], axis=1)  # how typical the sequence is

        for c in order:
            m = sub[lab == c]
            # the 3 most common runs of 3 zones (each counted once per sequence)
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

    paths = [" > ".join(S.ZN[z] for z in collapse(zs)) for zs in ex.zones]
    ex.assign(zone_percorso=paths).drop(columns=["zones", "path"]).to_csv(f"{S.BASE}/L2_sequenze_{FN}.csv", index=False)
    result = {"stabilita": stability, "profili": profiles, "n_sequenze": int(len(ex)), "n_partite_esplorazione": int(k0)}
    json.dump(result, open(f"{S.BASE}/L2_results_{FN}.json", "w"), indent=1, default=float)
    pd.DataFrame(profiles).drop(columns=["inizio", "trigrammi"]).to_csv(f"{S.BASE}/L2_profili_{FN}.csv", index=False)
    for phase in K:
        st = stability[phase]
        print(phase, "k", st["k"], "n", st["n"], "silhouette", round(st["silhouette"], 3), "Jaccard", [round(x, 2) for x in st["jaccard"]])

    # figure: one small pitch per family, 25 example paths and the mean arrow (red)
    fig, axs = plt.subplots(2, 5, figsize=(16, 6.4))
    for ax in axs.ravel():
        ax.axis("off")
    for p in profiles:
        fam = p["cl"]
        ax = axs[0 if fam[0] == "C" else 1, int(fam[1]) - 1]
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
        ax.annotate("", xy=(m.x1.mean(), m.y1.mean()), xytext=(m.x0.mean(), m.y0.mean()), arrowprops=dict(arrowstyle="->", color="#B3262D", lw=2.4))
        ax.set_title(f"{fam}  (n={p['n']}, stabilita' {p['jaccard']:.2f})", fontsize=9)
    plt.suptitle(
        f"{S.TEAM}: famiglie di sequenze (esplorazione). Riga alta: costruzione (inizio nella propria meta' campo). Riga bassa: fase avanzata. Freccia rossa = percorso medio",
        fontsize=10,
    )
    plt.tight_layout()
    plt.savefig(f"{S.BASE}/fig_L2_{FN}.png", dpi=140)


# ---------------------------------------------------------------- robustness
def robustness():
    rng = np.random.default_rng(7)
    out = {"team": S.TEAM, "n_matches_expl": int(k0), "n_seq_expl": int(len(ex))}

    def match_bootstrap(sub, k, B):
        # Jaccard of each group and ARI, resampling whole matches
        X = StandardScaler().fit_transform(sub[COLS].values)
        labels = KMeans(k, n_init=10, random_state=0).fit(X).labels_
        games = sub.gi.unique()
        rows_of = {g: np.where(sub.gi.values == g)[0] for g in games}
        score = np.zeros(k)
        aris = []
        for _ in range(B):
            idx = np.concatenate([rows_of[g] for g in rng.choice(games, len(games))])
            new = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
            aris.append(adjusted_rand_score(labels, new))
            for c in range(k):
                score[c] += best_jaccard(labels, new, c, k)
        return X, labels, score / B, float(np.mean(aris))

    def both_phases(cut, kb, ka, B):
        res = {}
        for phase, k, sub in [("costruzione", kb, ex[ex.x0 < cut]), ("avanzata", ka, ex[ex.x0 >= cut])]:
            if len(sub) < 10 * k:
                res[phase] = None
                continue
            X, labels, jac, ari = match_bootstrap(sub.reset_index(drop=True), k, B)
            res[phase] = {
                "n": int(len(sub)),
                "k": k,
                "silhouette": float(silhouette_score(X, labels)),
                "jaccard_mean": float(jac.mean()),
                "jaccard_min": float(jac.min()),
                "ari": ari,
            }
        return res

    # 1) stability of the chosen setting (cut 45, k = 5 and 3)
    out["match_bootstrap_x45"] = both_phases(45, 5, 3, B=200)
    for phase, v in out["match_bootstrap_x45"].items():
        print(f"[match-bootstrap] {phase}: n={v['n']} k={v['k']} Jaccard medio {v['jaccard_mean']:.2f} (min {v['jaccard_min']:.2f}) ARI {v['ari']:.2f} silhouette {v['silhouette']:.2f}")

    # 2) other cuts
    out["cut_sensitivity"] = {}
    for cut in (35, 40, 45, 50, 55):
        out["cut_sensitivity"][cut] = both_phases(cut, 5, 3, B=60)
        print(f"[taglio x={cut}]", out["cut_sensitivity"][cut])

    # 3) other k (cut 45)
    out["k_sensitivity"] = {}
    for phase, ks in (("costruzione", (3, 4, 5, 6, 7)), ("avanzata", (2, 3, 4, 5))):
        if phase == "costruzione":
            sub = ex[ex.x0 < 45].reset_index(drop=True)
        else:
            sub = ex[ex.x0 >= 45].reset_index(drop=True)
        for k in ks:
            X, labels, jac, ari = match_bootstrap(sub, k, 60)
            sil = float(silhouette_score(X, labels))
            out["k_sensitivity"][f"{phase}_k{k}"] = {"jaccard_mean": float(jac.mean()), "jaccard_min": float(jac.min()), "silhouette": sil}
            print(f"[k {phase}={k}] Jmean {jac.mean():.2f} Jmin {jac.min():.2f} sil {sil:.2f}")

    # 4) K-Means against Gaussian mixture and Ward
    out["methods"] = {}
    for phase, k, sub in [("costruzione", 5, ex[ex.x0 < 45]), ("avanzata", 3, ex[ex.x0 >= 45])]:
        X = StandardScaler().fit_transform(sub[COLS].values)
        lk = KMeans(k, n_init=10, random_state=0).fit_predict(X)
        lg = GaussianMixture(k, covariance_type="diag", n_init=5, random_state=0).fit(X).predict(X)
        lw = AgglomerativeClustering(k, linkage="ward").fit_predict(X)
        out["methods"][phase] = {
            "sil_kmeans": float(silhouette_score(X, lk)),
            "sil_gmm": float(silhouette_score(X, lg)),
            "sil_ward": float(silhouette_score(X, lw)),
            "ari_kmeans_gmm": float(adjusted_rand_score(lk, lg)),
            "ari_kmeans_ward": float(adjusted_rand_score(lk, lw)),
        }
        print(f"[metodi {phase}]", out["methods"][phase])

    # 5) can the family be predicted? cross-validation by match against the family shares
    ex["cl"] = ""
    for phase, k, sub in [("costruzione", 5, ex[ex.x0 < 45]), ("avanzata", 3, ex[ex.x0 >= 45])]:
        X = StandardScaler().fit_transform(sub[COLS].values)
        labels = KMeans(k, n_init=20, random_state=0).fit_predict(X)
        ex.loc[sub.index, "cl"] = [f"{phase[0].upper()}{l}" for l in labels]
    data = ex.sort_values(["gi", "pid"]).reset_index(drop=True)
    data["prev_cl"] = data.groupby("gi").cl.shift(1).fillna("start")

    def entropy(counts):
        p = np.array(counts)[np.array(counts) > 0] / np.sum(counts)
        return float(-(p * np.log2(p)).sum())

    out["pred"] = {}
    for phase in ("costruzione", "avanzata"):
        if phase == "costruzione":
            sub = data[data.x0 < 45].reset_index(drop=True)
        else:
            sub = data[data.x0 >= 45].reset_index(drop=True)
        counts = sub.cl.value_counts().values
        out["pred"][phase] = {"entropy": entropy(counts), "entropy_max": float(np.log2(len(counts)))}
        X = pd.concat(
            [
                pd.get_dummies(sub.play_pattern, dtype=float),
                sub[["minuto"]].astype(float) / 90,
                (sub.tempo == 2).astype(float).rename("t2"),
                pd.get_dummies(sub.prev_cl, prefix="prev", dtype=float),
            ],
            axis=1,
        ).values
        y = sub.cl.values
        g = sub.gi.values
        classes = list(np.unique(y))
        p_model = np.zeros((len(y), len(classes)))
        p_base = np.zeros_like(p_model)
        for tr, te in GroupKFold(6).split(X, y, g):
            clf = LogisticRegression(max_iter=2000, C=0.5).fit(X[tr], y[tr])
            p = np.full((len(te), len(classes)), 1e-6)
            p[:, [classes.index(c) for c in clf.classes_]] = clf.predict_proba(X[te])
            p_model[te] = p / p.sum(1, keepdims=True)
            shares = pd.Series(y[tr]).value_counts(normalize=True).reindex(classes).fillna(1e-6).values
            p_base[te] = shares / shares.sum()
        yi = np.array([classes.index(c) for c in y])
        loss_model = -np.log(p_model[np.arange(len(y)), yi])
        loss_base = -np.log(p_base[np.arange(len(y)), yi])
        d = loss_base - loss_model
        games = np.unique(g)
        means = []
        for _ in range(1000):
            means.append(np.mean(np.concatenate([d[g == x] for x in rng.choice(games, len(games))])))
        ci = np.percentile(means, [2.5, 97.5])
        out["pred"][phase].update(
            logloss_model=float(loss_model.mean()),
            logloss_base=float(loss_base.mean()),
            gain_mean=float(d.mean()),
            gain_ci=[float(x) for x in ci],
            acc_model=float((p_model.argmax(1) == yi).mean()),
            acc_base=float((p_base.argmax(1) == yi).mean()),
            n=int(len(y)),
        )
        print(f"[prevedibilita' {phase}] guadagno {d.mean():.4f} IC95 [{ci[0]:.4f}, {ci[1]:.4f}]")
    json.dump(out, open(f"{S.BASE}/robustness_{FN}.json", "w"), indent=1)


# ---------------------------------------------------------------- null
def null():
    # the same bootstrap on the real data and on two data sets without groups:
    # null_shuffle = every feature shuffled on its own; null_gauss = Gaussian data with the same mean and covariance
    rng = np.random.default_rng(11)

    def stability(X, g, k, B=100):
        labels = KMeans(k, n_init=10, random_state=0).fit(X).labels_
        games = np.unique(g)
        rows_of = {x: np.where(g == x)[0] for x in games}
        score = np.zeros(k)
        for _ in range(B):
            idx = np.concatenate([rows_of[x] for x in rng.choice(games, len(games))])
            new = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
            for c in range(k):
                score[c] += best_jaccard(labels, new, c, k)
        score = score / B
        return float(score.mean()), float(score.min()), float(silhouette_score(X, labels))

    out = {}
    for phase, k in [("costruzione", 5), ("avanzata", 3)]:
        if phase == "costruzione":
            sub = ex[ex.x0 < 45].reset_index(drop=True)
        else:
            sub = ex[ex.x0 >= 45].reset_index(drop=True)
        g = sub.gi.values
        X = StandardScaler().fit_transform(sub[COLS].values)
        res = {}
        res["osservato"] = stability(X, g, k)
        shuffled = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])])
        res["null_shuffle"] = stability(shuffled, g, k)
        gauss = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X))
        res["null_gauss"] = stability(gauss, g, k)
        out[phase] = {}
        for name, (jmean, jmin, sil) in res.items():
            out[phase][name] = {"jaccard_mean": jmean, "jaccard_min": jmin, "silhouette": sil}
            print(f"[{phase} k={k}] {name}: J {jmean:.2f} (min {jmin:.2f}) sil {sil:.2f}")
    json.dump(out, open(f"{S.BASE}/null_baseline_{FN}.json", "w"), indent=1)


if WHAT == "final":
    final()
elif WHAT == "robustness":
    robustness()
else:
    null()
