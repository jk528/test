// PC_003_四方镜子.js - WPS JavaScript 宏代码
// VBA转JS: 四方镜子.TXT
// 四方循环组合核心算法实现 - 纯JS 0基数组

// ========== 全局变量 ==========
var gConnector = "";
var gMergeMode = true;

// ========== 工具函数 ==========

function ShowMessage(message, type) {
    try {
        if (typeof Application.MsgBox === 'function') {
            Application.MsgBox(message, type || 64, "四方镜子");
        } else if (typeof Application.Alert === 'function') {
            Application.Alert(message);
        } else {
            console.log("【消息】" + message);
        }
    } catch (e) {
        console.log("【消息】" + message);
    }
}

function WPSInputBox(prompt, title, defaultValue, type) {
    try {
        return Application.InputBox(prompt, title, defaultValue, 100, 100, "", 0, type || 8);
    } catch (e) {
        console.error("InputBox 调用失败: " + (e.message || String(e)));
        return null;
    }
}

function CycleIndex(n, Y) {
    return ((n + Y - 1) % Y) + 1;
}

function CeilDivide(c, d) {
    return Math.ceil(c / d);
}

function GetLastColumn(sheet) {
    try {
        return sheet.Cells(1, sheet.Columns.Count).End(-4159).Column;
    } catch (e) {
        return sheet.UsedRange.Columns.Count;
    }
}

function GetLastRow(sheet, colIndex) {
    try {
        return sheet.Cells(sheet.Rows.Count, colIndex).End(-4162).Row;
    } catch (e) {
        return sheet.UsedRange.Rows.Count;
    }
}

// ========== 核心算法函数 ==========

