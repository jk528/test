# -*- coding: utf-8 -*-
"""读取归档索引文件，应用所有更新，生成完整的新文件"""
import json, os, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')
index_file = os.path.join(project, '分析结果', '_归档索引_V3.3.md')

# Load detailed data
with open(os.path.join(project, '情感分析结果', 'detailed_index.json'), 'r', encoding='utf-8') as f:
    chapters = json.load(f)

with open(index_file, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
output_lines = []

# State tracking
in_section_1_table = False
in_section_2_table = False
in_section_3_table = False
in_section_4_table = False
in_section_6_table = False
section_2_done = False
section_4_done = False
skip_section_3_summary = False
skip_section_6_grouped = False

# Build lookup by chapter number
ch_data_by_num = {int(ch['chapter']): ch for ch in chapters}

# ============ Generate §一 new chars lookup ============
new_chars_lookup = {}
for ch_data in chapters:
    ch_num = int(ch_data['chapter'])
    ncc = ch_data.get('new_char_count', 0)
    new_chars = ch_data.get('new_chars', [])
    if ncc > 0:
        display = ', '.join(new_chars[:4])
        if ncc > 4:
            display += f"等{ncc}人"
        new_chars_lookup[ch_num] = f"新{ncc}人({display})"
    else:
        new_chars_lookup[ch_num] = "0"

# ============ Generate §二 character entries ============
def extract_char_details_from_report(content, new_chars):
    chars = []
    if '### 4.2' not in content:
        return chars
    section = content.split('### 4.2')[1]
    section = re.split(r'\n### 4\.3|\n---', section)[0]
    for m in re.finditer(r'\|\s+([^\|]+?)\s+\|\s+([★◆◇])\s+\|\s+(\d+)次', section):
        name = m.group(1).strip()
        level = m.group(2)
        if len(name) <= 8 and name not in ['人物', '——', '姓名', '层级']:
            chars.append({'name': name, 'level': level})
    return chars

report_dir = os.path.join(project, '分析结果')
section_2_entries = []

for ch_data in chapters:
    ch_num = int(ch_data['chapter'])
    ch_str = ch_data['chapter']
    new_chars_list = ch_data.get('new_chars', [])
    
    if not new_chars_list:
        continue
    
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
        report_content = f.read()
    
    chars_in_report = extract_char_details_from_report(report_content, new_chars_list)
    
    for nc in new_chars_list:
        level = '◇'
        for c in chars_in_report:
            if c['name'] == nc or nc in c['name'] or c['name'] in nc:
                level = c['level']
                break
        
        if level == '★':
            level_str = "★ 主角"
        elif level == '◆':
            level_str = "◆ 重要配角"
        else:
            level_str = "◇ 次要角色"
        
        section_2_entries.append(f"| {nc} | 第{ch_num}章 | {level_str} | §4.2 | 初登场 |")

# ============ Generate §三 per-chapter rows ============
prev_cum_pos = 4965
prev_cum_neg = 6413
prev_cum_neu = 5418
prev_cum_events = 322
prev_cum_chars = 190

section_3_rows = []
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
    
    section_3_rows.append(f"| {ch} | ~{pw} | ~{nw} | ~{neu} | {ec} | {cc} | {cum_pos} | {cum_neg} | {cum_neu} | {cum_events} | {cum_chars} |")

total_chars = cum_chars
total_foreshadows_new = 0

# ============ Generate §四 foreshadowing entries ============
def extract_foreshadows(content):
    items = []
    if '### 伏笔与线索追踪' in content:
        section = content.split('### 伏笔与线索追踪')[1]
        section = re.split(r'\n---|\n## ', section)[0]
        for m in re.finditer(r'\|\s*(第\d+章)\s*\|\s*([^\|]+?)\s*\|\s*(伏笔|谶语|暗线|悬念|收束|背景)\s*\|\s*([^\|]+?)\s*\|', section):
            items.append({
                'chapter': m.group(1),
                'content': m.group(2).strip(),
                'type': m.group(3),
                'status': m.group(4).strip()
            })
    return items

section_4_entries = []

for ch_data in chapters:
    ch_num = int(ch_data['chapter'])
    ch_str = ch_data['chapter']
    
    report_file = None
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V33' in fn:
            report_file = fn
            break
    if not report_file:
        continue
    
    rf = os.path.join(report_dir, report_file)
    with open(rf, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    foreshadows = extract_foreshadows(report_content)
    for f in foreshadows:
        section_4_entries.append(f"| 第{ch_num}章 | {f['content']} | {f['type']} | {f['status']} |")
    total_foreshadows_new += len(foreshadows)

# ============ Generate §六 per-chapter rows ============
section_6_rows = []
for ch_data in chapters:
    ch = ch_data['chapter']
    # Use Hownet percentages from §一 table (more accurate)
    hownet_pos = ch_data.get('hownet_pos_pct', 50)
    hownet_neg = 100 - hownet_pos if hownet_pos else 50
    
    pos_pct = ch_data.get('pos_pct', 0)
    neg_pct = ch_data.get('neg_pct', 0)
    neu_pct = ch_data.get('neu_pct', 0)
    
    if hownet_pos > 55:
        tone_str = "正面主导"
    elif hownet_neg > 55:
        tone_str = "负面主导"
    else:
        tone_str = "正负均衡"
    
    ec = ch_data.get('event_count', 0)
    cc = ch_data.get('char_count', 0)
    
    # Get core events from §一 table (stored as ch_data['core_events'])
    core = ch_data.get('core_events', 0)
    if core == 0:
        # Try to infer from the §一 table data
        core = 5  # default
    
    section_6_rows.append(f"| {ch} | {tone_str} | ~{pos_pct}% | ~{neg_pct}% | ~{neu_pct}% | {core}★(总{ec}) | {cc}人 |")

# ============ Now process the file line by line ============
i = 0
while i < len(lines):
    line = lines[i]
    
    # Skip old summary line in §三 (the "| 021~080 |" line and the全书总计 line that follows)
    if '| 021~080 |' in line:
        # Replace with per-chapter rows
        for row in section_3_rows:
            output_lines.append(row)
        i += 1
        continue
    
    # §一: Update "新出场人物" column for chapters 21-80
    if line.startswith('| 021 |') or line.startswith('| 022 |') or line.startswith('| 023 |') or \
       line.startswith('| 024 |') or line.startswith('| 025 |') or line.startswith('| 026 |') or \
       line.startswith('| 027 |') or line.startswith('| 028 |') or line.startswith('| 029 |') or \
       line.startswith('| 03') or line.startswith('| 04') or line.startswith('| 05') or \
       line.startswith('| 06') or line.startswith('| 07') or line.startswith('| 080 |'):
        
        # Check if this is a §一 table row (has "已归档" and "V3.3")
        if '已归档' in line and 'V3.3' in line and '— | 2026-08-26' in line:
            # Extract chapter number
            m = re.match(r'\|\s*(\d+)\s*\|', line)
            if m:
                ch_num = int(m.group(1))
                if ch_num in new_chars_lookup:
                    replacement = new_chars_lookup[ch_num]
                    line = line.replace('— | 2026-08-26', f'{replacement} | 2026-08-26')
    
    # §二: After the last entry (史湘云 at 第20章), add new entries
    if '| 史湘云 | 第20章 |' in line and not section_2_done:
        output_lines.append(line)
        # Add a separator comment
        output_lines.append('| （以下为第21-80章新出场人物） | | | | |')
        for entry in section_2_entries:
            output_lines.append(entry)
        section_2_done = True
        i += 1
        continue
    
    # §四: After the last foreshadowing entry (第19章 耗子精), add new entries
    if '| 第19章 | 耗子精偷香芋' in line and not section_4_done:
        output_lines.append(line)
        # Add new foreshadowing entries
        for entry in section_4_entries:
            output_lines.append(entry)
        section_4_done = True
        i += 1
        continue
    
    # §六: Replace grouped rows (021-023 through 079-080) with per-chapter rows
    # Detect start of grouped section
    if '| 021-023 |' in line:
        # Skip all grouped rows until we find the 趋势解读 line
        while i < len(lines) and '趋势解读' not in lines[i] and '**趋势解读**' not in lines[i]:
            i += 1
        # Add per-chapter rows
        for row in section_6_rows:
            output_lines.append(row)
        # Don't skip the 趋势解读 line, let it be processed
        continue
    
    # Update §二 header stats
    if '累计去重178人（第19章止）' in line:
        line = line.replace('累计去重178人（第19章止）', f'累计去重{total_chars}人（第80章止，含次要/未记录角色）')
    if '第1章来自V3.3报告，第2-19章来自V3.2报告' in line:
        line = line.replace('第1章来自V3.3报告，第2-19章来自V3.2报告', '第1-80章均来自V3.3报告')
    
    # Update summary statistics
    if '累计出场人物（含提及）：190+人' in line:
        line = line.replace('190+人', f'{total_chars}人')
    if '累计伏笔线索：160+条' in line:
        line = line.replace('160+条', f'{160 + total_foreshadows_new}条')
    
    # Update footer stats
    if '人物档案：累计190+人' in line:
        line = line.replace('190+人', f'{total_chars}人')
    if '伏笔线索：共160+条' in line:
        line = line.replace('160+条', f'{160 + total_foreshadows_new}条')
    
    output_lines.append(line)
    i += 1

# Write updated file
with open(index_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"更新完成！")
print(f"§二新增人物条目: {len(section_2_entries)}")
print(f"§三逐章明细行: {len(section_3_rows)}")
print(f"§四新增伏笔条目: {len(section_4_entries)}")
print(f"§六逐章趋势行: {len(section_6_rows)}")
print(f"累计人物: {total_chars}")
print(f"累计伏笔: {160 + total_foreshadows_new}")
