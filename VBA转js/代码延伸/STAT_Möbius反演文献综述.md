# Möbius 反演在图论圈空间中的应用 — 文献综述与学习指南

> 基于 13 篇经典文献与前沿论文的系统整理
> 日期：2026-08-11

---

## 一、核心概念对比

### 1.1 三层应用框架

Möbius 反演在图论圈空间中的应用可分为三个层次，每层解决不同的问题：

| 层次 | 数学结构 | 核心问题 | 基分解 vs 反演 | 代表文献 |
|------|---------|---------|---------------|---------|
| **圈空间层** | GF(2) 向量空间 | 任意偶子图 = 哪些基本圈的 XOR？ | 纯线性基分解（无需反演） | Radcliffe, Kavitha 综述 |
| **格论层** | Bond lattice / 子图偏序集 | 从"至少含 H"反演"恰好含 H" | Möbius 函数 μ(G,H) 加权反演 | Tutte, Whitney, Rota |
| **计数层** | 自然数链 {0,1,...,N} | 从"至少 j 条边"反演"恰好 k 条边" | 二项式反演（Möbius 特例） | 本文 T(N,k), Kaplansky |

### 1.2 基分解 vs 容斥原理 vs Möbius 反演

| 维度 | 基分解 | 容斥原理 | Möbius 反演 |
|------|-------|---------|------------|
| **定义** | 复杂对象 = 基元素的线性组合 | "恰好" = "至少"的反演 | 偏序集上的一般反演框架 |
| **公式** | f = Σ cᵢ·bᵢ | T(k) = Σ(-1)^{j-k}·C(j,k)·E(j) | g(x) = Σ μ(y,x)·f(y) |
| **叠加核 K** | 基矩阵 B | C(k,j)（二项式系数） | 1（偏序集 ζ 函数） |
| **反演核 K⁻¹** | B⁻¹ | (-1)^{j-k}·C(j,k) | μ(y,x)（Möbius 函数） |
| **偏序集** | 向量空间 | 子集格 2^S | 任意局部有限偏序集 |
| **适用范围** | 线性空间 | 组合计数 | 任意偏序集 |
| **关系** | 独立框架 | Möbius 反演的特例 | 最一般的框架 |

### 1.3 不同偏序集下的 Möbius 反演特例

