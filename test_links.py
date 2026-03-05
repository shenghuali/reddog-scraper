import time
import random
import csv
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        # 1. 禁用最大化，设置窗口初始位置
        browser = p.chromium.launch(headless=False, args=["--window-position=0,0"])
        
        # 2. 显式设置 Viewport，防止占满全屏
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("--- 步骤 1: 访问首页获取分类 ---")
        page.goto("https://www.centrecom.com.au", wait_until="networkidle")
        
        # 触发菜单悬停以加载链接
        try:
            page.hover(".main-link-shop")
            time.sleep(2)
        except: pass

        # 提取分类并过滤黑名单
        links = page.locator("#main-menu a").all()
        categories = []
        blacklist = ["location", "contact", "about", "terms", "shipping", "privacy", "blog", "service", "jobs"]
        
        for link in links:
            href = link.get_attribute("href")
            text = link.inner_text().strip()
            if href and href.startswith("/") and len(text) > 2:
                if not any(word in href.lower() for word in blacklist):
                    categories.append({"name": text, "url": f"https://www.centrecom.com.au{href}"})
        
        # 随机抽取 1 个分类
        target_cat = random.choice(list({c['url']: c for c in categories}.values()))
        print(f"🎲 随机抽中分类: {target_cat['name']}")

        # --- 步骤 2: 进入分类并选第一个商品 ---
        page.goto(target_cat['url'], wait_until="domcontentloaded")
        first_product_el = page.locator(".prbox_box a.prbox_link").first
        
        if not first_product_el.count():
            print("❌ 该分类下未发现商品，请重新运行。")
            browser.close()
            return

        product_url = f"https://www.centrecom.com.au{first_product_el.get_attribute('href')}"
        
        # 5-7秒随机延迟，模拟真实用户
        delay = random.uniform(5, 7)
        print(f"😴 等待 {delay:.2f} 秒后进入详情页...")
        time.sleep(delay)
        
        page.goto(product_url, wait_until="networkidle")

        # --- 步骤 3: 提取精准数据 ---
        # 1. Name
        name = page.locator(".prod_top h1").inner_text().strip() if page.locator(".prod_top h1").count() else "N/A"
        
        # 2. SKU (直接提取 itemprop="sku" 标签内的文本)
        sku = "N/A"
        sku_el = page.locator('span[itemprop="sku"]')
        if sku_el.count():
            sku = sku_el.first.inner_text().strip()
        
        # 3. Price
        price = page.locator(".prod_price_current span").inner_text().strip() if page.locator(".prod_price_current span").count() else "N/A"

        # 4. Clayton Stock (精准匹配图中 li 内两个 span 的同级结构)
        clayton_stock = "Not Found"
        # 先找到包含 Clayton 文本的 span
        clayton_label = page.locator("span.prod_store_stock", has_text="Clayton")
        if clayton_label.count():
            # 定位到它的父级 li，然后寻找该 li 下类名包含 stock-result 的 span
            parent_li = clayton_label.locator("xpath=..")
            status_el = parent_li.locator("span[class*='stock-result']")
            if status_el.count():
                clayton_stock = status_el.inner_text().strip()

        # --- 步骤 4: 生成测试 CSV ---
        with open('test_single_product.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'SKU', 'Price', 'Clayton Stock', 'URL'])
            writer.writerow([name, sku, price, clayton_stock, product_url])
        
        print(f"\n✨ 测试抓取完成！")
        print(f"📊 结果: {name[:20]}... | SKU: {sku} | 价格: {price} | Clayton: {clayton_stock}")

        browser.close()

if __name__ == "__main__":
    run_test()