#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用TXT文件读取模块 - 自动检测编码并读取
支持: ANSI(GBK) / UTF-8(含BOM) / UTF-8(无BOM) / UTF-16LE / UTF-16BE / GB18030 等

检测策略（优先级从高到低）:
  1. BOM 快速检测: UTF-16LE/BE、UTF-8 BOM（确定性100%）
  2. charset-normalizer 统计分析（精度最高，需安装 pip install charset-normalizer）
  3. 手动 UTF-8 字节模式扫描（兜底，无需第三方库）

用法:
    from readtxt_universal import read_text_auto, detect_encoding
    content = read_text_auto("红楼梦.txt")
    enc = detect_encoding("红楼梦.txt")  # 返回编码名称，如 "UTF-8" / "GBK" / "UTF-16LE"
"""
import os

try:
    from charset_normalizer import from_bytes as _cn_from_bytes
    _HAS_CHARSET_NORMALIZER = True
except ImportError:
    _HAS_CHARSET_NORMALIZER = False


# ---------------------------------------------------------------------------
# 第1层：BOM 快速检测（确定性100%，零依赖，最高优先级）
# ---------------------------------------------------------------------------
_BOM_MAP = [
    (b"\xff\xfe", "UTF-16LE"),
    (b"\xfe\xff", "UTF-16BE"),
    (b"\xef\xbb\xbf", "UTF-8"),
    (b"\x2b\x2f\x76", "UTF-7"),
]


def _detect_by_bom(raw):
    """通过 BOM 头检测编码，返回编码名或 None"""
    for bom, enc in _BOM_MAP:
        if raw.startswith(bom):
            return enc
    return None


# ---------------------------------------------------------------------------
# 第2层：charset-normalizer 统计分析（最佳实践，精度最高）
# ---------------------------------------------------------------------------
def _detect_by_charset_normalizer(raw):
    """使用 charset-normalizer 统计分析编码"""
    if not _HAS_CHARSET_NORMALIZER:
        return None
    result = _cn_from_bytes(raw).best()
    if result is None or result.encoding is None:
        return None
    enc = result.encoding.lower().replace("-", "_")
    # charset-normalizer 可能返回 "utf_8" / "gbk" / "gb18030" / "big5" 等
    # 统一映射为 Python open() 支持的标准编码名
    _ALIAS = {
        "utf_8": "utf-8",
        "utf_16": "utf-16",
        "gb_2312": "gbk",
        "gb2312": "gbk",
        "iso_8859_1": "latin-1",
    }
    return _ALIAS.get(enc, enc)


# ---------------------------------------------------------------------------
# 第3层：手动 UTF-8 字节模式扫描（兜底，无需第三方库）
# ---------------------------------------------------------------------------
def _detect_by_utf8_scan(raw):
    """通过 UTF-8 多字节序列模式扫描判断 UTF-8 vs ANSI"""
    scan_len = min(len(raw), 1024)
    i = 0
    while i < scan_len:
        b1 = raw[i]
        if b1 <= 0x7F:
            i += 1
            continue
        # 尝试匹配 UTF-8 多字节序列
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


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
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


def read_text_auto(file_path):
    """自动检测编码并读取TXT文件全文

    支持: UTF-8(含/不含BOM) / UTF-16LE / UTF-16BE / GBK / GB18030 / Big5 等
    """
    with open(file_path, "rb") as f:
        raw = f.read()
    enc = detect_encoding_bytes(raw)
    # BOM 编码用 Python 内置 codec 自动剥离 BOM
    _BOM_CODEC = {"UTF-16LE": "utf-16", "UTF-16BE": "utf-16", "UTF-8": "utf-8-sig"}
    py_enc = _BOM_CODEC.get(enc, enc)
    try:
        return raw.decode(py_enc)
    except (UnicodeDecodeError, LookupError):
        # 检测失败时尝试常见编码列表
        for fallback in ("utf-8", "gbk", "gb18030", "big5", "latin-1"):
            try:
                return raw.decode(fallback)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")


def write_text_utf8_nobom(file_path, text):
    """写入UTF-8文本（无BOM）"""
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_text_ansi(file_path, text):
    """写入ANSI编码文本（GBK）"""
    with open(file_path, "w", encoding="gbk", newline="") as f:
        f.write(text)


def write_text_utf8_bom(file_path, text):
    """写入UTF-8文本（含BOM）"""
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python readtxt_universal.py <文件路径> [文件路径2 ...]")
        sys.exit(1)
    for path in sys.argv[1:]:
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
