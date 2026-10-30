"""Automated opposition report (L2, open play). Descriptive: it applies the validated settings and states how reliable each part is.
Usage:  python make_report.py <matches.json> "<Team>" [data_dir=.]
Output: report_<Team>.html (self-contained, print to PDF from the browser) and report_<Team>.json (all numbers) in data_dir.
Frozen settings (same as the validated protocol): phase cut x = 45, k = 5 build-up and k = 3 advanced, 11 features, K-Means n_init = 20, random_state = 0.
Reference teams: any other seq_<Team>.csv found in data_dir (written by this script) are used as a comparison."""

import sys, os, io, json, glob, base64, html as H, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
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
rng = np.random.default_rng(0)
df, nm = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()
TEAM = S.TEAM
BASE = S.BASE


def data_provider(mf):
    """Who the events come from: data_provider in the match list (generic CSV --provider=...), else StatsBomb when the list has
    StatsBomb's competition fields, else unnamed."""
    g = (json.load(open(mf, encoding="utf-8")) or [{}])[0]
    return g.get("data_provider") or ("StatsBomb Open Data" if "competition" in g else "events from the data provider")


PROVIDER = data_provider(S.MF)
df.drop(columns=["zones", "path"], errors="ignore").to_csv(f"{BASE}/seq_{TEAM.replace(' ', '_')}.csv", index=False)
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
    v = (
        float(OFFS.loc[str(match), "half1_start" if half == 1 else "half2_start"])
        + minute * 60
        + sec
        - (0 if half == 1 else 2700)
    )
    return f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{int(v % 60):02d}" if v >= 0 else ""


def boot_games(games, by, stat, B=B_CI):
    out = []
    for _ in range(B):
        gs = rng.choice(games, len(games))
        out.append(stat(np.concatenate([by[g] for g in gs])))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def jaccard_boot(X, g, k, B=B_STAB):
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
    return "stable" if j >= 0.75 else ("moderate" if j >= 0.60 else "unstable")


res = {"team": TEAM, "matches": int(nm), "period": seasons, "sequences": int(len(df)), "phases": {}}
fam_tables = {}
fam_idx = {}
for phase, k in K.items():
    sub = (df[df.x0 < CUT] if phase == "build-up" else df[df.x0 >= CUT]).reset_index(drop=True)
    sc = StandardScaler().fit(sub[COLS].values)
    X = sc.transform(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(X)
    order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
    names = {c: f"{'B' if phase == 'build-up' else 'A'}{i + 1}" for i, c in enumerate(order)}
    sub["fam"] = [names[l] for l in km.labels_]
    fam_idx[phase] = pd.Series(
        sub.fam.values, index=(df[df.x0 < CUT] if phase == "build-up" else df[df.x0 >= CUT]).index
    )
    g = sub.gi.values
    games = np.unique(g)
    by = {x: np.where(g == x)[0] for x in games}
    N = len(sub)
    nshots = sub.shot.sum()
    jac = jaccard_boot(X, g, k)
    jobs = float(jac.mean())
    Xs = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])])
    jsh = float(jaccard_boot(Xs, g, k, 60).mean())
    Xg = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X))
    jg = float(jaccard_boot(Xg, g, k, 60).mean())
    margin = jobs - max(jsh, jg)
    flag = (
        "clear structure" if margin >= 0.10 else "slices of a continuum (stability close to a structure-free baseline)"
    )
    rows = []
    for c in order:
        f = names[c]
        m = (sub.fam == f).values
        d = sub[m]
        share_ci = boot_games(games, by, lambda idx, m=m: m[idx].mean())
        shot_ci = boot_games(
            games, by, lambda idx, m=m: sub.shot.values[idx][m[idx]].mean() if m[idx].any() else np.nan
        )
        pm = np.array([m[by[x]].mean() for x in games])
        dm = np.linalg.norm(X - km.cluster_centers_[c], axis=1)[m]
        ex = [
            dict(
                date=str(r.data),
                opponent=str(r.avv),
                half=int(r.tempo),
                minute=int(r.minuto),
                second=int(r.sec),
                video=video_time(r.match, int(r.tempo), int(r.minuto), int(r.sec)),
                start=str(r.play_pattern),
                passes=int(r.n_pass),
                dur=float(r.dur),
                shot=bool(r.shot),
            )
            for r in d.iloc[np.argsort(dm)[:3]].itertuples()
        ]
        rows.append(
            dict(
                fam=f,
                n=int(m.sum()),
                share=float(m.mean()),
                share_ci=share_ci,
                passes=float(d.n_pass.mean()),
                dur=float(d.dur.mean()),
                long=float(d.long_share.mean()),
                x0=float(d.x0.mean()),
                x1=float(d.x1.mean()),
                directness=float(d.directness.mean()),
                shot=float(d.shot.mean()),
                shot_ci=[float(np.nanpercentile(shot_ci, 0)) if False else shot_ci[0], shot_ci[1]],
                shot_share=float(d.shot.sum() / max(nshots, 1)),
                per_match_p10_p90=[float(np.percentile(pm, 10)), float(np.percentile(pm, 90))],
                examples=ex,
                jaccard=float(jac[c]),
                reliability=reliability(jac[c]),
            )
        )
    pp = pd.crosstab(sub.play_pattern, sub.fam, normalize="index").round(3)
    ppn = sub.play_pattern.value_counts()
    res["phases"][phase] = dict(
        k=k,
        n=int(N),
        jaccard_mean=jobs,
        null_shuffle=jsh,
        null_gauss=jg,
        margin=float(margin),
        verdict=flag,
        families=rows,
        by_start=[dict(start=i, n=int(ppn[i]), shares=pp.loc[i].to_dict()) for i in pp.index],
    )
    fam_tables[phase] = (rows, pp, ppn)

