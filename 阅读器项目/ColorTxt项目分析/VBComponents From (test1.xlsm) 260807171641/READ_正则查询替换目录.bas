Attribute VB_Name = "READ_正则查询替换目录"
' 正则查询优化主函数
Sub 正则查询优化()
    ' 错误处理和性能优化
    On Error GoTo ErrorHandler
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Application.EnableEvents = False
    Dim startTime As Double: startTime = Timer
    ' 清除结果区域
    Range("E2:Z1048576").Clear
    ' 声明变量
    Dim regexPatterns As Variant, sourceData As Variant
    Dim matchResults As Variant, foundMatches As Variant
    Dim matchDict As Object, tempDict As Object, duplicateMatchDict As Object ' 新增字典用于保留重复项
    Dim regex As Object
    Dim patternCount As Long, dataCount As Long
    Dim i As Long, j As Long, k As Long
    Dim currentText As String, patternStr As String
    Dim matches As Object, match As Object
    Dim hasMatches As Boolean
    ' 初始化对象
    Set matchDict = CreateObject("Scripting.Dictionary")
    Set tempDict = CreateObject("Scripting.Dictionary")
    Set duplicateMatchDict = CreateObject("Scripting.Dictionary") ' 初始化新字典
    Set regex = CreateObject("VBScript.Regexp")
    ' 获取数据范围
    patternCount = Range("C1048576").End(xlUp).row
    dataCount = Range("A1048576").End(xlUp).row
    ' 检查是否有数据
    If patternCount < 2 Or dataCount < 2 Then
        MsgBox "请确保C列有正则表达式，A列有要处理的文本！", vbExclamation
        GoTo Cleanup
    End If
    ' 读取数据
    regexPatterns = Range("C2:C" & patternCount).Value
    sourceData = Range("A2:A" & dataCount).Value
    ' 准备结果数组
    ReDim matchResults(1 To dataCount - 1, 1 To 1)
    ReDim foundMatches(1 To dataCount - 1, 1 To 1)
    ' 构建正则表达式模式
    If patternCount = 2 Then
        patternStr = regexPatterns
    Else
        ' 优化的数组转置方法
        Dim tempArray() As String
        ReDim tempArray(1 To patternCount - 1)
        For i = 1 To patternCount - 1
            tempArray(i) = regexPatterns(i, 1)
        Next i
        patternStr = Join(tempArray, "|")
    End If
    ' 设置正则表达式属性
    With regex
        .Global = True
        .Pattern = patternStr
    End With
    ' 执行正则匹配
    For i = 1 To dataCount - 1
        currentText = sourceData(i, 1)
        With regex
            ' 替换匹配内容
            matchResults(i, 1) = .Replace(currentText, "xxx")
            ' 检查是否有匹配
            hasMatches = .Test(currentText)
            If Not hasMatches Then
                matchResults(i, 1) = ""
            Else
                ' 只执行一次正则匹配并保存结果
                Set matches = .Execute(currentText)
                Dim matchCount As Long
                matchCount = matches.count
                ' 声明存储匹配值的数组
                Dim matchValues() As String
                ReDim matchValues(0 To matchCount - 1)
                ' 遍历匹配结果并存储到数组中（保留原有高效逻辑）
                Dim m As Long
                For m = 0 To matchCount - 1
                    ' 直接使用matches.Item(m).Value获取匹配值
                    Dim currentMatch As String
                    currentMatch = matches.item(m).Value
                    ' 存储到数组
                    matchValues(m) = currentMatch
                    ' 更新字典计数
                    If matchDict.exists(currentMatch) Then
                        matchDict(currentMatch) = matchDict(currentMatch) + 1
                    Else
                        matchDict(currentMatch) = 1
                    End If
                    ' 记录所有匹配项
                    If foundMatches(i, 1) <> "" Then
                        foundMatches(i, 1) = foundMatches(i, 1) & "|" & currentMatch
                    Else
                        foundMatches(i, 1) = currentMatch
                    End If
                Next m
                ' 新增：使用重复执行.Execute(currentText)的方式填充新字典，保留重复项
                For m = 1 To matchCount
                    ' 重复执行.Execute(currentText)以获取每个匹配项
                    currentMatch = .Execute(currentText)(m - 1)
                    ' 使用唯一键存储重复项，键格式：内容_索引
                    Dim uniqueKey As String
                    uniqueKey = currentMatch & "_" & (duplicateMatchDict.count + 1)
                    duplicateMatchDict.Add uniqueKey, currentMatch
                Next m
            End If
        End With
    Next i

    ' 输出匹配信息
    [i2].Resize(UBound(matchResults), 1).Value = matchResults
    [j2].Resize(UBound(foundMatches), 1).Value = foundMatches
    ' 新增：输出重复项字典内容到第三列（K列）
    If duplicateMatchDict.count > 0 Then
        Dim duplicateArray() As Variant
        ReDim duplicateArray(1 To duplicateMatchDict.count, 1 To 1)
        ' 填充重复项数组
        k = 1
        For Each key In duplicateMatchDict.keys
            duplicateArray(k, 1) = duplicateMatchDict(key)
            k = k + 1
        Next key
        ' 输出到K列
        [K2].Resize(duplicateMatchDict.count, 1).Value = duplicateArray
    End If
      
  ' 处理匹配项的分隔
  If dataCount > 2 Then
      On Error Resume Next
      Range("J:J").TextToColumns Destination:=Range("J1"), DataType:=xlDelimited, _
          TextQualifier:=xlNone, ConsecutiveDelimiter:=False, Tab:=False, _
          Semicolon:=False, Comma:=False, Space:=False, Other:=True, OtherChar:="|"
      On Error GoTo ErrorHandler
  End If
    ' 输出到排序工作表 - 修改为三列数据并添加标题
    If Sheets("排序").Cells(1, 1) = "" Then
        With Sheets("排序")
            ' 1. 按查找顺序排序
            .Cells(1, 1).Value = "- 按查找顺序排序"
            .Cells(2, 1).Resize(matchDict.count, 2).Value = Application.Transpose(Array(matchDict.keys, matchDict.items))
            ' 2. 按词频排序降序
            If matchDict.count > 0 Then
                .Cells(1, 4).Value = "- 按词频降序排序"
                ' 填充数据
                .Cells(2, 4).Resize(matchDict.count, 2).Value = Application.Transpose(Array(matchDict.keys, matchDict.items))
                ' 使用Range.Sort方法进行词频降序排序
                .Range("D1:E" & matchDict.count + 1).Sort key1:=.Range("E2"), Order1:=xlDescending, Header:=xlYes

        End If
        ' 3. 按顺序(去词频)排序
        .Cells(1, 7).Value = "- 按顺序(去词频)排序"
        .Cells(2, 7).Resize(duplicateMatchDict.count, 1).Value = Application.Transpose(duplicateMatchDict.keys)
     .Range("g:g").TextToColumns Destination:=.Range("G1"), DataType:=xlDelimited, _
     TextQualifier:=xlNone, ConsecutiveDelimiter:=False, Tab:=False, _
     Semicolon:=False, Comma:=False, Space:=False, Other:=True, OtherChar:="_"
 ' 自动调整列宽        ' 自动调整列宽
    .Columns.AutoFit
    End With
    
