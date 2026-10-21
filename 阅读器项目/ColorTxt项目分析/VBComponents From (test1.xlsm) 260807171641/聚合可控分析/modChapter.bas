Attribute VB_Name = "modChapter"
Option Explicit

'==============================================================================
' Phase 2: 章节分割与正则识别
'   功能: 多正则识别章节标题 → 提取章号 → 生成章节列表 → 写入"目录"工作表
'   优化: 预编译正则对象 + 倍增扩容 + 中文数字转阿拉伯 + 目录区自动检测
'   参考: splittxt3 ScanChaptersV3 逻辑精简重构
'==============================================================================

' --- 章节数据(平行数组) ---
Private ch_starts() As Long       ' 起始行索引
Private ch_ends() As Long         ' 结束行索引
Private ch_titles() As String     ' 章节标题
Private ch_nums() As Long         ' 章号(0=无号)
Private ch_levels() As String     ' chapter/volume/special
Private ch_count As Long          ' 章节总数

' --- 预设正则 ---
Private Const NUM_CLASS As String = "[0-9０-９一二三四五六七八九十百千万亿零〇○两壹貳贰叁參肆伍陸陆柒捌玖拾佰仟萬]"

'==============================================================================
' 中文数字转阿拉伯数字
'==============================================================================
Public Function CnToInt(ByVal s As String) As Long
    Dim cnNum As Object
    Set cnNum = CreateObject("Scripting.Dictionary")
    cnNum("零") = 0: cnNum("〇") = 0: cnNum("○") = 0
    cnNum("一") = 1: cnNum("二") = 2: cnNum("三") = 3: cnNum("四") = 4
    cnNum("五") = 5: cnNum("六") = 6: cnNum("七") = 7: cnNum("八") = 8: cnNum("九") = 9
    cnNum("十") = 10: cnNum("百") = 100: cnNum("千") = 1000
    cnNum("万") = 10000: cnNum("亿") = 100000000
    cnNum("两") = 2: cnNum("壹") = 1: cnNum("贰") = 2: cnNum("叁") = 3
    cnNum("肆") = 4: cnNum("伍") = 5: cnNum("陆") = 6: cnNum("柒") = 7
    cnNum("捌") = 8: cnNum("玖") = 9: cnNum("拾") = 10: cnNum("佰") = 100
    cnNum("仟") = 1000: cnNum("萬") = 10000: cnNum("億") = 100000000

    Dim ss As String, i As Long, ch As String
    ss = Trim(s)
    ' 全角转半角
    For i = 0 To 9
        ss = Replace(ss, ChrW(&HFF10 + i), CStr(i))
    Next i
    ' 纯数字直接转
    If IsDigits(ss) Then
        On Error Resume Next
        CnToInt = CLng(ss)
        If Err.Number <> 0 Then CnToInt = 0
        On Error GoTo 0
        Set cnNum = Nothing
        Exit Function
    End If

    Dim total As Long, section As Long, current As Long, lastDigit As Long, val As Long
    total = 0: section = 0: current = 0: lastDigit = 0

    For i = 1 To Len(ss)
        ch = Mid(ss, i, 1)
        If Not cnNum.Exists(ch) Then GoTo NextChar
        val = cnNum(ch)
        If val < 10 Then
            lastDigit = val
        ElseIf val = 10 Then
            current = current + IIf(lastDigit > 0, lastDigit * 10, 10): lastDigit = 0
        ElseIf val = 100 Then
            current = current + IIf(lastDigit > 0, lastDigit * 100, 100): lastDigit = 0
        ElseIf val = 1000 Then
            current = current + IIf(lastDigit > 0, lastDigit * 1000, 1000): lastDigit = 0
        ElseIf val = 10000 Then
            If lastDigit > 0 Then current = current + lastDigit: lastDigit = 0
            section = (section + current) * 10000: current = 0
        ElseIf val = 100000000 Then
            If lastDigit > 0 Then current = current + lastDigit: lastDigit = 0
            total = (total + section + current) * 100000000: section = 0: current = 0
        End If
