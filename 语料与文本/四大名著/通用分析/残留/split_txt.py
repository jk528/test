#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT章节拆分工具（合并版）—— 按章节标题识别，支持两种拆分模式

模式:
    chapter  按章节一一拆分（每章一个文件）
    groups   聚合拆分（多章合并为一份）

用法:
    # 按章节一一拆分
    python split_txt.py --src 红楼梦.txt

    # 聚合拆分（默认 40,3）
    python split_txt.py --src 红楼梦.txt --mode groups
    python split_txt.py --src 红楼梦.txt --mode groups --chunk 20,1|20,1|80,1

    # 便捷：传 --chunk 自动切换为 groups 模式
    python split_txt.py --src 红楼梦.txt --chunk 40,3

命名规则(与VBA统一):
    chapter: [<前缀>_]<序号> <标题>.txt
    groups:  [<前缀>_]<序号>_第<起>-<止><单位>.txt

编码: 自动检测(ANSI/UTF-8/UTF-16) -> 输出 UTF-8 无BOM
"""
import re
import os
import sys
import math
import argparse

# 章节识别正则（与VBA一致，含"万"，支持大章节号）
PAT = re.compile(r"^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$")


# ===========================================================================
# 共享函数
# ===========================================================================

def scan_chapters(lines):
    """扫描章节起点，返回 (起点行号列表, 标题列表, 单位词)"""
    starts = []
    titles = []
    unit = "回"
    for i, ln in enumerate(lines):
        m = PAT.match(ln)
        if m:
            starts.append(i)
            title = m.group(4).strip()
            if not title:
                title = "第%s%s" % (m.group(1), m.group(2))
            titles.append(title)
            if len(starts) == 1:
                unit = m.group(2)
    return starts, titles, unit


def sanitize_filename(name):
    """清洗文件名（与VBA SanitizeFileName一致）：
    - 半角空格 -> 全角空格
    - 非法字符 -> 全角空格
    - 折叠连续全角空格；长度限制60
    """
    s = name.replace(" ", "　")
    for c in '\\/:*?"<>|':
        s = s.replace(c, "　")
    while "　　" in s:
        s = s.replace("　　", "　")
    s = s.strip()
    if not s:
        s = "untitled"
    return s[:60]


def resolve_output_dir(src, out_dir, suffix):
    r"""输出目录：空则从源文件路径派生 <src_dir>\<basename><suffix>"""
    if out_dir:
        return out_dir
    return os.path.join(os.path.dirname(os.path.abspath(src)),
                        os.path.splitext(os.path.basename(src))[0] + suffix)


def clean_output_dir(out_dir):
    """清理输出目录中的旧文件"""
    if os.path.exists(out_dir):
        import shutil
        old = os.listdir(out_dir)
        if old:
            print("[警告] 输出目录非空(%d项)，将清空后重建" % len(old))
            shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)


def format_range(ch_start, ch_end, unit):
    """格式化章号范围：第起-止单位 / 第起单位"""
    if ch_start == ch_end:
        return "第%d%s" % (ch_start, unit)
    return "第%d-%d%s" % (ch_start, ch_end, unit)


def write_file(out_dir, fname, body):
    """写入UTF-8无BOM文件"""
    from readtxt_universal import write_text_utf8_nobom
    fpath = os.path.join(out_dir, fname)
    write_text_utf8_nobom(fpath, body)
    return fpath


# ===========================================================================
# 模式1：按章节一一拆分
# ===========================================================================

def split_by_chapter(src, out_dir="", prefix="", serial_width=3):
    """按章节一一拆分：每章一个文件"""
    from readtxt_universal import read_text_auto, detect_encoding

    # 1. 读取源文件
    enc = detect_encoding(src)
    print("检测编码: %s" % enc)
    content = read_text_auto(src)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    print("源文件: %s" % src)
    print("总行数: %d  总字符: %d" % (len(lines), len(content)))

    # 2. 识别章节
    starts, titles, unit = scan_chapters(lines)
    n_total = len(starts)
    print("识别章节: %d  单位: %s" % (n_total, unit))
    if n_total == 0:
        print("未识别到章节，终止")
        sys.exit(1)

    # 3. 序号位数自适应
    serial_width = max(serial_width, len(str(n_total)))
    print("前缀: %s  序号位数: %d" % (prefix or "(无)", serial_width))

    # 4. 输出目录
    out_dir = resolve_output_dir(src, out_dir, "_拆分")
    clean_output_dir(out_dir)
    print("输出目录: %s" % out_dir)

    # 5. 写每章文件
    for idx in range(n_total):
        start_line = starts[idx]
        end_line = starts[idx + 1] - 1 if idx + 1 < n_total else len(lines) - 1
        safe_title = sanitize_filename(titles[idx])
        serial = str(idx + 1).zfill(serial_width)
        if prefix:
            fname = "%s_%s %s.txt" % (prefix, serial, safe_title)
        else:
            fname = "%s %s.txt" % (serial, safe_title)

        body = "\n".join(lines[start_line:end_line + 1])
        write_file(out_dir, fname, body)

        if idx < 3 or idx >= n_total - 2:
            print("  [%s] %s  (%d行)" % (serial, fname, end_line - start_line + 1))
        elif idx == 3:
            print("  ...")

    _print_report(n_total, out_dir)


# ===========================================================================
# 模式2：聚合拆分
# ===========================================================================

def parse_groups(input_str, total):
    """解析聚合格式字符串，返回 [(份数, 每份章数), ...]

    格式:
      N            便捷模式: 每N章一份, 份数=ceil(total/N), 末份可能不足
      a,b          单段: 每份a章, 共b份
      a,b|c,d|...  多段: 各段顺序聚合, 不足自动补余数段
    """
    s = input_str.strip()
    if not s:
        raise ValueError("聚合字符串为空")

    # 便捷模式：纯数字 -> 每N章一份
    if "," not in s and "|" not in s:
        n = int(s)
        if n <= 0:
            raise ValueError("每份章数必须为正数: %r" % s)
        count = math.ceil(total / n)
        return [(count, n)]

    # 多段格式：每份章数,份数|每份章数,份数|...
    parts = [p.strip() for p in s.split("|") if p.strip()]
    groups = []
    consumed = 0
    for part in parts:
        detail = [d.strip() for d in part.split(",")]
        if len(detail) != 2:
            raise ValueError("段格式错误: %r（应为 每份章数,份数）" % part)
        per_chapter, count = int(detail[0]), int(detail[1])
        if per_chapter <= 0 or count <= 0:
            raise ValueError("每份章数和份数必须为正数: %r" % part)
        groups.append((count, per_chapter))   # 内部存 (份数, 每份章数)
        consumed += count * per_chapter

    if consumed > total:
        raise ValueError("消耗章节数 %d 超过总章节数 %d" % (consumed, total))
    if consumed < total:
        groups.append((1, total - consumed))  # 余数自动补齐
    return groups


def expand_groups(groups, total):
    """展开为 [(序号, 起章号, 止章号), ...]（章号 1-based）"""
    files = []
    ch = 0
    idx = 0
    for (length, spacing) in groups:
        for _ in range(length):
            if ch >= total:
                break
            ch_start = ch + 1
            ch_end = min(ch + spacing, total)
            idx += 1
            files.append((idx, ch_start, ch_end))
            ch = ch_end
        if ch >= total:
            break
    return files


def split_by_groups(src, chunk_str="40,3", out_dir="", prefix="", serial_width=3):
    """聚合拆分：按聚合格式将多章合并为一份"""
    from readtxt_universal import read_text_auto, detect_encoding

    # 1. 读取源文件
    enc = detect_encoding(src)
    print("检测编码: %s" % enc)
    content = read_text_auto(src)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")

    # 输出目录
    out_dir = resolve_output_dir(src, out_dir, "_分组")

    # 2. 识别章节
    starts, titles, unit = scan_chapters(lines)
    total = len(starts)
    print("源文件: %s" % src)
    print("总行数: %d  识别章节: %d  单位: %s" % (len(lines), total, unit))
    print("聚合格式: %s" % chunk_str)
    if total == 0:
        print("未识别到章节，终止")
        sys.exit(1)

    # 3. 解析聚合规则
    try:
        groups = parse_groups(chunk_str, total)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)

    consumed = sum(L * S for (L, S) in groups)
    remainder = total - consumed
    print("解析段: %s" % " | ".join("%d,%d" % (S, L) for (L, S) in groups))
    if remainder > 0:
        print("[提示] 累计消耗 %d 章 < 总 %d 章，余数 %d 章自动追加为1个文件"
              % (consumed, total, remainder))

    # 4. 展开为文件列表
    files = expand_groups(groups, total)

    # 序号位数自适应
    serial_width = max(serial_width, len(str(len(files))))
    if serial_width > 3:
        print("[提示] 文件数 %d 超过3位容量，序号自动扩展为 %d 位" % (len(files), serial_width))

    # 5. 创建输出目录
    clean_output_dir(out_dir)
    print("输出目录: %s" % out_dir)
    print()

    # 6. 写每份文件
    for (idx, ch_s, ch_e) in files:
        line_start = starts[ch_s - 1]
        if ch_e < total:
            line_end = starts[ch_e] - 1
        else:
            line_end = len(lines) - 1

        body = "\n".join(lines[line_start:line_end + 1])

        range_str = format_range(ch_s, ch_e, unit)
        safe = sanitize_filename(range_str)
        serial = str(idx).zfill(serial_width)
        fname = "%s_%s.txt" % (serial, safe)
        if prefix:
            fname = "%s_%s" % (prefix, fname)

        write_file(out_dir, fname, body)
        print("  [%s/%d] %s  (第%d-%d%s, %d行)"
              % (serial, len(files), fname, ch_s, ch_e, unit, line_end - line_start + 1))

    _print_report(len(files), out_dir)


# ===========================================================================
# 完成报告
# ===========================================================================

def _print_report(n_files, out_dir):
    print()
    print("=" * 60)
    print("拆分完成！共生成 %d 个文件" % n_files)
    print("输出目录: %s" % out_dir)
    head = sorted(os.listdir(out_dir))
    if head:
        print("首文件: %s" % head[0])
        print("末文件: %s" % head[-1])


# ===========================================================================
# CLI 入口
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="TXT章节拆分工具（支持每章拆分 + 聚合拆分两种模式）")
    parser.add_argument("--src", required=True, help="源TXT路径")
    parser.add_argument("--mode", choices=["chapter", "groups"], default="chapter",
                        help="拆分模式: chapter=每章一文件(默认), groups=聚合拆分")
    parser.add_argument("--out", default="", help="输出目录(空=自动派生)")
    parser.add_argument("--chunk", default=None,
                        help="聚合格式 每份章数,份数|... 或便捷 N（传入时自动切换groups模式）")
    parser.add_argument("--prefix", default="", help="文件名前缀")
    parser.add_argument("--serial-width", type=int, default=3,
                        help="序号位数(默认3，文件数超容量时自动扩展)")
    args = parser.parse_args()

    # 传 --chunk 时自动切换为 groups 模式
    mode = args.mode
    if args.chunk is not None and mode == "chapter":
        mode = "groups"

    if mode == "chapter":
        split_by_chapter(args.src, args.out, args.prefix, args.serial_width)
    else:
        chunk_str = args.chunk if args.chunk else "40,3"
        split_by_groups(args.src, chunk_str, args.out, args.prefix, args.serial_width)


if __name__ == "__main__":
    main()
