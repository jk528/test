#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAG 检索（M3）—— 文本分块 + BGE 嵌入 + sqlite-vec 语义检索。

嵌入模型：BGE-small-zh-v1.5（512 维，~47MB，首次使用自动下载）。
模型不进安装包：fastembed 首次调用时按需下载到本地缓存，完全离线可用。
"""

import hashlib
import os
from typing import Any, Dict, List, Optional

from config import DATA_DIR, RAGConfig
from storage import BookStore

# fastembed 的 BGE 模型缓存目录（按需下载，避免每次联网）。
# 默认落在运行时数据目录（同步目录之外，见 config._resolve_data_dir）：
# 放 %TEMP% 会被磁盘清理工具清空，90MB 模型说没就没，下次提问要重下；
# 放 app/ 下则会随云盘同步，白占流量还可能被客户端锁住。
# 可用 EMBED_CACHE_DIR 覆盖。
_FASTEMBED_CACHE = os.environ.get(
    "EMBED_CACHE_DIR",
    str(DATA_DIR / "models"))


class Embedder:
    """懒加载的嵌入器（首次 embed 才下载/加载模型，约 1-3 秒）。"""

    def __init__(self, cfg: RAGConfig):
        self.cfg = cfg
        self._model: Optional[Any] = None
        self._dim: int = 512

    def _get_model(self):
        if self._model is None:
            # HuggingFace 国内镜像兜底 + 禁用 xet（镜像站不支持 CAS 协议，401）
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            from fastembed import TextEmbedding  # type: ignore
            self._model = TextEmbedding(
                model_name=self.cfg.embed_model,
                cache_dir=_FASTEMBED_CACHE,
            )
            # 从模型配置读取维度（默认 512）
            try:
                self._dim = int(self._model.model.model_cfg["dim"])
            except Exception:  # noqa: BLE001
                self._dim = 512
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入，返回 [dim] 向量列表。空输入返回 []。"""
        if not texts:
            return []
        model = self._get_model()
        vecs = list(model.embed(texts, batch_size=self.cfg.embed_batch))
        return [[float(x) for x in v] for v in vecs]

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return self._dim
        return 512


def chunk_text(text: str, chunk_lines: int = 20,
               chapter_idx: int = 0, line_offset: int = 0,
               max_chars: int = 800) -> List[Dict[str, Any]]:
    """按物理行分块。

    text: 章内文本（\n 分隔）；line_offset: 章首在全书中的 0 基行号。
    返回 [{chapter_idx, line_start, line_end, text}]，行号为全书绝对行号。
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []
    buf_start = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped and buf:
            # 空行作为分块边界（段落分隔）
            chunks.append(_make_chunk(chapter_idx, buf, buf_start,
                                      line_offset, max_chars))
            buf, buf_start = [], i + 1
            continue
        if not stripped:
            continue
        if not buf:
            buf_start = i
        buf.append(stripped)
        if len(buf) >= chunk_lines:
            chunks.append(_make_chunk(chapter_idx, buf, buf_start,
                                      line_offset, max_chars))
            buf = []
    if buf:
        chunks.append(_make_chunk(chapter_idx, buf, buf_start,
                                  line_offset, max_chars))
    return chunks


def _make_chunk(chapter_idx: int, buf: List[str], buf_start: int,
                line_offset: int, max_chars: int) -> Dict[str, Any]:
    text = "\n".join(buf)
    if len(text) > max_chars:
        text = text[:max_chars]
    return {
        "chapter_idx": chapter_idx,
        "line_start": line_offset + buf_start,
        "line_end": line_offset + buf_start + len(buf) - 1,
        "text": text,
    }


def normalize_newlines(text: str) -> str:
    """统一换行为 \\n。同一本书经 CRLF/LF 两种读法读入时视为同一内容。"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def book_id_of(text: str) -> str:
    """书 ID = 全文内容（换行归一化后）的 SHA1 前 16 位。

    刻意**不纳入源路径**：同一本书会被不同路径读到（`C:\\…`、`\\\\?\\C:\\…`、
    另一份拷贝、relativize 与否），旧实现把路径掺进哈希，导致同一本书被存成
    多条 books 记录、检索里同一条召回重复出现多次，LLM 上下文被白白稀释。
    书 = 内容，不是位置。
    """
    norm = normalize_newlines(text).encode("utf-8", errors="ignore")
    return hashlib.sha1(norm).hexdigest()[:16]


