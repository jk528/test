Attribute VB_Name = "Function_连接字符串"
Option Explicit

' ============================================================
' Function_连接字符串.bas  v2.0
' 核心函数（9 个）：
'   一、字符串连接
'     =连接(A1:E1)              →  12345              （直接拼接）
'     =连接(A1:E1, "-")         →  1-2-3-4-5          （加分隔符拼接）
'
'   二、相邻差（线性）
'     =相邻差绝对值求和(A1:E1)   →  4                  （|1-2|+|2-3|+|3-4|+|4-5|）
'     =相邻差绝对值数组(A1:E1)   →  {1,1,1,1}          （每步差值）
'
'   三、相邻差（环形）
'     =环形相邻差绝对值求和(A1:E1)  →  8               （线性+首尾|5-1|=4）
'     =环形相邻计数(A1:E1)          →  5               （满足条件的相邻对数）
'     =环形相邻判定数组(A1:E1)      →  {T,T,T,T,T}     （每对是否满足）
'
'   四、序列分析
'     =是否连续序列(A1:E1)       →  True               （是否连续整数）
'     =相邻差统计(A1:E1)         →  Array(max,min,avg) （统计信息）
'
' 适用：WPS / Excel VBA（导入 .bas 或粘贴到模块即可）
' 日期：2026-08-10
' ============================================================

' ============================================================
' 一、字符串连接（性能优化版：数组收集 + Join）
' ============================================================

' —— 核心函数：连接单元格区域的值
' 参数：
'   rng  - 单元格区域（任意矩形范围）
'   sep  - 分隔符，可省略；省略则直接拼接
'   skipEmpty - 是否跳过空单元格，默认 True（不产生 1--3）
Public Function 连接( _
    ByVal rng As Range, _
    Optional ByVal sep As String = "", _
    Optional ByVal skipEmpty As Boolean = True _
) As String
    Dim cell As Range
    Dim parts() As String
    Dim count As Long, i As Long
    count = 0

    ' 第一遍：计数（确定数组大小）
    For Each cell In rng.Cells
        If Not (skipEmpty And CStr(cell.Value) = "") Then
            count = count + 1
        End If
    Next cell

    If count = 0 Then
        连接 = ""
        Exit Function
    End If

    ' 第二遍：收集到数组
    ReDim parts(1 To count)
    i = 0
    For Each cell In rng.Cells
        If Not (skipEmpty And CStr(cell.Value) = "") Then
            i = i + 1
            parts(i) = CStr(cell.Value)
        End If
    Next cell

    ' 一次性 Join（性能远优于循环拼接）
    连接 = Join(parts, sep)
End Function

' —— 交互演示：选中区域 + 输入分隔符，结果写到旁边
Public Sub 演示_连接()
    Dim rng As Range
    Dim sep As String, result As String
    Dim target As Range

    On Error GoTo errH

    Set rng = Application.InputBox(prompt:="请选择要连接的单元格区域：", Type:=8, Title:="连接")
    If rng Is Nothing Then Exit Sub

    sep = InputBox("请输入分隔符（留空则直接拼接）：", "分隔符", "")

    result = 连接(rng, sep, True)

    Set target = rng.Cells(1, 1).Offset(0, rng.Columns.count)
    target.Value = result
    target.Worksheet.Columns(target.Column).AutoFit

    MsgBox "连接完成：" & vbCrLf & result, vbInformation
    Exit Sub
errH:
    MsgBox "错误：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 二、线性相邻差
' 公式：Sum |a[i] - a[i+1]|  （相邻两数之差取绝对值，再累加）
' 示例：1 2 3 4 5  →  |1-2|+|2-3|+|3-4|+|4-5| = 1+1+1+1 = 4
' ============================================================

