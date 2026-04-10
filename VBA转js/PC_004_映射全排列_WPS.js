// PC_004_映射全排列_WPS.js - 适配 WPS 环境的 JavaScript 代码

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

// 计算阶乘
function Factorial(n) {
    var result = 1;
    for (var i = 2; i <= n; i++) {
        result = result * i;
    }
    return result;
}

// 检测数组维度
function GetArrayDimension(Arr) {
    if (typeof Arr !== 'object' || Arr === null) {
        return 0;
    }
    
    // 检查是否为 WPS 范围对象
    if (Arr.Value) {
        return GetArrayDimension(Arr.Value);
    }
    
    // 检查是否为数组或类数组对象
    if (Array.isArray(Arr)) {
        if (Arr.length === 0) {
            return 1;
        }
        if (Array.isArray(Arr[0])) {
            return 2;
        }
        return 1;
    }
    
    // 检查是否为 WPS 返回的二维范围值（可能是对象形式）
    if (typeof Arr === 'object' && Arr.constructor && Arr.constructor.name === 'Array') {
        if (Arr.length === 0) {
            return 1;
        }
        if (typeof Arr[0] === 'object' && Arr[0].constructor && Arr[0].constructor.name === 'Array') {
            return 2;
        }
        return 1;
    }
    
    // 检查是否为类似数组的对象（如 WPS 范围值）
    if (typeof Arr === 'object' && typeof Arr.length === 'number') {
        if (Arr.length === 0) {
            return 1;
        }
        if (typeof Arr[0] === 'object' && typeof Arr[0].length === 'number') {
            return 2;
        }
        return 1;
    }
    
    return 0;
}

// 按行优先将二维数组转换为一维数组
function FlattenArrayRowMajor(matrix) {
    var result = [];
    for (var i = 0; i < matrix.length; i++) {
        for (var j = 0; j < matrix[i].length; j++) {
            result.push(matrix[i][j]);
        }
    }
    return result;
}

// 按列优先将二维数组转换为一维数组
function FlattenArrayColumnMajor(matrix) {
    var result = [];
    var rows = matrix.length;
    var cols = matrix[0].length;
    for (var j = 0; j < cols; j++) {
        for (var i = 0; i < rows; i++) {
            result.push(matrix[i][j]);
        }
    }
    return result;
}