def index_fingerprint(text: str, chapters: List[Dict[str, Any]],
                      chunk_lines: int) -> str:
    """索引签名 = 内容 + 分块行数 + 章节结构。

    用于判断「这本书的向量索引是否还是当前原文/参数的索引」。三者任一变化
    （换书、改 RAG_CHUNK_LINES、章节正则调整）都必须重建，否则召回会指向
    已经不存在或已经错位的正文位置。
    """
    h = hashlib.sha1()
    h.update(normalize_newlines(text).encode("utf-8", errors="ignore"))
    h.update(f"|cl={chunk_lines}|n={len(chapters)}".encode())
    for c in chapters:
        h.update(f"|{c.get('idx')}:{c.get('start_line')}"
                 f":{c.get('end_line')}".encode())
    return h.hexdigest()[:16]


def build_index(store: BookStore, embedder: Embedder, cfg: RAGConfig,
                book_id: str, raw_text: str,
                chapters: List[Dict[str, Any]],
                force: bool = False) -> Dict[str, Any]:
    """整书分块 + 嵌入 + 写库。返回索引统计。

    幂等：若库中已有与该书当前内容/参数一致的完整索引，直接跳过重建。
    前端每次打开书都会调用本方法，不设幂等会让每次开书都白跑一遍嵌入
    （228 分块约数秒 CPU），并且反复制造向量孤儿。
    """
    sig = index_fingerprint(raw_text, chapters, cfg.chunk_lines)
    if not force:
        n_chunks = store.count_chunks(book_id)
        if (n_chunks > 0 and store.get_index_sig(book_id) == sig
                and store.count_vectors(book_id) == n_chunks):
            return {
                "chunks": n_chunks, "embedded": n_chunks, "skipped": True,
                "vec_ready": store.vec_ready, "model": cfg.embed_model,
                "dim": embedder.dimension, "sig": sig,
            }
    lines = normalize_newlines(raw_text).split("\n")
    all_chunks: List[Dict[str, Any]] = []
    for ch in chapters:
        start = int(ch.get("start_line", 0))
        end = int(ch.get("end_line", len(lines) - 1))
        seg = "\n".join(lines[start:end + 1])
        all_chunks.extend(chunk_text(
            seg, chunk_lines=cfg.chunk_lines,
            chapter_idx=int(ch.get("idx", 0)), line_offset=start))
    chunk_ids = store.add_chunks(book_id, all_chunks)
    # 分批嵌入（避免一次嵌入全部长文本的内存峰值）
    embedded = 0
    batch = 32
    for i in range(0, len(all_chunks), batch):
        batch_chunks = all_chunks[i:i + batch]
        vecs = embedder.embed([c["text"] for c in batch_chunks])
        embedded += store.store_embeddings(chunk_ids[i:i + batch], vecs)
    store.set_index_sig(book_id, sig)
    return {
        "chunks": len(all_chunks), "embedded": embedded, "skipped": False,
        "vec_ready": store.vec_ready, "model": cfg.embed_model,
        "dim": embedder.dimension, "sig": sig,
    }


def search(store: BookStore, embedder: Embedder, cfg: RAGConfig,
           query: str, book_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """查询向量化 → topK 召回 → 返回片段列表。"""
    if not store.vec_ready:
        return []
    vec = embedder.embed([query])
    if not vec:
        return []
    return store.search_chunks(vec[0], top_k=cfg.top_k, book_id=book_id)


# 模块级嵌入器单例（sidecar 进程内复用，模型只加载一次）
_embedder: Optional[Embedder] = None


def get_embedder(cfg: RAGConfig) -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder(cfg)
    return _embedder


def reset_embedder() -> None:
    global _embedder
    _embedder = None