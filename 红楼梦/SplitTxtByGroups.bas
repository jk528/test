Attribute VB_Name = "SplitTxtByGroups"
Option Explicit

'==============================================================================
' 模块名称：SplitTxtByGroups
' 功能描述：按章节标题识别TXT，按聚合格式将多章合并为一份输出
' 聚合格式: 每份章数,份数|每份章数,份数|...  或便捷 N（每N章一份）
'   例: 40,3 -> 3份各40章； 20,1|20,1|80,1 -> 3份(1-20,21-40,41-120)
'   不足总章数时余数自动追加1个文件；突破9999章时序号位数自动扩展
' 输出格式: [前缀_]<序号补零>_第<起>-<止><单位>.txt（UTF-8无BOM）
'   - 命名规则与 split_by_groups.py 完全一致
'   - 序号位数自适应：文件数超当前位数容量时自动扩展（防 10000+ 章排序错乱）
'   - 正则中文数字含"万"，支持 第一万章 / 第十万章 等大章节号
' 工程约定：
'   - 所有Dim在过程顶部声明（WPS VBA严格性要求）
'   - 字符串拼接使用数组收集 + Join
'   - UTF-8读写使用 ADODB.Stream（VB内置I/O不支持UTF-8）
'   - 写入前预览分组清单并经用户确认，显示计时与吞吐量
'==============================================================================

' 章节识别正则（与 SplitTxtByChapter.bas / split_by_groups.py 一致，含"万"）
Private Const CHAPTER_PATTERN As String = "^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$"

'------------------------------------------------------------------------------
' 对外入口：选择TXT文件 → 输入聚合格式 → 生成文件
'   步骤1：弹出文件选择对话框，选中 .txt 文件
'   步骤2：弹出 InputBox，输入聚合格式（默认 40,3，支持 | 多段）
'   步骤3：预览确认后，清理输出目录旧文件并写入新文件
'   输出目录默认为 源文件所在目录\<文件名>_分组\
'------------------------------------------------------------------------------
Public Sub 聚合拆分()
    Dim fd As Object, filePath As String
    Dim chunkStr As String, prompt As String

    ' --- 步骤1：选择TXT文件 ---
    On Error Resume Next
    Set fd = Application.FileDialog(3)   ' msoFileDialogFilePicker = 3
    On Error GoTo 0

    If fd Is Nothing Then
        MsgBox "当前环境不支持文件选择对话框。", vbExclamation, "提示"
        Exit Sub
    End If

    fd.Title = "选择要聚合拆分的TXT文件"
    On Error Resume Next
    fd.Filters.Clear
    fd.Filters.Add "文本文件", "*.txt"
    fd.Filters.Add "所有文件", "*.*"
    On Error GoTo 0

    If fd.Show <> -1 Then Exit Sub
    filePath = fd.SelectedItems(1)

    ' --- 步骤2：输入聚合格式 ---
    prompt = "请输入聚合格式（每份章数,份数，以 | 分割多段）：" & vbCrLf & vbCrLf & _
             "示例：" & vbCrLf & _
             "  40,3              每份40章，共3份" & vbCrLf & _
             "  40                每40章一份（便捷模式）" & vbCrLf & _
             "  20,1|20,1|80,1    多段：1-20、21-40、41-120" & vbCrLf & vbCrLf & _
             "（余数自动补齐，如 40,2 实际得3份）"
    chunkStr = InputBox(prompt, "聚合拆分 - 输入格式", "40,3")

    If StrPtr(chunkStr) = 0 Then Exit Sub   ' 用户取消
    If Len(Trim(chunkStr)) = 0 Then
        MsgBox "未输入格式。", vbExclamation, "提示"
        Exit Sub
    End If

    ' --- 步骤3：调用核心过程 ---
    SplitTxtByGroups _
        InputPath:=filePath, _
        OutputDir:="", _
        ChunkStr:=chunkStr, _
        FileNamePrefix:="", _
        SerialWidth:=3
End Sub

