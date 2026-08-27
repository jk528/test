# -*- coding: utf-8 -*-
"""从 v34_extract2.json 生成 _归档索引_V3.4.md"""
import json, os, re

WORK = r'c:\Users\Administrator\.trae-cn\work\6a8e88bd38e645ba57bc4277'
OUT = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\_归档索引_V3.4.md'

data = json.load(open(os.path.join(WORK, 'v34_extract2.json'), encoding='utf-8'))
data.sort(key=lambda d: d['no'])

ARCHIVE_DATE = '2026-08-26'

# ---------- 名称归一化 ----------
# 同人别名 → 规范名（规范名取最常用称呼）
ALIAS = {
    '黛玉': '林黛玉', '林黛玉': '林黛玉',
    '宝玉': '贾宝玉', '贾宝玉': '贾宝玉',
    '凤姐': '王熙凤', '凤姐儿': '王熙凤', '王熙凤': '王熙凤',
    '秦氏': '秦可卿', '秦可卿': '秦可卿', '兼美/可卿': '秦可卿', '兼美': '秦可卿',
    '宝钗': '薛宝钗', '薛宝钗': '薛宝钗',
    '湘云': '史湘云', '史湘云': '史湘云', '史大姑娘': '史湘云', '史大姑娘/湘云': '史湘云',
    '元春': '贾元春', '元妃': '贾元春', '贾妃/元春': '贾元春', '贾元春（贾妃）': '贾元春', '贾元春': '贾元春', '贾妃': '贾元春',
    '雨村': '贾雨村', '贾雨村': '贾雨村',
    '刘老老': '刘姥姥', '刘姥姥': '刘姥姥',
    '周瑞媳妇': '周瑞家的', '周瑞家的': '周瑞家的',
    '岫烟': '邢岫烟', '邢岫烟': '邢岫烟',
    '香菱/秋菱': '香菱', '秋菱': '香菱', '香菱': '香菱',
    '金桂': '夏金桂', '夏金桂': '夏金桂',
    '玉钏': '玉钏儿', '玉钏儿': '玉钏儿',
    '智能': '智能儿', '智能儿': '智能儿',
    '金钏': '金钏儿', '金钏儿': '金钏儿',
    '焙茗': '茗烟', '茗烟': '茗烟',
    '北静王(水溶)': '北静王', '北静王（世荣）': '北静王', '北静王': '北静王',
    '夏秉忠(夏太监)': '夏秉忠', '夏秉忠': '夏秉忠',
    '金氏（璜大奶奶）': '金氏', '金氏': '金氏',
    '山子野(胡老名公)': '山子野', '山子野': '山子野',
    '贾夫人（贾敏）': '贾敏', '贾敏': '贾敏',
    '静虚(老尼)': '静虚', '静虚': '静虚',
    '史大姑娘': '史湘云',
    '迎春': '贾迎春', '探春': '贾探春', '惜春': '贾惜春',
    '五儿': '柳五儿', '柳五儿': '柳五儿',
    '守备之子': '守备公子', '守备公子': '守备公子',
}

# 情感基调标准标签映射（报告内表述不统一，归一为6类）
TONE_MAP = {
    '正面主导': '正面主导',
    '负面主导': '负面主导', '负面强主导': '负面主导',
    '中性主导': '中性主导',
    '正负均衡': '正负均衡', '正负平衡': '正负均衡',
    '中性偏高偏正': '中性偏正',
    '中性偏高偏负': '中性偏负',
    '正面略占主导': '中性偏正', '正面略主导': '中性偏正', '正面微弱主导': '中性偏正',
    '正负接近平衡，正面略主导': '中性偏正',
    '负面略占主导': '中性偏负', '负面略主导': '中性偏负',
}

def norm_tone(t):
    t = (t or '').strip()
    return TONE_MAP.get(t, t)

def split_names(raw):
    """处理组合条目，返回规范名列表"""
    raw = raw.strip()
    if raw == '元春/迎春/探春/惜春':
        return ['贾元春', '贾迎春', '贾探春', '贾惜春']
    return [ALIAS.get(raw, raw)]

# ---------- 计算首次出场（规范名） ----------
first = {}       # 规范名 -> 章号
first_meta = {}  # 规范名 -> {lvl, para, role, status} at first appearance
for d in data:
    for c in d['char_list']:
        for n in split_names(c['name']):
            n = n.strip()
            if n not in first:
                first[n] = d['no']
                first_meta[n] = {'lvl': c['lvl'], 'para': c['para'].strip(), 'role': c['role'].strip(), 'status': c['status'].strip()}

# 每章新出场规范名
newmap = {}
for d in data:
    lst = []
    for c in d['char_list']:
        for n in split_names(c['name']):
            n = n.strip()
            if first[n] == d['no']:
                lst.append(n)
    # 去重保序
    seen = set(); out = []
    for n in lst:
        if n not in seen:
            seen.add(n); out.append(n)
    newmap[d['no']] = out

