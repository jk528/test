# -*- coding: utf-8 -*-
"""从80份V3.4报告提取数据，生成 _归档索引_V3.4.md"""
import glob, re, os, json

folder = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\V3.4存档_1-80章'
files = sorted(glob.glob(os.path.join(folder, '*.md')))

def extract(f):
    t = open(f, encoding='utf-8').read()
    r = {'file': os.path.basename(f)}
    m = re.search(r'# 《红楼梦》第(\d+)章"(.+?)"双轨', t)
    r['no'] = int(m.group(1)); r['title'] = m.group(2)
    m2 = re.search(r'字数统计 \| (\d+)字', t)
    r['words'] = int(m2.group(1)) if m2 else None
    # 情感基调：取§5.2最终判定
    m = re.search(r'\|\s*\*\*情感基调\*\*\s*\|[^|]*\|[^|]*\|\s*\*\*(.+?)\*\*\s*\|', t)
    tone = m.group(1).strip() if m else None
    if tone is None:
        m = re.search(r'\| 情感基调 \| (.+?) \|', t)
        tone = m.group(1).strip() if m else None
    # 归一化：去括号注释
    tone2 = re.sub(r'（.*?）', '', tone or '').strip()
    r['tone_raw'] = tone; r['tone'] = tone2 or tone
    # §5.1 三维统计（正/负/中性词，同义词/反义词词典）
    seg51 = t.split('### 5.1')[1].split('### 5.2')[0] if '### 5.1' in t else ''
    def _num(s):
        s = (s or '').replace('~', '').replace('约', '').replace(',', '').replace('%', '').strip()
        m = re.search(r'([\d.]+)', s)
        return float(m.group(1)) if m else None
    m = re.search(r'^\| 正面词 \| ([^|]+) \| ([^|]+) \|', seg51, re.M)
    r['p3d'] = int(round(_num(m.group(1)))) if (m and _num(m.group(1)) is not None) else None
    r['p3d_pct'] = _num(m.group(2)) if m else None
    m = re.search(r'^\| 负面词 \| ([^|]+) \| ([^|]+) \|', seg51, re.M)
    r['n3d'] = int(round(_num(m.group(1)))) if (m and _num(m.group(1)) is not None) else None
    r['n3d_pct'] = _num(m.group(2)) if m else None
    m = re.search(r'^\| 中性词 \| ([^|]+) \| ([^|]+) \|', seg51, re.M)
    r['e3d'] = int(round(_num(m.group(1)))) if (m and _num(m.group(1)) is not None) else None
    r['e3d_pct'] = _num(m.group(2)) if m else None
    if r['e3d_pct'] is None and r['p3d_pct'] is not None and r['n3d_pct'] is not None:
        r['e3d_pct'] = round(100.0 - r['p3d_pct'] - r['n3d_pct'], 1)
    # 事件清单
    seg2 = t.split('## 二、事件接入清单')[1].split('## 三、')[0]
    lvl = re.findall(r'^\| (E\d+-\d+) \|[^|]*\|[^|]*\|[^|]*\|[^|]*\| ([★◆◇]) \|', seg2, re.M)
    r['events'] = len(lvl)
    r['stars'] = sum(1 for _, x in lvl if x == '★')
    r['keys'] = sum(1 for _, x in lvl if x == '◆')
    # 冲突数
    seg = t.split('### 4.3')[1].split('### 4.4')[0]
    r['conf'] = len(re.findall(r'^\| \d+ \|', seg, re.M))
    # 情感分段
    seg53 = t.split('### 5.3')[1].split('### 5.4')[0]
    r['segs'] = len(re.findall(r'^\| 第\d+', seg53, re.M))
    # 人物 §4.2
    seg42 = t.split('### 4.2')[1].split('**层级说明**')[0]
    char_rows = re.findall(r'^\| ([^|]+) \| ([★◆◇]) \|[^|]*\| ([^|]+) \|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\| ([^|]+) \| ([^|]+) \|', seg42, re.M)
    r['chars'] = len(char_rows)
    r['char_list'] = [{'name': a.strip(), 'lvl': b, 'para': c.strip(), 'role': d.strip(), 'status': e.strip()} for a,b,c,d,e in char_rows]
    # DUTIR 5.7.2
    m = re.search(r'主导情绪 \| (.+?) \|', t); r['dom_raw'] = m.group(1).strip() if m else None
    m = re.search(r'情绪丰富度 \| (.+?) \|', t); r['rich'] = m.group(1).strip() if m else None
    m = re.search(r'正负情绪比 \| (.+?) \|', t); r['ratio'] = m.group(1).strip() if m else None
    m = re.search(r'正面情绪词数 \| (\d+)', t); r['d_pos'] = int(m.group(1)) if m else None
    m = re.search(r'负面情绪词数 \| (\d+)', t); r['d_neg'] = int(m.group(1)) if m else None
    m = re.search(r'中性情绪词数 \| (\d+)', t); r['d_neu'] = int(m.group(1)) if m else None
    r['d_total'] = (r['d_pos'] or 0) + (r['d_neg'] or 0) + (r['d_neu'] or 0)
    # 7类词数 5.7.1
    d71 = t.split('5.7.1')[1].split('5.7.2')[0] if '5.7.1' in t else ''
    cat = {}
    for x in re.findall(r'^\| (好|乐|哀|怒|惧|恶|惊)（[^|]*） \| (正面|负面|中性) \| (\d+) \| ([\d.]+)%', d71, re.M):
        cat[x[0]] = {'polar': x[1], 'cnt': int(x[2]), 'pct': float(x[3])}
    r['cats'] = cat
    # 主导情绪名（去掉括号）
    dom = r['dom_raw']
    if dom:
        dom2 = re.sub(r'（.*?）', '', dom).strip()
        r['dom'] = dom2
    else:
        r['dom'] = None
    # Hownet 正/负%（5.7.3 交叉验证，第一列为Hownet）
    seg573 = t.split('5.7.3 与情感基调')[1].split('## 六')[0] if '5.7.3 与情感基调' in t else ''
    m = re.search(r'^\| 正面占比 \| (.+?) \|', seg573, re.M); r['h_pos'] = float(re.sub(r'[^\d.]', '', m.group(1))) if m else None
    m = re.search(r'^\| 负面占比 \| (.+?) \|', seg573, re.M); r['h_neg'] = float(re.sub(r'[^\d.]', '', m.group(1))) if m else None
    # 伏笔 §9.2
    seg92 = t.split('### 9.2')[1].split('### 9.3')[0] if '### 9.2' in t else ''
    r['foreshadows'] = re.findall(r'^\| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|', seg92, re.M)
    return r

data = []
errs = []
for f in files:
    try:
        data.append(extract(f))
    except Exception as e:
        errs.append((os.path.basename(f), repr(e)))

print('OK chapters:', len(data), 'ERRORS:', len(errs))
for b, e in errs:
    print('  ERR', b, e)

# 检查缺失
for k in ['words','tone','events','stars','keys','conf','segs','chars','dom','rich','ratio','d_pos','d_neg','d_neu','d_total','h_pos','h_neg','dom_raw']:
    miss = [d['no'] for d in data if d.get(k) in (None, '')]
    if miss:
        print(f'{k} missing:', miss)
# 情绪类别数
catmiss = [d['no'] for d in data if len(d.get('cats',{})) < 7]
print('cats<7:', catmiss)
# 伏笔数
fb = [d['no'] for d in data if not d.get('foreshadows')]
print('no foreshadow:', fb)

json.dump(data, open(r'c:\Users\Administrator\.trae-cn\work\6a8e88bd38e645ba57bc4277\v34_extract2.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('dumped v34_extract2.json')
# 打印第1、3、5章样本
for d in data:
    if d['no'] in (1,3,5):
        print(json.dumps(d, ensure_ascii=False))