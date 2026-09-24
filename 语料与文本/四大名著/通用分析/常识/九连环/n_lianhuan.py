# -*- coding: utf-8 -*-
"""
N 连环通用求解器
- 支持任意环数 n（1~25，受 BFS 内存限制）
- BFS 求最短路径 + 递推公式双重验证
- 生成对比 CSV：实际解法路径 vs 理论状态空间
- 自动生成各环数对照表

用法：
    python n_lianhuan.py 9          # 解九连环
    python n_lianhuan.py 5 7 9      # 解五、七、九连环
    python n_lianhuan.py --all 9    # 解1~9连环并生成对照表
"""

import csv
import sys
import os
from collections import deque


# ============================================================
# 1. N 连环规则模拟
# ============================================================

def get_valid_next_states(state, n):
    """
    根据 n 连环规则，从当前状态获取所有合法的下一状态。

    规则：
      - 第1环：随时可以取下或装上
      - 第k环(k>=2)：仅当第(k-1)环在框架上，且第1~(k-2)环都不在框架上时，
        才能取下或装上第k环

    状态编码：n位二进制，bit i 代表第(i+1)环
      1 = 在框架上（上环），0 = 已取下（下环）
    """
    moves = []
    # 第1环（bit 0）随时可切换
    moves.append(state ^ 1)
    # 第k环（bit k-1），k >= 2
    for k in range(2, n + 1):
        # 条件1：第(k-1)环必须在框架上
        if (state >> (k - 2)) & 1 == 0:
            continue
        # 条件2：第1~(k-2)环必须全部不在框架上
        all_off = True
        for j in range(k - 2):
            if (state >> j) & 1:
                all_off = False
                break
        if all_off:
            moves.append(state ^ (1 << (k - 1)))
    return moves


def solve_bfs(start, goal, n):
    """BFS 求最短路径，返回状态序列列表"""
    if start == goal:
        return [start]

    visited = {start: None}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for next_state in get_valid_next_states(current, n):
            if next_state not in visited:
                visited[next_state] = current
                if next_state == goal:
                    path = []
                    s = goal
                    while s is not None:
                        path.append(s)
                        s = visited[s]
                    path.reverse()
                    return path
                queue.append(next_state)

    return None


# ============================================================
# 2. 递推公式
# ============================================================

