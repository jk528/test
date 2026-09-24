Attribute VB_Name = "进度条测试"
' 进度条 mProcess
Sub Form_Process()
        Dim i As Integer
        mProcess.Init
        For i = 1 To 5000
                mProcess.Process "测试进度条...", i, 5000
        Next i
        mProcess.Hide
        
End Sub
