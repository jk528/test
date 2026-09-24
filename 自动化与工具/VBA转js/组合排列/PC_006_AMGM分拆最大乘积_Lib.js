// PC_006_AMGM分拆最大乘积_Lib.js
// 基于 AM-GM 不等式的离散均匀分拆最大乘积 - 独立工具库
// 纯算法实现，不依赖 WPS/浏览器环境，可被任意 JS 脚本引入
//
// 问题：给定正整数 N，将其分拆为 k 个正整数之和 a1+a2+...+ak = N (ai>=1)
//       求乘积 P = a1*a2*...*ak 的最大值。
//
// 原理（AM-GM 不等式）：当各份尽量相等时乘积最大。
//   设 N = q*k + r  (0 <= r < k)
//     - r = 0：所有份 = q，最大乘积 = q^k
//     - r > 0：r 份 = (q+1)，(k-r) 份 = q，最大乘积 = (q+1)^r * q^(k-r)
//
// ======================== 引入方式 ========================
// 方式1（WPS 宏）：将本文件代码粘贴到调用脚本顶部；或通过宏属性引用
// 方式2（Node.js）：const AMGM = require('./PC_006_AMGM分拆最大乘积_Lib.js');
// 方式3（浏览器）：<script src="PC_006_AMGM分拆最大乘积_Lib.js"></script>
//                  之后即可使用全局对象 AMGM
// 方式4（ES Module）：import AMGM from './PC_006_AMGM分拆最大乘积_Lib.js';
//
// ======================== API 一览 ========================
// AMGM.maxProduct(N, k)            单值：将 N 拆成 k 份时的最大乘积
// AMGM.partitionPlan(N, k)         方案：返回长度为 k 的数组（每份的具体值）
// AMGM.bestK(N)                    最优：给定 N 时使乘积最大的 k（可能多个并列）
// AMGM.row(N)                      行数据：k=0..N 的最大乘积数组
// AMGM.matrix(n)                   纯矩阵：N=0..n, k=0..n 的二维数组
// AMGM.matrixWithHeader(n)         带表头矩阵：与 PC_001_三角 风格一致，便于直接写入工作表
// AMGM.version                     库版本号
// =========================================================

