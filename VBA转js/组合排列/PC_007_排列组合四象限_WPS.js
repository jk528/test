// PC_007_排列组合四象限_WPS.js - 适配 WPS 环境的 JavaScript 代码
// 排列组合四象限矩阵生成（单点查询 + 批量矩阵）
//
// 前置条件：
//   在 WPS 宏编辑器中插入一个 JS 模块（建议命名 PC7Lib），
//   把 PC_007_排列组合四象限_Lib.js 全部内容粘贴进去。
//
// 四象限：
//   Type 1: 组合不放回 C(n, k)
//   Type 2: 组合放回 C(n+k-1, k)
//   Type 3: 排列不放回 A(n, k)
//   Type 4: 排列放回 n^k
//   Type 5: 全部生成

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

// 主函数：生成排列组合四象限矩阵
function 生成_排列组合四象限矩阵() {
    if (typeof PC === 'undefined') {
        Application.MsgBox(
            "未检测到 PC 库！\n" +
            "请先在 WPS 宏编辑器中插入一个 JS 模块（建议命名 PC7Lib），\n" +
            "并把 PC_007_排列组合四象限_Lib.js 的全部内容粘贴进去。",
            16, "集成错误"
        );
        return;
    }

    var typeChoice = Application.InputBox(
        "请选择类型：\n" +
        "1 = 组合不放回 C(n,k)\n" +
        "2 = 组合放回 C(n+k-1,k)\n" +
        "3 = 排列不放回 A(n,k)\n" +
        "4 = 排列放回 n^k\n" +
        "5 = 全部生成（all）",
        "排列组合四象限类型选择",
        "5",
        100, 100, "", 0, 1
    );
    if (typeChoice === false) return;
    var typeInput = parseInt(typeChoice);
    if (isNaN(typeInput) || typeInput < 1 || typeInput > 5) {
        Application.MsgBox("类型必须是 1..5 的整数。", 48);
        return;
    }

    var NInput = Application.InputBox(
        "请输入总数最大值 N（>=0）：",
        "排列组合四象限 - N设置",
        "10",
        100, 100, "", 0, 1
    );
    if (NInput === false) return;
    var n = parseInt(NInput);
    if (isNaN(n) || n < 0) {
        Application.MsgBox("N 必须为 >= 0 的整数。", 48);
        return;
    }

    // 大数预警
    var maxVal = PC.count(n, Math.floor(n / 2), PC.TYPE.NOREP_COMB);
    if (maxVal > 1e14) {
        var confirm = Application.MsgBox(
            "N=" + n + " 时部分值可能超出精确表示范围 (2^53)，\n" +
            "结果将出现浮点精度损失。\n\n是否继续？",
            4 + 48,
            "大数精度预警"
        );
        if (confirm !== 6) return;
    }

    var startTime = new Date().getTime();

    var typeConfigs = {
        1: { name: "排列组合_组合不放回_C(n,k)", type: PC.TYPE.NOREP_COMB },
        2: { name: "排列组合_组合放回_C(n+k-1,k)", type: PC.TYPE.REP_COMB },
        3: { name: "排列组合_排列不放回_A(n,k)", type: PC.TYPE.NOREP_PERM },
        4: { name: "排列组合_排列放回_n^k", type: PC.TYPE.REP_PERM }
    };

    var typesToGenerate = typeInput === 5 ? [1, 2, 3, 4] : [typeInput];

    for (var t = 0; t < typesToGenerate.length; t++) {
        var cfg = typeConfigs[typesToGenerate[t]];
        var outArr = PC.matrixWithHeader(n, cfg.type);
        var ws = GetOrInitWorksheet(cfg.name);
        ws.Cells.Clear();

        var rows = outArr.length;
        var cols = outArr[0].length;
        try {
            ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols)).Value2 = outArr;
        } catch (e) {
            for (var i = 0; i < rows; i++) {
                for (var j = 0; j < cols; j++) {
                    ws.Cells(i + 1, j + 1).Value2 = outArr[i][j];
                }
            }
        }
        ws.Columns.AutoFit();
    }

    var endTime = new Date().getTime();
    var elapsed = ((endTime - startTime) / 1000).toFixed(3);
    var typeLabel = typeInput === 5 ? "全部4种" : PC.TYPE_NAME[typeInput];
    console.log("已生成【" + typeLabel + "】（N=0.." + n + "）到工作表。用时：" + elapsed + " 秒");
}

