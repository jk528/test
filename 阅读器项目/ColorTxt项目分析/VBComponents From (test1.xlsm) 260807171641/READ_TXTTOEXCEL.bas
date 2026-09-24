Attribute VB_Name = "READ_TXTTOEXCEL"
Option Explicit
' 最终版统合数据导入 - 支持Excel、Word和TXT文件（带状态监控）

Sub ComprehensiveDataImport()
    Dim filePath As String
    Dim fileType As Integer
    Dim importMethod As Integer
    Dim processMode As Integer
    Dim startTime As Double
    Dim endTime As Double
    Dim stepStartTime As Double
    ' 记录开始时间
    startTime = Timer
    ' 禁用屏幕更新以提高性能
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    ' 显示开始信息
    Call ShowStatus("开始执行数据导入流程...")
    Debug.Print "===================================="
    Debug.Print "开始执行数据导入流程..."
    Debug.Print "开始时间: " & Now
    ' 步骤1：选取文件（支持多种类型）
    stepStartTime = Timer
    Call ShowStatus("步骤1：选择数据文件...")
    Debug.Print "步骤1：选择数据文件..."
    filePath = SelectMultiTypeFile()
    If filePath = "" Then
        Call ShowStatus("用户取消选择文件")
        Debug.Print "用户取消选择文件"
        GoTo Cleanup
    End If
    Call ShowStatus("步骤1完成：已选择文件 - " & Right(filePath, 50) & "（耗时：" & Format(Timer - stepStartTime, "0.000") & "秒）")
    Debug.Print "步骤1完成：已选择文件 - " & filePath
    Debug.Print "耗时：" & Format(Timer - stepStartTime, "0.000") & "秒"
    ' 步骤2：自动检测文件类型
    stepStartTime = Timer
    Call ShowStatus("步骤2：自动检测文件类型...")
    Debug.Print "步骤2：自动检测文件类型..."
    fileType = DetectFileType(filePath)
    If fileType = 0 Then
        MsgBox "不支持的文件类型", vbExclamation
        Debug.Print "不支持的文件类型"
        Call ShowStatus("步骤2失败：不支持的文件类型")
        GoTo Cleanup
    End If
    Call ShowStatus("步骤2完成：检测到文件类型 - " & GetFileTypeDescription(fileType) & "（耗时：" & Format(Timer - stepStartTime, "0.000") & "秒）")
    Debug.Print "步骤2完成：检测到文件类型 - " & GetFileTypeDescription(fileType)
    Debug.Print "耗时：" & Format(Timer - stepStartTime, "0.000") & "秒"
    ' 步骤3：选择处理方式（仅针对Word和TXT文件）
    If fileType = 2 Or fileType = 3 Then ' Word或TXT文件
        stepStartTime = Timer
        Call ShowStatus("步骤3：选择文本处理方式...")
        Debug.Print "步骤3：选择文本处理方式..."
        processMode = SelectProcessMode()
        If processMode = 0 Then
            Call ShowStatus("用户取消选择处理方式")
            Debug.Print "用户取消选择处理方式"
            GoTo Cleanup
        End If
        Call ShowStatus("步骤3完成：选择处理方式 - " & GetProcessModeDescription(processMode) & "（耗时：" & Format(Timer - stepStartTime, "0.000") & "秒）")
        Debug.Print "步骤3完成：选择处理方式 - " & GetProcessModeDescription(processMode)
        Debug.Print "耗时：" & Format(Timer - stepStartTime, "0.000") & "秒"
    End If
    ' 步骤4：选择导入方式
    stepStartTime = Timer
    Call ShowStatus("步骤4：选择导入方式...")
    Debug.Print "步骤4：选择导入方式..."
    importMethod = SelectImportMethod()
    If importMethod = 0 Then
        MsgBox "未选择导入方式", vbExclamation
        Debug.Print "未选择导入方式"
        Call ShowStatus("步骤4失败：未选择导入方式")
        GoTo Cleanup
    End If
    Call ShowStatus("步骤4完成：选择导入方式 - " & GetImportMethodDescription(importMethod) & "（耗时：" & Format(Timer - stepStartTime, "0.000") & "秒）")
    Debug.Print "步骤4完成：选择导入方式 - " & GetImportMethodDescription(importMethod)
    Debug.Print "耗时：" & Format(Timer - stepStartTime, "0.000") & "秒"
    ' 步骤5：根据自动检测的文件类型和导入方式执行导入
    stepStartTime = Timer
    Call ShowStatus("步骤5：执行数据导入...")
    Debug.Print "步骤5：执行数据导入..."
    Select Case fileType
        Case 1 ' Excel/SQL数据导入
            Call ShowStatus("正在导入Excel数据...")
            Debug.Print "正在导入Excel数据..."
            ImportExcelData filePath, importMethod
        Case 2 ' Word数据导入
            Call ShowStatus("正在导入Word数据...")
            Debug.Print "正在导入Word数据..."
            ImportWordData filePath, importMethod, processMode
        Case 3 ' TXT数据导入
            Call ShowStatus("正在导入TXT数据...")
            Debug.Print "正在导入TXT数据..."
            ImportTextData filePath, importMethod, processMode
    End Select
    Call ShowStatus("步骤5完成：数据导入成功（耗时：" & Format(Timer - stepStartTime, "0.000") & "秒）")
    Debug.Print "步骤5完成：数据导入成功"
    Debug.Print "耗时：" & Format(Timer - stepStartTime, "0.000") & "秒"
    ' 记录结束时间
    endTime = Timer
    ' 显示完成信息
    MsgBox "数据导入完成！" & vbCrLf & _
    "耗时: " & Format(endTime - startTime, "0.000") & " 秒", vbInformation
    Call ShowStatus("数据导入流程执行完成！总耗时：" & Format(endTime - startTime, "0.000") & "秒")
    Debug.Print "数据导入流程执行完成！"
    Debug.Print "总耗时：" & Format(endTime - startTime, "0.000") & "秒"
    Debug.Print "结束时间: " & Now
    Debug.Print "===================================="
    FormatSheet
Cleanup:
    ' 恢复设置
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Application.StatusBar = False
End Sub
' 通用函数：根据导入方式准备目标工作表和范围

Function PrepareImportTarget(importMethod As Integer) As Variant
    Dim result(1 To 2) As Variant ' result(1) = targetSheet, result(2) = targetRange
    Dim targetSheet As Worksheet
    Dim targetRange As Range
    Select Case importMethod
        Case 1 ' 默认ActiveSheet [A1]导入
            Set targetSheet = ActiveSheet
            Set targetRange = targetSheet.Range("A1")
        Case 2 ' 新建sheet页面导入
            Set targetSheet = ThisWorkbook.Worksheets.Add
            targetSheet.Name = "导入数据_" & Format(Now, "yyyyMMdd_HHmmss")
            Set targetRange = targetSheet.Range("A1")
            targetSheet.Activate
        Case 3 ' 新建excel导入
            Dim newWorkbook As Workbook
            Set newWorkbook = Workbooks.Add
            Set targetSheet = newWorkbook.Worksheets(1)
            Set targetRange = targetSheet.Range("A1")
        Case 4 ' 选择指定单元格位置导入
            ' 暂时恢复屏幕刷新以便用户选择单元格
            Application.ScreenUpdating = True
            Application.DisplayAlerts = True
            On Error Resume Next
            Set targetRange = Application.InputBox("请选择导入的目标单元格（从该单元格开始导入）", _
            "选择目标位置", Type:=8)
            On Error GoTo 0
            ' 重新禁用屏幕刷新
            Application.ScreenUpdating = False
            Application.DisplayAlerts = False
            If targetRange Is Nothing Then
                MsgBox "未选择目标单元格", vbExclamation
                PrepareImportTarget = Array(Nothing, Nothing)
                Exit Function
            End If
            Set targetSheet = targetRange.Parent
    End Select
    Set result(1) = targetSheet
    Set result(2) = targetRange
    PrepareImportTarget = result
