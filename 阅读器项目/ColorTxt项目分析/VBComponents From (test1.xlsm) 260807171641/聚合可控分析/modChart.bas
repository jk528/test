Attribute VB_Name = "modChart"
Option Explicit

'==============================================================================
' Phase 5: 堆叠折线图生成模块
'   功能: 基于"聚合结果"工作表数据生成 xlLineStacked 堆叠折线图
'   优化: 自动检测数据范围 + 图表样式设置 + 标题/轴标签
'==============================================================================

'==============================================================================
' 图表生成主函数
'==============================================================================

'------------------------------------------------------------------------------
' 从"聚合结果"工作表生成堆叠折线图
'   参数: chartTitle - 图表标题 (可选, 默认"字频聚合堆叠折线图")
'   返回: ChartObject 对象引用 (Nothing=失败)
'------------------------------------------------------------------------------
Public Function CreateStackedLineChart(Optional ByVal chartTitle As String = "字频聚合堆叠折线图") As Object
    Dim ws As Worksheet
    Dim chtObj As ChartObject
    Dim cht As Chart
    Dim lastRow As Long, lastCol As Long
    Dim dataRange As Range, catRange As Range
    Dim t0 As Double
    
    t0 = Timer
    Debug.Print "[Phase5] 开始生成堆叠折线图"
    
    ' 1. 获取聚合结果工作表
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("聚合结果")
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        MsgBox "未找到'聚合结果'工作表, 请先执行聚合", vbExclamation, "图表生成失败"
        Set CreateStackedLineChart = Nothing
        Exit Function
    End If
    On Error GoTo 0
    
    ' 2. 检测数据范围
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    
    If lastRow < 2 Or lastCol < 2 Then
        MsgBox "聚合结果数据不足, 无法生成图表", vbExclamation, "图表生成失败"
        Set CreateStackedLineChart = Nothing
        Exit Function
    End If
    
    Debug.Print "[Phase5] 数据范围: " & lastRow & "行 × " & lastCol & "列"
    
    ' 3. 删除旧图表
    Dim oldObj As ChartObject
    For Each oldObj In ws.ChartObjects
        oldObj.Delete
    Next oldObj
    
    ' 4. 创建图表
    ' 数据范围: B1到最后一列最后一行 (含表头作为系列名)
    Set dataRange = ws.Range(ws.Cells(1, 2), ws.Cells(lastRow, lastCol))
    ' 分类轴: A2到A最后一行 (章节标题)
    Set catRange = ws.Range("A2:A" & lastRow)
    
    ' 图表位置: 数据右侧
    Dim chartLeft As Double, chartTop As Double
    chartLeft = ws.Cells(1, lastCol + 2).Left
    chartTop = ws.Cells(1, 1).Top
    
    Set chtObj = ws.ChartObjects.Add(Left:=chartLeft, Top:=chartTop, _
                                     Width:=900, Height:=500)
    Set cht = chtObj.Chart
    
    ' 5. 设置图表类型和数据
    cht.ChartType = xlLineStacked
    cht.SetSourceData Source:=dataRange, PlotBy:=xlColumns
    
    ' 设置分类轴 (X轴标签 = 章节标题)
    cht.SeriesCollection(1).XValues = catRange
    
    ' 6. 图表样式设置
    With cht
        .HasTitle = True
        .ChartTitle.Text = chartTitle
        .ChartTitle.Font.Size = 14
        .ChartTitle.Font.Bold = True
        
        ' X轴
        .Axes(xlCategory).HasTitle = True
        .Axes(xlCategory).AxisTitle.Text = "章节"
        .Axes(xlCategory).AxisTitle.Font.Size = 10
        
        ' Y轴
        .Axes(xlValue).HasTitle = True
        .Axes(xlValue).AxisTitle.Text = "命中次数"
        .Axes(xlValue).AxisTitle.Font.Size = 10
        
        ' 图例
        .HasLegend = True
        .Legend.Position = xlLegendPositionBottom
        .Legend.Font.Size = 8
        
        ' 网格线
        .Axes(xlValue).HasMajorGridlines = True
        .Axes(xlCategory).HasMajorGridlines = False
    End With
    
    ' 7. 系列颜色 (使用渐变色, 避免默认颜色重复)
    Dim s As Long, sCount As Long
    sCount = cht.SeriesCollection.Count
    For s = 1 To sCount
        With cht.SeriesCollection(s)
            ' 线宽
            .Border.Weight = xlThin
            ' 平滑线
            .Smooth = False
        End With
    Next s
    
    Debug.Print "[Phase5] 图表生成完成, 系列数: " & sCount & ", 耗时: " & Format(Timer - t0, "0.00") & "s"
    
    Set CreateStackedLineChart = chtObj
