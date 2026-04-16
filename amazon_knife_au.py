#!/usr/bin/env python3
"""
Amazon AU Knife Scraper - Playwright版本
澳大利亚亚马逊刀具产品抓取
"""

import csv
import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# ============ 配置 ============
SEARCH_KEYWORDS = [
    "foldable utility knife",
    "box cutter knife", 
    "retractable utility knife",
    "pocket utility knife",
    "heavy duty box cutter",
    "olfa knife",
    "stanley knife"
]

MAX_PRODUCTS_PER_KEYWORD = 30
OUTPUT_FILE = f"amazon_standard_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

# ============ 工具函数 ============
def extract_price(price_text):
    """提取价格，支持多种格式"""
    if not price_text:
        return None
    
    # 匹配 $XX.XX 或 A$XX.XX 或 AU$XX.XX
    patterns = [
        r'\$\s*([0-9,]+\.?\d{0,2})',
        r'(?:AU\$|A\$)\s*([0-9,]+\.?\d{0,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, price_text.replace(',', ''))
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    return None

def extract_rating(rating_text):
    """提取评分"""
    if not rating_text:
        return None
    
    # 匹配 4.5 out of 5 stars
    match = re.search(r'([\d.]+)\s*out of\s*5', rating_text, re.I)
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    
    # 直接匹配数字
    match = re.search(r'\b([\d.]+)\s*(?:stars?|ratings?)', rating_text, re.I)
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return None

def extract_review_count(text):
    """提取评论数"""
    if not text:
        return None
    
    # 匹配 1,234 ratings
    match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?)', text, re.I)
    if match:
        try:
            return int(match.group(1).replace(',', ''))
        except:
            pass
    return None

def clean_text(text):
    """清理文本"""
    if not text:
        return ""
    text = ' '.join(text.split())
    return text.strip()

# ============ 核心爬虫 ============
class AmazonAUScraper:
    def __init__(self):
        self.all_products = []
        self.seen_asins = set()
        
    def search_products(self, page, keyword, max_results=30):
        """搜索产品"""
        products = []
        search_url = f"https://www.amazon.com.au/s?k={keyword.replace(' ', '+')}"
        
        print(f"🔍 搜索: {keyword}")
        
        try:
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # 点击接受 Cookies（如果需要）
            try:
                accept_btn = page.locator('button[data-cel-widget="gdpr-consent-banner-accept"]').first
                if accept_btn.is_visible(timeout=2000):
                    accept_btn.click()
                    time.sleep(1)
            except:
                pass
            
            # 等待产品加载
            page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)
            
            # 获取所有产品
            items = page.locator('[data-component-type="s-search-result"]').all()
            print(f"   找到 {len(items)} 个产品")
            
            for item in items[:max_results]:
                try:
                    # ASIN
                    asin = item.get_attribute('data-asin') or ''
                    if not asin or asin in self.seen_asins:
                        continue
                    
                    # 标题
                    title_elem = item.locator('h2 a span').first
                    title = title_elem.inner_text() if title_elem.is_visible() else ''
                    title = clean_text(title)
                    
                    # 价格 - 多种选择器
                    price = None
                    price_selectors = [
                        '.a-price .a-offscreen',
                        '.a-price-range .a-offscreen',
                        '.a-price-sale .a-offscreen',
                        '[data-cy="price-recipe"] .a-offscreen',
                        '.a-price-to-pay .a-offscreen'
                    ]
                    for selector in price_selectors:
                        try:
                            price_elem = item.locator(selector).first
                            if price_elem.is_visible():
                                price_text = price_elem.inner_text()
                                price = extract_price(price_text)
                                if price:
                                    break
                        except:
                            continue
                    
                    # 评分
                    rating = None
                    rating_selectors = [
                        '[aria-label*="stars"]',
                        '.a-icon-star-small',
                        '.a-icon-alt',
                        '[data-cy="reviews-ratings-row"]'
                    ]
                    for selector in rating_selectors:
                        try:
                            rating_elem = item.locator(selector).first
                            if rating_elem.is_visible():
                                rating_text = rating_elem.get_attribute('aria-label') or rating_elem.inner_text()
                                rating = extract_rating(rating_text)
                                if rating:
                                    break
                        except:
                            continue
                    
                    # 评论数
                    review_count = None
                    review_selectors = [
                        '[aria-label*="ratings"]',
                        '.a-size-base',
                        '[data-cy="reviews-ratings-row"] a'
                    ]
                    for selector in review_selectors:
                        try:
                            review_elem = item.locator(selector).first
                            if review_elem.is_visible():
                                review_text = review_elem.get_attribute('aria-label') or review_elem.inner_text()
                                review_count = extract_review_count(review_text)
                                if review_count:
                                    break
                        except:
                            continue
                    
                    # URL
                    url = f"https://www.amazon.com.au/dp/{asin}"
                    
                    product = {
                        'asin': asin,
                        'title': title,
                        'current_price': price,
                        'search_keyword': keyword,
                        'url': url,
                        'rating': rating,
                        'review_count': review_count,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    products.append(product)
                    self.seen_asins.add(asin)
                    
                    print(f"   ✓ {title[:50]}... ${price}")
                    
                except Exception as e:
                    continue
            
            return products
            
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            return []
    
    def run(self):
        """运行爬虫"""
        print(f"🚀 启动 Amazon AU 爬虫 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # 搜索所有关键词
            for keyword in SEARCH_KEYWORDS:
                products = self.search_products(page, keyword, MAX_PRODUCTS_PER_KEYWORD)
                self.all_products.extend(products)
                time.sleep(3)
            
            browser.close()
        
        # 保存结果
        print(f"\n💾 保存 {len(self.all_products)} 个产品到 {OUTPUT_FILE}")
        
        if self.all_products:
            keys = ['asin', 'title', 'current_price', 'search_keyword', 'url', 'rating', 'review_count', 'scraped_at']
            with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for product in self.all_products:
                    writer.writerow(product)
            print(f"✅ 完成！")
        else:
            print(f"⚠️ 没有找到任何产品")


if __name__ == "__main__":
    scraper = AmazonAUScraper()
    scraper.run()
