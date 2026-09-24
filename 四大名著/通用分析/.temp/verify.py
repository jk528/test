# -*- coding: utf-8 -*-
import io, os

ROOT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\四大名著\通用分析"
SRC  = os.path.join(ROOT, "拆分文本白描逐回分析_通用任务方法论.md")
OUT  = os.path.join(ROOT, ".temp", "verify.txt")

raw = open(SRC, "rb").read()
s = raw.decode("utf-8-sig")

L = []
L.append("bytes=%d" % len(raw))
L.append("has_bom=%s" % (raw[:3] == b"\xef\xbb\xbf"))
L.append("crlf=%d  lone_lf=%d" % (raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n")))
L.append("chars=%d" % len(s))

must_have = [
    "ContentProducer",            # frontmatter intact
    "v1 \u2192 v2 \u53d8\u66f4\u6458\u8981",
    "\u5168\u96c6\u53e3\u5f84",   # 全集口径
    "## \u4e94\u3001\u5199\u5165\u65b9\u5f0f",  # ## 五、写入方式
    "\u4e0d\u662f\u7cbe\u9009",   # 不是精选
    "\u00a77.7",                  # fixed cross-ref
    "batch_NN.md",
    "{batch_01}",  # placeholder-ish (may not exist)
]
for k in must_have[:-1]:
    L.append("HAS %r = %d" % (k, s.count(k)))

must_gone = [
    "\u6bcf{\u7ae0\u5355\u4f4d}\u9009\u0032\u81f3\u0034\u4e2a\u6700\u5178\u578b",  # 每{章单位}选2至4个最典型
    "\u5b81\u7f3a\u6bcb\u6ee5\uff0c\u540c\u4e00\u624b\u6cd5\u4e0d\u91cd\u590d\u4e3e\u4f8b",
    "\u00a77.3",
]
for k in must_gone:
    L.append("GONE %r = %d" % (k, s.count(k)))

L.append("step8_title_ok=%s" % ("\u6b65\u9aa4 8\uff1a\u8865\u6f0f\u8f6e" in s))
L.append("tplA_head_ok=%s" % ("\u6a21\u677f A\uff1a\u9996\u8f6e\u9010\u7ae0\u5206\u6790\uff08\u5168\u96c6\u53e3\u5f84\uff09" in s))
L.append("tail_ok=%s" % (s.rstrip().endswith("> AI\u751f\u6210")))

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
