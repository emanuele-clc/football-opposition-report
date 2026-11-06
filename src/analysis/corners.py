"""L3: corners with 360 frames. Can a defence exploit where a team sends its corners? Two commands:
  leverkusen  Bayer Leverkusen 2023/24: zones, xG, predictability, defensive set-up from 360, permutation test -> results_corners.json, fig_corners.png
  pooled      World Cup 2022 + Euro 2020 + Euro 2024 pooled, same test; set-up chosen on Euro 2020 + WC 2022, tested on Euro 2024
              -> results_pooled_corners.json
Usage: python corners.py leverkusen|pooled [data_folder=.]      (the folder with matches/, ev/ and t360/)
Zones and set-ups are defined by hand (author); delivery zone = where the corner pass ends, measured from the taker's side."""

import json, sys
import numpy as np, pandas as pd

if len(sys.argv) < 2 or sys.argv[1] not in ("leverkusen", "pooled"):
    sys.exit(__doc__)
WHAT = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else "."
ZONES = ["corto/fuori area", "primo palo", "centro", "secondo palo"]
SETUPS = ["carico vicino", "equilibrato", "carico lontano"]


def zone(end, y0):
    # distance of the end point from the touchline of the taker's side
    d = end[1] if y0 < 40 else 80 - end[1]
    if end[0] < 102 or d < 18:
        return ZONES[0]
    if d < 30:
        return ZONES[1]
    if d <= 50:
        return ZONES[2]
    return ZONES[3]


def corner_xg(ev, i, e, team):
    # xG of the shots of the same team in the same possession after the corner
    total = 0
    for s in ev[i + 1 :]:
        if s["possession"] == e["possession"] and s["team"]["name"] == team and s["type"]["name"] == "Shot":
            total += s["shot"].get("statsbomb_xg", 0)
    return total


def is_corner(e):
    return e["type"]["name"] == "Pass" and e["pass"].get("type", {}).get("name") == "Corner" and "end_location" in e["pass"]


def setup_of(near, far):
    # defenders in the box near / far from the taker
    if near - far >= 2:
        return SETUPS[0]
    if far - near >= 2:
        return SETUPS[2]
    return SETUPS[1]


def matrix(dd, min_n):
    # mean xG for every zone x set-up cell (the zone mean if the cell has fewer than min_n corners)
    A = np.zeros((len(ZONES), len(SETUPS)))
    for i, z in enumerate(ZONES):
        zone_mean = dd[dd.zone == z].xg.mean() if (dd.zone == z).any() else dd.xg.mean()
        for j, s in enumerate(SETUPS):
            cell = dd[(dd.zone == z) & (dd.setup == s)]
            A[i, j] = cell.xg.mean() if len(cell) >= min_n else zone_mean
    return A


def gain(dd, min_n):
    # observed xG minus xG if the defence always chose its best set-up
    A = matrix(dd, min_n)
    p = dd.zone.value_counts(normalize=True).reindex(ZONES).fillna(0).values
    return dd.xg.mean() - (p @ A).min()


def permutation_test(d3, rng, B, min_n):
    obs = gain(d3, min_n)
    boot = [gain(d3.iloc[rng.integers(0, len(d3), len(d3))], min_n) for _ in range(B)]
    x = d3.xg.values.copy()
    perm = []
    for _ in range(B):
        dp = d3.copy()
        dp["xg"] = rng.permutation(x)  # xG shuffled: no link between set-up and danger
        perm.append(gain(dp, min_n))
    return obs, boot, perm


