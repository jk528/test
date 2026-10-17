Attribute VB_Name = "STAT_003_预测_N1到N100"
Option Explicit

' ============================================================
' STAT_003_预测_N1到N100.bas   v1.0
' 功能：用对数阶乘预测 N=1..100 的全排列+环形相邻计数耗时，
'       输出到工作表。不实际运行全排列，只做数学预测。
'
' 核心思路：
'   耗时(秒) = N! × k_us / 1,000,000
'   其中 k_us = 每次排列的耗时（微秒），JS V8 基准 k=0.202 μs
'   大数精度用对数保证：log(N!) = Σ_{i=1..N} log(i)
'
' 对应 JS 文件：STAT_003_预测_N1到N100.js
' 日期：2026-08-11
' ============================================================

' —— 常量 ——
Private Const K_JS_US As Double = 0.202  ' μs/每次排列 (JS V8 基准)
Private Const UNIVERSE_AGE_SEC As Double = 86400# * 365# * 13.8E+9  ' 宇宙年龄≈138亿年

' ============================================================
' 一、入口 Sub
' ============================================================

' —— 主入口：生成 N=1..100 完整预测表写入新工作表
Public Sub 演示_预测N1到N100()
    Dim ws As Worksheet
    Dim row As Long

    ' --- 创建/获取工作表 ---
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("STAT_003_预测")
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = Worksheets.Add
        ws.Name = "STAT_003_预测"
    Else
        ws.Cells.Clear
    End If

    ' --- 应用设置（加速） ---
    Application.ScreenUpdating = False
    Application.Cursor = xlWait

    On Error GoTo errHandler

    row = 1

    ' --- 标题区 ---
    ws.Cells(row, 1).Value = "STAT_003 预测：N=1..100 全排列+环形相邻计数耗时"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 14
    row = row + 1
    ws.Cells(row, 1).Value = "基准 k = 0.202 μs/每次排列（基于 N=8..10 实测，JS V8 JIT 环境）"
    row = row + 1
    ws.Cells(row, 1).Value = "模型：耗时(秒) = N! × k_us / 1,000,000    对数保证精度：log(N!) = Σ log(i)"
    row = row + 2

    ' --- 6 个区间表 ---
    Call writeRangeTable(ws, row, 1, 15, "── 表1：N=1..15（实际可运行范围）──")
    Call writeRangeTable(ws, row, 16, 25, "── 表2：N=16..25（分钟 → 天）──")
    Call writeRangeTable(ws, row, 26, 40, "── 表3：N=26..40（天 → 年 → 千年）──")
    Call writeRangeTable(ws, row, 41, 60, "── 表4：N=41..60（千年 → 十亿年）──")
    Call writeRangeTable(ws, row, 61, 80, "── 表5：N=61..80（十亿年 → 万宇宙年龄）──")
    Call writeRangeTable(ws, row, 81, 100, "── 表6：N=81..100（亿亿宇宙年龄）──")

    ' --- 表7：里程碑精选 ---
    Call writeMilestoneTable(ws, row)

    ' --- 美化 ---
    ws.Range(ws.Cells(1, 1), ws.Cells(row, 6)).EntireColumn.AutoFit

    ' --- 恢复设置 ---
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault

    MsgBox "预测完成！工作表：STAT_003_预测", vbInformation
    Exit Sub

errHandler:
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault
    MsgBox "运行出错：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 二、工作表输出辅助
' ============================================================

