import json, os, re

# Load extracted data
with open(r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\v33_extracted_data.json', 'r', encoding='utf-8') as f:
    extracted = json.load(f)

# Load emotion data
emo_data = []
with open(r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\情绪分析数据\ch01-18_emotion_analysis.json', 'r', encoding='utf-8') as f:
    emo_data = json.load(f)
try:
    with open(r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\情绪分析数据\ch19-20_emotion_analysis.json', 'r', encoding='utf-8') as f:
        emo_data.extend(json.load(f))
except:
    pass

# Also load ch1 V3.3 test report data
ch1_data = {
    'chapter': 1, 'word_count': 6928, 'event_count': 17, 'char_count': 18,
    'pos': 95, 'neg': 210, 'neu': 195, 'pos_pct': 18, 'neg_pct': 42, 'neu_pct': 40,
    'dutir_total': 238, 'baseline': '负面主导', 'conflict_count': 4, 'emotion_segments': 6, 'narrative_dims': 6
}

# Merge all data
all_data = [ch1_data] + extracted
emo_by_ch = {e['chapter']: e for e in emo_data}

# Chapter titles
titles = {
    1: '甄士隐梦幻识通灵 贾雨村风尘怀闺秀',
    2: '贾夫人仙逝扬州城 冷子兴演说荣国府',
    3: '托内兄如海荐西宾 接外孙贾母惜孤女',
    4: '薄命女偏逢薄命郎 葫芦僧判断葫芦案',
    5: '贾宝玉神游太虚境 警幻仙曲演红楼梦',
    6: '贾宝玉初试云雨情 刘老老一进荣国府',
    7: '送宫花贾琏戏熙凤 宴宁府宝玉会秦钟',
    8: '贾宝玉奇缘识金锁 薛宝钗巧合认通灵',
    9: '训劣子李贵承申饬 嗔顽童茗烟闹书房',
    10: '金寡妇贪利权受辱 张太医论病细穷源',
    11: '庆寿辰宁府排家宴 见熙凤贾瑞起淫心',
    12: '王熙凤毒设相思局 贾天祥正照风月鉴',
    13: '秦可卿死封龙禁尉 王熙凤协理宁国府',
    14: '林如海灵返苏州郡 贾宝玉路遏北静王',
    15: '王凤姐弄权铁槛寺 秦鲸卿得趣馒头庵',
    16: '贾元春才选凤藻宫 秦鲸卿夭逝黄泉路',
    17: '大观园试才题对额 荣国府归省庆元宵',
    18: '皇恩重元妃省父母 天伦乐宝玉呈才藻',
    19: '情切切良宵花解语 意绵绵静日玉生香',
    20: '王熙凤正言弹妒意 林黛玉俏语谑娇音',
}

# New character counts per chapter (from V3.3 reports, approximate)
new_chars = {
    1: 18, 2: 24, 3: 17, 4: 11, 5: 10, 6: 8, 7: 13,
    8: 5, 9: 12, 10: 7, 11: 6, 12: 4, 13: 10, 14: 5,
    15: 6, 16: 8, 17: 10, 18: 3, 19: 5, 20: 8
}

# Calculate cumulative stats
cumulative_pos = 0
cumulative_neg = 0
cumulative_neu = 0
cumulative_events = 0
cumulative_chars = 0
cumulative_new_chars = 0

# Build index table rows
index_rows = []
stats_rows = []
trend_rows = []
emo_rows = []

for d in all_data:
    ch = d['chapter']
    wc = d['word_count']
    ec = d['event_count']
    cc = d['char_count']
    pos = d['pos']
    neg = d['neg']
    neu = d['neu']
    pos_pct = d.get('pos_pct', 0)
    neg_pct = d.get('neg_pct', 0)
    neu_pct = d.get('neu_pct', 0)
    baseline = d.get('baseline', '')
    conflicts = d.get('conflict_count', 0)
    segments = d.get('emotion_segments', 0)
    nar_dims = 6

    # Get DUTIR data from emotion JSON
    dutir_total = 0
    dutir_dominant = ''
    dutir_pos_pct = 0
    dutir_neg_pct = 0
    hownet_pos_pct = 0
    hownet_neg_pct = 0

    if ch in emo_by_ch:
        ed = emo_by_ch[ch]
        if 'dutir' in ed:
            dd = ed['dutir']
            dutir_total = dd.get('total', 0)
            ec2 = dd.get('emotion_counts', {})
            if ec2:
                dutir_dominant = max(ec2, key=ec2.get)
                total_emo = sum(ec2.values())
                pos_cats = sum(ec2.get(k, 0) for k in ['好', '乐'])
                neg_cats = sum(ec2.get(k, 0) for k in ['恶', '哀', '惧', '怒'])
                dutir_pos_pct = round(pos_cats / total_emo * 100) if total_emo > 0 else 0
                dutir_neg_pct = round(neg_cats / total_emo * 100) if total_emo > 0 else 0
        if 'hownet' in ed:
            hd = ed['hownet']
            ht = hd.get('pos_count', 0) + hd.get('neg_count', 0)
            hownet_pos_pct = round(hd.get('pos_count', 0) / ht * 100) if ht > 0 else 0
            hownet_neg_pct = round(hd.get('neg_count', 0) / ht * 100) if ht > 0 else 0

    # Override with known DUTIR data for ch19-20
    if ch == 19:
        dutir_total = 172
        dutir_dominant = '恶'
    elif ch == 20:
        dutir_total = 131
        dutir_dominant = '恶'

    nc = new_chars.get(ch, 0)

    cumulative_pos += pos
    cumulative_neg += neg
    cumulative_neu += neu
    cumulative_events += ec
    cumulative_chars += cc
    cumulative_new_chars += nc

    fname = '%03d_%s_V33_分析报告.md' % (ch, titles[ch].split(' ')[0][:8])
    if ch == 1:
        fname = '001_甄士隐梦幻识通灵_V33_测试报告.md'

    index_rows.append('| %03d | %s | %s | V3.3 | 已归档 | %s | ~%d%% | ~%d%% | ~%d%% | %d | %d | %d | %d★(总%d) | %d | %d | 2026-08-26 |' % (
        ch, titles[ch], fname, baseline, pos_pct, neg_pct, neu_pct,
        conflicts, nar_dims, segments, ec, ec, cc, nc))

    stats_rows.append('| %03d | ~%d | ~%d | ~%d | %d | %d | %d | %d | %d | %d | %d |' % (
        ch, pos, neg, neu, ec, cc, cumulative_pos, cumulative_neg, cumulative_neu,
        cumulative_events, cumulative_new_chars))

    trend_rows.append('| %03d | %s | ~%d%% | ~%d%% | ~%d%% | %d★(总%d) | %d人 |' % (
        ch, baseline, pos_pct, neg_pct, neu_pct, ec, ec, cc))

    # Emotion summary row
    consistency = '✅' if abs(dutir_pos_pct - hownet_pos_pct) <= 15 else '⚠'
    emo_rows.append('| %03d | %d | %s(%s) | %d%% | %d%% | — | %d%% | %d%% | %s |' % (
        ch, dutir_total, dutir_dominant, '',
        dutir_pos_pct, dutir_neg_pct,
        hownet_pos_pct, hownet_neg_pct, consistency))

# Print summary
print('=== Archive Index Data Summary ===')
print('Total chapters: %d' % len(all_data))
print('Total positive words: %d' % cumulative_pos)
print('Total negative words: %d' % cumulative_neg)
print('Total neutral words: %d' % cumulative_neu)
print('Total events: %d' % cumulative_events)
print('Total characters (cumulative): %d' % cumulative_new_chars)

# Save for use in index update
out = {
    'index_rows': index_rows,
    'stats_rows': stats_rows,
    'trend_rows': trend_rows,
    'emo_rows': emo_rows,
    'totals': {
        'pos': cumulative_pos,
        'neg': cumulative_neg,
        'neu': cumulative_neu,
        'events': cumulative_events,
        'chars': cumulative_new_chars
    }
}
with open(r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\v33_index_data.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('\nSaved index data.')
