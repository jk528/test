# -*- coding: utf-8 -*-
"""
修复人物出场档案的章节顺序
确保严格按照首次出场章号从小到大排列
"""

import os
import re

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
index_path = os.path.join(output_dir, '_归档索引.md')

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取人物出场档案表
match = re.search(
    r'## 二、人物出场档案\n\n>.*?\n\n\|.*?\n.*?\n(.*?)\n\n---',
    content, re.DOTALL
)

if match:
    table_text = match.group(1).strip()
    table_start = match.start()
    table_end = match.end()
    
    # 解析每行
    rows = []
    for line in table_text.split('\n'):
        line = line.strip()
        if not line or not line.startswith('|'):
            continue
        
        # 提取章号
        ch_match = re.search(r'第(\d+)章', line)
        if ch_match:
            ch_num = int(ch_match.group(1))
            rows.append((ch_num, line))
        else:
            rows.append((999, line))  # 无法识别的放最后
    
    # 按章号排序
    rows.sort(key=lambda x: x[0])
    
    # 重新组装表格
    sorted_lines = [line for _, line in rows]
    new_table = '\n'.join(sorted_lines)
    
    # 替换
    old_table_section = match.group(0)
    # 保持标题和说明不变，只替换表格内容
    new_section = re.sub(
        r'(\| 人物名.*?\n\|--------.*?\n).*?(\n\n---)',
        r'\1' + new_table + r'\2',
        old_table_section,
        flags=re.DOTALL
    )
    
    content = content.replace(old_table_section, new_section)
    
    # 统计各章人物数
    ch_counts = {}
    for ch, _ in rows:
        ch_counts[ch] = ch_counts.get(ch, 0) + 1
    
    print('人物出场档案已按章号排序：')
    for ch in sorted(ch_counts.keys()):
        if ch <= 19:
            print(f'  第{ch:02d}章：{ch_counts[ch]}人')
    
    print(f'\n总计：{len(rows)}人')
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('\n修复完成！')
else:
    print('未找到人物出场档案表')
