# -*- coding: utf-8 -*-
"""
插件 06 · 书签进度（核心闭环第 6 环）
================================================

【对应 VBA】无直接对应（VBA 用隐藏工作表记录进度）；ColorTxt 用 SQLite + 落盘。
【复盘定位】核心闭环的收口：让「读到哪、标了哪」能毫厘不差地回来。复盘反复
            强调的「假完成」教训在此落地为「诚信计数」——存的是真实行号，
            列表返回真实数量，不做虚标。

【实现逻辑拆解】
  输入    ：书号 book_id + 操作（加书签 / 列书签 / 删书签 / 存进度 / 读进度）
  处理    ：
     1. sqlite3（Python 标准库，零配置）建两张表：bookmarks、progress；
     2. 书签：增删查，带章节标题、正文行号、笔记、时间戳；
     3. 进度：以 book_id 为主键 upsert（INSERT ... ON CONFLICT REPLACE），
        存真实章节与行号，读回即恢复到上次位置。
  输出    ：Bookmark 列表 / Progress 记录
  关键差异：隐藏工作表 → sqlite3（崩溃安全、事务原子写，呼应复盘 R8）；
            全局变量 → 数据库持久化，重启不丢。

【纯逻辑说明】无 GUI，纯存储层；默认库文件可自定义，测试可用 ":memory:"。

【可独立运行】
  python plugin_06_bookmark_progress.py    # 内置内存库完整演示增删查 + 进度恢复
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass


_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id       TEXT    NOT NULL,
    chapter_title TEXT,
    line_index    INTEGER NOT NULL,
    note          TEXT,
    created_at    TEXT    DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS progress (
    book_id       TEXT PRIMARY KEY,
    chapter_title TEXT,
    line_index    INTEGER NOT NULL,
    updated_at    TEXT DEFAULT (datetime('now','localtime'))
);
"""


@dataclass
class Bookmark:
    id: int
    book_id: str
    chapter_title: str
    line_index: int
    note: str = ""
    created_at: str = ""


@dataclass
class Progress:
    book_id: str
    chapter_title: str
    line_index: int
    updated_at: str = ""


class BookmarkStore:
    """书签 + 阅读进度的 SQLite 存储（零三方依赖）。"""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ---- 书签 ----
    def add_bookmark(self, book_id: str, chapter_title: str,
                     line_index: int, note: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO bookmarks(book_id, chapter_title, line_index, note) "
            "VALUES (?,?,?,?)",
            (book_id, chapter_title, line_index, note),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        rows = self._conn.execute(
            "SELECT * FROM bookmarks WHERE book_id=? ORDER BY line_index",
            (book_id,),
        ).fetchall()
        return [Bookmark(**dict(r)) for r in rows]

    def remove_bookmark(self, bookmark_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def count_bookmarks(self, book_id: str) -> int:
        """诚信计数：返回真实条数，不做虚标（呼应复盘 R8）。"""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM bookmarks WHERE book_id=?", (book_id,)
        ).fetchone()
        return row["n"]

    # ---- 进度 ----
    def save_progress(self, book_id: str, chapter_title: str, line_index: int) -> None:
        """upsert 进度：同一本书只保留最新位置，存真实行号。"""
        self._conn.execute(
            "INSERT INTO progress(book_id, chapter_title, line_index, updated_at) "
            "VALUES (?,?,?,datetime('now','localtime')) "
            "ON CONFLICT(book_id) DO UPDATE SET "
            "chapter_title=excluded.chapter_title, line_index=excluded.line_index, "
            "updated_at=excluded.updated_at",
            (book_id, chapter_title, line_index),
        )
        self._conn.commit()

    def load_progress(self, book_id: str) -> Progress | None:
        row = self._conn.execute(
            "SELECT * FROM progress WHERE book_id=?", (book_id,)
        ).fetchone()
        return Progress(**dict(row)) if row else None


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    store = BookmarkStore(":memory:")

    bid = "hongloumeng-001"
    b1 = store.add_bookmark(bid, "第一回 甄士隐梦幻识通灵", 12, "主角出场")
    b2 = store.add_bookmark(bid, "第三回 托内兄如海荐西宾", 88, "贾府初见")

    print("[书签进度] 添加书签 id:", b1, b2)
    print("[书签进度] 诚信计数：当前书签数 =", store.count_bookmarks(bid))
    for b in store.list_bookmarks(bid):
        print(f"    #{b.id} [{b.chapter_title}] 行 {b.line_index}  {b.note}")

    store.save_progress(bid, "第三回 托内兄如海荐西宾", 90)
    p = store.load_progress(bid)
    print(f"\n[书签进度] 保存进度后读回：{p.chapter_title} @ 行 {p.line_index} (更新于 {p.updated_at})")

    store.remove_bookmark(b1)
    print(f"\n[书签进度] 删除书签 #{b1} 后，剩余 = {store.count_bookmarks(bid)}")

    store.close()


if __name__ == "__main__":
    _demo()