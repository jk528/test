#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
齐鲁网新闻联播索引页抓取脚本
自动定位目标日期的索引页，提取所有子条目链接，并执行脱敏处理
支持与央视网数据交叉比对，自动标记缺失条目

版本：v2.1.0（2026-07-11）
变更：
  v2.1.0 - 翻页逻辑优化：
    1) 连续翻页策略：找到目标日期后继续翻页，直到连续2页无新条目
    2) 扩大范围：每个方向最多翻5页（原前后各2页）
    3) 不轻易判定缺失：穷尽翻页搜索后再标记
  v2.0.0 - 五大优化：
    1) 新增独立页面内容抓取（提取视频简介/正文）
    2) 新增央视网交叉比对（自动匹配覆盖情况，标记缺失条目）
    3) 修复跨页补全逻辑（先has_target快速检查再请求，减少冗余）
    4) 优化排序逻辑（独立页面抓取时提取发布时间，按时间排序）
    5) 输出增强（Markdown表格增加覆盖状态列、缺失标记、交叉比对报告）
  v1.0.0 - 初始版本：索引页抓取、跨页补全、脱敏处理
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
from difflib import SequenceMatcher

# 复用 fetch_xwlb.py 的脱敏映射表和函数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from fetch_xwlb import desensitize

# 日志和缓存保存到系统临时目录，保持流程文件夹整洁
TEMP_DIR = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')), 'xwlb_cache')
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(TEMP_DIR, "fetch_iqilu.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

MAX_PAGES = 30          # 最多翻页数
REQUEST_TIMEOUT = 30     # 请求超时
PAGE_FETCH_DELAY = 0.3   # 页面请求间隔（秒），避免被封
ENTRY_FETCH_DELAY = 0.2 # 独立页面请求间隔（秒）
MAX_CONCURRENT_FETCHES = 5  # 最大并发独立页面抓取数

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url, delay=PAGE_FETCH_DELAY):
    """获取页面内容，带延迟防止被封"""
    import time
    if delay > 0:
        time.sleep(delay)
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
    # 主模式：### [标题](URL) ... 时间 YYYY-MM-DD
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
    
    # 筛选目标日期的子条目（排除完整版）
    for e in all_entries:
        if e["date_str"] == target_date_str and "完整版" not in e["title"]:
            if e["url"] not in seen_urls:
                seen_urls.add(e["url"])
                entries.append(e)
    
    return entries, complete_url


