Attribute VB_Name = "modAnalyze"
Option Explicit

' ============================================================
' 维度匹配与优先级裁决
' 流程：关键词命中 -> 按优先级/长度排序 -> 去重叠 -> 得到主维度与着色片段
' 统计：维度命中次数/句覆盖/字数覆盖、词频、字频、分段分布
' ============================================================

Public gHitDim() As String
Public gHitWords() As String
Public gHitCount() As Long
Public gPrimary() As String
Public gColorMap() As String
Public gHitNote() As String

Public gDimHitCount As Object
Public gDimSentCount As Object
Public gDimCharCount As Object
Public gWordFreq As Object
Public gCharFreq As Object
Public gDimParaCount As Object
Public gDimWordCount As Object

Public gTotalHits As Long
Public gHitSentenceCount As Long
Public gAnalyzeSeconds As Double

Private hPos() As Long
Private hLen() As Long
Private hKw() As String
Private hDim() As String
Private hPrio() As Long
Private hN As Long

Private gRe As Object

Public Sub AnaRun()
    Dim i As Long, t0 As Double, cap As Long
    t0 = Timer
    AnaInitStats
    cap = gSentCount
    If cap < 1 Then cap = 1
    ReDim gHitDim(1 To cap)
    ReDim gHitWords(1 To cap)
    ReDim gHitCount(1 To cap)
    ReDim gPrimary(1 To cap)
    ReDim gColorMap(1 To cap)
    ReDim gHitNote(1 To cap)

    For i = 1 To gSentCount
        AnaSentence i
        If (i Mod 250) = 0 Then DoEvents
    Next i
    gAnalyzeSeconds = Timer - t0
End Sub

Private Sub AnaInitStats()
    Set gDimHitCount = CreateObject("Scripting.Dictionary")
    Set gDimSentCount = CreateObject("Scripting.Dictionary")
    Set gDimCharCount = CreateObject("Scripting.Dictionary")
    Set gWordFreq = CreateObject("Scripting.Dictionary")
    Set gCharFreq = CreateObject("Scripting.Dictionary")
    Set gDimParaCount = CreateObject("Scripting.Dictionary")
    Set gDimWordCount = CreateObject("Scripting.Dictionary")
    gDimHitCount.CompareMode = 1
    gDimSentCount.CompareMode = 1
    gDimCharCount.CompareMode = 1
    gWordFreq.CompareMode = IIf(gCfg.CaseSensitive, 0, 1)
    gCharFreq.CompareMode = 1
    gDimParaCount.CompareMode = 1
    gDimWordCount.CompareMode = IIf(gCfg.CaseSensitive, 0, 1)
    gTotalHits = 0
    gHitSentenceCount = 0
    gAnalyzeSeconds = 0
End Sub

Private Sub AnaSentence(ByVal i As Long)
    hN = 0
    AnaCollect gSent(i)
    AnaResolve i
End Sub

Private Sub AnaCollect(ByVal s As String)
    Dim r As Long, mode As String
    For r = 1 To gRuleCount
        If LexRuleActive(r) Then
            mode = LexEffectiveMode(gRules(r).Mode)
            Select Case mode
                Case "正则"
                    AnaAddRegex s, r
                Case "包含"
                    AnaAddContains s, r
                Case "整词"
                    If gCfg.MatchMode <> "词典最大匹配" Then AnaAddContains s, r
                Case Else
                    AnaAddContains s, r
            End Select
        End If
    Next r
    If gCfg.MatchMode = "词典最大匹配" Then AnaTokenPass s
End Sub

Private Sub AnaTokenPass(ByVal s As String)
    Dim i As Long, L As Long, maxL As Long, w As String, best As Long
    i = 1
    Do While i <= Len(s)
        If TxtIsWordChar(Mid(s, i, 1)) Then
            maxL = gMaxWordLen
            If maxL > Len(s) - i + 1 Then maxL = Len(s) - i + 1
            best = -1
            For L = maxL To 1 Step -1
                w = Mid(s, i, L)
                If gWordBest.Exists(w) Then
                    best = CLng(gWordBest(w))
                    AnaAddHit i, L, gRules(best).Keyword, gRules(best).DimName, gRules(best).Priority
                    i = i + L
                    Exit For
                End If
            Next L
            If best < 0 Then i = i + 1
        Else
            i = i + 1
        End If
    Loop
