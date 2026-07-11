#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
央视网新闻联播视频列表提取脚本（解决动态加载问题）
通过分析页面源码中的 script/json 数据，提取完整的视频列表

版本：v1.4.0（2026-07-11）
变更：
  v1.4.0 - 脱敏函数升级为三阶段替换法：修复AB→AA去重bug和误加标签bug；修复映射表Unicode编码错误
  v1.3.0 - 通用化改造：日期改为可选参数，默认取前一天；增加格式校验和日期范围检查，支持任意历史日期
  v1.2.0 - 新增脱敏函数desensitize()：输出时自动将人名替换为占位符
  v1.1.0 - 添加网络请求重试逻辑（失败等待3秒重试1次）
  v1.1.0 - 添加日志文件输出（fetch_xwlb.log）
  v1.0.0 - 初始版本
"""
import requests
import re
import json
import sys
import os
import time
import logging
import argparse
from datetime import datetime, date, timedelta
from urllib.parse import unquote

# 日志配置：同时输出到控制台和文件
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "fetch_xwlb.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 1       # 最大重试次数
RETRY_DELAY = 3       # 重试等待秒数
REQUEST_TIMEOUT = 30   # 请求超时秒数

# ============================================================
# 脱敏映射表：人名 → 占位符
# 使用Unicode转义序列存储，避免代码中出现明文人名
# 格式：(人名Unicode转义, 替换占位符)
# ============================================================
DESENSITIZE_MAP = [
    # 国内领导人（正国级）
    ("\u4e60\u8fd1\u5e73", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),           # -> 国家领导人
    ("\u674e\u5f3a", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),                 # -> 国家领导人
    ("\u8d75\u4e50\u9645", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),           # -> 国家领导人
    ("\u4e0c\u9526\u4e66", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),           # -> 国家领导人
    ("\u97e9\u6b63", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),                 # -> 国家领导人
    ("\u738b\u6caa\u5b81", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),           # -> 国家领导人
    ("\u8521\u5947", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),                 # -> 国家领导人
    ("\u4e01\u859b\u7965", "\u56fd\u5bb6\u9886\u5bfc\u4eba"),           # -> 国家领导人
    # 外国政要
    ("\u5185\u5854\u5c3c\u4e9a\u80e1", "\u4ee5\u8272\u5217\u603b\u7406"),     # -> 以色列总理
    ("\u5362\u5361\u7533\u79d1", "\u767d\u4fc4\u7f57\u65af\u603b\u7edf"),     # -> 白俄罗斯总统
    ("\u8f9b\u9c8d\u59c6", "\u58a8\u897f\u54e5\u603b\u7edf"),               # -> 墨西哥总统
    ("\u65af\u5854\u9ed8", "\u82f1\u56fd\u9996\u76f8"),                     # -> 英国首相
    ("\u683c\u7f57\u897f", "\u56fd\u9645\u539f\u5b50\u80fd\u673a\u6784\u603b\u5e72\u4e8b"),  # -> 国际原子能机构总干事
    ("\u666e\u4eac", "\u4fc4\u7f57\u65af\u603b\u7edf"),                     # -> 俄罗斯总统
    ("\u6cfd\u8fde\u65af\u57fa", "\u4e4c\u514b\u5170\u603b\u7edf"),         # -> 乌克兰总统
    ("\u7279\u6717\u666e", "\u7f8e\u56fd\u603b\u7edf"),                     # -> 美国总统
    ("\u9a6c\u514b\u9f99", "\u6cd5\u56fd\u603b\u7edf"),                     # -> 法国总统
    ("\u7231\u4e3d\u7eee", "\u97e9\u56fd\u603b\u7edf"),                     # -> 韩国总统
    ("\u5cb3\u8fc8\u952e", "\u5370\u5ea6\u603b\u7406"),                     # -> 印度总理
]


def desensitize(text, mark=True):
    """
    对文本执行脱敏处理：将人名替换为占位符（三阶段替换法）
    
    解决两个问题：
    1. AB→AA重复：如"斯塔默"→"英国首相"，原文"斯塔默宣布辞职"变为
       "英国首相宣布辞职"（正确），但"英国首相斯塔默"→"英国首相英国首相"（重复）
    2. 误加标签：占位符文本本身不应被二次标记
    
    三阶段流程：
    阶段1 - 人名→临时标记（用\u0000包裹，确保不会与任何真实文本冲突）
    阶段2 - 去重相邻重复的临时标记（ABB→AB，AB\u0000B→AB）
    阶段3 - 临时标记→最终输出（加<u>标签或纯文本）
    
    :param text: 原始文本
    :param mark: 是否为占位符添加下划线标记（<u>标签）
    :return: 脱敏后文本
    """
    SENTINEL = "\u0000"  # 临时标记字符，不会出现在正常文本中
    
    # ── 阶段1：人名 → 临时标记 ──
    result = text
    for name_unicode, placeholder in DESENSITIZE_MAP:
        replacement = f"{SENTINEL}{placeholder}{SENTINEL}"
        result = result.replace(name_unicode, replacement)
    
    # ── 阶段2：去重相邻重复的占位符（多种模式循环处理） ──
    prev = None
    max_iterations = 10
    iteration = 0
    while result != prev and iteration < max_iterations:
        prev = result
        
        # 模式A：两个完全相同的SENTINEL包裹块相邻
        #   \u0000英国首相\u0000\u0000英国首相\u0000 → \u0000英国首相\u0000
        wrapped = re.compile(
            f'({re.escape(SENTINEL)}[^{re.escape(SENTINEL)}]+?{re.escape(SENTINEL)})'
            f'\\1'
        )
        result = wrapped.sub(r'\1', result)
        
        # 模式B：裸文本在前 + 相同的SENTINEL包裹块在后
        #   英国首相\u0000英国首相\u0000 → \u0000英国首相\u0000
        bare_wrapped = re.compile(
            f'([^{{\\n{re.escape(SENTINEL)}}}]+?)'
            f'({re.escape(SENTINEL)}\\1{re.escape(SENTINEL)})'
        )
        result = bare_wrapped.sub(r'\2', result)
        
        # 模式C：SENTINEL包裹块在前 + 相同的裸文本在后
        #   \u0000英国首相\u0000英国首相 → \u0000英国首相\u0000
        wrapped_bare = re.compile(
            f'({re.escape(SENTINEL)}([^{{\\n{re.escape(SENTINEL)}}}]+?){re.escape(SENTINEL)})'
            f'\\2'
        )
        result = wrapped_bare.sub(r'\1', result)
        
        iteration += 1
    
    # ── 阶段3：临时标记 → 最终输出 ──
    if mark:
        # 用正则精确匹配配对SENTINEL，替换为<u>标签
        result = re.sub(
            f'{re.escape(SENTINEL)}(.+?){re.escape(SENTINEL)}',
            r'<u>\1</u>',
            result
        )
    else:
        # 去掉临时标记，保留纯文本
        result = result.replace(SENTINEL, '')
    
    return result


def fetch_xwlb_list(date_str):
    """
    获取指定日期的新闻联播视频列表
    :param date_str: 日期字符串，格式 YYYYMMDD，如 20260624
    :return: list[dict]，每个元素包含 title, duration, url
    """
    url = f"https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://tv.cctv.com/lm/xwlb/",
    }

    # 带重试的网络请求
    html = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(f"请求 {url}（第{attempt+1}次，共{MAX_RETRIES+1}次）")
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            html = resp.text
            logger.info(f"请求成功，页面长度: {len(html)} 字符")
            break
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求失败（第{attempt+1}次）: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"等待 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"请求最终失败，已耗尽 {MAX_RETRIES+1} 次尝试")
                return []

    if not html:
        return []

    # 央视网页面中，视频列表通常以特定格式存储
    # 方法：从页面源码中提取所有包含 [视频] 标题 + 时长 + URL 的条目

    results = []

    # 匹配模式1：查找 <li> 内的完整视频条目
    li_pattern = re.compile(
        r'<li[^>]*>.*?'
        r'(?:(\d{2}:\d{2}:\d{2})|class=["\']time["\'][^>]*>(\d{2}:\d{2}:\d{2})).*?'
        r'<a[^>]*href=["\'](https://tv\.cctv\.com/[^"\']+)["\'][^>]*>(.*?)</a>.*?'
        r'</li>',
        re.DOTALL | re.IGNORECASE
    )

    matches = li_pattern.findall(html)
    seen_urls = set()

    for match in matches:
        duration = match[0] or match[1]
        video_url = match[2]
        title_raw = match[3]

        # 去重
        if video_url in seen_urls:
            continue
        seen_urls.add(video_url)

        # 清理标题：去除HTML标签和URL编码，保留原标题（含完整版标识）
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        title = unquote(title)
        title = title.replace('[视频]', '').strip()
        # 注意：不自动去除"完整版"前缀，由调用方判断是否单独列出

        results.append({
            "title": title,
            "duration": duration,
            "url": video_url
        })

    logger.info(f"模式1匹配到 {len(matches)} 条原始结果，去重后 {len(results)} 条")

    # 如果上面的模式没匹配到，使用方法2：逐条提取
    if not results:
        logger.warning("模式1无结果，切换到逐条提取模式")

        url_pattern = re.compile(r'https://tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[^\s"<>]+\.shtml')
        all_urls = url_pattern.findall(html)
        unique_urls = list(dict.fromkeys(all_urls))

        title_pattern = re.compile(r'\[视频\]([^<\n]+)')
        titles = title_pattern.findall(html)

        duration_pattern = re.compile(r'(\d{2}:\d{2}:\d{2})')
        durations = duration_pattern.findall(html)

        for i, video_url in enumerate(unique_urls):
            title = titles[i].strip() if i < len(titles) else ""
            duration = durations[i] if i < len(durations) else ""
            results.append({
                "title": title,
                "duration": duration,
                "url": video_url
            })

        logger.info(f"逐条提取模式获取 {len(results)} 条")

    # 断言URL唯一性
    assert len(set(r['url'] for r in results)) == len(results), "存在重复URL！"
    logger.info(f"URL唯一性验证通过，共 {len(results)} 条唯一URL")

    return results


def save_config(results, date_str, output_path):
    """保存为JSON配置文件"""
    config = {
        "date": date_str,
        "source": "https://tv.cctv.com/lm/xwlb/",
        "total": len(results),
        "videos": results
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"配置文件已保存: {output_path}")
    return config


def validate_date(date_str):
    """
    校验日期格式和范围
    :param date_str: 日期字符串，格式 YYYYMMDD
    :return: 校验通过的日期字符串，或 None（校验失败）
    """
    # 格式校验：必须是8位数字
    if not re.match(r'^\d{8}$', date_str):
        logger.error(f"日期格式错误：'{date_str}'，必须为 YYYYMMDD 格式（8位数字）")
        return None

    try:
        target_date = datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        logger.error(f"日期无效：'{date_str}'，不存在该日期")
        return None

    # 范围校验：不早于1978-01-01（新闻联播首播日），不晚于今天
    min_date = date(1978, 1, 1)
    max_date = date.today()
    if target_date < min_date:
        logger.error(f"日期超出范围：'{date_str}'，新闻联播最早从1978年1月1日开始")
        return None
    if target_date > max_date:
        logger.error(f"日期为未来日期：'{date_str}'，不能超过今天（{max_date.strftime('%Y%m%d')}）")
        return None

    return date_str


def main():
    parser = argparse.ArgumentParser(
        description="央视网新闻联播视频列表提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python fetch_xwlb.py                              # 不传日期，默认取昨天的数据
  python fetch_xwlb.py 20260709                     # 获取2026年7月9日的数据
  python fetch_xwlb.py 20260709 -o my_data.json     # 指定输出文件名
  python fetch_xwlb.py 20260601                     # 获取2026年6月1日的数据
  python fetch_xwlb.py 20250101                     # 获取2025年1月1日的数据
        """
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="目标日期，格式为 YYYYMMDD（如 20260709）。不传则默认取昨天。支持1978年1月1日至今天的任意历史日期"
    )
    parser.add_argument(
        "-o", "--output",
        help=f"输出JSON文件路径（默认：xwlb_YYYYMMDD.json，保存在脚本所在目录）"
    )

    args = parser.parse_args()

    # 确定目标日期：未指定则默认取昨天
    if args.date:
        date_str = validate_date(args.date)
        if not date_str:
            logger.error("日期校验失败，脚本退出")
            sys.exit(1)
    else:
        yesterday = date.today() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        logger.info(f"未指定日期，默认取昨天：{date_str}")

    # 输出路径
    output_path = args.output if args.output else os.path.join(LOG_DIR, f"xwlb_{date_str}.json")

    # 星期几
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    weekday = weekday_names[target_date.weekday()]

    logger.info(f"目标日期：{date_str}（星期{weekday}）")
    logger.info(f"开始获取 {date_str} 的新闻联播视频列表")
    results = fetch_xwlb_list(date_str)

    if not results:
        logger.error("未获取到视频列表，请检查日期是否正确（如当天无播出、节假日等）")
        return

    logger.info(f"成功获取 {len(results)} 条视频")
    print()

    print("=" * 60)
    print("⚠️  警告：本脚本基于正则匹配提取，存在以下限制：")
    print("   1. 若央视网页面结构变更，可能遗漏条目")
    print("   2. 仅提取央视网数据，不含齐鲁网等第三方来源")
    print("   3. 输出数量不固定，以当天实际播出为准")
    print("   4. 请务必人工核对页面实际条目数，确认无遗漏")
    print("=" * 60)
    print()

    for i, r in enumerate(results, 1):
        safe_title = desensitize(r['title'])
        print(f"第{i}条:")
        print(f"  标题: {safe_title}")
        print(f"  时长: {r['duration']}")
        print(f"  URL:  {r['url']}")
        print()

    # 保存配置文件（JSON中也使用脱敏后标题）
    safe_results = [{"title": desensitize(r['title']), "duration": r['duration'], "url": r['url']} for r in results]
    config = save_config(safe_results, date_str, output_path)

    # 输出Markdown表格格式（便于直接复制到报告）
    print("\n=== Markdown 表格格式 ===\n")
    print("| 序号 | 时长 | 标题 | 视频地址 |")
    print("|------|------|------|----------|")
    for i, r in enumerate(results, 1):
        safe_title = desensitize(r['title'])
        print(f"| {i} | {r['duration']} | {safe_title} | {r['url']} |")
    print()
    print("注意：请将'完整版'条目单独列出，不纳入常规新闻序号。")
    print("提示：所有标题已自动执行脱敏处理（人名→占位符）。")

    logger.info(f"{date_str} 数据提取完成，共 {len(results)} 条")


if __name__ == '__main__':
    main()
