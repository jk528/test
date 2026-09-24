# -*- coding: utf-8 -*-
import io, os, re, shutil, glob

TEMP = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp"
XYJ  = os.path.join(TEMP, "xyj_baimiao")
BAK  = os.path.join(TEMP, "xyj_baimiao.bak")
OUT  = os.path.join(TEMP, "_norm_report.txt")

CN = {'零':0,'〇':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

def cn2int(s):
    s = s.strip()
    if s.isdigit():
        return int(s)
    num, section = 0, 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            section += (num if num else 1) * 10; num = 0
        elif ch == '百':
            section += (num if num else 1) * 100; num = 0
        else:
            return None
    return section + num

# ---------- 1. 备份 ----------
os.makedirs(BAK, exist_ok=True)
n_bak = 0
for p in glob.glob(os.path.join(XYJ, "*")):
    d = os.path.join(BAK, os.path.basename(p))
    if not os.path.exists(d):
        shutil.copyfile(p, d)
    n_bak += 1

RE_H   = re.compile(r'^#{1,4}\s*第\s*([一二三四五六七八九十百〇零\d]+)\s*回[　\s]*(.*?)\s*$')
RE_GRP = re.compile(r'^#{1,4}\s*第[一二三四五六七八九十百〇零\d]+批')
RE_FR  = re.compile(r'^\s*(\d+)\.\s+(\*\*[^\n]+?)\s*$')
RE_ZH   = re.compile(r'^\*\*主线\*\*[:：]\s*(.+?)\s*$')
RE_HIT = re.compile(r'^\*\*本回命中\*\*[:：]?\s*(.+?)\s*$')

def norm_titles(t):
    t = re.sub(r'[\s　]+', '　', t).strip('　')
    return t

L = []
L.append("备份文件数 = %d -> %s" % (n_bak, BAK))

for pf in ("batch_04.md", "batch_06.md", "batch_07.md", "batch_09.md", "batch_10.md"):
    fp = os.path.join(XYJ, pf)
    src = io.open(fp, encoding="utf-8", newline="").read()
    lines = src.split("\n")

    # 切块
    blocks, cur = [], None
    for ln in lines:
        m = RE_H.match(ln)
        if m and not RE_GRP.match(ln):
            if cur: blocks.append(cur)
            cur = {"n": cn2int(m.group(1)), "titles": norm_titles(m.group(2)), "body": []}
            continue
        if RE_GRP.match(ln):
            continue
        if ln.strip() in ("---", ""):
            continue
        if cur is None:
            continue          # 丢弃首个标题之前的文件总标题/框架说明
        cur["body"].append(ln.rstrip())
    if cur: blocks.append(cur)

    out_parts, rep = [], []
    for b in blocks:
        main, frags, hits, other = None, [], None, []
        for ln in b["body"]:
            s = ln.strip()
            if not s:
                continue
            if RE_ZH.match(s):
                main = re.sub(r'^\*\*主线\*\*[:：]\s*', '', s)
                continue
            if s.startswith("**手法片段**"):
                continue
            mf = RE_FR.match(s)
            if mf:
                frags.append(re.sub(r'^\d+\.\s+', '', s))
                continue
            mh = RE_HIT.match(s)
            if mh:
                h = mh.group(1)
                h = re.sub(r'（\s*\d+\s*项\s*）\s*$', '', h).rstrip('。').rstrip()
                hits = h
                continue
            other.append(s)

        assert b["n"] is not None, pf + " 章节号解析失败"
        assert main, "%s 第%s回 缺主线" % (pf, b["n"])
        assert hits, "%s 第%s回 缺命中行" % (pf, b["n"])
        assert frags, "%s 第%s回 无片段" % (pf, b["n"])
        if other:
            L.append("  !! %s 第%s回 有未归类行 %d 条: %s" % (pf, b["n"], len(other), other[:2]))

        part = ["### 第 %d 回　%s" % (b["n"], b["titles"]), "",
                "**主线**：%s" % main, "",
                "**手法片段**：", ""]
        for i, f in enumerate(frags, 1):
            part += ["%d. %s" % (i, f), ""]
        part += ["**本回命中**：%s" % hits, ""]
        out_parts.append("\n".join(part))
        rep.append(b["n"])

    new = "\n".join(out_parts) + "\n"
    io.open(fp, "w", encoding="utf-8", newline="").write(new)

    # 回读断言
    chk = io.open(fp, encoding="utf-8", newline="").read()
    assert chk == new, pf + " 回读不一致"
    L.append("%s: 规整 %d 回 -> %s   bytes %d -> %d"
             % (pf, len(blocks), rep, len(src.encode('utf-8')), len(new.encode('utf-8'))))

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