End If
On Error GoTo ErrorHandler
' 显示处理时间
MsgBox "正则查询完成！" & vbCrLf & "处理时间: " & Format(Timer - startTime, "0.000s"), vbInformation
Cleanup:
' 清理资源和恢复Excel设置
On Error Resume Next
Set matchDict = Nothing
Set tempDict = Nothing
Set duplicateMatchDict = Nothing ' 清理新增的字典
Set regex = Nothing
Application.DisplayAlerts = True
Application.ScreenUpdating = True
Application.Calculation = xlCalculationAutomatic
Application.EnableEvents = True
Exit Sub
ErrorHandler:
' 错误处理
MsgBox "发生错误: " & err.Description & vbCrLf & "错误代码: " & err.number, vbCritical
GoTo Cleanup
End Sub

' 正则查询优化2函数
Sub 正则查询优化2()
    ' 错误处理和性能优化
    On Error GoTo ErrorHandler
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Application.EnableEvents = False
    Dim startTime As Double: startTime = Timer
    ' 清除结果区域
    Range("G2:H1048576").Clear
    ' 声明变量
    Dim regexPatterns As Variant, sourceData As Variant
    Dim matchResults As Variant
    Dim matchDict As Object
    Dim regex As Object
    Dim patternCount As Long, dataCount As Long
    Dim i As Long
    Dim currentText As String, patternStr As String
    Dim matches As Object, match As Object
    Dim hasMatches As Boolean
    ' 初始化对象
    Set matchDict = CreateObject("Scripting.Dictionary")
    Set regex = CreateObject("VBScript.Regexp")
    ' 获取数据范围
    patternCount = Range("D1048576").End(xlUp).row
    dataCount = Range("E1048576").End(xlUp).row
    ' 检查是否有数据
    If patternCount < 2 Or dataCount < 2 Then
        MsgBox "请确保D列有正则表达式，E列有要处理的文本！", vbExclamation
        GoTo Cleanup
    End If
    ' 读取数据
    regexPatterns = Range("D2:D" & patternCount).Value
    sourceData = Range("E2:E" & dataCount).Value
    ' 准备结果数组
    ReDim matchResults(1 To dataCount - 1, 1 To 1)
    ' 构建正则表达式模式
    If patternCount = 2 Then
        patternStr = regexPatterns(1, 1)
    Else
        ' 优化的数组转置方法
        Dim tempArray() As String
        ReDim tempArray(1 To patternCount - 1)
        For i = 1 To patternCount - 1
            tempArray(i) = regexPatterns(i, 1)
        Next i
        patternStr = Join(tempArray, "|")
    End If
    ' 设置正则表达式属性
    With regex
        .Global = True
        .Pattern = patternStr
    End With
    ' 执行正则匹配
    For i = 1 To dataCount - 1
        currentText = sourceData(i, 1)
        With regex
            ' 替换匹配内容
            matchResults(i, 1) = .Replace(currentText, "xxx")
            ' 检查是否有匹配
            hasMatches = .Test(currentText)
            If Not hasMatches Then
                ' 不匹配时保留原文本
                matchResults(i, 1) = currentText
            Else
                ' 处理匹配项并统计
                Set matches = .Execute(currentText)
                For Each match In matches
                    ' 更新匹配计数
                    If matchDict.exists(match.Value) Then
                        matchDict(match.Value) = matchDict(match.Value) + 1
                    Else
                        matchDict(match.Value) = 1
                    End If
                Next match
            End If
        End With
    Next i
    ' 输出结果
    [G2].Resize(UBound(matchResults), 1).Value = matchResults
    ' 输出匹配到的模式
    If matchDict.count > 0 Then
        [h2].Resize(matchDict.count, 1).Value = Application.WorksheetFunction.Transpose(matchDict.keys)
    End If
    ' 显示处理时间
    MsgBox "正则查询2完成！" & vbCrLf & "处理时间: " & Format(Timer - startTime, "0.000s"), vbInformation
