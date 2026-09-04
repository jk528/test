// PC_003_四方镜子_重构优化版.js
// 四方循环组合 - 重构优化实现
// 核心改进：消除重复代码、批量数据读写、统一算法架构、性能最大化

// ============================================================
//  第一部分：通用工具函数
// ============================================================

/**
 * 显示消息（兼容不同WPS版本）
 */
function Msg(msg, iconType) {
    try { Application.MsgBox(msg, iconType || 64, "四方镜子"); }
    catch (e) {
        try { Application.Alert(msg); }
        catch (e2) { console.log("【四方镜子】" + msg); }
    }
}

/**
 * 输入框封装
 */
function InputBox(prompt, title, defaultValue, type) {
    try {
        return Application.InputBox(prompt, title || "", defaultValue || "", 100, 100, "", 0, type || 8);
    } catch (e) {
        return null;
    }
}

/**
 * 1基循环索引： ys(n, Y) = ((n + Y - 1) mod Y) + 1
 * 例如：ys(1,3)=1, ys(3,3)=3, ys(4,3)=1
 */
function cycIdx(n, Y) {
    return ((n + Y - 1) % Y) + 1;
}

/**
 * 向上取整除法：ceil(c / d)
 */
function ceilDiv(c, d) {
    return Math.ceil(c / d);
}

/**
 * 获取最后一列（第1行有数据的最右列）
 */
function lastCol(ws) {
    try { return ws.Cells(1, ws.Columns.Count).End(-4159).Column; }
    catch (e) { return ws.UsedRange.Columns.Count; }
}

/**
 * 获取某列最后一行
 */
function lastRow(ws, col) {
    try { return ws.Cells(ws.Rows.Count, col).End(-4162).Row; }
    catch (e) { return ws.UsedRange.Rows.Count; }
}

/**
 * 批量读取区域值
 */
function readRange(ws, row1, col1, row2, col2) {
    return ws.Range(ws.Cells(row1, col1), ws.Cells(row2, col2)).Value2;
}

/**
 * 批量读取某列的数字格式
 */
function readNumberFormats(ws, col, rowCount) {
    return ws.Range(ws.Cells(1, col), ws.Cells(rowCount, col)).NumberFormat;
}

// ============================================================
//  第二部分：日期/数字格式化（批量预处理）
// ============================================================

/**
 * 判断格式字符串是否为日期格式
 */
function isDateFormat(fmt) {
    if (!fmt || fmt === 'General' || fmt === '@') return false;
    var lower = fmt.toLowerCase();
    var patterns = ['y', 'm', 'd', 'h', 's', '年', '月', '日', '时', '分', '秒', '上午', '下午'];
    for (var i = 0; i < patterns.length; i++) {
        if (lower.indexOf(patterns[i]) !== -1) return true;
    }
    return false;
}

/**
 * 将Excel日期序列号转为日期字符串
 * value: Excel 序列号（1=1900-01-01）
 */
