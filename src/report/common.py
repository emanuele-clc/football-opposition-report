"""Small functions used by several report sheets (restarts, setpieces, transitions, defending, xthreat, matchups, make_report)."""

import io, json, base64
import numpy as np

THIRDS = ["own third", "middle third", "final third"]


def team_matches(mf, team):
    # the matches of the team in the match list, in date order
    matches = []
    for g in json.load(open(mf, encoding="utf-8")):
        if team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"]):
            matches.append(g)
    matches.sort(key=lambda g: g["match_date"])
    return matches


def opponent(g, team):
    if g["home_team"]["home_team_name"] == team:
        return g["away_team"]["away_team_name"]
    return g["home_team"]["home_team_name"]


def third(x):
    # own third (x < 40), middle third, final third (x >= 80), on a 120 m pitch
    if x < 40:
        return THIRDS[0]
    if x < 80:
        return THIRDS[1]
    return THIRDS[2]


def is_type(e, name):
    return e["type"]["name"] == name


def boot(values, gi, games, B=1000, seed=0):
    # 95% interval of the mean of values, resampling whole matches (gi = match of each value)
    rng = np.random.default_rng(seed)
    by_match = {g: values[gi == g] for g in games}
    means = []
    for _ in range(B):
        v = np.concatenate([by_match[g] for g in rng.choice(games, len(games))])
        means.append(v.mean() if len(v) else np.nan)
    return [float(np.nanpercentile(means, 2.5)), float(np.nanpercentile(means, 97.5))]


def boot_stat(stat, games, B=1000, seed=0):
    # 95% interval of any statistic stat(matches), resampling whole matches
    rng = np.random.default_rng(seed)
    out = [stat(rng.choice(games, len(games))) for _ in range(B)]
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]


def pc(x):
    # 0.234 -> "23%" (empty if missing)
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return f"{100 * x:.0f}%"


def ci(c):
    # [0.21, 0.27] -> "21-27%"
    if not c:
        return ""
    return f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"


def fig_png(fig, dpi=110, tight=True):
    # matplotlib figure -> picture that can sit inside the HTML page
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    if tight:
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    else:
        fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
