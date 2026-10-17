# -*- coding: utf-8 -*-
"""综合提取脚本：从第21-80章报告中提取所有缺失数据，生成归档索引更新内容"""
import json, os, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')
report_dir = os.path.join(project, '分析结果')

# Load existing detailed data
with open(os.path.join(project, '情感分析结果', 'detailed_index.json'), 'r', encoding='utf-8') as f:
    chapters = json.load(f)

# Also load chapters 1-20 data from the existing index for cumulative calculations
# We'll read the existing §三 table to get cumulative values up to chapter 20
prev_cum_pos = 4965
prev_cum_neg = 6413
prev_cum_neu = 5418
prev_cum_events = 322
prev_cum_chars = 190

# ============ Extract foreshadowing data ============
def extract_foreshadows(content, ch_num):
    """Extract foreshadowing entries from report"""
    items = []
    # Try "### 伏笔与线索追踪" section first
    if '### 伏笔与线索追踪' in content:
        section = content.split('### 伏笔与线索追踪')[1]
        # Find the table - stop at next ### or ---
        section = re.split(r'\n---|\n## ', section)[0]
        for m in re.finditer(r'\|\s*(第\d+章)\s*\|\s*([^\|]+?)\s*\|\s*(伏笔|谶语|暗线|悬念|收束|背景)\s*\|\s*([^\|]+?)\s*\|', section):
            items.append({
                'chapter': m.group(1),
                'content': m.group(2).strip(),
                'type': m.group(3),
                'status': m.group(4).strip()
            })
    return items

# ============ Extract character details ============
def extract_char_details(content, ch_num):
    """Extract character details from §4.2 table"""
    chars = []
    # Find §4.2 section
    if '### 4.2' not in content:
        return chars
    section = content.split('### 4.2')[1]
    section = re.split(r'\n### 4\.3|\n---', section)[0]
    
    # Pattern: | name | level | count | paragraphs | behavior | emotion | dialogue% | relations | motive | role | status |
    for m in re.finditer(r'\|\s+([^\|]+?)\s+\|\s+([★◆◇])\s+\|\s+(\d+)次', section):
        name = m.group(1).strip()
        level = m.group(2)
        count = int(m.group(3))
        if len(name) <= 8 and name not in ['人物', '——', '姓名', '层级']:
            chars.append({'name': name, 'level': level, 'count': count})
    return chars

# ============ Extract chapter title ============
def extract_title(content):
    m = re.search(r'第\d+章["""]([^""]+)["""]', content)
    if m:
        return m.group(1)
    m = re.search(r'## 《红楼梦》第\d+章["""]([^""]+)["""]', content)
    if m:
        return m.group(1)
    return ""

# ============ Process all chapters ============
all_foreshadows = []
all_new_chars = {}  # chapter -> list of new chars with details

# Known chars from chapters 1-20 (we'll build this from the detailed_index data)
known_chars = set()
# The detailed_index already tracked new chars, so let's use that

