Attribute VB_Name = "READ_字频音"
Sub 字频音统计()
    ' 简化版字频音统计 - 移除全文显示，精简逻辑
    On Error GoTo ErrorHandler
    
    ' 核心变量声明
    Dim wordapp As Object, worddoc As Object
    Dim wdFile As String
    Dim Dic As Object
    Dim Text2 As String
    Dim text As String
    Dim n As Long, i As Long
    Dim Reg As Object
    Dim startTime As Single
    Dim wsResult As Worksheet
    Dim lastRow As Long
    Dim Word As String
    
    ' 性能优化设置
    startTime = Timer
    With Application
        .DisplayAlerts = False
        .ScreenUpdating = False
        .Calculation = xlCalculationManual
        .EnableEvents = False
    End With
    
    ' 选择文件
    wdFile = FileSelected
    If wdFile = "" Then
        GoTo Cleanup
    End If
    
    ' 创建字典对象用于字频统计
    Set Dic = CreateObject("Scripting.Dictionary")
    
    ' 创建正则表达式对象，用于提取中文字符
    Set Reg = CreateObject("vbscript.regexp")
    With Reg
        .Global = True
        .Pattern = "[^\u4e00-\u9fa5]"
    End With
    
    ' 打开Word文件并提取内容
    Set wordapp = CreateObject("Word.Application")
    wordapp.Visible = False
    Set worddoc = wordapp.Documents.Open(wdFile)
    
    ' 提取文本并过滤出中文字符
    text = worddoc.Range.text
    Text2 = Reg.Replace(text, "")
    
    ' 释放Word资源
    worddoc.Close SaveChanges:=False
    wordapp.Quit
    Set worddoc = Nothing
    Set wordapp = Nothing
    
    ' 获取中文字符数量并统计字频
    n = Len(Text2)
    If n = 0 Then
        MsgBox "文档中未找到中文字符！", vbInformation
        GoTo Cleanup
    End If
    
    ' 简化版字频统计 - 直接遍历字符串，避免额外数组
    For i = 1 To n
        Word = Mid(Text2, i, 1)
        Dic(Word) = Dic(Word) + 1
    Next i
    
    ' 创建结果工作表
    Set wsResult = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets("目录"))
    wsResult.Name = "字频音_" & Format(Now, "yyyyMMdd_HHmmss")
    
    ' 设置表头和统计信息
    With wsResult
        .Cells(1, 1) = "字"
        .Cells(1, 2) = "频率"
        .Cells(1, 3) = "拼音"
        .Cells(1, 4) = "全文字数"
        .Cells(2, 4) = n
        .Cells(3, 4) = "不重复字数"
        .Cells(4, 4) = Dic.count
        
        ' 应用表头格式
        .Range("A1:C1").Font.Bold = True
        .Range("D1:D4").Font.Bold = True
        
        ' 输出字频数据
        lastRow = Dic.count + 1
        If lastRow > 1 Then
            .Range("A2").Resize(lastRow - 1, 1) = Application.WorksheetFunction.Transpose(Dic.keys)
            .Range("B2").Resize(lastRow - 1, 1) = Application.WorksheetFunction.Transpose(Dic.items)
            
            ' 按频率降序排序
            .Range("A1:B" & lastRow).Sort key1:=.Range("B2"), Order1:=xlDescending, Header:=xlYes
            
            ' 生成拼音
            Call 生成拼音(wsResult, lastRow)
            
            ' 自动调整列宽
            .Columns("A:C").AutoFit
        End If
    End With
    
    ' 完成提示
    MsgBox "字频统计完成！" & vbCrLf & _
           "全文字数: " & n & vbCrLf & _
           "不重复字数: " & Dic.count & vbCrLf & _
           "耗时: " & Format(Timer - startTime, "0.00") & " 秒", vbInformation
    
Cleanup:
    ' 释放资源并恢复Excel设置
    Set Dic = Nothing
    Set Reg = Nothing
    With Application
        .DisplayAlerts = True
        .ScreenUpdating = True
        .Calculation = xlCalculationAutomatic
        .EnableEvents = True
    End With
    Exit Sub
    
ErrorHandler:
    ' 错误处理
    MsgBox "错误: " & err.Description & vbCrLf & _
           "错误代码: " & err.number, vbCritical
    GoTo Cleanup
End Sub



' 生成拼音函数（优化版本）
Sub 生成拼音(ws As Worksheet, lastRow As Long)
    Dim pinyinArray() As Variant
    Dim i As Long
    
    ' 避免不必要的数组操作
    If lastRow > 1 Then
        For i = 2 To lastRow
            On Error Resume Next
            ws.Cells(i, 3).Value = getpy(ws.Cells(i, 1).Value)
            On Error GoTo 0
        Next i
    End If
End Sub

Function FileSelected() As String
    With Application.FileDialog(msoFileDialogFilePicker)
        .Title = "请选择文档文件"
        .AllowMultiSelect = False
        .filters.Clear
        .filters.Add "文本文件", "*.txt"
        .filters.Add "Word文件", "*.doc;*.docx;*.docm"
        .filters.Add "所有文件", "*.*"
        .InitialFileName = ThisWorkbook.Path
        If .Show = -1 Then
            FileSelected = .SelectedItems(1)
        Else
            FileSelected = ""
        End If
    End With
End Function


