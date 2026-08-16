Option Explicit

'==============================================================================
' TXT章节拆分工具（完整合并版）
'   - 按章节一一拆分：每章一个文件
'   - 聚合拆分：按聚合格式将多章合并为一份
'   - 通用编码检测与读写：ANSI / UTF-8(含/无BOM) / UTF-16LE / UTF-16BE
'   复制粘贴到 VBA 编辑器（WPS/Excel/Word）即可运行，无需导入其他模块
'
' 入口：运行 拆分TXT（选择文件 → 选择模式 → 生成文件）
'
' 聚合格式: 每份章数,份数|每份章数,份数|...  或便捷 N（每N章一份）
'   例: 40,3 -> 3份各40章； 20,1|20,1|80,1 -> 3份(1-20,21-40,41-120)
'   不足总章数时余数自动追加1个文件；突破9999章时序号位数自动扩展
' 输出格式: [前缀_]<序号补零>_<标题或范围>.txt（UTF-8无BOM）
'   - 每章拆分: 序号 标题.txt（标题内半角空格转全角）
'   - 聚合拆分: 序号_第起-止单位.txt
'   - 序号位数自适应：文件数超当前位数容量时自动扩展
'   - 正则中文数字含"万"，支持 第一万章 / 第十万章 等大章节号
' 工程约定：
'   - 所有Dim在过程顶部声明（WPS VBA严格性要求）
'   - 字符串拼接使用数组收集 + Join
'   - 聚合拆分写入前预览确认；完成后显示计时与吞吐量
'   - 行结束符统一使用 vbLf（与内容归一化一致）
'   - CleanOutputDir 使用 fso 遍历删除，避免 Dir+Kill 循环Bug
'   - ADODB.Stream 用后显式 Set Nothing 释放 COM 对象
'   - 写入循环包裹 On Error，出错时报告具体文件名
'==============================================================================

' 章节识别正则（含"万"，支持大章节号）
Private Const CHAPTER_PATTERN As String = "^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$"

' 全局计时变量（由 拆分TXT 入口设置，ShowCompleteReport 读取）
Private g_tSelect As Double    ' 文件选择耗时（秒）
Private g_tTotal0 As Double    ' 整个过程起始时间戳
Private g_detectedEnc As String  ' 检测到的源文件编码


'==============================================================================
' 第一部分：通用TXT编码检测与读写
'==============================================================================

'------------------------------------------------------------------------------
' 自动检测编码并读取TXT文件内容
'   filePath  源TXT完整路径
'   返回      文件全文文本（失败返回空串）
'------------------------------------------------------------------------------
Public Function ReadTextAuto(ByVal filePath As String) As String
    Dim enc As String
    enc = DetectEncodingFile(filePath)
    Select Case enc
        Case "ANSI"
            ReadTextAuto = ReadTextANSI(filePath)
        Case "UTF-8 BOM", "UTF-8"
            ReadTextAuto = ReadTextUTF8(filePath)
        Case "UTF-16LE", "UTF-16BE"
            ReadTextAuto = ReadTextUTF16(filePath)
        Case Else
            ' 未知编码，尝试UTF-8兜底
            ReadTextAuto = ReadTextUTF8(filePath)
    End Select
End Function

