# -*- coding: utf-8 -*-
"""
随机极大数 + 极小数 中文转换演示
生成：小数点前100位整数 + 小数点后100位小数
输出：多种模式的中文读法，保存到文件
"""

import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from number_to_chinese import (
    number_to_chinese,
    decimal_to_chinese,
    get_big_units,
    get_small_units,
)


def generate_random_number(int_digits=100, dec_digits=100):
    """生成一个随机的超长数字：int_digits位整数 + dec_digits位小数"""
    # 整数部分：第一位不能是0
    int_part = str(random.randint(1, 9))
    for _ in range(int_digits - 1):
        int_part += str(random.randint(0, 9))

    # 小数部分
    dec_part = ''
    for _ in range(dec_digits):
        dec_part += str(random.randint(0, 9))

    return int_part, dec_part


def convert_and_save(output_dir='.'):
    """生成随机数并转换为中文，保存到文件"""

    int_part, dec_part = generate_random_number(100, 100)
    full_number = int_part + '.' + dec_part

    output_path = os.path.join(output_dir, "随机极大极小数中文转换演示.txt")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 72 + "\n")
        f.write("  随机极大数 + 极小数 中文转换演示\n")
        f.write("  整数部分：100位  |  小数部分：100位\n")
        f.write("=" * 72 + "\n\n")

        # ===== 原始数字 =====
        f.write("【原始数字】\n\n")
        f.write(f"整数部分（{len(int_part)}位）：\n")
        # 每10位一组，方便阅读
        groups = [int_part[i:i+10] for i in range(0, len(int_part), 10)]
        for i, g in enumerate(groups):
            f.write(f"  第{i*10+1:>3d}-{(i+1)*10:<3d}位:  {g}\n")
        f.write("\n")

        f.write(f"小数部分（{len(dec_part)}位）：\n")
        dec_groups = [dec_part[i:i+10] for i in range(0, len(dec_part), 10)]
        for i, g in enumerate(dec_groups):
            f.write(f"  第{i*10+1:>3d}-{(i+1)*10:<3d}位:  {g}\n")
        f.write("\n")

        f.write(f"完整数字：\n  {int_part}.{dec_part}\n\n")

        # ===== 数量级分析 =====
        f.write("-" * 72 + "\n")
        f.write("【数量级分析】\n\n")

        int_len = len(int_part)
        f.write(f"整数位数：{int_len} 位\n")
        f.write(f"数量级：10^{int_len - 1}\n")

        # 找出对应的大单位级别
        big_units = get_big_units()
        f.write(f"\n对应大数单位层级（中数体系，万进制）：\n")
        unit_index = (int_len - 1) // 4
        if unit_index < len(big_units):
            f.write(f"  整数部分约等于：{int_part[0]}.{int_part[1:4]}… × 10^{int_len-1}\n")
            f.write(f"  单位级别：第{unit_index}级（{big_units[unit_index][0]}级 = 10^{unit_index*4}）\n")
            f.write(f"  单位名称：{big_units[unit_index][0]}（指数 10^{unit_index*4}）\n")
        else:
            f.write(f"  超出命名单位范围（最大单位：{big_units[-1][0]} = 10^{(len(big_units)-1)*4}）\n")
            f.write(f"  使用科学计数法表示\n")

        f.write(f"\n小数位数：{len(dec_part)} 位\n")
        f.write(f"小数数量级：10^{-len(dec_part)}\n")

        small_units = get_small_units()
        f.write(f"\n对应小数单位层级：\n")
        if len(dec_part) <= len(small_units):
            f.write(f"  最小位单位：第{len(dec_part)}级（{small_units[len(dec_part)-1][0]} = 10^{-len(dec_part)}）\n")
            f.write(f"  单位名称：{small_units[len(dec_part)-1][0]}（指数 10^{-len(dec_part)}）\n")
            f.write(f"  所属体系：{small_units[len(dec_part)-1][2]}\n")
        else:
            f.write(f"  超出命名单位范围（共{len(small_units)}个小数单位）\n")
            f.write(f"  使用逐位读法\n")

        f.write("\n")

        # ===== 整数部分中文转换（多种模式） =====
        f.write("-" * 72 + "\n")
        f.write("【整数部分中文转换】\n\n")

        # 模式1：auto模式（递归表示）
        f.write("1) auto 模式（超出范围时递归表示）：\n\n")
        try:
            result = number_to_chinese(int_part, overflow_mode='auto')
            # 分段输出，方便阅读
            f.write(f"  {result}\n")
        except Exception as e:
            f.write(f"  转换失败：{e}\n")
        f.write("\n")

        # 模式2：scientific模式（科学计数法）
        f.write("2) scientific 模式（科学计数法读法）：\n\n")
        try:
            result = number_to_chinese(int_part, overflow_mode='scientific')
            f.write(f"  {result}\n")
        except Exception as e:
            f.write(f"  转换失败：{e}\n")
        f.write("\n")

        # 模式3：逐位读法
        digit_map = {'0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
                     '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'}
        f.write("3) 逐位读法（每一位直接读）：\n\n")
        digit_by_digit = ''.join(digit_map[d] for d in int_part)
        # 每20个字符换行
        f.write("  ")
        for i in range(0, len(digit_by_digit), 20):
            if i > 0:
                f.write("\n  ")
            f.write(digit_by_digit[i:i+20])
        f.write("\n\n")

        # ===== 小数部分中文转换（多种模式） =====
        f.write("-" * 72 + "\n")
        f.write("【小数部分中文转换】\n\n")

        # 模式1：逐位读法
        f.write("1) 逐位读法（digit by digit）：\n\n")
        dec_digit = ''.join(digit_map[d] for d in dec_part)
        f.write("  零点")
        for i in range(0, len(dec_digit), 20):
            if i > 0:
                f.write("\n  ")
            f.write(dec_digit[i:i+20])
        f.write("\n\n")

        # 模式2：单位读法（分厘毫丝...）
        f.write("2) 单位读法（分厘毫丝忽微...）：\n\n")
        try:
            result = decimal_to_chinese(f"0.{dec_part}", decimal_mode='unit')
            # 格式化输出
            if '约' in result:
                f.write(f"  {result}\n")
            else:
                # 每10个单位换行
                parts = result.split(' ')
                f.write("  ")
                count = 0
                for p in parts:
                    if count > 0 and count % 10 == 0:
                        f.write("\n  ")
                    f.write(p + ' ')
                    count += 1
                f.write("\n")
        except Exception as e:
            f.write(f"  转换失败：{e}\n")
        f.write("\n")

        # 模式3：科学计数法读法
        # 找出第一个非零数字的位置
        first_non_zero = 0
        for i, d in enumerate(dec_part):
            if d != '0':
                first_non_zero = i
                break
        f.write("3) 科学计数法读法：\n\n")
        if first_non_zero == len(dec_part) - 1:
            f.write(f"  约 {digit_map[dec_part[first_non_zero]]} 乘以十的负 {len(dec_part)} 次方\n")
        else:
            sig_fig = dec_part[first_non_zero:first_non_zero+4]
            sig_str = '.'.join([digit_map[sig_fig[0]], ''.join(digit_map[d] for d in sig_fig[1:])])
            f.write(f"  约 {sig_str} 乘以十的负 {len(dec_part)} 次方\n")
        f.write(f"  （首位有效数字在小数点后第 {first_non_zero+1} 位）\n")
        f.write("\n")

        # ===== 完整数字读法 =====
        f.write("-" * 72 + "\n")
        f.write("【完整数字中文读法】\n\n")

        f.write("整数部分（auto模式） + 小数部分（逐位读法）：\n\n")
        try:
            int_result = number_to_chinese(int_part, overflow_mode='auto')
            f.write(f"  {int_result} 点 {dec_digit[:30]}……\n")
            f.write(f"  （小数共{len(dec_part)}位，此处仅显示前30位）\n")
        except Exception as e:
            f.write(f"  转换失败：{e}\n")
        f.write("\n")

        f.write("整数部分（科学计数法） + 小数部分（科学计数法）：\n\n")
        try:
            int_sci = number_to_chinese(int_part, overflow_mode='scientific')
            f.write(f"  {int_sci} + 约 十的负 {len(dec_part)} 次方量级\n")
        except Exception as e:
            f.write(f"  转换失败：{e}\n")
        f.write("\n")

        # ===== 趣味对比 =====
        f.write("-" * 72 + "\n")
        f.write("【趣味对比】\n\n")

        f.write(f"  • 可观测宇宙粒子数：约 10^80（81位）\n")
        f.write(f"  • 本数整数部分：{int_len}位（10^{int_len-1}）\n")
        if int_len > 80:
            f.write(f"  → 本数比宇宙粒子数大 10^{int_len-81} 倍！\n")
        else:
            f.write(f"  → 本数比宇宙粒子数小 10^{80-(int_len-1)} 倍\n")
        f.write("\n")

        f.write(f"  • 贝肯斯坦界限（可观测宇宙）：约 10^122 bits\n")
        f.write(f"  • 本数整数位数：{int_len} 位\n")
        if int_len > 122:
            f.write(f"  → 本数位数超过宇宙信息容量！（宇宙装不下）\n")
        else:
            f.write(f"  → 本数位数在宇宙信息容量之内\n")
        f.write("\n")

        f.write(f"  • 华严大数「不可说不可说转」：约 10^(7×2^122)\n")
        f.write(f"  • 本数：10^{int_len-1}\n")
        f.write(f"  → 华严大数比本数大得多得多……（指数本身就是天文数字）\n")
        f.write("\n")

        f.write("=" * 72 + "\n")
        f.write("  演示结束\n")
        f.write("=" * 72 + "\n")

    print(f"✅ 文件已生成：{output_path}")
    print(f"   随机数：{int_part[:20]}... . ...{dec_part[-20:]}")
    print(f"   整数 {len(int_part)} 位，小数 {len(dec_part)} 位")
    return output_path


if __name__ == '__main__':
    random.seed(42)  # 固定种子，可复现
    convert_and_save()