# ---------------------------------------------------------------- Leverkusen
def leverkusen():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss, accuracy_score

    team = "Bayer Leverkusen"
    rng = np.random.default_rng(42)
    matches = sorted(json.load(open(f"{BASE}/matches/9_281.json", encoding="utf-8")), key=lambda g: g["match_date"])
    rows = []
    for gi, g in enumerate(matches):
        mid = g["match_id"]
        ev = json.load(open(f"{BASE}/ev/{mid}.json", encoding="utf-8"))
        frames = {d["event_uuid"]: d for d in json.load(open(f"{BASE}/t360/{mid}.json", encoding="utf-8"))}
        us, them = 0, 0  # score so far
        for i, e in enumerate(ev):
            t = e["team"]["name"]
            kind = e["type"]["name"]
            if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                if t == team:
                    us += 1
                else:
                    them += 1
            if kind == "Own Goal Against":
                if t == team:
                    them += 1
                else:
                    us += 1
            if t != team or not is_corner(e):
                continue
            y = e["location"][1]
            r = {
                "g": gi,
                "minute": e["minute"],
                "period": e["period"],
                "diff": us - them,
                "side": int(y < 40),
                "zone": zone(e["pass"]["end_location"], y),
                "xg": corner_xg(ev, i, e, team),
                "has360": 0,
                "n_opp_near": np.nan,
                "n_opp_far": np.nan,
                "n_att": np.nan,
                "n_opp_box": np.nan,
            }
            frame = frames.get(e["id"])
            if frame:
                r["has360"] = 1
                near = far = att = opp = 0
                for p in frame["freeze_frame"]:
                    px, py = p["location"]
                    if not (px >= 102 and 18 <= py <= 62):  # only players in the box
                        continue
                    if p["teammate"]:
                        att += 1
                    elif not p["keeper"]:
                        opp += 1
                        if (py if y < 40 else 80 - py) < 40:
                            near += 1
                        else:
                            far += 1
                r.update(n_opp_near=near, n_opp_far=far, n_att=att, n_opp_box=opp)
            rows.append(r)
    df = pd.DataFrame(rows)
    res = {"n_corner": len(df), "n_corner_360": int(df.has360.sum())}

    # 1) where the corners go, and how spread out (entropy, max 2 bits)
    def entropy(counts):
        p = np.array(counts, float)
        p = p[p > 0] / p.sum()
        return float(-(p * np.log2(p)).sum())

    cnt = df.zone.value_counts().reindex(ZONES).fillna(0).values
    res["zone_counts"] = dict(zip(ZONES, map(int, cnt)))
    res["entropy"] = entropy(cnt)
    res["entropy_max"] = 2.0
    bs = [entropy(pd.Series(rng.choice(df.zone.values, len(df))).value_counts().reindex(ZONES).fillna(0).values) for _ in range(2000)]
    res["entropy_ci"] = list(np.percentile(bs, [2.5, 97.5]))
    for s, label in [(1, "lato_y_basso"), (0, "lato_y_alto")]:
        c2 = df[df.side == s].zone.value_counts().reindex(ZONES).fillna(0).values
        res[f"zone_counts_{label}"] = dict(zip(ZONES, map(int, c2)))
        res[f"entropy_{label}"] = entropy(c2)

    # 2) xG per zone with a bootstrap interval
    def boot_mean(x, n=2000):
        x = np.asarray(x)
        return list(np.percentile([rng.choice(x, len(x)).mean() for _ in range(n)], [2.5, 97.5]))

    res["xg_mean_all"] = float(df.xg.mean())
    res["xg_mean_ci"] = boot_mean(df.xg)
    res["xg_by_zone"] = {}
    for z in ZONES:
        if (df.zone == z).sum() > 1:
            res["xg_by_zone"][z] = {"n": int((df.zone == z).sum()), "mean": float(df[df.zone == z].xg.mean()), "ci": boot_mean(df[df.zone == z].xg)}

    # 3) can the zone be predicted from side, minute, score, half? first 24 matches -> last 10
    X = df[["side", "minute", "diff", "period"]].astype(float).to_numpy().copy()
    X[:, 1] /= 90
    tr, te = df.g < 24, df.g >= 24
    clf = LogisticRegression(max_iter=1000, C=1.0).fit(X[tr], df.zone[tr])
    pr = clf.predict_proba(X[te])
    cl = list(clf.classes_)
    prior = df.zone[tr].value_counts(normalize=True).reindex(cl).fillna(1e-6).values
    res["pred"] = {
        "n_train": int(tr.sum()),
        "n_test": int(te.sum()),
        "acc_model": float(accuracy_score(df.zone[te], clf.predict(X[te]))),
        "acc_baseline": float((df.zone[te] == df.zone[tr].mode()[0]).mean()),
        "ll_model": float(log_loss(df.zone[te], pr, labels=cl)),
        "ll_baseline": float(log_loss(df.zone[te], np.tile(prior, (te.sum(), 1)), labels=cl)),
    }

    # 4) defensive set-up from the 360 frames, and the exploitability test
    d3 = df[df.has360 == 1].copy()
    d3["setup"] = [setup_of(a, b) for a, b in zip(d3.n_opp_near, d3.n_opp_far)]
    res["setup_counts"] = d3.setup.value_counts().reindex(SETUPS).fillna(0).astype(int).to_dict()
    res["opp_in_box_visible"] = {"median": float(d3.n_opp_box.median()), "min": int(d3.n_opp_box.min()), "max": int(d3.n_opp_box.max())}
    res["cells"] = {f"{z}|{s}": int(((d3.zone == z) & (d3.setup == s)).sum()) for z in ZONES for s in SETUPS}
    obs, boot, perm = permutation_test(d3, rng, 1000, 3)
    res["exploit_obs_xg"] = float(obs)
    res["exploit_boot_ci"] = list(np.percentile(boot, [2.5, 97.5]))
    res["exploit_null_mean"] = float(np.mean(perm))
    res["exploit_null_p95"] = float(np.percentile(perm, 95))
    res["exploit_pvalue"] = float((np.array(perm) >= obs).mean())
    # out of sample: best set-up from the first 24 matches, checked on the last 10
    train, test = d3[d3.g < 24], d3[d3.g >= 24]
    p = train.zone.value_counts(normalize=True).reindex(ZONES).fillna(0).values
    best = SETUPS[int((p @ matrix(train, 3)).argmin())]
    res["best_setup_train"] = best
    res["test360_n"] = int(len(test))
    res["test_best_n"] = int((test.setup == best).sum())
    res["test_best_xg"] = float(test[test.setup == best].xg.mean()) if (test.setup == best).any() else None
    res["test_other_xg"] = float(test[test.setup != best].xg.mean()) if (test.setup != best).any() else None
    json.dump(res, open(f"{BASE}/results_corners.json", "w"), indent=1, default=float)

    # figure
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    ax[0].bar(range(4), [res["zone_counts"][z] for z in ZONES], color="#2F6DB5")
    ax[0].set_xticks(range(4))
    ax[0].set_xticklabels(["corto/\nfuori area", "primo\npalo", "centro", "secondo\npalo"], fontsize=8)
    ax[0].set_title("Dove arrivano i corner (n=%d)" % len(df), fontsize=9)
    ax[0].set_ylabel("corner")
    zz = [z for z in ZONES if z in res["xg_by_zone"]]
    m = [res["xg_by_zone"][z]["mean"] for z in zz]
    lo = [res["xg_by_zone"][z]["ci"][0] for z in zz]
    hi = [res["xg_by_zone"][z]["ci"][1] for z in zz]
    ax[1].bar(range(len(zz)), m, yerr=[np.array(m) - lo, np.array(hi) - m], color="#E07B00", capsize=3)
    ax[1].set_xticks(range(len(zz)))
    ax[1].set_xticklabels([z.replace(" ", "\n") for z in zz], fontsize=8)
    ax[1].set_title("Mean xG per corner, with 95% interval", fontsize=9)
    ax[2].hist(perm, bins=30, color="#C9D3E0")
    ax[2].axvline(obs, color="#B3262D")
    ax[2].set_title("Exploitability osservata (rossa) contro il caso", fontsize=9)
    ax[2].set_xlabel("xG per corner")
    plt.tight_layout()
    plt.savefig("fig_corners.png", dpi=150)
    print(json.dumps(res, indent=1, default=float))


