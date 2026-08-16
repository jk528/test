Attribute VB_Name = "SplitTxtByChapter"
Option Explicit

'==============================================================================
' 模块名称：SplitTxtByChapter
' 功能描述：按章节标题（第N章/第N回 标题）拆分TXT文本为多个独立文件
' 适配场景：中文小说类长文本（已验证红楼梦.txt：UTF-8无BOM / 2.57MB / 120章）
' 输出格式：每章一个文件，命名 [<前缀>_]<序号> <标题>.txt（UTF-8无BOM）
'   - 序号与标题间用半角空格；标题内半角空格转全角空格（对齐西游记章节风格）
'   - 命名规则与 split_honglou_to_west_style.py 完全一致
' 工程约定：
'   - 所有Dim在过程顶部声明，循环内不重复Dim（WPS VBA严格性要求）
'   - 字符串拼接使用数组收集 + Join
'   - 读写依赖 ReadTxtUniversal.bas（自动检测 ANSI/UTF-8/UTF-16 编码）
'   - 写入前预览章节清单并经用户确认，显示计时与吞吐量
'==============================================================================

'------------------------------------------------------------------------------
' 对外入口：选择TXT文件 → 拆分每章一个文件
'   运行后弹出文件选择对话框，筛选 .txt 文件；选中即调用 SplitTxtByChapter
'   输出目录默认为 源文件所在目录\<文件名>_拆分\
'------------------------------------------------------------------------------
Public Sub 拆分()
    Dim fd As Object

    On Error Resume Next
    Set fd = Application.FileDialog(3)   ' msoFileDialogFilePicker = 3
    On Error GoTo 0

    If fd Is Nothing Then
        MsgBox "当前环境不支持文件选择对话框。", vbExclamation, "提示"
        Exit Sub
    End If

    fd.Title = "选择要拆分的TXT文件"
    On Error Resume Next
    fd.Filters.Clear
    fd.Filters.Add "文本文件", "*.txt"
    fd.Filters.Add "所有文件", "*.*"
    On Error GoTo 0

    If fd.Show <> -1 Then Exit Sub

    SplitTxtByChapter _
        InputPath:=fd.SelectedItems(1), _
        OutputDir:="", _
        FileNamePrefix:="", _
        SerialWidth:=3
End Sub

