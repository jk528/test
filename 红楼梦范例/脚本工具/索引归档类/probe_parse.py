# -*- coding: utf-8 -*-
import glob, re, os

folder = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\V3.4存档_1-80章'
files = sorted(glob.glob(os.path.join(folder, '*.md')))

def probe(f):
    t = open(f, encoding='utf-8').read()
    r = {}
    m = re.search(r'# 《红楼梦》第(\d+)章"(.+?)"双轨', t)
    r['title'] = (m.group(1), m.group(2)) if m else None
    m2 = re.search(r'字数统计 \| (\d+)字', t)
    r['words'] = m2.group(1) if m2 else None
    m3 = re.search(r'\| 情感基调 \| (.+?) \|', t)
    r['tone'] = m3.group(1).strip() if m3 else None
    # 5.1 词数
    pos = re.search(r'\|\s*正面词\s*\|\s*(\d+)\s*\|\s*([\d.]+)%', t)
    neg = re.search(r'\|\s*负面词\s*\|\s*(\d+)\s*\|\s*([\d.]+)%', t)
    r['pos'] = (pos.group(1), pos.group(2)) if pos else None
    r['neg'] = (neg.group(1), neg.group(2)) if neg else None
    # 事件总数/★数
    m4 = re.search(r'事件总数 ≥ 章字数÷500[^（]*（实际(\d+)个）', t)
    m5 = re.search(r'核心事件（★）≥ 5个（实际(\d+)个）', t)
    r['events'] = m4.group(1) if m4 else None
    r['stars'] = m5.group(1) if m5 else None
    # 冲突数
    seg = t.split('### 4.3')[1].split('### 4.4')[0]
    r['conf'] = len(re.findall(r'^\| \d+ \|', seg, re.M))
    # 情感分段
    seg53 = t.split('### 5.3')[1].split('### 5.4')[0]
    r['segs'] = len(re.findall(r'^\| 第\d+', seg53, re.M))
    # 人物数 §4.2
    seg42 = t.split('### 4.2')[1].split('**层级说明**')[0]
    r['chars'] = len(re.findall(r'^\| [^|]+ \| [★◆◇] \|', seg42, re.M))
    # 5.7 主导情绪
    m6 = re.search(r'\| 主导情绪 \| (.+?) \|', t)
    r['dom'] = m6.group(1).strip() if m6 else None
    m7 = re.search(r'\| 情绪丰富度 \| (.+?) \|', t)
    r['rich'] = m7.group(1).strip() if m7 else None
    # 5.7.1 DUTIR 合计/正负
    m8 = re.search(r'\\.5.7.1', t)
    # 正负情绪比
    m9 = re.search(r'\| 正负情绪比 \| (.+?) \|', t)
    r['ratio'] = m9.group(1).strip() if m9 else None
    # DUTIR 正面% 负面%（5.7.2）
    m10 = re.search(r'正面情绪词数 \| (\d+)', t)
    m11 = re.search(r'负面情绪词数 \| (\d+)', t)
    r['dutir_pos'] = m10.group(1) if m10 else None
    r['dutir_neg'] = m11.group(1) if m11 else None
    return r

for f in files[:8]:
    b = os.path.basename(f)
    try:
        r = probe(f)
        print(b[:20], '|', r['title'], '| 字数', r['words'], '| 基调', r['tone'], '| 正面', r['pos'], '负面', r['neg'], '| 事件', r['events'], '★', r['stars'], '| 冲突', r['conf'], '分段', r['segs'], '人物', r['chars'], '| 主导', r['dom'], '丰富度', r['rich'], '比', r['ratio'], 'DUTIR正', r['dutir_pos'], '负', r['dutir_neg'])
    except Exception as e:
        print(b, 'ERROR', e)