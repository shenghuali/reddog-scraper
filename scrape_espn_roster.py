import csv
import time
from playwright.sync_api import sync_playwright

TEAMS = [
    'atl', 'bos', 'bkn', 'cha', 'chi', 'cle', 'dal', 'den', 'det', 'gs', 
    'hou', 'ind', 'lac', 'lal', 'mem', 'mia', 'mil', 'min', 'no', 'ny', 
    'okc', 'orl', 'phi', 'phx', 'por', 'sac', 'sa', 'tor', 'utah', 'was'
]

def scrape_team_stats(team_abbr):
    url = f"https://www.espn.com/nba/team/stats/_/name/{team_abbr}"
    print(f"Scraping {team_abbr}...")
    
    player_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # ESPN uses two linked tables: one for names, one for stats.
            # We need to find the rows in both and zip them.
            
            # Selector for player names table
            name_rows = page.query_selector_all("section.TeamStats table.Table--fixed-left tbody tr")
            # Selector for stats table
            stat_rows = page.query_selector_all("section.TeamStats div.Table__Scroller table.Table tbody tr")
            
            if not name_rows or not stat_rows:
                print(f"No data found for {team_abbr}")
                return []

            # Determine headers from the stat table
            header_row = page.query_selector("section.TeamStats div.Table__Scroller table.Table thead tr")
            headers = [th.inner_text() for th in header_row.query_selector_all("th")] if header_row else []

            for n_row, s_row in zip(name_rows, stat_rows):
                name_cell = n_row.query_selector("td")
                if not name_cell or "Total" in name_cell.inner_text():
                    continue
                
                # Format: "Name POS" -> extract name and position
                full_text = name_cell.inner_text().strip()
                # Pos is usually at the end of the string
                parts = full_text.split()
                if len(parts) > 1:
                    pos = parts[-1]
                    name = " ".join(parts[:-1])
                else:
                    name = full_text
                    pos = "N/A"
                
                stats_cells = s_row.query_selector_all("td")
                stats_values = [td.inner_text().strip() for td in stats_cells]
                
                row_dict = {
                    'team': team_abbr.upper(),
                    'player': name,
                    'pos': pos
                }
                
                # Map headers to values
                for h, v in zip(headers, stats_values):
                    row_dict[h.lower()] = v
                
                player_data.append(row_dict)
                
        except Exception as e:
            print(f"Error scraping {team_abbr}: {e}")
        finally:
            browser.close()
            
    return player_data

def main():
    all_players = []
    for team in TEAMS:
        data = scrape_team_stats(team)
        all_players.extend(data)
        time.sleep(2) # Be nice to ESPN
    
    if not all_players:
        print("No data collected.")
        return

    # Consolidate all unique headers
    fieldnames = ['team', 'player', 'pos']
    for p in all_players:
        for k in p.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    output_path = '/data/reddog-scraper/nba-roster.csv'
    with open(output_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_players)
    
    print(f"Finished! Total players saved: {len(all_players)} to {output_path}")

if __name__ == "__main__":
    main()
