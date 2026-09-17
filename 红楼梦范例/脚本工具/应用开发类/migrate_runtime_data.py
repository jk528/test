#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把运行时数据（SQLite 主库 + 模型缓存）从同步目录内迁到同步目录外。

同步目录内保留运行时数据会带来：云盘客户端加锁导致 EBUSY、多机互相覆盖
导致库损坏、约 100 MB 模型白占同步流量。与 venv 的处理方式保持一致。
"""
import os
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
OLD = APP / ".data"
HOME = Path(os.environ.get("USERPROFILE") or Path.home())
NEW = HOME / ".honglou"

print("=" * 68)
print("迁移运行时数据到同步目录外")
print("=" * 68)
print(f"  源: {OLD}")
print(f"  目标: {NEW}")
print()

(NEW / "data").mkdir(parents=True, exist_ok=True)
(NEW / "models").mkdir(parents=True, exist_ok=True)

# ── 1. SQLite 主库 + 备份（-wal/-shm 不搬，靠 VACUUM 后的干净副本） ──
moved = []
for f in sorted(OLD.glob("honglou.sqlite*")):
    dst = NEW / "data" / f.name
    shutil.copy2(f, dst)
    moved.append((f.name, f.stat().st_size, dst.stat().st_size))
for name, a, b in moved:
    print(f"  库文件 {name:<46} {a/1048576:6.2f} MB -> {b/1048576:6.2f} MB")

# ── 2. 模型缓存：跳过 .incomplete 与 tmp_* 残件 ──
src_models = OLD / "models"
copied = skipped = 0
skip_bytes = 0
for d, _dirs, fs in os.walk(src_models):
    rel = Path(d).relative_to(src_models)
    (NEW / "models" / rel).mkdir(parents=True, exist_ok=True)
    for f in fs:
        sp = Path(d) / f
        if f.endswith(".incomplete") or f.startswith("tmp_"):
            skipped += 1
            skip_bytes += sp.stat().st_size
            continue
        shutil.copy2(sp, NEW / "models" / rel / f)
        copied += 1
print(f"  模型缓存：复制 {copied} 个有效文件，跳过 {skipped} 个残件"
      f"（{skip_bytes/1048576:.1f} MB）")

def size(p):
    return sum(os.path.getsize(os.path.join(d, f))
               for d, _s, fs in os.walk(p) for f in fs)

print(f"  新模型缓存体积：{size(NEW/'models')/1048576:.1f} MB")
print()

# ── 3. 验证：库能开、模型能加载、检索能跑 ──
print("=" * 68)
print("迁移后验证")
print("=" * 68)
sys.path.insert(0, str(APP / "sidecar"))
import config  # noqa: E402
from storage import get_store  # noqa: E402
from retrieval import get_embedder, search as rag_search  # noqa: E402

cfg = config.get_cfg()
print(f"  DATA_DIR : {config.DATA_DIR}")
print(f"  db_path  : {cfg.db_path}")
print(f"  模型缓存  : {__import__('retrieval')._FASTEMBED_CACHE}")
assert str(NEW) in cfg.db_path, "db_path 未落在新数据目录"
assert str(NEW) in __import__("retrieval")._FASTEMBED_CACHE, "模型缓存未落在新目录"

store = get_store(cfg.db_path)
print(f"  vec_ready: {store.vec_ready}")
print(f"  books    : {store.conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]}")
print(f"  chapters : {store.conn.execute('SELECT COUNT(*) FROM chapters').fetchone()[0]}")
print(f"  chunks   : {store.count_chunks('d6eefd4f47ba122d')}  "
      f"vectors: {store.count_vectors('d6eefd4f47ba122d')}")

emb = get_embedder(cfg.rag)
hits = rag_search(store, emb, cfg.rag, "贾宝玉梦游太虚幻境", "d6eefd4f47ba122d")
print(f"  检索自检 : 命中 {len(hits)}/{cfg.rag.top_k}，"
      f"首条 ch{hits[0]['chapter_idx']+1} d={hits[0]['distance']:.3f}")
ok = len(hits) == cfg.rag.top_k and store.vec_ready
print()
print("=" * 68)
print("验证通过 ✅ 新位置可用，可以清理同步目录内的旧副本"
      if ok else "验证失败 ❌ 先不要清理旧目录")
print("=" * 68)
sys.exit(0 if ok else 1)
