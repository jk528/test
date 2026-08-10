// STAT_005_公式验证.js
// 代数验证推导的定理：
// 1. 容斥反推 E(j) = sum_{k>=j} C(k,j) * T(N,k) （每个恰好 k 的排列在 C(k,j) 个 S 中被计）
// 2. 定理：E(N-1) == N * E(N) （组合地：每条 N-1 边集强制变成满分圈）
// 3. 推论：T(N,N-1) = E(N-1) - N*E(N) == 0
// 4. 容斥恰好 k 公式：T(N,k) = sum_{j=k..N} (-1)^(j-k) * C(j,k) * E(j)
// 日期：2026-08-11

function 环形相邻计数_arr(arr) {
    if (arr.length < 2) return 0;
    let vMin = arr[0], vMax = arr[0];
    for (const v of arr) { if (v<vMin) vMin=v; if (v>vMax) vMax=v; }
    const diff = vMax - vMin;
    if (diff === 0) return 0;
    let count = 0, n = arr.length;
    for (let i = 0; i < n; i++) {
        const a = arr[i], b = arr[(i+1)%n];
        const d = Math.abs(a - b);
        if (d === 1 || d === diff) count++;
    }
    return count;
}

function 全排列_遍历(arr, cb) {
    const n = arr.length;
    const c = new Array(n).fill(0);
    cb([...arr]);
    let i = 0;
    while (i < n) {
        if (c[i] < i) {
            const j = (i%2===0) ? 0 : c[i];
            [arr[i], arr[j]] = [arr[j], arr[i]];
            cb([...arr]);
            c[i]++; i = 0;
        } else { c[i] = 0; i++; }
    }
}

function fact(n) { let r=1; for (let i=2;i<=n;i++) r*=i; return r; }
function C(n,k) { if (k<0||k>n) return 0; let r=1; for (let i=1;i<=k;i++) r = r*(n-k+i)/i; return Math.round(r); }
function subfact(n) { // 错位排列 !n
    if (n===0) return 1; if (n===1) return 0;
    return (n-1) * (subfact(n-1) + subfact(n-2));
}

function getT(N) {
    const nums = Array.from({length:N},(_,i)=>i+1);
    const freq = new Map();
    全排列_遍历([...nums], perm => {
        const c = 环形相邻计数_arr(perm);
        freq.set(c, (freq.get(c)||0) + 1);
    });
    return freq; // Map<k, T(N,k)>
}

function T_from_freq(freq, k) { return freq.get(k) || 0; }

function E_from_T(Tmap, N, j) {
    // E(j) = sum_{k>=j} C(k,j) * T(k)
    let sum = 0;
    for (const [k, Tk] of Tmap.entries()) {
        if (k >= j) sum += C(k, j) * Tk;
    }
    return sum;
}

// ========== 运行 ==========
console.log('='.repeat(105));
console.log('  闭式公式与定理验证  (N=4..8 枚举实测)');
console.log('='.repeat(105) + '\n');

