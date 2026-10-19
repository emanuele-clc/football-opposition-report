"""Evidence grade of the statements of the opposition report (protocol: docs/protocol_evidence_grade.md; definitions and thresholds there, not repeated here).
Usage (from the repo root, data_dir = folder with data_info/ and ev/):
    python -X utf8 src/week4/evidence_grade.py smoke   <data_dir> <work_dir>                 # 2 dev teams x 8 matches, prints counts only
    python -X utf8 src/week4/evidence_grade.py extract <data_dir> <work_dir>                 # all 80 teams -> <work_dir>/teams/*.pkl (skips teams done)
    python -X utf8 src/week4/evidence_grade.py analyse <work_dir> --set dev|confirm         # -> results/evidence_grade_dev.json | results/evidence_grade.json
The analyse step refuses to run if the protocol or this script differ from the last commit, the commit is not on origin/main, or the result file exists.
Per match every statement is a numerator and a denominator computed by the report's own scripts (imported, same definitions)."""
import sys, os, json, glob, pickle, collections, subprocess, warnings
import numpy as np, pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.argv, ARGV = ["x", "none.json", "none", "."], sys.argv     # the report scripts read sys.argv when imported
sys.path[:0] = [os.path.join(REPO, "src", "week2"), os.path.join(REPO, "src", "report")]
import sequences_clustering as S, restarts as RS, setpieces as SP, transitions as TR, defending as DF, xthreat as XTH, keyplayers as KP
sys.argv = ARGV

LEAGUES = {"2_27": "Premier League", "11_27": "La Liga", "12_27": "Serie A", "7_27": "Ligue 1"}
DEV = ["Leicester City", "Arsenal", "Barcelona", "Atlético Madrid", "Real Madrid", "Napoli", "Sassuolo", "Gazélec Ajaccio", "Bordeaux"]
EXCLUDED = ["Juventus"]
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]; CUT = 45; K = {"build-up": 5, "advanced": 3}
SET = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}   # as keyplayers.py
CLAIMS = {"S01": "open-play sequences per match", "S02": "passes per sequence", "S03": "long-pass share of a sequence", "S04": "share of sequences starting in the build-up zone",
          "S05": "shot rate per sequence", "S06": "sequence duration (s)", "F07": "share of each build-up family", "F08": "share of each advanced family",
          "R09": "goal kicks: first pass short", "R10": "goal kicks: reached the opponent half", "R11": "goal kicks: ended in own half", "R12": "keeper: first pass short",
          "R13": "throw-ins in own half: ended in own half", "P14": "corners per match", "P15": "corners played short / outside the box", "P16": "corners to the far post",
          "P17": "corners ending in a shot", "T18": "open-play losses per match", "T19": "losses in own third", "T20": "counter-press regains within 5 s",
          "T21": "recoveries in the final third", "T22": "recoveries followed by a shot within 10 s", "D23": "PPDA", "D24": "pressures per match",
          "D25": "pressures in the final third", "D26": "height of defensive actions", "D27": "shots conceded per match", "D28": "xG conceded per match",
          "A29": "shots per match", "A30": "xG per match", "A31": "xT added per match", "A32": "pass completion under pressure in own half",
          "K33": "share of build-up receptions of the main receiver", "K34": "share of corners taken by the main taker"}
SCALAR = [c for c in CLAIMS if c[0] in "SRPTDA"]; FAM = {"F07": "build-up", "F08": "advanced"}; LEAD = {"K33": "recv", "K34": "ctak"}
MIN_PAST = 5

# every report script reads each event file again: keep the last few parsed files
_load, _cache = json.load, collections.OrderedDict()
def _cached_load(fp, *a, **k):
    name = os.path.normcase(os.path.abspath(getattr(fp, "name", "") or ""))
    if os.sep + "ev" + os.sep not in name: return _load(fp, *a, **k)
    if name in _cache: fp.close(); return _cache[name]
    _cache[name] = _load(fp, *a, **k)
    while len(_cache) > 2: _cache.popitem(last=False)
    return _cache[name]