total_chars = len(first)

# ---------- 视图函数 ----------
def into(f):
    return int(round(f))

def tone_label(d):
    return norm_tone(d['tone'] or d['tone_raw'] or '—')

def dom_label(d):
    cats = d['cats']
    if not cats:
        return (d.get('dom') or '—')
    maxpct = max(c['pct'] for c in cats.values())
    tops = [k for k, c in cats.items() if c['pct'] == maxpct]
    if len(tops) == 1:
        return '%s(%.1f%%)' % (tops[0], maxpct)
    return '%s并列(各%.1f%%)' % ('/'.join(tops), maxpct)

def tone_stat(d):
    cats = d['cats']
    pos = cats['好']['pct'] + cats['乐']['pct']
    neg = cats['哀']['pct'] + cats['怒']['pct'] + cats['惧']['pct'] + cats['恶']['pct']
    neu = cats['惊']['pct']
    return pos, neg, neu

def tone3d_stat(d):
    """索引表/趋势表用的三维统计占比（§5.1，取整）"""
    p = d.get('p3d_pct') or 0.0
    n = d.get('n3d_pct') or 0.0
    e = d.get('e3d_pct') or 0.0
    return into(p), into(n), into(e)

def tone3d_cnt(d):
    """逐章累计统计用的三维词数（§5.1）"""
    p = d.get('p3d') or 0
    n = d.get('n3d') or 0
    e = d.get('e3d')
    if e is None:
        e = d['cats'].get('惊', {}).get('cnt', 0)
    return p, n, e

def events_label(d):
    return '%d★(总%d)' % (d['stars'], d['events'])

# ---------- 构建文档 ----------
L = []
def a(s=''):
    L.append(s)

# ===== 头部 =====
a('# 红楼梦章节分析归档索引')
a('')
a('> **文件类型**：全局归档索引')
a('> **维护规则**：每章归档后追加一行；每章复测后更新状态；每周检查连续性')
a('> **参照规范**：`skill/章节分析归档规范.md` v1.3（§4.3-4.8）')
a('> **参照流程**：`skill/章节内容分析流程.md` v2.0（含§2.1.2事件拆分颗粒度规则）')
a('> **模板版本**：V3.4（双轨六要素 + 七类情绪分析 + 冲突/叙事/情感趋势 + 事件颗粒度规则 + 预言人物表）')
a('> **流程版本**：v2.0')
a('> **归档规范**：v1.3')
a('> **索引版本**：v3.2（V3.4体系）')
a('> **创建日期**：%s' % ARCHIVE_DATE)
a('> **更新日期**：%s（第1-80章全部V3.4从原文重新生成完毕）' % ARCHIVE_DATE)
a('')
a('> 涵盖范围：第1-80章，共80份V3.4分析报告（存于 `分析结果/V3.4存档_1-80章/`）')
a('> 人物统计口径：宽口径，累计去重人名计 %d 个（含直接出场、间接提及；别名已按规范名归并）' % total_chars)
a('')
a('---')
a('')
a('## 目录')
a('')
a('- [一、归档索引表](#一归档索引表)')
a('- [二、人物出场档案](#二人物出场档案)')
a('- [三、逐章累计统计](#三逐章累计统计)')
a('- [四、伏笔线索追踪](#四伏笔线索追踪)')
a('- [五、七类情绪分析汇总](#五七类情绪分析汇总)')
a('- [六、情感基调演变趋势](#六情感基调演变趋势)')
a('- [七、全局统计摘要](#七全局统计摘要)')
a('')
a('---')
a('')

# ===== 一、归档索引表 =====
a('## 一、归档索引表')
a('')
a('| 章号 | 章节标题 | 文件名 | 模板版本 | 分析状态 | 情感基调 | 正面词% | 负面词% | 中性词% | 冲突数 | 叙事维度 | 情感分段 | 核心事件数 | 出场人物数 | 新出场人物 | 归档日期 |')
a('|------|---------|--------|---------|---------|---------|---------|---------|---------|--------|----------|----------|-----------|-----------|-----------|---------|')

for d in data:
    pos, neg, neu = tone3d_stat(d)
    newcnt = len(newmap[d['no']])
    if newcnt == 0:
        new_s = '0'
    elif newcnt <= 4:
        new_s = '新%d人(%s)' % (newcnt, '、'.join(newmap[d['no']]))
    else:
        new_s = '新%d人(%s等%d人)' % (newcnt, '、'.join(newmap[d['no']][:3]), newcnt)
    a('| %03d | %s | %s | V3.4 | 已归档 | %s | ~%d%% | ~%d%% | ~%d%% | %d | 6 | %d | %s | %d | %s | %s |'
      % (d['no'], d['title'], d['file'], tone_label(d), into(pos), into(neg), into(neu), d['conf'], d['segs'], events_label(d), d['chars'], new_s, ARCHIVE_DATE))
