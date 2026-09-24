Attribute VB_Name = "F_003导出模块到指定文件夹"
Public Sub ExportCodeFile()
    ' 导出所有工程文件至指定文件夹
    
    On Error GoTo ErrorHandler
    
    Dim fso As Object
    Dim exportPath As String
    Dim component As Object
    Dim fileNumber As Integer
    Dim lineCount As Long
    Dim i As Long
    Dim componentPath As String
    Dim basePath As String
    
    ' 获取当前工作簿路径
    basePath = ActiveWorkbook.Path
    
    ' 让用户选择导出文件夹
    With Application.FileDialog(msoFileDialogFolderPicker)
        .Title = "请选择目标文件夹"
        .InitialFileName = basePath & "\"
        .AllowMultiSelect = False
        
        If .Show = 0 Then
            GoTo Cleanup
        Else
            exportPath = .SelectedItems(1) & "\"
        End If
    End With
    
    ' 创建文件系统对象
    Set fso = CreateObject("Scripting.FileSystemObject")
    
    ' 新文件夹路径
    exportPath = exportPath & "VBComponents From (" & ActiveWorkbook.Name & ") " & Format(Now, "yymmddhhmmss")
    
    ' 创建新文件夹
    If Not fso.FolderExists(exportPath) Then
        fso.CreateFolder exportPath
    End If
    
    exportPath = exportPath & "\"
    
    ' 禁用事件
    Application.EnableEvents = False
    
    ' 遍历组件
    For Each component In ActiveWorkbook.VBProject.VBComponents
        Select Case component.Type
            Case 1 ' 标准模块
                component.Export exportPath & component.Name & ".bas"
                
            Case 2 ' 类模块
                component.Export exportPath & component.Name & ".cls"
                
            Case 3 ' 用户窗体
                component.Export exportPath & component.Name & ".frm"
                
            Case 100 ' Microsoft Excel对象（工作表、ThisWorkbook等）
                fileNumber = FreeFile
                componentPath = exportPath & component.Name & ".txt"
                
                ' 打开txt文件进行写入
                Open componentPath For Output As fileNumber
                
                ' 遍历组件中的代码
                lineCount = component.CodeModule.CountOfLines
                For i = 1 To lineCount
                    Print #fileNumber, component.CodeModule.lines(i, 1)
                Next i
                
                ' 关闭文件
                Close fileNumber
        End Select
    Next component
    
    ' 成功提示
    If MsgBox("当前工作簿的所有工程文件已成功导出至文件夹：" & vbNewLine & exportPath & vbNewLine & vbNewLine & "是否需要打开文件夹查看？", vbInformation + vbOKCancel, "导出完成") = vbOK Then
        Shell "Explorer /select, " & exportPath, vbNormalFocus
    End If
    
    GoTo Cleanup
    
ErrorHandler:
    ' 错误处理
    If Not fso Is Nothing And Len(exportPath) > 0 Then
        On Error Resume Next
        fso.DeleteFolder Left(exportPath, Len(exportPath) - 1), True
        On Error GoTo 0
    End If
    
    MsgBox "导出失败：" & err.number & vbNewLine & err.Description, vbCritical, "错误"
    
Cleanup:
    ' 清理
    Set fso = Nothing
    Set component = Nothing
    Application.EnableEvents = True
    
End Sub