def search_target_date(target_date_str, start_page=1, max_pages=MAX_PAGES):
    """
    在齐鲁网索引页中搜索目标日期，支持跨页补全
    优化：先做 has_target 快速文本检查再决定是否请求相邻页
    :param target_date_str: 目标日期 YYYY-MM-DD
    :param start_page: 起始页码
    :return: (entries_list, complete_url) 目标日期的所有子条目和完整版URL
    """
    target_yyyymmdd = target_date_str.replace("-", "")
    seen_urls = set()
    all_target_entries = []
    complete_url = None
    found_page_num = None
    
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
            # 通过完整版锚点判断方向
            anchors = find_complete_anchors(html)
            if anchors:
                all_dates = [a["date_str"] for a in anchors if a["date_str"]]
                if all_dates:
                    newest = max(all_dates)
                    oldest = min(all_dates)
                    logger.info(f"  页面日期范围: {oldest} ~ {newest}")
                    
                    # 优化：齐鲁网页面按倒序排列，新内容在前
                    # 如果目标日期比最新日期还新，需要继续往前翻（页码更小）
                    # 如果目标日期比最旧日期还老，需要继续往后翻（页码更大）
                    if target_date_str > newest:
                        continue  # 继续找更新的页面
                    elif target_date_str < oldest:
                        pass  # 可能翻过头了，但继续检查
            continue
        
        # 找到包含目标日期的页面
        logger.info(f"  >> 在页面 {page_num} 找到目标日期 {target_date_str}")
        found_page_num = page_num
        
        entries, url = collect_entries_from_page(html, target_date_str, seen_urls)
        all_target_entries.extend(entries)
        if url and not complete_url:
            complete_url = url
        
        logger.info(f"  当前页收集到 {len(entries)} 条子条目")
        break
    
    if found_page_num is None:
        logger.error(f"在 {max_pages} 页内未找到目标日期 {target_date_str}")
        return [], None
    
    # ============================================================
    # 第二阶段：连续翻页补全（v2.1.0核心优化）
    # 策略：从主页面开始，向前后两个方向连续翻页，
    #        直到连续2页都没有找到新的目标日期条目为止
    # 每个方向最多翻5页，不轻易判定缺失
    # ============================================================
    logger.info(f"开始连续翻页补全，主页面: {found_page_num}")
    
    MAX_ADJACENT_PAGES = 5       # 每个方向最多翻5页
    CONSECUTIVE_EMPTY_LIMIT = 2   # 连续空页上限
    
    # 向后翻页（页码增大，内容更旧）
    consecutive_empty = 0
    for offset in range(1, MAX_ADJACENT_PAGES + 1):
        if consecutive_empty >= CONSECUTIVE_EMPTY_LIMIT:
            logger.info(f"  向后连续{CONSECUTIVE_EMPTY_LIMIT}页无新条目，停止")
            break
        check_page = found_page_num + offset
        check_url = get_page_url(check_page)
        logger.info(f"  向后检查页 {check_page} (offset=+{offset}): {check_url}")
        check_html = fetch_page(check_url)
        if not check_html:
            consecutive_empty += 1
            continue
        if target_date_str not in check_html and target_yyyymmdd not in check_html:
            logger.info(f"    页面 {check_page} 不包含目标日期")
            consecutive_empty += 1
            continue
        entries, url = collect_entries_from_page(check_html, target_date_str, seen_urls)
        if entries:
            all_target_entries.extend(entries)
            logger.info(f"    从页面 {check_page} 补充 {len(entries)} 条子条目")
            consecutive_empty = 0
        else:
            consecutive_empty += 1
        if url and not complete_url:
            complete_url = url
    
    # 向前翻页（页码减小，内容更新）
    consecutive_empty = 0
    for offset in range(1, MAX_ADJACENT_PAGES + 1):
        if consecutive_empty >= CONSECUTIVE_EMPTY_LIMIT:
            logger.info(f"  向前连续{CONSECUTIVE_EMPTY_LIMIT}页无新条目，停止")
            break
        check_page = found_page_num - offset
        if check_page < 1:
            break
        check_url = get_page_url(check_page)
        logger.info(f"  向前检查页 {check_page} (offset=-{offset}): {check_url}")
        check_html = fetch_page(check_url)
        if not check_html:
            consecutive_empty += 1
            continue
        if target_date_str not in check_html and target_yyyymmdd not in check_html:
            logger.info(f"    页面 {check_page} 不包含目标日期")
            consecutive_empty += 1
            continue
        entries, url = collect_entries_from_page(check_html, target_date_str, seen_urls)
        if entries:
            all_target_entries.extend(entries)
            logger.info(f"    从页面 {check_page} 补充 {len(entries)} 条子条目")
            consecutive_empty = 0
        else:
            consecutive_empty += 1
        if url and not complete_url:
            complete_url = url
    
    # 排序：按URL中的ID排序（齐鲁网URL中ID通常递增对应播出顺序）
    def sort_key(entry):
        match = re.search(r'(\d+)\.html$', entry["url"])
        if match:
            return int(match.group(1))
        return 0
    
    all_target_entries.sort(key=sort_key)
    
    logger.info(f"连续翻页补全完成，共收集 {len(all_target_entries)} 条子条目")
    return all_target_entries, complete_url


