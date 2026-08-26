# -*- coding: utf-8 -*-
"""
更新归档索引：在中性词%后插入3列（冲突数/叙事维度/情感分段）
"""

import os

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
index_path = os.path.join(output_dir, '_归档索引.md')

with open(index_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_index_table = False
table_started = False

for i, line in enumerate(lines):
    # 检测归档索引表的表头
    if '| 章号 | 章节标题 | 文件名 | 分析状态 | 情感基调 | 正面词% | 负面词% | 中性词% | 核心事件数 |' in line:
        # 更新表头：在中性词%后插入3列
        new_line = line.replace(
            '| 中性词% | 核心事件数 |',
            '| 中性词% | 冲突数 | 叙事维度 | 情感分段 | 核心事件数 |'
        )
        new_lines.append(new_line)
        in_index_table = True
        table_started = True
        print(f'  行{i+1}: 更新表头')
        continue
    
    # 检测分隔行
    if in_index_table and table_started and '|------|' in line and '核心事件数' not in line and not line.strip().startswith('| 0'):
        # 更新分隔行
        new_line = line.replace(
            '|---------|-----------|',
            '|---------|--------|----------|----------|-----------|'
        )
        new_lines.append(new_line)
        print(f'  行{i+1}: 更新分隔行')
        continue
    
    # 检测数据行（| 数字 | 标题 | ...格式）
    if in_index_table and line.strip().startswith('| 0') and '章' not in line[:20]:
        # 解析列，在中性词%后插入3个占位符
        cells = [c.strip() for c in line.split('|')]
        # 列索引：
        # 0: '', 1:章号, 2:标题, 3:文件名, 4:状态, 5:基调, 6:正面%, 7:负面%, 8:中性%, 
        # 9:核心事件数, 10:出场人物数, 11:新出场人物, 12:归档日期, 13:''
        if len(cells) >= 13:
            # 在第9列（中性%）后插入3列
            new_cells = cells[:9] + ['—', '—', '—'] + cells[9:]
            new_line = '| ' + ' | '.join(c for c in new_cells[1:-1]) + ' |\n'
            new_lines.append(new_line)
        else:
            new_lines.append(line)
        continue
    
    # 检测表格结束（遇到空行且后面不是数据行）
    if in_index_table and line.strip() == '' and i+1 < len(lines):
        next_line = lines[i+1].strip()
        # 如果下一行是"**索引统计**"或"## 二、"之类的，说明表格结束
        if next_line.startswith('**') or next_line.startswith('## '):
            in_index_table = False
            new_lines.append(line)
            print(f'  行{i+1}: 表格结束')
            continue
    
    new_lines.append(line)

# 保存
with open(index_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('\n归档索引表更新完成！')