# reliability: how far would the numbers move if only n matches were available?
df["fam"] = pd.concat(fam_idx.values())
games_all = np.unique(df.gi)
rng2 = np.random.default_rng(1)


def _shares(d, ph):
    q = d[d.fam.str.startswith("B" if ph == "build-up" else "A")]
    return np.array(
        [
            (q.fam == f).sum() / max(len(q), 1)
            for f in sorted(df[df.fam.str.startswith("B" if ph == "build-up" else "A")].fam.unique())
        ]
    )


_full = dict(passes=df.n_pass.mean(), long=df.long_share.mean(), shot=df.shot.mean())
_fsh = {ph: _shares(df, ph) for ph in K}
rel = {}
for n in [x for x in (3, 5, 8, 10) if x < len(games_all)]:
    e = {k: [] for k in _full}
    es = {ph: [] for ph in K}
    for _ in range(300):
        d = df[df.gi.isin(rng2.choice(games_all, n, replace=False))]
        for k in _full:
            e[k].append(
                abs(getattr(d, {"passes": "n_pass", "long": "long_share", "shot": "shot"}[k]).mean() - _full[k])
            )
        for ph in K:
            es[ph].append(np.max(np.abs(_shares(d, ph) - _fsh[ph])))
    rel[n] = dict(
        passes=float(np.percentile(e["passes"], 90)),
        long=float(np.percentile(e["long"], 90)),
        shot=float(np.percentile(e["shot"], 90)),
        build_up=float(np.percentile(es["build-up"], 90)),
        advanced=float(np.percentile(es["advanced"], 90)),
    )
res["reliability"] = {str(k): v for k, v in rel.items()}

