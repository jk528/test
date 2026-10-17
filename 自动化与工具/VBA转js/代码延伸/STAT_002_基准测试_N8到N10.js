// STAT_002_基准测试_N8到N12.js
// 运行 N=8..10（必要时到 N=11）的实际计时，拟合线性模型 k，再预估更大 N
// 注意：Heap 全排列复杂度 O(n!)，耗时与排列数 N! 线性成正比
// 拟合：time_ms = k * N!   →  k = time_ms / N!
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
function GenerateNums(N) { return Array.from({length:N}, (_,i)=>i+1); }

// —— 单个 N 的计时（暖机一次，正式测 3 次取最小）——
function benchOne(N, warmup=false) {
    const nums = GenerateNums(N);
    // warmup
    if (warmup) {
        const warmFreq = new Map();
        全排列_遍历([...nums], perm => {
            const cnt = 环形相邻计数_arr(perm);
            warmFreq.set(cnt, (warmFreq.get(cnt)||0)+1);
        });
    }

    const times_ms = [];
    const runs = N <= 9 ? 3 : (N <= 10 ? 2 : 1);
    for (let r = 0; r < runs; r++) {
        const freq = new Map();
        let total = 0;
        const t0 = process.hrtime.bigint();
        全排列_遍历([...nums], perm => {
            const cnt = 环形相邻计数_arr(perm);
            freq.set(cnt, (freq.get(cnt)||0) + 1);
            total++;
        });
        const t1 = process.hrtime.bigint();
        const ms = Number(t1 - t0) / 1_000_000;
        times_ms.push(ms);
    }
    const minMs = Math.min(...times_ms);
    const k = minMs / fact(N);   // ms / per_perm
    return { N, perms: fact(N), minMs, avgMs: times_ms.reduce((a,b)=>a+b,0)/times_ms.length, k_us: k*1000, freq_size: 0 };
}

console.log('='.repeat(85));
console.log('  基准测试：N=8..10 实际计时（每个 N 取最快一次，共 2~3 轮）');
console.log('  模型：耗时(ms) ≈ k × N!     k = 每次排列+环形计数+字典累加 的耗时 (μs)');
console.log('='.repeat(85) + '\n');

// —— 运行 N=1..7 作为暖机 ——
console.log('  [暖机] N=1..7 ...');
for (let Ni = 1; Ni <= 7; Ni++) benchOne(Ni, false);
console.log('  [暖机完成]\n');

// —— 正式基准 ——
const benchResults = [];
for (let N = 8; N <= 10; N++) {
    process.stdout.write(`  正在测量 N=${N} (${fact(N).toLocaleString()} 排列) ... `);
    const r = benchOne(N, false);
    benchResults.push(r);
    console.log(`✓ ${r.minMs.toFixed(1)} ms (k=${r.k_us.toFixed(3)} μs/排列)`);
}
console.log();

// —— 汇总表 ——
console.log('─'.repeat(85));
console.log('  实测数据汇总');
console.log('─'.repeat(85));
console.log('  |  N  |       排列数 N!       |  最快耗时(ms)  |  平均耗时(ms)  |  k (μs/排列)  |');
console.log('  |─────|───────────────────────|─────────────────|─────────────────|───────────────|');
for (const r of benchResults) {
    console.log(`  | ${String(r.N).padStart(3)} | ${r.perms.toLocaleString().padStart(21)} | ${r.minMs.toFixed(1).padStart(15)} | ${r.avgMs.toFixed(1).padStart(15)} | ${r.k_us.toFixed(3).padStart(13)} |`);
}

// —— 拟合 k：用加权平均（N 越大权重越高，越可信）——
let weightedK = 0, weightSum = 0;
for (const r of benchResults) {
    const w = r.N;  // 大 N 的 k 更稳定
    weightedK += r.k_us * w;
    weightSum += w;
}
weightedK /= weightSum;
const kSimpleAvg = benchResults.reduce((s,r)=>s+r.k_us, 0) / benchResults.length;
console.log();
console.log(`  拟合 k (加权平均)  = ${weightedK.toFixed(3)} μs/每次排列`);
console.log(`  拟合 k (简单平均)  = ${kSimpleAvg.toFixed(3)} μs/每次排列`);
const kFit = weightedK;  // 用加权平均

