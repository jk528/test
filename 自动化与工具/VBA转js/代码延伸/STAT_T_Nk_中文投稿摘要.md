# 中文投稿摘要稿

> 注：投稿前请填写作者姓名、单位、联系方式、基金项目等。
> 数值验证结果（n ≤ 16 与穷举 DP 逐点核对，n ≤ 500 行和恒等式验证）见 STAT_008 闭式公式.js / .bas。
> 对应英文版见 STAT_T_Nk_英文投稿摘要.md。

---

## 标题

**K_n 中随机 Hamilton 圈与参考 n 圈共享边数的精确分布**

（论坛短文版：**一个新的组合三角表 T(n,k) —— 计数恰有 k 个距离为 1 或 n−1 的环形相邻对的 [n] 排列**）

---

## 作者

[作者 1]，[作者 2]，……  
单位：……  
Email：……  
ORCID：……（arXiv / 国内核心期刊推荐）

---

## 中国图书馆分类号 (CLC) 与 MSC 2020

**CLC：O157.1（组合数学）· O157.5（图论枚举）**

**MSC 2020（国际数学分类号）**
- 主类：**05A05** —— 排列、字、矩阵
- 子类：**05A15** —— 精确计数问题、生成函数
- 子类：**05C30** —— 图论中的枚举
- 子类：**05C38** —— 路与圈
- 子类：**05A19** —— 组合恒等式、双射组合学

---

## 关键词

排列统计量 · 环形相邻 · Hamilton 圈交集 · 圈图 C_n · 容斥原理 · Kaplansky 圆周引理 · 图型 Stirling 数 · 受限排列计数 · 精确分布 · 组合三角表

---

## 摘要

> **字数约 500 字，符合中文核心期刊标准格式。**

设 $C_n$ 为顶点集 $[n]=\{1,2,\dots,n\}$ 上的标号圈图，其边集为 $E(C_n)=\{1,2\}, \{2,3\}, \dots, \{n{-}1, n\}, \{n, 1\}$。每个排列 $\pi \in S_n$ 对应 $K_n$ 中的一条有向 Hamilton 圈，由 $n$ 个无序相继对 $\{\pi(i), \pi(i{+}1)\}$（下标模 $n$）给出。本文引入组合三角表 $T(n, k)$（$0 \le k \le n$），其值为排列的 Hamilton 边集与 $E(C_n)$ 恰好交 $k$ 条边的排列数，即按 $[n]$ 的自然环序恰有 $k$ 对距离为 $1$ 或 $n{-}1$ 的环形相邻关系得到保持的排列数。

利用图论化重述结合 Kaplansky（1943）的圆周选边分段经典引理（即在圆周上选 $j$ 条边恰形成 $b$ 个相邻黑段的方式数为 $f(n,j,b)=\frac{n}{b}\binom{j{-}1}{b{-}1}\binom{n{-}j{-}1}{b{-}1}$），本文首先推导出容斥原像和的闭式表达式：

$$
E(n,j) = \sum_{|S|=j}\bigl|\{\pi : S \subseteq E(\pi)\}\bigr| \;=\; n \cdot (n{-}j{-}1)! \;\cdot\; \sum_{b=1}^{\min(j,n-j)} f(n,j,b) \cdot 2^b,
\qquad 1 \le j \le n{-}1,
$$

加上边界情形 $E(n,0)=n!$ 与 $E(n,n)=2n$。应用标准二项式反演（恰好 $k$ 条的容斥公式）得到通用闭式：

$$
T(n,k) \;=\; \sum_{j=k}^{n}\; (-1)^{j-k}\binom{j}{k}\, E(n,j), \qquad 0 \le k \le n,
$$

并由此直接证明端点精确公式：对任意 $n \ge 3$，有 $T(n,n)=2n$（满分排列为 $2 \times n$ 种）及 $T(n,n{-}1)=0$（缺一条边的排列恒不存在）。

**验证结果：**（1）逐点验证：对 $n \le 16$ 与位掩码 DP 穷举结果逐格比对（累计覆盖超过 200 亿个排列），所有值完全吻合；（2）行和恒等式：对 $n \le 500$ 使用任意精度 BigInt 验证 $\sum_k T(n,k)=n!$ 及端点公式均精确成立。

