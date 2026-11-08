Attribute VB_Name = "modOutput"
Option Explicit

' ============================================================
' 结果输出：逐句结果、汇总统计、图表数据、上色预览文本、词频 Top
' 约定：所有数值由 VBA 计算后写入，不使用公式，避免重算与外部引用
' ============================================================

Public Sub OutWriteAll()
    OutWriteResults
    OutWriteSummary
    OutWriteChartData
    OutWriteTop
End Sub

' ---------- 逐句结果 ----------

Public Sub OutWriteResults()
    Dim ws As Worksheet, arr() As Variant, i As Long, n As Long
    Dim startRow As Long, lastRow As Long, sNote As String, st As String, segN As Long

    Set ws = SheetResults()
    If gCfg.OverwriteResults Then
        ClearSheet ws
        startRow = gCfg.ResultStartRow
    Else
        lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
        If lastRow < 1 Then lastRow = 1
        startRow = lastRow + 1
        If startRow < 2 Then startRow = 2
    End If

    OutResultHeaders ws
    n = gSentCount
    If n < 1 Then Exit Sub

    ReDim arr(1 To n, 1 To 13)
    For i = 1 To n
        arr(i, 1) = i
        arr(i, 2) = gSentPara(i)
        arr(i, 3) = gSentIdx(i)
        arr(i, 4) = gSent(i)
        arr(i, 5) = Len(gSent(i))
        arr(i, 6) = gHitDim(i)
        arr(i, 7) = gHitWords(i)
        arr(i, 8) = gHitCount(i)
        arr(i, 9) = gPrimary(i)
        If gPrimary(i) <> "" Then
            If gDimColor.Exists(gPrimary(i)) Then
                arr(i, 10) = RGBToHex(CLng(gDimColor(gPrimary(i))))
            Else
                arr(i, 10) = ""
            End If
        Else
            arr(i, 10) = ""
        End If
        If Not gCfg.EnableColor Then
            arr(i, 11) = "未启用上色"
        ElseIf i <= gCfg.MaxColorSentences Then
            st = ""
            If gColReady Then
                If i <= UBound(gColStatus) Then st = gColStatus(i)
            End If
            If Len(st) = 0 Then st = "已上色预览"
            arr(i, 11) = st
        Else
            arr(i, 11) = "超出上色上限"
        End If
        segN = 0
        If Len(gColorMap(i)) > 0 Then segN = UBound(Split(gColorMap(i), ";")) + 1
        arr(i, 12) = segN
        sNote = gHitNote(i)
        If gSentStatus(i) <> "正常" Then
            If Len(sNote) > 0 Then
                sNote = gSentStatus(i) & "；" & sNote
            Else
                sNote = gSentStatus(i)
            End If
        End If
        arr(i, 13) = sNote
    Next i

    ws.Range("A" & startRow).Resize(n, 13).Value = arr
    OutFormatResults ws, startRow, n

    ' 主色色块（仅上色上限内的行，避免大量单元格格式调用）
    Dim cap As Long
    cap = n
    If cap > gCfg.MaxColorSentences Then cap = gCfg.MaxColorSentences
    For i = 1 To cap
        If gPrimary(i) <> "" Then
            If gDimColor.Exists(gPrimary(i)) Then
                ws.Cells(startRow + i - 1, 10).Interior.Color = CLng(gDimColor(gPrimary(i)))
            End If
        End If
    Next i
End Sub

Private Sub OutResultHeaders(ByVal ws As Worksheet)
    ws.Cells(1, 1).Value = "序号"
    ws.Cells(1, 2).Value = "段号"
    ws.Cells(1, 3).Value = "段内句号"
    ws.Cells(1, 4).Value = "原句"
    ws.Cells(1, 5).Value = "字数"
    ws.Cells(1, 6).Value = "命中维度"
    ws.Cells(1, 7).Value = "命中词"
    ws.Cells(1, 8).Value = "命中次数"
    ws.Cells(1, 9).Value = "主维度"
    ws.Cells(1, 10).Value = "主色(HEX)"
    ws.Cells(1, 11).Value = "上色状态"
    ws.Cells(1, 12).Value = "着色片段数"
    ws.Cells(1, 13).Value = "备注"
    StyleHeader ws, 13, 1
End Sub

