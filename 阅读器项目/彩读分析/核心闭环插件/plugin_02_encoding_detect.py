# -*- coding: utf-8 -*-
"""
插件 02 · 编码识别（核心闭环第 2 环）
================================================

【对应 VBA】DetectEncoding（Open For Binary + 手动 BOM 检测 + 启发式）
【复盘定位】文件导入的前置探针。编码不对，后面的切行/章节/上色全盘皆错，
            所以复盘把它单独列为一环，强调「三级策略」而非单一手段。

【实现逻辑拆解】
  输入    ：原始字节流（bytes）或文件路径
  处理    ：
     1. BOM 头检测   —— 先看文件头有没有 UTF-8/16/32 的字节序标记（最可靠）；
     2. 统计检测     —— chardet 对前 100KB 采样，给编码与置信度（可选依赖）；
     3. 中文启发式   —— UTF-8 严格解码试探；失败且存在 >= 0x80 字节则判 GBK
                        （中文环境 GBK/GB2312 的兜底）。
  输出    ：EncodingResult{ encoding, confidence, method }
  关键差异：VBA 只靠 BOM + 启发式，Python 引入 chardet 后准确率更高、
            且能给出置信度（对应复盘「可观测优先」原则）。

【纯逻辑说明】只做字节流判定，无 GUI，可独立单测；命令行可直接探测任意文件。

【可独立运行】
  python plugin_02_encoding_detect.py               # 内置多编码样例演示
  python plugin_02_encoding_detect.py <文件路径>     # 探测真实文件编码
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass


_BOMS = (
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
)


@dataclass
class EncodingResult:
    encoding: str
    confidence: float = 1.0
    method: str = "bom"          # bom | chardet | utf8 | gbk-heuristic | ascii


def detect_from_bytes(raw: bytes) -> EncodingResult:
    """三级编码识别的完整实现，返回带置信度与方法来源的结果。"""
    # 第 1 级：BOM 头
    for bom, enc in _BOMS:
        if raw.startswith(bom):
            return EncodingResult(enc, 1.0, "bom")

    # 第 2 级：chardet 统计检测（可选依赖）
    try:
        import chardet
        det = chardet.detect(raw[:100_000])
        enc = (det or {}).get("encoding")
        conf = (det or {}).get("confidence") or 0.0
        if enc:
            return EncodingResult(enc, round(conf, 2), "chardet")
    except Exception:
        pass

    # 第 3 级：UTF-8 严格试探
    try:
        raw.decode("utf-8")
        return EncodingResult("utf-8", 1.0, "utf8")
    except UnicodeDecodeError:
        pass

    # 中文 ANSI 启发式：含高位字节则判定 GBK
    if any(b >= 0x80 for b in raw):
        return EncodingResult("gbk", 0.7, "gbk-heuristic")
    return EncodingResult("ascii", 1.0, "ascii")


def detect_file(file_path: str) -> EncodingResult:
    """探测文件的编码（只读前 100KB 采样，避免大文件全量读入）。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    with open(file_path, "rb") as f:
        return detect_from_bytes(f.read(100_000))


# ---------------------------------------------------------------------------
# 内置演示
# ---------------------------------------------------------------------------
def _setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _demo():
    _setup_console()
    samples = {
        "UTF-8（无 BOM）": "红楼梦第一回 甄士隐梦幻识通灵".encode("utf-8"),
        "UTF-8（带 BOM）": b"\xef\xbb\xbf" + "红楼梦第一回".encode("utf-8"),
        "UTF-16 LE": "红楼梦第一回".encode("utf-16-le"),
        "GBK（中文 ANSI）": "红楼梦第一回 甄士隐梦幻识通灵".encode("gbk"),
        "ASCII 纯英文": b"hello world, chapter 01",
    }
    for name, raw in samples.items():
        r = detect_from_bytes(raw)
        print(f"[{name:16}] -> {r.encoding:12} 置信度={r.confidence:<5} 方法={r.method}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _setup_console()
        r = detect_file(sys.argv[1])
        print(f"文件={sys.argv[1]} 编码={r.encoding} 置信度={r.confidence} 方法={r.method}")
    else:
        _demo()