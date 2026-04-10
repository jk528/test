// PC_002_排列组合_WPS.js - WPS JavaScript 宏代码
// VBA转JS: PC_002_排列组合.TXT
// 四类排列组合核心算法实现

var k = 0;

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

function ToOneBased(Arr) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    if (Arr.length === 0) {
        return null;
    }
    if (Arr[0] !== undefined && Arr[0] !== null && Arr[0] !== '' && !isNaN(Arr[0]) && Arr[0] === 1) {
        return Arr;
    }
    var n = Arr.length;
    var result = [];
    result[0] = null;
    for (var i = 0; i < n; i++) {
        result[i + 1] = Arr[i];
    }
    return result;
}

function Clone1D(a) {
    if (!Array.isArray(a)) {
        return a;
    }
    var n = a.length - 1;
    if (n < 0) {
        return a;
    }
    var b = [];
    b[0] = null;
    for (var i = 1; i <= n; i++) {
        b[i] = a[i];
    }
    return b;
}

function CombinationDD(n, R) {
    if (R < 0 || R > n) {
        return 0;
    }
    if (R === 0 || R === n) {
        return 1;
    }
    if (R > n - R) {
        R = n - R;
    }
    var res = 1;
    for (var i = 1; i <= R; i++) {
        res = res * (n - R + i) / i;
    }
    return res;
}

function PermCount(m, n) {
    if (n < 0 || n > m) {
        return 0;
    }
    var res = 1;
    for (var i = 0; i < n; i++) {
        res = res * (m - i);
    }
    return res;
}

function TransposeNestedTo2D(List) {
    if (!Array.isArray(List)) {
        return List;
    }
    var rows = List.length;
    if (rows < 1) {
        return List;
    }
    var item = List[0];
    var cols;
    if (Array.isArray(item)) {
        cols = item.length - 1;
    } else {
        cols = 0;
    }
    var outArr = [];
    outArr[0] = null;
    for (var i = 0; i < rows; i++) {
        outArr[i + 1] = [];
        outArr[i + 1][0] = null;
        item = List[i];
        if (Array.isArray(item)) {
            for (var j = 1; j <= cols; j++) {
                outArr[i + 1][j] = item[j];
            }
        } else {
            outArr[i + 1][1] = item;
        }
    }
    return outArr;
}

function extractDataFromRange(range) {
    var data = [];
    try {
        var rows = range.Rows.Count;
        var cols = range.Columns.Count;
        for (var i = 1; i <= rows; i++) {
            for (var j = 1; j <= cols; j++) {
                try {
                    var cell = range.Cells(i, j);
                    var value = cell.Value;
                    if (value !== undefined && value !== null && value !== '') {
                        data.push(value);
                    }
                } catch (cellError) {
                }
            }
        }
    } catch (e) {
        try {
            var rangeValue = range.Value;
            if (rangeValue !== undefined && rangeValue !== null) {
                if (Array.isArray(rangeValue)) {
                    for (var i = 0; i < rangeValue.length; i++) {
                        if (Array.isArray(rangeValue[i])) {
                            for (var j = 0; j < rangeValue[i].length; j++) {
                                var value = rangeValue[i][j];
                                if (value !== undefined && value !== null && value !== '') {
                                    data.push(value);
                                }
                            }
                        } else {
                            var value = rangeValue[i];
                            if (value !== undefined && value !== null && value !== '') {
                                data.push(value);
                            }
                        }
                    }
                } else {
                    data.push(rangeValue);
                }
            }
        } catch (e2) {
        }
    }
    return data;
}

function RangeTo1DArray(rng) {
    if (!rng) {
        return null;
    }
    var src = extractDataFromRange(rng);
    if (src.length === 0) {
        return null;
    }
    var result = [];
    result[0] = null;
    for (var i = 0; i < src.length; i++) {
        result[i + 1] = src[i];
    }
    return result;
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

function GenComb_NoRepet(Arr, m, n, startIdx, depth, res, result, outIndex) {
    var maxI, i;
    if (depth > n) {
        outIndex[0] = outIndex[0] + 1;
        result[outIndex[0]] = Clone1D(res);
        return;
    }
    maxI = m - (n - depth);
    for (i = startIdx; i <= maxI; i++) {
        res[depth] = Arr[i];
        GenComb_NoRepet(Arr, m, n, i + 1, depth + 1, res, result, outIndex);
    }
}

function combin_arr1(Arr, n) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    var m = Arr.length - 1;
    if (n < 1 || n > m) {
        return null;
    }
    var count = CombinationDD(m, n);
    var result = [];
    result[0] = null;
    var res = [];
    res[0] = null;
    var outIndex = [0];
    GenComb_NoRepet(Arr, m, n, 1, 1, res, result, outIndex);
    return result;
}