// 核心全排列递归函数
function Solver(Arr, m, brr) {
    console.log("Solver 调用: m=" + m + ", Arr.length=" + Arr.length);
    try {
        var n = Arr.length - 1;
        console.log("Solver 内部: n=" + n);
        if (m < n) {
            console.log("递归调用 Solver, m+1=" + (m + 1));
            // 递归处理
            Solver(Arr, m + 1, brr);
            for (var i = m + 1; i <= n; i++) {
                console.log("交换位置: m=" + m + ", i=" + i + ", Arr=" + Arr.toString());
                // 交换元素
                var t = Arr[m];
                Arr[m] = Arr[i];
                Arr[i] = t;
                console.log("交换后 Arr=" + Arr.toString());
                // 递归处理交换后的排列
                Solver(Arr, m + 1, brr);
                // 恢复原始顺序（回溯）
                var t2 = Arr[m];
                Arr[m] = Arr[i];
                Arr[i] = t2;
                console.log("回溯后 Arr=" + Arr.toString());
            }
        } else {
            // 找到一个完整排列，存储到结果数组
            k++;
            console.log("找到排列 #" + k + ": " + Arr.toString());
            for (var i = 0; i < Arr.length; i++) {
                brr[k - 1][i] = Arr[i];
            }
            console.log("已存储到 brr[" + (k - 1) + "]");
        }
    } catch (e) {
        console.error("Solver 错误: " + (e.message || String(e)));
        throw e;
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
        console.error("错误: " + (e.stack || "无堆栈"));

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
                    console.log("Value 是单个值: " + rangeValue);
                    data.push(rangeValue);
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

// 主封装函数：全排列计算并返回二维数组
function CalculatePermutations(inputArray, isRowMajor) {
    console.log("开始执行 CalculatePermutations");
    try {
        // 默认参数
        if (isRowMajor === undefined) {
            isRowMajor = true;
        }
        console.log("isRowMajor: " + isRowMajor);
        
        var tempArray1D = [];
        
        console.log("检查 inputArray 类型: " + typeof inputArray);
        console.log("inputArray 是否有 Cells 属性: " + (inputArray && inputArray.Cells ? "是" : "否"));
        console.log("inputArray 是否有 Value 属性: " + (inputArray && inputArray.Value ? "是" : "否"));
        console.log("inputArray 是否为数组: " + (Array.isArray(inputArray) ? "是" : "否"));
        
        // 处理 WPS 范围对象
        if (inputArray && typeof inputArray === 'object' && inputArray.Cells) {
            console.log("检测到 WPS 范围对象，使用 extractDataFromRange");
            tempArray1D = extractDataFromRange(inputArray);
            console.log("extractDataFromRange 返回: " + tempArray1D.toString());
        } else if (inputArray && typeof inputArray === 'function') {
            console.log("检测到 inputArray 是函数，尝试获取其返回值");
            // WPS JavaScript 中 InputBox 返回的是函数代理，需要调用
            try {
                // 调用函数获取 Range 对象
                var rangeObj = inputArray();
                console.log("函数调用返回类型: " + typeof rangeObj);
                console.log("返回对象: " + JSON.stringify(rangeObj));
                console.log("返回对象是否有 Cells: " + (rangeObj && rangeObj.Cells ? "是" : "否"));
                console.log("返回对象是否有 Value: " + (rangeObj && rangeObj.Value ? "是" : "否"));
                console.log("返回对象是否有 Address: " + (rangeObj && rangeObj.Address ? "是" : "否"));
                console.log("返回对象构造函数: " + (rangeObj && rangeObj.constructor ? rangeObj.constructor.name : "无"));
                
                // 尝试遍历返回对象的所有属性
                if (rangeObj && typeof rangeObj === 'object') {
                    console.log("返回对象的属性列表:");
                    for (var prop in rangeObj) {
                        console.log("  - " + prop + ": " + typeof rangeObj[prop]);
                    }
                }
                
                if (rangeObj && rangeObj.Cells) {
                    console.log("调用 extractDataFromRange 处理返回对象");
                    tempArray1D = extractDataFromRange(rangeObj);
                    console.log("extractDataFromRange 返回: " + tempArray1D.toString());
                } else if (rangeObj && typeof rangeObj === 'object') {
                    console.log("返回对象是普通对象，检查 Value 属性");
                    if (rangeObj.Value) {
                        var val = rangeObj.Value;
                        console.log("Value 类型: " + typeof val);
                        if (Array.isArray(val)) {
                            console.log("Value 是数组");
                            inputArray = val;
                        } else if (val && val.Cells) {
                            console.log("Value 是范围对象");
                            tempArray1D = extractDataFromRange(val);
                        } else {
                            console.log("Value 是单个值: " + val);
                            tempArray1D = [val];
                        }
                    } else if (Array.isArray(rangeObj)) {
                        console.log("返回对象是数组，直接处理");
                        console.log("数组内容: " + JSON.stringify(rangeObj));
                        // 直接扁平化这个二维数组
                        for (var i = 0; i < rangeObj.length; i++) {
                            if (Array.isArray(rangeObj[i])) {
                                for (var j = 0; j < rangeObj[i].length; j++) {
                                    var value = rangeObj[i][j];
                                    console.log("处理值 [" + i + "][" + j + "]: " + value);
                                    if (value !== undefined && value !== null && value !== '') {
                                        tempArray1D.push(value);
                                    }
                                }
                            } else {
                                var value = rangeObj[i];
                                console.log("处理值 [" + i + "]: " + value);
                                if (value !== undefined && value !== null && value !== '') {
                                    tempArray1D.push(value);
                                }
                            }
                        }
                        console.log("处理后的一维数组: " + tempArray1D.toString());
                    } else {
                        console.log("返回对象是普通值: " + rangeObj);
                        tempArray1D = [rangeObj];
                    }
                } else {
                    console.error("函数未返回有效的范围对象");
                }
            } catch (funcError) {
                console.error("函数调用失败: " + (funcError.message || String(funcError)));
                console.error("错误堆栈: " + (funcError.stack || "无"));
            }
        } else if (inputArray && typeof inputArray === 'object' && inputArray.Value) {
            console.log("检测到包含 Value 属性的对象，尝试获取 Value");
            // 可能是包含 Value 属性的对象
            try {
                var valueData = inputArray.Value;
                console.log("Value 属性类型: " + typeof valueData);
                console.log("Value 属性是否为数组: " + (Array.isArray(valueData) ? "是" : "否"));
                
                if (Array.isArray(valueData)) {
                    inputArray = valueData;
                } else if (valueData && valueData.Cells) {
                    // Value 返回的是范围对象
                    console.log("Value 返回范围对象");
                    tempArray1D = extractDataFromRange(valueData);
                    console.log("extractDataFromRange 返回: " + tempArray1D.toString());
                } else {
                    // 单个值
                    console.log("单个值: " + valueData);
                    tempArray1D = [valueData];
                }
            } catch (valueError) {
                console.error("获取 Value 失败: " + (valueError.message || String(valueError)));
            }
        } else if (Array.isArray(inputArray)) {
            console.log("检测为普通 JavaScript 数组");
            // 普通 JavaScript 数组
            if (Array.isArray(inputArray[0])) {
                console.log("二维数组，使用扁平化");
                // 二维数组
                if (isRowMajor) {
                    tempArray1D = FlattenArrayRowMajor(inputArray);
                } else {
                    tempArray1D = FlattenArrayColumnMajor(inputArray);
                }
            } else {
                console.log("一维数组，直接使用");
                // 一维数组
                tempArray1D = inputArray;
            }
            // 过滤空值
            tempArray1D = tempArray1D.filter(function(item) {
                return item !== undefined && item !== null && item !== '';
            });
        } else {
            console.error("无法识别 inputArray 类型");
            throw new Error("无法识别输入类型");
        }
        
        console.log("处理后的一维数组: " + tempArray1D.toString());
        
        // 获取数组大小
        var arrSize = tempArray1D.length;
        console.log("数组大小: " + arrSize);
        
        if (arrSize === 0) {
            console.error("输入数组为空");
            throw new Error("输入数组为空");
        }
        
        console.log("开始计算排列");
        // 计算排列总数：n!
        var PermCount = Factorial(arrSize);
        console.log("排列总数: " + PermCount);
        
        console.log("初始化结果数组");
        // 初始化结果数组
        var resultArray = [];
        for (var i = 0; i < PermCount; i++) {
            resultArray[i] = [];
            for (var j = 0; j < arrSize; j++) {
                resultArray[i][j] = '';
            }
        }
        console.log("结果数组初始化完成");
        
        // 重置计数器
        k = 0;
        console.log("计数器重置: k = 0");
        
        // 准备临时数组用于传递
        var tempArray = [];
        for (var i = 0; i < arrSize; i++) {
            tempArray[i] = tempArray1D[i];
        }
        console.log("临时数组: " + tempArray.toString());
        
        console.log("调用 Solver 函数");
        // 调用Solver函数
        Solver(tempArray, 0, resultArray);
        console.log("Solver 函数执行完成，k = " + k);
        
        // 检查结果
        if (k === 0) {
            console.error("Solver 函数未生成任何排列");
            return null;
        }
        
        console.log("生成的排列数量: " + k);
        console.log("第一个排列: " + resultArray[0].toString());
        
        // 返回结果
        console.log("CalculatePermutations 执行完成，返回结果");
        return resultArray;
    } catch (error) {
        console.error("全排列错误: " + (error.message || String(error)));
        console.error("错误详情: " + error.stack);
        return null;
    }
}

// 测试函数 - 二维数组（优化版，带索引映射）
function TestPermutations2D() {
    console.log("开始执行 TestPermutations2D");
    try {
        // 开始计时
        var startTime = new Date().getTime();
        console.log("步骤1: 获取用户选择的单元格区域");
        
        // 获取用户选择的单元格区域
        console.log("步骤1: 获取用户选择的单元格区域");
        try {
            // Application.InputBox(prompt, title, default, left, top, helpFile, helpContextID, type)
            // Type = 8 表示 Range 对象
            var inputRange = Application.InputBox(
                "请选择要进行全排列的数据范围\n（支持一列、一行或矩形范围）",
                "选择数据范围",
                "",
                100,
                100,
                "",
                0,
                8
            );
            console.log("用户选择结果: " + (inputRange ? "成功" : "失败"));
        } catch (inputError) {
            console.error("InputBox 调用失败: " + (inputError.message || String(inputError)));
            try {
                ShowMessage("无法获取用户选择，请重试", 48);
            } catch (e) {}
            return;
        }
        
        // 检查用户是否取消选择
        if (inputRange === false) {
            console.log("用户取消选择");
            return;
        }
        
        // 检查是否成功获取范围
        if (!inputRange) {
            console.error("未选择有效范围");
            try {
                ShowMessage("未选择有效范围", 48);
            } catch (e) {
                console.error("未选择有效范围");
            }
            return;
        }
        
        console.log("步骤2: 调用 CalculatePermutations 计算全排列");
        // 调用封装函数（行优先）获取原始元素排列
        var resultArr = CalculatePermutations(inputRange, true);
        
        console.log("全排列计算结果: " + (resultArr ? "成功" : "失败"));
        
        // 输出结果
        if (resultArr === null) {
            console.error("计算错误");
            try {
                ShowMessage("计算错误", 48);
            } catch (e) {
                console.error("计算错误");
            }
            return;
        }
        
        console.log("步骤3: 准备工作表");
        // 获取或创建工作表
        var ws = GetOrInitWorksheet("全排列结果");
        console.log("工作表准备完成");
        
        ws.Cells.Clear();
        console.log("工作表已清空");
        
        // 获取结果数组的大小
        var rowCount = resultArr.length;
        var colCount = resultArr[0].length;
        console.log("结果数组大小: " + rowCount + "行 × " + colCount + "列");
        
        console.log("步骤4: 生成索引数组");
        // 创建索引数组 [1,2,3,...colCount]
        var indexArr = [];
        for (var i = 0; i < colCount; i++) {
            indexArr[i] = i + 1;
        }
        console.log("索引数组: " + indexArr.toString());
        
        console.log("步骤5: 计算索引排列");
        // 调用封装函数获取索引排列（使用相同的k值，确保排列顺序一致）
        var indexResultArr = CalculatePermutations(indexArr, true);
        
        console.log("索引排列计算结果: " + (indexResultArr ? "成功" : "失败"));
        
        // 检查索引排列是否成功
        if (indexResultArr === null) {
            console.error("索引排列计算错误");
            try {
                ShowMessage("索引排列计算错误", 48);
            } catch (e) {
                console.error("索引排列计算错误");
            }
            return;
        }
        
        console.log("步骤6: 设置标题行");
        // 设置标题行
        try {
            var totalCols = 1 + colCount * 2; // 序号 + 元素 + 映射
            
            // 创建标题数组
            var headerArray = [];
            headerArray[0] = [];
            headerArray[0][0] = "序号";
            for (var i = 0; i < colCount; i++) {
                headerArray[0][i + 1] = "元素 " + (i + 1);
                headerArray[0][i + 1 + colCount] = "映射 " + (i + 1);
            }
            
            console.log("标题数组: " + headerArray[0].toString());
            
            // 尝试使用 Range 写入
            try {
                var headerRange = ws.Range(ws.Cells(1, 1), ws.Cells(1, totalCols));
                headerRange.Value2 = headerArray;
                console.log("标题行 Range 写入成功");
            } catch (headerError) {
                console.error("标题行 Range 写入失败: " + (headerError.message || String(headerError)));
                // 逐单元格写入
                ws.Cells(1, 1).Value = "序号";
                for (var i = 0; i < colCount; i++) {
                    ws.Cells(1, i + 2).Value = "元素 " + (i + 1);
                    ws.Cells(1, i + 2 + colCount).Value = "映射 " + (i + 1);
                }
                console.log("逐单元格标题写入成功");
            }
            console.log("标题行设置完成");
        } catch (titleError) {
            console.error("标题行设置失败: " + (titleError.message || String(titleError)));
            try {
                ShowMessage("标题行设置失败: " + (titleError.message || String(titleError)), 48);
            } catch (e) {}
            return;
        }
        
        console.log("步骤7: 写入数据");
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
            
            console.log("数据数组合并完成");
            
            // 尝试使用 Range 批量写入
            try {
                var dataRange = ws.Range(ws.Cells(2, 1), ws.Cells(rowCount + 1, totalCols));
                dataRange.Value2 = allData;
                console.log("Range 批量写入成功");
            } catch (dataError) {
                console.error("Range 批量写入失败: " + (dataError.message || String(dataError)));
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
                console.log("逐行写入完成");
            }
            console.log("数据写入完成");
        } catch (writeError) {
            console.error("数据写入失败: " + (writeError.message || String(writeError)));
            try {
                ShowMessage("数据写入失败: " + (writeError.message || String(writeError)), 48);
            } catch (e) {}
            return;
        }
        
        console.log("步骤8: 调整列宽");
        // 自动调整列宽
        ws.Columns.AutoFit();
        console.log("列宽调整完成");
        
        // 结束计时
        var endTime = new Date().getTime();
        var elapsedTime = (endTime - startTime) / 1000;
        
        // 显示完成信息和用时
        var message = "全排列计算完成！\n" +
                     "排列总数: " + rowCount + "\n" +
                     "元素数量: " + colCount + "\n" +
                     "处理用时: " + elapsedTime.toFixed(3) + " 秒";
        
        console.log("步骤9: 激活工作表");
        // 激活结果工作表
        ws.Activate();
        console.log("工作表已激活");
        
        // 简单的消息提示
        try {
            if (typeof Application.MsgBox === 'function') {
                ShowMessage(message, 64);
            } else if (typeof Application.Alert === 'function') {
                Application.Alert(message);
            } else {
                console.log("消息提示: " + message);
            }
            console.log("消息框显示完成");
        } catch (e) {
            console.log("消息框显示失败: " + (e.message || String(e)));
        }
        
        console.log("TestPermutations2D 执行完成");
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
        try {
            ShowMessage("错误: " + (error.message || String(error)), 48);
        } catch (e) {
            // 忽略 MsgBox 错误
        }
    }
}

// 简化的测试函数，用于快速验证
function TestSimplePermutation() {
    try {
        // 测试简单数组
        var testArray = [1, 2, 3];
        var result = CalculatePermutations(testArray, true);
        
        if (result) {
            // 获取或创建工作表
            var ws = GetOrInitWorksheet("测试结果");
            ws.Cells.Clear();
            
            // 写入数据
            const rows = result.length;
            const cols = result[0].length;
            try {
                // 尝试直接数组赋值
                const range = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols));
                range.Value2 = result;
            } catch (e) {
                // 回退到逐单元格写入
                for (let i = 0; i < rows; i++) {
                    for (let j = 0; j < cols; j++) {
                        ws.Cells(i + 1, j + 1).Value = result[i][j];
                    }
                }
            }
            
            // 自动调整列宽
            ws.Columns.AutoFit();
            // 激活工作表
            ws.Activate();
            
            try {
                ShowMessage("简单测试完成，结果已输出到 '测试结果' 工作表", 64);
            } catch (e) {
                // 忽略 MsgBox 错误
            }
        }
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
    }
}