NextChar:
    Next i

    If lastDigit > 0 Then current = current + lastDigit
    On Error Resume Next
    CnToInt = total + section + current
    If Err.Number <> 0 Then CnToInt = 0
    On Error GoTo 0
    Set cnNum = Nothing
End Function

Private Function IsDigits(ByVal s As String) As Boolean
    Dim i As Long
    IsDigits = True
    For i = 1 To Len(s)
        If Not IsNumeric(Mid(s, i, 1)) Then IsDigits = False: Exit Function
    Next i
End Function

'==============================================================================
' 章节扫描主函数
'==============================================================================

'------------------------------------------------------------------------------
' 扫描章节 (多正则并列)
'   参数: lines() - 文本行数组, lineCount - 行数
'         patterns() - 正则模式数组, patternCount - 正则数
'   输出: ch_starts/ends/titles/nums/levels/count (模块级变量)
'------------------------------------------------------------------------------
Public Sub ScanChapters(lines() As String, ByVal lineCount As Long, _
                        patterns() As String, ByVal patternCount As Long)
    Dim regs() As Object
    Dim i As Long, r As Long, matched As Boolean, matchIdx As Long
    Dim m As Object, numStr As String, chNum As Long
    Dim initCap As Long, newCap As Long

    ' 初始化容量 2048 (倍增扩容)
    initCap = 2048
    ReDim ch_starts(0 To initCap - 1)
    ReDim ch_ends(0 To initCap - 1)
    ReDim ch_titles(0 To initCap - 1)
    ReDim ch_nums(0 To initCap - 1)
    ReDim ch_levels(0 To initCap - 1)
    ch_count = 0

    ' 预编译正则
    ReDim regs(0 To patternCount - 1)
    For r = 0 To patternCount - 1
        Set regs(r) = CreateObject("VBScript.RegExp")
        regs(r).Pattern = patterns(r)
        regs(r).IgnoreCase = True
    Next r

    ' 逐行扫描
    For i = 0 To lineCount - 1
        Dim line As String
        line = lines(i)
        If Len(Trim(line)) = 0 Then GoTo NextLine

        matched = False
        matchIdx = -1

        For r = 0 To patternCount - 1
            If regs(r).Test(line) Then
                matched = True
                matchIdx = r
                Exit For
            End If
        Next r

        If matched Then
            Set m = regs(matchIdx).Execute(line)
            Dim fullTitle As String
            fullTitle = Trim(m(0).Value)

            ' 提取章号
            If m(0).SubMatches.Count >= 1 Then
                numStr = m(0).SubMatches(0)
                chNum = CnToInt(numStr)
            Else
                chNum = 0
            End If

            ' 判断章节级别
            Dim lvl As String
            If chNum = 0 Then
                lvl = "special"
            Else
                lvl = "chapter"
            End If

            ' 设置上一章结束行
            If ch_count > 0 Then ch_ends(ch_count - 1) = i - 1
            ch_starts(ch_count) = i
            ch_titles(ch_count) = fullTitle
            ch_nums(ch_count) = chNum
            ch_levels(ch_count) = lvl
            ch_count = ch_count + 1

            ' 倍增扩容
            If ch_count > UBound(ch_starts) Then
                newCap = (UBound(ch_starts) + 1) * 2
                ReDim Preserve ch_starts(0 To newCap - 1)
                ReDim Preserve ch_ends(0 To newCap - 1)
                ReDim Preserve ch_titles(0 To newCap - 1)
                ReDim Preserve ch_nums(0 To newCap - 1)
                ReDim Preserve ch_levels(0 To newCap - 1)
            End If
        End If
NextLine:
    Next i

    ' 最后一章结束行
    If ch_count > 0 Then ch_ends(ch_count - 1) = lineCount - 1

    ' 释放正则对象
    For r = 0 To patternCount - 1
        Set regs(r) = Nothing
    Next r
