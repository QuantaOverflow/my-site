---
layout: ../../layouts/Article.astro
title: "中国三大金融网站反爬虫策略与数据爬取全攻略"
date: 2026-03-26
description: "深度解析雪球、东方财富、同花顺的反爬机制，含完整 Python 代码与 AKShare 替代方案"
tags: [code]
---
> 先说结论：三个平台里**东方财富最好啃，雪球次之，同花顺最麻烦**。如果只是想拿财报和新闻数据，装个 AKShare 基本够用，不需要自己写爬虫。真正需要折腾的只有社区帖子和评论这块。

---


# 一、雪球：Cookie 拿到就成功了一半


雪球的防护思路其实挺简单粗暴——所有 API 都要带 Cookie，没有就直接返回 `error_code: 400016`。核心字段是 `xq_a_token`，一个 40 位的十六进制串，只要有它，大部分接口都能打通。


其他防护层倒不用太担心。Referer 校验几乎是摆设，删掉也能正常响应；User-Agent 只要别用默认的 `python-requests/x.x.x` 就行；频率限制在未登录状态下大概是每分钟 15 次，触发了会返回 429，指数退避等一下就好。


唯一麻烦的是首次访问时有时会碰到阿里系的 `acw_sc__v2` JS 加密，这种情况直接上 Selenium 拿一次 Cookie，后续就可以复用了。


**获取 Cookie 最省事的方式：**


```python
import requests, time, random

class XueqiuSpider:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://xueqiu.com",
            "Referer": "https://xueqiu.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        # 访问首页，服务器会自动 Set-Cookie，xq_a_token 就在里面
        self.session.get("https://xueqiu.com/", headers=self.headers)

    def _get(self, url, params=None):
        for attempt in range(3):
            resp = self.session.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 429:
                time.sleep((2 ** attempt) * 10)
                continue
            resp.raise_for_status()
            return resp.json()
        return None
```


遇到 JS 加密过不去的情况，用 Selenium 捞一次就好，之后不用再开浏览器：


```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)
driver.get("https://xueqiu.com")
xq_a_token = next(c["value"] for c in driver.get_cookies() if c["name"] == "xq_a_token")
driver.quit()
# 把这个 token 存下来，一般能用挺久
```


## 主要 API 接口


社区这边最常用的几个接口：


| 接口功能  | URL 路径                                          | 关键参数                                       |
| ----- | ----------------------------------------------- | ------------------------------------------ |
| 分类帖子流 | `/v4/statuses/public_timeline_by_category.json` | `category`：-1全部/102沪深/104港股/105美股/111基金    |
| 热帖列表  | `/statuses/hot/listV2.json`                     | `size=15, since_id=-1, max_id=-1`          |
| 帖子搜索  | `/statuses/search.json`                         | `q=关键词, sort=time/reply, page=1, count=10` |
| 股票评论  | `/statuses/search.json`                         | `symbol=SH600519, source=user, sort=time`  |


财务数据在 `stock.xueqiu.com/v5/stock/finance/{region}/` 下，region 填 `cn`/`hk`/`us`：


| 报表    | 路径               | 常用参数                                |
| ----- | ---------------- | ----------------------------------- |
| 利润表   | `income.json`    | `type=Q4` 拿年报，`Q1-Q3` 拿季报，`count=5` |
| 资产负债表 | `balance.json`   | 同上                                  |
| 现金流量表 | `cash_flow.json` | 同上                                  |
| 主要指标  | `indicator.json` | 同上                                  |
| 主营业务  | `business.json`  | `is_detail=true`                    |


实际调用：


```python
spider = XueqiuSpider()

# 热帖
hot = spider._get("https://xueqiu.com/statuses/hot/listV2.json",
                   {"since_id": -1, "max_id": -1, "size": 15})

# 茅台最近5年年报利润表
import time as t
income = spider._get("https://stock.xueqiu.com/v5/stock/finance/cn/income.json",
                      {"symbol": "SH600519", "type": "Q4", "is_detail": "true", "count": 5})

# 日K线，往前120天
kline = spider._get("https://stock.xueqiu.com/v5/stock/chart/kline.json",
                     {"symbol": "SH600519", "begin": int(t.time()*1000),
                      "period": "day", "type": "before", "count": -120, "indicator": "kline"})
```


