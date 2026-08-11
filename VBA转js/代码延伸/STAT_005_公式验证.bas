Attribute VB_Name = "STAT_005_公式验证"
Option Explicit

' ============================================================
' STAT_005_公式验证.bas   v1.0
' 功能：验证环形相邻词频三角表 T(N,k) 的闭式公式定理
'
' 验证定理：
'   定理1：T(N,N) = 2N（满分情况）
'   定理2：E(N,N-1) = N × E(N,N)（容斥中间量关系）
'   定理3：T(N,N-1) = 0（空缺情况）
'   容斥反推：T(N,k) = Σ_{j=k..N} (-1)^{j-k} × C(j,k) × E(N,j)
'
' 算法链路：
'   1. Heap 全排列生成 1..N 的所有排列
'   2. 每个排列计算环形相邻计数（双向 |差|=1 或 |差|=N-1）
'   3. 统计 T(N,k) 频率字典
'   4. 由 T(N,k) 计算 E(N,j) = Σ_{k≥j} C(k,j)·T(N,k)
'   5. 验证定理 1/2/3 及容斥反推公式
'   6. 与 A180188（仅升序环形相邻）公式对比
'
' 对应 JS 文件：STAT_005_公式验证.js
' 适用：WPS / Excel VBA
' 日期：2026-08-11
' ============================================================

' ============================================================
' 一、入口 Sub
' ============================================================

' —— 主入口：对 N=4..8 执行公式验证，结果写入工作表
Public Sub 演示_公式验证()
    Dim ws As Worksheet

    ' --- 创建/获取工作表 ---
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("STAT_005_公式验证")
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = Worksheets.Add
        ws.Name = "STAT_005_公式验证"
    Else
        ws.Cells.Clear
    End If

    ' --- 应用设置（加速） ---
    Application.ScreenUpdating = False
    Application.Cursor = xlWait

    On Error GoTo errHandler

    Dim row As Long
    row = 1

    ' --- 总标题 ---
    ws.Cells(row, 1).Value = "STAT_005 闭式公式与定理验证 (N=4..8 枚举实测)"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 14
    row = row + 1
    ws.Cells(row, 1).Value = "定理1: T(N,N)=2N  |  定理2: E(N,N-1)=N×E(N,N)  |  定理3: T(N,N-1)=0  |  容斥反推: T(N,k)=Σ(-1)^(j-k)·C(j,k)·E(j)"
    row = row + 2

    ' --- 逐 N 验证 ---
    Dim N As Long
    For N = 4 To 8
        row = writeNBlock(ws, row, N)
        row = row + 1
    Next N

    ' --- A180188 对比表 ---
    row = writeA180188Comparison(ws, row)

    ' --- 美化 ---
    ws.UsedRange.EntireColumn.AutoFit

    ' --- 恢复设置 ---
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault

    MsgBox "公式验证完成！工作表：STAT_005_公式验证", vbInformation
    Exit Sub

errHandler:
    Application.ScreenUpdating = True
    Application.Cursor = xlDefault
    MsgBox "运行出错：" & Err.Description, vbExclamation
End Sub

' ============================================================
' 二、工作表输出辅助
' ============================================================

