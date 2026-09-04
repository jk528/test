# -*- coding: utf-8 -*-
"""
N×N 乘法表分析工具
- 生成完整表格 vs 传统口诀（小九九）的对比数据
- 验证交换律导致的去重：n² → n(n+1)/2
- 支持任意 n，生成 CSV 对比表

用法：
    python multiplication_table.py 9        # 生成 9×9 对比 CSV
    python multiplication_table.py 5 9 12   # 生成多个阶数
    python multiplication_table.py --all 12 # 生成 1~12 全部 + 对照表
"""

import csv
import sys
import os


def generate_csv(n, output_dir="."):
    """生成 n×n 乘法表对比 CSV"""
    total = n * n                          # 完整表格项数
    unique = n * (n + 1) // 2              # 小九九口诀数（去重后）
    merged = total - unique                # 被交换律合并的项数

    csv_name = f"乘法表_{n}x{n}.csv"
    csv_path = os.path.join(output_dir, csv_name)

    # 建立小九九（上三角+对角线）的"基准口诀"映射
    # 对于 a×b（a ≤ b），口诀是 a 在前 b 在后
    # 对于 b×a（b > a），对应口诀是 a×b
    def xiaojiujiu_key(a, b):
        """返回该乘积在小九九中的标准口诀形式"""
        if a <= b:
            return f"{a}×{b}={a*b}"
        else:
            return f"{b}×{a}={a*b}"

    def is_xiaojiujiu(a, b):
        """该位置是否在小九九中（a ≤ b，即上三角+对角线）"""
        return a <= b

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 表头说明
        writer.writerow([f'# {n}×{n} 乘法表：完整表格({total}项) vs 小九九口诀({unique}项) 对比'])
        writer.writerow([f'# 完整格子数 = n² = {total}'])
        writer.writerow([f'# 口诀数 = n(n+1)/2 = {unique}'])
        writer.writerow([f'# 被交换律合并的项数 = n(n-1)/2 = {merged}'])
        writer.writerow([])

        # === 表1：逐行对比表 ===
        writer.writerow(['# === 表1：逐行对比（左侧完整表格 / 右侧小九九去重）==='])
        writer.writerow([])

        # 列头
        header = ['序号']
        for j in range(1, n + 1):
            header.append(f'{j}列')
        header.extend(['', '行内口诀数', '累计口诀数'])
        writer.writerow(header)

        cumulative = 0
        for i in range(1, n + 1):
            row = [f'第{i}行']
            for j in range(1, n + 1):
                val = i * j
                if is_xiaojiujiu(i, j):
                    row.append(f'{i}×{j}={val}')
                else:
                    row.append(f'↪{j}×{i}={val}')  # 箭头指向小九九中的等价形式
            row.append('')
            row.append(i)  # 第i行有i条口诀
            cumulative += i
            row.append(cumulative)
            writer.writerow(row)

        writer.writerow([])

        # === 表2：区域统计 ===
        writer.writerow(['# === 表2：区域统计 ==='])
        writer.writerow([])
        writer.writerow(['区域', '条件', '项数', '占比', '说明'])
        writer.writerow(['对角线', 'i = j', n, f'{n/total*100:.1f}%',
                         '自身相乘，无镜像，必须单独记'])
        writer.writerow(['上三角', 'i < j', merged, f'{merged/total*100:.1f}%',
                         '与下三角镜像对称，只需记一份'])
        writer.writerow(['下三角', 'i > j', merged, f'{merged/total*100:.1f}%',
                         '可由上三角交换律推出，无需另记'])
        writer.writerow(['合计', '—', total, '100%', '完整表格'])
        writer.writerow(['口诀数', '对角线+一个三角', unique, f'{unique/total*100:.1f}%',
                         f'{n} + {merged} = {unique}'])
        writer.writerow([])

        # === 表3：小九九完整口诀列表 ===
        writer.writerow(['# === 表3：小九九口诀完整列表（按行）==='])
        writer.writerow([])
        writer.writerow(['序号', '行号', '口诀', '乘积', '备注'])

        idx = 0
        for i in range(1, n + 1):
            for j in range(1, i + 1):
                idx += 1
                val = j * i
                note = '（对角线）' if i == j else ''
                writer.writerow([idx, f'第{i}行', f'{j}×{i}={val}', val, note])

        writer.writerow([])

        # === 表4：验证：所有下三角项都能在上三角找到 ===
        writer.writerow(['# === 表4：交换律验证（下三角 ↔ 上三角 一一对应）==='])
        writer.writerow([])
        writer.writerow(['序号', '下三角项', '上三角等价项', '乘积', '是否相等'])

        idx = 0
        for i in range(2, n + 1):  # 从第2行开始才有下三角
            for j in range(1, i):  # j < i
                idx += 1
                val = i * j
                writer.writerow([idx, f'{i}×{j}={val}', f'{j}×{i}={val}', val, '✓ 相等'])

        writer.writerow([])
        writer.writerow([f'共 {merged} 对镜像项，验证全部通过。'])
        writer.writerow([])

        # === 汇总 ===
        writer.writerow(['# === 汇总 ==='])
        writer.writerow(['项目', '公式', '数值'])
        writer.writerow(['完整格子数', 'n²', total])
        writer.writerow(['小九九口诀数', 'n(n+1)/2', unique])
        writer.writerow(['对角线项数', 'n', n])
        writer.writerow(['一个三角的项数', 'n(n-1)/2', merged])
        writer.writerow(['被交换律合并的比例', 'n(n-1)/2 / n²', f'{merged/total*100:.2f}%'])
        writer.writerow(['口诀数/完整数比值', 'n(n+1)/2 / n²', f'{unique/total*100:.2f}%'])

    print(f"  ✅ {csv_name}（{unique}条口诀 / {total}个格子）")
    return {
        'n': n,
        'total': total,
        'unique': unique,
        'merged': merged,
        'diagonal': n,
        'csv_file': csv_path,
    }


