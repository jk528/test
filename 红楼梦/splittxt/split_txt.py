#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT章节拆分工具（完整合并版）—— 单文件，复制粘贴即可运行

功能:
  1. 通用TXT编码检测与读写: ANSI(GBK) / UTF-8(含/无BOM) / UTF-16LE / UTF-16BE / GB18030 / Big5
  2. 按章节一一拆分: 每章一个文件
  3. 聚合拆分: 按聚合格式将多章合并为一份

用法:
    # 按章节一一拆分
    python split_txt.py --src 红楼梦.txt

    # 聚合拆分（默认 40,3）
    python split_txt.py --src 红楼梦.txt --mode groups
    python split_txt.py --src 红楼梦.txt --mode groups --chunk "20,1|20,1|80,1"

    # 便捷：传 --chunk 自动切换为 groups 模式
    python split_txt.py --src 红楼梦.txt --chunk 40,3

    # 清洁模式：跳过正文<N字的章节，合并保留章节(>=N)
    python split_txt.py --src 红楼梦.txt --clean 100
    python split_txt.py --src 红楼梦.txt --clean 100,1

    # 清洁模式：合并跳过章节(<N)，用于确认问题
    python split_txt.py --src 红楼梦.txt --clean 100,0

    # 仅检测编码
    python split_txt.py --detect 红楼梦.txt

命名规则(与VBA统一):
    chapter: [<前缀>_]<序号> <标题>.txt
    groups:  [<前缀>_]<序号>_第<起>-<止><单位>.txt

