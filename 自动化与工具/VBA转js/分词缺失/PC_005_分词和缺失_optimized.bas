Attribute VB_Name = "PC_005_分词和缺失_优化"
Option Explicit

' ============================================================
' PC_005 分词和缺失分析 - 优化版
' 优化要点:
'   1. 变量声明集中到过程顶部 (VBA不支持块级作用域)
'   2. 用 ExtractColumn 替代 Application.Index (避免隐式计算开销)
'   3. 修正 GetFlattenedArray 一维/二维判定 (不再依赖 On Error 检测)
'   4. 修正 LogExecutionTime 空行定位 (用 End(xlUp) 替代 UsedRange)
'   5. 单格分词用 数组+Join 替代循环拼接 (避免 O(n^2))
'   6. 增加 空文本/单字符 校验
'   7. 简化 GetPaddedBinaryString 逻辑
' ============================================================

Sub 分词和缺失分析()
    On Error GoTo ErrorHandler

    ' --- 变量声明区 (全部集中在顶部) ---
    Dim startTime As Double
    Dim selectedRange As Range
    Dim dataCount As Long, combinations As Long
    Dim binaryArray As Variant, resultArray As Variant
    Dim i As Long, j As Long
    Dim text As String, textLength As Long
    Dim outputSheet As Worksheet
    Dim dict As Object
    Dim missingCount As Long
    Dim strParts() As String
    Dim dataArray As Variant
    Dim keptItems As String, missingItems As String
    Dim missingCounter As Long
    Dim dataSizeValue As Long
    Dim colData As Variant

    startTime = Timer
    Set dict = CreateObject("Scripting.Dictionary")

    ' --- 获取用户选择 ---
    On Error Resume Next
    Set selectedRange = Application.InputBox(prompt:="请选择数据范围（单格分词/多格组合）", Type:=8)
    On Error GoTo ErrorHandler
    If selectedRange Is Nothing Then Exit Sub

    ' ============================================================
    ' 分支一: 单个单元格 -> 文本分词分析
    '   对长度 n 的文本, 有 n-1 个可切分位置
    '   用二进制枚举 2^(n-1) 种切分方案
    '   "1" = 插入分隔符 | (该位置"缺失")
    '   "0" = 不切分
    ' ============================================================
    If selectedRange.count = 1 Then
        text = CStr(selectedRange.Value)
        textLength = Len(text)

        ' 输入校验
        If textLength = 0 Then
            MsgBox "选中的单元格为空，请选择包含文本的单元格。", vbExclamation
            Exit Sub
        End If
        If textLength = 1 Then
            MsgBox "单字符无需分词分析。", vbInformation
            Exit Sub
        End If
        If textLength > 20 Then
            MsgBox "文本长度过大(>" & textLength & ")，建议长度不超过20。", vbExclamation
            Exit Sub
        End If

        dataCount = textLength - 1
        combinations = 2 ^ dataCount

        ' 预分配数组
        ReDim binaryArray(1 To combinations, 1 To 1)
        ReDim resultArray(1 To combinations, 1 To 2)

        ' 生成二进制组合并计算结果
        For i = 0 To combinations - 1
            binaryArray(i + 1, 1) = GetPaddedBinaryString(i, dataCount)

            ' 用数组构建分词结果, 最后 Join 一次 (避免循环内拼接的 O(n^2))
            ReDim strParts(1 To textLength * 2 - 1)
            missingCount = 0
            For j = 1 To textLength
                strParts(j * 2 - 1) = Mid(text, j, 1)
                If j < textLength Then
                    If Mid(binaryArray(i + 1, 1), j, 1) = "1" Then
                        strParts(j * 2) = "|"
                        missingCount = missingCount + 1
                    Else
                        strParts(j * 2) = " "
                    End If
                End If
            Next j
            resultArray(i + 1, 1) = Join(strParts, "")
            resultArray(i + 1, 2) = missingCount
        Next i

        ' 创建输出工作表
        Set outputSheet = CreateOutputSheet("分词缺失分析")

        ' 输出结果
        With outputSheet
            .Columns("B:B").NumberFormatLocal = "@"
            .Range("B1").Resize(combinations, 1) = binaryArray
            colData = ExtractColumn(resultArray, 1, combinations)
            .Range("C1").Resize(combinations, 1) = colData
            colData = ExtractColumn(resultArray, 2, combinations)
            .Range("D1").Resize(combinations, 1) = colData
            .Range("B1:D1").Value = Array("二进制组合", "分词结果", "缺失位置数")
            .Columns("D:D").AutoFilter
            .Columns("B:F").EntireColumn.AutoFit
        End With

    ' ============================================================
    ' 分支二: 多个单元格 -> 组合缺失分析
    '   对 m 个数据项, 用二进制枚举 2^m 种保留/缺失方案
    '   "0" = 保留, "1" = 缺失
    ' ============================================================
    Else
        dataArray = GetFlattenedArray(selectedRange)
        dataCount = UBound(dataArray)

        If dataCount > 20 Then
            MsgBox "数据量过大(>" & dataCount & ")，建议数量不超过20。", vbExclamation
            Exit Sub
        End If

        combinations = 2 ^ dataCount

        ReDim binaryArray(1 To combinations, 1 To 1)
        ReDim resultArray(1 To combinations, 1 To 3)

        ' 存储数据到字典
        For i = 1 To dataCount
            dict.Add i, dataArray(i)
        Next i

        ' 生成组合结果
        For i = 0 To combinations - 1
            binaryArray(i + 1, 1) = GetPaddedBinaryString(i, dataCount)

            keptItems = ""
            missingItems = ""
            missingCounter = 0

            For j = 1 To dataCount
                If Mid(binaryArray(i + 1, 1), j, 1) = "0" Then
                    If keptItems <> "" Then keptItems = keptItems & "|"
                    keptItems = keptItems & dict(j)
                Else
                    If missingItems <> "" Then missingItems = missingItems & "|"
                    missingItems = missingItems & dict(j)
                    missingCounter = missingCounter + 1
                End If
            Next j

            resultArray(i + 1, 1) = keptItems
            resultArray(i + 1, 2) = missingItems
            resultArray(i + 1, 3) = missingCounter
        Next i

        Set outputSheet = CreateOutputSheet("组合缺失分析")

        With outputSheet
            .Columns("B:B").NumberFormatLocal = "@"
            .Range("B1").Resize(combinations, 1) = binaryArray
            colData = ExtractColumn(resultArray, 1, combinations)
            .Range("C1").Resize(combinations, 1) = colData
            colData = ExtractColumn(resultArray, 2, combinations)
            .Range("D1").Resize(combinations, 1) = colData
            colData = ExtractColumn(resultArray, 3, combinations)
            .Range("E1").Resize(combinations, 1) = colData
            .Range("B1:E1").Value = Array("二进制组合", "保留项", "缺失项", "缺失数量")
            .Columns("E:E").AutoFilter
            .Columns("B:E").EntireColumn.AutoFit
        End With
    End If

    ' --- 记录执行时间 ---
    If Not selectedRange Is Nothing Then
        If selectedRange.count = 1 Then
            dataSizeValue = CLng(Len(CStr(selectedRange.Value)))
        Else
            dataSizeValue = CLng(selectedRange.count)
        End If
        LogExecutionTime Timer - startTime, dataSizeValue
    End If
    Exit Sub

