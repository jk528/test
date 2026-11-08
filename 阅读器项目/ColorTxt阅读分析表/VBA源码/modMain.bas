Attribute VB_Name = "modMain"
Option Explicit

' ============================================================
' 一键入口：RunFullAnalysis
' 流程：读配置 -> 读词表 -> 读正文 -> 分句 -> 匹配 -> 输出 -> 上色 -> 图表
' ============================================================

Public Sub RunFullAnalysis()
    Dim t0 As Double, tPhase As Double, tSec As Double
    Dim raw As String, chartN As Long

    t0 = Timer
    On Error GoTo EH

    AppBusy True

    LoadConfig
    If gCfg.OverwriteResults Then LogClear
    LogMsg "START", "===== 一键分析开始 ====="
    LogMsg "CONFIG", "配置摘要: " & ConfigSnapshot()

    tPhase = Timer
    LexLoad
    If gRuleCount = 0 Then
        Err.Raise vbObjectError + 1001, , "词表没有可用关键词，请检查「词表」的启用列与维度开关"
    End If

    tPhase = Timer
    raw = TxtFromSheet()
    TxtSplitAll raw
    LogMsg "SPLIT", gParaCount & " 段 / " & gSentCount & " 句 / " & gTotalChars & " 字 / 汉字 " & gCJKChars & _
        "，耗时 " & Format(Timer - tPhase, "0.000") & "s"
    If gSentCount = 0 Then
        Err.Raise vbObjectError + 1002, , "正文输入为空，请在「正文输入」A5 起粘贴文本"
    End If
    If gTruncated Then LogMsg "SPLIT", "已因 max_total_chars 上限截断正文", "WARN"
    If gSentLimitHit Then LogMsg "SPLIT", "已达到 max_sentences 上限，后续句子未处理", "WARN"

    tPhase = Timer
    AnaRun
    LogMsg "ANALYZE", "命中句 " & gHitSentenceCount & " / " & gSentCount & "，总命中 " & gTotalHits & _
        " 次，耗时 " & Format(gAnalyzeSeconds, "0.000") & "s"

    tPhase = Timer
    OutWritePreviewText
    LogMsg "PREVIEW", "上色预览文本已写入，耗时 " & Format(Timer - tPhase, "0.000") & "s"

    tPhase = Timer
    ColResetBudget
    ColApplyPreview
    LogMsg "COLOR", "逐字符上色 " & gColorSentencesDone & " 句 / " & gColorUsedHits & " 命中 / " & _
        gColorUsedChars & " 字符，耗时 " & Format(Timer - tPhase, "0.000") & "s"
    If gColorTruncated Then LogMsg "COLOR", "上色预算用尽，部分句子已降级为整格底纹", "WARN"

    tPhase = Timer
    OutWriteAll
    LogMsg "OUTPUT", "逐句结果/汇总/图表数据/词频Top 已写入，耗时 " & Format(Timer - tPhase, "0.000") & "s"

    tPhase = Timer
    ChtBuild
    chartN = SheetChart().ChartObjects.Count
    LogMsg "CHART", "图表构建耗时 " & Format(Timer - tPhase, "0.000") & "s"

    tSec = Timer - t0
    OutUpdateTiming tSec, chartN
    LogMsg "DONE", "全流程完成，耗时 " & Format(tSec, "0.000") & " 秒；结果 " & gSentCount & " 行；上色字符 " & gColorUsedChars

    AppBusy False
    SetStatus "分析完成： " & gSentCount & " 句 / " & gTotalHits & " 命中 / " & Format(tSec, "0.000") & " 秒"
    If gCfg.ShowFinishMsg Then
        MsgBox "分析完成。" & vbCrLf & "句子数：" & gSentCount & vbCrLf & _
            "命中次数：" & gTotalHits & vbCrLf & "总耗时：" & Format(tSec, "0.000") & " 秒", vbInformation
    End If
    Exit Sub

EH:
    AppBusy False
    SetStatus "分析失败，详情见「运行日志」"
    LogMsg "ERROR", Err.Number & " / " & Err.Description, "ERROR"
    If gCfg.ShowFinishMsg Then
        MsgBox "分析失败：" & Err.Description & vbCrLf & "详情见「运行日志」工作表。", vbExclamation
    End If
End Sub

' ---------- 辅助按钮 ----------

Public Sub MainLoadSample()
    Dim wsS As Worksheet, wsI As Worksheet
    Dim i As Long, lastS As Long, lastI As Long
    Set wsS = SheetSample()
    Set wsI = SheetInput()
    lastS = wsS.Cells(wsS.Rows.Count, 1).End(xlUp).Row
    lastI = wsI.Cells(wsI.Rows.Count, 1).End(xlUp).Row
    If lastI >= INPUT_START Then
        wsI.Range("A" & INPUT_START & ":A" & lastI).ClearContents
    End If
    If lastS < 2 Then Exit Sub
    For i = 2 To lastS
        wsI.Cells(INPUT_START + i - 2, 1).Value = wsS.Cells(i, 1).Value
    Next i
    LogMsg "SAMPLE", "示例文本已载入「正文输入」A" & INPUT_START & " 起"
    SetStatus "示例已载入，点击「一键分析」"
End Sub

Public Sub MainClearResults()
    If MsgBox("确认清空所有分析结果（逐句结果/汇总/图表/预览/词频）？配置与词表不会被清空。", _
        vbYesNo + vbQuestion, "清空结果") <> vbYes Then Exit Sub
    ClearSheet SheetResults()
    ClearSheet SheetSummary()
    ClearSheet SheetChartData()
    ClearSheet SheetPreview()
    ClearSheet SheetTop()
    On Error Resume Next
    SheetChart().ChartObjects.Delete
    On Error GoTo 0
    LogMsg "CLEAR", "分析结果已清空"
    SetStatus "结果已清空"
End Sub

Public Sub MainClearInput()
    Dim ws As Worksheet, lastRow As Long
    If MsgBox("确认清空「正文输入」中的文本？", vbYesNo + vbQuestion, "清空正文") <> vbYes Then Exit Sub
    Set ws = SheetInput()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow >= INPUT_START Then
        ws.Range("A" & INPUT_START & ":A" & lastRow).ClearContents
    End If
    LogMsg "CLEAR", "正文输入已清空"
    SetStatus "正文已清空"
End Sub

' ---------- 自检（供自动化验证调用） ----------

Public Function MainSelfCheck() As String
    Dim s As String, logRows As Long, hasFormula As Boolean
    On Error Resume Next
    s = "sheets=" & ThisWorkbook.Worksheets.Count
    s = s & "|sent=" & gSentCount
    s = s & "|resultRows=" & OutCountResultRows()
    s = s & "|hits=" & gTotalHits
    s = s & "|coloredChars=" & gColorUsedChars
    s = s & "|coloredHits=" & gColorUsedHits
    s = s & "|chartObjects=" & SheetChart().ChartObjects.Count
    logRows = SheetLog().Cells(SheetLog().Rows.Count, 1).End(xlUp).Row
    s = s & "|logRows=" & logRows
    hasFormula = False
    If SheetResults().UsedRange.Rows.Count > 0 Then
        hasFormula = SheetResults().UsedRange.HasFormula
    End If
    s = s & "|resultsHasFormula=" & hasFormula
    s = s & "|" & ColProbe()
    MainSelfCheck = s
    On Error GoTo 0
End Function
