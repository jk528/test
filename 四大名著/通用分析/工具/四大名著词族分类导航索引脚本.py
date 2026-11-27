# -*- coding: utf-8 -*-
"""
四大名著名词列锦 · 分类导航索引合并脚本（单文件总索引版）
========================================================

功能：
  读取四书全部逐章 MD（西游记 100 回 / 红楼梦 120 章 / 三国演义 120 回 / 水浒传 120 回，共 460 个），
  提取每个 MD 末尾「## 本(回|章)词族表」段的全部分类词族表，
  按 25 大类关键词归并（规则与《四大名著词族分类合并脚本》完全一致，import 复用），
  合并为【一个】带页内导航索引的 MD：

    ① 顶部「总导航」：25 大类 × 四书（表数／词次）矩阵，大类名带页内锚点（#cat-NN），点击跳转；
    ② 主体：大类（## 级）→ 书（### 级）→ 章节·词族表（#### 级）→ 全部数据行，每区块可 [▲ 返回导航](#top)。

原则：
  1. 全部类不省略：25 大类（含「其他杂类」）全部进入本文件；
  2. 全部表全部行不省略：合计 6,933 张表、113,784 数据行逐行保留；
  3. 表内文字零改动：表名、出处、逐字引文均按原文件保留。

用法：
  python 四大名著词族分类导航索引脚本.py            # 输出至 四大名著/全四书词族合并分类/全四书词族合并分类导航索引.md
  python 四大名著词族分类导航索引脚本.py --dry-run  # 只统计校验，不写盘

自检（每次写盘后自动执行）：
  回读输出文件，断言 表数／数据行数／表头声明词次合计 与源数据完全相等（守恒），打印 PASS/FAIL。
"""

import io
import os
import re
import sys
import glob
from collections import OrderedDict

import 四大名著词族分类合并脚本 as merger  # 复用 CATS/OTHER/classify/parse_md/cn_chapter/BOOKS/BASE

BASE = merger.BASE
BOOKS = merger.BOOKS
OUT_DIR = os.path.join(BASE, '全四书词族合并分类')
OUT_FILE = os.path.join(OUT_DIR, '全四书词族合并分类导航索引.md')
TODAY = '2026-11-20'
UNIT = {'西游记': '100 回', '红楼梦': '120 章', '三国演义': '120 回', '水浒传': '120 回'}


def fmt(n):
    return '{:,}'.format(n)


def collect():
    data = OrderedDict()
    warnings = []
    n_files = 0
    for book in BOOKS:
        d = os.path.join(BASE, book, '名词列锦章节')
        files = sorted(glob.glob(os.path.join(d, '*.md')))
        if not files:
            print('[错误] 未找到 %s 的逐章 MD' % book)
            sys.exit(1)
        n_files += len(files)
        recs = []
        for fp in files:
            ch, label = merger.cn_chapter(fp)
            for name, declared, rows in merger.parse_md(fp):
                if declared != len(rows):
                    warnings.append('%s %s「%s」声明 %d 词次 ≠ 实际 %d 行'
                                    % (book, label, name, declared, len(rows)))
                recs.append(dict(ch=ch, label=label, name=name, declared=declared, rows=rows))
        data[book] = recs
    return data, warnings, n_files


