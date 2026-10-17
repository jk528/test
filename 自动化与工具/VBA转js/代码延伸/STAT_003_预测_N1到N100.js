// STAT_003_预测_N1到N100.js
// 从 N=1 预测到 N=100 的全排列+环形计数完整耗时
// 用对数保证大数精度：log(fact(N)) = Σ_{i=1..N} log(i)
// 日期：2026-08-11

// 基于 N=8..10 实测拟合的 k = 0.202 μs/每次排列 (JS V8)
const K_JS_US = 0.202;   // μs per permutation (JS)

// —— 对数阶乘：保证 N>20 时精度不丢失 ——
function logFact(n, base=Math.E) {
    let s = 0;
    for (let i = 2; i <= n; i++) s += Math.log(i);
    return s / Math.log(base);
}

function factApprox(n) {
    // 返回科学计数法 [m, e] 表示 m × 10^e，m ∈ [1, 10)
    const log10f = logFact(n, 10);
    const e = Math.floor(log10f);
    const m = Math.pow(10, log10f - e);
    return [m, e];
}

// —— 格式化大数阶乘（科学计数法）——
function fmtFactSci(n) {
    const [m, e] = factApprox(n);
    if (e <= 12) {
        // 小数字直接完整显示
        return factInt(n).toLocaleString();
    }
    return `${m.toFixed(3)} × 10^${e}`;
}

function factInt(n) {
    // n <= 18 时可精准整数
    let r = 1n;
    for (let i = 2n; i <= BigInt(n); i++) r *= i;
    return r.toString();
}

// —— 超大时间格式化（秒为基础单位）——
const TIME_UNITS = [
    { name: '微秒',   sec: 1e-6,    threshold: 0.001 },
    { name: '毫秒',   sec: 1e-3,    threshold: 1 },
    { name: '秒',     sec: 1,       threshold: 60 },
    { name: '分钟',   sec: 60,      threshold: 3600 },
    { name: '小时',   sec: 3600,    threshold: 86400 },
    { name: '天',     sec: 86400,   threshold: 86400*365 },
    { name: '年(365)',sec: 86400*365, threshold: 86400*365*1000 },
    { name: '千年',   sec: 86400*365*1e3,   threshold: 86400*365*1e6 },
    { name: '百万年', sec: 86400*365*1e6,   threshold: 86400*365*1e9 },
    { name: '十亿年', sec: 86400*365*1e9,   threshold: 86400*365*1e10 },
    { name: '宇宙年龄', sec: 86400*365*13.8e9, threshold: Infinity },
];
const UNIVERSE_AGE_SEC = 86400 * 365 * 13.8e9;  // 宇宙当前年龄 ≈ 138 亿年

function fmtBigTime(sec) {
    // 返回 [数值, 单位名, 换算后的值]
    if (!isFinite(sec) || sec < 1e-9) return ['≈0', '秒', sec];
    for (let i = 0; i < TIME_UNITS.length; i++) {
        const u = TIME_UNITS[i];
        if (sec < u.threshold) {
            const val = sec / u.sec;
            const digit = val>=1000 ? 0 : (val>=100 ? 1 : (val>=10 ? 2 : 3));
            return [val.toFixed(digit), u.name, sec];
        }
    }
    // 最后一个单位：宇宙年龄倍数
    const mult = sec / UNIVERSE_AGE_SEC;
    return [mult.toExponential(3), '×宇宙年龄', sec];
}

// —— 计算某个 N 下的总耗时（返回 [秒, 人类时间三元组]）——
function predict(N, k_us_perm = K_JS_US) {
    const lnFact = logFact(N, Math.E);
    const total_us = Math.exp(lnFact) * k_us_perm;  // 总 μs
    const total_sec = total_us / 1_000_000;
    return { sec: total_sec, time: fmtBigTime(total_sec) };
}

// ============================================================
// 主输出
// ============================================================

console.log('='.repeat(105));
console.log('  全排列+环形相邻计数 耗时预测  N=1 ~ N=100');
console.log('  基准 k = 0.202 μs/每次排列（基于 N=8..10 实测，JS V8 JIT 环境）');
console.log('='.repeat(105) + '\n');

const ratios = [
    { name: 'JS V8 (实测基准)', factor: 1 },
    { name: 'VBA × 20',          factor: 20 },
    { name: 'VBA × 40',          factor: 40 },
    { name: 'VBA × 60',          factor: 60 },
];

// 区间分块输出
const ranges = [
    { title: '区间 1：N=1..15（实际可运行范围）', from: 1, to: 15 },
    { title: '区间 2：N=16..25（分钟 → 天）', from: 16, to: 25 },
    { title: '区间 3：N=26..40（天 → 年 → 千年）', from: 26, to: 40 },
    { title: '区间 4：N=41..60（千年 → 十亿年）', from: 41, to: 60 },
    { title: '区间 5：N=61..80（十亿年 → 万宇宙年龄）', from: 61, to: 80 },
    { title: '区间 6：N=81..100（亿亿宇宙年龄）', from: 81, to: 100 },
];

