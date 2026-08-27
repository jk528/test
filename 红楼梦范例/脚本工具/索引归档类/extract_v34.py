# -*- coding: utf-8 -*-
import glob, re, os, json

folder = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果\V3.4存档_1-80章'
files = sorted(glob.glob(os.path.join(folder, '*.md')))

def pct(s):
    s = s.replace('约', '').replace('~', '').strip()
    m = re.search(r'([\d.]+)', s)
    return float(m.group(1)) if m else None

def extract(f):
    t = open(f, encoding='utf-8').read()
    r = {'file': os.path.basename(f)}
    m = re.search(r'# 《红楼梦》第(\d+)章"(.+?)"双轨', t)
    r['no'] = int(m.group(1)); r['title'] = m.group(2)
    m2 = re.search(r'字数统计 \| (\d+)字', t)
    r['words'] = int(m2.group(1)) if m2 else None
    m3 = re.search(r'\| 情感基调 \| (.+?) \|', t)
    r['tone'] = m3.group(1).strip() if m3 else None
    # 5.2判定表：正/负/中占比
    m = re.search(r'\|\s*正面词占比\s*\|\s*([\d.]+)%', t); r['pos_pct'] = float(m.group(1)) if m else None
    m = re.search(r'\|\s*负面词占比\s*\|\s*([\d.]+)%', t); r['neg_pct'] = float(m.group(1)) if m else None
    m = re.search(r'\|\s*中性词占比\s*\|\s*([\d.]+)%', t); r['neu_pct'] = float(m.group(1)) if m else None
    # 事件总数（个/件）
    m = re.search(r'事件总数 ≥ 章字数÷500[^（]*（[^，]*实际\s*(\d+)\s*[个件]', t); r['events'] = int(m.group(1)) if m else None
    m = re.search(r'核心事件（★）≥ 5个（实际(\d+)', t); r['stars'] = int(m.group(1)) if m else None
    m = re.search(r'关键事件（◆）≥ 4个（实际(\d+)', t); r['keys'] = int(m.group(1)) if m else None
    # 冲突数
    seg = t.split('### 4.3')[1].split('### 4.4')[0]
    r['conf'] = len(re.findall(r'^\| \d+ \|', seg, re.M))
    # 情感分段
    seg53 = t.split('### 5.3')[1].split('### 5.4')[0]
    r['segs'] = len(re.findall(r'^\| 第\d+', seg53, re.M))
    # 人物数
    seg42 = t.split('### 4.2')[1].split('**层级说明**')[0]
    r['chars'] = len(re.findall(r'^\| [^|]+ \| [★◆◇] \|', seg42, re.M))
    # DUTIR 5.7.2
    m = re.search(r'主导情绪 \| (.+?) \|', t); r['dom'] = m.group(1).strip() if m else None
    m = re.search(r'情绪丰富度 \| (.+?) \|', t); r['rich'] = m.group(1).strip() if m else None
    m = re.search(r'正负情绪比 \| (.+?) \|', t); r['ratio'] = m.group(1).strip() if m else None
    m = re.search(r'正面情绪词数 \| (\d+)', t); r['d_pos'] = int(m.group(1)) if m else None
    m = re.search(r'负面情绪词数 \| (\d+)', t); r['d_neg'] = int(m.group(1)) if m else None
    m = re.search(r'中性情绪词数 \| (\d+)', t); r['d_neu'] = int(m.group(1)) if m else None
    # DUTIR总词数: 5.7.1 合计行
    d71 = t.split('5.7.1')[1].split('5.7.2')[0] if '5.7.1' in t else ''
    m = re.search(r'\|\s*\*?\*?合计\*?\*?\s*\|\s*—\s*\|\s*\*?\*?(\d+)\*?\*?', d71)
    r['d_total'] = int(m.group(1)) if m else None
    # Hownet 正/负%（5.7.3 交叉验证）
    seg573 = t.split('5.7.3')[1].split('## 六')[0] if '5.7.3' in t else ''
    rows = re.findall(r'^\| 正面占比 \| (.+?) \| (.+?) \|', seg573, re.M)
    if not rows:
        # 备选：从 8.2
        seg82 = t.split('### 8.2')[1].split('### 8.3')[0] if '### 8.2' in t else ''
        m = re.search(r'\| 正面词占比 \| (.+?)% \| (.+?)% \|', seg82)
        r['h_pos'] = pct(m.group(1)) if m else None
        m = re.search(r'\| 负面词占比 \| (.+?)% \| (.+?)% \|', seg82)
        r['h_neg'] = pct(m.group(1)) if m else None
    else:
        r['h_pos'] = pct(rows[0][0]); r['h_neg'] = pct(rows[0][1])
    # 5.1 词数（精确或约数）
    m = re.search(r'\|\s*正面词\s*\|\s*(约?\d+)\s*\|\s*([\d.]+)%', t); r['pos_cnt'] = int(m.group(1)) if m else None
    m = re.search(r'\|\s*负面词\s*\|\s*(约?\d+)\s*\|\s*([\d.]+)%', t); r['neg_cnt'] = int(m.group(1)) if m else None
    return r

data = []
for f in files:
    try:
        data.append(extract(f))
    except Exception as e:
        print('ERR', os.path.basename(f), repr(e))

print('total', len(data))
# 输出为JSON供检查
import io
out = json.dumps(data, ensure_ascii=False, indent=1)
open(r'c:\Users\Administrator\.trae-cn\work\6a8e88bd38e645ba57bc4277\v34_extract.json', 'w', encoding='utf-8').write(out)

# 打印关键字段缺失统计
def missstat(key):
    miss = [d['no'] for d in data if d.get(key) is None]
    return miss
for k in ['words','tone','pos_pct','neg_pct','neu_pct','events','stars','keys','conf','segs','chars','dom','rich','ratio','d_pos','d_neg','d_neu','d_total','h_pos','h_neg','pos_cnt','neg_cnt']:
    m = missstat(k)
    print(f'{k}: missing {len(m)} -> {m[:20]}')
print('----- 前3章完整数据 -----')
for d in data[:3]:
    print(json.dumps(d, ensure_ascii=False))