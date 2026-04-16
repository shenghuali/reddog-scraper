import pandas as pd


CSV_PATH = 'nba_enriched_data.csv'


def calc_rest(current_date, previous_date):
    if pd.isna(previous_date):
        return ''
    delta = (current_date - previous_date).days
    return str(max(1, int(delta)))


df = pd.read_csv(CSV_PATH)
df['date'] = pd.to_datetime(df['date'])

# 保留原始顺序，按 season/date 稳定排序后计算；season 切换时重置，避免跨赛季串联。
df['_original_order'] = range(len(df))
df = df.sort_values(by=['season', 'date', '_original_order'], kind='stable').copy()

for col in ['home_rest', 'away_rest']:
    df[col] = ''
for col in ['home_b2b', 'away_b2b']:
    df[col] = ''

last_game_dates = {}
current_season = None

for index, row in df.iterrows():
    season = row.get('season', '')
    home = row['home_team']
    away = row['away_team']
    date = row['date']

    if season != current_season:
        last_game_dates = {}
        current_season = season

    home_rest = calc_rest(date, last_game_dates.get(home))
    away_rest = calc_rest(date, last_game_dates.get(away))

    if home_rest != '':
        df.at[index, 'home_rest'] = home_rest
        df.at[index, 'home_b2b'] = '1' if home_rest == '1' else '0'

    if away_rest != '':
        df.at[index, 'away_rest'] = away_rest
        df.at[index, 'away_b2b'] = '1' if away_rest == '1' else '0'

    last_game_dates[home] = date
    last_game_dates[away] = date

df = df.sort_values(by=['_original_order'], kind='stable').drop(columns=['_original_order'])
df.to_csv(CSV_PATH, index=False)
print('Updated existing rest and b2b columns')
