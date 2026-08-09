Attribute VB_Name = "Function_连接字符串"
Option Explicit

' ============================================================
' Function_连接字符串.bas
' 核心函数：
'   =连接(A1:E1)              →  12345              （直接拼接）
'   =连接(A1:E1, "-")         →  1-2-3-4-5          （加分隔符拼接）
'   =相邻差绝对值求和(A1:E1)   →  4                  （|1-2|+|2-3|+|3-4|+|4-5|）
'   =相邻差绝对值数组(A1:E1)   →  {1,1,1,1}          （每步差值）
' 适用：WPS / Excel VBA（导入 .bas 或粘贴到模块即可）
' 日期：2026-08-10
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
    Dim buf As String
    buf = ""

    For Each cell In rng.Cells
        If Not (skipEmpty And CStr(cell.Value) = "") Then
            If buf = "" Then
                buf = CStr(cell.Value)
            Else
                buf = buf & sep & CStr(cell.Value)
            End If
        End If
    Next cell

    连接 = buf
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

    ' 写入到区域右侧第一列，便于查看
    Set target = rng.Cells(1, 1).Offset(0, rng.Columns.count)
    target.Value = result
    target.Worksheet.Columns(target.Column).AutoFit

    MsgBox "连接完成：" & vbCrLf & result, vbInformation
    Exit Sub
errH:
    MsgBox "错误：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 二、相邻单元格：差绝对值求和
' 公式：Sum |a[i] - a[i+1]|  （相邻两数之差取绝对值，再累加）
' 示例：1 2 3 4 5  →  |1-2|+|2-3|+|3-4|+|4-5| = 1+1+1+1 = 4
' ============================================================

' —— 函数：相邻差绝对值求和
' 参数：
'   rng         - 单元格区域（任意矩形范围）
'   orderByRow  - True=按行优先（默认），False=按列优先
'   skipEmpty   - 是否跳过空单元格（默认 True）
' 返回：Double
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
' 三、内部辅助
' ============================================================

' —— 内部：把区域展开为一维数值数组（跳过空、非数字按 0）
Private Function CollectNumbers( _
    ByVal rng As Range, ByVal orderByRow As Boolean, ByVal skipEmpty As Boolean _
) As Variant
    Dim i As Long, j As Long, count As Long
    Dim result() As Double
    Dim v As Variant, vStr As String
    count = -1

    If orderByRow Then
        For i = 1 To rng.Rows.count
            For j = 1 To rng.Columns.count
                v = rng.Cells(i, j).Value
                vStr = CStr(v)
                If Not (skipEmpty And vStr = "") Then
                    count = count + 1
                    If count = 0 Then ReDim result(0 To 0) Else ReDim Preserve result(0 To count)
                    If IsNumeric(v) Then result(count) = CDbl(v) Else result(count) = 0
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
                    If count = 0 Then ReDim result(0 To 0) Else ReDim Preserve result(0 To count)
                    If IsNumeric(v) Then result(count) = CDbl(v) Else result(count) = 0
                End If
            Next i
        Next j
    End If

    If count < 0 Then CollectNumbers = Empty Else CollectNumbers = result
End Function