// 演示 1：单点查询
function 演示_单点查询() {
    if (typeof PC === 'undefined') {
        Application.MsgBox("请先导入 PC7Lib 模块", 16);
        return;
    }
    var nInput = Application.InputBox("请输入 n：", "单点查询-n", "5", 100, 100, "", 0, 1);
    if (nInput === false) return;
    var kInput = Application.InputBox("请输入 k：", "单点查询-k", "2", 100, 100, "", 0, 1);
    if (kInput === false) return;
    var n = parseInt(nInput);
    var k = parseInt(kInput);

    var msg = "n=" + n + ", k=" + k + "\n\n";
    msg += "组合不放回 C(n,k) = " + PC.count(n, k, PC.TYPE.NOREP_COMB) + "\n";
    msg += "组合放回 C(n+k-1,k) = " + PC.count(n, k, PC.TYPE.REP_COMB) + "\n";
    msg += "排列不放回 A(n,k) = " + PC.count(n, k, PC.TYPE.NOREP_PERM) + "\n";
    msg += "排列放回 n^k = " + PC.count(n, k, PC.TYPE.REP_PERM);

    Application.MsgBox(msg, 64, "排列组合单点查询");
}

// 演示 2：枚举生成
function 演示_枚举生成() {
    if (typeof PC === 'undefined') {
        Application.MsgBox("请先导入 PC7Lib 模块", 16);
        return;
    }

    var dataInput = Application.InputBox(
        "请输入元素列表（逗号分隔）：\n例如: A,B,C,D",
        "枚举生成-元素",
        "A,B,C",
        100, 100, "", 0, 2
    );
    if (dataInput === false) return;

    var arr = String(dataInput).split(/[,，]/).map(function (s) { return s.trim(); }).filter(function (s) { return s.length > 0; });
    if (arr.length === 0) {
        Application.MsgBox("元素列表为空", 48);
        return;
    }

    var kInput = Application.InputBox("请输入 k（选取数量）：", "枚举生成-k", "2", 100, 100, "", 0, 1);
    if (kInput === false) return;
    var k = parseInt(kInput);

    var typeChoice = Application.InputBox(
        "请选择类型：\n1 = 组合不放回\n2 = 组合放回\n3 = 排列不放回\n4 = 排列放回",
        "枚举生成-类型",
        "1",
        100, 100, "", 0, 1
    );
    if (typeChoice === false) return;
    var type = parseInt(typeChoice);
    if (type < 1 || type > 4) {
        Application.MsgBox("类型必须是 1..4", 48);
        return;
    }

    var result = PC.enumerate(arr, k, type);
    if (result === null) {
        var total = PC.count(arr.length, k, type);
        if (total > PC.MAX_ENUM) {
            Application.MsgBox(
                "结果数量 = " + total + " 超过上限 " + PC.MAX_ENUM + "，\n" +
                "无法枚举。请减少元素数量或 k 值。",
                48, "数量过大"
            );
        } else {
            Application.MsgBox("无法生成（参数非法？）", 48);
        }
        return;
    }

    // 写入工作表
    var ws = GetOrInitWorksheet("枚举结果");
    ws.Cells.Clear();

    // 表头
    var header = [];
    for (var c = 1; c <= k; c++) header.push("第" + c + "位");
    header.push("序号");
    ws.Range(ws.Cells(1, 1), ws.Cells(1, k + 1)).Value2 = header;

    // 数据
    var rowData = [];
    for (var idx = 0; idx < result.length; idx++) {
        var item = result[idx].slice();
        item.push(idx + 1);
        rowData.push(item);
    }

    try {
        ws.Range(ws.Cells(2, 1), ws.Cells(result.length + 1, k + 1)).Value2 = rowData;
    } catch (e) {
        for (var r = 0; r < rowData.length; r++) {
            for (var c = 0; c < rowData[r].length; c++) {
                ws.Cells(r + 2, c + 1).Value2 = rowData[r][c];
            }
        }
    }
    ws.Columns.AutoFit();

    Application.MsgBox(
        "已生成 " + result.length + " 条" + PC.TYPE_NAME[type] + "结果\n" +
        "到工作表【枚举结果】",
        64, "枚举完成"
    );
}

// 综合演示入口
function 演示_排列组合四象限() {
    if (typeof PC === 'undefined') {
        Application.MsgBox("请先导入 PC7Lib 模块", 16);
        return;
    }

    var choice = Application.InputBox(
        "请选择要运行的演示：\n" +
        "1 = 生成矩阵到工作表\n" +
        "2 = 单点查询\n" +
        "3 = 枚举生成（列出所有具体项）\n" +
        "4 = 全部依次运行",
        "排列组合四象限演示", "1", 100, 100, "", 0, 1
    );
    if (choice === false) return;
    var op = parseInt(choice);
    if (isNaN(op) || op < 1 || op > 4) {
        Application.MsgBox("请输入 1..4", 48);
        return;
    }

    switch (op) {
        case 1: 生成_排列组合四象限矩阵(); break;
        case 2: 演示_单点查询(); break;
        case 3: 演示_枚举生成(); break;
        case 4:
            生成_排列组合四象限矩阵();
            演示_单点查询();
            演示_枚举生成();
            break;
    }
}