json.load = _cached_load


# ---------------------------------------------------------------- extraction
def match_values(g, team, base, tmp, full=True):
    """Numerator and denominator of every scalar statement for one match, plus leader counters and the open-play sequences.
    full=False (generic CSV of another provider): no Pressure/Duel events, xG or pass outcomes, so D23-D28, A30-A32 are left out and K33 is not meaningful."""
    with open(tmp, "w", encoding="utf-8") as f: json.dump([g], f)
    for M in (S, RS, SP, TR, DF, XTH): M.MF, M.TEAM, M.BASE = tmp, team, base
    seq = S.extract()[0]; rs = RS.extract()[0]; sp = SP.extract()[0]; tl, tr = TR.extract()[:2]
    ev = json.load(open(os.path.join(base, "ev", f"{g['match_id']}.json"), encoding="utf-8"))
    n = len(seq); V = {}
    V["S01"] = (n, 1)
    for c, num in (("S02", "n_pass"), ("S03", "long_share"), ("S06", "dur"), ("S05", "shot")): V[c] = (float(seq[num].sum()) if n else 0.0, n)
    V["S04"] = (int((seq.x0 < CUT).sum()) if n else 0, n)
    q = lambda kind: rs[rs.kind == kind] if len(rs) else pd.DataFrame(columns=["short", "opp_half", "lost_own_half"])
    gk, kp_, ti = q("Goal kick"), q("Keeper"), q("Throw-in own half")
    V["R09"] = (int(gk.short.sum()), len(gk)); V["R10"] = (int(gk.opp_half.sum()), len(gk)); V["R11"] = (int(gk.lost_own_half.sum()), len(gk))
    V["R12"] = (int(kp_.short.sum()), len(kp_)); V["R13"] = (int(ti.lost_own_half.sum()), len(ti))
    co = sp[sp.kind == "Corner"] if len(sp) else pd.DataFrame(columns=["zone", "shot", "taker"])
    V["P14"] = (len(co), 1); V["P15"] = (int((co.zone == SP.ZONES[0]).sum()), len(co)); V["P16"] = (int((co.zone == "far post").sum()), len(co)); V["P17"] = (int(co.shot.sum()), len(co))
    V["T18"] = (len(tl), 1)
    V["T19"] = (int((tl.third == "own third").sum()) if len(tl) else 0, len(tl)); V["T20"] = (int(tl.regain5.sum()) if len(tl) else 0, len(tl))
    V["T21"] = (int((tr.third == "final third").sum()) if len(tr) else 0, len(tr)); V["T22"] = (int(tr.shot10.sum()) if len(tr) else 0, len(tr))
    shots = [e for e in ev if e["team"]["name"] == team and e["type"]["name"] == "Shot"]; V["A29"] = (len(shots), 1)
    if full:
        per, P = DF.extract()[:2]; xt = XTH.extract()[0][0]; kp = KP.events_view(team, [g["match_id"]], os.path.join(base, "ev")); d = per[0]
        V["D23"] = (d["opp_pass"], d["act_hi"]); V["D24"] = (d["pressures"], 1); V["D25"] = (sum(p["x"] >= 80 for p in P), d["pressures"])
        V["D26"] = (d["def_x_sum"], d["def_actions"]); V["D27"] = (d["shots"], 1); V["D28"] = (d["xg"], 1)
        V["A30"] = (float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in shots)), 1); V["A31"] = (float(xt["xt"]), 1)
        V["A32"] = (sum(z["up_ok"] for z in kp["under_pressure"]), sum(z["under_pressure"] for z in kp["under_pressure"]))
    recv = collections.Counter()
    for e in ev:   # 'builds through' of keyplayers.py: completed open-play passes received in own half
        if e["team"]["name"] != team or "player" not in e or e["type"]["name"] != "Pass": continue
        pa = e["pass"]
        if "outcome" not in pa and pa.get("type", {}).get("name") not in SET and pa.get("recipient") and pa["end_location"][0] < 60: recv[pa["recipient"]["name"]] += 1
    ctak = collections.Counter(co.taker.dropna()) if len(co) else collections.Counter()
    if n: seq = seq.assign(w0=(seq.y0 - 40).abs(), w1=(seq.y1 - 40).abs())[COLS]
    return {c: (float(a), float(b)) for c, (a, b) in V.items()}, recv, ctak, (seq if n else pd.DataFrame(columns=COLS))


