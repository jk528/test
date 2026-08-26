# -*- coding: utf-8 -*-
"""
用提取的178人完整数据重建归档索引的人物出场档案
"""

import os
import json
import re

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
output_dir = os.path.join(project_dir, '分析结果')

# 加载提取的人物数据
with open(os.path.join(output_dir, '人物档案_第1-19章.json'), 'r', encoding='utf-8') as f:
    persons_data = json.load(f)

# 读取当前归档索引
index_path = os.path.join(output_dir, '_归档索引.md')
with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 生成新的人物档案表
table_rows = []
for p in persons_data:
    # 状态演变：初登场（简化版，详细状态演变后续可逐步补充）
    status = '初登场'
    
    row = f'| {p["name"]} | 第{p["first_chapter"]}章 | {p["role"]} | {p["paragraph"]} | {status} |'
    table_rows.append(row)

new_table = '\n'.join(table_rows)

# 替换旧的人物档案表
# 找到"## 二、人物出场档案"到"---"之间的表格内容
old_section_match = re.search(
    r'(## 二、人物出场档案\n\n>.*?\n\n\| 人物名.*?\n\|--------.*?\n).*?(\n\n---)',
    content, re.DOTALL
)

if old_section_match:
    old_section = old_section_match.group(0)
    new_section = old_section_match.group(1) + new_table + old_section_match.group(2)
    
    content = content.replace(old_section, new_section)
    
    # 更新说明中的人数
    content = content.replace('累计去重178人', '累计去重178人')
    content = re.sub(r'累计去重\d+人', '累计去重178人', content)
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 验证
    print('人物档案表重建完成：')
    print(f'  总人数：{len(persons_data)}人')
    
    # 按章统计
    ch_counts = {}
    for p in persons_data:
        ch = p['first_chapter']
        ch_counts[ch] = ch_counts.get(ch, 0) + 1
    
    print('\n各章新出场人数：')
    cum = 0
    for ch in sorted(ch_counts.keys()):
        cum += ch_counts[ch]
        print(f'  第{ch:02d}章：{ch_counts[ch]:2d}人（累计{cum}人）')
    
    print(f'\n累计去重：{cum}人')
else:
    print('未找到人物档案表位置')
