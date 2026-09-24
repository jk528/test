# -*- coding: utf-8 -*-
import io, os, glob

ROOT4 = r"C:\Users\Administrator\Documents\这是什么\JK-temp\四大名著"
TEMP  = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp"
OUT   = os.path.join(TEMP, "_survey4.txt")

L = []

# 1. 源文本编码确认（全字节解码）
p1 = os.path.join(ROOT4, "西游记", "《西游记》_拆分", "001_07305_第一回　灵根育孕源流出　心性修持大道生.txt")
raw = open(p1, "rb").read()
L.append("### 源文本编码确认 %s" % os.path.basename(p1))
L.append("bytes=%d  head16=%r" % (len(raw), raw[:16]))
for enc in ("utf-8-sig", "utf-8", "gbk", "utf-16", "utf-16-le"):
    try:
        s = raw.decode(enc)
        L.append("  [OK] %-10s -> %r" % (enc, s[:60]))
    except Exception as e:
        L.append("  [FAIL] %-10s %s" % (enc, str(e)[:70]))
s1 = raw.decode("utf-8-sig")
L.append("--- 001 前 10 行 ---")
for line in s1.splitlines()[:10]:
    L.append("  |" + line[:70])
L.append("--- 001 末 3 行 ---")
for line in s1.splitlines()[-3:]:
    L.append("  |" + line[:70])

# 2. 红楼梦最终交付文档：头尾样式
for tag, sub, name in (
    ("红楼梦", "红楼梦分析", "《红楼梦》白描手法逐回解析：120回叙事技巧统合分析.md"),
    ("水浒传", "水浒传分析", "《水浒传》白描手法逐回解析：120回叙事技巧统合分析.md"),
    ("三国演义", "三国演义分析", "《三国演义》白描手法逐回解析：120回叙事技巧统合分析.md"),
):
    fp = os.path.join(ROOT4, sub, name)
    L.append("")
    L.append("=" * 60)
    L.append("### %s 交付文档 exists=%s" % (tag, os.path.exists(fp)))
    if not os.path.exists(fp):
        continue
    t = open(fp, "rb").read().decode("utf-8-sig")
    lines = t.splitlines()
    L.append("bytes=%d lines=%d" % (len(t.encode('utf-8')), len(lines)))
    L.append("--- 前 45 行 ---")
    for line in lines[:45]:
        L.append("  |" + line[:78])
    L.append("--- 末 22 行 ---")
    for line in lines[-22:]:
        L.append("  |" + line[:78])

# 3. hlm tail.md 全文
L.append("")
L.append("=" * 60)
L.append("### hlm tail.md 全文")
tp = os.path.join(TEMP, "hlm_baimiao", "tail.md")
if os.path.exists(tp):
    for line in open(tp, "rb").read().decode("utf-8-sig").splitlines():
        L.append("  |" + line[:90])

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
