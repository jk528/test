Attribute VB_Name = "STAT_002_基准测试_N8到N10"
Option Explicit

' ============================================================
' STAT_002_基准测试_N8到N10.bas   v1.0
' 功能：对 N=8..10 的全排列 + 环形相邻计数进行实际计时，
'       拟合线性模型 k = μs/排列，再预估 N=11..15 的耗时
'
' 模型：耗时(ms) ≈ k × N!     k = 每次排列+环形计数+字典累加 的耗时 (μs)
'       k_us = minMs / fact(N) × 1000
'
' 算法链路：
'   步骤1：Heap 全排列生成（O(n!)，原地交换，无重复）
'   步骤2：每个排列 -> 环形相邻计数（环形：首尾相接）
'   步骤3：Scripting.Dictionary 统计 {计数值 => 出现次数}
'   步骤4：Timer 计时，拟合 k，预估更大 N
'
' 计时：VBA Timer 函数（返回秒，精度毫秒级）
' 适用：WPS / Excel VBA
' 日期：2026-08-11
' ============================================================

' ============================================================
' 一、入口 Sub
' ============================================================

' —— 主入口：运行 N=1..7 暖机，然后 N=8..10 正式测试，
'            拟合 k，预测 N=11..15，全部写入新工作表
Public Sub 演示_基准测试()
    Dim ws As Worksheet
    Dim row As Long
    Dim Ni As Long, N As Long
    Dim oneRes As Variant
    Dim benchResults() As Variant
    Dim weightedK As Double, weightSum As Double
    Dim k_us As Double, kFit As Double
    Dim perms As Double, estMs As Double, tps As Double
    Dim ratios As Variant, ratio As Long, ri As Long
    Dim vbaMs As Double, jsMs As Double

    ' --- 创建/获取工作表 ---
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("STAT_002_基准测试")
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = Worksheets.Add
        ws.Name = "STAT_002_基准测试"
    Else
        ws.Cells.Clear
    End If

    ' --- 应用设置（加速） ---
    Application.ScreenUpdating = False
    Application.Cursor = xlWait
    Application.Calculation = xlCalculationManual
    Application.EnableEvents = False

    On Error GoTo errHandler

    ReDim benchResults(8 To 10)
    row = 1

    ' --- 标题区 ---
    ws.Cells(row, 1).Value = "STAT_002 基准测试：N=8..10 实测 + N=11..15 预判"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 14
    row = row + 1
    ws.Cells(row, 1).Value = "模型：耗时(ms) ≈ k × N!    k = 每次排列+环形计数+字典累加 的耗时 (μs)"
    row = row + 1
    ws.Cells(row, 1).Value = "计时方式：VBA Timer 函数（返回秒，精度毫秒级）"
    row = row + 2

    ' --- 暖机 N=1..7 ---
    ws.Cells(row, 1).Value = "[暖机] 运行 N=1..7 ..."
    row = row + 1
    For Ni = 1 To 7
        Call benchOne(Ni)
        ws.Cells(row, 1).Value = "  N=" & Ni & " 暖机完成"
        row = row + 1
    Next Ni
    ws.Cells(row, 1).Value = "[暖机完成]"
    row = row + 2

    ' --- 正式基准 N=8..10 ---
    ws.Cells(row, 1).Value = "[正式测试] N=8..10 ..."
    row = row + 2

    For N = 8 To 10
        ws.Cells(row, 1).Value = "  正在测量 N=" & N & " (" & Format(fact(N), "#,##0") & " 排列) ..."
        oneRes = benchOne(N)
        benchResults(N) = oneRes
        ws.Cells(row, 3).Value = "完成 " & Format(oneRes(2), "0.0") & " ms (k=" & Format(oneRes(4), "0.000") & " μs/排列)"
        row = row + 1
    Next N
    row = row + 1

    ' --- 表1：实测数据汇总 ---
    ws.Cells(row, 1).Value = "── 表1：实测数据汇总 ──"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 1).Value = "N"
    ws.Cells(row, 2).Value = "排列数 N!"
    ws.Cells(row, 3).Value = "最快耗时(ms)"
    ws.Cells(row, 4).Value = "平均耗时(ms)"
    ws.Cells(row, 5).Value = "k (μs/排列)"
    ws.Rows(row).Font.Bold = True
    row = row + 1
    For N = 8 To 10
        oneRes = benchResults(N)
        ws.Cells(row, 1).Value = oneRes(0)         ' N
        ws.Cells(row, 2).Value = oneRes(1)         ' perms
        ws.Cells(row, 2).NumberFormat = "#,##0"
        ws.Cells(row, 3).Value = oneRes(2)         ' minMs
        ws.Cells(row, 3).NumberFormat = "0.0"
        ws.Cells(row, 4).Value = oneRes(3)         ' avgMs
        ws.Cells(row, 4).NumberFormat = "0.0"
        ws.Cells(row, 5).Value = oneRes(4)         ' k_us
        ws.Cells(row, 5).NumberFormat = "0.000"
        row = row + 1
    Next N
    row = row + 1

    ' --- 拟合 k（加权平均，权重 = N，N 越大越可信）---
    weightedK = 0
    weightSum = 0
    For N = 8 To 10
        k_us = benchResults(N)(4)
        weightedK = weightedK + k_us * N
        weightSum = weightSum + N
    Next N
    weightedK = weightedK / weightSum
    kFit = weightedK

    ws.Cells(row, 1).Value = "拟合 k (加权平均) = " & Format(kFit, "0.000") & " μs/每次排列"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    row = row + 1

    ' --- 表2：时间预判 N=8..15 ---
    ws.Cells(row, 1).Value = "── 表2：时间预判（基于拟合 k=" & Format(kFit, "0.000") & " μs/排列）──"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 1).Value = "N"
    ws.Cells(row, 2).Value = "排列数 N!"
    ws.Cells(row, 3).Value = "预估耗时(ms)"
    ws.Cells(row, 4).Value = "人类可读"
    ws.Cells(row, 5).Value = "吞吐量(排/秒)"
    ws.Cells(row, 6).Value = "备注"
    ws.Rows(row).Font.Bold = True
    row = row + 1
    For N = 8 To 15
        perms = fact(N)
        estMs = perms * kFit / 1000         ' μs → ms
        tps = perms / (estMs / 1000)         ' 排/秒
        ws.Cells(row, 1).Value = N
        ws.Cells(row, 2).Value = perms
        ws.Cells(row, 2).NumberFormat = "#,##0"
        ws.Cells(row, 3).Value = estMs
        ws.Cells(row, 3).NumberFormat = "#,##0.0"
        ws.Cells(row, 4).Value = humanReadable(estMs)
        ws.Cells(row, 5).Value = tps
        ws.Cells(row, 5).NumberFormat = "#,##0"
        If N >= 8 And N <= 10 Then
            ws.Cells(row, 6).Value = "实测对照"
        End If
        row = row + 1
    Next N
    row = row + 1

    ' --- 表3：VBA 环境差异预估 ---
    ws.Cells(row, 1).Value = "── 表3：环境差异预估 ──"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 1).Value = "说明：本模块 k 来自 VBA Timer 实测。JS V8 通常比 VBA 快 20~60 倍。"
    row = row + 1
    ws.Cells(row, 1).Value = "      以下用 20x / 40x / 60x 三档系数换算：VBA预估 = perms × k；JS预估 = VBA ÷ 系数。"
    row = row + 2

    ratios = Array(20, 40, 60)
    For ri = 0 To 2
        ratio = ratios(ri)
        ws.Cells(row, 1).Value = "── JS 比 VBA 快 " & ratio & " 倍 ──"
        ws.Cells(row, 1).Font.Italic = True
        row = row + 1
        ws.Cells(row, 1).Value = "N"
        ws.Cells(row, 2).Value = "排列数 N!"
        ws.Cells(row, 3).Value = "VBA预估(本机k)"
        ws.Cells(row, 4).Value = "JS预估(÷" & ratio & ")"
        ws.Rows(row).Font.Bold = True
        row = row + 1
        For N = 8 To 14
            perms = fact(N)
            vbaMs = perms * kFit / 1000          ' VBA 实测预估
            jsMs = vbaMs / ratio                  ' JS 更快
            ws.Cells(row, 1).Value = N
            ws.Cells(row, 2).Value = perms
            ws.Cells(row, 2).NumberFormat = "#,##0"
            ws.Cells(row, 3).Value = humanReadable(vbaMs)
            ws.Cells(row, 4).Value = humanReadable(jsMs)
            row = row + 1
        Next N
        row = row + 1
    Next ri

    ' --- 建议 ---
    ws.Cells(row, 1).Value = "建议：VBA 下 N≥11 时使用本模块的预判先评估，N≥13 需谨慎（可能超过 1 小时）"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' --- 美化 ---
    ws.Range(ws.Cells(1, 1), ws.Cells(row, 6)).EntireColumn.AutoFit

    ' --- 恢复设置 ---
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True

    MsgBox "基准测试完成！工作表：STAT_002_基准测试" & vbCrLf & _
           "拟合 k = " & Format(kFit, "0.000") & " μs/排列", vbInformation
    Exit Sub

