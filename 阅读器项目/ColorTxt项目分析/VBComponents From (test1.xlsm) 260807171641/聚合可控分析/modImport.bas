Attribute VB_Name = "modImport"
Option Explicit

'==============================================================================
' Phase 1: TXT 导入与数据源工作表构建
'   功能: 读取TXT文件 → 按行分割 → 写入"数据源"工作表A列
'   优化: 批量写入(数组→Range) 替代逐行Cells赋值, 性能提升100x+
'   工作表结构: 数据源!A列=文本行, B列=目录标记, C列=正则标记
'==============================================================================

'------------------------------------------------------------------------------
' 导入TXT到数据源工作表
'   参数: filePath - TXT文件路径
'   返回: 导入行数 (失败返回0)
'   副作用: 创建或清空"数据源"工作表, A列写入文本
'------------------------------------------------------------------------------
Public Function ImportTxtToDataSource(ByVal filePath As String) As Long
    Dim ws As Worksheet
    Dim content As String, lines() As String, lineCount As Long
    Dim enc As String
    Dim i As Long
    Dim t0 As Double
    
    t0 = Timer
    
    ' 1. 检测编码并读取
    enc = DetectEncoding(filePath)
    Debug.Print "[Phase1] 编码: " & enc & " (" & GetEncodingName(enc) & ")"
    
    content = ReadTextAuto(filePath)
    If Len(content) = 0 Then
        MsgBox "文件内容为空: " & filePath, vbExclamation, "导入失败"
        ImportTxtToDataSource = 0
        Exit Function
    End If
    
    ' 2. 统一换行符 → 按行分割
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    
    Debug.Print "[Phase1] 总行数: " & lineCount
    
    ' 3. 获取或创建"数据源"工作表
    Set ws = GetOrCreateSheet("数据源")
    
    ' 4. 清空旧数据 (保留表头)
    ws.Cells.Clear
    ws.Range("A1").Value = "文本行"
    ws.Range("B1").Value = "目录标记"
    ws.Range("C1").Value = "正则标记"
    ws.Range("A1:C1").Font.Bold = True
    
    ' 5. 批量写入 (优化: 数组→Range, 避免逐行赋值)
    If lineCount > 0 Then
        Dim outputData() As Variant
        ReDim outputData(1 To lineCount, 1 To 1)
        
        For i = 0 To lineCount - 1
            outputData(i + 1, 1) = lines(i)
        Next i
        
        ws.Range("A2").Resize(lineCount, 1).Value = outputData
    End If
    
    ' 6. 格式设置
    ws.Columns("A").AutoFit
    ws.Range("A1:C1").Interior.Color = RGB(217, 225, 242)
    
    Debug.Print "[Phase1] 导入完成, 耗时: " & Format(Timer - t0, "0.00") & "s"
    ImportTxtToDataSource = lineCount
End Function

'------------------------------------------------------------------------------
' 从数据源工作表读取文本行数组
'   返回: lines() 字符串数组, lines(0) 为第一行文本
'------------------------------------------------------------------------------
Public Function ReadLinesFromDataSource() As String()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim arr As Variant
    Dim lines() As String
    Dim i As Long
    
    Set ws = ThisWorkbook.Worksheets("数据源")
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    
    If lastRow < 2 Then
        ReDim lines(0 To 0)
        lines(0) = ""
        ReadLinesFromDataSource = lines
        Exit Function
    End If
    
    arr = ws.Range("A2:A" & lastRow).Value
    ReDim lines(0 To UBound(arr, 1) - 1)
    
    For i = 1 To UBound(arr, 1)
        lines(i - 1) = CStr(arr(i, 1))
    Next i
    
    ReadLinesFromDataSource = lines
End Function

'==============================================================================
' 工作表工具函数
'==============================================================================

' 获取或创建工作表 (不存在则创建)
Public Function GetOrCreateSheet(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set GetOrCreateSheet = ThisWorkbook.Worksheets(sheetName)
    If Err.Number <> 0 Then
        Err.Clear
        Set GetOrCreateSheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        GetOrCreateSheet.Name = sheetName
    End If
    On Error GoTo 0
End Function

' 安全清空工作表 (保留表头行)
Public Sub ClearSheetData(ByVal sheetName As String, Optional ByVal keepHeader As Boolean = True)
    Dim ws As Worksheet
    Set ws = GetOrCreateSheet(sheetName)
    
    If keepHeader Then
        Dim lastRow As Long, lastCol As Long
        lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
        lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
        If lastRow > 1 Then
            ws.Range("A2:" & GetColLetter(lastCol) & lastRow).Clear
        End If
    Else
        ws.Cells.Clear
    End If
End Sub

' 列号转字母 (1→A, 27→AA)
Public Function GetColLetter(ByVal colNum As Long) As String
    GetColLetter = ""
    Do While colNum > 0
        GetColLetter = Chr(65 + (colNum - 1) Mod 26) & GetColLetter
        colNum = (colNum - 1) \ 26
    Loop
End Function

' 选择TXT文件对话框
Public Function SelectTxtFile(Optional ByVal title As String = "选择TXT文件") As String
    Dim fd As Object
    Set fd = Application.FileDialog(3) ' msoFileDialogFilePicker
    fd.Title = title
    fd.Filters.Clear
    fd.Filters.Add "文本文件", "*.txt"
    fd.Filters.Add "所有文件", "*.*"
    
    If fd.Show = -1 Then
        SelectTxtFile = fd.SelectedItems(1)
    Else
        SelectTxtFile = ""
    End If
End Function
