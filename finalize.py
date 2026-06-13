import pandas as pd, glob

df = pd.read_csv("/Users/vanavanesian/Downloads/ronaldo-analysis/ronaldo_matches_raw.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

# ---- Manager by date (United's actual touchline timeline) ----
def manager(d):
    s = d.strftime("%Y-%m-%d")
    if s <= "2021-11-20": return "Solskjaer"
    if s <= "2021-12-02": return "Carrick"      # 3 interim games
    if s <= "2022-06-30": return "Rangnick"
    return "ten Hag"
df["manager"] = df["date"].apply(manager)

# ---- Rest days since United's previous match in this dataset ----
df["rest_days"] = df["date"].diff().dt.days

# ---- Points & result ----
df["points"] = df.apply(lambda r: 1 if r.utd_goals_for == r.utd_goals_against
                        else (3 if r.utd_goals_for > r.utd_goals_against else 0)
                        if pd.notna(r.utd_goals_for) else None, axis=1)

# ---- Validate scores vs football-data (PL only) ----
frames = []
for f in glob.glob("/Users/vanavanesian/Downloads/ronaldo-analysis/raw/E0_2122.csv") + \
         glob.glob("/Users/vanavanesian/Downloads/ronaldo-analysis/raw/E0_2223.csv"):
    d = pd.read_csv(f); d["Date"] = pd.to_datetime(d["Date"], format="%d/%m/%Y", errors="coerce"); frames.append(d)
fd = pd.concat(frames)
fd = fd[(fd.HomeTeam == "Man United") | (fd.AwayTeam == "Man United")]
fd["mu_gf"] = fd.apply(lambda r: r.FTHG if r.HomeTeam == "Man United" else r.FTAG, axis=1)
fd["mu_ga"] = fd.apply(lambda r: r.FTAG if r.HomeTeam == "Man United" else r.FTHG, axis=1)
fdmap = {d.date(): (gf, ga) for d, gf, ga in zip(fd.Date, fd.mu_gf, fd.mu_ga)}

mismatch = 0
for _, r in df[df.competition == "Premier League"].iterrows():
    key = r.date.date()
    if key in fdmap:
        if (r.utd_goals_for, r.utd_goals_against) != fdmap[key]:
            mismatch += 1
            print(f"SCORE MISMATCH {key} {r.opponent}: fotmob {r.utd_goals_for}-{r.utd_goals_against} vs fd {fdmap[key]}")
print(f"PL score validation vs football-data: {mismatch} mismatches out of {(df.competition=='Premier League').sum()}")

# ---- Opponent strength control: United market win prob from B365 odds (PL only) ----
fd["overround"] = 1/fd["B365H"] + 1/fd["B365D"] + 1/fd["B365A"]
fd["mu_winprob"] = fd.apply(lambda r: (1/r.B365H if r.HomeTeam == "Man United" else 1/r.B365A)
                            / r.overround, axis=1)
probmap = {d.date(): p for d, p in zip(fd.Date, fd.mu_winprob)}
df["utd_mkt_winprob"] = df.apply(
    lambda r: round(probmap.get(r.date.date()), 3)
    if r.competition == "Premier League" and r.date.date() in probmap else None, axis=1)

# ---- Tidy column order ----
cols = ["date", "competition", "opponent", "home_away", "manager", "rest_days",
        "ronaldo", "ronaldo_started", "ronaldo_minutes",
        "utd_goals_for", "utd_goals_against", "points",
        "utd_xg", "opp_xg", "utd_possession",
        "utd_shots", "opp_shots", "utd_sot", "opp_sot",
        "utd_passes", "opp_passes", "utd_tackles", "utd_interceptions", "utd_fouls",
        "pressing_proxy", "utd_mkt_winprob"]
df = df[cols]
df.to_csv("/Users/vanavanesian/Downloads/ronaldo-analysis/ronaldo_stint_dataset.csv", index=False)

print("\n=== FINAL DATASET ===")
print("matches:", len(df), "| columns:", len(df.columns))
print("\nRonaldo involvement:")
print(df.ronaldo.value_counts().to_string())
print("\nStarted vs not-started PPG (raw, no controls):")
g = df.groupby(df.ronaldo_started == 1)["points"].agg(["mean", "count"])
print(g.to_string())
print("\nManager x Ronaldo-started crosstab (shows overlap / common support):")
print(pd.crosstab(df.manager, df.ronaldo_started).to_string())
print("\nBlanks per column:")
print(df.isna().sum()[df.isna().sum() > 0].to_string())
