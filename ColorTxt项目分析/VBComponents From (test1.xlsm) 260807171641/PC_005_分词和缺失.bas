Attribute VB_Name = "PC_005_分词和缺失"
Option Explicit

Sub 分词和缺失分析()
    On Error GoTo ErrorHandler
    Dim startTime As Double
    startTime = Timer
    
    ' 变量声明
    Dim selectedRange As Range
    Dim dataCount As Long, combinations As Long
    Dim binaryArray As Variant, resultArray As Variant
    Dim i As Long, j As Long
    Dim text As String, textLength As Long
    Dim outputSheet As Worksheet
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    
    ' 获取用户选择
    On Error Resume Next
    Set selectedRange = Application.InputBox(prompt:="请选择数据范围（单格分词/多格组合）", Type:=8)
    On Error GoTo ErrorHandler
    
    If selectedRange Is Nothing Then Exit Sub
    
    ' 处理单个单元格（文本分词分析）
    If selectedRange.count = 1 Then
        text = selectedRange.Value
        textLength = Len(text)
        
        ' 计算组合数
        If textLength > 20 Then
            MsgBox "文本长度过大，可能导致性能问题。建议长度不超过20。", vbExclamation
            Exit Sub
        End If
        
        dataCount = textLength - 1
        combinations = 2 ^ dataCount
        
        ' 预分配数组 - 优化性能
        ReDim binaryArray(1 To combinations, 1 To 1)
        ReDim resultArray(1 To combinations, 1 To 2) ' 第一列存储分词结果，第二列存储缺失数量
        
        ' 生成二进制组合并计算结果 - 优化算法
        For i = 0 To combinations - 1
            ' 直接生成二进制字符串并补零，避免多次函数调用
            binaryArray(i + 1, 1) = GetPaddedBinaryString(i, dataCount)
            
            ' 生成带分隔符的分词结果
            Dim tokenResult As String
            tokenResult = ""
            Dim missingCount As Long
            missingCount = 0
            
            For j = 1 To textLength
                ' 添加字符
                tokenResult = tokenResult & Mid(text, j, 1)
                
                ' 添加分隔符（不是最后一个字符）
                If j < textLength Then
                    Dim separator As String
                    If Mid(binaryArray(i + 1, 1), j, 1) = "1" Then
                        separator = "|" ' 分隔表示缺失位置
                        missingCount = missingCount + 1
                    Else
                        separator = " " ' 不分隔
                    End If
                    tokenResult = tokenResult & separator
                End If
            Next j
            
            resultArray(i + 1, 1) = tokenResult
            resultArray(i + 1, 2) = missingCount
        Next i
        
        ' 创建输出工作表
        Set outputSheet = CreateOutputSheet("分词缺失分析")
        
        ' 输出结果
        With outputSheet
            .Columns("B:B").NumberFormatLocal = "@" ' 设置二进制列为文本格式
            .Range("B1").Resize(combinations, 1) = binaryArray
            .Range("C1").Resize(combinations, 1) = Application.Index(resultArray, 0, 1)
            .Range("D1").Resize(combinations, 1) = Application.Index(resultArray, 0, 2)
            
            ' 设置标题
            .Range("B1:D1").Value = Array("二进制组合", "分词结果", "缺失位置数")
            
            ' 格式化和筛选
            .Columns("D:D").AutoFilter
            .Columns("B:F").EntireColumn.AutoFit
        End With
    
    ' 处理多单元格（组合分析）
    Else
        ' 获取数据并检查维度
        Dim dataArray As Variant
        dataArray = GetFlattenedArray(selectedRange)
        dataCount = UBound(dataArray)
        
        ' 检查数据量
        If dataCount > 20 Then
            MsgBox "数据量过大，可能导致性能问题。建议数量不超过20。", vbExclamation
            Exit Sub
        End If
        
        ' 计算组合数
        combinations = 2 ^ dataCount
        
        ' 预分配数组
        ReDim binaryArray(1 To combinations, 1 To 1)
        ReDim resultArray(1 To combinations, 1 To 3) ' 保留、缺失、缺失数量
        
        ' 存储数据到字典
        For i = 1 To dataCount
            dict.Add i, dataArray(i)
        Next i
        
        ' 生成组合结果
        For i = 0 To combinations - 1
            binaryArray(i + 1, 1) = GetPaddedBinaryString(i, dataCount)
            
            Dim keptItems As String, missingItems As String
            keptItems = ""
            missingItems = ""
            Dim missingCounter As Long
            missingCounter = 0
            
            For j = 1 To dataCount
                If Mid(binaryArray(i + 1, 1), j, 1) = "0" Then
                    ' 保留项
                    If keptItems <> "" Then keptItems = keptItems & "|"
                    keptItems = keptItems & dict(j)
                Else
                    ' 缺失项
                    If missingItems <> "" Then missingItems = missingItems & "|"
                    missingItems = missingItems & dict(j)
                    missingCounter = missingCounter + 1
                End If
            Next j
            
            resultArray(i + 1, 1) = keptItems
            resultArray(i + 1, 2) = missingItems
            resultArray(i + 1, 3) = missingCounter
        Next i
        
        ' 创建输出工作表
        Set outputSheet = CreateOutputSheet("组合缺失分析")
        
        ' 输出结果
        With outputSheet
            .Columns("B:B").NumberFormatLocal = "@" ' 设置二进制列为文本格式
            .Range("B1").Resize(combinations, 1) = binaryArray
            .Range("C1").Resize(combinations, 1) = Application.Index(resultArray, 0, 1)
            .Range("D1").Resize(combinations, 1) = Application.Index(resultArray, 0, 2)
            .Range("E1").Resize(combinations, 1) = Application.Index(resultArray, 0, 3)
            
            ' 设置标题
            .Range("B1:E1").Value = Array("二进制组合", "保留项", "缺失项", "缺失数量")
            
            ' 格式化和筛选
            .Columns("E:E").AutoFilter
            .Columns("B:E").EntireColumn.AutoFit
        End With
    End If
    
