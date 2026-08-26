# -*- coding: utf-8 -*-
"""生成逐章累计统计行和新出场人物数据，用于更新归档索引"""
import json, os

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..')

with open(os.path.join(project, '情感分析结果', 'detailed_index.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

# Previous cumulative (ch20)
prev_pos = 4965; prev_neg = 6413; prev_neu = 5418; prev_events = 322; prev_chars = 190

# Generate §三 rows
print("=== §三 逐章累计统计行 ===")
cum_pos = prev_pos; cum_neg = prev_neg; cum_neu = prev_neu; cum_events = prev_events; cum_chars = prev_chars

for r in data:
    ch = r['chapter']
    pw = r.get('pos_words', 0)
    nw = r.get('neg_words', 0)
    neu = r.get('neu_words', 0)
    ec = r.get('event_count', 0)
    cc = r.get('char_count', 0)
    ncc = r.get('new_char_count', 0)

    cum_pos += pw
    cum_neg += nw
    cum_neu += neu
    cum_events += ec
    cum_chars += ncc

    print(f"| {ch} | ~{pw} | ~{nw} | ~{neu} | {ec} | {cc} | {cum_pos} | {cum_neg} | {cum_neu} | {cum_events} | {cum_chars} |")

print(f"\n| **全书总计** | — | — | — | — | — | **{cum_pos}** | **{cum_neg}** | **{cum_neu}** | **{cum_events}** | **{cum_chars}** |")

# Generate §一 new chars column updates
print("\n=== §一 新出场人物列 ===")
for r in data:
    ch = r['chapter']
    ncc = r.get('new_char_count', 0)
    new_chars = r.get('new_chars', [])
    if ncc > 0:
        # Show first 3 names + count
        display = ', '.join(new_chars[:3])
        if ncc > 3:
            display += f"等{ncc}人"
        print(f"| {ch} | 新{ncc}人({display}) |")
    else:
        print(f"| {ch} | 0 |")

# Generate §二 character archive entries
print("\n=== §二 人物出场档案（第21-80章新出场人物） ===")
all_known = set()
# Rebuild known set from ch1-20
import re
report_dir = os.path.join(project, '分析结果')
for ch in range(1, 21):
    ch_str = f"{ch:03d}"
    for fn in os.listdir(report_dir):
        if fn.startswith(ch_str) and 'V33' in fn:
            with open(os.path.join(report_dir, fn), 'r', encoding='utf-8') as f:
                content = f.read()
            for m in re.finditer(r'\|\s+([^\|]+?)\s+\|\s+[★◆◇]\s+\|\s+(\d+)次\s+\|', content):
                name = m.group(1).strip()
                if len(name) <= 6:
                    all_known.add(name)
            break

for r in data:
    ch_num = int(r['chapter'])
    ch_str = r['chapter']
    new_chars = r.get('new_chars', [])
    for nc in new_chars:
        if nc not in all_known:
            all_known.add(nc)
            print(f"| {nc} | 第{ch_num}章 | ◇ 新出场角色 | §4.2 | 初登场 |")

print(f"\n累计人物（第80章止）: {len(all_known)}人")
