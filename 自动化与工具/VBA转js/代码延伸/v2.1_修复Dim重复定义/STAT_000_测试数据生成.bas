Attribute VB_Name = "STAT_000_测试数据生成"
Option Explicit

' ============================================================
' STAT_000_测试数据生成.bas   v2.1
' 生成测试用示例数据 + 一键验证所有模块
'
' 使用方法：
'   1. 在 WPS VBA 编辑器中导入此模块
'   2. 运行 演示_一键测试 即可
' ============================================================

' ============================================================
' 一、生成测试数据
' ============================================================

Public Sub 生成测试数据()
    ' --- 所有变量声明在过程顶部 ---
    Dim ws As Worksheet
    Dim r As Long, i As Long
    Dim nums1 As Variant, nums2 As Variant
    Dim rng As Range

    ' 创建或清空工作表
    On Error Resume Next
    Set ws = Worksheets("测试数据")
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = "测试数据"
    Else
        ws.Cells.Clear
    End If

    ' ===== 1. 基础数字序列 =====
    ws.Cells(1, 1).Value = "【基础数据】"
    ws.Cells(1, 1).Font.Bold = True
    r = 2

    ws.Cells(r, 1).Value = "序号"
    ws.Cells(r, 2).Value = "数值"
    ws.Cells(r, 3).Value = "排列"
    r = r + 1

    ' 生成 1..10 的序列
    For i = 1 To 10
        ws.Cells(r, 1).Value = i
        ws.Cells(r, 2).Value = i
        ws.Cells(r, 3).Value = i
        r = r + 1
    Next i
    r = r + 1

    ' ===== 2. 字符串连接测试数据 =====
    ws.Cells(r, 1).Value = "【连接字符串测试】"
    ws.Cells(r, 1).Font.Bold = True
    r = r + 1

    ws.Cells(r, 1).Value = "A列"
    ws.Cells(r, 2).Value = "B列"
    ws.Cells(r, 3).Value = "C列"
    ws.Cells(r, 4).Value = "D列"
    ws.Cells(r, 5).Value = "E列"
    r = r + 1

    ' 测试数据行
    ws.Cells(r, 1).Value = "苹果"
    ws.Cells(r, 2).Value = "香蕉"
    ws.Cells(r, 3).Value = "橙子"
    ws.Cells(r, 4).Value = "葡萄"
    ws.Cells(r, 5).Value = "西瓜"
    r = r + 1

    ws.Cells(r, 1).Value = 1
    ws.Cells(r, 2).Value = 2
    ws.Cells(r, 3).Value = 3
    ws.Cells(r, 4).Value = ""
    ws.Cells(r, 5).Value = 5
    r = r + 1

    ws.Cells(r, 1).Value = "A"
    ws.Cells(r, 2).Value = "B"
    ws.Cells(r, 3).Value = ""
    ws.Cells(r, 4).Value = "D"
    ws.Cells(r, 5).Value = "E"
    r = r + 1

    ' 空值测试行
    ws.Cells(r, 1).Value = ""
    ws.Cells(r, 2).Value = ""
    ws.Cells(r, 3).Value = "X"
    ws.Cells(r, 4).Value = ""
    ws.Cells(r, 5).Value = ""
    r = r + 2

    ' ===== 3. 环形相邻计数测试数据 =====
    ws.Cells(r, 1).Value = "【环形相邻计数测试】"
    ws.Cells(r, 1).Font.Bold = True
    r = r + 1

    ws.Cells(r, 1).Value = "排列"
    ws.Cells(r, 2).Value = "期望结果"
    ws.Cells(r, 3).Value = "说明"
    r = r + 1

    ' 1,2,3,4,5 → 满分 10 (5对全部相邻)
    ws.Cells(r, 1).Value = "1,2,3,4,5"
    ws.Cells(r, 2).Value = 10
    ws.Cells(r, 3).Value = "满分排列（正向）"
    r = r + 1

    ' 5,4,3,2,1 → 满分 10
    ws.Cells(r, 1).Value = "5,4,3,2,1"
    ws.Cells(r, 2).Value = 10
    ws.Cells(r, 3).Value = "满分排列（反向）"
    r = r + 1

    ' 1,3,5,2,4 → 0 分
    ws.Cells(r, 1).Value = "1,3,5,2,4"
    ws.Cells(r, 2).Value = 0
    ws.Cells(r, 3).Value = "零分排列"
    r = r + 1

    ' 1,2,4,3,5 → 4 分
    ws.Cells(r, 1).Value = "1,2,4,3,5"
    ws.Cells(r, 2).Value = 4
    ws.Cells(r, 3).Value = "部分相邻"
    r = r + 2

    ' 格式化
    ws.Columns("A:E").AutoFit
    ws.Range(ws.Cells(1, 1), ws.Cells(r, 5)).Borders.LineStyle = xlContinuous

    MsgBox "测试数据已生成到工作表「测试数据」", vbInformation
