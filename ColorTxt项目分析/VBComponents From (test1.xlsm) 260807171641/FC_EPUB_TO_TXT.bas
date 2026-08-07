Attribute VB_Name = "FC_EPUB_TO_TXT"
Option Explicit
Dim fso As Object, nb As String
Sub epubtotxt()
    Dim epubpath As String, zippath As String, txtpath As String
    Dim tempfolder As String
    Dim rarexepath As String
    Dim command As String
    Dim result As Long
    Dim zipsize As Long, waitseconds As Double
    Dim waittime As Date
    On Error GoTo ErrorHandler
    nb = 0
    '1选择epub文件
    With Application.FileDialog(msoFileDialogFilePicker)
        .Title = "选择要转换的EPUB文件"
        .filters.Clear
        .filters.Add "EPUB文件", "*.epub"
        If .Show = -1 Then
            epubpath = .SelectedItems(1)
        Else
            MsgBox "文件未选择,操作取消"
        End If
    End With
    '2初始化文件系统对象
    Set fso = CreateObject("Scripting.FileSystemObject")
    '3生成临时文件夹路径和zip路径
    tempfolder = fso.getparentfoldername(epubpath) & "\" & fso.GetBaseName(epubpath) & "_temp"
    zippath = Replace(epubpath, ".epub", ".zip")
    '4重命名EPUB为ZIP(确保清除旧文件)
    If fso.fileexists(zippath) Then fso.deletefile zippath, True
    fso.movefile epubpath, zippath
    '5创建临时文件夹
    If fso.FolderExists(tempfolder) Then fso.DeleteFolder tempfolder, True
    fso.CreateFolder tempfolder
    '6解压zip到临时文件夹
    rarexepath = "C:\program files\winrar\winrar.exe"
    command = """" & rarexepath & """ x -ep """ & zippath & """ """ & tempfolder & """"
    result = Shell(command, vbHide)
    '获取zip文件大小
    zipsize = fso.getfile(zippath).Size
    '根据文件大小计算等待时间
    Const ksecondsperMB As Double = 0.7 'MB等待时间
    waitseconds = (zipsize / 1024 / 1024) * ksecondsperMB
    If waitseconds < 3 Then waitseconds = 3 '设置最小时间
    waitseconds = Int(waitseconds + 0.5) '四舍五入取整数
    waittime = Now + TimeSerial(0, 0, waitseconds)
    Application.Wait waittime
    '7生成TXT文件(保存到EPUB目录)
    txtpath = fso.getparentfoldername(epubpath) & "\" & fso.GetBaseName(epubpath) & ".txt"
    Dim txtFile As Object
    Set txtFile = fso.CreateTextFile(txtpath, True)
    '遍历所有HTML/XHTML文件提取文本内容
    processallhtmlfiles tempfolder, txtFile, fso
    txtFile.Close
    '8恢复EPUB文件
    fso.movefile zippath, epubpath
Cleanup:
    On Error Resume Next
    nb = 0
    If Len(zippath) > 0 And Len(epubpath) > 0 Then
    fso.movefile zippath, epubpath
    End If
    If fso.FolderExists(tempfolder) Then fso.DeleteFolder tempfolder, True
    Set fso = Nothing
    If Len(txtpath) > 0 Then
        MsgBox "OK"
    Else
'        MsgBox "NO"
    End If
    Exit Sub
ErrorHandler:
'    MsgBox "错误代码:" & err.Number & vbCrLf & err.Description
    GoTo Cleanup
End Sub

'递归处理子文件夹中的html\xhtml文件
Sub processallhtmlfiles(folderPath As String, output As Object, fso As Object)
    Dim currentfolder As Object
    Set currentfolder = fso.GetFolder(folderPath)
    processfolder currentfolder, output, fso
End Sub

'递归遍历子文件夹
Private Sub processfolder(folder As Object, output As Object, fsd As Object)
    Dim file As Object
    Dim subFolder As Object '怀疑错误?
    '处理当前文件夹中的所有HTML\XHTML文件
    For Each file In folder.Files
    nb = nb + 1
        Dim ext As String
        ext = LCase(fso.GetExtensionName(file.Name))
        If ext = "html" Or ext = "htm" Or ext = "xhtml" Then
            processallhtmlfile file, output
        End If
    Next
    '递归处理子文件夹
    For Each subFolder In folder.SubFolders
        processfolder subFolder, output, fso
    Next
End Sub

'处理单个HTML\XHTML文件
Private Sub processallhtmlfile(file As Object, output As Object)
    Dim content As String
    content = ReadtextFile(file.Path)
    Dim processedText As String
    processedText = extracttextfromhtml(content)
    output.WriteLine vbCrLf
    output.WriteLine "第" & nb - 1 & "章___" & processedText
End Sub

Private Function ReadtextFile(filePath As String) As String
    Dim adstream As Object
    Set adstream = CreateObject("adodb.stream")
    adstream.Type = 2
    adstream.Charset = "UTF-8"
    adstream.Open
    adstream.LoadFromFile filePath
    ReadtextFile = adstream.ReadText
    adstream.Close
    Set adstream = Nothing
End Function
Private Function extracttextfromhtml(html As String) As String
    Dim regex As Object
    Set regex = CreateObject("VBScript.Regexp")
   
    With regex
        .Global = True
        .IgnoreCase = True  ' 统一处理大小写标签

        .Pattern = "<title.*/title>"
        html = .Replace(html, "|")
        .Pattern = "<blockquote.*/blockquote>"
        html = .Replace(html, "|")
        ' 第二步：删除所有剩余HTML标签（含属性）
        .Pattern = "<[^>]+>"  ' 匹配任意标签（包括自闭合标签）
        html = .Replace(html, "|")
        
        ' 第三步：处理HTML实体（修正分号缺失问题）
        html = Replace(html, "&nbsp;", " ")    ' 空格（补充分号）
        html = Replace(html, "&quot;", """")   ' 引号
        html = Replace(html, "&apos;", "'")    ' 单引号
        html = Replace(html, "&gt;", ">")      ' 大于号
        html = Replace(html, "&lt;", "<")      ' 小于号
        html = Replace(html, "&amp;", "&")     ' 连接号


        ' 保留：中文、英文、数字、常见中文标点、连接符
        .Pattern = "[^\u4e00-\u9fa5a-zA-Z0-9,?!:;{}()|~，。.…/_？！：:；“”‘’（）{}【】|、\-—<>&  ]+"
        html = .Replace(html, "|")
         .Pattern = "(\|){2,}"  ' 匹配2个及以上连续换行
        html = .Replace(html, "|")
    End With
    html = Right(html, Len(html) - 1)
    html = Replace(html, "|", vbCrLf & vbCrLf)
    extracttextfromhtml = Trim(html)  ' 去除首尾空白
End Function
