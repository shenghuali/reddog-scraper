#!/usr/bin/env python3
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.covers.com/sport/basketball/nba/odds"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_HTML = Path("covers_nba_odds.html")
OUT_DEBUG = Path("covers_nba_odds_debug.json")


def fetch_page():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    OUT_HTML.write_text(r.text, encoding="utf-8")
    return r.text


def collect_scripts(html: str):
    soup = BeautifulSoup(html, "html.parser")
    scripts = []
    for i, tag in enumerate(soup.find_all("script"), 1):
        src = tag.get("src")
        text = (tag.string or tag.get_text() or "").strip()
        scripts.append(
            {
                "index": i,
                "src": src,
                "preview": text[:2000],
                "contains_bet365": "bet365" in text.lower(),
                "contains_open": "open" in text.lower() or "opening" in text.lower(),
                "contains_total": "total" in text.lower() or "totals" in text.lower(),
                "contains_spread": "spread" in text.lower(),
            }
        )
    return scripts


def find_patterns(html: str):
    patterns = {}
    for key in ["bet365", "open", "opening", "spread", "total", "totals", "moneyline", "consensus"]:
        patterns[key] = len(re.findall(key, html, flags=re.I))
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.I)
    return patterns, script_srcs


def main():
    html = fetch_page()
    patterns, script_srcs = find_patterns(html)
    scripts = collect_scripts(html)
    debug = {
        "url": URL,
        "html_len": len(html),
        "pattern_counts": patterns,
        "script_srcs": script_srcs,
        "matching_scripts": [
            s
            for s in scripts
            if s["contains_bet365"] or s["contains_open"] or s["contains_total"] or s["contains_spread"]
        ],
    }
    OUT_DEBUG.write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({
        "saved_html": str(OUT_HTML),
        "saved_debug": str(OUT_DEBUG),
        "pattern_counts": patterns,
        "script_srcs": len(script_srcs),
        "matching_scripts": len(debug["matching_scripts"]),
    }, indent=2))


if __name__ == "__main__":
    main()
