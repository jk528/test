Attribute VB_Name = "modColor"
Option Explicit

' ============================================================
' 单元格内富文本上色
' 现实约束：Characters(start,length).Font.Color 每次调用都有开销，
' 大文本逐字符上色会卡死，因此采用「句子上限 + 单句命中上限 + 总字符预算」三重限制，
' 预算用尽后自动降级为整格浅色底纹。
' ============================================================

Public gColorUsedHits As Long
Public gColorUsedChars As Long
Public gColorTruncated As Boolean
Public gColorSentencesDone As Long
Public gColStatus() As String
Public gColReady As Boolean

Public Sub ColResetBudget()
    gColorUsedHits = 0
    gColorUsedChars = 0
    gColorTruncated = False
    gColorSentencesDone = 0
    gColReady = True
    If gSentCount < 1 Then
        ReDim gColStatus(1 To 1)
    Else
        ReDim gColStatus(1 To gSentCount)
    End If
End Sub

Public Sub ColApplyPreview()
    Dim ws As Worksheet, N As Long, i As Long, j As Long, cell As Range
    Dim st As String, primary As String

    Set ws = SheetPreview()
    N = gSentCount
    If N > gCfg.MaxColorSentences Then N = gCfg.MaxColorSentences
    If N < 1 Then Exit Sub

    If Not gCfg.EnableColor Or gCfg.ColorMode = "关闭" Then
        For i = 1 To N
            ws.Cells(i + 1, 4).Value = "未启用上色"
            gColStatus(i) = "未启用上色"
        Next i
        gColorSentencesDone = N
        Exit Sub
    End If

    For i = 1 To N
        If gCfg.ColorMode = "逐字符" And gColorUsedChars >= gCfg.MaxColorChars Then
            gColorTruncated = True
            For j = i To N
                primary = gPrimary(j)
                If primary <> "" Then
                    If gDimColor.Exists(primary) Then
                        ws.Cells(j + 1, 2).Interior.Color = LightenColor(CLng(gDimColor(primary)), 75)
                    End If
                End If
                st = "降级:整格(总字符预算用尽)"
                ws.Cells(j + 1, 4).Value = st
                gColStatus(j) = st
            Next j
            gColorSentencesDone = N
            Exit For
        End If

        Set cell = ws.Cells(i + 1, 2)
        st = ColApplyCell(cell, gColorMap(i), gPrimary(i))
        ws.Cells(i + 1, 4).Value = st
        gColStatus(i) = st
        If (i Mod 100) = 0 Then DoEvents
    Next i
    If gColorSentencesDone < N Then gColorSentencesDone = N
End Sub

Public Function ColApplyCell(ByRef cell As Range, ByVal colorMap As String, ByVal primaryDim As String) As String
    Dim segs() As String, a() As String, i As Long
    Dim pos As Long, ln As Long, c As Long, used As Long

    On Error Resume Next
    cell.Font.Color = RGB(0, 0, 0)
    On Error GoTo 0

    If gCfg.ColorMode = "整格" Then
        If primaryDim <> "" Then
            If gDimColor.Exists(primaryDim) Then cell.Interior.Color = LightenColor(CLng(gDimColor(primaryDim)), 70)
        End If
        ColApplyCell = "整格"
        Exit Function
    End If

    If Len(colorMap) = 0 Then
        ColApplyCell = "无命中"
        Exit Function
    End If

    segs = Split(colorMap, ";")
    used = 0
    For i = LBound(segs) To UBound(segs)
        If used >= gCfg.MaxHitsPerSentence Then
            ColApplyCell = "上色:" & used & "段(单句命中上限)"
            Exit Function
        End If
        a = Split(segs(i), "|")
        If UBound(a) >= 2 Then
            pos = CLng(a(0))
            ln = CLng(a(1))
            c = CLng(a(2))
            If gColorUsedChars + ln > gCfg.MaxColorChars Then
                gColorTruncated = True
                ColApplyCell = "上色:" & used & "段(总字符预算用尽)"
                Exit Function
            End If
            On Error Resume Next
            cell.Characters(pos, ln).Font.Color = c
            If Err.Number <> 0 Then
                Err.Clear
                ColApplyCell = "上色失败:位置越界"
                Exit Function
            End If
            On Error GoTo 0
            gColorUsedChars = gColorUsedChars + ln
            gColorUsedHits = gColorUsedHits + 1
            used = used + 1
        End If
    Next i

    ColApplyCell = "上色:" & used & "段"
End Function

Public Function ColProbe() As String
    Dim ws As Worksheet, cell As Range, i As Long, s As String
    Set ws = SheetPreview()
    If gSentCount = 0 Then
        ColProbe = "no-sentence"
        Exit Function
    End If
    Set cell = ws.Cells(2, 2)
    s = "len=" & Len(SVal(cell.Value))
    For i = 1 To Len(SVal(cell.Value))
        If cell.Characters(i, 1).Font.Color <> RGB(0, 0, 0) Then
            ColProbe = s & ";pos=" & i & ";rgb=" & cell.Characters(i, 1).Font.Color
            Exit Function
        End If
    Next i
    ColProbe = s & ";no-color"
End Function