**复杂度改进：** 原算法为 $O(2^n \cdot n^3)$ 的位掩码 DP，可行 $n$ 上限约为 18；本闭式公式算法为 $O(n^2)$，可行 $n$ 不再受算法限制。文末说明本三角表与 Yaqubi & Mirzavaziri（2026）新近提出的圈图 C_n 的图型 r-Stirling 数之间的结构性联系，以及为何它虽与 OEIS A180188（环形连续升序数）的满分列恰差 2 倍，但对一般 $k$ 并不具简单倍数关系，因而是一个 OEIS 尚未收录的新组合三角表。

**关键词（英文）**：Permutation statistics; cyclic adjacency; Hamiltonian cycle intersection; cycle graph C_n; inclusion–exclusion principle; Kaplansky's circular lemma.

---

## 1. 引言范文（首段）

> 约 400 字，可直接贴入中文期刊论文首页第一节。

$n$ 个元素的随机排列按 $[n]$ 的自然环序 $1{-}2{-}\cdots{-}n{-}1$ 能保留多少个**局部邻接关系**？这是一个经典而直观的问题。对于不动点（即 $\pi(i)=i$），已有完善的 derangement 理论和容斥解答；对于线性相邻"击中"（$\pi(i{+}1)=\pi(i)+1$），Possibly Wrong 博客[1] 利用期望的线性性质给出了期望值：线性情形为 $\frac{n-1}{n}$，环形情形恰好等于 1，且与 $n$ 无关。然而除了**一阶矩**，我们对相邻保留数的**精确分布**所知甚少——当问及"随机排列恰有 $k$ 个环形相邻对被保留的概率是多少"时，现有文献和 OEIS 序列库并未给出完整答案。

本问题可以等价地重述为图论问题：在标号完全图 $K_n$ 中固定一条参考 Hamilton 圈 $C_n$，所有剩余的 $(n{-}1)!/2$ 条无向 Hamilton 圈（即 $n!$ 条有向圈）各与 $C_n$ 共享多少条边？这一表述使问题直接进入"图型 Stirling 数"[2, 6] 的研究范畴，后者针对任意图 $G$ 计数其顶点分拆为 $k$ 个受 $G$ 边集支持的圈的方式数；当 $G=C_n$ 且 $k=1$（即 Hamilton 圈情形），Yaqubi 和 Mirzavaziri[2] 最近给出了 $[C_n/k]$ 的显式公式，其分子结构与 Kaplansky 1943 年[3]的圆周不相邻组合公式完全相同——这正是本文推导的关键桥梁。本文将该计数框架进一步细化为**共享边数**的分布，从而获得整张组合三角表的闭式表达，并辅以大尺度数值验证。

---

## 基金 / 致谢（可选）

**基金项目**：若受基金资助，按格式填写（例：国家自然科学基金 No. ××××××××）

**致谢**：感谢 [XX] 对组合恒等式部分提出的宝贵意见；感谢 OEIS 社区提供的数据查询服务；感谢开源 JS BigInt / VBA Decimal 运行时使大 $n$ 验证得以便捷实现。

---

## 参考文献（起始列表，投稿前请按目标期刊格式扩展并重编号）