# ---------------------------------------------------------------- pooled tournaments
def pooled():
    rng = np.random.default_rng(42)
    tournaments = [(43, 106, "Mondiale 2022"), (55, 282, "Europei 2024"), (55, 43, "Europei 2020")]
    rows = []
    per_tournament = {}
    for cid, sid, name in tournaments:
        for g in json.load(open(f"{BASE}/matches/{cid}_{sid}.json")):
            mid = g["match_id"]
            ev = json.load(open(f"{BASE}/ev/{mid}.json"))
            try:
                frames = {d["event_uuid"]: d for d in json.load(open(f"{BASE}/t360/{mid}.json"))}
            except FileNotFoundError:
                frames = {}
            for i, e in enumerate(ev):
                if not is_corner(e):
                    continue
                t = e["team"]["name"]
                y = e["location"][1]
                per_tournament[name] = per_tournament.get(name, 0) + 1
                r = {"torneo": name, "match": mid, "team": t, "zone": zone(e["pass"]["end_location"], y), "xg": corner_xg(ev, i, e, t), "has360": 0}
                frame = frames.get(e["id"])
                if frame:
                    near = far = 0
                    for p in frame["freeze_frame"]:
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
    d3["setup"] = [setup_of(a, b) for a, b in zip(d3.near, d3.far)]
    print("Corner totali:", len(df), "| con 360:", len(d3), "| xG medio %.3f" % d3.xg.mean())
    print(pd.crosstab(d3.zone, d3.setup).reindex(index=ZONES, columns=SETUPS).fillna(0).astype(int))

    obs, boot, perm = permutation_test(d3, rng, 500, 5)
    print("Exploitability: %.4f xG/corner | caso: media %.4f, 95-esimo %.4f | p = %.3f" % (obs, np.mean(perm), np.percentile(perm, 95), (np.array(perm) >= obs).mean()))

    # best set-up chosen on Euro 2020 + World Cup 2022, checked on Euro 2024
    train, test = d3[d3.torneo != "Europei 2024"], d3[d3.torneo == "Europei 2024"]
    p = train.zone.value_counts(normalize=True).reindex(ZONES).fillna(0).values
    best = SETUPS[int((p @ matrix(train, 5)).argmin())]
    a = test[test.setup == best].xg
    b = test[test.setup != best].xg
    diffs = [rng.choice(a.values, len(a)).mean() - rng.choice(b.values, len(b)).mean() for _ in range(2000)]
    print("Euro 2024: best set-up %s, xG %.3f (n=%d) vs others %.3f (n=%d)" % (best, a.mean(), len(a), b.mean(), len(b)))

    res = {
        "corner_per_torneo": per_tournament,
        "corner_totali": int(len(df)),
        "corner_con_360": int(len(d3)),
        "corner_360_per_torneo": {k: int(v) for k, v in d3.groupby("torneo").size().items()},
        "xg_medio_360": float(d3.xg.mean()),
        "zone": d3.zone.value_counts().reindex(ZONES).fillna(0).astype(int).to_dict(),
        "assetti": d3.setup.value_counts().reindex(SETUPS).fillna(0).astype(int).to_dict(),
        "exploit_obs": float(obs),
        "exploit_ci95_boot": [float(v) for v in np.percentile(boot, [2.5, 97.5])],
        "exploit_null_mean": float(np.mean(perm)),
        "exploit_null_p95": float(np.percentile(perm, 95)),
        "exploit_pvalue": float((np.array(perm) >= obs).mean()),
        "test_euro2024": {
            "assetto_migliore": best,
            "n": int(len(test)),
            "xg_assetto": float(a.mean()),
            "n_assetto": int(len(a)),
            "xg_altri": float(b.mean()),
            "n_altri": int(len(b)),
            "differenza": float(a.mean() - b.mean()),
            "ci95": [float(v) for v in np.percentile(diffs, [2.5, 97.5])],
        },
    }
    json.dump(res, open(f"{BASE}/results_pooled_corners.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if WHAT == "leverkusen":
    leverkusen()
else:
    pooled()