请求间隔建议 2–4 秒，加点随机抖动 `random.uniform(2, 4)`。`xq_a_token` 有时效性，脚本跑之前最好重新访问一次首页刷新。嫌麻烦的话直接用 `pysnowball` 库（GitHub 1.7k stars），接口封装得不错。


## 遇到 WAF 拦截怎么办


如果请求频率偏高或 IP 被标记，雪球会触发阿里云 WAF，具体表现是页面返回「访问验证」滑块，或者 Cookie 里多出来需要动态计算的 `acw_sc__v2`，此时纯 requests 就过不去了。


### acw_sc__v2 逆向（纯 requests 可行）


这个 Cookie 的生成逻辑是阿里系的经典操作：服务器在页面 JS 里塞一个 `arg1`（十六进制字符串），你要用它跑一段 hexXor + unsbox 计算才能拿到真正的 Cookie 值。逆向社区（如 GitHub spider_reverse 仓库）已经有完整还原代码，大致用法如下：


```python
import re, execjs, requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://xueqiu.com/"
}

# 第一步：拿到包含 arg1 的页面
resp = requests.get("https://xueqiu.com/today", headers=headers).text
arg1 = re.search(r"var arg1='([A-F0-9]+)';", resp).group(1)

# 第二步：用逆向出来的 JS 计算 acw_sc__v2
# xueqiu.js 是本地保存的已逆向 JS 文件（含 unsbox、hexXor、get_cookie 函数）
with open("xueqiu.js", "r", encoding="utf-8") as f:
    js_code = f.read()
acw_sc__v2 = execjs.compile(js_code).call("get_cookie", arg1)

# 第三步：带上 Cookie 正常请求
cookies = {"acw_sc__v2": acw_sc__v2}
resp2 = requests.get("https://xueqiu.com/目标API", cookies=cookies, headers=headers)
```


注意两点：JS 文件需要自己从逆向社区获取或调试（文章里有无限 debugger，需要先绕过）；`acw_sc__v2` 有效期较短，建议每次跑脚本前重新计算。另外首次访问还会植入一个 `acw_tc`（有效期约 30 分钟），这个直接带着就行，不需要额外处理。


### WAF 滑块验证码（行为验证）


如果触发了滑块弹窗，纯逆向就不够用了——阿里的行为验证会检测鼠标轨迹的速度曲线、停顿、加速度，简单 `move_to_element` 直接被识别。需要模拟真人拖动轨迹：


```python
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import random, time

driver = webdriver.Chrome(options=...)  # 建议加 stealth 插件或用 undetected-chromedriver
driver.get("https://xueqiu.com/")

# 等滑块出现
slider = driver.find_element("css selector", "#aliyunCaptcha-sliding-slider")
offset = 300  # 根据实际滑块宽度调整，或用 OpenCV 模板匹配精确计算

action = ActionChains(driver)
action.click_and_hold(slider).pause(random.uniform(0.2, 0.5))
# 分段拖动 + 加入随机抖动，模拟人手的不稳定
for i in range(10):
    dx = offset / 10 + random.randint(-2, 2)
    action.move_by_offset(dx, random.randint(-1, 1)).pause(random.uniform(0.01, 0.03))
action.release().perform()
time.sleep(1)  # 等待验证通过
```


轨迹生成用贝塞尔曲线会更自然，通过率大概能到 80% 以上。多次失败就换 IP 重试。这种场景下推荐用 **DrissionPage** 替代 Selenium，它对阿里系检测的规避效果更好，内置了不少反指纹处理。


---


# 二、东方财富：行情接口基本不设防


东方财富是三家里最好爬的，核心行情 API 根本不需要登录或 Cookie，直接带个 Referer 就能跑通。真正需要注意的反爬点只有两个：股吧爬多了会封 IP（大概 50–60 页触发，封约 1 小时），以及早期部分接口用 JSONP 格式包了一层——不传 `cb` 参数就能直接拿到纯 JSON，不用额外处理。


数据字段用的是代号体系（`f2` = 最新价，`f3` = 涨跌幅……），第一次看挺懵的，对着文档映射一遍就好。


## 全市场实时行情（一个请求搞定）


