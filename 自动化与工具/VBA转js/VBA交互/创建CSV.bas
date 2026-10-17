Attribute VB_Name = "CSV创建方法"
' ================================================
' CSV文件创建方法全览
' 支持4种主要方法: FilesystemObject, Workbook.SaveAs, ADO.Stream, Open语句
' ================================================

' 引用设置:
' FilesystemObject: 引用 Microsoft Scripting Runtime
' ADO.Stream: 引用 Microsoft ActiveX Data Objects x.x Library

' ================================================
' 1. FilesystemObject方法
' 优点: 功能丰富，可读性强，支持Unicode
' 缺点: 需要引用Scripting库
' ================================================

Sub CreateCSVWithFSO(filePath As String, data As Variant, Optional delimiter As String = ",", Optional writeUnicode As Boolean = True)
    ' 功能: 使用FileSystemObject创建CSV文件
    ' 参数:
    '   filePath - 文件路径
    '   data - 数据数组 (二维)
    '   delimiter - 分隔符，默认为逗号
    '   writeUnicode - 是否使用Unicode编码，默认为True
    
    Dim fso As Scripting.FileSystemObject
    Dim ts As Scripting.TextStream
    Dim i As Long, j As Long
    Dim line As String
    
    ' 创建FileSystemObject
    Set fso = New Scripting.FileSystemObject
    
    ' 创建文本流
    If writeUnicode Then
        Set ts = fso.CreateTextFile(filePath, True, True)  ' Unicode (UTF-16)
    Else
        Set ts = fso.CreateTextFile(filePath, True, False) ' ASCII
    End If
    
    ' 写入数据
    For i = LBound(data, 1) To UBound(data, 1)
        line = ""
        For j = LBound(data, 2) To UBound(data, 2)
            If j > LBound(data, 2) Then line = line & delimiter
            line = line & CStr(data(i, j))
        Next j
        ts.WriteLine line
    Next i
    
    ts.Close
    Set ts = Nothing
    Set fso = Nothing
    
    Debug.Print "CSV文件创建完成 (FSO): " & filePath
End Sub

' ================================================
' 2. Workbook.SaveAs方法
' 优点: 最简单，速度最快，Excel原生支持
' 缺点: 受Excel格式限制
' ================================================

Sub ExportToCSV_ANSI(filePath As String, ws As Worksheet)
    ' 功能: 使用Workbook.SaveAs导出ANSI编码CSV
    ' 参数:
    '   filePath - 目标文件路径
    '   ws - 要导出的工作表
    
    Dim wb As Workbook
    Dim originalFile As String
    
    ' 获取原始文件路径
    originalFile = ActiveWorkbook.FullName
    
    ' 复制工作表到新工作簿
    ws.Copy
    Set wb = ActiveWorkbook
    
    ' 保存为CSV (ANSI编码)
    wb.SaveAs filePath, xlCSV
    
    ' 关闭新工作簿
    wb.Close False
    
    Debug.Print "ANSI CSV导出完成: " & filePath
End Sub

Sub ExportToCSV_UTF8(filePath As String, ws As Worksheet)
    ' 功能: 使用Workbook.SaveAs导出UTF-8编码CSV
    ' 参数:
    '   filePath - 目标文件路径
    '   ws - 要导出的工作表
    
    Dim wb As Workbook
    
    ' 复制工作表到新工作簿
    ws.Copy
    Set wb = ActiveWorkbook
    
    ' 尝试保存为UTF-8 CSV
    ' 注意: xlCSVUTF8 在某些Excel版本中可能不可用
    On Error Resume Next
    wb.SaveAs filePath, xlCSVUTF8
    On Error GoTo 0
    
    ' 如果不支持xlCSVUTF8，降级到普通CSV
    If Err.Number <> 0 Then
        Debug.Print "xlCSVUTF8不支持，降级到普通CSV"
        wb.SaveAs filePath, xlCSV
    End If
    
    wb.Close False
    
    Debug.Print "UTF-8 CSV导出完成: " & filePath
End Sub

' ================================================
' 3. ADO.Stream方法
' 优点: 内存效率高，支持大文件，精确编码控制
' 缺点: 需要引用ADODB库
' ================================================

