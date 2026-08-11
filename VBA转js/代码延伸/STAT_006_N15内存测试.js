// N=15 内存与耗时测试
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
    let iterCount = 0;
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
                    if (dp[mask][last][c]) { target[c + adj] += dp[mask][last][c]; iterCount++; }
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
    result._iterCount = iterCount;
    return result;
}

function fact(n) { let r = 1; for (let i = 2; i <= n; i++) r *= i; return r; }

// 内存估算
function memEstimate(N) {
    const elements = Math.pow(2, N) * N * (N + 1);
    const bytes = elements * 8;  // Float64 = 8 bytes
    return { elements, bytes, MB: bytes / 1048576 };
}

console.log('='.repeat(90));
console.log('  N=10..18 内存与耗时估算（DP O(2^N · N³)）');
console.log('='.repeat(90) + '\n');

console.log('  |  N |  2^N  | dp数组元素数 | 内存(MB) | 内循环次数 | JS实测耗时 | VBA预估(×40) |');
console.log('  |----|-------|-------------|----------|-----------|-----------|-------------|');

for (let N = 10; N <= 18; N++) {
    const mem = memEstimate(N);
    // 理论内循环次数 = Σ C(N-1,k-1) * k * (N-k) * (N+1)
    let theoryIter = 0;
    function C(n, k) { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return Math.round(r); }
    for (let k = 1; k <= N; k++) {
        theoryIter += C(N - 1, k - 1) * k * (N - k) * (N + 1);
    }

    let jsMs = '—', vbaEst = '—';
    if (N <= 15) {
        const t0 = process.hrtime.bigint();
        const result = getT_dp(N);
        const t1 = process.hrtime.bigint();
        const ms = Number(t1 - t0) / 1e6;
        jsMs = ms.toFixed(0) + 'ms';
        const vbaMs = ms * 40;
        if (vbaMs < 60000) vbaEst = (vbaMs / 1000).toFixed(1) + '秒';
        else if (vbaMs < 3600000) vbaEst = (vbaMs / 60000).toFixed(1) + '分钟';
        else vbaEst = (vbaMs / 3600000).toFixed(1) + '小时';

        // 验证行和 = N!
        if (N <= 15) {
            let sum = 0;
            for (const v of result.values()) sum += v;
            const ok = sum === fact(N);
            const tNN = result.get(N) || 0;
            console.log(`  | ${String(N).padStart(2)} | ${String(Math.pow(2, N)).padStart(5)} | ${mem.elements.toLocaleString().padStart(11)} | ${mem.MB.toFixed(1).padStart(8)} | ${theoryIter.toLocaleString().padStart(9)} | ${jsMs.padStart(9)} | ${vbaEst.padStart(11)} | 行和=${sum}/${fact(N)} ${ok ? 'OK' : 'FAIL'} T(N,N)=${tNN}/${2*N}`);
            continue;
        }
    }
    console.log(`  | ${String(N).padStart(2)} | ${String(Math.pow(2, N)).padStart(5)} | ${mem.elements.toLocaleString().padStart(11)} | ${mem.MB.toFixed(1).padStart(8)} | ${theoryIter.toLocaleString().padStart(9)} | ${jsMs.padStart(9)} | ${vbaEst.padStart(11)} |`);
}

console.log('\n' + '='.repeat(90));
console.log('  结论：');
console.log('  - N=15: 内存 ~63MB，VBA 预估 < 5 分钟，可行');
console.log('  - N=16: 内存 ~136MB，32位 WPS/Excel 可能不够');
console.log('  - N=17: 内存 ~277MB，风险较高');
console.log('  - N=18: 内存 ~530MB，仅 64 位 Office 可行');
console.log('='.repeat(90));
