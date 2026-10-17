Attribute VB_Name = "F_001获取全部代码"
Option Explicit

' 主要功能：读取所有VBA代码并完整输出到Excel表格
Sub 读取所有代码到表格()
    On Error GoTo ErrorHandler
    
    Dim VBProj As Object
    Dim vbComp As Object
    Dim CodeMod As Object
    Dim ws As Worksheet
    Dim codeArray() As Variant
    Dim i As Long, j As Long, outputRow As Long
    Dim moduleName As String, moduleType As String
    Dim lineText As String
    Dim totalLines As Long, moduleLineCount As Long
    Dim startTimer As Double
    
    startTimer = Timer ' 记录开始时间
    
    ' 创建或准备结果工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("完整代码输出")
    On Error GoTo ErrorHandler
    
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        ws.Name = "完整代码输出"
    Else
        ws.Cells.ClearContents ' 清空现有内容
    End If
    
    ' 设置标题行
    With ws
        .Cells(1, 1).Value = "模块名称"
        .Cells(1, 2).Value = "模块类型"
        .Cells(1, 3).Value = "代码行号"
        .Cells(1, 4).Value = "代码内容"
        
        ' 格式化标题行
        With .Range("A1:D1")
            .Font.Bold = True
            .Interior.ColorIndex = 15 ' 浅灰色背景
            .HorizontalAlignment = xlCenter
        End With
    End With
    
    ' 尝试获取VBA项目
    On Error Resume Next
    Set VBProj = ThisWorkbook.VBProject
    
    If err.number <> 0 Then
        MsgBox "无法访问VBA项目。请在Excel选项中启用对VBA项目对象模型的信任访问。", vbExclamation
        Exit Sub
    End If
    On Error GoTo ErrorHandler
    
    ' 第一步：计算所有代码总行数，用于预分配数组
    totalLines = 0
    For Each vbComp In VBProj.VBComponents
        totalLines = totalLines + vbComp.CodeModule.CountOfLines
    Next vbComp
    
    ' 预分配二维数组，每行一个代码行
    ReDim codeArray(1 To totalLines, 1 To 4)
    outputRow = 1 ' 数组索引从1开始
    
    ' 第二步：遍历所有模块并读取代码
    For Each vbComp In VBProj.VBComponents
        moduleName = vbComp.Name
        
        ' 确定模块类型
        Select Case vbComp.Type
            Case 1: moduleType = "标准模块"
            Case 2: moduleType = "类模块"
            Case 3: moduleType = "窗体模块"
            Case 100: moduleType = "文档模块"
            Case Else: moduleType = "未知类型"
        End Select
        
        ' 获取代码模块
        Set CodeMod = vbComp.CodeModule
        moduleLineCount = CodeMod.CountOfLines
        
        ' 逐行读取并存储到二维数组
        For i = 1 To moduleLineCount
            lineText = CodeMod.lines(i, 1) ' 获取第i行代码
            
            ' 填充数组
            codeArray(outputRow, 1) = moduleName ' 模块名称
            codeArray(outputRow, 2) = moduleType ' 模块类型
            codeArray(outputRow, 3) = i ' 行号
            codeArray(outputRow, 4) = lineText ' 代码内容
            
            outputRow = outputRow + 1 ' 移至下一行
        Next i
        
        ' 清理对象引用
        Set CodeMod = Nothing
    Next vbComp
    
    ' 第三步：将二维数组输出到Excel表格
    If outputRow > 1 Then
        ' 输出数组内容到工作表，从第2行开始
        ws.Range("A2:D" & outputRow - 1).Value = codeArray
        
        ' 格式化输出
        With ws
            ' 调整列宽
            .Columns("A:A").ColumnWidth = 25 ' 模块名称列
            .Columns("B:B").ColumnWidth = 15 ' 模块类型列
            .Columns("C:C").ColumnWidth = 10 ' 行号列
            .Columns("D:D").ColumnWidth = 100 ' 代码内容列（较宽以便显示完整代码）
            
            ' 设置行高自动适应内容
            .Columns("D:D").WrapText = True
            .rows.AutoFit
            
            ' 设置行号列为数字格式
            .Columns("C:C").NumberFormat = "0"
            
            ' 添加自动筛选
            .Range("A1:D1").AutoFilter
            
            ' 冻结窗格，便于滚动时查看标题
            .Range("A2").Select
            .Activate
            ActiveWindow.FreezePanes = True
            
            ' 添加统计信息
            Dim statsRow As Long
            statsRow = outputRow + 2
            .Cells(statsRow, 1).Value = "统计信息："
            .Cells(statsRow, 1).Font.Bold = True
            .Cells(statsRow + 1, 2).Value = "总代码行数："
            .Cells(statsRow + 1, 3).Value = outputRow - 1
            .Cells(statsRow + 2, 2).Value = "总模块数："
            .Cells(statsRow + 2, 3).Value = VBProj.VBComponents.count
            .Cells(statsRow + 3, 2).Value = "执行时间："
            .Cells(statsRow + 3, 3).Value = Format(Timer - startTimer, "0.000") & " 秒"
        End With
        
        ' 提示完成
        MsgBox "已成功读取所有VBA代码并输出到表格！共读取了 " & outputRow - 1 & " 行代码。", vbInformation
    Else
        MsgBox "未找到任何VBA代码。", vbInformation
    End If
    
    ' 清理对象引用
    Set vbComp = Nothing
    Set VBProj = Nothing
    Set ws = Nothing
    Exit Sub
    
