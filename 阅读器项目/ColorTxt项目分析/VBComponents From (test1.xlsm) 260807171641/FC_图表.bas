Attribute VB_Name = "FC_图表"
Option Explicit

Sub ProductionCharts()
    Dim R As Integer, rr, i
    Dim rng As Range
    Dim MyChart As ChartObject
    On Error Resume Next
    rr = Sheet10.Range("b2:b104")
    For i = 1 To 103
    
    
    With Sheet3
       .ChartObjects("MyChart").Delete
        R = .Cells(.rows.count, 1).End(xlUp).row
        Set rng = .Range(.Cells(2, 1), .Cells(R, 6))
        Set MyChart = .ChartObjects.Add(120, 40, 1200, 500)
        MyChart.Name = "MyChart"
        With MyChart.Chart
            .ChartType = rr(i, 1) '52 53 55 56,(())62
            .SetSourceData Source:=rng, PlotBy:=xlColumns
          '  .ApplyDataLabels ShowValue:=True
            .HasTitle = True
            With .ChartTitle
                .text = "图表制作示例"
                .Font.Name = "宋体"
                .Font.Size = 14
            End With
        End With
    End With
    Set rng = Nothing
    Set MyChart = Nothing
  
    Next
End Sub
