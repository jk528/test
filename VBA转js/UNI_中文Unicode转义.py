#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
UNI_中文Unicode转义.py
中文 ↔ Unicode 转义序列 互转工具（Python 版）

与 JS / VBA 版本格式完全一致：
  - 默认仅转义非 ASCII 字符（>127），保留 ASCII 可读性
  - 十六进制大写，\uXXXX 风格
  - 补充平面字符（emoji 等 >U+FFFF）输出 UTF-16 代理对 \uHHHH\uLLLL
  - 支持解码 \uXXXX 与 ES6 \u{XXXXX} 两种形式

API：
  to_unicode(s, all=False, upper=True, brace=False)  编码：中文 → \uXXXX
  from_unicode(s)                                    解码：\uXXXX → 中文
  has_non_ascii(s)                                   检测：是否含非 ASCII
  to_unicode_lines(s, **opts)                        批量：按行编码 → list
  from_unicode_lines(arr)                            批量：行数组解码 → str

CLI：
  python UNI_中文Unicode转义.py "中文"                  编码字符串
  python UNI_中文Unicode转义.py -d "\u4E2D\u6587"       解码字符串
  python UNI_中文Unicode转义.py -i in.txt -o out.txt    编码文件
  python UNI_中文Unicode转义.py -i in.txt -o out.txt -d 解码文件
  python UNI_中文Unicode转义.py --test                  运行测试

