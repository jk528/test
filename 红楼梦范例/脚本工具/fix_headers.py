# -*- coding: utf-8 -*-
"""
修复1-18章缺少标题和头部信息块的问题
为每章补上：
1. 一级标题：# 《红楼梦》第X章"标题"双轨六要素分析报告
2. 分析框架/分析日期/文本来源 引用块
3. --- 分隔线
"""

import os
import re
import glob

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
split_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\红楼梦_拆分'

def get_chapter_info(chapter_num):
    """从拆分文件获取章节标题和文件名"""
    pattern = os.path.join(split_dir, f'{chapter_num:03d}_*_第{chapter_num}章*.txt')
    files = glob.glob(pattern)
    if not files:
        return None, None
    
    fname = os.path.basename(files[0])
    
    # 提取标题
    match = re.search(rf'第{chapter_num}章[　 ]+(.*?)\.txt', fname)
    if match:
        title = match.group(1).replace('　', ' ')
    else:
        title = ''
    
    return title, fname


def fix_chapter(chapter_num):
    """修复单章的标题和头部信息"""
    
    # 找报告文件
    pattern = os.path.join(output_dir, f'{chapter_num:03d}_*_双轨六要素分析报告.md')
    files = glob.glob(pattern)
    files = [f for f in files if 'V3.0存档' not in f and 'V3.2存档' not in f]
    if not files:
        return False, '找不到报告文件'
    
    fpath = files[0]
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有标题
    if content.startswith('# 《红楼梦》'):
        return True, '已有标题，跳过'
    
    # 获取章节标题
    ch_title, text_fname = get_chapter_info(chapter_num)
    if not ch_title:
        return False, '无法获取章节标题'
    
    # 构建新的头部
    header = f'# 《红楼梦》第{chapter_num}章"{ch_title}"双轨六要素分析报告\n\n'
    header += f'> **分析框架**：双轨六要素分析体系 V3.2\n'
    header += f'> **分析日期**：2026-08-26\n'
    header += f'> **文本来源**：`{text_fname}`\n\n'
    header += '---\n\n'
    
    # 在文件开头插入
    content = header + content
    
    # 保存
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True, '已修复'


def main():
    print('修复1-18章标题和头部信息...\n')
    
    success = 0
    skipped = 0
    failed = []
    
    for ch in range(1, 19):
        ok, msg = fix_chapter(ch)
        ch_str = f'{ch:03d}'
        if ok:
            if '跳过' in msg:
                skipped += 1
                print(f'  [{ch_str}] 跳过：{msg}')
            else:
                success += 1
                print(f'  [{ch_str}] ✓ {msg}')
        else:
            failed.append(ch)
            print(f'  [{ch_str}] ✗ 失败：{msg}')
    
    print(f'\n完成：修复{success}章，跳过{skipped}章，失败{len(failed)}章')
    if failed:
        print(f'失败章节：{failed}')


if __name__ == '__main__':
    main()