' 记录执行时间
Dim dataSizeValue As Long
If Not selectedRange Is Nothing Then
    If selectedRange.count = 1 Then
        dataSizeValue = CLng(Len(selectedRange.Value))
    Else
        dataSizeValue = CLng(selectedRange.count)
    End If
    LogExecutionTime Timer - startTime, dataSizeValue
End If
    
    Exit Sub
    
ErrorHandler:
    MsgBox "执行过程中发生错误: " & err.Description, vbExclamation, "错误"
End Sub

' 核心优化：直接生成指定长度的二进制字符串
Function GetPaddedBinaryString(ByVal number As Long, ByVal Length As Long) As String
    If Length = 0 Then
        GetPaddedBinaryString = "0"
        Exit Function
    End If
    
    Dim result As String
    result = ""
    
    ' 直接计算二进制表示
    Dim tempNum As Long
    tempNum = number
    
    Do While tempNum > 0 Or Len(result) < Length
        result = CStr(tempNum Mod 2) & result
        tempNum = tempNum \ 2
    Loop
    
    ' 确保长度符合要求（左侧补零）
    If Len(result) < Length Then
        result = String(Length - Len(result), "0") & result
    ElseIf Len(result) > Length Then
        ' 如果超过指定长度，截取右侧
        result = Right(result, Length)
    End If
    
    GetPaddedBinaryString = result
End Function

' 获取扁平化的数据数组
Function GetFlattenedArray(ByVal rng As Range) As Variant
    Dim Arr As Variant
    
    ' 检查是否为二维数组
    On Error Resume Next
    Dim Temp As Variant
    Temp = rng.Value2(1, 2)
    
    If err.number = 0 Then
        ' 二维数组，需要扁平化
        Arr = rng.Value2
        Dim flatCount As Long
        flatCount = rng.rows.count * rng.Columns.count
        ReDim result(1 To flatCount)
        
        Dim i As Long, j As Long, k As Long
        k = 1
        
        For i = 1 To UBound(Arr, 1)
            For j = 1 To UBound(Arr, 2)
                result(k) = Arr(i, j)
                k = k + 1
            Next j
        Next i
        
        GetFlattenedArray = result
    Else
        ' 一维数组，直接返回
        GetFlattenedArray = Application.Transpose(rng.Value2)
    End If
    
    On Error GoTo 0
End Function

' 创建安全的输出工作表
Function CreateOutputSheet(ByVal baseName As String) As Worksheet
    ' 检查工作表是否存在，如存在则删除
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(baseName)
    If Not ws Is Nothing Then
        Application.DisplayAlerts = False
        ws.Delete
        Application.DisplayAlerts = True
    End If
    On Error GoTo 0
    
    ' 创建新工作表
    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
    ws.Name = baseName
    Set CreateOutputSheet = ws
End Function


' 记录执行时间
Sub LogExecutionTime(ByVal executionTime As Double, ByVal dataSize As Long)
    On Error Resume Next
    Dim logSheet As Worksheet
    Set logSheet = ThisWorkbook.Sheets("快捷键后台")
    
    ' 如果工作表不存在，则创建它
    If logSheet Is Nothing Then
        Set logSheet = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        logSheet.Name = "快捷键后台"
        
        ' 设置标题行
        With logSheet
            .Cells(1, 1).Value = "执行时间(秒)"
            .Cells(1, 2).Value = "数据量"
            .Cells(1, 3).Value = "记录时间"
            .Range("A1:C1").Font.Bold = True
            .Columns("A:C").AutoFit
        End With
    End If
    
    ' 修复nextRow计算逻辑
    Dim nextRow As Long
    nextRow = logSheet.UsedRange.rows.count + 1
    
    ' 确保从第2行开始（即使表格为空）
    If nextRow < 2 Then nextRow = 2
    
    ' 将信息拆分到不同列中
    With logSheet
        .Cells(nextRow, 1).Value = Format(executionTime, "0.000")
        .Cells(nextRow, 2).Value = dataSize
        .Cells(nextRow, 3).Value = Now
        .Columns("A:C").AutoFit ' 自动调整列宽以显示完整内容
    End With
    
    On Error GoTo 0
End Sub
