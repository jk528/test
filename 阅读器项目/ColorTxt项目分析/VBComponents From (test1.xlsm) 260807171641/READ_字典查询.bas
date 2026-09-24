Attribute VB_Name = "READ_字典查询"
Option Explicit

' 主查询函数 - 从界面获取查询词并显示结果
Sub 字典查询()
    Dim startTime As Double
    Dim searchTerm As String
    Dim resultCount As Long
    Dim searchResult As Collection
    Dim frequencyDict As Object
    Dim resultArray() As Variant
    Dim frequencyArray() As Variant
    
    On Error GoTo ErrorHandler
    
    ' 记录开始时间
    startTime = Timer
Application.ScreenUpdating = False

    ' 清空之前的查询结果
    Sheets("查询").Range("A6:D1048576").ClearContents
    
    ' 获取查询词
    searchTerm = Trim(Sheets("查询").Range("B3"))
    If searchTerm = "" Then
        MsgBox "请输入查询词", vbExclamation, "提示"
        Exit Sub
    End If
    
    ' 执行查询
    Set frequencyDict = CreateObject("Scripting.Dictionary")
    Set searchResult = ExecuteSearch(searchTerm, frequencyDict, resultCount)
    
    ' 如果有结果，显示结果
    If resultCount > 0 Then
        ' 转换结果为数组并显示
        resultArray = ConvertCollectionToArray(searchResult, 2)
        Sheets("查询").Range("A6").Resize(UBound(resultArray, 1), UBound(resultArray, 2)) = resultArray
        
        ' 显示频率统计
        frequencyArray = GetFrequencyArray(frequencyDict)
        Sheets("查询").Range("C6").Resize(UBound(frequencyArray, 1), UBound(frequencyArray, 2)) = frequencyArray
        
        ' 更新后台数据
        UpdateBackendData searchTerm, resultCount, frequencyDict
    Else
        MsgBox "未找到匹配的结果", vbInformation, "提示"
    End If
    Dim ws As Worksheet
    Set ws = GetOrInitWorksheet(searchTerm)
    ws.[a1].Resize(UBound(resultArray), 1).Value = resultArray
    ws.Activate
    DictionarySortByColumnA
    Sheets("查询").Activate
  Application.ScreenUpdating = True
    ' 显示执行时间
    MsgBox "查询完成，共找到 " & resultCount & " 条结果\n执行时间: " & Format(Timer - startTime, "0.000s"), vbInformation, "查询结果"
    Exit Sub
    
ErrorHandler:
    MsgBox "查询过程中发生错误: " & err.Description, vbCritical, "错误"
End Sub

' 辅助查询函数 - 接收查询词参数进行查询
Private Sub 字典查询2(searchTerm As Variant)
    Dim startTime As Double
    Dim resultCount As Long
    Dim searchResult As Collection
    Dim frequencyDict As Object
    
    On Error GoTo ErrorHandler
    
    ' 记录开始时间
    startTime = Timer
    
'    ' 验证输入参数
'    If IsEmpty(searchTerm) Or Trim(searchTerm) = "" Then
'        Debug.Print "无效的查询词"
'        Exit Sub
'    End If
    
    ' 执行查询
    Set frequencyDict = CreateObject("Scripting.Dictionary")
    Set searchResult = ExecuteSearch(CStr(searchTerm), frequencyDict, resultCount)
    
    ' 更新后台数据
    UpdateBackendData CStr(searchTerm), resultCount, frequencyDict, True
    
    ' 输出执行时间到调试窗口
    Debug.Print "查询词: " & CStr(searchTerm) & ", 结果数: " & resultCount & ", 执行时间: " & Format(Timer - startTime, "0.000s")
    Exit Sub
    
ErrorHandler:
    Debug.Print "查询过程中发生错误: " & err.Description
End Sub

' 批量词条查询
Sub 批量词条查询()
    Dim selectedRange As Range
    Dim cell As Range
    Dim totalQueries As Long
    Dim startTime As Double
    
    On Error GoTo ErrorHandler
    
    ' 记录开始时间
    startTime = Timer
    totalQueries = 0
    Application.ScreenUpdating = True
    ' 获取用户选择的范围
    Set selectedRange = Application.InputBox(prompt:="请选择要查询的词条范围:", Type:=8)
    Application.ScreenUpdating = False
    ' 验证选择
    If selectedRange Is Nothing Then
        Exit Sub
    End If
    
    ' 对每个单元格进行查询
    For Each cell In selectedRange
        If Not IsEmpty(cell.Value) And Trim(cell.Value) <> "" Then
            字典查询2 cell.Value
            totalQueries = totalQueries + 1
        End If
    Next cell
    
    ' 显示总查询数和总时间
    MsgBox "批量查询完成\n总查询数: " & totalQueries & "\n总执行时间: " & Format(Timer - startTime, "0.000s"), vbInformation, "批量查询"
    Exit Sub
    