End Sub

Private Sub AnaAddContains(ByVal s As String, ByVal r As Long)
    Dim cmp As Long, pos As Long, kw As String, ln As Long
    kw = gRules(r).Keyword
    ln = Len(kw)
    If ln = 0 Then Exit Sub
    cmp = IIf(gCfg.CaseSensitive, vbBinaryCompare, vbTextCompare)
    pos = InStr(1, s, kw, cmp)
    Do While pos > 0
        AnaAddHit pos, ln, kw, gRules(r).DimName, gRules(r).Priority
        If hN >= 300 Then Exit Do
        pos = InStr(pos + ln, s, kw, cmp)
    Loop
End Sub

Private Sub AnaAddRegex(ByVal s As String, ByVal r As Long)
    Dim ms As Object, m As Object
    If gRe Is Nothing Then Set gRe = CreateObject("VBScript.RegExp")
    On Error Resume Next
    gRe.Global = True
    gRe.IgnoreCase = Not gCfg.CaseSensitive
    gRe.Pattern = gRules(r).Keyword
    If Err.Number <> 0 Then
        Err.Clear
        LogMsg "REGEX", "规则 #" & r & " 正则无效：" & gRules(r).Keyword, "WARN"
        On Error GoTo 0
        Exit Sub
    End If
    Set ms = gRe.Execute(s)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    For Each m In ms
        If m.Length > 0 Then
            AnaAddHit m.FirstIndex + 1, m.Length, m.Value, gRules(r).DimName, gRules(r).Priority
        End If
        If hN >= 300 Then Exit For
    Next m
End Sub

Private Sub AnaAddHit(ByVal pos As Long, ByVal ln As Long, ByVal kw As String, ByVal dimName As String, ByVal prio As Long)
    Dim cap As Long
    If hN = 0 Then
        cap = 32
        ReDim hPos(1 To cap)
        ReDim hLen(1 To cap)
        ReDim hKw(1 To cap)
        ReDim hDim(1 To cap)
        ReDim hPrio(1 To cap)
    ElseIf hN >= UBound(hPos) Then
        cap = hN * 2
        ReDim Preserve hPos(1 To cap)
        ReDim Preserve hLen(1 To cap)
        ReDim Preserve hKw(1 To cap)
        ReDim Preserve hDim(1 To cap)
        ReDim Preserve hPrio(1 To cap)
    End If
    hN = hN + 1
    hPos(hN) = pos
    hLen(hN) = ln
    hKw(hN) = kw
    hDim(hN) = dimName
    hPrio(hN) = prio
End Sub

Private Function AnaBetter(ByVal a As Long, ByVal b As Long) As Boolean
    If hPrio(a) < hPrio(b) Then
        AnaBetter = True
    ElseIf hPrio(a) > hPrio(b) Then
        AnaBetter = False
    ElseIf hLen(a) > hLen(b) Then
        AnaBetter = True
    ElseIf hLen(a) < hLen(b) Then
        AnaBetter = False
    Else
        AnaBetter = (hPos(a) < hPos(b))
    End If
End Function

Private Function AnaOverlaps(ByVal idx As Long, ByRef aPos() As Long, ByRef aLen() As Long, ByVal aN As Long) As Boolean
    Dim p As Long, e As Long, q As Long, qe As Long, t As Long
    p = hPos(idx)
    e = p + hLen(idx) - 1
    For t = 1 To aN
        q = aPos(t)
        qe = q + aLen(t) - 1
        If p <= qe And q <= e Then
            AnaOverlaps = True
            Exit Function
        End If
    Next t
End Function