errHandler:
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True
    MsgBox "运行出错：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 二、核心函数（从 JS 转换）
' ============================================================

' —— 环形相邻计数：环形首尾相接，条件 |差|=1 或 |差|=N-1（即 diff）
Private Function 环形相邻计数_arr(arr As Variant) As Long
    Dim vMin As Long, vMax As Long, diff As Long
    Dim i As Long, n As Long, count As Long
    n = UBound(arr) - LBound(arr) + 1
    If n < 2 Then Exit Function
    vMin = arr(LBound(arr)): vMax = arr(LBound(arr))
    For i = LBound(arr) To UBound(arr)
        If arr(i) < vMin Then vMin = arr(i)
        If arr(i) > vMax Then vMax = arr(i)
    Next i
    diff = vMax - vMin
    If diff = 0 Then Exit Function
    count = 0
    For i = LBound(arr) To UBound(arr)
        Dim a As Long, b As Long, d As Long
        a = arr(i)
        If i = UBound(arr) Then b = arr(LBound(arr)) Else b = arr(i + 1)
        d = Abs(a - b)
        If d = 1 Or d = diff Then count = count + 1
    Next i
    环形相邻计数_arr = count
End Function

' —— Heap 全排列遍历 + 字典统计（原地交换，O(n!)，无重复）
'     nums  - 输入一维数组（任意基）
'     freq  - Scripting.Dictionary，统计 {计数值 => 出现次数}
'     totalCount - 累计排列总数
Private Sub 全排列_HeapCallBack(nums As Variant, freq As Object, ByRef totalCount As Long)
    Dim n As Long, i As Long
    n = UBound(nums) - LBound(nums) + 1
    Dim arr() As Long
    ReDim arr(0 To n - 1)
    For i = 0 To n - 1: arr(i) = nums(LBound(nums) + i): Next i
    Dim c() As Long
    ReDim c(0 To n - 1)
    ' 第一个排列
    Dim cnt As Long
    cnt = 环形相邻计数_arr(arr)
    freq(cnt) = freq(cnt) + 1
    totalCount = totalCount + 1
    ' Heap 遍历
    i = 0
    Do While i < n
        If c(i) < i Then
            If i Mod 2 = 0 Then
                Dim tmp As Long: tmp = arr(0): arr(0) = arr(i): arr(i) = tmp
            Else
                tmp = arr(c(i)): arr(c(i)) = arr(i): arr(i) = tmp
            End If
            cnt = 环形相邻计数_arr(arr)
            If freq.Exists(cnt) Then freq(cnt) = freq(cnt) + 1 Else freq.Add cnt, 1
            totalCount = totalCount + 1
            c(i) = c(i) + 1
            i = 0
        Else
            c(i) = 0
            i = i + 1
        End If
    Loop
