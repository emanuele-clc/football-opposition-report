"""Automated opposition report (L2, open play). Descriptive: it applies the validated settings and states how reliable each part is.
Usage:  python make_report.py <matches.json> "<Team>" [data_dir=.]
Output: report_<Team>.html (self-contained, print to PDF from the browser) and report_<Team>.json (all numbers) in data_dir.
Frozen settings (same as the validated protocol): phase cut x = 45, k = 5 build-up and k = 3 advanced, 11 features, K-Means n_init = 20, random_state = 0.
Reference teams: any other seq_<Team>.csv found in data_dir (written by this script) are used as a comparison."""
import sys, os, io, json, glob, base64, html as H, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]; CUT = 45; K = {"build-up": 5, "advanced": 3}
B_CI, B_STAB = 1000, 100; rng = np.random.default_rng(0)
df, nm = S.extract(); df["w0"] = (df.y0 - 40).abs(); df["w1"] = (df.y1 - 40).abs(); TEAM = S.TEAM; BASE = S.BASE
df.drop(columns=["zones", "path"], errors="ignore").to_csv(f"{BASE}/seq_{TEAM.replace(' ', '_')}.csv", index=False)
seasons = f"{df.data.min()} to {df.data.max()}"

def boot_games(games, by, stat, B=B_CI):
    out = []
    for _ in range(B):
        gs = rng.choice(games, len(games)); out.append(stat(np.concatenate([by[g] for g in gs])))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]

def jaccard_boot(X, g, k, B=B_STAB):
    lab = KMeans(k, n_init=10, random_state=0).fit(X).labels_; games = np.unique(g); by = {x: np.where(g == x)[0] for x in games}; sc = np.zeros(k)
    for _ in range(B):
        idx = np.concatenate([by[x] for x in rng.choice(games, len(games))]); lb = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
        for c in range(k): a = lab == c; sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return sc / B

def reliability(j): return "stable" if j >= 0.75 else ("moderate" if j >= 0.60 else "unstable")
res = {"team": TEAM, "matches": int(nm), "period": seasons, "sequences": int(len(df)), "phases": {}}
fam_tables = {}
for phase, k in K.items():
    sub = (df[df.x0 < CUT] if phase == "build-up" else df[df.x0 >= CUT]).reset_index(drop=True); sc = StandardScaler().fit(sub[COLS].values); X = sc.transform(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(X); order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
    names = {c: f"{'B' if phase == 'build-up' else 'A'}{i + 1}" for i, c in enumerate(order)}; sub["fam"] = [names[l] for l in km.labels_]
    g = sub.gi.values; games = np.unique(g); by = {x: np.where(g == x)[0] for x in games}; N = len(sub); nshots = sub.shot.sum()
    jac = jaccard_boot(X, g, k); jobs = float(jac.mean())
    Xs = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])]); jsh = float(jaccard_boot(Xs, g, k, 60).mean())
    Xg = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X)); jg = float(jaccard_boot(Xg, g, k, 60).mean())
    margin = jobs - max(jsh, jg); flag = "clear structure" if margin >= 0.10 else "slices of a continuum (stability close to a structure-free baseline)"
    rows = []
    for c in order:
        f = names[c]; m = (sub.fam == f).values; d = sub[m]
        share_ci = boot_games(games, by, lambda idx, m=m: m[idx].mean()); shot_ci = boot_games(games, by, lambda idx, m=m: sub.shot.values[idx][m[idx]].mean() if m[idx].any() else np.nan)
        pm = np.array([m[by[x]].mean() for x in games])
        rows.append(dict(fam=f, n=int(m.sum()), share=float(m.mean()), share_ci=share_ci, passes=float(d.n_pass.mean()), dur=float(d.dur.mean()), long=float(d.long_share.mean()), x0=float(d.x0.mean()), x1=float(d.x1.mean()),
                         directness=float(d.directness.mean()), shot=float(d.shot.mean()), shot_ci=[float(np.nanpercentile(shot_ci, 0)) if False else shot_ci[0], shot_ci[1]], shot_share=float(d.shot.sum() / max(nshots, 1)),
                         per_match_p10_p90=[float(np.percentile(pm, 10)), float(np.percentile(pm, 90))], jaccard=float(jac[c]), reliability=reliability(jac[c])))
    pp = pd.crosstab(sub.play_pattern, sub.fam, normalize="index").round(3); ppn = sub.play_pattern.value_counts()
    res["phases"][phase] = dict(k=k, n=int(N), jaccard_mean=jobs, null_shuffle=jsh, null_gauss=jg, margin=float(margin), verdict=flag, families=rows,
                                by_start=[dict(start=i, n=int(ppn[i]), shares=pp.loc[i].to_dict()) for i in pp.index]); fam_tables[phase] = (rows, pp, ppn)

