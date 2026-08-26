# -*- coding: utf-8 -*-
"""验证全部19章V3.2结构一致性"""

import re, glob, os

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
files = sorted(glob.glob(os.path.join(output_dir, '???_*_双轨六要素分析报告.md')))
files = [f for f in files if 'V3.0存档' not in f]

print(f'共找到 {len(files)} 个报告文件\n')

all_ok = True
for fpath in files:
    fname = os.path.basename(fpath)
    ch_num = fname[:3]
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    h2_count = len(re.findall(r'^## ', content, re.MULTILINE))
    h3_count = len(re.findall(r'^### ', content, re.MULTILINE))
    
    has_v32 = 'V3.2' in content
    has_4_3 = bool(re.search(r'### 4\.3 冲突动机分析', content))
    has_4_4 = bool(re.search(r'### 4\.4 ', content))
    has_5_3_trend = bool(re.search(r'### 5\.3 情感趋势分析', content))
    has_5_7 = bool(re.search(r'### 5\.7 七类情绪分布', content))
    
    ok = (h2_count == 10 and has_4_3 and has_5_3_trend and has_v32 and has_5_7)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_ok = False
    
    print(f'[{status}] {ch_num}: h2={h2_count}, h3={h3_count}, 4.3={has_4_3}, 4.4={has_4_4}, 5.3trend={has_5_3_trend}, 5.7={has_5_7}, V3.2={has_v32}')

print(f'\n全部通过：{all_ok}')