function combin_arr_repet(Arr, n) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    var m = Arr.length - 1;
    if (n < 1 || m < 1) {
        return null;
    }
    var count = CombinationDD(m + n - 1, n);
    var brr = [];
    brr[0] = null;
    var idx = [];
    idx[0] = null;
    for (var i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    var outIndex = 0;
    var done = false;
    var p, i;
    while (!done) {
        var cur = [];
        cur[0] = null;
        for (i = 1; i <= n; i++) {
            cur[i] = Arr[idx[i]];
        }
        outIndex = outIndex + 1;
        brr[outIndex] = Clone1D(cur);
        p = n;
        while (p >= 1) {
            if (idx[p] < m) {
                idx[p] = idx[p] + 1;
                for (i = p + 1; i <= n; i++) {
                    idx[i] = idx[p];
                }
                break;
            } else {
                p = p - 1;
            }
        }
        if (p === 0) {
            done = true;
        }
    }
    return brr;
}

function SolverPermNoRepet(Arr, m, n, used, res, depth, result, R) {
    var i;
    if (depth > n) {
        R[0] = R[0] + 1;
        result[R[0]] = Clone1D(res);
        return;
    }
    for (i = 1; i <= m; i++) {
        if (!used[i]) {
            used[i] = true;
            res[depth] = Arr[i];
            SolverPermNoRepet(Arr, m, n, used, res, depth + 1, result, R);
            used[i] = false;
        }
    }
}

function permut_no_repet(Arr, n) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    var m = Arr.length - 1;
    if (n < 1 || n > m) {
        return null;
    }
    var kk = PermCount(m, n);
    var result = [];
    result[0] = null;
    var used = [];
    used[0] = null;
    var res = [];
    res[0] = null;
    var R = [0];
    SolverPermNoRepet(Arr, m, n, used, res, 1, result, R);
    return result;
}

function permut_repet(Arr, n) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    var m = Arr.length - 1;
    if (n < 1 || m < 1) {
        return null;
    }
    var kk = Math.pow(m, n);
    var result = [];
    result[0] = null;
    var idx = [];
    idx[0] = null;
    for (var i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    var R = 0;
    var done = false;
    var i;
    while (!done) {
        var res = [];
        res[0] = null;
        for (i = 1; i <= n; i++) {
            res[i] = Arr[idx[i]];
        }
        R = R + 1;
        result[R] = Clone1D(res);
        i = n;
        while (i >= 1) {
            if (idx[i] < m) {
                idx[i] = idx[i] + 1;
                break;
            } else {
                idx[i] = 1;
                i = i - 1;
            }
        }
        if (i === 0) {
            done = true;
        }
    }
    return result;
}

function IsNested1DList(List) {
    if (!Array.isArray(List)) {
        return false;
    }
    var rows = List.length;
    if (rows < 1) {
        return false;
    }
    var item = List[0];
    if (!Array.isArray(item)) {
        return false;
    }
    if (item[0] !== null) {
        return false;
    }
    return true;
}

function NestedListCount(List) {
    if (!Array.isArray(List)) {
        return 0;
    }
    return List.length;
}

function NestedItemLength(List) {
    if (!Array.isArray(List)) {
        return 0;
    }
    var item = List[0];
    if (!Array.isArray(item)) {
        return 0;
    }
    return item.length - 1;
}

function ExpectedCount(funcName, m, n) {
    switch (funcName.toLowerCase()) {
        case "combin_arr1":
            if (n < 1 || n > m) {
                return 0;
            }
            return CombinationDD(m, n);
        case "combin_arr_repet":
            if (n < 1 || m < 1) {
                return 0;
            }
            return CombinationDD(m + n - 1, n);
        case "permut_no_repet":
            if (n < 1 || n > m) {
                return 0;
            }
            return PermCount(m, n);
        case "permut_repet":
            if (n < 1 || m < 1) {
                return 0;
            }
            return Math.pow(m, n);
        default:
            return -1;
    }
}

function InvokeByName(funcName, Arr, n) {
    switch (funcName.toLowerCase()) {
        case "combin_arr1":
            return combin_arr1(Arr, n);
        case "combin_arr_repet":
            return combin_arr_repet(Arr, n);
        case "permut_no_repet":
            return permut_no_repet(Arr, n);
        case "permut_repet":
            return permut_repet(Arr, n);
        default:
            return null;
    }
}

function WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, actual, itemLen, passed, note) {
    ws.Cells(rowIdx, 1).Value = funcName;
    ws.Cells(rowIdx, 2).Value = m;
    ws.Cells(rowIdx, 3).Value = n;
    ws.Cells(rowIdx, 4).Value = expected;
    ws.Cells(rowIdx, 5).Value = actual;
    ws.Cells(rowIdx, 6).Value = itemLen;
    ws.Cells(rowIdx, 7).Value = passed ? "PASS" : "FAIL";
    ws.Cells(rowIdx, 8).Value = note || "";
}

function RunSingleTest(ws, rowIdx, funcName, baseArr, n) {
    try {
        var Arr = ToOneBased(baseArr);
        var m = 0;
        if (Array.isArray(Arr)) {
            m = Arr.length - 1;
        }
        var expected = ExpectedCount(funcName, m, n);
        var result = InvokeByName(funcName, Arr, n);
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
        } else if (!IsNested1DList(result)) {
            WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, NestedListCount(result), NestedItemLength(result), false, "结构非一维嵌套");
        } else {
            var actual = NestedListCount(result);
            var itemLen = NestedItemLength(result);
            var passed = (actual === expected) && (itemLen === n);
            WriteTestResultRow(ws, rowIdx, funcName, m, n, expected, actual, itemLen, passed, passed ? "" : "数量或项长度不匹配");
        }
        return rowIdx + 1;
    } catch (e) {
        WriteTestResultRow(ws, rowIdx, funcName, 0, n, 0, 0, 0, false, "运行异常: " + (e.message || String(e)));
        return rowIdx + 1;
    }
}

function 自测_组合排列_自动验证() {
    try {
        var ws = GetOrInitWorksheet("组合排列_自测报告");
        ws.Cells.Clear();
        ws.Range("A1:H1").Value = ["函数", "m(元素数)", "n(长度)", "期望数量", "实际数量", "每项长度", "结果", "备注"];
        var rowIdx = 2;
        var arr1 = ["A", "B", "C"];
        var arr2 = ["A", "A", "B"];
        var base1 = ToOneBased(arr1);
        var base2 = ToOneBased(arr2);
        var funcs = ["combin_arr1", "combin_arr_repet", "permut_no_repet", "permut_repet"];
        var ns1 = [1, 2, 3];
        var ns2 = [1, 2];
        var i, j;
        for (i = 0; i < funcs.length; i++) {
            for (j = 0; j < ns1.length; j++) {
                rowIdx = RunSingleTest(ws, rowIdx, funcs[i], base1, ns1[j]);
            }
        }
        for (i = 0; i < funcs.length; i++) {
            for (j = 0; j < ns2.length; j++) {
                rowIdx = RunSingleTest(ws, rowIdx, funcs[i], base2, ns2[j]);
            }
        }
        rowIdx = RunSingleTest(ws, rowIdx, "combin_arr1", base1, 0);
        rowIdx = RunSingleTest(ws, rowIdx, "combin_arr1", base1, 4);
        rowIdx = RunSingleTest(ws, rowIdx, "permut_no_repet", base1, 0);
        rowIdx = RunSingleTest(ws, rowIdx, "permut_no_repet", base1, 5);
        rowIdx = RunSingleTest(ws, rowIdx, "combin_arr_repet", base1, 0);
        rowIdx = RunSingleTest(ws, rowIdx, "permut_repet", base1, 0);
        rowIdx = RunSingleTest(ws, rowIdx, "combin_arr1", [], 1);
        rowIdx = RunSingleTest(ws, rowIdx, "permut_repet", [], 2);
        ws.Columns.AutoFit();
        ShowMessage("自测完成，请查看工作表【组合排列_自测报告】。", 64);
    } catch (e) {
        ShowMessage("自测发生错误: " + (e.message || String(e)), 48);
    }
}

function ParseComboRange(s, n) {
    s = s.toString().trim();
    if (s.length === 0) {
        return null;
    }
    s = s.toLowerCase().replace(/，/g, "-").replace(/；/g, "-").replace(/ /g, "");
    if (s === "all") {
        return { kStart: 1, kEnd: n };
    }
    var parts;
    if (s.indexOf("-") > 0) {
        parts = s.split("-");
        if (parts.length !== 2) {
            return null;
        }
        if (isNaN(parts[0]) || isNaN(parts[1])) {
            return null;
        }
        var kStart = parseInt(parts[0], 10);
        var kEnd = parseInt(parts[1], 10);
        if (kStart < 1 || kEnd < 1 || kStart > kEnd || kEnd > n) {
            return null;
        }
        return { kStart: kStart, kEnd: kEnd };
    } else {
        if (isNaN(s)) {
            return null;
        }
        var k = parseInt(s, 10);
        if (k < 1 || k > n) {
            return null;
        }
        return { kStart: k, kEnd: k };
    }
}

