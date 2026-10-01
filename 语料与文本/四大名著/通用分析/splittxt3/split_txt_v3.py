#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT章节拆分工具 v3.4（去重+乱序修复+卷级感知+目录区检测+广告清理+全自动模式）
  - 双版本：Python版（命令行，本文件） + VBA版（split_txt_v3.bas，WPS/Excel/Word）
  - 以 splittxt2 多正则版为底本，增加去重与乱序修复能力
  - 全面覆盖 13 类问题场景（重复4类 + 乱序3类 + 结构6类）
  - 定位：TXT质量修复工具（上游：splittxt2 拆分；下游：彩读阅读/静读天下等阅读器）

【v3.4 新增（与VBA版对齐）】
  - 章号归一化：全角数字/空格/冒号→半角、压缩空格、清零宽字符、Tab→空格（仅用于匹配）
  - 目录区检测：文件前30%内连续≥10个短正文(≤2行)且章号递增 → 自动跳过去重/排序/拆分
  - 广告/垃圾行清理：7类规则（网址/站点推广/分页提示/求票求收藏/符号分隔线/手机提示/加入书架）
    默认启用，--no-ad-clean 关闭
  - CLI 6组合：去重 none/first/longest × 排序 none/sort（lis 仅兼容保留；双标题场景由目录区检测+清洁模式覆盖）
  - --clean N 双合并文件：同时生成 保留大于等于N_*.txt 和 清理小于N_*.txt
  - --auto 全自动：分析→自动决策去重/排序组合→自动判定清洁N值→一键输出
  - 报告总-分结构：【总】结论建议 + 【分】七维度明细

【已覆盖的问题场景】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、重复类问题
  1. 相邻双标题    —— 每章标题连续出现2次（目录式+正文式）
  2. 整块重复粘贴  —— 某段章节被多次复制粘贴
  3. 末尾重复块    —— 文件尾部又重复了前面的章节
  4. 卷间章号重复  —— 第一卷第一章 vs 第二卷第一章（章号相同但属于不同卷）

二、乱序类问题
  5. 重复导致乱序  —— 重复粘贴块导致章号来回跳
  6. 末尾回退乱序  —— 末尾重复块导致章号从大跳小
  7. 整体完全乱序  —— 文件拼接顺序完全错误

三、结构类问题
  8. 多卷/多部/多册  —— 存在卷/部/册等上级结构，每卷内章号重新编号
  9. 多轨目录      —— 文件中存在多套独立的章节体系（如目录区+正文区各一套）
  10. 多级嵌套      —— 卷→篇→章→节 多层嵌套结构（当前支持两级：卷+章）
  11. 无号章节      —— 序章/楔子/番外/尾声/后记 等无数字编号的章节
  12. 章号缺失      —— 中间缺章，章号不连续
  13. 格式混合      —— 阿拉伯数字+中文数字混合，不同单位词混合

【6种去重×排序组合】（去重 none/first/longest × 排序 none/sort）
  none    + none   — 文件干净无重复无乱序，仅拆分
  none    + sort   — 无重复但整体乱序，按章号重排
  first   + none   — 相邻双标题/简单重复，保留首次出现
  first   + sort   — 简单重复且乱序
  longest + none   — 整块重复，保留内容最长且不改顺序
  longest + sort   — 重复+乱序严重，最彻底（默认）★推荐
  （lis 已合并入 first+sort，仅兼容保留；相邻双标题由目录区检测+清洁模式覆盖）

【3种卷级处理模式】
  auto       — 自动检测：有卷结构则启用卷-章二级去重（默认）
  flat       — 强制扁平：忽略卷结构，所有章节按章号去重
  by_volume  — 按卷分目录：每卷独立子文件夹输出

【双版本说明】
  Python版（split_txt_v3.py）— 命令行使用，分析功能更详细，适合批量处理
  VBA版（split_txt_v3.bas）  — WPS/Excel/Word 中运行，图形化交互，与 splittxt2 用法一致

用法（Python版）:
  # 全自动模式（推荐：分析→自动决策→清洁输出一步到位）
  python split_txt_v3.py --src 小说.txt --auto

  # 深度分析（全面诊断所有问题，总-分结构报告）
  python split_txt_v3.py --src 小说.txt --analyze

  # 按章节拆分（默认 longest+sort）
  python split_txt_v3.py --src 小说.txt

  # 指定6组合之一
  python split_txt_v3.py --src 小说.txt --dedup first --sort none

  # 清洁模式：同时生成 保留大于等于N / 清理小于N 双合并文件
  python split_txt_v3.py --src 小说.txt --clean 100

  # 按卷分目录输出
  python split_txt_v3.py --src 小说.txt --volume-mode by_volume

  # 聚合拆分
  python split_txt_v3.py --src 小说.txt --chunk 40,3
