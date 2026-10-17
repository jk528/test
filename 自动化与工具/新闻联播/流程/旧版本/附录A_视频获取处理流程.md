# 附录A：视频获取处理流程

## A.1 问题背景

### 遇到的问题
- 使用搜索引擎无法直接获取央视网《新闻联播》完整视频分条信息
- 央视网视频页面使用 JavaScript 动态加载，视频地址通过 GUID 动态生成
- 搜索返回结果有限，仅能获取到第三方转载链接（如齐鲁网）

### 问题原因分析
1. **搜索策略局限**：WebSearch 工具搜索央视网视频列表时，搜索引擎返回结果非常有限
2. **页面动态加载**：央视网视频页面使用 JavaScript 动态渲染内容，静态抓取无法获取完整信息
3. **地址动态生成**：视频 URL 格式为 `https://tv.cctv.com/2026/06/20/VIDE{随机字符}{日期}.shtml`，其中 VIDE 后面的字符是动态生成的 GUID
4. **视频流加密**：视频播放使用 `blob:` 协议，实际视频流地址需要通过 API 接口获取

## A.2 解决方案

### 方案一：Python requests 直接获取页面源码（推荐）

**适用场景**：
- 需要获取完整的视频分条信息（时长、标题、URL）
- 需要定期更新视频列表
- **需要确保每条新闻都有独立的视频URL**
- 无需安装浏览器环境

**核心原理**：
央视网历史日期页面 `day/YYYYMMDD.shtml` 的原始HTML源码中已包含完整的视频列表结构（`<li>` 标签内嵌 `<a>` 链接和时长），虽然页面使用JavaScript进行前端渲染增强，但所有视频数据在服务端渲染时已经写入HTML。因此使用 `requests` 直接获取页面源码并解析，即可获得完整的视频列表，无需等待浏览器JavaScript执行。

**实现步骤**：

**步骤 1：访问央视网历史日期列表页**
```python
import requests
import re

url = "https://tv.cctv.com/lm/xwlb/day/20260624.shtml"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

resp = requests.get(url, headers=headers, timeout=30)
resp.encoding = 'utf-8'
html = resp.text
```

**步骤 2：从源码中提取视频列表（含独立URL）**
```python
# 匹配 <li> 内的视频条目
li_pattern = re.compile(
    r'<li[^>]*>.*?'
    r'(\d{2}:\d{2}:\d{2}).*?'
    r'<a[^>]*href=["\'](https://tv\.cctv\.com/[^"\']+)["\'][^>]*>(.*?)</a>.*?'
    r'</li>',
    re.DOTALL | re.IGNORECASE
)

matches = li_pattern.findall(html)
results = []
seen_urls = set()

for match in matches:
    duration = match[0]
    video_url = match[1]
    title_raw = match[2]

    if video_url in seen_urls:
        continue
    seen_urls.add(video_url)

    title = re.sub(r'<[^>]+>', '', title_raw).strip()
    title = title.replace('[视频]', '').strip()
    title = re.sub(r'^完整版', '', title).strip()

    results.append({
        "title": title,
        "duration": duration,
        "url": video_url
    })

print(f"共提取 {len(results)} 条视频")
# 验证URL唯一性
assert len(results) == len(seen_urls), "存在重复URL"
```

**步骤 3：验证URL可访问性**
```python
import requests

def verify_url(url):
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

for video in results:
    is_valid = verify_url(video['url'])
    print(f"{video['title']}: {'有效' if is_valid else '待验证'}")
```

**优势**：
- 无需安装浏览器（Playwright/Puppeteer/Selenium）
- 运行速度快（单次请求即可）
- 数据完整性高（源码中包含所有视频条目）
- 可复现为自动化脚本

### 方案二：浏览器自动化获取（备选）

**适用场景**：
- 页面结构发生重大变化，requests方案失效时
- 需要执行页面交互（如点击、翻页）

**技术工具**：Playwright / Puppeteer / Selenium

```python
from playwright.sync_api import sync_playwright

def get_xwlb_videos():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://tv.cctv.com/lm/xwlb/day/20260624.shtml')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)  # 等待JS渲染
        
        videos = page.evaluate('''() => {
            const items = document.querySelectorAll('li');
            return Array.from(items).map(item => {
                const link = item.querySelector('a');
                const duration = item.textContent.match(/(\d{2}:\d{2}:\d{2})/);
                return {
                    title: item.textContent.replace(duration ? duration[0] : '', '').trim(),
                    duration: duration ? duration[0] : '',
                    url: link ? link.href : ''
                };
            }).filter(v => v.url && v.duration);
        }''')
        
        browser.close()
        return videos
```