' —— 函数：相邻差绝对值求和（线性，不环形）
Public Function 相邻差绝对值求和( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Double
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        相邻差绝对值求和 = 0
        Exit Function
    End If

    Dim n As Long, i As Long, total As Double
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        相邻差绝对值求和 = 0
        Exit Function
    End If

    total = 0
    For i = LBound(vals) To UBound(vals) - 1
        total = total + Abs(vals(i) - vals(i + 1))
    Next i

    相邻差绝对值求和 = total
End Function

' —— 函数：相邻差绝对值数组（返回每一步的差值，数组公式使用）
' 返回：一维 Double 数组（长度 = n-1）
Public Function 相邻差绝对值数组( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Variant
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        相邻差绝对值数组 = Empty
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        相邻差绝对值数组 = Empty
        Exit Function
    End If

    Dim diffs() As Double
    ReDim diffs(0 To n - 2)
    For i = LBound(vals) To UBound(vals) - 1
        diffs(i - LBound(vals)) = Abs(vals(i) - vals(i + 1))
    Next i

    相邻差绝对值数组 = diffs
End Function

' —— 演示 Sub：相邻差绝对值求和
Public Sub 演示_相邻差绝对值求和()
    Dim rng As Range
    Dim orderYN As Variant
    Dim result As Double

    On Error GoTo errH

    Set rng = Application.InputBox(prompt:="请选择要计算的单元格区域：", _
        Type:=8, Title:="相邻差绝对值求和")
    If rng Is Nothing Then Exit Sub

    orderYN = MsgBox("连接顺序：是=按行优先，否=按列优先", _
        vbQuestion + vbYesNo, "读取顺序")

    result = 相邻差绝对值求和(rng, (orderYN = vbYes), True)

    rng.Cells(1, 1).Offset(0, rng.Columns.count + 1).Value = result
    MsgBox "相邻差绝对值求和 = " & result, vbInformation
    Exit Sub
errH:
    MsgBox "错误：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 三、环形相邻（扩展"相邻"概念）
' 环形：首尾相接（最后一个→第一个 也是相邻）
' ============================================================

' —— 函数：环形相邻差绝对值求和
' 线性版 + 首尾一对的差值
' 示例：1 2 3 4 5  →  |1-2|+|2-3|+|3-4|+|4-5|+|5-1| = 1+1+1+1+4 = 8
Public Function 环形相邻差绝对值求和( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Double
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        环形相邻差绝对值求和 = 0
        Exit Function
    End If

    Dim n As Long, i As Long, total As Double
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        环形相邻差绝对值求和 = 0
        Exit Function
    End If

    total = 0
    ' 线性部分
    For i = LBound(vals) To UBound(vals) - 1
        total = total + Abs(vals(i) - vals(i + 1))
    Next i
    ' 环形部分：首尾相接
    total = total + Abs(vals(UBound(vals)) - vals(LBound(vals)))

    环形相邻差绝对值求和 = total
End Function

' —— 函数：环形相邻计数
' 规则：
'   1. 找最大值 max 和最小值 min，定义"相邻值" = max - min
'   2. 将数值序列视为环形（首尾相接）
'   3. 对每对相邻计算 |a[i] - a[i+1]|
'   4. 若差绝对值 == 1 或 == 相邻值(max-min)，则计数 +1
'   5. 返回总计数
' 示例：1 2 3 4 5  →  5
Public Function 环形相邻计数( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Long
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        环形相邻计数 = 0
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        环形相邻计数 = 0
        Exit Function
    End If

    ' 找最大值和最小值
    Dim vMin As Double, vMax As Double, diff As Double
    vMin = vals(LBound(vals))
    vMax = vals(LBound(vals))
    For i = LBound(vals) To UBound(vals)
        If vals(i) < vMin Then vMin = vals(i)
        If vals(i) > vMax Then vMax = vals(i)
    Next i
    diff = vMax - vMin   ' 相邻值

    ' 边界：所有值相同（diff=0），没有"相邻"关系，返回 0
    If diff = 0 Then
        环形相邻计数 = 0
        Exit Function
    End If

    ' 环形遍历，统计满足条件的相邻对
    Dim count As Long, a As Double, b As Double, d As Double
    count = 0
    For i = LBound(vals) To UBound(vals)
        a = vals(i)
        If i = UBound(vals) Then
            b = vals(LBound(vals))   ' 环形：最后一个→第一个
        Else
            b = vals(i + 1)
        End If
        d = Abs(a - b)
        If d = 1 Or d = diff Then
            count = count + 1
        End If
    Next i

    环形相邻计数 = count
End Function

' —— 函数：环形相邻判定数组（返回每对是否满足条件）
' 返回：一维 Boolean 数组（长度 = n）
' 示例：1 2 3 4 5  →  {True, True, True, True, True}
Public Function 环形相邻判定数组( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Variant
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        环形相邻判定数组 = Empty
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        环形相邻判定数组 = Empty
        Exit Function
    End If

    ' 找最大值和最小值
    Dim vMin As Double, vMax As Double, diff As Double
    vMin = vals(LBound(vals))
    vMax = vals(LBound(vals))
    For i = LBound(vals) To UBound(vals)
        If vals(i) < vMin Then vMin = vals(i)
        If vals(i) > vMax Then vMax = vals(i)
    Next i
    diff = vMax - vMin

    If diff = 0 Then
        Dim emptyResult() As Boolean
        ReDim emptyResult(0 To n - 1)
        For i = 0 To n - 1
            emptyResult(i) = False
        Next i
        环形相邻判定数组 = emptyResult
        Exit Function
    End If

    ' 环形遍历，判定每对
    Dim result() As Boolean
    ReDim result(0 To n - 1)
    Dim a As Double, b As Double, d As Double
    For i = LBound(vals) To UBound(vals)
        a = vals(i)
        If i = UBound(vals) Then
            b = vals(LBound(vals))
        Else
            b = vals(i + 1)
        End If
        d = Abs(a - b)
        result(i - LBound(vals)) = (d = 1 Or d = diff)
    Next i

    环形相邻判定数组 = result
End Function

' —— 演示 Sub：环形相邻计数
Public Sub 演示_环形相邻计数()
    Dim rng As Range
    Dim orderYN As Variant
    Dim result As Long

    On Error GoTo errH

    Set rng = Application.InputBox(prompt:="请选择要计算的单元格区域：", _
        Type:=8, Title:="环形相邻计数")
    If rng Is Nothing Then Exit Sub

    orderYN = MsgBox("读取顺序：是=按行优先，否=按列优先", _
        vbQuestion + vbYesNo, "读取顺序")

    result = 环形相邻计数(rng, (orderYN = vbYes), True)

    rng.Cells(1, 1).Offset(0, rng.Columns.count + 1).Value = result
    MsgBox "环形相邻计数 = " & result, vbInformation
    Exit Sub
errH:
    MsgBox "错误：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 四、序列分析
' ============================================================

' —— 函数：是否连续序列
' 判断数值是否为连续整数（排序后为 min, min+1, min+2, ..., max）
' 示例：
'   1,2,3,4,5    →  True   （连续整数）
'   5,4,3,2,1    →  True   （逆序也是连续）
'   1,3,5,2,4    →  True   （乱序也是连续）
'   1,2,4,5      →  False  （缺3）
'   1,2,2,3      →  False  （重复）
Public Function 是否连续序列( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True _
) As Boolean
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        是否连续序列 = False
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        是否连续序列 = (n = 1)  ' 单个值视为连续
        Exit Function
    End If

    ' 找最大值和最小值
    Dim vMin As Double, vMax As Double
    vMin = vals(LBound(vals))
    vMax = vals(LBound(vals))
    For i = LBound(vals) To UBound(vals)
        If vals(i) < vMin Then vMin = vals(i)
        If vals(i) > vMax Then vMax = vals(i)
    Next i

    ' 连续整数的条件：max - min + 1 = n（且无重复）
    If vMax - vMin + 1 <> n Then
        是否连续序列 = False
        Exit Function
    End If

    ' 检查是否有重复（用布尔数组标记）
    Dim seen() As Boolean
    ReDim seen(0 To n - 1)
    Dim idx As Long
    For i = LBound(vals) To UBound(vals)
        idx = CLng(vals(i) - vMin)
        If idx < 0 Or idx > n - 1 Then
            是否连续序列 = False
            Exit Function
        End If
        If seen(idx) Then
            是否连续序列 = False  ' 重复
            Exit Function
        End If
        seen(idx) = True
    Next i

    是否连续序列 = True
End Function

' —— 函数：相邻差统计
' 返回：Array(最大差, 最小差, 平均差, 差值和, 差值个数)
' 示例：1 2 3 4 5  →  Array(1, 1, 1, 4, 4)
Public Function 相邻差统计( _
    ByVal rng As Range, _
    Optional ByVal orderByRow As Boolean = True, _
    Optional ByVal skipEmpty As Boolean = True, _
    Optional ByVal circular As Boolean = False _
) As Variant
    Dim vals As Variant
    vals = CollectNumbers(rng, orderByRow, skipEmpty)

    If IsEmpty(vals) Then
        相邻差统计 = Array(0, 0, 0, 0, 0)
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(vals) - LBound(vals) + 1
    If n < 2 Then
        相邻差统计 = Array(0, 0, 0, 0, 0)
        Exit Function
    End If

    ' 计算差值个数
    Dim diffCount As Long
    If circular Then
        diffCount = n  ' 环形：n 对
    Else
        diffCount = n - 1  ' 线性：n-1 对
    End If

    Dim diffs() As Double
    ReDim diffs(0 To diffCount - 1)

    Dim a As Double, b As Double, di As Long
    di = 0
    For i = LBound(vals) To UBound(vals) - 1
        diffs(di) = Abs(vals(i) - vals(i + 1))
        di = di + 1
    Next i
    If circular Then
        diffs(di) = Abs(vals(UBound(vals)) - vals(LBound(vals)))
    End If

    ' 统计
    Dim maxDiff As Double, minDiff As Double, sumDiff As Double
    maxDiff = diffs(0)
    minDiff = diffs(0)
    sumDiff = 0
    For i = 0 To diffCount - 1
        If diffs(i) > maxDiff Then maxDiff = diffs(i)
        If diffs(i) < minDiff Then minDiff = diffs(i)
        sumDiff = sumDiff + diffs(i)
    Next i

    相邻差统计 = Array(maxDiff, minDiff, sumDiff / diffCount, sumDiff, diffCount)
End Function

' ============================================================
' 五、内部辅助（性能优化版）
' ============================================================

' —— 内部：把区域展开为一维数值数组（性能优化：先计数再 ReDim）
' 跳过空、非数字按 0 处理
Private Function CollectNumbers( _
    ByVal rng As Range, ByVal orderByRow As Boolean, ByVal skipEmpty As Boolean _
) As Variant
    Dim i As Long, j As Long, count As Long
    Dim v As Variant, vStr As String

    ' 第一遍：计数（确定数组大小，避免循环内 ReDim Preserve）
    count = 0
    If orderByRow Then
        For i = 1 To rng.Rows.count
            For j = 1 To rng.Columns.count
                v = rng.Cells(i, j).Value
                vStr = CStr(v)
                If Not (skipEmpty And vStr = "") Then
                    count = count + 1
                End If
            Next j
        Next i
    Else
        For j = 1 To rng.Columns.count
            For i = 1 To rng.Rows.count
                v = rng.Cells(i, j).Value
                vStr = CStr(v)
                If Not (skipEmpty And vStr = "") Then
                    count = count + 1
                End If
            Next i
        Next j
    End If

    If count = 0 Then
        CollectNumbers = Empty
        Exit Function
    End If

    ' 第二遍：收集（一次性 ReDim）
    Dim result() As Double
    ReDim result(0 To count - 1)
    Dim idx As Long
    idx = 0

    If orderByRow Then
        For i = 1 To rng.Rows.count
            For j = 1 To rng.Columns.count
                v = rng.Cells(i, j).Value
                vStr = CStr(v)
                If Not (skipEmpty And vStr = "") Then
                    If IsNumeric(v) Then
                        result(idx) = CDbl(v)
                    Else
                        result(idx) = 0
                    End If
                    idx = idx + 1
                End If
            Next j
        Next i
    Else
        For j = 1 To rng.Columns.count
            For i = 1 To rng.Rows.count
                v = rng.Cells(i, j).Value
                vStr = CStr(v)
                If Not (skipEmpty And vStr = "") Then
                    If IsNumeric(v) Then
                        result(idx) = CDbl(v)
                    Else
                        result(idx) = 0
                    End If
                    idx = idx + 1
                End If
            Next i
        Next j
    End If

    CollectNumbers = result
End Function