for ch_data in chapters:
    ch_num = int(ch_data['chapter'])
    ch_str = ch_data['chapter']
    
    # Find report file
    report_file = None
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V33' in fn:
            report_file = fn
            break
    
    if not report_file:
        continue
    
    rf = os.path.join(report_dir, report_file)
    with open(rf, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract foreshadowing
    foreshadows = extract_foreshadows(content, ch_num)
    all_foreshadows.extend(foreshadows)
    ch_data['foreshadows'] = foreshadows
    
    # Extract new character details
    chars = extract_char_details(content, ch_num)
    new_chars_list = ch_data.get('new_chars', [])
    
    char_details = []
    for nc in new_chars_list:
        for c in chars:
            if c['name'] == nc or nc in c['name'] or c['name'] in nc:
                char_details.append({
                    'name': nc,
                    'level': c['level'],
                    'count': c['count'],
                    'chapter': ch_num
                })
                break
        else:
            char_details.append({
                'name': nc,
                'level': '◇',
                'count': 0,
                'chapter': ch_num
            })
    
    all_new_chars[ch_num] = char_details

# ============ Generate §一 新出场人物列 ============
print("=" * 80)
print("=== §一 新出场人物列（第21-80章）===")
for ch_data in chapters:
    ch = ch_data['chapter']
    ncc = ch_data.get('new_char_count', 0)
    new_chars = ch_data.get('new_chars', [])
    if ncc > 0:
        display = ', '.join(new_chars[:4])
        if ncc > 4:
            display += f"等{ncc}人"
        print(f"| {ch} | 新{ncc}人({display}) |")
    else:
        print(f"| {ch} | 0 |")

# ============ Generate §二 人物出场档案条目 ============
print("\n" + "=" * 80)
print("=== §二 人物出场档案条目（第21-80章新出场人物）===")
for ch_num in sorted(all_new_chars.keys()):
    for c in all_new_chars[ch_num]:
        level_str = "★ 主角" if c['level'] == '★' else ("◆ 重要配角" if c['level'] == '◆' else "◇ 次要角色")
        print(f"| {c['name']} | 第{ch_num}章 | {level_str} | §4.2 | 初登场 |")

# ============ Generate §三 逐章累计统计行 ============
print("\n" + "=" * 80)
print("=== §三 逐章累计统计行（第21-80章）===")
cum_pos = prev_cum_pos
cum_neg = prev_cum_neg
cum_neu = prev_cum_neu
cum_events = prev_cum_events
cum_chars = prev_cum_chars

for ch_data in chapters:
    ch = ch_data['chapter']
    pw = ch_data.get('pos_words', 0)
    nw = ch_data.get('neg_words', 0)
    neu = ch_data.get('neu_words', 0)
    ec = ch_data.get('event_count', 0)
    cc = ch_data.get('char_count', 0)
    ncc = ch_data.get('new_char_count', 0)
    
    cum_pos += pw
    cum_neg += nw
    cum_neu += neu
    cum_events += ec
    cum_chars += ncc
    
    print(f"| {ch} | ~{pw} | ~{nw} | ~{neu} | {ec} | {cc} | {cum_pos} | {cum_neg} | {cum_neu} | {cum_events} | {cum_chars} |")

print(f"\n全书总计: 正面{cum_pos} | 负面{cum_neg} | 中性{cum_neu} | 事件{cum_events} | 人物{cum_chars}")

# ============ Generate §四 伏笔线索追踪条目 ============
print("\n" + "=" * 80)
print("=== §四 伏笔线索追踪条目（第21-80章）===")
for ch_data in chapters:
    ch = ch_data['chapter']
    foreshadows = ch_data.get('foreshadows', [])
    if foreshadows:
        for f in foreshadows:
            print(f"| 第{int(ch)}章 | {f['content']} | {f['type']} | {f['status']} |")

# ============ Generate §六 情感基调演变趋势（逐章）============
print("\n" + "=" * 80)
print("=== §六 情感基调演变趋势（第21-80章逐章）===")
for ch_data in chapters:
    ch = ch_data['chapter']
    tone = ch_data.get('dominant_emotion', '—')
    pos_pct = ch_data.get('pos_pct', 0)
    neg_pct = ch_data.get('neg_pct', 0)
    neu_pct = ch_data.get('neu_pct', 0)
    hownet_pos = ch_data.get('hownet_pos_pct', 0)
    hownet_neg = 100 - hownet_pos if hownet_pos else 0
    ec = ch_data.get('event_count', 0)
    cc = ch_data.get('char_count', 0)
    core = ch_data.get('core_events', 0)
    
    # Determine tone
    if hownet_pos > 55:
        tone_str = "正面主导"
    elif hownet_neg > 55:
        tone_str = "负面主导"
    else:
        tone_str = "正负均衡"
    
    print(f"| {ch} | {tone_str} | ~{pos_pct}% | ~{neg_pct}% | ~{neu_pct}% | {core}★(总{ec}) | {cc}人 |")

# ============ Summary stats ============
print("\n" + "=" * 80)
print("=== 汇总统计 ===")
total_foreshadows = sum(len(ch_data.get('foreshadows', [])) for ch_data in chapters)
total_new_chars = sum(ch_data.get('new_char_count', 0) for ch_data in chapters)
print(f"第21-80章新增伏笔条目: {total_foreshadows}")
print(f"第21-80章新增人物: {total_new_chars}")
print(f"第80章止累计人物: {cum_chars}")
print(f"第80章止累计伏笔: 160+{total_foreshadows}")
print(f"第80章止累计正面词: {cum_pos}")
print(f"第80章止累计负面词: {cum_neg}")
print(f"第80章止累计中性词: {cum_neu}")
print(f"第80章止累计事件: {cum_events}")