Private Sub OutFormatResults(ByVal ws As Worksheet, ByVal startRow As Long, ByVal n As Long)
    Dim lastR As Long
    lastR = startRow + n - 1
    With ws.Range("A1:M" & lastR)
        .Font.Name = gCfg.FontName
        .Font.Size = gCfg.FontSize
        .VerticalAlignment = xlTop
    End With
    ws.Columns(1).ColumnWidth = 6
    ws.Columns(2).ColumnWidth = 6
    ws.Columns(3).ColumnWidth = 8
    ws.Columns(4).ColumnWidth = 90
    ws.Columns(4).WrapText = False
    ws.Columns(5).ColumnWidth = 6
    ws.Columns(6).ColumnWidth = 22
    ws.Columns(7).ColumnWidth = 30
    ws.Columns(8).ColumnWidth = 8
    ws.Columns(9).ColumnWidth = 12
    ws.Columns(10).ColumnWidth = 10
    ws.Columns(11).ColumnWidth = 18
    ws.Columns(12).ColumnWidth = 10
    ws.Columns(13).ColumnWidth = 26
    ws.rows(1).RowHeight = 24
End Sub

' ---------- 汇总统计 ----------

Public Sub OutWriteSummary()
    Dim ws As Worksheet, r As Long, i As Long, j As Long
    Dim hitC As Long, sentC As Long, charC As Long, uniq As Long
    Set ws = SheetSummary()
    ClearSheet ws

    ws.Cells(1, 1).Value = "ColorTxt 阅读分析 · 汇总统计"
    ws.Range("A1:I1").Merge
    With ws.Range("A1:I1")
        .Font.Name = gCfg.FontName
        .Font.Size = 16
        .Font.Bold = True
        .Font.Color = RGB(31, 78, 121)
        .HorizontalAlignment = xlLeft
    End With
    ws.rows(1).RowHeight = 30

    ws.Cells(2, 1).Value = "生成时间：" & Format(Now, "yyyy-mm-dd hh:mm:ss")
    ws.Cells(3, 1).Value = "配置摘要：" & ConfigSnapshot()
    ws.Range("A2:I2").Merge
    ws.Range("A3:I3").Merge
    ws.Cells(2, 1).Font.Size = 10
    ws.Cells(3, 1).Font.Size = 10
    ws.Cells(3, 1).Font.Color = RGB(89, 89, 89)

    r = 5
    ws.Cells(r, 1).Value = "一、总体指标"
    ws.Cells(r, 1).Font.Bold = True
    ws.Cells(r, 1).Font.Size = 12
    ws.Cells(r, 1).Font.Color = RGB(31, 78, 121)
    r = r + 1
    ws.Cells(r, 1).Value = "指标"
    ws.Cells(r, 2).Value = "数值"
    StyleHeader ws, 2, r

    OutMetric ws, r, "总字数（含标点）", gTotalChars
    OutMetric ws, r, "汉字数", gCJKChars
    OutMetric ws, r, "段落数（含切分）", gParaCount
    OutMetric ws, r, "句子数", gSentCount
    If gSentCount > 0 Then
        OutMetric ws, r, "平均句长（字/句）", Format(gTotalChars / gSentCount, "0.0")
    Else
        OutMetric ws, r, "平均句长（字/句）", "0"
    End If
    OutMetric ws, r, "命中句数", gHitSentenceCount
    OutMetric ws, r, "句命中率", FormatPct(gHitSentenceCount, gSentCount)
    OutMetric ws, r, "总命中次数", gTotalHits
    OutMetric ws, r, "命中关键词数（去重）", gWordFreq.Count
    OutMetric ws, r, "唯一汉字数", gCharFreq.Count
    OutMetric ws, r, "匹配模式", gCfg.MatchMode
    OutMetric ws, r, "上色模式", gCfg.ColorMode
    OutMetric ws, r, "上色句子上限", gCfg.MaxColorSentences
    OutMetric ws, r, "分析耗时（秒）", Format(gAnalyzeSeconds, "0.000")
    OutMetric ws, r, "全流程耗时（秒）", "待更新"
    OutMetric ws, r, "上色字符数", 0
    OutMetric ws, r, "上色命中数", 0
    OutMetric ws, r, "上色是否截断", "待更新"
    OutMetric ws, r, "日志错误数", 0
    OutMetric ws, r, "图表对象数", 0

    ' 维度统计
    r = r + 2
    ws.Cells(r, 1).Value = "二、维度统计"
    ws.Cells(r, 1).Font.Bold = True
    ws.Cells(r, 1).Font.Size = 12
    ws.Cells(r, 1).Font.Color = RGB(31, 78, 121)
    r = r + 1
    ws.Cells(r, 1).Value = "维度"
    ws.Cells(r, 2).Value = "优先级"
    ws.Cells(r, 3).Value = "颜色"
    ws.Cells(r, 4).Value = "命中次数"
    ws.Cells(r, 5).Value = "命中句数"
    ws.Cells(r, 6).Value = "句覆盖率"
    ws.Cells(r, 7).Value = "覆盖字数"
    ws.Cells(r, 8).Value = "字数覆盖率"
    ws.Cells(r, 9).Value = "唯一词数"
    ws.Cells(r, 10).Value = "Top词"
    StyleHeader ws, 10, r

    For i = 1 To gDimCount
        r = r + 1
        ws.Cells(r, 1).Value = gDims(i)
        ws.Cells(r, 2).Value = AnaDimPriority(gDims(i))
        ws.Cells(r, 3).Value = RGBToHex(CLng(gDimColor(gDims(i))))
        hitC = 0: sentC = 0: charC = 0
        If gDimHitCount.Exists(gDims(i)) Then hitC = CLng(gDimHitCount(gDims(i)))
        If gDimSentCount.Exists(gDims(i)) Then sentC = CLng(gDimSentCount(gDims(i)))
        If gDimCharCount.Exists(gDims(i)) Then charC = CLng(gDimCharCount(gDims(i)))
        uniq = OutUniqueWordsForDim(gDims(i))
        ws.Cells(r, 4).Value = hitC
        ws.Cells(r, 5).Value = sentC
        ws.Cells(r, 6).Value = FormatPct(sentC, gSentCount)
        ws.Cells(r, 7).Value = charC
        ws.Cells(r, 8).Value = FormatPct(charC, gTotalChars)
        ws.Cells(r, 9).Value = uniq
        ws.Cells(r, 10).Value = AnaTopWordsForDim(gDims(i), gCfg.SummaryTopN)
        ws.Cells(r, 3).Interior.Color = CLng(gDimColor(gDims(i)))
        ws.Cells(r, 3).Font.Color = RGB(255, 255, 255)
        ws.Cells(r, 3).Font.Bold = True
        ws.Cells(r, 3).HorizontalAlignment = xlCenter
    Next i

    ' 校验
    r = r + 2
    ws.Cells(r, 1).Value = "三、一致性校验"
    ws.Cells(r, 1).Font.Bold = True
    ws.Cells(r, 1).Font.Size = 12
    ws.Cells(r, 1).Font.Color = RGB(31, 78, 121)

    Dim dimSum As Long, resultRows As Long, okAll As Boolean
    dimSum = OutDimHitSum()
    resultRows = OutCountResultRows()
    r = r + 1
    ws.Cells(r, 1).Value = "校验项"
    ws.Cells(r, 2).Value = "数值"
    StyleHeader ws, 2, r

    OutMetric ws, r, "逐句结果行数", resultRows
    OutMetric ws, r, "句子数", gSentCount
    OutMetric ws, r, "维度命中合计", dimSum
    OutMetric ws, r, "总命中次数", gTotalHits
    okAll = (resultRows = gSentCount) And (dimSum = gTotalHits)
    r = r + 1
    ws.Cells(r, 1).Value = "校验结论"
    If okAll Then
        ws.Cells(r, 2).Value = "PASS"
        ws.Cells(r, 2).Font.Color = RGB(46, 125, 50)
    Else
        ws.Cells(r, 2).Value = "WARN"
        ws.Cells(r, 2).Font.Color = RGB(192, 0, 0)
    End If
    ws.Cells(r, 2).Font.Bold = True

    ws.Columns(1).ColumnWidth = 24
    ws.Columns(2).ColumnWidth = 16
    ws.Columns(3).ColumnWidth = 10
    ws.Columns(4).ColumnWidth = 12
    ws.Columns(5).ColumnWidth = 12
    ws.Columns(6).ColumnWidth = 12
    ws.Columns(7).ColumnWidth = 12
    ws.Columns(8).ColumnWidth = 14
    ws.Columns(9).ColumnWidth = 10
    ws.Columns(10).ColumnWidth = 46
    ws.Range("A1:J" & r).Font.Name = gCfg.FontName
