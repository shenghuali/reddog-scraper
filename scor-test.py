import time
import csv
import os
from playwright.sync_api import sync_playwright

def force_write_to_disk(filename, data_list):
    if not data_list: return False
    while True:
        try:
            with open(filename, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(data_list)
                f.flush()
                os.fsync(f.fileno())
            return True
        except PermissionError:
            print(f"\n⚠️  文件被锁定！请关闭 Excel：{filename}")
            time.sleep(5)

def get_refined_categories(page):
    page.wait_for_timeout(3000)
    # 扩大搜索范围，抓取所有可能是分类的链接
    subcat_links = page.locator("a[class*='subcat-link']").all()
    
    raw_list = []
    for el in subcat_links:
        url = el.get_attribute("href")
        name = el.inner_text().strip()
        if url:
            full_url = url if url.startswith("http") else f"https://www.scorptec.com.au{url}"
            raw_list.append({"name": name, "url": full_url})

    cleaned = []
    whitelist = ['all ', 'stand', 'arm', 'mount', 'bracket', 'adapter', 'cable', 'accessory']
    blacklist = ['inch', 'hz', '4k', 'oled', 'curved', 'asus', 'msi', 'aoc', 'samsung', 'benq', 'acer']

    for cat in raw_list:
        ln = cat['name'].lower()
        if any(w in ln for w in whitelist):
            if cat['url'] not in [c['url'] for c in cleaned]: cleaned.append(cat)
            continue
        if any(b in ln for b in blacklist): continue
        if cat['url'] not in [c['url'] for c in cleaned]: cleaned.append(cat)
    return cleaned

def run_scorptec_fixed():
    data_file = "scorptec_total_data.csv"
    checkpoint_file = "scraped_categories.txt"
    
    scraped_urls = set()
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            scraped_urls = {line.strip() for line in f if line.strip()}

    if not os.path.exists(data_file) or os.path.getsize(data_file) == 0:
        with open(data_file, mode='w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(['Category', 'PN', 'Price', 'Stock', 'Name', 'Page', 'URL'])

    with sync_playwright() as p:
        # --- 核心修改 1: 启动位置固定 ---
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--js-flags=--max-old-space-size=4096",
                "--window-position=0,0",  # 每次重启都死守左上角
                "--window-size=1280,1000"
            ]
        )
        
        # 先拿类目
        temp_page = browser.new_page()
        print("正在获取类目...")
        try:
            temp_page.goto("https://www.scorptec.com.au/", wait_until="domcontentloaded", timeout=60000)
            all_cats = get_refined_categories(temp_page)
        finally:
            temp_page.close()

        todo_cats = [c for c in all_cats if c['url'] not in scraped_urls]
        print(f"📊 待处理: {len(todo_cats)} 个类目")

        for i in range(0, len(todo_cats), 5):
            # 每 5 个类目重启 context (比重启 browser 快，效果一样)
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            
            chunk = todo_cats[i:i+5]
            for cat in chunk:
                print(f"\n📂 抓取: {cat['name']}")
                try:
                    page.goto(cat['url'], wait_until="domcontentloaded", timeout=45000)
                    
                    # 尝试设置 90 个商品并等待渲染
                    if page.locator("select#pagination-view-count").count():
                        page.select_option("select#pagination-view-count", "90")
                        page.wait_for_timeout(4000)

                    current_page = 1
                    while True:
                        print(f"  > 第 {current_page} 页深度滚动并嗅探数据...")
                        
                        # --- 核心修改 2: 更加平滑且深入的滚动 ---
                        for _ in range(6):
                            page.mouse.wheel(0, 1200)
                            time.sleep(0.5)
                        
                        # 强行等待，确保价格标签从 N/A 变成数字
                        page.wait_for_timeout(4000) 

                        # --- 核心修改 3: 使用更稳健的通用选择器 ---
                        # 尝试多种可能的商品容器
                        products = page.locator(".product-list-detail, .item-box, .product-item").all()
                        
                        page_data = []
                        seen_pns = set()
                        
                        for product in products:
                            try:
                                # 只要可见且有标题就抓
                                if not product.is_visible(): continue
                                
                                title_el = product.locator("a[class*='title'], .detail-product-title a").first
                                if not title_el.count(): continue
                                
                                name = title_el.get_attribute("title") or title_el.inner_text()
                                # 这里的 PN 和 Price 使用模糊匹配定位
                                price = product.locator("[class*='price']").first.inner_text().strip()
                                pn = product.locator("span:has-text('PN:'), [class*='warranty'] span:last-child").first.inner_text().replace("PN:", "").strip()
                                stock = product.locator("[class*='stock']").first.inner_text().strip()

                                if name and pn and pn not in seen_pns:
                                    page_data.append([cat['name'], pn, price, stock, name, current_page, cat['url']])
                                    seen_pns.add(pn)
                            except: continue

                        if page_data:
                            force_write_to_disk(data_file, page_data)
                            print(f"  ✅ [落盘成功] 存入 {len(page_data)} 条商品")
                        else:
                            print("  ⚠️ 该页未能探测到商品，可能已到末尾或加载失败")
                            break

                        # 翻页
                        next_btn = page.locator("button.pagination-next, a.next-page").first
                        if next_btn.count() and next_btn.is_visible():
                            is_dis = page.evaluate("(btn) => btn.hasAttribute('disabled') || btn.classList.contains('disabled')", next_btn.element_handle())
                            if not is_dis:
                                next_btn.click(force=True)
                                page.wait_for_timeout(5000)
                                page.evaluate("window.scrollTo(0, 0)")
                                current_page += 1
                            else: break
                        else: break

                    with open(checkpoint_file, "a") as cf:
                        cf.write(cat['url'] + "\n")
                except Exception as e:
                    print(f"❌ 错误: {e}")
            
            page.close()
            context.close()
            print("--- 刷新内存，继续下一组 ---")
            
        browser.close()

if __name__ == "__main__":
    run_scorptec_fixed()