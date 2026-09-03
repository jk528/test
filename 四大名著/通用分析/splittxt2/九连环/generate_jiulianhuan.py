# -*- coding: utf-8 -*-
"""
九连环（Nine Linked Rings）状态序列生成器
- 使用 BFS 求从全上环(511)到全下环(0)的最短路径
- 生成对比 CSV：实际解法路径(342步) vs 理论状态空间(512)
- 同时验证用户原始格雷码代码的正确性
"""

import csv
from collections import deque

NUM_RINGS = 9
ALL_ON = (1 << NUM_RINGS) - 1   # 511 = 111111111
ALL_OFF = 0                      # 0   = 000000000


# ============================================================
# 1. 九连环规则模拟
# ============================================================

def get_valid_next_states(state):
    """
    根据九连环规则，从当前状态获取所有合法的下一步状态。

    规则：
      - 第1环：随时可以取下或装上
      - 第k环(k>=2)：仅当第(k-1)环在框架上，且第1~(k-2)环都不在框架上时，
        才能取下或装上第k环

    状态编码：9位二进制，bit i 代表第(i+1)环
      1 = 在框架上（上环），0 = 已取下（下环）
    """
    moves = []
    # 第1环（bit 0）随时可切换
    moves.append(state ^ 1)
    # 第k环（bit k-1），k >= 2
    for k in range(2, NUM_RINGS + 1):
        # 条件1：第(k-1)环必须在框架上
        if (state >> (k - 2)) & 1 == 0:
            continue
        # 条件2：第1~(k-2)环必须全部不在框架上
        all_off = True
        for j in range(k - 2):  # j = 0..k-3，对应第1~(k-2)环
            if (state >> j) & 1:
                all_off = False
                break
        if all_off:
            moves.append(state ^ (1 << (k - 1)))
    return moves


def solve_bfs(start, goal):
    """BFS 求最短路径，返回状态序列列表"""
    if start == goal:
        return [start]

    visited = {start: None}  # state -> parent_state
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for next_state in get_valid_next_states(current):
            if next_state not in visited:
                visited[next_state] = current
                if next_state == goal:
                    # 回溯路径
                    path = []
                    s = goal
                    while s is not None:
                        path.append(s)
                        s = visited[s]
                    path.reverse()
                    return path
                queue.append(next_state)

    return None  # 无解


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
    ring += 1  # 1-indexed
    if (prev_state >> (ring - 1)) & 1:
        return f"取下第{ring}环"
    else:
        return f"装上第{ring}环"


# ============================================================
# 2. 格雷码方法（用户原始代码）
# ============================================================

def gray_code_state(step):
    gray = step ^ (step >> 1)
    value = 511 - gray
    return value


def is_valid_move_sequence(states):
    """检查状态序列是否每一步都符合九连环规则"""
    invalid_steps = []
    for i in range(1, len(states)):
        prev = states[i - 1]
        curr = states[i]
        if curr not in get_valid_next_states(prev):
            invalid_steps.append(i)
    return invalid_steps


# ============================================================
# 3. 生成 CSV
# ============================================================

