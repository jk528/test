# T(N,k) 递推关系伪代码与数学原理标注

> 从 Kaplansky 引理到闭式公式的完整计算流程
> 每一步标注对应的数学原理和文献来源
> 日期：2026-08-11

---

## 一、完整计算流程伪代码

```
算法：计算三角表 T(N,k) for N=1..N_max, k=0..N

输入：N_max（最大 N 值）
输出：T[N][k]（恰好 k 条共享边的排列数）

═══════════════════════════════════════════════════════════════
步骤 0：预处理 — 组合数表
═══════════════════════════════════════════════════════════════

【数学原理】帕斯卡恒等式 C(n,k) = C(n-1,k-1) + C(n-1,k)
【文献来源】Stanley EC1 Ch.1

FOR n = 0 TO N_max:
    C[n][0] = 1
    C[n][n] = 1
    FOR k = 1 TO n-1:
        C[n][k] = C[n-1][k-1] + C[n-1][k]
    END FOR
END FOR

═══════════════════════════════════════════════════════════════
步骤 1：阶乘表
═══════════════════════════════════════════════════════════════

【数学原理】n! = n × (n-1)!
【精度要求】N≤18 用 Double, N≤27 用 Decimal, N>27 用 BigInt

fact[0] = 1
FOR n = 1 TO N_max:
    fact[n] = fact[n-1] * n
END FOR

═══════════════════════════════════════════════════════════════
步骤 2：Kaplansky 环上选边段数 f(N,j,b)
═══════════════════════════════════════════════════════════════

【数学原理】Kaplansky 圆周选边引理
  在 N 条边的圆上选 j 条，形成恰好 b 条连续路径段的方式数
  f(N,j,b) = N/b · C(j-1, b-1) · C(N-j-1, b-1)

【推导逻辑】
  (1) j 条黑边分成 b 段：在 j-1 个间隙中选 b-1 个分割点 → C(j-1, b-1)
  (2) N-j 条白边分成 b 段：在 N-j-1 个间隙中选 b-1 个分割点 → C(N-j-1, b-1)
  (3) 圆周旋转：固定起点 N 种，每配置被计算 b 次 → N/b

【文献来源】Kaplansky 1944, Bull. Amer. Math. Soc. 50(12), 906-914
【约束条件】1 ≤ b ≤ min(j, N-j)，且 j ≥ 1, N-j ≥ 1

FUNCTION f(N, j, b):
    IF b < 1 OR b > min(j, N-j) THEN RETURN 0
    IF j < 1 OR N-j < 1 THEN RETURN 0
    RETURN (N / b) * C[j-1][b-1] * C[N-j-1][b-1]
END FUNCTION

═══════════════════════════════════════════════════════════════
步骤 3：至少 j 条边的排列数 E(N,j)
═══════════════════════════════════════════════════════════════

【数学原理】容斥原理的"叠加态"计算
  E(N,j) = 所有"至少包含 j 条 C_N 边"的 Hamilton 圈排列数

【推导逻辑】
  (1) 选 j 条 C_N 边 → 形成 b 条连续段（用 f(N,j,b) 计数）
  (2) 每段是一个"超级块"，内部有 2 个方向 → 2^b
  (3) b 个超级块 + (N-j-b) 个单顶点块 = (N-j) 个块 → (N-j-1)! 种环形排列
  (4) 固定起点 N（已在 f 中计入），故排列数 = (N-j-1)! × 2^b

  E(N,j) = Σ_b f(N,j,b) × 2^b × (N-j-1)!
         = N × (N-j-1)! × Σ_b [1/b × C(j-1,b-1) × C(N-j-1,b-1) × 2^b]

【特殊情形】
  E(N,0) = N!   （所有排列都"至少含 0 条边"）
  E(N,N) = 2N   （满分排列 = 2方向 × N起点，已由 f(N,N,1)=N 验证）

【文献来源】本文推导，基于 Kaplansky 1944 + 容斥原理

FUNCTION E(N, j):
    IF j == 0 THEN RETURN fact[N]              // 所有排列
    IF j == N THEN RETURN 2 * N                // 满分：2方向×N起点
    
    sum = 0
    FOR b = 1 TO min(j, N-j):                  // 遍历段数
        fb = f(N, j, b)                        // Kaplansky 引理
        sum = sum + fb * power(2, b)           // 每段 2 方向
    END FOR
    
    RETURN N * fact[N-j-1] * sum               // 超级块的环形排列
END FUNCTION

═══════════════════════════════════════════════════════════════
步骤 4：二项式反演 — 从 E(N,j) 到 T(N,k)
═══════════════════════════════════════════════════════════════

【数学原理】Möbius 反演在自然数链上的特例 — 二项式反演

  叠加关系：E(N,j) = Σ_{k≥j} C(k,j) × T(N,k)
    含义："至少 j 条边" = Σ "恰好 k 条边" × C(k,j)
    解释：恰好 k 条边的排列中，任选 j 条作为"指定的至少 j 条" → C(k,j)

  反演公式：T(N,k) = Σ_{j≥k} (-1)^{j-k} × C(j,k) × E(N,j)
    含义：从容斥和中恢复"恰好 k 条"
    符号：(-1)^{j-k} 是 Möbius 函数 μ(j,k) = (-1)^{j-k} × C(j,k)

【文献来源】
  Rota 1964 — Möbius 反演一般框架 (Z. Wahrsch. 2, 340-368)
  Stanley 2011 — EC1 Ch.3, 二项式反演是子集格上的 Möbius 反演
  Reiner 1999 — N_=(G) = Σ μ(G,H)·N_≥(H) 的平行结构

【验证条件】
  行和：Σ_k T(N,k) = N!   （Parseval 恒等式的类比）
  满分：T(N,N) = E(N,N) = 2N   （反演在 j=N 时只有一项）
  空缺：T(N,N-1) = E(N,N-1) - N×E(N,N)   （代数推导得 0）

FUNCTION T(N, k):
    IF k > N THEN RETURN 0
    
    result = 0
    FOR j = k TO N:                            // 容斥反演
        sign = (-1) ^ (j - k)                  // Möbius 函数符号
        coeff = C[j][k]                         // 二项式系数
        ej = E(N, j)                            // 叠加态
        result = result + sign * coeff * ej
    END FOR
    
    RETURN result
END FUNCTION

═══════════════════════════════════════════════════════════════
步骤 5：端点闭式（快速验证）
═══════════════════════════════════════════════════════════════

【定理 1：满分定理】T(N,N) = 2N

【数学原理】组合论证
  恰好 N 条共享边 = Hamilton 圈的边集 = C_N 的边集
  → 排列必须沿 C_N 方向（正向或反向）× N 个起点 = 2N

【反演验证】
  T(N,N) = Σ_{j=N}^{N} (-1)^{N-N}·C(N,N)·E(N,N) = 1·1·2N = 2N  ✓

FUNCTION T_perfect(N):
    IF N < 3 THEN RETURN special_case(N)      // N=1:1, N=2:2
    RETURN 2 * N
END FUNCTION

──────────────────────────────────────────────────────────────

【定理 2：空缺定理】T(N,N-1) = 0

【数学原理】组合论证
  N-1 条边覆盖所有 N 个顶点（形成一条路径）
  路径的端点唯一确定，闭合的边恰好是缺失的那条
  → 第 N 条边必然也被选中 → 矛盾（不可能恰好 N-1 条）

【反演验证】
  T(N,N-1) = E(N,N-1) - (N-1)×E(N,N)

  E(N,N-1) = N × 1! × f(N,N-1,1) × 2^1
            = N × 1 × [N/1 × C(N-2,0) × C(0,0)] × 2
            = N × N × 2 = 2N²

  T(N,N-1) = 2N² - (N-1) × 2N = 2N² - 2N² + 2N = 2N

  ⚠️ 等等，这给出 2N 不是 0！需要重新检查...

  【修正】E(N,N-1) 的计算：
  j = N-1, b 的范围是 1 ≤ b ≤ min(N-1, 1) = 1
  f(N, N-1, 1) = N/1 × C(N-2, 0) × C(0, 0) = N × 1 × 1 = N

  E(N, N-1) = N × (N-(N-1)-1)! × f × 2^1
             = N × 0! × N × 2
             = N × 1 × N × 2 = 2N²

  T(N, N-1) = (-1)^0 × C(N-1, N-1) × E(N, N-1)
            + (-1)^1 × C(N, N-1) × E(N, N)
            = 1 × 2N² + (-1) × N × 2N
            = 2N² - 2N² = 0  ✓

FUNCTION T_void(N):
    IF N < 3 THEN RETURN special_case(N)
    RETURN 0
END FUNCTION

═══════════════════════════════════════════════════════════════
步骤 6：主程序
═══════════════════════════════════════════════════════════════

MAIN:
    INPUT N_max
    
    // 步骤 0-1：预处理
    build_combination_table(N_max)       // 帕斯卡恒等式
    build_factorial_table(N_max)         // 阶乘递推
    
    // 步骤 2-4：逐 N 计算
    FOR N = 1 TO N_max:
        FOR k = 0 TO N:
            T[N][k] = T(N, k)            // 闭式公式
        END FOR
    END FOR
    
    // 验证
    FOR N = 1 TO N_max:
        // 行和验证（Parseval 类比）
        row_sum = Σ_k T[N][k]
        ASSERT row_sum == fact[N]
        
        // 满分验证
        ASSERT T[N][N] == 2 * N          // N ≥ 3
        
        // 空缺验证
        ASSERT T[N][N-1] == 0            // N ≥ 3
    END FOR
    
    OUTPUT T[N][k]
END MAIN
```

