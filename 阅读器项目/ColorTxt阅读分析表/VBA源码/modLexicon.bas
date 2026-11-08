Attribute VB_Name = "modLexicon"
Option Explicit

' ============================================================
' 词表加载：维度、关键词、颜色、优先级、匹配规则
' 一个关键词出现在多个维度时，优先级数字最小者生效（优先级裁决）
' ============================================================

Public Type LexRule
    DimName As String
    Keyword As String
    ColorHex As String
    ColorRGB As Long
    Priority As Long
    Mode As String
    Enabled As Boolean
    Source As String
    Note As String
End Type

Public gRules() As LexRule
Public gRuleCount As Long

Public gDimColor As Object   ' 维度 -> RGB
Public gDimPrio As Object    ' 维度 -> 最小优先级
Public gDims() As String
Public gDimCount As Long

Public gWordBest As Object   ' 关键词 -> 规则索引（优先级最高）
Public gWordDim As Object    ' 关键词 -> 维度名
Public gMaxWordLen As Long

Public Sub LexLoad()
    Dim ws As Worksheet, lastRow As Long, i As Long
    Dim dimName As String, kw As String, colorHex As String
    Dim rgbVal As Long, prio As Long, modeS As String, enabled As Boolean
    Dim idx As Long, n As Long

    Set ws = SheetLexicon()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    gRuleCount = 0
    ReDim gRules(1 To 1)
    Set gDimColor = CreateObject("Scripting.Dictionary")
    Set gDimPrio = CreateObject("Scripting.Dictionary")
    Set gWordBest = CreateObject("Scripting.Dictionary")
    Set gWordDim = CreateObject("Scripting.Dictionary")
    gDimColor.CompareMode = 1
    gDimPrio.CompareMode = 1
    gWordBest.CompareMode = IIf(gCfg.CaseSensitive, 0, 1)
    gWordDim.CompareMode = IIf(gCfg.CaseSensitive, 0, 1)
    gMaxWordLen = 1
    gDimCount = 0

    For i = LEX_DATA_START To lastRow
        dimName = Trim(SVal(ws.Cells(i, 1).Value))
        kw = Trim(SVal(ws.Cells(i, 2).Value))
        If Len(dimName) > 0 And Len(kw) > 0 Then
            enabled = ToBool(ws.Cells(i, 6).Value)
            If enabled And DimensionEnabled(dimName) Then
                colorHex = Trim(SVal(ws.Cells(i, 3).Value))
                rgbVal = HexToRGB(colorHex)
                prio = ToLong(ws.Cells(i, 4).Value, 99)
                If prio < 1 Then prio = 99
                modeS = Trim(SVal(ws.Cells(i, 5).Value))
                If Len(modeS) = 0 Then modeS = "继承"

                n = gRuleCount + 1
                gRuleCount = n
                ReDim Preserve gRules(1 To n)
                With gRules(n)
                    .DimName = dimName
                    .Keyword = kw
                    .ColorHex = colorHex
                    .Priority = prio
                    .Mode = modeS
                    .Enabled = True
                    .Source = Trim(SVal(ws.Cells(i, 7).Value))
                    .Note = Trim(SVal(ws.Cells(i, 8).Value))
                End With

                ' 维度颜色：取该维度首次出现（或优先级最高行）的颜色
                If Not gDimColor.Exists(dimName) Then
                    If rgbVal < 0 Then rgbVal = LexPalette(gDimColor.Count)
                    gDimColor(dimName) = rgbVal
                End If
                If rgbVal >= 0 Then gRules(n).ColorRGB = rgbVal
                If gRules(n).ColorRGB = 0 And rgbVal < 0 Then gRules(n).ColorRGB = gDimColor(dimName)
                If gRules(n).ColorRGB = 0 Then gRules(n).ColorRGB = LexPalette(n - 1)

                ' 维度优先级取最小值
                If Not gDimPrio.Exists(dimName) Then
                    gDimPrio(dimName) = prio
                ElseIf prio < CLng(gDimPrio(dimName)) Then
                    gDimPrio(dimName) = prio
                End If

                If Len(kw) > gMaxWordLen Then gMaxWordLen = Len(kw)

                ' 仅当全局为词典最大匹配且该规则按整词匹配时，登记到词词典
                If gCfg.MatchMode = "词典最大匹配" Then
                    If LexEffectiveMode(modeS) = "整词" Then
                        If gWordBest.Exists(kw) Then
                            idx = CLng(gWordBest(kw))
                            If prio < gRules(idx).Priority Then gWordBest(kw) = n
                        Else
                            gWordBest(kw) = n
                        End If
                        gWordDim(kw) = gRules(CLng(gWordBest(kw))).DimName
                    End If
                End If
            End If
        End If
    Next i

    LexBuildDims

    If gRuleCount = 0 Then
        LogMsg "LEXICON", "词表没有可用关键词（请检查「启用」列与维度开关）", "ERROR"
    Else
        LogMsg "LEXICON", "已加载 " & gRuleCount & " 条规则 / " & gDimCount & " 个维度 / 词典词 " & gWordBest.Count & " 个"
    End If