ErrorHandler:
    MsgBox "发生错误: " & err.Description & " (错误号: " & err.number & ")", vbCritical
    
    ' 清理对象引用
    On Error Resume Next
    Set CodeMod = Nothing
    Set vbComp = Nothing
    Set VBProj = Nothing
    Set ws = Nothing
End Sub

' 辅助功能：快速测试单个模块的代码读取
Sub 读取单个模块代码()
    On Error GoTo ErrorHandler
    
    Dim VBProj As Object
    Dim vbComp As Object
    Dim CodeMod As Object
    Dim ws As Worksheet
    Dim moduleName As String
    Dim moduleLineCount As Long, i As Long
    Dim resultArray() As Variant
    
    ' 获取用户指定的模块名
    moduleName = InputBox("请输入要读取的模块名称：", "读取单个模块代码")
    If moduleName = "" Then Exit Sub
    
    ' 尝试获取VBA项目
    On Error Resume Next
    Set VBProj = ThisWorkbook.VBProject
    
    If err.number <> 0 Then
        MsgBox "无法访问VBA项目。请在Excel选项中启用对VBA项目对象模型的信任访问。", vbExclamation
        Exit Sub
    End If
    On Error GoTo ErrorHandler
    
    ' 查找指定模块
    Set vbComp = Nothing
    For Each vbComp In VBProj.VBComponents
        If vbComp.Name = moduleName Then
            Exit For
        End If
    Next vbComp
    
    If vbComp Is Nothing Then
        MsgBox "未找到名为 '" & moduleName & "' 的模块。", vbExclamation
        Exit Sub
    End If
    
    ' 创建结果工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("单个模块代码")
    On Error GoTo ErrorHandler
    
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        ws.Name = "单个模块代码"
    Else
        ws.Cells.ClearContents
    End If
    
    ' 设置标题
    ws.Cells(1, 1).Value = "行号"
    ws.Cells(1, 2).Value = "代码内容"
    ws.Range("A1:B1").Font.Bold = True
    ws.Range("A1:B1").Interior.ColorIndex = 15
    
    ' 获取代码模块
    Set CodeMod = vbComp.CodeModule
    moduleLineCount = CodeMod.CountOfLines
    
    ' 预分配数组
    ReDim resultArray(1 To moduleLineCount, 1 To 2)
    
    ' 读取代码到数组
    For i = 1 To moduleLineCount
        resultArray(i, 1) = i
        resultArray(i, 2) = CodeMod.lines(i, 1)
    Next i
    
    ' 输出到工作表
    ws.Range("A2:B" & moduleLineCount + 1).Value = resultArray
    
    ' 格式化
    ws.Columns("A:A").ColumnWidth = 8
    ws.Columns("B:B").ColumnWidth = 100
    ws.Columns("B:B").WrapText = True
    ws.rows.AutoFit
    
    MsgBox "已成功读取模块 '" & moduleName & "' 的代码，共 " & moduleLineCount & " 行。", vbInformation
    
    ' 清理
    Set CodeMod = Nothing
    Set vbComp = Nothing
    Set VBProj = Nothing
    Set ws = Nothing
    Exit Sub
    
ErrorHandler:
    MsgBox "发生错误: " & err.Description & " (错误号: " & err.number & ")", vbCritical
    On Error Resume Next
    Set CodeMod = Nothing
    Set vbComp = Nothing
    Set VBProj = Nothing
    Set ws = Nothing
End Sub

' 创建简单的操作界面
Sub 创建操作界面()
    Dim ws As Worksheet
    Dim btn1 As Button, btn2 As Button
    
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("代码读取工具")
    On Error GoTo 0
    
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        ws.Name = "代码读取工具"
    Else
        ws.Cells.Clear
    End If
    
    ' 设置标题
    With ws.Range("A1:C1")
        .Merge
        .Value = "VBA代码完整读取工具"
        .Font.Bold = True
        .Font.Size = 16
        .HorizontalAlignment = xlCenter
    End With
    
    ' 添加说明
    ws.Range("A3").Value = "此工具用于读取Excel工作簿中所有VBA代码并完整输出到Excel表格。"
    ws.Range("A4").Value = "输出结果包含模块名称、模块类型、代码行号和完整代码内容。"
    
    ' 创建按钮
    Set btn1 = ws.Buttons.Add(150, 80, 180, 30)
    With btn1
        .Caption = "读取所有代码到表格"
        .OnAction = "读取所有代码到表格"
        .Font.Bold = True
    End With
    
    Set btn2 = ws.Buttons.Add(150, 120, 180, 30)
    With btn2
        .Caption = "读取指定模块代码"
        .OnAction = "读取单个模块代码"
        .Font.Bold = True
    End With
    
    ' 添加注意事项
    ws.Range("A8").Value = "注意事项："
    ws.Range("A9").Value = "1. 需要在Excel选项中启用对VBA项目对象模型的信任访问"
    ws.Range("A10").Value = "2. 代码内容将完整保留，包括注释和空行"
    ws.Range("A11").Value = "3. 读取大项目时可能需要一定时间"
    
    ws.Columns("A").ColumnWidth = 60
    
    MsgBox "操作界面已创建完成！", vbInformation
End Sub

'' 自动打开时创建界面
'Sub Auto_Open()
'    On Error Resume Next
'    创建操作界面
'    On Error GoTo 0
'End Sub