(function (factory) {
    if (typeof module === 'object' && module.exports) {
        // Node.js / CommonJS
        module.exports = factory();
    } else if (typeof define === 'function' && define.amd) {
        // AMD
        define([], factory);
    } else {
        // 浏览器 / WPS 宏 / 其他全局环境
        // 优先 globalThis（ES2020，WPS 宏 SpiderMonkey/V8、Node、浏览器均支持）
        var g = typeof globalThis !== 'undefined' ? globalThis
              : typeof self !== 'undefined' ? self
              : typeof window !== 'undefined' ? window
              : typeof global !== 'undefined' ? global
              : (this || {});
        g.AMGM = factory();
    }
}(function () {

    // ----------------------------------------------------------
    // 单元最大乘积：将 N 分拆为 k 份正整数之和时的最大乘积
    // 入参：N >= 0, k >= 0（均整数）
    // 返回：最大乘积；非法情形返回 0
    //   - N=0, k=0 → 1（空积约定）
    //   - N>0, k=0 或 k>N → 0
    // ----------------------------------------------------------
    function maxProduct(N, k) {
        if (N === 0 && k === 0) return 1;       // 空积约定
        if (N <= 0 || k <= 0) return 0;         // 非法参数
        if (k > N) return 0;                     // 每份至少 1，k 不能超 N
        var q = Math.floor(N / k);
        var r = N % k;
        var prod = 1;
        for (var i = 0; i < k - r; i++) prod *= q;        // (k-r) 份 q
        for (var j = 0; j < r; j++) prod *= (q + 1);      // r 份 (q+1)
        return prod;
    }

    // ----------------------------------------------------------
    // 拆分方案：返回具体的每份值，长度为 k
    // 入参：N >= 1, 1 <= k <= N
    // 返回：长度为 k 的数组，前 r 个元素为 (q+1)，后 (k-r) 个为 q
    //       非法情形返回 null；空分拆 (N=0,k=0) 返回 []
    // ----------------------------------------------------------
    function partitionPlan(N, k) {
        if (N === 0 && k === 0) return [];
        if (N <= 0 || k <= 0 || k > N) return null;
        var q = Math.floor(N / k);
        var r = N % k;
        var plan = [];
        for (var i = 0; i < r; i++) plan.push(q + 1);
        for (var j = 0; j < k - r; j++) plan.push(q);
        return plan;
    }

    // ----------------------------------------------------------
    // 给定 N，返回所有 k (1..N) 中使乘积最大的 k 值
    // 返回：{ k: [...], maxProd: number }
    //   - k 数组可能含多个并列值（如 N=7 时 k=2 与 k=3 并列）
    // ----------------------------------------------------------
    function bestK(N) {
        if (N <= 0) return { k: [], maxProd: 0 };
        var maxProd = -1;
        var bestKs = [];
        for (var k = 1; k <= N; k++) {
            var p = maxProduct(N, k);
            if (p > maxProd) {
                maxProd = p;
                bestKs = [k];
            } else if (p === maxProd) {
                bestKs.push(k);
            }
        }
        return { k: bestKs, maxProd: maxProd };
    }

    // ----------------------------------------------------------
    // 行数据：N 固定，k=0..N 的最大乘积数组
    // 约定：k=0 且 N>0 时返回 null；k>N 时返回 null；N=0,k=0 返回 1
    // ----------------------------------------------------------
    function row(N) {
        var arr = [];
        for (var k = 0; k <= N; k++) {
            if (N === 0 && k === 0) {
                arr.push(1);
            } else if (k === 0 || k > N) {
                arr.push(null);
            } else {
                arr.push(maxProduct(N, k));
            }
        }
        return arr;
    }

    // ----------------------------------------------------------
    // 完整纯矩阵：N=0..n, k=0..n 的二维数值数组（无表头）
    //   result[N][k] = 最大乘积（或 null 表示无意义）
    // ----------------------------------------------------------
    function matrix(n) {
        var result = [];
        for (var N = 0; N <= n; N++) {
            result.push(row(N));
        }
        return result;
    }

    // ----------------------------------------------------------
    // 带表头矩阵：与 PC_001_三角 风格一致，便于直接写入工作表
    // 结构：
    //   [0][0]="总和"  [0][1]="总数"  [0][3+k]="拆k份"
    //   [m+1][0]=行和  [m+1][1]=m     [m+1][3+k]=最大乘积或""
    // 边界处理：
    //   m=0, k=0 → 1；m>0, k=0 → ""；k>m → ""
    // ----------------------------------------------------------
    function matrixWithHeader(n) {
        var rowsTotal = n + 2;
        var colsTotal = n + 3;
        var colStart = 3;
        var outArr = [];
        for (var i = 0; i < rowsTotal; i++) {
            outArr.push(new Array(colsTotal).fill(''));
        }

        // 表头
        outArr[0][0] = "总和";
        outArr[0][1] = "总数";
        for (var k = 0; k <= n; k++) {
            outArr[0][colStart + k] = "拆" + k + "份";
        }

        var rowIdx = 1;
        for (var m = 0; m <= n; m++) {
            outArr[rowIdx][1] = m;
            var sumRow = 0;

            if (m === 0) {
                // N=0 行：仅 k=0 处填 1（空积约定）
                outArr[rowIdx][colStart + 0] = 1;
                sumRow = 1;
                for (var k1 = 1; k1 <= n; k1++) {
                    outArr[rowIdx][colStart + k1] = "";
                }
            } else {
                // k=0：N>0 时无法分拆为 0 份，留空
                outArr[rowIdx][colStart + 0] = "";
                // k=1..m：最大乘积
                for (var k2 = 1; k2 <= m; k2++) {
                    var val = maxProduct(m, k2);
                    outArr[rowIdx][colStart + k2] = val;
                    sumRow += val;
                }
                // k=m+1..n：k>N，无法分拆，留空
                for (var k3 = m + 1; k3 <= n; k3++) {
                    outArr[rowIdx][colStart + k3] = "";
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
        maxProduct: maxProduct,
        partitionPlan: partitionPlan,
        bestK: bestK,
        row: row,
        matrix: matrix,
        matrixWithHeader: matrixWithHeader
    };
}));