'------------------------------------------------------------------------------
' 核心过程：通用拆分（可处理任意按"第N章/回/节/卷"分隔的TXT）
'   InputPath       源TXT完整路径
'   OutputDir       输出目录；传空串表示 源目录\<源文件名>_拆分\
'   FileNamePrefix  文件名前缀；传空串表示无前缀（仅 序号 标题.txt）
'   SerialWidth     序号位数；如 3 -> 001, 002, ..., 120
'------------------------------------------------------------------------------
Public Sub SplitTxtByChapter(InputPath As String, _
                             Optional OutputDir As String = "", _
                             Optional FileNamePrefix As String = "", _
                             Optional SerialWidth As Long = 3)
    ' === 所有变量声明在过程顶部 ===
    Dim fso As Object, reg As Object
    Dim stm As Object, stmOut As Object
    Dim content As String, body As String
    Dim lines() As String, bodyLines() As String
    Dim lineCount As Long, i As Long, j As Long, n As Long
    Dim chCount As Long, previewEnd As Long
    Dim chTitles() As String
    Dim chStarts() As Long, chEnds() As Long
    Dim t0 As Double, t1 As Double
    Dim srcDir As String, baseName As String, outDirFull As String
    Dim prefix As String, safeTitle As String, fileName As String, outPath As String
    Dim serialFmt As String, serial As String
    Dim ans As VbMsgBoxResult
    Dim preview As String
    Dim oldFile As String, oldCount As Long

    ' --- 校验输入文件 ---
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(InputPath) Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    srcDir = fso.GetParentFolderName(InputPath)
    baseName = fso.GetBaseName(InputPath)

    ' --- 确定输出目录 ---
    If Len(Trim(OutputDir)) = 0 Then
        outDirFull = srcDir & "\" & baseName & "_拆分"
    Else
        outDirFull = OutputDir
    End If

    ' --- 编译章节识别正则：^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$ ---
    '   中文数字含"万"，支持 第一万章 / 第十万章 等大章节号
    Set reg = CreateObject("VBScript.RegExp")
    reg.Pattern = "^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$"
    reg.IgnoreCase = False
    reg.Global = False

    ' --- 读取UTF-8全文 ---
    t0 = Timer
    content = ReadTextAuto(InputPath)
    If Len(content) = 0 Then
        MsgBox "读取失败或文件为空：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If

    ' --- 统一行结束符并按行切分 ---
    content = Replace(content, vbCrLf, vbLf)
    content = Replace(content, vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    t1 = Timer - t0

    ' --- 预扫描章节起点 ---
    ReDim chStarts(0 To 127)
    ReDim chEnds(0 To 127)
    ReDim chTitles(0 To 127)
    chCount = 0

    For i = 0 To lineCount - 1
        If reg.Test(lines(i)) Then
            ' 收尾上一章（标记其结束行）
            If chCount > 0 Then chEnds(chCount - 1) = i - 1
            chStarts(chCount) = i
            chTitles(chCount) = ExtractTitle(reg, lines(i))
            chCount = chCount + 1
            ' 容量不足时扩容
            If chCount > UBound(chStarts) Then
                ReDim Preserve chStarts(0 To chCount + 127)
                ReDim Preserve chEnds(0 To chCount + 127)
                ReDim Preserve chTitles(0 To chCount + 127)
            End If
        End If
    Next i
    If chCount > 0 Then chEnds(chCount - 1) = lineCount - 1

    If chCount = 0 Then
        MsgBox "未识别到任何章节标题（第N章/第N回/第N节/第N卷）。" & vbCrLf & _
               "请确认文件格式。", vbExclamation, "提示"
        Exit Sub
    End If

    ' --- 序号位数自适应：章节数超过当前位数容量时自动扩展（防 10000+ 章排序错乱）---
    If Len(CStr(chCount)) > SerialWidth Then SerialWidth = Len(CStr(chCount))

    ' --- 生成预览并请求确认 ---
    serialFmt = String(SerialWidth, "0")
    prefix = FileNamePrefix
    preview = "【拆分预览】" & vbCrLf & _
              "源文件：" & InputPath & vbCrLf & _
              "总行数：" & lineCount & vbCrLf & _
              "总字符：" & Len(content) & vbCrLf & _
              "识别章节：" & chCount & " 章" & vbCrLf & _
              "读取耗时：" & Format(t1, "0.00") & " 秒" & vbCrLf & _
              "输出目录：" & outDirFull & vbCrLf & _
              "命名格式：" & serialFmt & " 标题.txt" & vbCrLf & vbCrLf & _
              "前5章预览：" & vbCrLf
    If chCount > 5 Then previewEnd = 4 Else previewEnd = chCount - 1
    For i = 0 To previewEnd
        preview = preview & "  " & Format(i + 1, serialFmt) & " " & chTitles(i) & vbCrLf
    Next i
    If chCount > 5 Then preview = preview & "  ...(共 " & chCount & " 章)" & vbCrLf
    preview = preview & vbCrLf & "确认开始生成 " & chCount & " 个文件？"
    ans = MsgBox(preview, vbYesCancel + vbQuestion, "确认拆分")
    If ans <> vbYes Then
        MsgBox "已取消，未生成任何文件。", vbInformation, "中止"
        Exit Sub
    End If

    ' --- 创建输出目录 + 清理旧文件 ---
    If Not fso.FolderExists(outDirFull) Then fso.CreateFolder outDirFull
    oldCount = 0
    oldFile = Dir(outDirFull & "\*.txt")
    Do While Len(oldFile) > 0
        Kill outDirFull & "\" & oldFile
        oldCount = oldCount + 1
        oldFile = Dir()
    Loop

    ' --- 写每章文件 ---
    t0 = Timer
    For i = 0 To chCount - 1
        serial = Format(i + 1, serialFmt)
        safeTitle = SanitizeFileName(chTitles(i))
        ' 命名规则(与Python统一): [<前缀>_]<序号> <标题>.txt
        ' 序号与标题间用半角空格; 标题内半角空格已转全角(见SanitizeFileName)
        If Len(prefix) > 0 Then
            fileName = prefix & "_" & serial & " " & safeTitle & ".txt"
        Else
            fileName = serial & " " & safeTitle & ".txt"
        End If
        outPath = outDirFull & "\" & fileName

        ' 切片：chStarts(i) ~ chEnds(i)，含章节标题行
        n = chEnds(i) - chStarts(i) + 1
        ReDim bodyLines(0 To n - 1)
        For j = 0 To n - 1
            bodyLines(j) = lines(chStarts(i) + j)
        Next j
        body = Join(bodyLines, vbCrLf)

        WriteTextUTF8NoBOM outPath, body
    Next i
    t1 = Timer - t0

    ' --- 完成报告 ---
    If t1 > 0 Then
        MsgBox "拆分完成！" & vbCrLf & _
               "生成文件：" & chCount & " 个" & vbCrLf & _
               "输出目录：" & outDirFull & vbCrLf & _
               "写入耗时：" & Format(t1, "0.00") & " 秒" & vbCrLf & _
               "处理速率：" & Format(chCount / t1, "0.0") & " 文件/秒", _
               vbInformation, "完成"
    Else
        MsgBox "拆分完成！生成文件：" & chCount & " 个" & vbCrLf & _
               "输出目录：" & outDirFull, vbInformation, "完成"
    End If
End Sub

'------------------------------------------------------------------------------
' 从章节标题行提取标题文本（正则第4捕获组）
'------------------------------------------------------------------------------
Private Function ExtractTitle(reg As Object, line As String) As String
    Dim m As Object
    Set m = reg.Execute(line)
    If m.Count = 0 Then
        ExtractTitle = line
        Exit Function
    End If
    ExtractTitle = Trim(m(0).SubMatches(3))
    ' 标题为空时退化为"第N章"形式
    If Len(ExtractTitle) = 0 Then
        ExtractTitle = "第" & m(0).SubMatches(0) & m(0).SubMatches(1)
    End If
End Function

'------------------------------------------------------------------------------
' 清洗文件名(与Python sanitize_title完全一致)：
' - 半角空格 -> 全角空格(对齐西游记章节风格)
' - 非法字符 \ / : * ? " < > | -> 全角空格; 折叠连续全角空格
' - 长度限制<=60，避免路径过长
'------------------------------------------------------------------------------
Private Function SanitizeFileName(name As String) As String
    ' 命名规则(与Python sanitize_title完全一致):
    ' - 半角空格 -> 全角空格(对齐西游记"灵根育孕源流出　心性修持大道生"风格)
    ' - 文件名非法字符 \ / : * ? " < > | -> 全角空格
    ' - 折叠连续全角空格; 长度限制60
    Dim s As String
    s = name
    ' 半角空格 -> 全角空格
    s = Replace(s, " ", "　")
    ' 文件名非法字符 -> 全角空格
    s = Replace(s, "\", "　")
    s = Replace(s, "/", "　")
    s = Replace(s, ":", "　")
    s = Replace(s, "*", "　")
    s = Replace(s, "?", "　")
    s = Replace(s, """", "　")
    s = Replace(s, "<", "　")
    s = Replace(s, ">", "　")
    s = Replace(s, "|", "　")
    ' 折叠连续全角空格
    Do While InStr(s, "　　") > 0
        s = Replace(s, "　　", "　")
    Loop
    s = Trim(s)
    If Len(s) = 0 Then s = "untitled"
    If Len(s) > 60 Then s = Left(s, 60)
    SanitizeFileName = s
End Function

'------------------------------------------------------------------------------
' 读写函数已移至 ReadTxtUniversal.bas 模块：
'   ReadTextAuto  - 自动检测编码读取（ANSI/UTF-8/UTF-16）
'   WriteTextUTF8NoBOM - 写入UTF-8无BOM
'------------------------------------------------------------------------------
