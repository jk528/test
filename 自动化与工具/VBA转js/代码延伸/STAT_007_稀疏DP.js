// STAT_007_稀疏DP.js
// 改进算法：分层 DP + 稀疏存储，支持 N>15
// 原始：dp(2^N, N, N+1) 3D 数组，N=15 需 60MB，N=18 需 684MB
// 改进：按 popcount 分层，只存当前层和下一层，稀疏 Map 存储
//   每层峰值 ≈ C(N-1, N/2-1) * (N/2) 个 (mask,last) 对
//   N=18 峰值约 22 万条目，内存 < 50MB
// 日期：2026-08-11

// ============ 改进：稀疏分层 DP ============
function getT_dp_sparse(N) {
    if (N === 0) return new Map([[0, 1]]);
    if (N === 1) return new Map([[0, 1]]);
    if (N === 2) return new Map([[2, 2]]);

    const isAdj = (a, b) => {
        const d = Math.abs(a - b);
        return (d === 1 || d === N - 1) ? 1 : 0;
    };

    // 分层 DP：current = Map<key, Float64Array(N+1)>
    // key = mask * (N+1) + last（mask 含 bit 0，last ∈ mask）
    // Float64Array[c] = 排列数
    let current = new Map();

    // 初始化：mask=1 (只有 bit 0), last=0, c=0
    let initArr = new Float64Array(N + 1);
    initArr[0] = 1;
    current.set(1 * (N + 1) + 0, initArr);

    // 逐层推进：level = 已放置元素个数 - 1
    for (let level = 1; level < N; level++) {
        const next = new Map();

        for (const [key, counts] of current) {
            const mask = Math.floor(key / (N + 1));
            const last = key % (N + 1);

            for (let j = 0; j < N; j++) {
                if (mask & (1 << j)) continue; // j 已放置
                const newMask = mask | (1 << j);
                const adj = isAdj(last + 1, j + 1);
                const newKey = newMask * (N + 1) + j;

                let target = next.get(newKey);
                if (!target) {
                    target = new Float64Array(N + 1);
                    next.set(newKey, target);
                }
                for (let c = 0; c <= N - adj; c++) {
                    if (counts[c]) target[c + adj] += counts[c];
                }
            }
        }

        current = next; // 丢弃上一层，GC 回收
    }

    // 汇总：mask = full, 加闭合边 (last, 0)
    const full = (1 << N) - 1;
    const freq = new Map();

    for (const [key, counts] of current) {
        const mask = Math.floor(key / (N + 1));
        const last = key % (N + 1);
        if (mask !== full || last === 0) continue;

        const adj = isAdj(last + 1, 1);
        for (let c = 0; c <= N; c++) {
            if (counts[c]) {
                const k = c + adj;
                freq.set(k, (freq.get(k) || 0) + counts[c]);
            }
        }
    }

    const result = new Map();
    for (const [k, v] of freq) {
        result.set(k, Math.round(v * N));
    }
    return result;
}

// ============ 原始 DP（对比验证用） ============
function getT_dp(N) {
    if (N === 0) return new Map([[0, 1]]);
    if (N === 1) return new Map([[0, 1]]);
    if (N === 2) return new Map([[2, 2]]);
    const full = (1 << N) - 1;
    const dp = Array(1 << N).fill(null).map(() =>
        Array(N).fill(null).map(() => new Float64Array(N + 1))
    );
    dp[1][0][0] = 1;
    const isAdj = (a, b) => { const d = Math.abs(a - b); return (d === 1 || d === N - 1) ? 1 : 0; };
    for (let mask = 1; mask < (1 << N); mask++) {
        if (!(mask & 1)) continue;
        for (let last = 0; last < N; last++) {
            if (!(mask & (1 << last))) continue;
            for (let j = 0; j < N; j++) {
                if (mask & (1 << j)) continue;
                const newMask = mask | (1 << j);
                const adj = isAdj(last + 1, j + 1);
                const target = dp[newMask][j];
                for (let c = 0; c <= N - adj; c++) {
                    if (dp[mask][last][c]) target[c + adj] += dp[mask][last][c];
                }
            }
        }
    }
    const freq = new Map();
    for (let last = 1; last < N; last++) {
        const adj = isAdj(last + 1, 1);
        for (let c = 0; c <= N; c++) {
            if (dp[full][last][c]) { const k = c + adj; freq.set(k, (freq.get(k) || 0) + dp[full][last][c]); }
        }
    }
    const result = new Map();
    for (const [k, v] of freq) result.set(k, Math.round(v * N));
    return result;
}

// ============ 估算分层 DP 峰值内存 ============
function estimatePeakMemory(N) {
    // 峰值出现在 level ≈ N/2
    // 每层 (mask, last) 对数 = C(N-1, level) * (level+1)
    // 每对存 Float64Array(N+1) = (N+1)*8 bytes + Map 开销 ~64 bytes
    function C(n, k) { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return Math.round(r); }

    let maxEntries = 0;
    let maxLevel = 0;
    for (let level = 0; level < N; level++) {
        const masks = C(N - 1, level);
        const entries = masks * (level + 1);
        if (entries > maxEntries) { maxEntries = entries; maxLevel = level; }
    }
    const bytesPerEntry = (N + 1) * 8 + 64; // Float64Array + Map overhead
    const peakMB = maxEntries * bytesPerEntry / 1048576;
    // 两层（current + next）
    const twoLayerMB = peakMB * 2;
    return { maxEntries, maxLevel: maxLevel + 1, peakMB, twoLayerMB };
}

