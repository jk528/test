// PC_008_统合排列组合_WPS.js - 适配 WPS 宏环境的 JavaScript 入口
// 对应 VBA 版 PC_008_统合排列组合.TXT（统合多脚本优点）
//
// 前置条件：
//   在 WPS 宏编辑器中插入一个 JS 模块（建议命名 PC8Lib），
//   把 PC_008_统合排列组合_Lib.js 全部内容粘贴进去。
//
// 四象限：
//   Type 1: 组合不放回 C(n,k)      (元素不重复 · 去镜像)
//   Type 2: 组合放回   C(n+k-1,k)  (元素可重复 · 去镜像)
//   Type 3: 排列不放回 A(n,k)      (元素不重复 · 镜像)
//   Type 4: 排列放回   n^k         (元素可重复 · 镜像)
//   Type 5: 全部生成（矩阵用）

// ======================== 工具 ========================

// 获取或创建工作表
function GetOrInitWorksheet(Name) {
    var ws = null;
    try {
        ws = ThisWorkbook.Worksheets(Name);
    } catch (e) {
        ws = ThisWorkbook.Worksheets.Add();
        ws.Name = Name;
    }
    return ws;
}

// 检查 PC8 库是否就绪
function PC8Ready() {
    if (typeof PC8 === 'undefined') {
        Application.MsgBox(
            "未检测到 PC8 库！\n" +
            "请先在 WPS 宏编辑器中插入一个 JS 模块（建议命名 PC8Lib），\n" +
            "并把 PC_008_统合排列组合_Lib.js 的全部内容粘贴进去。",
            16, "集成错误"
        );
        return false;
    }
    return true;
}

// ======================== 主菜单 ========================
function 统合_排列组合_主菜单() {
    if (!PC8Ready()) return;
    var op = Application.InputBox(
        "请选择功能：\n\n" +
        "1 = 生成四象限矩阵（N 数值输入）\n" +
        "2 = 单点查询（n、k 数值输入）\n" +
        "3 = 枚举生成（参照范围 + 数值）\n\n" +
        "提示：类型均为 1=组合不放回 / 2=组合放回 /\n" +
        "3=排列不放回 / 4=排列放回",
        "PC8_统合排列组合", "1", 100, 100, "", 0, 1
    );
    if (op === false) return;
    op = parseInt(op);
    if (isNaN(op) || op < 1 || op > 3) {
        Application.MsgBox("请输入 1..3。", 48);
        return;
    }
    if (op === 1) 生成_四象限矩阵();
    else if (op === 2) 演示_单点查询();
    else 演示_枚举生成_范围();
}

// ======================== 入口 1：矩阵生成 ========================
function 生成_四象限矩阵() {
    if (!PC8Ready()) return;

    var typeChoice = Application.InputBox(
        "请选择类型：\n\n" +
        "1 = 组合不放回 C(n,k)      (元素不重复·去镜像)\n" +
        "2 = 组合放回 C(n+k-1,k)    (元素可重复·去镜像)\n" +
        "3 = 排列不放回 A(n,k)      (元素不重复·镜像)\n" +
        "4 = 排列放回 n^k           (元素可重复·镜像)\n" +
        "5 = 全部生成（all）\n\n" +
        "说明：矩阵中 0 = 不可选择（k>n 或 n=0 且 k>0）",
        "PC8_矩阵生成-类型", "5", 100, 100, "", 0, 1
    );
    if (typeChoice === false) return;
    var typeInput = parseInt(typeChoice);
    if (isNaN(typeInput) || typeInput < 1 || typeInput > 5) {
        Application.MsgBox("类型必须是 1..5 的整数。", 48);
        return;
    }

    var NInput = Application.InputBox(
        "请输入总数最大值 N（>=0）：",
        "PC8_矩阵生成-N", "10", 100, 100, "", 0, 1
    );
    if (NInput === false) return;
    var n = parseInt(NInput);
    if (isNaN(n) || n < 0) {
        Application.MsgBox("N 必须为 >= 0 的整数。", 48);
        return;
    }

    // 大数预警
    var maxVal = PC8.count(n, Math.floor(n / 2), PC8.TYPE.NOREP_COMB);
    if (maxVal > 1e14) {
        var c = Application.MsgBox(
            "N=" + n + " 时部分值可能超出精确表示范围 (2^53)，\n" +
            "结果将出现浮点精度损失。\n\n是否继续？",
            4 + 48, "大数精度预警"
        );
        if (c !== 6) return;
    }

    var typeConfigs = {
        1: { name: "四象限_组合不放回_Cnk", type: PC8.TYPE.NOREP_COMB },
        2: { name: "四象限_组合放回_Cnk",   type: PC8.TYPE.REP_COMB },
        3: { name: "四象限_排列不放回_Ank", type: PC8.TYPE.NOREP_PERM },
        4: { name: "四象限_排列放回_nk",   type: PC8.TYPE.REP_PERM }
    };
    var types = typeInput === 5 ? [1, 2, 3, 4] : [typeInput];

    for (var t = 0; t < types.length; t++) {
        var cfg = typeConfigs[types[t]];
        var outArr = PC8.matrixWithHeader(n, cfg.type);
        var ws = GetOrInitWorksheet(cfg.name);
        ws.Cells.Clear();
        var rows = outArr.length;
        var cols = outArr[0].length;
        try {
            ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols)).Value2 = outArr;
        } catch (e) {
            for (var i = 0; i < rows; i++)
                for (var j = 0; j < cols; j++)
                    ws.Cells(i + 1, j + 1).Value2 = outArr[i][j];
        }
        ws.Columns.AutoFit();
    }

    Application.MsgBox(
        "已生成矩阵（N=0.." + n + "）。\n说明：矩阵中 0 = 不可选择。",
        64, "PC8_矩阵生成"
    );
}

