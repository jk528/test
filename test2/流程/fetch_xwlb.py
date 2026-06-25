#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
央视网新闻联播视频列表提取脚本（解决动态加载问题）
通过分析页面源码中的 script/json 数据，提取完整的视频列表
"""
import requests
import re
import json
import sys
from urllib.parse import unquote

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

    resp = requests.get(url, headers=headers, timeout=30)
    resp.encoding = 'utf-8'
    html = resp.text

    # 央视网页面中，视频列表通常以特定格式存储
    # 方法：从页面源码中提取所有包含 [视频] 标题 + 时长 + URL 的条目

    results = []

    # 匹配模式1：查找 <li> 内的完整视频条目
    # 央视网列表结构：
    # <li>
    #   <span class="time">HH:MM:SS</span>
    #   <a href="https://tv.cctv.com/.../VIDE...shtml">[视频]标题</a>
    # </li>
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

        # 清理标题
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        title = unquote(title)
        title = title.replace('[视频]', '').strip()
        title = re.sub(r'^完整版', '', title).strip()

        results.append({
            "title": title,
            "duration": duration,
            "url": video_url
        })

    # 如果上面的模式没匹配到，使用方法2：逐条提取
    if not results:
        # 提取所有视频URL
        url_pattern = re.compile(r'https://tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[^\s"<>]+\.shtml')
        all_urls = url_pattern.findall(html)
        unique_urls = list(dict.fromkeys(all_urls))

        # 提取所有 [视频]标题
        title_pattern = re.compile(r'\[视频\]([^<\n]+)')
        titles = title_pattern.findall(html)

        # 提取所有时长
        duration_pattern = re.compile(r'(\d{2}:\d{2}:\d{2})')
        durations = duration_pattern.findall(html)

        # 简单对齐（按顺序匹配）
        for i, video_url in enumerate(unique_urls):
            title = titles[i].strip() if i < len(titles) else ""
            duration = durations[i] if i < len(durations) else ""
            results.append({
                "title": title,
                "duration": duration,
                "url": video_url
            })

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
    print(f"配置文件已保存: {output_path}")
    return config


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "20260624"
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"xwlb_{date_str}.json"

    print(f"正在获取 {date_str} 的新闻联播视频列表...")
    results = fetch_xwlb_list(date_str)

    if not results:
        print("未获取到视频列表，请检查日期是否正确")
        return

    print(f"\n成功获取 {len(results)} 条视频:\n")
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


if __name__ == '__main__':
    main()
