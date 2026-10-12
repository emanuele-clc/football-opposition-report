"""Settimana 3 - prove di robustezza del modulo L2 (solo partite di esplorazione, prime 70%).
Uso: python robustness_L2.py <matches.json> "<Squadra>" [cartella_dati=.]   (importa sequences_clustering.py da ../week2)
1) stabilita' con bootstrap sulle PARTITE (non sulle sequenze); 2) sensibilita' al taglio x e a k; 3) K-Means contro mistura gaussiana e Ward;
4) prevedibilita' della famiglia con validazione incrociata per partita (le partite riservate restano intatte)."""
import sys, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore"); import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score, log_loss
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
df, nm = S.extract(); k0 = int(round(nm * 0.7)); ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs(); ex["w1"] = (ex.y1 - 40).abs()
rng = np.random.default_rng(7); out = {"team": S.TEAM, "n_matches_expl": int(k0), "n_seq_expl": int(len(ex))}

def fit_labels(X, k, seed=0): return KMeans(k, n_init=10, random_state=seed).fit(X)
def match_bootstrap(sub, k, B=100):
    """Jaccard per gruppo ricampionando le PARTITE (con reinserimento)."""
    X = StandardScaler().fit_transform(sub[COLS].values); km0 = fit_labels(X, k); lab = km0.labels_
    games = sub.gi.unique(); by = {g: np.where(sub.gi.values == g)[0] for g in games}; sc = np.zeros(k); aris = []
    for _ in range(B):
        gs = rng.choice(games, len(games)); idx = np.concatenate([by[g] for g in gs])
        km = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]); lb = km.predict(X)
        aris.append(adjusted_rand_score(lab, lb))
        for c in range(k):
            a = lab == c; sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return X, lab, sc / B, float(np.mean(aris))

def phase_stats(cut, kb, ka, B=100):
    res = {}
    for fase, k, sub in [("costruzione", kb, ex[ex.x0 < cut]), ("avanzata", ka, ex[ex.x0 >= cut])]:
        if len(sub) < 10 * k: res[fase] = None; continue
        X, lab, sj, ari = match_bootstrap(sub.reset_index(drop=True), k, B)
        res[fase] = dict(n=int(len(sub)), k=k, silhouette=float(silhouette_score(X, lab)), jaccard_mean=float(sj.mean()), jaccard_min=float(sj.min()), ari=ari)
    return res

# 1) stabilita' con bootstrap sulle partite, configurazione scelta (x=45, k=5 e 3), e confronto con il bootstrap sulle sequenze
base = phase_stats(45, 5, 3, B=200); out["match_bootstrap_x45"] = base
for f, v in base.items(): print(f"[match-bootstrap] {f}: n={v['n']} k={v['k']} Jaccard medio {v['jaccard_mean']:.2f} (min {v['jaccard_min']:.2f}) ARI {v['ari']:.2f} silhouette {v['silhouette']:.2f}")
# 2) sensibilita' al taglio
out["cut_sensitivity"] = {}
for cut in (35, 40, 45, 50, 55):
    r = phase_stats(cut, 5, 3, B=60); out["cut_sensitivity"][cut] = r
    print(f"[taglio x={cut}] " + " | ".join(f"{f}: n={v['n']} Jmean {v['jaccard_mean']:.2f} Jmin {v['jaccard_min']:.2f} sil {v['silhouette']:.2f}" if v else f"{f}: troppo pochi" for f, v in r.items()))
# 3) sensibilita' a k (taglio 45)
out["k_sensitivity"] = {}
for kb in (3, 4, 5, 6, 7):
    sub = ex[ex.x0 < 45].reset_index(drop=True); X, lab, sj, ari = match_bootstrap(sub, kb, 60); out["k_sensitivity"][f"costruzione_k{kb}"] = dict(jaccard_mean=float(sj.mean()), jaccard_min=float(sj.min()), silhouette=float(silhouette_score(X, lab)))
    print(f"[k costruzione={kb}] Jmean {sj.mean():.2f} Jmin {sj.min():.2f} sil {silhouette_score(X, lab):.2f}")
for ka in (2, 3, 4, 5):
    sub = ex[ex.x0 >= 45].reset_index(drop=True); X, lab, sj, ari = match_bootstrap(sub, ka, 60); out["k_sensitivity"][f"avanzata_k{ka}"] = dict(jaccard_mean=float(sj.mean()), jaccard_min=float(sj.min()), silhouette=float(silhouette_score(X, lab)))
    print(f"[k avanzata={ka}] Jmean {sj.mean():.2f} Jmin {sj.min():.2f} sil {silhouette_score(X, lab):.2f}")
