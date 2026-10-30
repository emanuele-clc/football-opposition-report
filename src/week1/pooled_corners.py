"""Week 1 (check) - corners with 360 frames pooled from World Cup 2022, Euro 2020 and Euro 2024 (StatsBomb Open Data).
Counts corners with 360, estimates the distribution by zone, xG and the permutation test of exploitability at population level.
Limits: different teams pooled (heterogeneity ignored), zones and set-ups defined by the author."""

import json, sys, numpy as np, pandas as pd

BASE = sys.argv[1] if len(sys.argv) > 1 else "."
rng = np.random.default_rng(42)
SETS = [(43, 106, "Mondiale 2022"), (55, 282, "Europei 2024"), (55, 43, "Europei 2020")]
Z = ["corto/fuori area", "primo palo", "centro", "secondo palo"]
S = ["carico vicino", "equilibrato", "carico lontano"]


def zone(end, y0):
    d = end[1] if y0 < 40 else 80 - end[1]
    if end[0] < 102 or d < 18:
        return Z[0]
    return Z[1] if d < 30 else (Z[2] if d <= 50 else Z[3])


rows = []
tot_corner = {}
for cid, sid, name in SETS:
    for gi, g in enumerate(json.load(open(f"{BASE}/matches/{cid}_{sid}.json"))):
        mid = g["match_id"]
        ev = json.load(open(f"{BASE}/ev/{mid}.json"))
        try:
            fr = {d["event_uuid"]: d for d in json.load(open(f"{BASE}/t360/{mid}.json"))}
        except FileNotFoundError:
            fr = {}
        for i, e in enumerate(ev):
            if (
                e["type"]["name"] == "Pass"
                and e["pass"].get("type", {}).get("name") == "Corner"
                and "end_location" in e["pass"]
            ):
                t = e["team"]["name"]
                y = e["location"][1]
                tot_corner[name] = tot_corner.get(name, 0) + 1
                xg = sum(
                    s["shot"].get("statsbomb_xg", 0)
                    for s in ev[i + 1 :]
                    if s["possession"] == e["possession"] and s["team"]["name"] == t and s["type"]["name"] == "Shot"
                )
                r = dict(torneo=name, match=mid, team=t, zone=zone(e["pass"]["end_location"], y), xg=xg, has360=0)
                d3 = fr.get(e["id"])
                if d3:
                    near = far = 0
                    for p in d3["freeze_frame"]:
                        px, py = p["location"]
                        if px >= 102 and 18 <= py <= 62 and not p["teammate"] and not p["keeper"]:
                            if (py if y < 40 else 80 - py) < 40:
                                near += 1
                            else:
                                far += 1
                    r.update(has360=1, near=near, far=far)
                rows.append(r)
df = pd.DataFrame(rows)
d3 = df[df.has360 == 1].copy()
print("Corner totali per torneo:", tot_corner)
print("Corner totali:", len(df), "| con 360:", len(d3))
print(d3.groupby("torneo").size().to_dict())
d3["setup"] = np.where(d3.near - d3.far >= 2, S[0], np.where(d3.far - d3.near >= 2, S[2], S[1]))
print("Mean xG per corner (with 360): %.3f" % d3.xg.mean())
print("Zone:", d3.zone.value_counts().reindex(Z).fillna(0).astype(int).to_dict())
print("Assetti:", d3.setup.value_counts().reindex(S).fillna(0).astype(int).to_dict())
print("Zone x set-up cells:")
print(pd.crosstab(d3.zone, d3.setup).reindex(index=Z, columns=S).fillna(0).astype(int))


def matrix(dd, minn=5):
    A = np.zeros((4, 3))
    for i, z in enumerate(Z):
        zm = dd[dd.zone == z].xg.mean() if (dd.zone == z).any() else dd.xg.mean()
        for j, s in enumerate(S):
            c = dd[(dd.zone == z) & (dd.setup == s)]
            A[i, j] = c.xg.mean() if len(c) >= minn else zm
    return A


def gain(dd):
    A = matrix(dd)
    p = dd.zone.value_counts(normalize=True).reindex(Z).fillna(0).values
    return dd.xg.mean() - (p @ A).min()


obs = gain(d3)
boot = [gain(d3.iloc[rng.integers(0, len(d3), len(d3))]) for _ in range(500)]
x = d3.xg.values
perm = []
for _ in range(500):
    dp = d3.copy()
    dp["xg"] = rng.permutation(x)
    perm.append(gain(dp))
print(
    "Exploitability aggregata: %.4f xG/corner | IC95 bootstrap %.4f-%.4f | caso: media %.4f, 95-esimo %.4f | p = %.3f"
    % (obs, *np.percentile(boot, [2.5, 97.5]), np.mean(perm), np.percentile(perm, 95), (np.array(perm) >= obs).mean())
)
# out of sample by tournament: estimated on Euro 2020 + World Cup 2022, tested on Euro 2024
trn, tst = d3[d3.torneo != "Europei 2024"], d3[d3.torneo == "Europei 2024"]
A = matrix(trn)
p = trn.zone.value_counts(normalize=True).reindex(Z).fillna(0).values
best = S[int((p @ A).argmin())]
print("Out of sample (test: Euro 2024, %d corners with 360): best estimated set-up = %s" % (len(tst), best))
a = tst[tst.setup == best].xg
b = tst[tst.setup != best].xg
print(
    "  xG with best set-up: %.3f (n=%d) | others: %.3f (n=%d) | difference %.3f"
    % (a.mean(), len(a), b.mean(), len(b), a.mean() - b.mean())
)
bd = [rng.choice(a.values, len(a)).mean() - rng.choice(b.values, len(b)).mean() for _ in range(2000)]
print("  IC95 della differenza: %.3f ... %.3f" % tuple(np.percentile(bd, [2.5, 97.5])))
# Saves the numbers printed above (added 17 Oct 2026 so the result has a file in results/; the analysis above is unchanged).
json.dump(
    dict(
        corner_per_torneo=tot_corner,
        corner_totali=int(len(df)),
        corner_con_360=int(len(d3)),
        corner_360_per_torneo={k: int(v) for k, v in d3.groupby("torneo").size().items()},
        xg_medio_360=float(d3.xg.mean()),
        zone=d3.zone.value_counts().reindex(Z).fillna(0).astype(int).to_dict(),
        assetti=d3.setup.value_counts().reindex(S).fillna(0).astype(int).to_dict(),
        exploit_obs=float(obs),
        exploit_ci95_boot=[float(v) for v in np.percentile(boot, [2.5, 97.5])],
        exploit_null_mean=float(np.mean(perm)),
        exploit_null_p95=float(np.percentile(perm, 95)),
        exploit_pvalue=float((np.array(perm) >= obs).mean()),
        test_euro2024=dict(
            assetto_migliore=best,
            n=int(len(tst)),
            xg_assetto=float(a.mean()),
            n_assetto=int(len(a)),
            xg_altri=float(b.mean()),
            n_altri=int(len(b)),
            differenza=float(a.mean() - b.mean()),
            ci95=[float(v) for v in np.percentile(bd, [2.5, 97.5])],
        ),
    ),
    open(f"{BASE}/results_pooled_corners.json", "w", encoding="utf-8"),
    indent=1,
    ensure_ascii=False,
)