Private Sub AnaResolve(ByVal i As Long)
    Dim ord() As Long, k As Long, j As Long, idx As Long
    Dim aPos() As Long, aLen() As Long, aKw() As String, aDim() As String, aPrio() As Long
    Dim aN As Long, rejected As Long
    Dim dimCounts As Object, wordSeen As Object
    Dim words As String, dims As String, cm As String, primary As String
    Dim tmpS As String, tmpV As Long

    If hN = 0 Then
        gHitCount(i) = 0
        gHitDim(i) = ""
        gHitWords(i) = ""
        gPrimary(i) = ""
        gColorMap(i) = ""
        gHitNote(i) = "无命中"
        Exit Sub
    End If

    ReDim ord(1 To hN)
    For k = 1 To hN
        ord(k) = k
    Next k
    For k = 2 To hN
        idx = ord(k)
        j = k - 1
        Do While j >= 1
            If AnaBetter(idx, ord(j)) Then
                ord(j + 1) = ord(j)
                j = j - 1
            Else
                Exit Do
            End If
        Loop
        ord(j + 1) = idx
    Next k

    ReDim aPos(1 To hN)
    ReDim aLen(1 To hN)
    ReDim aKw(1 To hN)
    ReDim aDim(1 To hN)
    ReDim aPrio(1 To hN)
    aN = 0
    rejected = 0
    For k = 1 To hN
        idx = ord(k)
        If AnaOverlaps(idx, aPos, aLen, aN) Then
            rejected = rejected + 1
        Else
            aN = aN + 1
            aPos(aN) = hPos(idx)
            aLen(aN) = hLen(idx)
            aKw(aN) = hKw(idx)
            aDim(aN) = hDim(idx)
            aPrio(aN) = hPrio(idx)
        End If
    Next k

    ' 按位置排序，便于生成着色片段
    For k = 2 To aN
        tmpV = aPos(k)
        tmpS = aKw(k)
        Dim tLen As Long, tDim As String, tPrio As Long
        tLen = aLen(k): tDim = aDim(k): tPrio = aPrio(k)
        j = k - 1
        Do While j >= 1
            If aPos(j) > tmpV Then
                aPos(j + 1) = aPos(j)
                aLen(j + 1) = aLen(j)
                aKw(j + 1) = aKw(j)
                aDim(j + 1) = aDim(j)
                aPrio(j + 1) = aPrio(j)
                j = j - 1
            Else
                Exit Do
            End If
        Loop
        aPos(j + 1) = tmpV
        aLen(j + 1) = tLen
        aKw(j + 1) = tmpS
        aDim(j + 1) = tDim
        aPrio(j + 1) = tPrio
    Next k

    Set dimCounts = CreateObject("Scripting.Dictionary")
    dimCounts.CompareMode = 1
    Set wordSeen = CreateObject("Scripting.Dictionary")
    wordSeen.CompareMode = IIf(gCfg.CaseSensitive, 0, 1)
    For k = 1 To aN
        If dimCounts.Exists(aDim(k)) Then
            dimCounts(aDim(k)) = CLng(dimCounts(aDim(k))) + 1
        Else
            dimCounts(aDim(k)) = 1
        End If
        If Not wordSeen.Exists(aKw(k)) Then
            wordSeen(aKw(k)) = 1
            If Len(words) > 0 Then
                words = words & "|" & aKw(k)
            Else
                words = aKw(k)
            End If
        End If
    Next k

    ' 维度按命中次数降序、同次数按维度优先级
    Dim dn As Long, dk() As String, dv() As Long, d As Long, v As Variant
    dn = dimCounts.Count
    If dn > 0 Then
        ReDim dk(1 To dn)
        ReDim dv(1 To dn)
        d = 0
        For Each v In dimCounts.Keys
            d = d + 1
            dk(d) = CStr(v)
            dv(d) = CLng(dimCounts(v))
        Next v
        For d = 2 To dn
            tmpS = dk(d)
            tmpV = dv(d)
            j = d - 1
            Do While j >= 1
                If dv(j) < tmpV Or (dv(j) = tmpV And AnaDimRank(dk(j)) > AnaDimRank(tmpS)) Then
                    dk(j + 1) = dk(j)
                    dv(j + 1) = dv(j)
                    j = j - 1
                Else
                    Exit Do
                End If
            Loop
            dk(j + 1) = tmpS
            dv(j + 1) = tmpV
        Next d
        For d = 1 To dn
            If Len(dims) > 0 Then
                dims = dims & "|" & dk(d)
            Else
                dims = dk(d)
            End If
        Next d
        primary = dk(1)
    End If

    gHitCount(i) = aN
    gHitDim(i) = dims
    gHitWords(i) = words
    gPrimary(i) = primary
    If rejected > 0 Then
        gHitNote(i) = "重叠 " & rejected & " 处，已按优先级裁决"
    Else
        gHitNote(i) = ""
    End If

    cm = ""
    If gCfg.EnableColor Then
        For k = 1 To aN
            If Len(cm) > 0 Then cm = cm & ";"
            cm = cm & aPos(k) & "|" & aLen(k) & "|" & CLng(gDimColor(aDim(k)))
        Next k
    End If
    gColorMap(i) = cm

    AnaUpdateStats i, aN, aKw, aDim, aPos, aLen, dimCounts
