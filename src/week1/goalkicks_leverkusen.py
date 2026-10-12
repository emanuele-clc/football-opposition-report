"""Settimana 1 - rinvii dal fondo del Leverkusen 2023/24: quota di rinvii corti, entropia, bootstrap e confronto con la baseline."""
import json, math, sys
import numpy as np
BASE = sys.argv[1] if len(sys.argv) > 1 else "."
TEAM = "Bayer Leverkusen"
m = sorted(json.load(open(f"{BASE}/matches/9_281.json", encoding="utf-8")), key=lambda g: g["match_date"]); rows = []
for gi, g in enumerate(m):
    ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")); fr = {d["event_uuid"]: d for d in json.load(open(f"{BASE}/t360/{g['match_id']}.json", encoding="utf-8"))}
    sc = {"L": 0, "O": 0}
    for e in ev:
        t = e["team"]["name"]; ty = e["type"]["name"]
        if ty == "Shot" and e["shot"]["outcome"]["name"] == "Goal": sc["L" if t == TEAM else "O"] += 1
        if ty == "Own Goal Against": sc["O" if t == TEAM else "L"] += 1
        if ty == "Pass" and t == TEAM and e["pass"].get("type", {}).get("name") == "Goal Kick":
            ff = fr.get(e["id"]); opp = sum(1 for p in ff["freeze_frame"] if not p["teammate"]) if ff else None
            rows.append(dict(g=gi, minute=e["minute"], period=e["period"], diff=sc["L"] - sc["O"], home=int(g["home_team"]["home_team_name"] == TEAM), short=int(e["pass"].get("length", 99) < 30), has360=int(ff is not None), opp=opp))
ys = np.array([r["short"] for r in rows]); p = ys.mean(); H = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
rng = np.random.default_rng(0); bs = [rng.choice(ys, len(ys)).mean() for _ in range(2000)]
print("rinvii", len(rows), "con 360", sum(r["has360"] for r in rows), "| corti %.2f, IC95 %.2f-%.2f | entropia %.2f bit" % (p, *np.percentile(bs, [2.5, 97.5]), H))
print("avversari visibili (rinvii con 360): mediana", np.median([r["opp"] for r in rows if r["opp"] is not None]))
for lab, f in [("in vantaggio", lambda r: r["diff"] > 0), ("pari", lambda r: r["diff"] == 0), ("sotto", lambda r: r["diff"] < 0)]:
    s = [r["short"] for r in rows if f(r)]; print("  %s: %d rinvii, corti %.2f" % (lab, len(s), np.mean(s)))
X = lambda rs: np.array([[1, r["diff"], r["minute"] / 90, r["home"], int(r["period"] == 2)] for r in rs], float)
tr = [r for r in rows if r["g"] < 24]; te = [r for r in rows if r["g"] >= 24]
Xt, yt, Xe, ye = X(tr), np.array([r["short"] for r in tr], float), X(te), np.array([r["short"] for r in te], float)
w = np.zeros(Xt.shape[1])
for _ in range(2000):
    pr = 1 / (1 + np.exp(-Xt @ w)); w -= 0.05 * (Xt.T @ (pr - yt) / len(yt) + 0.01 * w)
pe = 1 / (1 + np.exp(-Xe @ w)); ll = lambda q, y: -np.mean(y * np.log(np.clip(q, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - q, 1e-6, 1)))
b = yt.mean(); print("test (%d rinvii): baseline acc %.2f ll %.3f | modello acc %.2f ll %.3f" % (len(ye), np.mean((b >= .5) == ye), ll(np.full(len(ye), b), ye), np.mean((pe >= .5) == ye), ll(pe, ye)))