function excelSerialToDate(value, fmt) {
    if (value === 0 || value === null || value === undefined) return "";

    var lowerFmt = fmt ? fmt.toLowerCase() : "";
    var isTimeOnly = lowerFmt.indexOf('h') !== -1
        && lowerFmt.indexOf('y') === -1
        && lowerFmt.indexOf('d') === -1
        && (lowerFmt.indexOf('m') === -1 || lowerFmt.indexOf('mm:') !== -1 || lowerFmt.indexOf(':mm') !== -1);

    // 纯时间格式（小于1的小数部分）
    if (isTimeOnly || value < 1) {
        var totalSec = Math.round(value * 24 * 60 * 60 * 1000) / 1000;
        var h = Math.floor(totalSec / 3600);
        var m = Math.floor((totalSec % 3600) / 60);
        var s = Math.floor(totalSec % 60);
        var ms = Math.round((totalSec - Math.floor(totalSec)) * 1000);
        var result = pad2(h) + ':' + pad2(m) + ':' + pad2(s);
        if (lowerFmt.indexOf('.0') !== -1 || lowerFmt.indexOf('.s') !== -1) {
            result += '.' + pad3(ms);
        }
        return result;
    }

    // 日期格式
    var date = new Date((value - 25569) * 86400000);
    var y = date.getFullYear();
    var mo = pad2(date.getMonth() + 1);
    var d = pad2(date.getDate());
    var result = y + '-' + mo + '-' + d;

    // 如果格式含时间部分
    if (lowerFmt.indexOf('h') !== -1 && lowerFmt.indexOf('y') === -1 ? false : lowerFmt.indexOf('h') !== -1) {
        // 检查是否同时有日期和时间
        if (lowerFmt.indexOf('y') !== -1 || lowerFmt.indexOf('d') !== -1 || lowerFmt.indexOf('m') !== -1) {
            var hh = pad2(date.getHours());
            var mm = pad2(date.getMinutes());
            var ss = pad2(date.getSeconds());
            result += ' ' + hh + ':' + mm + ':' + ss;
        }
    }

    return result;
}

function pad2(n) { return n < 10 ? '0' + n : String(n); }
function pad3(n) { return n < 10 ? '00' + n : n < 100 ? '0' + n : String(n); }

/**
 * 预处理源数据：将需要格式化的值转为字符串
 * 返回二维字符串数组
 */
function preformatSource(srcValues, srcFormats, rowCount, colCount) {
    var result = [];
    // 先判断每列是否需要日期格式化（整列格式相同则只需判断一次）
    var colIsDate = [];
    var colFmtStr = [];
    for (var c = 0; c < colCount; c++) {
        // 取第一行的格式作为列格式代表（通常整列格式一致）
        var fmt = srcFormats[0][c];
        colIsDate[c] = isDateFormat(fmt);
        colFmtStr[c] = fmt;
    }

    for (var r = 0; r < rowCount; r++) {
        result[r] = [];
        for (var c = 0; c < colCount; c++) {
            var val = srcValues[r][c];
            if (val === null || val === undefined || val === "") {
                result[r][c] = "";
            } else if (colIsDate[c] && typeof val === 'number') {
                result[r][c] = excelSerialToDate(val, colFmtStr[c]);
            } else {
                result[r][c] = String(val);
            }
        }
    }
    return result;
}

// ============================================================
//  第三部分：核心算法 - 四方循环组合（笛卡尔积）
// ============================================================

/**
 * 计算四方循环组合的循环步长数组
 * @param {Array} colCounts - 每列元素个数 [c1, c2, ..., cm]
 * @param {boolean} forward - true=正向(左慢右快), false=反向(左快右慢)
 * @returns {Array} 每列的循环步长
 *
 * 正向循环（VBA中的 L(2,n)）：
 *   step[0] = 1
 *   step[i] = step[i-1] * count[i-1]
 *   即第1列每 count[0]*count[1]*...*count[i-1] 行才变一次
 *
 * 反向循环（VBA中的 L(4,n)）：
 *   step[i] = total / (count[0] * ... * count[i])
 *   即第1列变化最快
 */
function calcCycleSteps(colCounts, forward) {
    var n = colCounts.length;
    var steps = [];
    if (forward) {
        steps[0] = 1;
        for (var i = 1; i < n; i++) {
            steps[i] = steps[i - 1] * colCounts[i - 1];
        }
    } else {
        var total = 1;
        for (var i = 0; i < n; i++) total *= colCounts[i];
        var cumProd = 1;
        for (var i = 0; i < n; i++) {
            cumProd *= colCounts[i];
            steps[i] = total / cumProd;
        }
    }
    return steps;
}

