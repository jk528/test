// PC_002_排列组合_WPS.js - WPS JavaScript 宏代码
// VBA转JS: PC_002_排列组合.TXT
// 四类排列组合核心算法实现 - 纯JS 0基数组

function ShowMessage(message, type) {
    try {
        if (typeof Application.MsgBox === 'function') {
            Application.MsgBox(message, type || 64, "排列组合");
        } else if (typeof Application.Alert === 'function') {
            Application.Alert(message);
        } else {
            console.log("【消息】" + message);
        }
    } catch (e) {
        console.log("【消息】" + message);
    }
}

function WPSInputBox(prompt, title, type) {
    try {
        return Application.InputBox(prompt, title || "", "", 100, 100, "", 0, type || 8);
    } catch (e) {
        console.error("InputBox 调用失败: " + (e.message || String(e)));
        return null;
    }
}

function CombinationDD(n, R) {
    if (R < 0 || R > n) return 0;
    if (R === 0 || R === n) return 1;
    if (R > n - R) R = n - R;
    var res = 1;
    for (var i = 1; i <= R; i++) {
        res = res * (n - R + i) / i;
    }
    return res;
}

function PermCount(m, n) {
    if (n < 0 || n > m) return 0;
    var res = 1;
    for (var i = 0; i < n; i++) {
        res = res * (m - i);
    }
    return res;
}

function extractDataFromRange(range) {
    var data = [];
    try {
        var rangeValue = range.Value2;
        if (Array.isArray(rangeValue)) {
            for (var i = 0; i < rangeValue.length; i++) {
                var row = rangeValue[i];
                if (Array.isArray(row)) {
                    for (var j = 0; j < row.length; j++) {
                        var v = row[j];
                        if (v !== undefined && v !== null && v !== '') data.push(v);
                    }
                } else if (row !== undefined && row !== null && row !== '') {
                    data.push(row);
                }
            }
        } else if (rangeValue !== undefined && rangeValue !== null && rangeValue !== '') {
            data.push(rangeValue);
        }
    } catch (e) {
        try {
            var rows = range.Rows.Count;
            var cols = range.Columns.Count;
            for (var i = 1; i <= rows; i++) {
                for (var j = 1; j <= cols; j++) {
                    var v = range.Cells(i, j).Value2;
                    if (v !== undefined && v !== null && v !== '') data.push(v);
                }
            }
        } catch (e2) {}
    }
    return data;
}

function RangeTo1DArray(rng) {
    if (!rng) return null;
    var src = extractDataFromRange(rng);
    if (src.length === 0) return null;
    return src;
}

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

var MAX_ROWS = 1048576;

function GenComb_NoRepet(Arr, m, n, startIdx, depth, res, result) {
    if (result.length >= MAX_ROWS) return;
    if (depth > n) {
        result.push(res.slice());
        return;
    }
    for (var i = startIdx; i <= m - (n - depth); i++) {
        res[depth - 1] = Arr[i - 1];
        GenComb_NoRepet(Arr, m, n, i + 1, depth + 1, res, result);
    }
}

function combin_arr1(Arr, n) {
    if (!Array.isArray(Arr) || Arr.length === 0) return null;
    var m = Arr.length;
    if (n < 1 || n > m) return null;
    if (CombinationDD(m, n) > MAX_ROWS) return null;
    var result = [];
    GenComb_NoRepet(Arr, m, n, 1, 1, [], result);
    return result;
}

function combin_arr_repet(Arr, n) {
    if (!Array.isArray(Arr) || Arr.length === 0) return null;
    var m = Arr.length;
    if (n < 1 || m < 1) return null;
    if (CombinationDD(m + n - 1, n) > MAX_ROWS) return null;
    var result = [];
    var idx = new Array(n).fill(0);
    while (true) {
        result.push(idx.map(function(i) { return Arr[i]; }));
        var p = n - 1;
        while (p >= 0 && idx[p] >= m - 1) p--;
        if (p < 0) break;
        idx[p]++;
        for (var i = p + 1; i < n; i++) idx[i] = idx[p];
    }
    return result;
}

function SolverPermNoRepet(Arr, m, n, used, res, depth, result) {
    if (result.length >= MAX_ROWS) return;
    if (depth > n) {
        result.push(res.slice());
        return;
    }
    for (var i = 0; i < m; i++) {
        if (!used[i]) {
            used[i] = true;
            res[depth - 1] = Arr[i];
            SolverPermNoRepet(Arr, m, n, used, res, depth + 1, result);
            used[i] = false;
        }
    }
}

function permut_no_repet(Arr, n) {
    if (!Array.isArray(Arr) || Arr.length === 0) return null;
    var m = Arr.length;
    if (n < 1 || n > m) return null;
    if (PermCount(m, n) > MAX_ROWS) return null;
    var result = [];
    SolverPermNoRepet(Arr, m, n, new Array(m).fill(false), [], 1, result);
    return result;
}

