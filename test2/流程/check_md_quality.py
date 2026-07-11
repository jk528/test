#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MD file quality check script for news broadcast summaries.
Checks: 7-part structure, URL validity, section 6 table format, desensitization.

Version: v1.0.0 (2026-07-11)
Usage:
  python check_md_quality.py <file_path>              # Check single file
  python check_md_quality.py --dir <directory>        # Batch check directory
  python check_md_quality.py --test-desensitize        # Test desensitize function only
"""
import os
import re
import sys
import glob
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 7 required sections
REQUIRED_SECTIONS = [
    "## 一、基调概述",
    "## 二、新闻速览",
    "## 三、重点新闻详解",
    "## 四、联播快讯详解",
    "## 五、完整性检测与播放时间",
    "## 六、新闻六要素索引",
    "## 七、占位符统合信息",
]

# Section 6 required 10 columns
SECTION6_HEADER = "| 序号 | 新闻标题（可点击跳转） | 类别 | 时间 | 地点 | 新闻主体 | 事件 | 原因 | 方式 | 详细信息源链接 |"

# URLs to exclude from format checks (data source references, not content links)
EXCLUDE_URLS = [
    'https://tv.cctv.com/lm/xwlb/',
    'https://tv.cctv.com/',
    'https://v.iqilu.com/',
    'http://www.xinhuanet.com/',
    'https://www.cls.cn/',
    'https://www.chinanews.com/',
    'tv.cctv.com',
    'v.iqilu.com',
]


def check_file(filepath):
    """Check a single MD file, return list of issues."""
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    file_size_kb = os.path.getsize(filepath) / 1024
    
    # ── 1. File size check ──
    if file_size_kb < 10:
        issues.append(f"[CRITICAL] file_size: {file_size_kb:.1f}KB < 10KB")
    
    # ── 2. 7-part structure check ──
    for section in REQUIRED_SECTIONS:
        if section not in content:
            issues.append(f"[ERROR] missing_section: {section}")
    
    # ── 3. Section 6 table header check ──
    if "## 六、新闻六要素索引" in content:
        if SECTION6_HEADER not in content:
            s6_match = re.search(r'## 六[^\n]*\n\n.*?\n(\|.+\|)', content, re.DOTALL)
            actual_header = s6_match.group(1) if s6_match else "NOT FOUND"
            issues.append(f"[ERROR] section6_header_mismatch:\n  expected: {SECTION6_HEADER}\n  actual:   {actual_header}")
        
        s6_start = content.find("## 六、新闻六要素索引")
        if s6_start != -1:
            s6_block = content[s6_start:s6_start+500]
            header_match = re.search(r'(\|.+\|)', s6_block)
            if header_match:
                col_count = len(header_match.group(1).split('|')) - 2
                if col_count != 10:
                    issues.append(f"[ERROR] section6_column_count: {col_count} != 10")
    
    # ── 4. URL extraction and validation ──
    # Extract URLs ending with proper chars (exclude trailing ）, ，, etc.)
    all_urls = re.findall(r'https?://[^\s\)>",，）]+', content)
    
    # Content URLs only (exclude data source references)
    content_urls = []
    for u in all_urls:
        # Exclude bare domain URLs (e.g., https://tv.cctv.com without path)
        if u.rstrip('/') in ['https://tv.cctv.com', 'https://v.iqilu.com',
                               'http://tv.cctv.com', 'http://v.iqilu.com',
                               'tv.cctv.com', 'v.iqilu.com']:
            continue
        if any(u.startswith(ex) for ex in EXCLUDE_URLS):
            continue
        content_urls.append(u)
    
    # HTTP check (only content URLs)
    http_urls = [u for u in content_urls if u.startswith('http://')]
    for u in http_urls:
        issues.append(f"[WARNING] http_url: {u}")
    
    # 央视网 URL format (exclude root URLs)
    cctv_urls = [u for u in content_urls if 'tv.cctv.com' in u]
    malformed_cctv = [u for u in cctv_urls if not re.search(r'\.shtml$', u)]
    for u in malformed_cctv:
        issues.append(f"[WARNING] malformed_cctv_url: {u}")
    
    # 齐鲁网 URL format (exclude root URLs)
    iqilu_urls = [u for u in content_urls if 'v.iqilu.com' in u]
    malformed_iqilu = [u for u in iqilu_urls if not re.search(r'\.html$', u)]
    for u in malformed_iqilu:
        issues.append(f"[WARNING] malformed_iqilu_url: {u}")
    
    # ── 5. Desensitization check ──
    SENSITIVE_NAMES = [
        "\u4e60\u8fd1\u5e73",  # Xi Jinping
        "\u674e\u5f3a",        # Li Qiang
        "\u8d75\u4e50\u9645",  # Zhao Leji (corrected: \u9645=际)
        "\u97e9\u6b63",        # Han Zheng
        "\u666e\u4eac",        # Putin
        "\u7279\u6717\u666e",  # Trump
    ]
    for name in SENSITIVE_NAMES:
        if name in content:
            issues.append(f"[CRITICAL] sensitive_name_found: {name}")
    
    # ── 6. Double-tag check ──
    double_tags = re.findall(r'<u><u>[^<]+</u></u>', content)
    for dt in double_tags:
        issues.append(f"[ERROR] double_tag: {dt}")
    
    # ── 7. Adjacent duplicate placeholder check ──
    # Only flag if 3+ Chinese chars are repeated (avoid false positives like "抢收抢种")
    dup_placeholders = re.findall(r'([\u4e00-\u9fff]{3,})\1', content)
    for dp in dup_placeholders:
        issues.append(f"[ERROR] duplicate_placeholder: {dp}{dp}")
    
    # ── 8. Check "--" in section 6 news_subject column ──
    if "## 六、新闻六要素索引" in content:
        s6_content = content[content.find("## 六、新闻六要素索引"):]
        table_rows = re.findall(r'\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|([^|]+)\|', s6_content)
        dash_count = sum(1 for cell in table_rows if cell.strip() == '--' or cell.strip() == '"--"' or cell.strip() == '"\u2014"')
        total_rows = len(table_rows)
        if total_rows > 0:
            dash_ratio = dash_count / total_rows
            if dash_ratio > 0.3:
                issues.append(f"[WARNING] high_dash_ratio: {dash_count}/{total_rows} ({dash_ratio:.0%})")
    
    # ── 9. Check "完整版" should be present ──
    if "完整版" not in content:
        issues.append(f"[ERROR] missing_full_version_entry")
    
    # ── 10. Check section 4 has subsections ──
    if "## 四、联播快讯详解" in content:
        s4_content = content[content.find("## 四、联播快讯详解"):]
        if not re.search(r'### 4\.\d', s4_content):
            issues.append(f"[WARNING] section4_missing_subsections")
    
    # ── 11. Check N/D/M/K/X stats present in section 5 ──
    if "## 五、完整性检测与播放时间" in content:
        s5_content = content[content.find("## 五、完整性检测与播放时间"):]
        for stat in ['N=', 'D=', 'M=', 'K=', 'X=']:
            if stat not in s5_content:
                issues.append(f"[ERROR] missing_stat_{stat}")
    
    return issues, {
        'size_kb': file_size_kb,
        'total_urls': len(content_urls),
        'cctv_urls': len(cctv_urls),
        'iqilu_urls': len(iqilu_urls),
        'http_urls': len(http_urls),
        'lines': len(lines),
    }


def main():
    parser = argparse.ArgumentParser(description='MD quality check for news broadcast summaries')
    parser.add_argument('path', nargs='?', help='Single MD file to check')
    parser.add_argument('--dir', help='Directory to batch check')
    parser.add_argument('--test-desensitize', action='store_true', help='Test desensitize function only')
    args = parser.parse_args()
    
    # Test mode
    if args.test_desensitize:
        sys.path.insert(0, SCRIPT_DIR)
        from fetch_xwlb import desensitize
        tests = [
            ("basic", "\u65af\u5854\u9ed8\u5ba3\u5e03\u8f9e\u804c", "<u>\u82f1\u56fd\u9996\u76f8</u>\u5ba3\u5e03\u8f9e\u804c"),
            ("ab_dedup", "\u82f1\u56fd\u9996\u76f8\u65af\u5854\u9ed8\u5ba3\u5e03\u8f9e\u804c", "<u>\u82f1\u56fd\u9996\u76f8</u>\u5ba3\u5e03\u8f9e\u804c"),
            ("ba_dedup", "\u65af\u5854\u9ed8\u82f1\u56fd\u9996\u76f8\u5ba3\u5e03\u8f9e\u804c", "<u>\u82f1\u56fd\u9996\u76f8</u>\u5ba3\u5e03\u8f9e\u804c"),
            ("no_mark", "\u65af\u5854\u9ed8\u5ba3\u5e03\u8f9e\u804c", "\u82f1\u56fd\u9996\u76f8\u5ba3\u5e03\u8f9e\u804c", False),
            ("multi_name", "\u666e\u4eac\u4e0e\u7279\u6717\u666e\u901a\u8bdd", "<u>\u4fc4\u7f57\u65af\u603b\u7edf</u>\u4e0e<u>\u7f8e\u56fd\u603b\u7edf</u>\u901a\u8bdd"),
            ("no_match", "\u5168\u56fd\u4eba\u5927\u5e38\u59d4\u4f1a\u4e3e\u884c\u4f1a\u8bae", "\u5168\u56fd\u4eba\u5927\u5e38\u59d4\u4f1a\u4e3e\u884c\u4f1a\u8bae"),
        ]
        passed = 0
        for name, inp, expected, *mark in tests:
            m = mark[0] if mark else True
            result = desensitize(inp, mark=m)
            ok = result == expected
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'} | {name}: {inp!r} -> {result!r}")
        print(f"\n{'='*40}\nResult: {passed}/{len(tests)} passed")
        sys.exit(0 if passed == len(tests) else 1)
    
    # Determine files to check
    if args.path:
        files = [args.path]
    elif args.dir:
        files = sorted(glob.glob(os.path.join(args.dir, '新闻联播总结_*.md')))
    else:
        print("Usage: python check_md_quality.py <file|--dir <directory>|--test-desensitize>")
        sys.exit(1)
    
    if not files:
        print("No MD files found!")
        sys.exit(1)
    
    print(f"Checking {len(files)} file(s)\n")
    print("=" * 80)
    
    total_issues = 0
    critical_count = 0
    error_count = 0
    warning_count = 0
    fail_count = 0
    
    for filepath in files:
        issues, stats = check_file(filepath)
        basename = os.path.basename(filepath)
        
        if issues:
            fail_count += 1
            severity_counts = {}
            for issue in issues:
                tag = issue.split(']')[0] + ']'
                severity_counts[tag] = severity_counts.get(tag, 0) + 1
            
            sev_str = ' '.join(f'{k}{v}' for k, v in sorted(severity_counts.items()))
            print(f"\n{'!'*3} {basename} ({stats['size_kb']:.1f}KB, {stats['lines']}L)")
            print(f"    Issues: {sev_str}")
            for issue in issues:
                print(f"      {issue}")
                if '[CRITICAL]' in issue:
                    critical_count += 1
                elif '[ERROR]' in issue:
                    error_count += 1
                elif '[WARNING]' in issue:
                    warning_count += 1
            total_issues += len(issues)
        else:
            print(f"  OK  {basename} ({stats['size_kb']:.1f}KB, {stats['lines']}L, "
                  f"{stats['cctv_urls']}cctv + {stats['iqilu_urls']}iqilu urls)")
    
    print(f"\n{'='*80}")
    print(f"\nSUMMARY: {len(files)} file(s) checked")
    print(f"  PASS: {len(files) - fail_count}")
    print(f"  FAIL: {fail_count}")
    print(f"  Total issues: {total_issues} (CRITICAL:{critical_count} ERROR:{error_count} WARNING:{warning_count})")
    
    if critical_count > 0:
        print(f"\n  *** {critical_count} CRITICAL issues need immediate fix ***")
        sys.exit(1)
    elif error_count > 0:
        print(f"\n  *** {error_count} ERROR issues need fix ***")
        sys.exit(1)
    else:
        print(f"\n  All checks passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