function 四方循环组合(正向循环, 横向输出) {
    var ws = Application.ActiveSheet;
    var 列数 = ws.Cells(1, ws.Columns.Count).End(-4159).Column;

    if (列数 <= 0) {
        ShowMessage("无有效数据列", 48);
        return false;
    }

    var 行数据 = [];
    for (var i = 0; i < 4; i++) {
        行数据[i] = [];
        for (var j = 0; j < 列数; j++) {
            行数据[i][j] = 0;
        }
    }

    行数据[1][0] = 1;

    for (var n = 0; n < 列数; n++) {
        行数据[0][n] = GetLastRow(ws, n + 1);
        if (n > 0) {
            行数据[1][n] = 行数据[1][n - 1] * 行数据[0][n - 1];
        }
        行数据[2][n] = 行数据[0][n] * 行数据[1][n];
    }

    for (var n = 0; n < 列数; n++) {
        行数据[3][n] = 行数据[2][列数 - 1] / 行数据[2][n];
    }

    var 最大值 = 0;
    for (var n = 0; n < 列数; n++) {
        if (行数据[0][n] > 最大值) 最大值 = 行数据[0][n];
        if (行数据[1][n] > 最大值) 最大值 = 行数据[1][n];
        if (行数据[2][n] > 最大值) 最大值 = 行数据[2][n];
        if (行数据[3][n] > 最大值) 最大值 = 行数据[3][n];
    }
    if (最大值 > 1048576) {
        ShowMessage("已超出表格限制", 48);
        return false;
    }

    var 总行数 = 行数据[2][列数 - 1];
    var 源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(总行数, 列数)).Value2;

    var 组合结果, 合并字符串;

    if (正向循环 && 横向输出) {
        组合结果 = [];
        for (var 列 = 0; 列 < 列数; 列++) {
            组合结果[列] = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 源行 = CycleIndex(CeilDivide(行 + 1, 行数据[1][列]), 行数据[0][列]);
                组合结果[列][行] = 源数据[源行 - 1][列];
            }
        }
        if (gConnector !== "") {
            合并字符串 = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 拼接 = "";
                for (var 列 = 0; 列 < 列数; 列++) {
                    拼接 += 组合结果[列][行] + gConnector;
                }
                合并字符串[行] = 拼接.substring(0, 拼接.length - gConnector.length);
            }
            ws.Range("F2").Resize(1, 总行数).Value2 = 合并字符串;
        } else {
            ws.Range("F2").Resize(列数, 总行数).Value2 = 组合结果;
        }
    } else if (正向循环 && !横向输出) {
        组合结果 = [];
        for (var 行 = 0; 行 < 总行数; 行++) {
            组合结果[行] = [];
        }
        for (var 列 = 0; 列 < 列数; 列++) {
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 源行 = CycleIndex(CeilDivide(行 + 1, 行数据[1][列]), 行数据[0][列]);
                组合结果[行][列] = 源数据[源行 - 1][列];
            }
        }
        if (gConnector !== "") {
            合并字符串 = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 拼接 = "";
                for (var 列 = 0; 列 < 列数; 列++) {
                    拼接 += 组合结果[行][列] + gConnector;
                }
                合并字符串[行] = [拼接.substring(0, 拼接.length - gConnector.length)];
            }
            ws.Range("F2").Resize(总行数, 1).Value2 = 合并字符串;
        } else {
            ws.Range("F2").Resize(总行数, 列数).Value2 = 组合结果;
        }
    } else if (!正向循环 && 横向输出) {
        组合结果 = [];
        for (var 列 = 0; 列 < 列数; 列++) {
            组合结果[列] = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 源行 = CycleIndex(CeilDivide(行 + 1, 行数据[3][列]), 行数据[0][列]);
                组合结果[列][行] = 源数据[源行 - 1][列];
            }
        }
        if (gConnector !== "") {
            合并字符串 = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 拼接 = "";
                for (var 列 = 0; 列 < 列数; 列++) {
                    拼接 += 组合结果[列][行] + gConnector;
                }
                合并字符串[行] = 拼接.substring(0, 拼接.length - gConnector.length);
            }
            ws.Range("F2").Resize(1, 总行数).Value2 = 合并字符串;
        } else {
            ws.Range("F2").Resize(列数, 总行数).Value2 = 组合结果;
        }
    } else if (!正向循环 && !横向输出) {
        组合结果 = [];
        for (var 行 = 0; 行 < 总行数; 行++) {
            组合结果[行] = [];
        }
        for (var 列 = 0; 列 < 列数; 列++) {
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 源行 = CycleIndex(CeilDivide(行 + 1, 行数据[3][列]), 行数据[0][列]);
                组合结果[行][列] = 源数据[源行 - 1][列];
            }
        }
        if (gConnector !== "") {
            合并字符串 = [];
            for (var 行 = 0; 行 < 总行数; 行++) {
                var 拼接 = "";
                for (var 列 = 0; 列 < 列数; 列++) {
                    拼接 += 组合结果[行][列] + gConnector;
                }
                合并字符串[行] = [拼接.substring(0, 拼接.length - gConnector.length)];
            }
            ws.Range("F2").Resize(总行数, 1).Value2 = 合并字符串;
        } else {
            ws.Range("F2").Resize(总行数, 列数).Value2 = 组合结果;
        }
    }
    return true;
}

