import time
import csv
import os
import random
from datetime import datetime
import json
import re
from playwright.sync_api import sync_playwright

# --- 工具函数 ---
def force_write_to_disk(filename, data_list):
    if not data_list: return False
    while True:
        try:
            parent = os.path.dirname(os.path.abspath(filename))
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(filename, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(data_list)
                f.flush()
                os.fsync(f.fileno())
            return True
        except PermissionError:
            print(f"\n⚠️ 文件被锁定！请关闭 Excel：{filename}")
            time.sleep(5)

def file_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def normalize_pn(v):
    if not v: return ""
    s = str(v).strip()
    s = re.sub(r"^\s*(model|pn|sku|part number)\s*[:：\-]?\s*", "", s, flags=re.IGNORECASE)
    return s.strip()

# --- Anti-Detection 逻辑 (纯原生注入，不再依赖外部库) ---
def apply_stealth_and_fingerprint(page):
    page.add_init_script("""
        // 抹除 webdriver 特征
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        // 伪装硬件指纹
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        
        // 伪装 Chrome 运行环境
        window.navigator.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // 伪装插件信息
        Object.defineProperty(navigator, 'plugins', {
            get: () => [{
                name: 'Chrome PDF Plugin',
                filename: 'internal-pdf-viewer',
                description: 'Portable Document Format'
            }]
        });
        
        // 伪装语言环境
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)

# --- 提取逻辑 ---
def extract_categories(page):
    return page.evaluate("""
        () => {
            const links = Array.from(document.querySelectorAll('ul.dropdown-menu li:nth-child(n+2) a'));
            return links.map(a => ({
                name: a.innerText.trim(),
                url: a.href
            })).filter(c => c.url && c.name && !c.url.includes('#'));
        }
    """)

def extract_product_links(page):
    return page.evaluate("""
        () => {
            const links = Array.from(document.querySelectorAll('.product a'));
            return Array.from(new Set(links.map(a => a.href))).filter(url => url && !url.includes('#'));
        }
    """)

def extract_detail_info(page):
    return page.evaluate("""
        () => {
            const nameEl = document.querySelector('.product-information h1');
            const priceEl = document.querySelector('span span.price');
            const mpnEl = document.querySelector('strong#MPN');
            const stockEl = document.querySelector('.btn-default');
            const gtinEl = document.querySelector('strong:nth-of-type(3)');
            const webidEl = document.querySelector('p.webid');
            return {
                name: nameEl ? nameEl.innerText.trim() : '',
                price: priceEl ? priceEl.innerText.trim() : '',
                mpn: mpnEl ? mpnEl.innerText.trim() : '',
                stock: stockEl ? stockEl.innerText.trim() : '',
                gtin: gtinEl ? gtinEl.innerText.trim() : '',
                webid: webidEl ? webidEl.innerText.trim() : ''
            };
        }
    """)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
EXTRA_HEADERS = {
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
}

def handle_initial_page(page):
    try:
        page.wait_for_load_state("networkidle")
        page.keyboard.press("Escape")
        selectors = ["button[aria-label='Close']", ".modal-close", ".close-button", "button:has-text('No thanks')", "button:has-text('Close')"]
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
            except: pass
    except Exception as e:
        print(f"Initial page handling: {e}")

def run_ca():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_dir = os.path.join(script_dir, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    
    cat_checkpoint_file = os.path.join(script_dir, "ca_scraped_categories.txt")
    prod_checkpoint_file = os.path.join(script_dir, "ca_scraped_urls.txt")
    
    scraped_categories = set()
    if os.path.exists(cat_checkpoint_file):
        with open(cat_checkpoint_file, "r") as f:
            scraped_categories = {line.strip() for line in f if line.strip()}
    
    scraped_urls = set()
    if os.path.exists(prod_checkpoint_file):
        with open(prod_checkpoint_file, "r") as f:
            scraped_urls = {line.strip() for line in f if line.strip()}

    data_file = os.path.join(csv_dir, f"ca_total_data_{file_ts()}.csv")
    with open(data_file, mode='w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(['Category', 'MPN', 'Price', 'Stock', 'Name', 'GTIN', 'WebID', 'URL'])

    profile_dir = os.path.join(script_dir, "profiles", "ca_profile")
    os.makedirs(profile_dir, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="chrome", # 调用本机 Chrome
            viewport={'width': 1280, 'height': 800},
            user_agent=USER_AGENT,
            extra_http_headers=EXTRA_HEADERS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        apply_stealth_and_fingerprint(page)
        
        base_url = "https://www.computeralliance.com.au/"
        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(random.uniform(5, 8))
        handle_initial_page(page)
        
        categories = extract_categories(page)
        for cat in categories:
            if cat['url'] in scraped_categories: continue
            
            print(f"\n📂 Category: {cat['name']}")
            try:
                page.goto(cat['url'], wait_until="networkidle", timeout=60000)
                product_urls = extract_product_links(page)
                for url in product_urls:
                    if url in scraped_urls: continue
                    
                    try:
                        time.sleep(random.uniform(2, 4)) # 延长随机延迟
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(1000)
                        
                        detail = extract_detail_info(page)
                        if detail['name']:
                            force_write_to_disk(data_file, [[cat['name'], normalize_pn(detail['mpn']), detail['price'], detail['stock'], detail['name'], detail['gtin'], detail['webid'], url]])
                            print(f" - OK: {detail['name']}")
                        
                        scraped_urls.add(url)
                    except: pass
                scraped_categories.add(cat['url'])
            except: pass
        context.close()

if __name__ == "__main__":
    run_ca()