/**
 * 构建四方循环组合矩阵（列优先存储：result[col][row]）
 * @param {Array} source - 源数据二维数组 source[row][col]
 * @param {Array} colCounts - 每列元素个数
 * @param {Array} steps - 每列循环步长
 * @param {number} totalRows - 总行数（笛卡尔积）
 * @returns {Array} result[col][row] - 组合结果
 */
function buildCartesianMatrix(source, colCounts, steps, totalRows) {
    var colCount = colCounts.length;
    var result = [];
    for (var c = 0; c < colCount; c++) {
        result[c] = [];
        var count = colCounts[c];
        var step = steps[c];
        for (var r = 0; r < totalRows; r++) {
            var srcRow = cycIdx(ceilDiv(r + 1, step), count);
            result[c][r] = source[srcRow - 1][c];
        }
    }
    return result;
}

/**
 * 将列优先矩阵转置为行优先
 * input:  matrix[col][row]  (C列 × R行)
 * output: result[row][col]  (R行 × C列)
 */
function transpose(matrix, colCount, rowCount) {
    var result = [];
    for (var r = 0; r < rowCount; r++) {
        result[r] = [];
        for (var c = 0; c < colCount; c++) {
            result[r][c] = matrix[c][r];
        }
    }
    return result;
}

/**
 * 合并每行列的值为字符串，用 connector 连接
 * 支持列优先和行优先两种输入
 */
function mergeRowStrings(matrix, colCount, rowCount, isColumnMajor, connector) {
    var result = [];
    for (var r = 0; r < rowCount; r++) {
        var parts = [];
        for (var c = 0; c < colCount; c++) {
            parts.push(isColumnMajor ? matrix[c][r] : matrix[r][c]);
        }
        result[r] = parts.join(connector);
    }
    return result;
}

// ============================================================
//  第四部分：核心算法 - 双边循环组合（LCM独立循环）
// ============================================================

/**
 * 计算数组的最小公倍数（LCM）
 */
function lcmArray(arr) {
    return Application.WorksheetFunction.Lcm(arr);
}

/**
 * 计算数组元素的乘积
 */
function productArray(arr) {
    var p = 1;
    for (var i = 0; i < arr.length; i++) p *= arr[i];
    return p;
}

/**
 * 构建双边循环矩阵（列优先存储：result[col][row]）
 * 每列独立循环，总行数 = LCM(各列行数)
 */
function buildLcmMatrix(source, colCounts, totalRows) {
    var colCount = colCounts.length;
    var result = [];
    for (var c = 0; c < colCount; c++) {
        result[c] = [];
        var count = colCounts[c];
        for (var r = 0; r < totalRows; r++) {
            var srcRow = cycIdx(r + 1, count);
            result[c][r] = source[srcRow - 1][c];
        }
    }
    return result;
}

// ============================================================
//  第五部分：输出封装
// ============================================================

/**
 * 将结果写入工作表
 * @param {Worksheet} ws - 目标工作表
 * @param {string} startCell - 起始单元格（如 "F2"）
 * @param {Array} data - 数据数组
 * @param {number} outRows - 输出行数
 * @param {number} outCols - 输出列数
 * @param {boolean} merged - 是否合并模式（单列/单行字符串数组）
 */
function writeOutput(ws, startCell, data, outRows, outCols, merged) {
    if (merged) {
        if (outCols === 1) {
            // 竖排合并：一维数组 -> 二维单列
            var colData = [];
            for (var i = 0; i < data.length; i++) colData[i] = [data[i]];
            ws.Range(startCell).Resize(outRows, 1).Value2 = colData;
        } else {
            // 横排合并：一维数组直接写入一行
            ws.Range(startCell).Resize(1, outCols).Value2 = data;
        }
    } else {
        ws.Range(startCell).Resize(outRows, outCols).Value2 = data;
    }
}

// ============================================================
//  第六部分：业务主函数
// ============================================================

var g_connector = "";  // 连接符号，空字符串表示不合并