def fetch_entry_detail(entry):
    """
    访问独立页面，提取详细信息（简介、发布时间等）
    :param entry: 条目字典 {title, url, date_str}
    :return: 补充了 detail 字段的条目字典
    """
    html = fetch_page(entry["url"], delay=ENTRY_FETCH_DELAY)
    if not html:
        entry["detail"] = ""
        entry["pub_time"] = ""
        return entry
    
    # 提取简介：齐鲁网页面格式为 "简介：\n\n标题内容" 或 "简介：\n\n正文内容"
    # v2.1.0: 增强正则，避免捕获"相关视频"等噪音
    detail_patterns = [
        # 模式1: "简介：\n\n内容" 直到 "###"或"相关视频"
        re.compile(r'简介[：:]\s*\n+(.*?)(?=【展开】|相关视频|###\s|次播放|$)', re.DOTALL),
        # 模式2: 内联 "简介：内容"
        re.compile(r'简介[：:]\s*(.*?)(?=【展开】|相关视频|###\s|次播放|$)', re.DOTALL),
    ]
    
    detail = ""
    for pat in detail_patterns:
        match = pat.search(html)
        if match:
            detail = match.group(1).strip()
            break
    
    # 清理HTML标签（齐鲁网页面简介中可能包含<p>、<div>等标签）
    detail = re.sub(r'<[^>]+>', '', detail).strip()
    # 清理多余空白
    detail = re.sub(r'\s+', ' ', detail).strip()
    
    # 如果简介就是标题本身（齐鲁网经常如此），标记为空
    if detail and detail == entry["title"]:
        detail = ""
    
    # 提取发布时间
    pub_time = ""
    pub_match = re.search(r'发布时间[：:]\s*(\d{4}年\d{2}月\d{2}日)', html)
    if pub_match:
        pub_time = pub_match.group(1).strip()
    
    entry["detail"] = detail
    entry["pub_time"] = pub_time
    return entry


def load_xwlb_data(date_str):
    """
    加载央视网JSON数据（如果存在）
    :param date_str: 日期 YYYYMMDD
    :return: list[dict] 央视网条目列表，或 None（文件不存在）
    """
    json_path = os.path.join(TEMP_DIR, f"xwlb_{date_str}.json")
    if not os.path.exists(json_path):
        logger.info(f"央视网JSON不存在: {json_path}，跳过交叉比对")
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        videos = data.get("videos", [])
        logger.info(f"加载央视网数据: {len(videos)} 条（来自 {json_path}）")
        return videos
    except Exception as e:
        logger.warning(f"读取央视网JSON失败: {e}")
        return None


def normalize_title_for_match(title):
    """
    标题标准化用于模糊匹配
    去除前缀（完整版、联播快讯标记等）、空格、HTML标签
    """
    # 去除常见前缀
    t = re.sub(r'^完整版', '', title)
    t = re.sub(r'^【联播快讯】', '', t)
    t = re.sub(r'^\[视频\]', '', t)
    # 去除HTML标签
    t = re.sub(r'<[^>]+>', '', t)
    # 去除多余空格
    t = t.strip()
    return t


def extract_keywords(title):
    """
    从标题中提取关键词用于宽松匹配
    去除常见停用词，保留有意义的名词/动词
    """
    t = normalize_title_for_match(title)
    # 停用词列表
    stop_words = {
        "的", "在", "了", "和", "与", "及", "或", "也", "都", "已", "将",
        "出席", "召开", "举行", "到", "向", "对", "称", "强调", "指出",
        "工作", "会议", "活动", "会", "上", "下", "中",
        "——", "—", "：", ":", "，", ",", "。",
    }
    # 按2-4字长度提取词组（中文无空格分词，用滑动窗口）
    keywords = set()
    # 提取所有2字以上连续中文字符段
    segments = re.findall(r'[\u4e00-\u9fa5]{2,}', t)
    for seg in segments:
        if seg not in stop_words and len(seg) >= 2:
            keywords.add(seg)
        # 也提取3字子串
        if len(seg) >= 3:
            for i in range(len(seg) - 2):
                sub = seg[i:i+3]
                if sub not in stop_words:
                    keywords.add(sub)
    return keywords