# clip list (all sequences with their family) and review kit for an analyst
cl = df.sort_values(["fam", "data", "tempo", "minuto", "sec"]).copy()
cl["video_time"] = [video_time(r.match, int(r.tempo), int(r.minuto), int(r.sec)) for r in cl.itertuples()]
cl[
    ["fam", "match", "data", "avv", "tempo", "minuto", "sec", "play_pattern", "n_pass", "dur", "shot", "video_time"]
].rename(
    columns={
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
).to_csv(
    f"{BASE}/clips_{TEAM.replace(' ', '_')}.csv", index=False
)
rev = [dict(family=r["fam"], **e_) for ph in res["phases"].values() for r in ph["families"] for e_ in r["examples"]]
pd.DataFrame(
    [
        dict(
            family=x["family"],
            date=x["date"],
            opponent=x["opponent"],
            half=x["half"],
            minute=x["minute"],
            second=x["second"],
            video_time=x["video"],
            start_type=x["start"],
            passes=x["passes"],
            duration_s=round(x["dur"]),
            ended_in_shot=int(x["shot"]),
            coherent_with_family="",
            comment="",
        )
        for x in rev
    ]
).to_csv(f"{BASE}/review_{TEAM.replace(' ', '_')}.csv", index=False, encoding="utf-8")
QS = [
    "Does this description match what you know about this team? What is right and what is wrong?",
    "Which parts would you use before a match and which would you skip?",
    "What is missing that you would need?",
    "Do the reliability notes change how you read the report?",
    "How long would it take you to get the same overview from video, and would this report shorten it?",
]
rcss = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;font-size:13px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:4px 6px}th{background:#E6ECF4}li{margin:6px 0}"
rows_h = "".join(
    f"<tr><td>{x['family']}</td><td>{x['date']}</td><td>{H.escape(x['opponent'])}</td><td>half {x['half']}, {x['minute']}:{x['second']:02d}</td><td>{x['video']}</td><td>{H.escape(x['start'])}</td><td>{x['passes']}</td><td>{'yes' if x['shot'] else 'no'}</td><td style='width:120px'>&nbsp;</td></tr>"
    for x in rev
)
open(f"{BASE}/review_{TEAM.replace(' ', '_')}.html", "w", encoding="utf-8").write(
    f"<html><head><meta charset='utf-8'><title>Analyst review: {H.escape(TEAM)}</title><style>{rcss}</style></head><body><h1>Analyst review: {H.escape(TEAM)}</h1><p>Part 1: watch each sequence and mark whether it fits the family it was assigned to (yes / partly / no). Part 2: answer the five questions. The same questions are used for every reviewer. Nothing here is evidence that the report is useful until someone with football experience has answered.</p><h2>Part 1: sequences</h2><table><tr><th>Family</th><th>Date</th><th>Opponent</th><th>Half, time</th><th>Video</th><th>Start</th><th>Passes</th><th>Shot</th><th>Fits? (yes / partly / no)</th></tr>{rows_h}</table><h2>Part 2: questions</h2><ol>"
    + "".join(f"<li>{q}<br><br><br></li>" for q in QS)
    + "</ol></body></html>"
)


# team style vs reference teams
def style(d, by_games=None):
    return dict(
        passes=d.n_pass.mean(),
        long=d.long_share.mean(),
        dur=d.dur.mean(),
        shot=d.shot.mean(),
        buildup_share=(d.x0 < CUT).mean(),
    )


mine = style(df)
gall = df.gi.values
ga = np.unique(gall)
bya = {x: np.where(gall == x)[0] for x in ga}
mine_ci = {
    kk: boot_games(
        ga,
        bya,
        lambda idx, kk=kk: (
            (df.x0.values[idx] < CUT).mean()
            if kk == "buildup_share"
            else df[{"passes": "n_pass", "long": "long_share", "dur": "dur", "shot": "shot"}[kk]].values[idx].mean()
        ),
        500,
    )
    for kk in mine
}
refs = {}
for f in glob.glob(f"{BASE}/seq_*.csv"):
    t = os.path.basename(f)[4:-4].replace("_", " ")
    if t != TEAM.replace("_", " "):
        refs[t] = style(pd.read_csv(f))
res["style"] = dict(
    team={k: float(v) for k, v in mine.items()},
    team_ci=mine_ci,
    references={t: {k: float(v) for k, v in s.items()} for t, s in refs.items()},
)
json.dump(res, open(f"{BASE}/report_{TEAM.replace(' ', '_')}.json", "w"), indent=1)


# figure: progression chart per family
def fig_png():
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4))
    cols = plt.cm.tab10.colors
    for ax, (phase, (rows, pp, ppn)) in zip(axs, fam_tables.items()):
        for i, r in enumerate(rows[::-1]):
            ax.barh(
                i,
                r["x1"] - r["x0"],
                left=r["x0"],
                height=0.15 + 0.7 * r["share"] / max(rr["share"] for rr in rows),
                color=cols[i % 10],
                alpha=0.85,
            )
            ax.text(
                max(r["x0"], r["x1"]) + 2,
                i,
                f"{r['fam']}  {r['share']:.0%} of sequences, shots {r['shot']:.0%}",
                va="center",
                fontsize=7.5,
            )
        ax.set_yticks([])
        ax.set_xlim(0, 150)
        ax.set_xticks([0, 30, 60, 90, 120])
        ax.axvline(CUT, color="grey", ls=":", lw=0.8)
        ax.set_xlabel("pitch position (own goal 0, opponent goal 120)")
        ax.set_title(f"{phase}: average start to end (bar thickness = share of sequences)", fontsize=9)
    plt.tight_layout()
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=140)
    plt.close(fig)
    return base64.b64encode(b.getvalue()).decode()