ErrorHandler:
    MsgBox "执行过程中发生错误: " & err.Description, vbExclamation, "错误"
End Sub

' ============================================================
' 核心函数: 直接生成指定长度的二进制字符串
' 优化: 去除冗余分支, 逻辑更简洁
' ============================================================
Function GetPaddedBinaryString(ByVal number As Long, ByVal Length As Long) As String
    Dim result As String
    Dim tempNum As Long

    If Length = 0 Then
        GetPaddedBinaryString = "0"
        Exit Function
    End If

    result = ""
    tempNum = number
    Do While tempNum > 0
        result = CStr(tempNum Mod 2) & result
        tempNum = tempNum \ 2
    Loop

    ' 左侧补零至指定长度
    If Len(result) < Length Then
        result = String(Length - Len(result), "0") & result
    End If

    GetPaddedBinaryString = result
End Function

' ============================================================
' 新增: 从二维数组提取单列 (替代 Application.Index)
' 原因: Application.Index 对大数组有隐式开销, 直接循环更快
' ============================================================
Function ExtractColumn(arr As Variant, colIndex As Long, rowCount As Long) As Variant
    Dim result() As Variant
    Dim i As Long
    ReDim result(1 To rowCount, 1 To 1)
    For i = 1 To rowCount
        result(i, 1) = arr(i, colIndex)
    Next i
    ExtractColumn = result