// ======================== 入口 2：单点查询 ========================
function 演示_单点查询() {
    if (!PC8Ready()) return;
    var nInput = Application.InputBox("请输入 n：", "PC8_单点查询-n", "5", 100, 100, "", 0, 1);
    if (nInput === false) return;
    var kInput = Application.InputBox("请输入 k：", "PC8_单点查询-k", "2", 100, 100, "", 0, 1);
    if (kInput === false) return;
    var n = parseInt(nInput);
    var k = parseInt(kInput);

    var msg = "n=" + n + ", k=" + k + "\n\n";
    msg += "组合不放回 C(n,k)   (去镜像) = " + PC8.count(n, k, PC8.TYPE.NOREP_COMB) + "\n";
    msg += "组合放回 C(n+k-1,k) (去镜像) = " + PC8.count(n, k, PC8.TYPE.REP_COMB) + "\n";
    msg += "排列不放回 A(n,k)   (镜像)   = " + PC8.count(n, k, PC8.TYPE.NOREP_PERM) + "\n";
    msg += "排列放回 n^k        (镜像)   = " + PC8.count(n, k, PC8.TYPE.REP_PERM) + "\n\n";
    msg += "说明：0 = 不可选择（k>n 或 n=0 且 k>0）";

    Application.MsgBox(msg, 64, "PC8_排列组合单点查询");
}