End Sub

Private Sub LexBuildDims()
    Dim tmp As Object, i As Long, j As Long, k As Long, n As Long
    Dim tmpS As String, tmpV As Long
    Dim tmpPrio() As Long
    Set tmp = CreateObject("Scripting.Dictionary")
    tmp.CompareMode = 1
    For i = 1 To gRuleCount
        If Not tmp.Exists(gRules(i).DimName) Then
            tmp(gRules(i).DimName) = CLng(gDimPrio(gRules(i).DimName))
        End If
    Next i
    n = tmp.Count
    gDimCount = n
    If n = 0 Then Exit Sub
    ReDim gDims(1 To n)
    ReDim tmpPrio(1 To n)
    k = 0
    Dim v As Variant
    For Each v In tmp.Keys
        k = k + 1
        gDims(k) = CStr(v)
        tmpPrio(k) = CLng(tmp(v))
    Next
    ' 按优先级升序，相同优先级按维度名
    For i = 2 To n
        tmpS = gDims(i)
        tmpV = tmpPrio(i)
        j = i - 1
        Do While j >= 1
            If tmpPrio(j) > tmpV Or (tmpPrio(j) = tmpV And gDims(j) > tmpS) Then
                gDims(j + 1) = gDims(j)
                tmpPrio(j + 1) = tmpPrio(j)
                j = j - 1
            Else
                Exit Do
            End If
        Loop
        gDims(j + 1) = tmpS
        tmpPrio(j + 1) = tmpV
    Next i
End Sub

Private Function LexPalette(ByVal idx As Long) As Long
    Dim hexes(0 To 7) As String
    hexes(0) = "#C00000"
    hexes(1) = "#1F4E79"
    hexes(2) = "#2E7D32"
    hexes(3) = "#00838F"
    hexes(4) = "#BF8F00"
    hexes(5) = "#7B1FA2"
    hexes(6) = "#5D4037"
    hexes(7) = "#616161"
    LexPalette = HexToRGB(hexes(idx Mod 8))
End Function

Public Function LexEffectiveMode(ByVal ruleMode As String) As String
    Dim m As String
    m = Trim(ruleMode)
    If Len(m) = 0 Or m = "继承" Then
        Select Case gCfg.MatchMode
            Case "词典最大匹配", "最大匹配": m = "整词"
            Case "关键词包含", "包含": m = "包含"
            Case "正则": m = "正则"
            Case Else: m = "整词"
        End Select
    Else
        Select Case m
            Case "整词", "包含", "正则"
            Case Else: m = "整词"
        End Select
    End If
    LexEffectiveMode = m
End Function

Public Function LexRuleActive(ByVal idx As Long) As Boolean
    If idx < 1 Or idx > gRuleCount Then
        LexRuleActive = False
        Exit Function
    End If
    LexRuleActive = gRules(idx).Enabled And DimensionEnabled(gRules(idx).DimName)
End Function
