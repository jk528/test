// test_v2_全部函数.js
// 验证 v2.0 所有函数的逻辑（翻译 VBA 到 JS）
// 日期：2026-08-10

// ============================================================
// 一、核心算法（VBA 翻译版）
// ============================================================

// 内部辅助：把数组展开为一维数值数组
function CollectNumbers(vals, skipEmpty = true) {
    const result = [];
    for (const v of vals) {
        const s = String(v);
        if (!(skipEmpty && s === '')) {
            if (typeof v === 'number' || !isNaN(Number(v))) {
                result.push(Number(v));
            } else {
                result.push(0);
            }
        }
    }
    return result;
}

// 1. 连接
function 连接(vals, sep = '', skipEmpty = true) {
    const parts = [];
    for (const v of vals) {
        const s = String(v);
        if (!(skipEmpty && s === '')) {
            parts.push(s);
        }
    }
    return parts.join(sep);
}

// 2. 相邻差绝对值求和（线性）
function 相邻差绝对值求和(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return 0;
    let total = 0;
    for (let i = 0; i < arr.length - 1; i++) {
        total += Math.abs(arr[i] - arr[i + 1]);
    }
    return total;
}

// 3. 相邻差绝对值数组（线性）
function 相邻差绝对值数组(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return [];
    const diffs = [];
    for (let i = 0; i < arr.length - 1; i++) {
        diffs.push(Math.abs(arr[i] - arr[i + 1]));
    }
    return diffs;
}

// 4. 环形相邻差绝对值求和
function 环形相邻差绝对值求和(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return 0;
    let total = 0;
    for (let i = 0; i < arr.length - 1; i++) {
        total += Math.abs(arr[i] - arr[i + 1]);
    }
    // 环形：首尾相接
    total += Math.abs(arr[arr.length - 1] - arr[0]);
    return total;
}

// 5. 环形相邻计数
function 环形相邻计数(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return 0;

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

// 6. 环形相邻判定数组
function 环形相邻判定数组(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return [];

    let vMin = arr[0], vMax = arr[0];
    for (const v of arr) {
        if (v < vMin) vMin = v;
        if (v > vMax) vMax = v;
    }
    const diff = vMax - vMin;

    const n = arr.length;
    const result = new Array(n);
    if (diff === 0) {
        for (let i = 0; i < n; i++) result[i] = false;
        return result;
    }

    for (let i = 0; i < n; i++) {
        const a = arr[i];
        const b = arr[(i + 1) % n];
        const d = Math.abs(a - b);
        result[i] = (d === 1 || d === diff);
    }
    return result;
}

// 7. 是否连续序列
function 是否连续序列(vals, skipEmpty = true) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length === 0) return false;
    if (arr.length === 1) return true;

    let vMin = arr[0], vMax = arr[0];
    for (const v of arr) {
        if (v < vMin) vMin = v;
        if (v > vMax) vMax = v;
    }

    if (vMax - vMin + 1 !== arr.length) return false;

    // 检查重复
    const seen = new Set();
    for (const v of arr) {
        const idx = v - vMin;
        if (seen.has(idx)) return false;
        seen.add(idx);
    }
    return true;
}

// 8. 相邻差统计
function 相邻差统计(vals, skipEmpty = true, circular = false) {
    const arr = CollectNumbers(vals, skipEmpty);
    if (arr.length < 2) return [0, 0, 0, 0, 0];

    const diffCount = circular ? arr.length : arr.length - 1;
    const diffs = [];
    for (let i = 0; i < arr.length - 1; i++) {
        diffs.push(Math.abs(arr[i] - arr[i + 1]));
    }
    if (circular) {
        diffs.push(Math.abs(arr[arr.length - 1] - arr[0]));
    }

    let maxDiff = diffs[0], minDiff = diffs[0], sumDiff = 0;
    for (const d of diffs) {
        if (d > maxDiff) maxDiff = d;
        if (d < minDiff) minDiff = d;
        sumDiff += d;
    }

    return [maxDiff, minDiff, sumDiff / diffCount, sumDiff, diffCount];
}

// ============================================================
// 二、测试框架
// ============================================================

let passCount = 0, failCount = 0;

function assert(actual, expected, name) {
    const ok = JSON.stringify(actual) === JSON.stringify(expected);
    const status = ok ? 'PASS' : 'FAIL';
    if (ok) passCount++; else failCount++;
    console.log(`[${status}] ${name}: 期望=${JSON.stringify(expected)} 实际=${JSON.stringify(actual)}`);
}

// ============================================================
// 三、测试用例
// ============================================================

