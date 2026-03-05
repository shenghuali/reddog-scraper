import time
import random
import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 配置区 ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
CSV_FILE = f'centrecom_results_{timestamp}.csv'
PROXY_LIST = [] # 12:30 回家后在此填入代理列表 [cite: 2026-03-05]

def get_valid_categories(page):
    """提取并过滤有效分类"""
    print(f"--- 步骤 1: 提取分类菜单 ---")
    try:
        page.hover(".main-link-shop")
        time.sleep(2)
    except: pass

    links = page.locator("#main-menu a").all()
    categories = []
    blacklist = ["location", "contact", "about", "terms", "shipping", "privacy", "blog", "service", "jobs", "track"]
    for link in links:
        href = link.get_attribute("href")
        text = link.inner_text().strip()
        if href and href.startswith("/") and len(text) > 2:
            if not any(word in href.lower() for word in blacklist):
                full_url = f"https://www.centrecom.com.au{href}"
                if full_url not in [c['url'] for c in categories]:
                    categories.append({"name": text, "url": full_url})
    return categories

def extract_product_details(page, url):
    """提取详情页 4 个核心维度"""
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000) 

        name = page.locator(".prod_top h1").inner_text().strip() if page.locator(".prod_top h1").count() else "N/A"
        
        # SKU：提取 itemprop="sku" 标签文本 [cite: 2026-03-05]
        sku = "N/A"
        sku_el = page.locator('span[itemprop="sku"]')
        if sku_el.count():
            sku = sku_el.first.inner_text().strip()
        
        price = page.locator(".prod_price_current span").inner_text().strip() if page.locator(".prod_price_current span").count() else "N/A"

        # Clayton 库存精准匹配 (匹配图中的 span.prod_store_stock)
        clayton_stock = "Not Found"
        clayton_label = page.locator("span.prod_store_stock", has_text="Clayton")
        if clayton_label.count():
            # 回溯父级 li，寻找同级中含 stock-result 的 span
            parent_li = clayton_label.locator("xpath=..")
            status_el = parent_li.locator("span[class*='stock-result']")
            if status_el.count():
                clayton_stock = status_el.inner_text().strip()

        return [name, sku, price, clayton_stock, url]
    except Exception as e:
        print(f"⚠️ 提取失败 {url}: {e}")
        return None

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--window-position=0,0"])
        
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'SKU', 'Price', 'Clayton Stock', 'URL'])

            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            page.goto("https://www.centrecom.com.au", wait_until="networkidle")
            category_list = get_valid_categories(page)
            print(f"✅ 锁定 {len(category_list)} 个分类。")
            page.close()
            context.close()

            for cat in category_list:
                print(f"\n📂 处理分类: {cat['name']}")
                proxy = {"server": random.choice(PROXY_LIST)} if PROXY_LIST else None
                run_context = browser.new_context(proxy=proxy, viewport={'width': 1280, 'height': 800})
                run_page = run_context.new_page()
                
                try:
                    current_cat_url = cat['url']
                    while current_cat_url: # 开启翻页循环
                        print(f"📄 正在抓取页面: {current_cat_url}")
                        run_page.goto(current_cat_url, wait_until="domcontentloaded")
                        
                        # 提取当前页商品链接
                        product_links = run_page.locator(".prbox_box a.prbox_link").all()
                        urls = list(set([f"https://www.centrecom.com.au{el.get_attribute('href')}" for el in product_links]))
                        
                        for p_url in urls:
                            data = extract_product_details(run_page, p_url)
                            if data:
                                writer.writerow(data)
                                f.flush()
                                print(f"✅ 已保存: {data[1]} | {data[0][:15]}...")
                            time.sleep(random.uniform(8, 12))
                            
                        # 检测是否有“下一页”
                        next_btn = run_page.locator(".pager .next-page a")
                        if next_btn.count():
                            next_href = next_btn.get_attribute("href")
                            current_cat_url = f"https://www.centrecom.com.au{next_href}"
                            print("➡️ 发现下一页，准备跳转...")
                        else:
                            current_cat_url = None # 抓完退出循环
                
                except Exception as e:
                    print(f"❌ 分类抓取中断: {e}")
                finally:
                    run_context.close()

        browser.close()

if __name__ == "__main__":
    main()