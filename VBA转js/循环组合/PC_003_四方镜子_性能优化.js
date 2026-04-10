// PC_003_四方镜子.js - WPS JavaScript 宏代码（性能优化版）
// VBA转JS: 四方镜子.TXT
// 四方循环组合核心算法实现 - 纯JS 0基数组
// 支持各类数据格式（时间、日期、数字、文本）正确连接

var gConnector = "";
var gMergeMode = true;

function ShowMessage(message, type) {
    try {
        Application.MsgBox(message, type || 64, "四方镜子");
    } catch (e) {
        try {
            Application.Alert(message);
        } catch (e2) {
            console.log("【消息】" + message);
        }
    }
}

function WPSInputBox(prompt, title, defaultValue, type) {
    try {
        return Application.InputBox(prompt, title || "", defaultValue || "", 100, 100, "", 0, type || 8);
    } catch (e) {
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

function DisableScreenUpdating() {
    try {
        Application.ScreenUpdating = false;
    } catch (e) {}
}

function EnableScreenUpdating() {
    try {
        Application.ScreenUpdating = true;
    } catch (e) {}
}

function SetCalculation(mode) {
    try {
        Application.Calculation = mode;
    } catch (e) {}
}

function GetAllData(ws, rowCount, colCount) {
    return ws.Range(ws.Cells(1, 1), ws.Cells(rowCount, colCount)).Value2;
}

function GetCellText(ws, row, col) {
    try {
        var cell = ws.Cells(row, col);
        var value = cell.Value2;
        var numberFormat = cell.NumberFormat;

        if (value === null || value === undefined || value === "") {
            return "";
        }

        if (typeof value === 'number' && numberFormat !== 'General' && numberFormat !== '@') {
            if (IsDateFormat(numberFormat)) {
                return FormatDate(value, numberFormat, cell.NumberFormatLocal);
            }
        }

        return String(value);
    } catch (e) {
        var v = ws.Cells(row, col).Value2;
        return v !== null && v !== undefined ? String(v) : "";
    }
}

function IsDateFormat(format) {
    if (!format) return false;
    var datePatterns = [
        'y', 'm', 'd', 'h', 's',
        '年', '月', '日', '时', '分', '秒',
        '上午', '下午'
    ];
    var upperFormat = format.toLowerCase();
    for (var i = 0; i < datePatterns.length; i++) {
        if (upperFormat.indexOf(datePatterns[i]) !== -1) {
            return true;
        }
    }
    return false;
}

function FormatDate(value, numberFormat, localFormat) {
    try {
        if (value === 0) return "";

        var isTimeOnly = false;
        var isDateOnly = false;

        if (numberFormat && typeof numberFormat === 'string') {
            var fmt = numberFormat.toLowerCase();
            isTimeOnly = fmt.indexOf('h') !== -1 && fmt.indexOf('y') === -1 && fmt.indexOf('m') === -1 && fmt.indexOf('d') === -1;
            isDateOnly = fmt.indexOf('y') !== -1 || fmt.indexOf('m') !== -1 || fmt.indexOf('d') !== -1;
        }

        if (isTimeOnly) {
            var hours = Math.floor(value * 24);
            var minutes = Math.floor((value * 24 * 60) % 60);
            var seconds = Math.floor((value * 24 * 60 * 60) % 60);
            var result = String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
            if (numberFormat.indexOf('ss') !== -1 && numberFormat.indexOf('hh') !== -1) {
                var ms = Math.round((value * 24 * 60 * 60 * 1000) % 1000);
                result += '.' + String(ms).padStart(3, '0');
            }
            return result;
        }

        if (isDateOnly) {
            var date = new Date((value - 25569) * 86400000);
            var year = date.getFullYear();
            var month = String(date.getMonth() + 1).padStart(2, '0');
            var day = String(date.getDate()).padStart(2, '0');
            var result = year + '-' + month + '-' + day;

            if (numberFormat.indexOf('h') !== -1) {
                var hours = String(date.getHours()).padStart(2, '0');
                var minutes = String(date.getMinutes()).padStart(2, '0');
                var seconds = String(date.getSeconds()).padStart(2, '0');
                result += ' ' + hours + ':' + minutes + ':' + seconds;
            }
            return result;
        }

        return String(value);
    } catch (e) {
        return String(value);
    }
}

function ValueToString(value, numberFormat) {
    if (value === null || value === undefined || value === "") {
        return "";
    }
    if (typeof value === 'number' && numberFormat && numberFormat !== 'General' && numberFormat !== '@') {
        if (IsDateFormat(numberFormat)) {
            return FormatDate(value, numberFormat, null);
        }
    }
    return String(value);
}

function MergeStringsWithJoin(parts, connector) {
    if (parts.length === 0) return "";
    return parts.join(connector);
}

function GetFormattedRowData(ws, rowIndex, colCount, isSourceOneBased) {
    var parts = [];
    for (var col = 0; col < colCount; col++) {
        var cellRow = isSourceOneBased ? rowIndex + 1 : rowIndex;
        var cellCol = col + 1;
        parts.push(GetCellText(ws, cellRow, cellCol));
    }
    return parts;
}

function GetFormattedRowFromArray(srcData, rowIndex, colCount) {
    var parts = [];
    for (var col = 0; col < colCount; col++) {
        parts.push(ValueToString(srcData[rowIndex][col], null));
    }
    return parts;
}

function 四方循环组合_构建数据(ws, colCount, colDataCount, 正向循环, 横向输出) {
    var cycleStep0 = colDataCount[0];
    var cycleStep = [cycleStep0];
    for (var i = 1; i < colCount; i++) {
        cycleStep[i] = cycleStep[i - 1] * colDataCount[i];
    }

    var totalRows = cycleStep[colCount - 1];

    var cycleArray = [1];
    for (var i = 1; i < colCount; i++) {
        cycleArray[i] = cycleArray[i - 1] * colDataCount[i - 1];
    }

    var reverseCycle = [];
    for (var i = 0; i < colCount; i++) {
        reverseCycle[i] = totalRows / cycleStep[i];
    }

    var useCycle = 正向循环 ? cycleArray : reverseCycle;

    var result, outRowCount, outColCount;

    if (横向输出) {
        if (gConnector !== "") {
            var merged = [];
            for (var row = 0; row < totalRows; row++) {
                var parts = [];
                for (var col = 0; col < colCount; col++) {
                    var srcRow = CycleIndex(CeilDivide(row + 1, useCycle[col]), colDataCount[col]);
                    parts.push(GetCellText(ws, srcRow, col + 1));
                }
                merged[row] = MergeStringsWithJoin(parts, gConnector);
            }
            result = merged;
            outRowCount = 1;
            outColCount = totalRows;
        } else {
            var matrix = [];
            for (var col = 0; col < colCount; col++) {
                matrix[col] = [];
                for (var row = 0; row < totalRows; row++) {
                    var srcRow = CycleIndex(CeilDivide(row + 1, useCycle[col]), colDataCount[col]);
                    matrix[col][row] = GetCellText(ws, srcRow, col + 1);
                }
            }
            result = matrix;
            outRowCount = colCount;
            outColCount = totalRows;
        }
    } else {
        if (gConnector !== "") {
            var merged = [];
            for (var row = 0; row < totalRows; row++) {
                var parts = [];
                for (var col = 0; col < colCount; col++) {
                    var srcRow = CycleIndex(CeilDivide(row + 1, useCycle[col]), colDataCount[col]);
                    parts.push(GetCellText(ws, srcRow, col + 1));
                }
                merged[row] = MergeStringsWithJoin(parts, gConnector);
            }
            result = merged;
            outRowCount = totalRows;
            outColCount = 1;
        } else {
            var matrix = [];
            for (var row = 0; row < totalRows; row++) {
                matrix[row] = [];
                for (var col = 0; col < colCount; col++) {
                    var srcRow = CycleIndex(CeilDivide(row + 1, useCycle[col]), colDataCount[col]);
                    matrix[row][col] = GetCellText(ws, srcRow, col + 1);
                }
            }
            result = matrix;
            outRowCount = totalRows;
            outColCount = colCount;
        }
    }

    return { result: result, outRowCount: outRowCount, outColCount: outColCount };
}

function 四方循环组合(正向循环, 横向输出) {
    DisableScreenUpdating();
    SetCalculation(-4135);

    try {
        var ws = Application.ActiveSheet;
        var colCount = GetLastColumn(ws);

        if (colCount <= 0) {
            ShowMessage("无有效数据列", 48);
            return false;
        }

        var colDataCount = [];
        for (var i = 0; i < colCount; i++) {
            var rowCount = GetLastRow(ws, i + 1);
            if (rowCount < 1) rowCount = 1;
            colDataCount[i] = rowCount;
        }

        var lcmProduct = 1;
        for (var i = 0; i < colCount; i++) {
            lcmProduct *= colDataCount[i];
        }

        if (lcmProduct > 1048576) {
            ShowMessage("已超出表格限制", 48);
            return false;
        }

        var output = 四方循环组合_构建数据(ws, colCount, colDataCount, 正向循环, 横向输出);

        if (gConnector !== "" && output.outColCount === 1) {
            var formatted = [];
            for (var i = 0; i < output.result.length; i++) {
                formatted[i] = [output.result[i]];
            }
            ws.Range("F2").Resize(output.outRowCount, 1).Value2 = formatted;
        } else if (gConnector !== "" && output.outRowCount === 1) {
            ws.Range("F2").Resize(1, output.outColCount).Value2 = output.result;
        } else {
            ws.Range("F2").Resize(output.outRowCount, output.outColCount).Value2 = output.result;
        }

        return true;
    } catch (e) {
        ShowMessage("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        SetCalculation(-4105);
        EnableScreenUpdating();
    }
}

function 双边循环组合(横向输出) {
    DisableScreenUpdating();
    SetCalculation(-4135);

    try {
        var ws = Application.ActiveSheet;
        var totalCols = GetLastColumn(ws);

        if (totalCols <= 0) {
            ShowMessage("无有效数据列", 48);
            return false;
        }

        var colRows = [];
        for (var i = 0; i < totalCols; i++) {
            var rowCount = GetLastRow(ws, i + 1);
            if (rowCount < 1) rowCount = 1;
            colRows[i] = rowCount;
        }

        var product = 1;
        for (var i = 0; i < colRows.length; i++) {
            product *= colRows[i];
        }

        var lcm = Application.WorksheetFunction.Lcm(colRows);

        if (lcm > 1048576) {
            ShowMessage("已超出表格限制", 48);
            return false;
        }

        var isComplete = (product - lcm === 0);
        var newWs = Application.Worksheets.Add();

        newWs.Name = isComplete ? "完整_" + lcm + "sheet" + Application.Sheets.Count : "残缺_" + product + "|" + lcm + "sheet" + Application.Sheets.Count;

        var mergedResult = [];
        var cycleMatrix = [];

        for (var j = 0; j < totalCols; j++) {
            cycleMatrix[j] = [];
        }

        for (var i = 0; i < lcm; i++) {
            var parts = [];
            for (var j = 0; j < totalCols; j++) {
                cycleMatrix[j][i] = GetCellText(ws, CycleIndex(i + 1, colRows[j]), j + 1);
                parts.push(cycleMatrix[j][i]);
            }
            mergedResult[i] = MergeStringsWithJoin(parts, gConnector);
        }

        if (横向输出) {
            if (gConnector !== "") {
                var colFormat = [];
                for (var k = 0; k < mergedResult.length; k++) {
                    colFormat[k] = [mergedResult[k]];
                }
                newWs.Range("A1").Resize(lcm, 1).Value2 = colFormat;
            } else {
                newWs.Range("A1").Resize(lcm, totalCols).Value2 = cycleMatrix;
            }
        } else {
            if (gConnector !== "") {
                newWs.Range("A1").Resize(1, lcm).Value2 = mergedResult;
            } else {
                newWs.Range("A1").Resize(totalCols, lcm).Value2 = cycleMatrix;
            }
        }

        return true;
    } catch (e) {
        ShowMessage("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        SetCalculation(-4105);
        EnableScreenUpdating();
    }
}

function 四方镜子_合并_竖() {
    var connector = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (connector === null) return;
    gConnector = connector || "-";
    gMergeMode = true;
    四方循环组合(false, false);
}

function 四方镜子_合并_横() {
    var connector = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (connector === null) return;
    gConnector = connector || "-";
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
    var connector = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (connector === null) return;
    gConnector = connector || "-";
    gMergeMode = true;
    双边循环组合(true);
}

function 四方镜子_双边循环_合并_横() {
    var connector = WPSInputBox("请输入连接符号:", "连接符号", "-", 2);
    if (connector === null) return;
    gConnector = connector || "-";
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

function 四方镜子_主入口() {
    var choice = WPSInputBox(
        "请选择操作：\n1: 四方循环_合并_竖\n2: 四方循环_合并_横\n3: 四方循环_分_竖\n4: 四方循环_分_横\n5: 双边循环_合并_竖\n6: 双边循环_合并_横\n7: 双边循环_分_竖\n8: 双边循环_分_横",
        "四方镜子", "1", 1
    );
    if (choice === false || choice === null) return;
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