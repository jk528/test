#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用TXT文件读取模块 - 自动检测编码并读取
支持: ANSI(GBK) / UTF-8(含BOM) / UTF-8(无BOM) / UTF-16LE / UTF-16BE

用法:
    from readtxt_universal import read_text_auto, detect_encoding
    content = read_text_auto("红楼梦.txt")
    enc = detect_encoding("红楼梦.txt")  # 返回 "ANSI" / "UTF-8 BOM" / "UTF-8" / "UTF-16LE" / "UTF-16BE"
"""
import os


def detect_encoding_bytes(file_bytes):
    """检测字节数组的编码

    逻辑:
      1. BOM 检测: FF FE = UTF-16LE; FE FF = UTF-16BE; EF BB BF = UTF-8 BOM
      2. 无BOM时扫描前100字节，检查高位字节模式:
         - 3字节序列 E0~EF + 80~BF + 80~BF -> UTF-8
         - 4字节序列 F0~F7 + 80~BF + 80~BF + 80~BF -> UTF-8
         - 其他高位字节 -> ANSI
      3. 全ASCII（无高位字节）-> ANSI（兼容纯英文）
    """
    if not file_bytes:
        return "ANSI"

    # BOM 检测
    if len(file_bytes) >= 2:
        if file_bytes[0] == 0xFF and file_bytes[1] == 0xFE:
            return "UTF-16LE"
        if file_bytes[0] == 0xFE and file_bytes[1] == 0xFF:
            return "UTF-16BE"
    if len(file_bytes) >= 3:
        if file_bytes[0] == 0xEF and file_bytes[1] == 0xBB and file_bytes[2] == 0xBF:
            return "UTF-8 BOM"

    # 无BOM: 扫描字节模式判断 UTF-8 vs ANSI
    scan_len = min(len(file_bytes), 100)
    for i in range(scan_len):
        b1 = file_bytes[i]
        if b1 > 0x7F:
            # 3字节UTF-8序列: E0~EF + 80~BF + 80~BF
            if (b1 & 0xF0) == 0xE0:
                if i + 2 < len(file_bytes):
                    if (file_bytes[i + 1] & 0xC0) == 0x80 and \
                       (file_bytes[i + 2] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 4字节UTF-8序列: F0~F7 + 80~BF + 80~BF + 80~BF
            if (b1 & 0xF8) == 0xF0:
                if i + 3 < len(file_bytes):
                    if (file_bytes[i + 1] & 0xC0) == 0x80 and \
                       (file_bytes[i + 2] & 0xC0) == 0x80 and \
                       (file_bytes[i + 3] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 2字节UTF-8序列: C0~DF + 80~BF
            if (b1 & 0xE0) == 0xC0:
                if i + 1 < len(file_bytes):
                    if (file_bytes[i + 1] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 高位字节不符合UTF-8前导字节模式 -> ANSI
            return "ANSI"

    return "ANSI"


def detect_encoding(file_path):
    """检测TXT文件编码，返回编码名称字符串"""
    with open(file_path, "rb") as f:
        raw = f.read()
    return detect_encoding_bytes(raw)


_ENCODING_MAP = {
    "ANSI": "gbk",
    "UTF-8 BOM": "utf-8-sig",
    "UTF-8": "utf-8",
    "UTF-16LE": "utf-16",
    "UTF-16BE": "utf-16",
}


def read_text_auto(file_path):
    """自动检测编码并读取TXT文件全文

    支持: ANSI(GBK) / UTF-8(含/不含BOM) / UTF-16LE / UTF-16BE
    """
    enc = detect_encoding(file_path)
    py_enc = _ENCODING_MAP.get(enc, "utf-8")
    with open(file_path, "r", encoding=py_enc) as f:
        return f.read()


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
        print("用法: python readtxt_universal.py <文件路径>")
        sys.exit(1)
    path = sys.argv[1]
    enc = detect_encoding(path)
    print("编码: %s" % enc)
    content = read_text_auto(path)
    print("字符数: %d" % len(content))
    print("前100字: %s" % content[:100])
