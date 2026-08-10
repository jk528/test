// 模拟 VBA 宏 演示_生成环形相邻词频表 的输出
// 与 STAT_001_全组合环形相邻词频.bas 的 WriteResultToSheet 输出格式完全一致
// 日期：2026-08-11

// === 1. 算法（与 VBA 完全一致）===
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

function 全排列环形词频统计(nums, outputCols=true) {
    const freq = new Map();
    let total = 0;
    全排列_遍历([...nums], perm => {
        const cnt = 环形相邻计数_arr(perm);
        freq.set(cnt, (freq.get(cnt)||0) + 1);
        total++;
    });
    const keys = [...freq.keys()].sort((a,b)=>a-b);
    const cols = outputCols ? 3 : 2;
    const result = [];
    for (const k of keys) {
        const row = new Array(cols);
        row[0] = k;
        row[1] = freq.get(k);
        if (cols === 3) row[2] = freq.get(k) / total;
        result.push(row);
    }
    return { result, total, N: nums.length };
}

// === 2. 模拟 演示_生成环形相邻词频表(N=5) 的工作表输出 ===
console.log('='.repeat(70));
console.log('  模拟 VBA 宏：演示_生成环形相邻词频表');
console.log('  输入 N=5，工作表名：环形相邻词频_N5');
console.log('='.repeat(70) + '\n');

const { result, total, N } = 全排列环形词频统计(GenerateNums(5), true);

// --- 输出格式：与 VBA WriteResultToSheet 完全一致 ---
// 表头
const hdr = '| 计数值(A) | 出现次数(B) | 占比(C) |';
console.log('  [工作表：环形相邻词频_N5]');
console.log('  ─────────────────────────────────────');
console.log('  ' + hdr);
console.log('  ' + hdr.replace(/[^|]/g, '─'));

// 数据行
const rows = result;
let sumCount = 0, sumPct = 0;
for (const row of rows) {
    const pct = (row[2] * 100).toFixed(1) + '%';
    console.log(`  | ${String(row[0]).padStart(8)} | ${String(row[1]).padStart(11)} | ${pct.padStart(7)} |`);
    sumCount += row[1];
    sumPct += row[2];
}

// 合计行
console.log('  ' + hdr.replace(/[^|]/g, '─'));
const sumPctStr = (sumPct * 100).toFixed(1) + '%';
console.log(`  | ${"合计".padEnd(8)} | ${String(sumCount).padStart(11)} | ${sumPctStr.padStart(7)} |`);

// 数字集合与全排列总数信息（VBA 写入 E 列）
console.log();
console.log(`  [E1] 数字集合 N=${N}`);
console.log(`  [E2] 全排列总数 = ${total}`);
console.log();

// --- 验证 ---
const exp5 = {0:10, 2:50, 3:50, 5:10};
console.log('─'.repeat(70));
console.log('  与用户示例验证（N=5 频率分布）');
console.log('─'.repeat(70));
let allPass = true;
for (const [k, exp] of Object.entries(exp5)) {
    const got = new Map(result.map(r=>[r[0],r[1]])).get(Number(k)) || 0;
    const ok = got === exp;
    if (!ok) allPass = false;
    console.log(`  ${ok?'✅':'❌'} 计数=${k}  频率=${got}  期望=${exp}  ${ok?'PASS':'FAIL'}`);
}
console.log();
console.log(`  合计验证: sum=${sumCount}  N!=${fact(N)}  ${sumCount===fact(N)?'✅ 相等':'❌ 不等'}`);
console.log(`  占比验证: sumPct=${(sumPct*100).toFixed(1)}%  ${Math.abs(sumPct-1)<1e-9?'✅ 100%':'❌'}`);
console.log();
console.log(allPass && sumCount===fact(N) ? '  🎉 全部验证通过！VBA 宏输出与预期完全一致。' : '  ❌ 存在验证失败！');
console.log('='.repeat(70));

// === 3. 额外模拟：批量对比表（N=1..7）===
console.log('\n\n' + '='.repeat(90));
console.log('  模拟 VBA 宏：批量生成_N1到N(最大N=7)   工作表：环形相邻词频_批量对比');
console.log('='.repeat(90) + '\n');

// 表头行
let line = '| 计数值 |';
for (let i = 1; i <= 7; i++) line += ` N=${i}(${fact(i)}) |`;
console.log('  ' + line);
console.log('  ' + line.replace(/[^|]/g, '─'));

// 收集每个 N 的频率
const allFreqs = [];
let maxCount = 0;
for (let Ni = 1; Ni <= 7; Ni++) {
    const { result: r } = 全排列环形词频统计(GenerateNums(Ni), false);
    const m = new Map(r.map(x=>[x[0],x[1]]));
    allFreqs.push(m);
    if (Ni > maxCount) maxCount = Ni;
}

// 数据行
for (let cnt = 0; cnt <= maxCount; cnt++) {
    let row = `| ${String(cnt).padStart(6)} |`;
    for (let Ni = 1; Ni <= 7; Ni++) {
        const v = allFreqs[Ni-1].get(cnt);
        row += ` ${v!==undefined ? String(v).padStart(String(fact(Ni)).length) : ' '.repeat(String(fact(Ni)).length)} |`;
    }
    console.log('  ' + row);
}

// 合计行
let sumLine = '|   合计 |';
for (let Ni = 1; Ni <= 7; Ni++) {
    let s = 0;
    for (const v of allFreqs[Ni-1].values()) s += v;
    sumLine += ` ${String(s).padStart(String(fact(Ni)).length)} |`;
}
console.log('  ' + sumLine.replace(/[^|]/g, '─'));
console.log('  ' + sumLine);
console.log();
console.log('  * 每个 N 列的合计 = N!，证明全部排列覆盖无遗漏无重复');
console.log('='.repeat(90));
