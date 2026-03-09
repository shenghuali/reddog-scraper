import time
import random
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 核心配置 ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
CSV_FILE = f'centrecom_results_{timestamp}.csv'

def get_proxy_settings():
    """动态生成代理，强制 Oxylabs 更换 IP"""
    session_id = random.randint(10000, 99999)
    return {
        "server": "http://pr.oxylabs.io:7777",
        "username": f"customer-cplonline_WfHQE-cc-au-city-melbourne-session-{session_id}",
        "password": "Cpl85428688_" 
    }

def request_interceptor(route):
    """拦截图片和媒体"""
    if route.request.resource_type in ["image", "font", "media"]:
        route.abort()
    else:
        route.continue_()

def get_current_ip(page):
    try:
        page.goto("https://api.ipify.org", timeout=15000)
        return page.inner_text("body").strip()
    except:
        return "IP 获取超时"

def apply_stealth(page):
    try:
        from playwright_stealth import stealth
        stealth(page)
    except Exception as e1:
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
        except Exception as e2:
            print(f"⚠️ Stealth 加载失败: {e1} | {e2}")

def get_valid_categories(page):
    print(f"--- 步骤 1: 提取分类菜单 ---")
    try:
        page.hover(".main-link-shop", timeout=5000)
        time.sleep(2)
    except: pass
    page.wait_for_selector("#main-menu", timeout=15000)
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
    try:
        time.sleep(random.uniform(12, 18)) 
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.mouse.wheel(0, random.randint(300, 600))
        
        name = page.locator(".prod_top h1").inner_text().strip() if page.locator(".prod_top h1").count() else "N/A"
        sku = page.locator('span[itemprop="sku"]').first.inner_text().strip() if page.locator('span[itemprop="sku"]').count() else "N/A"
        price = page.locator(".prod_price_current span").inner_text().strip() if page.locator(".prod_price_current span").count() else "N/A"
        return [name, sku, price, "Clayton", url]
    except:
        return None

def main():
    with sync_playwright() as p:
        
        # --- 初始化第一个浏览器实例 (代理必须放在这里) ---
        current_proxy = get_proxy_settings()
        browser = p.chromium.launch(headless=False, proxy=current_proxy)
        context = browser.new_context(
            locale="en-AU",
            timezone_id="Australia/Melbourne",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        apply_stealth(page)

        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'SKU', 'Price', 'Stock', 'URL'])

            print(f"🌐 初始 IP: {get_current_ip(page)}")
            print("\n🎯 第 1 次 60 秒人工验证窗口。请手动点击！")
            page.goto("https://www.centrecom.com.au", wait_until="domcontentloaded", timeout=90000)
            time.sleep(60) 

            category_list = get_valid_categories(page)
            print(f"✅ 锁定 {len(category_list)} 个分类。开启流量节省模式...")
            page.route("**/*", request_interceptor)

            product_count = 0
            for idx, cat in enumerate(category_list):
                print(f"📂 处理分类: {cat['name']}")
                try:
                    page.goto(cat['url'], wait_until="domcontentloaded", timeout=60000)
                    product_links = page.locator(".prbox_box a.prbox_link").all()
                    urls = [f"https://www.centrecom.com.au{el.get_attribute('href')}" for el in product_links]
                    
                    for p_url in list(set(urls)):
                        
                        # --- 核心修改：每 10 个商品彻底重启浏览器 ---
                        if product_count > 0 and product_count % 10 == 0:
                            print(f"\n🛑 抓取满 10 个。强制关闭浏览器并更换 IP...")
                            browser.close() # 必须连同浏览器一起关闭才能换代理
                            time.sleep(random.uniform(5, 10))
                            
                            # 重建全新的浏览器和上下文
                            current_proxy = get_proxy_settings()
                            browser = p.chromium.launch(headless=False, proxy=current_proxy)
                            context = browser.new_context(
                                locale="en-AU",
                                timezone_id="Australia/Melbourne",
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                            )
                            page = context.new_page()
                            apply_stealth(page)
                            
                            print(f"🔄 浏览器已重启。新 IP: {get_current_ip(page)}")
                            print("\n🎯 必须重新获取 Cloudflare 授权！请在 60 秒内手动点击验证码！")
                            page.goto("https://www.centrecom.com.au", wait_until="domcontentloaded", timeout=90000)
                            time.sleep(60)
                            
                            page.route("**/*", request_interceptor) # 重新开启拦截
                            
                        data = extract_product_details(page, p_url)
                        if data:
                            writer.writerow(data)
                            f.flush()
                            product_count += 1
                            print(f"✅ [{product_count}] 已保存: {data[1]}")
                            
                except Exception as e:
                    print(f"⚠️ 分类中断: {e}")

        browser.close()

if __name__ == "__main__":
    main()