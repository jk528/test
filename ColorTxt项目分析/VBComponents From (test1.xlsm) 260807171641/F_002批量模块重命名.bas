Attribute VB_Name = "F_002批量模块重命名"
' 请先在VBE中添加对"Microsoft Visual Basic for Applications Extensibility 5.3"的引用
' 操作方法：工具 > 引用 > 勾选 "Microsoft Visual Basic for Applications Extensibility 5.3"

Option Explicit

' 声明EXTENSIBILITY库中的强类型变量
Dim VBProj As VBIDE.VBProject
Dim vbComp As VBIDE.VBComponent

' ======================================================
' VBA模块批量重命名工具 - 简化验证版
' ======================================================

' 获取所有模块名称并写入Excel表格
Sub 获取VBA模块名称()
    Dim ws As Worksheet
    Dim i As Long
    Dim moduleCount As Long
    Dim moduleDict As Object
    Dim moduleArray() As Variant
    Dim moduleInfo As Variant
    
    ' 使用强类型引用VBA项目
    Set VBProj = ThisWorkbook.VBProject
    Set moduleDict = CreateObject("Scripting.Dictionary")
    
    ' 创建或获取模块管理工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("模块管理")
    On Error GoTo 0
    
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        ws.Name = "模块管理"
        
        ' 设置表头
        With ws.Range("A1:D1")
            .Value = Array("当前模块名称", "新模块名称", "操作状态", "模块类型")
            .Font.Bold = True
            .Interior.Color = RGB(200, 200, 200)
            .HorizontalAlignment = xlCenter
        End With
        ws.Columns("A:C").ColumnWidth = 30
        ws.Columns("D").ColumnWidth = 15
    Else
        ' 清除现有数据但保留表头
        ws.Range("A2:D" & ws.Cells(ws.rows.count, "A").End(xlUp).row).ClearContents
    End If
    
    ' 预计算可重命名的模块数量
    moduleCount = 0
    For Each vbComp In VBProj.VBComponents
        If IsRenameableModule(vbComp.Type) Then
            moduleCount = moduleCount + 1
        End If
    Next vbComp
    
    ' 如果有可重命名的模块，初始化数组
    If moduleCount > 0 Then
        ' 定义二维数组存储模块信息: [名称, 类型, 背景色]
        ReDim moduleArray(1 To moduleCount, 1 To 3)
        
        i = 1
        ' 填充数组
        For Each vbComp In VBProj.VBComponents
            If IsRenameableModule(vbComp.Type) Then
                moduleArray(i, 1) = vbComp.Name ' 模块名称
                moduleDict.Add vbComp.Name, vbComp.Type
                
                ' 根据模块类型设置类型名称和背景颜色
                Select Case vbComp.Type
                    Case vbext_ct_StdModule
                        moduleArray(i, 2) = "标准模块" ' 模块类型
                        moduleArray(i, 3) = RGB(220, 230, 242) ' 背景颜色
                    Case vbext_ct_ClassModule
                        moduleArray(i, 2) = "类模块"
                        moduleArray(i, 3) = RGB(220, 242, 220)
                    Case vbext_ct_MSForm
                        moduleArray(i, 2) = "窗体模块"
                        moduleArray(i, 3) = RGB(242, 230, 220)
                End Select
                
                i = i + 1
            End If
        Next vbComp

        moduleArray = Sort2DArray(Sort2DArray(Sort2DArray(moduleArray, 2), 1), 2)
        
        ' 一次性写入模块数据
        For i = 1 To moduleCount
            ws.Cells(i + 1, 1).Value = moduleArray(i, 1) ' 写入模块名称
            ws.Cells(i + 1, 4).Value = moduleArray(i, 2) ' 写入模块类型
            ws.Cells(i + 1, 1).Interior.Color = moduleArray(i, 3) ' 设置背景颜色
        Next i
    End If
    
    ' 提示用户
    If moduleCount = 0 Then
        MsgBox "在当前工作簿中未找到可重命名的VBA模块。", vbInformation, "提示"
    Else
        MsgBox "已成功获取" & moduleCount & "个VBA模块名称。" & vbCrLf & _
               "请在B列输入要修改为的新模块名称，然后运行'批量重命名VBA模块'宏。" & vbCrLf & _
               "系统将尝试生成您输入的名称，即使可能存在命名规则限制。", vbInformation, "操作提示"
        ws.Activate
        ws.Range("B2").Select
    End If
    
    ' 释放对象
    Set ws = Nothing
    Set VBProj = Nothing
    Set moduleDict = Nothing
