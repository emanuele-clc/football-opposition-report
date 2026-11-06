"""Automated opposition report (L2, open play). Descriptive: it applies the validated settings and states how reliable each part is.
Usage:  python make_report.py <matches.json> "<Team>" [data_dir=.]
Output: report_<Team>.html (self-contained, print to PDF from the browser) and report_<Team>.json (all numbers) in data_dir.
Frozen settings (same as the validated protocol): phase cut x = 45, k = 5 build-up and k = 3 advanced, 11 features, K-Means n_init = 20, random_state = 0.
Reference teams: any other seq_<Team>.csv found in data_dir (written by this script) are used as a comparison."""

import sys, os, io, json, glob, base64, html as H, warnings
import numpy as np, pandas as pd
from common import pc, ci

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis"))
import sequences_clustering as S
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"build-up": 5, "advanced": 3}
B_CI, B_STAB = 1000, 100
# One generator for the whole report: the order of the calls below decides every interval, so do not reorder them.
rng = np.random.default_rng(0)

df, nm = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()
TEAM = S.TEAM
BASE = S.BASE
FN = TEAM.replace(" ", "_")


def data_provider(mf):
    """Who the events come from: data_provider in the match list (generic CSV --provider=...), else StatsBomb when the list has
    StatsBomb's competition fields, else unnamed."""
    g = (json.load(open(mf, encoding="utf-8")) or [{}])[0]
    return g.get("data_provider") or ("StatsBomb Open Data" if "competition" in g else "events from the data provider")


PROVIDER = data_provider(S.MF)
df.drop(columns=["zones", "path"], errors="ignore").to_csv(f"{BASE}/seq_{FN}.csv", index=False)
seasons = f"{df.data.min()} to {df.data.max()}"

OFFS = None
if os.environ.get("OPPREPORT_OFFSETS"):
    OFFS = pd.read_csv(os.environ["OPPREPORT_OFFSETS"])
    OFFS["match_id"] = OFFS["match_id"].astype(str)
    OFFS = OFFS.set_index("match_id")


def video_time(match, half, minute, sec):
    """Video time = video second at which the half kicks off + match clock (cumulative minute) - 2700 s in the second half. Empty if data are missing."""
    if OFFS is None or str(match) not in OFFS.index or half not in (1, 2):
        return ""
    if half == 1:
        v = float(OFFS.loc[str(match), "half1_start"]) + minute * 60 + sec
    else:
        v = float(OFFS.loc[str(match), "half2_start"]) + minute * 60 + sec - 2700
    if v < 0:
        return ""
    return f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{int(v % 60):02d}"


def boot_games(games, by, stat, B=B_CI):
    out = []
    for _ in range(B):
        gs = rng.choice(games, len(games))
        out.append(stat(np.concatenate([by[g] for g in gs])))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def jaccard_boot(X, g, k, B=B_STAB):
    """Stability of each cluster: mean best-match Jaccard between the full fit and fits on bootstrap samples of matches."""
    lab = KMeans(k, n_init=10, random_state=0).fit(X).labels_
    games = np.unique(g)
    by = {x: np.where(g == x)[0] for x in games}
    sc = np.zeros(k)
    for _ in range(B):
        idx = np.concatenate([by[x] for x in rng.choice(games, len(games))])
        lb = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
        for c in range(k):
            a = lab == c
            sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return sc / B


def reliability(j):
    if j >= 0.75:
        return "stable"
    return "moderate" if j >= 0.60 else "unstable"


def examples(d, dist):
    """The three sequences closest to the family centre."""
    out = []
    for r in d.iloc[np.argsort(dist)[:3]].itertuples():
        out.append({
            "date": str(r.data),
            "opponent": str(r.avv),
            "half": int(r.tempo),
            "minute": int(r.minuto),
            "second": int(r.sec),
            "video": video_time(r.match, int(r.tempo), int(r.minuto), int(r.sec)),
            "start": str(r.play_pattern),
            "passes": int(r.n_pass),
            "dur": float(r.dur),
            "shot": bool(r.shot),
        })
    return out


