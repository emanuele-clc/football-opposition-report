"""'Ghosting'-style prediction (after Le et al. 2017, "Data-driven ghosting using deep imitation learning", MIT Sloan): where will each defender be in 3 s,
and how high will the back line be? An LSTM against simple baselines, on the DFL open tracking data. EXPLORATORY.
Usage:  python ghosting.py <dfl_dir> [out=results/exploratory_ghosting.json]          (needs <dfl_dir>/npz from dfl_load.py and torch)
Definitions (fixed before the first run; not tuned afterwards):
- positions at 5 Hz (every 5th frame of 25). Orientation: the defending team defends the goal at x = -52.5 (DFL metres, centre spot = 0).
- samples: one every 1 s in which the ball is in play for the whole window from 2 s before to 3 s after, the same team has the ball for the 2 s before
  (DFL BallPossession), and the defending team has 10 outfield players with positions in the whole window. Goalkeepers are not predicted.
- per defender, input = the last 2 s (11 steps) of: own x, y; ball x, y; own team's outfield centroid; attacking team's outfield centroid; position of the
  nearest attacker relative to the defender (10 numbers per step). Target = displacement from now to 3 s ahead.
- models: (0) persistence: the defender stays where he is; (1) constant velocity over the last 0.4 s; (2) ridge regression (alpha 1) on the flattened input;
  (3) LSTM, 1 layer, 64 units, linear head, Adam lr 0.001, 15 epochs, batch 256, MSE, torch seed 0. Inputs standardised with the training mean and sd.
- split: matches sorted by date, first 5 train, last 2 test (held out, used once). Models (2)-(3) see only the training matches.
- measures on the test matches: mean distance error of the predicted position (m); back-line height = mean x of the 4 deepest outfield defenders (computed
  from each model's predicted positions), absolute error in m. 95% bootstrap over 60 s blocks of test samples (1000 resamples, seed 0) for each error and for
  LSTM minus each baseline. Reading fixed in advance: the LSTM 'beats' a baseline only if the whole interval of the difference is below 0.
Data: Bassek et al. 2025, Scientific Data 12:195, CC BY 4.0. 7 matches of 2022/23 (5 with Fortuna Düsseldorf): far too few for a general model; this shows
what the method gives on open data, not what a club model trained on seasons of tracking would give."""

import sys, os, json, glob
import numpy as np

STEP, PAST, AHEAD = 5, 10, 15  # 5 Hz; 2 s = 10 steps back (11 points); 3 s = 15 steps ahead


def samples(path):
    a = np.load(path)
    meta = json.load(open(path[:-4] + "_events.json", encoding="utf-8"))
    P = meta["players"]
    out = []
    for h in (1, 2):
        xy = a[f"xy_{h}"][:, ::STEP].astype(float)
        ball = a[f"ball_{h}"][::STEP, :2].astype(float)
        alive = a[f"alive_{h}"][::STEP]
        poss = a[f"poss_{h}"][::STEP]
        pids = list(a[f"pids_{h}"])
        tid = np.array([P[p]["team"] for p in pids])
        field = np.array([P[p]["pos"] != "TW" for p in pids])
        T = xy.shape[1]
        for k in range(PAST, T - AHEAD, 5):
            w = slice(k - PAST, k + AHEAD + 1)
            if (
                not (alive[w] == 1).all()
                or poss[k] not in (1, 2)
                or not (poss[k - PAST : k + 1] == poss[k]).all()
                or not np.isfinite(ball[w]).all()
            ):
                continue
            att_id = meta["home"] if poss[k] == 1 else meta["guest"]
            def_id = meta["guest"] if poss[k] == 1 else meta["home"]
            d = meta["halves"][str(h)]["dir"]
            s = d if def_id == meta["home"] else -d
            D = np.where(field & (tid == def_id) & np.isfinite(xy[:, w, 0]).all(1))[0]
            A = np.where(field & (tid == att_id) & np.isfinite(xy[:, k - PAST : k + 1, 0]).all(1))[0]
            if len(D) != 10 or len(A) < 8:
                continue
            pd_, pa, b = xy[D, k - PAST : k + 1] * s, xy[A, k - PAST : k + 1] * s, ball[k - PAST : k + 1] * s
            cd, ca = pd_.mean(0), pa.mean(0)
            near = np.stack([pa[np.argmin(np.linalg.norm(pa[:, -1] - pd_[i, -1], axis=1))] - pd_[i] for i in range(10)])
            X = np.concatenate(
                [
                    pd_,
                    np.broadcast_to(b, (10, PAST + 1, 2)),
                    np.broadcast_to(cd, (10, PAST + 1, 2)),
                    np.broadcast_to(ca, (10, PAST + 1, 2)),
                    near,
                ],
                axis=2,
            )
            out.append(
                dict(
                    match=meta["match"],
                    date=meta["date"],
                    block=f"{meta['match']}-{h}-{k // 300}",
                    X=X.astype(np.float32),
                    now=pd_[:, -1],
                    vel=(pd_[:, -1] - pd_[:, -3]) / 0.4,
                    future=xy[D, k + AHEAD] * s,
                )
            )
    return out


