#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT章节拆分工具 v3.1（增强版）—— 全面解决章节质量问题

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
  10. 多级嵌套      —— 卷→篇→章→节 多层嵌套结构
  11. 无号章节      —— 序章/楔子/番外/尾声/后记 等无数字编号的章节
  12. 章号缺失      —— 中间缺章，章号不连续
  13. 格式混合      —— 阿拉伯数字+中文数字混合，不同单位词混合

【去重策略】
  adjacent   — 相邻重复去重（仅合并连续相同章号）
  first      — 保留首次出现（每章只留第一次）
  longest    — 保留内容最长的（每章留正文最多的）
  lis        — 最长递增子序列（智能找主线，去重+修序二合一）
  sort       — 按章号重新排序（最彻底，每个章号取最长后重排）

【卷级处理模式】
  auto       — 自动检测：有卷结构则启用卷-章二级去重
  flat       — 强制扁平：忽略卷结构，所有章节按章号去重
  by_volume  — 强制按卷：每卷独立处理，输出到各卷子目录

用法:
  # 深度分析（推荐第一步，全面诊断所有问题）
  python split_txt_v3.py --src 小说.txt --analyze

  # 按章节拆分（自动检测卷结构，LIS去重）
  python split_txt_v3.py --src 小说.txt --dedup lis

  # 强制扁平去重（忽略卷）
  python split_txt_v3.py --src 小说.txt --dedup sort --volume-mode flat

  # 按卷分目录输出
  python split_txt_v3.py --src 小说.txt --dedup lis --volume-mode by_volume

  # 聚合拆分
  python split_txt_v3.py --src 小说.txt --dedup lis --chunk 40,3
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
        line_stripped = line.rstrip()
        if not line_stripped.strip():
            continue

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
                'title': m.group(0).strip(),
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
                'title': m.group(0).strip(),
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
                    'title': m.group(0).strip(),
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
# 去重策略（支持卷级感知）
# ===========================================================================

def _dedup_key(ch, volume_mode):
    """生成去重用的唯一键"""
    if volume_mode == 'flat' or ch.get('vol_num') is None:
        return ('flat', ch['ch_num'], ch.get('ch_unit', ''))
    else:
        return (ch['vol_num'], ch['ch_num'], ch.get('ch_unit', ''))


def dedup_adjacent(chapters, volume_mode='auto'):
    """策略1：相邻重复去重"""
    if not chapters:
        return []
    result = [chapters[0]]
    for ch in chapters[1:]:
        key = _dedup_key(ch, volume_mode)
        last_key = _dedup_key(result[-1], volume_mode)
        if ch['ch_num'] > 0 and key == last_key:
            if ch['body_lines'] > result[-1]['body_lines']:
                result[-1] = ch
            continue
        result.append(ch)
    return result


def dedup_first(chapters, volume_mode='auto'):
    """策略2：保留首次出现"""
    seen = set()
    result = []
    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            # 无号章节：按标题去重
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode)
        if key not in seen:
            seen.add(key)
            result.append(ch)
    return result


def dedup_longest(chapters, volume_mode='auto'):
    """策略3：保留内容最长的"""
    best = OrderedDict()
    order = []

    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode)

        if key not in best:
            best[key] = ch
            order.append(key)
        else:
            if ch['body_lines'] > best[key]['body_lines']:
                best[key] = ch

    return [best[k] for k in order]


def dedup_lis(chapters, volume_mode='auto'):
    """策略4：最长递增子序列（LIS）
    支持卷级感知：同一卷内章号递增，跨卷时卷号也递增
    """
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


def dedup_sort(chapters, volume_mode='auto'):
    """策略5：按（卷号,章号）重新排序"""
    best = OrderedDict()

    for ch in chapters:
        if ch['ch_num'] <= 0 and ch['level'] == 'special':
            key = ('special', ch['title'])
        else:
            key = _dedup_key(ch, volume_mode)

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
    'adjacent': dedup_adjacent,
    'first': dedup_first,
    'longest': dedup_longest,
    'lis': dedup_lis,
    'sort': dedup_sort,
}