Cleanup:
    ' 清理资源和恢复Excel设置
    On Error Resume Next
    Set matchDict = Nothing
    Set regex = Nothing
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True
    Exit Sub
ErrorHandler:
    ' 错误处理
    MsgBox "发生错误: " & err.Description & vbCrLf & "错误代码: " & err.number, vbCritical
    GoTo Cleanup
End Sub

' 正则替换优化函数
Sub 正则替换优化()
    ' 错误处理和性能优化
    On Error GoTo ErrorHandler
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Application.EnableEvents = False
    Dim startTime As Double: startTime = Timer
    ' 声明变量
    Dim replacementData As Variant, sourceData As Variant
    Dim resultData() As Variant
    Dim replacements As Object
    Dim regex As Object
    Dim key As Variant
    Dim replacementCount As Long, replacementCount2 As Long, dataCount As Long
    Dim i As Long, j As Long
    Dim combinedText As String
    Dim textArray As Variant
    ' 初始化对象
    Set replacements = CreateObject("Scripting.Dictionary")
    Set regex = CreateObject("VBScript.Regexp")
    ' 获取数据范围
    replacementCount = Range("C1048576").End(xlUp).row
    replacementCount2 = Range("D1048576").End(xlUp).row
    dataCount = Range("A1048576").End(xlUp).row
    ' 检查是否有数据
    If replacementCount < 2 Or dataCount < 2 Or replacementCount2 < 2 Then
        MsgBox "请确保C列和D列有替换规则，A列有要处理的文本！", vbExclamation
        GoTo Cleanup
    End If
    ' 读取数据
    replacementData = Range("C2:D" & replacementCount).Value
    sourceData = Range("A2:A" & dataCount).Value
    ' 准备结果数组
    ReDim resultData(1 To dataCount - 1, 1 To 1)
    ' 构建替换字典
    For i = 1 To replacementCount - 1
        If Not replacements.exists(replacementData(i, 1)) Then
            replacements.Add replacementData(i, 1), replacementData(i, 2)
        End If
    Next i
    ' 合并源文本以便批量处理
    combinedText = ""
    For i = 1 To dataCount - 1
        combinedText = combinedText & sourceData(i, 1) & vbCr
    Next i
    ' 设置正则表达式属性
    With regex
        .Global = True
        .IgnoreCase = True ' 忽略大小写
        ' 执行批量替换
        For Each key In replacements.keys
            .Pattern = key
            combinedText = .Replace(combinedText, replacements(key))
        Next key
    End With
    ' 拆分文本并填充结果数组
    textArray = Split(combinedText, vbCr)
    For j = 1 To dataCount - 1
        If j - 1 <= UBound(textArray) Then
            resultData(j, 1) = textArray(j - 1)
        End If
    Next j
    ' 输出结果
    [i2].Resize(UBound(resultData), 1).Value = resultData
    Dim ws As Worksheet
    Set ws = GetOrInitWorksheet("替换后文本")
    ws.[a1].Resize(UBound(resultData), 1).Value = resultData
    ' 显示处理时间
    MsgBox "正则替换完成！" & vbCrLf & "处理时间: " & Format(Timer - startTime, "0.000s") & vbCrLf & "处理行数: " & dataCount - 1, vbInformation
