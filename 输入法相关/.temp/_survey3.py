# -*- coding: utf-8 -*-
import io, os, re, glob

ROOT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\四大名著\西游记"
TEMP = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp"
OUT  = os.path.join(TEMP, "_survey3.txt")

L = []
for sub in ("《西游记》_拆分", "西游记章节", "西游记分析"):
    d = os.path.join(ROOT, sub)
    L.append("=" * 60)
    L.append("DIR %s exists=%s" % (sub, os.path.isdir(d)))
    if not os.path.isdir(d):
        continue
    items = sorted(os.listdir(d))
    L.append("  count=%d" % len(items))
    for x in items[:8]:
        p = os.path.join(d, x)
        L.append("    %s  %s" % (x, ("%d B" % os.path.getsize(p)) if os.path.isfile(p) else "<DIR>"))
    if len(items) > 8:
        L.append("    ...")
        for x in items[-4:]:
            p = os.path.join(d, x)
            L.append("    %s  %s" % (x, ("%d B" % os.path.getsize(p)) if os.path.isfile(p) else "<DIR>"))

# 拆分文件尺寸统计 + 首行
d = os.path.join(ROOT, "《西游记》_拆分")
if os.path.isdir(d):
    L.append("=" * 60)
    L.append("拆分文件统计")
    fs = sorted(glob.glob(os.path.join(d, "*")))
    sizes = []
    heads = []
    for p in fs:
        if not os.path.isfile(p):
            continue
        b = os.path.getsize(p)
        sizes.append((os.path.basename(p), b))
        if len(heads) < 3:
            raw = open(p, "rb").read(400)
            for enc in ("utf-8-sig", "utf-8", "gbk", "utf-16"):
                try:
                    heads.append(os.path.basename(p) + " :: " + raw.decode(enc).splitlines()[0])
                    break
                except Exception:
                    pass
    L.append("  files=%d" % len(sizes))
    if sizes:
        bs = [s for _, s in sizes]
        L.append("  bytes min=%d max=%d avg=%d total=%d" % (min(bs), max(bs), sum(bs) // len(bs), sum(bs)))
    L += ["  " + h for h in heads]

# 现有 xyj batch 的标题行格式
L.append("=" * 60)
L.append("xyj_baimiao 各文件标题行样式（前6个标题）")
for p in sorted(glob.glob(os.path.join(TEMP, "xyj_baimiao", "batch_*.md"))):
    s = open(p, "rb").read().decode("utf-8-sig")
    L.append("  --- %s" % os.path.basename(p))
    n = 0
    for line in s.splitlines():
        if re.match(r"^#{1,4}\s*第", line) or re.match(r"^#{1,4}\s*第[一二三四五六七八九十百\d]+回", line):
            L.append("      %r" % line[:60])
            n += 1
            if n >= 6:
                break

# hlm head.md 结构（只取标题行）
L.append("=" * 60)
L.append("hlm head.md 结构")
hp = os.path.join(TEMP, "hlm_baimiao", "head.md")
if os.path.exists(hp):
    s = open(hp, "rb").read().decode("utf-8-sig")
    for line in s.splitlines():
        if line.startswith("#"):
            L.append("  " + line[:80])

# 西游记分析 目录里有啥
L.append("=" * 60)
d = os.path.join(ROOT, "西游记分析")
if os.path.isdir(d):
    for x in sorted(os.listdir(d)):
        p = os.path.join(d, x)
        L.append("  %s  %s" % (x, ("%d B" % os.path.getsize(p)) if os.path.isfile(p) else "<DIR>"))

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
