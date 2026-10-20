"""Settimana 1 - fattibilita': calci d'angolo del Bayer Leverkusen 2023/24 (StatsBomb Open Data, con 360).
Dati: StatsBomb Open Data (licenza non commerciale, citare StatsBomb). Eseguire dopo aver scaricato eventi e frame 360
nelle cartelle ev/ e t360/ (vedi download_data.py)."""

import json, math, collections, sys
import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression

BASE = sys.argv[1] if len(sys.argv) > 1 else "."
TEAM = "Bayer Leverkusen"
rng = np.random.default_rng(42)
matches = sorted(json.load(open(f"{BASE}/matches/9_281.json", encoding="utf-8")), key=lambda g: g["match_date"])


def zone(end, y0):
    ex, ey = end[0], end[1]
    d = ey if y0 < 40 else 80 - ey  # distanza laterale dell'arrivo dal lato del battitore
    if ex < 102 or d < 18:
        return "corto/fuori area"
    if d < 30:
        return "primo palo"
    if d <= 50:
        return "centro"
    return "secondo palo"


rows = []
for gi, g in enumerate(matches):
    mid = g["match_id"]
    ev = json.load(open(f"{BASE}/ev/{mid}.json", encoding="utf-8"))
    fr = {d["event_uuid"]: d for d in json.load(open(f"{BASE}/t360/{mid}.json", encoding="utf-8"))}
    score = {"L": 0, "O": 0}
    for i, e in enumerate(ev):
        t = e["team"]["name"]
        ty = e["type"]["name"]
        if ty == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            score["L" if t == TEAM else "O"] += 1
        if ty == "Own Goal Against":
            score["O" if t == TEAM else "L"] += 1
        if (
            ty == "Pass"
            and t == TEAM
            and e["pass"].get("type", {}).get("name") == "Corner"
            and "end_location" in e["pass"]
        ):
            y = e["location"][1]
            d = y if y < 40 else 80 - y
            xg = sum(
                s["shot"].get("statsbomb_xg", 0)
                for s in ev[i + 1 :]
                if s["possession"] == e["possession"] and s["team"]["name"] == TEAM and s["type"]["name"] == "Shot"
            )
            r = dict(
                g=gi,
                minute=e["minute"],
                period=e["period"],
                diff=score["L"] - score["O"],
                side=int(y < 40),
                zone=zone(e["pass"]["end_location"], y),
                xg=xg,
                has360=0,
                n_opp_near=np.nan,
                n_opp_far=np.nan,
                n_att=np.nan,
                n_opp_box=np.nan,
            )
            d360 = fr.get(e["id"])
            if d360:
                ff = d360["freeze_frame"]
                r["has360"] = 1

                def ind(p):
                    px, py = p["location"]
                    dd = py if y < 40 else 80 - py
                    return px >= 102 and 18 <= py <= 62, dd

                near = far = att = opp = 0
                for p in ff:
                    inbox, dd = ind(p)
                    if not inbox:
                        continue
                    if p["teammate"]:
                        att += 1
                    elif not p["keeper"]:
                        opp += 1
                        if dd < 40:
                            near += 1
                        else:
                            far += 1
                r.update(n_opp_near=near, n_opp_far=far, n_att=att, n_opp_box=opp)
            rows.append(r)
df = pd.DataFrame(rows)
res = {"n_corner": len(df), "n_corner_360": int(df.has360.sum())}
Z = ["corto/fuori area", "primo palo", "centro", "secondo palo"]


# 1) distribuzione e entropia con bootstrap
def entropy(counts):
    p = np.array(counts, float)
    p = p[p > 0] / p.sum()
    return float(-(p * np.log2(p)).sum())


cnt = df.zone.value_counts().reindex(Z).fillna(0).values
res["zone_counts"] = dict(zip(Z, map(int, cnt)))
res["entropy"] = entropy(cnt)
res["entropy_max"] = 2.0
bs = [
    entropy(pd.Series(rng.choice(df.zone.values, len(df))).value_counts().reindex(Z).fillna(0).values)
    for _ in range(2000)
]
res["entropy_ci"] = list(np.percentile(bs, [2.5, 97.5]))
for s, lab in [(1, "lato_y_basso"), (0, "lato_y_alto")]:
    sub = df[df.side == s]
    c2 = sub.zone.value_counts().reindex(Z).fillna(0).values
    res[f"zone_counts_{lab}"] = dict(zip(Z, map(int, c2)))
    res[f"entropy_{lab}"] = entropy(c2)


# 2) xG per zona con bootstrap
def boot_mean(x, n=2000):
    x = np.asarray(x)
    return list(np.percentile([rng.choice(x, len(x)).mean() for _ in range(n)], [2.5, 97.5]))


res["xg_mean_all"] = float(df.xg.mean())
res["xg_mean_ci"] = boot_mean(df.xg)
res["xg_by_zone"] = {
    z: dict(n=int((df.zone == z).sum()), mean=float(df[df.zone == z].xg.mean()), ci=boot_mean(df[df.zone == z].xg))
    for z in Z
    if (df.zone == z).sum() > 1
}

