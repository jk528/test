Attribute VB_Name = "modConfig"
Option Explicit

' ============================================================
' 配置读取：所有运行参数集中在「配置」工作表，改完重跑即生效
' ============================================================

Public Const CFG_DATA_START As Long = 4
Public Const INPUT_START As Long = 5
Public Const LEX_DATA_START As Long = 3

Public Type ConfigType
    MatchMode As String          ' 词典最大匹配 / 关键词包含 / 正则
    CaseSensitive As Boolean     ' 是否区分大小写
    OverwriteResults As Boolean  ' 是否覆盖已有结果
    EnableDims As Boolean        ' 维度总开关
    EnableColor As Boolean       ' 是否启用上色
    ColorMode As String          ' 逐字符 / 整格 / 关闭
    MaxColorSentences As Long    ' 最多上色句子数
    MaxHitsPerSentence As Long   ' 单句最多着色命中数
    MaxColorChars As Long        ' 全工作簿最多着色字符数
    FontName As String
    FontSize As Long
    ResultStartRow As Long
    TopN As Long
    SummaryTopN As Long
    IgnoreBlank As Boolean
    MaxParagraphChars As Long
    MaxSentenceChars As Long
    MaxTotalChars As Long
    MaxSentences As Long
    ChartType As String          ' 折线堆叠 / 柱状堆叠
    ShowFinishMsg As Boolean
    MinWordLen As Long
End Type

Public gCfg As ConfigType
Public gCfgRaw As Object
Public gDimSwitch As Object

Public Sub LoadConfig()
    Dim ws As Worksheet, lastRow As Long, i As Long, k As String
    Set ws = SheetConfig()
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row

    Set gCfgRaw = CreateObject("Scripting.Dictionary")
    Set gDimSwitch = CreateObject("Scripting.Dictionary")
    gCfgRaw.CompareMode = 1
    gDimSwitch.CompareMode = 1

    For i = CFG_DATA_START To lastRow
        k = Trim(SVal(ws.Cells(i, 1).Value))
        If Len(k) > 0 Then
            gCfgRaw(k) = ws.Cells(i, 2).Value
            If LCase(Left(k, 4)) = "dim_" Then
                gDimSwitch(Mid(k, 5)) = ToBool(ws.Cells(i, 2).Value)
            End If
        End If
    Next i

    With gCfg
        .MatchMode = CfgS("match_mode", "词典最大匹配")
        .CaseSensitive = CfgB("case_sensitive", False)
        .OverwriteResults = CfgB("overwrite_results", True)
        .EnableDims = CfgB("enable_dimensions", True)
        .EnableColor = CfgB("enable_color", True)
        .ColorMode = CfgS("color_mode", "逐字符")
        .MaxColorSentences = CfgL("max_color_sentences", 300)
        .MaxHitsPerSentence = CfgL("max_hits_per_sentence", 20)
        .MaxColorChars = CfgL("max_color_chars", 20000)
        .FontName = CfgS("font_name", "微软雅黑")
        .FontSize = CfgL("font_size", 11)
        .ResultStartRow = CfgL("result_start_row", 2)
        .TopN = CfgL("top_n", 30)
        .SummaryTopN = CfgL("summary_top_n", 5)
        .IgnoreBlank = CfgB("ignore_blank_lines", True)
        .MaxParagraphChars = CfgL("max_paragraph_chars", 2000)
        .MaxSentenceChars = CfgL("max_sentence_chars", 200)
        .MaxTotalChars = CfgL("max_total_chars", 60000)
        .MaxSentences = CfgL("max_sentences", 5000)
        .ChartType = CfgS("chart_type", "折线堆叠")
        .ShowFinishMsg = CfgB("show_finish_msg", False)
        .MinWordLen = CfgL("min_word_len", 2)
    End With

    ValidateConfig
End Sub

Private Function CfgS(ByVal key As String, ByVal dft As String) As String
    Dim s As String
    If gCfgRaw.Exists(key) Then
        s = Trim(SVal(gCfgRaw(key)))
        If Len(s) > 0 Then
            CfgS = s
        Else
            CfgS = dft
        End If
    Else
        CfgS = dft
    End If
End Function

Private Function CfgL(ByVal key As String, ByVal dft As Long) As Long
    If gCfgRaw.Exists(key) Then
        CfgL = ToLong(gCfgRaw(key), dft)
    Else
        CfgL = dft
    End If
End Function

Private Function CfgB(ByVal key As String, ByVal dft As Boolean) As Boolean
    If gCfgRaw.Exists(key) Then
        CfgB = ToBool(gCfgRaw(key))
    Else
        CfgB = dft
    End If
End Function

