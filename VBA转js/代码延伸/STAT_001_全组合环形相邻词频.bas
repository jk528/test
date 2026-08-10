Attribute VB_Name = "STAT_001_全组合环形相邻词频"
Option Explicit

' ============================================================
' STAT_001_全组合环形相邻词频.bas   v1.0
' 功能：对数字集合的全部全排列，计算"环形相邻计数"，统计频率分布
'
' 算法链路：
'   步骤1：Heap 全排列生成（O(n!)，原地交换，无重复）
'   步骤2：每个排列 -> 环形相邻计数（环形：首尾相接）
'   步骤3：Scripting.Dictionary 统计 {计数值 => 出现次数}
'   步骤4：输出到工作表（可选项）
'
' 示例（N=5，120 种排列）：
'   计数=0  →  频率 10
'   计数=2  →  频率 50
'   计数=3  →  频率 50
'   计数=5  →  频率 10
'   合计    →  120  (= 5!)
'
' 适用：WPS / Excel VBA
' 日期：2026-08-11
' ============================================================

' ============================================================
' 一、对外 API（4 个核心函数 + 3 个入口 Sub）
' ============================================================

' —— 函数：全排列环形相邻词频统计（直接传入一维数组，返回 3 列结果数组）
' 返回：二维数组  [[计数值, 出现次数, 占比], ...]（按计数值升序）
' 参数：
'   nums       - 一维数值数组（如 Array(1,2,3,4,5)）
'   outputCols - 可选：是否输出占比列（默认 True，3列；False 则 2列）
Public Function 全排列环形词频统计( _
    ByVal nums As Variant, _
    Optional ByVal outputCols As Boolean = True _
) As Variant
    Dim freq As Object  ' Scripting.Dictionary
    Set freq = CreateObject("Scripting.Dictionary")

    Dim totalCount As Long
    totalCount = 0

    ' --- 步骤 1+2：全排列 + 环形相邻计数 + 累加字典 ---
    Call 全排列_HeapCallBack(nums, freq, totalCount)

    ' --- 步骤 3：字典 -> 二维数组（按计数值升序） ---
    全排列环形词频统计 = DictToSortedArray(freq, totalCount, outputCols)
End Function

' —— 函数：全排列环形词频统计（从单元格区域读取）
' 返回：同上二维数组；区域为空时返回 Empty
Public Function 全排列环形词频统计_区域( _
    ByVal rng As Range, _
    Optional ByVal outputCols As Boolean = True _
) As Variant
    Dim nums As Variant
    nums = RangeToNumberArray(rng)
    If IsEmpty(nums) Then
        全排列环形词频统计_区域 = Empty
        Exit Function
    End If
    全排列环形词频统计_区域 = 全排列环形词频统计(nums, outputCols)
End Function

' —— 函数：单个排列的环形相邻计数（VBA 数组版，不经过单元格）
' 逻辑与 Function_连接字符串.bas 中的 环形相邻计数 完全一致
Public Function 环形相邻计数_数组(ByVal arr As Variant) As Long
    If IsEmpty(arr) Then
        环形相邻计数_数组 = 0
        Exit Function
    End If

    Dim n As Long, i As Long
    n = UBound(arr) - LBound(arr) + 1
    If n < 2 Then
        环形相邻计数_数组 = 0
        Exit Function
    End If

    ' 找最大值和最小值
    Dim vMin As Double, vMax As Double, diff As Double
    vMin = arr(LBound(arr))
    vMax = arr(LBound(arr))
    For i = LBound(arr) To UBound(arr)
        If arr(i) < vMin Then vMin = arr(i)
        If arr(i) > vMax Then vMax = arr(i)
    Next i
    diff = vMax - vMin

    ' 边界：所有值相同
    If diff = 0 Then
        环形相邻计数_数组 = 0
        Exit Function
    End If

    ' 环形遍历
    Dim count As Long, a As Double, b As Double, d As Double
    count = 0
    For i = LBound(arr) To UBound(arr)
        a = arr(i)
        If i = UBound(arr) Then
            b = arr(LBound(arr))
        Else
            b = arr(i + 1)
        End If
        d = Abs(a - b)
        If d = 1 Or d = diff Then
            count = count + 1
        End If
    Next i

    环形相邻计数_数组 = count
