#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite 主库（M3 地基）—— 按 V1.0 设计方案 §6 数据模型建表。

表：books / chapters / annotations / emotions / events / entities /
     entity_mentions / foreshadows / chunks / chunk_vec(VSS, 需 sqlite-vec)

设计约束（与方案一致）：
  - 一切位置 = (chapter_idx, line_start/end)，物理行号唯一权威；
  - 增量重析失效键 = (book_id, chapter_idx)；
  - sqlite-vec 不可用时降级：主库照常，仅向量检索不可用（vec_ready=False）。
"""

import json
import sqlite3
import sys
from typing import Any, Dict, List, Optional

# ───────────────────────────── DDL ─────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
  book_id      TEXT PRIMARY KEY,        -- 内容哈希（只含正文，不含路径）
  title        TEXT, source_path TEXT,
  total_chars  INTEGER, created_at INTEGER,
  index_sig    TEXT                     -- 向量索引签名（幂等重建判据）
);
CREATE TABLE IF NOT EXISTS chapters (
  book_id TEXT, idx INTEGER,            -- 0-based
  title TEXT, start_line INTEGER, end_line INTEGER,
  PRIMARY KEY (book_id, idx)
);
CREATE TABLE IF NOT EXISTS annotations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT, kind TEXT,              -- bookmark | highlight | note
  chapter_idx INTEGER,
  line_start INTEGER, line_end INTEGER,
  char_start INTEGER, char_end INTEGER, -- 可空（整行）
  text TEXT, note TEXT, color TEXT,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS emotions (
  book_id TEXT, chapter_idx INTEGER,
  line_start INTEGER, line_end INTEGER,
  dutir_top TEXT, polarity REAL, intensity REAL,
  weights_json TEXT,
  PRIMARY KEY (book_id, chapter_idx, line_start, line_end)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT, level TEXT,             -- 主线 | 支线 | 细节
  chapter_idx INTEGER, line_start INTEGER, line_end INTEGER,
  summary TEXT, w5h1_json TEXT, participants_json TEXT,
  -- M4：回灌报告时补的溯源列
  event_uid TEXT,                       -- 报告里的事件ID（如 E01-07）
  tone TEXT,                            -- 情感倾向
  anchor_precision TEXT,                -- quote | cooccur | para | chapter
  char_start INTEGER, char_end INTEGER, -- 引文精确锚点（可空）
  para_raw TEXT                         -- 报告原始「段落索引」表述
);
CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT, canonical TEXT, aliases_json TEXT,
  first_chapter INTEGER, appear_count INTEGER,
  profile_md TEXT, portrait_path TEXT
);
CREATE TABLE IF NOT EXISTS entity_mentions (
  entity_id INTEGER, book_id TEXT,
  chapter_idx INTEGER, line_start INTEGER,
  char_start INTEGER, char_end INTEGER, surface TEXT
);
CREATE TABLE IF NOT EXISTS foreshadows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT,
  setup_chapter INTEGER, setup_line INTEGER,
  payoff_chapter INTEGER, payoff_line INTEGER,
  note TEXT, status TEXT,               -- open | closed
  -- M4：回灌报告时补的溯源列
  content TEXT,                         -- 线索内容
  kind TEXT,                            -- 伏笔 | 暗线 | 主题伏笔 | 情节铺垫
  anchor_precision TEXT,
  setup_char_start INTEGER, setup_char_end INTEGER,
  payoff_raw TEXT                       -- 原文表述（如「预计回收：第3-98章」）
);
CREATE TABLE IF NOT EXISTS entity_relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT, chapter_idx INTEGER,
  entity_a TEXT, entity_b TEXT,
  relation TEXT,                        -- 夫妻 | 父女 | 主仆 | …
  evidence TEXT                         -- 本章互动描述
);
CREATE TABLE IF NOT EXISTS chapter_emotions (
  book_id TEXT, chapter_idx INTEGER,
  dutir_top TEXT, polarity REAL, intensity REAL,
  weights_json TEXT, word_count INTEGER,
  PRIMARY KEY (book_id, chapter_idx)
);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT, chapter_idx INTEGER,
  line_start INTEGER, line_end INTEGER,
  text TEXT
);
"""

