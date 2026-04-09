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

// 从 WPS 范围对象中提取数据
function extractDataFromRange(range) {
    var data = [];
    try {
        // 尝试获取范围的行列数
        var rows = range.Rows.Count;
        var cols = range.Columns.Count;
        
        // 遍历所有单元格
        for (var i = 1; i <= rows; i++) {
            for (var j = 1; j <= cols; j++) {
                var cell = range.Cells(i, j);
                var value = cell.Value;
                if (value !== undefined && value !== null && value !== '') {
                    data.push(value);
                }
            }
        }
    } catch (e) {
        // 如果直接访问行列失败，尝试其他方法
        try {
            // 尝试获取范围值
            var rangeValue = range.Value;
            if (rangeValue) {
                // 处理二维数组
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
                    // 单个单元格
                    if (rangeValue !== undefined && rangeValue !== null && rangeValue !== '') {
                        data.push(rangeValue);
                    }
                }
            }
        } catch (e2) {
            console.error("提取数据失败: " + (e2.message || String(e2)));
        }
    }
    return data;
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
            // 这是一个 WPS 范围对象
            tempArray1D = extractDataFromRange(inputArray);
        } else if (inputArray && inputArray.Value) {
            // 可能是包含 Value 属性的对象
            inputArray = inputArray.Value;
            
            // 检测数组维度
            var dimension = GetArrayDimension(inputArray);
            
            // 处理不同维度的数组
            if (dimension === 1) {
                // 一维数组
                if (Array.isArray(inputArray)) {
                    tempArray1D = inputArray.filter(function(item) {
                        return item !== undefined && item !== null && item !== '';
                    });
                } else if (typeof inputArray === 'object' && inputArray.length) {
                    // 类数组对象
                    for (var i = 0; i < inputArray.length; i++) {
                        var value = inputArray[i];
                        if (value !== undefined && value !== null && value !== '') {
                            tempArray1D.push(value);
                        }
                    }
                }
            } else if (dimension === 2) {
                // 二维数组
                if (isRowMajor) {
                    tempArray1D = FlattenArrayRowMajor(inputArray);
                } else {
                    tempArray1D = FlattenArrayColumnMajor(inputArray);
                }
                // 过滤空值
                tempArray1D = tempArray1D.filter(function(item) {
                    return item !== undefined && item !== null && item !== '';
                });
            } else {
                // 尝试直接处理
                if (typeof inputArray === 'object' && inputArray.length) {
                    for (var i = 0; i < inputArray.length; i++) {
                        if (typeof inputArray[i] === 'object' && inputArray[i].length) {
                            for (var j = 0; j < inputArray[i].length; j++) {
                                var value = inputArray[i][j];
                                if (value !== undefined && value !== null && value !== '') {
                                    tempArray1D.push(value);
                                }
                            }
                        } else {
                            var value = inputArray[i];
                            if (value !== undefined && value !== null && value !== '') {
                                tempArray1D.push(value);
                            }
                        }
                    }
                }
            }
        } else if (Array.isArray(inputArray)) {
            // 普通 JavaScript 数组
            if (Array.isArray(inputArray[0])) {
                // 二维数组
                if (isRowMajor) {
                    tempArray1D = FlattenArrayRowMajor(inputArray);
                } else {
                    tempArray1D = FlattenArrayColumnMajor(inputArray);
                }
            } else {
                // 一维数组
                tempArray1D = inputArray;
            }
            // 过滤空值
            tempArray1D = tempArray1D.filter(function(item) {
                return item !== undefined && item !== null && item !== '';
            });
        }
        
        // 获取数组大小
        var arrSize = tempArray1D.length;
        if (arrSize === 0) {
            throw new Error("输入数组为空");
        }
        
        // 计算排列总数：n!
        var PermCount = Factorial(arrSize);
        
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
        
        // 返回结果
        return resultArray;
    } catch (error) {
        console.error("全排列错误: " + (error.message || String(error)));
        return null;
    }
}

// 测试函数 - 二维数组（优化版，带索引映射）
function TestPermutations2D() {
    try {
        // 开始计时
        var startTime = new Date().getTime();
        
        // 获取用户选择的单元格区域
        var inputRange = Application.InputBox(
            "请选择要进行全排列的数据范围",
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
            return;
        }
        
        // 检查是否成功获取范围
        if (!inputRange) {
            try {
                Application.MsgBox("未选择有效范围", 48, "错误");
            } catch (e) {
                console.error("未选择有效范围");
            }
            return;
        }
        
        // 调用封装函数（行优先）获取原始元素排列
        var resultArr = CalculatePermutations(inputRange, true);
        
        // 输出结果
        if (resultArr === null) {
            try {
                Application.MsgBox("计算错误", 48, "错误");
            } catch (e) {
                console.error("计算错误");
            }
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
        
        // 调用封装函数获取索引排列（使用相同的k值，确保排列顺序一致）
        var indexResultArr = CalculatePermutations(indexArr, true);
        
        // 检查索引排列是否成功
        if (indexResultArr === null) {
            try {
                Application.MsgBox("索引排列计算错误", 48, "错误");
            } catch (e) {
                console.error("索引排列计算错误");
            }
            return;
        }
        
        // 设置标题行
        ws.Cells(1, 1).Value = "序号";
        for (var i = 0; i < colCount; i++) {
            ws.Cells(1, i + 2).Value = "元素 " + (i + 1);
            ws.Cells(1, i + 2 + colCount).Value = "映射 " + (i + 1);
        }
        
        // 写入数据
        for (var i = 0; i < rowCount; i++) {
            // 写入序号
            ws.Cells(i + 2, 1).Value = i + 1;
            
            // 写入原始元素
            for (var j = 0; j < colCount; j++) {
                ws.Cells(i + 2, j + 2).Value = resultArr[i][j];
            }
            
            // 写入索引映射
            for (var j = 0; j < colCount; j++) {
                ws.Cells(i + 2, j + 2 + colCount).Value = indexResultArr[i][j];
            }
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
        
        // 简单的消息提示
        try {
            Application.MsgBox(message, 64, "全排列测试");
        } catch (e) {
            // 忽略 MsgBox 错误
        }
        
    } catch (error) {
        console.error("测试错误: " + (error.message || String(error)));
        try {
            Application.MsgBox("错误: " + (error.message || String(error)), 48, "测试错误");
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
                Application.MsgBox("简单测试完成，结果已输出到 '测试结果' 工作表", 64, "测试完成");
            } catch (e) {
                // 忽略 MsgBox 错误
            }
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