End Function

' —— 函数：获取全排列总数（= N!，用于验证合计）
Public Function 全排列总数(ByVal N As Long) As Double
    Dim i As Long, res As Double
    res = 1
    For i = 2 To N
        res = res * i
    Next i
    全排列总数 = res
End Function

' ============================================================
' 二、入口 Sub（直接运行，结果写入工作表）
' ============================================================

' —— 主入口 1：交互输入 N，生成 1..N 的词频统计表写入工作表
' 输出工作表名：环形相邻词频_N{N}（如 环形相邻词频_N5）
Public Sub 演示_生成环形相邻词频表()
    Dim NStr As String, N As Long
    NStr = InputBox("请输入 N（生成 1..N 的全排列）：", "环形相邻词频统计", "5")
    If NStr = "" Then Exit Sub
    If Not IsNumeric(NStr) Then
        MsgBox "请输入数字", vbExclamation
        Exit Sub
    End If
    N = CLng(NStr)
    If N < 1 Then
        MsgBox "N 必须 >= 1", vbExclamation
        Exit Sub
    End If
    If N > 8 Then
        If MsgBox("N>8 时总数 >= 40320，可能耗时较长，是否继续？", vbYesNo + vbQuestion) <> vbYes Then
            Exit Sub
        End If
    End If

    Dim nums As Variant
    nums = GenerateNums(N)

    Dim result As Variant
    result = 全排列环形词频统计(nums, True)

    Call WriteResultToSheet(result, N, "环形相邻词频_N" & CStr(N))
End Sub

' —— 主入口 2：从单元格区域读取数字集合，输出词频
' 例：选中 A1:E1 = 1 2 3 4 5，运行本 Sub
Public Sub 演示_从区域生成词频()
    Dim rng As Range
    On Error GoTo errH
    Set rng = Application.InputBox(prompt:="请选择数字集合（矩形区域，数字按行优先读取）：", _
        Type:=8, Title:="环形相邻词频统计")
    If rng Is Nothing Then Exit Sub

    Dim nums As Variant
    nums = RangeToNumberArray(rng)
    If IsEmpty(nums) Then
        MsgBox "没有读取到有效数字", vbExclamation
        Exit Sub
    End If

    Dim N As Long
    N = UBound(nums) - LBound(nums) + 1

    Dim result As Variant
    result = 全排列环形词频统计(nums, True)

    Call WriteResultToSheet(result, N, "环形相邻词频_区域")
    Exit Sub
errH:
    MsgBox "错误：" & Err.Description, vbExclamation
End Sub

' —— 主入口 3：批量生成 N=1..MaxN 的词频统计表（对比分析）
' 输出到一张工作表：列 = N，行 = 计数值
Public Sub 批量生成_N1到N()
    Dim maxNStr As String, maxN As Long
    maxNStr = InputBox("请输入最大 N（批量生成 N=1..N 的对比表）：", "批量环形词频", "7")
    If maxNStr = "" Then Exit Sub
    If Not IsNumeric(maxNStr) Then
        MsgBox "请输入数字", vbExclamation
        Exit Sub
    End If
    maxN = CLng(maxNStr)
    If maxN < 1 Then
        MsgBox "N 必须 >= 1", vbExclamation
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.Cursor = xlWait

    ' --- 收集每个 N 的频率 Map ---
    Dim allFreqs() As Object   ' 每个 N 对应一个 Dictionary
    ReDim allFreqs(1 To maxN)
    Dim maxCount As Long
    maxCount = 0

    Dim N As Long
    For N = 1 To maxN
        Dim freq As Object
        Set freq = CreateObject("Scripting.Dictionary")
        Dim totalCount As Long
        totalCount = 0
        Call 全排列_HeapCallBack(GenerateNums(N), freq, totalCount)
        Set allFreqs(N) = freq
        If N > maxCount Then maxCount = N
    Next N

    ' --- 写入工作表 ---
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("环形相邻词频_批量对比")
    If Not ws Is Nothing Then
        ws.Cells.Clear
    Else
        Set ws = ThisWorkbook.Worksheets.Add
        ws.Name = "环形相邻词频_批量对比"
    End If
    On Error GoTo 0

    ' 表头
    ws.Cells(1, 1).Value = "计数值"
    For N = 1 To maxN
        ws.Cells(1, 1 + N).Value = "N=" & CStr(N) & " (共" & CStr(CLng(全排列总数(N))) & ")"
    Next N

    ' 数据行
    Dim cnt As Long, r As Long
    r = 2
    For cnt = 0 To maxCount
        ws.Cells(r, 1).Value = cnt
        For N = 1 To maxN
            If allFreqs(N).Exists(cnt) Then
                ws.Cells(r, 1 + N).Value = allFreqs(N)(cnt)
            End If
        Next N
        r = r + 1
    Next cnt

    ' 合计行
    ws.Cells(r, 1).Value = "合计"
    For N = 1 To maxN
        ws.Cells(r, 1 + N).Formula = "=SUM(R" & CStr(2) & "C:R" & CStr(r - 1) & "C)"
    Next N

    ' 美化
    ws.Range(ws.Cells(1, 1), ws.Cells(r, 1 + maxN)).EntireColumn.AutoFit
    ws.Rows(1).Font.Bold = True
    ws.Rows(r).Font.Bold = True

    Application.ScreenUpdating = True
    Application.Cursor = xlDefault
    MsgBox "批量生成完成！工作表：环形相邻词频_批量对比", vbInformation
