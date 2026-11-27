# -*- coding: utf-8 -*-
"""
四大名著名词列锦 · 词族按类合并脚本
===================================

功能：
  读取四书的逐章 MD（西游记 100 回 / 红楼梦 120 章 / 三国演义 120 回 / 水浒传 120 回），
  抽取每章「## 本回词族表」段内的全部词族表，按统一的大类关键词归并，
  输出「一个类一个 MD」的合并文件 + 一份总索引（00_索引.md）。

原则：
  1. 全部类不省略：每个类都输出独立文件（含「其他杂类」），其他杂类内部按原表名分组，逐表全列；
  2. 全部内容不省略：每张表保留原表名、声明词次与全部数据行（逐字引文不改动）；
  3. 归并只改"表名的归类"，不动表内任何文字。

用法：
  python 四大名著词族分类合并脚本.py            # 默认输出到 ../四书词族合并/
  python 四大名著词族分类合并脚本.py --dry-run  # 只统计不写文件

目录约定（相对脚本所在目录的上级）：
  {根}/西游记/名词列锦章节/*.md  等四书
  {根}/四书词族合并/              ← 输出
"""

import io
import os
import re
import sys
import glob
from collections import defaultdict, OrderedDict

BASE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))  # 四大名著根目录
BOOKS = ['西游记', '红楼梦', '三国演义', '水浒传']
UNIT = {'西游记': '回', '红楼梦': '章', '三国演义': '回', '水浒传': '回'}
OUT_DIR = os.path.join(BASE, '四书词族合并')
TODAY = '2026-11-19'

SEP_RE = re.compile(r'^\|[\s\-:|]+\|?\s*$')
HDR_RE = re.compile(r'^\|\s*词形\s*\|')
TITLE_RE = re.compile(r'^###\s+(.+?)（[^）]*?(\d+)\s*词次[^）]*）\s*$')

# 大类规则（有序，先匹配先用）；顺序重要：具体先于泛化
CATS = [
    ('数字与数量秩序',        r'数字'),
    ('亲属称谓与辈分',        r'亲属|辈分|排行|亲眷|儿孙'),
    ('诨名绰号与尊号',        r'诨名|绰号|尊号|星煞|帝王|圣号|法名|别号'),
    ('将佐军阵名录',          r'将佐|军阵名录|头领|星宿|正偏将|部将|点将|班次'),
    ('职官公门与人物称谓',    r'职官|官阶|公门|吏役|僧职|衔名|杂役|称谓|人物|名色|身份|部伍|军民|人等|员役|差役'),
    ('兵器军械与甲胄',        r'兵器|军械|甲胄|弓弩|火器|枪棒|刀枪|剑戟|牌弩'),
    ('军阵旗号与法术',        r'军阵|旗号|阵法|阵势|法术|妖法|神通|变化'),
    ('处所地理与方位',        r'处所|地理|州府|地名|关隘|城池|部洲|方位|仙境|洞府|山场|路途|行程|疆域|水泊'),
    ('建筑营寨与屋宇',        r'建筑|营寨|屋宇|厅堂|园林|宫殿|楼阁|店肆|门墙|馆阁'),
    ('器物陈设与珍宝',        r'器物|陈设|家私|家具|什物|珍宝|法宝|器皿|家生'),
    ('饮食茶酒与果品',        r'饮食|茶酒|果品|肴馔|筵席|粮草|饭食|酒器|祭品|面食'),
    ('服饰穿戴',              r'服饰|穿戴|衣冠|巾帽|锦帛|鞋袜|行头|衲袄|冠带'),
    ('车马舟船与鞍辔',        r'马匹|鞍辔|战骑|头口|牲畜|骡马|车马|车辆|船只|舟楫|水运|船具|海鳅'),
    ('时辰节令与天象气象',    r'时辰|节令|天象|气象|气候|四时|节候|景物·节令|岁时'),
    ('身体容貌与伤创',        r'身体|容貌|伤创|中毒|气色|残疾|髭须|形相|法相|体貌'),
    ('金银财物与钱粮',        r'金银|财物|钱粮|银钱|盘缠|财帛|银两|钱钞'),
    ('公文刑罚与文书',        r'公文|刑罚|牢狱|刑具|司法|牢城|文书|表章|状纸|文状|露布'),
    ('朝堂礼制与符节',        r'朝堂|礼制|仪典|礼俗|科举|符节|印信|奏疏|表诏|诏敕|敕旨'),
    ('医药伤病',              r'医药|伤病|方剂|药物|药毒|药饵'),
    ('诗词曲赋与韵文',        r'韵文|诗赋|诗词|偈|赞赋|赞诗|判词|曲子|酒令|俗谚|唱词|骈|联语|成句|歌谣'),
    ('禽兽虫鱼与草木',        r'禽兽|虫豸|虫鱼|草木|花卉|花木|瑞兽|禽鸟|走兽'),
    ('情态形容与色彩',        r'情态|形容|骂名|詈词|贬称|行色|色彩|形貌'),
    ('宗教神魔与祭祀丧仪',    r'宗教|祭祀|丧仪|佛理|丹道|经卷|冥界|轮回|法事|道场|香烛|醮|超度|仙凡|神魔|妖魔|神佛|冥界'),
    ('游艺说唱与百戏',        r'游艺|蹴球|说唱|相扑|百戏|博弈|戏曲'),
]
OTHER = '其他杂类'