End Sub

'==============================================================================
' 预设正则表达式
'==============================================================================

' 获取默认章节正则 (返回数组)
Public Sub GetDefaultPatterns(ByRef patterns() As String, ByRef count As Long)
    count = 3
    ReDim patterns(0 To count - 1)
    ' 1. 标准中文: 第N章/回/节 (含中文数字)
    patterns(0) = "^[ \t　]*第(" & NUM_CLASS & "+)(章|回|节)(?:[ \t　：:]+(.*))?$"
    ' 2. 无第字: N章/回/节
    patterns(1) = "^[ \t　]*(" & NUM_CLASS & "+)(章|回|节)(?:[ \t　：:]+(.*))?$"
    ' 3. 无号特殊章节: 序章/楔子/番外等
    patterns(2) = "^[ \t　]*(序章|楔子|尾声|番外|引子|后记|终章|序言|前言|跋)(?:[ \t　：:]+(.*))?$"
End Sub

'==============================================================================
' 写入"目录"工作表
'==============================================================================

'------------------------------------------------------------------------------
' 将章节列表写入"目录"工作表
'   结构: A列=章节标题, B列=章号
'   返回: 章节数量
'------------------------------------------------------------------------------
Public Function WriteChaptersToSheet() As Long
    Dim ws As Worksheet
    Dim i As Long, chapIdx As Long
    Dim chapIndices() As Long, chapCount As Long

    Set ws = GetOrCreateSheet("目录")
    ws.Cells.Clear

    ' 表头
    ws.Range("A1").Value = "章节标题"
    ws.Range("B1").Value = "章号"
    ws.Range("A1:B1").Font.Bold = True
    ws.Range("A1:B1").Interior.Color = RGB(217, 225, 242)

    ' 筛选章节级(排除volume)
    ReDim chapIndices(0 To ch_count - 1)
    chapCount = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then
            chapIndices(chapCount) = i
            chapCount = chapCount + 1
        End If
    Next i

    If chapCount = 0 Then
        Debug.Print "[Phase2] 未识别到章节"
        WriteChaptersToSheet = 0
        Exit Function
    End If

    ' 批量写入
    Dim outputData() As Variant
    ReDim outputData(1 To chapCount, 1 To 2)
    For i = 0 To chapCount - 1
        chapIdx = chapIndices(i)
        outputData(i + 1, 1) = ch_titles(chapIdx)
        outputData(i + 1, 2) = ch_nums(chapIdx)
    Next i

    ws.Range("A2").Resize(chapCount, 2).Value = outputData
    ws.Columns("A").AutoFit
    ws.Columns("B").AutoFit

    Debug.Print "[Phase2] 识别章节: " & chapCount & " 章"
    WriteChaptersToSheet = chapCount
End Function

'------------------------------------------------------------------------------
' 获取章节数据 (供其他模块调用)
'------------------------------------------------------------------------------
Public Sub GetChapterData(ByRef titles() As String, ByRef starts() As Long, _
                          ByRef ends() As Long, ByRef count As Long)
    Dim i As Long, chapIdx As Long
    Dim chapIndices() As Long, chapCount As Long

    ReDim chapIndices(0 To ch_count - 1)
    chapCount = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then
            chapIndices(chapCount) = i
            chapCount = chapCount + 1
        End If
    Next i

    count = chapCount
    If chapCount = 0 Then Exit Sub

    ReDim titles(0 To chapCount - 1)
    ReDim starts(0 To chapCount - 1)
    ReDim ends(0 To chapCount - 1)

    For i = 0 To chapCount - 1
        chapIdx = chapIndices(i)
        titles(i) = ch_titles(chapIdx)
        starts(i) = ch_starts(chapIdx)
        ends(i) = ch_ends(chapIdx)
    Next i
End Sub