'------------------------------------------------------------------------------
' 核心过程：通用聚合拆分（可供其他模块直接调用）
'   InputPath      源TXT完整路径
'   OutputDir      输出目录；空串 = 源目录下 <源文件名>_分组\
'   ChunkStr       聚合格式: 每份章数,份数|... 或便捷 N（默认 40,3）
'   FileNamePrefix 文件名前缀；空串 = 仅 序号_范围.txt
'   SerialWidth    序号位数；3 -> 001/002/...（文件数超容量时自动扩展）
'------------------------------------------------------------------------------
Public Sub SplitTxtByGroups(ByVal InputPath As String, _
    Optional ByVal OutputDir As String = "", _
    Optional ByVal ChunkStr As String = "40,3", _
    Optional ByVal FileNamePrefix As String = "", _
    Optional ByVal SerialWidth As Long = 3)

    Dim content As String, lines() As String, lineCount As Long
    Dim chStartLines() As Long, chCount As Long, unit As String
    Dim groupLens() As Long, groupSpaces() As Long, groupCount As Long
    Dim fileChStart() As Long, fileChEnd() As Long, fileCount As Long
    Dim serialFmt As String, prefix As String
    Dim outDirFull As String, segStr As String, errMsg As String
    Dim f As Long, g As Long, consumed As Long, remainder As Long
    Dim t0 As Double
    Dim fso As Object, preview As String, showN As Long, rangeStr As String
    Dim serial As String, safe As String, fname As String
    Dim startLine As Long, endLine As Long, segCount As Long
    Dim parts() As String, li As Long, body As String
    Dim oldFile As String, oldCount As Long

    ' --- 1. 读取源文件 ---
    If Dir(InputPath) = "" Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    content = ReadTextUTF8(InputPath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1

    ' --- 2. 识别章节 ---
    ScanChapters lines, lineCount, chStartLines, chCount, unit
    If chCount = 0 Then
        MsgBox "未识别到任何章节标题（第N章/第N回/第N节/第N卷）。" & vbCrLf & _
               "请确认文件格式。", vbExclamation, "提示"
        Exit Sub
    End If

    ' --- 3. 解析聚合格式 ---
    errMsg = ParseGroups(ChunkStr, chCount, groupLens, groupSpaces, groupCount)
    If Len(errMsg) > 0 Then
        MsgBox "聚合格式错误：" & vbCrLf & errMsg, vbExclamation, "错误"
        Exit Sub
    End If

    ' 计算累计消耗与余数
    consumed = 0
    For g = 0 To groupCount - 1
        consumed = consumed + groupLens(g) * groupSpaces(g)
    Next g
    remainder = chCount - consumed

    ' 生成解析段字符串（如 "40,3" 或 "20,1|20,1|80,1"）
    segStr = ""
    For g = 0 To groupCount - 1
        If g > 0 Then segStr = segStr & " | "
        segStr = segStr & groupSpaces(g) & "," & groupLens(g)
    Next g

    ' --- 4. 展开为文件列表 ---
    ExpandGroups groupLens, groupSpaces, groupCount, chCount, _
                 fileChStart, fileChEnd, fileCount

    ' --- 5. 序号位数自适应 ---
    If Len(CStr(fileCount)) > SerialWidth Then SerialWidth = Len(CStr(fileCount))
    serialFmt = String(SerialWidth, "0")
    prefix = FileNamePrefix

    ' --- 6. 确定输出目录 ---
    If Len(OutputDir) = 0 Then
        Set fso = CreateObject("Scripting.FileSystemObject")
        outDirFull = fso.GetParentFolderName(InputPath) & "\" & _
                     fso.GetBaseName(InputPath) & "_分组"
    Else
        outDirFull = OutputDir
    End If
    If Dir(outDirFull, vbDirectory) = "" Then
        MkDir outDirFull
    End If

    ' --- 7. 生成预览并请求确认 ---
    preview = "【聚合拆分预览】" & vbCrLf & _
              "源文件：" & InputPath & vbCrLf & _
              "总行数：" & lineCount & vbCrLf & _
              "识别章节：" & chCount & "  单位：" & unit & vbCrLf & _
              "聚合格式：" & ChunkStr & vbCrLf & _
              "解析段：" & segStr & vbCrLf
    If remainder > 0 Then
        preview = preview & "[提示] 余数 " & remainder & " 章自动追加为1个文件" & vbCrLf
    End If
    preview = preview & "将生成 " & fileCount & " 个文件：" & vbCrLf
    showN = fileCount
    If showN > 12 Then showN = 12
    For f = 0 To showN - 1
        If fileChStart(f) = fileChEnd(f) Then
            rangeStr = "第" & fileChStart(f) & unit
        Else
            rangeStr = "第" & fileChStart(f) & "-" & fileChEnd(f) & unit
        End If
        preview = preview & "  " & Format(f + 1, serialFmt) & "  " & rangeStr & vbCrLf
    Next f
    If fileCount > 12 Then
        preview = preview & "  ...（其余 " & (fileCount - 12) & " 份省略）" & vbCrLf
    End If
    preview = preview & vbCrLf & "输出目录：" & outDirFull & vbCrLf & vbCrLf & _
              "确认开始拆分？"
    If MsgBox(preview, vbOKCancel + vbQuestion, "聚合拆分预览") <> vbOK Then
        MsgBox "已取消。", vbInformation, "提示"
        Exit Sub
    End If

    ' --- 8. 清理输出目录旧文件 + 写每份文件 ---
    ' 清理旧文件（防止多次运行不同格式时残留文件混入，如两个 003 文件）
    oldCount = 0
    oldFile = Dir(outDirFull & "\*.txt")
    Do While Len(oldFile) > 0
        Kill outDirFull & "\" & oldFile
        oldCount = oldCount + 1
        oldFile = Dir()
    Loop
    t0 = Timer
    For f = 0 To fileCount - 1
        ' 章号 1-based -> 行号 0-based：第n章首行 = chStartLines(n-1)
        startLine = chStartLines(fileChStart(f) - 1)
        If fileChEnd(f) < chCount Then
            endLine = chStartLines(fileChEnd(f)) - 1   ' 下一章首行 - 1
        Else
            endLine = lineCount - 1                    ' 最后一行
        End If

        ' 拼接正文章节
        segCount = endLine - startLine
        ReDim parts(0 To segCount)
        For li = 0 To segCount
            parts(li) = lines(startLine + li)
        Next li
        body = Join(parts, vbLf)

        ' 生成文件名
        If fileChStart(f) = fileChEnd(f) Then
            rangeStr = "第" & fileChStart(f) & unit
        Else
            rangeStr = "第" & fileChStart(f) & "-" & fileChEnd(f) & unit
        End If
        safe = SanitizeFileName(rangeStr)
        serial = Format(f + 1, serialFmt)
        fname = serial & "_" & safe & ".txt"
        If Len(prefix) > 0 Then fname = prefix & "_" & fname

        WriteTextUTF8 outDirFull & "\" & fname, body
    Next f

    ' --- 9. 完成提示 ---
    MsgBox "聚合拆分完成！" & vbCrLf & _
           "生成文件：" & fileCount & " 个" & vbCrLf & _
           "耗时：" & Format(Timer - t0, "0.00") & " 秒" & vbCrLf & _
           "输出目录：" & outDirFull, vbInformation, "完成"
End Sub

'==============================================================================
' 内部函数
'==============================================================================

'------------------------------------------------------------------------------
' 扫描章节起点行
'   lines()       全文行数组（0-based）
'   lineCount     行数
'   chStartLines  输出：每章首行号（0-based，动态扩容）
'   chCount       输出：章节数
'   unit          输出：单位词（取首个匹配，章/回/节/卷）
'------------------------------------------------------------------------------
Private Sub ScanChapters(lines() As String, ByVal lineCount As Long, _
        ByRef chStartLines() As Long, ByRef chCount As Long, ByRef unit As String)
    Dim reg As Object, i As Long, m As Object
    ReDim chStartLines(0 To 127)
    chCount = 0
    unit = "回"

    Set reg = CreateObject("VBScript.RegExp")
    reg.Pattern = CHAPTER_PATTERN
    reg.IgnoreCase = False
    reg.Global = False

    For i = 0 To lineCount - 1
        If reg.Test(lines(i)) Then
            chStartLines(chCount) = i
            If chCount = 0 Then
                Set m = reg.Execute(lines(i))
                unit = m(0).SubMatches(1)
            End If
            chCount = chCount + 1
            If chCount > UBound(chStartLines) Then
                ReDim Preserve chStartLines(0 To chCount + 127)
            End If
        End If
    Next i
End Sub

'------------------------------------------------------------------------------
' 解析聚合格式字符串
'   格式:
'     N            便捷模式: 每N章一份, 份数=ceil(total/N), 末份可能不足
'     a,b          单段: 每份a章, 共b份
'     a,b|c,d|...  多段: 各段顺序聚合, 不足自动补余数段
'   返回: 空串=成功, 非空=错误信息
'   输出: groupLens()/groupSpaces() 并行数组, groupCount
'------------------------------------------------------------------------------
Private Function ParseGroups(ByVal chunkStr As String, ByVal total As Long, _
        ByRef groupLens() As Long, ByRef groupSpaces() As Long, _
        ByRef groupCount As Long) As String
    Dim s As String, parts() As String, p As Long, part As String
    Dim detail() As String, length As Long, spacing As Long
    Dim consumed As Long, n As Long, cnt As Long

    s = Trim(chunkStr)
    If Len(s) = 0 Then
        ParseGroups = "聚合字符串为空"
        Exit Function
    End If

    ReDim groupLens(0 To 31)
    ReDim groupSpaces(0 To 31)
    groupCount = 0
    consumed = 0

    ' 便捷模式：纯数字（无逗号无竖线）-> 每N章一份
    If InStr(s, ",") = 0 And InStr(s, "|") = 0 Then
        If Not IsDigits(s) Then
            ParseGroups = "便捷模式需为正整数: " & s
            Exit Function
        End If
        n = CLng(s)
        If n <= 0 Then
            ParseGroups = "每份章数必须为正数: " & s
            Exit Function
        End If
        cnt = total \ n
        If total Mod n > 0 Then cnt = cnt + 1   ' ceil(total/n)
        groupLens(0) = cnt
        groupSpaces(0) = n
        groupCount = 1
        ParseGroups = ""
        Exit Function
    End If

    ' 多段格式：每份章数,份数|每份章数,份数|...
    parts = Split(s, "|")
    For p = 0 To UBound(parts)
        part = Trim(parts(p))
        If Len(part) = 0 Then GoTo NextPart

        detail = Split(part, ",")
        If UBound(detail) <> 1 Then
            ParseGroups = "段格式错误: " & part & "（应为 每份章数,份数）"
            Exit Function
        End If
        If Not IsDigits(Trim(detail(0))) Or Not IsDigits(Trim(detail(1))) Then
            ParseGroups = "每份章数和份数需为正整数: " & part
            Exit Function
        End If
        ' 用户输入 detail(0)=每份章数, detail(1)=份数；内部存 length=份数, spacing=每份章数
        spacing = CLng(Trim(detail(0)))
        length = CLng(Trim(detail(1)))
        If length <= 0 Or spacing <= 0 Then
            ParseGroups = "每份章数和份数必须为正数: " & part
            Exit Function
        End If

        groupLens(groupCount) = length
        groupSpaces(groupCount) = spacing
        groupCount = groupCount + 1
        If groupCount > UBound(groupLens) Then
            ReDim Preserve groupLens(0 To groupCount + 31)
            ReDim Preserve groupSpaces(0 To groupCount + 31)
        End If
        consumed = consumed + length * spacing
NextPart:
    Next p

    If consumed > total Then
        ParseGroups = "消耗章节数 " & consumed & " 超过总章节数 " & total
        Exit Function
    End If
    If consumed < total Then
        ' 余数自动补齐
        groupLens(groupCount) = 1
        groupSpaces(groupCount) = total - consumed
        groupCount = groupCount + 1
    End If
    ParseGroups = ""
End Function

'------------------------------------------------------------------------------
' 判断字符串是否全为半角数字（0-9）
'------------------------------------------------------------------------------
Private Function IsDigits(ByVal s As String) As Boolean
    Dim i As Long, c As String
    If Len(s) = 0 Then Exit Function
    For i = 1 To Len(s)
        c = Mid(s, i, 1)
        If c < "0" Or c > "9" Then Exit Function
    Next i
    IsDigits = True
End Function

'------------------------------------------------------------------------------
' 展开聚合组为文件列表
'   groupLens/groupSpaces  聚合段数组
'   groupCount             段数
'   total                  总章节数
'   fileChStart/fileChEnd  输出：每份起止章号（1-based，动态扩容）
'   fileCount              输出：文件数
'------------------------------------------------------------------------------
Private Sub ExpandGroups(groupLens() As Long, groupSpaces() As Long, _
        ByVal groupCount As Long, ByVal total As Long, _
        ByRef fileChStart() As Long, ByRef fileChEnd() As Long, _
        ByRef fileCount As Long)
    Dim g As Long, k As Long, ch As Long
    ReDim fileChStart(0 To 31)
    ReDim fileChEnd(0 To 31)
    fileCount = 0
    ch = 0

    For g = 0 To groupCount - 1
        For k = 1 To groupLens(g)
            If ch >= total Then Exit For
            fileChStart(fileCount) = ch + 1
            If ch + groupSpaces(g) < total Then
                fileChEnd(fileCount) = ch + groupSpaces(g)
            Else
                fileChEnd(fileCount) = total
            End If
            ch = fileChEnd(fileCount)
            fileCount = fileCount + 1
            If fileCount > UBound(fileChStart) Then
                ReDim Preserve fileChStart(0 To fileCount + 31)
                ReDim Preserve fileChEnd(0 To fileCount + 31)
            End If
        Next k
        If ch >= total Then Exit For
    Next g
End Sub

'------------------------------------------------------------------------------
' 清洗文件名（与 split_by_groups.py SanitizeFileName 一致）
'   - 非法字符 \ / : * ? " < > | -> 全角空格
'   - 折叠连续全角空格；长度限制 60
'------------------------------------------------------------------------------
Private Function SanitizeFileName(ByVal name As String) As String
    Dim s As String
    s = name
    s = Replace(s, "\", "　")
    s = Replace(s, "/", "　")
    s = Replace(s, ":", "　")
    s = Replace(s, "*", "　")
    s = Replace(s, "?", "　")
    s = Replace(s, """", "　")
    s = Replace(s, "<", "　")
    s = Replace(s, ">", "　")
    s = Replace(s, "|", "　")
    Do While InStr(s, "　　") > 0
        s = Replace(s, "　　", "　")
    Loop
    s = Trim(s)
    If Len(s) = 0 Then s = "untitled"
    If Len(s) > 60 Then s = Left(s, 60)
    SanitizeFileName = s
End Function

'------------------------------------------------------------------------------
' 读取UTF-8文本（自动识别BOM；ADODB.Stream能正确处理有无BOM两种情况）
'------------------------------------------------------------------------------
Private Function ReadTextUTF8(ByVal path As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile path
    ReadTextUTF8 = stm.ReadText(-1)   ' adReadAll
    stm.Close
End Function

'------------------------------------------------------------------------------
' 写入UTF-8文本（无BOM）
'   ADODB.Stream 默认会写出3字节BOM，需先以文本模式写入再用二进制模式裁掉BOM
'------------------------------------------------------------------------------
Private Sub WriteTextUTF8(ByVal path As String, ByVal text As String)
    Dim stm As Object, bin As Variant

    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText text

    ' 切到二进制模式以剥离BOM
    stm.Position = 0
    stm.Type = 1          ' adTypeBinary
    stm.Position = 3      ' 跳过 UTF-8 BOM (EF BB BF)
    bin = stm.Read
    stm.Close

    ' 用一个干净的二进制流写出文件
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 1          ' adTypeBinary
    stm.Open
    stm.Write bin
    stm.SaveToFile path, 2    ' adSaveCreateOverWrite
    stm.Close
End Sub