| 偏序集 P | 叠加关系 | 反演核 μ | 名称 | 图论应用 |
|---------|---------|---------|------|---------|
| 子集格 (A⊆B) | g(A) = Σ_{B⊇A} f(B) | (-1)^{\|B\|-\|A\|} | 容斥原理 | 子图计数 |
| 整除格 (d\|n) | g(d) = Σ_{d\|e\|n} f(e) | μ(n/d) (经典 Möbius) | 数论反演 | 图的因子计数 |
| 自然数链 [k]⊆[j] | E(j) = Σ_{k≥j} C(k,j)·T(k) | (-1)^{j-k}·C(j,k) | 二项式反演 | **本文 T(N,k)** |
| 分拆格 Π_n | g(π) = Σ_{σ≥π} f(σ) | μ(π,σ) (分拆 Möbius) | 分拆反演 | 图的连通分量 |
| Bond lattice L(G) | N_≥(H) = Σ N_=(G') | μ(H,G) (图 Möbius) | 图反演 | 色多项式 |
| 子图格 | f(H) = Σ_{H'⊇H} g(H') | μ(H,H') | 子图反演 | Tutte 多项式 |

### 1.4 圈空间的基分解 vs T(N,k) 的容斥反演

| 对比维度 | 圈空间基分解 | T(N,k) 容斥反演 |
|---------|------------|----------------|
| **基元素** | 基本圈 C_e（m-n+1 个） | T(N,k)（N+1 个"频率层"） |
| **叠加操作** | XOR（GF(2) 对称差） | 加权求和 Σ C(k,j)·T(k) |
| **分解工具** | 生成树 + 非树边 | 二项式反演 |
| **叠加态** | 任意偶子图 | E(N,j)（至少 j 条边） |
| **基础层** | 基本圈组 | T(N,k)（恰好 k 条边） |
| **验证恒等式** | XOR(所有基本圈) = 原图 | Σ_k T(N,k) = N! |
| **复杂度** | O(m·n)（构造基本圈） | O(N²)（闭式公式） |

---

## 二、文献分类详解

### 2.1 奠基与理论框架（4 篇必读）

#### [1] Rota 1964 — Möbius 反演的诞生

- **文献**：G.-C. Rota, "On the foundations of combinatorial theory I: Theory of Möbius functions," *Z. Wahrscheinlichkeitstheorie* 2, 340–368, 1964.
- **链接**：[DOI: 10.1007/BF00531932](https://doi.org/10.1007/BF00531932)
- **核心贡献**：
  - 将数论中的 Möbius 函数推广到任意局部有限偏序集
  - 建立了 `g(x) = Σ_{y≤x} f(y)` ↔ `f(x) = Σ_{y≤x} μ(y,x)·g(y)` 的反演框架
  - 统一了容斥原理、数论 Möbius 反演、二项式反演为同一理论的特例
- **对本文的意义**：T(N,k) 的二项式反演是 Rota 框架在自然数链上的直接应用

#### [2] Stanley 2011 — 教科书标准参考

- **文献**：R. P. Stanley, *Enumerative Combinatorics*, Vol. 1, Ch. 3 (2nd ed.), Cambridge Univ. Press, 2011. ISBN: 9781107602625.
- **链接**：[Cambridge 出版社](https://www.cambridge.org/core/books/enumerative-combinatorics/9A9A3B9C8ECB6BE33D03B0A2DE6F4F28)
- **核心贡献**：
  - 第 3 章系统讲述偏序集上的 Möbius 反演
  - 包含几何格、分割格、图格的 Möbius 函数显式计算
  - 大量图论应用习题与例子
- **阅读建议**：先读 Ch.3.1-3.7（基本理论），再读 Ch.3.10（几何格应用）

#### [3] Tutte 1954 — 图论反演的起点

- **文献**：W. T. Tutte, "A contribution to the theory of chromatic polynomials," *Canad. J. Math.* 6, 80–91, 1954.
- **链接**：[DOI: 10.4153/CJM-1954-005-4](https://doi.org/10.4153/CJM-1954-005-4)
- **核心贡献**：
  - 引入 Tutte 多项式（最初称 dichromatic polynomial）
  - 建立色多项式与特征多项式的关系
  - Möbius 反演在图着色中的最早应用
- **对本文的意义**：T(N,k) 可视为 Tutte 多项式在"共享边数"维度的投影

#### [4] Reiner 1999 — Tutte 多项式的组合解释

- **文献**：V. Reiner, "An interpretation for the Tutte polynomial," *European J. Combin.* 20(4), 307–316, 1999.
- **链接**：[全文 PDF](https://www.math.ucdavis.edu/~deloera/MISC/LA-BIBLIO/trunk/ReinerVictor/Reiner1.pdf)
- **核心贡献**：
  - 给出 Tutte 多项式 T_M(x,y) 的统一组合解释
  - 显式使用 Möbius 反演连接色多项式、流多项式与圈空间
  - 推广了 Tutte, Greene, Jaeger 等人的多个特例
- **关键公式**：`N_=(G) = Σ_{H∈L'(G)} μ(G,H)·N_≥(H)` — 与本文 T(N,k) 的反演结构完全同构

### 2.2 圈空间与圈基（4 篇核心）

#### [5] Kavitha et al. 2009 — 最权威综述

- **文献**：T. Kavitha, C. Liebchen, K. Mehlhorn 等, "Cycle Bases in Graphs — Characterization, Algorithms, Complexity, and Applications," *Computer Science Review* 3(4), 199–243, 2009.
- **链接**：[DOI: 10.1016/j.cosrev.2009.08.001](https://doi.org/10.1016/j.cosrev.2009.08.001)
- **核心贡献**（196 次引用）：
  - 全面综述圈空间的各类基：无向/有向/整数/严格基本
  - 用圈矩阵 (cycle matrix) 刻画不同基类
  - 最小权圈基的多项式算法 + 严格基本基的 APX-hard 性
  - 三大应用：电网络、化学/生物路径、周期调度
- **关键定理**：圈空间维数 = m - n + c（c=连通分量数）

#### [6] Radcliffe 2018 — 入门讲义

- **文献**：M. Radcliffe, "Cycle Bases," CMU 讲义, 2018.
- **链接**：[PDF 全文](https://www.math.cmu.edu/~mradclif/teaching/241F18/CycleBases.pdf)
- **核心内容**：
  - 从生成树 → 非树边 → 基本圈的构造过程
  - Lemma: 每条非树边 e 与生成树 T 形成唯一基本圈 C_e
  - Kirchhoff 电压定律应用：只需在基本圈组上验证
- **阅读建议**：最佳入门材料，1 小时可读完

#### [7] Mehlhorn 2008 — 演讲 slides

- **文献**：K. Mehlhorn, "Cycle Bases in Graphs: Structure, Algorithms, Applications, Open Problems," MPI 演讲, 2008.
- **链接**：[Slides PDF](http://www.graphalgorithms.org/erice2008/Talks/CycleBasisTalk_Mehlhorn.pdf)
- **核心内容**（56 页）：
  - 结构定理：有向/无向/整数基的统一描述
  - 权界：最小权圈基的总权上下界
  - 生成树基 NP 完全（Deo et al. 1982）
  - 严格基本基 APX-hard

#### [8] Kavitha-Mehlhorn-Michail 2008 — 近似算法

- **文献**：T. Kavitha, K. Mehlhorn, D. Michail, "New Approximation Algorithms for Minimum Cycle Bases of Graphs."
- **链接**：[PDF 全文](https://d-michail.github.io/assets/papers/approxmcb-journal.pdf)
- **核心贡献**：
  - (2k-1)-近似算法，运行时间 O(kmn^{1+2/k} + mn^{(1+1/k)(ω-1)})
  - 2-近似算法，平面图线性时间
  - 应用：电网络分析、结构工程、化学、曲面重建

### 2.3 Möbius 反演在图论中的前沿应用（3 篇）

#### [9] Cooper-Okur 2025 — Euler 有向图的圈分拆

- **文献**：J. Cooper, U. Okur, "Partitions of an Eulerian Digraph into Circuits," arXiv:2502.00867, 2025.
- **链接**：[arXiv 全文](https://arxiv.org/abs/2502.00867)
- **核心贡献**：
  - 在 Euler 有向图边集的分拆格上使用 Whitney-Rota Möbius 函数
  - 证明取消性质：Σ(-1)^t·|𝕮_t(D)| = 0（除非 D 是单圈）
  - 连接 bond lattice L(G) 与 Heaps of Pieces 理论
  - 应用：推导 Harary-Sachs 定理
- **与本文联系**：圈分拆格上的 Möbius 反演 ↔ T(N,k) 的二项式反演

#### [10] Lavee-Linial 2025 — Time to Cycle

- **文献**：N. Lavee, N. Linial, "Time to Cycle," arXiv:2512.12852, 2025.
- **链接**：[arXiv 全文](https://arxiv.org/abs/2512.12852)
- **核心贡献**：
  - 用 Möbius 反演计算随机图中边 e₁ 加入圈的时间期望 E[T] = n
  - 推广到所有拟阵（matroid）
  - 展示反演在随机图过程中的威力
- **关键公式**：`g(H) = Σ_{B∈ℱ, H⊆B} μ(H,B)·f(B)` — 标准偏序集反演

#### [11] 2017 — Tutte 多项式极端系数

- **文献**："Several extreme coefficients of the Tutte polynomial of graphs," arXiv:1705.10023, 2017.
- **链接**：[arXiv 全文](https://arxiv.org/abs/1705.10023)
- **核心贡献**：
  - 显式使用 Möbius 反演定理：`N_=(G) = Σ_{H∈L'(G)} μ(G,H)·N_≥(H)`
  - "至少→恰好"反演在图计数中的直接范例
  - 与本文 T(N,k) 的反演结构完全平行

### 2.4 Tutte 多项式与格的 Möbius 函数（2 篇进阶）

#### [12] Wakefield 2023 — Chain Tutte 多项式

- **文献**：M. Wakefield, "Chain Tutte polynomials," arXiv:2305.02874, 2023.
- **链接**：[arXiv 全文](https://arxiv.org/abs/2305.02874)
- **核心贡献**：
  - 用 Möbius 多项式统一 Tutte 多项式与特征多项式
  - 给出 bond lattice（图的割格）上 Möbius 函数的新递推
  - 连接 Derksen 𝒢-不变量与 Tutte 多项式
- **进阶价值**：理解 bond lattice 的 Möbius 函数如何编码图的圈结构

#### [13] Hobbs-Oxley 2003 — Tutte 纪念文集

- **文献**：A. M. Hobbs, J. G. Oxley, "WILLIAM T. TUTTE, 1917–2002," 2003.
- **链接**：[PDF 全文](https://www.math.lsu.edu/~oxley/ahjo.pdf)
- **核心内容**：
  - Tutte 生平与学术贡献综述
  - dichromatic polynomial → Tutte 多项式的历史脉络
  - Whitney → Crapo → Rota 的发展谱系
  - 圈空间与拟阵理论的联系

### 2.5 中文参考（2 篇）

#### [14] 许胤龙 — 图论导引

- **核心内容**：第 10 章图矩阵与图空间，系统讲边空间、圈空间、基本圈组、割空间
- **链接**：[CSDN 笔记](https://blog.csdn.net/weixin_52921802/article/details/122223044)
- **适用**：中文入门圈空间概念

#### [15] 柯召, 魏万迪 — 组合论（上册）

- **核心内容**：容斥原理与圆周排列基础章节，中文 Möbius 反演入门
- **ISBN**：9787030287052
- **适用**：中文学习容斥原理的基础理论

---

## 三、核心公式对照表

### 3.1 反演公式家族

| 反演类型 | 叠加公式 | 反演公式 | 偏序集 | 文献来源 |
|---------|---------|---------|-------|---------|
| 容斥原理 | E(j) = Σ_{k≥j} T(k) | T(k) = Σ_{j≥k} (-1)^{j-k}·E(j) | 子集格 | Rota [1] |
| 二项式反演 | E(j) = Σ_{k≥j} C(k,j)·T(k) | T(k) = Σ_{j≥k} (-1)^{j-k}·C(j,k)·E(j) | 自然数链 | Stanley [2] |
| 数论 Möbius | g(d) = Σ_{d\|e\|n} f(e) | f(d) = Σ_{d\|e\|n} μ(n/e)·g(e) | 整除格 | Rota [1] |
| 图格反演 | N_≥(H) = Σ_{G'⊇H} N_=(G') | N_=(G) = Σ μ(G,H)·N_≥(H) | 子图格 | Reiner [4] |
| Bond lattice | N_≥(H) = Σ_{G'∈L'(G)} N_=(G') | N_=(G) = Σ μ(G,H)·N_≥(H) | Bond lattice | Tutte [3] |
| **本文 T(N,k)** | **E(N,j) = Σ_{k≥j} C(k,j)·T(N,k)** | **T(N,k) = Σ_{j≥k} (-1)^{j-k}·C(j,k)·E(N,j)** | **自然数链** | **本文** |

### 3.2 圈空间公式

| 公式 | 含义 | 文献来源 |
|------|------|---------|
| dim(C(G)) = m - n + c | 圈空间维数（c=连通分量） | Kavitha [5] |
| C_e = e + path_T(e) | 基本圈（非树边 + 树路径） | Radcliffe [6] |
| 任意圈 = XOR(某些基本圈) | 圈空间的基分解 | Veblen 定理 |
| T(G;1,1) = #生成树 | Tutte 多项式在 (1,1) 的值 | Tutte [3] |
| T(G;2,0) = #无环定向 | Tutte 多项式在 (2,0) 的值 | Reiner [4] |
| P(G,q) = (-1)^n·T(G;1-q,0) | 色多项式 = Tutte 多项式特例 | Tutte [3] |

### 3.3 本文 T(N,k) 公式体系

| 公式 | 含义 | 文献来源 |
|------|------|---------|
| f(N,j,b) = N/b·C(j-1,b-1)·C(N-j-1,b-1) | Kaplansky 环上选边段数 | Kaplansky 1944 |
| E(N,j) = N·(N-j-1)!·Σ_b f(N,j,b)·2^b | 至少含 j 条 C_N 边的排列数 | 本文 |
| T(N,k) = Σ_{j=k}^{N} (-1)^{j-k}·C(j,k)·E(N,j) | 恰好含 k 条 C_N 边的排列数 | 本文 |
| T(N,N) = 2N | 满分定理 | 本文 |
| T(N,N-1) = 0 | 空缺定理 | 本文 |
| Σ_k T(N,k) = N! | 行和恒等式 | 本文 |

---

## 四、推荐阅读路线

### 4.1 入门路线（零基础 → 理解圈空间）

```
第 1 步：Radcliffe 讲义 [6]           （1-2 小时）
         → 理解生成树、基本圈、圈空间维数
         
第 2 步：许胤龙《图论导引》第 10 章 [14]  （2-3 小时）
         → 中文巩固边空间、圈空间、割空间概念
         
第 3 步：Kavitha 综述 [5] 前半部分       （3-4 小时）
         → 圈基分类、圈矩阵、应用场景
```

### 4.2 理论路线（理解 Möbius 反演框架）

```
第 1 步：Rota 1964 [1]                  （精读，1 天）
         → Möbius 反演的一般框架
         → 理解 μ 函数的定义与性质
         
第 2 步：Stanley EC1 Ch.3 [2]           （精读 3.1-3.7, 3.10）
         → 偏序集上的系统理论
         → 几何格、分拆格的 Möbius 函数
         
第 3 步：Tutte 1954 [3]                 （精读）
         → 色多项式与特征多项式
         → 图格上的反演
         
第 4 步：Reiner 1999 [4]                （精读）
         → Tutte 多项式的统一组合解释
         → 理解 N_=(G) = Σ μ(G,H)·N_≥(H)
```

### 4.3 前沿路线（追踪最新应用）

```
第 1 步：Cooper-Okur 2025 [9]           （Euler 图圈分拆）
         → Bond lattice + Heaps of Pieces
         
第 2 步：Lavee-Linial 2025 [10]         （Time to Cycle）
         → 随机图过程 + Möbius 反演
         
第 3 步：Wakefield 2023 [12]            （Chain Tutte）
         → Bond lattice Möbius 函数递推
         
第 4 步：arXiv:1705.10023 [11]          （Tutte 极端系数）
         → "至少→恰好"反演的直接范例
```

### 4.4 本文 T(N,k) 的定位路线

```
Kaplansky 1944 (环上组合引理)
    ↓
Rota 1964 [1] (Möbius 反演框架)
    ↓
Stanley EC1 [2] (二项式反演 = 自然数链上的 Möbius)
    ↓
Reiner 1999 [4] (图格反演 N_= = Σ μ·N_≥)
    ↓
Barghi 2018 (图型 Stirling 数)
    ↓
Yaqubi 2026 (C_n 闭式)
    ↓
本文 T(N,k) (Hamilton 圈族 × C_N 的容斥反演)
```

### 4.5 算法实践路线

```
第 1 步：本文 STAT_001 (全排列枚举 O(N!))
         → 理解问题的暴力解法
         
第 2 步：本文 STAT_006 (位掩码 DP O(2^N·N³))
         → 理解状态压缩 + DP
         
第 3 步：本文 STAT_007 (稀疏 DP)
         → 理解空间优化
         
第 4 步：本文 STAT_008 (闭式公式 O(N²))
         → 理解容斥反演的计算威力
         
第 5 步：Kavitha 综述 [5] 后半部分
         → 圈基算法的复杂度分析
```

---

## 五、文献间的学术脉络

```
Whitney (1935) ──→ 图拟阵定义
    │
Tutte (1947,1954) ──→ Tutte 多项式 + 色多项式
    │                    │
    │              Crapo (1968) ──→ 推广到拟阵
    │                    │
Rota (1964) ──→ Möbius 反演一般框架
    │                    │
    │              Stanley (1986) ──→ EC1 系统化
    │                    │
    ├──── Reiner (1999) ──→ Tutte 多项式组合解释
    │                    │
    ├──── Kavitha-Mehlhorn (2009) ──→ 圈基算法综述
    │                    │
    ├──── Barghi (2018) ──→ 图型 Stirling 数
    │                    │
    ├──── Yaqubi (2026) ──→ C_n 闭式
    │                    │
    ├──── Cooper-Okur (2025) ──→ Euler 图圈分拆
    │                    │
    └──── Lavee-Linial (2025) ──→ Time to Cycle
    
    ═══════════════════════════════
    本文 T(N,k) ──→ Hamilton 圈 × C_N 容斥反演
    ═══════════════════════════════
```

**关键传承线**：
1. **理论线**：Whitney → Tutte → Rota → Stanley → Reiner（Möbius 反演框架）
2. **算法线**：Horton → de Pina → Kavitha → Mehlhorn（圈基算法）
3. **应用线**：Kaplansky → Barghi → Yaqubi → 本文（环上组合 → 图型 Stirling → T(N,k)）

---

## 六、核心洞察总结

### 6.1 三个层次的统一

```
圈空间基分解（GF(2) 线性代数）
    ↕ 圈空间是 bond lattice 的 GF(2) 投影
格论 Möbius 反演（偏序集理论）
    ↕ 自然数链是偏序集的特例
二项式反演（本文 T(N,k)）
```

每一层都是上一层的特例，但每一层都有独特的计算优势：
- 圈空间层：O(m·n) 构造基本圈
- 格论层：Tutte 多项式统一所有图不变量
- 计数层：O(N²) 闭式公式

### 6.2 "基分解 = 反演"的深层联系

```
基分解：找出基 → 线性组合 → 任意对象
反演：  叠加态 → 反演公式 → 基础层

本质相同：都是从"复合"恢复"基本成分"的操作
区别：基分解是空间视角（线性代数），反演是计数视角（组合学）
统一：Möbius 反演是两者的共同推广
```

### 6.3 本文 T(N,k) 的学术定位

| 定位维度 | 描述 |
|---------|------|
| **数学结构** | 二项式反演在 Hamilton 圈族上的应用 |
| **偏序集** | 自然数链 {0,1,...,N}（最简单的偏序集） |
| **叠加核** | C(k,j)（二项式系数） |
| **反演核** | (-1)^{j-k}·C(j,k) |
| **基元素** | T(N,k)（恰好 k 条共享边的排列数） |
| **参考圈** | C_N（固定的 n 圈） |
| **图论联系** | Bond lattice 上 Möbius 函数的投影 |
| **算法价值** | O(N²) 闭式 vs O(2^N·N³) DP |
| **新意** | 首次给出共享边数分布的完整闭式 |

### 6.4 一句话总结

> **从 Rota 1964 到本文 T(N,k)，Möbius 反演提供了一条从"看似无规律的叠加统计"到"有规律的基础分布"的统一通道——圈空间用线性代数分解，图格用 Möbius 函数反演，本文用二项式反演，三者同源。**

---

## 七、完整文献索引

| 编号 | 作者 | 年份 | 简称 | 链接 |
|------|------|------|------|------|
| [1] | G.-C. Rota | 1964 | Möbius 反演奠基 | [DOI](https://doi.org/10.1007/BF00531932) |
| [2] | R. P. Stanley | 2011 | EC1 Ch.3 偏序集理论 | [Cambridge](https://www.cambridge.org/core/books/enumerative-combinatorics/9A9A3B9C8ECB6BE33D03B0A2DE6F4F28) |
| [3] | W. T. Tutte | 1954 | 色多项式 | [DOI](https://doi.org/10.4153/CJM-1954-005-4) |
| [4] | V. Reiner | 1999 | Tutte 多项式解释 | [PDF](https://www.math.ucdavis.edu/~deloera/MISC/LA-BIBLIO/trunk/ReinerVictor/Reiner1.pdf) |
| [5] | Kavitha et al. | 2009 | 圈基综述 | [DOI](https://doi.org/10.1016/j.cosrev.2009.08.001) |
| [6] | M. Radcliffe | 2018 | 圈基讲义 | [PDF](https://www.math.cmu.edu/~mradclif/teaching/241F18/CycleBases.pdf) |
| [7] | K. Mehlhorn | 2008 | 圈基演讲 | [PDF](http://www.graphalgorithms.org/erice2008/Talks/CycleBasisTalk_Mehlhorn.pdf) |
| [8] | Kavitha-Mehlhorn-Michail | 2008 | 近似算法 | [PDF](https://d-michail.github.io/assets/papers/approxmcb-journal.pdf) |
| [9] | Cooper-Okur | 2025 | Euler 图分拆 | [arXiv](https://arxiv.org/abs/2502.00867) |
| [10] | Lavee-Linial | 2025 | Time to Cycle | [arXiv](https://arxiv.org/abs/2512.12852) |
| [11] | — | 2017 | Tutte 极端系数 | [arXiv](https://arxiv.org/abs/1705.10023) |
| [12] | M. Wakefield | 2023 | Chain Tutte | [arXiv](https://arxiv.org/abs/2305.02874) |
| [13] | Hobbs-Oxley | 2003 | Tutte 纪念 | [PDF](https://www.math.lsu.edu/~oxley/ahjo.pdf) |
| [14] | 许胤龙 | — | 图论导引 | [CSDN](https://blog.csdn.net/weixin_52921802/article/details/122223044) |
| [15] | 柯召, 魏万迪 | 1981 | 组合论 | — |

---

## 八、实践资源

| 资源 | 文件 | 说明 |
|------|------|------|
| 全排列枚举 | [STAT_001](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_001_全组合环形相邻词频.bas) | O(N!) 暴力基线 |
| 位掩码 DP | [STAT_006](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_006_总表特点分析.bas) | O(2^N·N³) DP |
| 稀疏 DP | [STAT_007](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_007_稀疏DP.bas) | 空间优化 DP |
| 闭式公式 | [STAT_008](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_008_闭式公式.bas) | O(N²) 容斥反演 |
| 基础图元叠加 | [STAT_009](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_009_基础图元叠加分解.py) | Python 圈空间可视化 |
| 公式推导 | [推导文档](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_T_Nk_闭式公式完整推导.md) | 从零到闭式的完整证明 |
| 基分解思想 | [思想总结](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_基分解思想总结.md) | 基分解 vs 容斥 vs Möbius |
