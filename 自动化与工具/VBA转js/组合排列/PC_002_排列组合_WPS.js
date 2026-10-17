// PC_002_排列组合_WPS.js - 适配 WPS 环境的 JavaScript 代码
// 四类组合/排列函数：组合不放回、组合放回、排列不放回、排列放回

// 用于记录索引的全局变量
var k = 0;

// WPS 兼容的消息提示函数
function ShowMessage(message, type) {
    try {
        // type: 64=信息, 48=错误
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

// WPS 兼容的 InputBox 函数
function WPSInputBox(prompt, title, type) {
    try {
        // Application.InputBox(prompt, title, default, left, top, helpFile, helpContextID, type)
        // type: 1=数值, 2=字符串, 8=Range
        return Application.InputBox(prompt, title || "", "", 100, 100, "", 0, type || 8);
    } catch (e) {
        console.error("InputBox 调用失败: " + (e.message || String(e)));
        return null;
    }
}

// 从 WPS 范围对象中提取数据
function extractDataFromRange(range) {
    console.log("=== 开始 extractDataFromRange ===");
    console.log("range 参数类型: " + typeof range);
    console.log("range 是否有 Cells: " + (range && range.Cells ? "是" : "否"));
    console.log("range 是否有 Rows: " + (range && range.Rows ? "是" : "否"));
    console.log("range 是否有 Columns: " + (range && range.Columns ? "是" : "否"));
    console.log("range 是否有 Value: " + (range && range.Value ? "是" : "否"));

    var data = [];

    // 方法1：直接访问 Rows.Count 和 Columns.Count
    try {
        console.log("尝试方法1：直接访问 Rows.Count 和 Columns.Count");
        var rows = range.Rows.Count;
        var cols = range.Columns.Count;
        console.log("范围大小: " + rows + "行 × " + cols + "列");

        // 遍历所有单元格
        for (var i = 1; i <= rows; i++) {
            for (var j = 1; j <= cols; j++) {
                try {
                    var cell = range.Cells(i, j);
                    var value = cell.Value;
                    console.log("单元格 (" + i + "," + j + ") 值: " + value + ", 类型: " + typeof value);
                    if (value !== undefined && value !== null && value !== '') {
                        data.push(value);
                        console.log("已添加值: " + value);
                    }
                } catch (cellError) {
                    console.error("读取单元格 (" + i + "," + j + ") 失败: " + (cellError.message || String(cellError)));
                }
            }
        }
        console.log("方法1执行完成，当前数据: " + data.toString());
    } catch (e) {
        console.error("方法1失败: " + (e.message || String(e)));

        // 方法2：尝试直接获取 Value
        console.log("尝试方法2：直接获取 range.Value");
        try {
            var rangeValue = range.Value;
            console.log("range.Value 类型: " + typeof rangeValue);
            console.log("range.Value 是否为数组: " + (Array.isArray(rangeValue) ? "是" : "否"));

            if (rangeValue !== undefined && rangeValue !== null) {
                if (Array.isArray(rangeValue)) {
                    console.log("处理二维数组 Value");
                    for (var i = 0; i < rangeValue.length; i++) {
                        if (Array.isArray(rangeValue[i])) {
                            for (var j = 0; j < rangeValue[i].length; j++) {
                                var value = rangeValue[i][j];
                                // 只添加非空的有效值
                                if (value !== undefined && value !== null && value !== '' && String(value).trim() !== '') {
                                    data.push(value);
                                }
                            }
                        } else {
                            var value = rangeValue[i];
                            // 只添加非空的有效值
                            if (value !== undefined && value !== null && value !== '' && String(value).trim() !== '') {
                                data.push(value);
                            }
                        }
                    }
                } else {
                    // 单个值
                    var singleValue = rangeValue;
                    if (singleValue !== undefined && singleValue !== null && singleValue !== '' && String(singleValue).trim() !== '') {
                        data.push(singleValue);
                    }
                }
            }
            console.log("方法2执行完成，当前数据: " + data.toString());
        } catch (e2) {
            console.error("方法2也失败: " + (e2.message || String(e2)));
        }
    }

    console.log("=== extractDataFromRange 最终结果: " + data.toString() + " ===");
    return data;
}

// 处理 InputBox 返回的数组数据
function processInputArray(inputArray) {
    console.log("=== 开始处理 InputBox 返回数据 ===");
    console.log("inputArray 类型: " + typeof inputArray);
    console.log("inputArray 是否有 Cells: " + (inputArray && inputArray.Cells ? "是" : "否"));
    console.log("inputArray 是否有 Value: " + (inputArray && inputArray.Value ? "是" : "否"));
    console.log("inputArray 是否为函数: " + (typeof inputArray === 'function' ? "是" : "否"));
    console.log("inputArray 是否为数组: " + (Array.isArray(inputArray) ? "是" : "否"));

    var data = [];

    // 处理 WPS 范围对象
    if (inputArray && typeof inputArray === 'object' && inputArray.Cells) {
        console.log("检测到 WPS 范围对象，使用 extractDataFromRange");
        data = extractDataFromRange(inputArray);
    } else if (inputArray && typeof inputArray === 'function') {
        // WPS JavaScript 中 InputBox 返回的是函数代理，需要调用
        console.log("检测到 inputArray 是函数，尝试获取其返回值");
        try {
            var rangeObj = inputArray();
            console.log("函数调用返回类型: " + typeof rangeObj);
            console.log("返回对象: " + JSON.stringify(rangeObj));

            if (rangeObj && rangeObj.Cells) {
                console.log("调用 extractDataFromRange 处理返回对象");
                data = extractDataFromRange(rangeObj);
            } else if (Array.isArray(rangeObj)) {
                console.log("返回对象是数组，直接处理");
                console.log("数组内容: " + JSON.stringify(rangeObj));
                // 直接扁平化这个二维数组
                for (var i = 0; i < rangeObj.length; i++) {
                    if (Array.isArray(rangeObj[i])) {
                        for (var j = 0; j < rangeObj[i].length; j++) {
                            var value = rangeObj[i][j];
                            console.log("处理值 [" + i + "][" + j + "]: " + value);
                            // 只添加非空的有效值
                            if (value !== undefined && value !== null && value !== '' && String(value).trim() !== '') {
                                data.push(value);
                            }
                        }
                    } else {
                        var value = rangeObj[i];
                        console.log("处理值 [" + i + "]: " + value);
                        // 只添加非空的有效值
                        if (value !== undefined && value !== null && value !== '' && String(value).trim() !== '') {
                            data.push(value);
                        }
                    }
                }
            } else if (rangeObj && typeof rangeObj === 'object' && rangeObj.Value) {
                console.log("返回对象有 Value 属性");
                var val = rangeObj.Value;
                if (Array.isArray(val)) {
                    console.log("Value 是数组");
                    for (var i = 0; i < val.length; i++) {
                        if (Array.isArray(val[i])) {
                            for (var j = 0; j < val[i].length; j++) {
                                var value = val[i][j];
                                if (value !== undefined && value !== null && value !== '') {
                                    data.push(value);
                                }
                            }
                        } else {
                            var value = val[i];
                            if (value !== undefined && value !== null && value !== '') {
                                data.push(value);
                            }
                        }
                    }
                } else if (val && val.Cells) {
                    console.log("Value 是范围对象");
                    data = extractDataFromRange(val);
                } else {
                    console.log("Value 是单个值: " + val);
                    data = [val];
                }
            } else if (rangeObj && typeof rangeObj !== 'object') {
                console.log("返回对象是普通值: " + rangeObj);
                data = [rangeObj];
            }
        } catch (funcError) {
            console.error("函数调用失败: " + (funcError.message || String(funcError)));
            console.error("错误堆栈: " + (funcError.stack || "无"));
        }
    } else if (inputArray && typeof inputArray === 'object' && inputArray.Value) {
        console.log("检测到包含 Value 属性的对象");
        try {
            var valueData = inputArray.Value;
            if (Array.isArray(valueData)) {
                console.log("Value 是数组");
                for (var i = 0; i < valueData.length; i++) {
                    if (Array.isArray(valueData[i])) {
                        for (var j = 0; j < valueData[i].length; j++) {
                            var value = valueData[i][j];
                            if (value !== undefined && value !== null && value !== '') {
                                data.push(value);
                            }
                        }
                    } else {
                        var value = valueData[i];
                        if (value !== undefined && value !== null && value !== '') {
                            data.push(value);
                        }
                    }
                }
            } else if (valueData && valueData.Cells) {
                console.log("Value 是范围对象");
                data = extractDataFromRange(valueData);
            } else {
                console.log("Value 是单个值: " + valueData);
                data = [valueData];
            }
        } catch (e) {
            console.error("获取 Value 失败: " + (e.message || String(e)));
        }
    } else if (Array.isArray(inputArray)) {
        console.log("检测为普通 JavaScript 数组");
        data = inputArray.filter(function(item) {
            return item !== undefined && item !== null && item !== '';
        });
    }

    console.log("=== processInputArray 最终结果: " + data.toString() + " ===");
    return data;
}

function ToOneBased(Arr) {
    if (!Array.isArray(Arr)) {
        return null;
    }
    if (Arr.length === 0) {
        return null;
    }
    if (Arr[0] !== undefined && Arr[0] !== null && Arr[0] !== '') {
        var hasIndex0 = false;
        for (var i = 0; i < Arr.length; i++) {
            if (i in Arr && !Array.isArray(Arr[i])) {
                hasIndex0 = true;
                break;
            }
        }
        if (!hasIndex0) {
            return Arr;
        }
    }
    var n = Arr.length;
    var result = [];
    result[0] = '';
    for (var i = 0; i < n; i++) {
        result[i + 1] = Arr[i];
    }
    return result;
}

function Clone1D(a) {
    if (!Array.isArray(a)) {
        return a;
    }
    var n = a.length;
    var b = [];
    b[0] = '';
    for (var i = 1; i <= n; i++) {
        b[i] = a[i];
    }
    return b;
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

function TransposeNestedTo2D(List) {
    if (!Array.isArray(List)) {
        return List;
    }
    var rows = List.length;
    if (rows < 1) {
        return List;
    }
    var item = List[0];
    var cols = 1;
    if (Array.isArray(item)) {
        cols = item.length;
    }
    var outArr = [];
    for (var i = 0; i < rows; i++) {
        outArr[i] = [];
        item = List[i];
        if (Array.isArray(item)) {
            for (var j = 0; j < cols; j++) {
                outArr[i][j] = item[j];
            }
        } else {
            outArr[i][0] = item;
        }
    }
    return outArr;
}

function RangeTo1DArray(rng) {
    try {
        var src = rng.Value;
        var m, n, result, idx, i, j;
        if (!src) {
            result = [];
            result[0] = '';
            result[1] = rng.Value;
            return result;
        }
        if (!Array.isArray(src)) {
            result = [];
            result[0] = '';
            result[1] = src;
            return result;
        }
        m = src.length;
        n = src[0].length;
        result = [];
        result[0] = '';
        idx = 1;
        for (i = 0; i < m; i++) {
            for (j = 0; j < n; j++) {
                result[idx] = src[i][j];
                idx++;
            }
        }
        return result;
    } catch (e) {
        var singleResult = [];
        singleResult[0] = '';
        singleResult[1] = rng.Value;
        return singleResult;
    }
}

function GetOrInitWorksheet(name) {
    try {
        var ws = null;
        try {
            ws = Application.Worksheets(name);
        } catch (e) {
            ws = null;
        }
        if (ws === null || ws === undefined) {
            ws = Application.Worksheets.Add();
            try {
                ws.Name = name;
            } catch (e2) {
            }
        }
        return ws;
    } catch (e) {
        return Application.Worksheets.Add();
    }
}

function GenComb_NoRepet(Arr, m, n, startIdx, depth, res, result, outIndex) {
    var i, maxI;
    if (depth > n) {
        outIndex[0] = outIndex[0] + 1;
        result[outIndex[0]] = Clone1D(res);
        return outIndex[0];
    }
    maxI = m - (n - depth);
    for (i = startIdx; i <= maxI; i++) {
        res[depth] = Arr[i];
        outIndex[0] = GenComb_NoRepet(Arr, m, n, i + 1, depth + 1, res, result, outIndex);
    }
    return outIndex[0];
}

function combin_arr1(Arr, n) {
    var m, count, result, res, outIndex;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (Arr[0] === '' || Arr[0] === undefined || Arr[0] === null) {
        m = 0;
        for (var i = 1; i < Arr.length; i++) {
            if (Arr[i] !== undefined && Arr[i] !== null && Arr[i] !== '') {
                m = Arr.length - 1;
                break;
            }
        }
        if (m === 0) {
            var emptyArr = [];
            emptyArr[0] = '';
            for (var i = 1; i < Arr.length; i++) {
                if (Arr[i] !== undefined && Arr[i] !== null && Arr[i] !== '') {
                    m = i;
                    break;
                }
            }
        }
    } else {
        m = Arr.length - 1;
    }
    if (n < 1 || n > m) {
        return null;
    }
    count = CombinationDD(m, n);
    result = [];
    result[0] = '';
    res = [];
    res[0] = '';
    outIndex = [0];
    GenComb_NoRepet(Arr, m, n, 1, 1, res, result, outIndex);
    return result;
}

function combin_arr_repet(Arr, n) {
    var m, i, count, idx, brr, cur, done, p, outIndex;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (Arr[0] === '' || Arr[0] === undefined) {
        m = 0;
        for (var ti = 1; ti < Arr.length; ti++) {
            if (Arr[ti] !== undefined && Arr[ti] !== null && Arr[ti] !== '') {
                m = Arr.length - 1;
                break;
            }
        }
    }
    if (n < 1 || m < 1) {
        return null;
    }
    count = CombinationDD(m + n - 1, n);
    brr = [];
    brr[0] = '';
    idx = [];
    idx[0] = '';
    for (i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    outIndex = 0;
    done = false;
    while (!done) {
        cur = [];
        cur[0] = '';
        for (i = 1; i <= n; i++) {
            cur[i] = Arr[idx[i]];
        }
        outIndex++;
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
        if (p === 0) done = true;
    }
    return brr;
}

function SolverPermNoRepet(Arr, m, n, used, res, depth, result, R) {
    var i;
    if (depth > n) {
        R[0] = R[0] + 1;
        result[R[0]] = Clone1D(res);
        return R[0];
    }
    for (i = 1; i <= m; i++) {
        if (!used[i]) {
            used[i] = true;
            res[depth] = Arr[i];
            R[0] = SolverPermNoRepet(Arr, m, n, used, res, depth + 1, result, R);
            used[i] = false;
        }
    }
    return R[0];
}

function permut_no_repet(Arr, n) {
    var m, kk, used, res, result, R;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (Arr[0] === '' || Arr[0] === undefined) {
        m = 0;
        for (var ti = 1; ti < Arr.length; ti++) {
            if (Arr[ti] !== undefined && Arr[ti] !== null && Arr[ti] !== '') {
                m = Arr.length - 1;
                break;
            }
        }
    }
    if (n < 1 || n > m) {
        return null;
    }
    kk = PermCount(m, n);
    result = [];
    result[0] = '';
    used = [];
    used[0] = '';
    res = [];
    res[0] = '';
    R = [0];
    SolverPermNoRepet(Arr, m, n, used, res, 1, result, R);
    return result;
}

function permut_repet(Arr, n) {
    var m, i, kk, idx, res, result, done, R;
    if (!Array.isArray(Arr)) {
        return null;
    }
    Arr = ToOneBased(Arr);
    if (Arr === null) return null;
    m = Arr.length - 1;
    if (Arr[0] === '' || Arr[0] === undefined) {
        m = 0;
        for (var ti = 1; ti < Arr.length; ti++) {
            if (Arr[ti] !== undefined && Arr[ti] !== null && Arr[ti] !== '') {
                m = Arr.length - 1;
                break;
            }
        }
    }
    if (n < 1 || m < 1) {
        return null;
    }
    kk = Math.pow(m, n);
    result = [];
    result[0] = '';
    idx = [];
    idx[0] = '';
    for (i = 1; i <= n; i++) {
        idx[i] = 1;
    }
    R = 0;
    done = false;
    while (!done) {
        res = [];
        res[0] = '';
        for (i = 1; i <= n; i++) {
            res[i] = Arr[idx[i]];
        }
        R++;
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
        if (i === 0) done = true;
    }
    return result;
}

function IsNested1DList(List) {
    var rows, item;
    if (!Array.isArray(List)) return false;
    rows = List.length;
    if (List[0] === '' || List[0] === undefined) {
        rows = 0;
        for (var i = 1; i < List.length; i++) {
            if (List[i] !== undefined && List[i] !== null && List[i] !== '') {
                rows++;
            }
        }
    }
    if (rows < 1) return false;
    var firstIndex = List[0] === '' ? 1 : 0;
    item = List[firstIndex];
    if (!Array.isArray(item)) return false;
    if (item[0] !== '' && item[0] !== undefined) return false;
    return true;
}

function NestedListCount(List) {
    if (!Array.isArray(List)) return 0;
    if (List[0] === '' || List[0] === undefined) {
        var cnt = 0;
        for (var i = 1; i < List.length; i++) {
            if (List[i] !== undefined && List[i] !== null && List[i] !== '') {
                cnt++;
            }
        }
        return cnt;
    }
    return List.length;
}

function NestedItemLength(List) {
    var item;
    if (!Array.isArray(List)) return 0;
    var firstIndex = List[0] === '' ? 1 : 0;
    item = List[firstIndex];
    if (!Array.isArray(item)) return 0;
    if (item[0] === '' || item[0] === undefined) {
        var len = 0;
        for (var i = 1; i < item.length; i++) {
            if (item[i] !== undefined && item[i] !== null && item[i] !== '') {
                len++;
            }
        }
        return len;
    }
    return item.length;
}

function ExpectedCount(funcName, m, n) {
    switch (funcName.toLowerCase()) {
        case "combin_arr1":
            if (n < 1 || n > m) return 0;
            return CombinationDD(m, n);
        case "combin_arr_repet":
            if (n < 1 || m < 1) return 0;
            return CombinationDD(m + n - 1, n);
        case "permut_no_repet":
            if (n < 1 || n > m) return 0;
            return PermCount(m, n);
        case "permut_repet":
            if (n < 1 || m < 1) return 0;
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
    if (note === undefined) note = "";
    try {
        ws.Cells(rowIdx, 1).Value2 = funcName;
        ws.Cells(rowIdx, 2).Value2 = m;
        ws.Cells(rowIdx, 3).Value2 = n;
        ws.Cells(rowIdx, 4).Value2 = expected;
        ws.Cells(rowIdx, 5).Value2 = actual;
        ws.Cells(rowIdx, 6).Value2 = itemLen;
        ws.Cells(rowIdx, 7).Value2 = passed ? "PASS" : "FAIL";
        ws.Cells(rowIdx, 8).Value2 = note;
    } catch (e) {
        try {
            ws.Cells(rowIdx, 1).Value = funcName;
            ws.Cells(rowIdx, 2).Value = m;
            ws.Cells(rowIdx, 3).Value = n;
            ws.Cells(rowIdx, 4).Value = expected;
            ws.Cells(rowIdx, 5).Value = actual;
            ws.Cells(rowIdx, 6).Value = itemLen;
            ws.Cells(rowIdx, 7).Value = passed ? "PASS" : "FAIL";
            ws.Cells(rowIdx, 8).Value = note;
        } catch (e2) {
            console.error("WriteTestResultRow 写入失败: " + (e2.message || String(e2)));
        }
    }
}

function RunSingleTest(ws, rowIdx, funcName, baseArr, n) {
    try {
        var Arr = ToOneBased(baseArr);
        var m = 0;
        if (Array.isArray(Arr)) {
            if (Arr[0] === '' || Arr[0] === undefined) {
                for (var ti = 1; ti < Arr.length; ti++) {
                    if (Arr[ti] !== undefined && Arr[ti] !== null && Arr[ti] !== '') {
                        m = Arr.length - 1;
                        break;
                    }
                }
            } else {
                m = Arr.length;
            }
        }
        var expected = ExpectedCount(funcName, m, n);
        var result = InvokeByName(funcName, Arr, n);

        console.log("RunSingleTest 调试: funcName=" + funcName + ", m=" + m + ", n=" + n);
        console.log("  Arr=" + JSON.stringify(Arr));
        console.log("  expected=" + expected);
        console.log("  result=" + (Array.isArray(result) ? "数组(length=" + result.length + ")" : "非数组"));
        if (Array.isArray(result)) {
            console.log("  result[0]=" + result[0]);
            console.log("  result[1]=" + JSON.stringify(result[1]));
            console.log("  NestedListCount=" + NestedListCount(result));
            console.log("  NestedItemLength=" + NestedItemLength(result));
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
    console.log("开始执行 自测_组合排列_自动验证");
    try {
        var ws = GetOrInitWorksheet("组合排列_自测报告");
        ws.Cells.Clear();

        // 设置标题行
        var headerArray = [["函数", "m(元素数)", "n(长度)", "期望数量", "实际数量", "每项长度", "结果", "备注"]];
        try {
            ws.Range(ws.Cells(1, 1), ws.Cells(1, 8)).Value2 = headerArray;
        } catch (e) {
            try {
                ws.Range("A1:H1").Value = headerArray[0];
            } catch (e2) {
                console.error("标题行写入失败: " + (e2.message || String(e2)));
                for (var h = 0; h < 8; h++) {
                    try {
                        ws.Cells(1, h + 1).Value2 = headerArray[0][h];
                    } catch (e3) {
                        try {
                            ws.Cells(1, h + 1).Value = headerArray[0][h];
                        } catch (e4) {}
                    }
                }
            }
        }

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
        var emptyArr = [];
        emptyArr[0] = '';
        rowIdx = RunSingleTest(ws, rowIdx, "combin_arr1", emptyArr, 1);
        rowIdx = RunSingleTest(ws, rowIdx, "permut_repet", emptyArr, 2);

        ws.Columns.AutoFit();
        ShowMessage("自测完成，请查看工作表【组合排列_自测报告】。", 64);
    } catch (e) {
        ShowMessage("自测发生错误: " + (e.message || String(e)), 48);
    }
}

function ParseComboRange(s, n) {
    s = s.toString().trim();
    if (s.length === 0) return null;
    var t = s.toString().toLowerCase();
    t = t.replace(/，/g, "-");
    t = t.replace(/；/g, "-");
    t = t.replace(/ /g, "");
    if (t === "all") {
        return { kStart: 1, kEnd: n };
    }
    if (t.indexOf("-") > 0) {
        var p = t.split("-");
        if (p.length !== 2) return null;
        if (isNaN(p[0]) || isNaN(p[1])) return null;
        var kStart = parseInt(p[0], 10);
        var kEnd = parseInt(p[1], 10);
        if (kStart < 1 || kEnd < 1 || kStart > kEnd || kEnd > n) {
            return null;
        }
        return { kStart: kStart, kEnd: kEnd };
    } else {
        if (isNaN(t)) return null;
        var k = parseInt(t, 10);
        if (k < 1 || k > n) return null;
        return { kStart: k, kEnd: k };
    }
}

function 组合排列_范围选取_示例() {
    console.log("开始执行 组合排列_范围选取_示例");
    try {
        console.log("步骤1: 获取用户选择的单元格区域");
        var selectedRange = WPSInputBox(
            "请选择数据区域（支持多列）",
            "组合排列输入",
            8
        );
        if (selectedRange === false || selectedRange === null) {
            console.log("用户取消选择");
            return;
        }

        console.log("步骤2: 处理选择的范围数据");
        var Arr = processInputArray(selectedRange);
        console.log("处理后的数组: " + Arr.toString());

        if (!Array.isArray(Arr) || Arr.length === 0) {
            ShowMessage("选择区域无有效数据。", 48);
            return;
        }

        console.log("步骤3: 获取排列组合类型");
        var opInput = WPSInputBox(
            "请选择类型：\n" +
            "1 = 组合不放回 C(m,k)(杨辉三角)(元素不重复去镜像)\n" +
            "2 = 组合放回 C(m+k-1,k)（元素重复去镜像）\n" +
            "3 = 排列不放回 P(m,k)=m!/(m-k)!(元素不重复镜像)\n" +
            "4 = 排列放回 m^k(元素重复镜像)",
            "类型选择",
            1
        );

        if (opInput === false || opInput === null) {
            console.log("用户取消选择");
            return;
        }

        var OP = parseInt(opInput);
        if (isNaN(OP) || OP < 1 || OP > 4) {
            ShowMessage("无效选择（请输入 1~4）。", 48);
            return;
        }

        var m = Arr.length;
        console.log("元素数量 m: " + m);

        console.log("步骤4: 获取组合长度范围");
        var comboRangeInput = WPSInputBox(
            "组合长度：输入 all（全部：1..n）或 单值k 或 区间 k1-k2\n" +
            "当前 m = " + m + "，有效范围：1.." + m,
            "组合长度",
            2
        );

        if (comboRangeInput === false || comboRangeInput === null || comboRangeInput === "") {
            console.log("用户取消选择");
            return;
        }

        var rangeResult = ParseComboRange(comboRangeInput, m);
        if (!rangeResult) {
            ShowMessage("组合长度输入非法，请输入 all、单值k或区间k1-k2（范围：1.." + m + "）。", 48);
            return;
        }

        var kStart = rangeResult.kStart;
        var kEnd = rangeResult.kEnd;
        console.log("选择的 k 范围: " + kStart + " - " + kEnd);

        var ws, funcName;
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
        }

        console.log("选择的函数: " + funcName);
        ws.Cells.Clear();

        // 设置标题行
        var headerArray = [["函数", "n", "项数", "每项长度"]];
        try {
            ws.Range(ws.Cells(1, 1), ws.Cells(1, 4)).Value2 = headerArray;
        } catch (e) {
            try {
                ws.Range("A1:D1").Value = headerArray[0];
            } catch (e2) {
                console.error("标题行写入失败: " + (e2.message || String(e2)));
                for (var h = 0; h < 4; h++) {
                    try {
                        ws.Cells(1, h + 1).Value2 = headerArray[0][h];
                    } catch (e3) {
                        try {
                            ws.Cells(1, h + 1).Value = headerArray[0][h];
                        } catch (e4) {}
                    }
                }
            }
        }

        console.log("步骤5: 开始计算组合排列");
        var infoRow = 2;
        var dataRow = 1;
        var k, res, out;

        for (k = kStart; k <= kEnd; k++) {
            console.log("计算 k = " + k);
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

            console.log("计算完成，result 类型: " + (Array.isArray(res) ? "数组" : "非数组"));

            if (!Array.isArray(res)) {
                try {
                    ws.Cells(infoRow, 1).Value2 = funcName;
                    ws.Cells(infoRow, 2).Value2 = k;
                    ws.Cells(infoRow, 3).Value2 = 0;
                    ws.Cells(infoRow, 4).Value2 = 0;
                } catch (e) {
                    try {
                        ws.Cells(infoRow, 1).Value = funcName;
                        ws.Cells(infoRow, 2).Value = k;
                        ws.Cells(infoRow, 3).Value = 0;
                        ws.Cells(infoRow, 4).Value = 0;
                    } catch (e2) {}
                }
                infoRow++;
            } else {
                try {
                    ws.Cells(infoRow, 1).Value2 = funcName;
                    ws.Cells(infoRow, 2).Value2 = k;
                    ws.Cells(infoRow, 3).Value2 = NestedListCount(res);
                    ws.Cells(infoRow, 4).Value2 = NestedItemLength(res);
                } catch (e) {
                    try {
                        ws.Cells(infoRow, 1).Value = funcName;
                        ws.Cells(infoRow, 2).Value = k;
                        ws.Cells(infoRow, 3).Value = NestedListCount(res);
                        ws.Cells(infoRow, 4).Value = NestedItemLength(res);
                    } catch (e2) {}
                }
                infoRow++;

                out = TransposeNestedTo2D(res);
                if (Array.isArray(out)) {
                    var outRows = out.length;
                    var outCols = out[0].length;
                    console.log("写入数据: " + outRows + "行 × " + outCols + "列");

                    try {
                        for (var ri = 0; ri < outRows; ri++) {
                            for (var ci = 0; ci < outCols; ci++) {
                                try {
                                    ws.Cells(dataRow + ri, 6 + ci).Value2 = out[ri][ci];
                                } catch (innerError) {
                                    try {
                                        ws.Cells(dataRow + ri, 6 + ci).Value = out[ri][ci];
                                    } catch (innerError2) {}
                                }
                            }
                        }
                        console.log("逐单元格写入完成");
                    } catch (writeError) {
                        console.error("写入失败: " + (writeError.message || String(writeError)));
                    }
                    dataRow = dataRow + outRows;
                }
            }
        }

        ws.Columns.AutoFit();
        ShowMessage("已生成结果到工作表【" + ws.Name + "】。\n范围：" + kStart + " - " + kEnd + "；类型：" + funcName, 64);
        console.log("组合排列计算完成");
    } catch (e) {
        console.error("发生错误: " + (e.message || String(e)));
        console.error("错误堆栈: " + (e.stack || "无"));
        ShowMessage("发生错误: " + (e.message || String(e)), 48);
    }
}

function Initialize() {
    console.log("PC_002_排列组合_WPS 代码初始化完成");
    console.log("可用函数:");
    console.log("1. 自测_组合排列_自动验证() - 自动测试四类组合排列函数");
    console.log("2. 组合排列_范围选取_示例() - 交互式选择数据范围进行组合排列");
    console.log("3. combin_arr1(Arr, n) - 组合不放回 C(m,n)");
    console.log("4. combin_arr_repet(Arr, n) - 组合放回 C(m+n-1,n)");
    console.log("5. permut_no_repet(Arr, n) - 排列不放回 P(m,n)");
    console.log("6. permut_repet(Arr, n) - 排列放回 m^n");
}

// 自动执行初始化
Initialize();