def classify(name):
    for cat, pat in CATS:
        if re.search(pat, name):
            return cat
    return OTHER


def parse_md(path):
    """返回 [(table_name, declared, rows), ...]"""
    with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    lines = text.split('\n')
    start = 0
    for i, ln in enumerate(lines):
        if ln.strip() == '## 本回词族表':
            start = i + 1
            break
    else:
        # 无节标题时，从第一个含“词次”的 ### 行起（兼容变体）
        for i, ln in enumerate(lines):
            if ln.startswith('###') and '词次' in ln:
                start = i
                break
    tables = []
    i = start
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('## ') and ln.strip() != '## 本回词族表':
            break
        m = TITLE_RE.match(ln.strip())
        if m:
            name = m.group(1).strip()
            declared = int(m.group(2))
            rows = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith('#'):
                s = lines[j].strip()
                if s.startswith('|') and not SEP_RE.match(s) and not HDR_RE.match(s):
                    rows.append(lines[j])
                j += 1
            tables.append((name, declared, rows))
            i = j
            continue
        i += 1
    return tables


def cn_chapter(path):
    base = os.path.basename(path)
    m = re.match(r'^(\d{3})_(.+)\.md$', base)
    if m:
        return int(m.group(1)), m.group(2)
    return 999, base


def main():
    dry = '--dry-run' in sys.argv
    data = OrderedDict()          # book -> list of dict(ch, label, name, declared, rows)
    per_book = {}
    warnings = []

    for book in BOOKS:
        d = os.path.join(BASE, book, '名词列锦章节')
        files = sorted(glob.glob(os.path.join(d, '*.md')))
        if not files:
            print('[错误] 未找到 %s 的逐章 MD' % book)
            sys.exit(1)
        recs = []
        for fp in files:
            ch, label = cn_chapter(fp)
            for name, declared, rows in parse_md(fp):
                if declared != len(rows):
                    warnings.append('%s %s %s 声明%d≠实际%d' % (book, label, name, declared, len(rows)))
                recs.append(dict(ch=ch, label=label, name=name, declared=declared, rows=rows))
        data[book] = recs
        t = len(recs)
        w = sum(len(r['rows']) for r in recs)
        per_book[book] = (t, w)
        print('%s: 表 %d / 词次 %d' % (book, t, w))

    # 分类
    cat_tables = defaultdict(lambda: defaultdict(list))  # cat -> book -> [rec]
    for book, recs in data.items():
        for r in recs:
            cat_tables[classify(r['name'])][book].append(r)

    known = [c for c, _ in CATS] + [OTHER]
    cat_order = [c for c in known if c in cat_tables]
    total_t = sum(v[0] for v in per_book.values())
    total_w = sum(v[1] for v in per_book.values())
    print('合计: 表 %d / 词次 %d；大类 %d 个' % (total_t, total_w, len(cat_order)))
    if warnings:
        print('警告 %d 条（声明词次≠实际行数）：' % len(warnings))
        for w in warnings[:20]:
            print('  ', w)

    if dry:
        print('--dry-run：未写文件')
        return

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    def cell(t, w):
        return '%s（%d 表）' % ('{:,}'.format(w), t) if t else '—'

    # 索引
    idx = []
    idx.append('# 四大名著名词列锦词族 · 分类合并索引\n')
    idx.append('> **口径**：四书逐章 MD 的「本回词族表」按表名关键词归并为统一大类；**全部类不省略、全部表全部行不省略**（含其他杂类），表内文字未作任何改动。')
    idx.append('> **数据**：西游记 100 回／红楼梦 120 章／三国演义 120 回／水浒传 120 回；生成日期：%s。' % TODAY)
    idx.append('> **合计**：{:,} 张词族表 · {:,} 词次。\n'.format(total_t, total_w))
    idx.append('| 序号 | 大类 | 西游记 | 红楼梦 | 三国演义 | 水浒传 | 合计词次 |')
    idx.append('|---|---|---|---|---|---|---|')
    for n, cat in enumerate(cat_order, 1):
        cells = []
        tot = 0
        for book in BOOKS:
            recs = cat_tables[cat].get(book, [])
            t = len(recs)
            w = sum(len(r['rows']) for r in recs)
            tot += w
            cells.append(cell(t, w))
        idx.append('| %02d | [%s](%02d_%s.md) | %s | %s | %s | %s | %s |' % (
            n, cat, n, safe_name(cat), cells[0], cells[1], cells[2], cells[3], '{:,}'.format(tot)))
    idx.append('')
    idx.append('## 其他杂类说明\n')
    other = cat_tables.get(OTHER, {})
    names = sorted({r['name'] for b in other for r in other[b]})
    idx.append('- 其他杂类共 **%d 个原始表名**，分布在四书；文件内按原表名分组、逐表全列（未截断）。' % len(names))
    idx.append('- 归并规则见脚本 `CATS` 关键词表；未命中任何规则的表名落此，属\"宁可多收\"的长尾。')
    idx.append('')
    if warnings:
        idx.append('## 校验注记\n')
        idx.append('- 声明词次≠实际数据行的表共 %d 张（已按实际行输出，未丢行）：' % len(warnings))
        for w in warnings[:50]:
            idx.append('  - %s' % w)
        idx.append('')
    write_md(os.path.join(OUT_DIR, '00_索引.md'), '\n'.join(idx))

    # 每类一个文件
    for n, cat in enumerate(cat_order, 1):
        recs_by_book = cat_tables[cat]
        tot_refs = sum(len(recs_by_book.get(b, [])) for b in BOOKS)
        tot_words = sum(len(r['rows']) for b in BOOKS for r in recs_by_book.get(b, []))
        lines = []
        lines.append('# 大类：%s（四书合并）\n' % cat)
        lines.append('> 归并口径：按词族表名关键词归入本类；表名、声明词次、数据行均按原文件保留。')
        lines.append('> 本类合计：%d 表 · %s 词次（%s）。\n' % (
            tot_refs, '{:,}'.format(tot_words),
            '／'.join('%s %d 表' % (b, len(recs_by_book.get(b, []))) for b in BOOKS)))
        for book in BOOKS:
            recs = recs_by_book.get(book, [])
            if not recs:
                continue
            recs = sorted(recs, key=lambda r: r['ch'])
            tw = sum(len(r['rows']) for r in recs)
            lines.append('## %s（%d 表 · %s 词次）\n' % (book, len(recs), '{:,}'.format(tw)))
            for r in recs:
                lines.append('### %s · %s（共 %d 词次）' % (r['label'], r['name'], len(r['rows'])))
                lines.append('| 词形 | 出处 | 原文片段 | 已见逐回条目 |')
                lines.append('|---|---|---|---|')
                lines.extend(r['rows'])
                lines.append('')
        write_md(os.path.join(OUT_DIR, '%02d_%s.md' % (n, safe_name(cat))), '\n'.join(lines))

    print('输出目录：%s（%d 个文件）' % (OUT_DIR, len(cat_order) + 1))


def safe_name(name):
    return re.sub(r'[\\/:*?"<>|\s]', '', name)


def write_md(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text if text.endswith('\n') else text + '\n')


if __name__ == '__main__':
    main()