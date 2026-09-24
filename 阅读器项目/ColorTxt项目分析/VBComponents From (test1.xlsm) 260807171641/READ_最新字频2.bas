Attribute VB_Name = "READ_最新字频2"
Sub to_字频音__重复字()
    Dim wordapp As Object, worddoc As Object
    Dim wdFile As String, Dic As Object
    Dim Words(), Text2 As String, Word As Variant
    Dim text As String, n As Long, nn As Long
    Dim Reg As Object, time As Single
    time = Timer
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False
    Set Dic = CreateObject("Scripting.Dictionary")
    wdFile = FileSelected
    If wdFile = "" Then Exit Sub
    Set wordapp = CreateObject("Word.Application")
    wordapp.Visible = False
    Set worddoc = wordapp.Documents.Open(wdFile)
    text = worddoc.Range.text
    Set Reg = CreateObject("vbscript.regexp")
    With Reg
        .Global = True
        .Pattern = "[^\u4e00-\u9fa5]"
        Text2 = .Replace(text, "")
    End With
    worddoc.Close False
    wordapp.Quit
    Set worddoc = Nothing
    Set wordapp = Nothing
    n = Len(Text2)
    ReDim Words(1 To n)
    For nn = 1 To n
        Words(nn) = Mid(Text2, nn, 1)
        Dic(Words(nn)) = Dic(Words(nn)) + 1
    Next
    Erase Words
    Dim sortedArray() As Variant
    sortedArray = DictTo2DArrayOptimized(Dic)
    Call BubbleSort2DArray(sortedArray, 2, True)
    Dic.RemoveAll
    Set Reg = Nothing
    text = ""
    Text2 = ""
    Dim LL, drr
    LL = Sheets("数据源").Range("A1048576").End(xlUp).row
    drr = Sheets("数据源").Range("A1:B" & LL)
    For i = 1 To UBound(sortedArray)
        mProcess.Init
        mProcess.Process "词频进度条...", i, UBound(sortedArray)
        rex2 sortedArray(i, 1), sortedArray(i, 2), drr
    Next
    mProcess.Hide
    With Sheets("目录2")
    .[a1] = "排序" '排除分列错位
    .Range("A:A").TextToColumns Other:=True, OtherChar:="|"
    .[a1] = "排序"
    .[B1] = "查找字"
    .[c1] = "语句"
    .[d1] = "目录"
    End With
    Set Dic = Nothing
    Set Reg = Nothing
    Erase Words
    MsgBox "词频统计完成" & vbCrLf & "共耗时：" & Format(Timer - time, "0.00") & "秒"
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

Sub BubbleSort2DArray(Arr() As Variant, sortCol As Long, Optional ascending As Boolean = True)
    Dim i As Long, j As Long
    Dim tempRow() As Variant
    ReDim tempRow(1 To UBound(Arr, 2))
    For i = LBound(Arr) To UBound(Arr) - 1
        For j = i + 1 To UBound(Arr)
            If (ascending And Arr(i, sortCol) > Arr(j, sortCol)) Or _
            (Not ascending And Arr(i, sortCol) < Arr(j, sortCol)) Then
            For Col = 1 To UBound(Arr, 2)
                tempRow(Col) = Arr(i, Col)
                Arr(i, Col) = Arr(j, Col)
                Arr(j, Col) = tempRow(Col)
            Next Col
        End If
    Next j
Next i
End Sub

Function DictTo2DArrayOptimized(dict As Object) As Variant
    Dim keys() As Variant
    Dim items() As Variant
    Dim result() As Variant
    Dim i As Long
    keys = dict.keys
    items = dict.items
    ReDim result(1 To dict.count, 1 To 2)
    For i = 1 To dict.count
        result(i, 1) = keys(i - 1)
        result(i, 2) = items(i - 1)
    Next i
    DictTo2DArrayOptimized = result
End Function

Function FileSelected()
    With Application.FileDialog(msoFileDialogFilePicker)
        .Title = "请选择Word文件"
        .AllowMultiSelect = False
        .filters.Clear
        .filters.Add "文本文件", "*.txt"
        '.filters.Add "All Files", "*.*"
        .InitialFileName = ThisWorkbook.Path & "\.xlsx"
        If .Show = -1 Then
            FileSelected = .SelectedItems(1)
        Else
            Exit Function
        End If
    End With
End Function

Sub rex2(n, nn, drr)
    On Error Resume Next
    Dim m, mat, mm, L, LL, i, j, k
    Dim brr
    Dim d2 As Object, Reg As Object, d3 As Object
    Set d2 = CreateObject("Scripting.Dictionary")
    Set d3 = CreateObject("Scripting.Dictionary")
    Set Reg = CreateObject("VBScript.Regexp")
    For i = 1 To UBound(drr)
    k = k + 1
        sr = drr(i, 1)
        With Reg
            .Global = True
            .Pattern = n
            If .Test(sr) = False Then
            Else
                Set mat = .Execute(sr)
                For m = 1 To mat.count
                    nn = nn - 1
                    If m > 1 Then
                        d3.Add k & "|" & n & "|" & drr(i, 1), drr(i, 2)
                    End If
                    If nn = 0 Then
                        GoTo Test
                    End If
                Next
            End If
        End With
    Next
Test:
    With Sheets("重复字")
        mm = .Range("A1048576").End(xlUp).row + 1
       
        .Cells(mm, 1).Resize(d3.count, 1) = Application.Transpose(d3.keys)
        
        .Cells(mm, 4).Resize(d3.count, 1) = Application.Transpose(d3.items)
    End With
End Sub


