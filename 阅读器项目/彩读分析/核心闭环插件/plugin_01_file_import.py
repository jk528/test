# -*- coding: utf-8 -*-
"""
插件 01 · 文件导入（核心闭环第 1 环）
================================================

【对应 VBA】READ_TXTTOEXCEL.bas（ImportTextDataToSheet / ConvertTextTo2DArray）
【复盘定位】核心闭环链路的入口：文件导入 → 编码识别 → 章节识别 → 内容上色
            → 目录跳转 → 书签进度。没有这一层，产品不成立。

【实现逻辑拆解】
  输入    ：本地文件路径（TXT / MD / DOCX / XLSX）
  处理    ：
     1. 按扩展名分发到对应 reader（txt/md → 纯读取；docx → python-docx；
        xlsx → openpyxl）；
     2. TXT 先走编码识别（三级策略，精化版见 plugin_02），再一次性 read()
        读入——替代 VBA「逐行 Line Input + & 拼接」（后者 10MB 文件要 15~30 秒，
        Python 一次性读取 + split 约 0.3~1 秒，快 15~30 倍）；
     3. 按换行切分、过滤空行，得到「文本行列表」（对应 VBA 数据源 A 列）；
     4. DOCX / XLSX 走可选三方库，未安装时抛出带安装提示的明确错误。
  输出    ：TextContent{ lines, encoding, total_lines, source_path }
  关键差异：一次性读取替代逐行拼接；纯库解析替代启动 Word/Excel 进程。

【纯逻辑说明】
  本模块只负责「把文件变成文本行」，不碰任何 GUI。上层（PyQt6 / Monaco）
  拿到 lines 后自行渲染，符合 core/gui 分离原则，可独立单测。

【可独立运行】
  python plugin_01_file_import.py                 # 用内置样章 + GBK 临时文件演示
  python plugin_01_file_import.py <文件路径>      # 导入真实文件并打印前 10 行
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 数据模型（对应 Python实现计划案 models/text_content.py）
# ---------------------------------------------------------------------------
@dataclass
class TextContent:
    lines: list[str]            # 文本行（对应数据源 A 列）
    encoding: str = "utf-8"     # 探测到的编码
    source_path: str = ""       # 源文件路径
    total_lines: int = 0        # 总行数（自动计算）

    def __post_init__(self):
        self.total_lines = len(self.lines)


# ---------------------------------------------------------------------------
# 编码识别（三级策略简版；完整版见 plugin_02_encoding_detect.py）
# ---------------------------------------------------------------------------
_BOMS = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


def detect_encoding(raw: bytes) -> str:
    """三级策略：BOM 头 → chardet 统计检测 → UTF-8 试探 + GBK 启发式。"""
    # 第 1 级：BOM 头（对应 VBA 的 Open For Binary 手动 BOM 检测）
    for bom, enc in _BOMS:
        if raw.startswith(bom):
            return enc
    # 第 2 级：chardet 统计检测（可选依赖，装了就最准）
    try:
        import chardet
        det = chardet.detect(raw[:100_000])
        if det and det.get("encoding"):
            return det["encoding"]
    except Exception:
        pass
    # 第 3 级：UTF-8 严格试探 + 中文 ANSI 启发式（GBK/GB2312 兜底）
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    if any(b >= 0x80 for b in raw):
        return "gbk"
    return "ascii"


# ---------------------------------------------------------------------------
# 各格式 reader
# ---------------------------------------------------------------------------
def _read_txt(file_path: str) -> TextContent:
    with open(file_path, "rb") as f:
        raw = f.read()
    enc = detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return TextContent(lines=lines, encoding=enc, source_path=file_path)


def _read_docx(file_path: str) -> TextContent:
    try:
        from docx import Document
    except ImportError as e:
        raise RuntimeError("读取 DOCX 需要 python-docx：pip install python-docx") from e
    doc = Document(file_path)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return TextContent(lines=lines, encoding="utf-8", source_path=file_path)


def _read_xlsx(file_path: str, sheet_name: str | None = None) -> TextContent:
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("读取 XLSX 需要 openpyxl：pip install openpyxl") from e
    wb = openpyxl.load_workbook(file_path, read_only=True)
    try:
        ws = wb[sheet_name] if sheet_name else wb.active
        lines = [str(cell.value) for row in ws.iter_rows()
                 for cell in row if cell.value is not None]
    finally:
        wb.close()
    return TextContent(lines=lines, encoding="utf-8", source_path=file_path)


_READERS = {
    ".txt": _read_txt,
    ".md": _read_txt,
    ".docx": _read_docx,
    ".xlsx": _read_xlsx,
}


def import_file(file_path: str, sheet_name: str | None = None) -> TextContent:
    """按扩展名分发读取。核心闭环第 1 环的唯一对外入口。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    reader = _READERS.get(ext)
    if reader is None:
        raise ValueError(f"不支持的文件类型：{ext}")
    if ext == ".xlsx":
        return reader(file_path, sheet_name)
    return reader(file_path)


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
_DEMO_TEXT = """第一回 甄士隐梦幻识通灵

此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。

列位看官，你道此书从何而来？说起根由虽近荒唐，细按则深有趣味。

第二回 贾夫人仙逝扬州城

原来这贾夫人，乃荣国府贾政之妻王氏。
"""


def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    # 1) 用手写中文生成一个 GBK 编码的临时 TXT，演示「GBK 落盘 → 识别导入」
    sample_gbk = "红楼梦 第一回\n甄士隐梦幻识通灵\n此开卷第一回也。\n"
    tmp = os.path.join(tempfile.gettempdir(), "colortxt_demo_sample.txt")
    with open(tmp, "wb") as f:
        f.write(sample_gbk.encode("gbk"))

    content = import_file(tmp)
    print(f"[文件导入] 路径      : {content.source_path}")
    print(f"[文件导入] 探测编码  : {content.encoding}")
    print(f"[文件导入] 总行数    : {content.total_lines}")
    for i, ln in enumerate(content.lines[:5], 1):
        print(f"    A{i}: {ln}")

    # 2) 内置样章（内存 UTF-8）直接切行
    lines = [ln for ln in _DEMO_TEXT.splitlines() if ln.strip()]
    print(f"\n[内置样章] 共 {len(lines)} 行，前 3 行：")
    for ln in lines[:3]:
        print(f"    {ln}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _setup_console()
        path = sys.argv[1]
        c = import_file(path)
        print(f"路径={c.source_path} 编码={c.encoding} 行数={c.total_lines}")
        for ln in c.lines[:10]:
            print(ln)
    else:
        _demo()