def compute_steps(n):
    """
    递推公式计算 n 连环最优解步数
    T(1) = 1, T(2) = 2
    T(n) = T(n-1) + 2*T(n-2) + 1
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1
    if n == 2:
        return 2
    T = [0] * (n + 1)
    T[1] = 1
    T[2] = 2
    for i in range(3, n + 1):
        T[i] = T[i - 1] + 2 * T[i - 2] + 1
    return T[n]


def compute_steps_table(max_n):
    """计算 1~max_n 的步数表"""
    T = [0] * (max_n + 1)
    if max_n >= 1:
        T[1] = 1
    if max_n >= 2:
        T[2] = 2
    for i in range(3, max_n + 1):
        T[i] = T[i - 1] + 2 * T[i - 2] + 1
    return T


def closed_form(n):
    """闭式公式"""
    if n <= 0:
        return 0
    if n % 2 == 1:  # 奇数
        return (2 ** (n + 1) - 1) // 3
    else:           # 偶数
        return (2 ** (n + 1) - 2) // 3


# ============================================================
# 3. 辅助函数
# ============================================================

def describe_move(prev_state, curr_state):
    """描述两状态之间的操作"""
    if prev_state is None:
        return "初始状态（全上环）"
    diff = prev_state ^ curr_state
    ring = 0
    while diff:
        if diff & 1:
            break
        diff >>= 1
        ring += 1
    ring += 1
    if (prev_state >> (ring - 1)) & 1:
        return f"取下第{ring}环"
    else:
        return f"装上第{ring}环"


def state_to_binary(state, n):
    """状态转 n 位二进制字符串"""
    return format(state, f'0{n}b')


# ============================================================
# 4. 生成 CSV
# ============================================================

def generate_csv(n, output_dir="."):
    """为 n 连环生成 CSV 文件"""
    all_on = (1 << n) - 1
    all_off = 0
    total_states = 1 << n

    # BFS 求解
    path = solve_bfs(all_on, all_off, n)
    if path is None:
        print(f"  ERROR: n={n} 无解！")
        return None

    num_steps = len(path) - 1
    num_path_states = len(path)
    formula_steps = compute_steps(n)

    # 验证
    assert num_steps == formula_steps, \
        f"BFS({num_steps}) != 公式({formula_steps})"

    # 状态 -> 步数 映射
    state_to_step = {}
    for step, state in enumerate(path):
        state_to_step[state] = step

    off_path_count = total_states - num_path_states

    # 文件名
    csv_name = f"n_lianhuan_{n}.csv"
    csv_path = os.path.join(output_dir, csv_name)

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 表头区
        writer.writerow([f'# {n}连环：实际解法({num_steps}步) vs 理论状态空间({total_states}) 对比表'])
        writer.writerow([f'# BFS最短路径模拟，规则=标准{n}连环'])
        writer.writerow([f'# 递推公式 T({n}) = {formula_steps}，闭式 = {closed_form(n)}'])
        writer.writerow([])

        writer.writerow([
            '行号',
            f'实际步数(0~{num_steps})', '实际状态(十进制)', f'实际状态(二进制{n}位)', '操作说明',
            f'理论状态序号(1~{total_states})', '理论状态(十进制)', f'理论状态(二进制{n}位)',
            '是否在实际路径上', '若在路径上的步数'
        ])

        # 数据行
        for i in range(total_states):
            row = [i + 1]

            if i < num_path_states:
                step = i
                state = path[step]
                prev_state = path[step - 1] if step > 0 else None
                move_desc = describe_move(prev_state, state)
                row.extend([step, state, state_to_binary(state, n), move_desc])
            else:
                row.extend(['', '', '', ''])

            theory_state = i
            on_path = theory_state in state_to_step
            step_if_on = state_to_step.get(theory_state, '')

            row.extend([
                i + 1, theory_state, state_to_binary(theory_state, n),
                '是' if on_path else '否', step_if_on
            ])
            writer.writerow(row)

        # 汇总统计
        writer.writerow([])
        writer.writerow(['# === 汇总统计 ==='])
        writer.writerow(['项目', '数值', '说明'])
        writer.writerow(['环数', n, f'{n}连环'])
        writer.writerow(['理论状态总数', total_states, f'2^{n} = {total_states}'])
        writer.writerow(['实际最短步数', num_steps, f'T({n}) = {formula_steps}'])
        writer.writerow(['路径上状态数', num_path_states, f'{num_steps} + 1'])
        writer.writerow(['不在路径上的状态数', off_path_count,
                         f'{total_states} - {num_path_states} = {off_path_count}'])
        writer.writerow(['闭式公式', closed_form(n),
                         f'({"奇" if n % 2 == 1 else "偶"}) '
                         f'(2^{n+1}-{"1" if n % 2 == 1 else "2"})/3 = {closed_form(n)}'])

    print(f"  ✅ {csv_name}（{total_states}行数据 + 汇总）")
    return {
        'n': n,
        'steps': num_steps,
        'path_states': num_path_states,
        'total_states': total_states,
        'off_path': off_path_count,
        'csv_file': csv_path,
    }


# ============================================================
# 5. 生成对照表
# ============================================================

def generate_summary_table(max_n, output_dir="."):
    """生成 1~max_n 的对照表 CSV"""
    T = compute_steps_table(max_n)
    csv_path = os.path.join(output_dir, "n_lianhuan_对照表.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([f'# N 连环对照表（1~{max_n}）'])
        writer.writerow([])

        writer.writerow([
            '环数 n', '状态空间 2^n', '最优步数 T(n)',
            '路径状态数 T(n)+1', '不在路径上的状态数',
            '闭式公式', '公式类型',
            'T(n)/T(n-1) 比值', '2^n / T(n) 比值'
        ])

        for n in range(1, max_n + 1):
            total = 1 << n
            steps = T[n]
            path_states = steps + 1
            off_path = total - path_states
            cf = closed_form(n)
            formula_type = f"(2^{n+1}-1)/3" if n % 2 == 1 else f"(2^{n+1}-2)/3"

            if n > 1 and T[n - 1] > 0:
                ratio_step = round(steps / T[n - 1], 4)
            else:
                ratio_step = ''

            ratio_space = round(total / steps, 4) if steps > 0 else ''

            writer.writerow([
                n, total, steps, path_states, off_path,
                cf, formula_type, ratio_step, ratio_space
            ])

    print(f"  ✅ n_lianhuan_对照表.csv（1~{max_n}）")
    return csv_path


# ============================================================
# 6. 单环详细分析
# ============================================================

def analyze(n):
    """分析单个 n 连环"""
    all_on = (1 << n) - 1
    all_off = 0
    total_states = 1 << n
    formula_steps = compute_steps(n)

    print(f"\n{'='*60}")
    print(f"  {n} 连环分析")
    print(f"{'='*60}")

    # 小规模用 BFS 验证，大规模只算公式
    if n <= 22:
        path = solve_bfs(all_on, all_off, n)
        bfs_steps = len(path) - 1 if path else -1
        match = "✓" if bfs_steps == formula_steps else "✗"
        print(f"  递推公式 T({n}) = {formula_steps}")
        print(f"  BFS 搜索结果   = {bfs_steps} {match}")
        print(f"  理论状态空间   = 2^{n} = {total_states}")
        print(f"  路径状态数     = {formula_steps + 1}")
        print(f"  不在路径上     = {total_states - formula_steps - 1}")
        print(f"  闭式公式       = {closed_form(n)}")
        if n >= 2:
            prev = compute_steps(n - 1)
            print(f"  T({n-1})          = {prev}")
            print(f"  不在路径上 = T({n-1}) ? {total_states - formula_steps - 1 == prev} ✓")
    else:
        print(f"  递推公式 T({n}) = {formula_steps}")
        print(f"  理论状态空间   = 2^{n} = {total_states}")
        print(f"  （n={n} 状态空间过大，跳过 BFS，仅用公式）")

    return formula_steps


# ============================================================
# 7. 主程序
# ============================================================

def print_usage():
    print("""