编码: 自动检测(ANSI/UTF-8/UTF-16) -> 输出 UTF-8 无BOM
"""
import re
import os
import sys
import math
import time
import shutil
import argparse

# 可选依赖：charset-normalizer（提升编码检测精度，未安装时自动降级为内置检测）
try:
    from charset_normalizer import from_bytes as _cn_from_bytes
    _HAS_CHARSET_NORMALIZER = True
except ImportError:
    _HAS_CHARSET_NORMALIZER = False

# 章节识别正则（与VBA一致，含"万"，支持大章节号）
PAT = re.compile(r"^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$")


# ===========================================================================
# 第一部分：通用TXT编码检测与读写
# ===========================================================================

# --- BOM 快速检测表（确定性100%，零依赖，最高优先级）---
_BOM_MAP = [
    (b"\xff\xfe", "UTF-16LE"),
    (b"\xfe\xff", "UTF-16BE"),
    (b"\xef\xbb\xbf", "UTF-8"),
]


def _detect_by_bom(raw):
    """通过 BOM 头检测编码，返回编码名或 None"""
    for bom, enc in _BOM_MAP:
        if raw.startswith(bom):
            return enc
    return None


def _detect_by_charset_normalizer(raw):
    """使用 charset-normalizer 统计分析编码（需安装第三方库）"""
    if not _HAS_CHARSET_NORMALIZER:
        return None
    result = _cn_from_bytes(raw).best()
    if result is None or result.encoding is None:
        return None
    enc = result.encoding.lower().replace("-", "_")
    _ALIAS = {
        "utf_8": "utf-8",
        "utf_16": "utf-16",
        "gb_2312": "gbk",
        "gb2312": "gbk",
        "iso_8859_1": "latin-1",
    }
    return _ALIAS.get(enc, enc)


def _detect_by_utf8_scan(raw):
    """通过 UTF-8 多字节序列模式扫描判断 UTF-8 vs ANSI（兜底，无需第三方库）"""
    scan_len = min(len(raw), 1024)
    i = 0
    while i < scan_len:
        b1 = raw[i]
        if b1 <= 0x7F:
            i += 1
            continue
        if (b1 & 0xE0) == 0xC0:
            seq_len = 2
        elif (b1 & 0xF0) == 0xE0:
            seq_len = 3
        elif (b1 & 0xF8) == 0xF0:
            seq_len = 4
        else:
            return "gbk"
        if i + seq_len > len(raw):
            return "gbk"
        for j in range(1, seq_len):
            if (raw[i + j] & 0xC0) != 0x80:
                return "gbk"
        i += seq_len
    return "utf-8"


def detect_encoding_bytes(raw):
    """检测字节数组的编码（三层策略）

    返回: 编码名称字符串，如 "UTF-8" / "GBK" / "UTF-16LE" / "GB18030"
    """
    if not raw:
        return "utf-8"

    # 第1层: BOM 检测
    enc = _detect_by_bom(raw)
    if enc:
        return enc

    # 第2层: charset-normalizer 统计分析
    enc = _detect_by_charset_normalizer(raw)
    if enc:
        return enc

    # 第3层: 手动 UTF-8 字节模式扫描兜底
    return _detect_by_utf8_scan(raw)


def detect_encoding(file_path):
    """检测TXT文件编码，返回编码名称字符串"""
    with open(file_path, "rb") as f:
        raw = f.read()
    return detect_encoding_bytes(raw)


def read_text_auto(file_path, encoding_hint=None):
    """自动检测编码并读取TXT文件全文

    支持: UTF-8(含/不含BOM) / UTF-16LE / UTF-16BE / GBK / GB18030 / Big5 等
    encoding_hint: 手动指定编码(如 "gbk")，跳过自动检测
    """
    with open(file_path, "rb") as f:
        raw = f.read()

    if encoding_hint:
        try:
            return raw.decode(encoding_hint, errors="strict")
        except UnicodeDecodeError as e:
            raise ValueError(
                "指定的编码 %s 解码失败: %s\n错误位置: 字节 %d-%d"
                % (encoding_hint, e.reason, e.start, e.end))

    enc = detect_encoding_bytes(raw)
    # BOM 编码用 Python 内置 codec 自动剥离 BOM
    _BOM_CODEC = {"UTF-16LE": "utf-16", "UTF-16BE": "utf-16", "UTF-8": "utf-8-sig"}
    py_enc = _BOM_CODEC.get(enc, enc)
    try:
        return raw.decode(py_enc, errors="strict")
    except (UnicodeDecodeError, LookupError):
        # 自动检测失败，依次尝试常见中文编码
        for fallback in ("utf-8", "gbk", "gb18030", "big5"):
            try:
                return raw.decode(fallback, errors="strict")
            except UnicodeDecodeError:
                continue
        raise ValueError(
            "无法解码文件，所有编码尝试均失败。\n"
            "请使用 --encoding 参数手动指定编码，例如:\n"
            "  --encoding gbk\n"
            "  --encoding big5\n"
            "  --encoding gb18030")


def write_text_utf8_nobom(file_path, text):
    """写入UTF-8文本（无BOM）"""
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


# ===========================================================================
# 第二部分：章节拆分共享函数
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
            title = m.group(0).strip()
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
    fpath = os.path.join(out_dir, fname)
    write_text_utf8_nobom(fpath, body)
    return fpath


# ===========================================================================
# 第三部分：模式1 - 按章节一一拆分
# ===========================================================================

def _build_clean_header(min_body_len, skipped_count, skipped_chapters,
                        skipped_body_lens, written_count, merge_flag):
    """构建清洁模式合并文件的头部信息"""
    header_lines = [
        "=" * 50,
        "清理说明：正文中文字数小于 %d 的章节已跳过" % min_body_len,
        "跳过章节：%d 个" % skipped_count,
    ]
    if skipped_chapters:
        header_lines.append("跳过明细：")
        for title, blen in skipped_chapters:
            header_lines.append("  %s（%d字）" % (title, blen))
        top3 = sorted(skipped_body_lens, reverse=True)[:3]
        top3_str = "、".join("%d字" % x for x in top3)
        header_lines.append("前三正文：%s" % top3_str)
    header_lines.append("保留章节：%d 个" % written_count)
    if merge_flag == 0:
        header_lines.append("本文件内容：跳过章节（正文汉字 < %d）" % min_body_len)
    elif merge_flag == 1:
        header_lines.append("本文件内容：保留章节（正文汉字 >= %d）" % min_body_len)
    header_lines.append("=" * 50)
    header_lines.append("")
    return header_lines


def split_by_chapter(src, out_dir="", prefix="", serial_width=3, encoding=None,
                     generate_title_only=False, min_body_len=0, merge_flag=None):
    """按章节一一拆分：每章一个文件

    generate_title_only: False=跳过仅有标题/正文不足的章节(默认), True=生成
    min_body_len: 最小正文字数(0=不检测)，正文少于该值的章节也跳过
    merge_flag: None=不合并, 0=合并跳过章节(<N), 1=合并保留章节(>=N)
    """
    t_total0 = time.time()

    # 1. 读取源文件
    t0 = time.time()
    enc = encoding.upper() if encoding else detect_encoding(src)
    print("编码: %s%s" % (enc, " (手动指定)" if encoding else " (自动检测)"))
    content = read_text_auto(src, encoding)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    print("源文件: %s" % src)
    print("总行数: %d  总字符: %d" % (len(lines), len(content)))
    t_read = time.time() - t0

    # 2. 识别章节
    t0 = time.time()
    starts, titles, unit = scan_chapters(lines)
    n_total = len(starts)
    print("识别章节: %d  单位: %s" % (n_total, unit))
    if n_total == 0:
        print("未识别到章节，终止")
        sys.exit(1)
    t_scan = time.time() - t0

    # 3. 序号位数自适应
    serial_width = max(serial_width, len(str(n_total)))
    print("前缀: %s  序号位数: %d" % (prefix or "(无)", serial_width))

    # 4. 输出目录
    out_dir = resolve_output_dir(src, out_dir, "_拆分")
    clean_output_dir(out_dir)
    print("输出目录: %s" % out_dir)

    # 5. 写每章文件
    title_only_count = 0
    short_body_count = 0
    skipped_count = 0
    written_count = 0
    skipped_body_lens = []
    kept_texts = []          # 合并文件用：保留章节的文本
    skipped_texts = []        # 合并文件用：跳过章节的文本
    skipped_chapters = []    # 合并文件用：跳过章节的(标题, 正文字数)
    t0 = time.time()
    for idx in range(n_total):
        start_line = starts[idx]
        end_line = starts[idx + 1] - 1 if idx + 1 < n_total else len(lines) - 1
        if end_line < start_line:
            end_line = start_line    # 安全保护
        n_lines = end_line - start_line + 1

        # 提取完整章节文本（含标题行）
        body = "\n".join(lines[start_line:end_line + 1])

        # 计算正文汉字数（不含标题行，仅统计汉字）
        if n_lines > 1:
            body_text = "".join(lines[start_line + 1:end_line + 1])
            body_len = len(re.sub(r'[^\u4e00-\u9fff]', '', body_text))
        else:
            body_len = 0

        # 判断是否为不足章节
        is_insufficient = False
        if n_lines == 1:
            title_only_count += 1
            is_insufficient = True
        elif min_body_len > 0 and body_len < min_body_len:
            short_body_count += 1
            is_insufficient = True

        if is_insufficient and not generate_title_only:
            skipped_count += 1
            skipped_body_lens.append(body_len)
            if merge_flag is not None:
                skipped_chapters.append((titles[idx], body_len))
            if merge_flag == 0:
                skipped_texts.append(body)
            continue

        safe_title = sanitize_filename(titles[idx])
        serial = str(written_count + 1).zfill(serial_width)
        if prefix:
            fname = "%s_%s_%s.txt" % (prefix, serial, safe_title)
        else:
            fname = "%s_%s.txt" % (serial, safe_title)

        write_file(out_dir, fname, body)
        if merge_flag == 1:
            kept_texts.append(body)

        if written_count < 3 or idx >= n_total - 2:
            if n_lines == 1:
                tag = "  (仅标题)"
            elif min_body_len > 0 and body_len < min_body_len:
                tag = "  (%d行,正文%d字)" % (n_lines, body_len)
            else:
                tag = "  (%d行)" % n_lines
            print("  [%s] %s%s" % (serial, fname, tag))
        elif written_count == 3:
            print("  ...")

        written_count += 1

    t_write = time.time() - t0
    t_total = time.time() - t_total0

    # 6. 生成合并文件（清洁模式）
    if merge_flag is not None:
        src_name = os.path.splitext(os.path.basename(src))[0]
        if merge_flag == 1 and kept_texts:
            merge_texts = kept_texts
            merge_name = "保留大于等于%d_%s.txt" % (min_body_len, src_name)
        elif merge_flag == 0 and skipped_texts:
            merge_texts = skipped_texts
            merge_name = "清理小于%d_%s.txt" % (min_body_len, src_name)
        else:
            merge_texts = None
        if merge_texts:
            header_lines = _build_clean_header(min_body_len, skipped_count, skipped_chapters,
                                               skipped_body_lens, written_count, merge_flag)
            merge_path = os.path.join(out_dir, merge_name)
            with open(merge_path, "w", encoding="utf-8") as f:
                f.write("\n".join(header_lines))
                f.write("\n".join(merge_texts))
            print("合并文件：%s（%d章合并）" % (merge_name, len(merge_texts)))

    parts = []
    if title_only_count > 0:
        parts.append("%d个仅有标题" % title_only_count)
    if short_body_count > 0:
        parts.append("%d个正文不足" % short_body_count)
    if skipped_count > 0:
        top3 = sorted(skipped_body_lens, reverse=True)[:3]
        top3_str = "、".join("%d字" % x for x in top3)
        print("[提示] 跳过 %d 个章节（%s），前三：%s（--keep-title-only 可生成）"
              % (skipped_count, "、".join(parts), top3_str))
    elif parts:
        print("[提示] %s（已生成）" % "、".join(parts))

    _print_report(written_count, out_dir, [
        ("读取文件", t_read),
        ("识别章节", t_scan),
        ("写入文件", t_write),
        ("总计耗时", t_total),
    ])


# ===========================================================================
# 第四部分：模式2 - 聚合拆分
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


def split_by_groups(src, chunk_str="40,3", out_dir="", prefix="", serial_width=3, encoding=None):
    """聚合拆分：按聚合格式将多章合并为一份"""
    t_total0 = time.time()

    # 1. 读取源文件
    t0 = time.time()
    enc = encoding.upper() if encoding else detect_encoding(src)
    print("编码: %s%s" % (enc, " (手动指定)" if encoding else " (自动检测)"))
    content = read_text_auto(src, encoding)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    t_read = time.time() - t0

    # 输出目录
    out_dir = resolve_output_dir(src, out_dir, "_分组")

    # 2. 识别章节
    t0 = time.time()
    starts, titles, unit = scan_chapters(lines)
    total = len(starts)
    t_scan = time.time() - t0
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
    t0 = time.time()
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

    t_write = time.time() - t0
    t_total = time.time() - t_total0

    _print_report(len(files), out_dir, [
        ("读取文件", t_read),
        ("识别章节", t_scan),
        ("写入文件", t_write),
        ("总计耗时", t_total),
    ])


# ===========================================================================
# 第五部分：完成报告与CLI入口
# ===========================================================================

def _print_report(n_files, out_dir, timing=None):
    print()
    print("=" * 60)
    print("拆分完成！共生成 %d 个文件" % n_files)
    print("输出目录: %s" % out_dir)
    head = sorted(os.listdir(out_dir))
    if head:
        print("首文件: %s" % head[0])
        print("末文件: %s" % head[-1])
    if timing:
        print()
        print("【计时统计】")
        for label, val in timing:
            print("  %s：%.2f 秒" % (label, val))


def _detect_main(paths):
    """仅检测编码模式"""
    for path in paths:
        with open(path, "rb") as f:
            raw = f.read()
        enc = detect_encoding_bytes(raw)
        print("文件: %s" % os.path.basename(path))
        print("  编码: %s (charset-normalizer: %s)" % (enc, "已启用" if _HAS_CHARSET_NORMALIZER else "未安装"))
        print("  字节数: %d" % len(raw))
        content = read_text_auto(path)
        print("  字符数: %d" % len(content))
        print("  前80字: %s" % content[:80])
        print()


def main():
    parser = argparse.ArgumentParser(
        description="TXT章节拆分工具（完整版，支持编码检测 + 每章拆分 + 聚合拆分）")
    parser.add_argument("--src", default=None, help="源TXT路径")
    parser.add_argument("--mode", choices=["chapter", "groups"], default="chapter",
                        help="拆分模式: chapter=每章一文件(默认), groups=聚合拆分")
    parser.add_argument("--out", default="", help="输出目录(空=自动派生)")
    parser.add_argument("--chunk", default=None,
                        help="聚合格式 每份章数,份数|... 或便捷 N（传入时自动切换groups模式）")
    parser.add_argument("--prefix", default="", help="文件名前缀")
    parser.add_argument("--serial-width", type=int, default=3,
                        help="序号位数(默认3，文件数超容量时自动扩展)")
    parser.add_argument("--encoding", default=None,
                        help="手动指定源文件编码(如 gbk/big5/utf-8)，跳过自动检测")
    parser.add_argument("--detect", nargs="+", default=None,
                        help="仅检测编码(不拆分): --detect 文件1 [文件2 ...]")
    parser.add_argument("--keep-title-only", action="store_true", default=False,
                        help="生成仅有标题/正文不足的章节文件（默认跳过）")
    parser.add_argument("--min-body-len", type=int, default=0,
                        help="最小正文字数(0=不检测)，正文少于该值的章节跳过")
    parser.add_argument("--clean", default=None,
                        help="清洁模式: N[,flag]，跳过正文汉字<N的章节；flag=0合并跳过章节, flag=1(默认)合并保留章节")
    args = parser.parse_args()

    # 仅检测编码模式
    if args.detect:
        _detect_main(args.detect)
        return

    if not args.src:
        parser.error("拆分模式需要 --src 参数")

    # 传 --chunk 时自动切换为 groups 模式
    mode = args.mode
    if args.chunk is not None and mode == "chapter":
        mode = "groups"

    # 解析 --clean 参数
    merge_flag = None
    if args.clean is not None:
        clean_parts = args.clean.split(",")
        clean_min = int(clean_parts[0])
        clean_flag = int(clean_parts[1]) if len(clean_parts) > 1 else 1
        args.min_body_len = clean_min
        merge_flag = clean_flag
        mode = "chapter"

    try:
        if mode == "chapter":
            split_by_chapter(args.src, args.out, args.prefix, args.serial_width,
                             args.encoding, args.keep_title_only, args.min_body_len, merge_flag)
        else:
            chunk_str = args.chunk if args.chunk else "40,3"
            split_by_groups(args.src, chunk_str, args.out, args.prefix, args.serial_width, args.encoding)
    except ValueError as e:
        print("[错误] %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