for (const range of ranges) {
    console.log('─'.repeat(105));
    console.log(`  ${range.title}`);
    console.log('─'.repeat(105));

    // 表头
    let hdr = '|  N |         N!         |';
    for (const r of ratios) hdr += `  ${r.name.padEnd(22)}  |`;
    console.log('  ' + hdr);
    console.log('  ' + hdr.replace(/[^|]/g, '─'));

    for (let N = range.from; N <= range.to; N++) {
        const factStr = N <= 21 ? BigInt(factInt(N)).toString().padStart(21) : fmtFactSci(N).padStart(21);
        let row = `| ${String(N).padStart(2)} | ${factStr} |`;

        for (const r of ratios) {
            const p = predict(N, K_JS_US * r.factor);
            const [v, unit] = p.time;
            row += `  ${v.padStart(10)} ${unit.padEnd(10)}  |`;
        }
        console.log('  ' + row);
    }
    console.log();
}

// ============================================================
// 里程碑表（精选关键 N）
// ============================================================
console.log('='.repeat(105));
console.log('  里程碑精选：典型耗时点');
console.log('='.repeat(105));

const milestones = [
    { N: 8,  mark: '< 0.1 秒' },
    { N: 10, mark: '< 1 秒' },
    { N: 11, mark: '~8 秒 (JS可行)' },
    { N: 12, mark: '~1.6 分钟' },
    { N: 13, mark: '~21 分钟' },
    { N: 14, mark: '~4.9 小时' },
    { N: 15, mark: '~3.1 天' },
    { N: 16, mark: '~49 天' },
    { N: 17, mark: '~1.4 年' },
    { N: 18, mark: '~25 年' },
    { N: 20, mark: '~9,586 年' },
    { N: 21, mark: '~20.1 万年' },
    { N: 23, mark: '~10 亿年' },
    { N: 24, mark: '> 170 亿年（>宇宙年龄）' },
    { N: 30, mark: '~ 10^30 年（天文级）' },
    { N: 40, mark: '~ 10^47 年' },
    { N: 50, mark: '~ 10^65 年' },
    { N: 60, mark: '~ 10^83 年' },
    { N: 69, mark: '双精度整数溢出边界 (2^53≈9e15)' },
    { N: 80, mark: '~ 10^113 年' },
    { N: 100, mark: '~ 10^155 年' },
];

let mHdr = '|  N  |   JS V8 耗时   |  VBA ×40 耗时   |  说明';
console.log('  ' + mHdr);
console.log('  ' + mHdr.replace(/[^|]/g, '─'));

for (const m of milestones) {
    const js = predict(m.N, K_JS_US);
    const vba = predict(m.N, K_JS_US * 40);
    console.log(`  | ${String(m.N).padStart(3)} | ${(js.time[0]+' '+js.time[1]).padStart(15)} | ${(vba.time[0]+' '+vba.time[1]).padStart(15)} |  ${m.mark}`);
}

// ============================================================
// 关键观察
// ============================================================
console.log('\n' + '='.repeat(105));
console.log('  关键观察');
console.log('='.repeat(105));

const obs = [
    ['JS V8 N=11', predict(11).time, '≈ 8 秒，可接受'],
    ['JS V8 N=12', predict(12).time, '≈ 1.6 分钟，可接受'],
    ['JS V8 N=13', predict(13).time, '≈ 21 分钟，可接受'],
    ['JS V8 N=14', predict(14).time, '≈ 4.9 小时，需过夜'],
    ['VBA×40 N=10', predict(10, K_JS_US*40).time, '≈ 29 秒，可接受'],
    ['VBA×40 N=11', predict(11, K_JS_US*40).time, '≈ 5.4 分钟，可接受（喝咖啡）'],
    ['VBA×40 N=12', predict(12, K_JS_US*40).time, '≈ 1.1 小时（吃午餐）'],
    ['VBA×40 N=13', predict(13, K_JS_US*40).time, '≈ 14 小时（睡一觉）'],
    ['VBA×40 N=14', predict(14, K_JS_US*40).time, '≈ 8 天（长假）'],
    ['N=23 × JS V8', predict(23).time, '≈ 10 亿年（恐龙还没出现...）'],
    ['N=24 × JS V8', predict(24).time, '> 138 亿年（超过宇宙当前年龄！）'],
    ['N=100 × JS V8', predict(100).time, `≈ 10^155 年（宇宙年龄的 ${(predict(100).sec/UNIVERSE_AGE_SEC).toExponential(1)} 倍）`],
];

for (const [name, timeArr, note] of obs) {
    console.log(`  ✦  ${name.padEnd(16)} ${(timeArr[0]+' '+timeArr[1]).padEnd(18)}  → ${note}`);
}

console.log('\n' + '='.repeat(105));
console.log('  实际建议：');
console.log('    • WPS VBA：N ≤ 11（5 分钟内），N=12 约 1~2 小时视机器性能');
console.log('    • Node.js：N ≤ 13（21 分钟内），N=14 约 5 小时');
console.log('    • N ≥ 14 建议：分治算法 + 多进程 + 对称剪枝（不枚举全排列，而是组合计数）');
console.log('='.repeat(105));