End Sub



' 判断模块类型是否可重命名
Function IsRenameableModule(moduleType As Long) As Boolean
    ' 标准模块、类模块和窗体模块可以重命名
    IsRenameableModule = (moduleType = vbext_ct_StdModule Or _
                         moduleType = vbext_ct_ClassModule Or _
                         moduleType = vbext_ct_MSForm)
End Function

' 批量重命名VBA模块
Sub 批量重命名VBA模块()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim currentName As String
    Dim newName As String
    Dim moduleExists As Boolean
    Dim renameCount As Integer
    Dim errorCount As Integer
    Dim duplicateNames As Object
    Dim moduleDict As Object
    Dim statusArray() As Variant
    Dim nameArray() As Variant
    Dim nameRange As Range
    Dim statusRange As Range
    
    ' 获取模块管理工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("模块管理")
    On Error GoTo 0
    
    If ws Is Nothing Then
        MsgBox "未找到'模块管理'工作表，请先运行'获取VBA模块名称'宏。", vbExclamation, "错误"
        Exit Sub
    End If
    
    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row
    If lastRow < 2 Then
        MsgBox "'模块管理'工作表中没有模块数据，请先运行'获取VBA模块名称'宏。", vbExclamation, "错误"
        Exit Sub
    End If
    
    ' 使用强类型引用VBA项目
    Set VBProj = ThisWorkbook.VBProject
    Set duplicateNames = CreateObject("Scripting.Dictionary")
    Set moduleDict = CreateObject("Scripting.Dictionary")
    
    ' 初始化计数器
    renameCount = 0
    errorCount = 0
    
    ' 构建模块字典以提高查找效率
    For Each vbComp In VBProj.VBComponents
        moduleDict.Add vbComp.Name, vbComp
    Next vbComp
    
    ' 清除之前的操作状态并初始化状态数组
    ReDim statusArray(1 To lastRow - 1, 1 To 1)
    ReDim nameArray(1 To lastRow - 1, 1 To 1)
    
    ' 获取当前名称和新名称范围
    Set nameRange = ws.Range("A2:B" & lastRow)
    
    ' 检查重复的新模块名（保留此检查，避免命名冲突）
    For i = 2 To lastRow
        newName = Trim(ws.Cells(i, 2).Value)
        If newName <> "" Then
            If duplicateNames.exists(newName) Then
                statusArray(i - 1, 1) = "错误：新名称重复"
                errorCount = errorCount + 1
            Else
                duplicateNames.Add newName, i
            End If
        End If
    Next i
    
    ' 如果有重复的新名称，一次性写入错误状态并退出
    If errorCount > 0 Then
        ws.Range("C2:C" & lastRow).Value = statusArray
        
        ' 设置错误行的颜色
        For i = 2 To lastRow
            If statusArray(i - 1, 1) = "错误：新名称重复" Then
                ws.Cells(i, 3).Interior.Color = vbRed
            End If
        Next i
        
        MsgBox "发现" & errorCount & "个重复的新模块名称，请修正后重试。", vbExclamation, "错误"
        ws.Activate
        GoTo Cleanup
    End If
    
    ' 执行重命名操作
    For i = 2 To lastRow
        currentName = Trim(ws.Cells(i, 1).Value)
        newName = Trim(ws.Cells(i, 2).Value)
        nameArray(i - 1, 1) = currentName ' 初始化为当前名称
        
        ' 跳过条件检查
        If currentName = "" Then
            statusArray(i - 1, 1) = "跳过：当前名称为空"
            GoTo NextIteration
        End If
        
        If newName = "" Then
            statusArray(i - 1, 1) = "跳过：未提供新名称"
            GoTo NextIteration
        End If
        
        ' 检查模块是否存在
        moduleExists = moduleDict.exists(currentName)
        
        If Not moduleExists Then
            statusArray(i - 1, 1) = "错误：模块不存在"
            errorCount = errorCount + 1
            GoTo NextIteration
        End If
        
        ' 检查新名称是否已被使用
        If moduleDict.exists(newName) And newName <> currentName Then
            statusArray(i - 1, 1) = "错误：新名称已存在"
            errorCount = errorCount + 1
            GoTo NextIteration
        End If
        
        ' 简化的名称验证 - 只检查基本的非空，其他都尝试生成
        If Not IsValidModuleName(newName) Then
            statusArray(i - 1, 1) = "警告：名称可能不规范"
            ' 不退出，继续尝试重命名
        End If
        
        ' 执行重命名 - 尝试生成，不预先阻止
        On Error Resume Next
        Set vbComp = moduleDict(currentName)
        vbComp.Name = newName
        
        If err.number = 0 Then
            statusArray(i - 1, 1) = "成功：重命名完成"
            nameArray(i - 1, 1) = newName ' 更新为新名称
            renameCount = renameCount + 1
            
            ' 更新字典中的模块名称
            moduleDict.Add newName, vbComp
            moduleDict.Remove currentName
        Else
            statusArray(i - 1, 1) = "错误：" & err.Description
            errorCount = errorCount + 1
            err.Clear
        End If
        On Error GoTo 0
        
