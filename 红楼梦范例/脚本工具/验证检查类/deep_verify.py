# -*- coding: utf-8 -*-
"""
深度验证脚本 - 检查更多维度的一致性
1. 数据占位符数量一致性
2. 完整性检测项数量一致性
3. §5子章节编号顺序正确性
4. 版本号三处一致性（头部/尾部/检测）
"""

import re, glob, os

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
files = sorted(glob.glob(os.path.join(output_dir, '???_*_双轨六要素分析报告.md')))
files = [f for f in files if 'V3.0存档' not in f and 'V3.2存档' not in f]

print('深度验证：' + str(len(files)) + ' 个文件\n')

all_ok = True
issues = []

for fpath in files:
    fname = os.path.basename(fpath)
    ch = fname[:3]
    chapter_issues = []
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 检查§5子章节顺序
    h5_sections = re.findall(r'^### (5\.\d+) ', content, re.MULTILINE)
    expected_h5 = ['5.1', '5.2', '5.3', '5.4', '5.5', '5.6', '5.7']
    if h5_sections != expected_h5:
        chapter_issues.append('§5子章节顺序不对: ' + str(h5_sections))
    
    # 2. 检查版本号一致性
    header_v32 = bool(re.search(r'分析框架.*V3\.2', content))
    tail_v32 = '报告版本：V3.2' in content
    detect_v32 = bool(re.search(r'模板.*V3\.2', content))
    if not (header_v32 and tail_v32 and detect_v32):
        chapter_issues.append('版本号不一致: header=' + str(header_v32) + ' tail=' + str(tail_v32) + ' detect=' + str(detect_v32))
    
    # 3. 检查流程版本一致性
    header_v18 = bool(re.search(r'分析流程.*v1\.8', content))
    tail_v18 = '流程版本：v1.8' in content
    detect_v18 = '流程v1.8' in content
    if not (header_v18 and tail_v18):
        chapter_issues.append('流程版本不一致: header=' + str(header_v18) + ' tail=' + str(tail_v18))
    
    # 4. 检查数据占位符数量
    data_placeholder_match = re.search(r'### 7\.4 数据占位符\n\n\|.*?\n.*?\n(.*?)(?=\n### 7\.5)', content, re.DOTALL)
    if data_placeholder_match:
        rows = [l for l in data_placeholder_match.group(1).strip().split('\n') if l.strip().startswith('|')]
        if len(rows) < 20:
            chapter_issues.append('数据占位符太少: ' + str(len(rows)) + '项')
    
    # 5. 检查完整性检测项
    integrity_match = re.search(r'### 8\.3 完整性检测.*?\n\n\|.*?\n.*?\n(.*?)(?=\n### 8\.4)', content, re.DOTALL)
    if integrity_match:
        rows = [l for l in integrity_match.group(1).strip().split('\n') if l.strip().startswith('|')]
        if len(rows) < 6:
            chapter_issues.append('完整性检测项太少: ' + str(len(rows)) + '项')
    
    # 6. 检查§4.3和§4.4的内容不为空
    has_43_content = bool(re.search(r'### 4\.3 冲突动机分析\n\n.*?\n\| 序号', content, re.DOTALL))
    has_44_content = bool(re.search(r'### 4\.4 .*?\n\n.*?\n\| 维度 \|', content, re.DOTALL))
    if not has_43_content:
        chapter_issues.append('§4.3内容为空或格式不对')
    if not has_44_content:
        chapter_issues.append('§4.4内容为空或格式不对')
    
    if chapter_issues:
        all_ok = False
        issues.append((ch, chapter_issues))
        status = 'FAIL'
    else:
        status = 'PASS'
    
    print('[' + status + '] ' + ch)
    for issue in chapter_issues:
        print('       - ' + issue)

print('\n' + '='*50)
print('全部通过：' + str(all_ok))
if issues:
    print('有问题的章节：' + str(len(issues)) + ' 个')
