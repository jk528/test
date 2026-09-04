'============================================================
' 四方镜子 - 标准模块（语义化命名版）
' 用途：存放核心算法函数，供 UserForm 调用
' 注意：当前连接符号 是全局变量，由窗体设置
'============================================================

Option Explicit

' 全局变量：连接符号（由窗体 TextBox1 输入赋值）
Public 当前连接符号 As String

' ============================================================
'  一、工具函数 - 循环数学
' ============================================================

' 循环索引：把任意正整数映射到 [1, 周期长度] 的循环范围内
' 就像钟表：第1格=1，第12格=12，第13格=1
Function 循环索引(序号 As Long, 周期长度 As Long) As Long
    循环索引 = ((序号 + 周期长度 - 1) Mod 周期长度) + 1
End Function

' 向上取整除法：ceil(被除数 / 除数)
' 用于计算"第几个周期"
Function 向上取整除法(被除数 As Long, 除数 As Long) As Long
    向上取整除法 = WorksheetFunction.RoundUp(被除数 / 除数, 0)
End Function

' ============================================================
'  二、工具函数 - 工作表读取
' ============================================================

Function 获取最后一列(工作表 As Worksheet) As Long
    获取最后一列 = 工作表.Cells(1, 工作表.Columns.Count).End(xlToLeft).Column
End Function

Function 获取最后一行(工作表 As Worksheet, 列号 As Long) As Long
    获取最后一行 = 工作表.Cells(工作表.Rows.Count, 列号).End(xlUp).Row
End Function

Function 批量读取区域(工作表 As Worksheet, 起始行 As Long, 起始列 As Long, _
                       结束行 As Long, 结束列 As Long) As Variant
    批量读取区域 = 工作表.Range(工作表.Cells(起始行, 起始列), 工作表.Cells(结束行, 结束列)).Value2
End Function

' ============================================================
'  三、核心算法 - 四方循环（笛卡尔积）
' ============================================================

' 计算每列的循环步长
' 步长含义：该列经过多少行才变化一次
'
' 正向循环（左列慢，右列快）：
'   第1列步长 = 1（每行都变）
'   第n列步长 = 前一列步长 × 前一列元素个数
'
' 反向循环（左列快，右列慢）：
'   第n列步长 = 总行数 / 前n列元素个数的乘积
Function 计算循环步长数组(每列元素个数 As Variant, 是否正向 As Boolean) As Variant
    Dim 列数 As Long, 列索引 As Long
    Dim 步长数组() As Long
    Dim 总行数 As Long, 累计乘积 As Long
    
    列数 = UBound(每列元素个数)
    ReDim 步长数组(1 To 列数)
    
    If 是否正向 Then
        步长数组(1) = 1
        For 列索引 = 2 To 列数
            步长数组(列索引) = 步长数组(列索引 - 1) * 每列元素个数(列索引 - 1)
        Next 列索引
    Else
        总行数 = 1
        For 列索引 = 1 To 列数
            总行数 = 总行数 * 每列元素个数(列索引)
        Next 列索引
        
        累计乘积 = 1
        For 列索引 = 1 To 列数
            累计乘积 = 累计乘积 * 每列元素个数(列索引)
            步长数组(列索引) = 总行数 / 累计乘积
        Next 列索引
    End If
    
    计算循环步长数组 = 步长数组
End Function

' 构建笛卡尔积矩阵（列优先存储：结果(列, 行)）
Function 构建笛卡尔积矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          步长数组 As Variant, 结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 该列元素数 As Long, 该列步长 As Long
    Dim 源行号 As Long
    
    列数 = UBound(每列元素个数)
    ReDim 结果(1 To 列数, 1 To 结果行数)
    
    For 列索引 = 1 To 列数
        该列元素数 = 每列元素个数(列索引)
        该列步长 = 步长数组(列索引)
        
        For 行索引 = 1 To 结果行数
            ' 核心公式：源行号 = 循环索引( 向上取整(行号/步长), 元素数 )
            源行号 = 循环索引(向上取整除法(行索引, 该列步长), 该列元素数)
            结果(列索引, 行索引) = 源数据(源行号, 列索引)
        Next 行索引
    Next 列索引
    
    构建笛卡尔积矩阵 = 结果
