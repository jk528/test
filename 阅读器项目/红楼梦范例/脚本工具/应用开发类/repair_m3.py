#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 数据修复：去重 books/chapters/chunks + 清孤儿向量，然后端到端验证。

只动派生缓存表（可完全重建），且脚本外已做文件级备份。
"""
import os
import shutil
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, ".."))
SIDE = os.path.join(APP, "sidecar")
sys.path.insert(0, SIDE)

DB = os.path.join(APP, ".data", "honglou.sqlite")
BOOK = os.path.abspath(os.path.join(APP, "..", "红楼梦.txt"))

print("=" * 68)
print("步骤 0｜备份")
print("=" * 68)
bak = DB + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(DB, bak)
print(f"  已备份 -> {os.path.basename(bak)}  ({os.path.getsize(bak)/1048576:.2f} MB)")
for ext in ("-wal", "-shm"):
    src = DB + ext
    if os.path.exists(src):
        shutil.copy2(src, bak + ext)
        print(f"  已备份 -> {os.path.basename(bak)}{ext}")

import sqlite_vec  # noqa: E402

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
con.enable_load_extension(True)
sqlite_vec.load(con)
con.enable_load_extension(False)

print()
print("=" * 68)
print("步骤 1｜修复前状态")
print("=" * 68)
before = {}
for t in ("books", "chapters", "chunks", "emotions", "annotations"):
    before[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:<14} {before[t]:>5}")
before["vectors"] = con.execute("SELECT COUNT(*) FROM chunk_vec").fetchone()[0]
orph = con.execute("SELECT COUNT(*) FROM chunk_vec v LEFT JOIN chunks c "
                   "ON c.id=v.chunk_id WHERE c.id IS NULL").fetchone()[0]
print(f"  {'chunk_vec':<14} {before['vectors']:>5}  其中孤儿 {orph}")

print()
print("=" * 68)
print("步骤 2｜清理")
print("=" * 68)
# 孤儿向量
cur = con.execute("DELETE FROM chunk_vec WHERE chunk_id NOT IN (SELECT id FROM chunks)")
print(f"  删除孤儿向量 {cur.rowcount} 行")
# 旧 book_id 全部作废（旧 id = 路径 + 首 64KB，与新口径不同）
for t in ("emotions", "chunks", "chapters", "annotations", "books"):
    cur = con.execute(f"DELETE FROM {t}")
    print(f"  清空 {t:<12} {cur.rowcount} 行")
# 顺带清掉旧 schema 迁移遗留与自增计数
con.execute("DELETE FROM sqlite_sequence")
con.commit()
con.execute("VACUUM")
con.close()
print("  已 VACUUM")

print()
print("=" * 68)
print("步骤 3｜端到端验证（走真实 sidecar 模块）")
print("=" * 68)
import config  # noqa: E402
from storage import get_store  # noqa: E402
from retrieval import get_embedder, book_id_of, build_index, search  # noqa: E402
from honglou_sidecar import parse_chapters  # noqa: E402

cfg = config.get_cfg()
store = get_store(cfg.db_path)
print(f"  db      : {cfg.db_path}")
print(f"  vec_ready: {store.vec_ready}")

text = open(BOOK, "rb").read().decode("utf-8", errors="replace")
bid = book_id_of(text)
print(f"  book_id : {bid}   （纯内容哈希）")

chapters, total_lines = parse_chapters(text)
print(f"  解析    : {len(chapters)} 章 / {total_lines} 行")

store.upsert_book(bid, "红楼梦", BOOK, len(text))
store.replace_chapters(bid, [
    {"idx": c["index"] - 1, "title": c["title"], "start_line": c["line"],
     "end_line": (chapters[i + 1]["line"] - 1 if i + 1 < len(chapters)
                  else total_lines - 1)}
    for i, c in enumerate(chapters)])
print(f"  入库    : books 1 行, chapters {len(chapters)} 行")

emb = get_embedder(cfg.rag)
ch_list = [{"idx": i, "title": c["title"], "start_line": c["line"],
            "end_line": (chapters[i + 1]["line"] - 1 if i + 1 < len(chapters)
                         else total_lines - 1)}
           for i, c in enumerate(chapters)]

t0 = time.time()
r1 = build_index(store, emb, cfg.rag, bid, text, ch_list)
dt1 = time.time() - t0
print(f"  建索引  : chunks={r1['chunks']} embedded={r1['embedded']} "
      f"skipped={r1['skipped']} 耗时 {dt1:.1f}s")

t0 = time.time()
r2 = build_index(store, emb, cfg.rag, bid, text, ch_list)
dt2 = time.time() - t0
print(f"  再调用  : skipped={r2['skipped']} 耗时 {dt2:.2f}s  "
      f"→ {'幂等生效 ✅' if r2['skipped'] else '幂等失效 ❌'}")

n_chunks = store.count_chunks(bid)
n_vec = store.count_vectors(bid)
n_all = store.count_all_vectors()
print(f"  chunks={n_chunks}  有效向量={n_vec}  向量总数={n_all}  "
      f"孤儿={n_all - n_vec}")

print()
print("  检索召回（含去重检查）：")
ok = True
for q in ["贾宝玉梦游太虚幻境", "王熙凤协理宁国府", "林黛玉初进贾府", "宝玉挨打"]:
    hits = search(store, emb, cfg.rag, q, bid)
    keys = [(h["chapter_idx"], h["line_start"]) for h in hits]
    uniq = len(set(keys))
    dup = len(keys) - uniq
    flag = "✅" if dup == 0 and len(hits) == cfg.rag.top_k else "⚠️"
    if dup or len(hits) != cfg.rag.top_k:
        ok = False
    print(f"    {flag} {q:<20} 命中 {len(hits)}/{cfg.rag.top_k} 去重后 {uniq} 重复 {dup}")
    for h in hits[:3]:
        print(f"         ch{h['chapter_idx']+1:<4}行{h['line_start']:<5} "
              f"d={h['distance']:.3f}  {h['text'][:22]!r}")

print()
print("=" * 68)
final = os.path.getsize(DB) / 1048576
print(f"结果：修复前 {before['vectors']} 向量(孤儿{orph}) / "
      f"{before['books']} 本书 -> 修复后 {n_all} 向量(孤儿{n_all-n_vec}) / 1 本书")
print(f"      DB {final:.2f} MB（修复前 6.32 MB）")
print(f"      检索去重与满额召回：{'全部通过 ✅' if ok else '仍有问题 ❌'}")
print("=" * 68)