// 测试字符串全排列
function TestStringPermutation() {
    console.log("开始执行 TestStringPermutation");
    try {
        // 测试字符串数组
        var testArray = ["你", "好", "吗"];
        console.log("测试字符串数组: " + testArray.toString());

        var result = CalculatePermutations(testArray, true);
        console.log("计算结果: " + (result ? "成功" : "失败"));

        if (result) {
            console.log("计算成功，生成 " + result.length + " 个排列");

            // 获取或创建工作表
            console.log("创建或获取工作表");
            var ws = GetOrInitWorksheet("字符串全排列结果");
            console.log("工作表获取成功");

            console.log("清空工作表");
            ws.Cells.Clear();
            console.log("工作表已清空");

            // 设置标题行
            console.log("设置标题行");
            try {
                // 使用 Range 对象写入标题行，更可靠
                var colCount = result[0].length;
                var totalCols = 1 + colCount * 2; // 序号 + 元素 + 映射
                
                // 创建标题数组
                var headerArray = [];
                headerArray[0] = [];
                headerArray[0][0] = "序号";
                for (var i = 0; i < colCount; i++) {
                    headerArray[0][i + 1] = "元素 " + (i + 1);
                    headerArray[0][i + 1 + colCount] = "映射 " + (i + 1);
                }
                
                console.log("标题数组: " + headerArray[0].toString());
                
                // 尝试使用 Range 写入
                try {
                    console.log("创建 Range 对象");
                    var headerRange = ws.Range(ws.Cells(1, 1), ws.Cells(1, totalCols));
                    console.log("Range 对象创建成功");
                    console.log("尝试写入 headerArray");
                    console.log("headerArray 类型: " + typeof headerArray);
                    console.log("headerArray 是否为数组: " + (Array.isArray(headerArray) ? "是" : "否"));
                    headerRange.Value = headerArray;
                    console.log("标题行 Range 写入成功");
                } catch (rangeError) {
                    console.error("Range 写入失败: " + (rangeError.message || String(rangeError)));
                    console.error("错误名称: " + (rangeError.name || "未知"));
                    console.error("错误堆栈: " + (rangeError.stack || "无堆栈信息"));
                    console.log("尝试使用 Value2 写入");
                    try {
                        headerRange.Value2 = headerArray;
                        console.log("Value2 写入成功");
                    } catch (value2Error) {
                        console.error("Value2 写入也失败: " + (value2Error.message || String(value2Error)));
                        console.log("尝试逐单元格写入");
                        
                        // 逐单元格写入
                        ws.Cells(1, 1).Value = "序号";
                        for (var i = 0; i < colCount; i++) {
                            ws.Cells(1, i + 2).Value = "元素 " + (i + 1);
                            ws.Cells(1, i + 2 + colCount).Value = "映射 " + (i + 1);
                        }
                        console.log("逐单元格标题写入成功");
                    }
                }
                console.log("标题行设置完成");
            } catch (titleError) {
                console.error("标题行设置失败: " + (titleError.message || String(titleError)));
                console.error("错误详情: " + (titleError.stack || "无堆栈信息"));
                try {
                    ShowMessage("标题行设置失败: " + (titleError.message || String(titleError)), 48);
                } catch (e) {}
                return;
            }

            // 创建索引数组
            console.log("创建索引数组");
            var indexArr = [];
            for (var i = 0; i < result[0].length; i++) {
                indexArr[i] = i + 1;
            }
            console.log("索引数组: " + indexArr.toString());

            console.log("计算索引排列");
            var indexResult = CalculatePermutations(indexArr, true);
            console.log("索引排列计算结果: " + (indexResult ? "成功" : "失败"));

            if (!indexResult) {
                console.error("索引排列计算失败");
                try {
                    Application.MsgBox("索引排列计算失败", 48, "错误");
                } catch (e) {}
                return;
            }

            // 写入数据
            console.log("开始写入数据，行数: " + result.length);
            try {
                var rowCount = result.length;
                var colCount = result[0].length;
                var totalCols = 1 + colCount * 2; // 序号 + 元素 + 映射

                // 合并所有数据到一个数组
                var allData = [];
                for (var i = 0; i < rowCount; i++) {
                    allData[i] = [];
                    // 序号
                    allData[i][0] = i + 1;
                    // 原始元素
                    for (var j = 0; j < colCount; j++) {
                        allData[i][j + 1] = result[i][j];
                    }
                    // 索引映射
                    for (var j = 0; j < colCount; j++) {
                        allData[i][j + 1 + colCount] = indexResult[i][j];
                    }
                }

                console.log("数据数组合并完成");

                // 尝试使用 Range 批量写入
                try {
                    console.log("创建数据 Range 对象");
                    var dataRange = ws.Range(ws.Cells(2, 1), ws.Cells(rowCount + 1, totalCols));
                    console.log("数据 Range 对象创建成功");
                    console.log("尝试写入 allData");
                    console.log("allData 长度: " + allData.length);
                    console.log("allData[0] 长度: " + (allData[0] ? allData[0].length : "undefined"));
                    dataRange.Value = allData;
                    console.log("Range 批量写入成功");
                } catch (dataError) {
                    console.error("Range 批量写入失败: " + (dataError.message || String(dataError)));
                    console.error("错误名称: " + (dataError.name || "未知"));
                    console.error("错误堆栈: " + (dataError.stack || "无堆栈信息"));
                    console.log("尝试使用 Value2 写入");
                    try {
                        dataRange.Value2 = allData;
                        console.log("Value2 批量写入成功");
                    } catch (value2Error) {
                        console.error("Value2 写入也失败: " + (value2Error.message || String(value2Error)));
                        console.log("尝试逐行写入");
                        
                        // 逐行写入
                        for (var i = 0; i < rowCount; i++) {
                            // 序号
                            ws.Cells(i + 2, 1).Value = i + 1;
                            // 原始元素
                            for (var j = 0; j < colCount; j++) {
                                ws.Cells(i + 2, j + 2).Value = result[i][j];
                            }
                            // 索引映射
                            for (var j = 0; j < colCount; j++) {
                                ws.Cells(i + 2, j + 2 + colCount).Value = indexResult[i][j];
                            }
                        }
                        console.log("逐行写入完成");
                    }
                }
                console.log("数据写入完成");
            } catch (dataError) {
                console.error("数据写入失败: " + (dataError.message || String(dataError)));
                console.error("错误详情: " + (dataError.stack || "无堆栈信息"));
                try {
                    ShowMessage("数据写入失败: " + (dataError.message || String(dataError)), 48);
                } catch (e) {}
                return;
            }

            // 自动调整列宽
            console.log("调整列宽");
            ws.Columns.AutoFit();

            // 激活工作表
            console.log("激活工作表");
            ws.Activate();

            try {
                ShowMessage("字符串全排列测试完成！\n原始字符串: 你、好、吗\n排列数量: " + result.length + "\n结果已输出到 '字符串全排列结果' 工作表", 64);
            } catch (e) {
                // 忽略 MsgBox 错误
            }
        } else {
            console.error("字符串全排列计算失败");
            try {
                ShowMessage("字符串全排列计算失败", 48);
            } catch (e) {
                // 忽略 MsgBox 错误
            }
        }
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
        try {
            ShowMessage("错误: " + (error.message || String(error)), 48);
        } catch (e) {
            // 忽略 MsgBox 错误
        }
    }
}

// 初始化函数，确保代码能在 WPS 中正常运行
function Initialize() {
    console.log("全排列代码初始化完成");
    console.log("可用函数:");
    console.log("1. TestPermutations2D() - 选择范围进行全排列");
    console.log("2. TestSimplePermutation() - 使用预设数组 [1,2,3] 测试");
    console.log("3. TestStringPermutation() - 使用预设字符串 ['你','好','吗'] 测试");
    console.log("4. CalculatePermutations(inputArray, isRowMajor) - 核心计算函数");
}