Sub CreateCSVWithADO(filePath As String, data As Variant, Optional delimiter As String = ",", Optional includeBOM As Boolean = True)
    ' 功能: 使用ADO.Stream创建UTF-8 CSV文件
    ' 参数:
    '   filePath - 文件路径
    '   data - 数据数组
    '   delimiter - 分隔符
    '   includeBOM - 是否包含BOM，默认为True
    
    Dim stream As ADODB.Stream
    Dim i As Long, j As Long
    Dim line As String
    Dim utf8Bom As String
    
    ' UTF-8 BOM
    utf8Bom = Chr(&HEF) & Chr(&HBB) & Chr(&HBF)
    
    ' 创建Stream对象
    Set stream = New ADODB.Stream
    stream.Type = adTypeText
    stream.Charset = "UTF-8"
    stream.Open
    
    ' 写入BOM (如果需要)
    If includeBOM Then
        stream.WriteText utf8Bom
    End If
    
    ' 写入数据
    For i = LBound(data, 1) To UBound(data, 1)
        line = ""
        For j = LBound(data, 2) To UBound(data, 2)
            If j > LBound(data, 2) Then line = line & delimiter
            line = line & CStr(data(i, j))
        Next j
        stream.WriteText line & vbCrLf
    Next i
    
    ' 保存到文件
    stream.SaveToFile filePath, adSaveCreateOverWrite
    stream.Close
    
    Set stream = Nothing
    Debug.Print "ADO Stream CSV创建完成: " & filePath & " (UTF-8" & IIf(includeBOM, " with BOM", " no BOM") & ")"
End Sub

' ================================================
' 4. Open语句方法 (轻量级)
' 优点: VBA原生，无需引用，最快速度
' 缺点: 仅支持ANSI编码
' ================================================

Sub CreateCSVWithOpen(filePath As String, data As Variant, Optional delimiter As String = ",")
    ' 功能: 使用VBA原生Open语句创建CSV文件
    ' 参数:
    '   filePath - 文件路径
    '   data - 数据数组
    '   delimiter - 分隔符
    
    Dim fileNum As Integer
    Dim i As Long, j As Long
    Dim line As String
    
    ' 获取可用文件号
    fileNum = FreeFile
    
    ' 打开文件用于写入
    Open filePath For Output As #fileNum
    
    ' 写入数据
    For i = LBound(data, 1) To UBound(data, 1)
        line = ""
        For j = LBound(data, 2) To UBound(data, 2)
            If j > LBound(data, 2) Then line = line & delimiter
            line = line & CStr(data(i, j))
        Next j
        Print #fileNum, line
    Next i
    
    ' 关闭文件
    Close #fileNum
    
    Debug.Print "Open语句 CSV创建完成: " & filePath & " (ANSI编码)"
End Sub

' ================================================
' 辅助函数 - 生成测试数据
' ================================================

Function GenerateTestData(rows As Long, cols As Long) As Variant
    ' 生成测试数据
    Dim data() As Variant
    Dim i As Long, j As Long
    
    ReDim data(1 To rows, 1 To cols)
    
    ' 表头
    For j = 1 To cols
        data(1, j) = "列" & j
    Next j
    
    ' 数据行
    For i = 2 To rows
        For j = 1 To cols
            data(i, j) = "数据" & i & "_" & j
        Next j
    Next i
    
    GenerateTestData = data
End Function

