#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红楼梦阅读分析一体化 — Python sidecar（M4：全景分析）

通信协议：stdio 上的 NDJSON / JSON-RPC 2.0 风格（每行一个 JSON 对象）
  请求：{"id": <int|str>, "method": "<方法名>", "params": {…}}
  成功：{"id": <同请求>, "result": {…}}
  失败：{"id": <同请求>, "error": {"code": <int>, "message": "<说明>"}}
  约定：stdout 只输出响应（保证 NDJSON 干净）；所有日志走 stderr。

版本演进：
  M1: ping / chapter_outline
  M2: analyze_sentiment / analyze_chapters（段落级情感 + 字级定位）
  M3: SQLite 主库（storage.py）+ RAG（retrieval.py）+ LLM 问答（llm.py）
      db_status / save_book / get_book / get_chapter_emotions /
      build_index / search / ask_ai / 标注增删查
  M4: 全景分析 —— 把既有 120 章 V3.4 报告「回灌」进库（analysis_import.py），
      产出事件时间线 / 人物榜与出场 / 伏笔起收 / 人物关系，全部带物理行锚点
      import_analysis / overview / list_events / list_entities / get_entity /
      list_mentions / list_foreshadows / list_relations
  M4.5: 全书预处理（把分析前置到开书时，读的时候直接吃库）——
      prepare_book / prepare_status / list_chapter_emotions

仅使用标准库 + jieba + venv 内依赖，便于 PyInstaller 打包。
"""

import json
import os
import re
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

# 确保同目录模块可导入（PyInstaller/开发态一致）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Windows 下 Python stdout 默认用系统码页（GBK），Rust 按 UTF-8 读会炸。
# 三层保险：Rust 设 PYTHONIOENCODING=utf-8 + 这里 reconfigure + JSON ensure_ascii=True。
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
except (AttributeError, Exception):
    pass

from config import cfg, resolve_analysis_dir, resolve_base_dir  # noqa: E402
from analysis_import import import_analysis  # noqa: E402
from storage import BookStore, get_store  # noqa: E402
from llm import get_llm  # noqa: E402
from retrieval import (  # noqa: E402
    Embedder, book_id_of, build_index, chunk_text, index_fingerprint,
    search as rag_search,
)

PROTOCOL = "honglou-sidecar/1"
SIDE_VERSION = "0.5.0-m4.5"

# 与 split_txt.bas 默认正则 #1、前端 src/lib/chapters.ts 一致
CHAPTER_RE = re.compile(r"^第([0-9一二三四五六七八九十百千万零〇两壹贰叁肆伍陆柒捌玖拾佰仟]+)(章|回|节|卷)\s*(.*)$")

# DUTIR 七类情绪顺序（与 emotion_analysis.py EmotionAnalyzer 一致）
EMOTION_ORDER = ["好", "乐", "哀", "怒", "惧", "恶", "惊"]


def log(msg: str) -> None:
    """日志一律走 stderr，避免污染 stdout 的 NDJSON。"""
    print(f"[sidecar] {msg}", file=sys.stderr, flush=True)


def read_text_auto(path: str) -> str:
    """BOM 优先；无 BOM 先 UTF-8 严格解码，失败回退 GBK。与 Rust read_text_file 对齐。"""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk", errors="replace")


def parse_chapters(text: str):
    """逐行、行首锚定，返回 (章节列表, 总行数)；行号为 0 基物理行。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters = []
    for i, raw_line in enumerate(lines):
        m = CHAPTER_RE.match(raw_line)
        if not m:
            continue
        chapters.append({
            "index": len(chapters) + 1,
            "line": i,
            "title": raw_line.strip(),
            "number_text": m.group(1),
            "unit": m.group(2),
            "name": (m.group(3) or "").strip(),
        })
    return chapters, len(lines)


# ---------------- 情感引擎（M2，懒加载） ----------------

BASE_DIR = resolve_base_dir()
_engine = None


