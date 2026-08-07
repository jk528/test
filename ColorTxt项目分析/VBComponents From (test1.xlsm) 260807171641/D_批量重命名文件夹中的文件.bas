Attribute VB_Name = "D_批量重命名文件夹中的文件"
Option Explicit

' 定义文件信息类型
Private Type FileInfo
    Name As String
    Path As String
    Size As Double
    Created As Date
    Modified As Date
    Type As String
End Type

Private fileCollection() As FileInfo
Private currentIndex As Long

' 主程序：获取文件信息并生成待处理表格
Sub 获取文件信息()
    Dim sourceFolder As String
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    ' 重置全局变量
    currentIndex = 0
    ReDim fileCollection(0 To 1000) ' 初始容量，动态调整

    ' 选择源文件夹
    sourceFolder = SelectFolder("请选择要扫描的文件夹")
    If sourceFolder = "" Then
        MsgBox "未选择源文件夹，程序退出", vbExclamation
        Exit Sub
    End If

    ' 递归扫描文件夹
    ScanFiles sourceFolder

    ' 无文件时退出
    If currentIndex = 0 Then
        MsgBox "未找到任何文件", vbInformation
        Exit Sub
    End If

    ' 调整数组大小
    ReDim Preserve fileCollection(0 To currentIndex - 1)

    ' 创建新工作表
    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
    ws.Name = "文件信息_" & Format(Now(), "yyyymmdd_hhmmss")

    ' 写入表头（含重命名所需列）
    With ws
        .Range("A1:H1").Value = Array("文件名", "完整路径", "大小(KB)", "创建时间", "修改时间", "文件类型", "新文件名", "新保存路径")
        .Range("A1:H1").Font.Bold = True
        .Range("A1:H1").HorizontalAlignment = xlCenter
        ' 预设新保存路径为源路径
        .Range("H2:H" & currentIndex + 1).Value = sourceFolder
    End With
Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    ' 写入文件信息
    For i = 0 To UBound(fileCollection)
        With ws
            .Cells(i + 2, 1).Value = fileCollection(i).Name
            .Cells(i + 2, 2).Value = fileCollection(i).Path
            .Cells(i + 2, 3).Value = fileCollection(i).Size / 1024
            .Cells(i + 2, 4).Value = fileCollection(i).Created
            .Cells(i + 2, 5).Value = fileCollection(i).Modified
            Dim ext As String
            ext = fso.GetExtensionName(fileCollection(i).Name)
            If ext <> "" Then
                .Cells(i + 2, 6).Value = ext
            Else
                .Cells(i + 2, 6).Value = ""
            End If
            '.Cells(i + 2, 6).Value = fileCollection(i).Type
            ' 默认新文件名为原文件名
            .Cells(i + 2, 7).Value = fso.GetBaseName(fileCollection(i).Name) ' fileCollection(i).Name
        End With
    Next i

    ' 格式化单元格
    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row
    ws.Range("A1:H" & lastRow).Columns.AutoFit
    ws.Range("C:C").NumberFormat = "0.00"
    ws.Range("D:E").NumberFormat = "yyyy-mm-dd hh:mm:ss"

    MsgBox "文件信息已提取完成，共找到 " & currentIndex & " 个文件\n请在 '新文件名' 和 '新保存路径' 列填写重命名规则", vbInformation
End Sub

' 选择文件夹对话框
Private Function SelectFolder(prompt As String) As String
    Dim fd As FileDialog
    Set fd = Application.FileDialog(msoFileDialogFolderPicker)
    With fd
        .Title = prompt
        .AllowMultiSelect = False
        If .Show = -1 Then
            SelectFolder = .SelectedItems(1)
        Else
            SelectFolder = ""
        End If
    End With
    Set fd = Nothing
End Function