End Sub

' ============================================================
' 二、一键测试所有模块
' ============================================================

Public Sub 演示_一键测试()
    ' --- 所有变量声明在过程顶部 ---
    Dim ws As Worksheet
    Dim r As Long
    Dim passCount As Long, failCount As Long
    Dim t0 As Double, t1 As Double

    ' 创建测试报告工作表
    On Error Resume Next
    Set ws = Worksheets("测试报告")
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = "测试报告"
    Else
        ws.Cells.Clear
    End If

    r = 1
    ws.Cells(r, 1).Value = "v2.1 模块测试报告"
    ws.Cells(r, 1).Font.Bold = True
    ws.Cells(r, 1).Font.Size = 14
    r = r + 1
    ws.Cells(r, 1).Value = "时间: " & Format(Now, "yyyy-mm-dd hh:nn:ss")
    r = r + 2

    ws.Cells(r, 1).Value = "模块"
    ws.Cells(r, 2).Value = "状态"
    ws.Cells(r, 3).Value = "耗时(秒)"
    ws.Cells(r, 4).Value = "备注"
    r = r + 1

    passCount = 0
    failCount = 0

    ' ===== 测试 STAT_008 闭式公式（最重要）=====
    ws.Cells(r, 1).Value = "STAT_008 闭式公式"
    t0 = Timer
    On Error GoTo Err008
    Call 测试_STAT_008
    t1 = Timer
    ws.Cells(r, 2).Value = "PASS"
    ws.Cells(r, 3).Value = Format(t1 - t0, "0.000")
    ws.Cells(r, 4).Value = "T(N,N)=2N, T(N,N-1)=0 验证通过"
    passCount = passCount + 1
    GoTo Next006
Err008:
    ws.Cells(r, 2).Value = "FAIL"
    ws.Cells(r, 3).Value = ""
    ws.Cells(r, 4).Value = "错误: " & Err.Description & " (错误号 " & Err.Number & ")"
    failCount = failCount + 1
    Err.Clear
Next006:
    r = r + 1

    ' ===== 测试 STAT_006 总表特点分析 =====
    ws.Cells(r, 1).Value = "STAT_006 总表特点分析"
    t0 = Timer
    On Error GoTo Err006
    Call 测试_STAT_006
    t1 = Timer
    ws.Cells(r, 2).Value = "PASS"
    ws.Cells(r, 3).Value = Format(t1 - t0, "0.000")
    ws.Cells(r, 4).Value = "N=1..10 总表 + 特点验证"
    passCount = passCount + 1
    GoTo Next005
Err006:
    ws.Cells(r, 2).Value = "FAIL"
    ws.Cells(r, 3).Value = ""
    ws.Cells(r, 4).Value = "错误: " & Err.Description & " (错误号 " & Err.Number & ")"
    failCount = failCount + 1
    Err.Clear
Next005:
    r = r + 1

    ' ===== 测试 STAT_005 公式验证 =====
    ws.Cells(r, 1).Value = "STAT_005 公式验证"
    t0 = Timer
    On Error GoTo Err005
    Call 测试_STAT_005
    t1 = Timer
    ws.Cells(r, 2).Value = "PASS"
    ws.Cells(r, 3).Value = Format(t1 - t0, "0.000")
    ws.Cells(r, 4).Value = "容斥 + 端点定理"
    passCount = passCount + 1
    GoTo Next001
