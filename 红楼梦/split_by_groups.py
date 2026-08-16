#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按章节聚合分组拆分TXT —— 将连续多章按"每份章数,份数|每份章数,份数"规则聚合为一个文件

聚合字符串格式（参考 READ_聚合生成折线堆叠图.bas 的输入逻辑）:
    每份章数,份数|每份章数,份数|...
      - | 分隔多段；每段 每份章数,份数
      - 每份章数 = 每个文件包含多少章
      - 份数 = 该段生成多少个文件
      - 段消耗 = 每份章数 * 份数，各段累计须 <= 总章数
      - 累计 < 总章数时，剩余章节自动追加一个"余数文件"

便捷模式:
    N              每N章一份，份数 = ceil(总章数 / N)，末份可能不足

示例（红楼梦 120 章）:
    --chunk 40,3                -> 每份40章共3份: 1-40 / 41-80 / 81-120
    --chunk 40                  -> 同上（便捷模式）
    --chunk 20,1|20,1|80,1      -> 1-20 / 21-40 / 41-120
    --chunk 30,2|60,1           -> 1-30 / 31-60 / 61-120
    --chunk 1,20|2,50           -> 前20章每章一文件, 后100章每2章一文件
    --chunk 40,1                -> 1-40 / 41-120（余数自动补齐）
    --chunk 30,4                -> 1-30 / 31-60 / 61-90 / 91-120

输出命名: [前缀_]<序号(补零)>_第<起>-<止><单位>.txt  (如 001_第1-40章.txt)
  - 序号位数由 --serial-width 控制（默认3）
  - 单位(章/回/节/卷)自动从源文件首个章节标题识别
  - 编码 UTF-8 无 BOM，正文保持源文件原样
"""
import re
import os
import sys
import math
import argparse

DEFAULT_CHUNK = "40,3"

# 章节识别正则（与 SplitTxtByChapter.bas / split_honglou_to_west_style.py 一致）
# 中文数字含"万"，支持 第一万章 / 第十万章 等大章节号
PAT = re.compile(r"^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$")


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
    ch = 0  # 已消费章节数
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


def sanitize_filename(name):
    """清洗文件名：非法字符 -> 全角空格，折叠连续空格，限长60"""
    s = name
    for c in '\\/:*?"<>|':
        s = s.replace(c, "　")
    while "　　" in s:
        s = s.replace("　　", "　")
    s = s.strip()
    return s[:60] if len(s) > 60 else s


def scan_chapters(lines):
    """扫描章节起点，返回 (起点行号列表, 单位词)"""
    starts = []
    unit = "回"
    for i, ln in enumerate(lines):
        m = PAT.match(ln)
        if m:
            starts.append(i)
            if len(starts) == 1:
                unit = m.group(2)
    return starts, unit


def main():
    parser = argparse.ArgumentParser(
        description="按章节聚合分组拆分TXT（聚合格式: 每份章数,份数|每份章数,份数...）")
    parser.add_argument("--src", required=True, help="源TXT路径")
    parser.add_argument("--out", default="", help="输出目录（空=源目录下<文件名>_分组）")
    parser.add_argument("--chunk", default=DEFAULT_CHUNK,
                        help="聚合格式 每份章数,份数|... 或便捷 N（默认 %(default)s）")
    parser.add_argument("--prefix", default="", help="文件名前缀")
    parser.add_argument("--serial-width", type=int, default=3,
                        help="序号位数（默认3，如 001/002/...）")
    args = parser.parse_args()

    # 1. 读取源文件（自动检测编码: ANSI/UTF-8/UTF-16）
    if not os.path.isfile(args.src):
        print("错误：源文件不存在 -> %s" % args.src)
        sys.exit(1)
    from readtxt_universal import read_text_auto, detect_encoding, write_text_utf8_nobom
    enc = detect_encoding(args.src)
    print("检测编码: %s" % enc)
    content = read_text_auto(args.src)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")

    # 输出目录：空则从源文件路径派生 <src_dir>\<basename>_分组
    out_dir = args.out
    if not out_dir:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(args.src)),
                               os.path.splitext(os.path.basename(args.src))[0] + "_分组")

    # 2. 识别章节
    starts, unit = scan_chapters(lines)
    total = len(starts)
    print("源文件: %s" % args.src)
    print("总行数: %d  识别章节: %d  单位: %s" % (len(lines), total, unit))
    print("聚合格式: %s" % args.chunk)
    if total == 0:
        print("未识别到章节，终止")
        sys.exit(1)

    # 3. 解析聚合规则
    try:
        groups = parse_groups(args.chunk, total)
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

    # 序号位数自适应：文件数超过当前位数容量时自动扩展（防 10000+ 章排序错乱）
    serial_width = max(args.serial_width, len(str(len(files))))
    if serial_width > args.serial_width:
        print("[提示] 文件数 %d 超过 %d 位容量，序号自动扩展为 %d 位"
              % (len(files), args.serial_width, serial_width))

    # 5. 创建输出目录
    if os.path.exists(out_dir):
        import shutil
        old = os.listdir(out_dir)
        if old:
            print("[警告] 输出目录非空(%d项)，将清空后重建" % len(old))
            shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print("输出目录: %s" % out_dir)
    print()

    # 6. 写每份文件
    for (idx, ch_s, ch_e) in files:
        line_start = starts[ch_s - 1]
        if ch_e < total:
            line_end = starts[ch_e] - 1   # starts[ch_e] 为下一章首行
        else:
            line_end = len(lines) - 1

        body = "\n".join(lines[line_start:line_end + 1])

        if ch_s == ch_e:
            range_str = "第%d%s" % (ch_s, unit)
        else:
            range_str = "第%d-%d%s" % (ch_s, ch_e, unit)
        safe = sanitize_filename(range_str)
        serial = str(idx).zfill(serial_width)
        fname = "%s_%s.txt" % (serial, safe)
        if args.prefix:
            fname = "%s_%s" % (args.prefix, fname)
        fpath = os.path.join(out_dir, fname)

        write_text_utf8_nobom(fpath, body)
        print("  [%s/%d] %s  (第%d-%d%s, %d行)"
              % (serial, len(files), fname, ch_s, ch_e, unit, line_end - line_start + 1))

    # 7. 完成报告
    print()
    print("=" * 60)
    print("拆分完成！共 %d 份" % len(files))
    print("输出目录: %s" % out_dir)
    head = sorted(os.listdir(out_dir))
    if head:
        print("首文件: %s" % head[0])
        print("末文件: %s" % head[-1])


if __name__ == "__main__":
    main()