NextIteration:
    Next i
    
    ' 一次性写入操作状态和更新后的名称
    ws.Range("C2:C" & lastRow).Value = statusArray
    ws.Range("A2:A" & lastRow).Value = nameArray
    
    ' 设置状态单元格的颜色
    For i = 2 To lastRow
        Select Case Left(statusArray(i - 1, 1), 2)
            Case "成功": ws.Cells(i, 3).Interior.Color = vbGreen
            Case "错误": ws.Cells(i, 3).Interior.Color = vbRed
            Case "跳过", "警告": ws.Cells(i, 3).Interior.Color = vbYellow
        End Select
    Next i
    
    ' 显示结果
    Dim skipCount As Integer
    skipCount = (lastRow - 1 - renameCount - errorCount)
    
    MsgBox "批量重命名操作完成！" & vbCrLf & vbCrLf & _
           "成功重命名：" & renameCount & "个模块" & vbCrLf & _
           "失败：" & errorCount & "个模块" & vbCrLf & _
           "跳过：" & skipCount & "个模块", vbInformation, "操作结果"
    
    ws.Activate

Cleanup:
    ' 释放对象
    Set ws = Nothing
    Set VBProj = Nothing
    Set duplicateNames = Nothing
    Set moduleDict = Nothing
End Sub

' 检查模块名称是否合法（极度简化版）
Function IsValidModuleName(moduleName As String) As Boolean
    ' 只做最基本的非空检查，其他都尝试生成
    If Trim(moduleName) <> "" Then
        IsValidModuleName = True
    Else
        IsValidModuleName = False
    End If
End Function

' 创建简单界面
Sub 创建模块管理界面()
    Dim ws As Worksheet
    Dim btn As Object
    
    ' 获取或创建工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("模块管理")
    On Error GoTo 0
    
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
        ws.Name = "模块管理"
    End If
    
    ' 清除现有内容和按钮
    ws.Cells.Clear
    For Each btn In ws.Shapes
        If TypeName(btn) = "Button" Then btn.Delete
    Next btn
    
    ' 设置界面
    With ws
        ' 标题
        .Range("A1").Value = "VBA模块批量重命名工具"
        .Range("A1").Font.Size = 16
        .Range("A1").Font.Bold = True
        
        ' 说明文字
        .Range("A3").Value = "使用说明："
        .Range("A3").Font.Bold = True
        .Range("A4").Value = "1. 点击'获取模块名称'按钮获取所有VBA模块"
        .Range("A5").Value = "2. 在B列输入要修改为的新模块名称"
        .Range("A6").Value = "3. 点击'批量重命名'按钮执行重命名操作"
        
        ' 简化验证说明
        .Range("A8").Value = "名称规则："
        .Range("A8").Font.Bold = True
        .Range("A9").Value = "- 系统将尝试生成您输入的任何非空名称"
        .Range("A10").Value = "- 仅检查名称是否为空和是否重复"
        .Range("A11").Value = "- 某些特殊字符或格式可能导致重命名失败"
        
        ' 创建按钮
        With .Buttons.Add(.Range("B9:C9").Left, .Range("B9:C9").Top, .Range("B9:C9").Width, .Range("B9:C9").Height)
            .Caption = "获取模块名称"
            .OnAction = "获取VBA模块名称"
            .Font.Bold = True
        End With
        
        With .Buttons.Add(.Range("B11:C11").Left, .Range("B11:C11").Top, .Range("B11:C11").Width, .Range("B11:C11").Height)
            .Caption = "批量重命名"
            .OnAction = "批量重命名VBA模块"
            .Font.Bold = True
        End With
        
        ' 调整列宽
        .Columns("A").ColumnWidth = 50
        .Columns("B:C").ColumnWidth = 15
    End With
    
    MsgBox "模块管理界面已创建完成，请在'模块管理'工作表中操作。", vbInformation, "操作提示"
    ws.Activate
    
    ' 释放对象
    Set ws = Nothing
End Sub

