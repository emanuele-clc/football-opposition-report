"""Week 4 - validation on the reserved matches (last 30%): H1, H2 and H3. Protocol: docs/protocol_replication.md.
Usage: python validate_replication.py <matches.json> "<Team>" [data_folder=.] --confirm [--no-h3]
       python validate_replication.py <matches.json> "<Team>" [data_folder=.] --dry-run   (only exploration matches, to test the code)
Families are fitted on the exploration matches and then frozen. Run it once, after committing the protocol.
--no-h3: H1 and H2 only, as for the first two teams (Leverkusen, Leicester; protocol docs/protocol_holdout.md), validated before H3 existed.
Until 6 Nov 2026 that was a separate file, validate_holdout.py, with the same code."""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
# thresholds written in the protocol
SHARE_MAX_DRIFT = 0.10
SIL_MIN = 0.10
B = 1000


def boot_ci(d, g, rng):
    # 95% interval of the mean of d, resampling whole matches (g = match of each sequence)
    games = np.unique(g)
    means = []
    for _ in range(B):
        pick = rng.choice(games, len(games))
        means.append(np.mean(np.concatenate([d[g == x] for x in pick])))
    return np.percentile(means, (2.5, 97.5))


def logloss_shot(p, y):
    return -np.log(np.where(y == 1, p, 1 - p))