def fit_phase(phase, k):
    in_phase = df[df.x0 < CUT] if phase == "build-up" else df[df.x0 >= CUT]
    sub = in_phase.reset_index(drop=True)
    X = StandardScaler().fit(sub[COLS].values).transform(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(X)
    # families ordered by mean start x (bigger first on ties) and named B1.. / A1..
    order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
    prefix = "B" if phase == "build-up" else "A"
    names = {c: f"{prefix}{i + 1}" for i, c in enumerate(order)}
    sub["fam"] = [names[l] for l in km.labels_]
    fam_index = pd.Series(sub.fam.values, index=in_phase.index)

    g = sub.gi.values
    games = np.unique(g)
    by = {x: np.where(g == x)[0] for x in games}
    nshots = sub.shot.sum()

    # structure check: stability against two structure-free baselines
    jac = jaccard_boot(X, g, k)
    j_obs = float(jac.mean())
    X_shuffled = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])])
    j_shuffle = float(jaccard_boot(X_shuffled, g, k, 60).mean())
    X_gauss = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X))
    j_gauss = float(jaccard_boot(X_gauss, g, k, 60).mean())
    margin = j_obs - max(j_shuffle, j_gauss)
    if margin >= 0.10:
        verdict = "clear structure"
    else:
        verdict = "slices of a continuum (stability close to a structure-free baseline)"

    rows = []
    for c in order:
        f = names[c]
        m = (sub.fam == f).values
        d = sub[m]
        share_ci = boot_games(games, by, lambda idx: m[idx].mean())
        shot_ci = boot_games(games, by, lambda idx: sub.shot.values[idx][m[idx]].mean() if m[idx].any() else np.nan)
        per_match = np.array([m[by[x]].mean() for x in games])
        dist = np.linalg.norm(X - km.cluster_centers_[c], axis=1)[m]
        rows.append({
            "fam": f,
            "n": int(m.sum()),
            "share": float(m.mean()),
            "share_ci": share_ci,
            "passes": float(d.n_pass.mean()),
            "dur": float(d.dur.mean()),
            "long": float(d.long_share.mean()),
            "x0": float(d.x0.mean()),
            "x1": float(d.x1.mean()),
            "directness": float(d.directness.mean()),
            "shot": float(d.shot.mean()),
            "shot_ci": [shot_ci[0], shot_ci[1]],
            "shot_share": float(d.shot.sum() / max(nshots, 1)),
            "per_match_p10_p90": [float(np.percentile(per_match, 10)), float(np.percentile(per_match, 90))],
            "examples": examples(d, dist),
            "jaccard": float(jac[c]),
            "reliability": reliability(jac[c]),
        })

    pp = pd.crosstab(sub.play_pattern, sub.fam, normalize="index").round(3)
    ppn = sub.play_pattern.value_counts()
    result = {
        "k": k,
        "n": int(len(sub)),
        "jaccard_mean": j_obs,
        "null_shuffle": j_shuffle,
        "null_gauss": j_gauss,
        "margin": float(margin),
        "verdict": verdict,
        "families": rows,
        "by_start": [{"start": i, "n": int(ppn[i]), "shares": pp.loc[i].to_dict()} for i in pp.index],
    }
    return result, rows, fam_index


res = {"team": TEAM, "matches": int(nm), "period": seasons, "sequences": int(len(df)), "phases": {}}
fam_rows = {}
fam_idx = {}
for phase, k in K.items():
    res["phases"][phase], fam_rows[phase], fam_idx[phase] = fit_phase(phase, k)

# Reliability: how far would the numbers move if only n matches were available?
df["fam"] = pd.concat(fam_idx.values())
games_all = np.unique(df.gi)
rng2 = np.random.default_rng(1)
FEATURE = {"passes": "n_pass", "long": "long_share", "shot": "shot"}