```python
import requests, pandas as pd

def get_all_a_stocks():
    url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "20000",
        "po": "1", "np": "2",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2",
        "fid": "f3",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",  # 沪深A股
        "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f12,f14,f15,f16,f17,f18,f20,f21,f23",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    data = requests.get(url, params=params, headers=headers).json()
    field_map = {
        "f2": "最新价", "f3": "涨跌幅", "f4": "涨跌额", "f5": "成交量",
        "f6": "成交额", "f12": "代码", "f14": "名称", "f20": "总市值",
        "f21": "流通市值", "f23": "市净率", "f9": "市盈率动",
    }
    return pd.DataFrame(data["data"]["diff"]).rename(columns=field_map)
```


URL 前缀的数字（38/48/82 等）随便换都能用，应该是负载均衡节点。


## 历史 K 线


```python
def get_kline(code, beg="20240101", end="20500101", klt=101, fqt=1):
    """klt: 101日K/102周K/103月K  fqt: 0不复权/1前复权/2后复权"""
    secid = f"1.{code}" if code[0] == "6" else f"0.{code}"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": str(klt), "fqt": str(fqt), "secid": secid,
        "beg": beg, "end": end,
    }
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
    data = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get",
                        params=params, headers=headers).json()
    cols = ["日期","开盘","收盘","最高","最低","成交量","成交额","振幅","涨跌幅","涨跌额","换手率"]
    klines = [x.split(",") for x in data["data"]["klines"]]
    return pd.DataFrame(klines, columns=cols).apply(pd.to_numeric, errors="ignore")
```


## 财务报表（全市场批量）


数据中心接口 `datacenter-web.eastmoney.com/api/data/v1/get` 可以批量拉全市场财报，这是东方财富最有价值的接口之一：


```python
import time

class EastMoneyFinance:
    URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }
    REPORTS = {
        "利润表": "RPT_DMSK_FN_INCOME",
        "资产负债表": "RPT_DMSK_FN_BALANCE",
        "现金流量表": "RPT_DMSK_FN_CASHFLOW",
        "业绩报表": "RPT_LICO_FN_CPD",
        "业绩预告": "RPT_PUBLIC_OP_NEWPREDICT",
    }

    def get_all_pages(self, report_type, report_date):
        all_data, page = [], 1
        while True:
            params = {
                "sortColumns": "NOTICE_DATE,SECURITY_CODE", "sortTypes": "-1,-1",
                "pageSize": "50", "pageNumber": str(page),
                "reportName": self.REPORTS[report_type], "columns": "ALL", "source": "WEB",
                "filter": f"(REPORT_DATE='{report_date}')",
            }
            resp = requests.get(self.URL, params=params, headers=self.HEADERS).json()
            if not resp.get("success") or not resp.get("result"): break
            all_data.extend(resp["result"]["data"])
            if page >= resp["result"]["pages"]: break
            page += 1
            time.sleep(0.5)
        return pd.DataFrame(all_data)

# 拉2024年年报全市场利润表
df = EastMoneyFinance().get_all_pages("利润表", "2024-12-31")
```


## 股吧爬取


股吧是东方财富里反爬最积极的地方，超过 50 页就容易被封 IP。结构是普通 HTML，requests 就够用：


```python
from bs4 import BeautifulSoup

def crawl_guba(stock_code, pages=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://guba.eastmoney.com/",
    }
    all_posts = []
    for page in range(1, pages + 1):
        url = f"http://guba.eastmoney.com/list,{stock_code}_{page}.html"
        resp = requests.get(url, headers=headers)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        for t in soup.select(".l3.a3")[1:]:
            all_posts.append({"标题": t.text.strip()})
        time.sleep(random.uniform(2, 4))
    return pd.DataFrame(all_posts)
```


行情 API 可以打到 1–2 次/秒，财务数据中心 0.5–1 次/秒，股吧建议 1次/3秒以上，量大的话备好代理池。


---


# 三、同花顺：hexin-v 是真的烦


同花顺是三家里反爬做得最认真的，核心机制是 **hexin-v** 这个动态加密参数——同时塞在 Cookie 的 `v` 字段和请求头的 `Hexin-V` 字段里，缺一个都会被 Nginx 直接拒掉。