End Sub

' ============================================================
' 三、核心算法 1：Heap 全排列（原地交换 + 回调字典累加）
' 时间：O(n!)，空间：O(n)，无重复排列
' ============================================================

Private Sub 全排列_HeapCallBack( _
    ByVal nums As Variant, _
    ByRef freq As Object, _
    ByRef totalCount As Long _
)
    Dim n As Long, i As Long, j As Long
    n = UBound(nums) - LBound(nums) + 1

    ' Heap 算法的 c 数组（0基）
    Dim c() As Long
    ReDim c(0 To n - 1)
    Dim k As Long
    For k = 0 To n - 1
        c(k) = 0
    Next k

    ' 初始排列
    Call ProcessOnePerm(nums, freq, totalCount)

    ' 原地变量（避免每次 Dim）
    Dim tmp As Double
    i = 0
    Do While i < n
        If c(i) < i Then
            ' 偶数 i：交换 0 和 i；奇数 i：交换 c(i) 和 i
            If i Mod 2 = 0 Then
                j = 0
            Else
                j = c(i)
            End If
            ' 对应到 1 基下标（如果 nums 是 1 基）
            Dim ii As Long, jj As Long
            ii = LBound(nums) + i
            jj = LBound(nums) + j
            tmp = nums(ii)
            nums(ii) = nums(jj)
            nums(jj) = tmp

            Call ProcessOnePerm(nums, freq, totalCount)

            c(i) = c(i) + 1
            i = 0
        Else
            c(i) = 0
            i = i + 1
        End If
    Loop
End Sub

' —— 处理单个排列：计算环形相邻计数，累加到字典
Private Sub ProcessOnePerm( _
    ByVal arr As Variant, _
    ByRef freq As Object, _
    ByRef totalCount As Long _
)
    Dim cnt As Long
    cnt = 环形相邻计数_数组(arr)
    If freq.Exists(cnt) Then
        freq(cnt) = freq(cnt) + 1
    Else
        freq.Add cnt, 1
    End If
    totalCount = totalCount + 1
End Sub

' ============================================================
' 四、核心算法 2：字典 -> 排序二维数组
' ============================================================

Private Function DictToSortedArray( _
    ByVal freq As Object, _
    ByVal totalCount As Long, _
    ByVal outputCols As Boolean _
) As Variant
    ' 先把 key 排序（冒泡，key 不多）
    Dim keys As Variant
    keys = freq.Keys
    Dim n As Long, i As Long, j As Long, tmp As Variant
    n = UBound(keys) - LBound(keys) + 1

    For i = LBound(keys) To UBound(keys) - 1
        For j = i + 1 To UBound(keys)
            If keys(i) > keys(j) Then
                tmp = keys(i)
                keys(i) = keys(j)
                keys(j) = tmp
            End If
        Next j
    Next i

    ' 构建结果数组
    Dim cols As Long
    If outputCols Then cols = 3 Else cols = 2

    Dim result() As Variant
    ReDim result(1 To n, 1 To cols)

    Dim r As Long
    r = 1
    For i = LBound(keys) To UBound(keys)
        result(r, 1) = keys(i)           ' 计数值
        result(r, 2) = freq(keys(i))     ' 出现次数
        If cols = 3 Then
            result(r, 3) = freq(keys(i)) / totalCount   ' 占比
        End If
        r = r + 1
    Next i

    DictToSortedArray = result