N 连环通用求解器
================
用法：
  python n_lianhuan.py 9          解九连环，生成 CSV
  python n_lianhuan.py 5 7 9      解五、七、九连环
  python n_lianhuan.py --all 9    解 1~9 连环 + 对照表
  python n_lianhuan.py --table 15 仅生成 1~15 对照表

参数：
  <数字>           解指定环数（可多个）
  --all <max_n>    解 1~max_n 连环 + 对照表
  --table <max_n>  仅生成对照表（不生成单独 CSV）
""")


def main():
    args = sys.argv[1:]

    if not args:
        print_usage()
        return

    # 输出目录
    output_dir = "."

    # 解析参数
    if '--all' in args:
        idx = args.index('--all')
        max_n = int(args[idx + 1]) if idx + 1 < len(args) else 9
        print(f"\n生成 1~{max_n} 连环的完整数据...\n")
        results = []
        for n in range(1, max_n + 1):
            r = generate_csv(n, output_dir)
            if r:
                results.append(r)
        generate_summary_table(max_n, output_dir)

        print(f"\n{'='*60}")
        print("  汇总")
        print(f"{'='*60}")
        print(f"  {'n':>4} {'状态空间':>12} {'最优步数':>12} {'路径状态':>12} {'不在路径':>12}")
        print(f"  {'-'*4} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
        for r in results:
            print(f"  {r['n']:>4} {r['total_states']:>12} {r['steps']:>12} "
                  f"{r['path_states']:>12} {r['off_path']:>12}")

    elif '--table' in args:
        idx = args.index('--table')
        max_n = int(args[idx + 1]) if idx + 1 < len(args) else 15
        print(f"\n生成 1~{max_n} 对照表...\n")
        generate_summary_table(max_n, output_dir)

    else:
        ns = [int(a) for a in args if a.isdigit()]
        if not ns:
            print_usage()
            return

        for n in ns:
            if n < 1:
                print(f"  跳过 n={n}（必须 >= 1）")
                continue
            if n > 25:
                print(f"  跳过 n={n}（状态空间 2^{n} 过大）")
                continue
            analyze(n)
            if n <= 22:
                generate_csv(n, output_dir)
            print()


if __name__ == "__main__":
    main()
