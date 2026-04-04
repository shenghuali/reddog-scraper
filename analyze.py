import pandas as pd
import glob

print("1. Loading Enriched Data (Base)")
df_enriched = pd.read_csv('/data/reddog-scraper/nba_enriched_data.csv')
print(f"Loaded {len(df_enriched)} records.")

print("2. Loading Advanced Stats (Current Strength)")
df_stats = pd.read_csv('/data/reddog-scraper/nba-advanced-stats.csv')
print(f"Loaded {len(df_stats)} team stats.")
print(df_stats.head(10))

print("3. Loading Injury Data (Game Day Variables)")
injury_files = glob.glob('/data/reddog-scraper/nba-injury-latest.csv')
if injury_files:
    latest_injury = injury_files[0]
    df_injury = pd.read_csv(latest_injury)
    print(f"Loaded {len(df_injury)} injury records from {latest_injury}.")
    
    # Simple check for notable injuries
    out_or_gtd = df_injury[df_injury['status'].str.contains('Out|Game Time', case=False, na=False)]
    print("\nNotable Injuries:")
    print(out_or_gtd[['team', 'player', 'injury', 'status']].head(20))
else:
    print("No injury data found.")
