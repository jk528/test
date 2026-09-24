# -*- coding: utf-8 -*-
import io, os, re, glob

BASE = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp"
OUT  = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp\_survey.txt"

L = []
for tag in ("xyj_baimiao", "hlm_baimiao", "sgyy_baimiao", "shz_baimiao"):
    d = os.path.join(BASE, tag)
    L.append("=" * 60)
    L.append("DIR %s exists=%s" % (tag, os.path.isdir(d)))
    if not os.path.isdir(d):
        continue
    for p in sorted(glob.glob(os.path.join(d, "*"))):
        raw = open(p, "rb").read()
        s = raw.decode("utf-8-sig")
        heads = re.findall(r"(?m)^### 第\s*(\d+)\s*回", s)
        hits  = re.findall(r"(?m)^\*\*本回命中\*\*", s)
        frags = re.findall(r"(?m)^\d+\.\s+\*\*", s)
        L.append("  %-16s bytes=%-7d lines=%-5d chapters=%-3d( %s..%s )  hitsLines=%-3d fragments=%d"
                 % (os.path.basename(p), len(raw), s.count("\n") + 1,
                    len(heads), heads[0] if heads else "-", heads[-1] if heads else "-",
                    len(hits), len(frags)))
    # per-chapter fragment counts for a couple of files
L.append("=" * 60)
L.append("detail: xyj_baimiao per-chapter fragment count")
for p in sorted(glob.glob(os.path.join(BASE, "xyj_baimiao", "batch_*.md"))):
    s = open(p, "rb").read().decode("utf-8-sig")
    blocks = re.split(r"(?=### 第)", s)
    L.append("  " + os.path.basename(p))
    for b in blocks:
        m = re.match(r"### 第\s*(\d+)\s*回", b)
        if not m:
            continue
        nf = len(re.findall(r"(?m)^\d+\.\s+\*\*", b))
        L.append("     第%-3s回 fragments=%d" % (m.group(1), nf))
L.append("=" * 60)
L.append("hlm hits.txt first 3 / last 2 lines")
hp = os.path.join(BASE, "hlm_baimiao", "hits.txt")
if os.path.exists(hp):
    hl = open(hp, "rb").read().decode("utf-8-sig").splitlines()
    L.append("  lines=%d" % len(hl))
    L += ["  " + x for x in hl[:3]]
    L += ["  " + x for x in hl[-2:]]

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