def all_teams(data_dir):
    T = []
    for key, lg in LEAGUES.items():
        ms = json.load(open(os.path.join(data_dir, "data_info", f"{key}.json"), encoding="utf-8"))
        for t in sorted({x for g in ms for x in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])}):
            T.append(dict(team=t, league=lg, matches=sorted([g for g in ms if t in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])))
    return T


def extract(data_dir, work, teams, max_matches=None):
    os.makedirs(os.path.join(work, "teams"), exist_ok=True); tmp = os.path.join(work, "one_match.json"); base = os.path.abspath(data_dir)
    for i, t in enumerate(teams):
        out = os.path.join(work, "teams", t["team"].replace(" ", "_") + ".pkl")
        if os.path.exists(out): continue
        ms = t["matches"][:max_matches] if max_matches else t["matches"]; R = dict(team=t["team"], league=t["league"], dates=[], ids=[], V=[], recv=[], ctak=[], seq=[])
        for mi, g in enumerate(ms):
            V, recv, ctak, seq = match_values(g, t["team"], base, tmp)
            R["dates"].append(g["match_date"]); R["ids"].append(g["match_id"]); R["V"].append(V); R["recv"].append(recv); R["ctak"].append(ctak); R["seq"].append(seq.assign(mi=mi))
        R["seq"] = pd.concat(R["seq"], ignore_index=True)
        pickle.dump(R, open(out, "wb")); print(f"[{i + 1}/{len(teams)}] {t['team']} ({t['league']}): {len(ms)} matches, {len(R['seq'])} sequences", flush=True)


# ---------------------------------------------------------------- forecasts
def pi_inside(nums, dens, t, F):
    """80% prediction interval for match t from the matches before t (protocol, Calibration). None if fewer than 3 past matches with data."""
    h = dens[:t] > 0
    if h.sum() < 3: return None
    ys = nums[:t][h] / dens[:t][h]; s2 = float(np.sum(dens[:t][h] * (ys - F) ** 2) / (h.sum() - 1))
    half = stats.t.ppf(0.90, h.sum() - 1) * np.sqrt(s2 * (1 / dens[t] + 1 / dens[:t].sum()))
    return bool(abs(nums[t] / dens[t] - F) <= half)


def forecast_rows(nums, dens, t, B, team, claim, item=""):
    if dens[:t].sum() <= 0 or dens[t] <= 0 or B is None or not np.isfinite(B): return None
    F = nums[:t].sum() / dens[:t].sum(); s5 = dens[max(t - 5, 0):t].sum()
    return dict(team=team, claim=claim, item=item, w=float(dens[t]), y=float(nums[t] / dens[t]), F=float(F), B=float(B),
                L=float(nums[max(t - 5, 0):t].sum() / s5) if s5 > 0 else np.nan, inside=pi_inside(nums, dens, t, F))


def arrays(R, c): return np.array([v[c][0] for v in R["V"]]), np.array([v[c][1] for v in R["V"]])


def leader(counters):
    tot = collections.Counter()
    for c in counters: tot.update(c)
    return sorted(tot.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if tot else None


def fit_families(R, phase):
    s = R["seq"]; nfit = len(R["dates"]) // 2; sub = s[(s.mi < nfit) & ((s.x0 < CUT) if phase == "build-up" else (s.x0 >= CUT))]; k = K[phase]
    sc = StandardScaler().fit(sub[COLS].values); km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(sub[COLS].values))
    order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
    name = {c: f"{'B' if phase == 'build-up' else 'A'}{i + 1}" for i, c in enumerate(order)}
    return lambda d: np.array([name[l] for l in km.predict(sc.transform(d[COLS].values))]) if len(d) else np.array([]), nfit