End Function

' 矩阵转置：列优先 → 行优先
Function 矩阵转置(矩阵 As Variant, 列数 As Long, 行数 As Long) As Variant
    Dim 结果 As Variant
    Dim 行 As Long, 列 As Long
    
    ReDim 结果(1 To 行数, 1 To 列数)
    
    For 行 = 1 To 行数
        For 列 = 1 To 列数
            结果(行, 列) = 矩阵(列, 行)
        Next 列
    Next 行
    
    矩阵转置 = 结果
End Function

' 按行合并字符串
Function 按行合并字符串(矩阵 As Variant, 列数 As Long, 行数 As Long, _
                         是否列优先 As Boolean, 连接符 As String) As Variant
    Dim 结果() As String
    Dim 行 As Long, 列 As Long
    Dim 片段数组() As String
    
    ReDim 结果(1 To 行数)
    ReDim 片段数组(1 To 列数)
    
    For 行 = 1 To 行数
        For 列 = 1 To 列数
            If 是否列优先 Then
                片段数组(列) = 矩阵(列, 行)
            Else
                片段数组(列) = 矩阵(行, 列)
            End If
        Next 列
        结果(行) = Join(片段数组, 连接符)
    Next 行
    
    按行合并字符串 = 结果
End Function

Function 计算数组乘积(数组 As Variant) As Long
    Dim i As Long
    计算数组乘积 = 1
    For i = LBound(数组) To UBound(数组)
        计算数组乘积 = 计算数组乘积 * 数组(i)
    Next i
End Function

' ============================================================
'  四、核心算法 - 双边循环（LCM独立循环）
' ============================================================

Function 计算最小公倍数(数组 As Variant) As Long
    计算最小公倍数 = WorksheetFunction.Lcm(数组)
End Function

Function 构建LCM循环矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 周期长度 As Long, 源行号 As Long
    
    列数 = UBound(每列元素个数)
    ReDim 结果(1 To 列数, 1 To 结果行数)
    
    For 列索引 = 1 To 列数
        周期长度 = 每列元素个数(列索引)
        For 行索引 = 1 To 结果行数
            源行号 = 循环索引(行索引, 周期长度)
            结果(列索引, 行索引) = 源数据(源行号, 列索引)
        Next 行索引
    Next 列索引
    
    构建LCM循环矩阵 = 结果
End Function

' ============================================================
'  五、输出 - 写入工作表
' ============================================================

Sub 写入结果(目标工作表 As Worksheet, 起始单元格 As String, _
              数据数组 As Variant, 输出行数 As Long, 输出列数 As Long, _
              是否合并模式 As Boolean)
    Dim 列格式数据 As Variant
    Dim i As Long
    
    If 是否合并模式 Then
        If 输出列数 = 1 Then
            ' 竖排合并：一维数组 → 二维单列
            ReDim 列格式数据(1 To UBound(数据数组), 1 To 1)
            For i = 1 To UBound(数据数组)
                列格式数据(i, 1) = 数据数组(i)
            Next i
            目标工作表.Range(起始单元格).Resize(输出行数, 1).Value2 = 列格式数据
        Else
            ' 横排合并：一维数组直接写入一行
            目标工作表.Range(起始单元格).Resize(1, 输出列数).Value2 = 数据数组
        End If
    Else
        目标工作表.Range(起始单元格).Resize(输出行数, 输出列数).Value2 = 数据数组
    End If
End Sub

' ============================================================
'  六、业务主函数
' ============================================================