// ======================== 入口 3：枚举生成（参照范围 + 数值） ========================
function 演示_枚举生成_范围() {
    if (!PC8Ready()) return;

    // 1. 选择数据范围
    var rng = Application.InputBox(
        "请选择数据区域（支持单格、单行、单列或矩形二维区域）：",
        "PC8_枚举生成-选择范围", "", 100, 100, "", 0, 8
    );
    if (rng === false) return;

    // 从 Range 对象提取 Value
    var raw = rng;
    try { if (typeof rng === 'function') raw = rng(); } catch (e) {}
    var value = raw;
    if (raw && typeof raw === 'object' && raw.Value !== undefined) value = raw.Value;

    // 判断是否二维区域（用于决定是否询问展开方式）
    var is2D = Array.isArray(value) && value.length > 0 && Array.isArray(value[0]);
    var rowCount = is2D ? value.length : 1;
    var colCount = is2D ? (value[0] ? value[0].length : 0) : 1;

    // 2. 行/列优先
    var rowMajor = true;
    if (rowCount > 1 && colCount > 1) {
        var lm = Application.InputBox(
            "选择范围是 " + rowCount + " 行 × " + colCount + " 列。\n\n" +
            "二维数组展开方式：\n" +
            "1 = 按行优先（逐行读取）\n" +
            "2 = 按列优先（逐列读取）",
            "PC8_枚举生成-展开方式", "1", 100, 100, "", 0, 1
        );
        if (lm === false) return;
        lm = parseInt(lm);
        if (lm !== 1 && lm !== 2) { Application.MsgBox("请输入 1 或 2。", 48); return; }
        rowMajor = (lm === 1);
    }

    // 3. 去空选项
    var sk = Application.InputBox(
        "是否去除选择范围内的空单元格？\n\n" +
        "1 = 去除空单元格（空单元格不参与计算）\n" +
        "2 = 保留空单元格（空字符串也算一个元素）",
        "PC8_枚举生成-去空选项", "1", 100, 100, "", 0, 1
    );
    if (sk === false) return;
    sk = parseInt(sk);
    if (sk !== 1 && sk !== 2) { Application.MsgBox("请输入 1 或 2。", 48); return; }
    var skipEmpty = (sk === 1);

    // 4. 扁平化
    var elements = PC8.flattenRange(value, rowMajor, skipEmpty);
    if (elements.length === 0) {
        Application.MsgBox("选择区域内无有效数据（可能全部为空）。", 48);
        return;
    }
    var m = elements.length;

    // 5. 选择类型
    var tp = Application.InputBox(
        "请选择类型：\n\n" +
        "1 = 组合不放回 C(m,k)      (元素不重复·去镜像)\n" +
        "2 = 组合放回 C(m+k-1,k)    (元素可重复·去镜像)\n" +
        "3 = 排列不放回 A(m,k)      (元素不重复·镜像)\n" +
        "4 = 排列放回 m^k           (元素可重复·镜像)\n\n" +
        "有效元素数 m = " + m,
        "PC8_枚举生成-类型", "1", 100, 100, "", 0, 1
    );
    if (tp === false) return;
    var typeInput = parseInt(tp);
    if (isNaN(typeInput) || typeInput < 1 || typeInput > 4) {
        Application.MsgBox("类型必须是 1..4。", 48);
        return;
    }

    // 6. 组合长度：all / 单值 k / 区间 k1-k2
    var kRaw = Application.InputBox(
        "组合长度：\n" +
        "all      = 全部（1.." + m + "）\n" +
        "单值 k   = 只生成 k 个\n" +
        "k1-k2    = 区间内全部",
        "PC8_枚举生成-长度", "all", 100, 100, "", 0, 2
    );
    if (kRaw === false) return;
    var parsed = PC8.parseComboRange(String(kRaw), m);
    if (!parsed) {
        Application.MsgBox("组合长度输入非法，请输入 all、单值k或区间k1-k2（范围：1.." + m + "）。", 48);
        return;
    }

    // 7. 输出工作表
    var typeName = PC8.typeName(typeInput);
    var sheetName = "枚举_" + typeName.replace(/[ ()\/]/g, "");
    var ws = GetOrInitWorksheet(sheetName);
    ws.Cells.Clear();
    ws.Range("A1:H1").Value2 = ["功能", "输入", "类型", "k范围", "行/列", "去空", "有效元素", "总项数"];
    ws.Cells(2, 1).Value2 = "枚举生成（参照范围+数值）";
    ws.Cells(2, 2).Value2 = (raw && raw.Address) ? raw.Address : "";
    ws.Cells(2, 3).Value2 = typeName;
    ws.Cells(2, 4).Value2 = String(kRaw);
    ws.Cells(2, 5).Value2 = rowMajor ? "行优先" : "列优先";
    ws.Cells(2, 6).Value2 = skipEmpty ? "去空" : "保留空";
    ws.Cells(2, 7).Value2 = m;
    ws.Cells(2, 8).Value2 = "计算中…";

    var blockRow = 4;
    var totalItems = 0;

    for (var k = parsed.start; k <= parsed.end; k++) {
        // 数量上限检查（溢出保护）
        var expect = PC8.count(m, k, typeInput);
        if (!isFinite(expect) || expect > PC8.MAX_ENUM) {
            ws.Cells(blockRow, 1).Value2 = "== k = " + k + " | 数量 超过上限 " + PC8.MAX_ENUM + "，已跳过 ==";
            blockRow += 2;
            continue;
        }
        if (2 * k + 1 > PC8.MAX_COLS) {
            ws.Cells(blockRow, 1).Value2 = "== k = " + k + " | 列数 " + (2 * k + 1) + " 超过工作表列数上限 " + PC8.MAX_COLS + "，已跳过 ==";
            blockRow += 2;
            continue;
        }

        var block = PC8.buildEnumBlock(elements, k, typeInput);
        if (!block) {
            ws.Cells(blockRow, 1).Value2 = "== k = " + k + " | 无法生成（参数非法或超出上限） ==";
            blockRow += 2;
            continue;
        }

        // 行数保护：数据块最后一行是否超出工作表最大行数
        if (blockRow + block.count - 1 > PC8.MAX_ROWS) {
            ws.Cells(blockRow, 1).Value2 = "== k = " + k + " | 项数 " + block.count + " 超出工作表剩余行数，已跳过 ==";
            blockRow += 2;
            continue;
        }

        totalItems += block.count;

        // 块标题
        ws.Cells(blockRow, 1).Value2 = "== k = " + k + " | 类型 " + typeName + " | 项数 " + block.count + " ==";
        blockRow++;

        // 表头
        var header = block.header;
        try {
            ws.Range(ws.Cells(blockRow, 1), ws.Cells(blockRow, header.length)).Value2 = header;
        } catch (e) {
            for (var hj = 0; hj < header.length; hj++) ws.Cells(blockRow, hj + 1).Value2 = header[hj];
        }
        blockRow++;

        // 数据块
        try {
            ws.Range(ws.Cells(blockRow, 1), ws.Cells(blockRow + block.count - 1, header.length)).Value2 = block.rows;
        } catch (e) {
            for (var bi = 0; bi < block.rows.length; bi++)
                for (var bj = 0; bj < block.rows[bi].length; bj++)
                    ws.Cells(blockRow + bi, bj + 1).Value2 = block.rows[bi][bj];
        }
        blockRow += block.count + 1;   // 块后留一空行
    }

    ws.Cells(2, 8).Value2 = totalItems;
    ws.Columns.AutoFit();

    Application.MsgBox(
        "已生成 " + totalItems + " 条结果到工作表【" + sheetName + "】。\n" +
        "范围：k = " + parsed.start + " - " + parsed.end + "；类型：" + typeName + "\n" +
        "展开：" + (rowMajor ? "行优先" : "列优先") + "；" + (skipEmpty ? "已去空" : "保留空") + "\n" +
        "输出格式：序号 + 元素 + 映射（参考 PC_004）",
        64, "PC8_枚举完成"
    );
}