def all_forecasts(TEAMS, subjects):
    by_league = collections.defaultdict(list)
    for R in TEAMS.values(): by_league[R["league"]].append(R)
    rows = []
    for name in subjects:
        R = TEAMS[name]; others = [U for U in by_league[R["league"]] if U["team"] != name]; n = len(R["dates"])
        for c in SCALAR:   # league baseline: other teams, matches before the date
            nums, dens = arrays(R, c)
            od = [(np.array(U["dates"]), *arrays(U, c)) for U in others]
            for t in range(MIN_PAST, n):
                bn = sum(on[od_ < R["dates"][t]].sum() for od_, on, _ in od); bd = sum(oe[od_ < R["dates"][t]].sum() for od_, _, oe in od)
                r = forecast_rows(nums, dens, t, bn / bd if bd > 0 else None, name, c)
                if r: rows.append(r)
        for c, phase in FAM.items():
            assign, nfit = fit_families(R, phase); ph = lambda s: s[(s.x0 < CUT) if phase == "build-up" else (s.x0 >= CUT)]
            own = ph(R["seq"]); own_lab = assign(own); own_mi = own.mi.values
            oth = [(np.array(U["dates"])[ph(U["seq"]).mi.values], assign(ph(U["seq"]))) for U in others]
            odates = np.concatenate([a for a, _ in oth]); olab = np.concatenate([b for _, b in oth])
            for fam in sorted(set(own_lab)):
                nums = np.array([np.sum((own_mi == mi) & (own_lab == fam)) for mi in range(n)], float); dens = np.array([np.sum(own_mi == mi) for mi in range(n)], float)
                for t in range(max(MIN_PAST, nfit), n):
                    m = odates < R["dates"][t]; r = forecast_rows(nums, dens, t, (olab[m] == fam).mean() if m.any() else None, name, c, fam)
                    if r: rows.append(r)
        for c, key in LEAD.items():
            for t in range(MIN_PAST, n):
                ld = leader(R[key][:t])
                if ld is None: continue
                nums = np.array([cn[ld] for cn in R[key]], float); dens = np.array([sum(cn.values()) for cn in R[key]], float)
                bs = []
                for U in others:
                    k_ = int(np.sum(np.array(U["dates"]) < R["dates"][t]))
                    if k_ < MIN_PAST: continue
                    lu = leader(U[key][:k_]); tot = sum(sum(cn.values()) for cn in U[key][:k_])
                    if lu is not None and tot > 0: bs.append(sum(cn[lu] for cn in U[key][:k_]) / tot)
                r = forecast_rows(nums, dens, t, float(np.mean(bs)) if bs else None, name, c)
                if r: rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- measures
def ratio_ci(d, num, den, B, seed, one_minus):
    """Pooled statistic sum(num)/sum(den) (or 1 minus it) and its 95% interval, bootstrap over teams."""
    g = d.assign(_a=num(d), _b=den(d)).groupby("team")[["_a", "_b"]].sum(); a, b = g._a.values, g._b.values
    i = np.random.default_rng(seed).integers(0, len(a), (B, len(a))); r = a[i].sum(1) / b[i].sum(1); f = (lambda x: 1 - x) if one_minus else (lambda x: x)
    return float(f(a.sum() / b.sum())), sorted([float(f(np.nanpercentile(r, 2.5))), float(f(np.nanpercentile(r, 97.5)))])


se = lambda f: (lambda d: d.w * (d.y - d[f]) ** 2)


def season_series(R, c):
    if c in LEAD:
        ld = leader(R[LEAD[c]]); return np.array([cn[ld] for cn in R[LEAD[c]]], float), np.array([sum(cn.values()) for cn in R[LEAD[c]]], float)
    return arrays(R, c)