End Function

' ============================================================
' 修正: 获取扁平化数据数组
' 原实现用 On Error 检测二维, 不可靠
' 改为用 Rows.Count / Columns.Count 显式判断
' ============================================================
Function GetFlattenedArray(ByVal rng As Range) As Variant
    Dim rowCount As Long, colCount As Long
    Dim Arr As Variant
    Dim i As Long, j As Long, k As Long
    Dim result() As Variant

    rowCount = rng.Rows.count
    colCount = rng.Columns.count
    Arr = rng.Value2

    If rowCount = 1 And colCount = 1 Then
        ReDim result(1 To 1)
        result(1) = Arr
        GetFlattenedArray = result
    ElseIf rowCount = 1 Then
        ReDim result(1 To colCount)
        For i = 1 To colCount
            result(i) = Arr(1, i)
        Next i
        GetFlattenedArray = result
    ElseIf colCount = 1 Then
        ReDim result(1 To rowCount)
        For i = 1 To rowCount
            result(i) = Arr(i, 1)
        Next i
        GetFlattenedArray = result
    Else
        ReDim result(1 To rowCount * colCount)
        k = 1
        For i = 1 To rowCount
            For j = 1 To colCount
                result(k) = Arr(i, j)
                k = k + 1
            Next j
        Next i
        GetFlattenedArray = result
    End If
End Function

' ============================================================
' 创建安全的输出工作表 (逻辑不变, 已较完善)
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

' ============================================================
' 修正: 记录执行时间
' 原实现用 UsedRange.Rows.Count 定位空行, 当表格有格式无数据时偏移错误
' 改为用 End(xlUp) 从底部向上定位, 可靠且标准
' ============================================================
Sub LogExecutionTime(ByVal executionTime As Double, ByVal dataSize As Long)
    On Error Resume Next
    Dim logSheet As Worksheet
    Dim nextRow As Long

    Set logSheet = ThisWorkbook.Sheets("快捷键后台")

    If logSheet Is Nothing Then
        Set logSheet = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        logSheet.Name = "快捷键后台"
        With logSheet
            .Cells(1, 1).Value = "执行时间(秒)"
            .Cells(1, 2).Value = "数据量"
            .Cells(1, 3).Value = "记录时间"
            .Range("A1:C1").Font.Bold = True
        End With
    End If

    ' 用 End(xlUp) 可靠定位最后一行 (替代不可靠的 UsedRange)
    nextRow = logSheet.Cells(logSheet.Rows.count, 1).End(xlUp).Row + 1
    If nextRow < 2 Then nextRow = 2

    With logSheet
        .Cells(nextRow, 1).Value = Format(executionTime, "0.000")
        .Cells(nextRow, 2).Value = dataSize
        .Cells(nextRow, 3).Value = Now
        .Columns("A:C").AutoFit
    End With
    On Error GoTo 0
End Sub
