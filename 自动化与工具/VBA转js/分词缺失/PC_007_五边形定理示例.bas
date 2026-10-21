Attribute VB_Name = "PC_007_五边形定理示例"
Option Explicit

' ============================================================
' PC_007 五边形数定理示例 - 分拆数快速计算
'
' 核心: 用欧拉五边形数定理的递推公式计算 p(n)
'   p(n) = p(n-1) + p(n-2) - p(n-5) - p(n-7) + p(n-12) + ...
'
' 功能:
'   1. 计算单个 p(n)
'   2. 生成 p(0)~p(n) 表格
'   3. 列出广义五边形数
'   4. 与递归生成法交叉验证
' ============================================================

' ============================================================
' 入口1: 计算单个分拆数 p(n)
' ============================================================
Sub 运行_计算单个分拆数()
    On Error GoTo ErrorHandler
    Dim inputStr As Variant
    Dim n As Long
    Dim result As Double

    inputStr = InputBox("输入 n (0~1000)", "计算分拆数 p(n)", "10")
    If IsEmpty(inputStr) Or inputStr = "" Then Exit Sub
    If Not IsNumeric(inputStr) Then
        MsgBox "请输入有效数字", vbExclamation
        Exit Sub
    End If

    n = CLng(inputStr)
    If n < 0 Then
        MsgBox "n 必须 >= 0", vbExclamation
        Exit Sub
    End If
    If n > 1000 Then
        MsgBox "n 过大, 建议 <= 1000 (Double 精度限制)", vbExclamation
        Exit Sub
    End If

    result = PartitionCount(n)
    MsgBox "p(" & n & ") = " & Format(result, "#,##0"), vbInformation, "五边形数定理"
    Exit Sub

ErrorHandler:
    MsgBox "错误: " & err.Description, vbExclamation
End Sub

' ============================================================
' 入口2: 生成 p(0)~p(n) 表格
' ============================================================
Sub 运行_分拆数表()
    On Error GoTo ErrorHandler
    Dim inputStr As Variant
    Dim n As Long
    Dim i As Long
    Dim ws As Worksheet
    Dim p() As Double

    inputStr = InputBox("输入 n (0~500)", "生成分拆数表 p(0)~p(n)", "30")
    If IsEmpty(inputStr) Or inputStr = "" Then Exit Sub
    If Not IsNumeric(inputStr) Then Exit Sub

    n = CLng(inputStr)
    If n < 0 Or n > 500 Then
        MsgBox "请输入 0~500 范围内的整数", vbExclamation
        Exit Sub
    End If

    ' 用五边形定理计算所有 p(0)~p(n)
    p = PartitionTable(n)

    ' 创建输出工作表
    Set ws = CreateOutputSheet("分拆数表")
    ws.Range("A1").Value = "n"
    ws.Range("B1").Value = "p(n)"
    ws.Range("C1").Value = "说明"

    For i = 0 To n
        ws.Cells(i + 2, 1).Value = i
        ws.Cells(i + 2, 2).Value = p(i)
        If i <= 10 Then
            ws.Cells(i + 2, 3).Value = GetPartitionExample(i)
        End If
    Next i

    With ws.Range("A1:C" & (n + 2))
        .Borders.LineStyle = xlContinuous
        .EntireColumn.AutoFit
        .Range("A1:C1").Font.Bold = True
    End With

    MsgBox "已生成 p(0)~p(" & n & ") 表格" & vbCrLf & _
           "p(" & n & ") = " & Format(p(n), "#,##0"), vbInformation
    Exit Sub

ErrorHandler:
    MsgBox "错误: " & err.Description, vbExclamation
End Sub