# team style vs reference teams
def style(d, by_games=None):
    return dict(passes=d.n_pass.mean(), long=d.long_share.mean(), dur=d.dur.mean(), shot=d.shot.mean(), buildup_share=(d.x0 < CUT).mean())
mine = style(df); gall = df.gi.values; ga = np.unique(gall); bya = {x: np.where(gall == x)[0] for x in ga}
mine_ci = {kk: boot_games(ga, bya, lambda idx, kk=kk: (df.x0.values[idx] < CUT).mean() if kk == "buildup_share" else df[{"passes": "n_pass", "long": "long_share", "dur": "dur", "shot": "shot"}[kk]].values[idx].mean(), 500) for kk in mine}
refs = {}
for f in glob.glob(f"{BASE}/seq_*.csv"):
    t = os.path.basename(f)[4:-4].replace("_", " ")
    if t != TEAM.replace("_", " "): refs[t] = style(pd.read_csv(f))
res["style"] = dict(team={k: float(v) for k, v in mine.items()}, team_ci=mine_ci, references={t: {k: float(v) for k, v in s.items()} for t, s in refs.items()})
json.dump(res, open(f"{BASE}/report_{TEAM.replace(' ', '_')}.json", "w"), indent=1)

# figure: progression chart per family
def fig_png():
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4)); cols = plt.cm.tab10.colors
    for ax, (phase, (rows, pp, ppn)) in zip(axs, fam_tables.items()):
        for i, r in enumerate(rows[::-1]):
            ax.barh(i, r["x1"] - r["x0"], left=r["x0"], height=0.15 + 0.7 * r["share"] / max(rr["share"] for rr in rows), color=cols[i % 10], alpha=0.85)
            ax.text(max(r["x0"], r["x1"]) + 2, i, f"{r['fam']}  {r['share']:.0%} of sequences, shots {r['shot']:.0%}", va="center", fontsize=7.5)
        ax.set_yticks([]); ax.set_xlim(0, 150); ax.set_xticks([0, 30, 60, 90, 120]); ax.axvline(CUT, color="grey", ls=":", lw=0.8); ax.set_xlabel("pitch position (own goal 0, opponent goal 120)"); ax.set_title(f"{phase}: average start to end (bar thickness = share of sequences)", fontsize=9)
    plt.tight_layout(); b = io.BytesIO(); fig.savefig(b, format="png", dpi=140); plt.close(fig); return base64.b64encode(b.getvalue()).decode()