End Function

'------------------------------------------------------------------------------
' 生成图表并导出为图片 (可选)
'   参数: exportPath - 图片保存路径 (空=不导出)
'------------------------------------------------------------------------------
Public Function CreateChartAndExport(Optional ByVal exportPath As String = "", _
                                      Optional ByVal chartTitle As String = "字频聚合堆叠折线图") As Boolean
    Dim chtObj As ChartObject
    
    Set chtObj = CreateStackedLineChart(chartTitle)
    If chtObj Is Nothing Then
        CreateChartAndExport = False
        Exit Function
    End If
    
    ' 导出图片
    If Len(exportPath) > 0 Then
        On Error Resume Next
        chtObj.Chart.Export exportPath, "PNG"
        If Err.Number = 0 Then
            Debug.Print "[Phase5] 图表已导出: " & exportPath
            CreateChartAndExport = True
        Else
            Debug.Print "[Phase5] 图表导出失败: " & Err.Description
            CreateChartAndExport = False
        End If
        On Error GoTo 0
    Else
        CreateChartAndExport = True
    End If
End Function

'==============================================================================
' 辅助: 图表样式优化
'==============================================================================

'------------------------------------------------------------------------------
' 为图表系列设置渐变色
'   色系: 蓝→青→绿→黄→橙→红 循环
'------------------------------------------------------------------------------
Public Sub SetChartGradientColors(ByVal cht As Chart)
    Dim s As Long, sCount As Long
    Dim r As Long, g As Long, b As Long
    
    sCount = cht.SeriesCollection.Count
    
    For s = 1 To sCount
        ' HSL→RGB 渐变 (色相360度均匀分布)
        Dim hue As Double
        hue = (s - 1) * 360 / sCount
        HslToRgb hue, 0.65, 0.5, r, g, b
        
        cht.SeriesCollection(s).Border.Color = RGB(r, g, b)
    Next s
End Sub

' HSL转RGB
Private Sub HslToRgb(ByVal h As Double, ByVal s As Double, ByVal l As Double, _
                     ByRef r As Long, ByRef g As Long, ByRef b As Long)
    Dim c As Double, x As Double, m As Double
    Dim hp As Double
    
    c = (1 - Abs(2 * l - 1)) * s
    hp = h / 60
    x = c * (1 - Abs(hp Mod 2 - 1))
    
    If hp < 1 Then
        r = Round(c * 255): g = Round(x * 255): b = 0
    ElseIf hp < 2 Then
        r = Round(x * 255): g = Round(c * 255): b = 0
    ElseIf hp < 3 Then
        r = 0: g = Round(c * 255): b = Round(x * 255)
    ElseIf hp < 4 Then
        r = 0: g = Round(x * 255): b = Round(c * 255)
    ElseIf hp < 5 Then
        r = Round(x * 255): g = 0: b = Round(c * 255)
    Else
        r = Round(c * 255): g = 0: b = Round(x * 255)
    End If
    
    m = l - c / 2
    r = r + Round(m * 255)
    g = g + Round(m * 255)
    b = b + Round(m * 255)
End Sub