def line(p):
    return np.sort(p[:, 0])[:4].mean()  # mean x of the 4 deepest outfield players


if __name__ == "__main__":
    import torch

    dfl = sys.argv[1]
    out = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "exploratory_ghosting.json"
        )
    )
    if os.path.exists(out):
        sys.exit(f"{out} exists: exploratory result already produced, not rerun.")
    S = [s for p in sorted(glob.glob(f"{dfl}/npz/*.npz")) for s in samples(p)]
    dates = sorted({(s["date"], s["match"]) for s in S})
    train_m = {m for _, m in dates[:5]}
    test_m = {m for _, m in dates[5:]}
    tr = [s for s in S if s["match"] in train_m]
    te = [s for s in S if s["match"] in test_m]
    Xtr = np.concatenate([s["X"] for s in tr])
    Ytr = np.concatenate([s["future"] - s["now"] for s in tr])
    Xte = np.concatenate([s["X"] for s in te])
    mu, sd = Xtr.reshape(-1, 10).mean(0), Xtr.reshape(-1, 10).std(0) + 1e-6
    Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    from sklearn.linear_model import Ridge

    ridge = Ridge(alpha=1.0).fit(Ztr.reshape(len(Ztr), -1), Ytr)
    R = ridge.predict(Zte.reshape(len(Zte), -1))
    torch.manual_seed(0)
    np.random.seed(0)

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.rnn = torch.nn.LSTM(10, 64, batch_first=True)
            self.head = torch.nn.Linear(64, 2)

        def forward(self, x):
            return self.head(self.rnn(x)[0][:, -1])

    net = Net()
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    xt, yt = torch.tensor(Ztr), torch.tensor(Ytr, dtype=torch.float32)
    loss_log = []
    g = torch.Generator().manual_seed(0)
    for ep in range(15):
        perm = torch.randperm(len(xt), generator=g)
        tot = 0.0
        for i in range(0, len(xt), 256):
            j = perm[i : i + 256]
            opt.zero_grad()
            l = torch.nn.functional.mse_loss(net(xt[j]), yt[j])
            l.backward()
            opt.step()
            tot += float(l) * len(j)
        loss_log.append(tot / len(xt))
        print(f"epoch {ep + 1} train MSE {loss_log[-1]:.3f}")
    with torch.no_grad():
        L = net(torch.tensor(Zte)).numpy()
    now = np.concatenate([s["now"] for s in te])
    fut = np.concatenate([s["future"] for s in te])
    vel = np.concatenate([s["vel"] for s in te])
    pred = {"persistence": now, "constant_velocity": now + vel * 3, "ridge": now + R, "lstm": now + L}
    n = len(te)
    blocks = np.array([s["block"] for s in te])
    pos_err = {
        k: np.linalg.norm(v - fut, axis=1).reshape(n, 10).mean(1) for k, v in pred.items()
    }  # per sample, mean over the 10 defenders
    line_err = {
        k: np.array([abs(line(v.reshape(n, 10, 2)[i]) - line(fut.reshape(n, 10, 2)[i])) for i in range(n)])
        for k, v in pred.items()
    }
    ub = np.unique(blocks)
    idx = {b: np.where(blocks == b)[0] for b in ub}
    rng = np.random.default_rng(0)
    draws = [np.concatenate([idx[b] for b in rng.choice(ub, len(ub))]) for _ in range(1000)]
    ci = lambda v: [
        float(np.percentile([v[d].mean() for d in draws], 2.5)),
        float(np.percentile([v[d].mean() for d in draws], 97.5)),
    ]
    summ = lambda E: {k: dict(mean=float(v.mean()), ci=ci(v)) for k, v in E.items()}
    diff = lambda E: {
        f"lstm_minus_{k}": dict(
            mean=float((E["lstm"] - E[k]).mean()), ci=ci(E["lstm"] - E[k]), lstm_beats=bool(ci(E["lstm"] - E[k])[1] < 0)
        )
        for k in E
        if k != "lstm"
    }
    res = {
        "status": "exploratory",
        "data": "DFL open tracking + events, Bassek et al. 2025 (CC BY 4.0), 7 matches 2022/23",
        "horizon_s": 3,
        "train_matches": sorted(train_m),
        "test_matches": sorted(test_m),
        "samples": dict(train=len(tr), test=n),
        "train_mse_by_epoch": loss_log,
        "position_error_m": summ(pos_err),
        "position_diff": diff(pos_err),
        "line_height_error_m": summ(line_err),
        "line_diff": diff(line_err),
        "test_line_height_sd_m": float(np.std([line(fut.reshape(n, 10, 2)[i]) for i in range(n)])),
        "test_mean_displacement_m": float(np.linalg.norm(fut - now, axis=1).mean()),
    }
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    print(
        json.dumps(
            {k: res[k] for k in ("samples", "position_error_m", "position_diff", "line_height_error_m", "line_diff")},
            indent=1,
        )
    )
