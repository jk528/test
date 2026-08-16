#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按西游记章节结构框架拆分TXT(命名规则与VBA SplitTxtByChapter完全一致)

用法:
    python split_honglou_to_west_style.py                      # 默认拆红楼梦
    python split_honglou_to_west_style.py --prefix HL          # 加前缀: HL_001 标题.txt
    python split_honglou_to_west_style.py --serial-width 4     # 序号4位: 0001 标题.txt
    python split_honglou_to_west_style.py --src D:\\a.txt --out D:\\out

命名规则(与VBA统一): [<前缀>_]<序号> <标题>.txt
- 序号与标题间用半角空格; 标题内半角空格转全角空格(对齐西游记风格)
- 文件内部: 保持源文件原样(第N章标题行 + 正文 + (本章完))
- 编码: UTF-8无BOM
"""
import re
import os
import sys

DEFAULT_SRC = r"C:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦\红楼梦.txt"
DEFAULT_OUT_DIR = r"C:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦\红楼梦_拆分"

# 章节识别正则(与VBA一致)
PAT = re.compile(r"^第([0-9一二三四五六七八九十百千零两]+)(章|回|节|卷)(\s*)(.*)$")


def sanitize_title(title):
    """清洗文件名标题(与VBA SanitizeFileName完全一致)：
    - 半角空格 -> 全角空格(对齐西游记"灵根育孕源流出　心性修持大道生"风格)
    - 非法字符 \\ / : * ? " < > | -> 全角空格
    - 折叠连续全角空格
    - 长度限制60
    """
    s = title
    # 半角空格 -> 全角空格
    s = s.replace(" ", "　")
    # 文件名非法字符 -> 全角空格
    for c in '\\/:*?"<>|':
        s = s.replace(c, "　")
    # 折叠连续全角空格
    while "　　" in s:
        s = s.replace("　　", "　")
    s = s.strip()
    if len(s) > 60:
        s = s[:60]
    return s


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="按西游记章节框架拆分TXT(命名规则与VBA SplitTxtByChapter完全一致)")
    parser.add_argument("--src", default=DEFAULT_SRC, help="源TXT路径(默认红楼梦.txt)")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="输出目录(默认红楼梦_拆分)")
    parser.add_argument("--prefix", default="", help="文件名前缀(默认无)")
    parser.add_argument("--serial-width", type=int, default=3, help="序号位数(默认3)")
    args = parser.parse_args()

    src = args.src
    out_dir = args.out
    prefix = args.prefix
    serial_width = args.serial_width

    # 1. 读取源文件
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    print(f"源文件: {src}")
    print(f"总行数: {len(lines)}  总字符: {len(content)}")
    print(f"前缀: {prefix or '(无)'}  序号位数: {serial_width}")

    # 2. 扫描章节起点
    starts = []
    for i, ln in enumerate(lines):
        m = PAT.match(ln)
        if m:
            starts.append((i, m.group(1), m.group(2), m.group(4)))
    print(f"识别章节: {len(starts)}")
    if not starts:
        print("未识别到章节，终止")
        sys.exit(1)

    # 3. 创建输出目录
    if os.path.exists(out_dir):
        # 清理旧目录(目录已不存在则跳过；存在则先列清单后删除)
        import shutil
        old_files = os.listdir(out_dir)
        if old_files:
            print(f"[警告] 输出目录非空({len(old_files)}项)，将清空后重建")
            shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"输出目录: {out_dir}")

    # 4. 写每章文件
    # 命名规则(与VBA统一): [<前缀>_]<序号> <标题>.txt
    n_total = len(starts)
    for idx in range(n_total):
        start_line = starts[idx][0]
        end_line = starts[idx + 1][0] - 1 if idx + 1 < n_total else len(lines) - 1
        title = starts[idx][3]
        safe_title = sanitize_title(title)
        serial = str(idx + 1).zfill(serial_width)
        if prefix:
            file_name = f"{prefix}_{serial} {safe_title}.txt"
        else:
            file_name = f"{serial} {safe_title}.txt"
        file_path = os.path.join(out_dir, file_name)

        # 切片：含章节标题行
        body_lines = lines[start_line:end_line + 1]
        body = "\n".join(body_lines)

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(body)

        if idx < 3 or idx >= n_total - 2:
            print(f"  [{serial}] {file_name}  ({end_line - start_line + 1}行)")
        elif idx == 3:
            print(f"  ...")

    # 5. 完成报告
    print()
    print("=" * 60)
    print(f"拆分完成！共生成 {n_total} 个文件")
    print(f"输出目录: {out_dir}")
    # 校验首尾
    head = os.listdir(out_dir)
    head.sort()
    print(f"首文件: {head[0]}")
    print(f"末文件: {head[-1]}")


if __name__ == "__main__":
    main()