End Sub

' —— 阶乘（用 Double 避免溢出，13! 已超过 Long 上限）
Private Function fact(ByVal n As Long) As Double
    Dim i As Long, r As Double
    r = 1
    For i = 2 To n
        r = r * i
    Next i
    fact = r
End Function

' —— 单个 N 的计时（正式测多次取最快，N 越大次数越少）
'     返回 Array(N, perms, minMs, avgMs, k_us)
Private Function benchOne(ByVal N As Long) As Variant
    Dim nums As Variant
    nums = GenerateNums(N)

    ' 运行次数：N 越大耗时越长，减少运行次数
    Dim runs As Long
    If N <= 8 Then
        runs = 3
    ElseIf N <= 9 Then
        runs = 2
    Else
        runs = 1
    End If

    Dim timesMs() As Double
    ReDim timesMs(0 To runs - 1)

    Dim r As Long
    For r = 0 To runs - 1
        Dim freq As Object
        Set freq = CreateObject("Scripting.Dictionary")
        Dim totalCount As Long
        totalCount = 0

        Dim t0 As Double, t1 As Double
        t0 = Timer
        Call 全排列_HeapCallBack(nums, freq, totalCount)
        t1 = Timer
        timesMs(r) = (t1 - t0) * 1000        ' 秒 → 毫秒
    Next r

    ' 最快与平均
    Dim minMs As Double, avgMs As Double, sumMs As Double
    minMs = timesMs(0)
    sumMs = 0
    For r = 0 To runs - 1
        If timesMs(r) < minMs Then minMs = timesMs(r)
        sumMs = sumMs + timesMs(r)
    Next r
    avgMs = sumMs / runs

    Dim perms As Double
    perms = fact(N)
    Dim k_us As Double
    k_us = minMs / perms * 1000              ' ms/排列 × 1000 = μs/排列

    benchOne = Array(N, perms, minMs, avgMs, k_us)
End Function

' —— 人类可读时间格式
Private Function humanReadable(ByVal ms As Double) As String
    If ms < 1000 Then
        humanReadable = Format(ms, "0.0") & " ms"
        Exit Function
    End If
    Dim sec As Double
    sec = ms / 1000
    If sec < 60 Then
        humanReadable = Format(sec, "0.00") & " 秒"
        Exit Function
    End If
    Dim min As Double
    min = sec / 60
    If min < 60 Then
        humanReadable = Format(min, "0.00") & " 分钟"
        Exit Function
    End If
    Dim hr As Double
    hr = min / 60
    If hr < 24 Then
        humanReadable = Format(hr, "0.00") & " 小时"
        Exit Function
    End If
    humanReadable = Format(hr / 24, "0.00") & " 天"
End Function

' ============================================================
' 三、辅助函数
' ============================================================

' —— 生成 1..N 的一维 Long 数组（1 基）
Private Function GenerateNums(ByVal N As Long) As Variant
    Dim i As Long
    Dim result() As Long
    ReDim result(1 To N)
    For i = 1 To N
        result(i) = i
    Next i
    GenerateNums = result
End Function
