Attribute VB_Name = "modUtil"
Option Explicit

' ============================================================
' 通用工具：工作表引用、颜色、配置读取、日志、排序
' 说明：工作表名固定，请勿重命名；如重命名需同步修改本模块。
' ============================================================

Public Function SheetHelp() As Worksheet
    Set SheetHelp = ThisWorkbook.Worksheets("使用说明")
End Function

Public Function SheetInput() As Worksheet
    Set SheetInput = ThisWorkbook.Worksheets("正文输入")
End Function

Public Function SheetConfig() As Worksheet
    Set SheetConfig = ThisWorkbook.Worksheets("配置")
End Function

Public Function SheetLexicon() As Worksheet
    Set SheetLexicon = ThisWorkbook.Worksheets("词表")
End Function

Public Function SheetResults() As Worksheet
    Set SheetResults = ThisWorkbook.Worksheets("逐句结果")
End Function

Public Function SheetSummary() As Worksheet
    Set SheetSummary = ThisWorkbook.Worksheets("汇总统计")
End Function

Public Function SheetChartData() As Worksheet
    Set SheetChartData = ThisWorkbook.Worksheets("图表数据")
End Function

Public Function SheetChart() As Worksheet
    Set SheetChart = ThisWorkbook.Worksheets("图表")
End Function

Public Function SheetPreview() As Worksheet
    Set SheetPreview = ThisWorkbook.Worksheets("上色预览")
End Function

Public Function SheetTop() As Worksheet
    Set SheetTop = ThisWorkbook.Worksheets("词频Top")
End Function

Public Function SheetLog() As Worksheet
    Set SheetLog = ThisWorkbook.Worksheets("运行日志")
End Function

Public Function SheetSample() As Worksheet
    Set SheetSample = ThisWorkbook.Worksheets("示例原文")
End Function

' ---------- 值转换 ----------

Public Function SVal(ByVal v As Variant) As String
    If IsError(v) Then
        SVal = ""
    ElseIf IsNull(v) Then
        SVal = ""
    ElseIf IsEmpty(v) Then
        SVal = ""
    Else
        SVal = CStr(v)
    End If
End Function

Public Function ToBool(ByVal v As Variant) As Boolean
    Dim s As String
    s = LCase(Trim(SVal(v)))
    ToBool = (s = "是" Or s = "true" Or s = "1" Or s = "yes" Or s = "y" Or s = "开" Or s = "启用")
End Function

Public Function ToLong(ByVal v As Variant, ByVal d As Long) As Long
    On Error Resume Next
    If IsNumeric(v) Then
        ToLong = CLng(v)
    Else
        ToLong = d
    End If
    On Error GoTo 0
End Function

' ---------- 颜色 ----------

Public Function HexToRGB(ByVal s As String) As Long
    Dim t As String, i As Long, ch As String
    Dim r As Long, g As Long, b As Long
    t = Replace(Trim(s), "#", "")
    If Len(t) <> 6 Then
        HexToRGB = -1
        Exit Function
    End If
    For i = 1 To 6
        ch = Mid(t, i, 1)
        If InStr("0123456789ABCDEFabcdef", ch) = 0 Then
            HexToRGB = -1
            Exit Function
        End If
    Next i
    r = CLng("&H" & Mid(t, 1, 2))
    g = CLng("&H" & Mid(t, 3, 2))
    b = CLng("&H" & Mid(t, 5, 2))
    HexToRGB = RGB(r, g, b)
End Function

Public Function RGBToHex(ByVal c As Long) As String
    Dim r As Long, g As Long, b As Long
    r = c Mod 256
    g = (c \ 256) Mod 256
    b = (c \ 65536) Mod 256
    RGBToHex = "#" & Right("0" & Hex(r), 2) & Right("0" & Hex(g), 2) & Right("0" & Hex(b), 2)
End Function

Public Function LightenColor(ByVal c As Long, ByVal pct As Long) As Long
    Dim r As Long, g As Long, b As Long, f As Double
    If pct < 0 Then pct = 0
    If pct > 100 Then pct = 100
    f = pct / 100
    r = c Mod 256
    g = (c \ 256) Mod 256
    b = (c \ 65536) Mod 256
    r = CLng(r + (255 - r) * f)
    g = CLng(g + (255 - g) * f)
    b = CLng(b + (255 - b) * f)
    LightenColor = RGB(r, g, b)
End Function

' ---------- 应用状态 ----------