def fuzzy_match_title(title_a, title_b, threshold=0.6):
    """
    模糊匹配两个标题是否指向同一新闻
    :param title_a: 标题A
    :param title_b: 标题B
    :param threshold: 相似度阈值（0-1）
    :return: True if similar enough
    """
    a = normalize_title_for_match(title_a)
    b = normalize_title_for_match(title_b)
    
    # 完全匹配
    if a == b:
        return True
    
    # 一个是另一个的子串（齐鲁网标题常截断央视网长标题）
    if len(a) > 5 and len(b) > 5:
        if a in b or b in a:
            return True
    
    # SequenceMatcher 模糊匹配
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= threshold


def cross_compare(xwlb_videos, iqilu_entries):
    """
    央视网与齐鲁网交叉比对
    :param xwlb_videos: 央视网条目列表 [{title, url, duration}, ...]
    :param iqilu_entries: 齐鲁网条目列表 [{title, url, date_str, detail}, ...]
    :return: (enhanced_list, unmatched_iqilu, kuaixun_mapping)
      enhanced_list: 增强的央视网条目列表
      unmatched_iqilu: 齐鲁网有但央视网未匹配的条目
      kuaixun_mapping: {cctv_idx: [iqilu_entry, ...]} 快讯目录→齐鲁网子条目映射
    """
    enhanced = []
    matched_iqilu_indices = set()
    kuaixun_mapping = {}  # 快讯目录→齐鲁网子条目映射
    
    for xwlb in xwlb_videos:
        xwlb_title = xwlb["title"]
        # 跳过完整版条目
        if "完整版" in xwlb_title and "新闻联播" in xwlb_title:
            enhanced.append({
                **xwlb,
                "iqilu_url": None,
                "coverage": "完整版",
                "match_type": "完整版跳过"
            })
            continue
        
        # 检测是否为快讯目录条目（国内联播快讯/国际联播快讯）
        is_kuaixun_dir = ("联播快讯" in xwlb_title and 
                         "【联播快讯】" not in xwlb_title and
                         "完整版" not in normalize_title_for_match(xwlb_title))
        
        if is_kuaixun_dir:
            # 快讯目录：查找齐鲁网中对应的子条目（按【联播快讯】前缀匹配）
            kuaixun_children = []
            # 确定快讯类型（国内/国际）
            kx_type = "国内" if "国内" in xwlb_title else ("国际" if "国际" in xwlb_title else "")
            
            for idx, iqilu in enumerate(iqilu_entries):
                if idx in matched_iqilu_indices:
                    continue
                iq_title = iqilu["title"]
                # 匹配【联播快讯】子条目
                if "联播快讯" in iq_title and ("【联播快讯】" in iq_title or "快讯" in iq_title):
                    # 如果能确定快讯类型，进一步过滤
                    if kx_type and kx_type in xwlb_title:
                        # 国内快讯不应匹配国际快讯
                        if kx_type == "国内" and "国际" in iq_title:
                            continue
                        if kx_type == "国际" and "国内" in iq_title:
                            continue
                    kuaixun_children.append((idx, iqilu))
            
            if kuaixun_children:
                # 记录映射关系
                kuaixun_mapping[xwlb["url"]] = [iq for _, iq in kuaixun_children]
                for idx, iqilu in kuaixun_children:
                    matched_iqilu_indices.add(idx)
                
                child_urls = [iq["url"] for _, iq in kuaixun_children]
                enhanced.append({
                    **xwlb,
                    "iqilu_url": child_urls,  # 快讯目录对应多个齐鲁网URL
                    "coverage": "齐鲁网拆分覆盖",
                    "match_type": f"快讯目录→{len(kuaixun_children)}条子条目",
                    "match_score": None
                })
            else:
                enhanced.append({
                    **xwlb,
                    "iqilu_url": None,
                    "coverage": "齐鲁网缺失",
                    "match_type": "快讯目录无子条目"
                })
            continue
        
        # 常规新闻：在齐鲁网条目中寻找最佳匹配
        best_match_idx = None
        best_score = 0
        
        for idx, iqilu in enumerate(iqilu_entries):
            if idx in matched_iqilu_indices:
                continue
            
            if fuzzy_match_title(xwlb_title, iqilu["title"], threshold=0.5):
                a = normalize_title_for_match(xwlb_title)
                b = normalize_title_for_match(iqilu["title"])
                score = SequenceMatcher(None, a, b).ratio()
                
                if score > best_score:
                    best_score = score
                    best_match_idx = idx
        
        if best_match_idx is not None:
            matched_iqilu_indices.add(best_match_idx)
            iqilu_url = iqilu_entries[best_match_idx]["url"]
            match_type = "精确匹配" if best_score > 0.8 else "模糊匹配"
            enhanced.append({
                **xwlb,
                "iqilu_url": iqilu_url,
                "coverage": "齐鲁网有",
                "match_type": match_type,
                "match_score": round(best_score, 2)
            })
        else:
            # v2.1.0: 不轻易判定缺失，降低阈值尝试关键词匹配
            # 提取央视网标题中的关键词，在齐鲁网未匹配条目中搜索
            best_fallback_idx = None
            best_fallback_score = 0
            xwlb_keywords = extract_keywords(xwlb_title)
            
            for idx, iqilu in enumerate(iqilu_entries):
                if idx in matched_iqilu_indices:
                    continue
                iq_keywords = extract_keywords(iqilu["title"])
                # 计算关键词重叠率
                if xwlb_keywords and iq_keywords:
                    overlap = len(xwlb_keywords & iq_keywords)
                    overlap_ratio = overlap / max(len(xwlb_keywords), len(iq_keywords))
                    if overlap_ratio > best_fallback_score:
                        best_fallback_score = overlap_ratio
                        best_fallback_idx = idx
            
            if best_fallback_idx is not None and best_fallback_score >= 0.3:
                # 找到关键词相近的条目，标记为"关联覆盖"
                matched_iqilu_indices.add(best_fallback_idx)
                iqilu_url = iqilu_entries[best_fallback_idx]["url"]
                enhanced.append({
                    **xwlb,
                    "iqilu_url": iqilu_url,
                    "coverage": "齐鲁网关联覆盖",
                    "match_type": f"关键词匹配(重叠率{round(best_fallback_score, 2)})",
                    "match_score": round(best_fallback_score, 2)
                })
            else:
                enhanced.append({
                    **xwlb,
                    "iqilu_url": None,
                    "coverage": "齐鲁网未独立收录",
                    "match_type": "无匹配（穷尽翻页后未找到）"
                })
    
    # 找出齐鲁网有但央视网未匹配的条目（多出项）
    unmatched_iqilu = []
    for idx, iqilu in enumerate(iqilu_entries):
        if idx not in matched_iqilu_indices:
            unmatched_iqilu.append(iqilu)
    
    return enhanced, unmatched_iqilu, kuaixun_mapping


