"""Evidence grade (A-D) of the statements of the opposition report. Protocol: docs/protocol_evidence_grade.md (definitions and thresholds are there).
Usage (from the repo root, data_dir = folder with data_info/ and ev/):
    python -X utf8 src/analysis/evidence_grade.py extract <data_dir> <work_dir>          # all 80 teams -> <work_dir>/teams/*.pkl
    python -X utf8 src/analysis/evidence_grade.py analyse <work_dir> --set dev|confirm  [--corrected <data_dir>]
The analyse step stops if the protocol or this script are not committed and pushed, or if the result file already exists (it runs once).
For every match each statement is a numerator and a denominator, computed with the report's own scripts (imported).
The smoke test run before the protocol (2 teams x 8 matches, counts only) is in archive/smoke_grade.py."""

import sys, os, json, glob, pickle, collections, subprocess, warnings
import numpy as np, pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# the report scripts read sys.argv when they are imported: give them a dummy one
ARGV = sys.argv
sys.argv = ["x", "none.json", "none", "."]
sys.path.insert(0, os.path.join(REPO, "src", "report"))
sys.path.insert(0, os.path.join(REPO, "src", "analysis"))
import sequences_clustering as S
import restarts as RS
import setpieces as SP
import transitions as TR
import defending as DF
import xthreat as XTH
import keyplayers as KP

sys.argv = ARGV

LEAGUES = {"2_27": "Premier League", "11_27": "La Liga", "12_27": "Serie A", "7_27": "Ligue 1"}
# the 9 thesis teams of these seasons (development set) and Juventus (already looked at)
DEV = ["Leicester City", "Arsenal", "Barcelona", "Atlético Madrid", "Real Madrid", "Napoli", "Sassuolo", "Gazélec Ajaccio", "Bordeaux"]
EXCLUDED = ["Juventus"]
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"build-up": 5, "advanced": 3}
SET = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}  # set-piece passes, as in keyplayers.py
CLAIMS = {
    "S01": "open-play sequences per match",
    "S02": "passes per sequence",
    "S03": "long-pass share of a sequence",
    "S04": "share of sequences starting in the build-up zone",
    "S05": "shot rate per sequence",
    "S06": "sequence duration (s)",
    "F07": "share of each build-up family",
    "F08": "share of each advanced family",
    "R09": "goal kicks: first pass short",
    "R10": "goal kicks: reached the opponent half",
    "R11": "goal kicks: ended in own half",
    "R12": "keeper: first pass short",
    "R13": "throw-ins in own half: ended in own half",
    "P14": "corners per match",
    "P15": "corners played short / outside the box",
    "P16": "corners to the far post",
    "P17": "corners ending in a shot",
    "T18": "open-play losses per match",
    "T19": "losses in own third",
    "T20": "counter-press regains within 5 s",
    "T21": "recoveries in the final third",
    "T22": "recoveries followed by a shot within 10 s",
    "D23": "PPDA",
    "D24": "pressures per match",
    "D25": "pressures in the final third",
    "D26": "height of defensive actions",
    "D27": "shots conceded per match",
    "D28": "xG conceded per match",
    "A29": "shots per match",
    "A30": "xG per match",
    "A31": "xT added per match",
    "A32": "pass completion under pressure in own half",
    "K33": "share of build-up receptions of the main receiver",
    "K34": "share of corners taken by the main taker",
}
SCALAR = [c for c in CLAIMS if c[0] in "SRPTDA"]  # one number per match
FAM = {"F07": "build-up", "F08": "advanced"}  # family shares
LEAD = {"K33": "recv", "K34": "ctak"}  # main player
MIN_PAST = 5  # forecasts start from the 6th match

# every report script opens the same event file again: keep the last two in memory (speed only)
_load = json.load
_cache = collections.OrderedDict()


