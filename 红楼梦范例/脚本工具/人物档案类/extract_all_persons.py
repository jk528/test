# -*- coding: utf-8 -*-
"""
从1-19章报告的§7.1人物占位符中提取全部出场人物
补全人物档案表
"""

import os
import re
import glob

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
output_dir = os.path.join(project_dir, '分析结果')


def extract_persons_from_report(chapter_num):
    """从单章报告的§7.1提取人物列表"""
    
    # 找文件
    pattern = os.path.join(output_dir, f'{chapter_num:03d}_*_双轨六要素分析报告.md')
    files = glob.glob(pattern)
    if not files:
        return []
    
    with open(files[0], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取§7.1人物占位符
    sec7_1_match = re.search(
        r'### 7\.1 人物占位符\n\n\|.*?\n.*?\n(.*?)(?=\n### 7\.2)',
        content, re.DOTALL
    )
    
    if not sec7_1_match:
        return []
    
    table_text = sec7_1_match.group(1)
    persons = []
    
    for line in table_text.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        
        cells = [c.strip() for c in line.split('|')]
        # 表格格式：| 序号 | 人物名 | 身份/角色 | 出场段落 |
        if len(cells) >= 5:
            name = cells[2]
            role = cells[3]
            paragraph = cells[4]
            
            # 跳过表头和分隔行
            if name == '人物名' or '---' in name:
                continue
            
            persons.append({
                'name': name,
                'role': role,
                'paragraph': paragraph,
                'chapter': chapter_num,
            })
    
    return persons


def main():
    print('=' * 60)
    print('提取1-19章全部出场人物')
    print('=' * 60)
    
    all_persons = {}  # name -> info
    chapter_persons = {}  # chapter -> [names]
    
    for ch in range(1, 20):
        persons = extract_persons_from_report(ch)
        chapter_persons[ch] = [p['name'] for p in persons]
        
        for p in persons:
            name = p['name']
            if name not in all_persons:
                all_persons[name] = {
                    'first_chapter': ch,
                    'role': p['role'],
                    'paragraph': p['paragraph'],
                }
        
        print(f'  第{ch:02d}章：{len(persons)}人出场，累计{len(all_persons)}人')
    
    # 按首次出场章号排序
    sorted_persons = sorted(all_persons.items(), key=lambda x: (x[1]['first_chapter'], x[0]))
    
    print(f'\n总计：{len(sorted_persons)}人')
    
    # 每章新出场统计
    ch_new = {}
    for name, info in sorted_persons:
        ch = info['first_chapter']
        ch_new[ch] = ch_new.get(ch, 0) + 1
    
    print('\n各章新出场人物：')
    for ch in sorted(ch_new.keys()):
        print(f'  第{ch:02d}章：{ch_new[ch]}人')
    
    # 保存为JSON供后续使用
    output_data = []
    for name, info in sorted_persons:
        output_data.append({
            'name': name,
            'first_chapter': info['first_chapter'],
            'role': info['role'],
            'paragraph': info['paragraph'],
        })
    
    import json
    output_path = os.path.join(output_dir, '人物档案_第1-19章.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f'\n数据已保存到：{output_path}')
    
    # 生成人物档案表的markdown
    table_rows = []
    for name, info in sorted_persons:
        row = f'| {name} | 第{info["first_chapter"]}章 | {info["role"]} | {info["paragraph"]} | 初登场 |'
        table_rows.append(row)
    
    print('\n人物档案表预览（前10行）：')
    for row in table_rows[:10]:
        print(f'  {row}')


if __name__ == '__main__':
    main()