def family_shares(d, phase):
    prefix = "B" if phase == "build-up" else "A"
    q = d[d.fam.str.startswith(prefix)]
    fams = sorted(df[df.fam.str.startswith(prefix)].fam.unique())
    return np.array([(q.fam == f).sum() / max(len(q), 1) for f in fams])


full = {k: df[col].mean() for k, col in FEATURE.items()}
full_shares = {ph: family_shares(df, ph) for ph in K}
rel = {}
for n in [x for x in (3, 5, 8, 10) if x < len(games_all)]:
    err = {k: [] for k in full}
    err_share = {ph: [] for ph in K}
    for _ in range(300):
        d = df[df.gi.isin(rng2.choice(games_all, n, replace=False))]
        for k, col in FEATURE.items():
            err[k].append(abs(d[col].mean() - full[k]))
        for ph in K:
            err_share[ph].append(np.max(np.abs(family_shares(d, ph) - full_shares[ph])))
    rel[n] = {
        "passes": float(np.percentile(err["passes"], 90)),
        "long": float(np.percentile(err["long"], 90)),
        "shot": float(np.percentile(err["shot"], 90)),
        "build_up": float(np.percentile(err_share["build-up"], 90)),
        "advanced": float(np.percentile(err_share["advanced"], 90)),
    }
res["reliability"] = {str(k): v for k, v in rel.items()}

# Clip list: every sequence with its family.
clips = df.sort_values(["fam", "data", "tempo", "minuto", "sec"]).copy()
clips["video_time"] = [video_time(r.match, int(r.tempo), int(r.minuto), int(r.sec)) for r in clips.itertuples()]
clip_cols = ["fam", "match", "data", "avv", "tempo", "minuto", "sec", "play_pattern", "n_pass", "dur", "shot", "video_time"]
clip_names = {
    "fam": "family",
    "data": "date",
    "avv": "opponent",
    "tempo": "half",
    "minuto": "minute",
    "sec": "second",
    "play_pattern": "start_type",
    "n_pass": "passes",
    "dur": "duration_s",
    "shot": "ended_in_shot",
}
clips[clip_cols].rename(columns=clip_names).to_csv(f"{BASE}/clips_{FN}.csv", index=False)

# Review kit for an analyst: the example sequences of every family.
review = [dict(family=r["fam"], **e) for ph in res["phases"].values() for r in ph["families"] for e in r["examples"]]
pd.DataFrame([{
    "family": x["family"],
    "date": x["date"],
    "opponent": x["opponent"],
    "half": x["half"],
    "minute": x["minute"],
    "second": x["second"],
    "video_time": x["video"],
    "start_type": x["start"],
    "passes": x["passes"],
    "duration_s": round(x["dur"]),
    "ended_in_shot": int(x["shot"]),
    "coherent_with_family": "",
    "comment": "",
} for x in review]).to_csv(f"{BASE}/review_{FN}.csv", index=False, encoding="utf-8")

