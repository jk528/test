# -*- coding: utf-8 -*-
"""
全面验证1-19章报告格式是否对齐第19章模板
检查所有##和###级别的章节结构
"""

import os
import re
import glob

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'

def get_headers(filepath):
    """提取文件中所有##和###级别的标题"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    headers = []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('### '):
            headers.append(('###', line.replace('### ', '')))
        elif line.startswith('## '):
            headers.append(('##', line.replace('## ', '')))
    
    return headers

def main():
    print('=' * 70)
    print('报告格式对齐验证：1-18章 vs 第19章（模板）')
    print('=' * 70)
    
    # 获取第19章作为模板
    template_path = os.path.join(output_dir, '019_情切切良宵花解语_意绵绵静日玉生香_双轨六要素分析报告.md')
    template_headers = get_headers(template_path)
    
    print(f'\n模板（第19章）章节结构：')
    print(f'  共 {len(template_headers)} 个标题')
    for level, title in template_headers:
        print(f'  {level} {title}')
    
    print('\n' + '=' * 70)
    print('逐章验证：')
    print('=' * 70)
    
    report_files = sorted(glob.glob(os.path.join(output_dir, '0[0-1][0-9]_*_双轨六要素分析报告.md')))
    report_files = [f for f in report_files if int(os.path.basename(f)[:3]) <= 18]
    
    all_pass = True
    results = []
    
    for fpath in report_files:
        basename = os.path.basename(fpath)
        ch_num = int(basename[:3])
        
        headers = get_headers(fpath)
        
        # 提取标题文本（去掉级别标记）
        template_titles = [t for _, t in template_headers]
        chapter_titles = [t for _, t in headers]
        
        # 找出差异
        missing = [t for t in template_titles if t not in chapter_titles]
        extra = [t for t in chapter_titles if t not in template_titles]
        
        # 计算##级别数量（大章节）
        template_h2 = sum(1 for l, _ in template_headers if l == '##')
        chapter_h2 = sum(1 for l, _ in headers if l == '##')
        
        passed = len(missing) == 0 and len(extra) == 0
        status = '✅' if passed else '❌'
        
        if not passed:
            all_pass = False
        
        results.append({
            'ch': ch_num,
            'status': status,
            'h2_count': chapter_h2,
            'total_count': len(headers),
            'missing': missing,
            'extra': extra,
        })
        
        print(f'\n第{ch_num:02d}章 {status}  (大章节{chapter_h2}个, 总标题{len(headers)}个)')
        if missing:
            print(f'  缺少：{missing}')
        if extra:
            print(f'  多余：{extra}')
    
    print('\n' + '=' * 70)
    print('验证汇总：')
    print('=' * 70)
    
    pass_count = sum(1 for r in results if r['status'] == '✅')
    print(f'\n通过：{pass_count}/18 章')
    print(f'模板大章节数：{sum(1 for l, _ in template_headers if l == "##")} 个')
    print(f'模板总标题数：{len(template_headers)} 个')
    
    if all_pass:
        print('\n🎉 全部18章格式与第19章模板完全对齐！')
    else:
        print('\n⚠ 存在差异的章节：')
        for r in results:
            if r['status'] == '❌':
                print(f'  第{r["ch"]:02d}章')

if __name__ == '__main__':
    main()