def discrimination(TEAMS, subjects, c, rng):
    vals, svar = [], []
    for name in subjects:
        nums, dens = season_series(TEAMS[name], c)
        if dens.sum() <= 0: continue
        vals.append(nums.sum() / dens.sum()); i = rng.integers(0, len(nums), (500, len(nums))); sd_ = dens[i].sum(1); ok = sd_ > 0
        svar.append(np.var(nums[i].sum(1)[ok] / sd_[ok], ddof=1))
    vals, svar = np.array(vals), np.array(svar); D = 1 - svar.mean() / np.var(vals, ddof=1)
    r2 = np.random.default_rng(8); Db = []
    for _ in range(1000):
        i = r2.integers(0, len(vals), len(vals)); Db.append(1 - svar[i].mean() / np.var(vals[i], ddof=1))
    return float(D), [float(np.nanpercentile(Db, 2.5)), float(np.nanpercentile(Db, 97.5))], float(np.mean(vals)), float(np.std(vals, ddof=1))


def matches_needed(TEAMS, subjects, c, sd, rng):
    ratio = {}
    for n in (3, 5, 8, 10, 15, 20):
        p90 = []
        for name in subjects:
            nums, dens = season_series(TEAMS[name], c)
            if dens.sum() <= 0 or n >= len(nums): continue
            full = nums.sum() / dens.sum(); i = np.argsort(rng.random((300, len(nums))), axis=1)[:, :n]; sd_ = dens[i].sum(1); ok = sd_ > 0   # 300 draws without replacement
            if ok.any(): p90.append(np.percentile(np.abs(nums[i].sum(1)[ok] / sd_[ok] - full), 90))
        ratio[str(n)] = float(np.median(p90) / sd) if p90 and sd > 0 else None
    need = next((n for n, r in ratio.items() if r is not None and r <= 0.5), ">20")
    return need, ratio


def grade(fc, disc):
    f_ok = fc in ("strong", "weak"); d_ok = disc in ("high", "medium")
    if disc == "n/a": return "B" if fc == "strong" else ("C" if fc == "weak" else "D")
    if fc == "strong" and disc == "high": return "A"
    if f_ok and d_ok: return "B"
    return "C" if (f_ok or d_ok) else "D"


def analyse(TEAMS, subjects, label):
    fr = all_forecasts(TEAMS, subjects); out = {}; rng7, rng11 = np.random.default_rng(7), np.random.default_rng(11)
    for c, desc in CLAIMS.items():
        d = fr[fr.claim == c]; r = dict(statement=desc, forecasts=int(len(d)), teams=int(d.team.nunique()))
        if len(d):
            r["skill"], r["skill_ci"] = ratio_ci(d, se("F"), se("B"), 2000, 2029, True)
            r["forecast"] = "strong" if r["skill_ci"][0] >= 0.10 else ("weak" if r["skill_ci"][0] > 0 else "none")
            dc = d[d.inside.notna()]; r["coverage_80"], r["coverage_ci"] = ratio_ci(dc, lambda x: x.inside.astype(float), lambda x: 0 * x.w + 1, 1000, 2031, False)
            r["calibration"] = "about right" if 0.75 <= r["coverage_80"] <= 0.85 else ("too narrow" if r["coverage_80"] < 0.75 else "too wide")
            dl = d[d.L.notna()]; r["last5_vs_season"], r["last5_ci"] = ratio_ci(dl, se("L"), se("F"), 2000, 2030, True)
            r["last5_verdict"] = "last 5 better" if r["last5_ci"][0] > 0 else ("season better" if r["last5_ci"][1] < 0 else "no difference")
        else: r["forecast"] = "none"
        if c in FAM:
            r["discrimination"] = "n/a"; r["matches_needed"] = "n/a"; r["items"] = int(d.groupby(["team", "item"]).ngroups)
        else:
            D, Dci, mean, sd = discrimination(TEAMS, subjects, c, rng7); r.update(D=D, D_ci=Dci, mean_between_teams=mean, sd_between_teams=sd)
            r["discrimination"] = "high" if D >= 0.7 else ("medium" if D >= 0.5 else "low")
            r["matches_needed"], r["error_p90_over_sd"] = matches_needed(TEAMS, subjects, c, sd, rng11)
        r["grade"] = grade(r["forecast"], r["discrimination"]); out[c] = r
        print(f"{c} {desc[:48]:48} n={r['forecasts']:5d}  skill {r.get('skill', np.nan):+.3f} {r['forecast']:6}  D {r.get('D', np.nan):+.2f} {r['discrimination']:6}  "
              f"cover {r.get('coverage_80', np.nan):.2f}  need {r['matches_needed']:>4}  -> {r['grade']}", flush=True)
    sc = {"SC1 counter-press share has low discrimination": out["T20"]["discrimination"] == "low",
          "SC2 passes per sequence: high discrimination and strong forecast": out["S02"]["discrimination"] == "high" and out["S02"]["forecast"] == "strong"}
    return dict(protocol="docs/protocol_evidence_grade.md", set=label, teams=sorted(subjects), n_teams=len(subjects),
                grades=dict(collections.Counter(r["grade"] for r in out.values())), sanity_checks=sc, statements=out,
                note="Grades of statement types, not of single teams. Forecast = season so far vs the league average of the other teams; descriptive, see the protocol for limits.")


