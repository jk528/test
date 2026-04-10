// PC_005_选择范围全排列_WPS.js - 适配 WPS 环境的 JavaScript 代码
// 从选择范围中进行全排列计算

// 用于记录排列索引的全局变量
var k = 0;

// WPS 兼容的消息提示函数
function ShowMessage(message, type) {
    try {
        // type: 64=信息, 48=错误
        if (typeof Application.MsgBox === 'function') {
            Application.MsgBox(message, type || 64, "全排列");
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
    var data = [];

    // 方法1：直接访问 Rows.Count 和 Columns.Count
    try {
        var rows = range.Rows.Count;
        var cols = range.Columns.Count;

        // 遍历所有单元格
        for (var i = 1; i <= rows; i++) {
            for (var j = 1; j <= cols; j++) {
                try {
                    var cell = range.Cells(i, j);
                    var value = cell.Value;
                    if (value !== undefined && value !== null && value !== '') {
                        data.push(value);
                    }
                } catch (cellError) {
                    // 忽略单元格读取错误
                }
            }
        }
    } catch (e) {
        // 方法2：尝试直接获取 Value
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
            // 忽略错误
        }
    }

    return data;
}

// 处理 InputBox 返回的数组数据
function processInputArray(inputArray) {
    var data = [];

    // 处理 WPS 范围对象
    if (inputArray && typeof inputArray === 'object' && inputArray.Cells) {
        data = extractDataFromRange(inputArray);
    } else if (inputArray && typeof inputArray === 'function') {
        // WPS JavaScript 中 InputBox 返回的是函数代理，需要调用
        try {
            var rangeObj = inputArray();

            if (rangeObj && rangeObj.Cells) {
                data = extractDataFromRange(rangeObj);
            } else if (Array.isArray(rangeObj)) {
                // 直接扁平化这个二维数组
                for (var i = 0; i < rangeObj.length; i++) {
                    if (Array.isArray(rangeObj[i])) {
                        for (var j = 0; j < rangeObj[i].length; j++) {
                            var value = rangeObj[i][j];
                            if (value !== undefined && value !== null && value !== '') {
                                data.push(value);
                            }
                        }
                    } else {
                        var value = rangeObj[i];
                        if (value !== undefined && value !== null && value !== '') {
                            data.push(value);
                        }
                    }
                }
            } else if (rangeObj && typeof rangeObj === 'object' && rangeObj.Value) {
                var val = rangeObj.Value;
                if (Array.isArray(val)) {
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
                    data = extractDataFromRange(val);
                } else {
                    data = [val];
                }
            } else if (rangeObj && typeof rangeObj !== 'object') {
                data = [rangeObj];
            }
        } catch (funcError) {
            console.error("函数调用失败: " + (funcError.message || String(funcError)));
        }
    } else if (inputArray && typeof inputArray === 'object' && inputArray.Value) {
        try {
            var valueData = inputArray.Value;
            if (Array.isArray(valueData)) {
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
                data = extractDataFromRange(valueData);
            } else {
                data = [valueData];
            }
        } catch (e) {
            console.error("获取 Value 失败: " + (e.message || String(e)));
        }
    } else if (Array.isArray(inputArray)) {
        data = inputArray.filter(function(item) {
            return item !== undefined && item !== null && item !== '';
        });
    }

    return data;
}

// 获取或创建工作表
function GetOrInitWorksheet(Name) {
    let ws;
    try {
        ws = ThisWorkbook.Worksheets(Name);
    } catch (e) {
        ws = ThisWorkbook.Worksheets.Add();
        ws.Name = Name;
    }
    return ws;
}

// 计算阶乘
function Factorial(n) {
    var result = 1;
    for (var i = 2; i <= n; i++) {
        result = result * i;
    }
    return result;
}

// 核心全排列递归函数
function Solver(Arr, m, brr) {
    var n = Arr.length - 1;
    if (m < n) {
        // 递归处理
        Solver(Arr, m + 1, brr);
        for (var i = m + 1; i <= n; i++) {
            // 交换元素
            var t = Arr[m];
            Arr[m] = Arr[i];
            Arr[i] = t;
            // 递归处理交换后的排列
            Solver(Arr, m + 1, brr);
            // 恢复原始顺序（回溯）
            var t2 = Arr[m];
            Arr[m] = Arr[i];
            Arr[i] = t2;
        }
    } else {
        // 找到一个完整排列，存储到结果数组
        k++;
        for (var i = 0; i < Arr.length; i++) {
            brr[k - 1][i] = Arr[i];
        }
    }
}

// 主封装函数：全排列计算并返回二维数组
function CalculatePermutations(inputArray, isRowMajor) {
    try {
        // 默认参数
        if (isRowMajor === undefined) {
            isRowMajor = true;
        }

        var tempArray1D = [];

        // 处理 WPS 范围对象
        if (inputArray && typeof inputArray === 'object' && inputArray.Cells) {
            tempArray1D = extractDataFromRange(inputArray);
        } else if (inputArray && typeof inputArray === 'function') {
            // WPS JavaScript 中 InputBox 返回的是函数代理
            try {
                var rangeObj = inputArray();
                if (rangeObj && rangeObj.Cells) {
                    tempArray1D = extractDataFromRange(rangeObj);
                } else if (Array.isArray(rangeObj)) {
                    for (var i = 0; i < rangeObj.length; i++) {
                        if (Array.isArray(rangeObj[i])) {
                            for (var j = 0; j < rangeObj[i].length; j++) {
                                var value = rangeObj[i][j];
                                if (value !== undefined && value !== null && value !== '') {
                                    tempArray1D.push(value);
                                }
                            }
                        } else {
                            var value = rangeObj[i];
                            if (value !== undefined && value !== null && value !== '') {
                                tempArray1D.push(value);
                            }
                        }
                    }
                }
            } catch (funcError) {
                console.error("函数调用失败: " + (funcError.message || String(funcError)));
            }
        } else if (Array.isArray(inputArray)) {
            tempArray1D = inputArray.filter(function(item) {
                return item !== undefined && item !== null && item !== '';
            });
        }

        // 获取数组大小
        var arrSize = tempArray1D.length;
        console.log("数组大小: " + arrSize);

        if (arrSize === 0) {
            throw new Error("输入数组为空");
        }

        // 检查元素数量，超过9则退出
        if (arrSize > 9) {
            var factorial9 = 362880; // 9!
            var factorial10 = 3628800; // 10!
            ShowMessage("元素数量不能超过 9 个！\n\n" +
                       "当前元素数量: " + arrSize + "\n" +
                       "9! = " + factorial9 + " 条排列\n" +
                       arrSize + "! = " + factorial10 + "+ 条排列\n\n" +
                       "数据量太大，为避免程序卡死，请减少元素数量。", 48);
            return null;
        }

        // 计算排列总数：n!
        var PermCount = Factorial(arrSize);
        console.log("排列总数: " + PermCount);

        // 初始化结果数组
        var resultArray = [];
        for (var i = 0; i < PermCount; i++) {
            resultArray[i] = [];
            for (var j = 0; j < arrSize; j++) {
                resultArray[i][j] = '';
            }
        }

        // 重置计数器
        k = 0;

        // 准备临时数组用于传递
        var tempArray = [];
        for (var i = 0; i < arrSize; i++) {
            tempArray[i] = tempArray1D[i];
        }

        // 调用Solver函数
        Solver(tempArray, 0, resultArray);

        // 检查结果
        if (k === 0) {
            return null;
        }

        return resultArray;
    } catch (error) {
        console.error("全排列错误: " + (error.message || String(error)));
        return null;
    }
}

// 测试函数 - 选择范围进行全排列
function TestPermutations2D() {
    try {
        // 开始计时
        var startTime = new Date().getTime();

        // 获取用户选择的单元格区域
        var inputRange = WPSInputBox(
            "请选择要进行全排列的数据范围\n（支持一列、一行或矩形范围）",
            "选择数据范围",
            8
        );

        if (inputRange === false || inputRange === null) {
            return;
        }

        if (!inputRange) {
            ShowMessage("未选择有效范围", 48);
            return;
        }

        // 调用封装函数（行优先）获取原始元素排列
        var resultArr = CalculatePermutations(inputRange, true);

        if (resultArr === null) {
            ShowMessage("计算错误", 48);
            return;
        }

        // 获取或创建工作表
        var ws = GetOrInitWorksheet("全排列结果");
        ws.Cells.Clear();

        // 获取结果数组的大小
        var rowCount = resultArr.length;
        var colCount = resultArr[0].length;

        // 创建索引数组 [1,2,3,...colCount]
        var indexArr = [];
        for (var i = 0; i < colCount; i++) {
            indexArr[i] = i + 1;
        }

        // 调用封装函数获取索引排列
        var indexResultArr = CalculatePermutations(indexArr, true);

        if (indexResultArr === null) {
            ShowMessage("索引排列计算错误", 48);
            return;
        }

        // 设置标题行
        try {
            var totalCols = 1 + colCount * 2; // 序号 + 元素 + 映射
            var headerArray = [];
            headerArray[0] = [];
            headerArray[0][0] = "序号";
            for (var i = 0; i < colCount; i++) {
                headerArray[0][i + 1] = "元素 " + (i + 1);
                headerArray[0][i + 1 + colCount] = "映射 " + (i + 1);
            }

            // 尝试使用 Range 写入
            try {
                var headerRange = ws.Range(ws.Cells(1, 1), ws.Cells(1, totalCols));
                headerRange.Value2 = headerArray;
            } catch (headerError) {
                // 逐单元格写入
                ws.Cells(1, 1).Value = "序号";
                for (var i = 0; i < colCount; i++) {
                    ws.Cells(1, i + 2).Value = "元素 " + (i + 1);
                    ws.Cells(1, i + 2 + colCount).Value = "映射 " + (i + 1);
                }
            }
        } catch (titleError) {
            console.error("标题行设置失败: " + (titleError.message || String(titleError)));
            ShowMessage("标题行设置失败: " + (titleError.message || String(titleError)), 48);
            return;
        }

        // 写入数据
        try {
            var allData = [];
            for (var i = 0; i < rowCount; i++) {
                allData[i] = [];
                // 序号
                allData[i][0] = i + 1;
                // 原始元素
                for (var j = 0; j < colCount; j++) {
                    allData[i][j + 1] = resultArr[i][j];
                }
                // 索引映射
                for (var j = 0; j < colCount; j++) {
                    allData[i][j + 1 + colCount] = indexResultArr[i][j];
                }
            }

            // 尝试使用 Range 批量写入
            try {
                var dataRange = ws.Range(ws.Cells(2, 1), ws.Cells(rowCount + 1, totalCols));
                dataRange.Value2 = allData;
            } catch (dataError) {
                // 逐行写入
                for (var i = 0; i < rowCount; i++) {
                    ws.Cells(i + 2, 1).Value = i + 1;
                    for (var j = 0; j < colCount; j++) {
                        ws.Cells(i + 2, j + 2).Value = resultArr[i][j];
                    }
                    for (var j = 0; j < colCount; j++) {
                        ws.Cells(i + 2, j + 2 + colCount).Value = indexResultArr[i][j];
                    }
                }
            }
        } catch (writeError) {
            console.error("数据写入失败: " + (writeError.message || String(writeError)));
            ShowMessage("数据写入失败: " + (writeError.message || String(writeError)), 48);
            return;
        }

        // 自动调整列宽
        ws.Columns.AutoFit();

        // 结束计时
        var endTime = new Date().getTime();
        var elapsedTime = (endTime - startTime) / 1000;

        // 显示完成信息和用时
        var message = "全排列计算完成！\n" +
                     "排列总数: " + rowCount + "\n" +
                     "元素数量: " + colCount + "\n" +
                     "处理用时: " + elapsedTime.toFixed(3) + " 秒";

        // 激活结果工作表
        ws.Activate();

        ShowMessage(message, 64);
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
        ShowMessage("错误: " + (error.message || String(error)), 48);
    }
}

// 初始化函数
// function Initialize() {
//     console.log("PC_005_选择范围全排列_WPS 代码初始化完成");
//     console.log("可用函数:");
//     console.log("1. TestPermutations2D() - 选择范围进行全排列（推荐）");
//     console.log("2. CalculatePermutations(inputArray, isRowMajor) - 核心计算函数");
//     console.log("3. extractDataFromRange(range) - 从范围提取数据");
//     console.log("4. processInputArray(inputArray) - 处理 InputBox 返回数据");
// }

// 自动执行初始化
// Initialize();