# 4) K-Means contro mistura gaussiana e Ward (taglio 45, k = 5 e 3)
out["methods"] = {}
for fase, k, sub in [("costruzione", 5, ex[ex.x0 < 45]), ("avanzata", 3, ex[ex.x0 >= 45])]:
    X = StandardScaler().fit_transform(sub[COLS].values); lk = KMeans(k, n_init=10, random_state=0).fit_predict(X)
    lg = GaussianMixture(k, covariance_type="diag", n_init=5, random_state=0).fit(X).predict(X); lw = AgglomerativeClustering(k, linkage="ward").fit_predict(X)
    out["methods"][fase] = dict(sil_kmeans=float(silhouette_score(X, lk)), sil_gmm=float(silhouette_score(X, lg)), sil_ward=float(silhouette_score(X, lw)),
        ari_kmeans_gmm=float(adjusted_rand_score(lk, lg)), ari_kmeans_ward=float(adjusted_rand_score(lk, lw)))
    print(f"[metodi {fase}] silhouette K-Means {silhouette_score(X, lk):.2f}, GMM {silhouette_score(X, lg):.2f}, Ward {silhouette_score(X, lw):.2f} | accordo (ARI) K-Means-GMM {adjusted_rand_score(lk, lg):.2f}, K-Means-Ward {adjusted_rand_score(lk, lw):.2f}")
# 5) prevedibilita' della famiglia: validazione incrociata per partita (6 gruppi), contro la baseline
ex["cl"] = ""
for fase, k, sub in [("costruzione", 5, ex[ex.x0 < 45]), ("avanzata", 3, ex[ex.x0 >= 45])]:
    X = StandardScaler().fit_transform(sub[COLS].values); lab = KMeans(k, n_init=20, random_state=0).fit_predict(X)
    ex.loc[sub.index, "cl"] = [f"{fase[0].upper()}{l}" for l in lab]
ex = ex.sort_values(["gi", "pid"]).reset_index(drop=True); ex["prev_cl"] = ex.groupby("gi").cl.shift(1).fillna("start")
H = lambda c: float(-(np.array(c)[np.array(c) > 0] / np.sum(c) * np.log2(np.array(c)[np.array(c) > 0] / np.sum(c))).sum())
out["pred"] = {}
for fase in ("costruzione", "avanzata"):
    sub = ex[ex.x0 < 45] if fase == "costruzione" else ex[ex.x0 >= 45]; sub = sub.reset_index(drop=True)
    cnt = sub.cl.value_counts().values; out["pred"][fase] = dict(entropy=H(cnt), entropy_max=float(np.log2(len(cnt))))
    Xc = pd.concat([pd.get_dummies(sub.play_pattern, dtype=float), sub[["minuto"]].astype(float) / 90, (sub.tempo == 2).astype(float).rename("t2"), pd.get_dummies(sub.prev_cl, prefix="prev", dtype=float)], axis=1).values
    y = sub.cl.values; g = sub.gi.values; classes = np.unique(y); pm = np.zeros((len(y), len(classes))); pb = np.zeros_like(pm)
    for tr, te in GroupKFold(6).split(Xc, y, g):
        clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xc[tr], y[tr]); p = np.full((len(te), len(classes)), 1e-6); p[:, [list(classes).index(c) for c in clf.classes_]] = clf.predict_proba(Xc[te]); pm[te] = p / p.sum(1, keepdims=True)
        pr = pd.Series(y[tr]).value_counts(normalize=True).reindex(classes).fillna(1e-6).values; pb[te] = pr / pr.sum()
    yi = np.array([list(classes).index(c) for c in y]); lm = -np.log(pm[np.arange(len(y)), yi]); lb = -np.log(pb[np.arange(len(y)), yi]); d = lb - lm
    games = np.unique(g); ci = np.percentile([np.mean(np.concatenate([d[g == gg] for gg in rng.choice(games, len(games))])) for _ in range(1000)], [2.5, 97.5])
    out["pred"][fase].update(logloss_model=float(lm.mean()), logloss_base=float(lb.mean()), gain_mean=float(d.mean()), gain_ci=[float(x) for x in ci],
        acc_model=float((pm.argmax(1) == yi).mean()), acc_base=float((pb.argmax(1) == yi).mean()), n=int(len(y)))
    print(f"[prevedibilita' {fase}] n={len(y)} entropia {H(cnt):.2f} su max {np.log2(len(cnt)):.2f} bit | log-loss modello {lm.mean():.3f}, baseline {lb.mean():.3f}, guadagno {d.mean():.4f} IC95 [{ci[0]:.4f}, {ci[1]:.4f}] | accuratezza modello {(pm.argmax(1)==yi).mean():.2f}, baseline {(pb.argmax(1)==yi).mean():.2f}")
json.dump(out, open(f"{S.BASE}/robustness_{S.TEAM.replace(' ','_')}.json", "w"), indent=1)
