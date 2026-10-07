# -*- coding: utf-8 -*-
"""从已验证的 09:57 不脱敏版第六部分提取六要素，构建精简格式结果 JSON。

E2E 用：AI 精读已完成（本日期六要素在前次会话已精读验证），
此处按 phase3_merge 精简格式（idx + category + elements）输出，
引号等字符从参考文件字节级保真提取，预填行（完整版/快讯目录行）省略，
由 --merge 自动从数据源补齐。
"""
import json
import re
import sys

RECOVERY = r"C:\Users\Administrator\Documents\这是什么\JK-temp\自动化与工具\新闻联播\.temp\恢复_不脱敏版_20261006.md"
OUT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\自动化与工具\新闻联播\归档\2026年10月\六要素结果_20261006.json"

with open(RECOVERY, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

# 定位第六部分表格行
rows = []
for ln in lines:
    m = re.match(r"^\|\s*([完整版\d\-]+)\s*\|", ln)
    if not m or "序号" in ln or re.match(r"^\|-", ln):
        continue
    parts = [p.strip() for p in ln.split("|")]
    # parts: ['', idx, title, category, time, location, subject, event, cause, method, source, '']
    if len(parts) < 11:
        continue
    idx = parts[1]
    if idx in ("序号",):
        continue
    rows.append({
        "idx": idx,
        "category": parts[3],
        "elements": {
            "location": parts[5],
            "subject": parts[6],
            "event": parts[7],
            "cause": parts[8],
            "method": parts[9],
        },
    })

# 省略预填行（完整版、快讯目录行 8/12），由 --merge 从数据源补齐
skip_prefill = {"完整版", "8", "12"}
items = [r for r in rows if r["idx"] not in skip_prefill]

result = {
    "date": "20261006",
    "date_display": "2026年10月06日",
    "news_items": items,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"结果JSON已生成: {OUT}")
print(f"精读条目: {len(items)} 条（预填行省略 {len(rows) - len(items)} 条）")
for it in items:
    e = it["elements"]
    print(f"  {it['idx']:>4} [{it['category']}] {e['subject'][:14]} | {e['event'][:20]}")
