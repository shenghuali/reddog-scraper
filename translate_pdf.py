import asyncio
from playwright.async_api import async_playwright
import os

html1 = """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap" rel="stylesheet">
<style>
    body { font-family: 'Noto Sans SC', sans-serif; margin: 40px; color: #333; line-height: 1.5; font-size: 14px; }
    h1 { font-size: 20px; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 5px; }
    h2 { font-size: 16px; color: #34495e; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 12px; }
    th, td { border: 1px solid #bdc3c7; padding: 8px; text-align: left; }
    th { background-color: #ecf0f1; color: #2c3e50; }
    .alert { color: #e74c3c; font-weight: bold; margin-bottom: 20px; }
    .header-info { margin-bottom: 20px; }
    .header-info p { margin: 2px 0; }
</style>
</head>
<body>
    <h1>居家养老支持月度对账单 (Support at Home Monthly Statement)</h1>
    <p><strong>2026年2月账单 (Statement for February 2026)</strong></p>
    
    <div class="header-info">
        <p><strong>单号:</strong> STA-023561</p>
        <p><strong>客户:</strong> Yong Xian Zheng</p>
        <p><strong>地址:</strong> 37A WILSON ROAD, Glen Waverley VIC 3150</p>
    </div>

    <h2>账单详情 (Statement Details)</h2>
    <p><strong>月份 (Month):</strong> 2026年2月<br>
    <strong>服务提供商 (Provider):</strong> 阳光居家护理服务 (Sunny Home Care Services)</p>
    
    <p class="alert">这不是一张收费单。如果您需要支付自费部分，您将会收到一份单独的发票。<br>
    (This is not a bill. You will receive a separate invoice if you need to pay a contribution.)</p>

    <h2>您的居家养老支持摘要 (Your Support at Home Summary)</h2>
    <p>生成账单时的余额摘要 (Summary balances at time of statement generation)</p>
    <table>
        <tr><th>预算项目 (Budget)</th><th>期初余额 (Opening)</th><th>已花费 (Spent)</th><th>期末余额 (Closing)</th></tr>
        <tr><td>持续性居家支持 - 2026年3月31日到期 (Home support ongoing)</td><td>$7,298.00</td><td>$1,504.58</td><td>$5,793.42</td></tr>
        <tr><td>居家护理账户 (Home care account)</td><td>$9,454.21</td><td>$0.00</td><td>$9,454.21</td></tr>
    </table>

    <h2>您的自费部分摘要 (Your Co-Contributions Summary)</h2>
    <ul>
        <li>期初余额 - 截至2026年2月1日未付 (Opening balance): $0.00</li>
        <li>本月新增自费金额 (New contributions this month): $153.87</li>
        <li>本月已付自费金额 (Contributions paid this month): $0.00</li>
        <li><strong>期末余额 - 截至2026年2月28日未付 (Closing balance): $153.87</strong></li>
    </ul>

    <h2>自费发票明细 (Contribution Invoices) - 2026年2月</h2>
    <table>
        <tr><th>日期 (Date)</th><th>发票号 (Invoice #)</th><th>服务项目 (Services)</th><th>状态 (Status)</th><th>金额 (Amount)</th></tr>
        <tr><td colspan="5" style="text-align:center;">无记录 (No items)</td></tr>
    </table>

    <h2>您在2026年2月接受的服务 (Services You Received in February 2026)</h2>
    <table>
        <tr><th>日期 (Date)</th><th>服务项目 (Service)</th><th>数量 (Units)</th><th>总费用 (Cost)</th><th>政府支付 (Govt Pays)</th><th>您支付 (You Pay)</th></tr>
        <tr><td>2月4日</td><td>团体社交支持 (Group social support)</td><td>1</td><td>$99.00</td><td>$88.75</td><td>$10.25</td></tr>
        <tr><td>2月5日</td><td>常规房屋清洁 (General house cleaning)</td><td>2</td><td>$190.00</td><td>$112.19</td><td>$37.41</td></tr>
        <tr><td>2月6日</td><td>心理辅导 (Psychology)</td><td>2</td><td>$277.20</td><td>$277.20</td><td>$0.00</td></tr>
        <tr><td>2月6日</td><td>团体社交支持 (Group social support)</td><td>1</td><td>$49.50</td><td>$44.38</td><td>$5.12</td></tr>
        <tr><td>2月12日</td><td>团体社交支持 (Group social support)</td><td>1</td><td>$327.80</td><td>$293.84</td><td>$33.96</td></tr>
        <tr><td>2月13日</td><td>物理治疗/理疗 (Physiotherapy)</td><td>2</td><td>$328.90</td><td>$328.90</td><td>$0.00</td></tr>
        <tr><td>2月18日</td><td>送餐服务 (Meal delivery)</td><td>1</td><td>$59.84</td><td>$44.91</td><td>$14.93</td></tr>
        <tr><td>2月19日</td><td>常规房屋清洁 (General house cleaning)</td><td>2</td><td>$149.60</td><td>$112.28</td><td>$37.32</td></tr>
        <tr><td>2月25日</td><td>送餐服务 (Meal delivery)</td><td>1</td><td>$63.14</td><td>$47.39</td><td>$15.75</td></tr>
        <tr><td colspan="3"><strong>总计 (Total):</strong></td><td><strong>$1,544.98</strong></td><td><strong>$1,349.84</strong></td><td><strong>$154.74</strong></td></tr>
    </table>

    <h2>影响您预算的服务项目 (Services Affecting Your Budgets)</h2>
    <p><strong>持续性居家支持 (Home Support Ongoing - ON)</strong></p>
    <table>
        <tr><th>服务项目 (Service)</th><th>数量 (Units)</th><th>已花费 (Spent)</th></tr>
        <tr><td>常规房屋清洁 (General house cleaning)</td><td>4</td><td>$299.20</td></tr>
        <tr><td>团体社交支持 (Group social support)</td><td>3</td><td>$476.30</td></tr>
        <tr><td>间接交通 (Indirect transport)</td><td>0</td><td>$16.64</td></tr>
        <tr><td>送餐服务 (Meal delivery)</td><td>2</td><td>$122.98</td></tr>
        <tr><td>物理治疗/理疗 (Physiotherapy)</td><td>2</td><td>$328.90</td></tr>
        <tr><td>心理辅导 (Psychology)</td><td>2</td><td>$277.20</td></tr>
        <tr><td colspan="2"><strong>总计 (Total):</strong></td><td><strong>$1,521.22</strong></td></tr>
    </table>

    <h2>往月服务费用调整 (Services Adjusted For Previous Months)</h2>
    <table>
        <tr><th>日期 (Date)</th><th>服务项目 (Service)</th><th>数量 (Units)</th><th>总费用 (Cost)</th><th>政府支付 (Govt Pays)</th><th>您支付 (You Pay)</th></tr>
        <tr><td>1月20日</td><td>间接交通 - 出租车服务 (Indirect transport - Taxi service)</td><td>1</td><td>$8.32</td><td>$7.45</td><td>$0.87</td></tr>
        <tr><td colspan="3"><strong>总计 (Total):</strong></td><td><strong>$8.32</strong></td><td><strong>$7.45</strong></td><td><strong>$0.87</strong></td></tr>
    </table>
</body>
</html>
"""