'------------------------------------------------------------------------------
' 检测TXT文件编码（传入文件路径）
'   返回 "ANSI" / "UTF-8 BOM" / "UTF-8" / "UTF-16LE" / "UTF-16BE"
'------------------------------------------------------------------------------
Public Function DetectEncodingFile(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    DetectEncodingFile = DetectEncodingBytes(fileBytes)
End Function

'------------------------------------------------------------------------------
' 检测编码（传入字节数组）
'   1. BOM 检测：FF FE = UTF-16LE; FE FF = UTF-16BE; EF BB BF = UTF-8 BOM
'   2. 无BOM时扫描前100字节，检查高位字节模式判断 UTF-8 vs ANSI
'   3. 全ASCII（无高位字节）→ ANSI
'------------------------------------------------------------------------------
Public Function DetectEncodingBytes(fileBytes() As Byte) As String
    Dim i As Long, scanLen As Long, b1 As Byte

    If UBound(fileBytes) < 0 Then
        DetectEncodingBytes = "ANSI"
        Exit Function
    End If

    ' --- BOM 检测 ---
    If UBound(fileBytes) >= 1 Then
        If fileBytes(0) = &HFF And fileBytes(1) = &HFE Then
            DetectEncodingBytes = "UTF-16LE"
            Exit Function
        End If
        If fileBytes(0) = &HFE And fileBytes(1) = &HFF Then
            DetectEncodingBytes = "UTF-16BE"
            Exit Function
        End If
    End If
    If UBound(fileBytes) >= 2 Then
        If fileBytes(0) = &HEF And fileBytes(1) = &HBB And fileBytes(2) = &HBF Then
            DetectEncodingBytes = "UTF-8 BOM"
            Exit Function
        End If
    End If

    ' --- 无BOM：扫描字节模式判断 UTF-8 vs ANSI ---
    scanLen = UBound(fileBytes)
    If scanLen > 100 Then scanLen = 100

    For i = 0 To scanLen
        If fileBytes(i) > &H7F Then
            b1 = fileBytes(i)
            Select Case True
                ' 3字节UTF-8序列: E0~EF + 80~BF + 80~BF
                Case (b1 And &HF0) = &HE0
                    If i + 2 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                ' 4字节UTF-8序列: F0~F7 + 80~BF + 80~BF + 80~BF
                Case (b1 And &HF8) = &HF0
                    If i + 3 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 And _
                           (fileBytes(i + 3) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                ' 2字节UTF-8序列: C0~DF + 80~BF
                Case (b1 And &HE0) = &HC0
                    If i + 1 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                Case Else
                    ' 高位字节不符合UTF-8前导字节模式 → ANSI
                    DetectEncodingBytes = "ANSI"
                    Exit Function
            End Select
        End If
    Next i

    ' 全ASCII（无高位字节）→ 视为ANSI（纯英文文件两者兼容）
    DetectEncodingBytes = "ANSI"
End Function

'------------------------------------------------------------------------------
' 读取文件原始字节数组
'------------------------------------------------------------------------------
Public Function ReadFileBytes(ByVal filePath As String) As Byte()
    Dim fileNo As Integer
    Dim fileBytes() As Byte
    fileNo = FreeFile
    Open filePath For Binary Access Read As #fileNo
    ReDim fileBytes(0 To LOF(fileNo) - 1)
    Get #fileNo, , fileBytes
    Close #fileNo
    ReadFileBytes = fileBytes
End Function

'------------------------------------------------------------------------------
' 读取ANSI编码TXT（系统默认编码，中文Windows=GBK）
'   注意：不能用 Open...For Input + Input()，因为文本模式会将 0x1A(Ctrl+Z)
'   解释为文件尾，导致 Error 62(输入超出文件尾)。改用 Binary 模式读取原始字节，
'   再用 StrConv 按 ANSI→Unicode 转换。
'------------------------------------------------------------------------------
Public Function ReadTextANSI(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    If UBound(fileBytes) < 0 Then Exit Function
    ReadTextANSI = StrConv(fileBytes, vbUnicode)
End Function

'------------------------------------------------------------------------------
' 读取UTF-8编码TXT（ADODB.Stream，自动处理有无BOM）
'------------------------------------------------------------------------------
Public Function ReadTextUTF8(ByVal filePath As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile filePath
    ReadTextUTF8 = stm.ReadText(-1)   ' adReadAll
    stm.Close
    Set stm = Nothing
End Function

'------------------------------------------------------------------------------
' 读取UTF-16编码TXT（FileSystemObject TristateTrue，自动处理LE/BE+BOM）
'------------------------------------------------------------------------------
Public Function ReadTextUTF16(ByVal filePath As String) As String
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(filePath, 1, False, -1)  ' -1 = TristateTrue(Unicode)
    ReadTextUTF16 = ts.ReadAll
    ts.Close
    Set ts = Nothing
    Set fso = Nothing
End Function

'------------------------------------------------------------------------------
' 写入UTF-8文本（无BOM）
'   ADODB.Stream 默认写3字节BOM，需切二进制模式裁掉
'------------------------------------------------------------------------------
Public Sub WriteTextUTF8NoBOM(ByVal filePath As String, ByVal text As String)
    Dim stm As Object, bin As Variant
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText text
    ' 切二进制模式剥离BOM
    stm.Position = 0
    stm.Type = 1          ' adTypeBinary
    stm.Position = 3      ' 跳过 UTF-8 BOM (EF BB BF)
    bin = stm.Read
    stm.Close
    Set stm = Nothing
    ' 干净二进制流写出
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 1          ' adTypeBinary
    stm.Open
    stm.Write bin
    stm.SaveToFile filePath, 2    ' adSaveCreateOverWrite
    stm.Close
    Set stm = Nothing
End Sub


'==============================================================================
' 第二部分：章节拆分核心逻辑
'==============================================================================

'==============================================================================
' 对外入口：选择TXT文件 → 选择拆分模式 → 生成文件
'==============================================================================
Public Sub 拆分TXT()
    Dim filePath As String
    Dim tSel0 As Double

    ' --- 初始化计时 ---
    g_tTotal0 = Timer
    g_tSelect = 0

    ' --- 步骤1：选择TXT文件 ---
    tSel0 = Timer
    filePath = SelectTxtFile("选择要拆分的TXT文件")
    g_tSelect = Timer - tSel0
    If Len(filePath) = 0 Then Exit Sub

    ' --- 步骤2：选择拆分模式 ---
    Dim mode As VbMsgBoxResult
    mode = MsgBox("请选择拆分模式：" & vbCrLf & vbCrLf & _
                  "  [是]  按章节一一拆分（每章一个文件）" & vbCrLf & _
                  "  [否]  聚合拆分（多章合并为一份）" & vbCrLf & _
                  "  [取消] 退出", _
                  vbYesNoCancel + vbQuestion, "选择拆分模式")

    If mode = vbCancel Then Exit Sub

    If mode = vbYes Then
        ' --- 按章节一一拆分 ---
        Dim contentMode As VbMsgBoxResult
        contentMode = MsgBox("选择章节内容处理方式：" & vbCrLf & vbCrLf & _
                            "  [是] 生成所有章节（含仅有标题/正文不足）" & vbCrLf & _
                            "  [否] 跳过仅有标题的章节（默认）" & vbCrLf & _
                            "  [取消] 自定义最小正文字数", _
                            vbYesNoCancel + vbQuestion + vbDefaultButton2, "章节内容处理")

        If contentMode = vbCancel Then
            Dim minBodyInput As String
            minBodyInput = InputBox("请输入最小正文字数：" & vbCrLf & _
                                   "正文少于指定字数的章节将被跳过（含仅有标题的章节）", _
                                   "自定义最小正文字数", "50")
            If StrPtr(minBodyInput) = 0 Then Exit Sub
            If Len(Trim(minBodyInput)) = 0 Or Not IsDigits(Trim(minBodyInput)) Then
                MsgBox "输入无效，请输入正整数。", vbExclamation, "提示"
                Exit Sub
            End If
            SplitByChapter InputPath:=filePath, GenerateTitleOnly:=False, _
                          MinBodyLen:=CLng(Trim(minBodyInput))
        ElseIf contentMode = vbYes Then
            SplitByChapter InputPath:=filePath, GenerateTitleOnly:=True
        Else
            SplitByChapter InputPath:=filePath, GenerateTitleOnly:=False
        End If
    Else
        ' --- 聚合拆分：输入格式 ---
        Dim chunkStr As String, prompt As String
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

        SplitByGroups InputPath:=filePath, ChunkStr:=chunkStr
    End If
End Sub

'==============================================================================
' 核心过程 1：按章节一一拆分
'   InputPath       源TXT完整路径
'   OutputDir       输出目录；空串 = 源目录下 <源文件名>_拆分\
'   FileNamePrefix  文件名前缀；空串 = 仅 序号 标题.txt
'   SerialWidth     序号位数；3 -> 001, 002, ...（文件数超容量时自动扩展）
'   GenerateTitleOnly  False=跳过仅有标题/正文不足的章节(默认), True=生成
'   MinBodyLen       最小正文字数(0=不检测)，正文少于该值的章节也跳过
'==============================================================================
Public Sub SplitByChapter(ByVal InputPath As String, _
                          Optional ByVal OutputDir As String = "", _
                          Optional ByVal FileNamePrefix As String = "", _
                          Optional ByVal SerialWidth As Long = 3, _
                          Optional ByVal GenerateTitleOnly As Boolean = False, _
                          Optional ByVal MinBodyLen As Long = 0)
    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim chCount As Long, unit As String
    Dim chStarts() As Long, chEnds() As Long, chTitles() As String
    Dim serialFmt As String, prefix As String
    Dim outDirFull As String
    Dim i As Long, n As Long, j As Long
    Dim bodyLines() As String, body As String
    Dim safeTitle As String, fileName As String, outPath As String, serial As String
    Dim t0 As Double, t1 As Double, tRead0 As Double, tRead1 As Double
    Dim tScan0 As Double, tScan1 As Double

    If g_tTotal0 = 0 Then g_tTotal0 = Timer    ' 直接调用时设置总起点

    ' --- 1. 读取源文件 ---
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(InputPath) Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    tRead0 = Timer
    g_detectedEnc = DetectEncodingFile(InputPath)
    content = ReadTextAuto(InputPath)
    If Len(content) = 0 Then
        MsgBox "读取失败或文件为空：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead1 = Timer - tRead0

    ' --- 2. 识别章节 ---
    tScan0 = Timer
    ScanChapters lines, lineCount, chStarts, chEnds, chTitles, chCount, unit
    tScan1 = Timer - tScan0
    If chCount = 0 Then
        MsgBox "未识别到任何章节标题（第N章/第N回/第N节/第N卷）。" & vbCrLf & _
               "请确认文件格式。", vbExclamation, "提示"
        Exit Sub
    End If

    ' --- 3. 序号位数自适应 ---
    If Len(CStr(chCount)) > SerialWidth Then SerialWidth = Len(CStr(chCount))
    serialFmt = String(SerialWidth, "0")
    prefix = FileNamePrefix

    ' --- 4. 确定输出目录 ---
    outDirFull = ResolveOutputDir(fso, InputPath, OutputDir, "_拆分")

    ' --- 5. 创建输出目录 + 清理旧文件 ---
    If Dir(outDirFull, vbDirectory) = "" Then MkDir outDirFull
    CleanOutputDir outDirFull

    ' --- 6. 写每章文件 ---
    Dim titleOnlyCount As Long, writtenCount As Long, skippedCount As Long
    Dim shortBodyCount As Long, bodyLen As Long, isInsufficient As Boolean
    Dim skipDetail As String, bodyText As String, regCn As Object
    titleOnlyCount = 0
    writtenCount = 0
    skippedCount = 0
    shortBodyCount = 0
    Set regCn = CreateObject("VBScript.RegExp")
    regCn.Global = True
    regCn.Pattern = "[" & ChrW(&H4E00) & "-" & ChrW(&H9FFF) & "]"
    t0 = Timer
    On Error GoTo WriteErr
    For i = 0 To chCount - 1
        n = chEnds(i) - chStarts(i) + 1
        If n < 1 Then n = 1    ' 安全保护：chEnds < chStarts 时仅写标题行

        ' 计算正文汉字数（不含标题行，仅统计汉字）
        If n > 1 Then
            ReDim bodyLines(0 To n - 2)
            For j = 0 To n - 2
                bodyLines(j) = lines(chStarts(i) + 1 + j)
            Next j
            bodyText = Join(bodyLines, "")
            bodyLen = regCn.Execute(bodyText).Count
        Else
            bodyLen = 0
        End If

        ' 判断是否为不足章节
        isInsufficient = False
        If n = 1 Then
            titleOnlyCount = titleOnlyCount + 1
            isInsufficient = True
        ElseIf MinBodyLen > 0 And bodyLen < MinBodyLen Then
            shortBodyCount = shortBodyCount + 1
            isInsufficient = True
        End If

        If isInsufficient And Not GenerateTitleOnly Then
            skippedCount = skippedCount + 1
            GoTo NextChapter
        End If

        serial = Format(writtenCount + 1, serialFmt)
        safeTitle = SanitizeFileName(chTitles(i))
        If Len(prefix) > 0 Then
            fileName = prefix & "_" & serial & "_" & safeTitle & ".txt"
        Else
            fileName = serial & "_" & safeTitle & ".txt"
        End If
        outPath = outDirFull & "\" & fileName

        ReDim bodyLines(0 To n - 1)
        For j = 0 To n - 1
            bodyLines(j) = lines(chStarts(i) + j)
        Next j
        body = Join(bodyLines, vbLf)

        WriteTextUTF8NoBOM outPath, body

        If writtenCount < 3 Or i >= chCount - 2 Then
            If n = 1 Then
                Debug.Print "  [" & serial & "] " & fileName & "  (仅标题)"
            ElseIf MinBodyLen > 0 And bodyLen < MinBodyLen Then
                Debug.Print "  [" & serial & "] " & fileName & "  (" & n & "行,正文" & bodyLen & "字)"
            Else
                Debug.Print "  [" & serial & "] " & fileName & "  (" & n & "行)"
            End If
        ElseIf writtenCount = 3 Then
            Debug.Print "  ..."
        End If

        writtenCount = writtenCount + 1
NextChapter:
    Next i
    On Error GoTo 0
    Set regCn = Nothing
    t1 = Timer - t0

    ' --- 7. 完成报告 ---
    ShowCompleteReport "按章节拆分完成", writtenCount, outDirFull, tRead1, tScan1, t1
    If skippedCount > 0 Then
        skipDetail = ""
        If titleOnlyCount > 0 Then skipDetail = titleOnlyCount & "个仅有标题"
        If shortBodyCount > 0 Then
            If Len(skipDetail) > 0 Then skipDetail = skipDetail & "、"
            skipDetail = skipDetail & shortBodyCount & "个正文不足"
        End If
        Debug.Print "[提示] 跳过 " & skippedCount & " 个章节（" & skipDetail & "）"
    ElseIf titleOnlyCount > 0 Or shortBodyCount > 0 Then
        skipDetail = ""
        If titleOnlyCount > 0 Then skipDetail = titleOnlyCount & "个仅有标题"
        If shortBodyCount > 0 Then
            If Len(skipDetail) > 0 Then skipDetail = skipDetail & "、"
            skipDetail = skipDetail & shortBodyCount & "个正文不足"
        End If
        Debug.Print "[提示] " & skipDetail & "（已生成）"
    End If
    Exit Sub
WriteErr:
    MsgBox "写入第 " & (i + 1) & " 个文件时出错：" & vbCrLf & _
           outPath & vbCrLf & _
           "错误：" & Err.Description, vbExclamation, "写入错误"
End Sub

'==============================================================================
' 核心过程 2：聚合拆分
'   InputPath       源TXT完整路径
'   OutputDir       输出目录；空串 = 源目录下 <源文件名>_分组\
'   ChunkStr        聚合格式: 每份章数,份数|... 或便捷 N（默认 40,3）
'   FileNamePrefix  文件名前缀；空串 = 仅 序号_范围.txt
'   SerialWidth     序号位数；3 -> 001/002/...（文件数超容量时自动扩展）
'==============================================================================
Public Sub SplitByGroups(ByVal InputPath As String, _
    Optional ByVal OutputDir As String = "", _
    Optional ByVal ChunkStr As String = "40,3", _
    Optional ByVal FileNamePrefix As String = "", _
    Optional ByVal SerialWidth As Long = 3)

    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim chStartLines() As Long, chCount As Long, unit As String
    Dim chEnds() As Long, chTitles() As String
    Dim groupLens() As Long, groupSpaces() As Long, groupCount As Long
    Dim fileChStart() As Long, fileChEnd() As Long, fileCount As Long
    Dim serialFmt As String, prefix As String
    Dim outDirFull As String, segStr As String, errMsg As String
    Dim f As Long, g As Long, consumed As Long, remainder As Long
    Dim t0 As Double, tRead0 As Double, tRead1 As Double
    Dim tScan0 As Double, tScan1 As Double
    Dim preview As String, showN As Long, rangeStr As String
    Dim serial As String, safe As String, fname As String
    Dim startLine As Long, endLine As Long, segCount As Long
    Dim parts() As String, li As Long, body As String

    If g_tTotal0 = 0 Then g_tTotal0 = Timer    ' 直接调用时设置总起点

    ' --- 1. 读取源文件 ---
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(InputPath) Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    tRead0 = Timer
    g_detectedEnc = DetectEncodingFile(InputPath)
    content = ReadTextAuto(InputPath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead1 = Timer - tRead0

    ' --- 2. 识别章节 ---
    tScan0 = Timer
    ScanChapters lines, lineCount, chStartLines, chEnds, chTitles, chCount, unit
    tScan1 = Timer - tScan0
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

    consumed = 0
    For g = 0 To groupCount - 1
        consumed = consumed + groupLens(g) * groupSpaces(g)
    Next g
    remainder = chCount - consumed

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
    outDirFull = ResolveOutputDir(fso, InputPath, OutputDir, "_分组")

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
        rangeStr = FormatRange(fileChStart(f), fileChEnd(f), unit)
        preview = preview & "  " & Format(f + 1, serialFmt) & "  " & rangeStr & vbCrLf
    Next f
    If fileCount > 12 Then
        preview = preview & "  ...（其余 " & (fileCount - 12) & " 份省略）" & vbCrLf
    End If
    preview = preview & vbCrLf & "输出目录：" & outDirFull & vbCrLf & vbCrLf & _
              "确认开始拆分？"
    If MsgBox(preview, vbOKCancel + vbQuestion, "聚合拆分预览") <> vbOK Then Exit Sub

    ' --- 8. 创建输出目录 + 清理旧文件 ---
    If Dir(outDirFull, vbDirectory) = "" Then MkDir outDirFull
    CleanOutputDir outDirFull

    ' --- 9. 写每份文件 ---
    t0 = Timer
    On Error GoTo GroupWriteErr
    For f = 0 To fileCount - 1
        startLine = chStartLines(fileChStart(f) - 1)
        If fileChEnd(f) < chCount Then
            endLine = chStartLines(fileChEnd(f)) - 1
        Else
            endLine = lineCount - 1
        End If

        segCount = endLine - startLine
        ReDim parts(0 To segCount)
        For li = 0 To segCount
            parts(li) = lines(startLine + li)
        Next li
        body = Join(parts, vbLf)

        rangeStr = FormatRange(fileChStart(f), fileChEnd(f), unit)
        safe = SanitizeFileName(rangeStr)
        serial = Format(f + 1, serialFmt)
        fname = serial & "_" & safe & ".txt"
        If Len(prefix) > 0 Then fname = prefix & "_" & fname

        WriteTextUTF8NoBOM outDirFull & "\" & fname, body
    Next f
    On Error GoTo 0

    ' --- 10. 完成报告 ---
    ShowCompleteReport "聚合拆分完成", fileCount, outDirFull, tRead1, tScan1, Timer - t0
    Exit Sub
GroupWriteErr:
    MsgBox "写入第 " & (f + 1) & " 份文件时出错：" & vbCrLf & _
           outDirFull & "\" & fname & vbCrLf & _
           "错误：" & Err.Description, vbExclamation, "写入错误"
End Sub


'==============================================================================
' 第三部分：共享内部函数
'==============================================================================

'------------------------------------------------------------------------------
' 文件选择对话框：返回选中文件路径，取消返回空串
'------------------------------------------------------------------------------
Private Function SelectTxtFile(ByVal title As String) As String
    Dim fd As Object

    On Error Resume Next
    Set fd = Application.FileDialog(3)   ' msoFileDialogFilePicker = 3
    On Error GoTo 0

    If fd Is Nothing Then
        MsgBox "当前环境不支持文件选择对话框。", vbExclamation, "提示"
        Exit Function
    End If

    fd.Title = title
    On Error Resume Next
    fd.Filters.Clear
    fd.Filters.Add "文本文件", "*.txt"
    On Error GoTo 0

    If fd.Show <> -1 Then Exit Function
    SelectTxtFile = fd.SelectedItems(1)
End Function

'------------------------------------------------------------------------------
' 统一章节扫描：返回起点/终点行号、标题、章节数、单位词
'------------------------------------------------------------------------------
Private Sub ScanChapters(lines() As String, ByVal lineCount As Long, _
        ByRef chStarts() As Long, ByRef chEnds() As Long, _
        ByRef chTitles() As String, _
        ByRef chCount As Long, ByRef unit As String)
    Dim reg As Object, i As Long, m As Object

    ReDim chStarts(0 To 127)
    ReDim chEnds(0 To 127)
    ReDim chTitles(0 To 127)
    chCount = 0
    unit = "回"

    Set reg = CreateObject("VBScript.RegExp")
    reg.Pattern = CHAPTER_PATTERN
    reg.IgnoreCase = False
    reg.Global = False

    For i = 0 To lineCount - 1
        If reg.Test(lines(i)) Then
            If chCount > 0 Then chEnds(chCount - 1) = i - 1
            chStarts(chCount) = i
            Set m = reg.Execute(lines(i))
            chTitles(chCount) = Trim(m(0).Value)
            If chCount = 0 Then unit = m(0).SubMatches(1)
            chCount = chCount + 1
            If chCount > UBound(chStarts) Then
                ReDim Preserve chStarts(0 To chCount + 127)
                ReDim Preserve chEnds(0 To chCount + 127)
                ReDim Preserve chTitles(0 To chCount + 127)
            End If
        End If
    Next i
    If chCount > 0 Then chEnds(chCount - 1) = lineCount - 1
End Sub

'------------------------------------------------------------------------------
' 清洗文件名（与 Python 一致）：
'   - 半角空格 -> 全角空格
'   - 非法字符 \ / : * ? " < > | -> 全角空格
'   - 折叠连续全角空格；长度限制 60
'------------------------------------------------------------------------------
Private Function SanitizeFileName(ByVal name As String) As String
    Dim s As String, chars As String, k As Long
    s = Replace(name, " ", "　")
    chars = "\/:*?""<>|"
    For k = 1 To Len(chars)
        s = Replace(s, Mid(chars, k, 1), "　")
    Next k
    Do While InStr(s, "　　") > 0
        s = Replace(s, "　　", "　")
    Loop
    s = Trim(s)
    If Len(s) = 0 Then s = "untitled"
    If Len(s) > 60 Then s = Left(s, 60)
    SanitizeFileName = s
End Function

'------------------------------------------------------------------------------
' 确定输出目录：空串时从源文件路径派生 <src_dir>\<basename><suffix>\
'------------------------------------------------------------------------------
Private Function ResolveOutputDir(fso As Object, ByVal InputPath As String, _
        ByVal OutputDir As String, ByVal suffix As String) As String
    If Len(OutputDir) = 0 Then
        ResolveOutputDir = fso.GetParentFolderName(InputPath) & "\" & _
                           fso.GetBaseName(InputPath) & suffix
    Else
        ResolveOutputDir = OutputDir
    End If
End Function

'------------------------------------------------------------------------------
' 清理输出目录中的旧 .txt 文件
'   使用 fso 遍历 + Delete，避免 Dir+Kill 循环中 Dir 内部状态被破坏
'   （Dir+Kill 在文件数多时已知会跳过文件或报错）
'------------------------------------------------------------------------------
Private Sub CleanOutputDir(ByVal outDir As String)
    Dim fso As Object, folder As Object, file As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FolderExists(outDir) Then
        Set folder = fso.GetFolder(outDir)
        For Each file In folder.Files
            If StrComp(fso.GetExtensionName(file.Name), "txt", vbTextCompare) = 0 Then
                file.Delete
            End If
        Next file
    End If
End Sub

'------------------------------------------------------------------------------
' 格式化章号范围字符串：第起-止单位 / 第起单位
'------------------------------------------------------------------------------
Private Function FormatRange(ByVal chStart As Long, ByVal chEnd As Long, _
        ByVal unit As String) As String
    If chStart = chEnd Then
        FormatRange = "第" & chStart & unit
    Else
        FormatRange = "第" & chStart & "-" & chEnd & unit
    End If
End Function

'------------------------------------------------------------------------------
' 显示完成报告（含计时明细：选择/读取/识别/写入/总计）
'------------------------------------------------------------------------------
Private Sub ShowCompleteReport(ByVal title As String, ByVal fileCount As Long, _
        ByVal outDir As String, ByVal tRead As Double, ByVal tScan As Double, _
        ByVal tWrite As Double)
    Dim tTotal As Double, msg As String
    tTotal = Timer - g_tTotal0

    msg = title & "！" & vbCrLf & _
          "生成文件：" & fileCount & " 个" & vbCrLf & _
          "源文件编码：" & g_detectedEnc & " → UTF-8" & vbCrLf & _
          "输出目录：" & outDir & vbCrLf & vbCrLf & _
          "【计时统计】" & vbCrLf & _
          "  文件选择：" & Format(g_tSelect, "0.00") & " 秒" & vbCrLf & _
          "  读取文件：" & Format(tRead, "0.00") & " 秒" & vbCrLf & _
          "  识别章节：" & Format(tScan, "0.00") & " 秒" & vbCrLf & _
          "  写入文件：" & Format(tWrite, "0.00") & " 秒" & vbCrLf & _
          "  总计耗时：" & Format(tTotal, "0.00") & " 秒"
    If tWrite > 0 Then
        msg = msg & vbCrLf & "  写入速率：" & Format(fileCount / tWrite, "0.0") & " 文件/秒"
    End If
    MsgBox msg, vbInformation, "完成"
End Sub


'==============================================================================
' 第四部分：聚合拆分专用内部函数
'==============================================================================

'------------------------------------------------------------------------------
' 解析聚合格式字符串
'   格式:
'     N            便捷模式: 每N章一份, 份数=ceil(total/N), 末份可能不足
'     a,b          单段: 每份a章, 共b份
'     a,b|c,d|...  多段: 各段顺序聚合, 不足自动补余数段
'   返回: 空串=成功, 非空=错误信息
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
        If total Mod n > 0 Then cnt = cnt + 1
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