"""

import re
import os
import sys
import time
import shutil
import argparse
from collections import defaultdict, OrderedDict

# ===========================================================================
# 中文数字转阿拉伯数字
# ===========================================================================
_CN_NUM = {
    '零': 0, '〇': 0, '○': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '百': 100, '千': 1000, '万': 10000, '亿': 100000000,
    '兩': 2, '两': 2, '壹': 1, '貳': 2, '贰': 2, '參': 3, '叁': 3,
    '肆': 4, '伍': 5, '陸': 6, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
    '拾': 10, '佰': 100, '仟': 1000, '萬': 10000, '億': 100000000,
    '廿': 20, '卅': 30, '卌': 40, '皕': 200,
}


def cn_to_int(s):
    """中文数字转阿拉伯数字"""
    s = s.strip()
    for i in range(10):
        s = s.replace(chr(0xFF10 + i), str(i))
    if s.isdigit():
        return int(s)

    total = 0
    section = 0
    current = 0
    last_digit = 0

    for ch in s:
        if ch not in _CN_NUM:
            continue
        val = _CN_NUM[ch]
        if val < 10:
            last_digit = val
        elif val == 10:
            current += last_digit * 10 if last_digit > 0 else 10
            last_digit = 0
        elif val == 100:
            current += last_digit * 100 if last_digit > 0 else 100
            last_digit = 0
        elif val == 1000:
            current += last_digit * 1000 if last_digit > 0 else 1000
            last_digit = 0
        elif val == 10000:
            if last_digit > 0:
                current += last_digit
                last_digit = 0
            section = (section + current) * 10000
            current = 0
        elif val == 100000000:
            if last_digit > 0:
                current += last_digit
                last_digit = 0
            total = (total + section + current) * 100000000
            section = 0
            current = 0

    if last_digit > 0:
        current += last_digit
    return total + section + current


# ===========================================================================
# 编码检测
# ===========================================================================
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read(8192)
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        return 'utf-16'
    for enc in ('utf-8', 'gbk', 'gb18030', 'big5'):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'


def read_text_auto(file_path, encoding_hint=None):
    if encoding_hint:
        with open(file_path, 'r', encoding=encoding_hint) as f:
            return f.read()
    enc = detect_encoding(file_path)
    with open(file_path, 'r', encoding=enc, errors='replace') as f:
        return f.read()


def write_text_utf8_nobom(file_path, text):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


# ===========================================================================
# 正则表达式库（多级别、多格式）
# ===========================================================================
_NUM = r'[0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]'

# 卷/部/册/篇 级标题正则
VOLUME_PATTERNS = [
    # 第N卷/部/册/篇/集/季
    (re.compile(r'^[ \t\u3000]*第(' + _NUM + r'+)(卷|部|册|篇|集|季)(?:[ \t\u3000：:]+(.*))?$'), 'vol_num', 'vol_unit'),
    # 第N卷 第N章 复合格式（同时匹配卷和章）
    (re.compile(r'^[ \t\u3000]*第(' + _NUM + r'+)(卷|部|册|篇)\s*第(' + _NUM + r'+)(章|回|节)(?:[ \t\u3000：:]+(.*))?$'), 'both', 'both'),
]

# 章节级标题正则（按优先级排列）
CHAPTER_PATTERNS = [
    # 1. 标准中文：第N章/回/节/卷 + 标题
    (re.compile(r'^[ \t\u3000]*第(' + _NUM + r'+)(章|回|节|卷)(?:[ \t\u3000：:]+(.*))?$'), 'standard'),
    # 2. 无"第"字：N章/回/节 + 标题
    (re.compile(r'^[ \t\u3000]*(' + _NUM + r'+)(章|回|节)(?:[ \t\u3000：:]+(.*))?$'), 'no_di'),
    # 3. 纯数字起始（3-4位数字开头）
    (re.compile(r'^[ \t\u3000]*([0-9０-９]{3,4})(?:[ \t\u3000：:]+(.*))?$'), 'pure_num'),
    # 4. 英文 Chapter
    (re.compile(r'^[ \t\u3000]*[Cc]hapter\s+([0-9０-９]+)(?:[ \t\u3000：:\.\-]+(.*))?$'), 'english'),
    # 5. 无号章节：序章/楔子/番外/尾声/引子/后记/终章/序言/前言/跋
    (re.compile(r'^[ \t\u3000]*(序章|楔子|尾声|番外|引子|后记|终章|序言|前言|跋)(?:[ \t\u3000：:]+(.*))?$'), 'no_num'),
]


# ===========================================================================
# v3.4 新增：章号归一化（移植自VBA版 NormalizeLineForMatch）
#   仅用于匹配，不影响输出原文
# ===========================================================================
def normalize_line_for_match(s):
    """全角数字/空格/冒号→半角、压缩连续空格、清零宽字符、Tab→空格"""
    r = s
    # 1. 全角数字 → 半角
    for i in range(10):
        r = r.replace(chr(0xFF10 + i), str(i))
    # 2. 全角空格 → 半角空格
    r = r.replace('\u3000', ' ')
    # 3. 全角冒号 → 半角冒号
    r = r.replace('：', ':')
    # 4. 清理零宽字符（U+200B-200D / FEFF）
    for z in ('\u200b', '\u200c', '\u200d', '\ufeff'):
        r = r.replace(z, '')
    # 5. Tab → 空格
    r = r.replace('\t', ' ')
    # 6. 压缩多个连续空格为一个
    r = re.sub(r' +', ' ', r)
    return r


# ===========================================================================
# v3.4 新增：广告/垃圾行清理（移植自VBA版 CleanAdLines，7类规则）
# ===========================================================================
_AD_PROMO_WORDS = ('记住本站', '收藏本站', '推荐收藏', '手机用户', '手机版',
                   '请访问', '永久域名', '最新地址', '笔趣阁', '顶点小说')
_AD_PAGE_WORDS = ('本章未完', '下一页继续', '点击下一页', '上一页', '下一页',
                  '返回目录', '加入书架', '加入书签')
_AD_BEG_WORDS = ('求月票', '求推荐', '求收藏', '求打赏', '感谢打赏', '感谢订阅')
_AD_DOMAIN_RE = re.compile(r'\.(com|net|cc|cn|org|info)([^0-9a-zA-Z]|$)', re.IGNORECASE)
_AD_SEP_CHARS = '*-=~·—＋+'


def clean_ad_lines(lines):
    """清理广告/垃圾行。返回 (清理后的行列表, 移除行数)"""
    result = []
    removed = 0
    for line in lines:
        t = line.strip()
        is_ad = False
        if not t:
            is_ad = False  # 空行保留
        elif ('http://' in t.lower() or 'https://' in t.lower()
              or 'www.' in t.lower()):
            is_ad = True  # 网址行
        elif len(t) < 40 and _AD_DOMAIN_RE.search(t):
            is_ad = True  # 含域名后缀的短行
        elif any(k in t for k in _AD_PROMO_WORDS):
            is_ad = True  # 站点推广语 / 手机端提示
        elif any(k in t for k in _AD_PAGE_WORDS):
            is_ad = True  # 分页提示 / 加入书架书签
        elif any(k in t for k in _AD_BEG_WORDS) and len(t) < 40:
            is_ad = True  # 求票求收藏短行
        elif len(t) >= 5 and t[0] in _AD_SEP_CHARS and all(c == t[0] for c in t):
            is_ad = True  # 纯符号分隔线
        if is_ad:
            removed += 1
        else:
            result.append(line)
    return result, removed


# ===========================================================================
# v3.4 新增：目录区检测（移植自VBA版 DetectTOC）
#   文件前30%内、连续≥min_toc_chapters个章节正文≤max_body_lines行且章号递增
#   → 判定为目录区，标记 is_toc=True（不参与去重/排序/拆分输出）
# ===========================================================================
def detect_toc(chapters, min_toc_chapters=10, max_body_lines=2):
    """检测并标记目录区章节，返回目录区章节数"""
    n = len(chapters)
    if n < min_toc_chapters:
        return 0

    toc_start = -1
    toc_count = 0
    in_toc = False
    consec = 0
    prev_num = 0
    chap_start = -1

    for i, ch in enumerate(chapters):
        if ch['level'] != 'chapter':
            continue
        body_ln = ch.get('body_lines', 0)

        if body_ln <= max_body_lines:
            # 正文很短，可能是目录项
            if not in_toc:
                # 检查是否在文件开头位置（前30%的章节内）
                if i > n * 0.3:
                    break
                chap_start = i
                consec = 1
                prev_num = ch['ch_num'] or 0
                in_toc = True
            else:
                cn = ch['ch_num'] or 0
                # 章号递增（目录通常是顺序的）
                if cn > prev_num or cn == 0:
                    consec += 1
                    prev_num = cn
                else:
                    # 章号回退，可能目录结束了
                    if consec >= min_toc_chapters:
                        toc_start = chap_start
                        toc_count = consec
                    in_toc = False
                    consec = 0
                    chap_start = -1
                    if toc_count > 0:
                        break
        else:
            # 正文足够长
            if in_toc:
                if consec >= min_toc_chapters:
                    toc_start = chap_start
                    toc_count = consec
                in_toc = False
                consec = 0
                chap_start = -1
                if toc_count > 0:
                    break

    # 循环结束时还在目录区中的情况
    if toc_count == 0 and in_toc and consec >= min_toc_chapters:
        toc_start = chap_start
        toc_count = consec

    # 标记目录区章节
    if toc_count > 0:
        for i in range(toc_start, toc_start + toc_count):
            chapters[i]['is_toc'] = True
    return toc_count


def get_body_hanzi_count(ch, lines):
    """章节正文汉字数（v3.5 优化：逐行计数，避免拼接大字符串）"""
    s_line = ch['line_idx']
    e_line = max(ch['end_line'], s_line)
    if e_line <= s_line:
        return 0
    # 逐行计数，避免拼接大字符串
    total = 0
    for line in lines[s_line + 1:e_line + 1]:
        total += len(re.findall(r'[一-鿿]', line))
    return total


def count_ooo(chapters):
    """统计章号回退（乱序）次数，仅统计 ch_num>0 的章节"""
    ooo = 0
    prev = 0
    for ch in chapters:
        if ch['ch_num'] <= 0:
            continue
        if prev > 0 and ch['ch_num'] < prev:
            ooo += 1
        prev = ch['ch_num']
    return ooo


def count_adj_dup(chapters):
    """统计相邻双标题数（同章号且行距≤2）"""
    adj = 0
    for i in range(1, len(chapters)):
        if (chapters[i]['ch_num'] == chapters[i - 1]['ch_num']
                and chapters[i]['ch_num'] > 0
                and chapters[i]['line_idx'] - chapters[i - 1]['line_idx'] <= 2):
            adj += 1
    return adj


def auto_decide(chapters):
    """v3.4 自动决策去重+排序组合（仅用 ch_num>0 且非目录区章节）
    返回 (dedup策略, sort策略, 判定理由)"""
    valid = [c for c in chapters if c['ch_num'] > 0 and not c.get('is_toc')]

    num_counts = defaultdict(int)
    for c in valid:
        num_counts[c['ch_num']] += 1
    dup_num_count = sum(1 for v in num_counts.values() if v > 1)  # 有重复的章号数
    ooo_count = count_ooo(valid)                                   # 章号回退次数
    adj_dup = count_adj_dup(valid)
    adj_ratio = adj_dup / len(valid) if valid else 0               # 相邻双标题占比

    # 决策表（按优先级）
    if dup_num_count == 0 and ooo_count == 0:
        return 'none', 'none', '无重复章号且无乱序，文件质量良好'
    if adj_ratio >= 0.3 and ooo_count < 10:
        return 'longest', 'none', f'相邻双标题占比{adj_ratio:.1%}≥30%且乱序{ooo_count}处<10'
    if ooo_count >= 10:
        return 'longest', 'sort', f'乱序{ooo_count}处≥10，需最彻底修复'
    if dup_num_count > 0:
        return 'longest', 'none', f'有{dup_num_count}个重复章号，保留最长内容且不改顺序'
    return 'longest', 'sort', '其余情况默认最彻底组合'


def auto_decide_n(chapters, lines):
    """v3.5 优化：自动判定清洁N值
    所有章节正文汉字数升序排序，下半区(≤中位数)找最大相邻间隔gap，
    N=间隔中点取整到10，clamp[50,1000]（上限锁死1000）；
    章节<20 或 gap<50 或 最大gap<次大gap×2 → N=100
    返回 (N, 判定理由)"""
    valid = [c for c in chapters if not c.get('is_toc')]
    counts = sorted(get_body_hanzi_count(c, lines) for c in valid)

    if len(counts) < 20:
        return 100, f'章节数{len(counts)}<20，使用默认值'

    median = counts[len(counts) // 2]
    lower = [c for c in counts if c <= median]
    if len(lower) < 2:
        return 100, '下半区数据不足，使用默认值'

    gaps = [(lower[i + 1] - lower[i], lower[i], lower[i + 1])
            for i in range(len(lower) - 1)]
    gaps.sort(key=lambda g: -g[0])
    max_gap, gap_lo, gap_hi = gaps[0]

    if max_gap < 50:
        return 100, f'下半区最大间隔{max_gap}<50，使用默认值'
    if len(gaps) > 1 and max_gap < gaps[1][0] * 2:
        return 100, f'最大间隔{max_gap}不显著(次大{gaps[1][0]}×2)，使用默认值'

    n = int(round((gap_lo + gap_hi) / 2 / 10.0)) * 10
    n = max(50, min(1000, n))
    return n, f'下半区最大间隔{gap_lo}~{gap_hi}字，取中点得N={n}'


def scan_structures(lines):
    """扫描所有层级结构（卷+章），返回结构化数据

    返回: chapters 列表，每个元素是 dict：
      {
        'line_idx': 行号,
        'title': 原始标题文本,
        'level': 'volume' | 'chapter' | 'special',
        'vol_num': 卷号 (int or None),
        'vol_unit': 卷单位词 (str or None),
        'ch_num': 章号 (int or None, special章节为0),
        'ch_unit': 章单位词 (str or None),
        'sub_title': 子标题 (str),
        'pattern_type': 匹配的正则类型,
      }
    """
    structures = []
    current_vol = None  # 当前卷号
    current_vol_unit = None
    current_vol_title = None

    for i, line in enumerate(lines):
        # v3.4：先归一化再匹配（仅影响匹配，title 仍取原始行）
        line_stripped = normalize_line_for_match(line).rstrip()
        if not line_stripped.strip():
            continue
        orig_title = line.strip()

        matched = False

        # 先尝试复合格式（卷+章在同一行）
        pat_both = VOLUME_PATTERNS[1][0]
        m = pat_both.match(line_stripped)
        if m:
            vol_num = cn_to_int(m.group(1))
            vol_unit = m.group(2)
            ch_num = cn_to_int(m.group(3))
            ch_unit = m.group(4)
            sub = m.group(5) or ''
            structures.append({
                'line_idx': i,
                'title': orig_title,
                'level': 'chapter',
                'vol_num': vol_num,
                'vol_unit': vol_unit,
                'ch_num': ch_num,
                'ch_unit': ch_unit,
                'sub_title': sub.strip(),
                'pattern_type': 'vol_ch_both',
            })
            # 更新当前卷
            current_vol = vol_num
            current_vol_unit = vol_unit
            matched = True
            continue

        # 再尝试卷级标题
        pat_vol = VOLUME_PATTERNS[0][0]
        m = pat_vol.match(line_stripped)
        if m:
            vol_num = cn_to_int(m.group(1))
            vol_unit = m.group(2)
            sub = m.group(3) or ''
            current_vol = vol_num
            current_vol_unit = vol_unit
            current_vol_title = m.group(0).strip()
            structures.append({
                'line_idx': i,
                'title': orig_title,
                'level': 'volume',
                'vol_num': vol_num,
                'vol_unit': vol_unit,
                'ch_num': None,
                'ch_unit': None,
                'sub_title': sub.strip(),
                'pattern_type': 'volume',
            })
            matched = True
            continue

        # 最后尝试章节级标题（按优先级）
        for pat, ptype in CHAPTER_PATTERNS:
            m = pat.match(line_stripped)
            if m:
                if ptype == 'standard':
                    ch_num = cn_to_int(m.group(1))
                    ch_unit = m.group(2)
                    sub = m.group(3) or ''
                elif ptype == 'no_di':
                    ch_num = cn_to_int(m.group(1))
                    ch_unit = m.group(2)
                    sub = m.group(3) or ''
                elif ptype == 'pure_num':
                    ch_num = cn_to_int(m.group(1))
                    ch_unit = '章'
                    sub = m.group(2) or ''
                elif ptype == 'english':
                    ch_num = cn_to_int(m.group(1))
                    ch_unit = 'Chapter'
                    sub = m.group(2) or ''
                elif ptype == 'no_num':
                    ch_num = 0  # 无号章节标记为0
                    ch_unit = '章'
                    sub = m.group(1) + ((' ' + m.group(2)) if m.group(2) else '')
                else:
                    continue

                level = 'special' if ptype == 'no_num' else 'chapter'
                structures.append({
                    'line_idx': i,
                    'title': orig_title,
                    'level': level,
                    'vol_num': current_vol,
                    'vol_unit': current_vol_unit,
                    'ch_num': ch_num,
                    'ch_unit': ch_unit,
                    'sub_title': sub.strip(),
                    'pattern_type': ptype,
                })
                matched = True
                break

    # 计算每个章节的结束行和正文字数
    for ci, s in enumerate(structures):
        if ci + 1 < len(structures):
            s['end_line'] = structures[ci + 1]['line_idx'] - 1
        else:
            s['end_line'] = len(lines) - 1
        s['body_lines'] = max(0, s['end_line'] - s['line_idx'])

    return structures


def get_chapters_only(structures):
    """从结构列表中提取章节（chapter + special），用于去重处理"""
    return [s for s in structures if s['level'] in ('chapter', 'special')]


def get_volumes(structures):
    """提取卷级结构"""
    return [s for s in structures if s['level'] == 'volume']


# ===========================================================================
# 去重策略（支持卷级感知 + 标题级去重）
# ===========================================================================

def _normalize_title(title):
    """标题规范化：用于标题级去重时的键
    处理：全角半角统一、空白压缩、标点清理、转小写
    """
    import re
    if not title:
        return ''
    t = title.strip()
    # 全角数字 → 半角
    full_digits = '０１２３４５６７８９'
    for i, d in enumerate(full_digits):
        t = t.replace(d, str(i))
    # 全角字母 → 半角（常见的）
    full_alpha_lower = 'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ'
    full_alpha_upper = 'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ'
    for i, c in enumerate(full_alpha_lower):
        t = t.replace(c, chr(ord('a') + i))
    for i, c in enumerate(full_alpha_upper):
        t = t.replace(c, chr(ord('A') + i))
    # 全角空格、全角冒号 → 半角
    t = t.replace('\u3000', ' ').replace('：', ':')
    # 零宽字符
    for z in ['\u200b', '\u200c', '\u200d', '\ufeff']:
        t = t.replace(z, '')
    # 压缩空白
    t = re.sub(r'\s+', '', t)
    # 移除常见标点符号
    t = re.sub('[' + re.escape('，。、；：""''（）《》【】「」『』！？·…—_,.;:""\'\'()[]<>!-') + ']', '', t)
    # 转小写
    t = t.lower()
    return t


def _dedup_key(ch, volume_mode, title_dedup=False):
    """生成去重用的唯一键
    title_dedup=True 时，键包含规范化标题，避免章号相同但标题不同的章节被误判为重复
    """
    base = []
    if volume_mode == 'flat' or ch.get('vol_num') is None:
        base = ['flat', ch['ch_num'], ch.get('ch_unit', '')]
    else:
        base = [ch['vol_num'], ch['ch_num'], ch.get('ch_unit', '')]
    
    if title_dedup and ch['ch_num'] > 0:
        base.append(_normalize_title(ch.get('title', '')))
    
    return tuple(base)


def dedup_first(chapters, volume_mode='auto', title_dedup=False):
    """策略1：保留首次出现"""
    seen = set()
    result = []
    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            # 无号章节：按标题去重
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode, title_dedup)
        if key not in seen:
            seen.add(key)
            result.append(ch)
    return result


def dedup_longest(chapters, volume_mode='auto', title_dedup=False):
    """策略2：保留内容最长的"""
    best = OrderedDict()
    order = []

    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode, title_dedup)

        if key not in best:
            best[key] = ch
            order.append(key)
        else:
            if ch['body_lines'] > best[key]['body_lines']:
                best[key] = ch

    return [best[k] for k in order]


def dedup_lis(chapters, volume_mode='auto', title_dedup=False):
    """策略4：最长递增子序列（LIS）
    支持卷级感知：同一卷内章号递增，跨卷时卷号也递增
    注意：LIS排序基于章号，标题去重不影响排序逻辑
    """
    # 先按去重键去重（保留首次出现），再做LIS
    if title_dedup:
        seen = {}
        unique_chapters = []
        for ch in chapters:
            if ch['ch_num'] <= 0 and ch['level'] == 'special':
                key = ('special', ch['title'])
            else:
                key = _dedup_key(ch, volume_mode, title_dedup)
            if key not in seen:
                seen[key] = True
                unique_chapters.append(ch)
        chapters = unique_chapters
    
    # 构造排序键：(卷号, 章号)
    def sort_key(ch):
        vol = ch.get('vol_num') or 0
        cn = ch['ch_num'] if ch['ch_num'] > 0 else -1  # 无号章节放前面
        return (vol, cn)

    valid = [(i, ch) for i, ch in enumerate(chapters)
             if ch['level'] in ('chapter', 'special')]
    if not valid:
        return []

    n = len(valid)
    tails_val = []
    indices = []
    prev = [-1] * n

    for i, (orig_idx, ch) in enumerate(valid):
        key = sort_key(ch)
        # 严格递增：找第一个 >= key 的位置
        left, right = 0, len(tails_val)
        while left < right:
            mid = (left + right) // 2
            if tails_val[mid] < key:
                left = mid + 1
            else:
                right = mid

        pos = left
        if pos == len(tails_val):
            tails_val.append(key)
            indices.append(i)
        else:
            tails_val[pos] = key
            indices[pos] = i

        if pos > 0:
            prev[i] = indices[pos - 1]

    lis_indices = []
    curr = indices[-1] if indices else -1
    while curr != -1:
        lis_indices.append(curr)
        curr = prev[curr]
    lis_indices.reverse()

    return [valid[i][1] for i in lis_indices]


def dedup_sort(chapters, volume_mode='auto', title_dedup=False):
    """策略5：按（卷号,章号）重新排序"""
    best = OrderedDict()

    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode, title_dedup)

        if key not in best:
            best[key] = ch
        else:
            if ch['body_lines'] > best[key]['body_lines']:
                best[key] = ch

    # 排序：special章节按出现顺序排前面，然后按(卷,章)排
    specials = [v for k, v in best.items() if k[0] == 'special']
    normals = [v for k, v in best.items() if k[0] != 'special']

    def normal_key(ch):
        vol = ch.get('vol_num') or 0
        cn = ch['ch_num'] if ch['ch_num'] > 0 else 999999
        return (vol, cn)

    normals.sort(key=normal_key)
    return specials + normals


DEDUP_STRATEGIES = {
    'none': None,
    'first': dedup_first,
    'longest': dedup_longest,
}

SORT_STRATEGIES = {
    'none': None,
    'lis': dedup_lis,
    'sort': dedup_sort,
}


# ===========================================================================
# 深度分析报告（v3.4：总-分结构，返回报告文本，print 由调用方做）
# ===========================================================================
def load_and_scan(file_path, encoding=None, ad_clean=True):
    """读取→(可选)广告清理→扫描→目录区检测
    返回 (lines, structures, chapters, volumes, toc_count, ad_removed, enc)"""
    if encoding:
        enc = encoding.upper()
        content = read_text_auto(file_path, encoding)
    else:
        enc = detect_encoding(file_path)
        content = read_text_auto(file_path)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')

    ad_removed = 0
    if ad_clean:
        lines, ad_removed = clean_ad_lines(lines)

    structures = scan_structures(lines)
    chapters = get_chapters_only(structures)
    volumes = get_volumes(structures)
    toc_count = detect_toc(chapters)
    return lines, structures, chapters, volumes, toc_count, ad_removed, enc


def deep_analyze(file_path, encoding=None, ad_clean=False):
    """深度分析：全面诊断所有问题。返回报告文本（总-分结构）"""
    out = []
    p = out.append

    lines, structures, chapters_all, volumes, toc_count, ad_removed, enc = \
        load_and_scan(file_path, encoding, ad_clean)
    content_len = sum(len(l) for l in lines) + len(lines)

    # 目录区章节不参与分析
    chapters = [c for c in chapters_all if not c.get('is_toc')]

    # ---------- 预计算汇总指标（供【总】使用） ----------
    vol_nums = set(v['vol_num'] for v in volumes if v['vol_num'])

    flat_map = defaultdict(list)
    for ch in chapters:
        if ch['ch_num'] > 0:
            flat_map[ch['ch_num']].append(ch)
    dup_flat = {k: v for k, v in flat_map.items() if len(v) > 1}
    dup_num_count = len(dup_flat)                          # 重复章号数
    dup_copies = sum(len(v) - 1 for v in dup_flat.values())  # 重复份数

    title_diff_count = 0
    title_diff_list = []
    for num_val, occ_list in flat_map.items():
        if len(occ_list) <= 1:
            continue
        norm_titles = set(_normalize_title(c.get('title', '')) for c in occ_list)
        if len(norm_titles) > 1:
            title_diff_count += 1
            title_diff_list.append((num_val, len(occ_list), sorted(norm_titles)))

    valid_chs = [ch for ch in chapters if ch['ch_num'] > 0]
    ooo_count = 0
    max_drop = 0
    max_drop_info = None
    prev_num = 0
    for ch in valid_chs:
        if ch['ch_num'] < prev_num:
            ooo_count += 1
            drop = prev_num - ch['ch_num']
            if drop > max_drop:
                max_drop = drop
                max_drop_info = (prev_num, ch['ch_num'], ch['line_idx'] + 1)
        prev_num = ch['ch_num']

    adj_dup = count_adj_dup(chapters)
    adj_ratio = adj_dup / len(chapters) if chapters else 0

    # 推荐组合 + 建议清洁N值
    rec_dedup, rec_sort, rec_reason = auto_decide(chapters)
    rec_n, rec_n_reason = auto_decide_n(chapters, lines)

    # ========== 【总】结论与建议 ==========
    p("=" * 70)
    p(f"  深度分析报告: {os.path.basename(file_path)}")
    p("=" * 70)
    p("【总】结论与建议")
    p(f"  问题计数: 卷结构{len(vol_nums)}个 / 重复章号{dup_num_count}个(共{dup_copies}份) / "
      f"乱序{ooo_count}处(最大跌{max_drop}) / 同章异题{title_diff_count}个 / "
      f"目录区{toc_count}章 / 相邻双标题占比{adj_ratio:.1%}")
    p(f"  推荐组合: --dedup {rec_dedup} --sort {rec_sort}  （{rec_reason}）")
    p(f"  建议清洁N值: {rec_n}  （{rec_n_reason}）")
    if ad_removed > 0:
        p(f"  广告清理: 已移除垃圾行 {ad_removed} 行（--no-ad-clean 可关闭）")
    p("")

    # ========== 【分】详细分析 ==========
    p("【分】详细分析")
    p(f"总行数: {len(lines):,}   总字符: {content_len:,}   编码: {enc}")
    p(f"识别结构: 卷级 {len(volumes)} 个, 章节级 {len(chapters_all)} 个"
      + (f"（其中目录区 {toc_count} 章，已跳过）" if toc_count > 0 else ""))
    p("")

    # ---------- 1. 卷结构分析 ----------
    p("-" * 50)
    p("【一、卷/部结构分析】")
    if volumes:
        p(f"  卷级标题数: {len(volumes)}")
        vol_units = set(v['vol_unit'] for v in volumes if v['vol_unit'])
        if vol_nums:
            p(f"  卷号范围: {min(vol_nums)} - {max(vol_nums)}")
        p(f"  卷单位词: {', '.join(sorted(vol_units))}")

        vol_chapter_counts = defaultdict(int)
        current_vol = None
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
            elif s['level'] in ('chapter', 'special'):
                vol_chapter_counts[current_vol] += 1

        p(f"  各卷章节数:")
        for vol_num in sorted(vol_chapter_counts.keys(), key=lambda x: (x is None, x or 0)):
            vol_label = f"第{vol_num}卷" if vol_num else "无卷"
            p(f"    {vol_label}: {vol_chapter_counts[vol_num]} 章")

        # 卷间章号重复检测
        common = set()
        if len(vol_nums) > 1:
            vol_chs = defaultdict(set)
            current_vol = None
            for s in structures:
                if s['level'] == 'volume':
                    current_vol = s['vol_num']
                elif s['level'] == 'chapter' and s['ch_num'] > 0:
                    vol_chs[current_vol].add(s['ch_num'])

            vol_list = sorted(vol_chs.keys(), key=lambda x: (x is None, x or 0))
            if len(vol_list) >= 2:
                common = vol_chs[vol_list[0]] & vol_chs[vol_list[1]]
                if common:
                    p(f"\n  ⚠ 卷间章号重复: 第{vol_list[0]}卷 和 第{vol_list[1]}卷 共享 {len(common)} 个章号")
                    p(f"    示例重复章号: {sorted(list(common))[:10]}...")
    else:
        p("  未检测到卷/部/册级结构")

    # ---------- 2. 重复分析 ----------
    p("")
    p("-" * 50)
    p("【二、重复章节分析】")

    unique_flat = len(flat_map)
    p(f"  扁平视角（忽略卷）:")
    p(f"    不重复章号数: {unique_flat}")
    p(f"    存在重复的章号数: {dup_num_count}")

    if dup_flat:
        sorted_dups = sorted(dup_flat.items(), key=lambda x: -len(x[1]))
        p(f"\n    重复最严重的前10个章号：")
        for num_val, occ_list in sorted_dups[:10]:
            count = len(occ_list)
            lines_str = '、'.join(str(c['line_idx'] + 1) for c in occ_list[:5])
            full_title = occ_list[0]['title']
            p(f"      第{num_val}章 ({count}次): {full_title}")
            p(f"        出现行号: {lines_str}")

        count_dist = defaultdict(int)
        for occ_list in dup_flat.values():
            count_dist[len(occ_list)] += 1
        p(f"\n    重复次数分布：")
        for cnt in sorted(count_dist.keys()):
            p(f"      出现{cnt}次的章号: {count_dist[cnt]}个")

    if title_diff_count > 0:
        p(f"\n  ⚠ 章号相同但标题不同: {title_diff_count} 个章号")
        p(f"    （说明同一章号下有不同标题，仅按章号去重可能误删）")
        p(f"    建议开启 --title-dedup 启用标题级去重")
        p(f"\n    完整列表：")
        for num_val, cnt, titles in title_diff_list:
            p(f"      第{num_val}章（{len(titles)}个不同标题）:")
            for t in titles:
                p(f"        · {t}")

    # 卷感知去重统计
    if volumes:
        vol_aware_map = defaultdict(list)
        for ch in chapters:
            if ch['ch_num'] > 0:
                key = (ch.get('vol_num'), ch['ch_num'])
                vol_aware_map[key].append(ch)
        dup_vol_aware = {k: v for k, v in vol_aware_map.items() if len(v) > 1}
        p(f"\n  卷感知视角（同卷内才算重复）:")
        p(f"    卷-章组合数: {len(vol_aware_map)}")
        p(f"    同卷内重复数: {len(dup_vol_aware)}")

    # ---------- 3. 乱序分析 ----------
    p("")
    p("-" * 50)
    p("【三、乱序分析】")

    p(f"  扁平视角（忽略卷）:")
    p(f"    乱序次数: {ooo_count}")
    if max_drop_info:
        p(f"    最大跌幅: 第{max_drop_info[0]}章 → 第{max_drop_info[1]}章 (跌{max_drop}, 行{max_drop_info[2]})")

    if volumes:
        p(f"\n  卷内视角（每卷单独统计）:")
        vol_ooo = defaultdict(int)
        vol_max_drop = defaultdict(lambda: (0, 0, 0))
        current_vol = None
        prev_ch = 0
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
                prev_ch = 0
            elif s['level'] == 'chapter' and s['ch_num'] > 0 and not s.get('is_toc'):
                if s['ch_num'] < prev_ch:
                    vol_ooo[current_vol] += 1
                    drop = prev_ch - s['ch_num']
                    if drop > vol_max_drop[current_vol][0]:
                        vol_max_drop[current_vol] = (drop, prev_ch, s['ch_num'])
                prev_ch = s['ch_num']

        for vol_num in sorted(vol_ooo.keys(), key=lambda x: (x is None, x or 0)):
            vol_label = f"第{vol_num}卷" if vol_num else "无卷"
            drop_info = vol_max_drop[vol_num]
            p(f"    {vol_label}: 乱序{vol_ooo[vol_num]}处, 最大跌{drop_info[0]} (第{drop_info[1]}→第{drop_info[2]}章)")

    # ---------- 4. 多轨目录检测 ----------
    p("")
    p("-" * 50)
    p("【四、多轨目录检测】")

    if toc_count > 0:
        toc_chs = [c for c in chapters_all if c.get('is_toc')]
        p(f"  ⚠ 检测到目录区（已自动跳过，不参与去重/排序/拆分）")
        p(f"    目录章节数: {toc_count} 章")
        p(f"    起始标题: {toc_chs[0]['title']}")
    else:
        p(f"  未检测到独立目录区")

    p(f"  相邻双标题数: {adj_dup} (占比 {adj_ratio:.1%})")
    if adj_ratio > 0.3:
        p(f"  → 疑似每章双标题结构（目录式+正文式各一次）")

    if len(valid_chs) > 10:
        seq_len = 1
        max_seq = 1
        for i in range(1, len(valid_chs)):
            if valid_chs[i]['ch_num'] == valid_chs[i - 1]['ch_num'] + 1:
                seq_len += 1
                max_seq = max(max_seq, seq_len)
            else:
                seq_len = 1
        p(f"  最长连续递增章号段长度: {max_seq}")

    # ---------- 5. 格式多样性分析 ----------
    p("")
    p("-" * 50)
    p("【五、格式多样性分析】")

    pattern_counts = defaultdict(int)
    unit_counts = defaultdict(int)
    for ch in chapters:
        pattern_counts[ch['pattern_type']] += 1
        if ch.get('ch_unit'):
            unit_counts[ch['ch_unit']] += 1

    p(f"  正则类型分布:")
    for ptype, cnt in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        p(f"    {ptype:15s}: {cnt:4d} 章 ({cnt / len(chapters) * 100:.1f}%)")

    p(f"  单位词分布:")
    for unit, cnt in sorted(unit_counts.items(), key=lambda x: -x[1]):
        p(f"    {unit:6s}: {cnt:4d} 章")

    special_chs = [ch for ch in chapters if ch['level'] == 'special']
    if special_chs:
        p(f"  无号章节（序章/楔子/番外等）: {len(special_chs)} 个")
        for ch in special_chs[:10]:
            p(f"    行{ch['line_idx'] + 1}: {ch['title'][:40]}")
        if len(special_chs) > 10:
            p(f"    ... 共 {len(special_chs)} 个")

    # ---------- 6. 连续性分析 ----------
    p("")
    p("-" * 50)
    p("【六、章号连续性分析】")

    if volumes:
        vol_chs = defaultdict(list)
        current_vol = None
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
            elif s['level'] == 'chapter' and s['ch_num'] > 0 and not s.get('is_toc'):
                vol_chs[current_vol].append(s['ch_num'])

        for vol_num in sorted(vol_chs.keys(), key=lambda x: (x is None, x or 0)):
            nums = sorted(set(vol_chs[vol_num]))
            if not nums:
                continue
            vol_label = f"第{vol_num}卷" if vol_num else "无卷"
            min_n, max_n = min(nums), max(nums)
            expected = max_n - min_n + 1
            actual = len(nums)
            missing = expected - actual
            p(f"  {vol_label}: {min_n}-{max_n}章, 应有{expected}章, 实有{actual}章, 缺{missing}章")
    else:
        nums = sorted(set(ch['ch_num'] for ch in chapters if ch['ch_num'] > 0))
        if nums:
            min_n, max_n = min(nums), max(nums)
            expected = max_n - min_n + 1
            missing = expected - len(nums)
            p(f"  章号范围: {min_n} - {max_n}")
            p(f"  应有章节数: {expected}")
            p(f"  实际章号数: {len(nums)}")
            p(f"  缺失章号数: {missing}")

            if missing > 0 and missing < 100:
                full_set = set(nums)
                missing_list = [n for n in range(min_n, max_n + 1) if n not in full_set]
                p(f"  缺失章号: {missing_list[:30]}")
                if len(missing_list) > 30:
                    p(f"    ... 共{len(missing_list)}个")

    # ---------- 7. 各组合效果预览 ----------
    p("")
    p("-" * 50)
    p("【七、6组合效果预览（扁平模式）】")

    title_dedup = True
    combos = [
        ("none+none",    "none",    "none"),
        ("none+sort",    "none",    "sort"),
        ("first+none",   "first",   "none"),
        ("first+sort",   "first",   "sort"),
        ("longest+none", "longest", "none"),
        ("longest+sort", "longest", "sort"),
    ]

    def _run_combo(chs, dedup_name, sort_name, vol_mode):
        result = chs
        if dedup_name != 'none':
            result = DEDUP_STRATEGIES[dedup_name](result, vol_mode, title_dedup=title_dedup)
        if sort_name != 'none':
            result = SORT_STRATEGIES[sort_name](result, vol_mode, title_dedup=title_dedup)
        return result

    for label, dedup_name, sort_name in combos:
        try:
            result = _run_combo(chapters, dedup_name, sort_name, 'flat')
            ooo_after = count_ooo(result)
            p(f"  {label:14s}: 剩{len(result):4d}章, 乱序{ooo_after:4d}处")
        except Exception as e:
            p(f"  {label:14s}: 错误 - {e}")

    if volumes:
        p(f"\n  【卷感知模式】")
        for label, dedup_name, sort_name in combos:
            try:
                result = _run_combo(chapters, dedup_name, sort_name, 'auto')
                ooo_after = 0
                prev_vol = None
                prev_ch = 0
                for ch in result:
                    if ch['ch_num'] <= 0:
                        continue
                    v = ch.get('vol_num')
                    if v == prev_vol and ch['ch_num'] < prev_ch:
                        ooo_after += 1
                    prev_vol = v
                    prev_ch = ch['ch_num']
                p(f"  {label:14s}: 剩{len(result):4d}章, 卷内乱序{ooo_after:3d}处")
            except Exception as e:
                p(f"  {label:14s}: 错误 - {e}")

    # ---------- 8. 建议 ----------
    p("")
    p("=" * 70)
    p("  处理建议：")

    suggestions = []
    if volumes and len(vol_nums) > 1 and common:
        suggestions.append("• 检测到多卷结构且卷间章号重复，建议启用卷感知模式")
        suggestions.append("  （--volume-mode auto 或 by_volume）")

    if ooo_count > 10 and dup_flat:
        suggestions.append("• 重复+乱序都严重，推荐 --dedup longest --sort sort（最彻底）")
    elif ooo_count > 10:
        suggestions.append("• 乱序严重，推荐 --dedup none --sort sort（按章号重排）")
    elif dup_flat:
        suggestions.append("• 有重复但乱序轻微，推荐 --dedup longest --sort none（保留最长且不改顺序）")

    if adj_ratio > 0.3:
        suggestions.append("• 每章双标题明显，推荐 --dedup longest --sort none")

    if not suggestions:
        suggestions.append("• 文件质量较好，可根据需要选择组合")

    suggestions.append(f"• 一键处理：--auto 自动完成分析+决策+清洁输出")

    for s in suggestions:
        p(f"  {s}")

    p("=" * 70)
    return '\n'.join(out)


# ===========================================================================
# 文件名工具
# ===========================================================================
def sanitize_filename(name):
    s = name.replace(' ', '\u3000')
    for c in '\\/:*?"<>|':
        s = s.replace(c, '\u3000')
    while '\u3000\u3000' in s:
        s = s.replace('\u3000\u3000', '\u3000')
    s = s.strip()
    if not s:
        s = 'untitled'
    return s[:60]


def format_range(ch_start, ch_end, unit):
    if ch_start == ch_end:
        return f"第{ch_start}{unit}"
    return f"第{ch_start}-{ch_end}{unit}"


# ===========================================================================
# 拆分函数
# ===========================================================================
def split_by_chapter(src, out_dir="", prefix="", serial_width=3, encoding=None,
                     dedup_strategy='longest', sort_strategy='sort', volume_mode='auto',
                     generate_title_only=False, min_body_len=0, merge_flag=None,
                     title_dedup=True, ad_clean=False, merge_dir=None):
    """按章节一一拆分"""
    t_total0 = time.time()

    # 1. 读取 + 广告清理 + 扫描 + 目录区检测
    t0 = time.time()
    lines, structures, all_chapters_raw, volumes, toc_count, ad_removed, enc = \
        load_and_scan(src, encoding, ad_clean)
    t_read = time.time() - t0
    print(f"编码: {enc}")
    print(f"源文件: {src}")
    print(f"总行数: {len(lines):,}")
    if ad_clean:
        print(f"广告清理: 移除垃圾行 {ad_removed} 行")

    # 2. 目录区章节不参与去重/排序/拆分输出
    t_scan = time.time() - t0
    all_chapters = [c for c in all_chapters_raw if not c.get('is_toc')]
    print(f"识别结构: 卷级 {len(volumes)} 个, 章节级 {len(all_chapters_raw)} 个"
          + (f"（其中目录区 {toc_count} 章，已跳过）" if toc_count > 0 else ""))

    # 3. 确定卷模式
    if volume_mode == 'auto':
        if volumes and len(set(v['vol_num'] for v in volumes if v['vol_num'])) > 1:
            actual_vol_mode = 'volume'
            print(f"卷模式: 自动检测 → 卷感知（检测到多卷结构）")
        else:
            actual_vol_mode = 'flat'
            print(f"卷模式: 自动检测 → 扁平（未检测到多卷）")
    elif volume_mode == 'flat':
        actual_vol_mode = 'flat'
        print(f"卷模式: 强制扁平")
    elif volume_mode == 'by_volume':
        actual_vol_mode = 'volume'
        print(f"卷模式: 按卷分目录")
    else:
        actual_vol_mode = 'flat'

    # 4. 去重
    chapters = all_chapters
    chapters_before_dedup = len(chapters)
    t0 = time.time()
    if dedup_strategy != 'none':
        dedup_func = DEDUP_STRATEGIES.get(dedup_strategy)
        if dedup_func is None:
            print(f"[错误] 未知去重策略: {dedup_strategy}")
            sys.exit(1)
        chapters = dedup_func(chapters, actual_vol_mode, title_dedup=title_dedup)
        print(f"去重策略: {dedup_strategy}" + (" + 标题去重" if title_dedup else ""))
    else:
        print(f"去重策略: none（不处理）")
    t_dedup = time.time() - t0
    dedup_removed = chapters_before_dedup - len(chapters)
    print(f"去重后章节: {len(chapters)}")

    # 4b. 排序
    ooo_before_sort = count_ooo(chapters)
    t0 = time.time()
    if sort_strategy != 'none':
        sort_func = SORT_STRATEGIES.get(sort_strategy)
        if sort_func is None:
            print(f"[错误] 未知排序策略: {sort_strategy}")
            sys.exit(1)
        chapters = sort_func(chapters, actual_vol_mode, title_dedup=title_dedup)
        print(f"排序策略: {sort_strategy}")
    else:
        print(f"排序策略: none（保持原文顺序）")
    t_sort = time.time() - t0
    ooo_after_sort = count_ooo(chapters)
    ooo_fixed = ooo_before_sort - ooo_after_sort
    print(f"排序后章节: {len(chapters)}")

    if not chapters:
        print("无有效章节，终止")
        sys.exit(1)

    # 5. 输出目录
    if volume_mode == 'by_volume' and actual_vol_mode == 'volume':
        base_out = resolve_output_dir(src, out_dir, "_拆分")
        clean_output_dir(base_out)
        print(f"输出根目录: {base_out}")
        out_dir = base_out
    else:
        out_dir = resolve_output_dir(src, out_dir, "_拆分")
        clean_output_dir(out_dir)
        print(f"输出目录: {out_dir}")

    # 6. 序号位数
    serial_width = max(serial_width, len(str(len(chapters))))

    # 7. 预计算字数（v3.5 优化：逐行累加，避免拼接大字符串）
    char_counts = []
    for ch in chapters:
        s_line = ch['line_idx']
        e_line = ch['end_line']
        if e_line < s_line:
            e_line = s_line
        n = e_line - s_line + 1
        total = sum(len(lines[k]) for k in range(s_line, e_line + 1))
        if n > 1:
            total += n - 1  # 换行符数
        char_counts.append(total)
    max_chars = max(char_counts) if char_counts else 0
    char_width = max(1, len(str(max_chars)))

    # 8. 写文件
    title_only_count = 0
    short_body_count = 0
    skipped_count = 0
    written_count = 0
    skipped_body_lens = []
    kept_texts = []
    skipped_texts = []
    skipped_chapters_list = []

    t0 = time.time()
    for idx, ch in enumerate(chapters):
        start_line = ch['line_idx']
        end_line = ch['end_line']
        if end_line < start_line:
            end_line = start_line
        n_lines = end_line - start_line + 1

        body = '\n'.join(lines[start_line:end_line + 1])

        # v3.5 优化：正文汉字数（逐行计数，避免拼接大字符串）
        if n_lines > 1:
            body_len = sum(len(re.findall(r'[一-鿿]', line))
                          for line in lines[start_line + 1:end_line + 1])
        else:
            body_len = 0

        is_insufficient = False
        if n_lines == 1:
            title_only_count += 1
            is_insufficient = True
        elif min_body_len > 0 and body_len < min_body_len:
            short_body_count += 1
            is_insufficient = True

        if is_insufficient and not generate_title_only:
            skipped_count += 1
            skipped_body_lens.append(body_len)
            if merge_flag is not None:
                skipped_chapters_list.append((ch['title'], body_len))
                skipped_texts.append(body)
            continue

        safe_title = sanitize_filename(ch['title'])
        serial = str(written_count + 1).zfill(serial_width)
        char_cnt = str(char_counts[idx]).zfill(char_width)

        # 确定文件路径（by_volume模式下分子目录）
        if volume_mode == 'by_volume' and actual_vol_mode == 'volume' and ch.get('vol_num'):
            vol_dir = f"第{ch['vol_num']}{ch.get('vol_unit', '卷')}"
            vol_dir = sanitize_filename(vol_dir)
            file_dir = os.path.join(out_dir, vol_dir)
            os.makedirs(file_dir, exist_ok=True)
        else:
            file_dir = out_dir

        if prefix:
            fname = f"{prefix}_{serial}_{char_cnt}_{safe_title}.txt"
        else:
            fname = f"{serial}_{char_cnt}_{safe_title}.txt"

        write_text_utf8_nobom(os.path.join(file_dir, fname), body)
        if merge_flag is not None:
            kept_texts.append(body)

        if written_count < 3 or idx >= len(chapters) - 2:
            if n_lines == 1:
                tag = "  (仅标题)"
            elif min_body_len > 0 and body_len < min_body_len:
                tag = f"  ({n_lines}行,正文{body_len}字)"
            else:
                tag = f"  ({n_lines}行)"
            vol_tag = f"[卷{ch['vol_num']}] " if ch.get('vol_num') else ""
            print(f"  [{serial}] {vol_tag}{fname}{tag}")
        elif written_count == 3:
            print("  ...")

        written_count += 1

    t_write = time.time() - t0
    t_total = time.time() - t_total0

    # 清洁模式双合并（v3.4：同时输出 保留≥N 和 清理<N 两个纯净正文文件，无报告头部）
    if merge_flag is not None:
        src_name = os.path.splitext(os.path.basename(src))[0]
        mdir = merge_dir if merge_dir else out_dir
        os.makedirs(mdir, exist_ok=True)
        kept_name = f"保留大于等于{min_body_len}_{src_name}.txt"
        with open(os.path.join(mdir, kept_name), 'w', encoding='utf-8') as f:
            f.write('\n'.join(kept_texts))
        print(f"合并文件：{kept_name}（{len(kept_texts)}章合并）")
        skipped_name = f"清理小于{min_body_len}_{src_name}.txt"
        with open(os.path.join(mdir, skipped_name), 'w', encoding='utf-8') as f:
            f.write('\n'.join(skipped_texts))
        print(f"合并文件：{skipped_name}（{len(skipped_texts)}章合并）")

    # ===== 报告（v3.4：总-分结构；v3.5：清洁模式落盘 拆分完成报告.txt，与VBA版一致） =====
    mode_label = f"清洁模式(N={min_body_len})" if merge_flag is not None else "拆分"
    src_name_r = os.path.splitext(os.path.basename(src))[0]
    rpt = []
    rpt.append("=" * 60)
    rpt.append(f"【总】{mode_label}完成：共生成 {written_count} 个文件")
    rpt.append(f"  输出目录: {out_dir}")
    rpt.append(f"  总耗时: {t_total:.2f} 秒")
    rpt.append("-" * 60)
    rpt.append("【分】详细统计")
    rpt.append(f"  来源: 编码{enc} / 总行数{len(lines):,} / 识别章节{len(all_chapters_raw)}"
               + (f"（目录区跳过{toc_count}）" if toc_count > 0 else ""))
    rpt.append(f"  质量: 去重{dedup_strategy}(减少{dedup_removed}章) / "
               f"排序{sort_strategy}(修序{ooo_fixed}处) / 卷模式{actual_vol_mode}")
    parts = []
    if title_only_count > 0:
        parts.append(f"{title_only_count}个仅有标题")
    if short_body_count > 0:
        parts.append(f"{short_body_count}个正文不足")
    skip_desc = '、'.join(parts) if parts else '无'
    top3 = sorted(skipped_body_lens, reverse=True)[:3]
    top3_str = '、'.join(f'{x}字' for x in top3) if top3 else '无'
    rpt.append(f"  清理: 广告行移除{ad_removed} / 跳过{skipped_count}章({skip_desc}) / "
               f"前三正文字数: {top3_str}")
    rpt.append(f"  计时: 读取{t_read:.2f}s / 识别{t_scan:.2f}s / 去重{t_dedup:.2f}s / "
               f"排序{t_sort:.2f}s / 写入{t_write:.2f}s")
    if merge_flag is not None:
        rpt.append("-" * 60)
        rpt.append(f"  文件清单: 保留大于等于{min_body_len}_{src_name_r}.txt（{len(kept_texts)}章） / "
                   f"清理小于{min_body_len}_{src_name_r}.txt（{len(skipped_texts)}章） / "
                   f"拆分文档\\（{written_count}个单章文件）")
    rpt.append("=" * 60)
    print()
    for _line in rpt:
        print(_line)
    if merge_flag is not None:
        _rdir = merge_dir if merge_dir else out_dir
        # v3.5：改名为"拆分完成报告.txt"，与VBA版一致（避免与深度"分析报告.txt"混淆）
        with open(os.path.join(_rdir, "拆分完成报告.txt"), 'w', encoding='utf-8') as _f:
            _f.write('\n'.join(rpt) + '\n')


def split_by_groups(src, chunk_str="40,3", out_dir="", prefix="",
                    serial_width=3, encoding=None, dedup_strategy='longest',
                    sort_strategy='sort', volume_mode='auto', title_dedup=True,
                    ad_clean=False):
    """聚合拆分"""
    import math

    t_total0 = time.time()

    t0 = time.time()
    lines, structures, all_chapters_raw, volumes, toc_count, ad_removed, enc = \
        load_and_scan(src, encoding, ad_clean)
    t_read = time.time() - t0
    print(f"编码: {enc}")
    print(f"源文件: {src}")
    print(f"总行数: {len(lines):,}")
    if ad_clean:
        print(f"广告清理: 移除垃圾行 {ad_removed} 行")

    t0 = time.time()
    # 目录区章节不参与去重/排序/拆分输出
    all_chapters = [c for c in all_chapters_raw if not c.get('is_toc')]

    if volume_mode == 'auto':
        actual_vol_mode = 'volume' if volumes else 'flat'
    else:
        actual_vol_mode = volume_mode if volume_mode != 'by_volume' else 'volume'
    # v3.5: 聚合优先级大于卷——聚合按全局章号连续切块，卷分组无意义，强制扁平
    if actual_vol_mode != 'flat':
        actual_vol_mode = 'flat'
        print("卷模式: 聚合拆分优先 → 强制扁平（忽略卷结构）")

    # 去重
    chapters = all_chapters
    if dedup_strategy != 'none':
        dedup_func = DEDUP_STRATEGIES.get(dedup_strategy)
        if dedup_func is None:
            print(f"[错误] 未知去重策略: {dedup_strategy}")
            sys.exit(1)
        chapters = dedup_func(chapters, actual_vol_mode, title_dedup=title_dedup)

    # 排序
    if sort_strategy != 'none':
        sort_func = SORT_STRATEGIES.get(sort_strategy)
        if sort_func is None:
            print(f"[错误] 未知排序策略: {sort_strategy}")
            sys.exit(1)
        chapters = sort_func(chapters, actual_vol_mode, title_dedup=title_dedup)

    t_scan = time.time() - t0

    unit = chapters[0].get('ch_unit', '章') if chapters else '章'
    total = len(chapters)

    print(f"识别章节(原始): {len(all_chapters_raw)}"
          + (f"（目录区跳过{toc_count}）" if toc_count > 0 else ""))
    print(f"去重策略: {dedup_strategy}")
    print(f"排序策略: {sort_strategy}")
    print(f"卷模式: {actual_vol_mode}")
    print(f"处理后章节: {total}  单位: {unit}")
    print(f"聚合格式: {chunk_str}")

    if total == 0:
        print("未识别到章节，终止")
        sys.exit(1)

    # 解析聚合格式
    def parse_groups(s, total_ch):
        s = s.strip()
        if not s:
            raise ValueError("聚合字符串为空")
        if ',' not in s and '|' not in s:
            n = int(s)
            if n <= 0:
                raise ValueError(f"每份章数必须为正数: {s}")
            cnt = math.ceil(total_ch / n)
            return [(cnt, n)]

        parts = [p.strip() for p in s.split('|') if p.strip()]
        groups = []
        consumed = 0
        for part in parts:
            detail = [d.strip() for d in part.split(',')]
            if len(detail) != 2:
                raise ValueError(f"段格式错误: {part}（应为 每份章数,份数）")
            per_chapter, count = int(detail[0]), int(detail[1])
            if per_chapter <= 0 or count <= 0:
                raise ValueError(f"每份章数和份数必须为正数: {part}")
            groups.append((count, per_chapter))
            consumed += count * per_chapter

        if consumed > total_ch:
            raise ValueError(f"消耗章节数 {consumed} 超过总章节数 {total_ch}")
        if consumed < total_ch:
            groups.append((1, total_ch - consumed))
        return groups

    try:
        groups = parse_groups(chunk_str, total)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    # 展开文件列表
    files = []
    ch = 0
    idx = 0
    for (length, spacing) in groups:
        for _ in range(length):
            if ch >= total:
                break
            ch_start = ch + 1
            ch_end = min(ch + spacing, total)
            idx += 1
            files.append((idx, ch_start, ch_end))
            ch = ch_end
        if ch >= total:
            break

    serial_width = max(serial_width, len(str(len(files))))

    out_dir = resolve_output_dir(src, out_dir, "_分组")
    clean_output_dir(out_dir)
    print(f"输出目录: {out_dir}")
    print()

    t0 = time.time()
    for (fidx, ch_s, ch_e) in files:
        line_start = chapters[ch_s - 1]['line_idx']
        if ch_e < total:
            line_end = chapters[ch_e]['line_idx'] - 1
        else:
            line_end = len(lines) - 1

        body = '\n'.join(lines[line_start:line_end + 1])

        range_str = format_range(ch_s, ch_e, unit)
        safe = sanitize_filename(range_str)
        serial = str(fidx).zfill(serial_width)
        fname = f"{serial}_{safe}.txt"
        if prefix:
            fname = f"{prefix}_{fname}"

        write_text_utf8_nobom(os.path.join(out_dir, fname), body)
        print(f"  [{serial}/{len(files)}] {fname}  (第{ch_s}-{ch_e}{unit}, {line_end - line_start + 1}行)")

    t_write = time.time() - t0
    t_total = time.time() - t_total0

    print()
    print("=" * 60)
    print(f"【总】聚合拆分完成：共生成 {len(files)} 个文件")
    print(f"  输出目录: {out_dir}")
    print(f"  总耗时: {t_total:.2f} 秒")
    print("-" * 60)
    print("【分】详细统计")
    print(f"  来源: 编码{enc} / 总行数{len(lines):,} / 识别章节{len(all_chapters_raw)}"
          + (f"（目录区跳过{toc_count}）" if toc_count > 0 else ""))
    print(f"  质量: 去重{dedup_strategy} / 排序{sort_strategy} / 卷模式{actual_vol_mode}")
    print(f"  清理: 广告行移除{ad_removed}")
    print(f"  计时: 读取{t_read:.2f}s / 识别+去重+排序{t_scan:.2f}s / 写入{t_write:.2f}s")
    print("=" * 60)


def resolve_output_dir(src, out_dir, suffix):
    if out_dir:
        return out_dir
    return os.path.join(os.path.dirname(os.path.abspath(src)),
                        os.path.splitext(os.path.basename(src))[0] + suffix)


def clean_output_dir(out_dir):
    if os.path.exists(out_dir):
        old = os.listdir(out_dir)
        if old:
            print(f"[警告] 输出目录非空({len(old)}项)，将清空后重建")
            shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)


# ===========================================================================
# v3.4 新增：全自动模式
#   读取+清理+扫描+目录区检测 → 深度分析 → 自动决策 → 执行清洁模式输出
# ===========================================================================
def auto_process(src, encoding=None, volume_mode='auto', title_dedup=True,
                 ad_clean=False):
    """全自动模式：一键完成分析、决策与清洁输出"""
    src_name = os.path.splitext(os.path.basename(src))[0]
    auto_dir = os.path.join(os.path.dirname(os.path.abspath(src)),
                            src_name + '_自动')
    clean_output_dir(auto_dir)
    print(f"输出目录: {auto_dir}")
    print()

    # 1. 深度分析（总-分报告）
    report = deep_analyze(src, encoding=encoding, ad_clean=ad_clean)
    report_path = os.path.join(auto_dir, '分析报告.txt')
    write_text_utf8_nobom(report_path, report)
    print(report)
    print()
    print(f"分析报告已保存: {report_path}")
    print()

    # 2. 自动决策（仅用 ch_num>0 且非目录区章节）
    lines, structures, chapters_all, volumes, toc_count, ad_removed, enc = \
        load_and_scan(src, encoding, ad_clean)
    dedup_strategy, sort_strategy, reason = auto_decide(chapters_all)
    n_value, n_reason = auto_decide_n(chapters_all, lines)

    print("=" * 60)
    print("  自动方案：")
    print(f"  • 去重策略: {dedup_strategy}  排序策略: {sort_strategy}")
    print(f"    判定理由: {reason}")
    print(f"  • 清洁N值: {n_value}")
    print(f"    判定理由: {n_reason}")
    print("=" * 60)
    print()

    # 3. 执行清洁模式输出（拆分文档子目录 + 双合并文件）
    split_dir = os.path.join(auto_dir, '拆分文档')
    split_by_chapter(src, out_dir=split_dir, encoding=encoding,
                     dedup_strategy=dedup_strategy, sort_strategy=sort_strategy,
                     volume_mode=volume_mode, min_body_len=n_value, merge_flag=1,
                     title_dedup=title_dedup, ad_clean=ad_clean,
                     merge_dir=auto_dir)


# ===========================================================================
# CLI入口
# ===========================================================================
def main():
    epilog = """6种去重×排序组合（--dedup × --sort）及适用场景：
  ┌───────────┬────────┬──────────────────────────────────┐
  │ 去重      │ 排序   │ 适用场景                         │
  ├───────────┼────────┼──────────────────────────────────┤
  │ none      │ none   │ 文件干净无重复无乱序，仅拆分     │
  │ none      │ sort   │ 无重复但整体乱序，按章号重排     │
  │ first     │ none   │ 相邻双标题/简单重复，留首次出现  │
  │ first     │ sort   │ 简单重复且乱序                   │
  │ longest   │ none   │ 整块重复，留最长内容且不改顺序   │
  │ longest   │ sort   │ 重复+乱序严重，最彻底(默认)      │
  └───────────┴────────┴──────────────────────────────────┘
  注: lis 已合并入 first+sort，仅兼容保留；相邻双标题由目录区检测+清洁模式覆盖。

