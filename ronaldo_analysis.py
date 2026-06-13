"""
Was Ronaldo the problem at Manchester United (second stint, Sep 2021 - Nov 2022)?

A simple, comprehensive statistical analysis.
Methods kept deliberately simple: t-tests, ANOVA-style group means, correlation,
linear/logistic regression (statsmodels, for p-values), effect sizes, percentiles.

Two levels of analysis:
  PART A  Team level   - did United press/defend/win differently with vs without
                         Ronaldo (within-stint, controlling for confounds)?
  PART B  Player level - did Ronaldo personally do less defensive work, and more
                         attacking work, than comparable forwards? (the mechanism)
  PART C  Summary table + multiple-testing note.
"""
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
RED, GREY = "#E64A40", "#9aa0a6"
results = []   # collect every test for the summary table


def cohen_d(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx-1)*x.var(ddof=1) + (ny-1)*y.var(ddof=1)) / (nx+ny-2))
    return (x.mean() - y.mean()) / sp


def ttest(name, a, b, note=""):
    a = pd.Series(a).dropna(); b = pd.Series(b).dropna()
    t, p = stats.ttest_ind(a, b, equal_var=False)   # Welch
    d = cohen_d(a, b)
    results.append({"test": name, "grpA_mean": round(a.mean(), 2),
                    "grpB_mean": round(b.mean(), 2), "p_value": p,
                    "cohen_d": round(d, 2), "note": note})
    print(f"  {name:32s} {a.mean():6.2f} vs {b.mean():6.2f} | "
          f"t={t:6.2f}  p={p:.4g}  d={d:+.2f}")
    return p


# =====================================================================
print("=" * 70)
print("PART A — TEAM LEVEL: with vs without Ronaldo (within his stint)")
print("=" * 70)
team = pd.read_csv("ronaldo_stint_dataset.csv")
team["started"] = team["ronaldo_started"] == 1
team["win"] = (team["points"] == 3).astype(int)
pl = team[team["competition"] == "Premier League"].copy()
print(f"Matches: {len(team)} | Ronaldo started {team.started.sum()}, "
      f"did not start {(~team.started).sum()}\n")

print("Pressing & defence (lower pressing_proxy = more intense press):")
ttest("pressing_proxy", team.loc[~team.started, "pressing_proxy"],
      team.loc[team.started, "pressing_proxy"], "team")
ttest("opp_xg_conceded", team.loc[~team.started, "opp_xg"],
      team.loc[team.started, "opp_xg"], "team")

print("\nRESULTS (the analysis you expected to be null):")
ttest("points", team.loc[~team.started, "points"],
      team.loc[team.started, "points"], "team")
# win rate via 2x2 + Fisher (small/!indep cells)
ct = pd.crosstab(team.started, team.win)
odds, p_win = stats.fisher_exact(ct)
print(f"  win rate (Fisher exact)          "
      f"{team.loc[~team.started,'win'].mean():.2f} vs "
      f"{team.loc[team.started,'win'].mean():.2f} | OR={odds:.2f}  p={p_win:.4g}")
results.append({"test": "win_rate", "grpA_mean": round(team.loc[~team.started,'win'].mean(),2),
                "grpB_mean": round(team.loc[team.started,'win'].mean(),2),
                "p_value": p_win, "cohen_d": np.nan, "note": "team, Fisher"})

print("\nConfound check — did he start vs weaker opponents? (PL market win prob)")
ttest("opp_strength(mkt winprob)", pl.loc[~pl.started, "utd_mkt_winprob"],
      pl.loc[pl.started, "utd_mkt_winprob"], "PL only")

print("\nControlled model — points adjusted for opponent strength, manager, venue (PL):")
m = smf.ols("points ~ started + utd_mkt_winprob + C(manager) + C(home_away)", data=pl).fit()
print(f"  started coef = {m.params['started[T.True]']:+.3f}  "
      f"p = {m.pvalues['started[T.True]']:.3f}  (adj R2 = {m.rsquared_adj:.3f})")

print("\nControlled model — pressing adjusted for opponent strength, manager, venue (PL):")
mp = smf.ols("pressing_proxy ~ started + utd_mkt_winprob + C(manager) + C(home_away)", data=pl).fit()
print(f"  started coef = {mp.params['started[T.True]']:+.3f}  "
      f"p = {mp.pvalues['started[T.True]']:.3f}  (opp strength p = "
      f"{mp.pvalues['utd_mkt_winprob']:.3g})")


# =====================================================================
print("\n" + "=" * 70)
print("PART B — PLAYER LEVEL: Ronaldo vs comparable forwards (per 90)")
print("=" * 70)
fw = pd.read_csv("forward_match_stats.csv")
ron = fw[fw.is_ronaldo == 1]
utd = fw[(fw.is_ronaldo == 0) & (fw.team == "United")]
allp = fw[fw.is_ronaldo == 0]
print(f"Forward-match rows: {len(fw)} (Ronaldo {len(ron)}, "
      f"United teammates {len(utd)}, all PL forwards {len(allp)})\n")

print("DEFENSIVE WORK — Ronaldo vs United teammate forwards:")
ttest("def_actions_p90 (vs UTD)", ron.def_actions_p90, utd.def_actions_p90, "player")
ttest("recoveries_p90 (vs UTD)", ron.recoveries_p90, utd.recoveries_p90, "player")
print("DEFENSIVE WORK — Ronaldo vs all PL forwards:")
ttest("def_actions_p90 (vs all)", ron.def_actions_p90, allp.def_actions_p90, "player")
ttest("recoveries_p90 (vs all)", ron.recoveries_p90, allp.recoveries_p90, "player")