function 双边循环组合(横向输出) {
    var ws = Application.ActiveSheet;
    var 总列数 = GetLastColumn(ws);

    if (总列数 <= 0) {
        ShowMessage("无有效数据列", 48);
        return false;
    }

    var 每列行数 = [];
    for (var i = 0; i < 总列数; i++) {
        每列行数[i] = GetLastRow(ws, i + 1);
    }

    var 总乘积 = 1;
    for (var i = 0; i < 每列行数.length; i++) {
        总乘积 *= 每列行数[i];
    }

    var 最小公倍数 = Application.WorksheetFunction.Lcm(每列行数);

    if (最小公倍数 > 1048576) {
        ShowMessage("已超出表格限制", 48);
        return false;
    }

    var 完整循环 = (总乘积 - 最小公倍数 === 0);
    var 源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(最小公倍数, 总列数)).Value2;
    var 新工作表 = Application.Worksheets.Add();

    if (完整循环) {
        新工作表.Name = "完整_" + 最小公倍数 + "sheet" + Application.Sheets.Count;
    } else {
        新工作表.Name = "残缺_" + 总乘积 + "|" + 最小公倍数 + "sheet" + Application.Sheets.Count;
    }

    var 合并结果 = [];

    if (横向输出) {
        var 竖向结果 = [];
        for (var i = 0; i < 最小公倍数; i++) {
            竖向结果[i] = [];
            var 拼接 = "";
            for (var j = 0; j < 总列数; j++) {
                竖向结果[i][j] = 源数据[CycleIndex(i + 1, 每列行数[j]) - 1][j];
                拼接 += 竖向结果[i][j] + gConnector;
            }
            合并结果[i] = 拼接.substring(0, 拼接.length - gConnector.length);
        }
        if (gConnector !== "") {
            var 转换结果 = [];
            for (var k = 0; k < 合并结果.length; k++) {
                转换结果[k] = [合并结果[k]];
            }
            新工作表.Range("A1").Resize(最小公倍数, 1).Value2 = 转换结果;
        } else {
            新工作表.Range("A1").Resize(最小公倍数, 总列数).Value2 = 竖向结果;
        }
    } else {
        var 横向结果 = [];
        for (var j = 0; j < 总列数; j++) {
            横向结果[j] = [];
        }
        for (var i = 0; i < 最小公倍数; i++) {
            var 拼接 = "";
            for (var j = 0; j < 总列数; j++) {
                横向结果[j][i] = 源数据[CycleIndex(i + 1, 每列行数[j]) - 1][j];
                拼接 += 横向结果[j][i] + gConnector;
            }
            合并结果[i] = 拼接.substring(0, 拼接.length - gConnector.length);
        }
        if (gConnector !== "") {
            新工作表.Range("A1").Resize(1, 最小公倍数).Value2 = 合并结果;
        } else {
            新工作表.Range("A1").Resize(总列数, 最小公倍数).Value2 = 横向结果;
        }
    }
    return true;
}

// ========== 业务函数 ==========

function 四方镜子_合并_竖() {
    var 连接符号 = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (连接符号 === null) return;
    gConnector = 连接符号 || "-";
    gMergeMode = true;
    四方循环组合(false, false);
}

function 四方镜子_合并_横() {
    var 连接符号 = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (连接符号 === null) return;
    gConnector = 连接符号 || "-";
    gMergeMode = true;
    四方循环组合(true, true);
}

function 四方镜子_分开_竖() {
    gConnector = "";
    gMergeMode = false;
    四方循环组合(false, false);
}

function 四方镜子_分开_横() {
    gConnector = "";
    gMergeMode = false;
    四方循环组合(true, true);
}

function 四方镜子_双边循环_合并_竖() {
    var 连接符号 = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (连接符号 === null) return;
    gConnector = 连接符号 || "-";
    gMergeMode = true;
    双边循环组合(true);
}

function 四方镜子_双边循环_合并_横() {
    var 连接符号 = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (连接符号 === null) return;
    gConnector = 连接符号 || "-";
    gMergeMode = true;
    双边循环组合(false);
}

function 四方镜子_双边循环_分_竖() {
    gConnector = "";
    gMergeMode = false;
    双边循环组合(true);
}

function 四方镜子_双边循环_分_横() {
    gConnector = "";
    gMergeMode = false;
    双边循环组合(false);
}

// ========== 主入口函数 ==========

function 四方镜子_主入口() {
    var choice = WPSInputBox(
        "请选择操作：\n" +
        "1: 四方循环_合并_竖\n" +
        "2: 四方循环_合并_横\n" +
        "3: 四方循环_分_竖\n" +
        "4: 四方循环_分_横\n" +
        "5: 双边循环_合并_竖\n" +
        "6: 双边循环_合并_横\n" +
        "7: 双边循环_分_竖\n" +
        "8: 双边循环_分_横",
        "四方镜子",
        "1",
        1
    );
    if (choice === false) return;
    choice = parseInt(choice);

    switch (choice) {
        case 1: 四方镜子_合并_竖(); break;
        case 2: 四方镜子_合并_横(); break;
        case 3: 四方镜子_分开_竖(); break;
        case 4: 四方镜子_分开_横(); break;
        case 5: 四方镜子_双边循环_合并_竖(); break;
        case 6: 四方镜子_双边循环_合并_横(); break;
        case 7: 四方镜子_双边循环_分_竖(); break;
        case 8: 四方镜子_双边循环_分_横(); break;
        default: ShowMessage("无效选择", 48);
    }
}