pc = lambda x: f"{100 * x:.0f}%"
ci = lambda c: f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"
css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1{color:#1F3A5F;margin-bottom:2px}h2{color:#1F3A5F;border-bottom:1px solid #ccc;padding-top:14px}table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.warn{background:#FFF4E0;border-left:4px solid #E8A33D;padding:6px 10px;margin:8px 0}.ok{background:#E8F4EA;border-left:4px solid #4C9A5B;padding:6px 10px;margin:8px 0}.small{color:#555;font-size:11px}"
h = [
    f"<html><head><meta charset='utf-8'><title>Opposition report: {H.escape(TEAM)}</title><style>{css}</style></head><body>",
    f"<h1>Opposition report: {H.escape(TEAM)}</h1>",
    f"<div class='small'>Open-play possession sequences, {H.escape(PROVIDER)}, {nm} matches ({seasons}), {len(df)} sequences with at least 3 passes. Automatically generated; intervals are 95% bootstrap over matches. Reference teams are the other teams processed so far (leagues and seasons may differ).</div>",
]
h.append(
    "<h2>1. Style at a glance</h2><table><tr><th></th><th>This team</th><th>95% interval</th>"
    + ("<th>Reference teams (mean, min-max)</th>" if refs else "")
    + "</tr>"
)
lab = {
    "passes": "Passes per sequence",
    "long": "Share of long passes (30+)",
    "dur": "Duration (seconds)",
    "shot": "Sequences ending in a shot",
    "buildup_share": "Sequences starting in own half (x < 45)",
}
for kk, nmx in lab.items():
    f_ = (lambda v: f"{v:.1f}") if kk in ("passes", "dur") else pc
    c = mine_ci[kk]
    cc = f"{f_(c[0])} to {f_(c[1])}"
    rf = ""
    if refs:
        vs = [s[kk] for s in refs.values()]
        rf = f"<td>{f_(np.mean(vs))} ({f_(min(vs))}-{f_(max(vs))}), {len(vs)} teams</td>"
    h.append(f"<tr><td>{H.escape(nmx)}</td><td>{f_(mine[kk])}</td><td>{cc}</td>{rf}</tr>")
h.append("</table>")
h.append(f"<img src='data:image/png;base64,{fig_png()}' style='width:100%'>")
for i, (phase, (rows, pp, ppn)) in enumerate(fam_tables.items(), 2):
    P = res["phases"][phase]
    box = "ok" if P["margin"] >= 0.10 else "warn"
    h.append(
        f"<h2>{i}. {phase.capitalize()} sequence families (k = {P['k']}, {P['n']} sequences)</h2><div class='{box}'><b>Structure check:</b> stability {P['jaccard_mean']:.2f} against {P['null_shuffle']:.2f} (shuffled features) and {P['null_gauss']:.2f} (single Gaussian blob): <b>{P['verdict']}</b>.</div>"
    )
    h.append(
        "<table><tr><th>Family</th><th>Share (95%)</th><th>Passes</th><th>Duration</th><th>Long</th><th>Start to end (x)</th><th>Shot rate (95%)</th><th>Share of shots</th><th>Per-match share (p10-p90)</th><th>Stability</th></tr>"
    )
    for r in rows:
        h.append(
            f"<tr><td>{r['fam']}</td><td>{pc(r['share'])} ({ci(r['share_ci'])})</td><td>{r['passes']:.1f}</td><td>{r['dur']:.0f}s</td><td>{pc(r['long'])}</td><td>{r['x0']:.0f} to {r['x1']:.0f}</td><td>{pc(r['shot'])} ({ci(r['shot_ci'])})</td><td>{pc(r['shot_share'])}</td><td>{ci(r['per_match_p10_p90'])}</td><td>{r['jaccard']:.2f} {r['reliability']}</td></tr>"
        )
    h.append("</table>")
    fams = list(rows and [r["fam"] for r in rows])
    h.append(
        "<b>Typical sequences to find on video</b> (the three closest to the centre of each family):<table><tr><th>Family</th><th>Date</th><th>Opponent</th><th>Half, minute</th><th>Start</th><th>Passes</th><th>Duration</th><th>Ended in a shot</th></tr>"
    )
    for r in rows:
        for e_ in r["examples"]:
            h.append(
                f"<tr><td>{r['fam']}</td><td>{e_['date']}</td><td>{H.escape(e_['opponent'])}</td><td>half {e_['half']}, {e_['minute']}:{e_['second']:02d}{(' (video ' + e_['video'] + ')') if e_['video'] else ''}</td><td>{H.escape(e_['start'])}</td><td>{e_['passes']}</td><td>{e_['dur']:.0f}s</td><td>{'yes' if e_['shot'] else 'no'}</td></tr>"
            )
    h.append("</table>")
    h.append(
        "<b>How sequences start decides the family</b> (row shares; this is the strongest regularity found in the validation):<table><tr><th>Start type</th><th>n</th>"
        + "".join(f"<th>{f}</th>" for f in fams)
        + "</tr>"
    )
    for s in P["by_start"]:
        h.append(
            f"<tr><td>{H.escape(s['start'])}</td><td>{s['n']}</td>"
            + "".join(f"<td>{pc(s['shares'].get(f, 0))}</td>" for f in fams)
            + "</tr>"
        )
    h.append("</table>")
h.append(
    f"<h2>4. How much can you trust this report?</h2><div class='{'warn' if nm < 8 else 'ok'}'>This report uses <b>{nm} matches</b>. "
    + (
        "With fewer than 8 matches, treat style numbers as rough."
        if nm < 8
        else "That is enough for passes and long-pass tendencies to be reliable; see the table for the others."
    )
    + "</div>"
)
h.append(
    "<p>If you only had <i>n</i> matches of this team, the numbers would typically (90% of the time) differ from the ones above by at most:</p><table><tr><th>Matches used</th><th>Passes per sequence</th><th>Long-pass share (points)</th><th>Shot rate (points)</th><th>Any family share, build-up (points)</th><th>Any family share, advanced (points)</th></tr>"
)
for n, v in rel.items():
    h.append(
        f"<tr><td>{n}</td><td>&plusmn;{v['passes']:.1f}</td><td>&plusmn;{100 * v['long']:.1f}</td><td>&plusmn;{100 * v['shot']:.1f}</td><td>&plusmn;{100 * v['build_up']:.0f}</td><td>&plusmn;{100 * v['advanced']:.0f}</td></tr>"
    )
h.append(
    "</table><p class='small'>Computed by repeatedly drawing n matches from this team's season and comparing with all of them. Across 10 teams (thesis validation), 8 to 10 matches were needed for passes and long-pass tendencies to be within half the gap between teams; shot rate and the share of sequences starting in the own half could not be told apart between teams reliably even with 15 matches. Families here are fitted on all available matches; with only a few matches the families themselves would be less stable. Recent form and tactical changes are not captured.</p>"
)
h.append(
    "<h2>5. How to read this report</h2><ul><li>Families are slices of how this team builds up, fitted on its own matches: they describe tendencies, not fixed tactical plans. Names such as B1 are labels, not tactical categories.</li>"
    "<li>Stability is the mean best-match Jaccard under bootstrap over matches (stable 0.75 or more, moderate 0.60-0.75, unstable below). When the structure check says 'slices of a continuum', treat the families as a convenient partition, not as separate behaviours.</li>"
    "<li>Validation on held-out matches (10 teams): families are reproduced (shares change by at most 10 points) and how a sequence starts explains almost all of the predictability; score, home/away, minute and previous family added nothing (exploratory).</li>"
    "<li>The families do <b>not</b> predict whether a sequence ends in a shot better than a one-variable rule based on where the sequence ends (families better in 0 of 10 teams, simple rule better in 5 of 10). Read them as a description of how the team builds up, not as a better shot predictor.</li>"
    "<li>Limits: event data only, no player positions off the ball; the tactical meaning of the families has not been validated by coaches; shot rates per family are descriptive, not causal.</li></ul></body></html>"
)
open(f"{BASE}/report_{TEAM.replace(' ', '_')}.html", "w", encoding="utf-8").write("".join(h))
print("saved", f"{BASE}/report_{TEAM.replace(' ', '_')}.html")
