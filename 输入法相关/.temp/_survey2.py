# -*- coding: utf-8 -*-
import io, os, re, glob

TEMP = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp"
ROOT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\四大名著"
OUT  = os.path.join(TEMP, "_survey2.txt")

CN = {'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

def cn2int(s):
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, section, num = 0, 0, 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            section += (num if num else 1) * 10
            num = 0
        elif ch == '百':
            section += (num if num else 1) * 100
            num = 0
        else:
            return None
    return total + section + num

L = []

# ---------- 1. 四大名著 目录结构 ----------
L.append("### TREE 四大名著 (depth<=2)")
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d)
    if os.path.isdir(p):
        subs = sorted(os.listdir(p))
        L.append("  [D] %s  -> %s" % (d, ", ".join(subs[:14])))
    else:
        L.append("  [F] %s" % d)

# ---------- 2. 找西游记源文本 ----------
L.append("")
L.append("### 西游记 related paths")
for pat in ("西游记", "*xiyouji*", "*xyj*", "*journey*"):
    for p in glob.glob(os.path.join(ROOT, "**", pat), recursive=True)[:20]:
        L.append("  %s" % p)

# ---------- 3. xyj_baimiao 精确画像 ----------
L.append("")
L.append("### xyj_baimiao 精确画像")
d = os.path.join(TEMP, "xyj_baimiao")
for p in sorted(glob.glob(os.path.join(d, "batch_*.md"))):
    s = open(p, "rb").read().decode("utf-8-sig")
    title = s.splitlines()[0] if s.splitlines() else ""
    # 章节标题：## 第X回 或 ### 第X回
    heads = re.findall(r"(?m)^#{2,4}\s*第([一二三四五六七八九十百\d]+)回", s)
    # 命中行
    hits_lines = re.findall(r"(?m)^\*\*本回命中\*\*(.*)$", s)
    L.append("  %-14s %s" % (os.path.basename(p), title))
    L.append("     声明章节标题: %s" % title)
    nums = [cn2int(h) for h in heads]
    L.append("     实际含回: %s (共%d回)" % (nums, len(nums)))
    # 逐回片段数
    blocks = re.split(r"(?m)(?=^#{2,4}\s*第[一二三四五六七八九十百\d]+回)", s)
    for b in blocks:
        m = re.search(r"(?m)^#{2,4}\s*第([一二三四五六七八九十百\d]+)回", b)
        if not m:
            continue
        n = cn2int(m.group(1))
        nf = len(re.findall(r"(?m)^\d+\.\s+\*\*", b))
        hits_m = re.search(r"(?m)^\*\*本回命中\*\*[:：]?\s*(.+)$", b)
        hn = 0
        if hits_m:
            hn = len([x for x in re.split(r"[、,，;；]", hits_m.group(1)) if x.strip() and not x.strip().startswith("（")])
        L.append("       第%-3s回 片段=%-3d 命中≈%d" % (n, nf, hn))

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
