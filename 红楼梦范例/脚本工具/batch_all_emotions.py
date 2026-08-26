# -*- coding: utf-8 -*-
"""批量运行第1-120章情感分析，结果保存到JSON文件（跳过已存在）"""
import json, sys, os, subprocess

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..')
output_dir = os.path.join(project, '情感分析结果')
os.makedirs(output_dir, exist_ok=True)

for ch in range(1, 121):
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
        import re
        m = re.search(rf'{cat}:\s*(\d+)\s*\(([\d.]+)%\)\s*words=\[([^\]]*)\]', output)
        if m:
            data[f'dutir_{cat}'] = {'count': int(m.group(1)), 'pct': float(m.group(2)), 'words': m.group(3)}

    m = re.search(r'DUTIR_TOTAL:\s*(\d+)', output)
    if m: data['dutir_total'] = int(m.group(1))
    m = re.search(r'POS:\s*(\d+)\s*NEG:\s*(\d+)\s*NEU:\s*(\d+)', output)
    if m: data['dutir_pos'] = int(m.group(1)); data['dutir_neg'] = int(m.group(2)); data['dutir_neu'] = int(m.group(3))

    m = re.search(r'pos:\s*(\d+)\s*neg:\s*(\d+)', output)
    if m: data['hownet_pos'] = int(m.group(1)); data['hownet_neg'] = int(m.group(2))
    m = re.search(r"pos%:\s*([\d.]+)\s*neg%:\s*([\d.]+)", output)
    if m: data['hownet_pos_pct'] = float(m.group(1)); data['hownet_neg_pct'] = float(m.group(2))
    m = re.search(r'total:\s*(\d+)', output)
    if m: data['hownet_total'] = int(m.group(1))

    m = re.search(r'pos_words:\s*\[([^\]]*)\]', output)
    if m: data['hownet_pos_words'] = m.group(1)
    m = re.search(r'neg_words:\s*\[([^\]]*)\]', output)
    if m: data['hownet_neg_words'] = m.group(1)

    m = re.findall(r'(\S+):\s*(\d+)', output.split('--- Top 30 words ---')[1] if '--- Top 30 words ---' in output else '')
    if m: data['top_words'] = [{'word': w, 'count': int(c)} for w, c in m[:30]]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {ch_str}")

print("All chapters processed.")