def guard(out):
    files = ["docs/protocol_evidence_grade.md", "src/week4/evidence_grade.py"]
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)
    if os.path.exists(out): sys.exit(f"{out} already exists: the run is done once (protocol, Procedure).")
    if git("ls-files", "--error-unmatch", *files).returncode: sys.exit("Commit the protocol and this script first.")
    if git("diff", "--quiet", "HEAD", "--", *files).returncode: sys.exit("The protocol or the script differ from the last commit: commit them first.")
    c = git("log", "-1", "--format=%H", "--", files[0]).stdout.strip()
    if git("merge-base", "--is-ancestor", c, "origin/main").returncode: sys.exit("The protocol commit is not on origin/main: push it first.")


def load_teams(work): return {R["team"]: R for R in (pickle.load(open(f, "rb")) for f in sorted(glob.glob(os.path.join(work, "teams", "*.pkl"))))}


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] not in ("smoke", "extract", "analyse"): sys.exit(__doc__)
    if a[0] == "extract":
        extract(a[1], a[2], all_teams(a[1]))
    elif a[0] == "smoke":   # code check only: counts, never a value
        work = os.path.join(a[2], "smoke"); T = [t for t in all_teams(a[1]) if t["team"] in ("Leicester City", "Arsenal")]
        extract(a[1], work, T, max_matches=8); TEAMS = load_teams(work); fr = all_forecasts(TEAMS, list(TEAMS))
        print("forecast rows per statement:", dict(fr.groupby("claim").size())); print("missing statements:", sorted(set(CLAIMS) - set(fr.claim)))
        for c in SCALAR + list(LEAD): discrimination(TEAMS, list(TEAMS), c, np.random.default_rng(7))
        print("smoke test passed (no values printed)")
    else:
        which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else ""
        if which not in ("dev", "confirm"): sys.exit("--set dev or --set confirm")
        out = os.path.join(REPO, "results", "evidence_grade_dev.json" if which == "dev" else "evidence_grade.json"); guard(out)
        TEAMS = load_teams(a[1]); subjects = [t for t in TEAMS if t in DEV] if which == "dev" else [t for t in TEAMS if t not in DEV + EXCLUDED]
        exp = 9 if which == "dev" else 70
        if len(subjects) != exp or len(TEAMS) != 80: sys.exit(f"expected 80 extracted teams and {exp} subjects, found {len(TEAMS)} and {len(subjects)}: run extract first")
        res = analyse(TEAMS, subjects, which); json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("grades:", res["grades"], "| sanity checks:", res["sanity_checks"], "->", out)
