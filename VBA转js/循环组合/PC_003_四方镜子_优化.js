// PC_003_四方镜子.js - WPS JavaScript 宏代码
// VBA转JS: 四方镜子.TXT
// 四方循环组合核心算法实现 - 纯JS 0基数组

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

function GetColumnData(ws, colIndex) {
    var lastRow = GetLastRow(ws, colIndex);
    if (lastRow < 1) lastRow = 1;
    return ws.Range(ws.Cells(1, colIndex), ws.Cells(lastRow, colIndex)).Value2;
}

function GetAllData(ws, rowCount, colCount) {
    return ws.Range(ws.Cells(1, 1), ws.Cells(rowCount, colCount)).Value2;
}

function MergeStrings(arr, colCount, rowCount, isVertical) {
    if (gConnector === "") return null;
    var result = [];
    for (var i = 0; i < rowCount; i++) {
        var str = "";
        for (var j = 0; j < colCount; j++) {
            str += isVertical ? arr[j][i] : arr[i][j];
            str += gConnector;
        }
        result[i] = str.substring(0, str.length - gConnector.length);
    }
    return result;
}

function OutputResult(ws, data, startCell, rowCount, colCount, isVertical) {
    if (gConnector !== "" && colCount === 1) {
        var converted = [];
        for (var i = 0; i < data.length; i++) {
            converted[i] = [data[i]];
        }
        ws.Range(startCell).Resize(rowCount, 1).Value2 = converted;
    } else if (gConnector !== "" && rowCount === 1) {
        ws.Range(startCell).Resize(1, colCount).Value2 = data;
    } else {
        ws.Range(startCell).Resize(rowCount, colCount).Value2 = data;
    }
}

function BuildCycleMatrix(源数据, 行数据, colCount, rowCount, useFirstCycle) {
    var cycleArray = useFirstCycle ? 行数据[1] : 行数据[3];
    var result = [];
    for (var col = 0; col < colCount; col++) {
        result[col] = [];
        for (var row = 0; row < rowCount; row++) {
            var srcRow = CycleIndex(CeilDivide(row + 1, cycleArray[col]), 行数据[0][col]);
            result[col][row] = 源数据[srcRow - 1][col];
        }
    }
    return result;
}

function 四方循环组合(正向循环, 横向输出) {
    var ws = Application.ActiveSheet;
    var colCount = GetLastColumn(ws);

    if (colCount <= 0) {
        ShowMessage("无有效数据列", 48);
        return false;
    }

    var colDataCount = [];
    for (var i = 0; i < colCount; i++) {
        colDataCount[i] = GetLastRow(ws, i + 1);
    }

    var lcmProduct = 1;
    for (var i = 0; i < colCount; i++) {
        lcmProduct *= colDataCount[i];
    }

    if (lcmProduct > 1048576) {
        ShowMessage("已超出表格限制", 48);
        return false;
    }

    var cycleStep = [];
    cycleStep[0] = colDataCount[0];
    for (var i = 1; i < colCount; i++) {
        cycleStep[i] = cycleStep[i - 1] * colDataCount[i];
    }

    var totalRows = cycleStep[colCount - 1];
    var srcData = GetAllData(ws, totalRows, colCount);

    var cycleArray = [];
    cycleArray[0] = 1;
    for (var i = 1; i < colCount; i++) {
        cycleArray[i] = cycleArray[i - 1] * colDataCount[i - 1];
    }

    var reverseCycle = [];
    for (var i = 0; i < colCount; i++) {
        reverseCycle[i] = totalRows / cycleStep[i];
    }

    var useCycle = 正向循环 ? cycleArray : reverseCycle;
    var matrix = BuildCycleMatrix(srcData, { 0: colDataCount, 1: cycleArray, 3: reverseCycle }, colCount, totalRows, 正向循环);

    var result, outRowCount, outColCount;
    if (横向输出) {
        if (gConnector !== "") {
            result = MergeStrings(matrix, colCount, totalRows, true);
            outRowCount = 1;
            outColCount = totalRows;
        } else {
            result = matrix;
            outRowCount = colCount;
            outColCount = totalRows;
        }
    } else {
        var transposed = [];
        for (var row = 0; row < totalRows; row++) {
            transposed[row] = [];
            for (var col = 0; col < colCount; col++) {
                transposed[row][col] = matrix[col][row];
            }
        }
        if (gConnector !== "") {
            result = MergeStrings(transposed, colCount, totalRows, false);
            outRowCount = totalRows;
            outColCount = 1;
        } else {
            result = transposed;
            outRowCount = totalRows;
            outColCount = colCount;
        }
    }

    OutputResult(ws, result, "F2", outRowCount, outColCount, 横向输出);
    return true;
}

function 双边循环组合(横向输出) {
    var ws = Application.ActiveSheet;
    var totalCols = GetLastColumn(ws);

    if (totalCols <= 0) {
        ShowMessage("无有效数据列", 48);
        return false;
    }

    var colRows = [];
    for (var i = 0; i < totalCols; i++) {
        colRows[i] = GetLastRow(ws, i + 1);
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
    var srcData = GetAllData(ws, lcm, totalCols);
    var newWs = Application.Worksheets.Add();

    newWs.Name = isComplete ? "完整_" + lcm + "sheet" + Application.Sheets.Count : "残缺_" + product + "|" + lcm + "sheet" + Application.Sheets.Count;

    var mergedResult = [];
    var cycleMatrix = [];

    for (var j = 0; j < totalCols; j++) {
        cycleMatrix[j] = [];
    }

    for (var i = 0; i < lcm; i++) {
        var str = "";
        for (var j = 0; j < totalCols; j++) {
            cycleMatrix[j][i] = srcData[CycleIndex(i + 1, colRows[j]) - 1][j];
            str += cycleMatrix[j][i] + gConnector;
        }
        mergedResult[i] = str.substring(0, str.length - gConnector.length);
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