// PC_004_映射全排列_WPS.js - 适配 WPS 环境的 JavaScript 代码

// 用于记录排列索引的全局变量
var k = 0;

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
    
    // 检查是否为数组
    if (Array.isArray(Arr)) {
        if (Arr.length === 0) {
            return 1;
        }
        if (Array.isArray(Arr[0])) {
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
    console.log("开始执行 CalculatePermutations");
    try {
        // 默认参数
        if (isRowMajor === undefined) {
            isRowMajor = true;
        }
        console.log("isRowMajor: " + isRowMajor);
        
        var tempArray1D;
        
        // 处理 WPS 范围对象
        if (inputArray && inputArray.Value) {
            console.log("处理 WPS 范围对象");
            inputArray = inputArray.Value;
            console.log("获取范围值成功");
        }
        
        // 检测数组维度
        console.log("检测数组维度");
        var dimension = GetArrayDimension(inputArray);
        console.log("数组维度: " + dimension);
        
        // 验证输入
        if (dimension < 1 || dimension > 2) {
            throw new Error("输入必须是一维或二维数组");
        }
        
        // 根据维度准备处理
        if (dimension === 1) {
            // 一维数组直接处理
            console.log("处理一维数组");
            tempArray1D = inputArray;
        } else {
            // 二维数组，按指定方式转换为一维
            console.log("处理二维数组");
            if (isRowMajor) {
                // 行优先
                console.log("按行优先扁平化");
                tempArray1D = FlattenArrayRowMajor(inputArray);
            } else {
                // 列优先
                console.log("按列优先扁平化");
                tempArray1D = FlattenArrayColumnMajor(inputArray);
            }
        }
        
        console.log("扁平化后的数组: " + tempArray1D.toString());
        
        // 过滤空值
        console.log("过滤空值");
        tempArray1D = tempArray1D.filter(function(item) {
            return item !== undefined && item !== null && item !== '';
        });
        console.log("过滤后的数组: " + tempArray1D.toString());
        
        // 获取数组大小
        var arrSize = tempArray1D.length;
        console.log("数组大小: " + arrSize);
        
        if (arrSize === 0) {
            throw new Error("输入数组为空");
        }
        
        // 计算排列总数：n!
        var PermCount = Factorial(arrSize);
        console.log("排列总数: " + PermCount);
        
        // 初始化结果数组
        console.log("初始化结果数组");
        var resultArray = [];
        for (var i = 0; i < PermCount; i++) {
            resultArray[i] = [];
            for (var j = 0; j < arrSize; j++) {
                resultArray[i][j] = 0;
            }
        }
        console.log("结果数组初始化完成");
        
        // 重置计数器
        k = 0;
        console.log("重置计数器: k = " + k);
        
        // 准备临时数组用于传递
        var tempArray = [];
        for (var i = 0; i < arrSize; i++) {
            tempArray[i] = tempArray1D[i];
        }
        console.log("临时数组: " + tempArray.toString());
        
        // 调用Solver函数
        console.log("调用 Solver 函数");
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
        return resultArray;
    } catch (error) {
        console.error("全排列错误: " + (error.message || String(error)));
        return null;
    }
}

// 测试函数 - 二维数组（优化版，带索引映射）
function TestPermutations2D() {
    console.log("开始执行 TestPermutations2D");
    try {
        // 开始计时
        var startTime = new Date().getTime();
        
        // 获取用户选择的单元格区域
        console.log("获取用户选择的单元格区域");
        var inputRange = Application.InputBox(
            "默认是：全排列不放回",
            "选择数据范围",
            "",
            100,
            100,
            "",
            0,
            8
        );
        
        // 检查用户是否取消选择
        if (inputRange === false) {
            console.log("用户取消选择");
            return;
        }
        
        // 检查是否成功获取范围
        if (!inputRange) {
            console.error("未选择有效范围");
            return;
        }
        
        console.log("成功获取范围，开始计算全排列");
        
        // 调用封装函数（行优先）获取原始元素排列
        var resultArr = CalculatePermutations(inputRange, true);
        
        // 输出结果
        if (resultArr === null) {
            console.error("计算错误");
            return;
        }
        
        console.log("计算成功，结果数组长度: " + resultArr.length);
        
        // 创建或获取工作表
        console.log("创建或获取工作表");
        var ws;
        try {
            ws = ThisWorkbook.Worksheets("二维数组测试结果");
            console.log("使用现有工作表");
        } catch (e) {
            console.log("创建新工作表");
            ws = ThisWorkbook.Worksheets.Add();
            ws.Name = "二维数组测试结果";
            console.log("新工作表创建成功");
        }
        
        // 获取结果数组的大小
        var rowCount = resultArr.length;
        var colCount = resultArr[0].length;
        console.log("结果数组大小: " + rowCount + "行 × " + colCount + "列");
        
        // 清空工作表
        console.log("清空工作表");
        ws.Cells.Clear();
        
        // 创建索引数组 [1,2,3,...colCount]
        var indexArr = [];
        for (var i = 0; i < colCount; i++) {
            indexArr[i] = i + 1;
        }
        console.log("创建索引数组: " + indexArr.toString());
        
        // 调用封装函数获取索引排列（使用相同的k值，确保排列顺序一致）
        var indexResultArr = CalculatePermutations(indexArr, true);
        
        // 检查索引排列是否成功
        if (indexResultArr === null) {
            console.error("索引排列计算错误");
            return;
        }
        
        console.log("索引排列计算成功");
        
        // 设置标题行
        console.log("设置标题行");
        for (var i = 0; i < colCount; i++) {
            ws.Cells(1, i + 1).Value = "元素 " + (i + 1);
            ws.Cells(1, i + 1 + colCount).Value = "映射 " + (i + 1);
        }
        console.log("标题行设置完成");
        
        // 写入原始元素排列
        console.log("开始写入原始元素排列");
        try {
            // 尝试批量写入原始元素
            var range1 = ws.Range(ws.Cells(2, 1), ws.Cells(rowCount + 1, colCount));
            console.log("创建原始元素范围: " + rowCount + "行 × " + colCount + "列");
            range1.Value = resultArr;
            console.log("原始元素批量写入成功");
        } catch (e) {
            console.error("原始元素批量写入失败，尝试逐单元格写入: " + (e.message || String(e)));
            // 逐单元格写入
            for (var i = 0; i < rowCount; i++) {
                for (var j = 0; j < colCount; j++) {
                    ws.Cells(i + 2, j + 1).Value = resultArr[i][j];
                }
            }
        }
        console.log("原始元素排列写入完成");
        
        // 写入索引排列
        console.log("开始写入索引排列");
        try {
            // 尝试批量写入索引
            var range2 = ws.Range(ws.Cells(2, colCount + 1), ws.Cells(rowCount + 1, colCount * 2));
            console.log("创建索引范围: " + rowCount + "行 × " + colCount + "列");
            range2.Value = indexResultArr;
            console.log("索引批量写入成功");
        } catch (e) {
            console.error("索引批量写入失败，尝试逐单元格写入: " + (e.message || String(e)));
            // 逐单元格写入
            for (var i = 0; i < rowCount; i++) {
                for (var j = 0; j < colCount; j++) {
                    ws.Cells(i + 2, j + 1 + colCount).Value = indexResultArr[i][j];
                }
            }
        }
        console.log("索引排列写入完成");
        
        // 自动调整列宽
        console.log("自动调整列宽");
        ws.Columns.AutoFit();
        
        // 结束计时
        var endTime = new Date().getTime();
        var elapsedTime = (endTime - startTime) / 1000;
        
        // 显示完成信息和用时
        var message = "二维数组全排列完成！\n" +
                     "排列总数: " + rowCount + "\n" +
                     "元素数量: " + colCount + "\n" +
                     "处理用时: " + elapsedTime.toFixed(3) + " 秒";
        
        console.log(message);
        
        // 激活结果工作表
        console.log("激活结果工作表");
        ws.Activate();
        
        // 简单的消息提示
        try {
            Application.MsgBox(message, 64, "全排列测试");
        } catch (e) {
            // 忽略 MsgBox 错误
        }
        
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
    }
}

// 简化的测试函数，用于快速验证
function TestSimplePermutation() {
    console.log("开始执行 TestSimplePermutation");
    try {
        // 测试简单数组
        console.log("使用测试数组: [1, 2, 3]");
        var testArray = [1, 2, 3];
        
        console.log("开始计算全排列");
        var result = CalculatePermutations(testArray, true);
        
        if (result) {
            console.log("计算成功，结果数组长度: " + result.length);
            console.log("测试结果:");
            console.log(result);
            
            // 创建测试工作表
            console.log("创建或获取测试工作表");
            var ws;
            try {
                ws = ThisWorkbook.Worksheets("测试结果");
                console.log("使用现有工作表");
            } catch (e) {
                console.log("创建新工作表");
                ws = ThisWorkbook.Worksheets.Add();
                ws.Name = "测试结果";
                console.log("新工作表创建成功");
            }
            
            console.log("清空工作表");
            ws.Cells.Clear();
            
            // 写入结果
            console.log("开始写入结果数据");
            try {
                // 尝试使用 Range.Value 批量写入
                var range = ws.Range(ws.Cells(1, 1), ws.Cells(result.length, result[0].length));
                console.log("创建范围对象: " + result.length + "行 × " + result[0].length + "列");
                
                // 转换数据格式以适应 WPS
                var dataToWrite = [];
                for (var i = 0; i < result.length; i++) {
                    dataToWrite[i] = [];
                    for (var j = 0; j < result[i].length; j++) {
                        dataToWrite[i][j] = result[i][j];
                    }
                }
                console.log("数据转换完成");
                
                // 尝试批量写入
                range.Value = dataToWrite;
                console.log("批量写入成功");
            } catch (batchError) {
                console.error("批量写入失败，尝试逐单元格写入: " + (batchError.message || String(batchError)));
                // 逐单元格写入
                for (var i = 0; i < result.length; i++) {
                    console.log("写入第 " + (i + 1) + " 行: " + result[i].toString());
                    for (var j = 0; j < result[i].length; j++) {
                        try {
                            var cell = ws.Cells(i + 1, j + 1);
                            cell.Value = result[i][j];
                            console.log("写入单元格 (" + (i + 1) + "," + (j + 1) + "): " + result[i][j]);
                        } catch (cellError) {
                            console.error("写入单元格失败 (" + (i + 1) + "," + (j + 1) + "): " + (cellError.message || String(cellError)));
                        }
                    }
                }
            }
            console.log("数据写入完成");
            
            console.log("自动调整列宽");
            ws.Columns.AutoFit();
            
            console.log("激活测试工作表");
            ws.Activate();
            
            try {
                Application.MsgBox("简单测试完成，结果已输出到 '测试结果' 工作表", 64, "测试完成");
            } catch (e) {
                // 忽略 MsgBox 错误
            }
        } else {
            console.error("测试失败，结果为 null");
        }
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
    }
}

// 初始化函数，确保代码能在 WPS 中正常运行
function Initialize() {
    console.log("全排列代码初始化完成");
    console.log("可用函数:");
    console.log("1. TestPermutations2D() - 选择范围进行全排列");
    console.log("2. TestSimplePermutation() - 使用预设数组测试");
    console.log("3. CalculatePermutations(inputArray, isRowMajor) - 核心计算函数");
}

// 自动执行初始化
Initialize();
