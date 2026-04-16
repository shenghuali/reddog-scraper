import csv
import re
import os

ROSTER_PATH = '/Users/shenghuali/reddog-scraper/nba-roster.csv'
CLEAN_ROSTER_PATH = '/Users/shenghuali/reddog-scraper/nba-roster-clean.csv'

def clean_name(name):
    # Remove suffixes like G*, F*, C*, G, F, C attached at the end of the name
    # Example: "Trae YoungG*" -> "Trae Young"
    name = name.replace('*', '')
    # Remove single letter pos markers at the end
    cleaned = re.sub(r'([a-z])([GFC])$', r'\1', name)
    return cleaned.strip()

def process_roster():
    players = {} # name -> list of rows
    headers = []
    
    with open(ROSTER_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            original_name = row['player']
            name = clean_name(original_name)
            row['player'] = name
            
            if name not in players:
                players[name] = []
            players[name].append(row)

    final_rows = []
    for name, rows in players.items():
        if len(rows) == 1:
            final_rows.append(rows[0])
        else:
            # Duplicate detection logic
            # 1. Specific overrides
            if name == "James Harden":
                # Current team: CLE
                final_rows.append(next(r for r in rows if r['team'] == 'CLE'))
                continue
            if name == "Jalen Green":
                # Current team: PHX
                final_rows.append(next(r for r in rows if r['team'] == 'PHX'))
                continue
            if name == "Trae Young":
                 # He appears in ATL and WAS. 10 GP in ATL, 3 GP in WAS. 
                 # Usually the one with fewer GP is the new team in a mid-season trade.
                 final_rows.append(min(rows, key=lambda x: int(x['gp']) if x['gp'].isdigit() else 999))
                 continue
            
            # Default heuristic: keep the one with fewer GP if they are close in date, 
            # or simply the one that makes sense.
            # ESPN trade marking: The entry with the '*' or specific pos marks usually indicates the new team.
            # Here we just keep the one with the least GP (the most recent team joined)
            try:
                best_row = min(rows, key=lambda x: int(x['gp']) if x['gp'].isdigit() else 999)
                final_rows.append(best_row)
            except:
                final_rows.append(rows[0])

    with open(CLEAN_ROSTER_PATH, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(final_rows)
    
    print(f"Cleanup complete. Reduced {len(players)} unique players from {sum(len(v) for v in players.values())} rows.")
    # Replace original
    os.rename(CLEAN_ROSTER_PATH, ROSTER_PATH)

if __name__ == "__main__":
    process_roster()