def _cached_load(fp, *a, **k):
    name = os.path.normcase(os.path.abspath(getattr(fp, "name", "") or ""))
    if os.sep + "ev" + os.sep not in name:
        return _load(fp, *a, **k)
    if name in _cache:
        fp.close()
        return _cache[name]
    _cache[name] = _load(fp, *a, **k)
    while len(_cache) > 2:
        _cache.popitem(last=False)
    return _cache[name]


json.load = _cached_load


# ---------------------------------------------------------------- per match values
def match_values(g, team, base, tmp, full=True):
    """(numerator, denominator) of every statement in one match, the counters for the main players, and the sequences.
    full=False: data without pressures, xG or pass outcomes (other providers), so D23-D28 and A30-A32 are skipped."""
    # the report scripts read a match list: write one with only this match
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([g], f)
    for M in (S, RS, SP, TR, DF, XTH):
        M.MF = tmp
        M.TEAM = team
        M.BASE = base
    seq = S.extract()[0]
    rs = RS.extract()[0]
    sp = SP.extract()[0]
    losses, recoveries = TR.extract()[:2]
    ev = json.load(open(os.path.join(base, "ev", f"{g['match_id']}.json"), encoding="utf-8"))
    n = len(seq)

    V = {}
    V["S01"] = (n, 1)
    for c, col in (("S02", "n_pass"), ("S03", "long_share"), ("S06", "dur"), ("S05", "shot")):
        if n:
            V[c] = (float(seq[col].sum()), n)
        else:
            V[c] = (0.0, n)
    V["S04"] = (int((seq.x0 < CUT).sum()) if n else 0, n)

    def restarts_of(kind):
        if len(rs):
            return rs[rs.kind == kind]
        return pd.DataFrame(columns=["short", "opp_half", "lost_own_half"])

    gk = restarts_of("Goal kick")
    keeper = restarts_of("Keeper")
    throw = restarts_of("Throw-in own half")
    V["R09"] = (int(gk.short.sum()), len(gk))
    V["R10"] = (int(gk.opp_half.sum()), len(gk))
    V["R11"] = (int(gk.lost_own_half.sum()), len(gk))
    V["R12"] = (int(keeper.short.sum()), len(keeper))
    V["R13"] = (int(throw.lost_own_half.sum()), len(throw))

    if len(sp):
        co = sp[sp.kind == "Corner"]
    else:
        co = pd.DataFrame(columns=["zone", "shot", "taker"])
    V["P14"] = (len(co), 1)
    V["P15"] = (int((co.zone == SP.ZONES[0]).sum()), len(co))
    V["P16"] = (int((co.zone == "far post").sum()), len(co))
    V["P17"] = (int(co.shot.sum()), len(co))

    nl, nr = len(losses), len(recoveries)
    V["T18"] = (nl, 1)
    V["T19"] = (int((losses.third == "own third").sum()) if nl else 0, nl)
    V["T20"] = (int(losses.regain5.sum()) if nl else 0, nl)
    V["T21"] = (int((recoveries.third == "final third").sum()) if nr else 0, nr)
    V["T22"] = (int(recoveries.shot10.sum()) if nr else 0, nr)

    shots = [e for e in ev if e["team"]["name"] == team and e["type"]["name"] == "Shot"]
    V["A29"] = (len(shots), 1)
    if full:
        per_match, pressures = DF.extract()[:2]
        xt = XTH.extract()[0][0]
        kp = KP.events_view(team, [g["match_id"]], os.path.join(base, "ev"))
        d = per_match[0]
        V["D23"] = (d["opp_pass"], d["act_hi"])
        V["D24"] = (d["pressures"], 1)
        V["D25"] = (sum(p["x"] >= 80 for p in pressures), d["pressures"])
        V["D26"] = (d["def_x_sum"], d["def_actions"])
        V["D27"] = (d["shots"], 1)
        V["D28"] = (d["xg"], 1)
        V["A30"] = (float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in shots)), 1)
        V["A31"] = (float(xt["xt"]), 1)
        V["A32"] = (sum(z["up_ok"] for z in kp["under_pressure"]), sum(z["under_pressure"] for z in kp["under_pressure"]))

    # who receives the build-up passes: completed open-play passes received in our half (as in keyplayers.py)
    recv = collections.Counter()
    for e in ev:
        if e["team"]["name"] != team or "player" not in e or e["type"]["name"] != "Pass":
            continue
        pa = e["pass"]
        if "outcome" in pa or pa.get("type", {}).get("name") in SET:
            continue
        if pa.get("recipient") and pa["end_location"][0] < 60:
            recv[pa["recipient"]["name"]] += 1
    # who takes the corners
    if len(co):
        ctak = collections.Counter(co.taker.dropna())
    else:
        ctak = collections.Counter()

    if n:
        seq = seq.assign(w0=(seq.y0 - 40).abs(), w1=(seq.y1 - 40).abs())[COLS]
    else:
        seq = pd.DataFrame(columns=COLS)
    values = {}
    for c, (a, b) in V.items():
        values[c] = (float(a), float(b))
    return values, recv, ctak, seq


