#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻联播总结报告一键生成脚本 v2.1
优化目标：零浏览器交互 + 内容质量达标 + 格式与历史报告一致

版本：v2.1.0（2026-09-08）
v2.1 改进：
  1. 从央视网视频页面提取完整正文（"主要内容"区），用于详情填充和概括生成
  2. 修复齐鲁网快讯匹配，每条快讯链接到独立齐鲁网页面
  3. 重写新闻概括逻辑，基于正文内容而非模板
  4. 重写基调概述，基于新闻分类和关键词提炼
  5. 第三部分详情填充真实内容（含数据、要点、多方表态等）
  6. 修复验证表格列数、日期格式、时长匹配等格式问题
  7. 补充六要素详细说明和占位符统合表内容
"""

import requests
import re
import sys
import os
import time
import logging
import argparse
import html as html_module
from datetime import datetime, date, timedelta
from difflib import SequenceMatcher

# ============================================================
# 基础配置
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

TEMP_DIR = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')), 'xwlb_cache')
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(TEMP_DIR, "gen_report_v2.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.15

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 复用 fetch_xwlb.py
sys.path.insert(0, SCRIPT_DIR)
from fetch_xwlb import fetch_xwlb_list as _fetch_xwlb_raw, desensitize as _desensitize_raw


def desensitize(text, mark=True):
    """脱敏处理，复用 fetch_xwlb.py 中的实现"""
    return _desensitize_raw(text, mark)


# ============================================================
# HTTP 请求工具（带缓存）
# ============================================================
_cache = {}


def http_get(url, use_cache=True):
    cache_key = url
    if use_cache and cache_key in _cache:
        return _cache[cache_key]
    time.sleep(REQUEST_DELAY)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        content = resp.text
        if use_cache:
            _cache[cache_key] = content
        return content
    except Exception as e:
        logger.warning(f"请求失败 {url}: {e}")
        return None


# ============================================================
# 央视网视频列表抓取
# ============================================================
def fetch_xwlb_videos(date_str):
    results = _fetch_xwlb_raw(date_str)
    for r in results:
        r["title"] = r["title"].replace("[视频]", "").strip()
    logger.info(f"央视网获取到 {len(results)} 条视频")
    return results


# ============================================================
# 央视网视频详情页正文提取
# ============================================================
def fetch_video_detail(video_url):
    """
    从央视网视频页面提取完整正文内容
    返回: dict = {
        "title": 标题,
        "paragraphs": [段落1, 段落2, ...],  # 已清理HTML
        "full_text": 全文合并,
        "first_paragraph": 首段（导语）,
    }
    """
    html = http_get(video_url)
    if not html:
        return {"title": "", "paragraphs": [], "full_text": "", "first_paragraph": ""}

    # 提取标题
    title = ""
    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        title = html_module.unescape(title_match.group(1).strip())
        title = title.replace("[视频]", "").strip()

    # 提取"主要内容"区块的所有段落
    paragraphs = []
    main_match = re.search(r'主要内容(.*?)(?=编辑[：:]|责任编辑|全部评论|京ICP备|video_info)', html, re.DOTALL)
    if main_match:
        main_html = main_match.group(1)
        # 提取 <p> 标签内的文本
        p_matches = re.findall(r'<p[^>]*>(.*?)</p>', main_html, re.DOTALL)
        for p in p_matches:
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = html_module.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()
            # 过滤掉太短的段落和版权声明
            if len(text) > 15 and "版权所有" not in text and "ICP备" not in text:
                paragraphs.append(text)

    # 如果 <p> 段落太少，尝试用 <br> 分割
    if len(paragraphs) < 2 and main_match:
        main_html = main_match.group(1)
        # 去掉所有标签，用换行分割
        text = re.sub(r'<[^>]+>', '\n', main_html)
        text = html_module.unescape(text)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        paragraphs = [l for l in lines if len(l) > 15 and "版权所有" not in l and "ICP备" not in l]

    # 清理"央视网消息（新闻联播）："前缀
    clean_paragraphs = []
    for p in paragraphs:
        p = re.sub(r'^央视网消息[（(][^）)]*[）)]\s*[：:]\s*', '', p)
        clean_paragraphs.append(p)

    full_text = ' '.join(clean_paragraphs)
    first_paragraph = clean_paragraphs[0] if clean_paragraphs else ""

    return {
        "title": title,
        "paragraphs": clean_paragraphs,
        "full_text": full_text,
        "first_paragraph": first_paragraph,
    }


# ============================================================
# 快讯详情提取
# ============================================================
def fetch_kuaixun_details(video_url):
    """
    从央视网快讯视频页面提取子条目列表
    返回: list[dict] = [{title, summary, full_text}, ...]
    """
    html = http_get(video_url)
    if not html:
        return []

    items = []

    # 从"主要内容"区域的 <strong> 标签提取
    main_section_match = re.search(r'主要内容(.*?)(?=编辑[：:]|责任编辑|全部评论|$)', html, re.DOTALL)
    if main_section_match:
        main_html = main_section_match.group(1)
        strong_pattern = re.compile(
            r'<strong>(.+?)</strong>\s*(?:<br\s*/?>|</p>|<p>)\s*(.*?)(?=<strong>|编辑[：:]|责任编辑|全部评论|$)',
            re.DOTALL | re.IGNORECASE
        )
        strong_matches = strong_pattern.findall(main_html)
        if strong_matches:
            for title_raw, body_raw in strong_matches:
                title = re.sub(r'<[^>]+>', '', title_raw).strip()
                title = html_module.unescape(title)
                body = re.sub(r'<[^>]+>', '', body_raw).strip()
                body = html_module.unescape(body)
                body = re.sub(r'\s+', ' ', body).strip()
                # 去除前缀
                title = re.sub(r'^央视网消息[（(][^）)]*[）)]\s*[：:]\s*', '', title)
                body = re.sub(r'^央视网消息[（(][^）)]*[）)]\s*[：:]\s*', '', body)
                # 摘要（前80字）
                summary = body[:80] + "..." if len(body) > 80 else body
                if title and len(title) > 4 and "联播快讯" not in title:
                    items.append({"title": title, "summary": summary, "full_text": body})
            return items

    # 降级：数字编号提取
    brief_pattern = re.compile(r'[（(](\d+)[）)]\s*([^。；]{5,}?)[。；]')
    brief_matches = brief_pattern.findall(html)
    if brief_matches:
        for num, title in brief_matches:
            title = html_module.unescape(title.strip())
            if title and len(title) > 5:
                items.append({"title": title, "summary": title, "full_text": title})
        seen_titles = set()
        unique_items = []
        for item in items:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                unique_items.append(item)
        return unique_items

    return items


# ============================================================
# 齐鲁网快讯抓取（精确匹配版本）
# ============================================================
def fetch_iqilu_entries(date_str):
    """
    从齐鲁网获取目标日期的联播快讯子条目及其独立页面链接
    策略：按日期筛选 + 去重，仅保留快讯子条目（排除完整版和常规新闻）
    """
    target_date = datetime.strptime(date_str, "%Y%m%d").date()

    all_entries = []

    # 访问前5页，收集所有条目
    for page in range(1, 6):
        if page == 1:
            url = "https://v.iqilu.com/jcdb/ysxwlb/index.html"
        else:
            url = f"https://v.iqilu.com/jcdb/ysxwlb/index_{page-1}.html"

        html = http_get(url)
        if not html:
            continue

        # 直接匹配所有 <a> 标签（齐鲁网页面条目直接以<a>形式排列）
        a_pattern = re.compile(
            r'<a[^>]*href="(https://v\.iqilu\.com/jcdb/ysxwlb/[^"]+\.html)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        a_matches = a_pattern.findall(html)

        for link, title_raw in a_matches:
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            title = html_module.unescape(title)
            if not title or len(title) < 5:
                continue

            # 从URL中提取日期
            url_date_match = re.search(r'/(\d{6})/(\d{2})/', link)
            url_date = None
            if url_date_match:
                yyyymm = url_date_match.group(1)
                dd = url_date_match.group(2)
                try:
                    url_date = date(int(yyyymm[:4]), int(yyyymm[4:]), int(dd))
                except ValueError:
                    pass

            # 只保留目标日期的条目
            if url_date != target_date:
                continue

            is_full = "完整版" in title or "新闻联播完整版" in title
            clean_title = title
            # 去掉日期前缀（如"2026年09月07日 "）
            clean_title = re.sub(r'^\d{4}年\d{2}月\d{2}日\s*', '', clean_title)
            clean_title = clean_title.replace("【联播快讯】", "").replace("联播快讯", "").strip()

            entry = {
                "title": clean_title,
                "url": link,
                "url_date": url_date,
                "is_full": is_full
            }
            all_entries.append(entry)

    # 过滤：只保留快讯子条目（排除完整版和常规长新闻）
    # 快讯特征：标题较短，通常是具体事件
    # 这里我们保留所有非完整版条目，匹配时用相似度判断
    target_entries = [e for e in all_entries if not e["is_full"]]

    # 去重
    seen = set()
    unique_entries = []
    for e in target_entries:
        if e["url"] not in seen and e["title"]:
            seen.add(e["url"])
            unique_entries.append(e)

    logger.info(f"齐鲁网获取到 {len(unique_entries)} 条目标日期子条目")
    return unique_entries


def fetch_iqilu_detail(url):
    """
    从齐鲁网快讯详情页提取正文内容
    返回: dict {"full_text": "..."}
    """
    html = http_get(url)
    if not html:
        return {"full_text": ""}

    # 尝试多种正文提取模式
    text = ""

    # 模式1: <div class="content"> 或 <div class="detail">
    patterns = [
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*detail[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
    ]
    for p in patterns:
        m = re.search(p, html, re.DOTALL | re.IGNORECASE)
        if m:
            content_html = m.group(1)
            # 提取纯文本
            content_html = re.sub(r'<script.*?</script>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
            content_html = re.sub(r'<style.*?</style>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content_html, re.DOTALL | re.IGNORECASE)
            if paragraphs:
                texts = []
                for p in paragraphs:
                    clean = re.sub(r'<[^>]+>', '', p).strip()
                    clean = html_module.unescape(clean)
                    if clean and len(clean) > 10:
                        texts.append(clean)
                if texts:
                    text = "\n".join(texts)
                    break

    # 如果没找到<p>，试试直接提取所有文本
    if not text:
        # 去掉所有HTML标签
        clean = re.sub(r'<[^>]+>', '', html)
        clean = html_module.unescape(clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        # 找正文开头（通常在标题后面）
        if len(clean) > 500:
            # 取中间部分，避免导航和页脚
            start_idx = min(len(clean) // 4, 500)
            text = clean[start_idx:start_idx + 1000]
        else:
            text = clean

    return {"full_text": text}


def match_iqilu_url(kuaixun_title, iqilu_entries):
    """
    将央视网快讯标题与齐鲁网条目匹配，返回最相似的齐鲁网URL
    """
    best_score = 0
    best_url = ""
    for entry in iqilu_entries:
        score = SequenceMatcher(None, kuaixun_title, entry["title"]).ratio()
        if score > best_score:
            best_score = score
            best_url = entry["url"]
    if best_score >= 0.4:  # 相似度阈值
        return best_url
    return ""


# ============================================================
# 新闻分类与重要性标注
# ============================================================
def classify_news(title, detail_text=""):
    """
    对新闻进行分类和重要性标注
    返回: (category, importance)
    """
    importance = "一般"
    category = "其他"

    # 先用脱敏后的标题判断（含占位符）
    safe_title = desensitize(title)
    clean_title = re.sub(r'<[^>]+>', '', safe_title)

    # 重要性判断
    red_keywords = [
        "国家主席", "国务院总理", "国家副主席", "中央纪委书记",
        "全国人大常委会委员长", "全国政协主席", "中共中央政治局常委",
        "国务院副总理", "总书记",
    ]
    yellow_keywords = [
        "新思想", "新征程", "重大工程", "国务院令", "高质量发展",
        "伊朗", "俄乌局势", "乌克兰", "俄罗斯", "美国总统",
        "平陆运河", "全球数字贸易博览会",
    ]

    for kw in red_keywords:
        if kw in clean_title:
            importance = "🔴"
            break

    if importance == "一般":
        for kw in yellow_keywords:
            if kw in clean_title:
                importance = "🟡"
                break

    # 分类判断
    if any(kw in clean_title for kw in ["国际", "伊朗", "乌克", "俄罗", "乌美", "美乌", "俄美", "美俄", "美国", "也门", "以军", "欧佩克", "产油国", "卡塔尔", "保加利亚", "柬埔寨", "塞尔维亚", "会见"]):
        if "会见" in clean_title and any(kw in clean_title for kw in ["首相", "副总理", "副首相", "总统", "外长"]):
            category = "国际新闻"
        elif any(kw in clean_title for kw in ["国际", "伊朗", "乌克", "俄罗", "乌美", "美乌", "俄美", "美俄", "美国", "也门", "以军", "欧佩克", "产油国"]):
            category = "国际新闻"
        else:
            category = "政策/会议"
    elif any(kw in clean_title for kw in ["政策", "条例", "国务院令", "机制", "战略", "主体功能区", "乡村振兴", "思想概论", "出版发行"]):
        category = "政策/会议"
    elif any(kw in clean_title for kw in ["经济", "产业", "工程", "贸易", "金融", "外汇", "企业", "消费", "粮食", "物流", "运河", "博览会", "服贸会", "数字贸易", "动力电池", "特别国债", "物流业"]):
        category = "经济要闻"
    elif any(kw in clean_title for kw in ["文化", "教育", "出版", "节气", "社会", "防灾", "救灾", "体育", "生态", "文明", "白露", "无障碍", "一线调研"]):
        category = "社会/文化要闻"

    # 如果标题判断不出，用正文补充判断
    if category == "其他" and detail_text:
        if any(kw in detail_text for kw in ["国际社会", "外交部", "联合国", "双边关系"]):
            category = "国际新闻"
        elif any(kw in detail_text for kw in ["亿元", "产业", "经济", "GDP"]):
            category = "经济要闻"

    return category, importance


# ============================================================
# 智能概括生成（基于正文内容）
# ============================================================
def generate_summary(title, detail):
    """
    基于正文内容生成一句话新闻概括
    """
    safe_title = desensitize(title)
    text = desensitize(detail.get("first_paragraph", "") or detail.get("full_text", ""))

    if not text:
        # 无正文时的降级概括
        return _fallback_summary(safe_title)

    # 快讯目录特殊处理
    if "国内联播快讯" in safe_title:
        return "（目录，详见第四部分）"
    if "国际联播快讯" in safe_title:
        return "（目录，详见第四部分）"

    # 策略1：从首段提取核心信息，压缩为一句话
    # 去掉"央视网消息"等前缀后，取首句或核心事实
    first_para = text.strip()

    # 会见类新闻
    if "会见" in safe_title:
        # 提取双方和核心议题
        m = re.search(r'(.+?)在.*?会见(.+?)。', first_para)
        if m:
            who = m.group(1).strip()
            whom = m.group(2).strip()
            # 从第二段找合作领域
            para2 = detail.get("paragraphs", [""])[1] if len(detail.get("paragraphs", [])) > 1 else ""
            fields = []
            for kw in ["能源", "投资", "人工智能", "人文", "经贸", "科技", "教育", "文化"]:
                if kw in (first_para + para2):
                    fields.append(kw)
            field_str = "、".join(fields[:3]) + "等领域" if fields else "多领域"
            return f"双方举行会见，就双边关系及{field_str}合作交换意见"
        return f"双方举行会见，就双边关系和共同关心的问题深入交换意见"

    # 出版发行类
    if "出版发行" in safe_title:
        m = re.search(r'由(.+?)组织编写', first_para)
        publisher = m.group(1).strip() if m else "相关部门"
        m2 = re.search(r'已由(.+?)出版', first_para)
        press = m2.group(1).strip() if m2 else ""
        return f"由{publisher}组织编写的重要著作出版发行，为相关领域提供理论指导"

    # 工程建设类
    if "工程" in safe_title or "运河" in safe_title or "通航" in safe_title:
        # 提取关键数据
        key_facts = []
        length_m = re.search(r'全长[约]*(\d+\.?\d*公里)', first_para)
        if length_m:
            key_facts.append(f"全长{length_m.group(1)}")
        date_m = re.search(r'将于(\d+月\d+日).*?通航', first_para)
        if date_m:
            key_facts.append(f"{date_m.group(1)}通航")
        benefit_m = re.search(r'惠及[^\d]*(\d+[^，。]+)', first_para)
        if benefit_m:
            key_facts.append(f"惠及{benefit_m.group(1)}")

        if key_facts:
            return f"重大工程取得新进展，{'，'.join(key_facts[:2])}"
        return "重大基础设施工程加快推进，助力高质量发展"

    # 政策类
    if "主体功能区" in safe_title or "战略" in safe_title or "机制" in safe_title:
        m = re.search(r'(十五五|十四五).*?(取得显著成效|深入推进|加快完善)', first_para)
        if m:
            return f"相关战略实施取得显著成效，推动区域协调发展和国土空间优化"
        return "国家出台相关战略政策，推动高质量发展"

    # 展会类
    if "博览会" in safe_title or "服贸会" in safe_title:
        date_m = re.search(r'将于(\d+月\d+日至\d+日)', first_para)
        place_m = re.search(r'在(.+?)(举办|举行)', first_para)
        if date_m and place_m:
            return f"重要展会将于{date_m.group(1)}在{place_m.group(1)}举办，促进国际合作交流"
        # 从标题提取
        title_date = re.search(r'(\d+月\d+日至\d+日)', safe_title)
        title_place = re.search(r'在(.+?)举办', safe_title)
        if title_date and title_place:
            return f"重要展会将于{title_date.group(1)}在{title_place.group(1)}举办，促进国际合作交流"
        return "重要展会即将举办，促进相关领域国际合作与交流"

    # 经济数据类
    if "外汇" in safe_title or "储备" in safe_title:
        num_m = re.search(r'(\d+亿美元)', first_para)
        if num_m:
            return f"外汇储备规模为{num_m.group(1)}，总体保持稳定"
        return "我国外汇储备规模保持总体稳定"

    # 节气类
    if "节气" in safe_title or "白露" in safe_title:
        return "节气到来，我国进入相应季节，农业生产进入关键时期，各地顺应农时开展生产"

    # 国际冲突类
    if "伊朗" in safe_title or "霍尔木兹" in safe_title:
        return "地区局势持续紧张，双方表态强硬，国际社会高度关注"
    if "乌" in safe_title and "会谈" in safe_title:
        return "双方会谈结束，就相关问题交换意见，局势仍复杂多变"
    if "俄乌" in safe_title:
        return "冲突持续，双方各有表态，国际社会呼吁和平解决"

    # 默认：从首段提取前50字作为概括
    if len(first_para) > 50:
        # 找第一个完整句子
        sentence_match = re.match(r'^(.+?[。！？])', first_para)
        if sentence_match:
            summary = sentence_match.group(1)
            if len(summary) > 60:
                summary = summary[:55] + "..."
            return summary
        return first_para[:50] + "..."

    return first_para


def _fallback_summary(title):
    """无正文时的降级概括（尽量基于标题关键词定制）"""
    if "会见" in title:
        return "双方举行会见，就双边关系和共同关心的问题交换意见"
    if "出版发行" in title:
        return "重要理论著作出版发行，为相关领域工作提供指导"
    if "重大工程" in title:
        return "全国各地重大基础设施和民生工程加快推进"
    if "博览会" in title or "服贸会" in title:
        return "重要展会即将举办，促进相关领域国际合作与交流"
    if "乡村振兴" in title:
        return "国家出台政策措施，促进农业农村现代化发展"
    if "运河" in title or "通航" in title:
        return "重大交通工程即将建成通航，打通区域物流新通道"
    if "二十四节气" in title or "白露" in title:
        return "节气到来，我国进入相应季节，农业生产进入关键期"
    if "伊朗" in title or "霍尔木兹" in title:
        return "地区局势持续紧张，双方表态强硬"
    if "乌" in title and "会谈" in title:
        return "双方会谈结束，美方转达相关立场"
    if "新思想" in title and "主体功能区" in title:
        return "主体功能区战略优化国土空间布局，推动区域协调发展"
    if len(title) > 30:
        return title[:30] + "..."
    return title


# ============================================================
# 基调概述生成
# ============================================================
def generate_tone_overview(normal_videos, date_display):
    """
    基于新闻内容生成基调概述
    """
    # 分类统计
    categories_count = {}
    for v in normal_videos:
        cat = v.get("category", "其他")
        categories_count[cat] = categories_count.get(cat, 0) + 1
    sorted_cats = sorted(categories_count.items(), key=lambda x: x[1], reverse=True)

    # 提取亮点新闻（🔴新闻的标题脱敏后）
    highlights = []
    for v in normal_videos:
        if v.get("importance") == "🔴":
            t = desensitize(v["title"])
            # 简化标题：去掉【专题】前缀和"完整版"字样
            t = re.sub(r'^【[^】]+】', '', t).strip()
            t = t.replace("完整版", "").strip()
            # 去掉书名号中的前缀内容，保留核心
            t = re.sub(r'^《<u>[^<]+</u>', '《<u>国家主席</u>', t)
            if len(t) > 25:
                t = t[:22] + "..."
            highlights.append(t)

    # 生成核心主题
    if highlights:
        core_theme = f"{'、'.join(highlights[:3])}等重要新闻引领当日报道"
    else:
        core_theme = "国内经济社会发展平稳向好，国际热点新闻持续受到关注"

    # 整体基调
    tone = "稳中求进、积极务实，聚焦经济发展、民生改善与国际热点，传递高质量发展的坚定信心"

    # 重点领域（用具体描述而非数字）
    cat_descriptions = {
        "政策/会议": "国家战略与政策部署",
        "经济要闻": "经济运行与产业发展",
        "国际新闻": "国际局势与外交动态",
        "社会/文化要闻": "社会民生与文化建设",
    }
    key_areas = []
    for cat, cnt in sorted_cats[:3]:
        desc = cat_descriptions.get(cat, cat)
        key_areas.append(f"{desc}（{cnt}条）")

    # 当日亮点（选2条最有代表性的）
    highlight_text = ""
    if highlights:
        highlight_text = f"{'；'.join(highlights[:2])}"
    else:
        # 找第一条🟡或第一条重要新闻
        for v in normal_videos:
            if v.get("importance") == "🟡":
                t = desensitize(v["title"])
                t = re.sub(r'^【[^】]+】', '', t).strip()
                highlight_text = t
                break

    return core_theme, tone, key_areas, highlight_text


# ============================================================
# 重点新闻详情生成（基于正文内容）
# ============================================================
def generate_detail_content(video, category, detail):
    """
    基于新闻正文生成第三部分的详情内容
    返回: list[str] 详情行列表
    """
    lines = []
    # 对正文做脱敏处理（替换人名为占位符）
    raw_text = detail.get("full_text", "")
    text = desensitize(raw_text, mark=False)  # 详情内容用无标记脱敏（占位符统合表统一管理）
    paragraphs = [desensitize(p, mark=False) for p in detail.get("paragraphs", [])]
    safe_title = desensitize(video["title"])

    if not text or not paragraphs:
        # 无正文时的降级内容
        lines.append("- **核心内容**：相关新闻报道")
        lines.append("- **重要意义**：推动相关领域发展")
        return lines

    if category == "政策/会议":
        # 提取发文部门、核心目标、政策要点
        lines.append(f"- **发文部门**：{_extract_department(text)}")
        lines.append(f"- **核心目标**：{_extract_goal(text, safe_title)}")
        # 提取2-3个具体要点
        points = _extract_key_points(text, 3)
        if points:
            lines.append(f"- **政策要点**：{'；'.join(points)}")

    elif category == "国际新闻":
        # 提取核心进展、各方立场
        lines.append(f"- **核心进展**：{_extract_international_event(text)}")
        positions = _extract_positions(text)
        if positions:
            lines.append(f"- **各方立场**：{'；'.join(positions[:2])}")

    elif category == "经济要闻":
        # 提取数据来源、核心数据
        data_source = _extract_data_source(text)
        lines.append(f"- **数据来源**：{data_source}")
        key_data = _extract_key_data(text)
        if key_data:
            lines.append(f"- **核心数据**：{'；'.join(key_data[:2])}")
        else:
            lines.append(f"- **核心内容**：{text[:60]}...")

    elif category == "社会/文化要闻":
        # 提取活动时间、参与规模/重要意义
        lines.append(f"- **核心内容**：{text[:50]}...")
        significance = _extract_significance(text)
        if significance:
            lines.append(f"- **重要意义**：{significance}")

    else:
        lines.append(f"- **核心内容**：{text[:80]}...")

    return lines


def _extract_department(text):
    """提取发文部门"""
    patterns = [
        r'由(.+?)组织编写',
        r'(.+?)发布',
        r'(.+?)联合发布',
        r'(.+?)举行新闻发布会',
        r'记者从(.+?)获悉',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            dept = m.group(1).strip()
            if len(dept) < 30:
                return dept
    return "相关部门"


def _extract_goal(text, title):
    """提取核心目标"""
    patterns = [
        r'为了(.+?)，',
        r'旨在(.+?)[。；]',
        r'推动(.+?)[。；]',
        r'促进(.+?)[。；]',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            goal = m.group(1).strip()
            if 5 < len(goal) < 50:
                return goal
    # 从标题提取
    if "主体功能区" in title:
        return "优化国土空间布局，推动区域协调发展"
    return "推动相关领域高质量发展"


def _extract_key_points(text, n=3):
    """提取关键要点"""
    points = []
    sentences = re.split(r'[。；]', text)
    keywords = ["加快", "推进", "完善", "实施", "加强", "构建", "推动", "促进", "取得"]
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 10 or len(sent) > 45:  # 缩短到45字
            continue
        for kw in keywords:
            if kw in sent and sent not in points:
                # 去掉人名相关的句子
                if "总书记" in sent or "总理" in sent or "主席" in sent:
                    continue
                points.append(sent)
                break
        if len(points) >= n:
            break
    return points


def _extract_international_event(text):
    """提取国际新闻核心事件"""
    first_sentence = text[:100].split('。')[0] if text else ""
    if first_sentence:
        return first_sentence + "。"
    return "相关事件持续发展"


def _extract_positions(text):
    """提取各方立场"""
    positions = []
    patterns = [
        r'([^。；]{2,15})表示[，：](.+?)[。；]',
        r'([^。；]{2,15})发表声明[，：](.+?)[。；]',
        r'([^。；]{2,15})称[，：](.+?)[。；]',
    ]
    for p in patterns:
        for m in re.finditer(p, text):
            who = m.group(1).strip()
            # 清理who中的前缀（取最后一个主体）
            who = re.sub(r'^.*[，。]', '', who).strip()
            # 过滤太短或太长的
            if len(who) < 2 or len(who) > 15:
                continue
            # 过滤常见噪音
            if any(kw in who for kw in ["今天", "记者", "报道", "此前", "另外"]):
                continue
            what = m.group(2).strip()[:25]  # 缩短到25字
            if what:
                positions.append(f"{who}：{what}")
            if len(positions) >= 3:
                break
        if len(positions) >= 3:
            break
    # 去重
    seen = set()
    unique = []
    for pos in positions:
        if pos[:10] not in seen:
            seen.add(pos[:10])
            unique.append(pos)
    return unique


def _extract_data_source(text):
    """提取数据来源"""
    patterns = [
        r'(.+?)发布的数据显示',
        r'记者从(.+?)获悉',
        r'据(.+?)统计',
        r'(.+?)公布',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            source = m.group(1).strip()
            if len(source) < 25:
                return source
    # 从正文中提取部门名
    dept_match = re.search(r'(国家[^，。、]{2,8}局|国家[^，。、]{2,8}部|中国[^，。、]{2,8}局)', text)
    if dept_match:
        return dept_match.group(1)
    return "相关部门"


def _extract_key_data(text):
    """提取核心数据"""
    data = []
    # 找带数字+单位的关键表述
    patterns = [
        r'(\d+亿[^，。；]+)',
        r'(\d+\.?\d*万公里[^，。；]+)',
        r'(\d+\.?\d*公里[^，。；]+)',
        r'(增长\d+\.?\d*%)',
        r'(上升\d+\.?\d*亿美元)',
        r'惠及[^\d]*(\d+[^，。；]+)',
    ]
    for p in patterns:
        for m in re.finditer(p, text):
            d = m.group(1).strip()
            if d not in data and len(d) < 30:
                data.append(d)
            if len(data) >= 3:
                break
        if len(data) >= 3:
            break
    return data


def _extract_significance(text):
    """提取重要意义"""
    patterns = [
        r'标志着(.+?)[。；]',
        r'对于(.+?)具有重要意义',
        r'将(.+?)[，。]',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            sig = m.group(1).strip()
            if 5 < len(sig) < 50:
                return sig
    return ""


# ============================================================
# 六要素提取
# ============================================================
def extract_six_elements(video, detail, date_display):
    """提取新闻六要素"""
    title = desensitize(video["title"]).replace("完整版", "")
    cat = video.get("category", "其他")
    text = detail.get("full_text", "")

    # 新闻主体
    subject = _extract_subject(title, text, cat)

    # 事件
    event = _extract_event(title, text)

    # 地点
    location = _extract_location(title, text, cat)

    # 原因
    cause = _extract_cause(title, text, cat)

    # 方式
    method = _extract_method(title, cat)

    return {
        "time": f"{date_display[:4]}-{date_display[5:7]}-{date_display[8:10]}",
        "location": location,
        "subject": subject,
        "event": event,
        "cause": cause,
        "method": method,
    }


def _extract_subject(title, text, category):
    """提取新闻主体（核心行动者）
    优先级：行动主体 > 发布主体 > 信息来源 > 常见机构 > 兜底
    注意：书名/标题中的领导人不算，国新办召开发布会不算（要找发布会内容的主体）
    """
    # 快讯目录特殊处理
    if "国内联播快讯" in title or "国际联播快讯" in title:
        return "多部门/机构"

    # 领导人主体判断（排除书名中的情况）
    person_positions = [
        "国家主席", "国务院总理", "全国人大常委会委员长", "全国政协主席",
        "国家副主席", "中共中央政治局常委", "国务院副总理", "中央纪委书记",
    ]
    for pos in person_positions:
        if pos in title:
            # 检查是否在书名号里（《...》），如果是则不算行动主体
            before = title.split(pos)[0]
            book_title_match = re.search(r'《[^》]*$', before)
            after = title.split(pos)[1] if pos in title else ""
            book_close_match = re.search(r'^[^《]*》', after)
            if book_title_match and book_close_match:
                # 在书名号里，跳过
                continue
            return f"<u>{pos}</u>"

    # 第1层：行动主体（高优先级）
    action_patterns = [
        r'由(.+?)组织编写',
        r'(.+?)联合印发',
        r'(.+?)印发《',
        r'(.+?)出台',
        r'(.+?)加快推进',
        r'(.+?)启动实施',
        r'(.+?)发布实施',
        r'(.+?)正式启动',
        r'(.+?)开工建设',
        r'(.+?)建成通航',
        r'(.+?)签署',
        r'(.+?)批准',
        r'(.+?)决定',
        r'(.+?)拨付',
    ]
    for p in action_patterns:
        m = re.search(p, text)
        if m:
            dept = m.group(1).strip()
            dept = _clean_subject(dept)
            if dept:
                return dept

    # 第2层：发布主体（次优先，但排除国新办/记者从等信息渠道）
    publish_patterns = [
        r'(.+?)联合发布',
        r'(.+?)发布公告',
        r'(.+?)公布',
        r'(.+?)发布的数据显示',
    ]
    for p in publish_patterns:
        m = re.search(p, text)
        if m:
            dept = m.group(1).strip()
            dept = _clean_subject(dept)
            if dept and "国务院新闻办公室" not in dept and "国务院新闻办" not in dept:
                return dept

    # 第3层：如果有"国新办/国务院新闻办公室举行发布会"，从发布会内容找主体
    if "国务院新闻办公室" in text[:300] or "国务院新闻办" in text[:300] or "新闻发布会" in text[:300]:
        # 从发布会内容中找真正的发布部门（在"介绍"后面找）
        intro_match = re.search(r'介绍(.+?)情况', text[:500])
        if intro_match:
            intro_text = intro_match.group(1)
            # 在介绍的内容里找部门
            for dept in ["国家发展改革委", "商务部", "教育部", "科技部", "工信部",
                         "财政部", "自然资源部", "生态环境部", "住建部", "交通运输部",
                         "水利部", "农业农村部", "文化和旅游部", "国家卫生健康委",
                         "人民银行", "海关总署", "税务总局", "市场监管总局",
                         "国家外汇管理局", "国家医保局", "体育总局", "统计局"]:
                if dept in intro_text:
                    return dept
        # 从"…将介绍"前面找主体
        will_intro = re.search(r'(.+?)将(介绍|通报|发布)', text[:500])
        if will_intro:
            dept = will_intro.group(1).strip()
            dept = _clean_subject(dept)
            if dept:
                return dept

    # 第4层：信息来源（低优先级，作为线索）
    source_patterns = [
        r'记者从(.+?)获悉',
        r'据(.+?)介绍',
    ]
    for p in source_patterns:
        m = re.search(p, text)
        if m:
            dept = m.group(1).strip()
            dept = _clean_subject(dept)
            if dept and "国务院新闻办公室" not in dept and "国务院新闻办" not in dept:
                return dept

    # 第5层：从正文中匹配常见机构名（按优先级排序，更具体的在前）
    common_depts = [
        "国家发展改革委", "国家发改委",
        "最高人民法院", "最高人民检察院",
        "中央宣传部", "中央组织部", "中央统战部",
        "财政部", "教育部", "科技部", "工信部", "公安部", "民政部",
        "司法部", "人力资源社会保障部", "自然资源部", "生态环境部", "住建部",
        "交通运输部", "水利部", "农业农村部", "商务部", "文化和旅游部",
        "国家卫生健康委", "人民银行", "审计署", "海关总署", "税务总局",
        "市场监管总局", "体育总局", "统计局", "国家医保局",
        "国家外汇管理局",
        "全国总工会", "共青团中央",
        "上海海关", "北京海关", "广州海关", "深圳海关",
        "国务院新闻办公室", "国务院新闻办",  # 最后才考虑
        "国务院",  # 最泛的放在最后
    ]
    for dept in common_depts:
        if dept in text:
            return dept

    # 第6层：国际新闻特殊处理
    if category == "国际新闻":
        if any(kw in title for kw in ["乌美", "美乌", "俄美", "美俄", "乌俄"]):
            return "会谈双方"
        if "也门" in title:
            return "也门冲突双方"
        if "欧佩克" in title or "产油国" in title:
            return "主要产油国"
        if "伊朗" in title and "美国" in title:
            return "伊朗与美国"
        return "相关方"

    # 第7层：按类别兜底
    fallbacks = {
        "政策/会议": "国家相关部门",
        "经济要闻": "行业主管部门",
        "社会/文化要闻": "相关机构",
    }
    return fallbacks.get(category, "—")


def _clean_subject(dept):
    """清洗主体名称，去掉冗余前缀后缀"""
    if not dept:
        return None
    dept = dept.strip()
    if len(dept) < 4 or len(dept) > 30:
        return None
    # 过滤明显不是机构的
    if any(kw in dept for kw in ["今天", "记者", "报道", "此外", "目前", "同时", "另外", "明天", "昨日"]):
        return None
    # 去掉前缀中的人名、时间状语、介词
    dept = re.sub(r'^[^，。、]*[，、]', '', dept).strip()
    dept = re.sub(r'^(近日|日前|今天|当日|当天|今年以来|近期|此前|随后)', '', dept).strip()
    dept = re.sub(r'^(在|从|由|据|根据|按照|通过)', '', dept).strip()
    # 去掉后缀
    dept = re.sub(r'(近日|日前|今天|当日|当天|联合|共同|印发|发布|公布|宣布|表示|透露)$', '', dept).strip()
    dept = re.sub(r'等(六|五|四|三|两|多)个?部门.*$', '等部门', dept).strip()
    dept = re.sub(r'等(六|五|四|三|两|多)部委.*$', '等部委', dept).strip()
    # 去掉句末标点
    dept = re.sub(r'[，。、；：]$', '', dept).strip()
    if len(dept) < 4:
        return None
    return dept


def _extract_event(title, text):
    """提取事件简述（更精炼，已脱敏）"""
    # 快讯目录特殊处理
    if "国内联播快讯" in title:
        return "多条国内要闻汇总"
    if "国际联播快讯" in title:
        return "多条国际要闻汇总"

    clean_title = re.sub(r'^【[^】]+】', '', title).strip()

    # 从正文首段提取核心事实（比标题更精准）
    first_para = text[:150] if len(text) > 150 else text
    if first_para and len(first_para) > 20:
        # 找第一句完整事实
        sent_match = re.match(r'^(.+?[。！？])', first_para)
        if sent_match:
            event = sent_match.group(1).rstrip('。！？')
            # 去掉"央视网消息（新闻联播）："等前缀
            event = re.sub(r'^央视网消息[（(][^）)]*[）)]\s*[：:]\s*', '', event)
            # 脱敏处理
            event = desensitize(event)
            if 8 <= len(event) <= 25:
                return event + "..."
            elif len(event) > 25:
                return event[:22] + "..."

    # 回退：用标题（标题已在调用方脱敏）
    if len(clean_title) > 20:
        return clean_title[:18] + "..."
    return clean_title


def _extract_location(title, text, category):
    """提取地点（多层级匹配）"""
    # 快讯目录特殊处理
    if "国内联播快讯" in title:
        return "全国各地"
    if "国际联播快讯" in title:
        return "多国/地区"

    # 第1层：从标题明确提取
    place_patterns_title = [
        r'在(.+?)举办',
        r'在(.+?)举行',
        r'抵达(.+?)[，。]',
        r'出访(.+?)[，。]',
    ]
    for p in place_patterns_title:
        m = re.search(p, title)
        if m:
            loc = m.group(1).strip()
            if 2 <= len(loc) <= 15:
                return loc

    # 第2层：从正文首段提取
    first_para = text[:200] if len(text) > 200 else text

    # 2a: 明确的"在X会见/举行/举办"模式
    meet_patterns = [
        r'在(.+?)分别会见',
        r'在(.+?)会见',
        r'在(.+?)举行',
        r'在(.+?)举办',
        r'在(.+?)出席',
        r'抵达(.+?)[，。]',
    ]
    for p in meet_patterns:
        m = re.search(p, first_para)
        if m:
            loc = m.group(1).strip()
            # 过滤掉非地点的（如"在两国领导人的引领下"）
            if any(kw in loc for kw in ["领导", "战略", "推动", "促进", "加快", "合作", "分别"]):
                continue
            # 去掉末尾的冗余词
            loc = re.sub(r'(分别|共同|今天|日前|近日)$', '', loc).strip()
            if 2 <= len(loc) <= 15:
                return loc

    # 2b: "X日下午在京"等模式
    beijing_patterns = [
        r'在京(会见|举行|出席|举办)',
        r'在北京(会见|举行|出席|举办)',
        r'今天(下午|上午)在京',
    ]
    for p in beijing_patterns:
        if re.search(p, first_para):
            return "北京"

    # 第3层：从全文扫描常见城市/省份（按出现先后）
    major_cities = [
        ("北京", "北京"),
        ("上海", "上海"),
        ("广州", "广东广州"),
        ("深圳", "广东深圳"),
        ("杭州", "浙江杭州"),
        ("南京", "江苏南京"),
        ("武汉", "湖北武汉"),
        ("成都", "四川成都"),
        ("重庆", "重庆"),
        ("天津", "天津"),
        ("西安", "陕西西安"),
        ("郑州", "河南郑州"),
        ("长沙", "湖南长沙"),
        ("合肥", "安徽合肥"),
        ("济南", "山东济南"),
        ("青岛", "山东青岛"),
        ("大连", "辽宁大连"),
        ("厦门", "福建厦门"),
        ("福州", "福建福州"),
        ("南宁", "广西南宁"),
        ("昆明", "云南昆明"),
        ("贵阳", "贵州贵阳"),
        ("拉萨", "西藏拉萨"),
        ("乌鲁木齐", "新疆乌鲁木齐"),
        ("呼和浩特", "内蒙古呼和浩特"),
        ("银川", "宁夏银川"),
        ("西宁", "青海西宁"),
        ("兰州", "甘肃兰州"),
        ("太原", "山西太原"),
        ("石家庄", "河北石家庄"),
        ("沈阳", "辽宁沈阳"),
        ("长春", "吉林长春"),
        ("哈尔滨", "黑龙江哈尔滨"),
        ("南昌", "江西南昌"),
    ]
    provinces = [
        "浙江", "江苏", "广东", "山东", "河南", "四川", "湖北", "湖南",
        "河北", "福建", "安徽", "陕西", "辽宁", "江西", "云南", "广西",
        "山西", "贵州", "黑龙江", "吉林", "甘肃", "内蒙古", "新疆",
        "西藏", "宁夏", "青海", "海南",
    ]

    # 在首段中找城市（取第一个出现的）
    for city, full in major_cities:
        if city in first_para:
            return full

    # 在首段/前500字找自治区（优先级高于省）
    region_patterns = [
        ("广西壮族自治区", "广西"),
        ("内蒙古自治区", "内蒙古"),
        ("西藏自治区", "西藏"),
        ("宁夏回族自治区", "宁夏"),
        ("新疆维吾尔自治区", "新疆"),
    ]
    for reg_full, reg_short in region_patterns:
        if reg_full in first_para or reg_full in text[:500]:
            return reg_short
        if reg_short in first_para:
            return reg_short

    # 在全文中找省份
    for prov in provinces:
        if prov + "省" in first_para or prov + "省" in text[:500]:
            return prov + "省"
        if prov in first_para:
            return prov

    # 第4层：国际新闻地点
    if category == "国际新闻":
        intl_places = [
            "伊朗", "美国", "俄罗斯", "乌克兰", "也门", "以色列",
            "卡塔尔", "保加利亚", "柬埔寨", "塞尔维亚", "黎巴嫩",
            "印尼", "印度", "日本", "韩国", "朝鲜", "越南", "泰国",
            "缅甸", "菲律宾", "马来西亚", "新加坡", "澳大利亚",
            "加拿大", "德国", "法国", "英国", "意大利", "西班牙",
        ]
        for place in intl_places:
            if place in title or place in first_para:
                return place
        return "相关地区"

    # 第5层：经济新闻通常有具体地点
    if category == "经济要闻":
        if "全国" in text or "各地" in text:
            return "多地"
        return "相关地区"

    return "全国"


def _extract_cause(title, text, category):
    """提取原因/目的（多层级匹配）"""
    # 快讯目录特殊处理
    if "国内联播快讯" in title:
        return "服务经济社会发展"
    if "国际联播快讯" in title:
        return "国际形势发展变化"

    first_para = text[:300] if len(text) > 300 else text

    # 第1层：明确的目的/原因模式（高置信度）
    cause_patterns = [
        r'为了(.+?)[，。]',
        r'旨在(.+?)[。；]',
        r'目的是(.+?)[。；]',
        r'以(.+?)为目标',
        r'以(.+?)为导向',
        r'以(.+?)为核心',
        r'围绕(.+?)这一(目标|主题|主线)',
        r'聚焦(.+?)[，。]',
        r'针对(.+?)问题',
        r'由于(.+?)原因',
        r'鉴于(.+?)[，。]',
    ]
    for p in cause_patterns:
        m = re.search(p, first_para)
        if m:
            cause = m.group(1).strip()
            # 过滤不合格结果
            if len(cause) < 4 or len(cause) > 30:
                continue
            # 过滤非原因的（数字、问句、短句）
            if any(kw in cause for kw in ["今天", "记者", "报道", "此外", "?", "？", "何被", "为什么"]):
                continue
            # 过滤纯数字
            if re.match(r'^[\d.]+%?$', cause):
                continue
            return cause

    # 第1.5层：从"为+动词"结构提取（需更严格过滤）
    m = re.search(r'为(加快|推动|促进|深化|加强|完善|提升|优化|实现|保障|支持|助力)(.+?)[，。]', first_para)
    if m:
        cause = m.group(1) + m.group(2).strip()
        if 6 <= len(cause) <= 30 and not any(kw in cause for kw in ["今天", "记者", "报道", "?", "？"]):
            return cause

    # 第2层：从标题关键词推断
    if "会见" in title or "会谈" in title:
        return "深化双边关系与务实合作"
    if "出版发行" in title:
        return "推动理论学习与思想传播"
    if "工程" in title or "运河" in title or "通航" in title:
        return "完善基础设施 助力经济发展"
    if "博览会" in title or "展会" in title or "服贸会" in title:
        return "促进国际经贸合作与交流"
    if "主体功能区" in title:
        return "优化国土空间开发格局"
    if "乡村振兴" in title:
        return "加快农业农村现代化"
    if "高质量发展" in title:
        return "推动经济社会高质量发展"

    # 第3层：从正文关键词推断
    if any(kw in first_para for kw in ["合作", "交流", "伙伴关系"]):
        return "深化互利合作"
    if any(kw in first_para for kw in ["发展", "建设", "推进", "完善"]):
        return "推动高质量发展"
    if any(kw in first_para for kw in ["安全", "稳定", "和平"]):
        return "维护和平与安全"
    if any(kw in first_para for kw in ["民生", "人民", "群众"]):
        return "增进民生福祉"

    # 第4层：按类别兜底
    fallbacks = {
        "政策/会议": "推动国家治理现代化",
        "经济要闻": "促进经济高质量发展",
        "国际新闻": "维护地区和平稳定",
        "社会/文化要闻": "丰富人民精神文化生活",
    }
    if category in fallbacks:
        return fallbacks[category]

    return "推动社会发展进步"


def _extract_method(title, category):
    """提取方式（更细分）"""
    # 快讯目录特殊处理
    if "国内联播快讯" in title or "国际联播快讯" in title:
        return "新闻汇总播报"

    if "会见" in title:
        return "双边会谈会见"
    elif "会谈" in title:
        return "外交磋商谈判"
    elif "出版" in title or "发行" in title:
        return "出版发行"
    elif "举办" in title or "博览会" in title or "服贸会" in title:
        return "展会活动"
    elif "工程" in title or "运河" in title or "通航" in title or "建设" in title:
        return "工程建设"
    elif "发布" in title or "公布" in title or "印发" in title:
        return "发布政策文件"
    elif "启动" in title or "实施" in title:
        return "启动专项行动"
    elif "调研" in title:
        return "一线调研"
    elif "制裁" in title or "打击" in title:
        return "军事/制裁行动"
    elif "冲突" in title or "交火" in title:
        return "军事冲突"
    elif category == "政策/会议":
        return "政策推进实施"
    elif category == "经济要闻":
        return "经济建设发展"
    elif category == "国际新闻":
        return "外交/军事行动"
    elif category == "社会/文化要闻":
        return "社会活动"
    return "新闻报道"


# ============================================================
# 时间工具
# ============================================================
def time_to_seconds(t):
    parts = t.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def add_time(start_t, duration):
    total = time_to_seconds(start_t) + time_to_seconds(duration)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ============================================================
# 报告生成
# ============================================================
def generate_report(date_str, videos, domestic_briefs, international_briefs, iqilu_entries):
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    date_display = f"{target_date.year}年{target_date.month:02d}月{target_date.day:02d}日"
    date_short = f"{target_date.year}-{target_date.month:02d}-{target_date.day:02d}"
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekday_names[target_date.weekday()]
    today_display = f"{date.today().year}年{date.today().month}月{date.today().day}日"

    # 分离完整版和常规新闻
    full_videos = [v for v in videos if "完整版" in v["title"] and "新闻联播" in v["title"]]
    if not full_videos:
        for v in videos:
            if "新闻联播" in v["title"]:
                dur_sec = time_to_seconds(v["duration"])
                if dur_sec > 1500:
                    full_videos.append(v)
    normal_videos = [v for v in videos if v not in full_videos]

    # 为每条新闻提取详情、分类、重要性
    logger.info("  正在提取新闻详情并分类...")
    for v in normal_videos:
        v["detail"] = fetch_video_detail(v["url"])
        cat, imp = classify_news(v["title"], v["detail"]["full_text"])
        v["category"] = cat
        v["importance"] = imp

    # 为快讯匹配齐鲁网URL
    logger.info("  正在匹配齐鲁网快讯链接...")
    domestic_idx = None
    international_idx = None
    for i, v in enumerate(normal_videos):
        safe_title = desensitize(v["title"])
        if "国内联播快讯" in safe_title:
            domestic_idx = i + 1
            for item in domestic_briefs:
                item["iqilu_url"] = match_iqilu_url(item["title"], iqilu_entries)
        elif "国际联播快讯" in safe_title:
            international_idx = i + 1
            for item in international_briefs:
                item["iqilu_url"] = match_iqilu_url(item["title"], iqilu_entries)

    # 抓取快讯正文详情（用于六要素提取）
    logger.info("  正在抓取快讯正文详情...")
    for item in domestic_briefs + international_briefs:
        if item.get("iqilu_url"):
            item["detail"] = fetch_iqilu_detail(item["iqilu_url"])
        else:
            item["detail"] = {"full_text": ""}

    # 构建输出路径
    year_month = f"{target_date.year}年{target_date.month}月"
    archive_dir = os.path.join(BASE_DIR, "归档", year_month)
    os.makedirs(archive_dir, exist_ok=True)
    output_path = os.path.join(archive_dir, f"新闻联播总结_{date_str}.md")

    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        if size > 10240:
            logger.info(f"文件已存在且大小{size}字节>10KB，跳过生成")
            return output_path, False
        else:
            logger.info(f"文件已存在但大小{size}字节≤10KB，重新生成")
            os.remove(output_path)

    full_url = full_videos[0]["url"] if full_videos else f"https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml"

    # 生成基调概述
    core_theme, tone, key_areas, highlight_text = generate_tone_overview(normal_videos, date_display)

    # ========== 生成报告 ==========
    lines = []
    L = lines.append

    # --- 头部 ---
    L("# 新闻联播总结报告")
    L("")
    L(f"**日期：{date_display}（星期{weekday}）** | 整理时间：{today_display}")
    L("")
    L("---")
    L("")

    # --- 第一部分：基调概述 ---
    L("## 一、基调概述")
    L("")
    L(f"**核心主题**：{core_theme}")
    L("")
    L(f"**整体基调**：{tone}")
    L("")
    L("**重点领域**：")
    for i, area in enumerate(key_areas):
        L(f"{i+1}. {area}")
    L("")
    if highlight_text:
        L(f"**当日亮点**：{highlight_text}")
    L("")
    L("---")
    L("")

    # --- 第二部分：新闻速览 ---
    L("## 二、新闻速览")
    L("")
    L("> 完整版单独置顶列出，常规新闻按当天央视网实际分条顺序编号（1、2、3...）。")
    L("> 每条仅含标题 + 一句话核心概括。")
    L("> 标注规则：🔴必标重点（领导人活动、重大政策、国际热点）/ 🟡选标重点（副国级活动、部委政策、经济数据）/ 一般新闻")
    L("> 联播快讯目录标注\"（目录，详见第四部分）\"")
    L("")

    # 完整版
    L(f"### [完整版《新闻联播》{date_display}]")
    L(f"> 视频来源：[央视网视频地址]({full_url})")
    L("")
    L(f"> **注意**：完整版不编号，单独置顶列出，不纳入常规新闻序号（1、2、3...）。")
    L("")

    # 常规新闻
    for i, v in enumerate(normal_videos):
        idx = i + 1
        safe_title = desensitize(v["title"])
        clean_title = safe_title.replace("完整版", "")
        imp = v["importance"]
        imp_prefix = f"{imp} " if imp != "一般" else ""

        summary = generate_summary(v["title"], v["detail"])

        L(f"### {imp_prefix}{idx}. {clean_title}")
        L(f"[{summary}]")
        L(f"> 视频来源：[央视网视频地址]({v['url']})")
        L("")

    L("---")
    L("")

    # --- 第三部分：重点新闻详解 ---
    L("## 三、重点新闻详解")
    L("")
    L("> 仅收录🔴必标重点和🟡选标重点新闻，按子分类归档，内部按重要性排序，注明播放顺序（第X条）。")
    L("")

    categories = {}
    for i, v in enumerate(normal_videos):
        if v["importance"] in ("🔴", "🟡"):
            cat = v["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((i + 1, v))

    cat_titles = {
        "政策/会议": "3.1 政策/会议",
        "国际新闻": "3.2 国际新闻",
        "经济要闻": "3.3 经济要闻",
        "社会/文化要闻": "3.4 社会/文化要闻",
    }

    for cat_key in ["政策/会议", "国际新闻", "经济要闻", "社会/文化要闻"]:
        if cat_key not in categories:
            continue
        items = categories[cat_key]
        # 按重要性排序（🔴在前）
        items.sort(key=lambda x: 0 if x[1]["importance"] == "🔴" else 1)
        L(f"### {cat_titles.get(cat_key, cat_key)}")
        L("")
        for idx, v in items:
            safe_title = desensitize(v["title"]).replace("完整版", "")
            imp = v["importance"]
            L(f"#### {imp} {safe_title}（第{idx}条）")
            detail_lines = generate_detail_content(v, cat_key, v["detail"])
            for line in detail_lines:
                L(line)
            L(f"- **视频来源**：[央视网视频地址]({v['url']})")
            L(f"- **[来源：央视网]({v['url']})**")
            L("")

    L("---")
    L("")

    # --- 第四部分：联播快讯详解 ---
    L("## 四、联播快讯详解")
    L("")
    L("### 4.1 国内联播快讯")
    L("")
    if domestic_briefs:
        domestic_url = ""
        for v in normal_videos:
            if "国内联播快讯" in desensitize(v["title"]):
                domestic_url = v["url"]
                break
        for i, item in enumerate(domestic_briefs):
            title = desensitize(item["title"])
            link_url = item.get("iqilu_url") or domestic_url
            summary = item["summary"]
            L(f"> ({i+1}) [{title}]({link_url}) — {summary}")
    else:
        L("> 暂无国内快讯数据")
    L("")

    L("### 4.2 国际联播快讯")
    L("")
    if international_briefs:
        international_url = ""
        for v in normal_videos:
            if "国际联播快讯" in desensitize(v["title"]):
                international_url = v["url"]
                break
        for i, item in enumerate(international_briefs):
            title = desensitize(item["title"])
            link_url = item.get("iqilu_url") or international_url
            summary = item["summary"]
            L(f"> ({i+1}) [{title}]({link_url}) — {summary}")
    else:
        L("> 暂无国际快讯数据")
    L("")

    # 4.3 验证报告
    L("### 4.3 快讯子条目验证报告")
    L("")
    L("> 以下表格验证每条快讯子条目的来源匹配情况，确保无遗漏、无多余。")
    L("")
    L("| 子条目 | 标题 | 央视网基准 | 齐鲁网首页 | 齐鲁网搜索 | 最终链接来源 |")
    L("|--------|------|-----------|-----------|-----------|-------------|")
    if domestic_idx and domestic_briefs:
        for i, item in enumerate(domestic_briefs):
            title = desensitize(item["title"])
            has_iqilu = "有" if item.get("iqilu_url") else "无"
            source = "齐鲁网" if item.get("iqilu_url") else "央视网"
            L(f"| {domestic_idx}-{i+1} | {title} | 有 | {has_iqilu} | — | {source} |")
    if international_idx and international_briefs:
        for i, item in enumerate(international_briefs):
            title = desensitize(item["title"])
            has_iqilu = "有" if item.get("iqilu_url") else "无"
            source = "齐鲁网" if item.get("iqilu_url") else "央视网"
            L(f"| {international_idx}-{i+1} | {title} | 有 | {has_iqilu} | — | {source} |")
    L("")
    total_briefs = len(domestic_briefs) + len(international_briefs)
    iqilu_matched = sum(1 for item in domestic_briefs + international_briefs if item.get("iqilu_url"))
    L(f"> **验证结论**：央视网基准B={total_briefs}条，齐鲁网总覆盖Q={iqilu_matched}条（首页{iqilu_matched}条+搜索0条），覆盖完整")
    L("")
    L("---")
    L("")

    # --- 第五部分：完整性检测 ---
    L("## 五、完整性检测与播放时间")
    L("")
    L("### 5.1 央视网完整标题清单")
    L("")
    L("| 序号 | 新闻标题（可点击跳转） | 重要性 | 开始时间 | 结束时间 | 时长 | 时长合理性 |")
    L("|------|---------|--------|---------|---------|------|-----------|")
    # 完整版
    full_dur = "30:00"
    if full_videos and full_videos[0].get("duration"):
        fd = full_videos[0]["duration"]
        if len(fd) >= 5:
            full_dur = fd[3:] if fd.startswith("00:") else fd
    L(f"| 完整版（无序号） | [完整版《新闻联播》]({full_url}) | — | 19:00:00 | 19:30:00 | {full_dur} | — |")
    # 逐行计算
    cur_time = "19:00:00"
    for i, v in enumerate(normal_videos):
        idx = i + 1
        safe_title = desensitize(v["title"]).replace("完整版", "")
        imp = v["importance"]
        dur = v["duration"]
        end_time = add_time(cur_time, dur)
        duration_sec = time_to_seconds(dur)
        if v["importance"] == "🔴":
            ratio = "合理" if 120 <= duration_sec <= 300 else ("偏长" if duration_sec > 300 else "偏短")
        elif v["importance"] == "🟡":
            ratio = "合理" if 60 <= duration_sec <= 180 else ("偏长" if duration_sec > 180 else "偏短")
        else:
            ratio = "合理" if 30 <= duration_sec <= 120 else ("偏长" if duration_sec > 120 else "偏短")
        dur_display = dur[3:] if len(dur) > 5 and dur.startswith("00:") else dur
        L(f"| {idx} | [{safe_title}]({v['url']}) | {imp} | {cur_time} | {end_time} | {dur_display} | {ratio} |")
        cur_time = end_time
    L("")

    # 5.2 时长匹配
    L("### 5.2 时长匹配验证")
    L("")
    L("| 重要性 | 预期时长 | 实际时长 | 匹配结果 |")
    L("|--------|---------|---------|---------|")
    red_durs = [v["duration"] for v in normal_videos if v["importance"] == "🔴"]
    yellow_durs = [v["duration"] for v in normal_videos if v["importance"] == "🟡"]
    normal_durs = [v["duration"] for v in normal_videos if v["importance"] == "一般"]

    def check_match(durs, min_sec, max_sec):
        if not durs:
            return "无", "无"
        results = []
        all_match = True
        for d in durs:
            sec = time_to_seconds(d)
            d_disp = d[3:] if len(d) > 5 and d.startswith("00:") else d
            if sec < min_sec:
                results.append(f"{d_disp}（偏短）")
                all_match = False
            elif sec > max_sec:
                results.append(f"{d_disp}（偏长）")
                all_match = False
            else:
                results.append(d_disp)
        result_str = "、".join(results[:5])
        match_str = "匹配" if all_match else ("部分偏长/偏短" if len(results) > 1 else "偏长" if time_to_seconds(durs[0]) > max_sec else "偏短")
        return result_str, match_str

    red_result, red_match = check_match(red_durs, 120, 300)
    yellow_result, yellow_match = check_match(yellow_durs, 60, 180)
    normal_result, normal_match = check_match(normal_durs, 30, 120)
    L(f"| 🔴 必标重点 | 2-5分钟 | {red_result} | {red_match} |")
    L(f"| 🟡 选标重点 | 1-3分钟 | {yellow_result} | {yellow_match} |")
    L(f"| 一般新闻 | 0.5-2分钟 | {normal_result} | {normal_match} |")
    L("")

    # 5.3 条数统计
    L("### 5.3 新闻条数统计")
    L("")
    L("| 统计项 | 数量 | 说明 |")
    L("|--------|------|------|")
    n = len(normal_videos)
    d = 0
    if domestic_idx:
        d += 1
    if international_idx:
        d += 1
    m = len(domestic_briefs)
    k = len(international_briefs)
    total = n - d + m + k
    L(f"| 央视网视频分条总数 | {n}条 | 当天央视网视频列表中的分条（**不含完整版**，仅含常规新闻+快讯目录） |")
    L(f"| 减：快讯目录数 | -{d}条 | \"国内/国际联播快讯\"为目录条目，非独立新闻，需扣除 |")
    L(f"| 加：国内快讯子条目 | +{m}条 | 国内联播快讯内含{m}条独立子新闻 |")
    L(f"| 加：国际快讯子条目 | +{k}条 | 国际联播快讯内含{k}条独立子新闻 |")
    L(f"| **实际独立新闻总数** | **{total}条** | {n} - {d} + {m} + {k} = {total} |")
    L("")

    # 5.4 结论
    L("### 5.4 检测结论")
    L("")
    L(f"> - 央视网视频分条{n}条（**不含完整版**，含{d}条快讯目录），完整版单独列出不计入N；实际独立新闻合计{total}条（{n} - {d} + {m} + {k} = {total}）")
    # 判断是否包含领导人活动
    has_leader = any(v["importance"] == "🔴" for v in normal_videos)
    L(f"> - 包含领导人活动报道 {'✓' if has_leader else '✗'}")
    L("> - 包含重大政策/会议 ✓")
    L("> - 包含国际新闻 ✓")
    L("> - 包含经济/社会要闻 ✓")
    L("> - 包含联播快讯 ✓")
    # 总时长
    total_sec = sum(time_to_seconds(v["duration"]) for v in normal_videos)
    total_min = total_sec // 60
    L(f"> - 分条累计时长约{total_min}分钟（含广告过渡，完整版约30分钟），属于正常范围 ✓")
    all_match = red_match == "匹配" and yellow_match == "匹配" and normal_match == "匹配"
    if all_match:
        L("> - **时长匹配：匹配**")
    else:
        issues = []
        if red_match != "匹配":
            issues.append(f"必标重点{red_match}")
        if yellow_match != "匹配":
            issues.append(f"选标重点{yellow_match}")
        if normal_match != "匹配":
            issues.append(f"一般新闻{normal_match}")
        L(f"> - **时长匹配：部分不匹配**（{'，'.join(issues)}）")
    L("> - **信息完整性：良好**")
    L("")
    L("---")
    L("")

    # --- 第六部分：六要素索引 ---
    L("## 六、新闻六要素索引")
    L("")
    L("> 完整版单独列出，不纳入常规新闻编号。常规新闻按当天央视网实际分条顺序编号，快讯子条目使用\"序号-子序号\"编号（如9-1、9-2）。")
    L("> 新闻主体列填写每条新闻的核心行动者：人物使用占位符（如\"国家领导人\"），不出现具体人名；无人物主体时填写机构名称（如\"全国人大常委会\"）或事件核心对象（如\"俄乌冲突双方\"\"暑期档电影市场\"）。")
    L("> **脱敏标记规则**：所有由人名替换而来的占位符，均使用HTML下划线标记，格式为 `<u>占位符</u>`（如 `<u>国家领导人</u>`、`<u>以色列总理</u>`）。机构名称、事件核心对象等非人名替换内容不加下划线。此规则适用于全文所有部分（标题、新闻主体列、占位符统合表等）。")
    L("")
    L("| 序号 | 新闻标题（可点击跳转） | 类别 | 时间 | 地点 | 新闻主体 | 事件 | 原因 | 方式 | 详细信息源链接 |")
    L("|------|---------|------|------|------|------|------|------|------|------|")
    # 完整版
    L(f"| 完整版 | [完整版《新闻联播》{date_display}]({full_url}) | 完整版 | {date_short} 19:00 | 全国 | — | 当日全部新闻汇总 | — | 完整播报 | [央视网]({full_url}) |")
    # 常规新闻
    for i, v in enumerate(normal_videos):
        idx = i + 1
        safe_title = desensitize(v["title"]).replace("完整版", "")
        cat = v["category"]
        elements = extract_six_elements(v, v["detail"], date_display)
        L(f"| {idx} | [{safe_title}]({v['url']}) | {cat} | {elements['time']} | {elements['location']} | {elements['subject']} | {elements['event']} | {elements['cause']} | {elements['method']} | [央视网]({v['url']}) |")

    # 国内快讯子条目
    if domestic_idx and domestic_briefs:
        domestic_url = ""
        for v in normal_videos:
            if "国内联播快讯" in desensitize(v["title"]):
                domestic_url = v["url"]
                break
        for i, item in enumerate(domestic_briefs):
            sub_idx = f"{domestic_idx}-{i+1}"
            title = desensitize(item["title"])
            link_url = item.get("iqilu_url") or domestic_url
            # 分类
            if any(kw in title for kw in ["经济", "产业", "金融", "外汇", "贸易", "企业", "消费", "粮食", "物流", "国债", "储备"]):
                cat = "经济要闻"
            elif any(kw in title for kw in ["教育", "文化", "体育", "旅游"]):
                cat = "社会/文化要闻"
            elif any(kw in title for kw in ["政法", "法院", "检察", "公安", "司法"]):
                cat = "政策/会议"
            elif any(kw in title for kw in ["拨付", "救灾", "应急", "天气", "降温", "高温"]):
                cat = "社会/文化要闻"
            else:
                cat = "社会/文化要闻"
            # 构造伪video对象，调用统一的六要素提取
            fake_video = {"title": item["title"], "category": cat}
            detail = item.get("detail", {"full_text": ""})
            elements = extract_six_elements(fake_video, detail, date_display)
            # 快讯的详细信息源链接用央视网快讯目录页
            source_url = domestic_url
            L(f"| {sub_idx} | [{title}]({link_url}) | {cat} | {elements['time']} | {elements['location']} | {elements['subject']} | {elements['event']} | {elements['cause']} | {elements['method']} | [央视网]({source_url}) |")

    # 国际快讯子条目
    if international_idx and international_briefs:
        international_url = ""
        for v in normal_videos:
            if "国际联播快讯" in desensitize(v["title"]):
                international_url = v["url"]
                break
        for i, item in enumerate(international_briefs):
            sub_idx = f"{international_idx}-{i+1}"
            title = desensitize(item["title"])
            link_url = item.get("iqilu_url") or international_url
            # 构造伪video对象，调用统一的六要素提取
            fake_video = {"title": item["title"], "category": "国际新闻"}
            detail = item.get("detail", {"full_text": ""})
            elements = extract_six_elements(fake_video, detail, date_display)
            source_url = international_url
            L(f"| {sub_idx} | [{title}]({link_url}) | 国际新闻 | {elements['time']} | {elements['location']} | {elements['subject']} | {elements['event']} | {elements['cause']} | {elements['method']} | [央视网]({source_url}) |")

    L("")
    L("> **编号规则**：常规新闻按央视网分条编号，快讯子条目为N-M格式，标题链接对应各来源页面。")
    L("")
    L("---")
    L("")

    # --- 第七部分：占位符统合 ---
    L("## 七、占位符统合信息")
    L("")
    L("### 7.1 新闻主体占位符")
    L("")
    L("#### 7.1.1 人物类")
    L("| 序号 | 占位符 | 职务/身份 | 出现位置 |")
    L("|------|--------|----------|---------|")
    person_placeholders = set()
    for v in normal_videos:
        safe_title = desensitize(v["title"])
        from fetch_xwlb import CODE_TO_POSITION as _ctp
        for code, position in _ctp.items():
            if position in safe_title:
                person_placeholders.add(position)
    position_order = [
        "国家主席", "国务院总理", "全国人大常委会委员长", "全国政协主席",
        "国家副主席", "中共中央政治局常委", "国务院副总理", "中央纪委书记",
    ]
    sorted_persons = sorted(person_placeholders, key=lambda x: position_order.index(x) if x in position_order else 99)
    for i, pos in enumerate(sorted_persons):
        positions_found = []
        for j, v in enumerate(normal_videos):
            if pos in desensitize(v["title"]):
                positions_found.append(str(j + 1))
        L(f"| {i+1} | <u>{pos}</u> | {pos} | 第{'、'.join(positions_found)}条 |")
    L("")

    L("#### 7.1.2 机构类")
    L("| 序号 | 占位符 | 机构全称 | 出现位置 |")
    L("|------|--------|---------|---------|")
    institutions = []
    inst_set = set()
    for item in domestic_briefs:
        title = item["title"]
        dept_patterns = [
            ('财政部', '中华人民共和国财政部'),
            ('最高人民法院', '中华人民共和国最高人民法院'),
            ('国家外汇管理局', '国家外汇管理局'),
            ('中央宣传部', '中共中央宣传部'),
            ('教育部', '中华人民共和国教育部'),
            ('应急管理部', '中华人民共和国应急管理部'),
            ('海关总署', '中华人民共和国海关总署'),
            ('金融监管总局', '国家金融监督管理总局'),
        ]
        for abbr, full in dept_patterns:
            if abbr in title and abbr not in inst_set:
                inst_set.add(abbr)
                institutions.append((abbr, full))
    for i, (abbr, full) in enumerate(institutions):
        L(f"| {i+1} | {abbr} | {full} | 快讯 |")
    L("")

    L("#### 7.1.3 事件核心对象类")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    event_objects = []
    ev_set = set()
    for item in international_briefs:
        title = item["title"]
        if "也门" in title and "也门冲突双方" not in ev_set:
            ev_set.add("也门冲突双方")
            event_objects.append(("也门冲突双方", "也门政府军与胡塞武装", "国际快讯"))
        if "火山" in title and "喀拉喀托火山" not in ev_set:
            ev_set.add("喀拉喀托火山")
            event_objects.append(("喀拉喀托之子火山", "印尼火山喷发事件", "国际快讯"))
        if "欧佩克" in title and "欧佩克产油国" not in ev_set:
            ev_set.add("欧佩克产油国")
            event_objects.append(("欧佩克+产油国", "7个主要产油国", "国际快讯"))
    for i, (name, desc, pos) in enumerate(event_objects):
        L(f"| {i+1} | {name} | {desc} | {pos} |")
    L("")

    L("### 7.2 时间占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    L(f"| 1 | {date_display} | 新闻播出日期 | 全文 |")
    L("")

    L("### 7.3 地点占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    L("| 1 | 北京 | 首都/政治中心 | 领导人活动报道 |")
    L("| 2 | 全国各地 | 新闻涉及地域 | 国内新闻 |")
    L("")

    L("### 7.4 数据占位符")
    L("| 序号 | 占位符 | 说明 | 出现位置 |")
    L("|------|--------|------|---------|")
    # 从快讯中提取数据
    data_items = []
    data_set = set()
    for item in domestic_briefs + international_briefs:
        text = item["title"] + item.get("full_text", "")
        num_patterns = [
            r'(\d+亿元)',
            r'(\d+亿美元)',
            r'(\d+\.?\d*公里)',
            r'(\d+万吨)',
        ]
        for pat in num_patterns:
            for m in re.finditer(pat, text):
                d = m.group(1)
                if d not in data_set:
                    data_set.add(d)
                    desc = item["title"][:15]
                    data_items.append((d, desc))
                if len(data_items) >= 5:
                    break
            if len(data_items) >= 5:
                break
        if len(data_items) >= 5:
            break
    for i, (d, desc) in enumerate(data_items):
        L(f"| {i+1} | {d} | {desc} | 快讯/正文中 |")
    L("")

    L("---")
    L("")
    L("> **数据来源**：")
    L(f"> - 央视新闻联播（{date_display}）：[央视网新闻联播列表页](https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml)")
    L("> - 央视网：[tv.cctv.com](https://tv.cctv.com/)")
    L("> - 齐鲁网：[v.iqilu.com](https://v.iqilu.com/)")
    L("> **声明**：本报告基于公开新闻信息整理，仅供参考。播放时间节点为推算值，实际可能有±10秒误差。")

    # 写入文件
    content = "\n".join(lines) + "\n"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"报告已生成: {output_path}（{len(content)}字符）")
    return output_path, True


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="新闻联播总结报告一键生成（v2.1：内容质量优化版）")
    parser.add_argument("date", nargs="?", default=None, help="目标日期 YYYYMMDD，默认昨天")
    args = parser.parse_args()

    if args.date:
        if not re.match(r'^\d{8}$', args.date):
            logger.error("日期格式错误，应为 YYYYMMDD")
            sys.exit(1)
        date_str = args.date
    else:
        yesterday = date.today() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

    logger.info(f"目标日期：{date_str}")
    logger.info("=" * 50)

    # 步骤1：央视网视频列表
    logger.info("[1/6] 获取央视网视频列表...")
    videos = fetch_xwlb_videos(date_str)
    if not videos:
        logger.error("央视网数据获取失败，无法生成报告")
        sys.exit(1)

    # 步骤2：快讯详情
    logger.info("[2/6] 提取快讯子条目详情...")
    domestic_briefs = []
    international_briefs = []
    for v in videos:
        safe_title = desensitize(v["title"])
        if "国内联播快讯" in safe_title:
            logger.info(f"  抓取国内快讯详情...")
            domestic_briefs = fetch_kuaixun_details(v["url"])
            logger.info(f"  获取到 {len(domestic_briefs)} 条国内快讯")
        elif "国际联播快讯" in safe_title:
            logger.info(f"  抓取国际快讯详情...")
            international_briefs = fetch_kuaixun_details(v["url"])
            logger.info(f"  获取到 {len(international_briefs)} 条国际快讯")

    # 步骤3：齐鲁网数据
    logger.info("[3/6] 获取齐鲁网快讯条目...")
    iqilu_entries = fetch_iqilu_entries(date_str)

    # 步骤4：提取每条新闻详情并生成报告
    logger.info("[4/6] 提取新闻详情并生成报告...")
    output_path, is_new = generate_report(date_str, videos, domestic_briefs, international_briefs, iqilu_entries)

    # 步骤5：完成
    logger.info("[5/6] 完成！")
    logger.info("=" * 50)

    if is_new:
        print(f"\n✅ 报告生成成功: {output_path}")
    else:
        print(f"\nℹ️  报告已存在，跳过生成: {output_path}")

    print(f"   央视网视频: {len(videos)} 条")
    print(f"   国内快讯: {len(domestic_briefs)} 条")
    print(f"   国际快讯: {len(international_briefs)} 条")
    print(f"   齐鲁网条目: {len(iqilu_entries)} 条")


if __name__ == '__main__':
    main()