它的生成逻辑大致是：浏览器加载 `chameleon.min.{版本号}.js` → 核心函数收集一堆环境信息（服务器时间戳、UA 哈希、鼠标轨迹等）→ 经过魔改的 base64 编码出最终值。最恶心的地方在于它不是按时间失效，而是**按使用次数失效，大概用 5–10 次就得重新生成一个**，这意味着你不能只拿一次就反复用，得做自动刷新。


## 四种拿 hexin-v 的方式


**方案一：Selenium（最稳，新手首选）**


让浏览器真实执行 JS，Cookie 就自然有了。注意要去掉 webdriver 特征，不然可能被检测到：


```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def get_hexin_v():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator,"webdriver",{get:()=>undefined})'})
    driver.get("http://q.10jqka.com.cn/")
    time.sleep(3)
    hexin_v = next((c["value"] for c in driver.get_cookies() if c["name"] == "v"), None)
    driver.quit()
    return hexin_v
```


**方案二：Node.js 执行逆向 JS（生产环境推荐）**


逆向出 `chameleon.min.js`，补好环境变量后用 Node.js 跑，速度比 Selenium 快多了，也不用开浏览器进程：


```python
import subprocess

def get_hexin_v_node():
    # hexin_v.js = 逆向出来的加密函数 + 补的 document/window 对象
    result = subprocess.run(["node", "hexin_v.js"], capture_output=True, text=True)
    return result.stdout.strip()
```


逆向步骤：① Cookie Hook 定位生成 `v` 的 JS 文件 → ② 提取 `chameleon.min.xxx.js` → ③ 补 `document={}`、`window={}` → ④ 用 v_jstools 浏览器扩展辅助补环境 → ⑤ 导出加密函数。这条路需要一定 JS 逆向基础，不熟悉的话先用方案一。


**方案三：PyExecJS（Python 里直接跑 JS）**


```python
import execjs

def get_hexin_v_execjs():
    with open("hexin_v_env.js", "r", encoding="utf-8") as f:
        ctx = execjs.compile(f.read())
    return ctx.call("get_v")
```


**方案四：pywencai（只需要问财功能的话）**


```python
import pywencai  # pip install pywencai，依赖 Node.js v16+

result = pywencai.get(query="市盈率小于20且净利润增速大于30的股票",
                      cookie="浏览器里复制的Cookie", loop=True, sleep=1)
```


## 财务接口有个免认证的漏网之鱼


同花顺的 `basic.10jqka.com.cn` 有个直接返回 JSON 的财务接口，**不需要 hexin-v**，是最省力的突破口：


```python
def get_ths_finance(stock_code):
    url = f"https://basic.10jqka.com.cn/api/stock/finance/{stock_code}_main.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"http://basic.10jqka.com.cn/{stock_code}/finance.html",
    }
    return requests.get(url, headers=headers).json()

data = get_ths_finance("600519")  # 贵州茅台，直接出数据
```


需要 hexin-v 的行情列表爬虫，记得做自动刷新：


```python
import copy, requests
from parsel import Selector

class THSSpider:
    def __init__(self):
        self.session = requests.Session()
        self.hexin_v = None
        self.base_headers = {
            "Host": "q.10jqka.com.cn",
            "Referer": "http://q.10jqka.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

    def get_stock_list(self, page=1):
        if not self.hexin_v:
            self.hexin_v = get_hexin_v()
        headers = copy.deepcopy(self.base_headers)
        headers["hexin-v"] = self.hexin_v
        headers["Cookie"] = f"v={self.hexin_v}"
        url = f"http://q.10jqka.com.cn/index/index/board/all/field/zdf/order/desc/page/{page}/ajax/1/"
        resp = self.session.get(url, headers=headers)
        resp.encoding = "GBK"
        if "Nginx forbidden" in resp.text:
            # hexin-v 用完了，刷新一个再试
            self.hexin_v = get_hexin_v()
            return self.get_stock_list(page)
        sel = Selector(text=resp.text)
        return [{"代码": r.css("td:nth-child(2)::text").get(""),
                 "名称": r.css("td:nth-child(3)::text").get(""),
                 "现价": r.css("td:nth-child(4)::text").get(""),
                 "涨跌幅": r.css("td:nth-child(5)::text").get("")}
                for r in sel.css("tbody tr")]
```