function 组合排列_范围选取_示例() {
    try {
        var selectedRange = WPSInputBox("请选择数据区域（支持多列）:", "组合排列输入", 8);
        if (!selectedRange) {
            return;
        }
        var Arr = RangeTo1DArray(selectedRange);
        if (!Array.isArray(Arr)) {
            ShowMessage("选择区域无有效数据。", 48);
            return;
        }
        var OP = WPSInputBox(
            "请选择类型：\n1 = 组合不放回 C(m,k)(杨辉三角)(元素不重复去镜像)\n2 = 组合放回 C(m+k-1,k)（元素重复去镜像）\n3 = 排列不放回 P(m,k)=m!/(m-k)!(元素不重复镜像)\n4 = 排列放回 m^k(元素重复镜像)",
            "类型选择",
            1
        );
        if (OP === null || OP === false) {
            return;
        }
        OP = parseInt(OP, 10);
        if (isNaN(OP) || OP < 1 || OP > 4) {
            ShowMessage("无效选择（请输入 1~4）。", 48);
            return;
        }
        var m = Arr.length - 1;
        var comboRangeInput = WPSInputBox("组合长度：输入 all（全部：1..n）或 单值k 或 区间 k1-k2", "组合长度", 2);
        if (!comboRangeInput) {
            return;
        }
        var rangeResult = ParseComboRange(comboRangeInput.toString(), m);
        if (!rangeResult) {
            ShowMessage("组合长度输入非法，请输入 all、单值k或区间k1-k2（范围：1..n）。", 48);
            return;
        }
        var kStart = rangeResult.kStart;
        var kEnd = rangeResult.kEnd;
        var funcName, ws;
        switch (OP) {
            case 1:
                funcName = "combin_arr1";
                ws = GetOrInitWorksheet("选区_组合不放回");
                break;
            case 2:
                funcName = "combin_arr_repet";
                ws = GetOrInitWorksheet("选区_组合放回");
                break;
            case 3:
                funcName = "permut_no_repet";
                ws = GetOrInitWorksheet("选区_排列不放回");
                break;
            case 4:
                funcName = "permut_repet";
                ws = GetOrInitWorksheet("选区_排列放回");
                break;
            default:
                ShowMessage("无效选择（请输入 1~4）。", 48);
                return;
        }
        ws.Cells.Clear();
        ws.Range("A1:D1").Value = ["函数", "n", "项数", "每项长度"];
        var infoRow = 2;
        var dataRow = 1;
        var k, res, out;
        for (k = kStart; k <= kEnd; k++) {
            switch (OP) {
                case 1:
                    res = combin_arr1(Arr, k);
                    break;
                case 2:
                    res = combin_arr_repet(Arr, k);
                    break;
                case 3:
                    res = permut_no_repet(Arr, k);
                    break;
                case 4:
                    res = permut_repet(Arr, k);
                    break;
            }
            if (!Array.isArray(res)) {
                ws.Cells(infoRow, 1).Value = funcName;
                ws.Cells(infoRow, 2).Value = k;
                ws.Cells(infoRow, 3).Value = 0;
                ws.Cells(infoRow, 4).Value = 0;
                infoRow = infoRow + 1;
            } else {
                ws.Cells(infoRow, 1).Value = funcName;
                ws.Cells(infoRow, 2).Value = k;
                ws.Cells(infoRow, 3).Value = NestedListCount(res);
                ws.Cells(infoRow, 4).Value = NestedItemLength(res);
                infoRow = infoRow + 1;
                out = TransposeNestedTo2D(res);
                if (Array.isArray(out)) {
                    var outRows = out.length - 1;
                    var outCols = out[1] ? out[1].length - 1 : 0;
                    ws.Range(ws.Cells(dataRow, 6), ws.Cells(dataRow + outRows - 1, 6 + outCols - 1)).Value = out;
                    dataRow = dataRow + outRows;
                }
            }
        }
        ws.Columns.AutoFit();
        ShowMessage("已生成结果到工作表【" + ws.Name + "】。\n范围：" + kStart + " - " + kEnd + "；类型：" + funcName, 64);
    } catch (e) {
        ShowMessage("错误: " + (e.message || String(e)), 48);
    }
}