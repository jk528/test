import os, re, json

report_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'
files = sorted([f for f in os.listdir(report_dir) if f.endswith('_V33_分析报告.md')])

print('=== Extracting data from V3.3 reports ===\n')

results = []
for fname in files:
    fpath = os.path.join(report_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    ch = int(fname[:3])

    # Extract word count
    wc_match = re.search(r'字数统计\s*\|\s*(\d+)字', content)
    word_count = int(wc_match.group(1)) if wc_match else 0

    # Extract event count
    events = set(re.findall(r'E\d{2}-\d{2}', content))
    event_count = len(events)

    # Count star/diamond events
    star_events = content.count('★')
    diamond_events = content.count('◆')

    # Extract character count from §7.1
    sec71 = re.search(r'### 7\.1.*?(\n## (?:七|八))', content, re.DOTALL)
    char_count = 0
    if sec71:
        table_text = sec71.group(0)
        # Count rows that start with | and don't contain ---
        rows = [l for l in table_text.split('\n') if l.strip().startswith('|') and '---' not in l and '人物名' not in l]
        char_count = len(rows)

    # Extract emotion counts from §5.1
    sec51 = re.search(r'### 5\.1.*?(?:### 5\.2|## 六)', content, re.DOTALL)
    pos_count = neg_count = neu_count = 0
    if sec51:
        sec51_text = sec51.group(0)
        pos_match = re.search(r'正面词[^\d]*(\d+)', sec51_text)
        neg_match = re.search(r'负面词[^\d]*(\d+)', sec51_text)
        neu_match = re.search(r'中性词[^\d]*(\d+)', sec51_text)
        if pos_match: pos_count = int(pos_match.group(1))
        if neg_match: neg_count = int(neg_match.group(1))
        if neu_match: neu_count = int(neu_match.group(1))

    # Extract DUTIR total
    dutir_match = re.search(r'DUTIR[^0-9]*(\d+)\s*个', content)
    dutir_total = int(dutir_match.group(1)) if dutir_match else 0

    # Extract baseline
    baseline_match = re.search(r'情感基调[:：]\s*(.+?)(?:\n|$)', content)
    baseline = baseline_match.group(1).strip() if baseline_match else ''

    # Extract conflict count from §4.3
    sec43_start = content.find('### 4.3')
    sec44_start = content.find('### 4.4')
    conflict_count = 0
    if sec43_start >= 0 and sec44_start >= 0:
        sec43_text = content[sec43_start:sec44_start]
        conflict_count = len(re.findall(r'^\| \d', sec43_text, re.MULTILINE))

    # Extract narrative dimensions from §4.4
    sec44_start_pos = content.find('### 4.4')
    sec5_start = content.find('## 五')
    narrative_dims = 0
    if sec44_start_pos >= 0 and sec5_start >= 0:
        sec44_text = content[sec44_start_pos:sec5_start]
        narrative_dims = sec44_text.count('|')

    # Extract emotion segments from §5.3
    sec53_start = content.find('### 5.3')
    sec54_start = content.find('### 5.4')
    emotion_segments = 0
    if sec53_start >= 0 and sec54_start >= 0:
        sec53_text = content[sec53_start:sec54_start]
        emotion_segments = len(re.findall(r'^\|', sec53_text, re.MULTILINE))
        if emotion_segments > 0:
            emotion_segments -= 2  # subtract header rows

    # Calculate percentages
    total_emo = pos_count + neg_count + neu_count
    pos_pct = round(pos_count / total_emo * 100) if total_emo > 0 else 0
    neg_pct = round(neg_count / total_emo * 100) if total_emo > 0 else 0
    neu_pct = round(neu_count / total_emo * 100) if total_emo > 0 else 0

    print('Ch%03d: words=%d events=%d chars=%d pos=%d(%d%%) neg=%d(%d%%) neu=%d(%d%%) dutir=%d conflicts=%d segs=%d | %s' % (
        ch, word_count, event_count, char_count,
        pos_count, pos_pct, neg_count, neg_pct, neu_count, neu_pct,
        dutir_total, conflict_count, emotion_segments, baseline[:30]))

    results.append({
        'chapter': ch,
        'word_count': word_count,
        'event_count': event_count,
        'char_count': char_count,
        'pos': pos_count, 'neg': neg_count, 'neu': neu_count,
        'pos_pct': pos_pct, 'neg_pct': neg_pct, 'neu_pct': neu_pct,
        'dutir_total': dutir_total,
        'baseline': baseline,
        'conflict_count': conflict_count,
        'emotion_segments': emotion_segments,
        'narrative_dims': 6  # V3.3 template has 6 dimensions
    })

# Save
out_path = os.path.join(report_dir, 'v33_extracted_data.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nSaved to:', out_path)
print('Total chapters:', len(results))