QS = [
    "Does this description match what you know about this team? What is right and what is wrong?",
    "Which parts would you use before a match and which would you skip?",
    "What is missing that you would need?",
    "Do the reliability notes change how you read the report?",
    "How long would it take you to get the same overview from video, and would this report shorten it?",
]
REVIEW_CSS = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;font-size:13px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:4px 6px}th{background:#E6ECF4}li{margin:6px 0}"
review_rows = "".join(
    f"<tr><td>{x['family']}</td><td>{x['date']}</td><td>{H.escape(x['opponent'])}</td><td>half {x['half']}, {x['minute']}:{x['second']:02d}</td><td>{x['video']}</td><td>{H.escape(x['start'])}</td><td>{x['passes']}</td><td>{'yes' if x['shot'] else 'no'}</td><td style='width:120px'>&nbsp;</td></tr>"
    for x in review
)
questions = "".join(f"<li>{q}<br><br><br></li>" for q in QS)
open(f"{BASE}/review_{FN}.html", "w", encoding="utf-8").write(
    f"<html><head><meta charset='utf-8'><title>Analyst review: {H.escape(TEAM)}</title><style>{REVIEW_CSS}</style></head><body><h1>Analyst review: {H.escape(TEAM)}</h1><p>Part 1: watch each sequence and mark whether it fits the family it was assigned to (yes / partly / no). Part 2: answer the five questions. The same questions are used for every reviewer. Nothing here is evidence that the report is useful until someone with football experience has answered.</p><h2>Part 1: sequences</h2><table><tr><th>Family</th><th>Date</th><th>Opponent</th><th>Half, time</th><th>Video</th><th>Start</th><th>Passes</th><th>Shot</th><th>Fits? (yes / partly / no)</th></tr>{review_rows}</table><h2>Part 2: questions</h2><ol>{questions}</ol></body></html>"
)


# Team style vs reference teams (the other seq_*.csv in the folder).
STYLE_COL = {"passes": "n_pass", "long": "long_share", "dur": "dur", "shot": "shot"}


def style(d):
    return {
        "passes": d.n_pass.mean(),
        "long": d.long_share.mean(),
        "dur": d.dur.mean(),
        "shot": d.shot.mean(),
        "buildup_share": (d.x0 < CUT).mean(),
    }


def style_stat(key):
    if key == "buildup_share":
        return lambda idx: (df.x0.values[idx] < CUT).mean()
    return lambda idx: df[STYLE_COL[key]].values[idx].mean()


mine = style(df)
all_gi = df.gi.values
all_games = np.unique(all_gi)
by_game = {x: np.where(all_gi == x)[0] for x in all_games}
mine_ci = {kk: boot_games(all_games, by_game, style_stat(kk), 500) for kk in mine}
refs = {}
for f in glob.glob(f"{BASE}/seq_*.csv"):
    t = os.path.basename(f)[4:-4].replace("_", " ")
    if t != TEAM.replace("_", " "):
        refs[t] = style(pd.read_csv(f))
res["style"] = {
    "team": {k: float(v) for k, v in mine.items()},
    "team_ci": mine_ci,
    "references": {t: {k: float(v) for k, v in s.items()} for t, s in refs.items()},
}
json.dump(res, open(f"{BASE}/report_{FN}.json", "w"), indent=1)


def fig_png():
    """Average start-to-end bar of each family, one panel per phase."""
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4))
    colors = plt.cm.tab10.colors
    for ax, (phase, rows) in zip(axs, fam_rows.items()):
        biggest = max(r["share"] for r in rows)
        for i, r in enumerate(rows[::-1]):
            ax.barh(i, r["x1"] - r["x0"], left=r["x0"], height=0.15 + 0.7 * r["share"] / biggest, color=colors[i % 10], alpha=0.85)
            ax.text(max(r["x0"], r["x1"]) + 2, i, f"{r['fam']}  {r['share']:.0%} of sequences, shots {r['shot']:.0%}", va="center", fontsize=7.5)
        ax.set_yticks([])
        ax.set_xlim(0, 150)
        ax.set_xticks([0, 30, 60, 90, 120])
        ax.axvline(CUT, color="grey", ls=":", lw=0.8)
        ax.set_xlabel("pitch position (own goal 0, opponent goal 120)")
        ax.set_title(f"{phase}: average start to end (bar thickness = share of sequences)", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def num1(v):
    return f"{v:.1f}"


CSS = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1{color:#1F3A5F;margin-bottom:2px}h2{color:#1F3A5F;border-bottom:1px solid #ccc;padding-top:14px}table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.warn{background:#FFF4E0;border-left:4px solid #E8A33D;padding:6px 10px;margin:8px 0}.ok{background:#E8F4EA;border-left:4px solid #4C9A5B;padding:6px 10px;margin:8px 0}.small{color:#555;font-size:11px}"
STYLE_LABELS = {
    "passes": "Passes per sequence",
    "long": "Share of long passes (30+)",
    "dur": "Duration (seconds)",
    "shot": "Sequences ending in a shot",
    "buildup_share": "Sequences starting in own half (x < 45)",
}

h = [
    f"<html><head><meta charset='utf-8'><title>Opposition report: {H.escape(TEAM)}</title><style>{CSS}</style></head><body>",
    f"<h1>Opposition report: {H.escape(TEAM)}</h1>",
    f"<div class='small'>Open-play possession sequences, {H.escape(PROVIDER)}, {nm} matches ({seasons}), {len(df)} sequences with at least 3 passes. Automatically generated; intervals are 95% bootstrap over matches. Reference teams are the other teams processed so far (leagues and seasons may differ).</div>",
]

# 1. style
ref_head = "<th>Reference teams (mean, min-max)</th>" if refs else ""
h.append(f"<h2>1. Style at a glance</h2><table><tr><th></th><th>This team</th><th>95% interval</th>{ref_head}</tr>")
for kk, label in STYLE_LABELS.items():
    fmt = num1 if kk in ("passes", "dur") else pc
    c = mine_ci[kk]
    ref_cell = ""
    if refs:
        vs = [s[kk] for s in refs.values()]
        ref_cell = f"<td>{fmt(np.mean(vs))} ({fmt(min(vs))}-{fmt(max(vs))}), {len(vs)} teams</td>"
    h.append(f"<tr><td>{H.escape(label)}</td><td>{fmt(mine[kk])}</td><td>{fmt(c[0])} to {fmt(c[1])}</td>{ref_cell}</tr>")
h.append("</table>")
h.append(f"<img src='data:image/png;base64,{fig_png()}' style='width:100%'>")

# 2-3. families of each phase
for i, (phase, rows) in enumerate(fam_rows.items(), 2):
    P = res["phases"][phase]
    box = "ok" if P["margin"] >= 0.10 else "warn"
    h.append(f"<h2>{i}. {phase.capitalize()} sequence families (k = {P['k']}, {P['n']} sequences)</h2><div class='{box}'><b>Structure check:</b> stability {P['jaccard_mean']:.2f} against {P['null_shuffle']:.2f} (shuffled features) and {P['null_gauss']:.2f} (single Gaussian blob): <b>{P['verdict']}</b>.</div>")
    h.append("<table><tr><th>Family</th><th>Share (95%)</th><th>Passes</th><th>Duration</th><th>Long</th><th>Start to end (x)</th><th>Shot rate (95%)</th><th>Share of shots</th><th>Per-match share (p10-p90)</th><th>Stability</th></tr>")
    for r in rows:
        h.append(f"<tr><td>{r['fam']}</td><td>{pc(r['share'])} ({ci(r['share_ci'])})</td><td>{r['passes']:.1f}</td><td>{r['dur']:.0f}s</td><td>{pc(r['long'])}</td><td>{r['x0']:.0f} to {r['x1']:.0f}</td><td>{pc(r['shot'])} ({ci(r['shot_ci'])})</td><td>{pc(r['shot_share'])}</td><td>{ci(r['per_match_p10_p90'])}</td><td>{r['jaccard']:.2f} {r['reliability']}</td></tr>")
    h.append("</table>")

    h.append("<b>Typical sequences to find on video</b> (the three closest to the centre of each family):<table><tr><th>Family</th><th>Date</th><th>Opponent</th><th>Half, minute</th><th>Start</th><th>Passes</th><th>Duration</th><th>Ended in a shot</th></tr>")
    for r in rows:
        for e in r["examples"]:
            video = f" (video {e['video']})" if e["video"] else ""
            h.append(f"<tr><td>{r['fam']}</td><td>{e['date']}</td><td>{H.escape(e['opponent'])}</td><td>half {e['half']}, {e['minute']}:{e['second']:02d}{video}</td><td>{H.escape(e['start'])}</td><td>{e['passes']}</td><td>{e['dur']:.0f}s</td><td>{'yes' if e['shot'] else 'no'}</td></tr>")
    h.append("</table>")

    fams = [r["fam"] for r in rows]
    h.append("<b>How sequences start decides the family</b> (row shares; this is the strongest regularity found in the validation):<table><tr><th>Start type</th><th>n</th>" + "".join(f"<th>{f}</th>" for f in fams) + "</tr>")
    for s in P["by_start"]:
        h.append(f"<tr><td>{H.escape(s['start'])}</td><td>{s['n']}</td>" + "".join(f"<td>{pc(s['shares'].get(f, 0))}</td>" for f in fams) + "</tr>")
    h.append("</table>")

# 4. reliability
if nm < 8:
    trust = "With fewer than 8 matches, treat style numbers as rough."
else:
    trust = "That is enough for passes and long-pass tendencies to be reliable; see the table for the others."
h.append(f"<h2>4. How much can you trust this report?</h2><div class='{'warn' if nm < 8 else 'ok'}'>This report uses <b>{nm} matches</b>. {trust}</div>")
h.append("<p>If you only had <i>n</i> matches of this team, the numbers would typically (90% of the time) differ from the ones above by at most:</p><table><tr><th>Matches used</th><th>Passes per sequence</th><th>Long-pass share (points)</th><th>Shot rate (points)</th><th>Any family share, build-up (points)</th><th>Any family share, advanced (points)</th></tr>")
for n, v in rel.items():
    h.append(f"<tr><td>{n}</td><td>&plusmn;{v['passes']:.1f}</td><td>&plusmn;{100 * v['long']:.1f}</td><td>&plusmn;{100 * v['shot']:.1f}</td><td>&plusmn;{100 * v['build_up']:.0f}</td><td>&plusmn;{100 * v['advanced']:.0f}</td></tr>")
h.append("</table><p class='small'>Computed by repeatedly drawing n matches from this team's season and comparing with all of them. Across 10 teams (thesis validation), 8 to 10 matches were needed for passes and long-pass tendencies to be within half the gap between teams; shot rate and the share of sequences starting in the own half could not be told apart between teams reliably even with 15 matches. Families here are fitted on all available matches; with only a few matches the families themselves would be less stable. Recent form and tactical changes are not captured.</p>")

# 5. how to read it
h.append(
    "<h2>5. How to read this report</h2><ul><li>Families are slices of how this team builds up, fitted on its own matches: they describe tendencies, not fixed tactical plans. Names such as B1 are labels, not tactical categories.</li>"
    "<li>Stability is the mean best-match Jaccard under bootstrap over matches (stable 0.75 or more, moderate 0.60-0.75, unstable below). When the structure check says 'slices of a continuum', treat the families as a convenient partition, not as separate behaviours.</li>"
    "<li>Validation on held-out matches (10 teams): families are reproduced (shares change by at most 10 points) and how a sequence starts explains almost all of the predictability; score, home/away, minute and previous family added nothing (exploratory).</li>"
    "<li>The families do <b>not</b> predict whether a sequence ends in a shot better than a one-variable rule based on where the sequence ends (families better in 0 of 10 teams, simple rule better in 5 of 10). Read them as a description of how the team builds up, not as a better shot predictor.</li>"
    "<li>Limits: event data only, no player positions off the ball; the tactical meaning of the families has not been validated by coaches; shot rates per family are descriptive, not causal.</li></ul></body></html>"
)
open(f"{BASE}/report_{FN}.html", "w", encoding="utf-8").write("".join(h))
print("saved", f"{BASE}/report_{FN}.html")