End Sub

Private Sub OutMetric(ByVal ws As Worksheet, ByRef r As Long, ByVal label As String, ByVal val As Variant)
    r = r + 1
    ws.Cells(r, 1).Value = label
    ws.Cells(r, 2).Value = val
    ws.Cells(r, 1).Font.Color = RGB(64, 64, 64)
End Sub

Private Function OutUniqueWordsForDim(ByVal dimName As String) As Long
    Dim key As Variant, p As Long, n As Long
    n = 0
    For Each key In gDimWordCount.Keys
        p = InStr(CStr(key), vbTab)
        If p > 0 Then
            If Left(CStr(key), p - 1) = dimName Then n = n + 1
        End If
    Next key
    OutUniqueWordsForDim = n
End Function

Private Function OutDimHitSum() As Long
    Dim key As Variant, n As Long
    n = 0
    For Each key In gDimHitCount.Keys
        n = n + CLng(gDimHitCount(key))
    Next key
    OutDimHitSum = n
End Function

Public Function OutCountResultRows() As Long
    Dim ws As Worksheet, lastRow As Long
    Set ws = SheetResults()
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow < 2 Then
        OutCountResultRows = 0
    Else
        OutCountResultRows = lastRow - 1
    End If
End Function

Public Function AnaDimPriority(ByVal dimName As String) As Long
    If gDimPrio.Exists(dimName) Then
        AnaDimPriority = CLng(gDimPrio(dimName))
    Else
        AnaDimPriority = 99
    End If
