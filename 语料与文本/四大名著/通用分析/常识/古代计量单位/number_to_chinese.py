# -*- coding: utf-8 -*-
"""
数字 ↔ 中文 转换器
- 支持超大整数（理论上可达 10^72，即「大数」级别）
- 支持小数转换（分、厘、毫、丝、忽、微... 乃至清净）
- 提供中文转数字的反向转换
- 生成对比 CSV：数字 vs 中文 对照表
- 多种模式：小写/大写金额/大数体系/小数体系等

参考九连环的递推结构设计：
  九连环：T(n) = T(n-1) + 2*T(n-2) + 1  （递推公式）
  中文数：按 4 位一组递归拆解，每组内按 个十百千 递推

大数体系（万进制 + 佛教延伸）：
  个 万 亿 兆 京 垓 秭 穰 沟 涧 正 载 极 恒河沙 阿僧祇 那由他 不可思议 无量 大数
  0  4  8  12 16 20 24 28 32 36 40 44 48  52     56     60       64     68    72

用法：
    python number_to_chinese.py 12345          # 数字转中文
    python number_to_chinese.py 123 456 789    # 多个数字
    python number_to_chinese.py --table 1000   # 生成 0~1000 对照表
    python number_to_chinese.py --verify       # 自动验证
    python number_to_chinese.py --big-units    # 生成大数单位表
    python number_to_chinese.py --small-units  # 生成小数单位表
"""

import csv
import sys
import os
import re


# ============================================================
# 1. 基础数据定义
# ============================================================

# 小写数字
DIGITS_LOWER = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

# 大写数字（财务用）
DIGITS_UPPER = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']

# 四位一组内的位权（个十百千）
SECTION_UNITS = ['', '十', '百', '千']

# 大单位（万进制 + 佛教延伸体系）：
# 个 万 亿 兆 京 垓 秭 穰 沟 涧 正 载 极 恒河沙 阿僧祇 那由他 不可思议 无量 大数
# 0  4  8  12 16 20 24 28 32 36 40 44 48  52     56     60       64     68    72
#
# 佛教终极单位（不可说系列）：
# 不可说 不可说不可说 不可说不可说转
#  76       80            84
#
# 说明：「不可说」系列出自《华严经》，本意为"无法用言语表达的极大数"，
#       此处按万进制规律将其量化为第19~21级大单位。
BIG_UNITS = [
    '',               # 10^0  个位（空）
    '万',             # 10^4
    '亿',             # 10^8
    '兆',             # 10^12
    '京',             # 10^16
    '垓',             # 10^20
    '秭',             # 10^24
    '穰',             # 10^28
    '沟',             # 10^32
    '涧',             # 10^36
    '正',             # 10^40
    '载',             # 10^44
    '极',             # 10^48
    '恒河沙',         # 10^52
    '阿僧祇',         # 10^56
    '那由他',         # 10^60
    '不可思议',       # 10^64
    '无量',           # 10^68
    '大数',           # 10^72
    '不可说',         # 10^76  —— 佛教终极系列
    '不可说不可说',   # 10^80
    '不可说不可说转', # 10^84
]

# 小数单位（传统 + 佛教延伸）：
# 分 厘 毫 丝 忽 微 纤 沙 尘 埃 渺 漠 模糊 逡巡 须臾 瞬息 弹指 刹那 六德 虚 空 清净
# -1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13  -14  -15  -16  -17  -18  -19 -20 -21 -22
#
# 佛教极微系列（物质分析的终极单位）：
# 微尘 邻虚尘 极微尘
# -23   -24    -25
#
# 说明：「微尘」系列出自佛教「五蕴皆空」的物质分析理论，
#       将物质不断细分至极微，此处按十进制规律将其量化。
SMALL_UNITS = [
    '分',         # 10^-1
    '厘',         # 10^-2
    '毫',         # 10^-3
    '丝',         # 10^-4
    '忽',         # 10^-5
    '微',         # 10^-6
    '纤',         # 10^-7
    '沙',         # 10^-8
    '尘',         # 10^-9
    '埃',         # 10^-10
    '渺',         # 10^-11
    '漠',         # 10^-12
    '模糊',       # 10^-13
    '逡巡',       # 10^-14
    '须臾',       # 10^-15
    '瞬息',       # 10^-16
    '弹指',       # 10^-17
    '刹那',       # 10^-18
    '六德',       # 10^-19
    '虚',         # 10^-20
    '空',         # 10^-21
    '清净',       # 10^-22
    '微尘',       # 10^-23  —— 佛教极微系列
    '邻虚尘',     # 10^-24
    '极微尘',     # 10^-25
]

# 大写金额的大单位（财务）
AMOUNT_BIG_UNITS = ['', '万', '亿', '兆']

# 金额单位
AMOUNT_UNITS = ['元', '角', '分']

# ============================================================
# 三大数字进制体系（下数/中数/上数）
# ============================================================
#
# 出自《数术记遗》：
#   下数：十十变之（十进制，每级×10）
#   中数：万万变之（万进制，每级×10000）
#   上数：自乘变之（自乘制，每级自乘）
#
# 传统十等大数名称：亿、兆、京、垓、秭、穰、沟、涧、正、载
# ============================================================

# 传统十等大数名称（从亿到载）
BIG_UNIT_NAMES = ['亿', '兆', '京', '垓', '秭', '穰', '沟', '涧', '正', '载']


def get_big_units_lower():
    """
    下数（十进制）体系：每级×10
    十万为亿，十亿为兆，十兆为京...
    返回 [(单位名, 指数), ...] 列表
    """
    units = [('', 0), ('十', 1), ('百', 2), ('千', 3), ('万', 4)]
    for i, name in enumerate(BIG_UNIT_NAMES):
        units.append((name, 5 + i))  # 亿=10^5, 兆=10^6, ...
    return units


def get_big_units_middle():
    """
    中数（万进制）体系：每级×10000
    万万为亿，万亿为兆，万兆为京...
    返回 [(单位名, 指数), ...] 列表
    """
    units = [('', 0), ('万', 4)]
    for i, name in enumerate(BIG_UNIT_NAMES):
        units.append((name, 8 + i * 4))  # 亿=10^8, 兆=10^12, ...
    return units


def get_big_units_upper():
    """
    上数（自乘制）体系：每级自乘
    万万为亿，亿亿为兆，兆兆为京...
    返回 [(单位名, 指数), ...] 列表
    """
    units = [('', 0), ('万', 4)]
    exp = 8  # 亿=10^8
    for name in BIG_UNIT_NAMES:
        units.append((name, exp))
        exp *= 2  # 下一个是自乘，指数翻倍
    return units