End Function

' ============================================================
' 五、辅助：输入输出
' ============================================================

' —— 单元格区域 -> 一维数字数组（跳过空和非数字）
Private Function RangeToNumberArray(ByVal rng As Range) As Variant
    Dim count As Long, i As Long, j As Long
    Dim v As Variant

    ' 计数
    count = 0
    For i = 1 To rng.Rows.count
        For j = 1 To rng.Columns.count
            v = rng.Cells(i, j).Value
            If CStr(v) <> "" And IsNumeric(v) Then
                count = count + 1
            End If
        Next j
    Next i

    If count = 0 Then
        RangeToNumberArray = Empty
        Exit Function
    End If

    ' 收集
    Dim result() As Double
    ReDim result(1 To count)
    Dim idx As Long
    idx = 0
    For i = 1 To rng.Rows.count
        For j = 1 To rng.Columns.count
            v = rng.Cells(i, j).Value
            If CStr(v) <> "" And IsNumeric(v) Then
                idx = idx + 1
                result(idx) = CDbl(v)
            End If
        Next j
    Next i

    RangeToNumberArray = result
End Function

' —— 生成 1..N 的一维数字数组
Private Function GenerateNums(ByVal N As Long) As Variant
    Dim i As Long
    Dim result() As Double
    ReDim result(1 To N)
    For i = 1 To N
        result(i) = i
    Next i
    GenerateNums = result
End Function

' —— 把词频结果写入新工作表
Private Sub WriteResultToSheet( _
    ByVal result As Variant, _
    ByVal N As Long, _
    ByVal sheetName As String _
)
    If IsEmpty(result) Then
        MsgBox "没有数据", vbExclamation
        Exit Sub
    End If

    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    If Not ws Is Nothing Then
        ws.Cells.Clear
    Else
        Set ws = ThisWorkbook.Worksheets.Add
        ws.Name = sheetName
    End If
    On Error GoTo 0

    Dim total As Double
    total = 全排列总数(N)

    ' 表头
    ws.Cells(1, 1).Value = "计数值"
    ws.Cells(1, 2).Value = "出现次数"
    ws.Cells(1, 3).Value = "占比"
    ws.Rows(1).Font.Bold = True

    ' 数据
    Dim rows As Long, r As Long
    rows = UBound(result, 1) - LBound(result, 1) + 1
    For r = 1 To rows
        ws.Cells(1 + r, 1).Value = result(r, 1)
        ws.Cells(1 + r, 2).Value = result(r, 2)
        If UBound(result, 2) >= 3 Then
            ws.Cells(1 + r, 3).Value = result(r, 3)
            ws.Cells(1 + r, 3).NumberFormat = "0.0%"
        End If
    Next r

    ' 合计
    ws.Cells(1 + rows + 1, 1).Value = "合计"
    ws.Cells(1 + rows + 1, 2).Formula = "=SUM(R[-" & CStr(rows) & "]C:R[-1]C)"
    ws.Cells(1 + rows + 1, 3).Formula = "=SUM(R[-" & CStr(rows) & "]C:R[-1]C)"
    ws.Rows(1 + rows + 1).Font.Bold = True

    ' 标题
    ws.Cells(1, 5).Value = "数字集合 N=" & CStr(N)
    ws.Cells(2, 5).Value = "全排列总数 = " & CStr(CLng(total))

    ws.Range("A:C").EntireColumn.AutoFit
    ws.Range("E:E").EntireColumn.AutoFit

    MsgBox "生成完成！工作表：" & sheetName & vbCrLf & _
        "全排列 " & CStr(CLng(total)) & " 种", vbInformation
End Sub
