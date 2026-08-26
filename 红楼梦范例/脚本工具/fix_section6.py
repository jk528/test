# -*- coding: utf-8 -*-
"""修复§六情感基调演变趋势的数据，使用§一索引表的正确数据"""
import os, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..')
index_file = os.path.join(project, '分析结果', '_归档索引_V3.3.md')

with open(index_file, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Parse §一 table rows to extract correct data per chapter
# Row format: | 021 | ... | 正面主导 | ~56% | ~42% | ~2% | 5 | 6 | 8 | 8★(总15) | 27 | 新6人(...) | 2026-08-26 |
# We need: tone, pos%, neg%, neu%, core_events_string, char_count

ch_one_data = {}  # ch_num -> {tone, pos_pct, neg_pct, neu_pct, core_str, char_count}

in_section_1 = False
for line in lines:
    if '## 一、归档索引表' in line:
        in_section_1 = True
        continue
    if in_section_1 and line.startswith('## '):
        in_section_1 = False
        break
    if in_section_1 and line.startswith('|') and '已归档' in line:
        # Parse the row
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 15:
            ch_num = parts[1]
            tone = parts[6]
            pos_pct = parts[7]
            neg_pct = parts[8]
            neu_pct = parts[9]
            core_str = parts[13]  # e.g., "8★(总15)"
            char_count = parts[14]  # e.g., "27"

            try:
                ch_int = int(ch_num)
                ch_one_data[ch_int] = {
                    'tone': tone,
                    'pos_pct': pos_pct,
                    'neg_pct': neg_pct,
                    'neu_pct': neu_pct,
                    'core_str': core_str,
                    'char_count': char_count
                }
            except ValueError:
                pass

print(f"从§一表解析到 {len(ch_one_data)} 章数据")

# Now fix §六 rows for chapters 21-80
output_lines = []
in_section_6_table = False
section_6_header_found = False

for line in lines:
    # Detect §六 table data rows for chapters 021-080
    m = re.match(r'^\|\s*(02[1-9]|0[3-9]\d|080)\s*\|', line)

    # Check if we're in the §六 section (after "## 六、情感基调演变趋势")
    if '## 六、情感基调演变趋势' in line:
        in_section_6_table = True

    if in_section_6_table and m:
        ch_num = int(m.group(1))
        if ch_num in ch_one_data and ch_num >= 21:
            data = ch_one_data[ch_num]
            new_line = f"| {ch_num:03d} | {data['tone']} | {data['pos_pct']} | {data['neg_pct']} | {data['neu_pct']} | {data['core_str']} | {data['char_count']}人 |"
            output_lines.append(new_line)
            continue

    # Check if we've left §六 (hit the 趋势解读 or footer)
    if in_section_6_table and ('趋势解读' in line or line.startswith('*索引版本')):
        in_section_6_table = False

    output_lines.append(line)

with open(index_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print("§六修复完成！")
print(f"修复了 {len(ch_one_data)} 章的趋势数据")
