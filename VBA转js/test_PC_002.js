// 独立测试脚本 - 验证PC_002排列组合核心JS逻辑

var k = 0;

function ToOneBased(Arr) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    if (Arr.length === 0) {
        return null;
    }
    if (Arr[0] !== undefined && Arr[0] !== null && Arr[0] !== '') {
        var hasIndex0 = false;
        for (var i = 0; i < Arr.length; i++) {
            if (i in Arr && !Array.isArray(Arr[i])) {
                hasIndex0 = true;
                break;
            }
        }
        if (!hasIndex0) {
            return Arr;
        }
    }
    var n = Arr.length;
    var result = [];
    result[0] = '';
    for (var i = 0; i < n; i++) {
        result[i + 1] = Arr[i];
    }
    return result;
}

function Clone1D(a) {
    if (!Array.isArray(a)) {
        return a;
    }
    var n = a.length;
    var b = [];
    b[0] = '';
    for (var i = 1; i <= n; i++) {
        b[i] = a[i];
    }
    return b;
}

function CombinationDD(n, R) {
    if (R < 0 || R > n) return 0;
    if (R === 0 || R === n) return 1;
    if (R > n - R) R = n - R;
    var res = 1;
    for (var i = 1; i <= R; i++) {
        res = res * (n - R + i) / i;
    }
    return res;
}

function PermCount(m, n) {
    if (n < 0 || n > m) return 0;
    var res = 1;
    for (var i = 0; i < n; i++) {
        res = res * (m - i);
    }
    return res;
}

function GenComb_NoRepet(Arr, m, n, startIdx, depth, res, result, outIndex) {
    var i, maxI;
    if (depth > n) {
        outIndex[0] = outIndex[0] + 1;
        result[outIndex[0]] = Clone1D(res);
        return outIndex[0];
    }
    maxI = m - (n - depth);
    for (i = startIdx; i <= maxI; i++) {
        res[depth] = Arr[i];
        outIndex[0] = GenComb_NoRepet(Arr, m, n, i + 1, depth + 1, res, result, outIndex);
    }
    return outIndex[0];
}

function combin_arr1(Arr, n) {
    var m, count, result, res, outIndex;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (n < 1 || n > m) {
        return null;
    }
    count = CombinationDD(m, n);
    result = [];
    result[0] = '';
    res = [];
    res[0] = '';
    outIndex = [0];
    GenComb_NoRepet(Arr, m, n, 1, 1, res, result, outIndex);
    return result;
}