def main():
    parser = argparse.ArgumentParser(
        description="齐鲁网新闻联播索引页抓取工具（v2.1.0：连续翻页+关联匹配+交叉比对）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python fetch_iqilu.py 20260609                # 获取6月9日的齐鲁网子条目
  python fetch_iqilu.py 20260609 -s 20           # 从第20页开始搜索
  python fetch_iqilu.py 20260609 -o out.json      # 指定输出文件
  python fetch_iqilu.py 20260609 --no-detail      # 跳过独立页面抓取（加快速度）
  python fetch_iqilu.py 20260609 --no-compare     # 跳过央视网交叉比对
        """
    )
    parser.add_argument("date", help="目标日期 YYYYMMDD")
    parser.add_argument("-s", "--start", type=int, default=1, help="起始搜索页码（默认1）")
    parser.add_argument("-o", "--output", help="输出JSON文件路径")
    parser.add_argument("--no-detail", action="store_true", help="跳过独立页面内容抓取（加快速度）")
    parser.add_argument("--no-compare", action="store_true", help="跳过央视网交叉比对")
    
    args = parser.parse_args()
    
    # 日期格式转换
    target_date = datetime.strptime(args.date, "%Y%m%d").date()
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    logger.info(f"目标日期: {target_date_str}")
    
    # ============================================================
    # 步骤1：搜索齐鲁网索引页
    # ============================================================
    entries, complete_url = search_target_date(target_date_str, args.start)
    
    if not entries:
        logger.error("未找到子条目")
        sys.exit(1)
    
    # ============================================================
    # 步骤2：抓取独立页面内容（可选）
    # ============================================================
    if not args.no_detail:
        logger.info(f"开始抓取 {len(entries)} 个独立页面内容...")
        for i, entry in enumerate(entries):
            logger.info(f"  [{i+1}/{len(entries)}] 抓取: {entry['url']}")
            entry = fetch_entry_detail(entry)
            if entry.get("detail"):
                logger.info(f"    简介: {entry['detail'][:50]}...")
        logger.info("独立页面内容抓取完成")
    else:
        for entry in entries:
            entry["detail"] = ""
            entry["pub_time"] = ""
    
    # ============================================================
    # 步骤3：脱敏处理
    # ============================================================
    safe_entries = []
    for e in entries:
        safe_title = desensitize(e["title"])
        safe_detail = desensitize(e.get("detail", "")) if e.get("detail") else ""
        safe_entries.append({
            "title": safe_title,
            "original_title": e["title"],  # 保留原标题用于匹配
            "url": e["url"],
            "date": e["date_str"],
            "detail": safe_detail,
            "pub_time": e.get("pub_time", "")
        })
    
    # ============================================================
    # 步骤4：央视网交叉比对（可选）
    # ============================================================
    compare_result = None
    unmatched_iqilu = None
    kuaixun_mapping = {}
    
    if not args.no_compare:
        xwlb_videos = load_xwlb_data(args.date)
        if xwlb_videos is not None:
            logger.info("开始央视网交叉比对...")
            # 使用原始标题（脱敏前）进行匹配
            raw_entries = [{"title": e["title"], "url": e["url"]} for e in entries]
            compare_result, unmatched_iqilu, kuaixun_mapping = cross_compare(xwlb_videos, raw_entries)
            
            # 统计覆盖情况
            covered = sum(1 for x in compare_result if x["coverage"] in ("齐鲁网有", "齐鲁网拆分覆盖", "齐鲁网关联覆盖"))
            missing = sum(1 for x in compare_result if x["coverage"] == "齐鲁网未独立收录")
            split_count = sum(1 for x in compare_result if x["coverage"] == "齐鲁网拆分覆盖")
            rel_count = sum(1 for x in compare_result if x["coverage"] == "齐鲁网关联覆盖")
            total_non_full = covered + missing
            logger.info(f"交叉比对结果: 央视网{total_non_full}条常规新闻中，"
                       f"齐鲁网覆盖{covered}条（精确/模糊{covered-split_count-rel_count}条，"
                       f"拆分{split_count}条，关联{rel_count}条），未独立收录{missing}条")
            if unmatched_iqilu:
                logger.info(f"齐鲁网多出{len(unmatched_iqilu)}条（央视网无对应条目）")
    
    # ============================================================
    # 步骤5：输出结果
    # ============================================================
    
    # 构建JSON结果
    result = {
        "date": args.date,
        "complete_url": complete_url,
        "total": len(safe_entries),
        "entries": safe_entries,
    }
    
    # 如果有交叉比对结果，加入
    if compare_result is not None:
        result["cross_compare"] = {
            "cctv_total": len(compare_result),
            "covered": sum(1 for x in compare_result if x["coverage"] in ("齐鲁网有", "齐鲁网拆分覆盖", "齐鲁网关联覆盖")),
            "missing": sum(1 for x in compare_result if x["coverage"] == "齐鲁网未独立收录"),
            "details": compare_result
        }
        if unmatched_iqilu:
            result["cross_compare"]["unmatched_iqilu"] = [
                {"title": u["title"], "url": u["url"]} for u in unmatched_iqilu
            ]
    
    # 保存JSON
    output_path = args.output if args.output else os.path.join(TEMP_DIR, f"iqilu_{args.date}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON已保存: {output_path}")
    
    # ============================================================
    # 输出Markdown表格
    # ============================================================
    print(f"\n{'='*60}")
    print(f"齐鲁网子条目列表（{target_date_str}，已脱敏）")
    print(f"{'='*60}\n")
    
    print("| 序号 | 标题 | URL | 详情 |")
    print("|------|------|-----|------|")
    for i, e in enumerate(safe_entries, 1):
        detail_preview = e.get("detail", "")[:40] + "..." if len(e.get("detail", "")) > 40 else e.get("detail", "")
        if not detail_preview:
            detail_preview = "—"
        print(f"| {i} | {e['title']} | {e['url']} | {detail_preview} |")
    
    if complete_url:
        print(f"\n完整版URL: {complete_url}")
    
    # 快讯子条目
    print(f"\n--- 快讯子条目 ---\n")
    kx_count = 0
    for i, e in enumerate(safe_entries, 1):
        if "联播快讯" in e["title"] or "快讯" in e["title"]:
            kx_count += 1
            detail_preview = e.get("detail", "")[:50] + "..." if len(e.get("detail", "")) > 50 else e.get("detail", "")
            print(f"| {i} | {e['title']} | {e['url']} | {detail_preview or '—'} |")
    if kx_count == 0:
        print("（无快讯子条目）")
    
    print(f"\n总计: {len(safe_entries)} 条子条目（已脱敏）")
    
    # ============================================================
    # 交叉比对报告
    # ============================================================
    if compare_result is not None:
        covered = sum(1 for x in compare_result if x["coverage"] in ("齐鲁网有", "齐鲁网拆分覆盖", "齐鲁网关联覆盖"))
        missing = sum(1 for x in compare_result if x["coverage"] == "齐鲁网未独立收录")
        total_non_full = covered + missing
        
        print(f"\n{'='*60}")
        print(f"央视网 x 齐鲁网 交叉比对报告（{target_date_str}）")
        print(f"{'='*60}\n")
        
        print(f"| 央视网序号 | 标题（已脱敏） | 覆盖状态 | 齐鲁网URL | 匹配方式 |")
        print(f"|-----------|------|---------|----------|---------|")
        
        seq = 0
        for x in compare_result:
            # 脱敏并清理"完整版"前缀（央视网标题常带"完整版"前缀）
            safe_title = desensitize(normalize_title_for_match(x["title"]))
            # 跳过完整版条目
            if x["coverage"] in ("完整版跳过", "完整版"):
                continue
            seq += 1
            
            # 覆盖状态标记
            if x["coverage"] == "齐鲁网有":
                coverage_mark = "覆盖"
            elif x["coverage"] == "齐鲁网拆分覆盖":
                coverage_mark = "拆分覆盖"
            elif x["coverage"] == "齐鲁网关联覆盖":
                coverage_mark = "关联覆盖"
            else:
                coverage_mark = "未独立收录"
            
            # 齐鲁网URL显示
            iqilu_url_raw = x.get("iqilu_url", "")
            if isinstance(iqilu_url_raw, list):
                # 快讯目录对应多个URL
                iqilu_url = f"{len(iqilu_url_raw)}条子条目"
            elif iqilu_url_raw:
                iqilu_url = iqilu_url_raw
            else:
                iqilu_url = "使用完整版"
            
            match_type = x.get("match_type", "")
            match_score = f" ({x['match_score']})" if x.get("match_score") is not None else ""
            
            print(f"| {seq} | {safe_title} | {coverage_mark} | {iqilu_url} | {match_type}{match_score} |")
        
        print(f"\n覆盖统计: {covered}/{total_non_full} 条覆盖", end="")
        if missing > 0:
            print(f"，{missing} 条未独立收录（使用完整版链接）")
        else:
            print("，齐鲁网全覆盖")
        
        if unmatched_iqilu:
            print(f"\n齐鲁网多出 {len(unmatched_iqilu)} 条（央视网无对应）:")
            for u in unmatched_iqilu:
                print(f"  - {desensitize(u['title'])}: {u['url']}")


if __name__ == '__main__':
    main()
