# -*- coding: utf-8 -*-
"""
插件 03 · 章节识别（核心闭环第 3 环）
================================================

【对应 VBA】READ_正则查询替换目录.bas（正则查询优化 C5 / 正则后辅助目录优化 C6）
【复盘定位】把连续文本切成「章节」，目录跳转、书签进度、按章上色都依赖它。

【实现逻辑拆解】
  输入    ：文本行列表 lines + 正则 pattern 列表（默认带小说/网文通用规则）
  处理    ：
     1. 多正则合并为「或」模式（对应 VBA 的 C2 单元格多正则合并）；
     2. 逐行 match，命中即得 {行号: 章节名}，兼识别 Markdown ATX 标题层级；
     3. 目录补全（向下填充）：遍历时维护 last_valid，非空→更新，
        空→沿用上一次有效章节——与 VBA「lastValidDir」逻辑完全一致。
  输出    ：Chapter{ title, line_index, level } 列表 + 补全后的目录列 catalog
  关键差异：VBScript.RegExp → Python re（语法几乎一致）；
            Scripting.Dictionary → dict；向下填充算法逐字迁移。

【纯逻辑说明】无 GUI，只产出「章节」这个纯数据结构，供目录跳转/书签消费。

【可独立运行】
  python plugin_03_chapter_detect.py    # 用内置红楼梦样章演示检测 + 补全
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass


# 默认章节规则（网文/小说通用），可按需传入覆盖
DEFAULT_PATTERNS = [
    r"^\s*第[零一二三四五六七八九十百千万两0-9０-９]+\s*[章回节卷集部篇].*",  # 第X章/回/节…
    r"^\s*[0-9０-９]+\s*[、,，.．:：\s].*\S",                                  # 数字 + 分隔符 + 标题
    r"^\s*[0-9０-９]+\s*$",                                                    # 纯数字标题
    r"^\s*(序章|楔子|尾声|后记|番外).*",                                       # 固定章名
]


@dataclass
class Chapter:
    title: str
    line_index: int     # 起始行号（0-based）
    level: int = 1      # 层级（Markdown ATX 标题 / 章节识别层级）

    @property
    def display(self) -> str:
        return f"{('#' * self.level)} {self.title}  @line {self.line_index}"


def detect_chapters(
    lines: list[str],
    patterns: list[str] | None = None,
) -> list[Chapter]:
    """正则匹配章节，返回 {行号: 章节名} 的有序列表。

    对应 VBA：多个正则以 | 合并为单个「或」模式后逐行 Execute。
    """
    pats = patterns or DEFAULT_PATTERNS
    combined = re.compile("|".join(f"(?:{p})" for p in pats))
    chapters: list[Chapter] = []
    for idx, line in enumerate(lines):
        m = combined.match(line)
        if not m:
            continue
        raw = m.group().strip()
        if not raw:
            continue
        level = _detect_md_level(line) or 1
        chapters.append(Chapter(title=raw, line_index=idx, level=level))
    return chapters


def fill_catalog(lines: list[str], chapters: list[Chapter]) -> list[str]:
    """目录向下填充：每个正文行归属到最近的上一个章节。

    对应 VBA「正则后辅助目录优化」的 lastValidDir 逻辑：
    命中章节 → 更新 last_valid；未命中 → 沿用 last_valid；首行前为空。
    """
    chapter_at_line = {c.line_index: c.title for c in chapters}
    catalog: list[str] = []
    last_valid = ""
    for i in range(len(lines)):
        if i in chapter_at_line:
            last_valid = chapter_at_line[i]
        catalog.append(last_valid)
    return catalog


def _detect_md_level(line: str) -> int | None:
    """识别 Markdown ATX 标题层级（# → 1，## → 2 ……），非 MD 标题返回 None。"""
    m = re.match(r"^(#{1,6})\s+\S", line)
    return len(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
_DEMO = [
    "第一回 甄士隐梦幻识通灵",
    "此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。",
    "列位看官，你道此书从何而来？说起根由虽近荒唐，细按则深有趣味。",
    "第二回 贾夫人仙逝扬州城",
    "原来这贾夫人，乃荣国府贾政之妻王氏。",
    "",
    "1、闲话清谈",
    "却说那日贾雨村闲来无事，便与冷子兴闲话。",
]


def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    ll = [ln for ln in _DEMO]  # 保留空行以演示补全
    chapters = detect_chapters(ll)
    print("[章节识别] 从文本中识别到章节：")
    for c in chapters:
        print(f"    {c.display}")

    catalog = fill_catalog(ll, chapters)
    print("\n[目录补全] 每个正文行的归属章节（A列=正文，B列=补全目录）：")
    for i, ln in enumerate(ll):
        label = ln if ln.strip() else "(空行)"
        print(f"    A{i+1}: {label:<26} B: {catalog[i] or '(无归属)'}")


if __name__ == "__main__":
    _demo()