' —— 写入单个 N 的验证块
Private Function writeNBlock(ws As Worksheet, ByVal startRow As Long, ByVal N As Long) As Long
    Dim row As Long
    row = startRow

    Dim freq As Object
    Set freq = getT(N)

    ' --- 区块标题 ---
    ws.Cells(row, 1).Value = "═══ N = " & N & " ═══"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    row = row + 1

    ' --- T(N,k) 原始频率行 ---
    ws.Cells(row, 1).Value = "T(" & N & ",k) 原始频率："
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    Dim k As Long
    For k = 0 To N
        ws.Cells(row, 1 + k * 2).Value = "k=" & k
        ws.Cells(row, 1 + k * 2 + 1).Value = T_from_freq(freq, k)
    Next k
    row = row + 2

    ' --- E(N,j) 容斥表 ---
    ws.Cells(row, 1).Value = "E(" & N & ",j) = Σ_{k≥j} C(k,j)·T(" & N & ",k)"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 1).Value = "j"
    ws.Cells(row, 2).Value = "E(j)"
    ws.Cells(row, 3).Value = "C(N,j)"
    ws.Cells(row, 4).Value = "平均H(S)=E/C"
    ws.Rows(row).Font.Bold = True
    row = row + 1
    Dim j As Long
    For j = 0 To N
        Dim Ej As Double, cnj As Double, avgH As Double
        Ej = E_from_T(freq, N, j)
        cnj = combNum(N, j)
        If cnj > 0 Then avgH = Ej / cnj Else avgH = 0
        ws.Cells(row, 1).Value = j
        ws.Cells(row, 2).Value = Ej
        ws.Cells(row, 3).Value = cnj
        ws.Cells(row, 4).Value = avgH
        row = row + 1
    Next j
    row = row + 1

    ' --- 定理1验证：T(N,N) == 2N ---
    Dim Tnn As Long
    Tnn = T_from_freq(freq, N)
    ws.Cells(row, 1).Value = "【定理1】T(" & N & "," & N & ") = " & Tnn & _
        "   vs   2N = " & (2 * N) & "   →   " & IIf(Tnn = 2 * N, "PASS", "FAIL")
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' --- 定理2验证：E(N,N-1) == N × E(N,N) ---
    Dim En_1 As Double, En As Double
    En_1 = E_from_T(freq, N, N - 1)
    En = E_from_T(freq, N, N)
    ws.Cells(row, 1).Value = "【定理2】E(" & N & "," & (N - 1) & ") = " & En_1 & _
        "   vs   N·E(" & N & "," & N & ") = " & (N * En) & "   →   " & _
        IIf(En_1 = N * En, "PASS", "FAIL")
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' --- 定理3验证：T(N,N-1) == 0 ---
    Dim Tn_nm1 As Long
    Tn_nm1 = T_from_freq(freq, N - 1)
    ws.Cells(row, 1).Value = "【定理3】T(" & N & "," & (N - 1) & ") = " & Tn_nm1 & _
        "   →   " & IIf(Tn_nm1 = 0, "PASS", "FAIL")
    ws.Cells(row, 1).Font.Bold = True
    row = row + 2

    ' --- 容斥反推验证 ---
    ws.Cells(row, 1).Value = "【容斥反推】对所有 k，T(N,k) = Σ_{j=k..N} (-1)^{j-k}·C(j,k)·E(j) 验证："
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 1).Value = "k"
    ws.Cells(row, 2).Value = "公式值"
    ws.Cells(row, 3).Value = "实测值"
    ws.Cells(row, 4).Value = "结果"
    ws.Rows(row).Font.Bold = True
    row = row + 1

    Dim allPass As Boolean
    allPass = True
    For k = 0 To N
        Dim ie As Double
        ie = 0
        For j = k To N
            Dim Ej_k As Double
            Ej_k = E_from_T(freq, N, j)
            If (j - k) Mod 2 = 0 Then
                ie = ie + combNum(j, k) * Ej_k
            Else
                ie = ie - combNum(j, k) * Ej_k
            End If
        Next j
        Dim realT As Long
        realT = T_from_freq(freq, k)
        Dim ok As Boolean
        ok = (ie = realT)
        If Not ok Then allPass = False
        ws.Cells(row, 1).Value = k
        ws.Cells(row, 2).Value = ie
        ws.Cells(row, 3).Value = realT
        ws.Cells(row, 4).Value = IIf(ok, "PASS", "FAIL")
        row = row + 1
    Next k
    ws.Cells(row, 1).Value = "→ 全部 k 验证: " & IIf(allPass, "ALL PASS", "SOME FAIL")
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1

    ' --- 分隔线 ---
    row = row + 1
    ws.Cells(row, 1).Value = String(80, "-")
    row = row + 1

    writeNBlock = row
End Function

' —— 写入 A180188 对比表
Private Function writeA180188Comparison(ws As Worksheet, ByVal startRow As Long) As Long
    Dim row As Long
    row = startRow

    row = row + 1
    ws.Cells(row, 1).Value = "═══ A180188 对比表 ═══"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    row = row + 1
    ws.Cells(row, 1).Value = "A180188 闭式（仅升序环形相邻）：T_asc(n,k) = n × C(n-1,k) × !(n-1-k)   (k ≤ n-1)"
    row = row + 1
    ws.Cells(row, 1).Value = "我们的三角：T(N,k)（双向 |差|=1，并自动含 |差|=N-1 的边 (1,N)）"
    row = row + 2

    ' 表头
    ws.Cells(row, 1).Value = "N"
    ws.Cells(row, 2).Value = "k"
    ws.Cells(row, 3).Value = "我们T(N,k)"
    ws.Cells(row, 4).Value = "A180188值"
    ws.Cells(row, 5).Value = "比值"
    ws.Rows(row).Font.Bold = True
    row = row + 1

    Dim N As Long, k As Long
    For N = 4 To 8
        Dim freq As Object
        Set freq = getT(N)
        For k = 0 To N
            Dim ourT As Long, ascT As Double
            ourT = T_from_freq(freq, k)
            ascT = 0
            If k <= N - 1 Then
                ascT = N * combNum(N - 1, k) * subfact(N - 1 - k)
            End If
            If ourT <> 0 Or ascT <> 0 Then
                ws.Cells(row, 1).Value = N
                ws.Cells(row, 2).Value = k
                ws.Cells(row, 3).Value = ourT
                ws.Cells(row, 4).Value = ascT
                If ascT <> 0 Then
                    ws.Cells(row, 5).Value = ourT / ascT
                    ws.Cells(row, 5).NumberFormat = "0.00"
                Else
                    ws.Cells(row, 5).Value = "—"
                End If
                row = row + 1
            End If
        Next k
        row = row + 1
    Next N

    ' 结论
    row = row + 1
    ws.Cells(row, 1).Value = "结论：满分 T(N,N)=2N 恰好是 A180188 满分 (k=N-1) 值 n 的 2 倍。"
    row = row + 1
    ws.Cells(row, 1).Value = "      其他 k 没有简单倍数关系，说明双向相邻 ≠ 升序×2。"
    row = row + 1

    writeA180188Comparison = row
