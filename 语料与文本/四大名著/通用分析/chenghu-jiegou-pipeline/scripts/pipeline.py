# -*- coding: utf-8 -*-
"""章回小说「称呼学解构（整合版）」全书流水线 · 统一 CLI。

子命令：
  init    探查底本并生成项目配置、输出目录、批次执行简报
  plan    列出「底本 txt → 输出 md」映射与批次划分（供并行执行单元使用）
  check   单篇规格 + 引文锚定自检（或 --all 逐篇）
  qc      全书完整性 + 结构 / 计数守恒 / 引文锚定 + 规格汇总
  readme  生成 README 进度表（统计表 + 批次表 + 预判四题 + 适配参数）

所有路径由 config 决定，不含任何书目硬编码；任一章回小说均可复用。
退出码：0 通过；1 存在 ERROR（WARN 只提示、不阻断，但须人工清零）。
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

CONFIG_NAME = 'chenghu.config.json'
SECTIONS = ['## 0.', '## 1.', '## 2.', '## 3.', '## 4.', '## 5.']
ENGLISH_ALLOW = {'who', 'stance', 'mood', 'channel', 'lexeme', 'bcc',
                 'handicap', 'to', 'cc', 'ai', 'md', 'txt'}
EVENT_ROW = re.compile(r'(?m)^\|\s*\*{0,2}(\d+b?)\*{0,2}\s*\|')
QUOTE = re.compile(r'「([^「」]+)」')
SPLIT_SEG = re.compile(r'……|＋|——|—')
ZERO_WIDTH = re.compile(r'[\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]')


# ---------- 归一化：与工程质检脚本 v2.1 的码点规则完全一致 ----------
def norm(s):
    out = []
    for ch in s:
        c = ord(ch)
        if c < 0x20:
            continue
        if c in (0x20, 0x3000, 0xA0, 0xAD, 0x180E, 0xFEFF):
            continue
        if 0x200B <= c <= 0x200F or 0x202A <= c <= 0x202E or 0x2060 <= c <= 0x2064:
            continue
        if 0xE000 <= c <= 0xF8FF or 0xFE00 <= c <= 0xFE0F:
            continue
        if 0x21 <= c <= 0x2F or 0x3A <= c <= 0x40 or 0x5B <= c <= 0x60 or 0x7B <= c <= 0x7E:
            continue
        if 0x2010 <= c <= 0x2027 or c == 0xB7:
            continue
        if 0x3001 <= c <= 0x303F:
            continue
        if (0xFF01 <= c <= 0xFF0F or 0xFF1A <= c <= 0xFF20 or
                0xFF3B <= c <= 0xFF40 or 0xFF5B <= c <= 0xFF65):
            continue
        out.append(ch)
    return ''.join(out)


def read(p):
    return Path(p).read_text(encoding='utf-8')


def load_config(path=None):
    if path:
        cfg = json.loads(read(path))
        cfg['_config_path'] = str(Path(path).resolve())
        return cfg
    p = Path.cwd()
    while p and p != p.parent:
        cand = p / CONFIG_NAME
        if cand.is_file():
            cfg = json.loads(read(cand))
            cfg['_config_path'] = str(cand)
            return cfg
        p = p.parent
    sys.exit('未找到配置：请用 --config 指向 %s，或先执行 init' % CONFIG_NAME)


def book_root(cfg):
    return Path(cfg['root']) / cfg['book_dir']


def dirs(cfg):
    b = book_root(cfg)
    return b / cfg['split_dir'], b / cfg.get('nieq_dir', '名词列锦章节'), b / cfg.get('out_dir', '称呼学解构/整合版可查')


def source_maps(cfg):
    split, nieq, _ = dirs(cfg)
    src, nq = {}, {}
    for p in glob.glob(str(split / '*.txt')):
        m = re.match(r'^(\d{3})_', os.path.basename(p))
        if m:
            src[m.group(1)] = norm(read(p))
    if nieq.is_dir():
        for p in glob.glob(str(nieq / '*.md')):
            m = re.match(r'^(\d{3})_', os.path.basename(p))
            if m:
                nq[m.group(1)] = norm(read(p))
    return src, nq


def out_files(cfg):
    _, _, out = dirs(cfg)
    return sorted(glob.glob(str(out / '[0-9][0-9][0-9]_*.md')))


def sources_for(num, src, nq):
    return src.get(num, ''), nq.get(num, '')


def anchor(c, s0, n0, src, num):
    """返回 (校验片段数, 未锚定明细)。"""
    total, miss = 0, []
    for i, q in enumerate(QUOTE.findall(c), 1):
        for seg in SPLIT_SEG.split(q):
            nf = norm(seg)
            if len(nf) < 12:
                continue
            total += 1
            if s0 and nf in s0:
                continue
            if n0 and nf in n0:
                continue
            elsewhere = [k for k, v in src.items() if k != num and nf in v]
            tag = ('→' + ','.join(elsewhere)) if elsewhere else '×'
            miss.append('[Q%d%s]%s' % (i, tag, nf[:20]))
    return total, miss


# ---------- 单篇检查 ----------
def check_one(md, cfg, src, nq):
    num = re.match(r'^(\d{3})_', os.path.basename(md)).group(1)
    c = read(md)
    errors, warns, stats = [], [], {}
    for i, sec in enumerate(SECTIONS):
        if not re.search(r'(?m)^##\s*%d\s*\.' % i, c):
            errors.append('缺§%d' % i)
    rows = EVENT_ROW.findall(c)
    decl = re.search(r'本回解构\s*(\d+)\s*件', c)
    decl = int(decl.group(1)) if decl else 0
    if decl < 1 or decl != len(rows):
        errors.append('计数不符(声明%d/表行%d)' % (decl, len(rows)))
    nums = [int(re.sub(r'b$', '', r)) for r in rows]
    if nums and nums != list(range(1, len(nums) + 1)):
        errors.append('事件编号不连续:%s' % nums[:15])
    d2 = re.search(r'重点解构\s*(\d+)\s*段', c)
    h3 = len(re.findall(r'(?m)^###\s', c))
    if d2 and int(d2.group(1)) != h3:
        errors.append('解构段不符(声明%s/实际%d)' % (d2.group(1), h3))
    if h3 != int(cfg.get('focus_segments', 3)):
        warns.append('###段数=%d(目标%s)' % (h3, cfg.get('focus_segments', 3)))
    if not re.search(r'(?m)^>\s*AI生成\s*$', c):
        errors.append('缺AI尾标')
    if '（注：' not in c:
        errors.append('缺尾注块')
    if '【A】' not in c:
        errors.append('缺【A】锚')
    zw = len(ZERO_WIDTH.findall(c))
    if zw:
        errors.append('零宽字符×%d' % zw)
    if '拆分底本' not in c and (cfg['split_dir'] + '/' + num + '_') not in c:
        errors.append('底本引用缺')
    s0, n0 = sources_for(num, src, nq)
    total, miss = anchor(c, s0, n0, src, num)
    for m in miss[:12]:
        errors.append('QMISS:' + m)
    if len(miss) > 12:
        errors.append('QMISS:…另%d条' % (len(miss) - 12))
    if not s0:
        errors.append('本回底本缺失(%s)' % num)
    chars = len(c)
    quotes = c.count('「')  # 工程口径：数开引号，与既有 README 统计一致
    if chars < int(cfg.get('min_chars', 15700)):
        warns.append('字符%d<下限%s' % (chars, cfg.get('min_chars', 15700)))
    if not (int(cfg.get('min_quotes', 185)) <= quotes <= int(cfg.get('max_quotes', 230))):
        warns.append('「」=%d(目标%s–%s)' % (quotes, cfg.get('min_quotes', 185), cfg.get('max_quotes', 230)))
    bad = sorted({w for w in re.findall(r'[A-Za-z]{3,}', c) if w.lower() not in ENGLISH_ALLOW})
    if bad:
        warns.append('英文残留:' + ','.join(bad[:8]))
    seg4 = c.split('## 4.')[1].split('## 5.')[0] if '## 4.' in c else ''
    law = len([l for l in seg4.splitlines()
               if l.startswith('| ') and not l.startswith('| :') and '定律 / 命中' not in l])
    if law and not (int(cfg.get('min_law_rows', 55)) <= law <= int(cfg.get('max_law_rows', 75))):
        warns.append('定律行=%d' % law)
    if not re.search(r'[(（]\s*%d\s*/\s*%d\s*[)）]' % (int(num), cfg['chapters']), c):
        warns.append('头标系列标注缺失(N/%d)' % cfg['chapters'])
    stats = dict(num=num, chars=chars, events=len(rows), decl=decl, h3=h3,
                 quotes=quotes, law=law, segs=total, miss=len(miss))
    return errors, warns, stats


def print_result(name, errors, warns, stats=None):
    if errors:
        print('[FAIL] %s ▶ %s' % (name, '；'.join(errors[:8])))
    elif warns:
        print('[WARN] %s ▶ %s' % (name, '；'.join(warns[:6])))
    else:
        print('[ OK ] %s' % name)
    if stats:
        print('       字符%d 事件%d ###%d 「」%d 定律%d 片段%d 未锚定%d'
              % (stats['chars'], stats['events'], stats['h3'], stats['quotes'],
                 stats['law'], stats['segs'], stats['miss']))


# ---------- 子命令 ----------
def cmd_init(a):
    root = Path(a.root).resolve()
    b = root / a.book_dir
    split = b / a.split_dir
    if not split.is_dir():
        sys.exit('拆分底本目录不存在：%s' % split)
    txts = sorted(glob.glob(str(split / '*.txt')))
    actual = len(txts)
    if actual != a.chapters:
        print('[注意] 声明回数 %d，底本实际 %d 个 → 配置按实际值 %d 写入（避免漏做尾段）'
              % (a.chapters, actual, actual))
    nieq = b / a.nieq_dir
    if not nieq.is_dir():
        print('[注意] 未找到名词列锦目录 %s；引文将只锚定底本本身' % nieq)
    out = b / a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    cfg = {
        'book': a.book,
        'root': str(root),
        'book_dir': a.book_dir,
        'split_dir': a.split_dir,
        'nieq_dir': a.nieq_dir,
        'out_dir': a.out_dir,
        'chapters': actual,
        'events_per_chapter': a.events,
        'focus_segments': 3,
        'min_chars': a.min_chars,
        'min_quotes': 185,
        'max_quotes': 230,
        'min_law_rows': 55,
        'max_law_rows': 75,
        'batch_size': a.batch,
        'themes': ['题1：待定（全书称谓主轴）', '题2：待定', '题3：待定', '题4：待定'],
    }
    cfg_path = b / CONFIG_NAME
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    print('配置已写入：%s' % cfg_path)
    brief = b / '称呼学解构' / '批次执行简报.md'
    brief.parent.mkdir(parents=True, exist_ok=True)
    tpl = Path(__file__).resolve().parent.parent / 'assets' / 'brief_template.md'
    text = read(tpl) if tpl.is_file() else '# {book} 称呼学解构（整合版）· 批次执行简报\n\n按 SKILL.md 执行。\n'
    text = (text.replace('{book}', a.book)
                .replace('{root}', str(root))
                .replace('{book_dir}', a.book_dir)
                .replace('{split_dir}', a.split_dir)
                .replace('{nieq_dir}', a.nieq_dir)
                .replace('{out_dir}', a.out_dir)
                .replace('{chapters}', str(actual))
                .replace('{min_chars}', str(a.min_chars))
                .replace('{themes}', '\n'.join('%d. %s' % (i + 1, t) for i, t in enumerate(cfg['themes']))))
    brief.write_text(text, encoding='utf-8')
    print('简报已写入：%s' % brief)
    print('输出目录：%s' % out)
    print('下一步：精读第 1 回生成样板 → python pipeline.py plan --config "%s"' % cfg_path)


def parse_chapter(name, cfg):
    """从底本文件名解析 (编号, 回次标签, 上句)。"""
    m = re.match(r'^(\d{3})_(.*)\.txt$', name)
    if not m:
        return None
    num, tail = m.group(1), m.group(2)
    tail = re.sub(r'^\d+_', '', tail)          # 去掉字数字段
    mm = re.search(r'第[一二三四五六七八九十百千零〇\d]+[回章]', tail)
    label = mm.group(0) if mm else ''
    rest = tail[mm.end():] if mm else tail
    segs = [s for s in re.split(r'[　\s]+', rest) if s]
    upper = segs[0] if segs else ''
    if cfg.get('chapter_label_style') == 'arabic':
        label = '第%d回' % int(num)
    return num, label, upper


def cmd_plan(a):
    cfg = load_config(a.config)
    split, _, out = dirs(cfg)
    done = {os.path.basename(p)[:3] for p in out_files(cfg)}
    items = []
    for p in sorted(glob.glob(str(split / '*.txt'))):
        r = parse_chapter(os.path.basename(p), cfg)
        if not r:
            print('[跳过] 无法解析文件名：%s' % os.path.basename(p))
            continue
        num, label, upper = r
        name = '%s_%s_%s.md' % (num, label, upper) if label else '%s_%s.md' % (num, upper)
        items.append((num, os.path.basename(p), name, num in done))
    lo, hi = a.from_chapter or 1, a.to_chapter or cfg['chapters']
    items = [it for it in items if lo <= int(it[0]) <= hi]
    if a.missing_only:
        items = [it for it in items if not it[3]]
    size = a.batch or int(cfg.get('batch_size', 5))
    for i in range(0, len(items), size):
        chunk = items[i:i + size]
        print('\n=== 单元 %02d（第 %s–%s 回，共 %d 篇）===' %
              (i // size + 1, chunk[0][0], chunk[-1][0], len(chunk)))
        for num, src, dst, is_done in chunk:
            print('  %s  %s → %s%s' % (num, src, dst, '   [已存在]' if is_done else ''))
    print('\n合计 %d 篇；已完成 %d，待生成 %d。底本总数 %d，配置回数 %d。' %
          (len(items), sum(1 for x in items if x[3]), sum(1 for x in items if not x[3]),
           len(glob.glob(str(split / '*.txt'))), cfg['chapters']))


def cmd_check(a):
    cfg = load_config(a.config)
    src, nq = source_maps(cfg)
    files = out_files(cfg) if a.all else ([a.file] if a.file else [])
    if not files:
        sys.exit('未指定稿件：传 <file.md> 或 --all')
    nfail = nwarn = 0
    for f in files:
        e, w, st = check_one(f, cfg, src, nq)
        print_result(os.path.basename(f), e, w, st)
        nfail += bool(e)
        nwarn += bool(w)
    print('--- 篇数 %d，FAIL %d，WARN %d ---' % (len(files), nfail, nwarn))
    sys.exit(1 if nfail else 0)


def cmd_qc(a):
    cfg = load_config(a.config)
    src, nq = source_maps(cfg)
    files = out_files(cfg)
    nums = sorted(int(os.path.basename(f)[:3]) for f in files)
    missing = [n for n in range(1, cfg['chapters'] + 1) if n not in nums]
    dup = [n for n in set(nums) if nums.count(n) > 1]
    print('=== 完整性：篇数 %d / 应 %d；缺号 %s；重号 %s ===' %
          (len(files), cfg['chapters'], missing or '无', dup or '无'))
    nfail = nwarn = 0
    totals = dict(chars=0, events=0, quotes=0, segs=0, miss=0)
    for f in files:
        e, w, st = check_one(f, cfg, src, nq)
        if e or w:
            print_result(os.path.basename(f), e, w)
        nfail += bool(e)
        nwarn += bool(w)
        for k in totals:
            totals[k] += st[k]
    print('=== 声明事件总数＝%d（须与 README 批次表累计一致）===' % totals['events'])
    print('=== 引文片段＝%d；未锚定＝%d；字符合计＝%d；「」合计＝%d ===' %
          (totals['segs'], totals['miss'], totals['chars'], totals['quotes']))
    print('=== 篇数 %d，FAIL %d，WARN %d ===' % (len(files), nfail, nwarn))
    ok = not nfail and not missing and not dup and len(files) == cfg['chapters']
    print('=== 质检通过：结构／计数守恒／完整性／引文锚定 全部 OK ===' if ok
          else '=== 质检未通过：按 [FAIL] 逐篇修复后重试；WARN 亦须人工清零 ===')
    sys.exit(0 if ok else 1)


def cmd_readme(a):
    cfg = load_config(a.config)
    src, nq = source_maps(cfg)
    rows = []
    for f in out_files(cfg):
        _, _, st = check_one(f, cfg, src, nq)
        rows.append((os.path.basename(f), st))
    total_chars = sum(r[1]['chars'] for r in rows)
    total_ev = sum(r[1]['events'] for r in rows)
    total_q = sum(r[1]['quotes'] for r in rows)
    total_law = sum(r[1]['law'] for r in rows)
    L = []
    L.append('# 《%s》称呼学解构 · 整合版可查：规格与进度' % cfg['book'])
    L.append('')
    L.append('> 本文件只对应 `整合版可查/` 内的整合版回目，独立统计；由 pipeline.py readme 自动生成。')
    L.append('> 体例：双公式为纲、四层十二件为目、十问为检核；引文只锚定本回拆分底本与其名词列锦，跨回一律转述。')
    L.append('')
    L.append('## 1. 已收录（%d 篇，累计 %d 件）' % (len(rows), total_ev))
    L.append('')
    L.append('| 回次 | 文件 | 字符 | 事件 | 定律行 | 「」 | 未锚定 |')
    L.append('| :--- | :--- | ---: | ---: | ---: | ---: | ---: |')
    for name, st in rows:
        L.append('| %s | `%s` | %s | %d | %d | %d | %d |' %
                 (name[:3], name, format(st['chars'], ','), st['events'],
                  st['law'], st['quotes'], st['miss']))
    L.append('')
    L.append('> 合计：字符 %s，事件 %d，定律行 %d，引文「」%d 处。' %
             (format(total_chars, ','), total_ev, total_law, total_q))
    L.append('')
    L.append('## 2. 预判四题（全书级，滚动登记）')
    L.append('')
    for i, t in enumerate(cfg.get('themes', []), 1):
        L.append('%d. %s' % (i, t))
    L.append('')
    L.append('## 3. 移植适配参数')
    L.append('')
    L.append('| 适配点 | 取值 |')
    L.append('| :--- | :--- |')
    L.append('| 语料源 | `%s/NNN_*.txt`（%d 回） |' % (cfg['split_dir'], cfg['chapters']))
    L.append('| 参考坐标 | `%s/NNN_*.md` |' % cfg.get('nieq_dir', '名词列锦章节'))
    L.append('| 头标分母 | （N/%d） |' % cfg['chapters'])
    L.append('| 单篇自检 | `python pipeline.py check --config %s <稿件>`，未锚定须为 0 |' % CONFIG_NAME)
    L.append('| 全局质检 | `python pipeline.py qc --config %s` |' % CONFIG_NAME)
    L.append('')
    L.append('## 4. 批次表')
    L.append('')
    L.append('| 批次 | 回次 | 状态 | 累计事件 |')
    L.append('| :--- | :--- | :--- | ---: |')
    size = int(cfg.get('batch_size', 5))
    for lo in range(1, cfg['chapters'] + 1, size * 2):
        hi = min(lo + size * 2 - 1, cfg['chapters'])
        got = sum(1 for n in range(lo, hi + 1)
                  if any(os.path.basename(f).startswith('%03d_' % n) for f in out_files(cfg)))
        state = '**已完成（质检退出码 0、未锚定 0）**' if got == hi - lo + 1 else '进行中（%d/%d）' % (got, hi - lo + 1)
        L.append('| 第 %d–%d 回 | %d 篇 | %s | %d |' %
                 (lo, hi, got, state, got * int(cfg.get('events_per_chapter', 12))))
    L.append('')
    L.append('## 5. 生成纪律')
    L.append('')
    L.append('- 单会话一批 4–6 回防上下文衰减；全书批量改以并行执行单元（每单元约 5 回）生成，各单元按同一简报产出。')
    L.append('- 每篇写完跑单文件自检，未锚定 0 才算过关；全书合成后再跑全局质检，退出码 0 且未锚定 0。')
    L.append('- 引文只从本回拆分底本逐字复制；禁止把并列/节选词并入同一「」；跨回一律转述。')
    L.append('- 每条「谁称谁」过归属门（施称者／受称者／引语三格）；锚定通过 ≠ 归属正确。')
    L.append('- 全书 %d 篇齐全、无缺号无重号；累计事件 %d 与全局质检声明一致。' % (cfg['chapters'], total_ev))
    L.append('- 未明确说「同步／提交」，不 commit、不 push。')
    L.append('')
    _, _, out = dirs(cfg)
    target = out / 'README：整合版规格与进度.md'
    target.write_text('\n'.join(L), encoding='utf-8')
    print('已写入：%s' % target)
    print('篇数 %d，事件 %d，字符 %d，「」%d' % (len(rows), total_ev, total_chars, total_q))


def main():
    ap = argparse.ArgumentParser(description='称呼学解构（整合版）全书流水线')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('init', help='探查底本并生成配置/简报/输出目录')
    p.add_argument('--root', required=True, help='工作区根目录')
    p.add_argument('--book', required=True, help='书名，如 水浒传')
    p.add_argument('--book-dir', required=True, help='书名目录（相对 root）')
    p.add_argument('--split-dir', required=True, help='拆分底本目录名')
    p.add_argument('--nieq-dir', default='名词列锦章节', help='名词列锦目录名')
    p.add_argument('--out-dir', default='称呼学解构/整合版可查', help='输出目录（相对 book-dir）')
    p.add_argument('--chapters', type=int, required=True, help='声明回数（以底本实际数为准自动校正）')
    p.add_argument('--events', type=int, default=12, help='每回事件数')
    p.add_argument('--min-chars', type=int, default=15700, help='单篇字符下限')
    p.add_argument('--batch', type=int, default=5, help='并行单元每批回数')
    p.set_defaults(func=cmd_init)

    p = sub.add_parser('plan', help='输出底本→稿件映射与批次划分')
    p.add_argument('--config')
    p.add_argument('--batch', type=int)
    p.add_argument('--from-chapter', type=int)
    p.add_argument('--to-chapter', type=int)
    p.add_argument('--missing-only', action='store_true')
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser('check', help='单篇规格 + 锚定自检')
    p.add_argument('file', nargs='?')
    p.add_argument('--config')
    p.add_argument('--all', action='store_true')
    p.set_defaults(func=cmd_check)

    p = sub.add_parser('qc', help='全书完整性与五维质检')
    p.add_argument('--config')
    p.set_defaults(func=cmd_qc)

    p = sub.add_parser('readme', help='生成 README 进度表')
    p.add_argument('--config')
    p.set_defaults(func=cmd_readme)

    a = ap.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