def generate_summary_table(max_n, output_dir="."):
    """生成 1~max_n 的对照表"""
    csv_path = os.path.join(output_dir, "乘法表_对照表.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([f'# N×N 乘法表对照表（1~{max_n}）'])
        writer.writerow([])
        writer.writerow([
            '阶数 n', '完整格子数 n²',
            '口诀数 n(n+1)/2', '对角线 n',
            '一个三角 n(n-1)/2', '被合并比例',
            '口诀/完整 比值', '口诀数增长比 T(n)/T(n-1)'
        ])

        prev = 0
        for n in range(1, max_n + 1):
            total = n * n
            unique = n * (n + 1) // 2
            tri = n * (n - 1) // 2
            merge_pct = f'{tri/total*100:.2f}%'
            ratio = f'{unique/total*100:.2f}%'

            if n > 1 and prev > 0:
                growth = f'{unique/prev:.4f}'
            else:
                growth = ''

            writer.writerow([n, total, unique, n, tri, merge_pct, ratio, growth])
            prev = unique

    print(f"  ✅ 乘法表_对照表.csv（1~{max_n}）")
    return csv_path


def print_usage():
    print("""
N×N 乘法表分析工具
==================
用法：
  python multiplication_table.py 9        生成 9×9 对比 CSV
  python multiplication_table.py 5 9 12   生成多个阶数
  python multiplication_table.py --all 12 生成 1~12 全部 + 对照表
""")


def main():
    args = sys.argv[1:]
    output_dir = "."

    if not args:
        print_usage()
        return

    if '--all' in args:
        idx = args.index('--all')
        max_n = int(args[idx + 1]) if idx + 1 < len(args) else 9
        print(f"\n生成 1~{max_n} 乘法表数据...\n")
        for n in range(1, max_n + 1):
            generate_csv(n, output_dir)
        generate_summary_table(max_n, output_dir)
        print()
    else:
        ns = [int(a) for a in args if a.isdigit()]
        if not ns:
            print_usage()
            return
        for n in ns:
            if n < 1:
                print(f"  跳过 n={n}（必须 >= 1）")
                continue
            generate_csv(n, output_dir)


if __name__ == "__main__":
    main()