console.log('=== Function_连接字符串 v2.0 全函数测试 ===\n');

// --- 1. 连接 ---
console.log('--- 1. 连接 ---');
assert(连接([1,2,3,4,5]), '12345', '连接_直接拼接');
assert(连接([1,2,3,4,5], '-'), '1-2-3-4-5', '连接_分隔符');
assert(连接([1,2,3,4,5], '、'), '1、2、3、4、5', '连接_中文分隔符');
assert(连接([1,'',3], '-', true), '1-3', '连接_跳过空');
assert(连接([1,'',3], '-', false), '1--3', '连接_保留空');

// --- 2. 相邻差绝对值求和（线性）---
console.log('\n--- 2. 相邻差绝对值求和 ---');
assert(相邻差绝对值求和([1,2,3,4,5]), 4, '线性求和_12345');
assert(相邻差绝对值求和([5,4,3,2,1]), 4, '线性求和_逆序');
assert(相邻差绝对值求和([1,3,5,2,4]), 9, '线性求和_乱序');
assert(相邻差绝对值求和([1]), 0, '线性求和_单值');

// --- 3. 相邻差绝对值数组 ---
console.log('\n--- 3. 相邻差绝对值数组 ---');
assert(相邻差绝对值数组([1,2,3,4,5]), [1,1,1,1], '差值数组_12345');
assert(相邻差绝对值数组([5,4,3,2,1]), [1,1,1,1], '差值数组_逆序');
assert(相邻差绝对值数组([1,3,5]), [2,2], '差值数组_135');

// --- 4. 环形相邻差绝对值求和 ---
console.log('\n--- 4. 环形相邻差绝对值求和 ---');
assert(环形相邻差绝对值求和([1,2,3,4,5]), 8, '环形求和_12345');
assert(环形相邻差绝对值求和([5,4,3,2,1]), 8, '环形求和_逆序');
assert(环形相邻差绝对值求和([1,3,5]), 8, '环形求和_135');  // |1-3|+|3-5|+|5-1| = 2+2+4 = 8

// --- 5. 环形相邻计数 ---
console.log('\n--- 5. 环形相邻计数 ---');
assert(环形相邻计数([1,2,3,4,5]), 5, '环形计数_12345');
assert(环形相邻计数([5,4,3,2,1]), 5, '环形计数_逆序');
assert(环形相邻计数([1,3,5,2,4]), 0, '环形计数_乱序');
assert(环形相邻计数([5,5,5,5]), 0, '环形计数_全相同');
assert(环形相邻计数([1,5,1,5]), 4, '环形计数_交替');

// --- 6. 环形相邻判定数组 ---
console.log('\n--- 6. 环形相邻判定数组 ---');
assert(环形相邻判定数组([1,2,3,4,5]), [true,true,true,true,true], '判定数组_12345');
assert(环形相邻判定数组([1,3,5,2,4]), [false,false,false,false,false], '判定数组_乱序');
assert(环形相邻判定数组([5,5,5,5]), [false,false,false,false], '判定数组_全相同');

// --- 7. 是否连续序列 ---
console.log('\n--- 7. 是否连续序列 ---');
assert(是否连续序列([1,2,3,4,5]), true, '连续_12345');
assert(是否连续序列([5,4,3,2,1]), true, '连续_逆序');
assert(是否连续序列([1,3,5,2,4]), true, '连续_乱序');
assert(是否连续序列([1,2,4,5]), false, '连续_缺3');
assert(是否连续序列([1,2,2,3]), false, '连续_重复');
assert(是否连续序列([10,11,12]), true, '连续_两位数');
assert(是否连续序列([1]), true, '连续_单值');
assert(是否连续序列([]), false, '连续_空');

// --- 8. 相邻差统计 ---
console.log('\n--- 8. 相邻差统计 ---');
assert(相邻差统计([1,2,3,4,5]), [1,1,1,4,4], '统计_线性_12345');
assert(相邻差统计([1,2,3,4,5], true, true), [4,1,1.6,8,5], '统计_环形_12345');
assert(相邻差统计([1,3,5]), [2,2,2,4,2], '统计_线性_135');
assert(相邻差统计([1,3,5], true, true), [4,2,2.6666666666666665,8,3], '统计_环形_135');

// ============================================================
// 四、结果汇总
// ============================================================

console.log('\n=== 测试结果汇总 ===');
console.log(`通过: ${passCount}/${passCount + failCount}`);
console.log(`失败: ${failCount}/${passCount + failCount}`);
console.log(failCount === 0 ? '\n✅ 全部通过！' : '\n❌ 存在失败用例，请检查');