# ===========================================================================
# 深度分析报告
# ===========================================================================
def deep_analyze(file_path):
    """深度分析：全面诊断所有问题"""
    print("=" * 70)
    print(f"  深度分析报告: {os.path.basename(file_path)}")
    print("=" * 70)

    content = read_text_auto(file_path)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')
    print(f"总行数: {len(lines):,}")
    print(f"总字符: {len(content):,}")

    structures = scan_structures(lines)
    chapters = get_chapters_only(structures)
    volumes = get_volumes(structures)

    print(f"识别结构: 卷级 {len(volumes)} 个, 章节级 {len(chapters)} 个")
    print()

    # ---------- 1. 卷结构分析 ----------
    print("-" * 50)
    print("【一、卷/部结构分析】")
    if volumes:
        print(f"  卷级标题数: {len(volumes)}")
        vol_nums = set(v['vol_num'] for v in volumes if v['vol_num'])
        vol_units = set(v['vol_unit'] for v in volumes if v['vol_unit'])
        print(f"  卷号范围: {min(vol_nums)} - {max(vol_nums)}") if vol_nums else None
        print(f"  卷单位词: {', '.join(sorted(vol_units))}")

        # 每卷的章数
        vol_chapter_counts = defaultdict(int)
        current_vol = None
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
            elif s['level'] in ('chapter', 'special'):
                vol_chapter_counts[current_vol] += 1

        print(f"  各卷章节数:")
        for vol_num in sorted(vol_chapter_counts.keys(), key=lambda x: (x is None, x or 0)):
            vol_label = f"第{vol_num}卷" if vol_num else "无卷"
            print(f"    {vol_label}: {vol_chapter_counts[vol_num]} 章")

        # 卷间章号重复检测
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
                    print(f"\n  ⚠ 卷间章号重复: 第{vol_list[0]}卷 和 第{vol_list[1]}卷 共享 {len(common)} 个章号")
                    print(f"    示例重复章号: {sorted(list(common))[:10]}...")
    else:
        print("  未检测到卷/部/册级结构")

    # ---------- 2. 重复分析 ----------
    print()
    print("-" * 50)
    print("【二、重复章节分析】")

    # 扁平去重统计（忽略卷）
    flat_map = defaultdict(list)
    for ch in chapters:
        if ch['ch_num'] > 0:
            flat_map[ch['ch_num']].append(ch)

    unique_flat = len(flat_map)
    dup_flat = {k: v for k, v in flat_map.items() if len(v) > 1}

    print(f"  扁平视角（忽略卷）:")
    print(f"    不重复章号数: {unique_flat}")
    print(f"    存在重复的章号数: {len(dup_flat)}")

    if dup_flat:
        sorted_dups = sorted(dup_flat.items(), key=lambda x: -len(x[1]))
        print(f"\n    重复最严重的15个章号：")
        for num_val, occ_list in sorted_dups[:15]:
            count = len(occ_list)
            lines_str = ', '.join(str(c['line_idx'] + 1) for c in occ_list[:5])
            title_preview = occ_list[0]['title'][:30]
            print(f"      第{num_val}章 ({count}次): {title_preview}... (行: {lines_str}...)")

        count_dist = defaultdict(int)
        for occ_list in dup_flat.values():
            count_dist[len(occ_list)] += 1
        print(f"\n    重复次数分布：")
        for cnt in sorted(count_dist.keys()):
            print(f"      出现{cnt}次的章号: {count_dist[cnt]}个")

    # 卷感知去重统计
    if volumes:
        vol_aware_map = defaultdict(list)
        for ch in chapters:
            if ch['ch_num'] > 0:
                key = (ch.get('vol_num'), ch['ch_num'])
                vol_aware_map[key].append(ch)
        dup_vol_aware = {k: v for k, v in vol_aware_map.items() if len(v) > 1}
        print(f"\n  卷感知视角（同卷内才算重复）:")
        print(f"    卷-章组合数: {len(vol_aware_map)}")
        print(f"    同卷内重复数: {len(dup_vol_aware)}")

    # ---------- 3. 乱序分析 ----------
    print()
    print("-" * 50)
    print("【三、乱序分析】")

    # 扁平乱序
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

    print(f"  扁平视角（忽略卷）:")
    print(f"    乱序次数: {ooo_count}")
    if max_drop_info:
        print(f"    最大跌幅: 第{max_drop_info[0]}章 → 第{max_drop_info[1]}章 (跌{max_drop}, 行{max_drop_info[2]})")

    # 卷内乱序
    if volumes:
        print(f"\n  卷内视角（每卷单独统计）:")
        vol_ooo = defaultdict(int)
        vol_max_drop = defaultdict(lambda: (0, 0, 0))
        current_vol = None
        prev_ch = 0
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
                prev_ch = 0
            elif s['level'] == 'chapter' and s['ch_num'] > 0:
                if s['ch_num'] < prev_ch:
                    vol_ooo[current_vol] += 1
                    drop = prev_ch - s['ch_num']
                    if drop > vol_max_drop[current_vol][0]:
                        vol_max_drop[current_vol] = (drop, prev_ch, s['ch_num'])
                prev_ch = s['ch_num']

        for vol_num in sorted(vol_ooo.keys(), key=lambda x: (x is None, x or 0)):
            vol_label = f"第{vol_num}卷" if vol_num else "无卷"
            drop_info = vol_max_drop[vol_num]
            print(f"    {vol_label}: 乱序{vol_ooo[vol_num]}处, 最大跌{drop_info[0]} (第{drop_info[1]}→第{drop_info[2]}章)")

    # ---------- 4. 多轨目录检测 ----------
    print()
    print("-" * 50)
    print("【四、多轨目录检测】")

    # 检测方法1：相邻双标题比例
    adj_dup = 0
    for i in range(1, len(chapters)):
        if (chapters[i]['ch_num'] == chapters[i-1]['ch_num']
                and chapters[i]['ch_num'] > 0
                and chapters[i]['line_idx'] - chapters[i-1]['line_idx'] <= 2):
            adj_dup += 1

    adj_ratio = adj_dup / len(chapters) if chapters else 0
    print(f"  相邻双标题数: {adj_dup} (占比 {adj_ratio:.1%})")
    if adj_ratio > 0.3:
        print(f"  → 疑似每章双标题结构（目录式+正文式各一次）")

    # 检测方法2：完整的章号序列出现多次
    # 找最长的连续递增序列出现的次数
    if len(valid_chs) > 10:
        print(f"  章号序列模式检测中...")
        # 简单检测：统计1到N的完整序列出现了几次
        # 找第一个连续递增块的长度
        seq_len = 1
        max_seq = 1
        for i in range(1, len(valid_chs)):
            if valid_chs[i]['ch_num'] == valid_chs[i-1]['ch_num'] + 1:
                seq_len += 1
                max_seq = max(max_seq, seq_len)
            else:
                seq_len = 1
        print(f"  最长连续递增章号段长度: {max_seq}")

    # ---------- 5. 格式多样性分析 ----------
    print()
    print("-" * 50)
    print("【五、格式多样性分析】")

    pattern_counts = defaultdict(int)
    unit_counts = defaultdict(int)
    for ch in chapters:
        pattern_counts[ch['pattern_type']] += 1
        if ch.get('ch_unit'):
            unit_counts[ch['ch_unit']] += 1

    print(f"  正则类型分布:")
    for ptype, cnt in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        print(f"    {ptype:15s}: {cnt:4d} 章 ({cnt/len(chapters)*100:.1f}%)")

    print(f"  单位词分布:")
    for unit, cnt in sorted(unit_counts.items(), key=lambda x: -x[1]):
        print(f"    {unit:6s}: {cnt:4d} 章")

    special_chs = [ch for ch in chapters if ch['level'] == 'special']
    if special_chs:
        print(f"  无号章节（序章/楔子/番外等）: {len(special_chs)} 个")
        for ch in special_chs[:10]:
            print(f"    行{ch['line_idx']+1}: {ch['title'][:40]}")
        if len(special_chs) > 10:
            print(f"    ... 共 {len(special_chs)} 个")

    # ---------- 6. 连续性分析 ----------
    print()
    print("-" * 50)
    print("【六、章号连续性分析】")

    if volumes:
        # 分卷统计
        vol_chs = defaultdict(list)
        current_vol = None
        for s in structures:
            if s['level'] == 'volume':
                current_vol = s['vol_num']
            elif s['level'] == 'chapter' and s['ch_num'] > 0:
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
            print(f"  {vol_label}: {min_n}-{max_n}章, 应有{expected}章, 实有{actual}章, 缺{missing}章")
    else:
        nums = sorted(set(ch['ch_num'] for ch in chapters if ch['ch_num'] > 0))
        if nums:
            min_n, max_n = min(nums), max(nums)
            expected = max_n - min_n + 1
            missing = expected - len(nums)
            print(f"  章号范围: {min_n} - {max_n}")
            print(f"  应有章节数: {expected}")
            print(f"  实际章号数: {len(nums)}")
            print(f"  缺失章号数: {missing}")

            if missing > 0 and missing < 100:
                full_set = set(nums)
                missing_list = [n for n in range(min_n, max_n + 1) if n not in full_set]
                print(f"  缺失章号: {missing_list[:30]}")
                if len(missing_list) > 30:
                    print(f"    ... 共{len(missing_list)}个")

    # ---------- 7. 各策略效果预览 ----------
    print()
    print("-" * 50)
    print("【七、各去重策略效果预览（扁平模式）】")
    for name, func in DEDUP_STRATEGIES.items():
        try:
            deduped = func(chapters, 'flat')
            ooo_after = 0
            prev = 0
            for ch in deduped:
                if ch['ch_num'] <= 0:
                    continue
                if ch['ch_num'] < prev:
                    ooo_after += 1
                prev = ch['ch_num']
            print(f"  {name:12s}: 剩{len(deduped):4d}章, 乱序{ooo_after:4d}处")
        except Exception as e:
            print(f"  {name:12s}: 错误 - {e}")

    if volumes:
        print(f"\n  【卷感知模式】")
        for name, func in DEDUP_STRATEGIES.items():
            try:
                deduped = func(chapters, 'auto')
                # 卷感知乱序：同卷内比较
                ooo_after = 0
                prev_vol = None
                prev_ch = 0
                for ch in deduped:
                    if ch['ch_num'] <= 0:
                        continue
                    v = ch.get('vol_num')
                    if v == prev_vol:
                        if ch['ch_num'] < prev_ch:
                            ooo_after += 1
                    prev_vol = v
                    prev_ch = ch['ch_num']
                print(f"  {name:12s}: 剩{len(deduped):4d}章, 卷内乱序{ooo_after:3d}处")
            except Exception as e:
                print(f"  {name:12s}: 错误 - {e}")

    # ---------- 8. 建议 ----------
    print()
    print("=" * 70)
    print("  处理建议：")

    suggestions = []
    if volumes and len(vol_nums) > 1 and common:
        suggestions.append("• 检测到多卷结构且卷间章号重复，建议启用卷感知模式")
        suggestions.append("  （--volume-mode auto 或 by_volume）")

    if ooo_count > 10:
        suggestions.append("• 乱序严重，推荐 sort 策略（最彻底）或 lis 策略（智能）")
    elif dup_flat:
        suggestions.append("• 有重复但乱序轻微，推荐 longest 策略（保留内容最长的）")

    if adj_ratio > 0.3:
        suggestions.append("• 每章双标题明显，adjacent 策略即可解决大部分问题")

    if not suggestions:
        suggestions.append("• 文件质量较好，可根据需要选择策略")

    for s in suggestions:
        print(f"  {s}")

    print("=" * 70)


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
                     dedup_strategy='lis', volume_mode='auto',
                     generate_title_only=False, min_body_len=0, merge_flag=None):
    """按章节一一拆分"""
    t_total0 = time.time()

    # 1. 读取
    t0 = time.time()
    if encoding:
        enc = encoding.upper()
        content = read_text_auto(src, encoding)
    else:
        enc = detect_encoding(src)
        content = read_text_auto(src)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')
    t_read = time.time() - t0
    print(f"编码: {enc}")
    print(f"源文件: {src}")
    print(f"总行数: {len(lines):,}  总字符: {len(content):,}")

    # 2. 扫描结构
    t0 = time.time()
    structures = scan_structures(lines)
    all_chapters = get_chapters_only(structures)
    volumes = get_volumes(structures)
    t_scan = time.time() - t0
    print(f"识别结构: 卷级 {len(volumes)} 个, 章节级 {len(all_chapters)} 个")

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
    t0 = time.time()
    dedup_func = DEDUP_STRATEGIES.get(dedup_strategy)
    if dedup_func is None:
        print(f"[错误] 未知去重策略: {dedup_strategy}")
        sys.exit(1)
    chapters = dedup_func(all_chapters, actual_vol_mode)
    t_dedup = time.time() - t0
    print(f"去重策略: {dedup_strategy}")
    print(f"去重后章节: {len(chapters)}")

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

    # 7. 预计算字数
    char_counts = []
    for ch in chapters:
        s_line = ch['line_idx']
        e_line = ch['end_line']
        if e_line < s_line:
            e_line = s_line
        char_counts.append(len('\n'.join(lines[s_line:e_line + 1])))
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

        # 正文汉字数
        if n_lines > 1:
            body_text = ''.join(lines[start_line + 1:end_line + 1])
            body_len = len(re.sub(r'[^\u4e00-\u9fff]', '', body_text))
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
            if merge_flag == 0:
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
        if merge_flag == 1:
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

    # 清洁模式合并
    if merge_flag is not None and (merge_flag == 0 or merge_flag == 1):
        src_name = os.path.splitext(os.path.basename(src))[0]
        header_lines = [
            "=" * 50,
            f"清理说明：正文中文字数小于 {min_body_len} 的章节已跳过",
            f"跳过章节：{skipped_count} 个",
        ]
        if skipped_chapters_list:
            header_lines.append("跳过明细：")
            for title, blen in skipped_chapters_list:
                header_lines.append(f"  {title}（{blen}字）")
            top3 = sorted(skipped_body_lens, reverse=True)[:3]
            header_lines.append("前三正文：" + "、".join(f"{x}字" for x in top3))
        header_lines.append(f"保留章节：{written_count} 个")

        if merge_flag == 0 and skipped_texts:
            header_lines.append(f"本文件内容：跳过章节（正文汉字 < {min_body_len}）")
            header_lines.append("=" * 50)
            merge_name = f"清理小于{min_body_len}_{src_name}.txt"
            merge_path = os.path.join(out_dir, merge_name)
            with open(merge_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(header_lines) + '\n')
                f.write('\n'.join(skipped_texts))
            print(f"合并文件：{merge_name}（{len(skipped_texts)}章合并）")
        elif merge_flag == 1 and kept_texts:
            header_lines.append(f"本文件内容：保留章节（正文汉字 >= {min_body_len}）")
            header_lines.append("=" * 50)
            merge_name = f"保留大于等于{min_body_len}_{src_name}.txt"
            merge_path = os.path.join(out_dir, merge_name)
            with open(merge_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(header_lines) + '\n')
                f.write('\n'.join(kept_texts))
            print(f"合并文件：{merge_name}（{len(kept_texts)}章合并）")

    # 报告
    print()
    print("=" * 60)
    print(f"拆分完成！共生成 {written_count} 个文件")
    print(f"输出目录: {out_dir}")
    print(f"去重策略: {dedup_strategy}")
    print(f"卷模式: {actual_vol_mode}")
    print()
    print("【计时统计】")
    print(f"  读取文件: {t_read:.2f} 秒")
    print(f"  识别结构: {t_scan:.2f} 秒")
    print(f"  去重处理: {t_dedup:.2f} 秒")
    print(f"  写入文件: {t_write:.2f} 秒")
    print(f"  总计耗时: {t_total:.2f} 秒")

    parts = []
    if title_only_count > 0:
        parts.append(f"{title_only_count}个仅有标题")
    if short_body_count > 0:
        parts.append(f"{short_body_count}个正文不足")
    if skipped_count > 0:
        top3 = sorted(skipped_body_lens, reverse=True)[:3]
        print(f"\n[提示] 跳过 {skipped_count} 个章节（{'、'.join(parts)}），前三：{'、'.join(f'{x}字' for x in top3)}")
    elif parts:
        print(f"\n[提示] {'、'.join(parts)}（已生成）")


