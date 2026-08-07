Attribute VB_Name = "D_数据源页面"
' 重命名活动工作表为数据源
Sub 重命名活动工作表为数据源()
    Dim ws As Worksheet
    Dim dataSourceWs As Worksheet
    Dim hasDataSource As Boolean

    
    ' 设置活动工作表
    Set ws = ActiveSheet
    
    ' 检查是否存在数据源工作表
    hasDataSource = False
    For Each dataSourceWs In ThisWorkbook.Worksheets
        If dataSourceWs.Name = "数据源" Then
            hasDataSource = True
            Exit For
        End If
    Next dataSourceWs
    
    ' 如果存在数据源工作表，添加后缀
    If hasDataSource Then
       
        dataSourceWs.Name = "数据源_" & Format(Now(), "yyyymmdd_hhmmss")
    End If
    
    ' 重命名活动工作表为数据源
    ws.Name = "数据源"
    
    'MsgBox "活动工作表已成功重命名为 '数据源'", vbInformation
End Sub