def _get_engine():
    """加载 jieba（红楼梦分词词典）+ EmotionAnalyzer（DUTIR 七类）。"""
    global _engine
    if _engine is not None:
        return _engine
    if not BASE_DIR:
        raise RuntimeError("基础目录未找到（HONGLOU_BASE_DIR 未设且相对路径无效）")
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from emotion_analysis import EmotionAnalyzer  # noqa: E402
    import jieba  # noqa: E402
    seg_dict = os.path.join(BASE_DIR, "红楼梦分词词典.txt")
    if os.path.isfile(seg_dict):
        jieba.load_userdict(seg_dict)
    analyzer = EmotionAnalyzer()
    _engine = {"jieba": jieba, "analyzer": analyzer}
    log(f"分析引擎已加载 BASE_DIR={BASE_DIR}")
    return _engine


# ---------------- 存储 / LLM / RAG 单例 ----------------

def _store() -> BookStore:
    return get_store(cfg.db_path)


def _embedder():
    from retrieval import get_embedder
    return get_embedder(cfg.rag)


# ---------------- JSON-RPC 方法表 ----------------

def m_ping(_params: dict) -> dict:
    return {"protocol": PROTOCOL, "version": SIDE_VERSION,
            "python": sys.version.split()[0],
            "db_path": cfg.db_path}


def m_chapter_outline(params: dict) -> dict:
    """params: {path?: str, text?: str}，二选一。"""
    text = params.get("text")
    source = params.get("source", "inline")
    if text is None:
        path = params.get("path")
        if not path:
            raise ValueError("params 需要 path 或 text")
        text = read_text_auto(path)
        source = path
    chapters, total_lines = parse_chapters(text)
    return {
        "source": source, "total_lines": total_lines,
        "chapter_count": len(chapters), "chapters": chapters,
    }


def _analyze_lines(lines: List[str], indices: List[int], eng: dict) -> List[dict]:
    """对 lines 的指定物理行做段落级情感 + 字级词定位（公共实现）。

    供 m_analyze_sentiment（视口/临时文本）与 m_prepare_book（全书预处理）共用，
    保证两条路径的结果口径完全一致 —— 这是「预处理结果可直接替代实时计算」的前提。

    返回按 indices 顺序的列表，每项：
      {line, dutir_top, polarity, intensity, weights, word_spans,
       word_count, emo_total, pos_count, neg_count}
    """
    jieba = eng["jieba"]
    analyzer = eng["analyzer"]
    emo_dicts = analyzer.emotion_dicts
    out: List[dict] = []
    for i in indices:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            out.append({"line": i, "dutir_top": None, "polarity": 0.0,
                        "intensity": 0.0, "weights": {}, "word_spans": [],
                        "word_count": 0, "emo_total": 0,
                        "pos_count": 0, "neg_count": 0})
            continue
        leading = len(line) - len(line.lstrip())
        words = jieba.lcut(stripped)
        result = analyzer.analyze_words(words)
        counts = result["emotion_counts"]
        total = result["total_emotion_words"]
        pos_c = result["positive_emotion_count"]
        neg_c = result["negative_emotion_count"]
        if total == 0:
            out.append({"line": i, "dutir_top": None, "polarity": 0.0,
                        "intensity": 0.0, "weights": {}, "word_spans": [],
                        "word_count": len(words), "emo_total": 0,
                        "pos_count": 0, "neg_count": 0})
            continue
        pos = 0
        word_spans = []
        for word in words:
            if word.strip():
                for emo in EMOTION_ORDER:
                    if word in emo_dicts.get(emo, set()):
                        word_spans.append({
                            "start": leading + pos,
                            "end": leading + pos + len(word),
                            "emotion": emo, "word": word,
                        })
                        break
            pos += len(word)
        top = max(EMOTION_ORDER, key=lambda e: counts.get(e, 0))
        polarity = round((pos_c - neg_c) / total, 3)
        intensity = round(total / max(len(words), 1), 3)
        weights = {e: counts.get(e, 0) for e in EMOTION_ORDER}
        out.append({"line": i, "dutir_top": top, "polarity": polarity,
                    "intensity": intensity, "weights": weights,
                    "word_spans": word_spans, "word_count": len(words),
                    "emo_total": total, "pos_count": pos_c, "neg_count": neg_c})
    return out


