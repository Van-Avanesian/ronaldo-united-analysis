import json, glob, csv, os

BASE = "/Users/vanavanesian/Downloads/ronaldo-analysis/"
MUID = 10260
# map FotMob match file -> date/competition from our match dataset
import pandas as pd
meta = pd.read_csv(BASE + "ronaldo_stint_dataset.csv")
# we need matchId per row; reload raw which has matchId... rebuild map from cached files instead
# (raw csv dropped matchId; re-derive by reading each cached match's general date)

def stat_value(pstats, title):
    for g in pstats.get("stats", []):
        if title in g["stats"]:
            return g["stats"][title]["stat"]["value"]
    return None

rows = []
for mf in glob.glob(BASE + "fotmob/m_*.json"):
    d = json.load(open(mf))
    g = d.get("general", {})
    date = g.get("matchTimeUTCDate", "")[:10]
    # restrict to the stint window (cached folder also holds the 2 dropped games)
    if not ("2021-09-11" <= date <= "2022-11-13"):
        continue
    content = d.get("content", {})
    lineup = content.get("lineup") or {}
    ps = content.get("playerStats") or {}
    if not ps:
        continue
    # id -> usual position class (0 GK,1 DEF,2 MID,3 ATT) and fine positionId
    pos, posid = {}, {}
    for side in ("homeTeam", "awayTeam"):
        grp = lineup.get(side) or {}
        for p in grp.get("starters", []) + grp.get("subs", []):
            pos[p["id"]] = p.get("usualPlayingPositionId")
            posid[p["id"]] = p.get("positionId")
    CF_IDS = {104, 105, 106, 114, 115, 116}   # central-striker grid positions
    comp = None  # competition from our meta by date
    mrow = meta[meta["date"] == date]
    comp = mrow["competition"].iloc[0] if len(mrow) else None

    for pid, p in ps.items():
        if pos.get(p.get("id")) != 3:        # attackers only
            continue
        mins = stat_value(p, "Minutes played")
        if not mins or mins < 30:            # avoid per-90 noise from cameos
            continue
        defa = stat_value(p, "Defensive actions")
        recov = stat_value(p, "Recoveries")
        box = stat_value(p, "Touches in opposition box")
        goals = stat_value(p, "Goals")
        assists = stat_value(p, "Assists")
        xg = stat_value(p, "Expected goals (xG)")
        chances = stat_value(p, "Chances created")
        if defa is None:
            continue
        is_utd = p.get("teamId") == MUID
        is_ron = "Ronaldo" in p.get("name", "")
        def p90(x): return round(x / mins * 90, 2) if x is not None else None
        rows.append({
            "date": date, "competition": comp, "player": p.get("name"),
            "team": "United" if is_utd else "Opponent",
            "is_ronaldo": int(is_ron), "minutes": mins,
            "is_centre_fwd": int(posid.get(p.get("id")) in CF_IDS),
            # defensive
            "def_actions": defa, "recoveries": recov, "touches_opp_box": box,
            "def_actions_p90": p90(defa), "recoveries_p90": p90(recov),
            "box_touches_p90": p90(box),
            # attacking (the trade-off side)
            "goals": goals, "assists": assists, "xg": xg, "chances_created": chances,
            "goal_invol_p90": p90((goals or 0) + (assists or 0)),
            "xg_p90": p90(xg), "chances_p90": p90(chances),
        })

cols = list(rows[0].keys())
with open(BASE + "forward_match_stats.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

import statistics as st
ron = [r for r in rows if r["is_ronaldo"]]
utd_peers = [r for r in rows if not r["is_ronaldo"] and r["team"] == "United"]
all_peers = [r for r in rows if not r["is_ronaldo"]]
print(f"Forward-match rows: {len(rows)} (Ronaldo {len(ron)}, United peers {len(utd_peers)}, all peers {len(all_peers)})")
def mean(g, k): return round(st.mean([r[k] for r in g if r[k] is not None]), 2)
print("\nDefensive actions per 90:")
print(f"  Ronaldo:        {mean(ron,'def_actions_p90')}")
print(f"  United peers:   {mean(utd_peers,'def_actions_p90')}")
print(f"  All PL peers:   {mean(all_peers,'def_actions_p90')}")
print("Recoveries per 90:")
print(f"  Ronaldo {mean(ron,'recoveries_p90')} | United peers {mean(utd_peers,'recoveries_p90')} | all {mean(all_peers,'recoveries_p90')}")
print("Touches in opp box per 90:")
print(f"  Ronaldo {mean(ron,'box_touches_p90')} | United peers {mean(utd_peers,'box_touches_p90')} | all {mean(all_peers,'box_touches_p90')}")
print("\nUnited forward peers in sample:", sorted(set(r["player"] for r in utd_peers)))
