#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
齐鲁网新闻联播索引页抓取脚本
自动定位目标日期的索引页，提取所有子条目链接，并执行脱敏处理

版本：v1.0.0（2026-07-11）
"""
import requests
import re
import json
import sys
import os
import argparse
import logging
from datetime import datetime, date, timedelta
from urllib.parse import unquote

# 复用 fetch_xwlb.py 的脱敏映射表和函数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from fetch_xwlb import desensitize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, "fetch_iqilu.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

MAX_PAGES = 30  # 最多翻页数
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url):
    """获取页面内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        logger.warning(f"请求失败 {url}: {e}")
        return None


def extract_entries(html):
    """
    从索引页HTML中提取所有条目（标题+URL+日期）
    返回 list[dict]: [{title, url, date_str}, ...]
    """
    entries = []
    # 匹配模式：<a href="https://v.iqilu.com/jcdb/ysxwlb/..." ...>标题</a>
    # 同时提取日期标记（"时间 2026-06-09"）
    
    # 先按条目分割
    # 模式：### [标题](URL) ... 时间 YYYY-MM-DD
    pattern = re.compile(
        r'###\s*\[([^\]]+)\]\(([^)]+)\).*?时间\s*(\d{4}-\d{2}-\d{2})',
        re.DOTALL
    )
    matches = pattern.findall(html)
    
    for title, url, date_str in matches:
        entries.append({
            "title": title.strip(),
            "url": url.strip(),
            "date_str": date_str.strip()
        })
    
    # 备用模式：直接匹配 <a href> 标签
    if not entries:
        a_pattern = re.compile(
            r'<a[^>]*href="(https://v\.iqilu\.com/jcdb/ysxwlb/[^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        a_matches = a_pattern.findall(html)
        
        # 尝试从上下文提取日期
        date_pattern = re.compile(r'时间\s*(\d{4}-\d{2}-\d{2})')
        dates = date_pattern.findall(html)
        
        for i, (url, title) in enumerate(a_matches):
            date_str = dates[i] if i < len(dates) else ""
            entries.append({
                "title": title.strip(),
                "url": url.strip(),
                "date_str": date_str.strip()
            })
    
    return entries


def find_complete_anchors(html):
    """
    查找页面中所有完整版锚点
    返回 list[dict]: [{date_str, title, url}, ...]
    """
    anchors = []
    # 模式：YYYY年MM月DD日中央新闻联播完整版
    pattern = re.compile(
        r'(\d{4})年(\d{2})月(\d{2})日中央新闻联播完整版.*?href="(https://v\.iqilu\.com[^"]+)"',
        re.DOTALL
    )
    matches = pattern.findall(html)
    
    for y, m, d, url in matches:
        date_str = f"{y}-{m}-{d}"
        anchors.append({
            "date_str": date_str,
            "url": url.strip()
        })
    
    # 备用：从标题列表中查找
    if not anchors:
        for entry in extract_entries(html):
            if "完整版" in entry["title"] and "中央新闻联播" in entry["title"]:
                anchors.append(entry)
    
    return anchors


def get_page_url(page_num):
    """根据页码生成URL"""
    if page_num == 1:
        return "https://v.iqilu.com/jcdb/ysxwlb/index.html"
    else:
        return f"https://v.iqilu.com/jcdb/ysxwlb/index_{page_num - 1}.html"


def collect_entries_from_page(html, target_date_str, seen_urls):
    """
    从单个页面HTML中提取目标日期的子条目
    :param html: 页面HTML内容
    :param target_date_str: 目标日期 YYYY-MM-DD
    :param seen_urls: 已记录的URL集合（去重用）
    :return: (entries_list, complete_url) 该页面中找到的目标日期条目和完整版URL
    """
    entries = []
    complete_url = None
    
    all_entries = extract_entries(html)
    anchors = find_complete_anchors(html)
    
    # 查找完整版URL
    for a in anchors:
        if a["date_str"] == target_date_str:
            complete_url = a.get("url", None)
            break
    
    # 筛选目标日期的子条目
    for e in all_entries:
        if e["date_str"] == target_date_str and "完整版" not in e["title"]:
            if e["url"] not in seen_urls:
                seen_urls.add(e["url"])
                entries.append(e)
    
    return entries, complete_url


def search_target_date(target_date_str, start_page=1, max_pages=MAX_PAGES):
    """
    在齐鲁网索引页中搜索目标日期，支持跨页补全
    :param target_date_str: 目标日期 YYYY-MM-DD
    :param start_page: 起始页码
    :return: (entries_list, complete_url) 目标日期的所有子条目和完整版URL
    """
    target_yyyymmdd = target_date_str.replace("-", "")
    seen_urls = set()  # 用于去重
    all_target_entries = []  # 收集所有页面找到的目标日期条目
    complete_url = None  # 完整版URL
    found_page_num = None  # 首次找到目标日期的页面号
    
    # 第一阶段：找到包含目标日期的页面
    for page_num in range(start_page, start_page + max_pages):
        url = get_page_url(page_num)
        logger.info(f"搜索索引页 {page_num}: {url}")
        html = fetch_page(url)
        if not html:
            continue
        
        # 快速检查：页面是否包含目标日期
        has_target = target_date_str in html or target_yyyymmdd in html
        
        if not has_target:
            # 通过完整版锚点判断是否需要继续搜索
            anchors = find_complete_anchors(html)
            if anchors:
                all_dates = [a["date_str"] for a in anchors if a["date_str"]]
                if all_dates:
                    newest = max(all_dates)
                    oldest = min(all_dates)
                    logger.info(f"  页面日期范围: {oldest} ~ {newest}")
                    
                    if target_date_str > newest:
                        # 目标日期比页面最新日期还新，往前翻（页面是按倒序排列的，新的在上）
                        continue
                    elif target_date_str < oldest:
                        # 目标日期比页面最旧日期还老，可能翻过头了，但继续检查几页确认
                        # 允许再往后翻2页作为缓冲
                        pass
            continue
        
        # 找到包含目标日期的页面
        logger.info(f"  ✓ 在页面 {page_num} 找到目标日期 {target_date_str}")
        found_page_num = page_num
        
        # 从当前页面收集条目
        entries, url = collect_entries_from_page(html, target_date_str, seen_urls)
        all_target_entries.extend(entries)
        if url and not complete_url:
            complete_url = url
        
        logger.info(f"  当前页收集到 {len(entries)} 条子条目")
        break
    
    if found_page_num is None:
        logger.error(f"在 {max_pages} 页内未找到目标日期 {target_date_str}")
        return [], None
    
    # 第二阶段：跨页补全 —— 遍历前后相邻页面
    logger.info(f"开始跨页补全，主页面: {found_page_num}")
    
    # 检查范围：前后各2页
    for offset in [-2, -1, 1, 2]:
        check_page = found_page_num + offset
        if check_page < 1:
            continue
        
        check_url = get_page_url(check_page)
        logger.info(f"  检查相邻页 {check_page}: {check_url}")
        check_html = fetch_page(check_url)
        if not check_html:
            continue
        
        # 检查相邻页面是否包含目标日期
        if target_date_str not in check_html and target_yyyymmdd not in check_html:
            logger.info(f"    页面 {check_page} 不包含目标日期，跳过")
            continue
        
        # 从相邻页面收集目标日期条目
        entries, url = collect_entries_from_page(check_html, target_date_str, seen_urls)
        if entries:
            all_target_entries.extend(entries)
            logger.info(f"    从页面 {check_page} 补充 {len(entries)} 条子条目")
        if url and not complete_url:
            complete_url = url
            logger.info(f"    从页面 {check_page} 找到完整版URL")
    
    # 按URL中的ID排序（齐鲁网URL通常包含ID，按ID排序可恢复时间顺序）
    def sort_key(entry):
        # 从URL中提取数字ID作为排序键
        match = re.search(r'(\d+)\.html$', entry["url"])
        if match:
            return int(match.group(1))
        return 0
    
    all_target_entries.sort(key=sort_key)
    
    logger.info(f"跨页补全完成，共收集 {len(all_target_entries)} 条子条目")
    return all_target_entries, complete_url


def main():
    parser = argparse.ArgumentParser(
        description="齐鲁网新闻联播索引页抓取工具（自动脱敏）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python fetch_iqilu.py 20260609              # 获取6月9日的齐鲁网子条目
  python fetch_iqilu.py 20260609 -s 20        # 从第20页开始搜索
  python fetch_iqilu.py 20260609 -o out.json   # 指定输出文件
        """
    )
    parser.add_argument("date", help="目标日期 YYYYMMDD")
    parser.add_argument("-s", "--start", type=int, default=1, help="起始搜索页码（默认1）")
    parser.add_argument("-o", "--output", help="输出JSON文件路径")
    
    args = parser.parse_args()
    
    # 日期格式转换
    target_date = datetime.strptime(args.date, "%Y%m%d").date()
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    logger.info(f"目标日期: {target_date_str}")
    
    # 搜索
    entries, complete_url = search_target_date(target_date_str, args.start)
    
    if not entries:
        logger.error("未找到子条目")
        sys.exit(1)
    
    # 执行脱敏处理
    safe_entries = []
    for e in entries:
        safe_title = desensitize(e["title"])
        safe_entries.append({
            "title": safe_title,
            "url": e["url"],
            "date": e["date_str"]
        })
    
    # 输出结果
    result = {
        "date": args.date,
        "complete_url": complete_url,
        "total": len(safe_entries),
        "entries": safe_entries
    }
    
    # 保存JSON
    output_path = args.output if args.output else os.path.join(SCRIPT_DIR, f"iqilu_{args.date}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON已保存: {output_path}")
    
    # 输出Markdown表格
    print("\n=== 齐鲁网子条目列表（已脱敏）===\n")
    print("| 序号 | 标题 | URL |")
    print("|------|------|-----|")
    for i, e in enumerate(safe_entries, 1):
        print(f"| {i} | {e['title']} | {e['url']} |")
    
    if complete_url:
        print(f"\n完整版URL: {complete_url}")
    
    # 标记快讯子条目
    print("\n=== 快讯子条目 ===\n")
    for i, e in enumerate(safe_entries, 1):
        if "联播快讯" in e["title"] or "快讯" in e["title"]:
            print(f"| {i} | {e['title']} | {e['url']} |")
    
    print(f"\n总计: {len(safe_entries)} 条子条目（已脱敏）")


if __name__ == '__main__':
    main()