def generate_three_systems_table(output_dir="."):
    """生成三大进制体系对照表 CSV"""
    csv_path = os.path.join(output_dir, "三大数字进制对照表.csv")

    lower = get_big_units_lower()
    middle = get_big_units_middle()
    upper = get_big_units_upper()

    # 收集所有单位名称（去重，按中数顺序）
    all_names = []
    seen = set()
    for name, _ in middle:
        if name and name not in seen:
            all_names.append(name)
            seen.add(name)

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['# 中国古代三大数字进制对照表（下数/中数/上数）'])
        writer.writerow(['# 出自《数术记遗》（东汉·徐岳）'])
        writer.writerow([])

        writer.writerow([
            '序号', '单位名称',
            '下数（十进制）数值', '下数递推',
            '中数（万进制）数值', '中数递推',
            '上数（自乘制）数值', '上数递推'
        ])

        for idx, name in enumerate(all_names):
            # 查找各体系中的指数
            lower_exp = next((e for n, e in lower if n == name), '')
            middle_exp = next((e for n, e in middle if n == name), '')
            upper_exp = next((e for n, e in upper if n == name), '')

            # 递推描述
            if name == '万':
                lower_desc = '十个千'
                middle_desc = '十个千'
                upper_desc = '十个千（起点）'
            elif name == '亿':
                lower_desc = '十个万'
                middle_desc = '万万（一万个万）'
                upper_desc = '万万（万自乘）'
            else:
                lower_desc = '十个前级'
                middle_desc = '万个前级'
                upper_desc = '前级自乘'

            writer.writerow([
                idx + 1,
                name,
                f'10^{lower_exp}' if lower_exp != '' else '',
                lower_desc if lower_exp != '' else '',
                f'10^{middle_exp}' if middle_exp != '' else '',
                middle_desc if middle_exp != '' else '',
                f'10^{upper_exp}' if upper_exp != '' else '',
                upper_desc if upper_exp != '' else '',
            ])

        # 说明区
        writer.writerow([])
        writer.writerow(['# === 体系说明 ==='])
        writer.writerow(['体系', '规则', '特点', '使用场景'])
        writer.writerow([
            '下数（十进制）', '十十变之，每级×10',
            '简单易懂，增长慢', '先秦时期，日常计数'
        ])
        writer.writerow([
            '中数（万进制）', '万万变之，每级×10000',
            '四位一组，符合汉语习惯', '唐宋以后主流，沿用至今'
        ])
        writer.writerow([
            '上数（自乘制）', '自乘变之，每级自乘',
            '指数爆炸，增长极快', '佛教/哲学概念，表达无限大'
        ])

    print(f"  ✅ 三大数字进制对照表.csv（{len(all_names)}个单位）")
    return csv_path


# ============================================================
# 华严大数体系（出自《大方广佛华严经·阿僧祇品》）
# ============================================================
#
# 华严经中的数字体系，共124个单位（从洛叉到不可说不可说转）
# 递推规则：
#   1. 起点：洛叉 = 10^5（十万）
#   2. 俱胝 = 100 × 洛叉 = 10^7（注意：此步为100倍，非自乘）
#   3. 从阿庾多开始为自乘制：每个单位 = 前一单位 × 前一单位（自乘）
#
# 指数规律（从俱胝开始为第1个自乘单位）：
#   第 n 个单位的指数 = 7 × 2^(n-1)
#
# 文献出处：《大方广佛华严经》卷第四十五 阿僧祇品第三十
#           （实叉难陀 译本，CBETA T10n0279）
# ============================================================

# 华严大数完整单位列表（按顺序，从洛叉开始到不可说不可说转）
# 共124个单位（含洛叉基准点）
HUAYAN_BIG_UNITS = [
    '洛叉',       # 0 - 基准点 10^5（十万）
    '俱胝',       # 1 - 100洛叉 = 10^7（百亿）
    '阿庾多',     # 2 - 俱胝俱胝
    '那由他',     # 3 - 阿庾多阿庾多
    '频婆罗',     # 4 - 那由他那由他
    '矜羯罗',     # 5 - 频婆罗频婆罗
    '阿伽罗',     # 6 - 矜羯罗矜羯罗
    '最胜',       # 7 - 阿伽罗阿伽罗
    '摩婆罗',     # 8 - 最胜最胜
    '阿婆罗',     # 9 - 摩婆罗摩婆罗
    '多婆罗',     # 10 - 阿婆罗阿婆罗
    '界分',       # 11 - 多婆罗多婆罗
    '普摩',       # 12 - 界分界分
    '祢摩',       # 13 - 普摩普摩
    '阿婆钤',     # 14 - 祢摩祢摩
    '弥伽婆',     # 15 - 阿婆钤阿婆钤
    '毘攞伽',     # 16 - 弥伽婆弥伽婆
    '毘伽婆',     # 17 - 毘攞伽毘攞伽
    '僧羯逻摩',   # 18 - 毘伽婆毘伽婆
    '毘萨罗',     # 19 - 僧羯逻摩僧羯逻摩
    '毘贍婆',     # 20 - 毘萨罗毘萨罗
    '毘盛伽',     # 21 - 毘贍婆毘贍婆
    '毘素陀',     # 22 - 毘盛伽毘盛伽
    '毘婆诃',     # 23 - 毘素陀毘素陀
    '毘薄底',     # 24 - 毘婆诃毘婆诃
    '毘佉担',     # 25 - 毘薄底毘薄底
    '称量',       # 26 - 毘佉担毘佉担
    '一持',       # 27 - 称量称量
    '异路',       # 28 - 一持一持
    '颠倒',       # 29 - 异路异路
    '三末耶',     # 30 - 颠倒颠倒
    '毘覩罗',     # 31 - 三末耶三末耶
    '奚婆罗',     # 32 - 毘覩罗毘覩罗
    '伺察',       # 33 - 奚婆罗奚婆罗
    '周广',       # 34 - 伺察伺察
    '高出',       # 35 - 周广周广
    '最妙',       # 36 - 高出高出
    '泥罗婆',     # 37 - 最妙最妙
    '诃理婆',     # 38 - 泥罗婆泥罗婆
    '一动',       # 39 - 诃理婆诃理婆
    '诃理蒲',     # 40 - 一动一动
    '诃理三',     # 41 - 诃理蒲诃理蒲
    '奚鲁伽',     # 42 - 诃理三诃理三
    '达攞步陀',   # 43 - 奚鲁伽奚鲁伽
    '诃鲁那',     # 44 - 达攞步陀达攞步陀
    '摩鲁陀',     # 45 - 诃鲁那诃鲁那
    '忏慕陀',     # 46 - 摩鲁陀摩鲁陀
    '瑿攞陀',     # 47 - 忏慕陀忏慕陀
    '摩鲁摩',     # 48 - 瑿攞陀瑿攞陀
    '调伏',       # 49 - 摩鲁摩摩鲁摩
    '离憍慢',     # 50 - 调伏调伏
    '不动',       # 51 - 离憍慢离憍慢
    '极量',       # 52 - 不动不动
    '阿么怛罗',   # 53 - 极量极量
    '勃么怛罗',   # 54 - 阿么怛罗阿么怛罗
    '伽么怛罗',   # 55 - 勃么怛罗勃么怛罗
    '那么怛罗',   # 56 - 伽么怛罗伽么怛罗
    '奚么怛罗',   # 57 - 那么怛罗那么怛罗
    '鞞么怛罗',   # 58 - 奚么怛罗奚么怛罗
    '钵罗么怛罗', # 59 - 鞞么怛罗鞞么怛罗
    '尸婆么怛罗', # 60 - 钵罗么怛罗钵罗么怛罗
    '翳罗',       # 61 - 尸婆么怛罗尸婆么怛罗
    '薜罗',       # 62 - 翳罗翳罗
    '谛罗',       # 63 - 薜罗薜罗
    '偈罗',       # 64 - 谛罗谛罗
    '窣步罗',     # 65 - 偈罗偈罗
    '泥罗',       # 66 - 窣步罗窣步罗
    '计罗',       # 67 - 泥罗泥罗
    '细罗',       # 68 - 计罗计罗
    '睥罗',       # 69 - 细罗细罗
    '谜罗',       # 70 - 睥罗睥罗
    '娑攞荼',     # 71 - 谜罗谜罗
    '谜鲁陀',     # 72 - 娑攞荼娑攞荼
    '契鲁陀',     # 73 - 谜鲁陀谜鲁陀
    '摩覩罗',     # 74 - 契鲁陀契鲁陀
    '娑母罗',     # 75 - 摩覩罗摩覩罗
    '阿野娑',     # 76 - 娑母罗娑母罗
    '迦么罗',     # 77 - 阿野娑阿野娑
    '摩伽婆',     # 78 - 迦么罗迦么罗
    '阿怛罗',     # 79 - 摩伽婆摩伽婆
    '醯鲁耶',     # 80 - 阿怛罗阿怛罗
    '薜鲁婆',     # 81 - 醯鲁耶醯鲁耶
    '羯罗波',     # 82 - 薜鲁婆薜鲁婆
    '诃婆婆',     # 83 - 羯罗波羯罗波
    '毘婆罗',     # 84 - 诃婆婆诃婆婆
    '那婆罗',     # 85 - 毘婆罗毘婆罗
    '摩攞罗',     # 86 - 那婆罗那婆罗
    '娑婆罗',     # 87 - 摩攞罗摩攞罗
    '迷攞普',     # 88 - 娑婆罗娑婆罗
    '者么罗',     # 89 - 迷攞普迷攞普
    '驮么罗',     # 90 - 者么罗者么罗
    '钵攞么陀',   # 91 - 驮么罗驮么罗
    '毘伽摩',     # 92 - 钵攞么陀钵攞么陀
    '乌波跋多',   # 93 - 毘伽摩毘伽摩
    '演说',       # 94 - 乌波跋多乌波跋多
    '无尽',       # 95 - 演说演说
    '出生',       # 96 - 无尽无尽
    '无我',       # 97 - 出生出生
    '阿畔多',     # 98 - 无我无我
    '青莲华',     # 99 - 阿畔多阿畔多
    '钵头摩',     # 100 - 青莲华青莲华
    '僧祇',       # 101 - 钵头摩钵头摩
    '趣',         # 102 - 僧祇僧祇
    '至',         # 103 - 趣趣
    '阿僧祇',     # 104 - 至至
    '阿僧祇转',   # 105 - 阿僧祇阿僧祇
    '无量',       # 106 - 阿僧祇转阿僧祇转
    '无量转',     # 107 - 无量无量
    '无边',       # 108 - 无量转无量转
    '无边转',     # 109 - 无边无边
    '无等',       # 110 - 无边转无边转
    '无等转',     # 111 - 无等无等
    '不可数',     # 112 - 无等转无等转
    '不可数转',   # 113 - 不可数不可数
    '不可称',     # 114 - 不可数转不可数转
    '不可称转',   # 115 - 不可称不可称
    '不可思',     # 116 - 不可称转不可称转
    '不可思转',   # 117 - 不可思不可思
    '不可量',     # 118 - 不可思转不可思转
    '不可量转',   # 119 - 不可量不可量
    '不可说',     # 120 - 不可量转不可量转
    '不可说转',   # 121 - 不可说不可说
    '不可说不可说', # 122 - 不可说转不可说转
    '不可说不可说转', # 123 - 不可说不可说 不可说不可说
]