pc = lambda x: f"{100 * x:.0f}%"; ci = lambda c: f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"
css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1{color:#1F3A5F;margin-bottom:2px}h2{color:#1F3A5F;border-bottom:1px solid #ccc;padding-top:14px}table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.warn{background:#FFF4E0;border-left:4px solid #E8A33D;padding:6px 10px;margin:8px 0}.ok{background:#E8F4EA;border-left:4px solid #4C9A5B;padding:6px 10px;margin:8px 0}.small{color:#555;font-size:11px}"
h = [f"<html><head><meta charset='utf-8'><title>Opposition report: {H.escape(TEAM)}</title><style>{css}</style></head><body>", f"<h1>Opposition report: {H.escape(TEAM)}</h1>",
     f"<div class='small'>Open-play possession sequences, StatsBomb Open Data, {nm} matches ({seasons}), {len(df)} sequences with at least 3 passes. Automatically generated; intervals are 95% bootstrap over matches. Reference teams are the other teams processed so far (leagues and seasons may differ).</div>"]
h.append("<h2>1. Style at a glance</h2><table><tr><th></th><th>This team</th><th>95% interval</th>" + ("<th>Reference teams (mean, min-max)</th>" if refs else "") + "</tr>")
lab = {"passes": "Passes per sequence", "long": "Share of long passes (30+)", "dur": "Duration (seconds)", "shot": "Sequences ending in a shot", "buildup_share": "Sequences starting in own half (x < 45)"}
for kk, nmx in lab.items():
    f_ = (lambda v: f"{v:.1f}") if kk in ("passes", "dur") else pc; c = mine_ci[kk]; cc = f"{f_(c[0])} to {f_(c[1])}"
    rf = ""
    if refs: vs = [s[kk] for s in refs.values()]; rf = f"<td>{f_(np.mean(vs))} ({f_(min(vs))}-{f_(max(vs))}), {len(vs)} teams</td>"
    h.append(f"<tr><td>{H.escape(nmx)}</td><td>{f_(mine[kk])}</td><td>{cc}</td>{rf}</tr>")
h.append("</table>"); h.append(f"<img src='data:image/png;base64,{fig_png()}' style='width:100%'>")
for i, (phase, (rows, pp, ppn)) in enumerate(fam_tables.items(), 2):
    P = res["phases"][phase]; box = "ok" if P["margin"] >= 0.10 else "warn"
    h.append(f"<h2>{i}. {phase.capitalize()} sequence families (k = {P['k']}, {P['n']} sequences)</h2><div class='{box}'><b>Structure check:</b> stability {P['jaccard_mean']:.2f} against {P['null_shuffle']:.2f} (shuffled features) and {P['null_gauss']:.2f} (single Gaussian blob): <b>{P['verdict']}</b>.</div>")
    h.append("<table><tr><th>Family</th><th>Share (95%)</th><th>Passes</th><th>Duration</th><th>Long</th><th>Start to end (x)</th><th>Shot rate (95%)</th><th>Share of shots</th><th>Per-match share (p10-p90)</th><th>Stability</th></tr>")
    for r in rows:
        h.append(f"<tr><td>{r['fam']}</td><td>{pc(r['share'])} ({ci(r['share_ci'])})</td><td>{r['passes']:.1f}</td><td>{r['dur']:.0f}s</td><td>{pc(r['long'])}</td><td>{r['x0']:.0f} to {r['x1']:.0f}</td><td>{pc(r['shot'])} ({ci(r['shot_ci'])})</td><td>{pc(r['shot_share'])}</td><td>{ci(r['per_match_p10_p90'])}</td><td>{r['jaccard']:.2f} {r['reliability']}</td></tr>")
    h.append("</table>"); fams = list(rows and [r['fam'] for r in rows])
    h.append("<b>How sequences start decides the family</b> (row shares; this is the strongest regularity found in the validation):<table><tr><th>Start type</th><th>n</th>" + "".join(f"<th>{f}</th>" for f in fams) + "</tr>")
    for s in P["by_start"]: h.append(f"<tr><td>{H.escape(s['start'])}</td><td>{s['n']}</td>" + "".join(f"<td>{pc(s['shares'].get(f, 0))}</td>" for f in fams) + "</tr>")
    h.append("</table>")
h.append("<h2>4. How to read this report</h2><ul><li>Families are slices of how this team builds up, fitted on its own matches: they describe tendencies, not fixed tactical plans. Names such as B1 are labels, not tactical categories.</li>"
         "<li>Stability is the mean best-match Jaccard under bootstrap over matches (stable 0.75 or more, moderate 0.60-0.75, unstable below). When the structure check says 'slices of a continuum', treat the families as a convenient partition, not as separate behaviours.</li>"
         "<li>Validation on held-out matches (10 teams): families are reproduced (shares change by at most 10 points) and how a sequence starts explains almost all of the predictability; score, home/away, minute and previous family added nothing (exploratory).</li>"
         "<li>The families do <b>not</b> predict whether a sequence ends in a shot better than a one-variable rule based on where the sequence ends (families better in 0 of 10 teams, simple rule better in 5 of 10). Read them as a description of how the team builds up, not as a better shot predictor.</li>"
         "<li>Limits: event data only, no player positions off the ball; the tactical meaning of the families has not been validated by coaches; shot rates per family are descriptive, not causal.</li></ul></body></html>")
open(f"{BASE}/report_{TEAM.replace(' ', '_')}.html", "w", encoding="utf-8").write("".join(h)); print("saved", f"{BASE}/report_{TEAM.replace(' ', '_')}.html")