End Function

' ============================================================
' 三、核心函数（从 JS 转换）
' ============================================================

' —— 环形相邻计数（双向 |差|=1 或 |差|=max-min）
' 对环形排列，统计相邻元素差值绝对值为 1 或为 max-min 的边数
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
    For i = LBound(arr) To UBound(arr)
        Dim a As Long, b As Long, d As Long
        a = arr(i)
        If i = UBound(arr) Then b = arr(LBound(arr)) Else b = arr(i + 1)
        d = Abs(a - b)
        If d = 1 Or d = diff Then count = count + 1
    Next i
    环形相邻计数_arr = count
End Function

' —— Heap 全排列遍历（原地交换，无重复，O(n!)）
' 对 nums 的所有全排列，计算环形相邻计数并累加到 freq 字典
Private Sub 全排列_HeapCallBack(nums As Variant, freq As Object, ByRef totalCount As Long)
    Dim n As Long, i As Long
    n = UBound(nums) - LBound(nums) + 1
    Dim arr() As Long
    ReDim arr(0 To n - 1)
    For i = 0 To n - 1: arr(i) = nums(LBound(nums) + i): Next i
    Dim c() As Long
    ReDim c(0 To n - 1)
    Dim cnt As Long: cnt = 环形相邻计数_arr(arr)
    If freq.Exists(cnt) Then freq(cnt) = freq(cnt) + 1 Else freq.Add cnt, 1
    totalCount = totalCount + 1
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
            c(i) = c(i) + 1: i = 0
        Else
            c(i) = 0: i = i + 1
        End If
    Loop
End Sub

' —— 获取 T(N,k) 频率字典（枚举 1..N 的所有全排列）
Private Function getT(ByVal N As Long) As Object
    Dim freq As Object: Set freq = CreateObject("Scripting.Dictionary")
    Dim nums() As Long: ReDim nums(1 To N)
    Dim i As Long
    For i = 1 To N: nums(i) = i: Next i
    Dim total As Long
    Call 全排列_HeapCallBack(nums, freq, total)
    Set getT = freq
End Function

' —— 从字典获取 T(N,k)（不存在则返回 0）
Private Function T_from_freq(freq As Object, ByVal k As Long) As Long
    If freq.Exists(k) Then T_from_freq = freq(k) Else T_from_freq = 0
End Function

' —— 计算 E(N,j) = Σ_{k≥j} C(k,j) × T(N,k)
' 容斥中间量：每条 j-边集在 C(k,j) 个 k-排列中被计
Private Function E_from_T(freq As Object, ByVal N As Long, ByVal j As Long) As Double
    Dim key As Variant, sum As Double: sum = 0#
    For Each key In freq.Keys
        If CLng(key) >= j Then
            sum = sum + combNum(CLng(key), j) * freq(key)
        End If
    Next key
    E_from_T = sum
End Function

' —— 组合数 C(n,k) = n! / (k! × (n-k)!)
Private Function combNum(ByVal n As Long, ByVal k As Long) As Double
    If k < 0 Or k > n Then Exit Function
    Dim r As Double: r = 1#
    Dim i As Long
    For i = 1 To k: r = r * (n - k + i) / i: Next i
    combNum = r
End Function

' —— 阶乘 n!
Private Function fact(ByVal n As Long) As Double
    Dim r As Double: r = 1#: Dim i As Long
    For i = 2 To n: r = r * i: Next i
    fact = r
End Function

' —— 错位排列数 !n (subfactorial)
' !0=1, !1=0, !n = (n-1) × (!(n-1) + !(n-2))
Private Function subfact(ByVal n As Long) As Double
    If n = 0 Then subfact = 1: Exit Function
    If n = 1 Then subfact = 0: Exit Function
    subfact = (n - 1) * (subfact(n - 1) + subfact(n - 2))
End Function
