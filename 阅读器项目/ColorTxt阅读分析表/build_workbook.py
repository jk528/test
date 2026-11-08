# -*- coding: utf-8 -*-
"""
ColorTxt 阅读分析（一键版）工作簿生成脚本
================================================
依赖：pywin32（Windows + Microsoft Excel）
用法：
    1) pip install -r requirements.txt
    2) 确保本机已安装 Microsoft Excel
    3) python build_workbook.py
产物：
    ColorTxt阅读分析_一键版.xlsm
    VBA源码_导出GBK/*.bas   （从工作簿导出的模块，可直接重新导入）

说明：
    - 脚本会临时把 HKCU 下的 AccessVBOM 设为 1，以便写入 VBA 工程；
      结束后恢复原值。
    - 源模块位于 VBA源码/（UTF-8，供阅读）；导入时转换为 GBK 临时文件，
      因为中文 Windows 的 VBA 编辑器使用 ANSI/GBK 代码页。
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import win32com.client as win32
import pythoncom

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "VBA源码"
EXPORT_DIR = ROOT / "VBA源码_导出GBK"
OUT_FILE = ROOT / "ColorTxt阅读分析_一键版.xlsm"

SHEET_NAMES = [
    "使用说明", "正文输入", "配置", "词表", "逐句结果", "汇总统计",
    "图表数据", "图表", "上色预览", "词频Top", "运行日志", "示例原文",
]

CFG_DATA_START = 4
LEX_DATA_START = 3
INPUT_START = 5


def rgb(hex_str: str) -> int:
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return b * 65536 + g * 256 + r


CONFIG_ROWS = [
    ("match_mode", "词典最大匹配", "全局默认匹配方式：词典最大匹配 / 关键词包含 / 正则。词表「匹配规则」为“继承”时使用此值。", "全局"),
    ("case_sensitive", "否", "是否区分英文大小写（中文不受影响）。", "全局"),
    ("overwrite_results", "是", "每次运行是否清空旧结果；选“否”时逐句结果追加到末尾，汇总/图表仍按本次运行重建。", "运行"),
    ("enable_dimensions", "是", "维度总开关；选“否”时所有维度停用。", "全局"),
    ("enable_color", "是", "是否启用单元格内富文本上色。", "上色"),
    ("color_mode", "逐字符", "逐字符 / 整格 / 关闭。逐字符是 ColorTxt 的阅读效果；整格只用主维度底色，性能最好。", "上色"),
    ("max_color_sentences", "300", "最多对多少句做逐字符上色；同时决定「上色预览」的行数。", "性能"),
    ("max_hits_per_sentence", "20", "单句最多着色命中片段数，防止单句过长导致大量 Characters 调用。", "性能"),
    ("max_color_chars", "20000", "全工作簿着色字符总预算；超出后剩余句子自动降级为整格浅色底纹。", "性能"),
    ("font_name", "微软雅黑", "结果表与预览的字体。", "格式"),
    ("font_size", "11", "结果表字号（上色预览自动 +1）。", "格式"),
    ("result_start_row", "2", "逐句结果数据起始行；第 1 行固定为表头。", "输出"),
    ("top_n", "30", "词频 / 字频 Top N。", "输出"),
    ("summary_top_n", "5", "汇总统计中每个维度展示的 Top 词数量。", "输出"),
    ("ignore_blank_lines", "是", "是=忽略空行；否=空行保留为空段（在图表数据中占一行 0 值）。", "文本"),
    ("max_paragraph_chars", "2000", "单段最大字符数；超出按标点切分为多个段块。", "文本"),
    ("max_sentence_chars", "200", "单句最大字符数；超出切分，避免单句过长影响上色。", "文本"),
    ("max_total_chars", "60000", "单次最多处理字符数（含标点）；超出截断并在日志告警。", "性能"),
    ("max_sentences", "5000", "单次最多处理句子数。", "性能"),
    ("chart_type", "折线堆叠", "折线堆叠 / 柱状堆叠。", "图表"),
    ("show_finish_msg", "否", "运行结束/失败是否弹窗；自动化验证请保持“否”。", "运行"),
    ("min_word_len", "2", "词频统计最小词长（只影响 Top 词表，不影响维度匹配）。", "输出"),
]

DIM_SWITCHES = [
    ("dim_人物", "是", "维度开关：人物"),
    ("dim_地点", "是", "维度开关：地点"),
    ("dim_功法/行为", "是", "维度开关：功法/行为"),
    ("dim_物品", "是", "维度开关：物品"),
    ("dim_时间", "是", "维度开关：时间"),
    ("dim_情绪/神态", "是", "维度开关：情绪/神态"),
    ("dim_事件", "是", "维度开关：事件"),
    ("dim_其他", "是", "维度开关：其他"),
]

LEX_ROWS = [
    ("维度名", "关键词", "颜色", "优先级", "匹配规则", "启用", "来源", "备注"),
    ("人物", "萧炎", "#C00000", 1, "继承", "是", "继承", "主角"),
    ("人物", "药老", "#C00000", 1, "继承", "是", "继承", "导师"),
    ("人物", "云韵", "#C00000", 1, "继承", "是", "继承", ""),
    ("人物", "纳兰嫣然", "#C00000", 1, "继承", "是", "继承", ""),
    ("地点", "乌坦城", "#1F4E79", 2, "继承", "是", "继承", ""),
    ("地点", "魔兽山脉", "#1F4E79", 2, "继承", "是", "继承", ""),
    ("地点", "城门口", "#1F4E79", 2, "继承", "是", "继承", ""),
    ("地点", "城外", "#1F4E79", 2, "包含", "是", "简化", "包含匹配示例"),
    ("功法/行为", "焚决", "#2E7D32", 3, "继承", "是", "继承", ""),
    ("功法/行为", "斗气", "#2E7D32", 3, "继承", "是", "继承", ""),
    ("功法/行为", "炼药", "#2E7D32", 3, "继承", "是", "继承", "与“事件”同词，按优先级归功法"),
    ("功法/行为", "调息", "#2E7D32", 3, "继承", "是", "继承", ""),
    ("功法/行为", "修炼", "#2E7D32", 3, "继承", "是", "继承", "样例中未出现，用于展示 0 覆盖"),
    ("功法/行为", "突破", "#2E7D32", 3, "继承", "是", "继承", ""),
    ("物品", "丹药", "#00838F", 4, "继承", "是", "继承", ""),
    ("物品", "回气丹", "#00838F", 4, "继承", "是", "继承", ""),
    ("物品", "纳戒", "#00838F", 4, "继承", "是", "继承", ""),
    ("物品", "魔核", "#00838F", 4, "继承", "是", "继承", ""),
    ("物品", "药方", "#00838F", 4, "继承", "是", "继承", ""),
    ("物品", "炼药笔记", "#00838F", 4, "包含", "是", "简化", ""),
    ("时间", "三年之期", "#BF8F00", 5, "继承", "是", "继承", ""),
    ("时间", "三年", "#BF8F00", 5, "包含", "是", "简化", "与“三年之期”重叠，优先取长词"),
    ("时间", "清晨", "#BF8F00", 5, "继承", "是", "继承", ""),
    ("时间", "夜里", "#BF8F00", 5, "继承", "是", "继承", ""),
    ("时间", "第二天", "#BF8F00", 5, "继承", "是", "继承", ""),
    ("时间", "今天", "#BF8F00", 5, "继承", "是", "继承", ""),
    ("情绪/神态", "冷冷", "#7B1FA2", 6, "继承", "是", "简化", ""),
    ("情绪/神态", "笑意", "#7B1FA2", 6, "继承", "是", "简化", ""),
    ("情绪/神态", "沉默", "#7B1FA2", 6, "继承", "是", "简化", ""),
    ("情绪/神态", "愤怒", "#7B1FA2", 6, "继承", "是", "简化", ""),
    ("情绪/神态", "喘了口气", "#7B1FA2", 6, "包含", "是", "简化", ""),
    ("事件", "退婚", "#5D4037", 7, "继承", "是", "简化", ""),
    ("事件", "战斗", "#5D4037", 7, "继承", "是", "简化", ""),
    ("事件", "嘶吼", "#5D4037", 7, "继承", "是", "简化", ""),
    ("事件", "炼药", "#5D4037", 7, "继承", "是", "简化", "同词多维度，优先级裁决为功法"),
    ("其他", "斗气", "#616161", 8, "继承", "是", "简化", "同词多维度，优先级裁决为功法"),
]

SAMPLE = [
    "夜色压在乌坦城的上空，萧炎站在药铺门口，指尖还残留着丹药的苦味。他抬头看向远处的魔兽山脉，心里默默算着三年之期。",
    "药老的声音从纳戒里传来，带着几分笑意：「小子，斗气不是靠急出来的。你今日炼药的手法已经稳了，明天去城外试试。」",
    "清晨，萧炎独自走进魔兽山脉外围。他在一棵老树下盘膝而坐，运转焚决，体内斗气沿着经脉缓缓流动。",
    "忽然，草丛中传来低沉的嘶吼。一头二阶魔兽扑出，萧炎侧身避开，掌中斗气凝成气旋，反手拍在魔兽的脖颈上。",
    "战斗结束时，他的衣袖已被划破。萧炎喘了口气，从纳戒中取出一枚回气丹服下，又把地上的魔核收进布袋。",
    "回到乌坦城，云韵正在城门口等他。她看了一眼他身上的伤，冷冷地说：「你太急了。若再深入十里，遇上三阶魔兽，没人救得了你。」",
    "萧炎没有反驳。他知道云韵说得对，可三年之期越来越近，纳兰嫣然的退婚像一根刺，扎在心里。",
    "夜里，他再次翻开炼药笔记。药老说，真正的突破不在丹药，而在心境。萧炎沉默许久，终于把灯吹灭，闭目调息。",
    "第二天清晨，他带着新的药方出城。乌坦城的城门在身后渐渐远去，魔兽山脉的雾气在前方升起。他知道，这一趟不会轻松。",
    "但他还是走了进去。焚决在体内缓缓转动，斗气如溪流般汇聚，三年之期，从今天开始倒计时。",
]

HELP_LINES = [
    ("ColorTxt 阅读分析 · 一键版", 1),
    ("", 0),
    ("一键流程", 2),
    ("1. 在「正文输入」A5 起粘贴文本（每行一段；也可把多行文本整段粘进 A5，宏会按换行拆分）。", 0),
    ("2. 如需调整维度/颜色/匹配方式，编辑「配置」与「词表」，不需要改代码。", 0),
    ("3. 点击「一键分析」，依次完成：分句 → 分词/匹配 → 优先级裁决 → 上色 → 逐句结果 → 汇总 → 图表。", 0),
    ("4. 结果在「逐句结果」「汇总统计」「图表」「上色预览」「词频Top」；过程信息在「运行日志」。", 0),
    ("", 0),
    ("工作表作用", 2),
    ("正文输入：粘贴正文；A1-A3 为提示区，请从 A5 开始。", 0),
    ("配置：集中参数开关，改完直接重跑。", 0),
    ("词表：维度名 / 关键词 / 颜色 / 优先级 / 匹配规则 / 启用；可自由增删行。", 0),
    ("逐句结果：每句一行，含命中维度、命中词、主维度、主色、上色状态。", 0),
    ("汇总统计：总体指标、维度覆盖率、一致性校验、耗时。", 0),
    ("图表数据：维度 × 段落的命中矩阵，图表最多展示前 120 段。", 0),
    ("图表：堆叠折线/柱状图，直观看到各维度在段落间的分布。", 0),
    ("上色预览：字符级着色后的句子，是 ColorTxt 阅读效果的 Excel 落地。", 0),
    ("词频Top：关键词词频 + 汉字字频 Top N。", 0),
    ("运行日志：每次运行的阶段耗时、告警与错误。", 0),
    ("", 0),
    ("必须知道的限制", 2),
    ("· Excel 单格上限 32767 字符；超长段落会按 max_paragraph_chars / max_sentence_chars 切分。", 0),
    ("· 单元格内逐字符上色靠 Characters(start,length).Font.Color，大文本会变慢；已用“句数 + 单句命中 + 总字符预算”三重限制。", 0),
    ("· Excel 没有中文分词引擎；本项目用“词表词典最大匹配 / 关键词包含 / 正则”替代，精度取决于词表。", 0),
    ("· 宏安全性：首次打开需点击“启用内容”；修改后必须另存为 .xlsm。", 0),
    ("· 详细说明、性能实测与已知限制见同目录 README.md。", 0),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def write_table(ws, start_row: int, start_col: int, rows) -> None:
    if not rows:
        return
    nrows = len(rows)
    ncols = max(len(r) for r in rows)
    data = []
    for r in rows:
        row = list(r) + [""] * (ncols - len(r))
        data.append(tuple(row))
    ws.Range(ws.Cells(start_row, start_col), ws.Cells(start_row + nrows - 1, start_col + ncols - 1)).Value = tuple(data)


def add_button(ws, left, top, width, height, caption, macro, primary=True) -> None:
    shp = ws.Shapes.AddShape(5, left, top, width, height)  # 5 = rounded rectangle
    shp.OnAction = macro
    shp.TextFrame2.TextRange.Text = caption
    shp.TextFrame2.TextRange.Font.Name = "微软雅黑"
    shp.TextFrame2.TextRange.Font.Size = 11
    shp.TextFrame2.TextRange.Font.Bold = True
    shp.TextFrame2.VerticalAnchor = 3
    shp.TextFrame2.HorizontalAnchor = 2
    if primary:
        shp.Fill.ForeColor.RGB = rgb("#1F4E79")
        shp.Line.ForeColor.RGB = rgb("#1F4E79")
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
    else:
        shp.Fill.ForeColor.RGB = rgb("#D9E2F3")
        shp.Line.ForeColor.RGB = rgb("#8EA9DB")
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = rgb("#1F4E79")


def build_structure(wb) -> None:
    # 删除多余表，按顺序创建
    while wb.Sheets.Count > 1:
        wb.Sheets(wb.Sheets.Count).Delete()
    first = wb.Sheets(1)
    first.Name = SHEET_NAMES[0]
    for name in SHEET_NAMES[1:]:
        ws = wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
        ws.Name = name

    tab_colors = {
        "使用说明": "#808080", "正文输入": "#1F4E79", "配置": "#BF8F00",
        "词表": "#BF8F00", "逐句结果": "#2E7D32", "汇总统计": "#2E7D32",
        "图表数据": "#7B1FA2", "图表": "#7B1FA2", "上色预览": "#7B1FA2",
        "词频Top": "#616161", "运行日志": "#616161", "示例原文": "#BF8F00",
    }
    for name, hx in tab_colors.items():
        wb.Sheets(name).Tab.Color = rgb(hx)


def build_help(wb) -> None:
    ws = wb.Sheets("使用说明")
    ws.Cells(1, 1).Value = HELP_LINES[0][0]
    ws.Range("A1:J1").Merge()
    ws.Range("A1:J1").Font.Name = "微软雅黑"
    ws.Range("A1:J1").Font.Size = 20
    ws.Range("A1:J1").Font.Bold = True
    ws.Range("A1:J1").Font.Color = rgb("#1F4E79")
    ws.Rows(1).RowHeight = 38

    r = 3
    for text, kind in HELP_LINES[1:]:
        ws.Cells(r, 1).Value = text
        if kind == 2:
            ws.Cells(r, 1).Font.Bold = True
            ws.Cells(r, 1).Font.Size = 13
            ws.Cells(r, 1).Font.Color = rgb("#1F4E79")
        else:
            ws.Cells(r, 1).Font.Size = 10.5
            ws.Cells(r, 1).Font.Color = rgb("#404040")
        r += 1
    ws.Columns(1).ColumnWidth = 118
    ws.Range("A3:A%d" % (r - 1)).WrapText = True
    ws.Range("A3:A%d" % (r - 1)).Font.Name = "微软雅黑"

    add_button(ws, 720, 8, 112, 32, "一键分析", "RunFullAnalysis", True)
    add_button(ws, 840, 8, 112, 32, "载入示例", "MainLoadSample", False)
    add_button(ws, 960, 8, 112, 32, "清空结果", "MainClearResults", False)


def build_input(wb) -> None:
    ws = wb.Sheets("正文输入")
    ws.Cells(1, 1).Value = "正文输入"
    ws.Cells(1, 1).Font.Name = "微软雅黑"
    ws.Cells(1, 1).Font.Size = 16
    ws.Cells(1, 1).Font.Bold = True
    ws.Cells(1, 1).Font.Color = rgb("#1F4E79")
    ws.Cells(2, 1).Value = "从 A5 开始粘贴。每行一段；也可以把整段多行文本粘进 A5，宏会按换行自动拆分。"
    ws.Cells(2, 1).Font.Size = 10
    ws.Cells(2, 1).Font.Color = rgb("#7F7F7F")
    ws.Cells(3, 1).Value = "↓ 文本区"
    ws.Cells(3, 1).Font.Bold = True
    ws.Cells(3, 1).Font.Color = rgb("#BF8F00")
    for i, para in enumerate(SAMPLE):
        ws.Cells(INPUT_START + i, 1).Value = para
    ws.Columns(1).ColumnWidth = 120
    ws.Range("A%d:A200" % INPUT_START).WrapText = True
    ws.Range("A%d:A200" % INPUT_START).Font.Name = "微软雅黑"
    ws.Range("A%d:A200" % INPUT_START).Font.Size = 11
    ws.Rows("%d:200" % INPUT_START).RowHeight = 22

    add_button(ws, 720, 8, 112, 32, "一键分析", "RunFullAnalysis", True)
    add_button(ws, 840, 8, 112, 32, "清空正文", "MainClearInput", False)
    add_button(ws, 960, 8, 112, 32, "载入示例", "MainLoadSample", False)


def build_config(wb) -> None:
    ws = wb.Sheets("配置")
    ws.Cells(1, 1).Value = "配置（改完直接点「一键分析」，无需改代码）"
    ws.Range("A1:D1").Merge()
    ws.Range("A1:D1").Font.Name = "微软雅黑"
    ws.Range("A1:D1").Font.Size = 15
    ws.Range("A1:D1").Font.Bold = True
    ws.Range("A1:D1").Font.Color = rgb("#1F4E79")
    ws.Rows(1).RowHeight = 30

    ws.Cells(2, 1).Value = "A 列为内部参数名（请勿改名）；B 列为值；C 列为含义；D 列为作用域。"
    ws.Range("A2:D2").Merge()
    ws.Cells(2, 1).Font.Size = 9
    ws.Cells(2, 1).Font.Color = rgb("#7F7F7F")

    headers = ("参数名（勿改）", "值", "含义", "作用域")
    write_table(ws, 3, 1, [headers])
    style_header(ws, 1, 3, 4)

    rows = [(k, v, d, s) for (k, v, d, s) in CONFIG_ROWS]
    rows += [(k, v, d, "维度") for (k, v, d) in DIM_SWITCHES]
    write_table(ws, CFG_DATA_START, 1, rows)

    # 维度开关区块加浅色底
    dim_start = CFG_DATA_START + len(CONFIG_ROWS)
    ws.Range("A%d:D%d" % (dim_start, dim_start + len(DIM_SWITCHES) - 1)).Interior.Color = rgb("#FFF2CC")

    ws.Columns(1).ColumnWidth = 26
    ws.Columns(2).ColumnWidth = 20
    ws.Columns(3).ColumnWidth = 78
    ws.Columns(4).ColumnWidth = 10
    ws.Range("A3:D%d" % (CFG_DATA_START + len(rows) - 1)).Font.Name = "微软雅黑"
    ws.Range("A3:D%d" % (CFG_DATA_START + len(rows) - 1)).Font.Size = 10
    ws.Range("C4:C%d" % (CFG_DATA_START + len(rows) - 1)).WrapText = True
    ws.Range("B4:B%d" % (CFG_DATA_START + len(rows) - 1)).HorizontalAlignment = 2


def build_lexicon(wb) -> None:
    ws = wb.Sheets("词表")
    ws.Cells(1, 1).Value = "词表（可自由增删行；优先级数字越小越优先）"
    ws.Range("A1:H1").Merge()
    ws.Range("A1:H1").Font.Name = "微软雅黑"
    ws.Range("A1:H1").Font.Size = 15
    ws.Range("A1:H1").Font.Bold = True
    ws.Range("A1:H1").Font.Color = rgb("#1F4E79")
    ws.Rows(1).RowHeight = 30

    write_table(ws, 2, 1, LEX_ROWS)
    style_header(ws, 2, 2, 8)

    last = 2 + len(LEX_ROWS) - 1
    ws.Columns(1).ColumnWidth = 14
    ws.Columns(2).ColumnWidth = 16
    ws.Columns(3).ColumnWidth = 10
    ws.Columns(4).ColumnWidth = 9
    ws.Columns(5).ColumnWidth = 10
    ws.Columns(6).ColumnWidth = 8
    ws.Columns(7).ColumnWidth = 9
    ws.Columns(8).ColumnWidth = 40
    ws.Range("A2:H%d" % last).Font.Name = "微软雅黑"
    ws.Range("A2:H%d" % last).Font.Size = 10
    ws.Range("C3:C%d" % last).HorizontalAlignment = 2
    ws.Range("D3:D%d" % last).HorizontalAlignment = 2
    ws.Range("F3:F%d" % last).HorizontalAlignment = 2
    # 颜色示例：给颜色单元格填上实际颜色
    for r in range(3, last + 1):
        hx = str(ws.Cells(r, 3).Value or "")
        if len(hx) == 7 and hx.startswith("#"):
            ws.Cells(r, 3).Interior.Color = rgb(hx)
            ws.Cells(r, 3).Font.Color = 0xFFFFFF
            ws.Cells(r, 3).Font.Bold = True


def style_header(ws, row1: int, row2: int, cols: int) -> None:
    rng = ws.Range(ws.Cells(row1, 1), ws.Cells(row2, cols))
    rng.Font.Name = "微软雅黑"
    rng.Font.Bold = True
    rng.Font.Color = 0xFFFFFF
    rng.Interior.Color = rgb("#1F4E79")
    rng.HorizontalAlignment = 2
    rng.VerticalAlignment = -4160
    for r in range(row1, row2 + 1):
        ws.Rows(r).RowHeight = 24


def build_results_shell(wb) -> None:
    for name in ("逐句结果", "汇总统计", "图表数据", "上色预览", "词频Top", "运行日志"):
        ws = wb.Sheets(name)
        ws.Cells.Clear()
        ws.Cells.Font.Name = "微软雅黑"
        ws.Cells.Font.Size = 10

    ws = wb.Sheets("逐句结果")
    headers = ("序号", "段号", "段内句号", "原句", "字数", "命中维度", "命中词",
               "命中次数", "主维度", "主色(HEX)", "上色状态", "着色片段数", "备注")
    write_table(ws, 1, 1, [headers])
    style_header(ws, 1, 1, 13)
    ws.Columns(4).ColumnWidth = 90
    ws.Columns(4).WrapText = False

    ws = wb.Sheets("上色预览")
    write_table(ws, 1, 1, [("编号", "正文（字符级着色）", "主维度", "上色状态")])
    style_header(ws, 1, 1, 4)
    ws.Columns(2).ColumnWidth = 150
    ws.Columns(2).WrapText = True

    ws = wb.Sheets("词频Top")
    write_table(ws, 1, 1, [("排名", "词", "次数", "维度")])
    style_header(ws, 1, 1, 4)

    ws = wb.Sheets("运行日志")
    write_table(ws, 1, 1, [("时间", "阶段", "级别", "信息")])
    style_header(ws, 1, 1, 4)
    ws.Columns(1).ColumnWidth = 20
    ws.Columns(2).ColumnWidth = 12
    ws.Columns(3).ColumnWidth = 8
    ws.Columns(4).ColumnWidth = 100

    ws = wb.Sheets("图表")
    ws.Cells.Clear()
    ws.Range("A1").Value = "图表区域（运行「一键分析」后自动生成）"
    ws.Range("A1").Font.Name = "微软雅黑"
    ws.Range("A1").Font.Size = 10
    ws.Range("A1").Font.Color = rgb("#7F7F7F")

    ws = wb.Sheets("汇总统计")
    ws.Cells.Clear()
    ws.Range("A1").Value = "点击「一键分析」生成汇总统计。"
    ws.Range("A1").Font.Name = "微软雅黑"
    ws.Range("A1").Font.Size = 11
    ws.Range("A1").Font.Color = rgb("#7F7F7F")


def build_sample_sheet(wb) -> None:
    ws = wb.Sheets("示例原文")
    ws.Cells(1, 1).Value = "示例原文（隐藏表，仅用于「载入示例」）"
    for i, para in enumerate(SAMPLE):
        ws.Cells(2 + i, 1).Value = para
    ws.Columns(1).ColumnWidth = 120
    ws.Range("A2:A%d" % (1 + len(SAMPLE))).WrapText = True
    ws.Visible = 2  # very hidden


def import_modules(wb) -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="colortxt_bas_"))
    imported = []
    try:
        for f in sorted(SRC_DIR.glob("*.bas")):
            text = f.read_text(encoding="utf-8")
            tmp_path = tmp_dir / f.name
            tmp_path.write_text(text, encoding="gbk")
            wb.VBProject.VBComponents.Import(str(tmp_path))
            imported.append(f.name)
        log("已导入模块： " + ", ".join(imported))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def export_modules(wb) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for old in EXPORT_DIR.glob("*.bas"):
        old.unlink()
    count = 0
    for comp in wb.VBProject.VBComponents:
        if comp.Type == 1:  # vbext_ct_StdModule
            path = EXPORT_DIR / (comp.Name + ".bas")
            comp.Export(str(path))
            count += 1
    log("已从工作簿导出 %d 个标准模块到 %s" % (count, EXPORT_DIR))


def set_access_vbom(xl_version: str, enable: bool, old_value):
    import winreg
    parts = xl_version.split(".")
    key = r"Software\Microsoft\Office\%s.%s\Excel\Security" % (parts[0], parts[1] if len(parts) > 1 else "0")
    if enable:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, "AccessVBOM", 0, winreg.REG_DWORD, 1)
        return old_value
    # 恢复
    try:
        if old_value is None:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, "AccessVBOM")
        else:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "AccessVBOM", 0, winreg.REG_DWORD, old_value)
    except FileNotFoundError:
        pass
    return old_value


def read_old_access_vbom(xl_version: str):
    import winreg
    parts = xl_version.split(".")
    key = r"Software\Microsoft\Office\%s.%s\Excel\Security" % (parts[0], parts[1] if len(parts) > 1 else "0")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            v, _ = winreg.QueryValueEx(k, "AccessVBOM")
            return v
    except FileNotFoundError:
        return None


def main() -> int:
    if not SRC_DIR.exists():
        log("缺少 VBA源码 目录")
        return 1
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AutomationSecurity = 1  # 允许宏运行（仅本次自动化会话）
    xl_version = xl.Version
    old_vbom = read_old_access_vbom(xl_version)
    set_access_vbom(xl_version, True, old_vbom)

    wb = None
    try:
        wb = xl.Workbooks.Add()
        build_structure(wb)
        build_help(wb)
        build_input(wb)
        build_config(wb)
        build_lexicon(wb)
        build_results_shell(wb)
        build_sample_sheet(wb)

        wb.Sheets("使用说明").Activate()
        xl.ActiveWindow.DisplayGridlines = False
        xl.ActiveWindow.Zoom = 100

        import_modules(wb)

        log("保存为 xlsm ...")
        wb.SaveAs(str(OUT_FILE), FileFormat=52)

        log("运行一键分析（样例文本）...")
        t0 = time.time()
        xl.Run("RunFullAnalysis")
        elapsed = time.time() - t0
        log("宏执行完成，外部计时 %.2f 秒" % elapsed)

        report = xl.Run("MainSelfCheck")
        log("自检： " + str(report))

        logrow = wb.Sheets("运行日志").Cells(wb.Sheets("运行日志").Rows.Count, 1).End(-4162).Row
        vals = wb.Sheets("运行日志").Range("A1:D%d" % logrow).Value
        out_log = []
        for row in vals:
            out_log.append(" | ".join("" if v is None else str(v) for v in row))
        (ROOT / "build_run_log.txt").write_text("\n".join(out_log), encoding="utf-8")

        export_modules(wb)
        wb.Sheets("使用说明").Activate()
        wb.Save()
        log("工作簿已保存： %s" % OUT_FILE)
        return 0
    except Exception as e:
        import traceback
        log("生成失败： %r" % e)
        log(traceback.format_exc())
        try:
            if wb is not None:
                wb.Close(SaveChanges=False)
        except Exception:
            pass
        return 2
    finally:
        try:
            xl.Quit()
        except Exception:
            pass
        set_access_vbom(xl_version, False, old_vbom)


if __name__ == "__main__":
    sys.exit(main())