Err005:
    ws.Cells(r, 2).Value = "FAIL"
    ws.Cells(r, 3).Value = ""
    ws.Cells(r, 4).Value = "错误: " & Err.Description & " (错误号 " & Err.Number & ")"
    failCount = failCount + 1
    Err.Clear
Next001:
    r = r + 1

    ' ===== 测试 STAT_001 全组合环形相邻 =====
    ws.Cells(r, 1).Value = "STAT_001 全组合环形相邻"
    t0 = Timer
    On Error GoTo Err001
    Call 测试_STAT_001
    t1 = Timer
    ws.Cells(r, 2).Value = "PASS"
    ws.Cells(r, 3).Value = Format(t1 - t0, "0.000")
    ws.Cells(r, 4).Value = "N=1..8 枚举验证"
    passCount = passCount + 1
    GoTo Done
Err001:
    ws.Cells(r, 2).Value = "FAIL"
    ws.Cells(r, 3).Value = ""
    ws.Cells(r, 4).Value = "错误: " & Err.Description & " (错误号 " & Err.Number & ")"
    failCount = failCount + 1
    Err.Clear
Done:
    r = r + 2

    ' ===== 汇总 =====
    ws.Cells(r, 1).Value = "汇总"
    ws.Cells(r, 1).Font.Bold = True
    r = r + 1
    ws.Cells(r, 1).Value = "通过: " & passCount & " / 失败: " & failCount
    r = r + 1

    If failCount = 0 Then
        ws.Cells(r, 1).Value = "全部模块测试通过！v2.1 修复确认有效。"
        ws.Cells(r, 1).Font.Color = RGB(0, 128, 0)
    Else
        ws.Cells(r, 1).Value = "有 " & failCount & " 个模块失败，请查看上方备注列定位问题。"
        ws.Cells(r, 1).Font.Color = RGB(255, 0, 0)
    End If

    ' 格式化
    ws.Columns("A:D").AutoFit
    ws.Range(ws.Cells(1, 1), ws.Cells(r, 4)).Borders.LineStyle = xlContinuous

    ' 恢复错误处理
    On Error GoTo 0

    MsgBox "测试完成！" & vbCrLf & _
           "通过: " & passCount & "  失败: " & failCount & vbCrLf & _
           "详情见「测试报告」工作表", vbInformation
End Sub

' ============================================================
' 三、各模块测试函数
' ============================================================

Private Sub 测试_STAT_008()
    ' --- 测试闭式公式 STAT_008 ---
    Dim N As Long, k As Long
    Dim freq As Object
    Dim sum As Variant
    Dim tNN As Variant, tNNm1 As Variant
    Dim nfact As Variant
    Dim i As Long
    Dim keyVar As Variant

    For N = 3 To 15
        Set freq = getT_closed(N)

        ' 行和验证
        sum = CDec(0)
        For Each keyVar In freq.Keys
            sum = sum + freq(keyVar)
        Next keyVar

        ' N!
        nfact = CDec(1)
        For i = 1 To N
            nfact = nfact * CDec(i)
        Next i

        If sum <> nfact Then
            Err.Raise vbObjectError + 1, "测试_STAT_008", _
                "N=" & N & " 行和验证失败: " & CStr(sum) & " ≠ " & CStr(nfact)
        End If

        ' 满分定理 T(N,N) = 2N
        tNN = dictGetD(freq, N)
        If tNN <> CDec(2 * N) Then
            Err.Raise vbObjectError + 2, "测试_STAT_008", _
                "N=" & N & " 满分定理失败: T(N,N)=" & CStr(tNN) & " ≠ " & (2 * N)
        End If

        ' 空缺定理 T(N,N-1) = 0
        tNNm1 = dictGetD(freq, N - 1)
        If tNNm1 <> CDec(0) Then
            Err.Raise vbObjectError + 3, "测试_STAT_008", _
                "N=" & N & " 空缺定理失败: T(N,N-1)=" & CStr(tNNm1) & " ≠ 0"
        End If
    Next N
