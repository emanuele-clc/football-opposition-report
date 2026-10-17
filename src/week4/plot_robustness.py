"""Figures for the exploratory robustness checks and the second-provider test (thesis, January). Reads only results/.
Usage: python -X utf8 src/week4/plot_robustness.py   ->  figures/fig_methods.png, figures/fig_sensitivity.png, figures/fig_provider_napoli.png"""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); RES = os.path.join(ROOT, "results"); FIG = os.path.join(ROOT, "figures")
TEAMS = ["Bayer Leverkusen", "Leicester City", "Barcelona", "Arsenal", "Atlético Madrid", "Real Madrid", "Napoli", "Sassuolo", "Gazélec Ajaccio", "Bordeaux"]
R = {t: json.load(open(os.path.join(RES, f"exploratory_robustness_{t.replace(' ', '_')}.json"), encoding="utf-8")) for t in TEAMS}
INK, MUTED, GRID = "#121a33", "#5b6584", "#dfe3ee"; C = {"kmeans": "#1d6fd1", "gmm": "#d4a017", "ward": "#3c9a2a"}
plt.rcParams.update({"font.family": "Calibri", "font.size": 12, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "axes.edgecolor": GRID})
SRC = lambda fig, s, note=". EXPLORATORY, exploration matches only.": fig.text(0.01, 0.012, "Source: " + s + note, fontsize=9, color=MUTED)

# 1. Methods: stability and agreement with K-Means (build-up)
fig, axs = plt.subplots(1, 2, figsize=(12, 6)); fig.subplots_adjust(0.17, 0.2, 0.98, 0.84, wspace=0.08)
fig.text(0.02, 0.94, "Same data, other algorithms: K-Means is the most stable, and the others find different families", fontsize=16, fontweight="bold", color=INK)
fig.text(0.02, 0.895, "Build-up, k = 5. Left: stability (mean Jaccard, bootstrap over matches). Right: agreement with K-Means (adjusted Rand index; 1 = same families)", fontsize=11, color=MUTED)
y = np.arange(len(TEAMS))[::-1]
for m, lab, off in (("kmeans", "K-Means", 0.22), ("gmm", "Gaussian mixture", 0), ("ward", "Hierarchical (Ward)", -0.22)):
    axs[0].barh(y + off, [R[t]["metodi"]["costruzione"][m]["jaccard"] for t in TEAMS], 0.2, color=C[m], label=lab)
    if m != "kmeans": axs[1].barh(y + off, [R[t]["metodi"]["costruzione"][m]["ari_vs_kmeans"] for t in TEAMS], 0.2, color=C[m])
axs[0].set_yticks(y); axs[0].set_yticklabels(TEAMS); axs[0].set_xlim(0, 1); axs[0].set_xlabel("stability"); axs[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=10)
axs[1].set_yticks(y); axs[1].set_yticklabels([]); axs[1].set_xlim(0, 1); axs[1].set_xlabel("agreement with K-Means (ARI)"); axs[1].axvline(1, color=C["kmeans"], lw=2)
for ax in axs: ax.grid(axis="y", visible=False)
SRC(fig, "results/exploratory_robustness_<Team>.json"); fig.savefig(os.path.join(FIG, "fig_methods.png"), dpi=200, facecolor="white"); plt.close(fig)

# 2. Sensitivity: margin over the Gaussian null by choice of k and cut
keys = [("costruzione_x45_k4", "build-up\nk=4"), ("costruzione_x45_k5", "build-up\nk=5 (thesis)"), ("costruzione_x45_k6", "build-up\nk=6"), ("costruzione_x40_k5", "build-up\nx<40"),
        ("costruzione_x50_k5", "build-up\nx<50"), ("avanzata_x45_k2", "advanced\nk=2"), ("avanzata_x45_k3", "advanced\nk=3 (thesis)"), ("avanzata_x45_k4", "advanced\nk=4")]