Public Sub AppBusy(ByVal busy As Boolean)
    If busy Then
        Application.ScreenUpdating = False
        Application.Calculation = xlCalculationManual
        Application.EnableEvents = False
    Else
        Application.ScreenUpdating = True
        Application.Calculation = xlCalculationAutomatic
        Application.EnableEvents = True
    End If
End Sub

Public Sub SetStatus(ByVal s As String)
    On Error Resume Next
    Application.StatusBar = s
    On Error GoTo 0
End Sub

' ---------- 日志 ----------

Public Sub LogClear()
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = SheetLog()
    ws.Cells.Clear
    ws.Cells(1, 1).Value = "时间"
    ws.Cells(1, 2).Value = "阶段"
    ws.Cells(1, 3).Value = "级别"
    ws.Cells(1, 4).Value = "信息"
    ws.Range("A1:D1").Font.Bold = True
    ws.Range("A1:D1").Interior.Color = RGB(31, 78, 121)
    ws.Range("A1:D1").Font.Color = RGB(255, 255, 255)
    On Error GoTo 0
End Sub

Public Sub LogMsg(ByVal stage As String, ByVal msg As String, Optional ByVal level As String = "INFO")
    Dim ws As Worksheet, r As Long
    On Error Resume Next
    Set ws = SheetLog()
    r = ws.Cells(ws.rows.Count, 1).End(xlUp).Row + 1
    If r < 2 Then r = 2
    ws.Cells(r, 1).Value = Format(Now, "yyyy-mm-dd hh:mm:ss")
    ws.Cells(r, 2).Value = stage
    ws.Cells(r, 3).Value = level
    ws.Cells(r, 4).Value = msg
    If level = "ERROR" Then
        ws.Cells(r, 3).Font.Color = RGB(192, 0, 0)
        ws.Cells(r, 3).Font.Bold = True
    ElseIf level = "WARN" Then
        ws.Cells(r, 3).Font.Color = RGB(191, 143, 0)
    End If
    On Error GoTo 0
End Sub

Public Function LogCountErrors() As Long
    Dim ws As Worksheet, i As Long, n As Long
    On Error Resume Next
    Set ws = SheetLog()
    n = 0
    For i = 2 To ws.Cells(ws.rows.Count, 1).End(xlUp).Row
        If SVal(ws.Cells(i, 3).Value) = "ERROR" Then n = n + 1
    Next
    LogCountErrors = n
    On Error GoTo 0
End Function

' ---------- 字典排序 ----------

' 返回前 n 个键值（按值降序），写入 outKeys/outVals，返回实际个数
Public Function DictTopKeys(ByVal d As Object, ByVal n As Long, ByRef outKeys() As String, ByRef outVals() As Long) As Long
    Dim k As Long, i As Long, j As Long, tmpS As String, tmpV As Long
    Dim cnt As Long
    cnt = d.Count
    If cnt = 0 Or n <= 0 Then
        DictTopKeys = 0
        Exit Function
    End If
    If n > cnt Then n = cnt
    ReDim outKeys(1 To cnt)
    ReDim outVals(1 To cnt)
    k = 0
    Dim v As Variant
    For Each v In d.Keys
        k = k + 1
        outKeys(k) = CStr(v)
        outVals(k) = CLng(d(v))
    Next
    ' 插入排序（降序），相同值保持原键序
    For i = 2 To cnt
        tmpS = outKeys(i)
        tmpV = outVals(i)
        j = i - 1
        Do While j >= 1
            If outVals(j) < tmpV Then
                outKeys(j + 1) = outKeys(j)
                outVals(j + 1) = outVals(j)
                j = j - 1
            Else
                Exit Do
            End If
        Loop
        outKeys(j + 1) = tmpS
        outVals(j + 1) = tmpV
    Next i
    DictTopKeys = n
End Function

Public Function FormatPct(ByVal part As Long, ByVal total As Long) As String
    If total <= 0 Then
        FormatPct = "0.0%"
    Else
        FormatPct = Format(part / total, "0.0%")
    End If
End Function

Public Sub ClearSheet(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Cells.Clear
    ws.Cells.Interior.ColorIndex = xlNone
    On Error GoTo 0
End Sub

Public Sub StyleHeader(ByVal ws As Worksheet, ByVal cols As Long, ByVal rowNo As Long)
    With ws.Range(ws.Cells(rowNo, 1), ws.Cells(rowNo, cols))
        .Font.Bold = True
        .Font.Color = RGB(255, 255, 255)
        .Interior.Color = RGB(31, 78, 121)
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With
    ws.rows(rowNo).RowHeight = 22
End Sub