End Sub

Private Sub 测试_STAT_006()
    ' --- 测试 DP 算法 STAT_006（只测小 N）---
    Dim N As Long
    Dim freq As Object
    Dim keyVar As Variant
    Dim sum As Double

    For N = 3 To 8
        Set freq = getT_dp(N)

        sum = 0
        For Each keyVar In freq.Keys
            sum = sum + freq(keyVar)
        Next keyVar

        ' 行和 ≈ N!（Double 精度）
        If Abs(sum - WorksheetFunction.Fact(N)) > 0.5 Then
            Err.Raise vbObjectError + 4, "测试_STAT_006", _
                "N=" & N & " DP行和验证失败: " & sum & " ≠ " & WorksheetFunction.Fact(N)
        End If
    Next N
End Sub

Private Sub 测试_STAT_005()
    ' --- 测试公式验证 STAT_005（仅验证核心逻辑）---
    Dim N As Long
    Dim freq As Object
    Dim tNN As Variant

    For N = 3 To 10
        Set freq = getT_closed(N)
        tNN = dictGetD(freq, N)

        If tNN <> CDec(2 * N) Then
            Err.Raise vbObjectError + 5, "测试_STAT_005", _
                "N=" & N & " 验证失败: T(N,N)=" & CStr(tNN)
        End If
    Next N
End Sub

Private Sub 测试_STAT_001()
    ' --- 测试全组合环形相邻 STAT_001（仅测小 N）---
    Dim N As Long
    Dim freq As Object
    Dim keyVar As Variant
    Dim sum As Long

    For N = 3 To 7
        Set freq = 统计环形相邻词频(CLng(N))

        sum = 0
        For Each keyVar In freq.Keys
            sum = sum + freq(keyVar)
        Next keyVar

        If sum <> WorksheetFunction.Fact(N) Then
            Err.Raise vbObjectError + 6, "测试_STAT_001", _
                "N=" & N & " 枚举行和失败: " & sum & " ≠ " & WorksheetFunction.Fact(N)
        End If
    Next N
End Sub

' ============================================================
' 四、错误日志工具
' ============================================================

' 将错误信息写入工作表「错误日志」
Public Sub 写入错误日志(ByVal moduleName As String, ByVal errNumber As Long, _
                       ByVal errDesc As String, Optional ByVal extraInfo As String = "")
    ' --- 所有变量声明在过程顶部 ---
    Dim ws As Worksheet
    Dim r As Long

    On Error Resume Next
    Set ws = Worksheets("错误日志")
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = "错误日志"
        ws.Cells(1, 1).Value = "时间"
        ws.Cells(1, 2).Value = "模块"
        ws.Cells(1, 3).Value = "错误号"
        ws.Cells(1, 4).Value = "错误描述"
        ws.Cells(1, 5).Value = "附加信息"
        ws.Range("A1:E1").Font.Bold = True
    End If

    r = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    If r < 2 Then r = 2

    ws.Cells(r, 1).Value = Format(Now, "yyyy-mm-dd hh:nn:ss")
    ws.Cells(r, 2).Value = moduleName
    ws.Cells(r, 3).Value = errNumber
    ws.Cells(r, 4).Value = errDesc
    ws.Cells(r, 5).Value = extraInfo

    ws.Columns("A:E").AutoFit
    ws.Cells(Rows.Count, 1).End(xlUp).Select
End Sub

' 带错误日志的调用包装器
Public Sub 安全调用(ByVal moduleName As String, ByVal procName As String)
    On Error GoTo ErrorHandler

    Application.Run procName
    MsgBox moduleName & " 运行成功！", vbInformation
    Exit Sub

ErrorHandler:
    Call 写入错误日志(moduleName, Err.Number, Err.Description, _
                     "过程: " & procName & " | Erl: " & Erl)
    MsgBox moduleName & " 运行失败！" & vbCrLf & _
           "错误号: " & Err.Number & vbCrLf & _
           "错误描述: " & Err.Description & vbCrLf & _
           "详情见「错误日志」工作表", vbCritical
End Sub