End Sub

Private Function AnaDimRank(ByVal dimName As String) As Long
    If gDimPrio.Exists(dimName) Then
        AnaDimRank = CLng(gDimPrio(dimName))
    Else
        AnaDimRank = 99
    End If
End Function

Private Sub AnaUpdateStats(ByVal i As Long, ByVal aN As Long, ByRef aKw() As String, ByRef aDim() As String, _
    ByRef aPos() As Long, ByRef aLen() As Long, ByVal dimCounts As Object)
    Dim v As Variant, k As Long, p As Long, q As Long, ch As String
    Dim s As String

    gTotalHits = gTotalHits + aN
    If aN > 0 Then gHitSentenceCount = gHitSentenceCount + 1
    s = gSent(i)

    For Each v In dimCounts.Keys
        p = CLng(dimCounts(v))
        If gDimHitCount.Exists(CStr(v)) Then
            gDimHitCount(CStr(v)) = CLng(gDimHitCount(CStr(v))) + p
        Else
            gDimHitCount(CStr(v)) = p
        End If
        If gDimSentCount.Exists(CStr(v)) Then
            gDimSentCount(CStr(v)) = CLng(gDimSentCount(CStr(v))) + 1
        Else
            gDimSentCount(CStr(v)) = 1
        End If
        If gDimCharCount.Exists(CStr(v)) Then
            gDimCharCount(CStr(v)) = CLng(gDimCharCount(CStr(v))) + Len(s)
        Else
            gDimCharCount(CStr(v)) = Len(s)
        End If
    Next v

    For k = 1 To aN
        If gWordFreq.Exists(aKw(k)) Then
            gWordFreq(aKw(k)) = CLng(gWordFreq(aKw(k))) + 1
        Else
            gWordFreq(aKw(k)) = 1
        End If
        q = gSentPara(i)
        If gDimParaCount.Exists(aDim(k) & vbTab & q) Then
            gDimParaCount(aDim(k) & vbTab & q) = CLng(gDimParaCount(aDim(k) & vbTab & q)) + 1
        Else
            gDimParaCount(aDim(k) & vbTab & q) = 1
        End If
        If gDimWordCount.Exists(aDim(k) & vbTab & aKw(k)) Then
            gDimWordCount(aDim(k) & vbTab & aKw(k)) = CLng(gDimWordCount(aDim(k) & vbTab & aKw(k))) + 1
        Else
            gDimWordCount(aDim(k) & vbTab & aKw(k)) = 1
        End If
    Next k

    ' 字频（仅汉字）
    For p = 1 To Len(s)
        ch = Mid(s, p, 1)
        If TxtIsCJK(ch) Then
            If gCharFreq.Exists(ch) Then
                gCharFreq(ch) = CLng(gCharFreq(ch)) + 1
            Else
                gCharFreq(ch) = 1
            End If
        End If
    Next p
End Sub

Public Function AnaTopWordsForDim(ByVal dimName As String, ByVal topN As Long) As String
    Dim tmp As Object, key As Variant, p As Long
    Dim ks() As String, vs() As Long, n As Long, i As Long, outS As String
    Set tmp = CreateObject("Scripting.Dictionary")
    tmp.CompareMode = gDimWordCount.CompareMode
    For Each key In gDimWordCount.Keys
        p = InStr(CStr(key), vbTab)
        If p > 0 Then
            If Left(CStr(key), p - 1) = dimName Then
                tmp(Mid(CStr(key), p + 1)) = gDimWordCount(key)
            End If
        End If
    Next key
    n = DictTopKeys(tmp, topN, ks, vs)
    For i = 1 To n
        If Len(outS) > 0 Then outS = outS & "、"
        outS = outS & ks(i) & "(" & vs(i) & ")"
    Next i
    AnaTopWordsForDim = outS
End Function
