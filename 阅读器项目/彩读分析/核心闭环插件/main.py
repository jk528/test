# -*- coding: utf-8 -*-
"""
最小闭环主程序（核心闭环 6 环串联）
================================================

把 6 个可独立运行的插件按数据流串成一条最小可用链路：

    文件路径 ─▶ [01 文件导入] ─▶ [02 编码识别] ─▶ 文本行 lines
                                        │
                      ┌─────────────────┘
                      ▼
               [03 章节识别] ─▶ Chapter 列表 ─┬─▶ [05 目录跳转] ─▶ 定位区间
                      │                       └─▶ [06 书签进度] ─▶ 持久化
                      ▼
               [04 内容上色] ─▶ Span 区间流 (渲染层消费)

运行方式：python main.py
"""

from __future__ import annotations

import os
import sys
import tempfile

from plugin_01_file_import import import_file
from plugin_02_encoding_detect import detect_from_bytes
from plugin_03_chapter_detect import detect_chapters, fill_catalog
from plugin_04_coloring import build_rules, highlight, resolve_overlaps
from plugin_05_catalog_jump import build_ranges, jump_to_line, search_chapters
from plugin_06_bookmark_progress import BookmarkStore


# 内置样章（多章回 + 角色名，覆盖上色/跳转/书签所需语义）
_SAMPLE = (
    "第一回 甄士隐梦幻识通灵\n"
    "此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。\n"
    "宝玉笑道：这个妹妹我曾见过的。黛玉也不理他，只管向贾母道安。\n"
    "\n"
    "第二回 贾夫人仙逝扬州城\n"
    "原来这贾夫人，乃荣国府贾政之妻王氏。黛玉自此常住贾府。\n"
    "\n"
    "第三回 托内兄如海荐西宾\n"
    "贾雨村听得这话，便与冷子兴计较，欲托贾政荐个西宾的差事。\n"
)

# 上色用的角色关键词（对应 READ_上色 的用户自定义高亮词）
_KEYWORDS = ["宝玉", "黛玉", "贾母", "贾政"]


def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_closed_loop() -> dict:
    """执行完整闭环，返回各环节的关键产物（供上层或测试取用）。"""
    result: dict = {}

    # -------- 第 1~2 环：文件导入 + 编码识别 --------
    tmp = os.path.join(tempfile.gettempdir(), "colortxt_loop_sample.txt")
    with open(tmp, "wb") as f:
        f.write(_SAMPLE.encode("gbk"))          # 刻意用 GBK 落盘，验证编码识别

    content = import_file(tmp)
    result["encoding"] = content.encoding
    result["lines"] = content.lines

    raw = open(tmp, "rb").read()
    result["encode_report"] = detect_from_bytes(raw)

    print("[闭环 1/2] 文件导入 + 编码识别")
    print(f"    源文件   : {tmp}")
    print(f"    探测编码 : {result['encode_report'].encoding} "
          f"(置信度 {result['encode_report'].confidence}, 方法 {result['encode_report'].method})")
    print(f"    文本行数 : {content.total_lines}")

    # -------- 第 3 环：章节识别 + 目录补全 --------
    lines = content.lines
    chapters = detect_chapters(lines)
    catalog = fill_catalog(lines, chapters)
    result["chapters"] = chapters
    result["catalog"] = catalog

    print("\n[闭环 3] 章节识别：")
    for c in chapters:
        print(f"    {c.display}")

    # -------- 第 4 环：内容上色 --------
    rules = build_rules(_KEYWORDS)
    spans = []
    for i, ln in enumerate(lines):
        for s in highlight(ln, rules):
            spans.append((i, s.start, s.end, s.word, s.color))
    result["spans"] = spans
    result["span_count"] = len(spans)

    print(f"\n[闭环 4] 内容上色：全书扫描产出 {len(spans)} 个着色区间（关键词 {_KEYWORDS}）")
    for line_no, s, e, w, c in spans[:6]:
        print(f"    行{line_no} ({s},{e}) [{w}] = {c}")

    # -------- 第 5 环：目录跳转 --------
    ranges = build_ranges(chapters, len(lines))
    target = jump_to_line(chapters, len(lines), 4)      # 跳到第 4 行
    hit = search_chapters(chapters, "贾")               # 模糊搜索
    result["jump"] = target
    result["search"] = hit

    print("\n[闭环 5] 目录跳转：")
    print(f"    按行号跳到第 4 行 -> {target.chapter} 行区间 [{target.start_line}, {target.end_line})")
    print(f"    模糊搜索「贾」 -> {[c.title for c in hit]}")

    # -------- 第 6 环：书签进度 --------
    bid = "hongloumeng-loop"
    store = BookmarkStore(":memory:")
    store.add_bookmark(bid, chapters[0].title, 2, "主角登场")
    store.add_bookmark(bid, chapters[-1].title, 6)
    store.save_progress(bid, target.chapter, target.start_line)
    prog = store.load_progress(bid)
    result["bookmarks"] = store.list_bookmarks(bid)
    result["progress"] = prog

    print("\n[闭环 6] 书签进度：")
    for b in result["bookmarks"]:
        print(f"    书签 #{b.id} [{b.chapter_title}] 行 {b.line_index}  {b.note}")
    print(f"    阅读进度 -> {prog.chapter_title} @ 行 {prog.line_index}")
    store.close()

    return result


def _demo():
    _setup_console()
    print("=" * 60)
    print("  彩读 · 核心闭环最小演示（6 环全链路串通）")
    print("=" * 60)
    run_closed_loop()
    print("\n" + "=" * 60)
    print("闭环完成：导入 → 编码 → 章节 → 上色 → 跳转 → 书签 全链路跑通")


if __name__ == "__main__":
    _demo()