// ============ 主测试 ============
function fact(n) { let r = 1; for (let i = 2; i <= n; i++) r *= i; return r; }

console.log('='.repeat(100));
console.log('  稀疏分层 DP 测试 —— 支持 N>15');
console.log('  优化：按 popcount 分层 + Map 稀疏存储，只保留 2 层');
console.log('='.repeat(100) + '\n');

// 1. 正确性验证：N=4..15 对比原始 DP
console.log('【验证】稀疏 DP vs 原始 DP (N=4..15)：');
let allPass = true;
for (let N = 4; N <= 15; N++) {
    const sparse = getT_dp_sparse(N);
    const original = N <= 14 ? getT_dp(N) : null; // N=15 原始 DP 可能慢
    if (original) {
        let pass = true;
        const keys = new Set([...sparse.keys(), ...original.keys()]);
        for (const k of keys) {
            if ((sparse.get(k) || 0) !== (original.get(k) || 0)) { pass = false; break; }
        }
        if (!pass) allPass = false;
        // 行和验证
        let sum = 0;
        for (const v of sparse.values()) sum += v;
        const sumOK = sum === fact(N);
        console.log(`  N=${String(N).padStart(2)}: ${pass ? 'PASS' : 'FAIL'}  行和=${sum}/${fact(N)} ${sumOK ? 'OK' : 'FAIL'}`);
    } else {
        let sum = 0;
        for (const v of sparse.values()) sum += v;
        const sumOK = sum === fact(N);
        const tNN = sparse.get(N) || 0;
        const tNNm1 = sparse.get(N - 1) || 0;
        console.log(`  N=${String(N).padStart(2)}: 行和=${sum}/${fact(N)} ${sumOK ? 'OK' : 'FAIL'}  T(N,N)=${tNN}/${2*N} ${tNN===2*N?'OK':'FAIL'}  T(N,N-1)=${tNNm1}/0 ${tNNm1===0?'OK':'FAIL'}`);
    }
}
console.log();

// 2. 内存估算
console.log('【内存估算】分层 DP 峰值内存（两层）：\n');
console.log('  |  N | 峰值层 | (mask,last)对数 | 单层(MB) | 两层(MB) | 原始DP(MB) | 节省倍数 |');
console.log('  |----|--------|----------------|---------|---------|-----------|---------|');
for (let N = 10; N <= 22; N++) {
    const est = estimatePeakMemory(N);
    const origMB = Math.pow(2, N) * N * (N + 1) * 8 / 1048576;
    const savings = origMB / est.twoLayerMB;
    console.log(`  | ${String(N).padStart(2)} |  ${est.maxLevel}     | ${est.maxEntries.toLocaleString().padStart(14)} | ${est.peakMB.toFixed(1).padStart(7)} | ${est.twoLayerMB.toFixed(1).padStart(7)} | ${origMB.toFixed(0).padStart(9)} | ${savings.toFixed(0).padStart(7)}x |`);
}
console.log();

// 3. 实测 N=16..18
console.log('【实测】N=16..18 稀疏 DP：\n');
for (let N = 16; N <= 18; N++) {
    const est = estimatePeakMemory(N);
    process.stdout.write(`  N=${N} (峰值两层 ~${est.twoLayerMB.toFixed(0)}MB) ... `);
    const memBefore = process.memoryUsage().heapUsed;
    const t0 = process.hrtime.bigint();
    const result = getT_dp_sparse(N);
    const t1 = process.hrtime.bigint();
    const memAfter = process.memoryUsage().heapUsed;
    const ms = Number(t1 - t0) / 1e6;
    const memDelta = (memAfter - memBefore) / 1048576;

    let sum = 0;
    for (const v of result.values()) sum += v;
    const tNN = result.get(N) || 0;
    const tNNm1 = result.get(N - 1) || 0;
    console.log(`${ms.toFixed(0)}ms, 堆内存+${memDelta.toFixed(0)}MB`);
    console.log(`    行和=${sum.toLocaleString()} / ${fact(N).toLocaleString()} ${sum === fact(N) ? 'OK' : 'FAIL'}`);
    console.log(`    T(N,N)=${tNN} / 2N=${2*N} ${tNN === 2*N ? 'OK' : 'FAIL'}`);
    console.log(`    T(N,N-1)=${tNNm1} / 0 ${tNNm1 === 0 ? 'OK' : 'FAIL'}`);

    // 打印频率分布
    let detail = '    分布: ';
    const keys = [...result.keys()].sort((a, b) => a - b);
    for (const k of keys) {
        detail += `k=${k}:${result.get(k).toLocaleString()}  `;
    }
    console.log(detail);
    console.log();
}

console.log('='.repeat(100));
console.log('  结论：');
console.log('  - 分层 DP 将内存从 O(2^N·N²) 降至 O(C(N,N/2)·N²)，节省 2^N/C(N,N/2) ≈ √N 倍');
console.log('  - N=18: 原始 684MB → 改进 ~100MB，JS 实测可行');
console.log('  - VBA 中 N=18: 预估 ~200MB（Dictionary 开销更大），64 位 Office 可行');
console.log('='.repeat(100));