def m_analyze_sentiment(params: dict) -> dict:
    """段落级（物理行级）情感分析 + 字级情感词定位。"""
    text = params.get("text")
    if not isinstance(text, str):
        raise ValueError("params 需要 text (string)")
    text = params.get("text")
    if not isinstance(text, str):
        raise ValueError("params 需要 text (string)")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip()]
    rows = _analyze_lines(lines, idx, _get_engine())
    return {"paragraphs": [{
        "line_offset": r["line"], "dutir_top": r["dutir_top"],
        "polarity": r["polarity"], "intensity": r["intensity"],
        "weights": r["weights"], "word_spans": r["word_spans"],
    } for r in rows]}


def m_analyze_chapters(params: dict) -> dict:
    """批量分析所有章节的主导情绪（用于目录着色）。"""
    text = params.get("text")
    chapters = params.get("chapters")
    if not isinstance(text, str) or not isinstance(chapters, list):
        raise ValueError("params 需要 text (string) 和 chapters (list)")
    eng = _get_engine()
    jieba = eng["jieba"]
    analyzer = eng["analyzer"]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    total_lines = len(lines)
    chapter_emotions = []
    for idx, ch in enumerate(chapters):
        start = ch.get("line", 0)
        end = chapters[idx + 1]["line"] if idx + 1 < len(chapters) else total_lines
        all_counts = {e: 0 for e in EMOTION_ORDER}
        total_emotion = 0
        total_words = 0
        pos_count = 0
        neg_count = 0
        for line_no in range(start, min(end, total_lines)):
            stripped = lines[line_no].strip()
            if not stripped:
                continue
            words = jieba.lcut(stripped)
            result = analyzer.analyze_words(words)
            for e in EMOTION_ORDER:
                all_counts[e] += result["emotion_counts"].get(e, 0)
            total_emotion += result["total_emotion_words"]
            total_words += len(words)
            pos_count += result["positive_emotion_count"]
            neg_count += result["negative_emotion_count"]
        if total_emotion == 0:
            chapter_emotions.append({
                "index": idx + 1, "dutir_top": None, "polarity": 0.0,
                "intensity": 0.0, "weights": all_counts,
            })
            continue
        top = max(EMOTION_ORDER, key=lambda e: all_counts[e])
        polarity = round((pos_count - neg_count) / total_emotion, 3)
        intensity = round(total_emotion / max(total_words, 1), 3)
        chapter_emotions.append({
            "index": idx + 1, "dutir_top": top, "polarity": polarity,
            "intensity": intensity, "weights": all_counts,
        })
    return {"chapter_emotions": chapter_emotions}


# ---------- M3：SQLite 主库 ----------

