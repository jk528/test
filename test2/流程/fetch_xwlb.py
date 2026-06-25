#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
央视网新闻联播视频列表提取脚本（解决动态加载问题）
通过分析页面源码中的 script/json 数据，提取完整的视频列表

版本：v1.1.0（2026-06-26）
变更：
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


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "20260624"
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"xwlb_{date_str}.json"

    logger.info(f"开始获取 {date_str} 的新闻联播视频列表")
    results = fetch_xwlb_list(date_str)

    if not results:
        logger.error("未获取到视频列表，请检查日期是否正确")
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
        print(f"第{i}条:")
        print(f"  标题: {r['title']}")
        print(f"  时长: {r['duration']}")
        print(f"  URL:  {r['url']}")
        print()

    # 保存配置文件
    config = save_config(results, date_str, output_path)

    # 输出Markdown表格格式（便于直接复制到报告）
    print("\n=== Markdown 表格格式 ===\n")
    print("| 序号 | 时长 | 标题 | 视频地址 |")
    print("|------|------|------|----------|")
    for i, r in enumerate(results, 1):
        print(f"| {i} | {r['duration']} | {r['title']} | {r['url']} |")
    print()
    print("注意：请将'完整版'条目单独列出，不纳入常规新闻序号。")

    logger.info(f"{date_str} 数据提取完成，共 {len(results)} 条")


if __name__ == '__main__':
    main()
