# -*- coding: utf-8 -*-
"""
插件 05 · 目录跳转（核心闭环第 5 环）
================================================

【对应 VBA】D_CatalogJump.bas（InitializeCatalogJump）+ Sheet6/Sheet8 事件
【复盘定位】让读者在「目录」与「正文」之间往返：点目录定位正文、按行号反查
            当前章节、模糊搜索章节标题。

【实现逻辑拆解】
  输入    ：章节列表 chapters + 全书总行数 + 跳转目标（行号 / 标题 / 关键词）
  处理    ：
     1. 构建章节区间：每章 start=本章起始行，end=下一章起始行（末章=总行数）；
     2. 精确跳转：给定行号，二分/遍历定位其所属章节（对应 VBA Cells(行,1).Select）；
     3. 标题跳转：按标题精确相等匹配；
     4. 模糊搜索：关键词 in 标题（对应 VBA Like "*词条*"）。
  输出    ：JumpResult{ chapter, start_line, end_line }（供 GUI 定位与滚动）
  关键差异：VBA Cells.Select → 纯逻辑返回行号区间，GUI 层用 QTextCursor(block)
            + ensureCursorVisible() 消费；Range.Find → 内存 in / re.search。

【纯逻辑说明】无 GUI，只做「行号 → 章节」的定位计算，可独立单测。

【可独立运行】
  python plugin_05_catalog_jump.py    # 复用内置章节数据演示精确跳转/标题跳转/模糊搜索
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from plugin_03_chapter_detect import Chapter, detect_chapters, fill_catalog


@dataclass
class JumpResult:
    chapter: str
    start_line: int     # 章节起始行（0-based，含）
    end_line: int       # 章节结束行（0-based，不含）


def build_ranges(chapters: list[Chapter], total_lines: int) -> list[JumpResult]:
    """把章节列表换算为 [start, end) 行号区间（末章到全书末尾）。"""
    chapters = sorted(chapters, key=lambda c: c.line_index)
    results: list[JumpResult] = []
    for i, c in enumerate(chapters):
        end = chapters[i + 1].line_index if i + 1 < len(chapters) else total_lines
        results.append(JumpResult(c.title, c.line_index, end))
    return results


def jump_to_line(chapters: list[Chapter], total_lines: int, line_index: int) -> JumpResult | None:
    """按行号精确跳转（对应 VBA Cells(行号, 1).Select），返回所属章节区间。"""
    ranges = build_ranges(chapters, total_lines)
    for r in ranges:
        if r.start_line <= line_index < r.end_line:
            return r
    return None


def jump_to_title(chapters: list[Chapter], title: str) -> Chapter | None:
    """按标题精确跳转。"""
    for c in chapters:
        if c.title == title:
            return c
    return None


def search_chapters(chapters: list[Chapter], keyword: str) -> list[Chapter]:
    """标题模糊搜索（对应 VBA Like "*词条*" → Python `keyword in title`）。"""
    return [c for c in chapters if keyword in c.title]


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
_DEMO = [
    "第一回 甄士隐梦幻识通灵",
    "此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。",
    "列位看官，你道此书从何而来？",
    "第二回 贾夫人仙逝扬州城",
    "原来这贾夫人，乃荣国府贾政之妻王氏。",
    "第三回 托内兄如海荐西宾",
    "却说林如海姓林名海，表字如海。",
]


def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    lines = _DEMO
    chapters = detect_chapters(lines)
    total = len(lines)

    print("[目录跳转] 章节区间总览：")
    for r in build_ranges(chapters, total):
        print(f"    {r.chapter:<20} 行 [{r.start_line}, {r.end_line})")

    print("\n[目录跳转] 精确跳转到第 4 行（0-based）：")
    r = jump_to_line(chapters, total, 4)
    print(f"    -> {r.chapter}  行区间 [{r.start_line}, {r.end_line})")

    print("\n[目录跳转] 按标题精确跳转「第三回 托内兄如海荐西宾」：")
    c = jump_to_title(chapters, "第三回 托内兄如海荐西宾")
    print(f"    -> 命中，起始行 {c.line_index}" if c else "    -> 未命中")

    print("\n[目录跳转] 模糊搜索「贾」：")
    for c in search_chapters(chapters, "贾"):
        print(f"    {c.display}")

    print("\n[目录跳转] 目录补全（复用 plugin_03 的输出）：")
    catalog = fill_catalog(lines, chapters)
    for i, ln in enumerate(lines):
        print(f"    行{i} -> {catalog[i]}")


if __name__ == "__main__":
    _demo()