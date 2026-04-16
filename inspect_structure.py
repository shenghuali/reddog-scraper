import urllib.request, json, re
url = "https://www.sportsbookreview.com/betting-odds/nba-basketball/pointspread/full-game/?date=2026-03-23"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, flags=re.S)
    if m:
        data = json.loads(m.group(1))
        # 递归打印所有 key，看看数据藏哪
        def print_keys(obj, depth=0):
            if depth > 3: return
            if isinstance(obj, dict):
                for k in obj.keys():
                    print("  " * depth + str(k))
                    print_keys(obj[k], depth + 1)
        print_keys(data)
    else:
        print("No JSON found.")