/**
 * 四方循环组合主函数
 * @param {boolean} forward - true=正向循环, false=反向循环
 * @param {boolean} horizontal - true=横向输出(列×行), false=竖向输出(行×列)
 */
function runCartesian(forward, horizontal) {
    // 关闭屏幕刷新和自动计算以提升性能
    var screenUpdating = true;
    var calcMode = -4105; // xlCalculationAutomatic
    try { screenUpdating = Application.ScreenUpdating; Application.ScreenUpdating = false; } catch (e) {}
    try { calcMode = Application.Calculation; Application.Calculation = -4135; } catch (e) {} // xlCalculationManual

    try {
        var ws = Application.ActiveSheet;
        var colCount = lastCol(ws);
        if (colCount <= 0) { Msg("无有效数据列", 48); return false; }

        // 1. 获取每列行数
        var colCounts = [];
        for (var i = 0; i < colCount; i++) {
            var rc = lastRow(ws, i + 1);
            colCounts[i] = rc < 1 ? 1 : rc;
        }

        // 2. 计算总行数（笛卡尔积）并检查限制
        var totalRows = productArray(colCounts);
        if (totalRows > 1048576) { Msg("已超出表格限制", 48); return false; }

        // 3. 批量读取源数据和格式
        var srcValues = readRange(ws, 1, 1, totalRows, colCount);
        var srcFormats = readNumberFormats(ws, 1, totalRows); // 只读取第一行格式作为列代表

        // 4. 预处理格式化（日期等）
        var source = preformatSource(srcValues, srcFormats, totalRows, colCount);

        // 5. 计算循环步长
        var steps = calcCycleSteps(colCounts, forward);

        // 6. 构建组合矩阵（列优先）
        var matrix = buildCartesianMatrix(source, colCounts, steps, totalRows);

        // 7. 根据输出方向和合并模式准备输出数据
        var outputData, outRows, outCols;
        var merged = g_connector !== "";

        if (horizontal) {
            // 横向输出：列×行
            if (merged) {
                outputData = mergeRowStrings(matrix, colCount, totalRows, true, g_connector);
                outRows = 1;
                outCols = totalRows;
            } else {
                outputData = matrix;   // 已经是 [col][row]
                outRows = colCount;
                outCols = totalRows;
            }
        } else {
            // 竖向输出：行×列
            if (merged) {
                outputData = mergeRowStrings(matrix, colCount, totalRows, true, g_connector);
                outRows = totalRows;
                outCols = 1;
            } else {
                outputData = transpose(matrix, colCount, totalRows);
                outRows = totalRows;
                outCols = colCount;
            }
        }

        // 8. 写入结果
        writeOutput(ws, "F2", outputData, outRows, outCols, merged);

        return true;
    } catch (e) {
        Msg("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        try { Application.Calculation = calcMode; } catch (e) {}
        try { Application.ScreenUpdating = screenUpdating; } catch (e) {}
    }
}

/**
 * 双边循环组合主函数
 * @param {boolean} vertical - true=竖排输出(行×列), false=横排输出(列×行)
 *   注意：VBA中参数 hs=True 表示竖向排列（结果按列存，输出竖向）
 *        这里参数名做了更清晰的命名
 */
function runLcmCycle(vertical) {
    var screenUpdating = true;
    var calcMode = -4105;
    try { screenUpdating = Application.ScreenUpdating; Application.ScreenUpdating = false; } catch (e) {}
    try { calcMode = Application.Calculation; Application.Calculation = -4135; } catch (e) {}

    try {
        var ws = Application.ActiveSheet;
        var colCount = lastCol(ws);
        if (colCount <= 0) { Msg("无有效数据列", 48); return false; }

        // 1. 获取每列行数
        var colCounts = [];
        for (var i = 0; i < colCount; i++) {
            var rc = lastRow(ws, i + 1);
            colCounts[i] = rc < 1 ? 1 : rc;
        }

        // 2. 计算LCM和乘积
        var product = productArray(colCounts);
        var lcm = lcmArray(colCounts);
        if (lcm > 1048576) { Msg("已超出表格限制", 48); return false; }

        var isComplete = (product === lcm);

        // 3. 批量读取源数据和格式
        var srcValues = readRange(ws, 1, 1, lcm, colCount);
        var srcFormats = readNumberFormats(ws, 1, lcm);

        // 4. 预处理格式化
        var source = preformatSource(srcValues, srcFormats, lcm, colCount);

        // 5. 构建LCM循环矩阵（列优先）
        var matrix = buildLcmMatrix(source, colCounts, lcm);

        // 6. 新建工作表
        var newWs = Application.Worksheets.Add();
        newWs.Name = isComplete
            ? "完整_" + lcm + "sheet" + Application.Sheets.Count
            : "残缺_" + product + "|" + lcm + "sheet" + Application.Sheets.Count;

        // 7. 准备输出数据
        var outputData, outRows, outCols;
        var merged = g_connector !== "";

        if (vertical) {
            // 竖向输出：行×列
            if (merged) {
                outputData = mergeRowStrings(matrix, colCount, lcm, true, g_connector);
                outRows = lcm;
                outCols = 1;
            } else {
                outputData = transpose(matrix, colCount, lcm);
                outRows = lcm;
                outCols = colCount;
            }
        } else {
            // 横向输出：列×行
            if (merged) {
                outputData = mergeRowStrings(matrix, colCount, lcm, true, g_connector);
                outRows = 1;
                outCols = lcm;
            } else {
                outputData = matrix;
                outRows = colCount;
                outCols = lcm;
            }
        }

        // 8. 写入结果
        writeOutput(newWs, "A1", outputData, outRows, outCols, merged);

        return true;
    } catch (e) {
        Msg("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        try { Application.Calculation = calcMode; } catch (e) {}
        try { Application.ScreenUpdating = screenUpdating; } catch (e) {}
    }
}

// ============================================================
//  第七部分：入口函数（8种操作模式）
// ============================================================

function 四方镜子_合并_竖() {
    var c = InputBox("请输入连接符号:", "连接符号", "-", 2);
    if (c === null) return;
    g_connector = c || "-";
    runCartesian(false, false);
}

function 四方镜子_合并_横() {
    var c = InputBox("请输入连接符号:", "连接符号", "-", 2);
    if (c === null) return;
    g_connector = c || "-";
    runCartesian(true, true);
}

function 四方镜子_分开_竖() {
    g_connector = "";
    runCartesian(false, false);
}

function 四方镜子_分开_横() {
    g_connector = "";
    runCartesian(true, true);
}

function 四方镜子_双边循环_合并_竖() {
    var c = InputBox("请输入连接符号:", "连接符号", "-", 2);
    if (c === null) return;
    g_connector = c || "-";
    runLcmCycle(true);
}

function 四方镜子_双边循环_合并_横() {
    var c = InputBox("请输入连接符号:", "连接符号", "-", 2);
    if (c === null) return;
    g_connector = c || "-";
    runLcmCycle(false);
}

function 四方镜子_双边循环_分_竖() {
    g_connector = "";
    runLcmCycle(true);
}

function 四方镜子_双边循环_分_横() {
    g_connector = "";
    runLcmCycle(false);
}

// ============================================================
//  第八部分：主入口
// ============================================================

function 四方镜子_主入口() {
    var choice = InputBox(
        "请选择操作：\n" +
        "1: 四方循环_合并_竖\n" +
        "2: 四方循环_合并_横\n" +
        "3: 四方循环_分_竖\n" +
        "4: 四方循环_分_横\n" +
        "5: 双边循环_合并_竖\n" +
        "6: 双边循环_合并_横\n" +
        "7: 双边循环_分_竖\n" +
        "8: 双边循环_分_横",
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
        default: Msg("无效选择", 48);
    }
}
