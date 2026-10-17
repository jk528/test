"""
STAT_009_基础图元叠加分解.py
基础图元叠加与分解的完整模拟

演示：
1. 创建 3 个基础图元（简单圈）
2. 叠加（XOR / 对称差）生成看似无规律的图
3. 用生成树 + 基本圈分解算法还原出基础图元
4. 同时演示容斥原理：E(N,j) → T(N,k) 的反演过程
5. 可视化全流程

依赖：pip install networkx matplotlib numpy
运行：python STAT_009_基础图元叠加分解.py
"""

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from itertools import combinations
from math import comb, factorial
import os

# ============================================================
# 第一部分：图论 — 基础图元叠加与分解
# ============================================================

def create_basis_cycles(n=8):
    """创建 3 个基础图元（简单圈），它们将作为'有规律的基'"""
    bases = []
    # 基元 1: 三角形 (1-2-3-1)
    bases.append(nx.Graph(name="C3(三角形)"))
    bases[0].add_edges_from([(1,2), (2,3), (3,1)])

    # 基元 2: 四边形 (4-5-6-7-4)
    bases.append(nx.Graph(name="C4(四边形)"))
    bases[1].add_edges_from([(4,5), (5,6), (6,7), (7,4)])

    # 基元 3: 五边形 (1-5-8-3-7-1) —— 跨越前两个区域，制造"混乱"
    bases.append(nx.Graph(name="C5(五边形)"))
    bases[2].add_edges_from([(1,5), (5,8), (8,3), (3,7), (7,1)])

    return bases


def superpose_graphs(graphs):
    """叠加多个图 = 边的对称差 (XOR)
    两条边在偶数个图中出现 → 消去
    两条边在奇数个图中出现 → 保留
    """
    edge_count = {}
    for g in graphs:
        for e in g.edges():
            key = tuple(sorted(e))
            edge_count[key] = edge_count.get(key, 0) + 1

    result = nx.Graph(name="叠加图")
    nodes = set()
    for g in graphs:
        nodes.update(g.nodes())
    result.add_nodes_from(sorted(nodes))

    for edge, count in edge_count.items():
        if count % 2 == 1:  # 奇数次 → 保留
            result.add_edge(*edge)

    return result, edge_count


def decompose_cycle_space(graph):
    """用生成树 + 基本圈分解图的圈空间
    算法：
    1. 找一棵生成树 T
    2. 对每条非树边 e，T+e 形成唯一基本圈
    3. 所有基本圈构成圈空间的一组基
    4. 图中任何圈 = 基本圈的 XOR 组合
    """
    if not nx.is_connected(graph):
        # 取最大连通分量
        components = list(nx.connected_components(graph))
        largest = max(components, key=len)
        graph = graph.subgraph(largest).copy()

    # 1. 找生成树
    spanning_tree = nx.minimum_spanning_tree(graph)

    # 2. 非树边
    non_tree_edges = set(graph.edges()) - set(spanning_tree.edges())
    non_tree_edges = non_tree_edges | {(v,u) for (u,v) in set(spanning_tree.edges())}
    non_tree_edges = set(tuple(sorted(e)) for e in non_tree_edges) - set(tuple(sorted(e)) for e in spanning_tree.edges())

    # 3. 对每条非树边，找基本圈
    fundamental_cycles = []
    for e in non_tree_edges:
        e_sorted = tuple(sorted(e))
        # 在生成树中找 e 两端点的路径
        try:
            path = nx.shortest_path(spanning_tree, e_sorted[0], e_sorted[1])
            cycle_edges = set()
            for i in range(len(path)-1):
                cycle_edges.add(tuple(sorted((path[i], path[i+1]))))
            cycle_edges.add(e_sorted)
            fundamental_cycles.append({
                'non_tree_edge': e_sorted,
                'path': path,
                'edges': cycle_edges,
                'length': len(cycle_edges)
            })
        except nx.NetworkXNoPath:
            continue

    return spanning_tree, fundamental_cycles