Sub CreateEmployeeTestData(filePath As String, method As String)
    ' 创建员工测试数据并保存为CSV
    Dim data As Variant
    Dim i As Long
    
    ReDim data(1 To 11, 1 To 5)
    
    ' 表头
    data(1, 1) = "姓名"
    data(1, 2) = "年龄"
    data(1, 3) = "城市"
    data(1, 4) = "薪资"
    data(1, 5) = "部门"
    
    ' 数据行
    Dim names As Variant
    Dim cities As Variant
    Dim departments As Variant
    
    names = Array("张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "王十二")
    cities = Array("北京", "上海", "广州", "深圳", "杭州")
    departments = Array("技术部", "销售部", "人事部", "财务部")
    
    For i = 2 To 11
        data(i, 1) = names(i - 2)
        data(i, 2) = 20 + (i - 2) * 2
        data(i, 3) = cities((i - 2) Mod 5)
        data(i, 4) = 5000 + (i - 2) * 1000
        data(i, 5) = departments((i - 2) Mod 4)
    Next i
    
    ' 根据方法创建CSV
    Select Case method
        Case "FSO"
            CreateCSVWithFSO filePath, data
        Case "ADO_BOM"
            CreateCSVWithADO filePath, data, ",", True
        Case "ADO_NO_BOM"
            CreateCSVWithADO filePath, data, ",", False
        Case "OPEN"
            CreateCSVWithOpen filePath, data
        Case "SAVEAS_ANSI"
            CreateTestWorkbookAndExportANSI filePath
        Case "SAVEAS_UTF8"
            CreateTestWorkbookAndExportUTF8 filePath
    End Select
End Sub

' ================================================
' 测试工作簿创建函数
' ================================================

Sub CreateTestWorkbookAndExportANSI(filePath As String)
    Dim wb As Workbook
    Dim ws As Worksheet
    Dim i As Long
    
    Set wb = Workbooks.Add
    Set ws = wb.Worksheets(1)
    
    ' 创建测试数据
    ws.Cells(1, 1).Value = "姓名"
    ws.Cells(1, 2).Value = "年龄"
    ws.Cells(1, 3).Value = "城市"
    ws.Cells(1, 4).Value = "薪资"
    ws.Cells(1, 5).Value = "部门"
    
    Dim names As Variant
    Dim cities As Variant
    Dim departments As Variant
    
    names = Array("张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "王十二")
    cities = Array("北京", "上海", "广州", "深圳", "杭州")
    departments = Array("技术部", "销售部", "人事部", "财务部")
    
    For i = 2 To 11
        ws.Cells(i, 1).Value = names(i - 2)
        ws.Cells(i, 2).Value = 20 + (i - 2) * 2
        ws.Cells(i, 3).Value = cities((i - 2) Mod 5)
        ws.Cells(i, 4).Value = 5000 + (i - 2) * 1000
        ws.Cells(i, 5).Value = departments((i - 2) Mod 4)
    Next i
    
    ' 导出为CSV (ANSI)
    wb.SaveAs filePath, xlCSV
    
    wb.Close False
    Set ws = Nothing
    Set wb = Nothing
    
    Debug.Print "ANSI CSV导出完成: " & filePath
End Sub

Sub CreateTestWorkbookAndExportUTF8(filePath As String)
    Dim wb As Workbook
    Dim ws As Worksheet
    Dim i As Long
    
    Set wb = Workbooks.Add
    Set ws = wb.Worksheets(1)
    
    ' 创建测试数据 (同上面的函数)
    ws.Cells(1, 1).Value = "姓名"
    ws.Cells(1, 2).Value = "年龄"
    ws.Cells(1, 3).Value = "城市"
    ws.Cells(1, 4).Value = "薪资"
    ws.Cells(1, 5).Value = "部门"
    
    Dim names As Variant
    Dim cities As Variant
    Dim departments As Variant
    
    names = Array("张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "王十二")
    cities = Array("北京", "上海", "广州", "深圳", "杭州")
    departments = Array("技术部", "销售部", "人事部", "财务部")
    
    For i = 2 To 11
        ws.Cells(i, 1).Value = names(i - 2)
        ws.Cells(i, 2).Value = 20 + (i - 2) * 2
        ws.Cells(i, 3).Value = cities((i - 2) Mod 5)
        ws.Cells(i, 4).Value = 5000 + (i - 2) * 1000
        ws.Cells(i, 5).Value = departments((i - 2) Mod 4)
    Next i
    
    ' 尝试导出为UTF-8 CSV
    On Error Resume Next
    wb.SaveAs filePath, xlCSVUTF8
    If Err.Number <> 0 Then
        Debug.Print "xlCSVUTF8不支持，使用ANSI编码"
        wb.SaveAs filePath, xlCSV
    End If
    On Error GoTo 0
    
    wb.Close False
    Set ws = Nothing
    Set wb = Nothing
    
    Debug.Print "UTF-8 CSV导出完成: " & filePath
End Sub

' ================================================
' 性能测试函数
' ================================================

Sub PerformanceTest()
    Dim testData As Variant
    Dim startTime As Double, endTime As Double
    Dim i As Long
    
    ' 生成大数据集 (1000行, 10列)
    testData = GenerateTestData(1000, 10)
    
    Dim basePath As String
    basePath = ThisWorkbook.Path & "\"
    
    Debug.Print "=== 性能测试开始 ==="
    
    ' 1. FilesystemObject
    startTime = Timer
    CreateCSVWithFSO basePath & "perf_fso.csv", testData
    endTime = Timer
    Debug.Print "FilesystemObject: " & Format(endTime - startTime, "0.000") & "秒"
    
    ' 2. ADO.Stream
    startTime = Timer
    CreateCSVWithADO basePath & "perf_ado.csv", testData, ",", True
    endTime = Timer
    Debug.Print "ADO.Stream: " & Format(endTime - startTime, "0.000") & "秒"
    
    ' 3. Open语句
    startTime = Timer
    CreateCSVWithOpen basePath & "perf_open.csv", testData
    endTime = Timer
    Debug.Print "Open语句: " & Format(endTime - startTime, "0.000") & "秒"
    
    Debug.Print "=== 性能测试完成 ==="
End Sub

' ================================================
' 主测试函数
' ================================================

Sub TestAllCSVMethods()
    ' 测试所有CSV创建方法
    
    Dim basePath As String
    basePath = ThisWorkbook.Path & "\"
    
    Debug.Print "=== CSV创建方法测试开始 ==="
    
    ' 确保目录存在
    If Dir(basePath, vbDirectory) = "" Then
        MkDir basePath
    End If
    
    ' 测试1: FilesystemObject
    Debug.Print "1. 测试FilesystemObject方法..."
    CreateEmployeeTestData basePath & "employee_fso.csv", "FSO"
    
    ' 测试2: Workbook.SaveAs ANSI
    Debug.Print "2. 测试Workbook.SaveAs ANSI方法..."
    CreateEmployeeTestData basePath & "employee_ansi.csv", "SAVEAS_ANSI"
    
    ' 测试3: Workbook.SaveAs UTF-8
    Debug.Print "3. 测试Workbook.SaveAs UTF-8方法..."
    CreateEmployeeTestData basePath & "employee_utf8.csv", "SAVEAS_UTF8"
    
    ' 测试4: ADO.Stream UTF-8 with BOM
    Debug.Print "4. 测试ADO.Stream UTF-8 BOM方法..."
    CreateEmployeeTestData basePath & "employee_ado_bom.csv", "ADO_BOM"
    
    ' 测试5: ADO.Stream UTF-8 无BOM
    Debug.Print "5. 测试ADO.Stream UTF-8 无BOM方法..."
    CreateEmployeeTestData basePath & "employee_ado_nobom.csv", "ADO_NO_BOM"
    
    ' 测试6: Open语句
    Debug.Print "6. 测试Open语句方法..."
    CreateEmployeeTestData basePath & "employee_open.csv", "OPEN"
    
    Debug.Print "=== 所有CSV创建方法测试完成 ==="
    Debug.Print "请查看 " & basePath & " 目录下的生成文件"
End Sub

' ================================================
' 便捷函数 - 单键测试
' ================================================

Sub 快速测试CSV创建()
    ' 便捷函数：一键测试所有方法
    Call TestAllCSVMethods
    
    ' 清理工作
    Debug.Print "测试完成！生成的文件位于: " & ThisWorkbook.Path
End Sub

Sub 显示使用说明()
    Debug.Print "=== CSV创建方法使用说明 ==="
    Debug.Print "1. 快速测试: 运行 '快速测试CSV创建'"
    Debug.Print "2. 性能测试: 运行 'PerformanceTest'"
    Debug.Print "3. 单独测试某个方法:"
    Debug.Print "   - FSO方法: CreateCSVWithFSO"
    Debug.Print "   - ADO方法: CreateCSVWithADO"
    Debug.Print "   - Open方法: CreateCSVWithOpen"
    Debug.Print "   - SaveAs方法: ExportToCSV_ANSI"
    Debug.Print ""
    Debug.Print "注意: FilesystemObject需要引用 'Microsoft Scripting Runtime'"
    Debug.Print "      ADO.Stream需要引用 'Microsoft ActiveX Data Objects x.x Library'"
    Debug.Print ""
    Debug.Print "编码说明:"
    Debug.Print "  - ANSI: 兼容性好，但不支持中文等多语言"
    Debug.Print "  - UTF-8: 现代标准，支持所有语言"
    Debug.Print "  - UTF-8 BOM: Excel友好，但某些程序可能不识别"
    Debug.Print "  - 无BOM UTF-8: 最通用，但Excel可能无法自动识别"
End Sub