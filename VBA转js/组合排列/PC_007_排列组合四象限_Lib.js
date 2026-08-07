// PC_007_排列组合四象限_Lib.js
// 排列组合四象限计算 - 独立工具库
// 补全 PC_001（三角矩阵）缺失的单点查询与枚举功能
//
// 四象限定义：
//   Type 1: 组合不放回 C(n, k)          元素不重复，不计顺序
//   Type 2: 组合放回 C(n+k-1, k)        元素可重复，不计顺序
//   Type 3: 排列不放回 A(n, k) = n!/(n-k)! 元素不重复，计顺序
//   Type 4: 排列放回 n^k                元素可重复，计顺序
//
// ======================== 引入方式 ========================
// 方式1（WPS 宏）：将本文件代码粘贴到调用脚本顶部；或通过宏属性引用
// 方式2（Node.js）：const PC = require('./PC_007_排列组合四象限_Lib.js');
// 方式3（浏览器）：<script src="PC_007_排列组合四象限_Lib.js"></script>
//
// ======================== API 一览 ========================
// PC.count(n, k, type)             单值：计算排列/组合数量
// PC.enumerate(arr, k, type)       枚举：生成具体排列/组合列表
// PC.row(n, type)                  行数据：k=0..n 的计数数组
// PC.matrix(n, type)               纯矩阵：n=0..N, k=0..N 的二维数组
// PC.matrixWithHeader(n, type)     带表头矩阵：与 PC_001 三角风格一致
// PC.TYPE                          常量对象 { NOREP_COMB:1, REP_COMB:2, NOREP_PERM:3, REP_PERM:4 }
// PC.version                       库版本号
// =========================================================

