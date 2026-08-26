# -*- coding: utf-8 -*-
"""批量运行第81-120章情感分析"""
import os, sys, subprocess, json, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..')
output_dir = os.path.join(project, '情感分析结果')
os.makedirs(output_dir, exist_ok=True)

for ch in range(81, 121):
    ch_str = f"{ch:03d}"
    json_path = os.path.join(project, '红楼梦_分词结果', f'{ch_str}.json')
    if not os.path.exists(json_path):
        print(f"[SKIP] {ch_str}.json not found")
        continue

    output_file = os.path.join(output_dir, f'{ch_str}_emotion.json')
    if os.path.exists(output_file):
        print(f"[EXIST] {ch_str} already done")
        continue

    cmd = [sys.executable, os.path.join(base, 'batch_emotion_analysis.py'), ch_str]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project, encoding='utf-8')

    output = result.stdout
    data = {'chapter': ch_str, 'raw': output}

    # Parse DUTIR categories
    for cat in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
        m = re.search(rf'{cat}:\s*(\d+)\s*\(([\d.]+)%\)\s*words=\[([^\]]*)\]', output)
        if m:
            data[f'dutir_{cat}'] = {'count': int(m.group(1)), 'pct': float(m.group(2)), 'words': m.group(3)}

    # Parse Hownet
    m = re.search(r'正面词:\s*(\d+)\s*\(([\d.]+)%\)', output)
    if m:
        data['hownet_pos'] = {'count': int(m.group(1)), 'pct': float(m.group(2))}
    m = re.search(r'负面词:\s*(\d+)\s*\(([\d.]+)%\)', output)
    if m:
        data['hownet_neg'] = {'count': int(m.group(1)), 'pct': float(m.group(2))}
    m = re.search(r'中性词:\s*(\d+)\s*\(([\d.]+)%\)', output)
    if m:
        data['hownet_neu'] = {'count': int(m.group(1)), 'pct': float(m.group(2))}

    # Parse high frequency words
    m = re.search(r'高频词汇.*?\n((?:\d+\.\s+[^\n]+\n?)+)', output)
    if m:
        data['high_freq'] = m.group(1)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {ch_str}")

print("All chapters 81-120 emotion analysis complete.")