' ============================================================
' 入口3: 列出广义五边形数
' ============================================================
Sub 运行_五边形数列表()
    On Error GoTo ErrorHandler
    Dim inputStr As Variant
    Dim count As Long
    Dim ws As Worksheet
    Dim i As Long
    Dim k As Long
    Dim gk As Long
    Dim sign As Integer

    inputStr = InputBox("列出多少个广义五边形数", "五边形数", "20")
    If IsEmpty(inputStr) Or inputStr = "" Then Exit Sub
    If Not IsNumeric(inputStr) Then Exit Sub

    count = CLng(inputStr)
    If count < 1 Or count > 200 Then
        MsgBox "请输入 1~200", vbExclamation
        Exit Sub
    End If

    Set ws = CreateOutputSheet("五边形数")
    ws.Range("A1").Value = "序号"
    ws.Range("B1").Value = "k"
    ws.Range("C1").Value = "广义五边形数 g(k)"
    ws.Range("D1").Value = "递推符号"

    i = 1
    For k = 1 To count \ 2 + 1
        ' 正 k
        gk = k * (3 * k - 1) \ 2
        sign = IIf(k Mod 2 = 1, 1, -1)
        ws.Cells(i + 1, 1).Value = i
        ws.Cells(i + 1, 2).Value = k
        ws.Cells(i + 1, 3).Value = gk
        ws.Cells(i + 1, 4).Value = IIf(sign > 0, "+", "-")
        i = i + 1

        ' 负 k
        gk = k * (3 * k + 1) \ 2
        ws.Cells(i + 1, 1).Value = i
        ws.Cells(i + 1, 2).Value = -k
        ws.Cells(i + 1, 3).Value = gk
        ws.Cells(i + 1, 4).Value = IIf(sign > 0, "+", "-")
        i = i + 1

        If i > count Then Exit For
    Next k

    With ws.Range("A1:D" & i)
        .Borders.LineStyle = xlContinuous
        .EntireColumn.AutoFit
        .Range("A1:D1").Font.Bold = True
    End With

    MsgBox "已列出 " & (i - 1) & " 个广义五边形数", vbInformation
    Exit Sub

ErrorHandler:
    MsgBox "错误: " & err.Description, vbExclamation
End Sub

' ============================================================
' 入口4: 交叉验证 (五边形定理 vs 递归生成)
' ============================================================
Sub 运行_交叉验证()
    On Error GoTo ErrorHandler
    Dim inputStr As Variant
    Dim n As Integer
    Dim i As Integer
    Dim ws As Worksheet
    Dim pentagonalP As Double
    Dim recursiveP As Long

    inputStr = InputBox("验证 n 的范围 (1~25, 递归法较慢)", "交叉验证", "15")
    If IsEmpty(inputStr) Or inputStr = "" Then Exit Sub
    If Not IsNumeric(inputStr) Then Exit Sub

    n = CInt(inputStr)
    If n < 1 Or n > 25 Then
        MsgBox "请输入 1~25 (递归生成法限制)", vbExclamation
        Exit Sub
    End If

    Set ws = CreateOutputSheet("交叉验证")
    ws.Range("A1").Value = "n"
    ws.Range("B1").Value = "五边形定理 p(n)"
    ws.Range("C1").Value = "递归生成 p(n)"
    ws.Range("D1").Value = "一致?"

    For i = 0 To n
        pentagonalP = PartitionCount(i)
        recursiveP = GetAllPartitions(i).count

        ws.Cells(i + 2, 1).Value = i
        ws.Cells(i + 2, 2).Value = pentagonalP
        ws.Cells(i + 2, 3).Value = recursiveP
        If pentagonalP = recursiveP Then
            ws.Cells(i + 2, 4).Value = "OK"
            ws.Cells(i + 2, 4).Font.Color = vbGreen
        Else
            ws.Cells(i + 2, 4).Value = "MISMATCH"
            ws.Cells(i + 2, 4).Font.Color = vbRed
        End If
    Next i

    With ws.Range("A1:D" & (n + 2))
        .Borders.LineStyle = xlContinuous
        .EntireColumn.AutoFit
        .Range("A1:D1").Font.Bold = True
    End With

    MsgBox "交叉验证完成! n=0~" & n, vbInformation
    Exit Sub

ErrorHandler:
    MsgBox "错误: " & err.Description, vbExclamation
End Sub