def all_teams(data_dir):
    teams = []
    for key, league in LEAGUES.items():
        ms = json.load(open(os.path.join(data_dir, "data_info", f"{key}.json"), encoding="utf-8"))
        names = set()
        for g in ms:
            names.add(g["home_team"]["home_team_name"])
            names.add(g["away_team"]["away_team_name"])
        for t in sorted(names):
            own = [g for g in ms if t in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
            own.sort(key=lambda g: g["match_date"])
            teams.append({"team": t, "league": league, "matches": own})
    return teams


def extract(data_dir, work, teams, max_matches=None):
    # one pickle per team with the values of every match; teams already done are skipped
    os.makedirs(os.path.join(work, "teams"), exist_ok=True)
    tmp = os.path.join(work, "one_match.json")
    base = os.path.abspath(data_dir)
    for i, t in enumerate(teams):
        out = os.path.join(work, "teams", t["team"].replace(" ", "_") + ".pkl")
        if os.path.exists(out):
            continue
        ms = t["matches"][:max_matches] if max_matches else t["matches"]
        R = {"team": t["team"], "league": t["league"], "dates": [], "ids": [], "V": [], "recv": [], "ctak": [], "seq": []}
        for mi, g in enumerate(ms):
            V, recv, ctak, seq = match_values(g, t["team"], base, tmp)
            R["dates"].append(g["match_date"])
            R["ids"].append(g["match_id"])
            R["V"].append(V)
            R["recv"].append(recv)
            R["ctak"].append(ctak)
            R["seq"].append(seq.assign(mi=mi))
        R["seq"] = pd.concat(R["seq"], ignore_index=True)
        pickle.dump(R, open(out, "wb"))
        print(f"[{i + 1}/{len(teams)}] {t['team']} ({t['league']}): {len(ms)} matches, {len(R['seq'])} sequences", flush=True)


# ---------------------------------------------------------------- forecasts
def pi_inside(nums, dens, t, F):
    # is match t inside the 80% prediction interval made from the matches before it? None if fewer than 3 past matches
    h = dens[:t] > 0
    if h.sum() < 3:
        return None
    ys = nums[:t][h] / dens[:t][h]
    s2 = float(np.sum(dens[:t][h] * (ys - F) ** 2) / (h.sum() - 1))
    half = stats.t.ppf(0.90, h.sum() - 1) * np.sqrt(s2 * (1 / dens[t] + 1 / dens[:t].sum()))
    return bool(abs(nums[t] / dens[t] - F) <= half)


def forecast_rows(nums, dens, t, B, team, claim, item=""):
    # one forecast of match t: F = season so far, B = league average, L = last 5 matches
    if dens[:t].sum() <= 0 or dens[t] <= 0 or B is None or not np.isfinite(B):
        return None
    F = nums[:t].sum() / dens[:t].sum()
    start = max(t - 5, 0)
    s5 = dens[start:t].sum()
    if s5 > 0:
        L = float(nums[start:t].sum() / s5)
    else:
        L = np.nan
    return {
        "team": team,
        "claim": claim,
        "item": item,
        "w": float(dens[t]),
        "y": float(nums[t] / dens[t]),
        "F": float(F),
        "B": float(B),
        "L": L,
        "inside": pi_inside(nums, dens, t, F),
    }


def arrays(R, c):
    nums = np.array([v[c][0] for v in R["V"]])
    dens = np.array([v[c][1] for v in R["V"]])
    return nums, dens


def leader(counters):
    # player with the highest total (ties: first name in alphabetical order)
    total = collections.Counter()
    for c in counters:
        total.update(c)
    if not total:
        return None
    return sorted(total.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def in_phase(s, phase):
    if phase == "build-up":
        return s[s.x0 < CUT]
    return s[s.x0 >= CUT]


def fit_families(R, phase):
    # families fitted on the first half of the season; returns a function that labels sequences
    s = R["seq"]
    nfit = len(R["dates"]) // 2
    sub = in_phase(s[s.mi < nfit], phase)
    k = K[phase]
    scaler = StandardScaler().fit(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(scaler.transform(sub[COLS].values))
    lab = km.labels_
    order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
    letter = "B" if phase == "build-up" else "A"
    name = {}
    for i, c in enumerate(order):
        name[c] = f"{letter}{i + 1}"

    def assign(d):
        if not len(d):
            return np.array([])
        return np.array([name[l] for l in km.predict(scaler.transform(d[COLS].values))])

    return assign, nfit


def all_forecasts(TEAMS, subjects):
    by_league = collections.defaultdict(list)
    for R in TEAMS.values():
        by_league[R["league"]].append(R)
    rows = []
    for name in subjects:
        R = TEAMS[name]
        others = [U for U in by_league[R["league"]] if U["team"] != name]
        n = len(R["dates"])

        # one number per match: the baseline is the other teams of the league, matches before that date
        for c in SCALAR:
            nums, dens = arrays(R, c)
            other = []
            for U in others:
                on, oe = arrays(U, c)
                other.append((np.array(U["dates"]), on, oe))
            for t in range(MIN_PAST, n):
                bn = sum(on[od < R["dates"][t]].sum() for od, on, _ in other)
                bd = sum(oe[od < R["dates"][t]].sum() for od, _, oe in other)
                r = forecast_rows(nums, dens, t, bn / bd if bd > 0 else None, name, c)
                if r:
                    rows.append(r)

        # family shares: families of this team, the other teams' sequences labelled with them
        for c, phase in FAM.items():
            assign, nfit = fit_families(R, phase)
            own = in_phase(R["seq"], phase)
            own_lab = assign(own)
            own_mi = own.mi.values
            odates, olab = [], []
            for U in others:
                us = in_phase(U["seq"], phase)
                odates.append(np.array(U["dates"])[us.mi.values])
                olab.append(assign(us))
            odates = np.concatenate(odates)
            olab = np.concatenate(olab)
            for fam in sorted(set(own_lab)):
                nums = np.array([np.sum((own_mi == mi) & (own_lab == fam)) for mi in range(n)], float)
                dens = np.array([np.sum(own_mi == mi) for mi in range(n)], float)
                for t in range(max(MIN_PAST, nfit), n):
                    before = odates < R["dates"][t]
                    B = (olab[before] == fam).mean() if before.any() else None
                    r = forecast_rows(nums, dens, t, B, name, c, fam)
                    if r:
                        rows.append(r)

        # main player: share of the leader so far; baseline = same share of the leaders of the other teams
        for c, key in LEAD.items():
            for t in range(MIN_PAST, n):
                ld = leader(R[key][:t])
                if ld is None:
                    continue
                nums = np.array([cn[ld] for cn in R[key]], float)
                dens = np.array([sum(cn.values()) for cn in R[key]], float)
                shares = []
                for U in others:
                    k = int(np.sum(np.array(U["dates"]) < R["dates"][t]))
                    if k < MIN_PAST:
                        continue
                    lu = leader(U[key][:k])
                    tot = sum(sum(cn.values()) for cn in U[key][:k])
                    if lu is not None and tot > 0:
                        shares.append(sum(cn[lu] for cn in U[key][:k]) / tot)
                B = float(np.mean(shares)) if shares else None
                r = forecast_rows(nums, dens, t, B, name, c)
                if r:
                    rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- measures
def ratio_ci(d, num, den, B, seed, one_minus):
    # sum(num) / sum(den) over all rows (or 1 minus it) with a 95% interval, resampling teams
    g = d.assign(_a=num(d), _b=den(d)).groupby("team")[["_a", "_b"]].sum()
    a = g._a.values
    b = g._b.values
    i = np.random.default_rng(seed).integers(0, len(a), (B, len(a)))
    r = a[i].sum(1) / b[i].sum(1)
    value = a.sum() / b.sum()
    lo = np.nanpercentile(r, 2.5)
    hi = np.nanpercentile(r, 97.5)
    if one_minus:
        value, lo, hi = 1 - value, 1 - lo, 1 - hi
    return float(value), sorted([float(lo), float(hi)])


def se(col):
    # squared error of the forecast in column col, weighted by the denominator of the match
    def f(d):
        return d.w * (d.y - d[col]) ** 2

    return f


def season_series(R, c):
    if c in LEAD:
        ld = leader(R[LEAD[c]])
        nums = np.array([cn[ld] for cn in R[LEAD[c]]], float)
        dens = np.array([sum(cn.values()) for cn in R[LEAD[c]]], float)
        return nums, dens
    return arrays(R, c)


def discrimination(TEAMS, subjects, c, rng):
    # D = 1 - (noise within a team) / (variance between teams); near 1 = the number separates teams
    vals, noise = [], []
    for name in subjects:
        nums, dens = season_series(TEAMS[name], c)
        if dens.sum() <= 0:
            continue
        vals.append(nums.sum() / dens.sum())
        i = rng.integers(0, len(nums), (500, len(nums)))
        sd = dens[i].sum(1)
        ok = sd > 0
        noise.append(np.var(nums[i].sum(1)[ok] / sd[ok], ddof=1))
    vals = np.array(vals)
    noise = np.array(noise)
    D = 1 - noise.mean() / np.var(vals, ddof=1)
    r2 = np.random.default_rng(8)
    Db = []
    for _ in range(1000):
        i = r2.integers(0, len(vals), len(vals))
        Db.append(1 - noise[i].mean() / np.var(vals[i], ddof=1))
    ci = [float(np.nanpercentile(Db, 2.5)), float(np.nanpercentile(Db, 97.5))]
    return float(D), ci, float(np.mean(vals)), float(np.std(vals, ddof=1))


def matches_needed(TEAMS, subjects, c, sd, rng):
    # error with only n matches (90th percentile, 300 random draws without replacement) divided by the spread between teams
    ratio = {}
    for n in (3, 5, 8, 10, 15, 20):
        p90 = []
        for name in subjects:
            nums, dens = season_series(TEAMS[name], c)
            if dens.sum() <= 0 or n >= len(nums):
                continue
            full = nums.sum() / dens.sum()
            i = np.argsort(rng.random((300, len(nums))), axis=1)[:, :n]
            s = dens[i].sum(1)
            ok = s > 0
            if ok.any():
                p90.append(np.percentile(np.abs(nums[i].sum(1)[ok] / s[ok] - full), 90))
        if p90 and sd > 0:
            ratio[str(n)] = float(np.median(p90) / sd)
        else:
            ratio[str(n)] = None
    need = ">20"
    for n, r in ratio.items():
        if r is not None and r <= 0.5:
            need = n
            break
    return need, ratio


def grade(fc, disc):
    f_ok = fc in ("strong", "weak")
    d_ok = disc in ("high", "medium")
    if disc == "n/a":  # family shares: only the forecast counts
        if fc == "strong":
            return "B"
        if fc == "weak":
            return "C"
        return "D"
    if fc == "strong" and disc == "high":
        return "A"
    if f_ok and d_ok:
        return "B"
    if f_ok or d_ok:
        return "C"
    return "D"


def inside_share(x):
    return x.inside.astype(float)


def ones(x):
    return 0 * x.w + 1


def analyse(TEAMS, subjects, label):
    fr = all_forecasts(TEAMS, subjects)
    out = {}
    rng7 = np.random.default_rng(7)
    rng11 = np.random.default_rng(11)
    for c, desc in CLAIMS.items():
        d = fr[fr.claim == c]
        r = {"statement": desc, "forecasts": int(len(d)), "teams": int(d.team.nunique())}
        if len(d):
            # forecast skill: season so far against the league average
            r["skill"], r["skill_ci"] = ratio_ci(d, se("F"), se("B"), 2000, 2029, True)
            if r["skill_ci"][0] >= 0.10:
                r["forecast"] = "strong"
            elif r["skill_ci"][0] > 0:
                r["forecast"] = "weak"
            else:
                r["forecast"] = "none"
            # how often the 80% interval contains the next match
            dc = d[d.inside.notna()]
            r["coverage_80"], r["coverage_ci"] = ratio_ci(dc, inside_share, ones, 1000, 2031, False)
            if 0.75 <= r["coverage_80"] <= 0.85:
                r["calibration"] = "about right"
            elif r["coverage_80"] < 0.75:
                r["calibration"] = "too narrow"
            else:
                r["calibration"] = "too wide"
            # last 5 matches against the whole season so far
            dl = d[d.L.notna()]
            r["last5_vs_season"], r["last5_ci"] = ratio_ci(dl, se("L"), se("F"), 2000, 2030, True)
            if r["last5_ci"][0] > 0:
                r["last5_verdict"] = "last 5 better"
            elif r["last5_ci"][1] < 0:
                r["last5_verdict"] = "season better"
            else:
                r["last5_verdict"] = "no difference"
        else:
            r["forecast"] = "none"

        if c in FAM:
            r["discrimination"] = "n/a"
            r["matches_needed"] = "n/a"
            r["items"] = int(d.groupby(["team", "item"]).ngroups)
        else:
            D, D_ci, mean, sd = discrimination(TEAMS, subjects, c, rng7)
            r["D"] = D
            r["D_ci"] = D_ci
            r["mean_between_teams"] = mean
            r["sd_between_teams"] = sd
            if D >= 0.7:
                r["discrimination"] = "high"
            elif D >= 0.5:
                r["discrimination"] = "medium"
            else:
                r["discrimination"] = "low"
            r["matches_needed"], r["error_p90_over_sd"] = matches_needed(TEAMS, subjects, c, sd, rng11)
        r["grade"] = grade(r["forecast"], r["discrimination"])
        out[c] = r
        print(
            f"{c} {desc[:48]:48} n={r['forecasts']:5d}  skill {r.get('skill', np.nan):+.3f} {r['forecast']:6}  D {r.get('D', np.nan):+.2f} {r['discrimination']:6}  "
            f"cover {r.get('coverage_80', np.nan):.2f}  need {r['matches_needed']:>4}  -> {r['grade']}",
            flush=True,
        )

    checks = {
        "SC1 counter-press share has low discrimination": out["T20"]["discrimination"] == "low",
        "SC2 passes per sequence: high discrimination and strong forecast": out["S02"]["discrimination"] == "high"
        and out["S02"]["forecast"] == "strong",
    }
    return {
        "protocol": "docs/protocol_evidence_grade.md",
        "set": label,
        "teams": sorted(subjects),
        "n_teams": len(subjects),
        "grades": dict(collections.Counter(r["grade"] for r in out.values())),
        "sanity_checks": checks,
        "statements": out,
        "note": "Grades of statement types, not of single teams. Forecast = season so far vs the league average of the other teams; descriptive, see the protocol for limits.",
    }


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def guard(out, files):
    # the confirmatory run happens once, with committed and pushed code
    if os.path.exists(out):
        sys.exit(f"{out} already exists: the run is done once (protocol, Procedure).")
    if git("ls-files", "--error-unmatch", *files).returncode:
        sys.exit("Commit the protocol and the scripts first.")
    if git("diff", "--quiet", "HEAD", "--", *files).returncode:
        sys.exit("The protocol or the scripts differ from the last commit: commit them first.")
    c = git("log", "-1", "--format=%H", "--", files[0]).stdout.strip()
    if git("merge-base", "--is-ancestor", c, "origin/main").returncode:
        sys.exit("The protocol commit is not on origin/main: push it first.")


def drop_missing(TEAMS, data_dir):
    """Correction of 19 Oct (protocol, note 1): drop the matches whose event file does not contain the team's name
    (StatsBomb sometimes names the team differently there, e.g. 'Marseille'): the team's data are missing, not zero."""
    dropped = {}
    for name, R in TEAMS.items():
        keep = []
        for i, m in enumerate(R["ids"]):
            events = _load(open(os.path.join(data_dir, "ev", f"{m}.json"), encoding="utf-8"))
            if name in {e["team"]["name"] for e in events}:
                keep.append(i)
        if len(keep) == len(R["ids"]):
            continue
        dropped[name] = [R["ids"][i] for i in range(len(R["ids"])) if i not in keep]
        new_index = {}
        for j, i in enumerate(keep):
            new_index[i] = j
        for k in ("dates", "ids", "V", "recv", "ctak"):
            R[k] = [R[k][i] for i in keep]
        seq = R["seq"][R["seq"].mi.isin(keep)]
        R["seq"] = seq.assign(mi=seq.mi.map(new_index))
    return dropped


def load_teams(work):
    TEAMS = {}
    for f in sorted(glob.glob(os.path.join(work, "teams", "*.pkl"))):
        R = pickle.load(open(f, "rb"))
        TEAMS[R["team"]] = R
    return TEAMS


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] not in ("extract", "analyse"):
        sys.exit(__doc__)

    if a[0] == "extract":
        extract(a[1], a[2], all_teams(a[1]))

    else:
        which = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else ""
        if which not in ("dev", "confirm"):
            sys.exit("--set dev or --set confirm")
        corrected = sys.argv[sys.argv.index("--corrected") + 1] if "--corrected" in sys.argv else None  # data dir, protocol note 1
        if corrected and which != "confirm":
            sys.exit("--corrected is only for the confirmatory set (protocol note 1)")
        if which == "dev":
            out = os.path.join(REPO, "results", "evidence_grade_dev.json")
        elif corrected:
            out = os.path.join(REPO, "results", "evidence_grade_corrected.json")
        else:
            out = os.path.join(REPO, "results", "evidence_grade.json")
        guard(out, ["docs/protocol_evidence_grade.md", "src/analysis/evidence_grade.py"])

        TEAMS = load_teams(a[1])
        dropped = {}
        if corrected:
            dropped = drop_missing(TEAMS, corrected)
            print("dropped team-matches (team name not in the events):", {t: len(v) for t, v in dropped.items()})
        if which == "dev":
            subjects = [t for t in TEAMS if t in DEV]
            expected = 9
        else:
            subjects = [t for t in TEAMS if t not in DEV + EXCLUDED]
            expected = 70
        if len(subjects) != expected or len(TEAMS) != 80:
            sys.exit(f"expected 80 extracted teams and {expected} subjects, found {len(TEAMS)} and {len(subjects)}: run extract first")

        res = analyse(TEAMS, subjects, which + ("-corrected" if corrected else ""))
        if corrected:
            res["correction"] = {
                "note": "protocol note 1 (19 Oct 2026)",
                "dropped_team_matches": {t: [int(m) for m in v] for t, v in dropped.items()},
            }
        json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("grades:", res["grades"], "| sanity checks:", res["sanity_checks"], "->", out)