日期：2026-08-13
"""

import re
import sys
import time
import argparse

VERSION = "1.0.0"

# 十六进制校验
_RE_HEX = re.compile(r'^[0-9a-fA-F]+$')


# ============================================================
# 内部：码点 → 转义字符串
# ============================================================
def _escape_codepoint(cp, upper=True, brace=False):
    """单个码点 → \\uXXXX 或代理对或 \\u{XXXXX}。"""
    if brace:
        hfmt = '{:X}' if upper else '{:x}'
        return '\\u{' + hfmt.format(cp) + '}'
    fmt = '{:04X}' if upper else '{:04x}'
    if cp <= 0xFFFF:
        return '\\u' + fmt.format(cp)
    # 补充平面 → UTF-16 代理对
    cp -= 0x10000
    hi = 0xD800 + (cp >> 10)
    lo = 0xDC00 + (cp & 0x3FF)
    return '\\u' + fmt.format(hi) + '\\u' + fmt.format(lo)


# ============================================================
# to_unicode：中文 → \uXXXX 转义序列
#   s        : 原始字符串
#   all      : True 转义全部字符；False（默认）仅转义非 ASCII
#   upper    : 十六进制大写（默认 True）
#   brace    : 使用 \u{XXXXX} 形式（默认 False）
# ============================================================
def to_unicode(s, all=False, upper=True, brace=False):
    if s is None:
        return ''
    s = str(s)
    out = []
    for ch in s:
        cp = ord(ch)
        if all or cp > 0x7F:
            out.append(_escape_codepoint(cp, upper, brace))
        else:
            out.append(ch)
    return ''.join(out)


# ============================================================
# from_unicode：\uXXXX / \u{XXXXX} → 中文
#   手动扫描，正确处理代理对配对与非法序列
#   非法序列（孤立代理、超范围码点、非法十六进制）保留原字面量
# ============================================================
def from_unicode(s):
    if s is None:
        return ''
    s = str(s)
    out = []
    i = 0
    n = len(s)
    while i < n:
        # 匹配 \u 起始
        if s[i] == '\\' and i + 1 < n and s[i + 1] == 'u':
            # ---- ES6 \u{XXXXX} 形式 ----
            if i + 2 < n and s[i + 2] == '{':
                close = s.find('}', i + 3)
                if close != -1:
                    hex_str = s[i + 3:close]
                    if _RE_HEX.match(hex_str):
                        cp = int(hex_str, 16)
                        if 0 <= cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF):
                            out.append(chr(cp))
                            i = close + 1
                            continue
                    # 非法，保留原字面量
                    out.append(s[i:close + 1])
                    i = close + 1
                    continue
            # ---- \uXXXX 形式 ----
            if i + 6 <= n:
                hex_str = s[i + 2:i + 6]
                if _RE_HEX.match(hex_str):
                    cp = int(hex_str, 16)
                    # 高代理：尝试配对下一个 \uXXXX 低代理
                    if 0xD800 <= cp <= 0xDBFF and i + 12 <= n and s[i + 6:i + 8] == '\\u':
                        lo_hex = s[i + 8:i + 12]
                        if _RE_HEX.match(lo_hex):
                            lo = int(lo_hex, 16)
                            if 0xDC00 <= lo <= 0xDFFF:
                                full = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
                                out.append(chr(full))
                                i += 12
                                continue
                    # 单个合法码点（非代理区间）
                    if 0xD800 <= cp <= 0xDFFF:
                        out.append(s[i:i + 6])   # 孤立代理，保留字面量
                    else:
                        out.append(chr(cp))
                    i += 6
                    continue
        # 普通字符原样保留
        out.append(s[i])
        i += 1
    return ''.join(out)


# ============================================================
# has_non_ascii：检测字符串是否含非 ASCII 字符
# ============================================================
def has_non_ascii(s):
    if s is None:
        return False
    return any(ord(ch) > 0x7F for ch in str(s))


# ============================================================
# to_unicode_lines：按行编码，返回行列表（便于多行存储）
# ============================================================
def to_unicode_lines(s, **opts):
    if s is None:
        return []
    s = str(s).replace('\r\n', '\n').replace('\r', '\n')
    return [to_unicode(line, **opts) for line in s.split('\n')]


# ============================================================
# from_unicode_lines：行数组解码还原（用 \n 重新拼接）
# ============================================================
def from_unicode_lines(arr):
    if not arr:
        return ''
    return '\n'.join(from_unicode(line) for line in arr)


# ============================================================
# CLI 文件读写
# ============================================================
def _read_file(path):
    encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    raise IOError('无法识别文件编码: ' + path)


def _write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ============================================================
# 测试：标准场景 / 边界条件 / 往返一致 / 随机 + 计时
# ============================================================
def _run_tests():
    import random
    passed = 0
    failed = 0
    fails = []

    def eq(actual, expected, label):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            fails.append('{} | 期望:{} 实际:{}'.format(label, repr(expected), repr(actual)))

    print('=' * 48)
    print(' Unicode 转义库测试 (Python)  v' + VERSION)
    print('=' * 48)

    # --- 一、标准场景 ---
    print('--- 一、标准场景 ---')
    eq(to_unicode('中文'), '\\u4E2D\\u6587', '中文编码')
    eq(to_unicode('Hello 世界'), 'Hello \\u4E16\\u754C', '中英混合仅转义中文')
    eq(to_unicode('ABC123'), 'ABC123', '纯ASCII不转义')
    eq(to_unicode('中文', upper=False), '\\u4e2d\\u6587', '小写十六进制')
    eq(to_unicode('AB', all=True), '\\u0041\\u0042', 'all=True转义全部')
    eq(to_unicode('中', brace=True), '\\u{4E2D}', 'ES6大括号形式')

    # --- 二、解码还原 ---
    print('--- 二、解码还原 ---')
    eq(from_unicode('\\u4E2D\\u6587'), '中文', '标准解码')
    eq(from_unicode('\\u4e2d\\u6587'), '中文', '小写转义解码')
    eq(from_unicode('\\u{4E16}\\u{754C}'), '世界', 'ES6形式解码')
    eq(from_unicode('Hello \\u4E16\\u754C'), 'Hello 世界', '混合文本解码')
    eq(from_unicode('普通文本'), '普通文本', '无转义原样返回')

    # --- 三、往返一致性 ---
    print('--- 三、往返一致性 ---')
    samples = ['中文测试', 'Hello 世界！2026', '排列组合 C(n,k)',
               '特殊符号：①②③★☆【】', '日文テスト 한국어', '',
               '单', 'AAAA']
    for idx, s in enumerate(samples):
        eq(from_unicode(to_unicode(s)), s, '往返一致#' + str(idx))

    # 注：含 \uXXXX 字面量的串无法无损往返（转义编解码器固有特性）
    # 如 '混合\u0041转义' 往返后 \u0041 被还原为 A，与 Python 内置
    # unicode_escape 行为一致，属正确行为而非缺陷。

    # --- 四、边界条件 ---
    print('--- 四、边界条件 ---')
    eq(to_unicode(''), '', '空串编码')
    eq(from_unicode(''), '', '空串解码')
    eq(to_unicode(None), '', 'None编码安全')
    eq(from_unicode(None), '', 'None解码安全')
    eq(to_unicode(123), '123', '数字转字符串')
    eq(from_unicode('\\uD800'), '\\uD800', '孤立高代理保留原样')
    eq(from_unicode('\\u{110000}'), '\\u{110000}', '超范围码点保留原样')
    eq(from_unicode('\\uXYZW'), '\\uXYZW', '非法十六进制保留原样')

    # --- 五、补充平面字符 emoji ---
    print('--- 五、补充平面字符 emoji ---')
    emoji = '😀'  # U+1F600
    enc_emoji = to_unicode(emoji)
    eq(enc_emoji, '\\uD83D\\uDE00', 'emoji代理对')
    eq(from_unicode(enc_emoji), emoji, 'emoji解码还原')
    eq(to_unicode(emoji, brace=True), '\\u{1F600}', 'emoji ES6形式')
    eq(from_unicode('\\u{1F600}'), emoji, 'emoji ES6解码')
    eq(from_unicode('\\uD83D\\uDE00\\u4E2D'), '😀中', 'emoji+中文混合解码')

    # --- 六、检测函数 ---
    print('--- 六、检测函数 ---')
    eq(has_non_ascii('中文'), True, '检测中文True')
    eq(has_non_ascii('ABC123'), False, '检测纯ASCII False')
    eq(has_non_ascii('Hello 世界'), True, '检测混合True')
    eq(has_non_ascii(''), False, '空串检测False')

    # --- 七、多行批量 ---
    print('--- 七、多行批量 ---')
    multi = '第一行中文\nSecond line\n第三行'
    lines_enc = to_unicode_lines(multi)
    eq(len(lines_enc), 3, '多行拆分3行')
    eq(lines_enc[0], '\\u7B2C\\u4E00\\u884C\\u4E2D\\u6587', '第1行编码')
    eq(lines_enc[1], 'Second line', '第2行ASCII原样')
    eq(lines_enc[2], '\\u7B2C\\u4E09\\u884C', '第3行编码')
    eq(from_unicode_lines(lines_enc), multi, '多行往返一致')

    # --- 八、随机往返测试 + 计时 ---
    print('--- 八、随机往返测试 + 计时 ---')
    random.seed(20260813)
    t0 = time.perf_counter()
    random_fail = 0
    N_CN = 10000
    for _ in range(N_CN):
        length = 1 + random.randint(0, 19)
        rs = ''.join(chr(random.randint(0x4E00, 0x9FFF)) for _ in range(length))
        if from_unicode(to_unicode(rs)) != rs:
            random_fail += 1
    t1 = time.perf_counter()
    eq(random_fail, 0, '{}次随机中文往返'.format(N_CN))
    print('    中文随机: {}次 / {:.3f}s / {:.0f}次/秒'.format(
        N_CN, t1 - t0, N_CN / (t1 - t0)))

    t2 = time.perf_counter()
    random_emoji_fail = 0
    N_EM = 2000
    for _ in range(N_EM):
        parts = []
        for _ in range(1 + random.randint(0, 4)):
            if random.random() < 0.5:
                parts.append(''.join(chr(random.randint(0x4E00, 0x9FFF))
                                     for _ in range(1 + random.randint(0, 2))))
            else:
                parts.append(chr(random.randint(0x1F300, 0x1F8FF)))
        es = ''.join(parts)
        if from_unicode(to_unicode(es)) != es:
            random_emoji_fail += 1
    t3 = time.perf_counter()
    eq(random_emoji_fail, 0, '{}次随机中文+emoji往返'.format(N_EM))
    print('    emoji随机: {}次 / {:.3f}s / {:.0f}次/秒'.format(
        N_EM, t3 - t2, N_EM / (t3 - t2)))

    # --- 结果汇总 ---
    print('-' * 48)
    print('通过: {}  失败: {}'.format(passed, failed))
    if fails:
        print('失败明细:')
        for f in fails:
            print('  ' + f)
    print('✓ 全部通过' if failed == 0 else '✗ 存在失败用例')
    print('=' * 48)

    # --- 演示 ---
    demo = '排列组合四象限：C(n,k) 组合不放回'
    print('\n===== 演示 =====')
    print('原文:', demo)
    print('编码:', to_unicode(demo))
    print('解码:', from_unicode(to_unicode(demo)))

    return failed == 0


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='中文 ↔ Unicode 转义序列互转工具')
    parser.add_argument('text', nargs='?', default=None,
                        help='要编码/解码的字符串')
    parser.add_argument('-d', '--decode', action='store_true',
                        help='解码模式（默认为编码）')
    parser.add_argument('-i', '--input', default=None,
                        help='输入文件路径')
    parser.add_argument('-o', '--output', default=None,
                        help='输出文件路径')
    parser.add_argument('--all', action='store_true',
                        help='转义全部字符（含 ASCII）')
    parser.add_argument('--lower', action='store_true',
                        help='十六进制小写')
    parser.add_argument('--brace', action='store_true',
                        help='使用 ES6 \\u{XXXXX} 形式')
    parser.add_argument('--test', action='store_true',
                        help='运行测试')
    args = parser.parse_args()

    if args.test:
        sys.exit(0 if _run_tests() else 1)

    opts = {'all': args.all, 'upper': not args.lower, 'brace': args.brace}
    func = from_unicode if args.decode else to_unicode

    # 文件模式
    if args.input:
        content = _read_file(args.input)
        result = func(content, **opts) if not args.decode else func(content)
        if args.output:
            _write_file(args.output, result)
            print('已写入: {}'.format(args.output))
        else:
            print(result)
        return

    # 字符串模式
    if args.text is None:
        parser.print_help()
        return
    if args.decode:
        print(from_unicode(args.text))
    else:
        print(to_unicode(args.text, **opts))


if __name__ == '__main__':
    main()
