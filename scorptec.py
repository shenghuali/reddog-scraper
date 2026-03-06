import time
from playwright.sync_api import sync_playwright

def run_scorptec_scraper():
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 1. 访问首页获取所有子分类链接
            print("正在访问首页以获取子分类列表...")
            page.goto("https://www.scorptec.com.au/", wait_until="domcontentloaded")
            page.wait_for_selector(".sm-subcat-link")

            # 提取所有子分类的 a 标签链接
            # 这种方式直接锁定到具体的子类目，避免了父级目录的干扰
            sub_category_elements = page.query_selector_all(".sm-subcat-link a")
            category_urls = []
            for el in sub_category_elements:
                href = el.get_attribute("href")
                if href and href not in category_urls:
                    category_urls.append(href)

            print(f"共找到 {len(category_urls)} 个子分类链接。")

            # 2. 遍历分类进行抓取 (示例循环)
            for cat_url in category_urls:
                print(f"\n--- 正在进入分类: {cat_url} ---")
                page.goto(cat_url, wait_until="domcontentloaded")

                # --- 页面初始化配置 ---
                try:
                    # A. 确保 'In stock only' 是关闭的
                    stock_id = "input#widget-instock"
                    if page.query_selector(stock_id):
                        if page.is_checked(stock_id):
                            print("关闭库存过滤...")
                            page.click("label[for='widget-instock']")
                            page.wait_for_load_state("networkidle")

                    # B. 设置显示数量为最大
                    select_id = "select#pagination-view-count"
                    if page.query_selector(select_id):
                        options = page.eval_on_selector(select_id, "select => Array.from(select.options).map(o => o.value)")
                        target = next((x for x in ["90", "60", "30"] if x in options), None)
                        if target and page.input_value(select_id) != target:
                            print(f"切换页面容量至: {target}")
                            page.select_option(select_id, target)
                            page.wait_for_load_state("networkidle")
                except Exception as config_err:
                    print(f"配置页面参数时跳过: {config_err}")

                # --- 抓取商品信息 ---
                page.wait_for_selector(".product-list-detail", timeout=5000)
                products = page.query_selector_all(".product-list-detail")
                
                print(f"当前页面抓取到 {len(products)} 个商品:")
                for product in products:
                    # 名称 (取 title 属性)
                    name_el = product.query_selector(".detail-product-title a")
                    name = name_el.get_attribute("title") if name_el else "N/A"

                    # 价格
                    price_el = product.query_selector(".detail-product-price")
                    price = price_el.inner_text().strip() if price_el else "N/A"

                    # Part Number (最后一个 span)
                    pn_el = product.query_selector(".detail-product-warranty span:last-child")
                    pn = pn_el.inner_text().strip() if pn_el else "N/A"

                    # 库存
                    stock_el = product.query_selector(".detail-product-stock")
                    stock = stock_el.inner_text().strip() if stock_el else "N/A"

                    print(f"  > [PN: {pn}] | {price} | {stock} | {name[:50]}")

                # 间隔 5 秒
                print("任务间隔 5 秒...")
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n用户手动停止。")
        except Exception as e:
            print(f"\n脚本运行出错: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_scorptec_scraper()