---

## 二、数学原理对照表

| 步骤 | 伪代码函数 | 数学原理 | 文献来源 | 公式 |
|------|-----------|---------|---------|------|
| 0 | `build_combination_table` | 帕斯卡恒等式 | Stanley EC1 Ch.1 | C(n,k)=C(n-1,k-1)+C(n-1,k) |
| 1 | `build_factorial_table` | 阶乘递推 | 基本定义 | n! = n×(n-1)! |
| 2 | `f(N,j,b)` | Kaplansky 圆周选边引理 | Kaplansky 1944 | N/b·C(j-1,b-1)·C(N-j-1,b-1) |
| 3 | `E(N,j)` | 容斥叠加态 + 超级块排列 | 本文推导 | N·(N-j-1)!·Σ_b f·2^b |
| 4 | `T(N,k)` | Möbius 反演（二项式反演） | Rota 1964, Stanley 2011 | Σ(-1)^{j-k}·C(j,k)·E(N,j) |
| 5a | `T_perfect(N)` | 满分定理（组合论证） | 本文 | T(N,N)=2N |
| 5b | `T_void(N)` | 空缺定理（组合+代数） | 本文 | T(N,N-1)=0 |
| 6 | `MAIN` 验证 | Parseval 类比 + 行和恒等式 | 本文 | Σ_k T(N,k) = N! |