End Function

' ---------- 图表数据 ----------

Public Sub OutWriteChartData()
    Dim ws As Worksheet, p As Long, d As Long, i As Long, j As Long
    Dim arr() As Variant, total As Long, v As Long, key As String
    Set ws = SheetChartData()
    ClearSheet ws
    p = gParaCount
    d = gDimCount
    If p < 1 Or d < 1 Then Exit Sub

    ReDim arr(1 To p + 1, 1 To d + 2)
    arr(1, 1) = "段号"
    For j = 1 To d
        arr(1, 1 + j) = gDims(j)
    Next j
    arr(1, d + 2) = "合计"

    For i = 1 To p
        arr(i + 1, 1) = "第" & i & "段"
        total = 0
        For j = 1 To d
            v = 0
            key = gDims(j) & vbTab & i
            If gDimParaCount.Exists(key) Then v = CLng(gDimParaCount(key))
            arr(i + 1, 1 + j) = v
            total = total + v
        Next j
        arr(i + 1, d + 2) = total
    Next i

    ws.Range("A1").Resize(p + 1, d + 2).Value = arr
    StyleHeader ws, d + 2, 1
    ws.Columns(1).ColumnWidth = 10
    For j = 2 To d + 2
        ws.Columns(j).ColumnWidth = 10
    Next j
    ws.Range("A1").Resize(p + 1, d + 2).Font.Name = gCfg.FontName
    ws.Range("A1").Resize(p + 1, d + 2).Font.Size = 10
End Sub

' ---------- 上色预览（仅文本） ----------

Public Sub OutWritePreviewText()
    Dim ws As Worksheet, n As Long, i As Long, arr() As Variant
    Set ws = SheetPreview()
    ClearSheet ws

    ws.Cells(1, 1).Value = "编号"
    ws.Cells(1, 2).Value = "正文（字符级着色）"
    ws.Cells(1, 3).Value = "主维度"
    ws.Cells(1, 4).Value = "上色状态"
    StyleHeader ws, 4, 1

    n = gSentCount
    If n > gCfg.MaxColorSentences Then n = gCfg.MaxColorSentences
    If n < 1 Then Exit Sub

    ReDim arr(1 To n, 1 To 4)
    For i = 1 To n
        arr(i, 1) = gSentPara(i) & "-" & gSentIdx(i)
        arr(i, 2) = gSent(i)
        arr(i, 3) = gPrimary(i)
        arr(i, 4) = "待上色"
    Next i
    ws.Range("A2").Resize(n, 4).Value = arr

    ws.Columns(1).ColumnWidth = 8
    ws.Columns(2).ColumnWidth = 150
    ws.Columns(3).ColumnWidth = 12
    ws.Columns(4).ColumnWidth = 20
    ws.Columns(2).WrapText = True
    With ws.Range("A1:D" & (n + 1))
        .Font.Name = gCfg.FontName
        .Font.Size = gCfg.FontSize + 1
        .VerticalAlignment = xlCenter
    End With
    ws.Range("B2:B" & (n + 1)).HorizontalAlignment = xlLeft
    ws.rows("2:" & (n + 1)).RowHeight = 38