End Function
' 步骤1：选择多种类型文件（合并前3个过滤器）

Function SelectMultiTypeFile() As String
    Dim fd As FileDialog
    Set fd = Application.FileDialog(msoFileDialogFilePicker)
    With fd
        .Title = "请选择要导入的数据文件"
        .filters.Clear
        ' 合并前3个过滤器为一个 "Data Files"
        .filters.Add "Data Files", "*.xls;*.xlsx;*.xlsm;*.xlsb;*.doc;*.docx;*.docm;*.txt"
        .filters.Add "All Files", "*.*"
        .AllowMultiSelect = False
        If .Show = -1 Then
            SelectMultiTypeFile = .SelectedItems(1)
        Else
            SelectMultiTypeFile = ""
        End If
    End With
    Set fd = Nothing
End Function
' 步骤2：自动检测文件类型

Function DetectFileType(filePath As String) As Integer
    Dim fileExt As String
    ' 获取文件扩展名
    fileExt = LCase(Right(filePath, Len(filePath) - InStrRev(filePath, ".")))
    ' 根据扩展名判断文件类型
    Select Case fileExt
        Case "xls", "xlsx", "xlsm", "xlsb"
            DetectFileType = 1 ' Excel文件
        Case "doc", "docx", "docm"
            DetectFileType = 2 ' Word文件
        Case "txt"
            DetectFileType = 3 ' TXT文件
        Case Else
            DetectFileType = 0 ' 不支持的文件类型
    End Select
End Function
' 选择处理方式（从AI生成去除标点中添加）

Function SelectProcessMode() As Integer
    ' ==============================================
    ' 功能：让用户选择文本处理方式
    ' 返回：1=保留部分标点，2=不保留标点，3=正常读取，0=取消
    ' ==============================================
    Dim prompt As String
    Dim inputValue As String
    Dim selectedMode As Integer
    ' 构建选择提示
    prompt = "请选择文本处理方式（输入对应数字）：" & vbCrLf & vbCrLf & _
    "1. 保留部分标点（保留空格和全角空格）" & vbCrLf & _
    "2. 不保留标点（只保留中文字符、英文字母、数字）" & vbCrLf & _
    "3. 正常读取（保留所有内容）" & vbCrLf & vbCrLf & _
    "例如：输入 1 选择保留部分标点"
    ' 获取用户输入
    inputValue = InputBox(prompt, "选择处理方式", "1")
    ' 验证输入
    If IsNumeric(inputValue) Then
        selectedMode = CInt(inputValue)
        If selectedMode >= 1 And selectedMode <= 3 Then
            SelectProcessMode = selectedMode
        Else
            SelectProcessMode = 0
        End If
    Else
        SelectProcessMode = 0
    End If
End Function
' 步骤3：选择导入方式

Function SelectImportMethod() As Integer
    Dim methodList As String
    Dim selectedInput As String
    Dim selectedMethod As Integer
    ' 构建导入方式列表
    methodList = vbCrLf & _
    "1: 默认ActiveSheet [A1]导入" & vbCrLf & _
    "2: 新建sheet页面导入" & vbCrLf & _
    "3: 新建excel导入" & vbCrLf & _
    "4: 选择指定单元格位置导入"
    ' 让用户选择导入方式
    selectedInput = InputBox("请选择导入方式：" & methodList & vbCrLf & vbCrLf & "例如：输入 1 选择默认导入方式", "选择导入方式", "1")
    ' 验证输入
    If IsNumeric(selectedInput) Then
        selectedMethod = CInt(selectedInput)
        If selectedMethod >= 1 And selectedMethod <= 4 Then
            SelectImportMethod = selectedMethod
        Else
            SelectImportMethod = 0
        End If
    Else
        SelectImportMethod = 0
    End If
End Function
' 步骤4.1：Excel/SQL数据导入

Sub ImportExcelData(filePath As String, importMethod As Integer)
    Dim sheetName As String
    Dim targetSheet As Worksheet
    Dim targetRange As Range
    Dim importTarget As Variant
    ' 步骤2：自动检测文件类型
    Call ShowStatus("步骤2：自动检测文件类型...")
    Debug.Print "步骤2：自动检测文件类型..."
    ' 选择工作表
    sheetName = SelectWorksheet(filePath)
    If sheetName = "" Then
        MsgBox "未选择工作表", vbExclamation
        Exit Sub
    End If
    ' 使用通用函数准备导入目标
    importTarget = PrepareImportTarget(importMethod)
    Set targetSheet = importTarget(1)
    Set targetRange = importTarget(2)
    ' 检查是否成功准备目标
    If targetSheet Is Nothing Or targetRange Is Nothing Then
        Exit Sub
    End If
    ' 执行Excel数据导入
    ImportExcelDataToSheet filePath, sheetName, targetSheet, targetRange
End Sub
' 步骤4.2：Word数据导入（添加处理方式参数）

Sub ImportWordData(filePath As String, importMethod As Integer, processMode As Integer)
    Dim targetSheet As Worksheet
    Dim targetRange As Range
    Dim importTarget As Variant
    ' 使用通用函数准备导入目标
    importTarget = PrepareImportTarget(importMethod)
    Set targetSheet = importTarget(1)
    Set targetRange = importTarget(2)
    ' 检查是否成功准备目标
    If targetSheet Is Nothing Or targetRange Is Nothing Then
        Exit Sub
    End If
    ' 执行Word数据导入（使用处理方式）
    ImportWordDataToSheet filePath, targetSheet, targetRange, processMode
End Sub
' 步骤4.3：TXT数据导入（添加处理方式参数）

Sub ImportTextData(filePath As String, importMethod As Integer, processMode As Integer)
    Dim targetSheet As Worksheet
    Dim targetRange As Range
    Dim importTarget As Variant
    ' 使用通用函数准备导入目标
    importTarget = PrepareImportTarget(importMethod)
    Set targetSheet = importTarget(1)
    Set targetRange = importTarget(2)
    ' 检查是否成功准备目标
    If targetSheet Is Nothing Or targetRange Is Nothing Then
        Exit Sub
    End If
    ' 执行TXT数据导入（使用处理方式）
    ImportTextDataToSheet filePath, targetSheet, targetRange, processMode
End Sub
' 选择Excel工作表（参考SQL数据导入窗体重构）