---

## 三、DP 算法伪代码（对照）

```
算法：位掩码 DP 计算 T(N,k)（用于验证闭式公式）

【数学原理】状态压缩动态规划
  利用环形旋转对称性固定起点 first=1，减少 N 倍计算量
  dp[mask][last][c] = 已放置 mask、末元素 last、路径中 c 条满足条件相邻对

【复杂度】O(2^N · N³) 时间，O(2^N · N²) 空间
【适用范围】N ≤ 15（原始）/ N ≤ 18（稀疏）
【文献来源】本文 STAT_006 / STAT_007

FUNCTION T_DP(N):
    // 边条件：|a-b|=1 或 |a-b|=N-1
    FUNCTION is_adj(a, b):
        d = abs(a - b)
        RETURN (d == 1 OR d == N-1)
    END FUNCTION
    
    // 初始化：固定起点 first=1
    first = 1
    initial_mask = 1 << (first - 1)
    dp[initial_mask][first][0] = 1
    
    // DP 转移
    FOR mask = initial_mask TO (1 << N) - 1:
        IF NOT (mask & initial_mask) THEN CONTINUE     // 必须含起点
        
        FOR last = 1 TO N:
            IF NOT (mask & (1 << (last-1))) THEN CONTINUE
            
            FOR c = 0 TO N:
                IF dp[mask][last][c] == 0 THEN CONTINUE
                
                // 枚举下一个未放置的元素
                FOR j = 1 TO N:
                    IF mask & (1 << (j-1)) THEN CONTINUE  // 已放置
                    
                    new_mask = mask | (1 << (j-1))
                    new_c = c
                    IF is_adj(last, j) THEN
                        new_c = c + 1                    // 新增一条满足条件的相邻对
                    END IF
                    
                    dp[new_mask][j][new_c] += dp[mask][last][c]
                END FOR
            END FOR
        END FOR
    END FOR
    
    // 统计结果：全放置 + 闭合到起点
    full_mask = (1 << N) - 1
    FOR last = 1 TO N:
        FOR c = 0 TO N:
            final_c = c
            IF is_adj(last, first) THEN
                final_c = c + 1                          // 闭合边
            END IF
            T[N][final_c] += dp[full_mask][last][c]
        END FOR
    END FOR
    
    // 还原：固定起点除以了 N!/N = (N-1)!，需要乘回 N
    FOR k = 0 TO N:
        T[N][k] = T[N][k] * N
    END FOR
    
    RETURN T[N][*]
END FUNCTION
```