End Sub

' ---------- 词频 / 字频 Top ----------

Public Sub OutWriteTop()
    Dim ws As Worksheet, n As Long, i As Long
    Dim ks() As String, vs() As Long
    Dim arr() As Variant
    Set ws = SheetTop()
    ClearSheet ws

    ws.Cells(1, 1).Value = "排名"
    ws.Cells(1, 2).Value = "词"
    ws.Cells(1, 3).Value = "次数"
    ws.Cells(1, 4).Value = "维度"
    StyleHeader ws, 4, 1

    n = DictTopKeys(gWordFreq, gCfg.TopN, ks, vs)
    If n > 0 Then
        ReDim arr(1 To n, 1 To 4)
        For i = 1 To n
            arr(i, 1) = i
            arr(i, 2) = ks(i)
            arr(i, 3) = vs(i)
            If gWordDim.Exists(ks(i)) Then arr(i, 4) = gWordDim(ks(i)) Else arr(i, 4) = ""
        Next i
        ws.Range("A2").Resize(n, 4).Value = arr
    End If

    ' 字频区（F:H）
    ws.Cells(1, 6).Value = "排名"
    ws.Cells(1, 7).Value = "字"
    ws.Cells(1, 8).Value = "次数"
    With ws.Range("F1:H1")
        .Font.Bold = True
        .Font.Color = RGB(255, 255, 255)
        .Interior.Color = RGB(31, 78, 121)
        .HorizontalAlignment = xlCenter
    End With
    n = DictTopKeys(gCharFreq, gCfg.TopN, ks, vs)
    If n > 0 Then
        ReDim arr(1 To n, 1 To 3)
        For i = 1 To n
            arr(i, 1) = i
            arr(i, 2) = ks(i)
            arr(i, 3) = vs(i)
        Next i
        ws.Range("F2").Resize(n, 3).Value = arr
    End If

    ws.Columns(1).ColumnWidth = 8
    ws.Columns(2).ColumnWidth = 18
    ws.Columns(3).ColumnWidth = 10
    ws.Columns(4).ColumnWidth = 14
    ws.Columns(6).ColumnWidth = 8
    ws.Columns(7).ColumnWidth = 10
    ws.Columns(8).ColumnWidth = 10
    ws.Range("A1:H" & (gCfg.TopN + 1)).Font.Name = gCfg.FontName
    ws.Range("A1:H" & (gCfg.TopN + 1)).Font.Size = gCfg.FontSize
End Sub

' ---------- 运行结束时回填耗时/上色统计 ----------

Public Sub OutUpdateTiming(ByVal totalSec As Double, ByVal chartObjs As Long)
    Dim ws As Worksheet, r As Long, lastRow As Long, label As String
    Set ws = SheetSummary()
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    For r = 1 To lastRow
        label = SVal(ws.Cells(r, 1).Value)
        Select Case label
            Case "全流程耗时（秒）"
                ws.Cells(r, 2).Value = Format(totalSec, "0.000")
            Case "上色字符数"
                ws.Cells(r, 2).Value = gColorUsedChars
            Case "上色命中数"
                ws.Cells(r, 2).Value = gColorUsedHits
            Case "上色是否截断"
                If gColorTruncated Then ws.Cells(r, 2).Value = "是" Else ws.Cells(r, 2).Value = "否"
            Case "日志错误数"
                ws.Cells(r, 2).Value = LogCountErrors()
            Case "图表对象数"
                ws.Cells(r, 2).Value = chartObjs
        End Select
    Next r
End Sub