M = np.array([[R[t]["sensibilita"][k]["margin"] for k, _ in keys] for t in TEAMS])
fig, ax = plt.subplots(figsize=(12, 6.3)); fig.subplots_adjust(0.16, 0.15, 0.92, 0.8)
fig.text(0.02, 0.94, "Is the structure clear? It depends on the choices", fontsize=16, fontweight="bold", color=INK)
fig.text(0.02, 0.895, "Stability minus the stability of structure-free data (one Gaussian blob). Dark cells: margin of at least 0.10, the threshold used for 'clear structure'", fontsize=11, color=MUTED)
im = ax.imshow(M, cmap="RdBu", vmin=-0.25, vmax=0.25, aspect="auto"); ax.grid(False)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, f"{M[i, j]:+.2f}", ha="center", va="center", fontsize=10, color="white" if abs(M[i, j]) >= 0.12 else INK, fontweight="bold" if M[i, j] >= 0.10 else "normal")
ax.set_xticks(range(len(keys))); ax.set_xticklabels([l for _, l in keys], fontsize=10); ax.set_yticks(range(len(TEAMS))); ax.set_yticklabels(TEAMS)
counts = (M >= 0.10).sum(0); [ax.text(j, -0.75, f"{c}/10 clear", ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold") for j, c in enumerate(counts)]
cb = fig.colorbar(im, ax=ax, fraction=0.03); cb.set_label("margin over the null")
SRC(fig, "results/exploratory_robustness_<Team>.json (40 resamples per cell; the thesis E1 test used its own computation: 4 of 10 at k = 5)")
fig.savefig(os.path.join(FIG, "fig_sensitivity.png"), dpi=200, facecolor="white"); plt.close(fig)

# 3. Second provider: Napoli, StatsBomb 2015/16 vs Wyscout 2017/18
P = json.load(open(os.path.join(RES, "exploratory_provider_wyscout_napoli.json"), encoding="utf-8"))
rows = [("Passes per sequence", P["stile"]["passes"], "num"), ("Duration (s)", P["stile"]["dur"], "num"), ("Long-pass share", P["stile"]["long"], "pct"), ("Sequences ending in a shot", P["stile"]["shot"], "pct"),
        ("Goal kicks played short", P["riprese_corte"]["Goal kick"], "pct"), ("Keeper restarts (count)", P["riprese_n"]["Keeper"], "num"), ("Losses per match", P["perdite_per_partita"], "num"), ("Recoveries per match", P["recuperi_per_partita"], "num")]
fig, ax = plt.subplots(figsize=(12, 6.2)); fig.subplots_adjust(0.24, 0.2, 0.97, 0.84)
fig.text(0.02, 0.94, "The report runs on a second provider; some definitions differ", fontsize=16, fontweight="bold", color=INK)
fig.text(0.02, 0.895, "Napoli: StatsBomb 2015/16 (possession ids) vs Wyscout 2017/18 (reconstructed possessions). Ratio Wyscout / StatsBomb; different seasons, so only large gaps point to definitions", fontsize=11, color=MUTED)
for i, (lab, (a, b), u) in enumerate(rows[::-1]):
    r = b / a; ax.barh(i, r - 1, left=1, color="#3c9a2a" if abs(r - 1) < 0.2 else "#d9483b", height=0.55)
    f = (lambda v: f"{100 * v:.0f}%") if u == "pct" else (lambda v: f"{v:.0f}" if float(v).is_integer() or v >= 100 else f"{v:.1f}")
    ax.text(max(r, 1) + 0.02, i, f"{f(a)} → {f(b)}", va="center", fontsize=11)
ax.axvline(1, color=INK, lw=1.2); ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows[::-1]]); ax.set_xlim(0.2, 1.9); ax.set_xlabel("Wyscout / StatsBomb (1 = same)"); ax.grid(axis="y", visible=False)
fig.text(0.02, 0.06, "Green: within 20%. Red: larger gap; checked so far: goal kicks (start position missing in Wyscout, fixed), keeper restarts (inferred), losses and recoveries (no carries, many duels).", fontsize=10, color=INK)
SRC(fig, "results/exploratory_provider_wyscout_napoli.json; Wyscout data: Pappalardo et al. 2019 (CC BY 4.0)", ". EXPLORATORY, whole seasons.")
fig.savefig(os.path.join(FIG, "fig_provider_napoli.png"), dpi=200, facecolor="white"); plt.close(fig)
print("saved figures/fig_methods.png, figures/fig_sensitivity.png, figures/fig_provider_napoli.png")