html2 = """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap" rel="stylesheet">
<style>
    body { font-family: 'Noto Sans SC', sans-serif; margin: 40px; color: #333; line-height: 1.5; font-size: 14px; }
    h1 { font-size: 20px; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 5px; }
    h2 { font-size: 16px; color: #34495e; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 12px; }
    th, td { border: 1px solid #bdc3c7; padding: 8px; text-align: left; }
    th { background-color: #ecf0f1; color: #2c3e50; }
    .alert { color: #e74c3c; font-weight: bold; margin-bottom: 20px; }
    .header-info { margin-bottom: 20px; }
    .header-info p { margin: 2px 0; }
</style>
</head>
<body>
    <h1>居家养老支持月度对账单 (Support at Home Monthly Statement)</h1>
    <p><strong>2026年2月账单 (Statement for February 2026)</strong></p>
    
    <div class="header-info">
        <p><strong>单号:</strong> STA-023593</p>
        <p><strong>客户:</strong> Zhixin Qiu</p>
        <p><strong>地址:</strong> 37A WILSON ROAD, GLEN WAVERLEY VIC 3150</p>
    </div>

    <h2>账单详情 (Statement Details)</h2>
    <p><strong>月份 (Month):</strong> 2026年2月<br>
    <strong>服务提供商 (Provider):</strong> 阳光居家护理服务 (Sunny Home Care Services)</p>
    
    <p class="alert">这不是一张收费单。如果您需要支付自费部分，您将会收到一份单独的发票。<br>
    (This is not a bill. You will receive a separate invoice if you need to pay a contribution.)</p>

    <h2>您的居家养老支持摘要 (Your Support at Home Summary)</h2>
    <p>生成账单时的余额摘要 (Summary balances at time of statement generation)</p>
    <table>
        <tr><th>预算项目 (Budget)</th><th>期初余额 (Opening)</th><th>已花费 (Spent)</th><th>期末余额 (Closing)</th></tr>
        <tr><td>持续性居家支持 - 2026年3月31日到期 (Home support ongoing)</td><td>$1,798.25</td><td>$677.43</td><td>$1,120.82</td></tr>
    </table>

    <h2>您的自费部分摘要 (Your Co-Contributions Summary)</h2>
    <ul>
        <li>期初余额 - 截至2026年2月1日未付 (Opening balance): $0.00</li>
        <li>本月新增自费金额 (New contributions this month): $41.96</li>
        <li>本月已付自费金额 (Contributions paid this month): $0.00</li>
        <li><strong>期末余额 - 截至2026年2月28日未付 (Closing balance): $41.96</strong></li>
    </ul>

    <h2>自费发票明细 (Contribution Invoices) - 2026年2月</h2>
    <table>
        <tr><th>日期 (Date)</th><th>发票号 (Invoice #)</th><th>服务项目 (Services)</th><th>状态 (Status)</th><th>金额 (Amount)</th></tr>
        <tr><td colspan="5" style="text-align:center;">无记录 (No items)</td></tr>
    </table>

    <h2>您在2026年2月接受的服务 (Services You Received in February 2026)</h2>
    <table>
        <tr><th>日期 (Date)</th><th>服务项目 (Service)</th><th>数量 (Units)</th><th>总费用 (Cost)</th><th>政府支付 (Govt Pays)</th><th>您支付 (You Pay)</th></tr>
        <tr><td>2月12日</td><td>团体社交支持 (Group social support)</td><td>1</td><td>$327.80</td><td>$293.84</td><td>$33.96</td></tr>
        <tr><td>2月13日</td><td>间接交通 - 出租车服务 (Indirect transport - Taxi service)</td><td>1</td><td>$35.18</td><td>$31.54</td><td>$3.64</td></tr>
        <tr><td>2月13日</td><td>间接交通 - 出租车服务 (Indirect transport - Taxi service)</td><td>1</td><td>$50.45</td><td>$45.23</td><td>$5.22</td></tr>
        <tr><td>2月24日</td><td>物理治疗/理疗 (Physiotherapy)</td><td>1</td><td>$264.00</td><td>$264.00</td><td>$0.00</td></tr>
        <tr><td colspan="3"><strong>总计 (Total):</strong></td><td><strong>$677.43</strong></td><td><strong>$634.61</strong></td><td><strong>$42.82</strong></td></tr>
    </table>

    <h2>影响您预算的服务项目 (Services Affecting Your Budgets)</h2>
    <p><strong>持续性居家支持 (Home Support Ongoing - ON)</strong></p>
    <table>
        <tr><th>服务项目 (Service)</th><th>数量 (Units)</th><th>已花费 (Spent)</th></tr>
        <tr><td>团体社交支持 (Group social support)</td><td>1</td><td>$327.80</td></tr>
        <tr><td>间接交通 (Indirect transport)</td><td>2</td><td>$102.13</td></tr>
        <tr><td>物理治疗/理疗 (Physiotherapy)</td><td>1</td><td>$264.00</td></tr>
        <tr><td colspan="2"><strong>总计 (Total):</strong></td><td><strong>$693.93</strong></td></tr>
    </table>

    <h2>往月服务费用调整 (Services Adjusted For Previous Months)</h2>
    <table>
        <tr><th>日期 (Date)</th><th>服务项目 (Service)</th><th>数量 (Units)</th><th>总费用 (Cost)</th><th>政府支付 (Govt Pays)</th><th>您支付 (You Pay)</th></tr>
        <tr><td>1月20日</td><td>间接交通 - 出租车服务 (Indirect transport - Taxi service)</td><td>1</td><td>$8.25</td><td>$7.39</td><td>$0.86</td></tr>
        <tr><td colspan="3"><strong>总计 (Total):</strong></td><td><strong>$8.25</strong></td><td><strong>$7.39</strong></td><td><strong>$0.86</strong></td></tr>
    </table>
</body>
</html>
"""

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = await browser.new_page()
            
            with open('doc1.html', 'w', encoding='utf-8') as f:
                f.write(html1)
            await page.goto(f"file://{os.path.abspath('doc1.html')}", wait_until='networkidle')
            await page.pdf(path='Yong_Xian_Zheng_CN.pdf', format='A4', print_background=True)
            
            with open('doc2.html', 'w', encoding='utf-8') as f:
                f.write(html2)
            await page.goto(f"file://{os.path.abspath('doc2.html')}", wait_until='networkidle')
            await page.pdf(path='Zhixin_Qiu_CN.pdf', format='A4', print_background=True)
            
            await browser.close()
            print("PDFs generated successfully")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