' 执行四方循环组合（笛卡尔积）
' 参数:
'   是否正向      - True=左慢右快(正向), False=左快右慢(反向)
'   是否横向输出  - True=列×行横向输出, False=行×列竖向输出
Sub 执行四方循环(是否正向 As Boolean, 是否横向输出 As Boolean)
    Dim 原屏幕刷新状态 As Boolean
    Dim 原计算模式 As XlCalculation
    
    原屏幕刷新状态 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    On Error GoTo 错误处理
    
    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet
    
    ' 1. 获取列数
    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        MsgBox "无有效数据列", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If
    
    ' 2. 统计每列元素个数
    Dim 每列元素个数() As Long
    Dim 列 As Long, 行数 As Long
    
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列
    
    ' 3. 计算笛卡尔积总行数
    Dim 结果总行数 As Long
    结果总行数 = 计算数组乘积(每列元素个数)
    
    If 结果总行数 > 1048576 Then
        MsgBox "已超出表格限制", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If
    
    ' 4. 批量读取源数据
    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 结果总行数, 总列数)
    
    ' 5. 计算循环步长
    Dim 步长数组 As Variant
    步长数组 = 计算循环步长数组(每列元素个数, 是否正向)
    
    ' 6. 构建结果矩阵（列优先）
    Dim 结果矩阵 As Variant
    结果矩阵 = 构建笛卡尔积矩阵(原始数据, 每列元素个数, 步长数组, 结果总行数)
    
    ' 7. 准备输出数据
    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")
    
    If 是否横向输出 Then
        ' 横向输出：列 × 行
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 1
            输出列数 = 结果总行数
        Else
            输出数据 = 结果矩阵
            输出行数 = 总列数
            输出列数 = 结果总行数
        End If
    Else
        ' 竖向输出：行 × 列
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 结果总行数
            输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 结果总行数)
            输出行数 = 结果总行数
            输出列数 = 总列数
        End If
    End If
    
    ' 8. 写入结果（从F2开始）
    写入结果 当前工作表, "F2", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新状态
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    MsgBox "执行错误: " & Err.Description, vbCritical, "四方镜子"
    Resume 清理退出
End Sub

' 执行双边循环组合（LCM独立循环）
' 参数:
'   是否竖向输出 - True=行×列竖向输出, False=列×行横向输出
Sub 执行双边循环(是否竖向输出 As Boolean)
    Dim 原屏幕刷新状态 As Boolean
    Dim 原计算模式 As XlCalculation
    
    原屏幕刷新状态 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    On Error GoTo 错误处理
    
    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet
    
    ' 1. 获取列数
    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        MsgBox "无有效数据列", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If
    
    ' 2. 统计每列元素个数
    Dim 每列元素个数() As Long
    Dim 列 As Long, 行数 As Long
    
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列
    
    ' 3. 计算乘积和最小公倍数
    Dim 列数乘积 As Long, 最小公倍数 As Long
    列数乘积 = 计算数组乘积(每列元素个数)
    最小公倍数 = 计算最小公倍数(每列元素个数)
    
    If 最小公倍数 > 1048576 Then
        MsgBox "已超出表格限制", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If
    
    Dim 是否完整循环 As Boolean
    是否完整循环 = (列数乘积 = 最小公倍数)
    
    ' 4. 批量读取源数据
    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 最小公倍数, 总列数)
    
    ' 5. 构建LCM循环矩阵
    Dim 结果矩阵 As Variant
    结果矩阵 = 构建LCM循环矩阵(原始数据, 每列元素个数, 最小公倍数)
    
    ' 6. 新建工作表（在"重复字"工作表之后）
    Dim 新工作表 As Worksheet
    On Error Resume Next
    Set 新工作表 = Worksheets.Add(After:=Worksheets("重复字"))
    If Err.Number <> 0 Then
        Set 新工作表 = Worksheets.Add
    End If
    On Error GoTo 错误处理
    
    If 是否完整循环 Then
        新工作表.Name = "完整_" & 最小公倍数 & "sheet" & Sheets.Count
    Else
        新工作表.Name = "残缺_" & 列数乘积 & "|" & 最小公倍数 & "sheet" & Sheets.Count
    End If
    
    ' 7. 准备输出数据
    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")
    
    If 是否竖向输出 Then
        ' 竖向输出：行 × 列
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 最小公倍数
            输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 最小公倍数)
            输出行数 = 最小公倍数
            输出列数 = 总列数
        End If
    Else
        ' 横向输出：列 × 行
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 1
            输出列数 = 最小公倍数
        Else
            输出数据 = 结果矩阵
            输出行数 = 总列数
            输出列数 = 最小公倍数
        End If
    End If
    
    ' 8. 写入结果（从A1开始）
    写入结果 新工作表, "A1", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新状态
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    MsgBox "执行错误: " & Err.Description, vbCritical, "四方镜子"
    Resume 清理退出
End Sub
