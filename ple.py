from playwright.sync_api import sync_playwright
import datetime
import pandas as pd
import time
import random
from urllib.parse import urljoin

def run():
    with sync_playwright() as p:
        # 1. 启动浏览器
        # 调试时 headless=False (可以看到浏览器)，正式跑建议 True
        browser = p.chromium.launch(headless=False, slow_mo=3000) 
        page = browser.new_page()

        print("正在打开主页...")
        base_url = "http://ple.com.au/"
        page.goto(base_url)
        
        # 等待侧边栏加载
        try:
            page.wait_for_selector(".siteCategoriesMain a", state="attached", timeout=15000)
        except:
            print("❌ 主页侧边栏加载超时，请检查网络")
            browser.close()
            return

        # 2. 提取分类链接
        category_elements = page.locator(".siteCategoriesMain a").all()
        categories = []

        
        for cat in category_elements:
            name = cat.text_content().strip()
            href = cat.get_attribute("href")
            print(f"提取到分类: [{name}] - {href}")
            if not href: continue
            
            full_url = urljoin(base_url, href)
            categories.append({"name": name, "url": full_url})
        

        manual_categories = [
            {
                "name": "Developer Kits",
                "url": "https://www.ple.com.au/Categories/1477/Desktop-Computers/Developer-Kits" 
            }, 
            {
                "name": "Mini PCs",
                "url": "https://www.ple.com.au/Categories/1092/Desktop-Computers/Mini-PCs" 
            }, 
            {
                "name": "Custom water cooling blocks",
                "url": "https://www.ple.com.au/Categories/681/Cooling-Water-Cooling/Blocks" 
            },
             {
                "name": "Custom water cooling reservoirs",
                "url": "https://www.ple.com.au/Categories/682/Cooling-Water-Cooling/Reservoirs" 
            },
             {
                "name": "Custom water cooling radiators",
                "url": "https://www.ple.com.au/Categories/684/Cooling-Water-Cooling/Radiators" 
            },
             {
                "name": "Custom water cooling coolant and additives",
                "url": "https://www.ple.com.au/Categories/683/Cooling-Water-Cooling/Coolant-and-Additives" 
            },
             {
                "name": "Custom water cooling blocks",
                "url": "https://www.ple.com.au/Categories/740/Cooling-Water-Cooling/Fittings-and-Adapters" 
            },
             {
                "name": "Custom water cooling pumps",
                "url": "https://www.ple.com.au/Categories/678/Cooling-Water-Cooling/Pumps" 
            },
             {
                "name": "Custom water cooling tools",
                "url": "https://www.ple.com.au/Categories/685/Cooling-Water-Cooling/Tools" 
            },
             {
                "name": "Custom water cooling thermal compound",
                "url": "https://www.ple.com.au/Categories/741/Cooling-Water-Cooling/Thermal-Compound" 
            },
             {
                "name": "Custom water cooling Tubing",
                "url": "https://www.ple.com.au/Categories/680/Cooling-Water-Cooling/Tubing" 
            },
             {
                "name": "Custom water cooling tools",
                "url": "https://www.ple.com.au/Categories/691/Cooling-Water-Cooling/Kits" 
            },
        ]
        
        categories.extend(manual_categories)

        print(f"一共找到了 {len(categories)} 个分类！", flush=True)
        # --- ⚠️ 调试开关：只抓前 2 个分类测试 ---
        target_categories = categories
        # target_categories = categories # 想抓全部时，用这一行
        
        all_ple_data = []

        # 3. 遍历分类
        for i, category in enumerate(target_categories):
            print(f"[{i+1}/{len(target_categories)}] 正在进入分类: {category['name']}")
            
            # 跳转
            try:
                page.goto(category['url'], timeout=60000) # 增加超时时间防止页面卡顿
                
                # 等待商品列表出现 (如果没有商品，这里会超时报错，跳过该分类)
                page.wait_for_selector(".itemGrid2TileStandard:has-text('$')", timeout=10000)
            except:
                print(f"   ⚠️ 分类 {category['name']} 加载超时或无商品，跳过...")
                continue

            # --- 核心抓取逻辑 (无翻页) ---
            
            # 1. 获取当前页所有商品元素
            product_elements = page.locator(".itemGrid2TileStandard").all()
            print(f"   -> 发现 {len(product_elements)} 个商品，开始抓取...")

            # 2. 遍历每一个商品
            for product in product_elements:
                try:
                    # --- 提取标题 ---
                    title = product.locator(".itemGrid2TileStandardDescription > a").inner_text()
                    # --- 提取价格 ---
                    price = product.locator(".itemGrid2TileStandardPrice").inner_text().split("Was")[0].strip()
                    
                    # --- 提取编号 ---
                    sku = product.locator(".itemGrid2TileMfgModel").inner_text().strip()
                    # --- 提取库存 (WA / VIC) ---
                    avail_list = product.locator(".itemGrid2TileFeatureListAvailabilityStateAvail")
                    
                    stock_west = "Unknown"
                    stock_vic = "Unknown"

                    # 逻辑：根据列表顺序提取 (假设顺序固定)
                    # 第一个是 WA
                    if avail_list.count() > 0:
                        svg = avail_list.nth(0).locator("svg").first
                        if svg.count() > 0:
                            icon = svg.get_attribute("data-icon")
                            stock_west = "In Stock" if icon == "check" else "Out of Stock"

                    # 第二个是 VIC
                    if avail_list.count() > 1:
                        svg = avail_list.nth(1).locator("svg").first
                        if svg.count() > 0:
                            icon = svg.get_attribute("data-icon")
                            stock_vic = "In Stock" if icon == "check" else "Out of Stock"
                    
                    # 存入数据
                    all_ple_data.append({
                        "category": category['name'],
                        "title": title,
                        "price": price,
                        "sku": sku,
                        "stock_WA": stock_west,
                        "stock_VIC": stock_vic
                    })
                    
                except Exception as e:
                    # 某个商品出错了，打印一下，继续抓下一个
                    # print(f"抓取单个商品出错: {e}") 
                    continue

            # 每个分类抓完后休息一下，防封
            time.sleep(random.uniform(1, 2))

        # 4. 保存文件
        browser.close()
        
        if len(all_ple_data) > 0:
            df = pd.DataFrame(all_ple_data)
            # 使用 datetime.datetime.now() 修复之前的报错
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = f"ple_products_{timestamp}.csv"
            
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"\n✅ 成功！已保存 {len(all_ple_data)} 条数据到: {csv_path}")
        else:
            print("\n⚠️ 警告：没有抓取到任何数据！")

if __name__ == "__main__":
    run()