for (let N = 4; N <= 8; N++) {
    const Tmap = getT(N);

    // 先打印 T(N,k) 原始行
    let rowT = `  T(${String(N).padStart(2)},k) = [`;
    const keys = [...Tmap.keys()].sort((a,b)=>a-b);
    const parts = [];
    for (const k of keys) parts.push(`${k}:${Tmap.get(k)}`);
    rowT += parts.join('  ') + ']';
    console.log(rowT + '\n');

    // 计算 E(j) 表
    console.log(`  ┌ 表 E(${N},j) = Σ_{k≥j} C(k,j)·T(${N},k)`);
    console.log(`  │  j    E(j)   C(${N},j)   平均每组 H(S)=E/C     2^j·N!/(N-j+1)?    2N (j=N)  N·2N (j=N-1)  N!·2^j/(N)??`);
    console.log(`  │  ────────────────────────────────────────────────────────────────────────────────────`);
    for (let j = 0; j <= N; j++) {
        const Ej = E_from_T(Tmap, N, j);
        const cnj = C(N, j);
        const avgH = Ej / cnj;
        const guess = cnj * Math.pow(2, j) * fact(N) / (N - j + 1);
        const mark2N = j===N ? (Ej===2*N ? '✅=2N' : `❌≠2N (=${Ej})`) : '';
        const markN2N = j===N-1 ? (Ej===N*2*N ? '✅=N·2N' : `❌≠N·2N`) : '';
        console.log(`  │  ${j}  ${String(Ej).padStart(7)}  ${String(cnj).padStart(7)}  ${avgH===Math.round(avgH)?String(avgH).padStart(10):avgH.toFixed(2).padStart(10)}  ${String(Math.round(guess)).padStart(14)}   ${mark2N.padEnd(14)}  ${markN2N.padEnd(12)}`);
    }
    console.log(`  │`);

    // 定理 1：T(N,N) == 2N
    const Tnn = T_from_freq(Tmap, N);
    const pass1 = Tnn === 2*N;
    console.log(`  │ 【定理 1】T(${N},${N}) = ${Tnn}  ==  2·${N} = ${2*N}    ${pass1?'✅ PASS':'❌ FAIL'}`);

    // 定理 2：E(N-1) == N * E(N)
    const En_1 = E_from_T(Tmap, N, N-1);
    const En   = E_from_T(Tmap, N, N);
    const pass2 = En_1 === N * En;
    console.log(`  │ 【定理 2】E(${N},${N-1})=${En_1}  ==  ${N}·E(${N},${N})=${N*En}   ${pass2?'✅ PASS':'❌ FAIL'}`);

    // 定理 3：T(N,N-1) = E(N-1) - C(N,N-1)*E(N)  ==  0
    const Tn_nm1 = T_from_freq(Tmap, N-1);
    const formula = En_1 - C(N, N-1) * En;
    const pass3a = Tn_nm1 === 0;
    const pass3b = formula === 0;
    console.log(`  │ 【定理 3】实测 T(${N},${N-1})=${Tn_nm1}（应为 0）   ${pass3a?'✅ PASS':'❌ FAIL'}`);
    console.log(`  │          容斥公式 E(${N-1}) - C(N,${N-1})·E(N) = ${formula}   ${pass3b?'✅ PASS':'❌ FAIL'}`);

    // 一般 k 的容斥反推验证
    console.log(`  │`);
    console.log(`  │ 【容斥反推】对所有 k，T(N,k) = Σ_{j=k..N} (-1)^{j-k}·C(j,k)·E(j) 验证：`);
    let allPass = true;
    for (let k = 0; k <= N; k++) {
        let ie = 0;
        for (let j = k; j <= N; j++) {
            const Ej = E_from_T(Tmap, N, j);
            ie += ((j-k) % 2 === 0 ? 1 : -1) * C(j, k) * Ej;
        }
        const realT = T_from_freq(Tmap, k);
        const ok = ie === realT;
        if (!ok) allPass = false;
        const mark = ok ? '✅' : '❌';
        if (realT > 0 || Math.abs(ie) > 0) {
            console.log(`  │   ${mark}  k=${k}: 公式=${String(ie).padStart(7)}  实测=${String(realT).padStart(7)}  ${ie===realT?'PASS':'FAIL'}`);
        }
    }
    console.log(`  │   → 全部 k 验证: ${allPass ? '✅ ALL PASS' : '❌ SOME FAILED'}`);

    console.log('  ' + '─'.repeat(103) + '\n');
}

// ======== 附：与 A180188 (仅升序环形相邻) 公式对比 ========
console.log('='.repeat(105));
console.log('  对比：仅升序相邻 (circular successions, A180188) 公式 vs 我们的 "双向含(N,1)" 三角');
console.log('='.repeat(105));
console.log(`
  A180188 已知闭式：T_Ascending(n,k) = n · C(n-1,k) · !(n-1-k)
    其中 !m 为错位排列数 (subfactorial)
    T_Ascending(n,n-1) = n · 1 · !0 = n (满分 n 个排列：顺时针平移 n 种)
    T_Ascending(n, n)=0（因为 A180188 最多 k=n-1 条升序边）

  我们的三角：T(n,k)（双向 |差|=1，并自动含 |差|=n-1 的边 (1,n)）
    由于每条参考边都有正反 2 种方向出现，推测存在 2^j 级放大；
    但满分 T(n,n)=2n = 2 · T_Ascending(n,n-1)（恰好 2 倍！）
`);

for (let N = 4; N <= 8; N++) {
    const Tmap = getT(N);
    console.log(`  N=${N}`);
    for (let k = 0; k <= N; k++) {
        const ourT = T_from_freq(Tmap, k);
        let ascT = 0;
        if (k <= N-1) ascT = N * C(N-1, k) * subfact(N-1-k);  // A180188 公式
        // 注：A180188 是"仅升序环形相邻数计数"，k 最大 N-1
        if (ourT || ascT) {
            const ratio = ourT / ascT;
            console.log(`    k=${k}：  我们=${String(ourT).padStart(6)}  A180188(仅升)=${String(ascT).padStart(6)}  比值=${isFinite(ratio)?ratio.toFixed(2):'—'}`);
        }
    }
    console.log();
}
console.log('='.repeat(105));
console.log('  结论：我们的满分 T(N,N)=2N 恰好是 A180188 满分 (k=N-1) 值 n 的 2 倍。');
console.log('        其他 k 没有简单倍数关系，说明双向相邻≠升序×2。');
console.log('='.repeat(105));
