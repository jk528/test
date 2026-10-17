Attribute VB_Name = "查找一件套合集"
Dim findValue As Range
Dim n
Sub 查找()
Attribute 查找.VB_ProcData.VB_Invoke_Func = " \n14"
    On Error Resume Next
    n = ActiveCell
    If ActiveSheet.Name = "数据源" Then
        Sheets("快捷键后台").Range("E" & (Sheets("快捷键后台").Range("E1048576").End(xlUp).row + 1)).Value = ActiveSheet.Name
        Sheets("快捷键后台").Range("f" & (Sheets("快捷键后台").Range("E1048576").End(xlUp).row)).Value = Now
        Sheets("快捷键后台").Range("g" & (Sheets("快捷键后台").Range("E1048576").End(xlUp).row)).Value = n
    Else
        Sheets("快捷键后台").Range("a" & (Sheets("快捷键后台").Range("a1048576").End(xlUp).row + 1)).Value = ActiveSheet.Name
        Sheets("快捷键后台").Range("b" & (Sheets("快捷键后台").Range("A1048576").End(xlUp).row)).Value = Now
        Sheets("快捷键后台").Range("c" & (Sheets("快捷键后台").Range("A1048576").End(xlUp).row)).Value = n
    End If
    Set findValue = Worksheets("数据源").Columns("A").find(what:=n)
    Worksheets("数据源").Select
    Range(Worksheets("数据源").Columns("a").find(what:=n).Address).Activate
End Sub

Sub 下查()
Attribute 下查.VB_ProcData.VB_Invoke_Func = " \n14"
    On Error Resume Next
    Set findValue = Worksheets("数据源").Columns("A").FindNext(After:=findValue)
    Range(findValue.Address).Activate
End Sub

Sub 上查()
Attribute 上查.VB_ProcData.VB_Invoke_Func = " \n14"
    On Error Resume Next
    Set findValue = Worksheets("数据源").Columns("A").FindPrevious(After:=findValue)
    Range(findValue.Address).Activate
End Sub

Sub 返回()
Attribute 返回.VB_ProcData.VB_Invoke_Func = " \n14"
    On Error Resume Next
    Sheets(Sheets("快捷键后台").Range("a" & (Sheets("快捷键后台").Range("a1048576").End(xlUp).row)).Value).Select
    Sheets("快捷键后台").Range("d" & (Sheets("快捷键后台").Range("A1048576").End(xlUp).row)).Value = DateDiff("s", Sheets("快捷键后台").Range("b" & (Sheets("快捷键后台").Range("a1048576").End(xlUp).row)).Value, Now) & "秒"
End Sub