def split_by_groups(src, chunk_str="40,3", out_dir="", prefix="",
                    serial_width=3, encoding=None, dedup_strategy='lis',
                    volume_mode='auto'):
    """聚合拆分"""
    import math

    t_total0 = time.time()

    t0 = time.time()
    if encoding:
        enc = encoding.upper()
        content = read_text_auto(src, encoding)
    else:
        enc = detect_encoding(src)
        content = read_text_auto(src)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')
    t_read = time.time() - t0
    print(f"编码: {enc}")
    print(f"源文件: {src}")
    print(f"总行数: {len(lines):,}")

    t0 = time.time()
    structures = scan_structures(lines)
    all_chapters = get_chapters_only(structures)
    volumes = get_volumes(structures)

    if volume_mode == 'auto':
        actual_vol_mode = 'volume' if volumes else 'flat'
    else:
        actual_vol_mode = volume_mode if volume_mode != 'by_volume' else 'volume'

    dedup_func = DEDUP_STRATEGIES.get(dedup_strategy)
    chapters = dedup_func(all_chapters, actual_vol_mode)
    t_scan = time.time() - t0

    unit = chapters[0].get('ch_unit', '章') if chapters else '章'
    total = len(chapters)

    print(f"识别章节(原始): {len(all_chapters)}")
    print(f"去重策略: {dedup_strategy}")
    print(f"卷模式: {actual_vol_mode}")
    print(f"去重后章节: {total}  单位: {unit}")
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
    print(f"聚合拆分完成！共生成 {len(files)} 个文件")
    print(f"输出目录: {out_dir}")
    print(f"去重策略: {dedup_strategy}")
    print()
    print("【计时统计】")
    print(f"  读取文件: {t_read:.2f} 秒")
    print(f"  识别+去重: {t_scan:.2f} 秒")
    print(f"  写入文件: {t_write:.2f} 秒")
    print(f"  总计耗时: {t_total:.2f} 秒")


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
# CLI入口
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="TXT章节拆分工具 v3.1（去重+乱序修复+卷级感知增强版）")
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
                        help="深度分析：全面诊断所有问题")
    parser.add_argument("--dedup", default="lis",
                        choices=list(DEDUP_STRATEGIES.keys()),
                        help="去重策略: adjacent/first/longest/lis/sort (默认: lis)")
    parser.add_argument("--volume-mode", default="auto",
                        choices=["auto", "flat", "by_volume"],
                        help="卷级处理模式: auto(自动检测)/flat(扁平)/by_volume(按卷分目录)")
    parser.add_argument("--keep-title-only", action="store_true", default=False,
                        help="生成仅有标题/正文不足的章节文件")
    parser.add_argument("--min-body-len", type=int, default=0,
                        help="最小正文字数(0=不检测)")
    parser.add_argument("--clean", default=None,
                        help="清洁模式: N[,flag]")
    args = parser.parse_args()

    if args.analyze:
        if not args.src:
            parser.error("--analyze 需要 --src 参数")
        deep_analyze(args.src)
        return

    if not args.src:
        parser.error("拆分模式需要 --src 参数")

    mode = args.mode
    if args.chunk is not None and mode == "chapter":
        mode = "groups"

    merge_flag = None
    if args.clean is not None:
        clean_parts = args.clean.split(",")
        clean_min = int(clean_parts[0])
        clean_flag = int(clean_parts[1]) if len(clean_parts) > 1 else 1
        args.min_body_len = clean_min
        merge_flag = clean_flag
        mode = "chapter"

    try:
        if mode == "chapter":
            split_by_chapter(args.src, args.out, args.prefix, args.serial_width,
                             args.encoding, args.dedup, args.volume_mode,
                             args.keep_title_only, args.min_body_len, merge_flag)
        else:
            chunk_str = args.chunk if args.chunk else "40,3"
            split_by_groups(args.src, chunk_str, args.out, args.prefix,
                            args.serial_width, args.encoding, args.dedup,
                            args.volume_mode)
    except ValueError as e:
        print(f"[错误] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