function permut_repet(Arr, n) {
    if (!Array.isArray(Arr) || Arr.length === 0) return null;
    var m = Arr.length;
    if (n < 1 || m < 1) return null;
    if (Math.pow(m, n) > MAX_ROWS) return null;
    var result = [];
    var idx = new Array(n).fill(0);
    while (true) {
        result.push(idx.map(function(i) { return Arr[i]; }));
        var i = n - 1;
        while (i >= 0 && idx[i] >= m - 1) i--;
        if (i < 0) break;
        idx[i]++;
        for (var j = i + 1; j < n; j++) idx[j] = 0;
    }
    return result;
}

// 验证函数
function IsNestedArray(List) {
    return Array.isArray(List) && List.length > 0 && Array.isArray(List[0]);
}

function NestedListCount(List) {
    return Array.isArray(List) ? List.length : 0;
}

function NestedItemLength(List) {
    return IsNestedArray(List) ? List[0].length : 0;
}

function ExpectedCount(funcName, m, n) {
    var fn = funcName.toLowerCase();
    if (fn === "combin_arr1" && n >= 1 && n <= m) return CombinationDD(m, n);
    if (fn === "combin_arr_repet" && n >= 1 && m >= 1) return CombinationDD(m + n - 1, n);
    if (fn === "permut_no_repet" && n >= 1 && n <= m) return PermCount(m, n);
    if (fn === "permut_repet" && n >= 1 && m >= 1) return Math.pow(m, n);
    return 0;
}

function InvokeByName(funcName, Arr, n) {
    var fn = funcName.toLowerCase();
    if (fn === "combin_arr1") return combin_arr1(Arr, n);
    if (fn === "combin_arr_repet") return combin_arr_repet(Arr, n);
    if (fn === "permut_no_repet") return permut_no_repet(Arr, n);
    if (fn === "permut_repet") return permut_repet(Arr, n);
    return null;
}

function WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, actual, itemLen, passed, note) {
    ws.Cells(rowIdx, 1).Value2 = funcName;
    ws.Cells(rowIdx, 2).Value2 = m;
    ws.Cells(rowIdx, 3).Value2 = n;
    ws.Cells(rowIdx, 4).Value2 = expected;
    ws.Cells(rowIdx, 5).Value2 = actual;
    ws.Cells(rowIdx, 6).Value2 = itemLen;
    ws.Cells(rowIdx, 7).Value2 = passed ? "PASS" : "FAIL";
    ws.Cells(rowIdx, 8).Value2 = note || "";
}

function RunSingleTest(ws, rowIdx, funcName, Arr, n) {
    if (!Array.isArray(Arr)) Arr = [];
    var m = Arr.length;
    var expected = ExpectedCount(funcName, m, n);
    var result;
    try {
        result = InvokeByName(funcName, Arr, n);
    } catch (e) {
        WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, 0, 0, false, "运行异常: " + (e.message || String(e)));
        return rowIdx + 1;
    }
    if (expected === 0) {
        if (Array.isArray(result)) {
            var cnt = NestedListCount(result);
            WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, cnt, NestedItemLength(result), cnt === 0, "非法参数应无结果");
        } else {
            WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, 0, 0, true, "非法参数返回Empty");
        }
        return rowIdx + 1;
    }
    if (!Array.isArray(result)) {
        WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, 0, 0, false, "未返回数组");
    } else if (!IsNestedArray(result)) {
        WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, NestedListCount(result), NestedItemLength(result), false, "结构非嵌套数组");
    } else {
        var actual = NestedListCount(result);
        var itemLen = NestedItemLength(result);
        var passed = (actual === expected) && (itemLen === n);
        WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, actual, itemLen, passed, passed ? "" : "数量或项长度不匹配");
    }
    return rowIdx + 1;
}

function 自测_组合排列_自动验证() {
    try {
        var ws = GetOrInitWorksheet("组合排列_自测报告");
        ws.Cells.Clear();
        ws.Range("A1:H1").Value2 = ["函数", "m(元素数)", "n(长度)", "期望数量", "实际数量", "每项长度", "结果", "备注"];
        var rowIdx = 2;
        var funcs = ["combin_arr1", "combin_arr_repet", "permut_no_repet", "permut_repet"];
        var tests = [
            { arr: ["A", "B", "C"], n: 1 },
            { arr: ["A", "B", "C"], n: 2 },
            { arr: ["A", "B", "C"], n: 3 },
            { arr: ["A", "A", "B"], n: 1 },
            { arr: ["A", "A", "B"], n: 2 },
            { arr: ["A", "B", "C"], n: 0 },
            { arr: ["A", "B", "C"], n: 4 },
            { arr: ["A", "B", "C"], n: 5 },
            { arr: ["A", "A", "B"], n: 0 },
            { arr: [], n: 1 },
            { arr: [], n: 2 }
        ];
        for (var ti = 0; ti < tests.length; ti++) {
            for (var fi = 0; fi < funcs.length; fi++) {
                rowIdx = RunSingleTest(ws, rowIdx, funcs[fi], tests[ti].arr, tests[ti].n);
            }
        }
        ws.Columns.AutoFit();
        ShowMessage("自测完成，请查看工作表【组合排列_自测报告】。", 64);
    } catch (e) {
        ShowMessage("自测发生错误: " + (e.message || String(e)), 48);
    }
}