# 3) prevedibilita' fuori campione (prime 24 partite -> ultime 10)
X = df[["side", "minute", "diff", "period"]].astype(float).to_numpy().copy()
X[:, 1] /= 90
tr, te = df.g < 24, df.g >= 24
clf = LogisticRegression(max_iter=1000, C=1.0).fit(X[tr], df.zone[tr])
from sklearn.metrics import log_loss, accuracy_score

pr = clf.predict_proba(X[te])
cl = list(clf.classes_)
prior = df.zone[tr].value_counts(normalize=True).reindex(cl).fillna(1e-6).values
res["pred"] = dict(
    n_train=int(tr.sum()),
    n_test=int(te.sum()),
    acc_model=float(accuracy_score(df.zone[te], clf.predict(X[te]))),
    acc_baseline=float((df.zone[te] == df.zone[tr].mode()[0]).mean()),
    ll_model=float(log_loss(df.zone[te], pr, labels=cl)),
    ll_baseline=float(log_loss(df.zone[te], np.tile(prior, (te.sum(), 1)), labels=cl)),
)

# 4) assetto difensivo da 360 e matrice zona x assetto
d3 = df[df.has360 == 1].copy()
d3["setup"] = np.where(
    d3.n_opp_near - d3.n_opp_far >= 2,
    "carico vicino",
    np.where(d3.n_opp_far - d3.n_opp_near >= 2, "carico lontano", "equilibrato"),
)
S = ["carico vicino", "equilibrato", "carico lontano"]
res["setup_counts"] = d3.setup.value_counts().reindex(S).fillna(0).astype(int).to_dict()
res["opp_in_box_visible"] = dict(
    median=float(d3.n_opp_box.median()), min=int(d3.n_opp_box.min()), max=int(d3.n_opp_box.max())
)
res["cells"] = {f"{z}|{s}": int(((d3.zone == z) & (d3.setup == s)).sum()) for z in Z for s in S}


def matrix(dd, minn=3):
    A = np.zeros((len(Z), len(S)))
    for i, z in enumerate(Z):
        zm = dd[dd.zone == z].xg.mean() if (dd.zone == z).any() else dd.xg.mean()
        for j, s in enumerate(S):
            c = dd[(dd.zone == z) & (dd.setup == s)]
            A[i, j] = c.xg.mean() if len(c) >= minn else zm
    return A


def gain(dd):
    A = matrix(dd)
    p = dd.zone.value_counts(normalize=True).reindex(Z).fillna(0).values
    return dd.xg.mean() - (p @ A).min()  # xG osservato meno xG con la migliore risposta difensiva


obs = gain(d3)
res["exploit_obs_xg"] = float(obs)
boot = [gain(d3.iloc[rng.integers(0, len(d3), len(d3))]) for _ in range(1000)]
res["exploit_boot_ci"] = list(np.percentile(boot, [2.5, 97.5]))
perm = []
x = d3.xg.values.copy()
for _ in range(1000):
    dp = d3.copy()
    dp["xg"] = rng.permutation(x)
    perm.append(gain(dp))
res["exploit_null_mean"] = float(np.mean(perm))
res["exploit_null_p95"] = float(np.percentile(perm, 95))
res["exploit_pvalue"] = float((np.array(perm) >= obs).mean())
# fuori campione
tr3, te3 = d3.g < 24, d3.g >= 24
A = matrix(d3[tr3])
p = d3[tr3].zone.value_counts(normalize=True).reindex(Z).fillna(0).values
best = S[int((p @ A).argmin())]
res["best_setup_train"] = best
tes = d3[te3]
res["test360_n"] = int(len(tes))
res["test_best_n"] = int((tes.setup == best).sum())
res["test_best_xg"] = float(tes[tes.setup == best].xg.mean()) if (tes.setup == best).any() else None
res["test_other_xg"] = float(tes[tes.setup != best].xg.mean()) if (tes.setup != best).any() else None
json.dump(res, open(f"{BASE}/results_corners.json", "w"), indent=1, default=float)

# figure
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
c = [res["zone_counts"][z] for z in Z]
ax[0].bar(range(4), c, color="#2F6DB5")
ax[0].set_xticks(range(4))
ax[0].set_xticklabels(["corto/\nfuori area", "primo\npalo", "centro", "secondo\npalo"], fontsize=8)
ax[0].set_title("Dove arrivano i corner (n=%d)" % len(df), fontsize=9)
ax[0].set_ylabel("corner")
zz = [z for z in Z if z in res["xg_by_zone"]]
m = [res["xg_by_zone"][z]["mean"] for z in zz]
lo = [res["xg_by_zone"][z]["ci"][0] for z in zz]
hi = [res["xg_by_zone"][z]["ci"][1] for z in zz]
ax[1].bar(range(len(zz)), m, yerr=[np.array(m) - lo, np.array(hi) - m], color="#E07B00", capsize=3)
ax[1].set_xticks(range(len(zz)))
ax[1].set_xticklabels([z.replace(" ", "\n") for z in zz], fontsize=8)
ax[1].set_title("xG medio per corner, con intervallo 95%", fontsize=9)
ax[2].hist(perm, bins=30, color="#C9D3E0")
ax[2].axvline(obs, color="#B3262D")
ax[2].set_title("Exploitability osservata (rossa) contro il caso", fontsize=9)
ax[2].set_xlabel("xG per corner")
plt.tight_layout()
plt.savefig("fig_corners.png", dpi=150)
print(json.dumps(res, indent=1, default=float))