频率方面：行情列表 2–5 秒/页，`basic.10jqka.com.cn` 这个免认证接口可以稍微快一点，1–2 秒/个。问财建议 3–5 秒/次别太急。返回 "Nginx forbidden" 就说明 hexin-v 失效了，触发自动刷新。


---


# 四、能用开源库就别自己造轮子


说实话，财报和新闻数据根本不用自己爬——AKShare、BaoStock、Tushare Pro 已经把主要接口都封装好了，省去了大量调试时间。


## 三个库的横向对比


|         | AKShare         | BaoStock     | Tushare Pro      |
| ------- | --------------- | ------------ | ---------------- |
| 费用      | 完全免费            | 完全免费         | 积分制（100元/1000积分） |
| 注册      | 无需              | 无需           | 需要 Token         |
| 接口数量    | 2000+           | ~20          | 200+             |
| 数据来源    | 东方财富+同花顺+雪球+新浪等 | 自有数据库        | 自有数据库            |
| 社区热度/排行 | ✅               | ❌            | ✅                |
| 财经新闻    | ✅ 东财/同花顺/财联社/富途 | ❌            | ✅                |
| 三大财务报表  | ✅ 东财+同花顺双源      | ✅ 季频（2007年起） | ✅ 需≥2000积分       |
| 帖子正文/评论 | ❌               | ❌            | ❌                |


**注意**：三个库都不支持帖子正文和评论——这块只能自己写爬虫，没有捷径。


## AKShare 常用调用


```python
import akshare as ak

# 社区热度
follow_rank = ak.stock_hot_follow_xq(symbol="SH600519")    # 雪球关注排行
hot_rank = ak.stock_hot_rank_em()                           # 东财人气榜

# 新闻（多源）
news_em = ak.stock_info_global_em()      # 东方财富
news_ths = ak.stock_info_global_ths()    # 同花顺
news_cls = ak.stock_info_global_cls()    # 财联社

# 财务报表
balance = ak.stock_balance_sheet_by_report_em(symbol="SH600519")
profit = ak.stock_profit_sheet_by_report_em(symbol="SH600519")
cashflow = ak.stock_cash_flow_sheet_by_report_em(symbol="SH600519")

# 同花顺源（可以和东财数据交叉验证）
abstract = ak.stock_financial_abstract_new_ths(symbol="600519")
forecast = ak.stock_profit_forecast_ths(symbol="600519")
```


## BaoStock 适合做历史回测


接口虽然少，但历史数据干净，从 1990 年到现在都有，而且不用担心被封：


```python
import baostock as bs

bs.login()
rs = bs.query_history_k_data_plus("sh.600519",
    "date,code,open,high,low,close,volume,amount",
    start_date="2024-01-01", end_date="2024-12-31",
    frequency="d", adjustflag="3")  # 3=后复权
profit = bs.query_profit_data(code="sh.600519", year=2023, quarter=4)
bs.logout()
```


---


# 五、按数据类型选方案


**社区帖子和评论**：三个库都不支持，必须自己写。优先级建议：雪球（Session+Cookie，最好搞）> 东方财富股吧（requests 解析 HTML，注意 50 页限制）> 同花顺（hexin-v 门槛高，能不爬就不爬）。


**财经新闻**：AKShare 一行代码搞定，东财/同花顺/财联社/富途四个源随便选，不需要自己写。


**财报和财务指标**：首选 AKShare，东方财富源和同花顺源可以交叉验证互相校对。对数据质量要求极高的场景，Tushare Pro 的数据更规范。历史回测场景用 BaoStock，从 1990 年起的数据都有，字段少但稳定。


---


# 最后说几句


频率控制没什么特别技巧，所有平台统一保持 2–3 秒间隔 + 随机抖动就行，大量采集上代理池。同花顺记得做 hexin-v 自动刷新（返回 "Nginx forbidden" 就触发），每个值只能用 5–10 次。


**一个容易踩的坑**：不要在交易时段用这些接口高频拉行情数据，一方面容易触发限流，另一方面非交易时段数据是静态的，稳定很多，跑历史数据都放到收盘后再跑。


数据量特别大或者对数据质量要求很高的场景，认真考虑一下同花顺 iFinD 或者 Wind，折腾爬虫的时间成本算进去，付费接口其实挺划算的。