def huayan_unit_exponent(idx):
    """
    计算华严大数体系中第 idx 个单位的指数（以10为底）。

    规则：
      - idx=0 (洛叉): 指数 = 5
      - idx=1 (俱胝): 指数 = 7  （100洛叉 = 10^7）
      - idx>=2: 指数 = 7 × 2^(idx-1)  （自乘制）
    """
    if idx == 0:
        return 5
    elif idx == 1:
        return 7
    else:
        # 从俱胝开始，每一级自乘，指数翻倍
        # 第 idx 个单位 = 7 * 2^(idx-1)
        return 7 * (2 ** (idx - 1))


def generate_huayan_big_units_table(output_dir="."):
    """
    生成华严大数体系完整对照表 CSV。
    共124个单位（从洛叉到不可说不可说转）。
    """
    csv_path = os.path.join(output_dir, "华严大数124单位对照表.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['# 华严大数体系对照表（共124个单位）'])
        writer.writerow(['# 出处：《大方广佛华严经·阿僧祇品》'])
        writer.writerow(['# 译本：实叉难陀（唐） CBETA T10n0279'])
        writer.writerow(['# 规则：前二级为100倍关系，从阿庾多开始为自乘制（每级自乘）'])
        writer.writerow(['# 指数公式：n>=2时，指数 = 7 × 2^(n-1)'])
        writer.writerow([])
        writer.writerow([
            '序号', '单位名称', '梵文/音译', '指数(10^x)',
            '位数', '递推方式', '分类', '说明'
        ])

        # 分类标签
        categories = {
            0: ('基础', '起点，十万'),
            1: ('基础', '100洛叉，百亿'),
            2: ('自乘系列1', '俱胝俱胝'),
        }

        for i, name in enumerate(HUAYAN_BIG_UNITS):
            exp = huayan_unit_exponent(i)

            # 分类
            if i == 0:
                cat = '基准（洛叉）'
                desc = '起点：十万（10^5）'
            elif i == 1:
                cat = '基准（俱胝）'
                desc = '100洛叉 = 百亿（10^7），自乘制起点'
            elif i <= 20:
                cat = '自乘·前序（2-20）'
                desc = f'自乘第{i-1}级'
            elif i <= 60:
                cat = '自乘·中序（21-60）'
                desc = f'自乘第{i-1}级'
            elif i <= 100:
                cat = '自乘·后序（61-100）'
                desc = f'自乘第{i-1}级'
            elif i <= 104:
                cat = '阿僧祇系列'
                desc = '僧祇→趣→至→阿僧祇→阿僧祇转'
            elif i <= 123:
                cat = '终极·不可说系列'
                desc = '无量/无边/无等/不可数/不可称/不可思/不可量/不可说...'
            else:
                cat = '其他'
                desc = ''

            # 位数
            digits = exp + 1

            # 递推方式
            if i == 0:
                recurrence = '基准'
            elif i == 1:
                recurrence = '100 × 洛叉'
            else:
                prev_name = HUAYAN_BIG_UNITS[i-1]
                recurrence = f'{prev_name} × {prev_name}（自乘）'

            writer.writerow([
                i,
                name,
                '',  # 梵文名暂空
                f'10^{exp}',
                f'约 {digits} 位',
                recurrence,
                cat,
                desc
            ])

        # 说明区
        writer.writerow([])
        writer.writerow(['# === 关键节点 ==='])
        writer.writerow(['序号', '单位', '指数(约)', '位数(约)', '说明'])

        key_nodes = [
            (0, '洛叉', '5', '6', '起点：十万'),
            (1, '俱胝', '7', '8', '100洛叉，自乘制起点'),
            (3, '那由他', '28', '29', '佛经常用极大数'),
            (104, '阿僧祇', '7×2^103', '极多', '无数，佛教核心概念'),
            (120, '不可说', '7×2^119', '极多', '无法用言语表达'),
            (123, '不可说不可说转', '7×2^122', '极多', '华严经最大数词'),
        ]
        for node in key_nodes:
            writer.writerow(list(node))

    print(f"  ✅ 华严大数124单位对照表.csv（共{len(HUAYAN_BIG_UNITS)}个单位）")
    return csv_path


def generate_huayan_vs_chinese_table(output_dir="."):
    """
    生成华严大数 vs 中国本土上数法 对比表 CSV。
    """
    csv_path = os.path.join(output_dir, "华严大数与本土上数法对比表.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['# 华严大数 vs 中国本土上数法 对比表'])
        writer.writerow([])

        # 维度对比
        writer.writerow(['对比维度', '中国本土上数法', '华严大数（印度佛教）'])
        comparisons = [
            ['出处', '《数术记遗》（东汉·徐岳）', '《大方广佛华严经·阿僧祇品》（印度佛经）'],
            ['单位数量', '10个（亿~载）+ 万 = 11个', '124个（洛叉~不可说不可说转）'],
            ['起点', '万（10^4）', '洛叉（10^5，十万）'],
            ['第一个大单位', '亿（万万 = 10^8）', '俱胝（100洛叉 = 10^7）'],
            ['递推规则', '完全自乘制：亿亿为兆，兆兆为京...', '前二级100倍关系，之后自乘制'],
            ['指数公式', '第n个(从万起): 指数 = 2^(n+1)', '第n个(从俱胝起): 指数 = 7 × 2^(n-1)'],
            ['增长速度', '极快（指数翻倍）', '极快（指数翻倍，基数更大）'],
            ['第10级指数', '兆（第3级）：10^16', '第10级（多婆罗）：约10^3584'],
            ['最后一级', '载：10^4096', '不可说不可说转：10^(7×2^122)'],
            ['用途', '数学概念，表达极大数', '描述佛刹、菩萨数量等宗教概念'],
            ['文化背景', '中国本土数学/术数', '印度佛教，经丝绸之路传入中国'],
        ]
        for row in comparisons:
            writer.writerow(row)

        writer.writerow([])
        writer.writerow(['# === 优缺点对比 ==='])
        writer.writerow(['方面', '本土上数法', '华严大数'])

        pros_cons = [
            ['优点1', '单位少，容易记忆', '单位多，层级精细'],
            ['优点2', '体系简洁，逻辑清晰', '表达范围极广，几乎无限'],
            ['优点3', '本土文化，容易理解', '宗教哲学内涵丰富'],
            ['缺点1', '单位太少，很快到顶', '单位太多，难以记忆'],
            ['缺点2', '实际使用场景有限', '梵语音译，字面意义不明'],
            ['缺点3', '到"载"就停了，后续靠概念', '体系过于庞大，无实用价值'],
        ]
        for row in pros_cons:
            writer.writerow(row)

        writer.writerow([])
        writer.writerow(['# === 自乘逻辑底层差异 ==='])
        writer.writerow(['对比项', '本土上数法（数穷则变）', '华严大数（单一底数翻倍）'])

        logic_diff = [
            ['自乘起点', '万（10^4）', '俱胝（10^7）'],
            ['指数公式', '2^(n+1)', '7 × 2^(n-1)'],
            ['数学本质', '递推序列：U(n) = U(n-1)²', '指数塔：10^(7×2^(n-1))'],
            ['底数变化', '每级底数都在变（上一级的终点）', '以俱胝为基准的指数翻倍'],
            ['单位生成方式', '被动生成（数穷则变，不得不变）', '主动预设（经文中一次性列出124个）'],
            ['单位性质', '每个单位都是独立的"质变"节点', '大多数单位只是"占位符"'],
            ['哲学底色', '实用主义：够用就好，数到哪说到哪', '宗教超越：追求极致，逼近无限'],
            ['经典表述', '数穷则变，变则通', '不可说不可说转'],
        ]
        for row in logic_diff:
            writer.writerow(row)

        writer.writerow([])
        writer.writerow(['# === 文化根源差异 ==='])
        writer.writerow(['文化维度', '中国本土', '印度佛教'])
        culture_diff = [
            ['文明类型', '农业文明（实用导向）', '宗教文明（终极关怀导向）'],
            ['思维方式', '实用主义：够用就行', '思辨主义：追问终极'],
            ['数字用途', '计数、计算、度量衡', '描述宇宙/时间/功德等宗教概念'],
            ['审美倾向', '简洁之美：少而精', '繁复之美：多而全'],
            ['对无限的态度', '用"无数""无量"等模糊概念带过', '用精细的数字层级来"逼近"无限'],
        ]
        for row in culture_diff:
            writer.writerow(row)

    print(f"  ✅ 华严大数与本土上数法对比表.csv")
    return csv_path


# ============================================================
# 2. 核心算法：数字转中文（递推/分组结构）
# ============================================================

def _convert_section(n, digits):
    """
    将 0~9999 的数字转换为中文（一组四位）。
    这是核心递推单元，类似九连环中的 T(n) 递推。

    规则：
      - 千位非零：几千 + 剩余三位
      - 百位非零：几百 + 剩余两位
      - 十位非零：几十 + 个位
      - 中间有零：用一个「零」连接
      - 末尾零：不读
    """
    if n == 0:
        return ''

    result = ''
    # 从高位到低位处理
    qian = n // 1000
    bai = (n // 100) % 10
    shi = (n // 10) % 10
    ge = n % 10

    # 千位
    if qian > 0:
        result += digits[qian] + '千'

    # 百位
    if bai > 0:
        if qian > 0 and bai == 0:
            pass  # 已由中间零处理
        result += digits[bai] + '百'
    elif qian > 0 and (shi > 0 or ge > 0):
        result += digits[0]  # 千位后有零

    # 十位
    if shi > 0:
        if bai > 0 and shi == 0:
            pass
        result += digits[shi] + '十'
    elif bai > 0 and ge > 0:
        result += digits[0]  # 百位后有零

    # 个位
    if ge > 0:
        result += digits[ge]

    return result


def number_to_chinese(n, mode='lower', overflow_mode='auto'):
    """
    将整数转换为中文数字。

    采用「四位一组」的递推分组结构（万进制），类似九连环的分层递推：
      - 每组 4 位（个十百千），调用 _convert_section 处理
      - 组之间用大单位（万、亿、兆...）连接
      - 全零的组跳过
      - 组间零时补一个「零」

    超出最大单位（不可说不可说转，10^84）时的溢出策略：
      - 'auto'       : 自动模式，优先用递归方式，过大则用科学计数法（默认）
      - 'recursive'  : 递归方式，用「X + 最大单位」表示
      - 'scientific' : 科学计数法，「十的X次方」
      - 'hybrid'     : 混合方式，最高位用单位，剩余用科学计数法

    参数:
        n: 整数（支持负数）
        mode: 'lower' 小写 / 'upper' 大写 / 'amount' 金额
        overflow_mode: 溢出处理模式
    """
    if mode == 'upper' or mode == 'amount':
        digits = DIGITS_UPPER
    else:
        digits = DIGITS_LOWER

    # 处理零
    if n == 0:
        if mode == 'amount':
            return digits[0] + '元整'
        return digits[0]

    # 处理负数
    negative = False
    if n < 0:
        negative = True
        n = -n

    # 四位一组，从低位到高位分组
    sections = []
    temp = n
    while temp > 0:
        sections.append(temp % 10000)
        temp = temp // 10000

    section_count = len(sections)
    max_unit_idx = len(BIG_UNITS) - 1  # 最大单位索引

    # === 检查是否超出单位范围 ===
    if section_count > len(BIG_UNITS):
        # 超出最大单位范围，使用溢出策略
        return _number_to_chinese_overflow(
            n, sections, digits, mode, overflow_mode, negative
        )

    # === 正常范围内的处理 ===
    result_parts = []

    for i in range(section_count - 1, -1, -1):
        sec = sections[i]
        if sec == 0:
            # 全零组：如果后面还有非零组，需要补一个「零」
            if result_parts and not result_parts[-1].endswith(digits[0]):
                pass
            continue

        sec_str = _convert_section(sec, digits)

        # 处理组间零：当前组不足四位，且前面已有内容，且前面不是零
        if result_parts and sec < 1000 and not result_parts[-1].endswith(digits[0]):
            result_parts.append(digits[0])

        # 添加组内容 + 大单位
        if i > 0:  # 不是最末组（个组），才加大单位
            if mode == 'amount':
                if i < len(AMOUNT_BIG_UNITS):
                    sec_str += AMOUNT_BIG_UNITS[i]
            else:
                sec_str += BIG_UNITS[i]

        result_parts.append(sec_str)

    result = ''.join(result_parts)

    # 特殊处理：开头为「一十」时简化为「十」（仅小写模式）
    if mode == 'lower' and result.startswith('一十'):
        result = result[1:]

    # 负数
    if negative:
        result = '负' + result

    # 金额模式
    if mode == 'amount':
        result += '元整'

    return result


def _number_to_chinese_overflow(n, sections, digits, mode, overflow_mode, negative):
    """
    处理超出最大单位范围的数字。

    溢出策略：
      'recursive'  : 递归方式，将高位部分作为系数，加上最大单位
      'scientific' : 科学计数法
      'auto'       : 自动选择（默认用 recursive，系数部分不超过最大单位本身）
    """
    max_unit_idx = len(BIG_UNITS) - 1
    max_unit_name = BIG_UNITS[max_unit_idx]  # 最大单位名（不可说不可说转）
    max_unit_value = 10 ** (max_unit_idx * 4)  # 最大单位的数值

    if overflow_mode == 'scientific':
        # 科学计数法：十的X次方
        # 找到最高位的数量级
        magnitude = len(str(n)) - 1
        # 计算有效数字（保留4位有效数字）
        significant = n / (10 ** (magnitude - 3))
        significant = round(significant)
        # 用科学计数法表示
        result = f"{_convert_section(significant, digits)}乘以十的{_number_to_chinese_small(magnitude, digits)}次方"
        if negative:
            result = '负' + result
        return result

    elif overflow_mode == 'recursive':
        # 递归方式：系数 + 最大单位 + 低位
        # 系数部分 = n // max_unit_value
        # 低位部分 = n % max_unit_value
        coeff = n // max_unit_value
        remainder = n % max_unit_value

        # 递归转换系数
        coeff_str = number_to_chinese(coeff, mode=mode, overflow_mode='recursive')

        result = coeff_str + max_unit_name

        # 如果低位非零，加上低位部分
        if remainder > 0:
            # 判断低位最高位在第几位，决定是否补零
            remainder_sections = []
            temp = remainder
            while temp > 0:
                remainder_sections.append(temp % 10000)
                temp = temp // 10000
            # 如果低位不足max_unit_idx组，需要补零
            # 简单处理：直接加「零」+ 低位中文
            remainder_str = number_to_chinese(remainder, mode=mode, overflow_mode='recursive')
            # 判断是否需要中间加零
            # 如果低位最高组不足四位且非零，前面补零
            if remainder < 10 ** ((len(remainder_sections) - 1) * 4 + 3):
                result += digits[0] + remainder_str
            else:
                result += remainder_str

        if negative:
            result = '负' + result
        return result

    else:  # 'auto' 或 'hybrid'
        # 自动模式：先尝试 recursive，如果系数部分也超出了最大单位，
        # 则用科学计数法表示系数
        coeff = n // max_unit_value
        remainder = n % max_unit_value

        # 检查系数是否也超出了范围
        coeff_sections = []
        temp = coeff
        while temp > 0:
            coeff_sections.append(temp % 10000)
            temp = temp // 10000

        if len(coeff_sections) <= len(BIG_UNITS):
            # 系数在范围内，用递归方式
            return _number_to_chinese_overflow(
                n, sections, digits, mode, 'recursive', negative
            )
        else:
            # 系数也超出了，用科学计数法
            return _number_to_chinese_overflow(
                n, sections, digits, mode, 'scientific', negative
            )


def _number_to_chinese_small(n, digits):
    """将较小的整数转换为中文（用于科学计数法的指数，不加大单位）"""
    if n == 0:
        return digits[0]
    result = ''
    # 逐位转换（对于指数，直接逐位读更清晰）
    for ch in str(n):
        result += digits[int(ch)]
    return result


def _expand_scientific_notation(s):
    """将科学计数法字符串展开为普通十进制字符串"""
    s = s.strip().lower()
    if 'e' not in s:
        return s

    mantissa, exponent = s.split('e')
    exp = int(exponent)

    # 处理尾数
    if '.' in mantissa:
        int_m, dec_m = mantissa.split('.')
    else:
        int_m, dec_m = mantissa, ''

    mantissa_digits = int_m + dec_m
    dot_pos = len(int_m)  # 小数点的位置（在第几位之后）

    # 新的小数点位置
    new_dot_pos = dot_pos + exp

    if new_dot_pos <= 0:
        # 小数点在最左边，需要补前导零
        zeros = -new_dot_pos
        result = '0.' + '0' * zeros + mantissa_digits
    elif new_dot_pos >= len(mantissa_digits):
        # 小数点在最右边，需要补末尾零
        zeros = new_dot_pos - len(mantissa_digits)
        result = mantissa_digits + '0' * zeros
    else:
        # 小数点在中间
        result = mantissa_digits[:new_dot_pos] + '.' + mantissa_digits[new_dot_pos:]

    return result


def decimal_to_chinese(n, mode='lower', decimal_mode='dot', overflow_mode='auto'):
    """
    支持小数的数字转中文。

    参数:
        n: 数字（int/float/str）
        mode: 'lower' 小写 / 'upper' 大写 / 'amount' 金额
        decimal_mode:
            'dot' - 逐位读法（如 三点一四一五）
            'unit' - 单位读法（如 三分一厘四毫...）
        overflow_mode: 超出单位范围时的处理策略
            'auto'       - 自动模式（默认）
            'recursive'  - 递归方式，用「X + 最小单位」表示
            'scientific' - 科学计数法
    """
    # 处理整数情况
    if isinstance(n, int):
        return number_to_chinese(n, mode, overflow_mode)
    if isinstance(n, float) and n == int(n):
        return number_to_chinese(int(n), mode, overflow_mode)

    s = str(n)
    # 处理科学计数法格式的字符串（如 '1e-22', '1E+100'）
    if 'e' in s.lower():
        s = _expand_scientific_notation(s)

    if '.' not in s:
        return number_to_chinese(int(s), mode, overflow_mode)

    int_part, dec_part = s.split('.')
    int_result = number_to_chinese(int(int_part), mode, overflow_mode)

    digits = DIGITS_UPPER if mode in ('upper', 'amount') else DIGITS_LOWER

    if decimal_mode == 'unit':
        # 单位读法：分、厘、毫、丝、忽、微...
        return _decimal_unit_mode(int_result, dec_part, digits, overflow_mode)
    else:
        # 逐位读法（默认）
        # 对于极长的小数（超过一定长度），用科学计数法截断
        max_dot_digits = 50  # 超过50位就用摘要方式
        if len(dec_part) > max_dot_digits:
            # 摘要方式：显示前几位 + ... + 数量级
            first_few = ''.join(digits[int(ch)] for ch in dec_part[:10])
            magnitude = len(dec_part)
            mag_str = _number_to_chinese_small(magnitude, digits)
            dec_result = f'点{first_few}……（共{mag_str}位小数，约十的负{mag_str}次方）'
            return int_result + dec_result
        else:
            dec_result = '点'
            for ch in dec_part:
                dec_result += digits[int(ch)]
            return int_result + dec_result


def _decimal_unit_mode(int_result, dec_part, digits, overflow_mode):
    """
    小数单位读法的实现。
    对于超出 SMALL_UNITS 范围的部分，使用溢出策略。
    """
    max_small_idx = len(SMALL_UNITS)  # 小数单位数量

    # 找出第一个非零位的位置
    first_non_zero = 0
    for i, ch in enumerate(dec_part):
        if ch != '0':
            first_non_zero = i
            break
    else:
        # 小数部分全零
        return int_result

    # 如果第一个非零位在单位范围内，正常处理
    if first_non_zero < max_small_idx:
        dec_result = ''
        for i, ch in enumerate(dec_part):
            d = int(ch)
            if d == 0:
                continue
            if i < max_small_idx:
                dec_result += digits[d] + SMALL_UNITS[i]
            else:
                # 超出范围的部分，需要溢出处理
                overflow_dec = dec_part[i:]
                overflow_str = _decimal_overflow_unit(
                    overflow_dec, i, digits, overflow_mode
                )
                dec_result += overflow_str
                break
        if not dec_result:
            # 小数部分全零
            return int_result
        # 整数部分为零时，直接返回小数部分（不加"零"）
        if int_result == digits[0]:
            return dec_result.strip()
        return int_result + ' ' + dec_result.strip()
    else:
        # 第一个非零位就超出了范围，直接用溢出处理
        overflow_str = _decimal_overflow_unit(
            dec_part, 0, digits, overflow_mode
        )
        # 整数部分为零时，直接返回小数部分
        if int_result == digits[0]:
            return overflow_str
        return int_result + ' ' + overflow_str


def _decimal_overflow_unit(dec_part, start_pos, digits, overflow_mode):
    """
    处理超出小数单位范围的部分。

    参数:
        dec_part: 小数部分字符串
        start_pos: 起始位置（在整个小数中的位置，0开始）
        digits: 数字字符列表
        overflow_mode: 溢出模式
    """
    max_small_idx = len(SMALL_UNITS)
    smallest_unit = SMALL_UNITS[-1]  # 最小单位名（极微尘）

    if overflow_mode == 'scientific':
        # 科学计数法
        # 找到第一个非零位
        first_non_zero = 0
        for i, ch in enumerate(dec_part):
            if ch != '0':
                first_non_zero = i
                break
        total_pos = start_pos + first_non_zero + 1
        # 取有效数字（前4位）
        significant_str = dec_part[first_non_zero:first_non_zero+4]
        significant = int(significant_str.ljust(4, '0')[:4])
        sig_str = _convert_section(significant, digits)
        pos_str = _number_to_chinese_small(total_pos, digits)
        return f"{sig_str}乘以十的负{pos_str}次方"

    elif overflow_mode == 'recursive':
        # 递归方式：用最小单位表示
        # 超出了多少级
        overflow_levels = start_pos - max_small_idx + 1
        if overflow_levels <= 0:
            overflow_levels = 1

        # 计算相当于多少个"最小单位"
        # 小数的递归：每往右4位，系数乘以10000，单位不变
        # 简化处理：用科学计数法表示系数 + 最小单位
        first_non_zero = 0
        for i, ch in enumerate(dec_part):
            if ch != '0':
                first_non_zero = i
                break

        total_pos = start_pos + first_non_zero
        # 计算有效数字前几位
        significant_str = dec_part[first_non_zero:first_non_zero+4]
        significant = int(significant_str.ljust(4, '0')[:4])

        # 计算相对于最小单位的位置
        offset_from_smallest = total_pos - (max_small_idx - 1)
        if offset_from_smallest >= 0:
            # 在最小单位之后，用递归
            # 简化：用科学计数法形式 + 最小单位
            sig_str = _convert_section(significant, digits)
            exp = offset_from_smallest + 4 - len(significant_str.rstrip('0'))
            # 直接返回「十的负X次方 极微尘」形式不太好
            # 改用：有效数字 + 最小单位的递归表示
            return f"{sig_str}十的负{_number_to_chinese_small(offset_from_smallest, digits)}次方{smallest_unit}"
        else:
            # 不应该走到这里
            return ''

    else:  # 'auto'
        # 自动模式：如果超出不多（在4级以内），用递归，否则用科学计数法
        overflow_levels = start_pos - max_small_idx + 1
        if overflow_levels <= 4:
            return _decimal_overflow_unit(dec_part, start_pos, digits, 'recursive')
        else:
            return _decimal_overflow_unit(dec_part, start_pos, digits, 'scientific')


# ============================================================
# 3. 反向转换：中文转数字
# ============================================================

def chinese_to_number(s):
    """
    将中文数字转换为整数（阿拉伯数字）。
    反向递推：先按大单位分组，组内按位权累加。
    """
    s = s.strip()

    # 负数
    negative = False
    if s.startswith('负'):
        negative = True
        s = s[1:]

    # 零
    if s in ('零', '〇'):
        return 0

    # 建立单位映射
    digit_map = {}
    for i, d in enumerate(DIGITS_LOWER):
        digit_map[d] = i
    for i, d in enumerate(DIGITS_UPPER):
        digit_map[d] = i

    big_unit_values = {}
    for i, u in enumerate(BIG_UNITS):
        if u:  # 跳过空字符串
            big_unit_values[u] = 10 ** (4 * i)

    section_unit_values = {'十': 10, '百': 100, '千': 1000}

    # 查找最大的大单位，按大单位分割
    total = 0
    remaining = s

    # 从最大的大单位往小找
    for unit_name in reversed(BIG_UNITS):
        if not unit_name:
            continue
        if unit_name in remaining:
            idx = remaining.index(unit_name)
            left_part = remaining[:idx]
            right_part = remaining[idx + len(unit_name):]

            # 左边是该单位的系数
            if left_part:
                section_val = _parse_section(left_part, digit_map, section_unit_values)
                total += section_val * big_unit_values[unit_name]
            else:
                # 没有左边（如「万」直接开头），系数为 1（仅「十」有此情况）
                total += 1 * big_unit_values[unit_name]

            remaining = right_part

    # 剩余部分（个组）
    if remaining:
        total += _parse_section(remaining, digit_map, section_unit_values)

    if negative:
        total = -total

    return total


def _parse_section(s, digit_map, section_unit_values):
    """
    解析一组四位以内的中文数字（个十百千）。
    反向递推：遇到单位就累加。
    """
    if not s:
        return 0

    result = 0
    current_digit = 0
    i = 0

    while i < len(s):
        ch = s[i]

        if ch in digit_map:
            current_digit = digit_map[ch]
            # 检查下一个字符是不是单位
            if i + 1 < len(s) and s[i+1] in section_unit_values:
                unit = s[i+1]
                result += current_digit * section_unit_values[unit]
                current_digit = 0
                i += 2
            else:
                # 个位直接加
                result += current_digit
                current_digit = 0
                i += 1
        elif ch in section_unit_values:
            # 单位前没有数字（如「十万」中的「十」），默认为1
            if ch == '十' and result == 0 and current_digit == 0:
                result += 1 * section_unit_values[ch]
            else:
                result += current_digit * section_unit_values[ch]
                current_digit = 0
            i += 1
        elif ch == '零' or ch == '〇':
            # 零跳过
            i += 1
        else:
            i += 1  # 未知字符跳过

    return result


# ============================================================
# 4. 特殊模式
# ============================================================

def number_to_zhifayin(n):
    """
    数字转中文大写（财务/支票用）。
    支持两位小数（角分）。
    """
    if isinstance(n, int):
        return number_to_chinese(n, mode='amount')

    # 处理小数
    s = f"{n:.2f}"
    int_part, dec_part = s.split('.')
    int_num = int(int_part)
    jiao = int(dec_part[0])
    fen = int(dec_part[1])

    result = number_to_chinese(int_num, mode='upper') + '元'

    if jiao == 0 and fen == 0:
        result += '整'
    elif jiao > 0 and fen == 0:
        result += DIGITS_UPPER[jiao] + '角整'
    elif jiao == 0 and fen > 0:
        result += '零' + DIGITS_UPPER[fen] + '分'
    else:
        result += DIGITS_UPPER[jiao] + '角' + DIGITS_UPPER[fen] + '分'

    return result


# ============================================================
# 5. 验证与测试
# ============================================================

def verify_range(start, end, verbose=False):
    """
    验证指定范围内的数字，确保 数字→中文→数字 的往返一致。
    类似九连环中的 BFS 验证递推公式。
    """
    errors = []
    for n in range(start, end + 1):
        zh = number_to_chinese(n)
        back = chinese_to_number(zh)
        if back != n:
            errors.append((n, zh, back))
            if verbose:
                print(f"  ✗ {n} -> '{zh}' -> {back}")

    total = end - start + 1
    passed = total - len(errors)
    print(f"  验证范围 [{start}, {end}]，共 {total} 个")
    print(f"  通过：{passed} / {total} ({passed*100//total}%)")
    if errors:
        print(f"  错误：{len(errors)} 个")
        if not verbose:
            for n, zh, back in errors[:10]:
                print(f"    {n} -> '{zh}' -> {back}")
            if len(errors) > 10:
                print(f"    ... 共 {len(errors)} 个错误")
    else:
        print(f"  全部通过 ✓")

    return len(errors) == 0


def test_examples():
    """运行一些典型测试用例"""
    test_cases = [
        (0, '零'),
        (1, '一'),
        (10, '十'),
        (11, '十一'),
        (20, '二十'),
        (100, '一百'),
        (101, '一百零一'),
        (110, '一百一十'),
        (111, '一百一十一'),
        (200, '二百'),
        (1000, '一千'),
        (1001, '一千零一'),
        (1010, '一千零一十'),
        (1100, '一千一百'),
        (10000, '一万'),
        (10001, '一万零一'),
        (10010, '一万零一十'),
        (10100, '一万零一百'),
        (11000, '一万一千'),
        (12345, '一万二千三百四十五'),
        (100000000, '一亿'),
        (100000001, '一亿零一'),
        (123456789, '一亿二千三百四十五万六千七百八十九'),
        (-123, '负一百二十三'),
    ]

    print("\n=== 典型用例测试 ===")
    all_pass = True
    for num, expected in test_cases:
        result = number_to_chinese(num)
        status = '✓' if result == expected else '✗'
        if result != expected:
            all_pass = False
        print(f"  {status} {num:>12} -> {result:<30} (期望: {expected})")

    print(f"\n  结果：{'全部通过 ✓' if all_pass else '有错误 ✗'}")
    return all_pass


# ============================================================
# 6. 生成 CSV 对照表
# ============================================================

def generate_csv(start, end, output_dir=".", mode='lower'):
    """
    生成数字-中文对照表 CSV。
    类似九连环中的 generate_csv 函数。
    """
    csv_name = f"数字中文对照表_{start}_{end}.csv"
    csv_path = os.path.join(output_dir, csv_name)

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 表头区
        writer.writerow([f'# 数字 ↔ 中文 对照表（{start} ~ {end}）'])
        writer.writerow([f'# 模式：{"小写数字" if mode=="lower" else "大写金额" if mode=="amount" else "大写数字"}'])
        writer.writerow([f'# 共 {end - start + 1} 条记录'])
        writer.writerow([])

        writer.writerow([
            '序号',
            '阿拉伯数字',
            '中文小写',
            '中文大写',
            '财务金额',
            '反向转换验证',
            '位数',
            '备注'
        ])

        for n in range(start, end + 1):
            zh_lower = number_to_chinese(n, 'lower')
            zh_upper = number_to_chinese(n, 'upper')
            zh_amount = number_to_zhifayin(n) if n >= 0 else ''

            # 反向验证
            back = chinese_to_number(zh_lower)
            verify_result = '✓ 一致' if back == n else '✗ 不一致'

            # 位数
            digits = len(str(abs(n)))

            # 备注
            remark = ''
            if n == 0:
                remark = '零'
            elif n == 10:
                remark = '「一十」简化为「十」'
            elif n == 10000:
                remark = '万进制第一级'
            elif n == 100000000:
                remark = '万进制第二级（亿）'

            writer.writerow([
                n - start + 1,
                n,
                zh_lower,
                zh_upper,
                zh_amount,
                verify_result,
                digits,
                remark
            ])

        # 汇总统计
        writer.writerow([])
        writer.writerow(['# === 汇总统计 ==='])
        writer.writerow(['项目', '数值', '说明'])
        writer.writerow(['起始数字', start, ''])
        writer.writerow(['结束数字', end, ''])
        writer.writerow(['记录总数', end - start + 1, ''])
        writer.writerow(['最大位数', len(str(abs(end))), ''])
        writer.writerow(['最大数中文', number_to_chinese(end, 'lower'), ''])

    print(f"  ✅ {csv_name}（共 {end-start+1} 条记录）")
    return csv_path


def generate_big_units_table(output_dir="."):
    """生成大数单位对照表（含传统万进制 + 佛教延伸体系）"""
    csv_path = os.path.join(output_dir, "大数单位对照表.csv")

    # 单位说明
    unit_notes = {
        '': '基本单位（个/一）',
        '万': '万进制第一级',
        '亿': '万万为亿',
        '兆': '万亿为兆',
        '京': '万兆为京',
        '垓': '万京为垓',
        '秭': '万垓为秭',
        '穰': '万秭为穰',
        '沟': '万穰为沟',
        '涧': '万沟为涧',
        '正': '万涧为正',
        '载': '万正为载（《数术记遗》体系上限）',
        '极': '万载为极，传统体系最大数',
        '恒河沙': '如恒河中所有沙数（佛教）',
        '阿僧祇': '无量数，无法计算（佛教 Asamkhya）',
        '那由他': '极大数（佛教 Nayuta）',
        '不可思议': '心思言语都不能及（佛教 Acintya）',
        '无量': '没有限量（佛教 Apramana）',
        '大数': '佛法中最大的数词（佛教 Maha-samkhya）',
    }

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['# 中国古代大数单位对照表（万进制 + 佛教延伸）'])
        writer.writerow(['# 体系：《数术记遗》(万~载) + 《华严经》(极~大数)'])
        writer.writerow(['# 共 ' + str(len(BIG_UNITS)) + ' 级（含个位）'])
        writer.writerow([])
        writer.writerow(['序号', '体系', '单位名称', '数值（10的幂）', '科学计数法', '位数', '说明'])

        for i, unit in enumerate(BIG_UNITS):
            power = 4 * i
            name = unit if unit else '个/一'

            # 体系分类
            if i <= 11:  # 个~载
                system = '传统（数术记遗）'
            elif i == 12:  # 极
                system = '过渡（极）'
            else:  # 恒河沙~大数
                system = '佛教（华严经）'

            writer.writerow([
                i + 1,
                system,
                name,
                power,
                f"10^{power}",
                power + 1,
                unit_notes.get(unit, '')
            ])

    print(f"  ✅ 大数单位对照表.csv（共 {len(BIG_UNITS)} 级）")
    return csv_path


def generate_small_units_table(output_dir="."):
    """生成小数单位对照表（传统 + 佛教延伸）"""
    csv_path = os.path.join(output_dir, "小数单位对照表.csv")

    # 单位说明
    unit_notes = {
        '分': '十分之一',
        '厘': '一百分之一',
        '毫': '一千分之一',
        '丝': '蚕吐的丝，万分之一',
        '忽': '蜘蛛丝般细，十万分之一',
        '微': '细微，百万分之一',
        '纤': '纤细如丝，千万分之一',
        '沙': '如沙粒般微小，亿分之一',
        '尘': '如尘埃般小，十亿分之一',
        '埃': '尘埃的边缘，百亿分之一',
        '渺': '渺小，千亿分之一',
        '漠': '沙漠中的一粒沙，万亿分之一',
        '模糊': '模糊不清（传统体系延伸）',
        '逡巡': '顷刻之间',
        '须臾': '片刻，极短时间',
        '瞬息': '一眨眼一呼吸',
        '弹指': '弹一下手指的时间',
        '刹那': '极短时间，梵语 Ksana',
        '六德': '佛教极小单位',
        '虚': '虚空，不存在',
        '空': '空无所有',
        '清净': '清净无染（佛教体系下限）',
    }

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['# 中国古代小数单位对照表（传统 + 佛教延伸）'])
        writer.writerow(['# 体系：传统度量衡（分~漠） + 佛教时间单位借用（模糊~清净）'])
        writer.writerow(['# 共 ' + str(len(SMALL_UNITS)) + ' 级'])
        writer.writerow([])
        writer.writerow(['序号', '体系', '单位名称', '数值（10的幂）', '科学计数法', '对应小数', '说明'])

        for i, unit in enumerate(SMALL_UNITS):
            power = -(i + 1)

            # 体系分类
            if i < 12:  # 分~漠
                system = '传统（度量衡）'
            else:  # 模糊~清净
                system = '佛教（时间借用）'

            # 对应小数值
            dec_value = f"1e{power}"

            writer.writerow([
                i + 1,
                system,
                unit,
                power,
                f"10^{power}",
                dec_value,
                unit_notes.get(unit, '')
            ])

    print(f"  ✅ 小数单位对照表.csv（共 {len(SMALL_UNITS)} 级）")
    return csv_path


# ============================================================
# 7. 命令行接口
# ============================================================

def print_usage():
    print("""
数字 ↔ 中文 转换器
=================
用法：
  python number_to_chinese.py 12345          单个数字转中文
  python number_to_chinese.py 123 456 789    多个数字
  python number_to_chinese.py 3.1415         小数转换（逐位读法）
  python number_to_chinese.py --decimal-unit 3.14  小数转换（单位读法）
  python number_to_chinese.py --table 1000   生成 0~1000 对照表 CSV
  python number_to_chinese.py --range 1 100  生成 1~100 对照表 CSV
  python number_to_chinese.py --verify       自动验证 0~10000
  python number_to_chinese.py --big-units    生成大数单位表
  python number_to_chinese.py --small-units  生成小数单位表
  python number_to_chinese.py --three-systems 生成三大进制对照表
  python number_to_chinese.py --huayan       生成华严大数124单位表
  python number_to_chinese.py --huayan-compare 生成华严vs本土上数法对比表
  python number_to_chinese.py --test         运行典型测试用例
  python number_to_chinese.py 壹佰贰拾叁       中文转数字（自动检测）

参数：
  <数字>            转换指定数字（可多个）
  --table <n>       生成 0~n 的完整对照表
  --range <a> <b>   生成 a~b 的对照表
  --verify          验证 0~10000 的往返转换
  --big-units       生成大数单位对照表（个~大数+不可说系列）
  --small-units     生成小数单位对照表（分~极微尘，共25级）
  --three-systems   生成三大数字进制对照表（下数/中数/上数）
  --huayan          生成华严大数124单位对照表
  --huayan-compare  生成华严大数 vs 本土上数法对比表
  --decimal-unit <n>  小数转换（单位读法：分厘毫丝...）
  --test            运行典型测试用例
  --amount <n>      财务金额格式转换
""")


def main():
    args = sys.argv[1:]

    if not args:
        print_usage()
        return

    output_dir = "."

    # 生成对照表模式
    if '--table' in args:
        idx = args.index('--table')
        max_n = int(args[idx + 1]) if idx + 1 < len(args) else 1000
        print(f"\n生成 0~{max_n} 数字中文对照表...\n")
        generate_csv(0, max_n, output_dir)
        return

    if '--range' in args:
        idx = args.index('--range')
        start = int(args[idx + 1]) if idx + 1 < len(args) else 0
        end = int(args[idx + 2]) if idx + 2 < len(args) else start + 100
        print(f"\n生成 {start}~{end} 数字中文对照表...\n")
        generate_csv(start, end, output_dir)
        return

    if '--big-units' in args:
        print("\n生成大数单位对照表...\n")
        generate_big_units_table(output_dir)
        return

    if '--small-units' in args:
        print("\n生成小数单位对照表...\n")
        generate_small_units_table(output_dir)
        return

    if '--three-systems' in args:
        print("\n生成三大数字进制对照表...\n")
        generate_three_systems_table(output_dir)
        return

    if '--huayan' in args:
        print("\n生成华严大数对照表...\n")
        generate_huayan_big_units_table(output_dir)
        return

    if '--huayan-compare' in args:
        print("\n生成华严大数 vs 本土上数法对比表...\n")
        generate_huayan_vs_chinese_table(output_dir)
        return

    # 小数单位读法模式
    if '--decimal-unit' in args:
        idx = args.index('--decimal-unit')
        if idx + 1 < len(args):
            try:
                num = float(args[idx + 1])
                result = decimal_to_chinese(num, 'lower', 'unit')
                print(f"\n  {args[idx+1]} -> {result}\n")
            except ValueError:
                print(f"  错误：'{args[idx+1]}' 不是有效数字")
        return

    # 验证模式
    if '--verify' in args:
        print("\n=== 自动验证 0~10000 ===\n")
        verify_range(0, 10000, verbose=False)
        return

    # 测试模式
    if '--test' in args:
        test_examples()
        return

    # 金额模式
    if '--amount' in args:
        idx = args.index('--amount')
        if idx + 1 < len(args):
            try:
                num = float(args[idx + 1])
                result = number_to_zhifayin(num)
                print(f"\n  {args[idx+1]} -> {result}\n")
            except ValueError:
                print(f"  错误：'{args[idx+1]}' 不是有效数字")
        return

    # 普通转换模式
    numbers = []
    chinese_texts = []

    for a in args:
        # 尝试判断是数字还是中文
        if re.match(r'^-?\d+$', a):
            numbers.append(int(a))
        elif re.match(r'^-?\d+\.\d+$', a):
            numbers.append(float(a))
        else:
            # 可能是中文数字
            chinese_texts.append(a)

    if numbers:
        print("\n=== 数字 → 中文 ===\n")
        for n in numbers:
            if isinstance(n, float):
                result = decimal_to_chinese(n)
            else:
                result = number_to_chinese(n)
            upper = number_to_chinese(int(n), 'upper') if isinstance(n, int) else ''
            print(f"  {n:>15}  →  {result}")
            if upper:
                print(f"  {'大写':>15}  →  {upper}")
        print()

    if chinese_texts:
        print("\n=== 中文 → 数字 ===\n")
        for text in chinese_texts:
            try:
                result = chinese_to_number(text)
                print(f"  {text:<20}  →  {result}")
            except Exception as e:
                print(f"  {text:<20}  →  解析失败: {e}")
        print()


if __name__ == "__main__":
    main()
