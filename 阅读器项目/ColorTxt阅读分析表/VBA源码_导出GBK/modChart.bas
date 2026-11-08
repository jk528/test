Attribute VB_Name = "modChart"
Option Explicit

' ============================================================
' 图表：按段堆叠展示各维度命中次数
' 为可读性，图表最多展示前 120 段；完整数据仍在「图表数据」表
' ============================================================

Public Sub ChtBuild()
    Dim wsC As Worksheet, wsD As Worksheet
    Dim rows As Long, cols As Long
    Dim co As ChartObject

    Set wsC = SheetChart()
    Set wsD = SheetChartData()

    On Error Resume Next
    wsC.ChartObjects.Delete
    On Error GoTo 0

    If gParaCount < 1 Or gDimCount < 1 Then
        LogMsg "CHART", "无分段或维度数据，跳过图表", "WARN"
        Exit Sub
    End If

    rows = gParaCount
    If rows > 120 Then rows = 120
    cols = gDimCount + 2

    Set co = wsC.ChartObjects.Add(12, 12, 920, 430)
    With co.Chart
        If gCfg.ChartType = "柱状堆叠" Then
            .ChartType = 52       ' xlColumnStacked
        Else
            .ChartType = 63       ' xlLineStacked
        End If
        .SetSourceData Source:=wsD.Range("A1").Resize(rows + 1, cols)
        .PlotBy = 2               ' xlColumns
        .HasTitle = True
        .ChartTitle.Text = "维度命中分布（前 " & rows & " 段）"
        .ChartTitle.Font.Size = 14
        .ChartTitle.Font.Bold = True
        .HasLegend = True
        .Legend.Position = -4107  ' xlLegendPositionBottom
        .Legend.Font.Size = 9
        .Axes(1).HasTitle = True  ' xlCategory
        .Axes(1).AxisTitle.Text = "段号"
        .Axes(1).TickLabels.Font.Size = 8
        .Axes(2).HasTitle = True  ' xlValue
        .Axes(2).AxisTitle.Text = "命中次数"
    End With

    If rows < gParaCount Then
        LogMsg "CHART", "图表仅展示前 120 段，完整分布见「图表数据」", "WARN"
    End If
    LogMsg "CHART", "图表已重建：" & rows & " 段 × " & gDimCount & " 维度"
End Sub
