# -*- coding: utf-8 -*-
"""提取第21-80章的情感分析数据用于更新归档索引"""
import json, os, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')
emotion_dir = os.path.join(project, '情感分析结果')
report_dir = os.path.join(project, '分析结果')

results = []

for ch in range(21, 81):
    ch_str = f"{ch:03d}"
    emo_file = os.path.join(emotion_dir, f'{ch_str}_emotion.json')

    data = {'chapter': ch_str}

    # Read emotion JSON
    if os.path.exists(emo_file):
        with open(emo_file, 'r', encoding='utf-8') as f:
            emo = json.load(f)
        data['dutir_total'] = emo.get('dutir_total', 0)
        data['dutir_pos'] = emo.get('dutir_pos', 0)
        data['dutir_neg'] = emo.get('dutir_neg', 0)
        data['dutir_neu'] = emo.get('dutir_neu', 0)
        data['hownet_pos'] = emo.get('hownet_pos', 0)
        data['hownet_neg'] = emo.get('hownet_neg', 0)
        data['hownet_total'] = emo.get('hownet_total', 0)

        # Calculate percentages
        dut_total = data['dutir_total'] or 1
        data['dutir_pos_pct'] = round(data['dutir_pos'] / dut_total * 100, 1)
        data['dutir_neg_pct'] = round(data['dutir_neg'] / dut_total * 100, 1)

        how_total = data['hownet_total'] or 1
        data['hownet_pos_pct'] = round(data['hownet_pos'] / how_total * 100, 1)
        data['hownet_neg_pct'] = round(data['hownet_neg'] / how_total * 100, 1)

        # Extract DUTIR category data
        dutir_cats = {}
        for cat in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
            key = f'dutir_{cat}'
            if key in emo and isinstance(emo[key], dict):
                dutir_cats[cat] = emo[key].get('count', 0)
            else:
                dutir_cats[cat] = 0

        # Find dominant emotion
        dominant = max(dutir_cats, key=dutir_cats.get) if any(dutir_cats.values()) else '好'
        dominant_pct = round(dutir_cats[dominant] / dut_total * 100, 1) if dut_total > 1 else 0
        data['dominant_emotion'] = f"{dominant}({dominant_pct}%)"
        data['dutir_cats'] = dutir_cats

        # Count emotion categories present
        cats_present = sum(1 for v in dutir_cats.values() if v > 0)
        data['emotion_richness'] = f"{cats_present}/7"

        # Determine base tone
        if data['dutir_pos_pct'] > data['dutir_neg_pct']:
            data['base_tone'] = '正面主导'
        elif data['dutir_neg_pct'] > data['dutir_pos_pct']:
            data['base_tone'] = '负面主导'
        else:
            data['base_tone'] = '中性'

        # Cross-validation
        diff = abs(data['dutir_pos_pct'] - data['hownet_pos_pct'])
        data['cross_valid'] = '✅' if diff <= 15 else '⚠'

        # Top words
        if 'top_words' in emo:
            data['top_words'] = emo['top_words'][:5]

    # Try to get word count and chapter title from report file
    report_files = [f for f in os.listdir(report_dir) if f.startswith(ch_str) and 'V33' in f]
    if report_files:
        rf = os.path.join(report_dir, report_files[0])
        data['report_file'] = report_files[0]
        with open(rf, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract word count from §1.2
        m = re.search(r'字数统计.*?(\d+)字', content)
        if m:
            data['word_count'] = int(m.group(1))

        # Extract chapter title
        m = re.search(r'第\d+章"([^"]+)"', content)
        if m:
            data['title'] = m.group(1)

        # Count events (E{ch}-XX patterns)
        events = re.findall(rf'E{ch}-\d+', content)
        data['event_count'] = len(set(events))

        # Count characters in §4.2 table
        char_matches = re.findall(r'\| (.+?) \| [★◆◇]', content)
        data['char_count'] = len(set(char_matches)) if char_matches else 0

    results.append(data)

# Output summary
print("章号 | 标题 | 字数 | 事件数 | 人物数 | DUTIR正面% | DUTIR负面% | Hownet正面% | Hownet负面% | 主导情绪 | 丰富度 | 基调 | 一致性")
print("---|---|---|---|---|---|---|---|---|---|---|---|---")

for r in results:
    ch = r['chapter']
    title = r.get('title', '—')
    wc = r.get('word_count', '—')
    ec = r.get('event_count', '—')
    cc = r.get('char_count', '—')
    dp = r.get('dutir_pos_pct', '—')
    dn = r.get('dutir_neg_pct', '—')
    hp = r.get('hownet_pos_pct', '—')
    hn = r.get('hownet_neg_pct', '—')
    de = r.get('dominant_emotion', '—')
    er = r.get('emotion_richness', '—')
    bt = r.get('base_tone', '—')
    cv = r.get('cross_valid', '—')
    print(f"{ch} | {title} | {wc} | {ec} | {cc} | {dp} | {dn} | {hp} | {hn} | {de} | {er} | {bt} | {cv}")

# Also output JSON for further processing
output_file = os.path.join(project, '情感分析结果', 'index_summary.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSummary saved to {output_file}")
