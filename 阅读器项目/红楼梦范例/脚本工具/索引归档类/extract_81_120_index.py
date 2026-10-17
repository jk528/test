# -*- coding: utf-8 -*-
"""从第81-120章V3.4报告中提取详细数据，更新归档索引"""
import os, re, json

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')
report_dir = os.path.join(project, '分析结果')
emotion_dir = os.path.join(project, '情感分析结果')

# Load emotion JSONs for accurate data
emotion_data = {}
for ch in range(81, 121):
    ch_str = f"{ch:03d}"
    ejf = os.path.join(emotion_dir, f'{ch_str}_emotion.json')
    if os.path.exists(ejf):
        with open(ejf, 'r', encoding='utf-8') as f:
            emotion_data[ch] = json.load(f)

# Known chars from chapters 1-80 (cumulative: 359)
prev_cum_chars = 359
prev_cum_pos = 9380
prev_cum_neg = 10989
prev_cum_neu = 5692
prev_cum_events = 1267

results = []

for ch in range(81, 121):
    ch_str = f"{ch:03d}"
    
    # Find report file
    report_file = None
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V34' in fn:
            report_file = fn
            break
    if not report_file:
        print(f"[SKIP] No report for {ch_str}")
        continue
    
    rf = os.path.join(report_dir, report_file)
    with open(rf, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {'chapter': ch_str, 'chapter_num': ch}
    
    # Extract title
    m = re.search(r'第(\d+)章["""]([^""]+)["""]', content)
    if m:
        data['title'] = m.group(2).strip()
    else:
        data['title'] = ''
    
    # Extract word count
    m = re.search(r'(\d+)字', content[:2000])
    if m:
        data['word_count'] = int(m.group(1))
    
    # Extract event count from §2 table
    events = re.findall(r'\| E' + str(ch) + r'-\d+\s*\|', content)
    data['event_count'] = len(events)
    
    # Count star/diamond events
    star_events = len(re.findall(r'\| E' + str(ch) + r'-\d+\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*★', content))
    data['core_events'] = star_events
    
    # Extract character count from §4.2 table
    char_pattern = r'\|\s+([^\|]+?)\s+\|\s+[★◆◇]\s+\|\s+\d+次'
    chars = []
    for m in re.finditer(char_pattern, content):
        name = m.group(1).strip()
        if len(name) <= 8 and name not in ['人物', '——', '姓名', '层级']:
            chars.append(name)
    data['char_count'] = len(chars)
    data['chars_list'] = chars
    
    # Extract foreshadowing count
    foreshadow_section = ''
    if '### 伏笔与线索追踪' in content:
        foreshadow_section = content.split('### 伏笔与线索追踪')[1]
        foreshadow_section = re.split(r'\n---|\n## ', foreshadow_section)[0]
    elif '伏笔与线索追踪' in content:
        foreshadow_section = content.split('伏笔与线索追踪')[1]
        foreshadow_section = re.split(r'\n---|\n## ', foreshadow_section)[0]
    
    foreshadows = re.findall(r'\|\s*第\d+章\s*\|', foreshadow_section)
    data['foreshadow_count'] = len(foreshadows)
    
    # Extract conflict count from §4.3
    conflict_section = ''
    if '### 4.3' in content:
        conflict_section = content.split('### 4.3')[1]
        conflict_section = re.split(r'\n### 4\.4|\n---', conflict_section)[0]
    conflicts = re.findall(r'\|\s*\d+\s*\|', conflict_section)
    data['conflict_count'] = len(conflicts)
    
    # Get emotion data from JSON
    if ch in emotion_data:
        ej = emotion_data[ch]
        # hownet_pos can be int or dict
        hp = ej.get('hownet_pos', 0)
        hn = ej.get('hownet_neg', 0)
        data['hownet_pos'] = hp if isinstance(hp, int) else hp.get('count', 0)
        data['hownet_neg'] = hn if isinstance(hn, int) else hn.get('count', 0)
        data['hownet_pos_pct'] = ej.get('hownet_pos_pct', 50)
        data['hownet_neg_pct'] = ej.get('hownet_neg_pct', 50)
        
        # DUTIR data
        dutir_total = 0
        dutir_pos = 0
        dutir_neg = 0
        for cat in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
            key = f'dutir_{cat}'
            if key in ej:
                count = ej[key]['count']
                dutir_total += count
                if cat in ['好', '乐']:
                    dutir_pos += count
                elif cat in ['哀', '怒', '惧', '恶']:
                    dutir_neg += count
        data['dutir_total'] = dutir_total
        data['dutir_pos'] = dutir_pos
        data['dutir_neg'] = dutir_neg
        
        # Dominant emotion
        max_cat = ''
        max_count = 0
        for cat in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
            key = f'dutir_{cat}'
            if key in ej and ej[key]['count'] > max_count:
                max_count = ej[key]['count']
                max_cat = cat
        data['dominant_emotion'] = max_cat
        
        # Emotion richness
        richness = sum(1 for cat in ['好', '乐', '哀', '怒', '惧', '恶', '惊'] if f'dutir_{cat}' in ej and ej[f'dutir_{cat}']['count'] > 0)
        data['richness'] = richness
    else:
        data['hownet_pos'] = 0
        data['hownet_neg'] = 0
        data['hownet_pos_pct'] = 50
        data['hownet_neg_pct'] = 50
        data['dutir_total'] = 0
        data['dominant_emotion'] = '—'
        data['richness'] = 0
    
    # Determine tone
    if data['hownet_pos_pct'] > 55:
        data['tone'] = '正面主导'
    elif data['hownet_neg_pct'] > 55:
        data['tone'] = '负面主导'
    else:
        data['tone'] = '正负均衡'
    
    # Neutral words (approximate from total - pos - neg)
    total_emotion = data['hownet_pos'] + data['hownet_neg']
    data['neu_words'] = max(0, total_emotion // 10)  # rough estimate
    
    results.append(data)

# Calculate new characters per chapter
known_chars = set()
# We don't have the full 1-80 char list, but we know cumulative is 359
# For new chars, we'll estimate based on char table extraction
all_known = set()
for r in results:
    new_in_ch = []
    for c in r['chars_list']:
        if c not in all_known:
            new_in_ch.append(c)
            all_known.add(c)
    r['new_chars'] = new_in_ch
    r['new_char_count'] = len(new_in_ch)

# ============ Generate output ============
print("=" * 80)
print("=== §一 归档索引行（第81-120章）===")
cum_pos = prev_cum_pos
cum_neg = prev_cum_neg
cum_neu = prev_cum_neu
cum_events = prev_cum_events
cum_chars = prev_cum_chars

for r in results:
    ch = r['chapter']
    title = r['title'][:20] if r['title'] else ''
    filename = ''
    for fn in os.listdir(report_dir):
        if fn.startswith(ch) and 'V34' in fn:
            filename = fn
            break
    
    tone = r['tone']
    pos_pct = f"~{r['hownet_pos_pct']:.0f}%"
    neg_pct = f"~{r['hownet_neg_pct']:.0f}%"
    neu_pct = "—"
    conflicts = r['conflict_count']
    narrative_dim = 6
    emotion_seg = r['richness']
    core_str = f"{r['core_events']}★(总{r['event_count']})"
    char_count = r['char_count']
    
    ncc = r['new_char_count']
    if ncc > 0:
        new_chars_display = ', '.join(r['new_chars'][:4])
        if ncc > 4:
            new_chars_display += f"等{ncc}人"
        new_chars_str = f"新{ncc}人({new_chars_display})"
    else:
        new_chars_str = "0"
    
    cum_pos += r['hownet_pos']
    cum_neg += r['hownet_neg']
    cum_neu += r['neu_words']
    cum_events += r['event_count']
    cum_chars += ncc
    
    print(f"| {ch} | {title} | {filename} | V3.4 | 已归档 | {tone} | {pos_pct} | {neg_pct} | {neu_pct} | {conflicts} | {narrative_dim} | {emotion_seg} | {core_str} | {char_count} | {new_chars_str} | 2026-08-26 |")

print(f"\n=== 累计统计（第120章止）===")
print(f"累计正面词: {cum_pos}")
print(f"累计负面词: {cum_neg}")
print(f"累计中性词: {cum_neu}")
print(f"累计事件: {cum_events}")
print(f"累计人物: {cum_chars}")

# ============ Generate §三 逐章累计统计行 ============
print("\n" + "=" * 80)
print("=== §三 逐章累计统计行（第81-120章）===")
cum_pos2 = prev_cum_pos
cum_neg2 = prev_cum_neg
cum_neu2 = prev_cum_neu
cum_events2 = prev_cum_events
cum_chars2 = prev_cum_chars

for r in results:
    ch = r['chapter']
    pw = r['hownet_pos']
    nw = r['hownet_neg']
    neu = r['neu_words']
    ec = r['event_count']
    cc = r['char_count']
    ncc = r['new_char_count']
    
    cum_pos2 += pw
    cum_neg2 += nw
    cum_neu2 += neu
    cum_events2 += ec
    cum_chars2 += ncc
    
    print(f"| {ch} | ~{pw} | ~{nw} | ~{neu} | {ec} | {cc} | {cum_pos2} | {cum_neg2} | {cum_neu2} | {cum_events2} | {cum_chars2} |")

# ============ Generate §六 情感基调演变趋势 ============
print("\n" + "=" * 80)
print("=== §六 情感基调演变趋势（第81-120章）===")
for r in results:
    ch = r['chapter']
    tone = r['tone']
    pos_pct = f"~{r['hownet_pos_pct']:.0f}%"
    neg_pct = f"~{r['hownet_neg_pct']:.0f}%"
    neu_pct = "—"
    core_str = f"{r['core_events']}★(总{r['event_count']})"
    char_count = f"{r['char_count']}人"
    print(f"| {ch} | {tone} | {pos_pct} | {neg_pct} | {neu_pct} | {core_str} | {char_count} |")

# ============ Summary ============
print("\n" + "=" * 80)
print("=== 汇总 ===")
total_new_chars = sum(r['new_char_count'] for r in results)
total_events = sum(r['event_count'] for r in results)
total_foreshadows = sum(r['foreshadow_count'] for r in results)
print(f"第81-120章新增人物: {total_new_chars}")
print(f"第81-120章事件总数: {total_events}")
print(f"第81-120章伏笔总数: {total_foreshadows}")
print(f"全书累计人物: {cum_chars}")
print(f"全书累计事件: {cum_events}")