### DP 与闭式的对照

| 维度 | DP 算法 | 闭式公式 |
|------|--------|---------|
| **数学原理** | 状态压缩 + 递推 | Kaplansky 引理 + Möbius 反演 |
| **复杂度** | O(2^N·N³) | O(N²) |
| **适用 N** | ≤18 | 任意(JS) / ≤27(VBA) |
| **精度** | Double/Decimal | BigInt 无上限 |
| **角色** | 验证工具 | 计算工具 |
| **文件** | STAT_006/007 | STAT_008 |

---

## 四、稀疏 DP 伪代码（对照）

```
算法：稀疏分层 DP（突破内存限制）

【数学原理】按 popcount 分层，只保留非零状态
  每层用 Dictionary 稀疏存储，key = mask·(N+1)+last
  复杂度不变 O(2^N·N³)，但空间从 O(2^N·N²) 降到 O(C(N,N/2)·N)

【文献来源】本文 STAT_007

FUNCTION T_sparse_DP(N):
    first = 1
    
    // 层 1：只含起点
    cur_layer = new Dictionary
    key = (1 << (first-1)) * (N+1) + first
    cur_layer[key] = [1, 0, 0, ..., 0]    // c=0 时计数为 1
    
    // 按 popcount 分层推进
    FOR popcount = 1 TO N-1:
        next_layer = new Dictionary
        
        FOR EACH (key, counts) IN cur_layer:
            mask = key / (N+1)
            last = key % (N+1)
            
            FOR j = 1 TO N:
                IF mask & (1 << (j-1)) THEN CONTINUE
                
                new_mask = mask | (1 << (j-1))
                new_key = new_mask * (N+1) + j
                
                FOR c = 0 TO popcount:
                    IF counts[c] == 0 THEN CONTINUE
                    
                    new_c = c
                    IF is_adj(last, j) THEN new_c = c + 1
                    
                    IF new_c > N THEN CONTINUE
                    
                    IF new_key NOT IN next_layer:
                        next_layer[new_key] = [0, 0, ..., 0]
                    END IF
                    next_layer[new_key][new_c] += counts[c]
                END FOR
            END FOR
        END FOR
        
        cur_layer = next_layer
    END FOR
    
    // 统计 + 闭合
    full_mask = (1 << N) - 1
    FOR k = 0 TO N: T[N][k] = 0
    
    FOR EACH (key, counts) IN cur_layer:
        mask = key / (N+1)
        last = key % (N+1)
        IF mask != full_mask THEN CONTINUE
        
        FOR c = 0 TO N:
            final_c = c
            IF is_adj(last, first) THEN final_c = c + 1
            IF final_c <= N THEN
                T[N][final_c] += counts[c]
            END IF
        END FOR
    END FOR
    
    FOR k = 0 TO N: T[N][k] *= N
    RETURN T[N][*]
END FUNCTION
```

---

## 五、算法选择决策树