a('')
a('---')
a('')

# ===== 二、人物出场档案 =====
a('## 二、人物出场档案')
a('')
a('> 按名字首次出场章号排序；累计去重人物 %d 个（宽口径，别名归并；组合条目"元春/迎春/探春/惜春"已拆分）' % total_chars)
a('')
a('| 序号 | 人物名 | 层级 | 首次出场章号 | 首次出场身份 | 首次出场段落 |')
a('|------|--------|------|-----------|------------|------------|')

items = sorted(first.items(), key=lambda kv: (kv[1], kv[0]))
for i, (name, ch) in enumerate(items, 1):
    m = first_meta[name]
    a('| %d | %s | %s | 第%d章 | %s | %s |' % (i, name, m['lvl'], ch, m['role'], m['para']))
a('')
a('---')
a('')

# ===== 三、逐章累计统计 =====
a('## 三、逐章累计统计')
a('')
a('| 章号 | 正面词数 | 负面词数 | 中性词数 | 事件数 | 本章人物 | 累计正面词 | 累计负面词 | 累计中性词 | 累计事件 | 累计去重人物 |')
a('|------|---------|---------|---------|--------|---------|-----------|-----------|-----------|---------|-------------|')

cum_pos = cum_neg = cum_neu = cum_ev = 0
cum_char = 0
cum_char_set = set()
for d in data:
    # 词数（三维统计 §5.1）
    pl, nl, ntl = tone3d_cnt(d)
    cum_pos += pl; cum_neg += nl; cum_neu += ntl; cum_ev += d['events']
    for c in d['char_list']:
        for n in split_names(c['name']):
            cum_char_set.add(n.strip())
    cum_char = len(cum_char_set)
    a('| %03d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |'
      % (d['no'], pl, nl, ntl, d['events'], d['chars'], cum_pos, cum_neg, cum_neu, cum_ev, cum_char))

a('| **全书总计(1-80)** | — | — | — | — | — | **%d** | **%d** | **%d** | **%d** | **%d** |'
  % (cum_pos, cum_neg, cum_neu, cum_ev, cum_char))
a('')
a('---')
a('')

# ===== 四、伏笔线索追踪 =====
a('## 四、伏笔线索追踪')
a('')
fb_all = []
for d in data:
    for row in d['foreshadows']:
        fb_all.append((d['no'], row))
# 去掉表头行
fb_rows = [(no, r) for no, r in fb_all if r[0] != '伏笔内容']
a('| 章号 | 线索内容 | 类型 | 预计回收章节范围 |')
a('|------|---------|------|----------------|')
for no, r in fb_rows:
    a('| %03d | %s | %s | %s |' % (no, r[0], r[1], r[2] if len(r) > 2 else '—'))
a('')
# 类型统计
from collections import Counter
typc = Counter(r[1] for _, r in fb_rows)
typs = '、'.join('%s(%d条)' % (k, v) for k, v in typc.items())
a('> 伏笔线索合计 %d 条；类型分布：%s' % (len(fb_rows), typs))
a('')
a('---')
a('')

# ===== 五、七类情绪分析汇总 =====
a('## 五、七类情绪分析汇总（DUTIR + Hownet 双轨）')
a('')
a('| 章号 | DUTIR词数 | 主导情绪 | DUTIR正面% | DUTIR负面% | 正负比 | 情绪丰富度 | Hownet正面% | Hownet负面% | 基调一致 |')
a('|------|----------|---------|-----------|-----------|--------|-----------|------------|------------|---------|')
for d in data:
    pos, neg, neu = tone_stat(d)
    if d['h_pos'] is not None and d['h_neg'] is not None:
        diff = abs(d['h_pos'] - pos)
        base = '✅' if diff <= 15 else '⚠'
    else:
        base = '—'
    a('| %03d | %d | %s | %.1f%% | %.1f%% | %s | %s | %s | %s | %s |'
      % (d['no'], d['d_total'], dom_label(d), pos, neg, d['ratio'], d['rich'],
         (('%.1f%%' % d['h_pos']) if d['h_pos'] is not None else '—'),
         (('%.1f%%' % d['h_neg']) if d['h_neg'] is not None else '—'),
         base))
a('')
a('> 一致性标准（规范§4.7）：DUTIR正面% vs Hownet正面% 差异 ≤15%% 为一致（✅），>15%% 为告警（⚠）')
a('')
a('---')
a('')

