import pandas as pd
from datetime import datetime
import glob

# Load Advanced Stats (Current Strength)
df_stats = pd.read_csv('/data/reddog-scraper/nba-advanced-stats-latest.csv')
print("--- 当前强队战力排行 (Top 5 Net Rating) ---")
print(df_stats.head(5)[['team', 'ortg', 'drtg', 'nrtg']])
print("\n")

# Load Injury Data
injury_files = glob.glob('/data/reddog-scraper/nba-injury-*.csv')
if injury_files:
    latest_injury = sorted(injury_files, reverse=True)[0]
    df_injury = pd.read_csv(latest_injury)
    
    # Filter for notable players Out or GTD
    # Just list some notable recent injuries affecting strong teams
    strong_teams = df_stats.head(10)['team'].tolist()
    impactful_injuries = df_injury[df_injury['team'].isin(strong_teams) & df_injury['status'].str.contains('Out|Game Time', case=False, na=False)]
    
    print("--- 强队核心伤病预警 (临场排查) ---")
    print(impactful_injuries[['team', 'player', 'injury', 'status']].head(10))
