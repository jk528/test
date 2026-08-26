# -*- coding: utf-8 -*-
"""从第21-80章MD报告中提取逐章详细数据，用于补充归档索引"""
import json, os, re

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')
report_dir = os.path.join(project, '分析结果')
emo_dir = os.path.join(project, '情感分析结果')

results = []

# 已有人物集合（第1-20章）
known_chars = set()
# 读取第20章报告获取已知人物列表
for ch in range(1, 21):
    ch_str = f"{ch:03d}"
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V33' in fn:
            rf = os.path.join(report_dir, fn)
            with open(rf, 'r', encoding='utf-8') as f:
                content = f.read()
            # Extract characters from §4.2 table
            char_matches = re.findall(r'\|\s+([^\|]+?)\s+\|\s+[★◆◇]', content)
            for c in char_matches:
                c = c.strip()
                if len(c) <= 6 and c not in ['人物', '——']:
                    known_chars.add(c)
            break

print(f"已知人物（第1-20章）: {len(known_chars)}人")

for ch in range(21, 81):
    ch_str = f"{ch:03d}"
    data = {'chapter': ch_str}

    # Find report file
    report_file = None
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V33' in fn:
            report_file = fn
            break

    if not report_file:
        print(f"[SKIP] No report for {ch_str}")
        continue

    rf = os.path.join(report_dir, report_file)
    with open(rf, 'r', encoding='utf-8') as f:
        content = f.read()

    data['report_file'] = report_file

    # Extract title
    m = re.search(r'第\d+章"([^"]+)"', content)
    if m:
        data['title'] = m.group(1)

    # Extract word count
    m = re.search(r'字数统计.*?(\d+)字', content)
    if m:
        data['word_count'] = int(m.group(1))

    # Extract event count - count unique E{ch}-XX
    events = set(re.findall(rf'E{ch}-\d+', content))
    data['event_count'] = len(events)

    # Count core events (★)
    core_events = len(re.findall(rf'E{ch}-\d+.*?★', content))
    data['core_events'] = core_events

    # Extract characters from §4.2 table
    # Pattern: | name | level | count | ...
    char_pattern = r'\|\s+([^\|]+?)\s+\|\s+[★◆◇]\s+\|\s+(\d+)次\s+\|'
    chars_in_chapter = []
    for m in re.finditer(char_pattern, content):
        name = m.group(1).strip()
        count = int(m.group(2))
        if len(name) <= 6 and name not in ['人物', '——', '姓名']:
            chars_in_chapter.append({'name': name, 'count': count, 'is_new': name not in known_chars})

    data['char_count'] = len(chars_in_chapter)
    new_chars = [c['name'] for c in chars_in_chapter if c['is_new']]
    data['new_chars'] = new_chars
    data['new_char_count'] = len(new_chars)

    # Update known chars
    for c in chars_in_chapter:
        known_chars.add(c['name'])

    # Extract conflict count from §4.3
    conflicts = re.findall(r'\|\s*\d+\s*\|.*?人vs|命运冲突|身份冲突', content)
    data['conflict_count'] = len(conflicts)

    # Count conflicts more accurately - rows in §4.3 table
    conflict_section = content.split('### 4.3')[1].split('### 4.4')[0] if '### 4.3' in content and '### 4.4' in content else ''
    conflict_rows = re.findall(r'\|\s*\d+\s*\|', conflict_section)
    data['conflict_count'] = len(conflict_rows)

    # Extract emotion data from §5.1
    m = re.search(r'正面词\s*\|\s*(\d+)\s*\|\s*([\d.]+)%', content)
    if m:
        data['pos_words'] = int(m.group(1))
        data['pos_pct'] = float(m.group(2))

    m = re.search(r'负面词\s*\|\s*(\d+)\s*\|\s*([\d.]+)%', content)
    if m:
        data['neg_words'] = int(m.group(1))
        data['neg_pct'] = float(m.group(2))

    m = re.search(r'中性词\s*\|\s*(\d+)\s*\|\s*([\d.]+)%', content)
    if m:
        data['neu_words'] = int(m.group(1))
        data['neu_pct'] = float(m.group(2))

    # Extract DUTIR total from §5.7
    m = re.search(r'合计\s*\|\s*—\s*\|\s*(\d+)\s*\|\s*100%', content)
    if m:
        data['dutir_total'] = int(m.group(1))

    # Extract dominant emotion
    m = re.search(r'主导情绪\s*\|\s*([好乐哀怒惧恶惊])\（([^）]+)\）', content)
    if m:
        data['dominant_emotion'] = f"{m.group(1)}({m.group(2)})"

    # Extract emotion richness
    m = re.search(r'情绪丰富度\s*\|\s*(\d+)/7\s*\(?(\d+)%\)?', content)
    if m:
        data['emotion_richness'] = f"{m.group(1)}/7"

    # Extract Hownet data from §8.2
    m = re.search(r'正面词占比\s*\|\s*([\d.]+)%\s*\|\s*([\d.]+)%', content)
    if m:
        data['hownet_pos_pct'] = float(m.group(1))
        data['dutir_pos_pct_82'] = float(m.group(2))

    # Extract foreshadowing from §6 or §9.2
    foreshadow_section = ''
    if '### 9.2' in content:
        foreshadow_section = content.split('### 9.2')[1].split('### 9.3')[0]
    elif '伏笔与线索追踪' in content:
        foreshadow_section = content.split('伏笔与线索追踪')[1].split('---')[0] if '---' in content.split('伏笔与线索追踪')[1] else ''

    foreshadow_rows = re.findall(r'\|\s*第\d+章\s*\|', foreshadow_section)
    data['foreshadow_count'] = len(foreshadow_rows)

    # Extract foreshadowing content
    foreshadow_items = []
    for m in re.finditer(r'\|\s*(第\d+章)\s*\|\s*([^\|]+?)\s*\|\s*(伏笔|谶语|暗线|悬念|收束)\s*\|', foreshadow_section):
        foreshadow_items.append({
            'chapter': m.group(1),
            'content': m.group(2).strip(),
            'type': m.group(3)
        })
    data['foreshadows'] = foreshadow_items

    results.append(data)

# Output summary
print(f"\n章号 | 正面词 | 负面词 | 中性词 | 事件数 | 人物数 | 新人物数 | 冲突数 | 伏笔数 | 新人物列表")
print("---|---|---|---|---|---|---|---|---|---")

for r in results:
    ch = r['chapter']
    pw = r.get('pos_words', '—')
    nw = r.get('neg_words', '—')
    neu = r.get('neu_words', '—')
    ec = r.get('event_count', '—')
    cc = r.get('char_count', '—')
    ncc = r.get('new_char_count', '—')
    cf = r.get('conflict_count', '—')
    fc = r.get('foreshadow_count', '—')
    nc = ', '.join(r.get('new_chars', [])[:5])
    if len(r.get('new_chars', [])) > 5:
        nc += f"...(共{ncc}人)"
    print(f"{ch} | {pw} | {nw} | {neu} | {ec} | {cc} | {ncc} | {cf} | {fc} | {nc}")

# Save full data
output_file = os.path.join(project, '情感分析结果', 'detailed_index.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n详细数据已保存到 {output_file}")
print(f"累计人物（第80章止）: {len(known_chars)}人")
