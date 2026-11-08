Attribute VB_Name = "modText"
Option Explicit

' ============================================================
' 文本预处理：归一化、段落切分、句子切分、超长内容硬切
' 说明：Excel 单元格上限 32767 字符，超长段落会按标点或硬切分块。
' ============================================================

Public gSent() As String
Public gSentPara() As Long
Public gSentIdx() As Long
Public gSentStatus() As String
Public gSentCount As Long

Public gParaText() As String
Public gParaCount As Long

Public gTotalChars As Long
Public gCJKChars As Long
Public gTruncated As Boolean
Public gSentLimitHit As Boolean

Public Sub TxtSplitAll(ByVal raw As String)
    Dim lines() As String, i As Long, line As String, remain As String
    Dim cut As Long

    gSentCount = 0
    gParaCount = 0
    gTotalChars = 0
    gCJKChars = 0
    gTruncated = False
    gSentLimitHit = False
    ReDim gSent(1 To 1)
    ReDim gSentPara(1 To 1)
    ReDim gSentIdx(1 To 1)
    ReDim gSentStatus(1 To 1)
    ReDim gParaText(1 To 1)

    raw = TxtNormalize(raw)
    lines = Split(raw, vbLf)

    For i = LBound(lines) To UBound(lines)
        line = TxtTrim(lines(i))
        If Len(line) > 0 Then
            If Len(line) > gCfg.MaxParagraphChars Then
                remain = line
                Do While Len(remain) > 0
                    cut = TxtFindCut(remain, gCfg.MaxParagraphChars)
                    TxtAddParagraph Left(remain, cut), "超长段落已切分"
                    remain = TxtTrim(Mid(remain, cut + 1))
                Loop
            Else
                TxtAddParagraph line, ""
            End If
        ElseIf Not gCfg.IgnoreBlank Then
            ' 不忽略空行时，空行保留为空段（图表中显示为 0）
            gParaCount = gParaCount + 1
            ReDim Preserve gParaText(1 To gParaCount)
            gParaText(gParaCount) = ""
        End If
    Next i
End Sub

Public Function TxtFromSheet() As String
    Dim ws As Worksheet, lastRow As Long, i As Long
    Dim v As Variant, s As String, all As String
    Set ws = SheetInput()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < INPUT_START Then lastRow = INPUT_START - 1

    For i = INPUT_START To lastRow
        v = ws.Cells(i, 1).Value
        If Not IsEmpty(v) Then
            s = SVal(v)
            If Len(s) > 0 Then
                If Len(all) + Len(s) > gCfg.MaxTotalChars * 2 Then
                    LogMsg "INPUT", "输入超过 max_total_chars 的两倍，后续行未读取", "WARN"
                    Exit For
                End If
                If Len(all) > 0 Then
                    all = all & vbLf & s
                Else
                    all = s
                End If
            End If
        End If
    Next i
    TxtFromSheet = all
End Function

Public Function TxtNormalize(ByVal s As String) As String
    Dim t As String
    t = s
    t = Replace(t, vbCrLf, vbLf)
    t = Replace(t, vbCr, vbLf)
    t = Replace(t, vbTab, " ")
    t = Replace(t, ChrW(65279), "")      ' BOM
    t = Replace(t, ChrW(8203), "")       ' 零宽空格
    t = Replace(t, ChrW(160), " ")       ' 不换行空格
    t = Replace(t, ChrW(12288), " ")     ' 全角空格
    TxtNormalize = t
End Function

Public Function TxtTrim(ByVal s As String) As String
    Dim t As String
    t = s
    t = Trim(t)
    Do While Len(t) > 0
        If Left(t, 1) = " " Or Left(t, 1) = vbLf Or Left(t, 1) = Chr(10) Then
            t = Mid(t, 2)
        Else
            Exit Do
        End If
    Loop
    Do While Len(t) > 0
        If Right(t, 1) = " " Or Right(t, 1) = vbLf Then
            t = Left(t, Len(t) - 1)
        Else
            Exit Do
        End If
    Loop
    TxtTrim = t
End Function

Private Sub TxtAddParagraph(ByVal s As String, ByVal baseStatus As String)
    Dim remain As Long
    s = TxtTrim(s)
    If Len(s) = 0 Then Exit Sub

    ' 总字数上限保护
    If gTotalChars + Len(s) > gCfg.MaxTotalChars Then
        remain = gCfg.MaxTotalChars - gTotalChars
        If remain <= 0 Then
            gTruncated = True
            Exit Sub
        End If
        s = Left(s, remain)
        gTruncated = True
        baseStatus = "达到 max_total_chars 上限，已截断"
    End If

    gParaCount = gParaCount + 1
    ReDim Preserve gParaText(1 To gParaCount)
    gParaText(gParaCount) = s
    TxtSplitSentences s, gParaCount, baseStatus
End Sub