' —— 写入一个区间表（N | N! | JS V8 | VBA×20 | VBA×40 | VBA×60）
Private Sub writeRangeTable(ws As Worksheet, ByRef row As Long, _
                            ByVal fromN As Long, ByVal toN As Long, _
                            ByVal title As String)
    Dim N As Long

    ' 区间标题
    ws.Cells(row, 1).Value = title
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' 表头
    ws.Cells(row, 1).Value = "N"
    ws.Cells(row, 2).Value = "N! (科学计数法)"
    ws.Cells(row, 3).Value = "JS V8 耗时"
    ws.Cells(row, 4).Value = "VBA × 20"
    ws.Cells(row, 5).Value = "VBA × 40"
    ws.Cells(row, 6).Value = "VBA × 60"
    ws.Rows(row).Font.Bold = True
    row = row + 1

    ' 数据行
    For N = fromN To toN
        ws.Cells(row, 1).Value = N
        ws.Cells(row, 2).Value = fmtFactSci(N)
        ws.Cells(row, 3).Value = fmtBigTime(predict(N, K_JS_US))
        ws.Cells(row, 4).Value = fmtBigTime(predict(N, K_JS_US * 20#))
        ws.Cells(row, 5).Value = fmtBigTime(predict(N, K_JS_US * 40#))
        ws.Cells(row, 6).Value = fmtBigTime(predict(N, K_JS_US * 60#))
        row = row + 1
    Next N
    row = row + 1
End Sub

' —— 写入里程碑精选表（N | JS V8耗时 | VBA×40耗时 | 说明）
Private Sub writeMilestoneTable(ws As Worksheet, ByRef row As Long)
    Dim milestones As Variant
    Dim i As Long, N As Long

    ' 区间标题
    ws.Cells(row, 1).Value = "── 表7：里程碑精选 ──"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' 表头
    ws.Cells(row, 1).Value = "N"
    ws.Cells(row, 2).Value = "JS V8 耗时"
    ws.Cells(row, 3).Value = "VBA ×40 耗时"
    ws.Cells(row, 4).Value = "说明"
    ws.Rows(row).Font.Bold = True
    row = row + 1

    ' 里程碑数据：N 与 说明 配对
    milestones = Array( _
        Array(8, "< 0.1 秒"), _
        Array(10, "< 1 秒"), _
        Array(11, "~8 秒 (JS可行)"), _
        Array(12, "~1.6 分钟"), _
        Array(13, "~21 分钟"), _
        Array(14, "~4.9 小时"), _
        Array(15, "~3.1 天"), _
        Array(16, "~49 天"), _
        Array(17, "~1.4 年"), _
        Array(18, "~25 年"), _
        Array(20, "~9,586 年"), _
        Array(21, "~20.1 万年"), _
        Array(23, "~10 亿年"), _
        Array(24, "> 170 亿年（>宇宙年龄）"), _
        Array(30, "~ 10^30 年（天文级）"), _
        Array(40, "~ 10^47 年"), _
        Array(50, "~ 10^65 年"), _
        Array(60, "~ 10^83 年"), _
        Array(69, "双精度整数溢出边界 (2^53≈9e15)"), _
        Array(80, "~ 10^113 年"), _
        Array(100, "~ 10^155 年") _
    )

    ' 数据行
    For i = LBound(milestones) To UBound(milestones)
        N = milestones(i)(0)
        ws.Cells(row, 1).Value = N
        ws.Cells(row, 2).Value = fmtBigTime(predict(N, K_JS_US))
        ws.Cells(row, 3).Value = fmtBigTime(predict(N, K_JS_US * 40#))
        ws.Cells(row, 4).Value = milestones(i)(1)
        row = row + 1
    Next i
    row = row + 1
End Sub

' ============================================================
' 三、核心数学函数（从 JS 转换）
' ============================================================

' —— 对数阶乘：log(n!) = Σ log(i)，自然对数
Private Function logFact(ByVal n As Long) As Double
    Dim s As Double, i As Long
    s = 0#
    For i = 2 To n
        s = s + Log(i)
    Next i
    logFact = s
End Function

' —— 阶乘近似值的科学计数法尾数 m (m × 10^e，m ∈ [1, 10))
Private Function factApprox_Mantissa(ByVal n As Long) As Double
    Dim log10f As Double, e As Long
    log10f = logFact(n) / Log(10#)
    e = CLng(Int(log10f))
    factApprox_Mantissa = 10# ^ (log10f - e)
End Function

' —— 阶乘近似值的指数 e
Private Function factApprox_Exp(ByVal n As Long) As Long
    Dim log10f As Double
    log10f = logFact(n) / Log(10#)
    factApprox_Exp = CLng(Int(log10f))
End Function

' —— 格式化阶乘为科学计数法字符串
'    n≤18 显示精确值，否则 m.fff × 10^e
Private Function fmtFactSci(ByVal n As Long) As String
    If n <= 18 Then
        fmtFactSci = factInt(n)
        Exit Function
    End If
    Dim m As Double, e As Long
    m = factApprox_Mantissa(n)
    e = factApprox_Exp(n)
    fmtFactSci = Format(m, "0.000") & " × 10^" & e
End Function

' —— 精确阶乘（用 String 乘法，支持大数）
'    n≤18 可用 Double 直接算，更大用字符串模拟
Private Function factInt(ByVal n As Long) As String
    If n <= 18 Then
        factInt = CStr(CDbl(factDouble(n)))
        Exit Function
    End If
    ' 字符串大数乘法
    Dim result As String
    result = "1"
    Dim i As Long
    For i = 2 To n
        result = StringMultiply(result, CStr(i))
    Next i
    factInt = result
End Function

' —— 阶乘（Double 直接计算，n≤18 精确）
Private Function factDouble(ByVal n As Long) As Double
    Dim r As Double: r = 1#
    Dim i As Long
    For i = 2 To n: r = r * i: Next i
    factDouble = r
End Function

' —— 大数字符串乘法
Private Function StringMultiply(ByVal a As String, ByVal b As String) As String
    Dim la As Long, lb As Long, i As Long, j As Long
    Dim da() As Long, db() As Long, dr() As Long
    la = Len(a): lb = Len(b)
    ReDim da(0 To la - 1): ReDim db(0 To lb - 1)
    ReDim dr(0 To la + lb - 1)
    For i = 0 To la - 1: da(i) = CLng(Mid(a, la - i, 1)): Next i
    For i = 0 To lb - 1: db(i) = CLng(Mid(b, lb - i, 1)): Next i
    For i = 0 To la - 1
        For j = 0 To lb - 1
            dr(i + j) = dr(i + j) + da(i) * db(j)
        Next j
    Next i
    For i = 0 To la + lb - 2
        If dr(i) >= 10 Then
            dr(i + 1) = dr(i + 1) + dr(i) \ 10
            dr(i) = dr(i) Mod 10
        End If
    Next i
    Dim s As String: s = ""
    Dim top As Long: top = la + lb - 1
    Do While top > 0 And dr(top) = 0: top = top - 1: Loop
    For i = top To 0 Step -1: s = s & CStr(dr(i)): Next i
    StringMultiply = s
End Function

' —— 格式化超大时间（微秒→毫秒→秒→分钟→小时→天→年→千年→百万年→十亿年→宇宙年龄倍数）
Private Function fmtBigTime(ByVal sec As Double) As String
    If sec < 0.001 Then
        fmtBigTime = Format(sec * 1000000#, "0.0") & " 微秒"
    ElseIf sec < 1 Then
        fmtBigTime = Format(sec * 1000#, "0.0") & " 毫秒"
    ElseIf sec < 60 Then
        fmtBigTime = Format(sec, "0.00") & " 秒"
    ElseIf sec < 3600 Then
        fmtBigTime = Format(sec / 60#, "0.00") & " 分钟"
    ElseIf sec < 86400 Then
        fmtBigTime = Format(sec / 3600#, "0.00") & " 小时"
    ElseIf sec < 86400# * 365 Then
        fmtBigTime = Format(sec / 86400#, "0.00") & " 天"
    ElseIf sec < 86400# * 365# * 1000 Then
        fmtBigTime = Format(sec / (86400# * 365#), "0.00") & " 年"
    ElseIf sec < 86400# * 365# * 1000000 Then
        fmtBigTime = Format(sec / (86400# * 365# * 1000#), "0.00") & " 千年"
    ElseIf sec < 86400# * 365# * 1000000000 Then
        fmtBigTime = Format(sec / (86400# * 365# * 1000000#), "0.00") & " 百万年"
    ElseIf sec < 86400# * 365# * 10000000000# Then
        fmtBigTime = Format(sec / (86400# * 365# * 1000000000#), "0.00") & " 十亿年"
    Else
        fmtBigTime = Format(sec / UNIVERSE_AGE_SEC, "0.00E+00") & " ×宇宙年龄"
    End If
End Function

' —— 预测 N 的耗时（秒）
'    sec = exp(logFact(N)) * k_us / 1e6
Private Function predict(ByVal N As Long, ByVal k_us As Double) As Double
    Dim lnFact As Double
    lnFact = logFact(N)
    predict = Exp(lnFact) * k_us / 1000000#
End Function