Cleanup:
    ' 清理资源和恢复Excel设置
    On Error Resume Next
    Set replacements = Nothing
    Set regex = Nothing
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True
    Exit Sub
ErrorHandler:
    ' 错误处理
    MsgBox "发生错误: " & err.Description & vbCrLf & "错误代码: " & err.number, vbCritical
    GoTo Cleanup
End Sub

' 正则后辅助目录优化函数
Sub 正则后辅助目录优化()
    ' 错误处理和性能优化
    On Error GoTo ErrorHandler
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Dim startTime As Double: startTime = Timer
    ' 声明变量
    Dim dataCount As Long
    Dim directoryData As Variant, validDirectories As Variant
    Dim lastValidDir As String
    Dim i As Long, j As Long
    ' 获取数据范围
    dataCount = Range("A1048576").End(xlUp).row
    ' 检查是否有数据
    If dataCount < 2 Then
        MsgBox "请确保A列有要处理的数据！", vbExclamation
        GoTo Cleanup
    End If
    ' 读取目录数据
    directoryData = Range("J2:J" & dataCount).Value
    ' 准备有效目录数组
    ReDim validDirectories(1 To dataCount - 1, 1 To 1)
    j = 0
    ' 处理目录数据
    For i = 1 To dataCount - 1
        If directoryData(i, 1) <> "" Then
            ' 保存有效目录
            lastValidDir = directoryData(i, 1)
            j = j + 1
            validDirectories(j, 1) = lastValidDir
        Else
            ' 空目录时使用上一个有效目录
            If lastValidDir <> "" Then
                directoryData(i, 1) = lastValidDir
            End If
        End If
    Next i

    ' 输出结果
    [b2].Resize(dataCount - 1, 1).Value = directoryData
    ' 输出到目录工作表
    If j > 0 Then
        Sheets("目录").Cells(5, 1).Resize(j, 1).Value = validDirectories
    End If
    ' 显示处理时间
    MsgBox "目录处理完成！" & vbCrLf & "处理时间: " & Format(Timer - startTime, "0.000s") & vbCrLf & "有效目录数量: " & j, vbInformation
Cleanup:
    ' 恢复Excel设置
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Exit Sub
ErrorHandler:
    ' 错误处理
    MsgBox "发生错误: " & err.Description & vbCrLf & "错误代码: " & err.number, vbCritical
    GoTo Cleanup
End Sub