print("\nATTACKING THREAT (the trade-off) — Ronaldo vs all PL forwards:")
ttest("box_touches_p90 (vs all)", ron.box_touches_p90, allp.box_touches_p90, "player")
ttest("xg_p90 (vs all)", ron.xg_p90, allp.xg_p90, "player")
ttest("goal_invol_p90 (vs all)", ron.goal_invol_p90, allp.goal_invol_p90, "player")

print("\nMinutes-adjusted regression: recoveries_p90 ~ Ronaldo + minutes (all forwards)")
mr = smf.ols("recoveries_p90 ~ is_ronaldo + minutes", data=fw).fit()
print(f"  Ronaldo coef = {mr.params['is_ronaldo']:+.3f}  p = {mr.pvalues['is_ronaldo']:.3g}")

print("\nIndependence-respecting robustness — player-level means (each forward once):")
agg = fw.dropna(subset=["recoveries_p90"]).groupby("player").recoveries_p90.mean()
pct = (agg < agg["Cristiano Ronaldo"]).mean() * 100
print(f"  {len(agg)} unique forwards | Ronaldo recoveries/90 = "
      f"{agg['Cristiano Ronaldo']:.2f} -> {pct:.0f}th percentile")

# ---- Robustness #2: compare only against CENTRE-FORWARDS (same role) ----
print("\nRobustness — vs CENTRE-FORWARDS only (fairer like-for-like role):")
cf = fw[(fw.is_centre_fwd == 1) & (fw.is_ronaldo == 0)]
print(f"  centre-forward peer-matches: {len(cf)} "
      f"({cf.player.nunique()} unique CFs)")
ttest("recoveries_p90 (vs CF)", ron.recoveries_p90, cf.recoveries_p90, "player, CF-only")
ttest("def_actions_p90 (vs CF)", ron.def_actions_p90, cf.def_actions_p90, "player, CF-only")
ttest("xg_p90 (vs CF)", ron.xg_p90, cf.xg_p90, "player, CF-only")
cf_agg = fw[fw.is_centre_fwd == 1].dropna(subset=["recoveries_p90"]).groupby("player").recoveries_p90.mean()
cf_pct = (cf_agg < cf_agg["Cristiano Ronaldo"]).mean() * 100
print(f"  among {len(cf_agg)} centre-forwards, Ronaldo recoveries/90 -> {cf_pct:.0f}th percentile")


# =====================================================================
print("\n" + "=" * 70)
print("PART C — SUMMARY & MULTIPLE TESTING")
print("=" * 70)
summ = pd.DataFrame(results)
n_tests = len(summ)
bonf = 0.05 / n_tests
summ["sig_0.05"] = summ.p_value < 0.05
summ["sig_bonf"] = summ.p_value < bonf
summ["p_value"] = summ.p_value.map(lambda x: f"{x:.3g}")
print(summ.to_string(index=False))
print(f"\n{n_tests} tests run -> Bonferroni threshold p < {bonf:.4f}")
summ.to_csv("results_summary.csv", index=False)


# =====================================================================
# FIGURES
# =====================================================================
def save(fig, name):
    fig.tight_layout(); fig.savefig(name, dpi=110); plt.close(fig)

# 1. Results not significant — points with/without
fig, ax = plt.subplots(figsize=(6, 4.5))
order = [False, True]
sns.boxplot(data=team, x="started", y="points", order=order, color=RED, ax=ax, fliersize=0)
sns.stripplot(data=team, x="started", y="points", order=order, color="black", alpha=.4, ax=ax)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Did not start", "Started"]); ax.set_xlabel("")
ax.set_ylabel("Points won"); ax.set_title("Results with vs without Ronaldo (no significant difference)")
save(fig, "py_points.png")

# 2. Defensive: recoveries Ronaldo vs forwards
fig, ax = plt.subplots(figsize=(6, 4.5))
fw["grp"] = np.where(fw.is_ronaldo == 1, "Ronaldo", "Other forwards")
sns.boxplot(data=fw, x="grp", y="recoveries_p90", order=["Other forwards", "Ronaldo"],
            hue="grp", palette={"Ronaldo": RED, "Other forwards": GREY}, legend=False,
            ax=ax, fliersize=0)
sns.stripplot(data=fw, x="grp", y="recoveries_p90", order=["Other forwards", "Ronaldo"],
              color="black", alpha=.3, ax=ax)
ax.set_xlabel(""); ax.set_ylabel("Recoveries per 90")
ax.set_title("Ball recoveries: Ronaldo vs other PL forwards (p < 1e-10)")
save(fig, "py_recoveries.png")

# 3. The trade-off: defensive work vs attacking threat
fig, ax = plt.subplots(figsize=(6.5, 4.5))
for g, c in [("Other forwards", GREY), ("Ronaldo", RED)]:
    sub = fw[fw.grp == g]
    ax.scatter(sub.box_touches_p90, sub.def_actions_p90, c=c, label=g, alpha=.7, s=30)
ax.set_xlabel("Touches in opposition box per 90 (attacking)")
ax.set_ylabel("Defensive actions per 90")
ax.set_title("The trade-off: Ronaldo stays high, does little defending")
ax.legend()
save(fig, "py_tradeoff.png")

print("\nFigures saved: py_points.png, py_recoveries.png, py_tradeoff.png")
print("Summary table: results_summary.csv")