```
[1] Possibly Wrong, "Coincidences in random shuffling revisited",
    2013.
    https://possiblywrong.wordpress.com/2013/03/18/coincidences-in-random-shuffling-revisited/

[2] D. Yaqubi, M. Mirzavaziri, "On the Graphical r-Stirling Numbers of
    the First Kind for Specific Graph Families,"
    arXiv:2602.02046 [math.CO], 2026 年 2 月.
    https://arxiv.org/abs/2602.02046
    (该文给出 C_n 的图型 Stirling 数 [C_n/k] = n/k · C(k, n−k)，
     与本文 f(n,j,b) 公式结构完全一致)

[3] I. Kaplansky, "Symbolic solution of certain problems in permutations,"
    Bulletin of the American Mathematical Society, vol. 50, no. 12,
    pp. 906–914, December 1944.
    DOI: 10.1090/S0002-9904-1944-08261-X
    https://doi.org/10.1090/S0002-9904-1944-08261-X
    (Kaplansky 圆周选边分段引理原始文献；
     相关姊妹篇：同作者 "Solution of the problème des ménages,"
     Bull. Amer. Math. Soc. 49 (1943), 784–785,
     https://doi.org/10.1090/S0002-9904-1943-08011-8 )

[4] J. Riordan, An Introduction to Combinatorial Analysis,
    John Wiley & Sons, New York, 1958; reprinted by Dover, 2002
    (Dover 平装版 ISBN: 0486425363).
    Google Books:
    https://books.google.com/books?id=R6oZAQAAIAAJ
    书评 DOI: 10.1017/S0020268100037914
    (中译本《组合分析导论》，第 7 章 圆周排列与容斥)

[5] N. J. A. Sloane 等, The On-Line Encyclopedia of Integer Sequences,
    2026 年发布, https://oeis.org .
    相关序列直达链接：
      A034807 — C_n 的 k-matchings / Kaplansky 不相邻圆周组合数
         https://oeis.org/A034807
      A180188 — 环形连续升序继承数 triangle (本文 T(n,k)/2 仅 n=n/2 对应)
         https://oeis.org/A180188
      A001710 — 交错群阶 = n!/2，即 (n+1) 顶点上标号连通 2-正则图数
         https://oeis.org/A001710

[6] A. Barghi, "Stirling numbers of the first kind for graphs,"
    Australasian Journal of Combinatorics, vol. 70, part 2,
    pp. 253–268, 2018. (图型 Stirling 数原创定义论文)
    AJC 开放获取全文：
    http://ajc.maths.uq.edu.au/?page=get_volumes&volume=70#vol70_2
    (注：Yaqubi & Mirzavaziri [2] 中将此原始定义扩展为 r-Stirling 情形；
     D. DeFord 的后续工作可一并参考：
     K. J. Gonzales, "Cyclic and Linear Graph Partitions and Normal Ordering,"
     arXiv:2106.08069 [math.CO], 2021.
     https://arxiv.org/abs/2106.08069 )

[7] 柯召, 魏万迪, 《组合论》（上册）,
    科学出版社, 北京, 1981.
    ISBN: 9787030287052 (2010 年重印版)
    豆瓣图书链接：https://book.douban.com/subject/3315046/
    (中文参考，容斥原理、圆周排列与错位问题基础章节)

[8] 屠规彰, 《组合计数方法及其应用》,
    科学出版社, 北京, 1981.
    豆瓣图书链接：https://book.douban.com/subject/2269958/
    中国国家图书馆馆藏记录：
    http://opac.nlc.cn/F?func=find-b&request=%E5%B1%A0%E8%A7%84%E5%BD%B0+%E7%BB%84%E5%90%88%E8%AE%A1%E6%95%B0%E6%96%B9%E6%B3%95&find_code=WRD
```

---

## 投稿前自检清单

- [ ] 作者、单位、**通信作者 Email** 完整填写
- [ ] 基金项目号 / 致谢内容（若有）补齐
- [ ] **国内期刊投稿建议**：
  - 《数学学报》（中文版）、《应用数学学报》可投"短文/研究简报"栏目
  - 《高校应用数学学报》、《数学杂志》适合偏组合/图论方向
  - 一般要求公式用 Word 公式编辑器或 LaTeX，正文宋体五号
- [ ] **arXiv 投稿建议**：直接用英文版，选 `math.CO`（组合数学），可选交叉 `cs.DM`
- [ ] **中文数学论坛 / 社区发帖**：
  - 知乎"数学"专栏 + 标签「组合数学」「排列组合」，用短文标题版
  - 数学研发论坛 (emath.ac.cn) "组合数学"板块
- [ ] **数据/代码公开声明**（建议加）：
  > "本文数值验证与公式计算的参考实现（VBA Decimal 版支持 n ≤ 27，JavaScript BigInt 版支持任意 n）可从 [仓库地址 / 通讯作者索取] 获得，所有表格和三角表数值可完全复现。"