' 递归扫描文件夹
Private Sub ScanFiles(folderPath As String)
    Dim fso As Object, folder As Object, file As Object, subFolder As Object
    Dim ext As String

    On Error Resume Next
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set folder = fso.GetFolder(folderPath)

    ' 权限检查
    If err.number <> 0 Then
        MsgBox "无法访问文件夹: " & folderPath & vbCrLf & err.Description, vbExclamation
        err.Clear
        Exit Sub
    End If

    ' 处理文件
    For Each file In folder.Files
        If Not file.Name Like "~$*" And Not file.Path = ThisWorkbook.FullName Then
            ' 动态扩容数组
            If currentIndex > UBound(fileCollection) Then
                ReDim Preserve fileCollection(0 To UBound(fileCollection) * 2)
            End If

            ' 收集文件信息
            With fileCollection(currentIndex)
                .Name = file.Name
                .Path = file.Path
                .Size = file.Size
                .Created = file.DateCreated
                .Modified = file.DateLastModified
                ext = fso.GetExtensionName(file.Path)
                .Type = IIf(ext = "", "无扩展名文件", ext & " 文件")
            End With

            currentIndex = currentIndex + 1
        End If
    Next file

    ' 递归子文件夹
    For Each subFolder In folder.SubFolders
        ScanFiles subFolder.Path
    Next subFolder

    On Error GoTo 0
    Set fso = Nothing: Set folder = Nothing
End Sub
' 批量重命名并另存文件
Sub 批量重命名并另存()
    Dim ws As Worksheet
    Dim fso As Object
    Dim lastRow As Long, i As Long, successCount As Long
    Dim sourcePath As String, targetPath As String
    Dim sourceName As String, targetName As String
    Dim t As Double

    t = Timer
    successCount = 0
    Set fso = CreateObject("Scripting.FileSystemObject")

    ' 验证当前工作表是否为文件信息表
    On Error Resume Next
    Set ws = ActiveSheet
    If ws.Range("A1").Value <> "文件名" Or ws.Range("H1").Value <> "新保存路径" Then
        MsgBox "请在文件信息工作表中运行此宏", vbExclamation
        Exit Sub
    End If

    lastRow = ws.Cells(ws.rows.count, "A").End(xlUp).row

    ' 遍历文件信息
    For i = 2 To lastRow
        sourceName = ws.Cells(i, 1).Value
        sourcePath = ws.Cells(i, 2).Value
        targetName = ws.Cells(i, 7).Value & "." & ws.Cells(i, 6).Value
        targetPath = ws.Cells(i, 8).Value

        ' 跳过空行
        If sourceName = "" Then Exit For

        ' 验证必要信息
        If targetName = "" Then
            ws.Cells(i, 9).Value = "错误：新文件名为空"
            ws.Cells(i, 9).Interior.Color = vbYellow
            GoTo NextFile
        End If

        ' 创建目标文件夹
        If Not fso.FolderExists(targetPath) Then
            On Error Resume Next
            fso.CreateFolder (targetPath)
            If err.number <> 0 Then
                ws.Cells(i, 9).Value = "文件夹创建失败: " & err.Description
                ws.Cells(i, 9).Interior.Color = vbRed
                err.Clear
                GoTo NextFile
            End If
            On Error GoTo 0
        End If

        ' 复制并重命名文件
        On Error Resume Next
        fso.CopyFile sourcePath, targetPath & "\" & targetName, OverWriteFiles:=True
        If err.number = 0 Then
            successCount = successCount + 1
            ws.Cells(i, 9).Value = "成功"
            ws.Cells(i, 9).Interior.Color = vbGreen
        Else
            ws.Cells(i, 9).Value = "失败: " & err.Description
            ws.Cells(i, 9).Interior.Color = vbRed
            err.Clear
        End If
        On Error GoTo 0

NextFile:
    Next i

    ' 完成报告
    Set fso = Nothing
    ws.Range("I1").Value = "处理状态"
'    ws.Range("I:I").AutoFit
    MsgBox "批量处理完成\n成功: " & successCount & " 个文件\n失败: " & (lastRow - 1 - successCount) & " 个文件\n耗时: " & Format(Timer - t, "0.00") & "秒", vbInformation
End Sub


