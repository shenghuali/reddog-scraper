#!/usr/bin/env python3
"""
Amazon AU 爬虫 - 完整版
抓取澳大利亚亚马逊刀具产品
"""

import csv
import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# ============ 配置 ============
SEARCH_KEYWORDS = [
    "utility knife",
    "box cutter", 
    "stanley knife",
    "olfa knife",
    "retractable knife",
    "folding utility knife",
    "snap off blade knife",
    "craft knife"
]

MAX_PAGES = 3  # 每关键词翻3页
PRODUCTS_PER_PAGE = 24  # 亚马逊每页约24个产品

OUTPUT_FILE = f"amazon_au_products_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

# ============ 工具函数 ============
def clean_price(price_text):
    """提取价格数字"""
    if not price_text:
        return None
    # 匹配 $XX.XX 或 A$XX.XX
    match = re.search(r'\$\s*([0-9,]+\.?\d{0,2})', price_text.replace(',', ''))
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return None

def clean_text(text):
    """清理文本"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_rating(text):
    """提取评分"""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*out of\s*5', text, re.I)
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return None

def extract_reviews(text):
    """提取评论数"""
    if not text:
        return None
    match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?)', text, re.I)
    if match:
        try:
            return int(match.group(1).replace(',', ''))
        except:
            pass
    return None

# ============ 核心爬虫 ============
class AmazonAUCrawler:
    def __init__(self):
        self.all_products = []
        self.seen_asins = set()
        
    def scrape_search_page(self, page, keyword, page_num=1):
        """抓取搜索结果页"""
        products = []
        
        # 构建URL
        base_url = f"https://www.amazon.com.au/s?k={keyword.replace(' ', '+')}"
        if page_num > 1:
            start_index = (page_num - 1) * 24
            url = f"{base_url}&page={page_num}&s=exact-aware-popularity-rank"
        else:
            url = base_url
        
        print(f"   📄 第 {page_num} 页: {url[:80]}...")
        
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            
            # 接受 cookies 弹窗
            try:
                accept_btn = page.locator('button[data-cel-widget="gdpr-consent-banner-accept"]').first
                if accept_btn.is_visible(timeout=2000):
                    accept_btn.click()
                    time.sleep(1)
            except:
                pass
            
            # 等待产品加载
            page.wait_for_selector('[data-component-type="s-search-result"]', timeout=15000)
            
            # 获取所有产品
            items = page.locator('[data-component-type="s-search-result"]').all()
            print(f"   📦 找到 {len(items)} 个产品")
            
            for item in items:
                try:
                    # ASIN
                    asin = item.get_attribute('data-asin') or ''
                    if not asin or asin in self.seen_asins:
                        continue
                    
                    # 标题
                    title_selectors = [
                        'h2 a span',
                        '.a-size-base-plus',
                        '.a-size-mini span',
                        'h2 span'
                    ]
                    title = ''
                    for sel in title_selectors:
                        try:
                            elem = item.locator(sel).first
                            if elem.is_visible():
                                title = elem.inner_text()
                                if title:
                                    break
                        except:
                            continue
                    title = clean_text(title)
                    
                    if not title:
                        continue
                    
                    # 价格 - 多种选择器
                    price = None
                    price_selectors = [
                        '.a-price .a-offscreen',
                        '.a-price-range .a-offscreen',
                        '.a-price-sale .a-offscreen',
                        '.a-price-to-pay .a-offscreen',
                        '.a-price-symbol'
                    ]
                    for sel in price_selectors:
                        try:
                            price_elem = item.locator(sel).first
                            if price_elem.is_visible():
                                price_text = price_elem.inner_text()
                                price = clean_price(price_text)
                                if price:
                                    break
                        except:
                            continue
                    
                    # 评分
                    rating = None
                    try:
                        rating_elem = item.locator('[aria-label*="out of 5 stars"]').first
                        if rating_elem.is_visible():
                            rating_text = rating_elem.get_attribute('aria-label')
                            rating = extract_rating(rating_text)
                    except:
                        pass
                    
                    # 评论数
                    review_count = None
                    try:
                        review_elem = item.locator('[href*="#customerReviews"] .a-size-base').first
                        if review_elem.is_visible():
                            review_text = review_elem.inner_text()
                            review_count = extract_reviews(review_text)
                    except:
                        pass
                    
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
                    
                    price_str = f"${price:.2f}" if price else "N/A"
                    print(f"   ✓ {title[:50]}... {price_str}")
                    
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
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # 搜索所有关键词
            for keyword in SEARCH_KEYWORDS:
                print(f"🔍 关键词: {keyword}")
                for page_num in range(1, MAX_PAGES + 1):
                    products = self.scrape_search_page(page, keyword, page_num)
                    self.all_products.extend(products)
                    if page_num < MAX_PAGES:
                        time.sleep(2)
                print()
            
            browser.close()
        
        # 保存结果
        print(f"💾 保存 {len(self.all_products)} 个产品到 {OUTPUT_FILE}")
        
        if self.all_products:
            keys = ['asin', 'title', 'current_price', 'search_keyword', 'url', 'rating', 'review_count', 'scraped_at']
            with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for product in self.all_products:
                    writer.writerow(product)
            print(f"✅ 完成！文件: {OUTPUT_FILE}")
        else:
            print(f"⚠️ 没有找到任何产品")


if __name__ == "__main__":
    scraper = AmazonAUScraper()
    scraper.run()