VEC_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(
  chunk_id INTEGER PRIMARY KEY, embedding FLOAT[512]
);
"""


class BookStore:
    """单连接 SQLite 门面。sidecar 是单线程事件循环，无需多线程连接池。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.vec_ready: bool = False

    # ── 连接 / 初始化 ──────────────────────────────────────────

    def connect(self) -> "BookStore":
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._try_load_vec()
        self.init_schema()
        return self

    def _try_load_vec(self) -> None:
        """加载 sqlite-vec 扩展（失败不阻塞主库）。"""
        try:
            import sqlite_vec  # type: ignore
            assert self._conn is not None
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._conn.execute(VEC_TABLE_SQL)
            self.vec_ready = True
        except Exception as e:  # noqa: BLE001
            print(f"[storage] sqlite-vec 不可用（向量检索降级）: {e}",
                  file=sys.stderr, flush=True)
            self.vec_ready = False

    def init_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript(SCHEMA_SQL)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """老库补列（幂等）。CREATE TABLE IF NOT EXISTS 不会改已存在的表结构，
        所以新增列必须单独检测后 ALTER，否则老库启动即报 no such column。"""
        assert self._conn is not None
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(books)")}
        if "index_sig" not in cols:
            self._conn.execute("ALTER TABLE books ADD COLUMN index_sig TEXT")
        ecols = {r[1] for r in self._conn.execute("PRAGMA table_info(emotions)")}
        if "spans_json" not in ecols:
            self._conn.execute("ALTER TABLE emotions ADD COLUMN spans_json TEXT")
        # M4：events / foreshadows 的溯源列（老库补齐，新库由 DDL 建好）
        for table, col, decl in (
            ("events", "event_uid", "TEXT"),
            ("events", "tone", "TEXT"),
            ("events", "anchor_precision", "TEXT"),
            ("events", "char_start", "INTEGER"),
            ("events", "char_end", "INTEGER"),
            ("events", "para_raw", "TEXT"),
            ("foreshadows", "content", "TEXT"),
            ("foreshadows", "kind", "TEXT"),
            ("foreshadows", "anchor_precision", "TEXT"),
            ("foreshadows", "setup_char_start", "INTEGER"),
            ("foreshadows", "setup_char_end", "INTEGER"),
            ("foreshadows", "payoff_raw", "TEXT"),
        ):
            cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        assert self._conn is not None, "BookStore 未 connect"
        return self._conn

    # ── books / chapters ────────────────────────────────────────

    def upsert_book(self, book_id: str, title: str, source_path: str,
                    total_chars: int) -> None:
        self.conn.execute(
            "INSERT INTO books(book_id,title,source_path,total_chars,created_at) "
            "VALUES(?,?,?,?,?) "
            "ON CONFLICT(book_id) DO UPDATE SET "
            "title=excluded.title, source_path=excluded.source_path, "
            "total_chars=excluded.total_chars",
            (book_id, title, source_path, total_chars,
             int(__import__("time").time())),
        )
        self.conn.commit()

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM books WHERE book_id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def replace_chapters(self, book_id: str,
                         chapters: List[Dict[str, Any]]) -> None:
        """整书替换章节表（增量失效键 = book_id）。"""
        self.conn.execute("DELETE FROM chapters WHERE book_id=?", (book_id,))
        self.conn.executemany(
            "INSERT INTO chapters(book_id, idx, title, start_line, end_line) "
            "VALUES(?,?,?,?,?)",
            [(book_id, c["idx"], c["title"], c["start_line"], c["end_line"])
             for c in chapters],
        )
        self.conn.commit()

    def get_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM chapters WHERE book_id=? ORDER BY idx", (book_id,))
        return [dict(r) for r in rows]

    # ── emotions（段落级，驱动着色）──────────────────────────

    @staticmethod
    def _emo_row(book_id: str, chapter_idx: int,
                 r: Dict[str, Any]) -> tuple:
        """把一行情感结果整理成 INSERT 参数（含字级词位置）。"""
        return (
            book_id, chapter_idx, r["line_start"],
            r.get("line_end", r["line_start"]),
            r.get("dutir_top"), r.get("polarity", 0.0),
            r.get("intensity", 0.0),
            json.dumps(r.get("weights", {}), ensure_ascii=False),
            json.dumps(r.get("word_spans", []), ensure_ascii=False),
        )

    def replace_chapter_emotions(self, book_id: str, chapter_idx: int,
                                 rows: List[Dict[str, Any]]) -> None:
        """整章替换（增量重析失效键 = (book_id, chapter_idx)）。"""
        self.conn.execute(
            "DELETE FROM emotions WHERE book_id=? AND chapter_idx=?",
            (book_id, chapter_idx))
        self.conn.executemany(
            "INSERT INTO emotions(book_id, chapter_idx, line_start, line_end, "
            "dutir_top, polarity, intensity, weights_json, spans_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            [self._emo_row(book_id, chapter_idx, r) for r in rows],
        )
        self.conn.commit()

    def upsert_emotions(self, book_id: str, chapter_idx: int,
                        rows: List[Dict[str, Any]]) -> int:
        """按行增量写情感（幂等：同行覆盖）。

        与 replace_chapter_emotions 的区别：那个是整章替换，只适合「一次性
        算完整章」的场景；前端是视口驱动、分批算的，若用整章替换，后到的
        批次会把先前批次的成果冲掉。故增量场景一律走本方法。
        """
        if not rows:
            return 0
        self.conn.executemany(
            "INSERT OR REPLACE INTO emotions(book_id, chapter_idx, line_start, "
            "line_end, dutir_top, polarity, intensity, weights_json, "
            "spans_json) VALUES(?,?,?,?,?,?,?,?,?)",
            [self._emo_row(book_id, chapter_idx, r) for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def get_chapter_emotions(self, book_id: str,
                             chapter_idx: int) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM emotions WHERE book_id=? AND chapter_idx=? "
            "ORDER BY line_start", (book_id, chapter_idx))
        out = []
        for r in rows:
            d = dict(r)
            for key, col, default in (("weights", "weights_json", {}),
                                      ("word_spans", "spans_json", [])):
                raw = d.pop(col, None)
                try:
                    d[key] = json.loads(raw) if raw else default
                except (TypeError, ValueError):
                    d[key] = default
            out.append(d)
        return out

    # ── annotations（书签/高亮/笔记，锚定物理行）──────────────

    # ── chapter_emotions（章级情感汇总：目录着色 / 情绪曲线）────

    def upsert_chapter_emotions(self, book_id: str,
                                rows: List[Dict[str, Any]]) -> int:
        """章级情感汇总（幂等：同章覆盖）。rows 每项需含 chapter_idx。"""
        if not rows:
            return 0
        self.conn.executemany(
            "INSERT OR REPLACE INTO chapter_emotions(book_id, chapter_idx, "
            "dutir_top, polarity, intensity, weights_json, word_count) "
            "VALUES(?,?,?,?,?,?,?)",
            [(book_id, int(r["chapter_idx"]), r.get("dutir_top"),
              float(r.get("polarity") or 0.0),
              float(r.get("intensity") or 0.0),
              json.dumps(r.get("weights") or {}, ensure_ascii=False),
              int(r.get("word_count") or 0)) for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def list_chapter_emotions(self, book_id: str) -> List[Dict[str, Any]]:
        """按章序返回章级情感（前端目录着色与情绪曲线直接消费）。"""
        rows = self.conn.execute(
            "SELECT * FROM chapter_emotions WHERE book_id=? ORDER BY chapter_idx",
            (book_id,))
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            raw = d.pop("weights_json", None)
            try:
                d["weights"] = json.loads(raw) if raw else {}
            except (TypeError, ValueError):
                d["weights"] = {}
            out.append(d)
        return out

    def emotion_coverage(self, book_id: str) -> Dict[str, int]:
        """已备段落数与已备章数 —— 全书预处理（prepare_book）的幂等判据。"""
        lines = self.conn.execute(
            "SELECT COUNT(*) FROM emotions WHERE book_id=?",
            (book_id,)).fetchone()[0]
        chapters = self.conn.execute(
            "SELECT COUNT(*) FROM chapter_emotions WHERE book_id=?",
            (book_id,)).fetchone()[0]
        return {"lines": int(lines), "chapters": int(chapters)}

    def emotion_lines_by_chapter(self, book_id: str) -> Dict[int, int]:
        """各章已备段落行数。

        判据要同时看段落级：章级表有记录、但段落被清空（例如整章替换测试）
        时，必须重算那一章，否则缺口永远补不回来。
        """
        rows = self.conn.execute(
            "SELECT chapter_idx, COUNT(*) AS n FROM emotions WHERE book_id=? "
            "GROUP BY chapter_idx", (book_id,))
        return {int(r["chapter_idx"]): int(r["n"]) for r in rows}

    def clear_emotions(self, book_id: str) -> int:
        """清空某书全部情感（段落级 + 章级）。仅供 force 重算使用。"""
        n1 = self.conn.execute(
            "DELETE FROM emotions WHERE book_id=?", (book_id,)).rowcount
        n2 = self.conn.execute(
            "DELETE FROM chapter_emotions WHERE book_id=?", (book_id,)).rowcount
        self.conn.commit()
        return int(n1) + int(n2)

    def upsert_annotation(self, book_id: str, kind: str, chapter_idx: int,
                          line_start: int, line_end: int,
                          text: str = "", note: str = "",
                          char_start: Optional[int] = None,
                          char_end: Optional[int] = None,
                          color: str = "") -> int:
        """同书同行同 kind 更新，否则插入。返回行 id。"""
        cur = self.conn.execute(
            "SELECT id FROM annotations WHERE book_id=? AND kind=? "
            "AND line_start=? AND line_end=?",
            (book_id, kind, line_start, line_end))
        row = cur.fetchone()
        created = int(__import__("time").time())
        if row:
            self.conn.execute(
                "UPDATE annotations SET text=?, note=?, char_start=?, "
                "char_end=?, color=? WHERE id=?",
                (text, note, char_start, char_end, color, row["id"]))
            self.conn.commit()
            return int(row["id"])
        self.conn.execute(
            "INSERT INTO annotations(book_id, kind, chapter_idx, line_start, "
            "line_end, char_start, char_end, text, note, color, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, kind, chapter_idx, line_start, line_end, char_start,
             char_end, text, note, color, created))
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    def delete_annotation(self, ann_id: int) -> None:
        self.conn.execute("DELETE FROM annotations WHERE id=?", (ann_id,))
        self.conn.commit()

    def list_annotations(self, book_id: str,
                         kind: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM annotations WHERE book_id=?"
        args: List[Any] = [book_id]
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        sql += " ORDER BY line_start"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ── chunks + 向量检索（RAG）───────────────────────────────

    def add_chunks(self, book_id: str,
                   chunks: List[Dict[str, Any]]) -> List[int]:
        """插入分块，返回 chunk_id 列表（与 chunks 一一对应，供向量关联）。

        重建索引前**必须**先清掉本书记忆体里对应的旧向量行：chunks 是
        AUTOINCREMENT，重新插入会拿到全新的 id，旧向量行不会自动消失，
        会变成指向已删除 chunk 的孤儿。KNN 会照常命中这些孤儿，
        但随后的 JOIN chunks 会把它们剔除 —— 于是 topK 名义 6 条、
        实际返回 3~4 条，且随重建次数递增而递减（实测库中曾累积 456 行孤儿）。
        """
        self._purge_vectors_of(book_id)
        self.conn.execute("DELETE FROM chunks WHERE book_id=?", (book_id,))
        ids: List[int] = []
        for c in chunks:
            cur = self.conn.execute(
                "INSERT INTO chunks(book_id, chapter_idx, line_start, "
                "line_end, text) VALUES(?,?,?,?,?)",
                (book_id, c["chapter_idx"], c["line_start"], c["line_end"],
                 c["text"]))
            ids.append(int(cur.lastrowid))
        self.conn.commit()
        return ids

    def _purge_vectors_of(self, book_id: str) -> int:
        """删除某书全部分块的向量行（含已成孤儿的）。返回删除行数。"""
        if not self.vec_ready:
            return 0
        rows = self.conn.execute(
            "SELECT id FROM chunks WHERE book_id=?", (book_id,)).fetchall()
        ids = [int(r[0]) for r in rows]
        if not ids:
            return 0
        removed = 0
        for i in range(0, len(ids), 400):  # 分段，避开 SQLite 变量上限
            part = ids[i:i + 400]
            ph = ",".join("?" * len(part))
            cur = self.conn.execute(
                f"DELETE FROM chunk_vec WHERE chunk_id IN ({ph})", part)
            removed += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        self.conn.commit()
        return removed

    def purge_orphan_vectors(self) -> int:
        """清理所有指向已不存在分块的向量行。返回清理行数。"""
        if not self.vec_ready:
            return 0
        rows = self.conn.execute(
            "SELECT v.chunk_id FROM chunk_vec v "
            "LEFT JOIN chunks c ON c.id = v.chunk_id WHERE c.id IS NULL"
        ).fetchall()
        ids = [int(r[0]) for r in rows]
        if not ids:
            return 0
        for i in range(0, len(ids), 400):
            part = ids[i:i + 400]
            ph = ",".join("?" * len(part))
            self.conn.execute(
                f"DELETE FROM chunk_vec WHERE chunk_id IN ({ph})", part)
        self.conn.commit()
        return len(ids)

    def count_chunks(self, book_id: str) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE book_id=?",
            (book_id,)).fetchone()[0])

    def get_index_sig(self, book_id: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT index_sig FROM books WHERE book_id=?", (book_id,)).fetchone()
        return row[0] if row else None

    def set_index_sig(self, book_id: str, sig: str) -> None:
        self.conn.execute("UPDATE books SET index_sig=? WHERE book_id=?",
                          (sig, book_id))
        self.conn.commit()

    def count_vectors(self, book_id: str) -> int:
        """某书**有效**向量数（JOIN 后的，不含孤儿）。"""
        if not self.vec_ready:
            return 0
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM chunk_vec v JOIN chunks c ON c.id = v.chunk_id "
            "WHERE c.book_id=?", (book_id,)).fetchone()[0])

    def count_all_vectors(self) -> int:
        if not self.vec_ready:
            return 0
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM chunk_vec").fetchone()[0])

    def store_embeddings(self, chunk_ids: List[int],
                         embeddings: List[List[float]]) -> int:
        """写入 chunk_vec（sqlite-vec）。返回写入条数。

        用裸 INSERT 而非 INSERT OR REPLACE：vec0 虚拟表**不支持** OR REPLACE
        （实测报 `UNIQUE constraint failed on v primary key`），写了也会在
        主键冲突时抛异常。此处依赖调用前已清理旧行，冲突即代表逻辑出错，
        应当直接暴露而不是被 OR REPLACE 掩盖。
        """
        if not self.vec_ready or not embeddings:
            return 0
        payload = []
        for cid, emb in zip(chunk_ids, embeddings):
            emb_json = json.dumps([float(x) for x in emb])
            payload.append((cid, emb_json))
        self.conn.executemany(
            "INSERT INTO chunk_vec(chunk_id, embedding) VALUES(?,?)", payload)
        self.conn.commit()
        return len(payload)

    def search_chunks(self, embedding: List[float], top_k: int = 6,
                      book_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """语义检索：返回 [{id, chapter_idx, line_start, line_end, text, distance}]。"""
        if not self.vec_ready:
            return []
        emb_json = json.dumps([float(x) for x in embedding])
        sql = (
            "SELECT c.id, c.chapter_idx, c.line_start, c.line_end, c.text, "
            "v.distance FROM chunk_vec v "
            "JOIN chunks c ON c.id = v.chunk_id "
            "WHERE v.embedding MATCH ? AND v.k = ? "
        )
        args: List[Any] = [emb_json, int(top_k)]
        if book_id:
            sql += "AND c.book_id = ? "
            args.append(book_id)
        rows = self.conn.execute(sql, args)
        return [dict(r) for r in rows]


    # ── M4：事件 / 人物 / 伏笔 / 关系（全景分析）────────────────

    def list_events(self, book_id: str, chapter_from: Optional[int] = None,
                    chapter_to: Optional[int] = None,
                    level: Optional[str] = None,
                    entity: Optional[str] = None,
                    limit: int = 3000) -> List[Dict[str, Any]]:
        """按章区间/级别/人物筛事件。entity 为规范名（参与人物里包含即命中）。"""
        sql = ("SELECT id, event_uid, level, chapter_idx, line_start, line_end, "
               "summary, tone, anchor_precision, participants_json, para_raw, "
               "char_start, char_end FROM events WHERE book_id=?")
        args: List[Any] = [book_id]
        if chapter_from is not None:
            sql += " AND chapter_idx >= ?"
            args.append(int(chapter_from))
        if chapter_to is not None:
            sql += " AND chapter_idx <= ?"
            args.append(int(chapter_to))
        if level:
            sql += " AND level = ?"
            args.append(level)
        if entity:
            sql += " AND participants_json LIKE ?"
            args.append(f'%"{entity}"%')
        sql += " ORDER BY chapter_idx, line_start, id LIMIT ?"
        args.append(int(limit))
        out = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            try:
                d["participants"] = json.loads(d.pop("participants_json") or "[]")
            except (TypeError, ValueError):
                d["participants"] = []
            out.append(d)
        return out

    def count_events(self, book_id: str) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE book_id=?",
            (book_id,)).fetchone()[0])

    def events_per_chapter(self, book_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT chapter_idx, COUNT(*) AS n, "
            "MAX(line_start) AS last_line FROM events WHERE book_id=? "
            "GROUP BY chapter_idx ORDER BY chapter_idx", (book_id,))
        return [dict(r) for r in rows]

    def list_entities(self, book_id: str, min_appear: int = 1,
                      limit: int = 400) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, canonical, aliases_json, first_chapter, appear_count "
            "FROM entities WHERE book_id=? AND appear_count >= ? "
            "ORDER BY appear_count DESC, canonical LIMIT ?",
            (book_id, int(min_appear), int(limit)))
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["aliases"] = json.loads(d.pop("aliases_json") or "[]")
            except (TypeError, ValueError):
                d["aliases"] = []
            out.append(d)
        return out

    def get_entity(self, book_id: str,
                   canonical: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM entities WHERE book_id=? AND canonical=?",
            (book_id, canonical)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["aliases"] = json.loads(d.pop("aliases_json") or "[]")
        except (TypeError, ValueError):
            d["aliases"] = []
        return d

    def list_mentions(self, book_id: str, chapter_idx: Optional[int] = None,
                      entity_id: Optional[int] = None,
                      limit: int = 4000) -> List[Dict[str, Any]]:
        """人物出场位置（供正文高亮与出场曲线）。"""
        sql = ("SELECT m.entity_id, e.canonical, m.chapter_idx, m.line_start, "
               "m.char_start, m.char_end, m.surface FROM entity_mentions m "
               "JOIN entities e ON e.id = m.entity_id WHERE m.book_id=?")
        args: List[Any] = [book_id]
        if chapter_idx is not None:
            sql += " AND m.chapter_idx = ?"
            args.append(int(chapter_idx))
        if entity_id is not None:
            sql += " AND m.entity_id = ?"
            args.append(int(entity_id))
        sql += " ORDER BY m.chapter_idx, m.line_start, m.char_start LIMIT ?"
        args.append(int(limit))
        return [dict(r) for r in self.conn.execute(sql, args)]

    def entity_chapter_curve(self, book_id: str, limit: int = 40
                             ) -> List[Dict[str, Any]]:
        """出场 Top 人物的逐章出场数（用于出场曲线）。"""
        rows = self.conn.execute(
            "SELECT e.canonical, m.chapter_idx, COUNT(*) AS n "
            "FROM entity_mentions m JOIN entities e ON e.id = m.entity_id "
            "WHERE m.book_id=? AND e.id IN ("
            "  SELECT id FROM entities WHERE book_id=? "
            "  ORDER BY appear_count DESC LIMIT ?"
            ") GROUP BY e.canonical, m.chapter_idx "
            "ORDER BY e.canonical, m.chapter_idx",
            (book_id, book_id, int(limit)))
        return [dict(r) for r in rows]

    def list_foreshadows(self, book_id: str,
                         status: Optional[str] = None
                         ) -> List[Dict[str, Any]]:
        sql = ("SELECT id, setup_chapter, setup_line, payoff_chapter, "
               "payoff_line, content, kind, status, anchor_precision, payoff_raw "
               "FROM foreshadows WHERE book_id=?")
        args: List[Any] = [book_id]
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY setup_chapter, setup_line, id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def list_relations(self, book_id: str, entity: Optional[str] = None,
                       limit: int = 600) -> List[Dict[str, Any]]:
        sql = ("SELECT id, chapter_idx, entity_a, entity_b, relation, evidence "
               "FROM entity_relations WHERE book_id=?")
        args: List[Any] = [book_id]
        if entity:
            sql += " AND (entity_a = ? OR entity_b = ?)"
            args.extend([entity, entity])
        sql += " ORDER BY chapter_idx, id LIMIT ?"
        args.append(int(limit))
        return [dict(r) for r in self.conn.execute(sql, args)]

    def maintenance_mark_payoff(self, book_id: str) -> int:
        """把「已收回」的伏笔两锚点都补上 payoff_line（同章内按内容找行）。"""
        n = 0
        rows = self.conn.execute(
            "SELECT id, setup_chapter FROM foreshadows "
            "WHERE book_id=? AND payoff_chapter IS NOT NULL "
            "AND payoff_line IS NULL", (book_id,)).fetchall()
        for r in rows:
            first = self.conn.execute(
                "SELECT MIN(line_start) FROM events WHERE book_id=? "
                "AND chapter_idx=?", (book_id, r["setup_chapter"])).fetchone()
            if first and first[0] is not None:
                self.conn.execute(
                    "UPDATE foreshadows SET payoff_line=? WHERE id=?",
                    (first[0], r["id"]))
                n += 1
        if n:
            self.conn.commit()
        return n

    def overview(self, book_id: str) -> Dict[str, Any]:
        """全景统计（前端首屏一次拉齐）。"""
        def one(sql: str, *a):
            row = self.conn.execute(sql, a).fetchone()
            return row[0] if row else 0

        by_level = {r["level"]: r["n"] for r in self.conn.execute(
            "SELECT level, COUNT(*) AS n FROM events WHERE book_id=? "
            "GROUP BY level ORDER BY n DESC", (book_id,))}
        prec = {r["anchor_precision"]: r["n"] for r in self.conn.execute(
            "SELECT anchor_precision, COUNT(*) AS n FROM events "
            "WHERE book_id=? GROUP BY anchor_precision", (book_id,))}
        tones = {r["tone"]: r["n"] for r in self.conn.execute(
            "SELECT tone, COUNT(*) AS n FROM events WHERE book_id=? "
            "GROUP BY tone ORDER BY n DESC", (book_id,))}
        return {
            "events": one("SELECT COUNT(*) FROM events WHERE book_id=?", book_id),
            "entities": one("SELECT COUNT(*) FROM entities WHERE book_id=?",
                            book_id),
            "mentions": one("SELECT COUNT(*) FROM entity_mentions WHERE book_id=?",
                            book_id),
            "foreshadows": one("SELECT COUNT(*) FROM foreshadows WHERE book_id=?",
                               book_id),
            "foreshadows_open": one(
                "SELECT COUNT(*) FROM foreshadows WHERE book_id=? AND status='open'",
                book_id),
            "relations": one("SELECT COUNT(*) FROM entity_relations WHERE book_id=?",
                             book_id),
            "chapters_with_events": one(
                "SELECT COUNT(DISTINCT chapter_idx) FROM events WHERE book_id=?",
                book_id),
            "events_by_level": by_level,
            "events_by_tone": tones,
            "anchor_precision": prec,
            "top_entities": self.list_entities(book_id, 1, 15),
        }

# 模块级单例（sidecar 进程内复用）
_store: Optional[BookStore] = None


def get_store(db_path: str) -> BookStore:
    global _store
    if _store is None:
        _store = BookStore(db_path).connect()
    return _store


def reset_store() -> None:
    """测试/重载用：关闭并清空单例。"""
    global _store
    if _store is not None:
        _store.close()
        _store = None