' ============================================================
' 核心函数: 用五边形数定理计算 p(n)
'   递推: p(n) = sum( (-1)^(k-1) * [p(n-g_k) + p(n-g_{-k})] )
'   g_k = k*(3k-1)/2, g_{-k} = k*(3k+1)/2
'   时间 O(n*sqrt(n)), 空间 O(n)
' ============================================================
Function PartitionCount(ByVal n As Long) As Double
    Dim p() As Double
    Dim i As Long, k As Long
    Dim gk1 As Long, gk2 As Long
    Dim sign As Double

    If n < 0 Then
        PartitionCount = 0
        Exit Function
    End If
    If n = 0 Then
        PartitionCount = 1
        Exit Function
    End If

    ReDim p(0 To n)
    p(0) = 1

    For i = 1 To n
        p(i) = 0
        k = 1
        sign = 1

        Do
            ' g_k = k*(3k-1)/2
            gk1 = k * (3 * k - 1) \ 2
            If gk1 > i Then Exit Do
            p(i) = p(i) + sign * p(i - gk1)

            ' g_{-k} = k*(3k+1)/2
            gk2 = k * (3 * k + 1) \ 2
            If gk2 <= i Then
                p(i) = p(i) + sign * p(i - gk2)
            End If

            sign = -sign
            k = k + 1
        Loop
    Next i

    PartitionCount = p(n)
End Function

' ============================================================
' 批量计算: 返回 p(0)~p(n) 的完整数组
' ============================================================
Function PartitionTable(ByVal n As Long) As Double()
    Dim p() As Double
    Dim i As Long, k As Long
    Dim gk1 As Long, gk2 As Long
    Dim sign As Double

    ReDim p(0 To n)
    p(0) = 1

    For i = 1 To n
        p(i) = 0
        k = 1
        sign = 1
        Do
            gk1 = k * (3 * k - 1) \ 2
            If gk1 > i Then Exit Do
            p(i) = p(i) + sign * p(i - gk1)
            gk2 = k * (3 * k + 1) \ 2
            If gk2 <= i Then
                p(i) = p(i) + sign * p(i - gk2)
            End If
            sign = -sign
            k = k + 1
        Loop
    Next i

    PartitionTable = p
End Function

' ============================================================
' 辅助: 小 n 的分拆示例 (用于表格说明列)
' ============================================================
Function GetPartitionExample(ByVal n As Long) As String
    Select Case n
        Case 0: GetPartitionExample = "(空)"
        Case 1: GetPartitionExample = "1"
        Case 2: GetPartitionExample = "2 | 1+1"
        Case 3: GetPartitionExample = "3 | 2+1 | 1+1+1"
        Case 4: GetPartitionExample = "4 | 3+1 | 2+2 | 2+1+1 | 1+1+1+1"
        Case 5: GetPartitionExample = "5 | 4+1 | 3+2 | 3+1+1 | 2+2+1 | ..."
        Case 6: GetPartitionExample = "6 | 5+1 | 4+2 | 4+1+1 | 3+3 | ..."
        Case 7: GetPartitionExample = "7 | 6+1 | 5+2 | 5+1+1 | 4+3 | ..."
        Case 8: GetPartitionExample = "8 | 7+1 | 6+2 | 6+1+1 | 5+3 | ..."
        Case 9: GetPartitionExample = "9 | 8+1 | 7+2 | 7+1+1 | 6+3 | ..."
        Case 10: GetPartitionExample = "10 | 9+1 | 8+2 | 8+1+1 | 7+3 | ..."
        Case Else: GetPartitionExample = ""
    End Select
End Function

' ============================================================
' 辅助: 递归生成无序分拆 (用于交叉验证, 复用 PC_006 逻辑)
' ============================================================
Function GetAllPartitions(n As Integer) As Collection
    Dim partitions As Collection
    Set partitions = New Collection
    If n >= 0 Then GeneratePartitions n, n, "", partitions
    Set GetAllPartitions = partitions
End Function

Sub GeneratePartitions(n As Integer, max As Integer, current As String, ByRef partitions As Collection)
    Dim i As Integer
    Dim newPartition As String

    If n = 0 Then
        If current <> "" Then partitions.Add current
        Exit Sub
    End If

    For i = 1 To Application.Min(n, max)
        If current = "" Then
            newPartition = CStr(i)
        Else
            newPartition = CStr(i) & "+" & current
        End If
        GeneratePartitions n - i, i, newPartition, partitions
    Next i
End Sub

' ============================================================
' 辅助: 创建输出工作表 (复用)
' ============================================================
Function CreateOutputSheet(ByVal baseName As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(baseName)
    If Not ws Is Nothing Then
        Application.DisplayAlerts = False
        ws.Delete
        Application.DisplayAlerts = True
    End If
    On Error GoTo 0

    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
    ws.Name = baseName
    Set CreateOutputSheet = ws
End Function