function ParseComboRange(s, n) {
    s = String(s).trim().toLowerCase().replace(/[，；]/g, "-").replace(/ /g, "");
    if (s === "all") {
        return { kStart: 1, kEnd: n };
    }
    if (s.indexOf("-") > 0) {
        var parts = s.split("-");
        if (parts.length !== 2 || isNaN(parts[0]) || isNaN(parts[1])) {
            return null;
        }
        var kStart = parseInt(parts[0], 10);
        var kEnd = parseInt(parts[1], 10);
        if (kStart < 1 || kEnd < 1 || kStart > kEnd || kEnd > n) {
            return null;
        }
        return { kStart: kStart, kEnd: kEnd };
    }
    if (isNaN(s)) {
        return null;
    }
    var k = parseInt(s, 10);
    if (k < 1 || k > n) {
        return null;
    }
    return { kStart: k, kEnd: k };
}

function 组合排列_范围选取_示例() {
    try {
        var selectedRange = WPSInputBox("请选择数据区域（支持多列）:", "组合排列输入", 8);
        if (!selectedRange) return;
        var Arr = RangeTo1DArray(selectedRange);
        if (!Array.isArray(Arr) || Arr.length === 0) {
            ShowMessage("选择区域无有效数据。", 48);
            return;
        }
        var OP = WPSInputBox(
            "请选择类型：\n1 = 组合不放回 C(m,k)\n2 = 组合放回 C(m+k-1,k)\n3 = 排列不放回 P(m,k)\n4 = 排列放回 m^k",
            "类型选择", 1
        );
        if (OP === null || OP === false) return;
        OP = parseInt(OP, 10);
        if (isNaN(OP) || OP < 1 || OP > 4) {
            ShowMessage("无效选择（请输入 1~4）。", 48);
            return;
        }
        var comboRangeInput = WPSInputBox("组合长度：输入 all（全部：1..n）或 单值k 或 区间 k1-k2", "组合长度", 2);
        if (!comboRangeInput) return;
        var rangeResult = ParseComboRange(String(comboRangeInput), Arr.length);
        if (!rangeResult) {
            ShowMessage("组合长度输入非法，请输入 all、单值k或区间k1-k2（范围：1..n）。", 48);
            return;
        }
        var funcNames = ["", "combin_arr1", "combin_arr_repet", "permut_no_repet", "permut_repet"];
        var wsNames = ["", "选区_组合不放回", "选区_组合放回", "选区_排列不放回", "选区_排列放回"];
        var funcMap = { 1: combin_arr1, 2: combin_arr_repet, 3: permut_no_repet, 4: permut_repet };
        var ws = GetOrInitWorksheet(wsNames[OP]);
        ws.Cells.Clear();
        ws.Range("A1:D1").Value2 = ["函数", "n", "项数", "每项长度"];
        var infoRow = 2, dataRow = 1;
        for (var k = rangeResult.kStart; k <= rangeResult.kEnd; k++) {
            var res = funcMap[OP](Arr, k);
            if (res === null) {
                ShowMessage("数据量超过Excel限制（" + MAX_ROWS + "行），请减少元素数量或组合长度。", 48);
                return;
            }
            if (Array.isArray(res) && res.length > 0) {
                ws.Cells(infoRow++, 1).Value2 = funcNames[OP];
                ws.Cells(infoRow - 1, 2).Value2 = k;
                ws.Cells(infoRow - 1, 3).Value2 = res.length;
                ws.Cells(infoRow - 1, 4).Value2 = res[0].length;
                ws.Range(ws.Cells(dataRow, 6), ws.Cells(dataRow + res.length - 1, 6 + res[0].length - 1)).Value2 = res;
                dataRow += res.length;
            } else {
                ws.Cells(infoRow, 1).Value2 = funcNames[OP];
                ws.Cells(infoRow, 2).Value2 = k;
                ws.Cells(infoRow++, 3).Value2 = 0;
            }
        }
        ws.Columns.AutoFit();
        ShowMessage("已生成结果到工作表【" + ws.Name + "】。", 64);
    } catch (e) {
        ShowMessage("错误: " + (e.message || String(e)), 48);
    }
}