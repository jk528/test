# -*- coding: utf-8 -*-
"""
插件 04 · 内容上色（核心闭环第 4 环）
================================================

【对应 VBA】READ_上色.bas（Color_SS_TO_SS_22，Characters.Font.Color 逐子串染色）
【复盘定位】「上色」是整个产品的核心卖点，也是技术栈地基的裁决点：
            VBA 用逐个 COM 调用染色，10 万字要 3~10 分钟，是机制性慢；
            正确做法是「一次扫描产出着色区间流」，由渲染内核批量上色。

【实现逻辑拆解】
  输入    ：文本 text + 关键词列表 keywords（+ 可选颜色列表）
  处理    ：
     1. 编译规则：每个关键词绑定一个颜色（对应 VBA 的 4 色循环 Select Case mm）；
     2. 一次扫描：用 re.finditer 对每个词定位全部出现区间 (start, end)——
        替代 VBA 的「InStr 循环 + 逐子串 COM 调用」；
     3. 按「区间起始 + 词长降序」排序裁决重叠（长词优先），产出最终区间流。
  输出    ：Span{ start, end, word, color } 区间流（供任意渲染层消费）
  关键差异：逐子串 COM 调用 → 一次 re 扫描，性能提升百倍；
            区间流是「core/gui 分离」的关键中间产物——PyQt6 的
            QSyntaxHighlighter.setFormat(start,len,fmt) 或 Monaco 的
            token range 都吃同一份区间流。

【纯逻辑说明】
  本模块不依赖任何 GUI，只产出「哪些字符该着什么色」的指令流。
  上层高亮器（QSyntaxHighlighter / Monarch / decoration）对接即可。

【可独立运行】
  python plugin_04_coloring.py          # 内置《红楼梦》台词演示（ANSI + 区间 + HTML）
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, field


# 对应 VBA 4 色循环：RGB(255,0,0)/(0,255,0)/(0,0,255)/(0,255,255)
COLOR_NAMES = ["red", "green", "blue", "cyan"]

# ANSI 前景色（演示用）
_ANSI = {"red": "\033[31m", "green": "\033[32m", "blue": "\033[34m", "cyan": "\033[36m"}
_RESET = "\033[0m"


@dataclass
class ColorRule:
    keyword: str
    color: str
    enabled: bool = True


@dataclass
class Span:
    start: int
    end: int
    word: str
    color: str


def build_rules(keywords: list[str], colors: list[str] | None = None) -> list[ColorRule]:
    """把关键词编译成着色规则（对应 VBA searchTexts 数组 + 4 色循环）。"""
    palette = colors or COLOR_NAMES
    return [
        ColorRule(keyword=w, color=palette[i % len(palette)])
        for i, w in enumerate(keywords)
    ]


def highlight(text: str, rules: list[ColorRule]) -> list[Span]:
    """一次扫描，产出着色区间流（按长词优先、位置排序，逐子串调用在此被消除）。"""
    spans: list[Span] = []
    for rule in rules:
        if not rule.enabled or not rule.keyword:
            continue
        for m in re.finditer(re.escape(rule.keyword), text):
            spans.append(Span(m.start(), m.end(), rule.keyword, rule.color))
    # 重叠裁决：起始位置升序、词长降序（长词优先，对应复盘的冲突规则）
    spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
    return spans


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """抛弃被长词完全覆盖的区段（每通道独立取值、高优先级语义优先的简化落地）。"""
    kept: list[Span] = []
    last_end = -1
    for s in spans:
        if s.start >= last_end:
            kept.append(s)
            last_end = s.end
    return kept


def render_ansi(text: str, spans: list[Span]) -> str:
    """渲染成 ANSI 彩色文本（控制台演示用，等价于 GUI 层把区间套成格式）。"""
    buf: list[str] = []
    pos = 0
    for s in spans:
        buf.append(text[pos:s.start])
        buf.append(_ANSI.get(s.color, ""))
        buf.append(text[s.start:s.end])
        buf.append(_RESET)
        pos = s.end
    buf.append(text[pos:])
    return "".join(buf)


def render_html(text: str, spans: list[Span]) -> str:
    """渲染成 HTML（带 <mark> 包裹着色，等价于 Monaco decoration 消费同一区间流）。"""
    buf: list[str] = []
    pos = 0
    for s in spans:
        buf.append(html.escape(text[pos:s.start]))
        buf.append(f'<span style="color:{s.color};font-weight:600">')
        buf.append(html.escape(text[s.start:s.end]))
        buf.append("</span>")
        pos = s.end
    buf.append(html.escape(text[pos:]))
    return "".join(buf)


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
_DEMO = "宝玉笑道：这个妹妹我曾见过的。黛玉也不理他，只管向贾母道：见过哥哥。"


def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    rules = build_rules(["宝玉", "黛玉", "贾母", "妹妹"])
    spans = highlight(_DEMO, rules)
    resolved = resolve_overlaps(spans)

    print("[内容上色] 关键词规则：")
    for r in rules:
        print(f"    {r.keyword:<6} -> {r.color}")

    print(f"\n[内容上色] 一次扫描产出 {len(resolved)} 个着色区间：")
    for s in resolved:
        print(f"    ({s.start:>2}, {s.end:>2}) [{s.word}] = {s.color}")

    print("\n[内容上色] ANSI 彩色预览（终端看有色，纯文本看词序）：")
    print("    " + render_ansi(_DEMO, resolved))

    print("\n[内容上色] HTML 预览片段：")
    print("    " + render_html(_DEMO, resolved))


if __name__ == "__main__":
    _demo()