def main():
    dry = '--dry-run' in sys.argv
    data, warnings, n_files = collect()

    # 归并：大类 -> 书 -> [rec]
    cat_tables = OrderedDict()
    for b in BOOKS:
        for r in data[b]:
            cat_tables.setdefault(merger.classify(r['name']), OrderedDict()).setdefault(b, []).append(r)
    cat_order = [c for c, _ in merger.CATS] + [merger.OTHER]
    cat_order = [c for c in cat_order if c in cat_tables]

    per_book = {b: (len(data[b]), sum(len(r['rows']) for r in data[b])) for b in BOOKS}
    total_t = sum(v[0] for v in per_book.values())
    total_w = sum(v[1] for v in per_book.values())
    other_names = sorted({r['name']
                           for b in cat_tables.get(merger.OTHER, {})
                           for r in cat_tables[merger.OTHER][b]})

    for b in BOOKS:
        print('%s: 表 %d / 词次 %s' % (b, per_book[b][0], fmt(per_book[b][1])))
    print('合计: 表 %d / 词次 %s；大类 %d 个；源文件 %d 个' % (total_t, fmt(total_w), len(cat_order), n_files))
    for x in warnings:
        print('  [警告] %s' % x)

    if dry:
        print('--dry-run：未写文件')
        return

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # 1) 文档头 + 总导航矩阵
    L = []
    L.append('<a id="top"></a>')
    L.append('# 全四书词族合并分类 · 导航索引')
    L.append('')
    L.append('> **口径**：提取四书 %d 个逐章 MD 末尾「本回/章词族表」段的全部分类词族表，'
             '按 25 大类关键词归并（规则与《四大名著词族分类合并脚本》完全一致）；'
             '**全部类不省略（含「其他杂类」）、全部表全部行不省略**；表名、声明词次、数据行均按原文件保留，表内文字零改动。'
             % n_files)
    L.append('> **数据**：%s；合计 **%s 表 · %s 词次**。' %
             ('　'.join('%s %s，%d 表／%s 词次' % (b, UNIT[b], per_book[b][0], fmt(per_book[b][1]))
                       for b in BOOKS),
              fmt(total_t), fmt(total_w)))
    L.append('> **层级**：%d 大类（含其他杂类）→ 书（西游记→红楼梦→三国演义→水浒传）→ 章 → 词族表 → 数据行。'
             % len(cat_order))
    L.append('> **导航**：点击「总导航」中带链接的大类名跳至对应区块（页内锚点 #cat-NN）；'
             '每个区块标题右侧 [▲ 返回导航](#top)；定位具体章/表可用编辑器大纲面板（#### 级标题）或检索「第X回/章 · 表名」。')
    L.append('> **生成**：%s；由 `通用分析/工具/四大名著词族分类导航索引脚本.py` 复算重跑（--dry-run 支持统计校验）。'
             % TODAY)
    L.append('')
    L.append('## 总导航（%d 大类 × 四书）' % len(cat_order))
    L.append('')
    L.append('| 序号 | 大类 | 西游记（表／词次） | 红楼梦 | 三国演义 | 水浒传 | 合计表 | 合计词次 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for n, cat in enumerate(cat_order, 1):
        cells, tot_t, tot_w = [], 0, 0
        for b in BOOKS:
            recs = cat_tables[cat].get(b, [])
            t, w = len(recs), sum(len(r['rows']) for r in recs)
            tot_t += t
            tot_w += w
            cells.append('%d／%s' % (t, fmt(w)) if t else '—')
        L.append('| %02d | [%s](#cat-%02d) | %s | %s | %s | %s | %d | %s |'
                 % (n, cat, n, cells[0], cells[1], cells[2], cells[3], tot_t, fmt(tot_w)))
    L.append('| — | **合计** | %d／%s | %d／%s | %d／%s | %d／%s | **%d** | **%s** |' % (
        per_book['西游记'][0], fmt(per_book['西游记'][1]),
        per_book['红楼梦'][0], fmt(per_book['红楼梦'][1]),
        per_book['三国演义'][0], fmt(per_book['三国演义'][1]),
        per_book['水浒传'][0], fmt(per_book['水浒传'][1]),
        total_t, fmt(total_w)))
    L.append('')
    L.append('> 其中「其他杂类」为未命中任何大类关键词的 %d 个原始表名（长尾），全部逐表保留于本文件对应区块，未截断。'
             % len(other_names))
    L.append('')

    # 2) 主体：大类 → 书 → 章节·表 → 数据行
    for n, cat in enumerate(cat_order, 1):
        by_book = cat_tables[cat]
        tot_t = sum(len(by_book.get(b, [])) for b in BOOKS)
        tot_w = sum(len(r['rows']) for b in BOOKS for r in by_book.get(b, []))
        parts = ['%s %d 表／%s 词次'
                 % (b, len(by_book[b]), fmt(sum(len(r['rows']) for r in by_book[b])))
                 for b in BOOKS if by_book.get(b)]
        L.append('<a id="cat-%02d"></a>' % n)
        L.append('## 大类 %02d · %s（%d 表 · %s 词次）　[▲ 返回导航](#top)' % (n, cat, tot_t, fmt(tot_w)))
        L.append('')
        L.append('> %s' % '　'.join(parts))
        L.append('')
        for b in BOOKS:
            recs = by_book.get(b)
            if not recs:
                continue
            recs = sorted(recs, key=lambda r: r['ch'])
            L.append('### %s · %s（%d 表 · %s 词次）'
                     % (b, cat, len(recs), fmt(sum(len(r['rows']) for r in recs))))
            L.append('')
            for r in recs:
                L.append('#### %s · %s（共 %d 词次）' % (r['label'], r['name'], len(r['rows'])))
                L.append('| 词形 | 出处 | 原文片段 | 已见逐回条目 |')
                L.append('|---|---|---|---|')
                L.extend(r['rows'])
                L.append('')
        L.append('')

    if warnings:
        L.append('## 校验注记')
        L.append('')
        L.append('- 声明词次与实测行数不符的表（已按实测行数输出，未丢行）：')
        for x in warnings:
            L.append('  - %s' % x)
        L.append('')

    text = '\n'.join(L) + '\n'
    with io.open(OUT_FILE, 'w', encoding='utf-8', newline='') as f:
        f.write(text)

    # 3) 守恒自检：回读输出文件
    with io.open(OUT_FILE, 'r', encoding='utf-8', errors='replace') as f:
        out = f.read()
    body = out[out.find('<a id="cat-'):]
    pipes = [ln.strip() for ln in body.split('\n') if ln.lstrip().startswith('|')]
    n_hdr = sum(1 for x in pipes if merger.HDR_RE.match(x))
    n_sep = sum(1 for x in pipes if merger.SEP_RE.match(x))
    n_data = len(pipes) - n_hdr - n_sep
    decls = re.findall(r'(?m)^#### .+?（共 (\d+) 词次）$', out)
    n_tables = len(decls)
    sum_declared = sum(int(x) for x in decls)
    ok = (n_hdr == n_tables == total_t) and (n_data == total_w) and (sum_declared == total_w)
    print('守恒自检: 表头行 %s/%d · 表数 %s · 数据行 %s/%d · 声明词次合计 %s/%d → %s'
          % (fmt(n_hdr), total_t, fmt(n_tables), fmt(n_data), total_w, fmt(sum_declared), total_w,
             'PASS' if ok else 'FAIL'))
    print('输出: %s（%s bytes）' % (OUT_FILE, fmt(os.path.getsize(OUT_FILE))))
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()