Function SelectWorksheet(filePath As String) As String
    On Error GoTo ErrorHandler
    Dim conn As Object
    Dim cat As Object
    Dim table As Object
    Dim wsDict As Object
    Dim wsList As String
    Dim selectedInput As String
    Dim selectedCode As Integer
    Dim i As Integer
    Dim engineType As String
    Debug.Print "开始获取Excel工作表列表..."
    Debug.Print "文件路径: " & filePath
    ' 创建字典存储工作表信息
    Set wsDict = CreateObject("scripting.dictionary")
    ' 参考SQL数据导入窗体的连接逻辑
    ' 根据Excel版本选择驱动
    engineType = IIf(val(Application.Version) >= 15, "Microsoft.ACE.OLEDB.12.0", "Microsoft.Jet.OLEDB.4.0")
    Debug.Print "使用驱动: " & engineType
    ' 创建连接字符串
    Dim connectionString As String
    connectionString = "Provider=" & engineType & ";Extended Properties='Excel 8.0;HDR=YES';Data Source=" & filePath
    Debug.Print "连接字符串: " & connectionString
    ' 创建并打开连接
    Set conn = CreateObject("ADODB.Connection")
    conn.Open connectionString
    Debug.Print "连接成功"
    ' 使用ADOX.Catalog获取工作表
    Set cat = CreateObject("ADOX.Catalog")
    Set cat.ActiveConnection = conn
    Debug.Print "创建ADOX.Catalog成功"
    ' 遍历表集合获取工作表
    Debug.Print "开始获取工作表列表..."
    For Each table In cat.Tables
        ' 处理标准工作表名称格式
        If Right(table.Name, 1) = "$" Then
            wsDict(Left(table.Name, Len(table.Name) - 1)) = ""
            Debug.Print "找到工作表: " & Left(table.Name, Len(table.Name) - 1)
        End If
        ' 处理带引号的工作表名称格式
        If Left(table.Name, 1) = "'" And Right(table.Name, 2) = "$'" Then
            wsDict(Mid(table.Name, 2, Len(table.Name) - 3)) = ""
            Debug.Print "找到工作表: " & Mid(table.Name, 2, Len(table.Name) - 3)
        End If
    Next
    ' 关闭连接和清理
    conn.Close
    Set conn = Nothing
    Set cat = Nothing
    Set table = Nothing
    Debug.Print "连接已关闭，资源已释放"
    ' 构建工作表列表
    wsList = vbCrLf
    i = 1
    ' 创建编号到工作表名称的映射
    Dim numberedDict As Object
    Set numberedDict = CreateObject("scripting.dictionary")
    Debug.Print "工作表列表:"
    Debug.Print "===================================="
    Dim wsName As Variant
    For Each wsName In wsDict.keys
        numberedDict(i) = wsName
        wsList = wsList & i & ": " & wsName & vbCrLf
        Debug.Print i & ": " & wsName
        i = i + 1
    Next
    Debug.Print "===================================="
    ' 如果没有找到工作表
    If numberedDict.count = 0 Then
        MsgBox "未找到工作表", vbInformation, "提示"
        Debug.Print "未找到工作表"
        SelectWorksheet = ""
        Exit Function
    End If
    ' 构建提示信息
    Dim promptMessage As String
    promptMessage = "请输入要选择的工作表编号：" & vbCrLf & vbCrLf & _
    "====================================" & vbCrLf & _
    "工作表列表：" & wsList & _
    "====================================" & vbCrLf & _
    "例如：输入 1 选择第一个工作表" & vbCrLf & _
    "      输入 2 选择第二个工作表"
    ' 获取用户输入
    selectedInput = InputBox(promptMessage, "选择工作表 - SQL数据导入", "1")
    Debug.Print "用户输入: " & selectedInput
    ' 验证输入并获取对应工作表
    If IsNumeric(selectedInput) Then
        selectedCode = CInt(selectedInput)
        If numberedDict.exists(selectedCode) Then
            SelectWorksheet = numberedDict(selectedCode)
            Debug.Print "选择的工作表: " & SelectWorksheet
        Else
            ' 输入的编号不存在，显示错误信息
            MsgBox "输入的工作表编号不存在，请重新输入", vbExclamation, "输入错误"
            Debug.Print "输入的工作表编号不存在: " & selectedCode
            SelectWorksheet = ""
        End If
    Else
        ' 输入不是数字，显示错误信息
        MsgBox "请输入有效的数字编号", vbExclamation, "输入错误"
        Debug.Print "输入不是有效的数字: " & selectedInput
        SelectWorksheet = ""
    End If
    ' 释放字典
    Set wsDict = Nothing
    Set numberedDict = Nothing
    Debug.Print "字典资源已释放"
    Exit Function
ErrorHandler:
    Dim errorMessage As String
    ' 构建详细的错误信息
    errorMessage = "读取工作表列表时发生错误：" & vbCrLf & _
    "错误代码: " & err.number & vbCrLf & _
    "错误描述: " & err.Description & vbCrLf & vbCrLf & _
    "可能的原因：" & vbCrLf & _
    "1. Excel文件被其他程序占用" & vbCrLf & _
    "2. Excel文件格式不正确或已损坏" & vbCrLf & _
    "3. 缺少必要的数据库驱动程序" & vbCrLf & _
    "4. 文件路径包含特殊字符"
    ' 显示错误信息
    MsgBox errorMessage, vbCritical, "错误"
    Debug.Print "错误: " & err.Description
    Debug.Print "错误代码: " & err.number
    ' 确保释放所有资源
    On Error Resume Next
    If Not conn Is Nothing Then
        conn.Close
        Set conn = Nothing
    End If
    If Not cat Is Nothing Then
        Set cat = Nothing
    End If
    If Not wsDict Is Nothing Then
        Set wsDict = Nothing
    End If
    If Not numberedDict Is Nothing Then
        Set numberedDict = Nothing
    End If
    On Error GoTo 0
    Debug.Print "错误处理完成，资源已释放"
    SelectWorksheet = ""
End Function
' 获取Excel文件的连接字符串