# ===== 六、情感基调演变趋势 =====
a('## 六、情感基调演变趋势')
a('')
a('| 章号 | 情感基调 | 正面% | 负面% | 中性% | 核心事件 | 出场人物 |')
a('|------|---------|-------|-------|-------|---------|---------|')
for d in data:
    pos, neg, neu = tone3d_stat(d)
    a('| %03d | %s | ~%d%% | ~%d%% | ~%d%% | %s | %d人 |'
      % (d['no'], tone_label(d), into(pos), into(neg), into(neu), events_label(d), d['chars']))
a('')
# 趋势解读：按阶段归纳
a('### 趋势解读')
a('')
a('全书1-80章情感基调按叙事阶段归纳如下（以三维统计正/负/中性词占比为据）：')
a('')
a('| 阶段 | 章号范围 | 情感特征 |')
a('|------|---------|---------|')
a('| 1 | 1-5 | 开篇铺垫期：神话缘起与黛玉进府，基调波动，正负交织 |')
a('| 2 | 6-8 | 世情描写期：一进荣国府与秦钟入塾、识金锁，倾向中性偏负 |')
a('| 3 | 9-16 | 冲突密集期：相思局/秦氏之死/弄权铁槛寺/元妃才选，负面持续主导 |')
a('| 4 | 17-20 | 省亲回暖与摩擦期：大观园题额、元妃省亲回暖，兼有情绪研磨 |')
a('| 5 | 21-27 | 青春情长与冲突期：宝玉情长、金钏彩霞、滴翠亭，正负交织 |')
a('| 6 | 28-32 | 情定与悲剧潜伏期：茜香罗、诉肺腑、金钏跳井，负面加深 |')
a('| 7 | 33-40 | 大承苔挞与海棠结社期：宝玉挨打、结社吟诗，情绪起伏 |')
a('| 8 | 41-47 | 大观园雅集与鸳鸯抗婚期：品茶醉卧、雅集、宝玉受惩，跌宕 |')
a('| 9 | 48-56 | 香菱学诗与探春兴利期：雅集联诗、除宿弊，正面回暖 |')
a('| 10 | 57-63 | 紫鹃试玉与群芳夜宴期：试玉/宝玉病、群芳开夜宴，温馨与隐忧 |')
a('| 11 | 64-70 | 尤氏线悲剧与诗社重建期：尤二姐/尤三姐悲剧，暗示家运 |')
a('| 12 | 71-77 | 抄检大观园与悲音期：绣春囊/抄检/晴雯之死，负面深重 |')
a('| 13 | 78-80 | 姽婳词与美香菱屈受期：芙蓉诔、夏金桂入门，家道渐衰 |')
a('')
a('---')
a('')

# ===== 七、全局统计摘要 =====
a('## 七、全局统计摘要')
a('')
total_words = sum(d['words'] for d in data)
total_events = sum(d['events'] for d in data)
total_stars = sum(d['stars'] for d in data)
total_keys = sum(d['keys'] for d in data)
total_fb = len(fb_rows)
a('| 统计项 | 数值 | 说明 |')
a('|--------|------|------|')
a('| 已归档章数 | 80/120章（66.7%） | 第1-80章V3.4全部归档 |')
a('| 累计出场人物 | %d人 | 宽口径累计去重（别名归并） |' % total_chars)
a('| 累计伏笔线索 | %d条 | 全局追踪表总条数 |' % total_fb)
a('| 累计正面词 | %d词 | 三维统计正面词累加（§5.1） |' % cum_pos)
a('| 累计负面词 | %d词 | 三维统计负面词累加（§5.1） |' % cum_neg)
a('| 累计中性词 | %d词 | 三维统计中性词累加（§5.1） |' % cum_neu)
a('| 累计三维词合计 | %d词 | 正/负/中性三维统计总词数 |' % (cum_pos + cum_neg + cum_neu))
a('| 累计事件 | %d件 | 含★核心%d + ◆关键%d + ◇背景 |' % (total_events, total_stars, total_keys))
a('| 累计正文字数 | %d字 | 第1-80章文本字数合计 |' % total_words)
a('')
a('---')
a('')
a('*索引版本：v3.2（V3.4体系）*')
a('*参照流程：`skill/章节内容分析流程.md` v2.0*')
a('*参照规范：`skill/章节分析归档规范.md` v1.3*')
a('*模板参照：章节分析空白模板 V3.4*')
a('*数据来源：80份V3.4分析报告（`分析结果/V3.4存档_1-80章/`）；§5.1三维统计（同义词/反义词） + §5.7 DUTIR七类 + Hownet极性双轨*')
a('*生成日期：%s*' % ARCHIVE_DATE)

content = '\n'.join(L) + '\n'
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(content)

print('生成完成:', OUT)
print('总字数', total_words, '总事件', total_events, '去重人物', total_chars, '伏笔', total_fb)
print('累计正/负/中', cum_pos, cum_neg, cum_neu)

# 打印情感基调分布以便核查
from collections import Counter
print('情感基调分布:', dict(Counter(tone_label(d) for d in data)))