def verify_decomposition(original_graph, fundamental_cycles):
    """验证：将所有基本圈 XOR，应能还原原图的边集"""
    edge_count = {}
    for fc in fundamental_cycles:
        for e in fc['edges']:
            edge_count[e] = edge_count.get(e, 0) + 1

    reconstructed = set()
    for e, c in edge_count.items():
        if c % 2 == 1:
            reconstructed.add(e)

    original_edges = set(tuple(sorted(e)) for e in original_graph.edges())
    return reconstructed == original_edges, reconstructed, original_edges


# ============================================================
# 第二部分：组合 — 容斥原理的 Möbius 反演演示
# ============================================================

def compute_E(N, j):
    """计算 E(N,j) = 容斥原像和
    E(N,j) = N · (N-j-1)! · Σ_b f(N,j,b) · 2^b
    f(N,j,b) = N/b · C(j-1,b-1) · C(N-j-1,b-1)
    """
    if j == 0:
        return factorial(N)
    if j == N:
        return 2 * N

    total = 0
    max_b = min(j, N - j)
    for b in range(1, max_b + 1):
        f = N * comb(j-1, b-1) * comb(N-j-1, b-1) // b
        total += f * (2 ** b)

    return N * factorial(N - j - 1) * total


def compute_T_mobius(N):
    """用 Möbius 反演（容斥）计算 T(N,k)
    T(N,k) = Σ_{j=k}^{N} (-1)^{j-k} · C(j,k) · E(N,j)
    """
    E = [compute_E(N, j) for j in range(N + 1)]
    T = {}
    for k in range(N + 1):
        t = 0
        for j in range(k, N + 1):
            sign = (-1) ** (j - k)
            t += sign * comb(j, k) * E[j]
        if t > 0:
            T[k] = t
    return T, E


def superposition_demo(N=6):
    """演示：E(N,j) 是'叠加态'，T(N,k) 是'分解后的基础层'
    就像多个频率的正弦波叠加成复杂波形，再通过傅里叶变换分解
    """
    T, E = compute_T_mobius(N)

    print(f"\n{'='*70}")
    print(f"  Möbius 反漾示例：N={N}")
    print(f"  E(N,j) = 叠加态（至少含 j 条边）→ T(N,k) = 基础层（恰好 k 条边）")
    print(f"{'='*70}")

    print(f"\n  叠加态 E(N,j)：")
    for j in range(N + 1):
        print(f"    E({N},{j}) = {E[j]:>10}")

    print(f"\n  反演分解 T(N,k)：")
    for k in sorted(T.keys()):
        print(f"    T({N},{k}) = {T[k]:>10}")

    row_sum = sum(T.values())
    print(f"\n  行和验证: Σ T = {row_sum} = {N}! = {factorial(N)} {'✅' if row_sum == factorial(N) else '❌'}")
    print(f"  满分验证: T({N},{N}) = {T.get(N, 0)} = 2×{N} = {2*N} {'✅' if T.get(N, 0) == 2*N else '❌'}")

    return T, E


# ============================================================
# 第三部分：可视化
# ============================================================