Function GetExcelConnectionString(filePath As String, Optional hasHeaders As Boolean = True, Optional readOnly As Boolean = False, Optional maxScanRows As Integer = 0) As String
    Dim fileExt As String
    Dim hdrSetting As String
    Dim engineType As String
    Dim readOnlySetting As String
    Dim maxScanSetting As String
    Dim modeSetting As String
    Dim imexSetting As String
    Dim typeGuessSetting As String
    Dim importMixedSetting As String
    ' 检查文件是否存在
    If Dir(filePath) = "" Then
        GetExcelConnectionString = ""
        Exit Function
    End If
    ' 获取文件扩展名
    fileExt = LCase(Right(filePath, Len(filePath) - InStrRev(filePath, ".")))
    ' 设置表头参数
    hdrSetting = IIf(hasHeaders, "HDR=YES", "HDR=NO")
    ' 设置只读参数
    readOnlySetting = IIf(readOnly, "ReadOnly=1;", "")
    ' 设置模式参数
    modeSetting = IIf(readOnly, "Mode=Read;", "Mode=ReadWrite;")
    ' 设置IMEX参数（用于处理混合数据类型）
    imexSetting = "IMEX=1;"
    ' 设置类型猜测行数
    typeGuessSetting = "TypeGuessRows=0;"
    ' 设置混合类型导入方式
    importMixedSetting = "ImportMixedTypes=Text;"
    ' 设置最大扫描行数（用于确定列类型）
    If maxScanRows > 0 Then
        maxScanSetting = "MaxScanRows=" & CStr(maxScanRows) & ";"
    Else
        maxScanSetting = ""
    End If
    ' 对于所有Excel文件，优先使用ACE驱动
    engineType = "Microsoft.ACE.OLEDB.12.0"
    ' 根据文件扩展名返回不同的连接字符串
    Select Case fileExt
        Case "xlsx", "xlsm", "xltx", "xltm", "xlsb"
            ' Excel 2007及以上格式
            GetExcelConnectionString = "Provider=" & engineType & ";" & _
            "Data Source=" & filePath & ";" & _
            modeSetting & _
            readOnlySetting & _
            "Extended Properties=""Excel 12.0 Xml;" & hdrSetting & ";" & maxScanSetting & imexSetting & typeGuessSetting & importMixedSetting & """"
        Case "xls"
            ' Excel 97-2003格式
            GetExcelConnectionString = "Provider=" & engineType & ";" & _
            "Data Source=" & filePath & ";" & _
            modeSetting & _
            readOnlySetting & _
            "Extended Properties=""Excel 8.0;" & hdrSetting & ";" & maxScanSetting & imexSetting & typeGuessSetting & importMixedSetting & """"
        Case Else
            ' 默认使用ACE驱动和Excel 2007格式
            GetExcelConnectionString = "Provider=" & engineType & ";" & _
            "Data Source=" & filePath & ";" & _
            modeSetting & _
            readOnlySetting & _
            "Extended Properties=""Excel 12.0 Xml;" & hdrSetting & ";" & maxScanSetting & imexSetting & typeGuessSetting & importMixedSetting & """"
    End Select
End Function
' 导入Excel数据到指定工作表

Sub ImportExcelDataToSheet(filePath As String, sheetName As String, targetSheet As Worksheet, startCell As Range)
    On Error GoTo ErrorHandler
    Dim conn As Object
    Dim rs As Object
    Dim connectionString As String
    Dim sql As String
    Dim dataArray() As Variant
    Dim fieldCount As Long
    Dim recordCount As Long
    Dim i As Long
    Dim j As Long
    Dim engineType As String
    Debug.Print "开始导入Excel数据..."
    Debug.Print "文件路径: " & filePath
    Debug.Print "工作表名称: " & sheetName
    Debug.Print "目标工作表: " & targetSheet.Name
    Debug.Print "起始单元格: " & startCell.Address
    ' 清空目标区域
    targetSheet.Range(startCell.Address).CurrentRegion.Clear
    Debug.Print "目标区域已清空"
    ' 参考SQL数据导入窗体的连接逻辑
    ' 根据Excel版本选择驱动
    engineType = IIf(val(Application.Version) >= 15, "Microsoft.ACE.OLEDB.12.0", "Microsoft.Jet.OLEDB.4.0")
    Debug.Print "使用驱动: " & engineType
    ' 创建连接字符串
    connectionString = "Provider=" & engineType & ";Extended Properties='Excel 8.0;HDR=YES';Data Source=" & filePath
    Debug.Print "连接字符串: " & connectionString
    ' 创建并打开连接
    Set conn = CreateObject("ADODB.Connection")
    conn.Open connectionString
    Debug.Print "连接成功"
    ' 创建记录集
    Set rs = CreateObject("ADODB.Recordset")
    Debug.Print "创建记录集成功"
    ' 构建SQL语句
    sql = "SELECT * FROM [" & sheetName & "$]"
    Debug.Print "SQL语句: " & sql
    ' 执行查询
    rs.Open sql, conn, 1, 3
    Debug.Print "查询执行成功"
    ' 检查是否有数据
    If rs.EOF And rs.BOF Then
        MsgBox "所选工作表无数据", vbInformation
        Debug.Print "所选工作表无数据"
        GoTo Cleanup
    End If
    ' 获取字段数量
    fieldCount = rs.Fields.count
    Debug.Print "字段数量: " & fieldCount
    ' 导入表头
    Debug.Print "开始导入表头..."
    For i = 0 To fieldCount - 1
        targetSheet.Cells(startCell.row, startCell.Column + i).Value = rs.Fields(i).Name
        targetSheet.Cells(startCell.row, startCell.Column + i).Font.Bold = True
        Debug.Print "表头 " & i + 1 & ": " & rs.Fields(i).Name
    Next i
    Debug.Print "表头导入完成"
    ' 计算记录数量
    rs.MoveLast
    recordCount = rs.recordCount
    rs.MoveFirst
    Debug.Print "记录数量: " & recordCount
    ' 调整数组大小
    ReDim dataArray(1 To recordCount, 1 To fieldCount)
    Debug.Print "数据数组已调整大小: " & recordCount & "行, " & fieldCount & "列"
    ' 填充数据到数组
    Debug.Print "开始填充数据到数组..."
    i = 1
    Do While Not rs.EOF
        For j = 1 To fieldCount
            ' 处理数据类型
            On Error Resume Next
            dataArray(i, j) = rs.Fields(j - 1).Value
            If err.number <> 0 Then
                ' 处理特殊数据类型
                dataArray(i, j) = CStr(rs.Fields(j - 1).Value)
                err.Clear
            End If
            On Error GoTo ErrorHandler
        Next j
        i = i + 1
        rs.MoveNext
    Loop
    Debug.Print "数据填充完成"
    ' 批量写入数据
    Debug.Print "开始批量写入数据..."
    targetSheet.Range(startCell.Offset(1, 0), startCell.Offset(recordCount, fieldCount - 1)).Value = dataArray
    Debug.Print "数据写入完成"
    ' 调整列宽
    targetSheet.Columns.AutoFit
    Debug.Print "列宽已自动调整"
Cleanup:
    ' 关闭记录集和连接
    On Error Resume Next
    If Not rs Is Nothing Then
        If rs.State = 1 Then ' adStateOpen
            rs.Close
        End If
        Set rs = Nothing
        Debug.Print "记录集已关闭"
    End If
    If Not conn Is Nothing Then
        If conn.State = 1 Then ' adStateOpen
            conn.Close
        End If
        Set conn = Nothing
        Debug.Print "连接已关闭"
    End If
    On Error GoTo 0
    Debug.Print "资源已释放"
    Exit Sub
ErrorHandler:
    Dim errorMessage As String
    ' 构建详细的错误信息
    errorMessage = "导入Excel数据时发生错误：" & vbCrLf & _
    "错误代码: " & err.number & vbCrLf & _
    "错误描述: " & err.Description & vbCrLf & vbCrLf & _
    "可能的原因：" & vbCrLf & _
    "1. Excel文件被其他程序占用" & vbCrLf & _
    "2. Excel文件格式不正确或已损坏" & vbCrLf & _
    "3. SQL查询语句错误" & vbCrLf & _
    "4. 数据类型不匹配"
    ' 显示错误信息
    MsgBox errorMessage, vbCritical, "错误"
    Debug.Print "错误: " & err.Description
    Debug.Print "错误代码: " & err.number
    ' 确保释放资源
    GoTo Cleanup
End Sub
' 导入Word数据到指定工作表（添加处理方式参数）

Sub ImportWordDataToSheet(filePath As String, targetSheet As Worksheet, startCell As Range, processMode As Integer)
    Dim content As String
    Dim processedContent As String
    Dim dataArray() As Variant
    Debug.Print "开始导入Word数据..."
    Debug.Print "文件路径: " & filePath
    Debug.Print "目标工作表: " & targetSheet.Name
    Debug.Print "起始单元格: " & startCell.Address
    Debug.Print "处理方式: " & GetProcessModeDescription(processMode)
    ' 清空目标区域
    targetSheet.Range(startCell.Address).CurrentRegion.Clear
    Debug.Print "目标区域已清空"
    ' 使用Word对象模型读取文件内容
    Debug.Print "开始读取Word文件内容..."
    content = ReadFileContentWithWord(filePath)
    Debug.Print "Word文件内容读取完成"
    Debug.Print "内容长度: " & Len(content) & " 字符"
    ' 根据选择的处理方式处理文本
    Debug.Print "开始处理文本，处理方式: " & GetProcessModeDescription(processMode)
    Select Case processMode
        Case 1 ' 保留部分标点（保留空格和全角空格）
            processedContent = ProcessTextWithSpaces(content)
            Debug.Print "使用方式1处理文本：保留部分标点"
        Case 2 ' 不保留标点（只保留中文字符、英文字母、数字）
            processedContent = ProcessTextWithoutPunctuation(content)
            Debug.Print "使用方式2处理文本：不保留标点"
        Case 3 ' 正常读取（保留所有内容）
            processedContent = content
            Debug.Print "使用方式3处理文本：正常读取"
    End Select
    Debug.Print "文本处理完成"
    Debug.Print "处理后长度: " & Len(processedContent) & " 字符"
    ' 将处理后的文本转换为二维数组
    Debug.Print "开始将文本转换为二维数组..."
    dataArray = ConvertTextTo2DArray(processedContent, processMode)
    Debug.Print "文本转换完成"
    Debug.Print "数组行数: " & UBound(dataArray, 1) & " 行"
    ' 批量写入单元格
    Debug.Print "开始批量写入数据..."
    If UBound(dataArray, 1) > 0 Then
        targetSheet.Range(startCell.Address).Resize(UBound(dataArray, 1), 1).Value = dataArray
        Debug.Print "数据写入完成，共 " & UBound(dataArray, 1) & " 行"
        ' 调整列宽
        targetSheet.Columns(startCell.Column).AutoFit
        Debug.Print "列宽已自动调整"
    Else
        Debug.Print "没有数据需要写入"
    End If
    Debug.Print "Word数据导入完成！"
End Sub
' 导入TXT数据到指定工作表（添加处理方式参数）

Sub ImportTextDataToSheet(filePath As String, targetSheet As Worksheet, startCell As Range, processMode As Integer)
    Dim fileBytes() As Byte
    Dim encoding As String
    Dim content As String
    Dim processedContent As String
    Dim dataArray() As Variant
    Debug.Print "开始导入TXT数据..."
    Debug.Print "文件路径: " & filePath
    Debug.Print "目标工作表: " & targetSheet.Name
    Debug.Print "起始单元格: " & startCell.Address
    Debug.Print "处理方式: " & GetProcessModeDescription(processMode)
    ' 清空目标区域
    targetSheet.Range(startCell.Address).CurrentRegion.Clear
    Debug.Print "目标区域已清空"
    ' 读取文件字节并检测编码
    Debug.Print "开始读取文件字节并检测编码..."
    fileBytes = ReadFileBytes(filePath)
    encoding = DetectEncoding(fileBytes)
    Erase fileBytes
    Debug.Print "编码检测完成"
    Debug.Print "文件编码: " & encoding
    ' 根据编码读取TXT文件内容
    Debug.Print "开始根据编码读取TXT文件内容..."
    Select Case encoding
        Case "ANSI"
            content = ReadTextFileANSI(filePath)
            Debug.Print "使用ANSI编码读取"
        Case "UTF-8 BOM", "UTF-8"
            content = ReadTextFileUTF8(filePath)
            Debug.Print "使用UTF-8编码读取"
        Case "UTF-16LE", "UTF-16BE"
            content = ReadTextFileUnicode(filePath)
            Debug.Print "使用Unicode编码读取"
        Case Else
            MsgBox "TXT编码不支持,建议手动粘贴或者另存为txt_UTF-8后再次运行!", vbExclamation
            Debug.Print "不支持的编码: " & encoding
            Exit Sub
    End Select
    Debug.Print "TXT文件内容读取完成"
    Debug.Print "内容长度: " & Len(content) & " 字符"
    ' 根据选择的处理方式处理文本
    Debug.Print "开始处理文本，处理方式: " & GetProcessModeDescription(processMode)
    Select Case processMode
        Case 1 ' 保留部分标点（保留空格和全角空格）
            processedContent = ProcessTextWithSpaces(content)
            Debug.Print "使用方式1处理文本：保留部分标点"
        Case 2 ' 不保留标点（只保留中文字符、英文字母、数字）
            processedContent = ProcessTextWithoutPunctuation(content)
            Debug.Print "使用方式2处理文本：不保留标点"
        Case 3 ' 正常读取（保留所有内容）
            processedContent = content
            Debug.Print "使用方式3处理文本：正常读取"
    End Select
    Debug.Print "文本处理完成"
    Debug.Print "处理后长度: " & Len(processedContent) & " 字符"
    ' 将处理后的文本转换为二维数组
    Debug.Print "开始将文本转换为二维数组..."
    dataArray = ConvertTextTo2DArray(processedContent, processMode)
    Debug.Print "文本转换完成"
    Debug.Print "数组行数: " & UBound(dataArray, 1) & " 行"
    ' 批量写入单元格
    Debug.Print "开始批量写入数据..."
    If UBound(dataArray, 1) > 0 Then
        targetSheet.Range(startCell.Address).Resize(UBound(dataArray, 1), 1).Value = dataArray
        Debug.Print "数据写入完成，共 " & UBound(dataArray, 1) & " 行"
        ' 调整列宽
        targetSheet.Columns(startCell.Column).AutoFit
        Debug.Print "列宽已自动调整"
    Else
        Debug.Print "没有数据需要写入"
    End If
    Debug.Print "TXT数据导入完成！"
End Sub
' 使用Word对象模型读取文件内容

Function ReadFileContentWithWord(filePath As String) As String
    Dim wordapp As Object
    Dim worddoc As Object
    Dim content As String
    Debug.Print "开始使用Word对象模型读取文件..."
    Debug.Print "文件路径: " & filePath
    ' 创建Word应用实例
    Debug.Print "创建Word应用实例..."
    Set wordapp = CreateObject("Word.Application")
    wordapp.Visible = False
    wordapp.DisplayAlerts = False
    Debug.Print "Word应用实例创建成功"
    ' 打开文件（Word或TXT）
    Debug.Print "打开文件..."
    Set worddoc = wordapp.Documents.Open(filePath, readOnly:=True)
    Debug.Print "文件打开成功"
    ' 一次性读取全部内容
    Debug.Print "读取文件内容..."
    content = worddoc.Range.text
    Debug.Print "内容读取完成"
    ' 清理
    Debug.Print "关闭文件和清理资源..."
    worddoc.Close False
    wordapp.Quit
    Debug.Print "资源清理完成"
    ' 释放对象
    Set worddoc = Nothing
    Set wordapp = Nothing
    Debug.Print "对象释放完成"
    ReadFileContentWithWord = content
    Debug.Print "函数执行完成"
End Function
' 检测TXT文件编码

Function DetectEncoding(fileBytes() As Byte) As String
    Dim i As Integer
    Dim charByte1 As Byte
    Dim LL
    If UBound(fileBytes) >= 1 And fileBytes(0) = &HFF And fileBytes(1) = &HFE Then
        DetectEncoding = "UTF-16LE"
        Exit Function
    End If
    If UBound(fileBytes) >= 1 And fileBytes(0) = &HFE And fileBytes(1) = &HFF Then
        DetectEncoding = "UTF-16BE"
        Exit Function
    End If
    If UBound(fileBytes) >= 2 And fileBytes(0) = &HEF And fileBytes(1) = &HBB And fileBytes(2) = &HBF Then
        DetectEncoding = "UTF-8 BOM"
        Exit Function
    End If
    If UBound(fileBytes) > 100 Then
        LL = 100
    Else
        LL = UBound(fileBytes)
    End If
    For i = 0 To LL
        If fileBytes(i) > &H7F Then
            If (fileBytes(i) And &H80) = &H80 Then
                charByte1 = fileBytes(i)
                Select Case True
                    Case (charByte1 And &HF0) = &HE0
                        If i + 2 <= UBound(fileBytes) Then
                            If (fileBytes(i + 1) And &HC0) = &H80 And (fileBytes(i + 2) And &HC0) = &H80 Then
                                DetectEncoding = "UTF-8"
                                Exit Function
                            End If
                        End If
                    Case (charByte1 And &HF8) = &HF0
                        If i + 3 <= UBound(fileBytes) Then
                            If (fileBytes(i + 1) And &HC0) = &H80 And (fileBytes(i + 2) And &HC0) = &H80 And (fileBytes(i + 3) And &HC0) = &H80 Then
                                DetectEncoding = "UTF-8"
                                Exit Function
                            End If
                        End If
                    Case Else
                        DetectEncoding = "ANSI"
                        Exit Function
                End Select
            End If
        End If
    Next i
    DetectEncoding = "ANSI"
End Function
' 读取文件字节

Function ReadFileBytes(filePath As String) As Byte()
    Dim fileNumber As Integer
    Dim fileBytes() As Byte
    fileNumber = FreeFile
    Open filePath For Binary As #fileNumber
    ReDim fileBytes(LOF(fileNumber) - 1)
    Get #fileNumber, , fileBytes
    Close #fileNumber
    ReadFileBytes = fileBytes
End Function
' 读取ANSI编码的TXT文件

Function ReadTextFileANSI(filePath As String) As String
    Dim fileNo As Integer
    Dim lineText As String
    Dim content As String
    fileNo = FreeFile()
    On Error GoTo ErrorHandler
    Open filePath For Input As #fileNo
    Do While Not EOF(fileNo)
        Line Input #fileNo, lineText
        content = content & lineText & vbCrLf
    Loop
    Close #fileNo
    ReadTextFileANSI = content
    Exit Function
ErrorHandler:
    MsgBox "文件操作出错，请检查路径或内容格式。", vbExclamation
    If fileNo <> 0 Then Close #fileNo
    ReadTextFileANSI = ""
End Function
' 读取UTF-8编码的TXT文件

Function ReadTextFileUTF8(filePath As String) As String
    Dim stream As Object
    Dim content As String
    On Error GoTo ErrorHandler
    Set stream = CreateObject("ADODB.Stream")
    With stream
        .Type = 2
        .Charset = "utf-8"
        .Open
        .LoadFromFile filePath
        content = .ReadText
        .Close
    End With
    ReadTextFileUTF8 = content
    Set stream = Nothing
    Exit Function
ErrorHandler:
    MsgBox "文件操作出错，请检查路径或内容格式。", vbExclamation
    If Not stream Is Nothing Then
        stream.Close
        Set stream = Nothing
    End If
    ReadTextFileUTF8 = ""
End Function
' 读取Unicode编码的TXT文件

Function ReadTextFileUnicode(filePath As String) As String
    Dim fso As Object
    Dim ts As Object
    Dim content As String
    On Error GoTo ErrorHandler
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(filePath, 1, False, -1) ' -1 = TristateTrue
    content = ts.ReadAll
    ts.Close
    ReadTextFileUnicode = content
    Set ts = Nothing
    Set fso = Nothing
    Exit Function
ErrorHandler:
    MsgBox "文件操作出错，请检查路径或内容格式。", vbExclamation
    If Not ts Is Nothing Then
        ts.Close
        Set ts = Nothing
    End If
    Set fso = Nothing
    ReadTextFileUnicode = ""
End Function
' 处理方式1：保留部分标点（保留空格和全角空格）

Function ProcessTextWithSpaces(text As String) As String
    Dim regex As Object
    Set regex = CreateObject("VBScript.RegExp")
    ' 去除标点符号，保留中文字符、英文字母、数字、空格和全角空格
    With regex
        .Global = True
        .Pattern = "[^\u4e00-\u9fa5a-zA-Z0-9 \u3000]"
        text = .Replace(text, "|")
    End With
    ' 处理多余的特定符号
    With regex
        .Pattern = "\|{2,}"
        text = .Replace(text, "|")
    End With
    ' 去除首尾特定符号
    text = Trim(text, "|")
    ProcessTextWithSpaces = text
End Function
' 处理方式2：不保留标点（只保留中文字符、英文字母、数字）

Function ProcessTextWithoutPunctuation(text As String) As String
    Dim regex As Object
    Set regex = CreateObject("VBScript.RegExp")
    ' 去除标点符号，只保留中文字符、英文字母、数字
    With regex
        .Global = True
        .Pattern = "[^\u4e00-\u9fa5a-zA-Z0-9]"
        text = .Replace(text, "|")
    End With
    ' 处理多余的特定符号
    With regex
        .Pattern = "\|{2,}"
        text = .Replace(text, "|")
    End With
    ' 去除首尾特定符号
    text = Trim(text, "|")
    ProcessTextWithoutPunctuation = text
End Function
' 自定义Trim函数，支持指定字符

Function Trim(text As String, Optional charToTrim As String = " ") As String
    Dim regex As Object
    Set regex = CreateObject("VBScript.RegExp")
    With regex
        .Global = True
        .Pattern = "^[" & charToTrim & "]+|[" & charToTrim & "]+$"
        Trim = .Replace(text, "")
    End With
    Set regex = Nothing
End Function
' 带分割功能的自定义替换函数

Public Function CustomReplaceAndSplit(text As String) As Variant
    Dim processedText As String
    Dim regex As Object
    Dim resultArray() As String
    ' 步骤1: 替换LF为CRLF，再替换CR为CRLF
    processedText = Replace(Replace(text, vbLf, vbCrLf), vbCr, vbCrLf)
    ' 步骤2: 使用正则表达式将连续的CRLF压缩为单个CRLF
    Set regex = CreateObject("VBScript.RegExp")
    With regex
        .Global = True
        .Pattern = vbCrLf & "{2,}"
    End With
    processedText = regex.Replace(processedText, vbCrLf)
    ' 步骤3: 按CRLF分割字符串
    resultArray = Split(processedText, vbCrLf)
    ' 返回分割后的数组
    CustomReplaceAndSplit = resultArray
End Function
' 将处理后的文本转换为二维数组

Function ConvertTextTo2DArray(text As String, processMode As Integer) As Variant
    Dim elements() As String
    Dim lines() As String
    Dim resultArray() As Variant
    Dim i As Long
    Dim j As Long
    ' 处理空文本情况
    If Trim(text) = "" Then
        ConvertTextTo2DArray = Array()
        Exit Function
    End If
    Select Case processMode
        Case 1, 2 ' 处理过的文本（使用"|"分割）
            elements = Split(text, "|")
            ReDim resultArray(1 To UBound(elements) + 1, 1 To 1)
            For i = 0 To UBound(elements)
                resultArray(i + 1, 1) = Trim(elements(i))
            Next i
        Case 3 ' 正常读取（按行分割）
            lines = CustomReplaceAndSplit(text)
            ' 过滤空行
            j = 0
            For i = LBound(lines) To UBound(lines)
                If Trim(lines(i)) <> "" Then
                    j = j + 1
                End If
            Next i
            If j > 0 Then
                ReDim resultArray(1 To j, 1 To 1)
                j = 1
                For i = LBound(lines) To UBound(lines)
                    If Trim(lines(i)) <> "" Then
                        resultArray(j, 1) = Trim(lines(i))
                        j = j + 1
                    End If
                Next i
            Else
                resultArray = Array()
            End If
    End Select
    ConvertTextTo2DArray = resultArray
End Function
' 显示状态信息

Sub ShowStatus(message As String)
    Dim statusBarText As String
    ' 构建状态信息
    statusBarText = "【数据导入】 " & message
    ' 更新状态栏
    Application.StatusBar = statusBarText
    ' 短暂显示（对于长时间操作）
    DoEvents
End Sub
' 获取文件类型描述

Function GetFileTypeDescription(fileType As Integer) As String
    Select Case fileType
        Case 1
            GetFileTypeDescription = "Excel文件"
        Case 2
            GetFileTypeDescription = "Word文件"
        Case 3
            GetFileTypeDescription = "TXT文件"
        Case Else
            GetFileTypeDescription = "未知文件类型"
    End Select
End Function
' 获取处理方式描述

Function GetProcessModeDescription(processMode As Integer) As String
    Select Case processMode
        Case 1
            GetProcessModeDescription = "保留部分标点"
        Case 2
            GetProcessModeDescription = "不保留标点"
        Case 3
            GetProcessModeDescription = "正常读取"
        Case Else
            GetProcessModeDescription = "未知处理方式"
    End Select
End Function
' 获取导入方式描述

Function GetImportMethodDescription(importMethod As Integer) As String
    Select Case importMethod
        Case 1
            GetImportMethodDescription = "默认ActiveSheet [A1]导入"
        Case 2
            GetImportMethodDescription = "新建sheet页面导入"
        Case 3
            GetImportMethodDescription = "新建excel导入"
        Case 4
            GetImportMethodDescription = "选择指定单元格位置导入"
        Case Else
            GetImportMethodDescription = "未知导入方式"
    End Select
End Function

Sub FormatSheet()
    Dim ws As Worksheet
    Dim targetCell As Range
    Dim lastRow As Long
    On Error Resume Next
    ' 设置工作表和目标范围
    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row
    ' 如果有数据才进行格式设置
    If lastRow > 0 Then
        Set targetCell = ws.Range("A1:A" & lastRow)
        ' 禁用屏幕更新以提高性能
        Application.ScreenUpdating = False
        ' 应用样式设置
        ' 设置列宽
        ws.Columns("A:A").ColumnWidth = 200
        With targetCell
            .Font.Size = 26 ' 大字体
            .WrapText = True ' 自动换行
            .EntireRow.AutoFit ' 自动调整行高
            .Interior.Color = RGB(173, 216, 230) ' 浅蓝色背景
        End With
        ' 恢复屏幕更新
        Application.ScreenUpdating = True
    End If
End Sub
' 导出数据到Word文件
' 修复438错误：对象不支持该属性或方法
' 实现批量字符串连接后一次性写入Word
Sub ExportToWord()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim filePath As String
    Dim wordapp As Object
    Dim worddoc As Object
    Dim dataArray As Variant
    Dim exportCount As Long
    Dim i As Long
    Dim contentToWrite As String ' 存储所有要写入的内容
    Dim startTime As Double ' 开始时间
    Dim endTime As Double ' 结束时间
    Dim totalTime As Double ' 总耗时
    
    ' 初始化对象引用
    Set ws = Nothing
    Set wordapp = Nothing
    Set worddoc = Nothing
    
    On Error GoTo ErrorHandler
    
    ' 禁用屏幕更新以提高性能
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    ' 记录开始时间
    startTime = Timer
    
    ' 设置工作表
    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row
    
    ' 检查是否有数据
    If lastRow < 1 Then
        MsgBox "当前工作表没有数据可导出！", vbExclamation
        GoTo Cleanup
    End If
    
    ' 获取保存路径
    filePath = Application.GetSaveAsFilename( _
        FileFilter:="Word文档 (*.docx), *.docx", _
        Title:="保存为Word文件")
    
    If filePath = "False" Then Exit Sub
    
    ' 读取数据到数组以提高性能
    dataArray = ws.Range("A1:A" & lastRow).Value
    
    ' 构建要写入的内容（批量字符串连接）
    contentToWrite = ""
    exportCount = 0
    
    ' 显示进度条
    For i = 1 To UBound(dataArray, 1)
        ' 更新进度条
        If i Mod 100 = 0 Or i = UBound(dataArray, 1) Then
            Application.StatusBar = "正在准备导出数据... " & _
                                   Format(i / UBound(dataArray, 1), "0.00%") & _
                                   " (" & i & "/" & UBound(dataArray, 1) & ")"
            DoEvents ' 允许Excel更新界面
        End If
        
        If Not IsEmpty(dataArray(i, 1)) Then
            ' 连接字符串，添加换行符
            contentToWrite = contentToWrite & CStr(dataArray(i, 1)) & vbCr
            exportCount = exportCount + 1
        End If
    Next i
    
    ' 创建Word应用程序实例
    Application.StatusBar = "正在初始化Word应用程序..."
    Set wordapp = CreateObject("Word.Application")
    wordapp.Visible = False
    wordapp.DisplayAlerts = False
    
    ' 创建新文档
    Application.StatusBar = "正在创建Word文档..."
    Set worddoc = wordapp.Documents.Add
    
    ' 一次性写入所有内容到Word文档
    Application.StatusBar = "正在写入数据到Word文档..."
    ' 使用Range.Text属性避免content.InsertAfter可能的438错误
    worddoc.Range(0, 0).text = contentToWrite
    
    ' 保存文档（兼容早期Word版本）
    Application.StatusBar = "正在保存Word文档..."
    On Error Resume Next
    ' 先尝试使用SaveAs方法
    worddoc.SaveAs filePath, 16 ' 16 = wdFormatXMLDocument (docx格式)
    
    If err.number <> 0 Then
        ' 如果SaveAs失败，尝试使用SaveAs2
        err.Clear
        worddoc.SaveAs2 filePath, 16
    End If
    On Error GoTo ErrorHandler
    
    ' 关闭文档和Word应用程序
    Application.StatusBar = "正在关闭Word应用程序..."
    worddoc.Close False
    wordapp.Quit
    
    ' 清除状态栏
    Application.StatusBar = False
    
    ' 记录结束时间并计算总耗时
    endTime = Timer
    totalTime = endTime - startTime
    
    ' 显示完成信息，包含总耗时
    MsgBox "Word文件导出完成！" & vbCrLf & _
           "文件保存路径: " & filePath & vbCrLf & _
           "成功导出行数: " & exportCount & vbCrLf & _
           "总耗时: " & Format(totalTime, "0.00") & " 秒", vbInformation
    
Cleanup:
    ' 清理资源
    On Error Resume Next
    
    ' 确保状态栏被清除
    Application.StatusBar = False
    
    If Not worddoc Is Nothing Then
        worddoc.Close False
        Set worddoc = Nothing
    End If
    If Not wordapp Is Nothing Then
        wordapp.Quit
        Set wordapp = Nothing
    End If
    Set ws = Nothing
    
    ' 恢复设置
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    
    Exit Sub
    
ErrorHandler:
    ' 处理错误
    MsgBox "导出Word文件时出错: " & err.Description & vbCrLf & _
           "错误代码: " & err.number & vbCrLf & _
           "当前文件: " & filePath & vbCrLf & _
           "已处理行数: " & exportCount, vbCritical
    GoTo Cleanup
End Sub

' 导出数据到TXT文件 (优化版)
Sub ExportToTXT()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim filePath As String
    Dim stream As Object
    Dim dataArray As Variant
    Dim exportCount As Long
    Dim errorCount As Long
    Dim errorLog As String
    Dim i As Long
    Dim processedData As String
    Dim startTime As Double

    ' 初始化对象引用
    Set ws = Nothing
    Set stream = Nothing
    errorLog = ""

    On Error GoTo ErrorHandler

    ' 禁用屏幕更新以提高性能
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    startTime = Timer

    ' 设置工作表
    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row

    ' 检查是否有数据
    If lastRow < 1 Then
        MsgBox "当前工作表没有数据可导出！", vbExclamation
        GoTo Cleanup
    End If

    ' 获取保存路径
    filePath = Application.GetSaveAsFilename( _
        FileFilter:="文本文件 (*.txt), *.txt", _
        Title:="保存为TXT文件")

    If filePath = "False" Then Exit Sub

    ' 初始化ADODB.Stream对象（支持UTF-8编码）
    Set stream = CreateObject("ADODB.Stream")
    With stream
        .Type = 2 ' adTypeText
        .Charset = "UTF-8" ' 使用UTF-8编码替代ASCII
        .Open
    End With

    ' 读取数据到数组以提高性能
    dataArray = ws.Range("A1:A" & lastRow).Value

    ' 写入数据
    exportCount = 0
    errorCount = 0

    For i = 1 To UBound(dataArray, 1)
        ' 显示进度
        If i Mod 100 = 0 Or i = lastRow Then
            Application.StatusBar = "正在导出TXT文件... " & Format(i / lastRow, "0.00%") & _
                               " (" & i & "/" & lastRow & ")"
            DoEvents
        End If

        On Error Resume Next
        If Not IsEmpty(dataArray(i, 1)) Then
'            ' 数据预处理
'            processedData = PreprocessExportData(dataArray(i, 1))
' 数据预处理
            processedData = dataArray(i, 1)
            ' 写入数据
            stream.WriteText processedData & vbCrLf
            
            If err.number = 0 Then
                exportCount = exportCount + 1
            Else
                errorCount = errorCount + 1
                ' 记录错误信息
                errorLog = errorLog & "行 " & i & ": " & err.Description & " (原始数据: " & _
                          Left(dataArray(i, 1), 50) & IIf(Len(dataArray(i, 1)) > 50, "...", "") & ")" & vbCrLf
                err.Clear
            End If
        End If
        On Error GoTo ErrorHandler
    Next i

    ' 保存并关闭流
    stream.SaveToFile filePath, 2 ' adSaveCreateOverWrite
    stream.Close

    ' 显示完成信息
    Dim totalTime As Double
    totalTime = Timer - startTime
    
    Dim message As String
    message = "TXT文件导出完成！" & vbCrLf & _
              "文件保存路径: " & filePath & vbCrLf & _
              "成功导出行数: " & exportCount & vbCrLf & _
              "错误行数: " & errorCount & vbCrLf & _
              "耗时: " & Format(totalTime, "0.00") & " 秒"
    
    ' 如果有错误，显示错误详情
    If errorCount > 0 Then
        message = message & vbCrLf & vbCrLf & "错误详情:" & vbCrLf & errorLog
        MsgBox message, vbExclamation, "导出完成 - 包含错误"
    Else
        MsgBox message, vbInformation, "导出完成"
    End If

Cleanup:
    ' 清理资源
    On Error Resume Next
    If Not stream Is Nothing Then stream.Close: Set stream = Nothing
    Set ws = Nothing

    ' 恢复设置
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Application.StatusBar = False

    Exit Sub

ErrorHandler:
    ' 增强的错误处理
    Dim errorMsg As String
    errorMsg = "导出TXT文件时出错: " & vbCrLf & _
               "错误代码: " & err.number & vbCrLf & _
               "错误描述: " & err.Description & vbCrLf & _
               "当前行: " & IIf(i > 0, i, "未知") & vbCrLf & _
               "当前文件: " & filePath
    
    If errorCount > 0 Then
        errorMsg = errorMsg & vbCrLf & vbCrLf & "已记录的错误: " & errorCount & " 行"
    End If
    
    MsgBox errorMsg, vbCritical, "导出错误"
    GoTo Cleanup
End Sub

' 数据预处理函数（精简版，只保留核心功能）
Function PreprocessExportData(data As Variant) As String
    Dim result As String
    
    ' 1. 安全转换为字符串
    On Error Resume Next
    result = CStr(data)
    
    If err.number = 0 Then
        ' 2. 移除首尾空格
        result = Trim(result)
    Else
        ' 处理无法转换的数据
        result = "[无法转换的数据]"
        err.Clear
    End If
    
    On Error GoTo 0
    PreprocessExportData = result
End Function