ErrorHandler:
'    MsgBox "批量查询过程中发生错误: " & err.Description, vbCritical, "错误"
End Sub

' 执行搜索的核心函数
Private Function ExecuteSearch(searchTerm As String, ByRef frequencyDict As Object, ByRef resultCount As Long) As Collection
    Dim dataSheet As Worksheet
    Dim lastRow As Long
    Dim dataArray As Variant
    Dim i As Long
    Dim resultColl As New Collection
    
    ' 设置数据源
    Set dataSheet = Sheets("数据源")
    lastRow = dataSheet.Cells(dataSheet.rows.count, 1).End(xlUp).row
    
    ' 读取数据到数组
    If lastRow >= 2 Then
        dataArray = dataSheet.Range("A2:B" & lastRow).Value
        
        ' 搜索匹配项并统计频率
        For i = 1 To UBound(dataArray, 1)
            If dataArray(i, 1) Like "*" & searchTerm & "*" Then
                ' 添加到结果集合
                resultColl.Add Array(dataArray(i, 1), dataArray(i, 2))
                
                ' 更新频率统计
                If frequencyDict.exists(dataArray(i, 2)) Then
                    frequencyDict(dataArray(i, 2)) = frequencyDict(dataArray(i, 2)) + 1
                Else
                    frequencyDict(dataArray(i, 2)) = 1
                End If
            End If
        Next i
    End If
    
    ' 设置结果计数
    resultCount = resultColl.count
    
    ' 返回结果
    Set ExecuteSearch = resultColl
End Function

' 将集合转换为二维数组
Private Function ConvertCollectionToArray(sourceColl As Collection, columnsCount As Long) As Variant()
    Dim resultArray() As Variant
    Dim i As Long, j As Long
    Dim itemArray As Variant
    
    ' 调整数组大小
    ReDim resultArray(1 To sourceColl.count, 1 To columnsCount)
    
    ' 填充数组
    For i = 1 To sourceColl.count
        itemArray = sourceColl(i)
        For j = 1 To columnsCount
            If j <= UBound(itemArray) + 1 Then
                resultArray(i, j) = itemArray(j - 1)
            End If
        Next j
    Next i
    
    ' 返回数组
    ConvertCollectionToArray = resultArray
End Function

' 获取频率统计数组
Private Function GetFrequencyArray(frequencyDict As Object) As Variant()
    Dim resultArray() As Variant
    Dim keys() As Variant
    Dim items() As Variant
    Dim i As Long
    
    ' 获取键和值
    keys = frequencyDict.keys
    items = frequencyDict.items
    
    ' 调整数组大小
    ReDim resultArray(1 To frequencyDict.count, 1 To 2)
    
    ' 填充数组
    For i = 0 To frequencyDict.count - 1
        resultArray(i + 1, 1) = keys(i)
        resultArray(i + 1, 2) = items(i)
    Next i
    
    ' 返回数组
    GetFrequencyArray = resultArray
End Function

' 更新后台数据
Private Sub UpdateBackendData(searchTerm As String, resultCount As Long, frequencyDict As Object, Optional isBatchMode As Boolean = False)
    Dim backendSheet As Worksheet
    Dim lastRow As Long
    Dim lastColumn As Long
    Dim categoryArray As Variant
    Dim i As Long
    
    ' 设置目录表
    Set backendSheet = Sheets("目录")
    lastRow = backendSheet.Cells(backendSheet.rows.count, 1).End(xlUp).row
    lastColumn = backendSheet.Cells(1, backendSheet.Columns.count).End(xlToLeft).Column + 1
    
    ' 读取类别数据
    If lastRow >= 1 Then
        categoryArray = backendSheet.Range("A1:A" & lastRow).Value
        
        ' 填充频率数据
        For i = 1 To UBound(categoryArray, 1)
            If frequencyDict.exists(categoryArray(i, 1)) Then
                categoryArray(i, 1) = frequencyDict(categoryArray(i, 1))
            ElseIf isBatchMode Then
                categoryArray(i, 1) = 0
            Else
                categoryArray(i, 1) = 0
            End If
        Next i
        
        ' 写入数据
        backendSheet.Cells(1, lastColumn).Resize(lastRow) = categoryArray
        backendSheet.Cells(1, lastColumn) = resultCount
        backendSheet.Cells(2, lastColumn) = searchTerm
        
'        ' 如果是批量模式，添加空行
'        If isBatchMode Then
            backendSheet.Cells(3, lastColumn) = ""
            backendSheet.Cells(4, lastColumn) = ""
'        End If
    End If
End Sub


