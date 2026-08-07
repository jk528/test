// PC_006_AMGM分拆最大乘积_WPS.js - 适配 WPS 环境的 JavaScript 代码
// 基于 AM-GM 不等式的离散均匀分拆最大乘积矩阵
//
// 问题：给定正整数 N，将其分拆为 k 个正整数之和 a1+a2+...+ak = N (ai>=1)
//       求乘积 P = a1*a2*...*ak 的最大值。
//
// 由 AM-GM 不等式：(a1+a2+...+ak)/k >= (a1*a2*...*ak)^(1/k)
// 即 N/k >= P^(1/k)，故 P <= (N/k)^k，当各 ai 相等时取等。
//
// 由于 ai 必须为正整数，最优分拆为：
//   设 N = q*k + r  (0 <= r < k)
//     - r = 0：所有份 = q，最大乘积 = q^k
//     - r > 0：r 份 = (q+1)，(k-r) 份 = q，最大乘积 = (q+1)^r * q^(k-r)

// 单元最大乘积计算函数
// 返回：将 N 分拆为 k 份正整数之和时的最大乘积；非法情形返回 0
function MaxProductPartition(N, k) {
    if (N === 0 && k === 0) return 1;       // 空分拆，约定空积为 1
    if (N <= 0 || k <= 0) return 0;         // 非法参数
    if (k > N) return 0;                     // 每份至少为 1，k 不能超过 N
    var q = Math.floor(N / k);
    var r = N % k;
    var prod = 1;
    // (k-r) 份 q
    for (var i = 0; i < k - r; i++) prod *= q;
    // r 份 (q+1)
    for (var j = 0; j < r; j++) prod *= (q + 1);
    return prod;
}

// 构建 AM-GM 分拆最大乘积矩阵二维数组
// 行：N = 0..n (被分拆总和)；列：k = 0..n (分拆份数)
function 构建_AMGM分拆最大乘积_矩阵(n) {
    var rowsTotal = n + 2;     // 1 表头 + (n+1) 数据行
    var colsTotal = n + 3;     // 总和列 + 总数列 + (n+1) 个 k 列
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

    var row = 1;
    for (var m = 0; m <= n; m++) {
        outArr[row][1] = m;
        var sumRow = 0;

        if (m === 0) {
            // N=0 行：仅 k=0 处填 1（空积约定），其余空
            outArr[row][colStart + 0] = 1;
            sumRow = 1;
            for (var k = 1; k <= n; k++) {
                outArr[row][colStart + k] = "";
            }
        } else {
            // k=0：N>0 时无法分拆为 0 份，留空
            outArr[row][colStart + 0] = "";
            // k=1..m：最大乘积
            for (var k = 1; k <= m; k++) {
                var val = MaxProductPartition(m, k);
                outArr[row][colStart + k] = val;
                sumRow += val;
            }
            // k=m+1..n：k>N，无法分拆，留空
            for (var k2 = m + 1; k2 <= n; k2++) {
                outArr[row][colStart + k2] = "";
            }
        }

        outArr[row][0] = sumRow;
        row++;
    }

    return outArr;
}

// 工具：获取或创建工作表
function GetOrInitWorksheet(Name) {
    var ws;
    try {
        ws = ThisWorkbook.Worksheets(Name);
    } catch (e) {
        ws = ThisWorkbook.Worksheets.Add();
        ws.Name = Name;
    }
    return ws;
}

// 主函数：生成 AM-GM 分拆最大乘积矩阵
function 生成_AMGM分拆最大乘积矩阵() {
    var NInput = Application.InputBox(
        "请输入总数最大值 N（>=0）：\n" +
        "矩阵将列出 N=0..N, k=0..N 各组合的最大乘积。\n\n" +
        "AM-GM 不等式原理：\n" +
        "  N = q*k + r (0 <= r < k)\n" +
        "  r = 0 时  P = q^k\n" +
        "  r > 0 时  P = (q+1)^r * q^(k-r)",
        "AM-GM 分拆最大乘积矩阵 - N 设置",
        "12",
        100, 100, "", 0, 1
    );
    if (NInput === false) return;
    var n = parseInt(NInput, 10);
    if (isNaN(n) || n < 0) {
        Application.MsgBox("N 必须为 >= 0 的整数。", 48, "输入错误");
        return;
    }

    // 大数预警：JS Number 双精度精确范围约 2^53 ≈ 9e15
    // N=55, k≈18 时 q=3, 3^18 ≈ 3.87e8 仍在范围内；
    // N=60, k≈20 时 3^20 ≈ 3.49e9 仍在范围内；
    // N>=80 时部分乘积将超出精确表示范围
    if (n > 60) {
        var confirm = Application.MsgBox(
            "N=" + n + " 时部分乘积可能超出 2^53 (约 9e15) 精确表示范围，\n" +
            "结果将出现浮点精度损失。\n\n是否继续？",
            4 + 48,   // vbYesNo + vbExclamation
            "大数精度预警"
        );
        if (confirm !== 6) return;   // vbYes = 6
    }

    var startTime = new Date().getTime();

    var sheetName = "AMGM分拆最大乘积矩阵";
    var outArr = 构建_AMGM分拆最大乘积_矩阵(n);
    var ws = GetOrInitWorksheet(sheetName);
    ws.Cells.Clear();

    var rows = outArr.length;
    var cols = outArr[0].length;
    try {
        var range = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols));
        range.Value2 = outArr;
    } catch (e) {
        Application.MsgBox("数组赋值失败，正在使用逐单元格写入方式...", 48, "提示");
        for (var i = 0; i < rows; i++) {
            for (var j = 0; j < cols; j++) {
                ws.Cells(i + 1, j + 1).Value2 = outArr[i][j];
            }
        }
    }

    ws.Columns.AutoFit();

    var endTime = new Date().getTime();
    var elapsed = ((endTime - startTime) / 1000).toFixed(3);
    console.log("已生成【AM-GM 分拆最大乘积矩阵】（N=0.." + n + ", k=0.." + n + "）到工作表。用时：" + elapsed + " 秒");
}