def visualize_all(bases, superposed, spanning_tree, fund_cycles, N=6, T=None, E=None):
    """生成完整可视化：4 子图 + 容斥柱状图"""
    fig = plt.figure(figsize=(18, 14))

    # ---- 子图 1-3: 三个基础图元 ----
    colors = ['#e74c3c', '#3498db', '#2ecc71']
    labels = ['基元 1: C₃(三角形)', '基元 2: C₄(四边形)', '基元 3: C₅(五边形)']

    all_nodes = set()
    for g in bases:
        all_nodes.update(g.nodes())
    all_nodes = sorted(all_nodes)

    pos_global = {}
    for i, n in enumerate(all_nodes):
        angle = 2 * np.pi * i / len(all_nodes)
        pos_global[n] = (np.cos(angle), np.sin(angle))

    for idx, (g, color, label) in enumerate(zip(bases, colors, labels)):
        ax = fig.add_subplot(2, 4, idx + 1)
        pos = {n: pos_global[n] for n in g.nodes()}
        nx.draw(g, pos, node_color=color, node_size=400, edge_color=color,
                width=2.5, with_labels=True, font_size=10, font_weight='bold')
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.set_aspect('equal')

    # ---- 子图 4: 叠加后的"无规律"图 ----
    ax4 = fig.add_subplot(2, 4, 4)
    pos_super = {n: pos_global[n] for n in superposed.nodes()}
    # 边的颜色按出现次数
    _, edge_count = superpose_graphs(bases)
    edge_colors = []
    for e in superposed.edges():
        c = edge_count.get(tuple(sorted(e)), 1)
        edge_colors.append('#e74c3c' if c == 3 else '#9b59b6' if c == 2 else '#e67e22')

    nx.draw(superposed, pos_super, node_color='#2c3e50', node_size=400,
            edge_color=edge_colors, width=3, with_labels=True,
            font_size=10, font_weight='bold', font_color='white')
    ax4.set_title('叠加结果\n（看似无规律）', fontsize=11, fontweight='bold', color='#2c3e50')
    ax4.set_aspect('equal')

    # 图例
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label='出现 3 次（奇）'),
        mpatches.Patch(color='#9b59b6', label='出现 2 次（偶→消去）'),
        mpatches.Patch(color='#e67e22', label='出现 1 次（奇）'),
    ]
    ax4.legend(handles=legend_elements, loc='lower right', fontsize=7)

    # ---- 子图 5: 生成树 ----
    ax5 = fig.add_subplot(2, 4, 5)
    pos_tree = {n: pos_global[n] for n in spanning_tree.nodes()}
    nx.draw(spanning_tree, pos_tree, node_color='#8e44ad', node_size=400,
            edge_color='#8e44ad', width=2.5, with_labels=True,
            font_size=10, font_weight='bold', style='dashed')
    ax5.set_title(f'生成树 T\n({spanning_tree.number_of_edges()} 条边)', fontsize=11, fontweight='bold')
    ax5.set_aspect('equal')

    # ---- 子图 6-8: 基本圈（分解结果） ----
    cycle_colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#1abc9c']
    for idx in range(min(3, len(fund_cycles))):
        ax = fig.add_subplot(2, 4, 6 + idx)
        fc = fund_cycles[idx]
        sub = nx.Graph()
        sub.add_edges_from(list(fc['edges']))
        pos_fc = {n: pos_global[n] for n in sub.nodes()}
        c = cycle_colors[idx % len(cycle_colors)]
        nx.draw(sub, pos_fc, node_color=c, node_size=400, edge_color=c,
                width=2.5, with_labels=True, font_size=10, font_weight='bold')
        ax.set_title(f'基本圈 {idx+1}\n(非树边 {fc["non_tree_edge"]}, 长度 {fc["length"]})',
                     fontsize=10, fontweight='bold')
        ax.set_aspect('equal')

    plt.suptitle('基础图元叠加 → 无规律图 → 生成树分解 → 基本圈还原',
                 fontsize=15, fontweight='bold', y=1.02)

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(__file__), 'STAT_009_叠加分解可视化.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n  可视化已保存: {output_path}")
    plt.close()

    # ---- 第二张图：容斥反演柱状图 ----
    if T and E:
        fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        j_vals = list(range(N + 1))
        e_vals = [E[j] for j in j_vals]
        bars1 = ax1.bar(j_vals, e_vals, color='#3498db', alpha=0.8, edgecolor='black')
        ax1.set_xlabel('j (至少含 j 条边)', fontsize=12)
        ax1.set_ylabel('E(N,j)', fontsize=12)
        ax1.set_title(f'叠加态 E({N},j)\n（看似无规律的递减序列）', fontsize=13, fontweight='bold')
        ax1.set_xticks(j_vals)
        for bar, val in zip(bars1, e_vals):
            if val > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.01,
                        f'{val}', ha='center', va='bottom', fontsize=8)

        k_vals = sorted(T.keys())
        t_vals = [T[k] for k in k_vals]
        bars2 = ax2.bar(k_vals, t_vals, color='#e74c3c', alpha=0.8, edgecolor='black')
        ax2.set_xlabel('k (恰好 k 条边)', fontsize=12)
        ax2.set_ylabel('T(N,k)', fontsize=12)
        ax2.set_title(f'Möbius 反演后 T({N},k)\n（分解出的基础层）', fontsize=13, fontweight='bold')
        ax2.set_xticks(k_vals)
        for bar, val in zip(bars2, t_vals):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.01,
                    f'{val}', ha='center', va='bottom', fontsize=8)

        plt.suptitle(f'容斥原理 = 频谱分解：E({N},j) → T({N},k)  (N={N})',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        output_path2 = os.path.join(os.path.dirname(__file__), 'STAT_009_容斥反演柱状图.png')
        plt.savefig(output_path2, dpi=150, bbox_inches='tight')
        print(f"  容斥柱状图已保存: {output_path2}")
        plt.close()


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("  基础图元叠加与分解模拟")
    print("  演示：有规律的基 → 叠加成无规律 → 算法分解还原")
    print("=" * 70)

    # ---- 第一部分：图论叠加分解 ----
    print("\n【第一部分：图论 — 基础图元叠加与圈空间分解】\n")

    # 1. 创建基础图元
    bases = create_basis_cycles()
    print("  基础图元：")
    for i, g in enumerate(bases):
        print(f"    基元 {i+1}: {g.name}, 边 = {sorted(g.edges())}")

    # 2. 叠加
    superposed, edge_count = superpose_graphs(bases)
    print(f"\n  叠加结果（XOR / 对称差）：")
    print(f"    节点 = {sorted(superposed.nodes())}")
    print(f"    边 = {sorted(superposed.edges())}")
    print(f"    各边出现次数：")
    for e, c in sorted(edge_count.items()):
        status = "保留(奇)" if c % 2 == 1 else "消去(偶)"
        print(f"      {e}: {c} 次 → {status}")

    # 3. 分解
    spanning_tree, fund_cycles = decompose_cycle_space(superposed)
    print(f"\n  分解结果：")
    print(f"    生成树边 = {sorted(spanning_tree.edges())}")
    print(f"    非树边数 = {len(fund_cycles)} (= m - n + 1 = {superposed.number_of_edges()} - {spanning_tree.number_of_nodes()} + 1)")
    for i, fc in enumerate(fund_cycles):
        print(f"    基本圈 {i+1}: 非树边={fc['non_tree_edge']}, "
              f"路径={fc['path']}, 长度={fc['length']}")

    # 4. 验证
    verified, reconstructed, original = verify_decomposition(superposed, fund_cycles)
    print(f"\n  验证：XOR(所有基本圈) == 原图边集？  {'✅ 完全一致' if verified else '❌ 不一致'}")
    if not verified:
        print(f"    原始: {original}")
        print(f"    重建: {reconstructed}")

    # ---- 第二部分：容斥反演 ----
    print(f"\n{'='*70}")
    print("【第二部分：组合 — 容斥原理的 Möbius 反演】")

    T, E = superposition_demo(N=6)
    T2, E2 = superposition_demo(N=8)

    # ---- 第三部分：可视化 ----
    print(f"\n{'='*70}")
    print("【第三部分：可视化生成】\n")

    visualize_all(bases, superposed, spanning_tree, fund_cycles, N=6, T=T, E=E)

    # ---- 总结 ----
    print(f"\n{'='*70}")
    print("  总结")
    print(f"{'='*70}")
    print("""
  ┌─────────────────┬──────────────────────┬──────────────────────┐
  │                 │  图论类比             │  组合论类比           │
  ├─────────────────┼──────────────────────┼──────────────────────┤
  │  基础图元        │  基本圈 (fund. cycles)│  T(N,k) 恰好 k 条边  │
  │  叠加操作        │  XOR / 对称差         │  E(N,j) 至少 j 条边  │
  │  分解工具        │  生成树 + 非树边      │  Möbius 反演 / 容斥   │
  │  分解结果        │  基本圈集合           │  T(N,k) 分布表        │
  │  正确性验证      │  XOR 还原 = 原图      │  Σ T = N! 行和恒等   │
  └─────────────────┴──────────────────────┴──────────────────────┘

  核心洞察：
  - "看似无规律" = 大脑无法处理的信息叠加态
  - "找出基础图" = 找到一组基 (basis) 使分解可行
  - "分解算法"   = Möbius 反演 / 生成树 / 傅里叶变换（同构思想）
  - 容斥原理 = 组合学中的"傅里叶变换"
""")


if __name__ == '__main__':
    main()