function combin_arr_repet(Arr, n) {
    var m, i, count, idx, brr, cur, done, p, outIndex;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (n < 1 || m < 1) {
        return null;
    }
    count = CombinationDD(m + n - 1, n);
    brr = [];
    brr[0] = '';
    idx = [];
    idx[0] = '';
    for (i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    outIndex = 0;
    done = false;
    while (!done) {
        cur = [];
        cur[0] = '';
        for (i = 1; i <= n; i++) {
            cur[i] = Arr[idx[i]];
        }
        outIndex++;
        brr[outIndex] = Clone1D(cur);
        p = n;
        while (p >= 1) {
            if (idx[p] < m) {
                idx[p] = idx[p] + 1;
                for (i = p + 1; i <= n; i++) {
                    idx[i] = idx[p];
                }
                break;
            } else {
                p = p - 1;
            }
        }
        if (p === 0) done = true;
    }
    return brr;
}

function SolverPermNoRepet(Arr, m, n, used, res, depth, result, R) {
    var i;
    if (depth > n) {
        R[0] = R[0] + 1;
        result[R[0]] = Clone1D(res);
        return R[0];
    }
    for (i = 1; i <= m; i++) {
        if (!used[i]) {
            used[i] = true;
            res[depth] = Arr[i];
            R[0] = SolverPermNoRepet(Arr, m, n, used, res, depth + 1, result, R);
            used[i] = false;
        }
    }
    return R[0];
}

function permut_no_repet(Arr, n) {
    var m, kk, used, res, result, R;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (n < 1 || n > m) {
        return null;
    }
    kk = PermCount(m, n);
    result = [];
    result[0] = '';
    used = [];
    used[0] = '';
    res = [];
    res[0] = '';
    R = [0];
    SolverPermNoRepet(Arr, m, n, used, res, 1, result, R);
    return result;
}

function permut_repet(Arr, n) {
    var m, i, kk, idx, res, result, done, R;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (n < 1 || m < 1) {
        return null;
    }
    kk = Math.pow(m, n);
    result = [];
    result[0] = '';
    idx = [];
    idx[0] = '';
    for (i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    R = 0;
    done = false;
    while (!done) {
        res = [];
        res[0] = '';
        for (i = 1; i <= n; i++) {
            res[i] = Arr[idx[i]];
        }
        R++;
        result[R] = Clone1D(res);
        i = n;
        while (i >= 1) {
            if (idx[i] < m) {
                idx[i] = idx[i] + 1;
                break;
            } else {
                idx[i] = 1;
                i = i - 1;
            }
        }
        if (i === 0) done = true;
    }
    return result;
}

function NestedListCount(List) {
    if (!Array.isArray(List)) return 0;
    if (List[0] === '' || List[0] === undefined) {
        var cnt = 0;
        for (var i = 1; i < List.length; i++) {
            if (List[i] !== undefined && List[i] !== null) {
                cnt++;
            }
        }
        return cnt;
    }
    return List.length;
}

function NestedItemLength(List) {
    var item;
    if (!Array.isArray(List)) return 0;
    var firstIndex = List[0] === '' ? 1 : 0;
    item = List[firstIndex];
    if (!Array.isArray(item)) return 0;
    if (item[0] === '' || item[0] === undefined) {
        var len = 0;
        for (var i = 1; i < item.length; i++) {
            if (item[i] !== undefined && item[i] !== null) {
                len++;
            }
        }
        return len;
    }
    return item.length;
}

function TransposeNestedTo2D(List) {
    if (!Array.isArray(List)) {
        return List;
    }
    var rows = List.length;
    if (rows < 1) {
        return List;
    }
    var item = List[0];
    var cols = 1;
    if (Array.isArray(item)) {
        cols = item.length;
    }
    var outArr = [];
    for (var i = 0; i < rows; i++) {
        outArr[i] = [];
        item = List[i];
        if (Array.isArray(item)) {
            for (var j = 0; j < cols; j++) {
                outArr[i][j] = item[j];
            }
        } else {
            outArr[i][0] = item;
        }
    }
    return outArr;
}

console.log("========== PC_002 排列组合 核心函数测试 ==========\n");

var testPassed = 0;
var testFailed = 0;

function assertEqual(actual, expected, testName) {
    if (actual === expected) {
        console.log("[PASS] " + testName + " = " + actual);
        testPassed++;
    } else {
        console.log("[FAIL] " + testName + " - 期望: " + expected + ", 实际: " + actual);
        testFailed++;
    }
}

function assertArrayLength(arr, expected, testName) {
    var len = NestedListCount(arr);
    if (len === expected) {
        console.log("[PASS] " + testName + " 项数 = " + len);
        testPassed++;
    } else {
        console.log("[FAIL] " + testName + " 项数 - 期望: " + expected + ", 实际: " + len);
        testFailed++;
    }
}

function assertItemLength(arr, expected, testName) {
    var len = NestedItemLength(arr);
    if (len === expected) {
        console.log("[PASS] " + testName + " 每项长度 = " + len);
        testPassed++;
    } else {
        console.log("[FAIL] " + testName + " 每项长度 - 期望: " + expected + ", 实际: " + len);
        testFailed++;
    }
}

console.log("--- 工具函数测试 ---");
assertEqual(CombinationDD(5, 2), 10, "C(5,2)");
assertEqual(CombinationDD(5, 3), 10, "C(5,3)");
assertEqual(CombinationDD(6, 0), 1, "C(6,0)");
assertEqual(PermCount(5, 2), 20, "P(5,2)");
assertEqual(PermCount(5, 3), 60, "P(5,3)");

console.log("\n--- 组合不放回 C(m,n) 测试 ---");
var arr1 = ["A", "B", "C"];
var result1 = combin_arr1(arr1, 2);
assertArrayLength(result1, 3, "C(3,2)");
assertItemLength(result1, 2, "C(3,2)");
console.log("结果: " + JSON.stringify(TransposeNestedTo2D(result1)));

var result2 = combin_arr1(arr1, 3);
assertArrayLength(result2, 1, "C(3,3)");
assertItemLength(result2, 3, "C(3,3)");
console.log("结果: " + JSON.stringify(TransposeNestedTo2D(result2)));

console.log("\n--- 组合放回 C(m+n-1,n) 测试 ---");
var result3 = combin_arr_repet(arr1, 2);
assertArrayLength(result3, 6, "C(3+2-1,2)=C(4,2)");
assertItemLength(result3, 2, "C(3+2-1,2)");
console.log("结果: " + JSON.stringify(TransposeNestedTo2D(result3)));

console.log("\n--- 排列不放回 P(m,n) 测试 ---");
var result4 = permut_no_repet(arr1, 2);
assertArrayLength(result4, 6, "P(3,2)");
assertItemLength(result4, 2, "P(3,2)");
console.log("结果: " + JSON.stringify(TransposeNestedTo2D(result4)));

console.log("\n--- 排列放回 m^n 测试 ---");
var result5 = permut_repet(arr1, 2);
assertArrayLength(result5, 9, "3^2");
assertItemLength(result5, 2, "3^2");
console.log("结果: " + JSON.stringify(TransposeNestedTo2D(result5)));

console.log("\n========== 测试结果 ==========");
console.log("通过: " + testPassed);
console.log("失败: " + testFailed);
if (testFailed === 0) {
    console.log("\n所有核心函数测试通过！");
} else {
    console.log("\n存在 " + testFailed + " 个测试失败，请检查！");
}