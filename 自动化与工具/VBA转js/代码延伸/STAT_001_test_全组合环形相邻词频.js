// STAT_001_test_全组合环形相邻词频.js
// 先验证 N=5 的频率分布是否为：0:10, 5:10, 2:50, 3:50
// 日期：2026-08-11

// ============================================================
// 核心算法 1：环形相邻计数（数组版，直接传数值数组，不经过单元格）
// 逻辑与 VBA Function_连接字符串.bas 中的 环形相邻计数 完全一致
// ============================================================
function 环形相邻计数_arr(arr) {
    if (!arr || arr.length < 2) return 0;

    let vMin = arr[0], vMax = arr[0];
    for (const v of arr) {
        if (v < vMin) vMin = v;
        if (v > vMax) vMax = v;
    }
    const diff = vMax - vMin;
    if (diff === 0) return 0;

    let count = 0;
    const n = arr.length;
    for (let i = 0; i < n; i++) {
        const a = arr[i];
        const b = arr[(i + 1) % n];
        const d = Math.abs(a - b);
        if (d === 1 || d === diff) count++;
    }
    return count;
}

// ============================================================
// 核心算法 2：全排列生成（Heap 算法，原地交换，无重复，O(n!)）
// 对每个生成的排列，回调 callback(排列数组)
// ============================================================
function 全排列_遍历(arr, callback) {
    const n = arr.length;
    const c = new Array(n).fill(0);

    callback([...arr]);  // 初始排列

    let i = 0;
    while (i < n) {
        if (c[i] < i) {
            // 交换：偶数i交换0和i，奇数i交换c[i]和i
            const j = (i % 2 === 0) ? 0 : c[i];
            [arr[i], arr[j]] = [arr[j], arr[i]];
            callback([...arr]);
            c[i]++;
            i = 0;
        } else {
            c[i] = 0;
            i++;
        }
    }
}

// ============================================================
// 核心算法 3：词频统计（Map）
// ============================================================
function 统计环形相邻词频(数字集合) {
    const freq = new Map();
    const total = { count: 0 };

    const start = Date.now();

    全排列_遍历([...数字集合], perm => {
        const cnt = 环形相邻计数_arr(perm);
        freq.set(cnt, (freq.get(cnt) || 0) + 1);
        total.count++;
    });

    const time = Date.now() - start;
    return { freq, total: total.count, time };
}

// ============================================================
// 测试：N=1 到 N=7 的词频分布
// ============================================================

console.log('=== 全组合环形相邻词频统计 ===\n');

for (let N = 1; N <= 7; N++) {
    const nums = Array.from({length: N}, (_, i) => i + 1);
    const result = 统计环形相邻词频(nums);

    console.log(`--- N=${N}  ${N}! = ${fact(N)} 种排列（实际处理 ${result.total}） 耗时 ${result.time}ms ---`);

    // 排序输出
    const keys = [...result.freq.keys()].sort((a, b) => a - b);
    let sum = 0;
    for (const k of keys) {
        const v = result.freq.get(k);
        const pct = (v / result.total * 100).toFixed(1);
        console.log(`  计数=${k}  频率=${v}  占比=${pct}%`);
        sum += v;
    }
    console.log(`  合计: ${sum}  ✓`);

    // 用户示例验证（N=5）
    if (N === 5) {
        const exp0 = 10, exp2 = 50, exp3 = 50, exp5 = 10;
        const f0 = result.freq.get(0) || 0;
        const f2 = result.freq.get(2) || 0;
        const f3 = result.freq.get(3) || 0;
        const f5 = result.freq.get(5) || 0;
        const ok = (f0===exp0 && f2===exp2 && f3===exp3 && f5===exp5);
        console.log(`  [${ok?'PASS':'FAIL'}] 用户示例验证：0:${f0}/${exp0}, 2:${f2}/${exp2}, 3:${f3}/${exp3}, 5:${f5}/${exp5}`);
    }
    console.log();
}

function fact(n) {
    let r = 1;
    for (let i = 2; i <= n; i++) r *= i;
    return r;
}