Private Sub TxtSplitSentences(ByVal p As String, ByVal para As Long, ByVal baseStatus As String)
    Dim i As Long, startPos As Long, idx As Long, ch As String, nxt As String, s As String
    idx = 0
    startPos = 1

    For i = 1 To Len(p)
        If TxtIsEndAt(p, i) Then
            ' 连续吃掉句末标点与后置引号/括号
            Do While i < Len(p)
                nxt = Mid(p, i + 1, 1)
                If TxtIsEndPunct(nxt) Or TxtIsClosing(nxt) Then
                    i = i + 1
                Else
                    Exit Do
                End If
            Loop
            s = Mid(p, startPos, i - startPos + 1)
            If Len(TxtTrim(s)) > 0 Then
                idx = idx + 1
                TxtAddSentence s, para, idx, baseStatus
            End If
            startPos = i + 1
        End If

        ' 无标点超长片段，按硬切兜底
        If i - startPos + 1 >= gCfg.MaxSentenceChars Then
            s = Mid(p, startPos, i - startPos + 1)
            idx = idx + 1
            TxtAddSentence s, para, idx, "超长句已切分（无标点硬切）"
            startPos = i + 1
        End If
    Next i

    If startPos <= Len(p) Then
        s = Mid(p, startPos)
        If Len(TxtTrim(s)) > 0 Then
            idx = idx + 1
            TxtAddSentence s, para, idx, baseStatus
        End If
    End If
End Sub

Private Sub TxtAddSentence(ByVal s As String, ByVal para As Long, ByRef idxInPara As Long, ByVal status As String)
    Dim remain As String, cut As Long, first As Boolean
    s = TxtTrim(s)
    If Len(s) = 0 Then Exit Sub

    If Len(s) > gCfg.MaxSentenceChars Then
        remain = s
        first = True
        Do While Len(remain) > 0
            cut = TxtFindCut(remain, gCfg.MaxSentenceChars)
            If first Then
                first = False
            Else
                idxInPara = idxInPara + 1
            End If
            TxtPushSentence Left(remain, cut), para, idxInPara, "超长句已切分"
            remain = TxtTrim(Mid(remain, cut + 1))
        Loop
    Else
        TxtPushSentence s, para, idxInPara, status
    End If
End Sub

Private Sub TxtPushSentence(ByVal s As String, ByVal para As Long, ByVal idxInPara As Long, ByVal status As String)
    s = TxtTrim(s)
    If Len(s) = 0 Then Exit Sub
    If gSentCount >= gCfg.MaxSentences Then
        gSentLimitHit = True
        Exit Sub
    End If
    gSentCount = gSentCount + 1
    ReDim Preserve gSent(1 To gSentCount)
    ReDim Preserve gSentPara(1 To gSentCount)
    ReDim Preserve gSentIdx(1 To gSentCount)
    ReDim Preserve gSentStatus(1 To gSentCount)
    gSent(gSentCount) = s
    gSentPara(gSentCount) = para
    gSentIdx(gSentCount) = idxInPara
    If Len(status) = 0 Then
        gSentStatus(gSentCount) = "正常"
    Else
        gSentStatus(gSentCount) = status
    End If
    gTotalChars = gTotalChars + Len(s)
    gCJKChars = gCJKChars + TxtCJKCount(s)
End Sub

Public Function TxtFindCut(ByVal s As String, ByVal maxLen As Long) As Long
    Dim i As Long, ch As String
    If Len(s) <= maxLen Then
        TxtFindCut = Len(s)
        Exit Function
    End If
    For i = maxLen To 2 Step -1
        ch = Mid(s, i, 1)
        If InStr("，、,；;：: ", ch) > 0 Then
            TxtFindCut = i
            Exit Function
        End If
    Next i
    TxtFindCut = maxLen
End Function

Public Function TxtIsEndAt(ByVal p As String, ByVal i As Long) As Boolean
    Dim ch As String, nxt As String
    ch = Mid(p, i, 1)
    If ch = "." Or ch = "．" Then
        nxt = ""
        If i < Len(p) Then nxt = Mid(p, i + 1, 1)
        TxtIsEndAt = (i = Len(p)) Or (nxt = " ") Or (nxt = vbLf)
    Else
        TxtIsEndAt = TxtIsEndPunct(ch)
    End If
End Function

Public Function TxtIsEndPunct(ByVal ch As String) As Boolean
    If Len(ch) = 0 Then Exit Function
    TxtIsEndPunct = (InStr("。！？!?；;…", ch) > 0)
End Function

Public Function TxtIsClosing(ByVal ch As String) As Boolean
    If Len(ch) = 0 Then Exit Function
    TxtIsClosing = (InStr("”’」』）】》〉〕］｝""')]}", ch) > 0)
End Function

Public Function TxtIsCJK(ByVal ch As String) As Boolean
    Dim w As Long
    If Len(ch) = 0 Then Exit Function
    w = AscW(ch)
    If w < 0 Then w = w + 65536
    TxtIsCJK = (w >= 19968 And w <= 40959) Or (w >= 13312 And w <= 19903)
End Function

Public Function TxtIsWordChar(ByVal ch As String) As Boolean
    Dim w As Long
    If Len(ch) = 0 Then Exit Function
    w = AscW(ch)
    If w < 0 Then w = w + 65536
    If TxtIsCJK(ch) Then
        TxtIsWordChar = True
        Exit Function
    End If
    ' 半角/全角字母数字
    If (w >= 48 And w <= 57) Or (w >= 65 And w <= 90) Or (w >= 97 And w <= 122) Then
        TxtIsWordChar = True
    ElseIf (w >= 65296 And w <= 65305) Or (w >= 65313 And w <= 65338) Or (w >= 65345 And w <= 65370) Then
        TxtIsWordChar = True
    ElseIf (w >= 12352 And w <= 12543) Then
        TxtIsWordChar = True
    End If
End Function

Public Function TxtCJKCount(ByVal s As String) As Long
    Dim i As Long, n As Long
    n = 0
    For i = 1 To Len(s)
        If TxtIsCJK(Mid(s, i, 1)) Then n = n + 1
    Next i
    TxtCJKCount = n
End Function