def m_db_status(_params: dict) -> dict:
    store = _store()
    return {
        "db_path": cfg.db_path, "vec_ready": store.vec_ready,
        "tables": [r[0] for r in store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")],
        "llm_configured": get_llm(cfg.llm).usable,
        "analysis_dir": resolve_analysis_dir(),
        "version": SIDE_VERSION,
    }


def m_save_book(params: dict) -> dict:
    """params: {title, source_path, text} —— 自动计算 book_id、写书与章节。"""
    title = params.get("title", "")
    source_path = params.get("source_path", "")
    text = params.get("text", "")
    if not text:
        raise ValueError("params 需要 text")
    book_id = params.get("book_id") or book_id_of(text)
    chapters, total_lines = parse_chapters(text)
    store = _store()
    store.upsert_book(book_id, title, source_path, len(text))
    store.replace_chapters(book_id, [
        {"idx": c["index"] - 1, "title": c["title"],
         "start_line": c["line"],
         "end_line": (chapters[i + 1]["line"] - 1
                      if i + 1 < len(chapters) else total_lines - 1)}
        for i, c in enumerate(chapters)])
    return {"book_id": book_id, "chapters": len(chapters),
            "total_lines": total_lines}


def m_get_book(params: dict) -> dict:
    book_id = params.get("book_id")
    store = _store()
    book = store.get_book(book_id) if book_id else None
    chapters = store.get_chapters(book_id) if book_id else []
    return {"book": book, "chapters": chapters}


def m_save_chapter_emotions(params: dict) -> dict:
    """params: {book_id, chapter_idx, rows:[{line_start,line_end,dutir_top,
              polarity,intensity,weights}]} —— 整章替换。"""
    store = _store()
    store.replace_chapter_emotions(params["book_id"], int(params["chapter_idx"]),
                                   params.get("rows", []))
    return {"saved": len(params.get("rows", []))}


def m_get_chapter_emotions(params: dict) -> dict:
    rows = _store().get_chapter_emotions(params["book_id"],
                                         int(params["chapter_idx"]))
    return {"rows": rows}


def m_upsert_emotions(params: dict) -> dict:
    """params: {book_id, chapter_idx, rows:[{line_start,line_end,dutir_top,
              polarity,intensity,weights,word_spans}]} —— 按行增量写。

    与 save_chapter_emotions（整章替换）的区别：前端是视口驱动、分批算的，
    整章替换会让后到的批次冲掉先前批次的成果，故增量场景走本方法。
    """
    n = _store().upsert_emotions(params["book_id"],
                                 int(params["chapter_idx"]),
                                 params.get("rows", []))
    return {"saved": n}


def m_upsert_annotation(params: dict) -> dict:
    """书签/高亮/笔记（同书同 kind 同行更新）。"""
    ann_id = _store().upsert_annotation(
        params["book_id"], params.get("kind", "bookmark"),
        int(params.get("chapter_idx", 0)),
        int(params.get("line_start", 0)), int(params.get("line_end", 0)),
        text=params.get("text", ""), note=params.get("note", ""),
        char_start=params.get("char_start"), char_end=params.get("char_end"),
        color=params.get("color", ""))
    return {"id": ann_id}


def m_list_annotations(params: dict) -> dict:
    rows = _store().list_annotations(params["book_id"],
                                     params.get("kind"))
    return {"annotations": rows}


def m_delete_annotation(params: dict) -> dict:
    _store().delete_annotation(int(params["id"]))
    return {"deleted": int(params["id"])}


# ---------- M3：RAG 检索 + LLM 问答 ----------

def m_build_index(params: dict) -> dict:
    """params: {book_id, text, chapters:[{index,line}], force?: bool} —— 分块+嵌入+写库。

    幂等：库中已有与当前内容/分块参数一致的完整索引时直接跳过（force 可强制重建）。
    """
    book_id = params["book_id"]
    text = params["text"]
    chapters_in = params.get("chapters", [])
    # 转换为 storage 需要的 [{idx,start_line,end_line}]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ch_list = []
    for i, c in enumerate(chapters_in):
        start = int(c.get("line", 0))
        end = (int(chapters_in[i + 1]["line"]) - 1
               if i + 1 < len(chapters_in) else len(lines) - 1)
        ch_list.append({"idx": i, "title": c.get("title", ""),
                        "start_line": start, "end_line": end})
    return build_index(_store(), _embedder(), cfg.rag, book_id, text, ch_list,
                       force=bool(params.get("force", False)))


def m_index_status(params: dict) -> dict:
    """params: {book_id, text?, chapters?} —— 索引现状 + 是否需要重建。

    前端打开书时先问一次，避免每次开书都无条件重跑嵌入。
    """
    book_id = params["book_id"]
    store = _store()
    n_chunks = store.count_chunks(book_id)
    n_vec = store.count_vectors(book_id)
    sig_stored = store.get_index_sig(book_id)
    need = n_chunks == 0 or n_vec != n_chunks
    text = params.get("text")
    chapters_in = params.get("chapters")
    if text is not None and chapters_in is not None:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ch_list = []
        for i, c in enumerate(chapters_in):
            start = int(c.get("line", 0))
            end = (int(chapters_in[i + 1]["line"]) - 1
                   if i + 1 < len(chapters_in) else len(lines) - 1)
            ch_list.append({"idx": i, "start_line": start, "end_line": end})
        sig_now = index_fingerprint(text, ch_list, cfg.rag.chunk_lines)
        need = need or sig_stored != sig_now
    return {
        "book_id": book_id, "chunks": n_chunks, "vectors": n_vec,
        "vec_ready": store.vec_ready, "indexed": n_chunks > 0 and n_vec == n_chunks,
        "need_rebuild": need, "sig": sig_stored,
    }


def m_maintenance(_params: dict) -> dict:
    """清理向量表孤儿行（历史遗留；正常写入路径已不会再产生）。"""
    store = _store()
    before = store.count_all_vectors()
    removed = store.purge_orphan_vectors()
    return {"vectors_before": before, "orphans_removed": removed,
            "vectors_after": store.count_all_vectors()}


def m_search(params: dict) -> dict:
    """params: {query, book_id?} —— 语义检索。"""
    query = params.get("query", "")
    if not query:
        raise ValueError("params 需要 query")
    hits = rag_search(_store(), _embedder(), cfg.rag, query,
                      params.get("book_id"))
    return {"hits": hits}


def m_ask_ai(params: dict) -> dict:
    """RAG 问答：params: {query, book_id?, use_rag: bool}。

    返回 {answer, used:[{id,chapter_idx,line_start,line_end}]}
    """
    query = params.get("query", "")
    if not query:
        raise ValueError("params 需要 query")
    llm = get_llm(cfg.llm)
    if params.get("use_rag", True):
        hits = rag_search(_store(), _embedder(), cfg.rag, query,
                          params.get("book_id"))
        if hits:
            result = llm.ask_with_context(query, hits)
            return {"answer": result["answer"], "sources": result["used"]}
    # 无命中或未启用 RAG：直接问（无上下文）
    answer = llm.chat([
        {"role": "system",
         "content": "你是《红楼梦》文本分析助手，用中文简明回答。"},
        {"role": "user", "content": query},
    ])
    return {"answer": answer, "sources": []}


# ---------- M4：全景分析（事件 / 人物 / 伏笔 / 关系）----------

def m_import_analysis(params: dict) -> dict:
    """params: {book_id, text, chapters?} —— 把既有 V3.4 报告回灌进主库。

    幂等（整书替换）。chapters 省略时从主库读（save_book 已写过章节表）。
    """
    book_id = params["book_id"]
    text = params.get("text")
    if not text:
        raise ValueError("params 需要 text")
    store = _store()
    chapters = params.get("chapters") or store.get_chapters(book_id)
    if not chapters:
        raise ValueError("主库无章节数据，请先 save_book")
    analysis_dir = resolve_analysis_dir()
    if not analysis_dir:
        raise RuntimeError("未找到 分析结果/ 目录（可用 HONGLOU_ANALYSIS_DIR 指定）")
    stats = import_analysis(store, book_id, text, chapters, analysis_dir)
    log(f"[M4] 回灌完成 events={stats['events']} entities={stats['entities']} "
        f"mentions={stats['mentions']} foreshadows={stats['foreshadows']}")
    return stats


def m_overview(params: dict) -> dict:
    """params: {book_id} —— 全景统计（前端首屏一次拉齐）。"""
    return _store().overview(params["book_id"])


def m_list_events(params: dict) -> dict:
    """params: {book_id, chapter_from?, chapter_to?, level?, entity?, limit?}"""
    rows = _store().list_events(
        params["book_id"], params.get("chapter_from"),
        params.get("chapter_to"), params.get("level"), params.get("entity"),
        int(params.get("limit", 3000)))
    return {"events": rows}


def m_list_entities(params: dict) -> dict:
    """params: {book_id, min_appear?, limit?} —— 按出场数排序的人物榜。"""
    rows = _store().list_entities(params["book_id"],
                                  int(params.get("min_appear", 1)),
                                  int(params.get("limit", 200)))
    return {"entities": rows}


def m_get_entity(params: dict) -> dict:
    """params: {book_id, canonical} —— 角色卡：档案 + 逐章出场曲线 + 关系。"""
    store = _store()
    book_id = params["book_id"]
    ent = store.get_entity(book_id, params["canonical"])
    if not ent:
        raise ValueError(f"未收录人物: {params['canonical']}")
    mentions = store.list_mentions(book_id, None, int(ent["id"]))
    curve: Dict[int, int] = {}
    for m in mentions:
        curve[m["chapter_idx"]] = curve.get(m["chapter_idx"], 0) + 1
    return {
        "entity": ent,
        "curve": [{"chapter_idx": k, "n": v} for k, v in sorted(curve.items())],
        "first_lines": mentions[:3],
        "relations": store.list_relations(book_id, params["canonical"]),
    }


def m_list_mentions(params: dict) -> dict:
    """params: {book_id, chapter_idx?, entity_id?, limit?} —— 人物出场位置。"""
    return {"mentions": _store().list_mentions(
        params["book_id"], params.get("chapter_idx"), params.get("entity_id"),
        int(params.get("limit", 4000)))}


def m_list_foreshadows(params: dict) -> dict:
    """params: {book_id, status?} —— 伏笔清单（起锚点 ↔ 收章节）。"""
    return {"foreshadows": _store().list_foreshadows(
        params["book_id"], params.get("status"))}


def m_list_relations(params: dict) -> dict:
    """params: {book_id, entity?, limit?} —— 人物关系（报告「人物关系梳理」表）。"""
    return {"relations": _store().list_relations(
        params["book_id"], params.get("entity"),
        int(params.get("limit", 600)))}


# ---------- M4.5：全书预处理（分析前置）----------

def _chapter_ranges(chapters: list, total_lines: int) -> List[tuple]:
    """归一章节行区间 → [(章序0基, start_line, end_line)]。

    兼容两种来源：前端 parse_chapters（{index,line}）与主库（{start_line,end_line}）。
    """
    out = []
    for i, ch in enumerate(chapters):
        start = ch.get("start_line", ch.get("line", 0))
        if i + 1 < len(chapters):
            nxt = chapters[i + 1].get("start_line", chapters[i + 1].get("line", 0))
            end = int(nxt) - 1
        else:
            end = total_lines - 1
        out.append((i, int(start), int(end)))
    return out


def m_prepare_book(params: dict) -> dict:
    """全书预处理：一次算完段落级情感 + 章级汇总并落库，阅读时直接吃库。

    params: {book_id, text, chapters?, chapter_from?, chapter_to?, force?}
      · chapters 省略时从主库读（save_book 已写过章节表）
      · chapter_from / chapter_to 为 0 基闭区间，可分片调用以显示进度
      · force=True 时先清空该书情感再全量重算
    幂等：同一区间重复调用结果一致（按行/按章覆盖写）。
    """
    book_id = params["book_id"]
    text = params.get("text")
    if not text:
        raise ValueError("params 需要 text")
    store = _store()
    chapters = params.get("chapters") or store.get_chapters(book_id)
    if not chapters:
        raise ValueError("主库无章节数据，请先 save_book")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    total = len(lines)
    ranges = _chapter_ranges(chapters, total)
    lo = int(params.get("chapter_from", 0))
    hi = int(params.get("chapter_to", len(ranges) - 1))

    force = bool(params.get("force"))
    if force:
        store.clear_emotions(book_id)
    # 判据同时看段落级：章级有记录但段落为空时必须重算（否则缺口补不回）
    lines_by_chap = {} if force else store.emotion_lines_by_chapter(book_id)
    prepared = {ci for ci, n in lines_by_chap.items() if n > 0}
    todo = [(ci, st, en) for ci, st, en in ranges
            if lo <= ci <= hi and ci not in prepared]
    if not todo:
        log(f"[M4.5] 预处理跳过（第 {lo}-{hi} 章已备，不重算）")
        return {"book_id": book_id, "chapter_from": lo, "chapter_to": hi,
                "chapters": 0, "paragraphs": 0, "skipped": True,
                "elapsed_ms": 0, "coverage": store.emotion_coverage(book_id)}

    t0 = time.time()
    eng = _get_engine()

    n_paras = 0
    n_chaps = 0
    chap_rows = []
    for ci, start, end in todo:
        idx = [i for i in range(start, min(end + 1, total)) if lines[i].strip()]
        rows = _analyze_lines(lines, idx, eng)
        store.upsert_emotions(book_id, ci, [{
            "line_start": r["line"], "line_end": r["line"],
            "dutir_top": r["dutir_top"], "polarity": r["polarity"],
            "intensity": r["intensity"], "weights": r["weights"],
            "word_spans": r["word_spans"],
        } for r in rows])
        n_paras += len(rows)
        # 章级汇总（口径与 m_analyze_chapters 一致）
        counts = {e: 0 for e in EMOTION_ORDER}
        emo_total = 0
        words = 0
        pos_c = 0
        neg_c = 0
        for r in rows:
            for e in EMOTION_ORDER:
                counts[e] += r["weights"].get(e, 0)
            emo_total += r["emo_total"]
            words += r["word_count"]
            pos_c += r["pos_count"]
            neg_c += r["neg_count"]
        if emo_total == 0:
            chap_rows.append({"chapter_idx": ci, "dutir_top": None,
                              "polarity": 0.0, "intensity": 0.0,
                              "weights": counts, "word_count": words})
        else:
            chap_rows.append({
                "chapter_idx": ci,
                "dutir_top": max(EMOTION_ORDER, key=lambda e: counts[e]),
                "polarity": round((pos_c - neg_c) / emo_total, 3),
                "intensity": round(emo_total / max(words, 1), 3),
                "weights": counts, "word_count": words})
        n_chaps += 1
    store.upsert_chapter_emotions(book_id, chap_rows)
    elapsed = int((time.time() - t0) * 1000)
    log(f"[M4.5] 预处理完成 章 {lo}-{hi}：{n_chaps} 章 / {n_paras} 段 / {elapsed}ms")
    return {"book_id": book_id, "chapter_from": lo, "chapter_to": hi,
            "chapters": n_chaps, "paragraphs": n_paras, "skipped": False,
            "elapsed_ms": elapsed, "coverage": store.emotion_coverage(book_id)}


def m_prepare_status(params: dict) -> dict:
    """params: {book_id, chapters_total?} —— 开书先问一次，避免重复预处理。"""
    book_id = params["book_id"]
    cov = _store().emotion_coverage(book_id)
    total = params.get("chapters_total")
    ready = (int(cov["chapters"]) >= int(total)) if total is not None else None
    return {"book_id": book_id, "prepared_chapters": cov["chapters"],
            "prepared_lines": cov["lines"],
            "chapters_total": total, "ready": ready}


def m_list_chapter_emotions(params: dict) -> dict:
    """params: {book_id} —— 章级情感（目录着色 / 情绪曲线，读库不重算）。"""
    return {"rows": _store().list_chapter_emotions(params["book_id"])}


METHODS = {
    "ping": m_ping,
    "chapter_outline": m_chapter_outline,
    "analyze_sentiment": m_analyze_sentiment,
    "analyze_chapters": m_analyze_chapters,
    # M4.5 全书预处理（分析前置）
    "prepare_book": m_prepare_book,
    "prepare_status": m_prepare_status,
    "list_chapter_emotions": m_list_chapter_emotions,
    "db_status": m_db_status,
    "save_book": m_save_book,
    "get_book": m_get_book,
    "save_chapter_emotions": m_save_chapter_emotions,
    "upsert_emotions": m_upsert_emotions,
    "get_chapter_emotions": m_get_chapter_emotions,
    "upsert_annotation": m_upsert_annotation,
    "list_annotations": m_list_annotations,
    "delete_annotation": m_delete_annotation,
    "build_index": m_build_index,
    "index_status": m_index_status,
    "maintenance": m_maintenance,
    "search": m_search,
    "ask_ai": m_ask_ai,
    # M4 全景分析
    "import_analysis": m_import_analysis,
    "overview": m_overview,
    "list_events": m_list_events,
    "list_entities": m_list_entities,
    "get_entity": m_get_entity,
    "list_mentions": m_list_mentions,
    "list_foreshadows": m_list_foreshadows,
    "list_relations": m_list_relations,
}


def handle(req: dict) -> dict:
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}
    fn = METHODS.get(method)
    if fn is None:
        return {"id": rid, "error": {"code": -32601, "message": f"未知方法: {method}"}}
    try:
        return {"id": rid, "result": fn(params)}
    except Exception as e:  # 业务异常统一回传，不让进程退出
        return {"id": rid, "error": {"code": -32000, "message": str(e)}}


def main() -> int:
    log(f"sidecar 启动 protocol={PROTOCOL} version={SIDE_VERSION}")
    log(f"SQLite 主库: {cfg.db_path}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            resp = {"id": None, "error": {"code": -32700, "message": f"JSON 解析失败: {e}"}}
        else:
            resp = handle(req)
        sys.stdout.write(json.dumps(resp, ensure_ascii=True) + "\n")
        sys.stdout.flush()
    log("stdin 关闭，sidecar 退出")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)