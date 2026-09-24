// PC_006_AMGM分拆最大乘积_使用示例_WPS.js
// 演示如何在 WPS 宏中集成并调用 AMGM 库
//
// 前置条件（必读）：
//   1. 在 WPS 宏编辑器中插入一个 JS 模块，命名为 AMGMLib
//   2. 把 PC_006_AMGM分拆最大乘积_Lib.js 全部内容粘贴到 AMGMLib 模块中
//   3. 然后把本文件内容粘贴到另一个 JS 模块中
//   4. 运行 演示_AMGM库集成调用()
//
// 原理：WPS JS 宏中所有模块共享同一全局作用域，
//      Lib 中的 UMD 包装在 WPS 宏环境下会走 `root.AMGM = factory()` 分支，
//      把 AMGM 对象挂载到全局，其他模块可直接使用。

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

// 示例 1：单值查询 - 查询 N=10 拆成 3 份的最大乘积
function 示例1_单值查询() {
    var N = 10, k = 3;
    var prod = AMGM.maxProduct(N, k);
    var plan = AMGM.partitionPlan(N, k);
    Application.MsgBox(
        "N=" + N + " 拆成 " + k + " 份：\n" +
        "最大乘积 = " + prod + "\n" +
        "拆分方案 = " + plan.join(" + ") + " = " + N,
        64, "AMGM 单值查询"
    );
}

// 示例 2：找最优 k - 给定 N，自动找使乘积最大的 k
function 示例2_最优k查询() {
    var NInput = Application.InputBox("请输入 N（>=1）：", "最优 k 查询", "20", 100, 100, "", 0, 1);
    if (NInput === false) return;
    var N = parseInt(NInput, 10);
    if (isNaN(N) || N < 1) {
        Application.MsgBox("N 必须 >= 1", 48);
        return;
    }
    var best = AMGM.bestK(N);
    var plan = AMGM.partitionPlan(N, best.k[0]);
    Application.MsgBox(
        "N = " + N + "\n" +
        "最优 k = " + best.k.join(" 或 ") + "\n" +
        "最大乘积 = " + best.maxProd + "\n" +
        "拆分方案 = " + plan.join(" + ") + " = " + N,
        64, "AMGM 最优 k 查询"
    );
}

// 示例 3：完整矩阵输出 - 调用 matrixWithHeader 直接写入工作表
function 示例3_输出完整矩阵() {
    var NInput = Application.InputBox("请输入 N（>=0）：", "矩阵输出", "12", 100, 100, "", 0, 1);
    if (NInput === false) return;
    var n = parseInt(NInput, 10);
    if (isNaN(n) || n < 0) {
        Application.MsgBox("N 必须 >= 0", 48);
        return;
    }
    var outArr = AMGM.matrixWithHeader(n);
    var ws = GetOrInitWorksheet("AMGM分拆最大乘积矩阵");
    ws.Cells.Clear();
    var rows = outArr.length, cols = outArr[0].length;
    ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols)).Value2 = outArr;
    ws.Columns.AutoFit();
    Application.MsgBox("已生成 N=0.." + n + " 的矩阵到工作表【AMGM分拆最大乘积矩阵】", 64);
}

// 示例 4：最优分析报告 - 每行最优 k + 拆分方案，写入工作表
function 示例4_最优分析报告() {
    var NInput = Application.InputBox("请输入 N 上限（>=1）：", "最优分析", "30", 100, 100, "", 0, 1);
    if (NInput === false) return;
    var nMax = parseInt(NInput, 10);
    if (isNaN(nMax) || nMax < 1) {
        Application.MsgBox("N 必须 >= 1", 48);
        return;
    }

    var ws = GetOrInitWorksheet("AMGM最优分析报告");
    ws.Cells.Clear();

    // 表头
    var header = ["N", "最优k", "并列k", "最大乘积", "拆分方案", "乘积位数"];
    ws.Range(ws.Cells(1, 1), ws.Cells(1, header.length)).Value2 = header;

    var row = 2;
    for (var N = 1; N <= nMax; N++) {
        var best = AMGM.bestK(N);
        var plan = AMGM.partitionPlan(N, best.k[0]);
        var digits = String(best.maxProd).length;
        ws.Cells(row, 1).Value2 = N;
        ws.Cells(row, 2).Value2 = best.k[0];
        ws.Cells(row, 3).Value2 = best.k.length > 1 ? best.k.join(",") : "";
        ws.Cells(row, 4).Value2 = best.maxProd;
        ws.Cells(row, 5).Value2 = plan.join("+");
        ws.Cells(row, 6).Value2 = digits;
        row++;
    }
    ws.Columns.AutoFit();
    Application.MsgBox("已生成 N=1.." + nMax + " 的最优分析到工作表【AMGM最优分析报告】", 64);
}

// 综合演示入口：依次执行 4 个示例
function 演示_AMGM库集成调用() {
    if (typeof AMGM === 'undefined') {
        Application.MsgBox(
            "未检测到 AMGM 库！\n" +
            "请先在 WPS 宏编辑器中插入一个 JS 模块（建议命名 AMGMLib），\n" +
            "并把 PC_006_AMGM分拆最大乘积_Lib.js 的全部内容粘贴进去。",
            16, "集成错误"
        );
        return;
    }

    var choice = Application.InputBox(
        "请选择要运行的示例：\n" +
        "1 = 单值查询（N=10, k=3）\n" +
        "2 = 最优 k 查询（输入 N）\n" +
        "3 = 输出完整矩阵到工作表\n" +
        "4 = 最优分析报告（每行最优 k + 方案）\n" +
        "5 = 全部依次运行",
        "AMGM 库集成演示", "1", 100, 100, "", 0, 1
    );
    if (choice === false) return;
    var op = parseInt(choice, 10);
    if (isNaN(op) || op < 1 || op > 5) {
        Application.MsgBox("请输入 1..5", 48);
        return;
    }

    switch (op) {
        case 1: 示例1_单值查询(); break;
        case 2: 示例2_最优k查询(); break;
        case 3: 示例3_输出完整矩阵(); break;
        case 4: 示例4_最优分析报告(); break;
        case 5:
            示例1_单值查询();
            示例2_最优k查询();
            示例3_输出完整矩阵();
            示例4_最优分析报告();
            break;
    }
}