def run(with_h3, protocol):
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    dry = "--dry-run" in flags
    if not dry and "--confirm" not in flags:
        sys.exit(f"Refusing to open the reserved matches without --confirm. First commit {protocol}, then rerun with --confirm.")

    sys.argv = [sys.argv[0]] + args
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
    import sequences_clustering as S
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score, adjusted_rand_score
    from sklearn.linear_model import LogisticRegression

    df, n_matches = S.extract()
    k0 = int(round(n_matches * 0.7))
    if dry:
        # dry run: split the exploration matches again 70/30
        k1 = int(round(k0 * 0.7))
        train = df[df.gi < k1].copy()
        test = df[(df.gi >= k1) & (df.gi < k0)].copy()
    else:
        train = df[df.gi < k0].copy()
        test = df[df.gi >= k0].copy()
    for d in (train, test):
        d["w0"] = (d.y0 - 40).abs()
        d["w1"] = (d.y1 - 40).abs()

    def in_phase(d, phase):
        if phase == "costruzione":
            return d.x0 < CUT
        return d.x0 >= CUT

    # fit the families on the training matches only
    models = {}
    for phase, k in K.items():
        sub = train[in_phase(train, phase)]
        scaler = StandardScaler().fit(sub[COLS].values)
        km = KMeans(k, n_init=20, random_state=0).fit(scaler.transform(sub[COLS].values))
        # number the families by mean start x (then by size)
        lab = km.labels_
        order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
        rank = {}
        for i, c in enumerate(order):
            rank[c] = i + 1
        models[phase] = (scaler, km, rank)

    def assign(d):
        d["cl"] = ""
        for phase, (scaler, km, rank) in models.items():
            m = in_phase(d, phase)
            if m.sum():
                letter = "C" if phase == "costruzione" else "A"
                labels = km.predict(scaler.transform(d.loc[m, COLS].values))
                d.loc[m, "cl"] = [f"{letter}{rank[l]}" for l in labels]
        d = d.sort_values(["gi", "pid"]).reset_index(drop=True)
        d["prev_cl"] = d.groupby("gi").cl.shift(1).fillna("start")
        return d

    train = assign(train)
    test = assign(test)

    def context(d, cols=None):
        # what the model knows: play pattern, minute, half, previous family
        X = pd.concat(
            [
                pd.get_dummies(d.play_pattern, dtype=float),
                d[["minuto"]].astype(float) / 90,
                (d.tempo == 2).astype(float).rename("t2"),
                pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
            ],
            axis=1,
        )
        if cols is None:
            return X
        return X.reindex(columns=cols, fill_value=0.0)

    rng = np.random.default_rng(2026)
    out = {
        "team": S.TEAM,
        "modo": "DRY-RUN (solo esplorazione)" if dry else "VALIDAZIONE RISERVATE",
        "partite_train": int(train.gi.nunique()),
        "partite_test": int(test.gi.nunique()),
        "n_seq_train": int(len(train)),
        "n_seq_test": int(len(test)),
    }
    for phase, k in K.items():
        a = train[in_phase(train, phase)].reset_index(drop=True)
        b = test[in_phase(test, phase)].reset_index(drop=True)
        scaler, km, rank = models[phase]
        r = {"n_train": int(len(a)), "n_test": int(len(b))}

        # H2: same family shares on new matches, and the frozen families still separate the data
        fam = sorted(a.cl.unique())
        share_a = a.cl.value_counts(normalize=True).reindex(fam).fillna(0)
        share_b = b.cl.value_counts(normalize=True).reindex(fam).fillna(0)
        r["quote_train"] = share_a.round(3).to_dict()
        r["quote_test"] = share_b.round(3).to_dict()
        r["max_scarto_quote"] = float((share_a - share_b).abs().max())
        if b.cl.nunique() > 1:
            r["silhouette_congelata_test"] = float(silhouette_score(scaler.transform(b[COLS].values), b.cl.values))
        else:
            r["silhouette_congelata_test"] = None
        refit = KMeans(k, n_init=20, random_state=0).fit_predict(StandardScaler().fit_transform(b[COLS].values))
        r["ari_riadattamento_descrittivo"] = float(adjusted_rand_score(b.cl.values, refit))
        sil = r["silhouette_congelata_test"]
        r["H2_pass"] = bool(r["max_scarto_quote"] <= SHARE_MAX_DRIFT and sil is not None and sil >= SIL_MIN)

        # H1: does the context predict the family better than the family shares alone?
        Xa = context(a)
        Xb = context(b, Xa.columns)
        classes = list(np.unique(a.cl.values))
        clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, a.cl.values)
        p = np.full((len(b), len(classes)), 1e-6)
        p[:, [classes.index(c) for c in clf.classes_]] = clf.predict_proba(Xb.values)
        p /= p.sum(1, keepdims=True)
        base = pd.Series(a.cl.values).value_counts(normalize=True).reindex(classes).fillna(1e-6).values
        base = base / base.sum()
        yi = np.array([classes.index(c) for c in b.cl.values])
        loss_model = -np.log(p[np.arange(len(b)), yi])
        loss_base = -np.log(base[yi])
        gain = loss_base - loss_model
        g = b.gi.values
        ci = boot_ci(gain, g, rng)
        r["logloss_modello"] = float(loss_model.mean())
        r["logloss_baseline"] = float(loss_base.mean())
        r["guadagno"] = float(gain.mean())
        r["guadagno_ci95"] = [float(ci[0]), float(ci[1])]
        r["accuratezza_modello"] = float((p.argmax(1) == yi).mean())
        r["accuratezza_baseline"] = float((base.argmax() == yi).mean())
        r["H1_pass"] = bool(ci[0] > 0)
        out[phase] = r
        print(
            f"[{phase}] test: {len(b)} seq, {len(np.unique(g))} partite | H1 guadagno {gain.mean():+.3f} IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}] -> {'PASS' if ci[0] > 0 else 'NON confermato'} | "
            f"H2 scarto quote max {r['max_scarto_quote']:.2f}, silhouette {sil:.2f} -> {'PASS' if r['H2_pass'] else 'NON confermato'} | ARI riadattamento {r['ari_riadattamento_descrittivo']:.2f}"
        )
        if not with_h3:
            continue

        # H3: knowing the family helps to predict a shot (compared with the overall shot rate)
        ya = a.shot.astype(int).values
        yb = b.shot.astype(int).values
        Fa = pd.get_dummies(a.cl, dtype=float)
        Fb = pd.get_dummies(b.cl, dtype=float).reindex(columns=Fa.columns, fill_value=0.0)
        p0 = float(np.clip(ya.mean(), 1e-6, 1 - 1e-6))
        p_fam = LogisticRegression(max_iter=2000, C=0.5).fit(Fa.values, ya).predict_proba(Fb.values)[:, 1]
        p_fam = np.clip(p_fam, 1e-6, 1 - 1e-6)
        gain_fam = logloss_shot(p0, yb) - logloss_shot(p_fam, yb)
        # descriptive: the same with the raw features instead of the families
        raw = LogisticRegression(max_iter=2000, C=0.5).fit(scaler.transform(a[COLS].values), ya)
        p_raw = np.clip(raw.predict_proba(scaler.transform(b[COLS].values))[:, 1], 1e-6, 1 - 1e-6)
        gain_raw = logloss_shot(p0, yb) - logloss_shot(p_raw, yb)
        ci3 = boot_ci(gain_fam, g, np.random.default_rng(2027))
        r["tiro_train"] = a.groupby("cl").shot.mean().round(3).to_dict()
        r["tiro_test"] = b.groupby("cl").shot.mean().round(3).to_dict()
        r["H3_guadagno"] = float(gain_fam.mean())
        r["H3_ci95"] = [float(ci3[0]), float(ci3[1])]
        r["H3_pass"] = bool(ci3[0] > 0)
        r["guadagno_modello_feature_descrittivo"] = float(gain_raw.mean())
        print(
            f"[{phase}] H3 tiro: guadagno famiglie {gain_fam.mean():+.4f} IC95 [{ci3[0]:+.4f}, {ci3[1]:+.4f}] -> {'PASS' if ci3[0] > 0 else 'NON confermato'} | (descrittivo) modello sulle feature grezze {gain_raw.mean():+.4f} | tiro per famiglia test {r['tiro_test']}"
        )

    fn = f"{S.BASE}/{'dryrun' if dry else 'holdout'}_{S.TEAM.replace(' ', '_')}.json"
    json.dump(out, open(fn, "w"), indent=1, default=float)
    print("salvato", fn)


if __name__ == "__main__":
    if "--no-h3" in sys.argv:
        run(with_h3=False, protocol="docs/protocol_holdout.md")
    else:
        run(with_h3=True, protocol="docs/protocol_replication.md")