(function (factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else {
        var g = typeof globalThis !== 'undefined' ? globalThis
              : typeof self !== 'undefined' ? self
              : typeof window !== 'undefined' ? window
              : typeof global !== 'undefined' ? global
              : (this || {});
        g.PC = factory();
    }
}(function () {

    // 类型常量
    var TYPE = {
        NOREP_COMB: 1,   // 组合不放回 C(n,k)
        REP_COMB: 2,     // 组合放回 C(n+k-1,k)
        NOREP_PERM: 3,   // 排列不放回 A(n,k)
        REP_PERM: 4      // 排列放回 n^k
    };

    // 类型中文名
    var TYPE_NAME = {
        1: "组合不放回 C(n,k)",
        2: "组合放回 C(n+k-1,k)",
        3: "排列不放回 A(n,k)",
        4: "排列放回 n^k"
    };

    // 单行上限（安全值，防止超大枚举导致内存溢出）
    var MAX_ENUM = 10000000;

    // ----------------------------------------------------------
    // 计数：C(n,k) 组合不放回
    // ----------------------------------------------------------
    function countCombNoRepet(n, k) {
        if (k < 0 || k > n) return 0;
        if (k === 0 || k === n) return 1;
        if (k > n - k) k = n - k;
        var res = 1;
        for (var i = 1; i <= k; i++) {
            res = res * (n - k + i) / i;
        }
        return Math.round(res);
    }

    // ----------------------------------------------------------
    // 计数：C(n+k-1,k) 组合放回
    // ----------------------------------------------------------
    function countCombRepet(n, k) {
        if (k < 0 || n < 1) return 0;
        if (k === 0) return 1;
        return countCombNoRepet(n + k - 1, k);
    }

    // ----------------------------------------------------------
    // 计数：A(n,k) 排列不放回
    // ----------------------------------------------------------
    function countPermNoRepet(n, k) {
        if (k < 0 || k > n) return 0;
        if (k === 0) return 1;
        var res = 1;
        for (var i = 0; i < k; i++) {
            res = res * (n - i);
        }
        return res;
    }

    // ----------------------------------------------------------
    // 计数：n^k 排列放回
    // ----------------------------------------------------------
    function countPermRepet(n, k) {
        if (k < 0) return 0;
        if (k === 0) return 1;
        return Math.pow(n, k);
    }

    // ----------------------------------------------------------
    // 统一计数入口
    // ----------------------------------------------------------
    function count(n, k, type) {
        switch (type) {
            case TYPE.NOREP_COMB: return countCombNoRepet(n, k);
            case TYPE.REP_COMB:   return countCombRepet(n, k);
            case TYPE.NOREP_PERM: return countPermNoRepet(n, k);
            case TYPE.REP_PERM:   return countPermRepet(n, k);
            default: return 0;
        }
    }

    // ----------------------------------------------------------
    // 枚举：组合不放回
    // ----------------------------------------------------------
    function enumerateCombNoRepet(arr, k) {
        if (!Array.isArray(arr) || arr.length === 0) return null;
        var n = arr.length;
        if (k < 1 || k > n) return null;
        var total = countCombNoRepet(n, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        function rec(start, depth, res) {
            if (result.length >= MAX_ENUM) return;
            if (depth > k) {
                result.push(res.slice());
                return;
            }
            for (var i = start; i <= n - (k - depth); i++) {
                res[depth - 1] = arr[i - 1];
                rec(i + 1, depth + 1, res);
            }
        }
        rec(1, 1, []);
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：组合放回
    // ----------------------------------------------------------
    function enumerateCombRepet(arr, k) {
        if (!Array.isArray(arr) || arr.length === 0) return null;
        var n = arr.length;
        if (k < 1) return null;
        var total = countCombRepet(n, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var idx = new Array(k).fill(0);
        while (true) {
            result.push(idx.map(function (i) { return arr[i]; }));
            var p = k - 1;
            while (p >= 0 && idx[p] >= n - 1) p--;
            if (p < 0) break;
            idx[p]++;
            for (var i = p + 1; i < k; i++) idx[i] = idx[p];
        }
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：排列不放回
    // ----------------------------------------------------------
    function enumeratePermNoRepet(arr, k) {
        if (!Array.isArray(arr) || arr.length === 0) return null;
        var n = arr.length;
        if (k < 1 || k > n) return null;
        var total = countPermNoRepet(n, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var used = new Array(n).fill(false);
        function rec(depth, res) {
            if (result.length >= MAX_ENUM) return;
            if (depth > k) {
                result.push(res.slice());
                return;
            }
            for (var i = 0; i < n; i++) {
                if (!used[i]) {
                    used[i] = true;
                    res[depth - 1] = arr[i];
                    rec(depth + 1, res);
                    used[i] = false;
                }
            }
        }
        rec(1, []);
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：排列放回
    // ----------------------------------------------------------
    function enumeratePermRepet(arr, k) {
        if (!Array.isArray(arr) || arr.length === 0) return null;
        var n = arr.length;
        if (k < 1) return null;
        var total = countPermRepet(n, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var idx = new Array(k).fill(0);
        while (true) {
            result.push(idx.map(function (i) { return arr[i]; }));
            var p = k - 1;
            while (p >= 0 && idx[p] >= n - 1) p--;
            if (p < 0) break;
            idx[p]++;
            for (var i = p + 1; i < k; i++) idx[i] = 0;
        }
        return result;
    }

    // ----------------------------------------------------------
    // 统一枚举入口
    // ----------------------------------------------------------
    function enumerate(arr, k, type) {
        switch (type) {
            case TYPE.NOREP_COMB: return enumerateCombNoRepet(arr, k);
            case TYPE.REP_COMB:   return enumerateCombRepet(arr, k);
            case TYPE.NOREP_PERM: return enumeratePermNoRepet(arr, k);
            case TYPE.REP_PERM:   return enumeratePermRepet(arr, k);
            default: return null;
        }
    }

    // ----------------------------------------------------------
    // 行数据：n 固定，k=0..n 的计数数组
    // ----------------------------------------------------------
    function row(n, type) {
        var arr = [];
        var maxK = (type === TYPE.REP_COMB || type === TYPE.REP_PERM)
                   ? n  // 放回类型：k 理论上可无限，矩阵内只到 n
                   : n;
        for (var k = 0; k <= maxK; k++) {
            if (type === TYPE.REP_COMB || type === TYPE.REP_PERM) {
                // 放回类型：k=0 返回 1（空选择），k>0 正常计算
                arr.push(count(n, k, type));
            } else {
                // 不放回：k>n 返回 0
                arr.push(count(n, k, type));
            }
        }
        return arr;
    }

    // ----------------------------------------------------------
    // 纯矩阵：n=0..nMax, k=0..nMax 的二维数值数组
    // ----------------------------------------------------------
    function matrix(nMax, type) {
        var result = [];
        for (var n = 0; n <= nMax; n++) {
            result.push(row(n, type));
        }
        return result;
    }

    // ----------------------------------------------------------
    // 带表头矩阵：与 PC_001 三角风格一致
    // 行：n=0..nMax；列：k=0..nMax
    // ----------------------------------------------------------
    function matrixWithHeader(nMax, type) {
        var rowsTotal = nMax + 2;
        var colsTotal = nMax + 3;
        var colStart = 3;
        var outArr = [];
        for (var i = 0; i < rowsTotal; i++) {
            outArr.push(new Array(colsTotal).fill(''));
        }

        // 表头
        outArr[0][0] = "总和";
        outArr[0][1] = "总数";
        for (var k = 0; k <= nMax; k++) {
            outArr[0][colStart + k] = "选" + k + "个";
        }

        var rowIdx = 1;
        for (var n = 0; n <= nMax; n++) {
            outArr[rowIdx][1] = n;
            var sumRow = 0;

            // k=0: 恒为 1
            outArr[rowIdx][colStart + 0] = 1;
            sumRow += 1;

            // k=1..nMax
            for (var k = 1; k <= nMax; k++) {
                var val;
                if (type === TYPE.REP_COMB || type === TYPE.REP_PERM) {
                    // 放回类型：对所有 k 都有意义
                    val = count(n, k, type);
                    outArr[rowIdx][colStart + k] = val;
                    sumRow += val;
                } else {
                    // 不放回：k > n 时无意义，留空
                    if (k <= n) {
                        val = count(n, k, type);
                        outArr[rowIdx][colStart + k] = val;
                        sumRow += val;
                    } else {
                        outArr[rowIdx][colStart + k] = "";
                    }
                }
            }

            outArr[rowIdx][0] = sumRow;
            rowIdx++;
        }

        return outArr;
    }

    // 导出 API
    return {
        version: '1.0.0',
        TYPE: TYPE,
        TYPE_NAME: TYPE_NAME,
        MAX_ENUM: MAX_ENUM,
        count: count,
        enumerate: enumerate,
        row: row,
        matrix: matrix,
        matrixWithHeader: matrixWithHeader
    };
}));