// —— 预估 N=11 到 N=14 ——
console.log();
console.log('─'.repeat(85));
console.log(`  时间预判（基于拟合 k=${kFit.toFixed(3)} μs/排列）`);
console.log('─'.repeat(85));
console.log('  |  N  |       排列数 N!       |  预估耗时(ms)  |  人类可读         |  吞吐量 (排/秒)  |');
console.log('  |─────|───────────────────────|─────────────────|───────────────────|─────────────────|');

function humanReadable(ms) {
    if (ms < 1000) return ms.toFixed(1) + ' ms';
    const sec = ms / 1000;
    if (sec < 60) return sec.toFixed(2) + ' 秒';
    const min = sec / 60;
    if (min < 60) return min.toFixed(2) + ' 分钟';
    const hr = min / 60;
    if (hr < 24) return hr.toFixed(2) + ' 小时';
    return (hr/24).toFixed(2) + ' 天';
}

for (let N = 8; N <= 15; N++) {
    const perms = fact(N);
    const estMs = perms * kFit / 1000;  // μs → ms
    const tps = perms / (estMs / 1000);  // 排/秒
    let mark = '';
    if (N >= 8 && N <= 10) mark = ' (实测对照)';
    console.log(`  | ${String(N).padStart(3)} | ${perms.toLocaleString().padStart(21)} | ${estMs>=1000?estMs.toLocaleString(undefined,{maximumFractionDigits:0}).padStart(15):estMs.toFixed(1).padStart(15)} | ${humanReadable(estMs).padEnd(17)} | ${tps>=1000?tps.toLocaleString(undefined,{maximumFractionDigits:0}).padStart(15):tps.toFixed(0).padStart(15)} |${mark}`);
}

// —— VBA 粗略换算系数 ——
console.log();
console.log('─'.repeat(85));
console.log('  环境差异预估：JS (Node V8) vs VBA (WPS/Excel)');
console.log('─'.repeat(85));
console.log();
console.log('  说明：上述计时基于 Node.js V8 JIT，VBA 解释执行通常比 JS 慢 20~60 倍。');
console.log('        以下用 20x / 40x / 60x 三档系数换算为 VBA 预估耗时：\n');

for (const ratio of [20, 40, 60]) {
    console.log(`  ── 慢 ${ratio} 倍 ──`);
    console.log(`  |  N  |       排列数 N!       |  JS预估     |  VBA预估(${ratio}x)  |`);
    console.log(`  |─────|───────────────────────|─────────────|────────────────────|`);
    for (let N = 8; N <= 14; N++) {
        const perms = fact(N);
        const jsMs = perms * kFit / 1000;
        const vbaMs = jsMs * ratio;
        let jsStr, vbaStr;
        if (jsMs < 60000) jsStr = (jsMs/1000).toFixed(1)+' 秒'; else if (jsMs<3600_000) jsStr=(jsMs/60000).toFixed(1)+'分'; else jsStr=(jsMs/3600_000).toFixed(1)+'时';
        if (vbaMs < 60000) vbaStr = (vbaMs/1000).toFixed(1)+' 秒'; else if (vbaMs<3600_000) vbaStr=(vbaMs/60000).toFixed(1)+'分'; else if (vbaMs<86400_000) vbaStr=(vbaMs/3600_000).toFixed(1)+'时'; else vbaStr=(vbaMs/86400_000).toFixed(2)+'天';
        console.log(`  | ${String(N).padStart(3)} | ${perms.toLocaleString().padStart(21)} | ${jsStr.padStart(11)} | ${vbaStr.padStart(18)} |`);
    }
    console.log();
}

console.log('='.repeat(85));
console.log(`  建议：VBA 下 N≥11 时使用本模块的"预判_耗时"先评估，N≥13 需谨慎（可能超过 1 小时）`);
console.log('='.repeat(85));
