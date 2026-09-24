# -*- coding: utf-8 -*-
import io, os, shutil, sys

ROOT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\四大名著\通用分析"
SRC  = os.path.join(ROOT, "拆分文本白描逐回分析_通用任务方法论.md")
TMP  = os.path.join(ROOT, ".temp")
OUT  = os.path.join(TMP, "inspect.txt")

os.makedirs(TMP, exist_ok=True)

raw = open(SRC, "rb").read()
bom = raw[:3] == b"\xef\xbb\xbf"
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n")

s = raw.decode("utf-8-sig")

lines = []

lines.append("exists=%s" % os.path.exists(SRC))
lines.append("bytes=%d" % len(raw))
lines.append("has_bom=%s" % bom)
lines.append("crlf=%d lf_total=%d" % (crlf, lf))
lines.append("chars=%d" % len(s))
lines.append("line_count=%d" % len(s.splitlines()))

# backup
bkdir = os.path.join(TMP, "bak")
os.makedirs(bkdir, exist_ok=True)
bk = os.path.join(bkdir, "拆分文本白描逐回分析_通用任务方法论.orig.md")
shutil.copyfile(SRC, bk)
lines.append("backup=%s exists=%s bytes=%d" % (bk, os.path.exists(bk), os.path.getsize(bk)))

# anchors that matter (ASCII-only probes where possible)
probes = [
    "2\u20134",
    "batch_01",
    "hits.txt",
    "\u8865\u5168\u5b50\u4ee3\u7406",
    "\u8865\u5168\u8f6e",
    "\u4e2d\u95f4\u76ee\u5f55",
]
for p in probes:
    lines.append("probe %r -> %d" % (p, s.count(p)))

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(lines))
print("OK")
