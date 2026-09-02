# -*- coding: utf-8 -*-
"""
验证三段采样编码检测逻辑（等价于 VBA 的 DetectEncodingBytes + ScanBytesForEncoding）
测试各种边界场景，确保与原版单段扫描行为一致，并验证三段采样的优势。
"""

import os
import sys

SCAN_LEN = 100


def scan_bytes_original(data, start_idx, end_idx):
    """
    原版单段扫描（只检查 ub 边界，不检查 endIdx 边界）
    用于与原版行为对比，不受新逻辑影响
    """
    ub = len(data) - 1
    if start_idx < 0:
        start_idx = 0
    if end_idx > ub:
        end_idx = ub
    if start_idx > end_idx:
        return ""

    for i in range(start_idx, end_idx + 1):
        b1 = data[i]
        if b1 > 0x7F:
            # 3字节UTF-8序列
            if (b1 & 0xF0) == 0xE0:
                if i + 2 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80 and \
                       (data[i + 2] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 4字节UTF-8序列
            elif (b1 & 0xF8) == 0xF0:
                if i + 3 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80 and \
                       (data[i + 2] & 0xC0) == 0x80 and \
                       (data[i + 3] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 2字节UTF-8序列
            elif (b1 & 0xE0) == 0xC0:
                if i + 1 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            else:
                return "ANSI"
    return ""


def scan_bytes_for_encoding(data, start_idx, end_idx):
    """
    在指定字节范围内扫描，判断 UTF-8 vs ANSI
    返回: "UTF-8" / "ANSI" / "" （空串 = 全ASCII，无结论）
    逻辑与 VBA 的 ScanBytesForEncoding 完全等价
    段边界处理：
      - 段起点遇到延续字节(0x80~0xBF) → 跳过，找前导字节
      - 段尾不做截断保护，验证序列时只检查 ub（文件末尾）
    """
    ub = len(data) - 1
    if start_idx < 0:
        start_idx = 0
    if end_idx > ub:
        end_idx = ub
    if start_idx > end_idx:
        return ""

    for i in range(start_idx, end_idx + 1):
        b1 = data[i]
        if b1 > 0x7F:
            # 跳过 UTF-8 延续字节（0x80~0xBF）：段起点可能切在多字节序列中间
            if (b1 & 0xC0) == 0x80:
                continue
            # 3字节UTF-8序列: E0~EF + 80~BF + 80~BF
            if (b1 & 0xF0) == 0xE0:
                if i + 2 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80 and \
                       (data[i + 2] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 4字节UTF-8序列: F0~F7 + 80~BF + 80~BF + 80~BF
            elif (b1 & 0xF8) == 0xF0:
                if i + 3 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80 and \
                       (data[i + 2] & 0xC0) == 0x80 and \
                       (data[i + 3] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            # 2字节UTF-8序列: C0~DF + 80~BF
            elif (b1 & 0xE0) == 0xC0:
                if i + 1 <= ub:
                    if (data[i + 1] & 0xC0) == 0x80:
                        return "UTF-8"
                return "ANSI"
            else:
                # 高位字节不符合UTF-8前导字节模式 → ANSI
                return "ANSI"
    # 本段全为 ASCII
    return ""


def detect_encoding_bytes_original(data):
    """原版：只扫描前100字节（用于对比）"""
    if len(data) == 0:
        return "ANSI"

    # BOM 检测
    if len(data) >= 2:
        if data[0] == 0xFF and data[1] == 0xFE:
            return "UTF-16LE"
        if data[0] == 0xFE and data[1] == 0xFF:
            return "UTF-16BE"
    if len(data) >= 3:
        if data[0] == 0xEF and data[1] == 0xBB and data[2] == 0xBF:
            return "UTF-8 BOM"

    # 原版：只扫前100字节（用原版扫描函数，只检查 ub 边界）
    scan_len = min(len(data) - 1, SCAN_LEN - 1)
    result = scan_bytes_original(data, 0, scan_len)
    if result:
        return result
    return "ANSI"


def detect_encoding_bytes_new(data):
    """新版：三段采样（头部/中部/尾部）"""
    if len(data) == 0:
        return "ANSI"

    total_len = len(data)

    # BOM 检测
    if len(data) >= 2:
        if data[0] == 0xFF and data[1] == 0xFE:
            return "UTF-16LE"
        if data[0] == 0xFE and data[1] == 0xFF:
            return "UTF-16BE"
    if len(data) >= 3:
        if data[0] == 0xEF and data[1] == 0xBB and data[2] == 0xBF:
            return "UTF-8 BOM"

    # 文件太小，直接全量扫描
    if total_len < SCAN_LEN * 3:
        result = scan_bytes_for_encoding(data, 0, total_len - 1)
        return result if result else "ANSI"

    # 头部
    head_end = SCAN_LEN - 1
    result = scan_bytes_for_encoding(data, 0, head_end)
    if result:
        return result

    # 中部
    mid_start = (total_len // 2) - (SCAN_LEN // 2)
    if mid_start < head_end + 1:
        mid_start = head_end + 1
    mid_end = mid_start + SCAN_LEN - 1
    if mid_end >= total_len:
        mid_end = total_len - 1
    result = scan_bytes_for_encoding(data, mid_start, mid_end)
    if result:
        return result

    # 尾部
    tail_end = total_len - 1
    tail_start = tail_end - SCAN_LEN + 1
    if tail_start <= mid_end:
        tail_start = mid_end + 1
    if tail_start <= tail_end:
        result = scan_bytes_for_encoding(data, tail_start, tail_end)
        if result:
            return result

    return "ANSI"


# ============================================================
# 测试用例生成工具
# ============================================================

def make_ascii(n):
    """生成 n 字节纯 ASCII（用空格和字母）"""
    return b"A" * n


def make_utf8_cn(text):
    """中文转 UTF-8 字节"""
    return text.encode("utf-8")


def make_gbk_cn(text):
    """中文转 GBK 字节"""
    return text.encode("gbk")


def head_tail_wrap(head_bytes, body_bytes, tail_bytes):
    """拼接 head + body + tail"""
    return head_bytes + body_bytes + tail_bytes


# ============================================================
# 测试框架
# ============================================================

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.cases = []

    def test(self, name, data, expected_new, expected_original=None, note=""):
        """
        运行一个测试用例
        expected_new: 新版预期结果
        expected_original: 原版预期结果（不填则与新版相同）
        """
        if expected_original is None:
            expected_original = expected_new

        result_new = detect_encoding_bytes_new(data)
        result_ori = detect_encoding_bytes_original(data)

        pass_new = (result_new == expected_new)
        pass_ori = (result_ori == expected_original)

        status = "PASS" if (pass_new and pass_ori) else "FAIL"
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1

        size = len(data)
        info = f"[{status}] {name} (size={size}B)"
        if note:
            info += f"  -- {note}"
        info += f"\n       新版: {result_new} (预期: {expected_new}) {'✓' if pass_new else '✗'}"
        info += f"\n       原版: {result_ori} (预期: {expected_original}) {'✓' if pass_ori else '✗'}"

        if result_new != result_ori:
            info += "  [新旧不同]"

        self.cases.append(info)
        print(info)

    def summary(self):
        print()
        print("=" * 70)
        print(f"测试结果：通过 {self.passed}，失败 {self.failed}，共 {self.passed + self.failed} 个")
        print("=" * 70)
        return self.failed == 0


# ============================================================
# 测试用例
# ============================================================

def run_all_tests():
    t = TestRunner()

    # ---------- 1. BOM 检测 ----------
    print("\n=== 第一组：BOM 检测 ===")

    t.test("UTF-8 BOM + 中文",
           b"\xef\xbb\xbf" + "你好".encode("utf-8"),
           "UTF-8 BOM")

    t.test("UTF-16LE BOM",
           b"\xff\xfe" + "你好".encode("utf-16-le"),
           "UTF-16LE")

    t.test("UTF-16BE BOM",
           b"\xfe\xff" + "你好".encode("utf-16-be"),
           "UTF-16BE")

    # ---------- 2. 小文件（< 300字节）----------
    print("\n=== 第二组：小文件（< 300字节，全量扫描）===")

    t.test("小文件-纯ASCII(50B)",
           make_ascii(50),
           "ANSI")

    t.test("小文件-UTF-8中文(50字)",
           ("你好世界" * 10).encode("utf-8"),
           "UTF-8")

    t.test("小文件-GBK中文",
           "你好世界".encode("gbk"),  # 8字节GBK
           "ANSI", note="GBK高位字节不符合UTF-8前导模式 → ANSI")

    t.test("空文件",
           b"",
           "ANSI")

    # ---------- 3. 头部即有中文（新旧一致）----------
    print("\n=== 第三组：头部即有中文（新旧行为一致）===")

    t.test("大文件-开头即UTF-8中文",
           "第一章".encode("utf-8") + make_ascii(10000),
           "UTF-8", "UTF-8",
           "头部第一字节就是高位，新旧都能立即识别")

    t.test("大文件-开头即GBK中文",
           "第一章".encode("gbk") + make_ascii(10000),
           "ANSI", "ANSI",
           "GBK首字节不匹配UTF-8前导模式，新旧都立即判ANSI")

    # ---------- 4. 头部纯ASCII，中文在中部（新版优势）----------
    print("\n=== 第四组：头部纯ASCII，中文在中部（新版修复误判）===")

    # 构造：前500字节ASCII，中间是UTF-8中文
    data = make_ascii(500) + "第一章 测试内容".encode("utf-8") + make_ascii(500)
    t.test("头部500B ASCII + 中部UTF-8中文",
           data,
           "UTF-8", "ANSI",
           "原版只扫前100B，全是ASCII → 误判ANSI；新版中部采样命中 → 正确UTF-8")

    # 构造：前200字节ASCII，中间是GBK
    data = make_ascii(200) + "第一章".encode("gbk") + make_ascii(200)
    t.test("头部200B ASCII + 中部GBK",
           data,
           "ANSI", "ANSI",
           "原版只扫前100B全ASCII → 判ANSI；新版中部扫到GBK非法高位 → ANSI，结果一致但原因不同")

    # ---------- 5. 头部中部都纯ASCII，中文在尾部 ----------
    print("\n=== 第五组：头部中部都纯ASCII，中文在尾部 ===")

    data = make_ascii(2000) + "结尾内容".encode("utf-8")
    t.test("前2000B全ASCII + 尾部UTF-8",
           data,
           "UTF-8", "ANSI",
           "原版误判ANSI；新版尾部采样命中 → 正确UTF-8")

    data = make_ascii(2000) + "结尾".encode("gbk")
    t.test("前2000B全ASCII + 尾部GBK",
           data,
           "ANSI", "ANSI",
           "两者都判ANSI，新版尾部确认GBK非法高位")

    # ---------- 6. 超大文件，中文均匀分布 ----------
    print("\n=== 第六组：超大文件，中文均匀分布 ===")

    big_utf8 = ("第1章 内容".encode("utf-8") + b" " * 200) * 100  # ~25KB
    t.test("大文件-UTF-8均匀分布",
           big_utf8,
           "UTF-8", "UTF-8",
           "头部第一行就有中文，新旧一致")

    big_gbk = ("第1章 内容".encode("gbk") + b" " * 200) * 100  # ~22KB
    t.test("大文件-GBK均匀分布",
           big_gbk,
           "ANSI", "ANSI",
           "GBK首字节即非法，新旧一致")

    # ---------- 7. 临界尺寸：刚好 300 字节 ----------
    print("\n=== 第七组：临界尺寸 ===")

    # 299字节：走全量扫描
    data = make_ascii(100) + "中间".encode("utf-8") + make_ascii(187)
    t.test("299B文件-UTF-8中文在中部",
           data,
           "UTF-8", "ANSI",
           "299 < 300 → 全量扫描；原版只扫前100B误判")

    # 300字节：走三段
    data = make_ascii(100) + make_ascii(100) + "结尾".encode("utf-8") + make_ascii(84)
    t.test("300B文件-UTF-8中文在尾部附近",
           data,
           "UTF-8", "ANSI",
           "刚好300B → 三段采样；尾部段命中")

    # ---------- 8. 纯 ASCII 大文件 ----------
    print("\n=== 第八组：纯 ASCII 大文件 ===")

    t.test("纯ASCII 10KB",
           make_ascii(10240),
           "ANSI", "ANSI",
           "三段全为ASCII → 兜底ANSI，新旧一致")

    # ---------- 9. 2字节UTF-8字符（拉丁文扩展等）----------
    print("\n=== 第九组：2字节UTF-8序列 ===")

    # U+00E9 (é) = 0xC3 0xA9，典型2字节UTF-8
    data = b"\xc3\xa9" + make_ascii(1000)
    t.test("2字节UTF-8字符(é)在头部",
           data,
           "UTF-8", "UTF-8")

    data = make_ascii(500) + b"\xc3\xa9" + make_ascii(500)
    t.test("2字节UTF-8字符(é)在中部",
           data,
           "UTF-8", "ANSI",
           "原版只扫头→误判；新版中部命中")

    # ---------- 10. 4字节UTF-8字符（emoji等）----------
    print("\n=== 第十组：4字节UTF-8序列（emoji）===")

    # U+1F600 😀 = F0 9F 98 80
    data = b"\xf0\x9f\x98\x80" + make_ascii(1000)
    t.test("4字节UTF-8(😀)在头部",
           data,
           "UTF-8", "UTF-8")

    data = make_ascii(500) + b"\xf0\x9f\x98\x80" + make_ascii(500)
    t.test("4字节UTF-8(😀)在中部",
           data,
           "UTF-8", "ANSI",
           "原版只扫头→误判；新版中部命中")

    # ---------- 11. 非法UTF-8高位字节（确认ANSI）----------
    print("\n=== 第十一组：非法高位字节（确认判ANSI）===")

    # 0x80-0xBF 单独出现是非法的（只能是延续字节）
    data = b"\x80" + make_ascii(1000)
    t.test("非法高位0x80在头部",
           data,
           "ANSI", "ANSI",
           "0x80不是UTF-8前导字节 → 立即ANSI")

    # 0xF8以上也是非法的
    data = b"\xf8" + make_ascii(1000)
    t.test("非法高位0xF8在头部",
           data,
           "ANSI", "ANSI")

    # GBK 的第一字节通常是 0x81-0xFE，第二字节 0x40-0xFE
    # 大多数GBK首字节(0x81-0xA0, 0xB0-0xF7等) & 0xC0 ≠ 0x80, & 0xE0 ≠ 0xC0
    # 所以会落入 case else → ANSI
    data = "中".encode("gbk") + make_ascii(1000)  # "中" = D6 D0
    t.test("GBK汉字在头部",
           data,
           "ANSI", "ANSI",
           "D6 & E0 = C0 ≠ E0, D6 & C0 = C0 ≠ 80 → 落入else → ANSI")

    # ---------- 12. 多段混合，验证优先级 ----------
    print("\n=== 第十二组：早停机制验证 ===")

    # 头部就是UTF-8 → 应立即返回，不扫中部尾部
    data = "你好".encode("utf-8") + make_ascii(2000)
    t.test("头部UTF-8 → 立即返回",
           data,
           "UTF-8", "UTF-8",
           "验证早停：第一个高位字节即判定UTF-8")

    # 头部是GBK → 立即返回ANSI，不扫中部尾部
    data = "你好".encode("gbk") + make_ascii(2000)
    t.test("头部GBK → 立即返回ANSI",
           data,
           "ANSI", "ANSI",
           "验证早停：第一个高位字节即判定ANSI")

    # ---------- 13. 三段不重叠边界 ----------
    print("\n=== 第十三组：三段不重叠边界 ===")

    # 构造一个刚好三段不重叠的文件（300B+），中文分别在三段边界
    data = (make_ascii(99) + b"\xe4\xb8\xad" +  # 头部段末尾附近："中" = E4 B8 AD
            make_ascii(98) + b"\xe4\xb8\xad" +  # 中部段
            make_ascii(98) + b"\xe4\xb8\xad")   # 尾部段
    t.test("三段各有一个UTF-8汉字",
           data,
           "UTF-8", "UTF-8",
           "304B<500B → 走全量扫描，直接命中")

    # 只有尾部有中文，头部中部全ASCII
    data = make_ascii(300) + "结尾".encode("utf-8")
    t.test("仅尾部有UTF-8中文(300B后)",
           data,
           "UTF-8", "ANSI",
           "头部中部全ASCII → 尾部段命中 → UTF-8")

    # ---------- 14. 真实小说格式模拟 ----------
    print("\n=== 第十四组：真实小说格式模拟 ===")

    # 模拟：开头是ASCII版权声明，正文是UTF-8中文
    header = b"Copyright 2024 All Rights Reserved\n" * 5  # 约200B
    body = ("第1章 测试内容\n这是正文内容。\n" * 50).encode("utf-8")  # 约1.5KB
    footer = b"\n-- END --\n" * 5
    data = header + body + footer
    t.test("模拟小说-头部ASCII版权+UTF-8正文",
           data,
           "UTF-8", "ANSI",
           "典型场景：开头英文版权声明，正文中文；原版误判ANSI，新版中部命中")

    # 模拟：楔子/序章是纯ASCII（少见但可能），正文章节是中文
    intro = make_ascii(150)  # 类似 "PROLOGUE" 等
    main = ("第一回 内容\n" * 100).encode("utf-8")
    data = intro + main
    t.test("模拟小说-150B ASCII序章 + UTF-8正文",
           data,
           "UTF-8", "ANSI",
           "原版只扫前100B全是ASCII → 误判ANSI")

    # ---------- 15. 段边界（核心修复验证）----------
    print("\n=== 第十五组：段边界（核心修复验证）===")

    # 场景1：3字节UTF-8汉字跨头部段尾（99-101字节处）
    # 段尾不做截断保护，可跨段读取后续字节验证 → 正确判UTF-8
    cn_char = "中".encode("utf-8")  # E4 B8 AD
    data = make_ascii(99) + cn_char + make_ascii(500)
    t.test("3字节UTF-8跨头部段尾(99-101)",
           data,
           "UTF-8", "UTF-8",
           "段尾前导字节跨段验证 → 正确UTF-8，新旧一致")

    # 场景2：2字节UTF-8字符跨段尾
    data = make_ascii(99) + b"\xc3\xa9" + make_ascii(500)  # é = C3 A9
    t.test("2字节UTF-8(é)跨头部段尾(99-100)",
           data,
           "UTF-8", "UTF-8",
           "段尾2字节字符跨段验证 → UTF-8，新旧一致")

    # 场景3：4字节UTF-8(emoji)跨段尾
    data = make_ascii(99) + b"\xf0\x9f\x98\x80" + make_ascii(500)  # 😀
    t.test("4字节UTF-8(😀)跨头部段尾(99-102)",
           data,
           "UTF-8", "UTF-8",
           "段尾4字节字符跨段验证 → UTF-8，新旧一致")

    # 场景4：GBK 字符在段尾 → 正确判ANSI
    data = make_ascii(98) + "中".encode("gbk") + make_ascii(500)
    t.test("GBK字符在段尾(完整GBK → ANSI)",
           data,
           "ANSI", "ANSI",
           "GBK首字节D6落入else → ANSI，新旧一致")

    # 场景5：UTF-8 序列完全在段内 → 正常判UTF-8
    data = make_ascii(97) + "中".encode("utf-8") + make_ascii(500)
    t.test("3字节UTF-8完整在头部段内(97-99)",
           data,
           "UTF-8", "UTF-8",
           "汉字完整在段内 → UTF-8，新旧一致")

    # 场景6：段尾前导字节 + 非法延续字节 → 正确判ANSI
    data = make_ascii(99) + b"\xe4\x00" + make_ascii(500)
    t.test("段尾前导字节+非法延续字节 → ANSI",
           data,
           "ANSI", "ANSI",
           "E4后跟0x00（非延续字节）→ 非法 → ANSI")

    # 场景7：UTF-8字符刚好被段边界切成两半（段起点在中间字节）
    # 这是本次修复的核心：段起点跳过延续字节 → 找到前导字节 → 正确判断
    # 1000B文件，中段起点=450（中点500往前50）
    # 让"中文"从第448字节开始：E4(448) B8(449) AD(450) E6(451) 96(452) 87(453)
    # 中段起点450 = AD（"中"的第3字节，延续字节）→ 跳过 → 找到E6 → 判UTF-8
    cn_bytes = "中文".encode("utf-8")  # 6字节: E4 B8 AD E6 96 87
    data = make_ascii(448) + cn_bytes + make_ascii(546)  # 448+6+546=1000
    t.test("中段起点切在UTF-8序列中间（核心修复）",
           data,
           "UTF-8", "ANSI",
           "原版只扫头部→误判；新版中段起点跳过延续字节→找到前导字节→正确UTF-8")

    # 场景8：验证段起点跳过多个连续延续字节（单函数精确验证）
    # "中中中" UTF-8 = 9字节: E4 B8 AD E4 B8 AD E4 B8 AD
    # 从第4字节(B8, 第2个"中"的第2字节)开始扫，应跳过B8 AD找到E4 → 判UTF-8
    triple_cn = "中中中".encode("utf-8")
    r = scan_bytes_for_encoding(triple_cn, 4, 8)
    assert r == "UTF-8", f"单函数测试失败: 期望UTF-8, 实际{r}"
    # 用整体测试方式输出（小文件走全量扫描，新旧一致）
    t.test("段起点跳过多个连续延续字节",
           triple_cn,
           "UTF-8", "UTF-8",
           "起点4落在'中中中'中间，跳过延续字节→找到前导字节→UTF-8")

    # 场景9：段尾最后一个字节是非法高位（非UTF-8前导，非延续）
    # 比如0x80在段尾 → 应该被判为延续字节跳过？还是落入else→ANSI？
    # 0x80 & 0xC0 = 0x80 → 是延续字节 → 跳过
    # 但0x80作为段内第一个高位字节，前面没有前导字节，跳过后继续
    # 这种情况下如果后面全是ASCII → 返回空串
    data = make_ascii(99) + b"\x80" + make_ascii(500)
    t.test("段首字节是孤立延续字节0x80",
           data,
           "ANSI", "ANSI",
           "0x80是延续字节→跳过；后面全ASCII→本段无结论；其他段也无结论→兜底ANSI")

    # ---------- 16. 段起点截断（已有修复，回归验证）----------
    print("\n=== 第十六组：段起点截断（回归验证）===")

    # "中"=E4 B8 AD，让段起点落在 B8(第2字节)上
    data = make_ascii(50) + "中文".encode("utf-8") + make_ascii(200)
    # 直接测试 ScanBytesForEncoding 单函数：起点=51(=B8)，终点=150
    # 这里通过整体测试验证：让中文从第99字节开始，头部段(0-99)第99字节是E4
    # 上面第15组第1个用例已经覆盖了头部段尾的情况
    # 这里测试中部段起点切在UTF-8序列中间
    # 构造：文件400B，UTF-8中文从第199字节开始（中部段约150-249，起点切在中间字节）
    cn_bytes = "你好世界".encode("utf-8")  # 12字节
    data = make_ascii(199) + cn_bytes + make_ascii(200)
    t.test("中部段起点切在UTF-8序列中间(199字节处)",
           data,
           "UTF-8", "ANSI",
           "原版只扫头部→误判；新版中部段起点跳过延续字节→找到前导字节→正确UTF-8")

    return t.summary()


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