def generate_csv():
    # BFS 求解
    path = solve_bfs(ALL_ON, ALL_OFF)
    if path is None:
        print("ERROR: 无解！")
        return

    num_steps = len(path) - 1  # 341步
    num_states_on_path = len(path)  # 342个状态

    # 构建状态 -> 步数 映射
    state_to_step = {}
    for step, state in enumerate(path):
        state_to_step[state] = step

    # 格雷码序列
    gray_seq = [gray_code_state(s) for s in range(num_steps + 1)]
    gray_invalid = is_valid_move_sequence(gray_seq)

    # 统计
    total_theory = 1 << NUM_RINGS  # 512
    off_path_count = total_theory - num_states_on_path  # 170

    print(f"实际最短路径：{num_steps} 步，{num_states_on_path} 个状态")
    print(f"理论状态空间：{total_theory} 个状态")
    print(f"不在路径上的状态：{off_path_count} 个")
    print(f"格雷码序列非法步数：{len(gray_invalid)} 处")
    if gray_invalid:
        print(f"  首个非法步：第{gray_invalid[0]}步 "
              f"({gray_seq[gray_invalid[0]-1]} -> {gray_seq[gray_invalid[0]]})")

    # 写 CSV
    csv_path = "jiulianhuan.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 表头
        writer.writerow([
            '# 九连环：实际解法(341步) vs 理论状态空间(512) 对比表'
        ])
        writer.writerow([
            '# 生成说明：BFS最短路径模拟，规则=标准九连环'
        ])
        writer.writerow([])  # 空行

        writer.writerow([
            '行号',
            '实际步数(0~341)', '实际状态(十进制)', '实际状态(二进制9位)', '操作说明',
            '理论状态序号(1~512)', '理论状态(十进制)', '理论状态(二进制9位)',
            '是否在实际路径上', '若在路径上的步数'
        ])

        # 数据行：512行（理论状态数）
        for i in range(total_theory):
            row = [i + 1]

            # 左侧：实际解法路径（仅前342行有数据）
            if i < num_states_on_path:
                step = i
                state = path[step]
                prev_state = path[step - 1] if step > 0 else None
                move_desc = describe_move(prev_state, state)
                row.extend([
                    step,
                    state,
                    format(state, '09b'),
                    move_desc
                ])
            else:
                row.extend(['', '', '', ''])

            # 右侧：理论状态（全部512行）
            theory_state = i  # 0~511
            theory_seq = i + 1  # 1~512
            on_path = theory_state in state_to_step
            step_if_on_path = state_to_step.get(theory_state, '')

            row.extend([
                theory_seq,
                theory_state,
                format(theory_state, '09b'),
                '是' if on_path else '否',
                step_if_on_path
            ])

            writer.writerow(row)

        # 空行
        writer.writerow([])

        # 汇总统计区
        writer.writerow(['# === 汇总统计 ==='])
        writer.writerow(['项目', '数值', '说明'])
        writer.writerow(['环数', NUM_RINGS, '九连环'])
        writer.writerow(['理论状态总数', total_theory,
                         f'2^{NUM_RINGS} = {total_theory}（所有可能的状态组合）'])
        writer.writerow(['实际最短步数', num_steps,
                         '从全上环到全下环的最少操作步数'])
        writer.writerow(['路径上状态数', num_states_on_path,
                         '实际步数+1（含初始状态）'])
        writer.writerow(['不在路径上的状态数', off_path_count,
                         f'{total_theory} - {num_states_on_path} = {off_path_count}'])
        writer.writerow(['格雷码序列非法步数', len(gray_invalid),
                         '用户原始格雷码代码产生的非法移动次数'])

        # 格雷码 vs BFS 对比区
        writer.writerow([])
        writer.writerow(['# === 格雷码序列 vs BFS正确序列（前20步对比）==='])
        writer.writerow(['步数', 'BFS正确状态(十进制)', 'BFS正确状态(二进制)',
                         '格雷码状态(十进制)', '格雷码状态(二进制)',
                         '是否一致', '格雷码该步是否合法'])
        for step in range(min(20, num_steps + 1)):
            bfs_state = path[step]
            gray_state = gray_seq[step]
            match = '一致' if bfs_state == gray_state else '不一致'
            if step == 0:
                valid = '合法'
            else:
                valid = '合法' if gray_seq[step] in get_valid_next_states(gray_seq[step - 1]) else '非法'
            writer.writerow([
                step, bfs_state, format(bfs_state, '09b'),
                gray_state, format(gray_state, '09b'),
                match, valid
            ])

    print(f"\n✅ CSV 已生成：{csv_path}（共{total_theory}行数据 + 汇总统计）")
    return path, gray_seq, gray_invalid


# ============================================================
# 4. 递推公式验证
# ============================================================

def verify_formula():
    """验证九连环步数递推公式"""
    # T(n) = T(n-1) + 2*T(n-2) + 1, T(1)=1, T(2)=2
    T = [0] * (NUM_RINGS + 1)
    T[1] = 1
    T[2] = 2
    for n in range(3, NUM_RINGS + 1):
        T[n] = T[n - 1] + 2 * T[n - 2] + 1

    print("\n=== 递推公式验证 ===")
    print("公式：T(n) = T(n-1) + 2*T(n-2) + 1, T(1)=1, T(2)=2")
    for n in range(1, NUM_RINGS + 1):
        # 闭式
        if n % 2 == 1:  # 奇数
            closed = (2 ** (n + 1) - 1) // 3
            formula = f"(2^{n+1}-1)/3 = {closed}"
        else:  # 偶数
            closed = (2 ** (n + 1) - 2) // 3
            formula = f"(2^{n+1}-2)/3 = {closed}"
        print(f"  T({n}) = {T[n]}  闭式: {formula}")

    return T


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("九连环状态序列生成器")
    print("=" * 60)

    # 验证递推公式
    T = verify_formula()

    # 生成 CSV
    result = generate_csv()

    if result:
        path, gray_seq, gray_invalid = result

        # 详细分析
        print("\n=== 关键数据 ===")
        print(f"九连环最优解步数：{T[9]} （递推公式验证）")
        print(f"BFS 搜索结果：    {len(path) - 1} 步")
        print(f"两者一致：        {T[9] == len(path) - 1}")

        print(f"\n格雷码方法验证：")
        print(f"  起点：{gray_seq[0]} (应为511) {'✓' if gray_seq[0] == 511 else '✗'}")
        print(f"  终点：{gray_seq[-1]} (应为0)   {'✓' if gray_seq[-1] == 0 else '✗'}")
        print(f"  非法步数：{len(gray_invalid)}")
        if gray_invalid:
            print(f"  结论：格雷码方法不正确！虽然起点终点对，但中间步骤违反九连环规则")
            print(f"  首个非法步：第{gray_invalid[0]}步 "
                  f"状态{gray_seq[gray_invalid[0]-1]}→{gray_seq[gray_invalid[0]]}")
        else:
            print(f"  结论：格雷码方法正确")

        # 状态空间分析
        on_path = set(path)
        off_path = [s for s in range(512) if s not in on_path]
        print(f"\n状态空间分析：")
        print(f"  在路径上的状态：{len(on_path)} 个")
        print(f"  不在路径上的状态：{len(off_path)} 个")
        print(f"  示例（不在路径上的前10个状态）：{off_path[:10]}")
