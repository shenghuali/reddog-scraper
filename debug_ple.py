from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Go directly to a category page to test product listing selectors
        url = "https://www.ple.com.au/Categories/Accessories"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        try:
            page.wait_for_selector(".itemGrid2TileStandard", timeout=10000)
            print("Selector '.itemGrid2TileStandard' found!")
            
            products = page.locator(".itemGrid2TileStandard").all()
            print(f"Found {len(products)} products.")
            
            if len(products) > 0:
                first = products[0]
                print("First product details:")
                # Check inner selectors
                title_sel = ".itemGrid2TileStandardDescription > a"
                price_sel = ".itemGrid2TileStandardPrice"
                sku_sel = ".itemGrid2TileMfgModel"
                
                print(f"Title present: {first.locator(title_sel).count() > 0}")
                print(f"Price present: {first.locator(price_sel).count() > 0}")
                print(f"SKU present: {first.locator(sku_sel).count() > 0}")
                
        except Exception as e:
            print(f"Selector '.itemGrid2TileStandard' NOT found or timed out: {e}")
            
            # Dump some classes to see what replaced it
            print("Dumping classes from the page content...")
            content = page.content()
            # Simple regex to find class="..."
            import re
            classes = set(re.findall(r'class="([^"]+)"', content))
            print(f"Found {len(classes)} unique class strings. Sample: {list(classes)[:20]}")

        browser.close()

if __name__ == "__main__":
    debug()