### 方案三：API 接口获取（进阶）

**适用场景**：
- 已知视频 GUID，需要获取视频详细信息
- 需要获取视频的真实播放地址

**视频信息接口**
```
接口地址：//api.cntv.cn/video/videoinfoByGuid
请求参数：
  - guid: 视频GUID（从页面URL中提取）
  - serviceId: 服务ID

示例：
//api.cntv.cn/video/videoinfoByGuid?guid=2flMySL99j9yksI4qlbc&serviceId=page
```

**GUID 提取方法**
```python
import re

url = 'https://tv.cctv.com/2026/06/20/VIDE2flMySL99j9yksI4qlbc260620.shtml'
guid = re.search(r'VIDE([^\.]+)', url).group(1)
guid = re.sub(r'\d{6}$', '', guid)
# 结果：2flMySL99j9yksI4qlbc
```

## A.3 注意事项

### 反爬虫策略
- 央视网可能有反爬虫机制，建议：
  - 设置合理的请求间隔（2-5秒）
  - 使用真实的 User-Agent
  - 必要时使用代理IP

### 页面结构变化
- 央视网页面结构可能会更新，需要：
  - 定期检查页面结构
  - 使用稳定的 CSS 选择器
  - 添加异常处理机制

### 视频地址有效期
- 视频播放地址可能有有效期限制
- 建议获取后及时使用或存储视频信息而非直接地址

### 版权说明
- 央视网视频内容受版权保护
- 获取的视频信息仅用于个人学习研究
- 禁止大规模爬取和商用

## A.4 常见问题

**Q1：为什么直接搜索获取不到视频列表？**
A：央视网视频列表通过 JavaScript 动态加载，搜索引擎爬虫无法执行 JavaScript，因此搜索结果显示不完整。

**Q2：视频 blob: 地址如何转换为真实地址？**
A：blob: 地址是浏览器本地生成的，需要通过央视网 API 接口获取真实的视频流地址。

**Q3：GUID 会变化吗？**
A：每个视频的 GUID 是固定的，但新发布的视频会生成新的 GUID。

**Q4：如何获取历史日期的视频？**
A：使用历史日期页面 `https://tv.cctv.com/lm/xwlb/day/YYYYMMDD.shtml`，该页面包含当日所有视频的独立分条链接和完整版链接。

**Q5：为什么报告中多条新闻用了同一个视频链接？**
A：这是最常见的错误。原因通常有：
1. 从搜索结果中只获取了一个视频URL，然后复制到所有新闻条目
2. 未访问历史日期页面，而是使用了默认列表页的单个链接
3. 未执行URL唯一性检查

**解决方法**：
- 必须访问 `https://tv.cctv.com/lm/xwlb/day/YYYYMMDD.shtml` 获取当日完整视频列表
- 每条新闻从页面中提取其对应的独立 `href`
- 使用 `Set` 去重验证URL唯一性
- 写入报告前，再次检查不同新闻条目是否共用URL

**Q6：如何验证报告中的视频链接都是独立的？**
A：使用以下PowerShell命令自查：
```powershell
# 提取所有央视网链接
$allUrls = Select-String -Path '新闻联播总结_20260624.md' -Pattern 'https://tv\.cctv\.com/[^)]+' -AllMatches | ForEach-Object { $_.Matches.Value }

# 统计每个URL出现次数
$allUrls | Group-Object | Sort-Object Count -Descending | Format-Table Name, Count

# 理想结果：每个URL只出现1次（对应1条新闻）
# 若某URL出现多次，说明多条新闻共用同一个链接，需要修正
```

**Q7：如果央视网某条新闻没有独立视频页面怎么办？**
A：正常情况下，央视网《新闻联播》的每条新闻（含完整版）都有独立的视频页面。若遇到缺失：
1. 检查是否访问了正确的历史日期页面
2. 刷新页面重新提取
3. 若确实缺失，使用该新闻所在快讯目录的汇总链接作为替代
4. 在报告中标注"该条新闻无独立视频页，使用快讯汇总页"