Private Sub ValidateConfig()
    Dim old As Long

    old = gCfg.MaxColorSentences
    If gCfg.EnableColor And gCfg.MaxColorSentences < 1 Then gCfg.MaxColorSentences = 1
    If gCfg.MaxColorSentences > 5000 Then gCfg.MaxColorSentences = 5000
    If old <> gCfg.MaxColorSentences Then LogMsg "CONFIG", "max_color_sentences 已修正为 " & gCfg.MaxColorSentences, "WARN"

    old = gCfg.MaxHitsPerSentence
    If gCfg.MaxHitsPerSentence < 1 Then gCfg.MaxHitsPerSentence = 1
    If gCfg.MaxHitsPerSentence > 100 Then gCfg.MaxHitsPerSentence = 100
    If old <> gCfg.MaxHitsPerSentence Then LogMsg "CONFIG", "max_hits_per_sentence 已修正为 " & gCfg.MaxHitsPerSentence, "WARN"

    old = gCfg.MaxColorChars
    If gCfg.MaxColorChars < 1 Then gCfg.MaxColorChars = 1
    If gCfg.MaxColorChars > 60000 Then gCfg.MaxColorChars = 60000
    If old <> gCfg.MaxColorChars Then LogMsg "CONFIG", "max_color_chars 已修正为 " & gCfg.MaxColorChars, "WARN"

    old = gCfg.MaxParagraphChars
    If gCfg.MaxParagraphChars < 200 Then gCfg.MaxParagraphChars = 200
    If gCfg.MaxParagraphChars > 30000 Then gCfg.MaxParagraphChars = 30000
    If old <> gCfg.MaxParagraphChars Then LogMsg "CONFIG", "max_paragraph_chars 已修正为 " & gCfg.MaxParagraphChars, "WARN"

    old = gCfg.MaxSentenceChars
    If gCfg.MaxSentenceChars < 30 Then gCfg.MaxSentenceChars = 30
    If gCfg.MaxSentenceChars > gCfg.MaxParagraphChars Then gCfg.MaxSentenceChars = gCfg.MaxParagraphChars
    If old <> gCfg.MaxSentenceChars Then LogMsg "CONFIG", "max_sentence_chars 已修正为 " & gCfg.MaxSentenceChars, "WARN"

    old = gCfg.MaxTotalChars
    If gCfg.MaxTotalChars < 2000 Then gCfg.MaxTotalChars = 2000
    If gCfg.MaxTotalChars > 200000 Then gCfg.MaxTotalChars = 200000
    If old <> gCfg.MaxTotalChars Then LogMsg "CONFIG", "max_total_chars 已修正为 " & gCfg.MaxTotalChars, "WARN"

    old = gCfg.MaxSentences
    If gCfg.MaxSentences < 50 Then gCfg.MaxSentences = 50
    If gCfg.MaxSentences > 20000 Then gCfg.MaxSentences = 20000
    If old <> gCfg.MaxSentences Then LogMsg "CONFIG", "max_sentences 已修正为 " & gCfg.MaxSentences, "WARN"

    old = gCfg.TopN
    If gCfg.TopN < 5 Then gCfg.TopN = 5
    If gCfg.TopN > 100 Then gCfg.TopN = 100
    If old <> gCfg.TopN Then LogMsg "CONFIG", "top_n 已修正为 " & gCfg.TopN, "WARN"

    old = gCfg.SummaryTopN
    If gCfg.SummaryTopN < 2 Then gCfg.SummaryTopN = 2
    If gCfg.SummaryTopN > 20 Then gCfg.SummaryTopN = 20
    If old <> gCfg.SummaryTopN Then LogMsg "CONFIG", "summary_top_n 已修正为 " & gCfg.SummaryTopN, "WARN"

    old = gCfg.ResultStartRow
    If gCfg.ResultStartRow < 2 Then gCfg.ResultStartRow = 2
    If gCfg.ResultStartRow > 10000 Then gCfg.ResultStartRow = 10000
    If old <> gCfg.ResultStartRow Then LogMsg "CONFIG", "result_start_row 已修正为 " & gCfg.ResultStartRow, "WARN"

    old = gCfg.FontSize
    If gCfg.FontSize < 7 Then gCfg.FontSize = 7
    If gCfg.FontSize > 40 Then gCfg.FontSize = 40
    If old <> gCfg.FontSize Then LogMsg "CONFIG", "font_size 已修正为 " & gCfg.FontSize, "WARN"

    old = gCfg.MinWordLen
    If gCfg.MinWordLen < 1 Then gCfg.MinWordLen = 1
    If gCfg.MinWordLen > 10 Then gCfg.MinWordLen = 10
    If old <> gCfg.MinWordLen Then LogMsg "CONFIG", "min_word_len 已修正为 " & gCfg.MinWordLen, "WARN"
End Sub

Public Function DimensionEnabled(ByVal dimName As String) As Boolean
    If Not gCfg.EnableDims Then
        DimensionEnabled = False
        Exit Function
    End If
    If gDimSwitch.Exists(dimName) Then
        DimensionEnabled = gDimSwitch(dimName)
    Else
        DimensionEnabled = True
    End If
End Function

Public Function ConfigSnapshot() As String
    ConfigSnapshot = "match_mode=" & gCfg.MatchMode & _
        "; case=" & CStr(gCfg.CaseSensitive) & _
        "; color=" & gCfg.ColorMode & _
        "; max_color_sent=" & gCfg.MaxColorSentences & _
        "; max_hits/sent=" & gCfg.MaxHitsPerSentence & _
        "; max_color_chars=" & gCfg.MaxColorChars & _
        "; max_total_chars=" & gCfg.MaxTotalChars & _
        "; top_n=" & gCfg.TopN & _
        "; chart=" & gCfg.ChartType
End Function