```
输入 N
  │
  ├─ N ≤ 10 ?
  │   └─ YES → 全排列枚举 O(N!)         [STAT_001]
  │            精度：Double 即可
  │            优点：简单直接，可验证
  │
  ├─ N ≤ 15 ?
  │   └─ YES → 位掩码 DP O(2^N·N³)      [STAT_006]
  │            内存：< 60MB
  │            精度：Double 精确
  │
  ├─ N ≤ 18 ?
  │   └─ YES → 稀疏 DP O(2^N·N³)        [STAT_007]
  │            内存：< 100MB
  │            精度：Double 精确（18! < 2^53）
  │
  ├─ N ≤ 27 ?
  │   └─ YES → 闭式公式 O(N²) [VBA]     [STAT_008]
  │            精度：Decimal（27! < 7.9×10^28）
  │            优点：秒级完成
  │
  └─ N 任意
      └─ 闭式公式 O(N²) [JS BigInt]     [STAT_008]
               精度：BigInt 无上限
               优点：N=500 仅需 248ms
```

---

## 六、验证流程伪代码

```
算法：完整验证（闭式 vs DP vs 端点定理）

MAIN_VERIFY:
    FOR N = 3 TO 16:                           // DP 可行范围
        // 方法 1：闭式公式
        FOR k = 0 TO N:
            T_closed[N][k] = T(N, k)           // 闭式 O(N²)
        END FOR
        
        // 方法 2：DP 枚举
        T_dp[N][*] = T_DP(N)                   // DP O(2^N·N³)
        
        // 逐点比对
        FOR k = 0 TO N:
            ASSERT T_closed[N][k] == T_dp[N][k]
        END FOR
        
        // 行和验证（Parseval 类比）
        ASSERT Σ_k T_closed[N][k] == fact[N]
        
        // 端点定理验证
        ASSERT T_closed[N][N] == 2 * N         // 满分定理
        ASSERT T_closed[N][N-1] == 0           // 空缺定理
        
        PRINT "N=", N, " 全部验证通过 ✓"
    END FOR
    
    // 大 N 仅用闭式（DP 不可行）
    FOR N = 20 TO 500 STEP 10:
        FOR k = 0 TO N:
            T_closed[N][k] = T(N, k)
        END FOR
        ASSERT Σ_k T_closed[N][k] == fact[N]   // BigInt 验证
        ASSERT T_closed[N][N] == 2 * N
        ASSERT T_closed[N][N-1] == 0
        PRINT "N=", N, " 闭式验证通过 ✓"
    END FOR
END MAIN_VERIFY
```

---

## 七、核心公式速查卡

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Kaplansky 引理 (1944):                                     │
│    f(N,j,b) = N/b · C(j-1,b-1) · C(N-j-1,b-1)              │
│                                                              │
│  叠加态 (容斥):                                              │
│    E(N,j) = N · (N-j-1)! · Σ_b f(N,j,b) · 2^b             │
│    E(N,0) = N!,  E(N,N) = 2N                                │
│                                                              │
│  反演 (Möbius/二项式):                                       │
│    T(N,k) = Σ_{j=k}^{N} (-1)^{j-k} · C(j,k) · E(N,j)      │
│                                                              │
│  端点定理:                                                   │
│    T(N,N) = 2N        (满分定理)                             │
│    T(N,N-1) = 0       (空缺定理)                             │
│    Σ_k T(N,k) = N!    (行和恒等式)                           │
│                                                              │
│  复杂度: O(N²) 时间, O(N) 空间                               │
│  精度: Double(N≤18) / Decimal(N≤27) / BigInt(任意)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 参考文件

| 文件 | 说明 |
|------|------|
| [STAT_008_闭式公式.js](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_008_闭式公式.js) | 闭式公式 JS 实现（BigInt） |
| [STAT_008_闭式公式.bas](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_008_闭式公式.bas) | 闭式公式 VBA 实现（Decimal） |
| [STAT_006_总表特点分析.js](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_006_总表特点分析.js) | 位掩码 DP 实现 |
| [STAT_007_稀疏DP.js](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_007_稀疏DP.js) | 稀疏分层 DP 实现 |
| [STAT_T_Nk_闭式公式完整推导.md](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_T_Nk_闭式公式完整推导.md) | 完整数学推导 |
| [STAT_理论文献阅读笔记.md](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/VBA转js/代码延伸/STAT_理论文献阅读笔记.md) | 7 篇文献阅读笔记 |
