// PC_008_统合排列组合_Lib.js
// 统合多脚本优点的排列组合核心库（纯函数，无 Excel/WPS 依赖）
// 对应 VBA 版 PC_008_统合排列组合.TXT
//
// 统合来源：
//   - 以 PC_007（排列组合四象限）为底本：四象限计数 / 矩阵 / 枚举主体
//   - 参考 PC_001（三角）：元素"镜像 / 去镜像"的说法
//   - 参考 PC_004（映射全排列）：二维数组行 / 列优先、元素 + 映射双列输出
//   - 参考 PC_002（排列组合）：枚举"参照范围 + 数值(all / 单值 k / 区间 k1-k2)"
//   - 参考 PC_005（选择范围全排列）：范围输入去空单元格选项
//
// 四象限定义（镜像说法沿用 PC_001）：
//   Type 1: 组合不放回 C(n,k)      (元素不重复 · 去镜像)
//   Type 2: 组合放回   C(n+k-1,k)  (元素可重复 · 去镜像)
//   Type 3: 排列不放回 A(n,k)      (元素不重复 · 镜像)
//   Type 4: 排列放回   n^k         (元素可重复 · 镜像)
//
// 数值约定（沿用 PC_007）：
//   0 = 不可选择。任何类型 k > n 时矩阵填 0（不再留空）；
//       放回类型 n = 0 且 k > 0 时同样不可选择，计数函数返回 0。
//
// ======================== 引入方式 ========================
// 方式1（WPS 宏）：将本文件代码粘贴到一个 JS 模块（建议命名 PC8Lib）
// 方式2（Node.js）：const PC8 = require('./PC_008_统合排列组合_Lib.js');
// 方式3（浏览器）：<script src="PC_008_统合排列组合_Lib.js"></script>
//
// ======================== API 一览 ========================
// PC8.count(n, k, type)                    单值：计算排列/组合数量
// PC8.matrixWithHeader(nMax, type)         带表头矩阵：n=0..N, k=0..N
// PC8.enumerateIdx(m, k, type)             枚举：基于索引 1..m 生成（每项长度 k）
// PC8.buildEnumBlock(elements, k, type)    枚举块：{header, rows}（序号+元素+映射）
// PC8.flattenRange(value, rowMajor, skipEmpty) 范围扁平化（行/列优先 + 去空）
// PC8.parseComboRange(s, m)                解析 all / 单值 k / 区间 k1-k2
// PC8.TYPE / PC8.TYPE_NAME                 常量对象
// PC8.MAX_ENUM / MAX_ROWS / MAX_COLS       安全上限
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
        g.PC8 = factory();
    }
}(function () {
    'use strict';

    // 类型常量
    var TYPE = {
        NOREP_COMB: 1,   // 组合不放回 C(n,k)
        REP_COMB: 2,     // 组合放回 C(n+k-1,k)
        NOREP_PERM: 3,   // 排列不放回 A(n,k)
        REP_PERM: 4      // 排列放回 n^k
    };

    // 类型中文名（镜像说法）
    var TYPE_NAME = {
        1: "组合不放回 C(n,k)",
        2: "组合放回 C(n+k-1,k)",
        3: "排列不放回 A(n,k)",
        4: "排列放回 n^k"
    };

    // 安全上限
    var MAX_ENUM = 10000000;   // 枚举安全上限（内存保护）
    var MAX_ROWS = 1048576;    // 工作表最大行数（写入保护）
    var MAX_COLS = 16384;      // 工作表最大列数（写入保护）

    // ----------------------------------------------------------
    // 工具：组合数 C(n,r) 用浮点安全计算（避免中间溢出）
    // ----------------------------------------------------------
    function combinationDD(n, r) {
        if (r < 0 || r > n) return 0;
        if (r === 0 || r === n) return 1;
        if (r > n - r) r = n - r;
        var res = 1;
        for (var i = 1; i <= r; i++) {
            res = res * (n - r + i) / i;
        }
        return Math.round(res);
    }

    // ----------------------------------------------------------
    // 工具：排列数 A(n,k) = n*(n-1)*...*(n-k+1)
    // ----------------------------------------------------------
    function permCount(n, k) {
        if (k < 0 || k > n) return 0;
        var res = 1;
        for (var i = 0; i < k; i++) {
            res = res * (n - i);
        }
        return res;
    }

    // ----------------------------------------------------------
    // 计数：C(n,k) 组合不放回（0 = 不可选择）
    // ----------------------------------------------------------
    function countCombNoRepet(n, k) {
        if (k < 0 || k > n) return 0;   // 0 = 不可选择（k > n）
        if (k === 0 || k === n) return 1;
        return combinationDD(n, k);
    }

    // ----------------------------------------------------------
    // 计数：C(n+k-1,k) 组合放回（0 = 不可选择）
    // ----------------------------------------------------------
    function countCombRepet(n, k) {
        if (k < 0 || k > n || n < 1) return 0;  // 0 = 不可选择（k > n 或 n=0 且 k>0）
        if (k === 0) return 1;
        return combinationDD(n + k - 1, k);
    }

    // ----------------------------------------------------------
    // 计数：A(n,k) 排列不放回（0 = 不可选择）
    // ----------------------------------------------------------
    function countPermNoRepet(n, k) {
        if (k < 0 || k > n) return 0;   // 0 = 不可选择（k > n）
        if (k === 0) return 1;
        return permCount(n, k);
    }

    // ----------------------------------------------------------
    // 计数：n^k 排列放回（0 = 不可选择）
    // ----------------------------------------------------------
    function countPermRepet(n, k) {
        if (k < 0 || k > n) return 0;   // 0 = 不可选择（k > n）
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
    // 枚举：组合不放回（回溯法，索引严格递增）→ 每项为 1 基索引数组
    // ----------------------------------------------------------
    function enumerateCombNoRepetIdx(m, k) {
        if (k < 1 || k > m) return null;   // 0 = 不可选择（k > m）
        var total = combinationDD(m, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var res = new Array(k);
        function rec(start, depth) {
            if (depth > k) {
                result.push(res.slice());
                return;
            }
            var maxI = m - (k - depth);
            for (var i = start; i <= maxI; i++) {
                res[depth - 1] = i;
                rec(i + 1, depth + 1);
            }
        }
        rec(1, 1);
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：组合放回（非递减索引迭代）→ 每项为 1 基索引数组
    // ----------------------------------------------------------
    function enumerateCombRepetIdx(m, k) {
        if (k < 1 || k > m || m < 1) return null;   // 0 = 不可选择（k > m）
        var total = combinationDD(m + k - 1, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var idx = new Array(k).fill(1);   // 值 1..m
        while (true) {
            result.push(idx.slice());
            var p = k - 1;
            while (p >= 0 && idx[p] >= m) p--;
            if (p < 0) break;
            idx[p]++;
            for (var q = p + 1; q < k; q++) idx[q] = idx[p];
        }
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：排列不放回（回溯 + used 标记）→ 每项为 1 基索引数组
    // ----------------------------------------------------------
    function enumeratePermNoRepetIdx(m, k) {
        if (k < 1 || k > m) return null;   // 0 = 不可选择（k > m）
        var total = permCount(m, k);
        if (total > MAX_ENUM) return null;
        var result = [];
        var used = new Array(m + 1).fill(false);   // 索引 1..m
        var res = new Array(k);
        function rec(depth) {
            if (depth > k) {
                result.push(res.slice());
                return;
            }
            for (var i = 1; i <= m; i++) {
                if (!used[i]) {
                    used[i] = true;
                    res[depth - 1] = i;
                    rec(depth + 1);
                    used[i] = false;
                }
            }
        }
        rec(1);
        return result;
    }

    // ----------------------------------------------------------
    // 枚举：排列放回（m 进制进位法）→ 每项为 1 基索引数组
    // ----------------------------------------------------------
    function enumeratePermRepetIdx(m, k) {
        if (k < 1 || k > m || m < 1) return null;   // 0 = 不可选择（k > m）
        var total = Math.pow(m, k);
        if (!isFinite(total) || total > MAX_ENUM) return null;
        var result = [];
        var idx = new Array(k).fill(1);   // 值 1..m
        while (true) {
            result.push(idx.slice());
            var i = k - 1;
            while (i >= 0) {
                if (idx[i] < m) { idx[i]++; break; }
                else { idx[i] = 1; i--; }
            }
            if (i < 0) break;
        }
        return result;
    }

    // ----------------------------------------------------------
    // 统一枚举入口：基于索引生成，返回二维数组（每项为 1 基索引数组）
    // ----------------------------------------------------------
    function enumerateIdx(m, k, type) {
        switch (type) {
            case TYPE.NOREP_COMB: return enumerateCombNoRepetIdx(m, k);
            case TYPE.REP_COMB:   return enumerateCombRepetIdx(m, k);
            case TYPE.NOREP_PERM: return enumeratePermNoRepetIdx(m, k);
            case TYPE.REP_PERM:   return enumeratePermRepetIdx(m, k);
            default: return null;
        }
    }

    // ----------------------------------------------------------
    // 范围扁平化：把 Range.Value（二维/一维数组或标量）转为 1 维数组
    // 参数：rowMajor = true 行优先 / false 列优先；skipEmpty = true 去空
    // ----------------------------------------------------------
    function isBlank(v) {
        if (v === null || v === undefined) return true;
        if (typeof v === 'string' && v.trim() === '') return true;
        return false;
    }

    function flattenRange(value, rowMajor, skipEmpty) {
        var out = [];
        function push(v) {
            if (isBlank(v)) {
                if (!skipEmpty) out.push(v);
            } else {
                out.push(v);
            }
        }
        if (Array.isArray(value)) {
            var is2D = value.length > 0 && Array.isArray(value[0]);
            if (is2D) {
                var rows = value.length;
                var cols = value[0].length;
                if (rowMajor) {
                    for (var i = 0; i < rows; i++)
                        for (var j = 0; j < cols; j++) push(value[i][j]);
                } else {
                    for (var j = 0; j < cols; j++)
                        for (var i = 0; i < rows; i++) push(value[i][j]);
                }
            } else {
                for (var i = 0; i < value.length; i++) push(value[i]);
            }
        } else {
            push(value);   // 标量（单单元格）
        }
        return out;
    }

    // ----------------------------------------------------------
    // 枚举块：把索引枚举映射回实际元素，输出"序号 + 元素 + 映射"双列
    // 返回：{ header: [...], rows: [[序号, 元素1..k, 映射1..k], ...], count }
    //       或 null（不可选择 / 超限）
    // ----------------------------------------------------------
    function buildEnumBlock(elements, k, type) {
        var m = elements.length;
        var res = enumerateIdx(m, k, type);
        if (!res) return null;

        var header = ["序号"];
        for (var j = 1; j <= k; j++) header.push("元素" + j);
        for (var j = 1; j <= k; j++) header.push("映射" + j);

        var rows = [];
        for (var i = 0; i < res.length; i++) {
            var item = res[i];
            var row = [i + 1];
            for (var j = 0; j < k; j++) row.push(elements[item[j] - 1]);  // 元素 = arr(索引)
            for (var j = 0; j < k; j++) row.push(item[j]);                 // 映射 = 索引
            rows.push(row);
        }
        return { header: header, rows: rows, count: res.length };
    }

    // ----------------------------------------------------------
    // 解析组合长度输入：all / 单值 k / 区间 k1-k2
    // 返回：{ start, end }（1 基，闭区间）或 null（非法）
    // ----------------------------------------------------------
    function parseComboRange(s, m) {
        s = String(s).trim();
        if (s === '') return null;
        var t = s.toLowerCase()
                 .replace(/[，；]/g, '-')   // 中文逗号 / 分号统一为 '-'
                 .replace(/\s+/g, '');
        var start, end;
        if (t === 'all') {
            start = 1; end = m;
        } else if (t.indexOf('-') >= 0) {
            var parts = t.split('-');
            if (parts.length !== 2) return null;
            start = parseInt(parts[0], 10);
            end = parseInt(parts[1], 10);
            if (isNaN(start) || isNaN(end)) return null;
        } else {
            start = end = parseInt(t, 10);
            if (isNaN(start)) return null;
        }
        if (start < 1 || end < 1 || start > end || end > m) return null;
        return { start: start, end: end };
    }

    // ----------------------------------------------------------
    // 带表头矩阵：n=0..nMax, k=0..nMax（0 = 不可选择）
    // 列布局：0=总和, 1=总数, 2+ = 选 k 个
    // ----------------------------------------------------------
    function matrixWithHeader(nMax, type) {
        var rowsTotal = nMax + 2;
        var colsTotal = nMax + 3;
        var colStart = 2;   // 0 基：0=总和, 1=总数, 2=选0个
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
            for (var k = 0; k <= nMax; k++) {
                // 任何类型 k > n 均返回 0（不可选择），放回类型 n=0 且 k>0 也返回 0
                var val = count(n, k, type);
                outArr[rowIdx][colStart + k] = val;
                sumRow += val;
            }
            outArr[rowIdx][0] = sumRow;
            rowIdx++;
        }
        return outArr;
    }

    // 工具：类型中文名
    function typeName(type) {
        return TYPE_NAME[type] || "未知类型";
    }

    // 导出 API
    return {
        version: '1.0.0',
        TYPE: TYPE,
        TYPE_NAME: TYPE_NAME,
        MAX_ENUM: MAX_ENUM,
        MAX_ROWS: MAX_ROWS,
        MAX_COLS: MAX_COLS,
        count: count,
        countCombNoRepet: countCombNoRepet,
        countCombRepet: countCombRepet,
        countPermNoRepet: countPermNoRepet,
        countPermRepet: countPermRepet,
        enumerateIdx: enumerateIdx,
        buildEnumBlock: buildEnumBlock,
        flattenRange: flattenRange,
        parseComboRange: parseComboRange,
        matrixWithHeader: matrixWithHeader,
        typeName: typeName
    };
}));