示例：
  python split_txt_v3.py --src 小说.txt --auto          # 全自动（推荐）
  python split_txt_v3.py --src 小说.txt --analyze       # 深度分析
  python split_txt_v3.py --src 小说.txt --clean 100     # 清洁模式(双合并文件)
  python split_txt_v3.py --src 小说.txt --dedup first --sort none
"""
    parser = argparse.ArgumentParser(
        description="TXT章节拆分工具 v3.4（去重+乱序修复+卷级感知+目录区检测+广告清理+全自动模式）",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", default=None, help="源TXT路径")
    parser.add_argument("--mode", choices=["chapter", "groups"], default="chapter",
                        help="拆分模式: chapter=每章一文件(默认), groups=聚合拆分")
    parser.add_argument("--out", default="", help="输出目录(空=自动派生)")
    parser.add_argument("--chunk", default=None,
                        help="聚合格式 每份章数,份数|... 或便捷 N")
    parser.add_argument("--prefix", default="", help="文件名前缀")
    parser.add_argument("--serial-width", type=int, default=3,
                        help="序号位数(默认3)")
    parser.add_argument("--encoding", default=None,
                        help="手动指定源文件编码")
    parser.add_argument("--analyze", action="store_true",
                        help="深度分析：全面诊断所有问题（总-分结构报告）")
    parser.add_argument("--auto", action="store_true",
                        help="全自动模式：分析→自动决策组合与清洁N值→清洁模式输出到 <名>_自动/")
    parser.add_argument("--dedup", default="longest",
                        choices=list(DEDUP_STRATEGIES.keys()),
                        help="去重策略: none/first/longest (默认: longest)；"
                             "双标题场景由目录区检测+清洁模式覆盖")
    parser.add_argument("--sort", default="sort",
                        choices=list(SORT_STRATEGIES.keys()),
                        help="排序策略: none/sort (默认: sort)；"
                             "lis 已合并入 first+sort，仅兼容保留")
    parser.add_argument("--volume-mode", default="auto",
                        choices=["auto", "flat", "by_volume"],
                        help="卷级处理模式: auto(自动检测)/flat(扁平)/by_volume(按卷分目录)")
    parser.add_argument("--keep-title-only", action="store_true", default=False,
                        help="生成仅有标题/正文不足的章节文件")
    parser.add_argument("--min-body-len", type=int, default=0,
                        help="最小正文字数(0=不检测)")
    parser.add_argument("--clean", default=None, type=int,
                        help="清洁模式：N=最小正文字数，同时生成 保留大于等于N / 清理小于N 双合并文件（纯净正文无头部）")
    parser.add_argument("--title-dedup", dest="title_dedup", action="store_true", default=True,
                        help="标题级去重（默认开启）：同章号同标题才算重复，不同标题保留为不同章节")
    parser.add_argument("--no-title-dedup", dest="title_dedup", action="store_false",
                        help="关闭标题级去重：仅按章号去重（同章号不同标题会被误删）")
    parser.add_argument("--ad-clean", dest="ad_clean", action="store_true", default=False,
                        help="广告/垃圾行清理（默认关闭）：网址/推广语/分页提示/求票/分隔线等7类规则")
    parser.add_argument("--no-ad-clean", dest="ad_clean", action="store_false",
                        help="关闭广告/垃圾行清理（默认行为，保留原文）")
    args = parser.parse_args()

    if args.analyze:
        if not args.src:
            parser.error("--analyze 需要 --src 参数")
        print(deep_analyze(args.src, encoding=args.encoding, ad_clean=args.ad_clean))
        return

    if args.auto:
        if not args.src:
            parser.error("--auto 需要 --src 参数")
        auto_process(args.src, encoding=args.encoding, volume_mode=args.volume_mode,
                     title_dedup=args.title_dedup, ad_clean=args.ad_clean)
        return

    if not args.src:
        parser.error("拆分模式需要 --src 参数")

    mode = args.mode
    if args.chunk is not None and mode == "chapter":
        mode = "groups"

    merge_flag = None
    if args.clean is not None:
        args.min_body_len = args.clean
        merge_flag = 1  # 清洁模式（双合并文件）
        mode = "chapter"

    try:
        if mode == "chapter":
            _out = args.out
            _mdir = None
            if merge_flag is not None:
                # v3.5: 清洁模式固定五件套结构（拆分文档\ + 双合并 + 分析报告.txt + 拆分完成报告.txt 在输出根目录）
                if not _out:
                    _out = os.path.splitext(os.path.basename(args.src))[0] + "_自动"
                _mdir = _out
                _out = os.path.join(_out, "拆分文档")
            split_by_chapter(args.src, _out, args.prefix, args.serial_width,
                             args.encoding, args.dedup, args.sort, args.volume_mode,
                             args.keep_title_only, args.min_body_len, merge_flag,
                             title_dedup=args.title_dedup, ad_clean=args.ad_clean,
                             merge_dir=_mdir)
        else:
            chunk_str = args.chunk if args.chunk else "40,3"
            split_by_groups(args.src, chunk_str, args.out, args.prefix,
                            args.serial_width, args.encoding, args.dedup,
                            args.sort, args.volume_mode, title_dedup=args.title_dedup,
                            ad_clean=args.ad_clean)
    except ValueError as e:
        print(f"[错误] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
