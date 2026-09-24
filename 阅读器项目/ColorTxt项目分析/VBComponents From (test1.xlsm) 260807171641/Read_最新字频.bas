Attribute VB_Name = "Read_最新字频"
'目录空4
Sub to___字频音333()
    'On Error Resume Next
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
    ' 将字典内容复制到二维数组
    Dim sortedArray() As Variant
    sortedArray = DictTo2DArrayOptimized(Dic)
    ' 调用冒泡排序(按频率降序)
    Call BubbleSort2DArray(sortedArray, 2, True)
    Dim dict As Object
    Set dict = ArrayToDictWithPipe(sortedArray)
    Dim sortedArray2() As Variant
    sortedArray2 = DictTo2DArrayOptimized(dict)
    Erase sortedArray
    Dic.RemoveAll
    dict.RemoveAll
    Set Reg = Nothing
    text = ""
    Text2 = ""
    Dim LL, drr
    LL = Sheets("数据源").Range("A1048576").End(xlUp).row
    drr = Sheets("数据源").Range("A1:B" & LL)
    For i = 1 To UBound(sortedArray2)
        mProcess.Init
        mProcess.Process "词频进度条...", i, UBound(sortedArray2)
        rex2 sortedArray2(i, 1), sortedArray2(i, 2), drr
    Next
    mProcess.Hide
    Set Dic = Nothing
    Set Reg = Nothing
    Erase Words
    MsgBox "词频统计完成" & vbCrLf & "共耗时：" & Format(Timer - time, "0.00") & "秒"
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

' 冒泡排序实现
Sub BubbleSort2DArray(Arr() As Variant, sortCol As Long, Optional ascending As Boolean = True)
    Dim i As Long, j As Long
    Dim tempRow() As Variant
    ReDim tempRow(1 To UBound(Arr, 2))
    For i = LBound(Arr) To UBound(Arr) - 1
        For j = i + 1 To UBound(Arr)
            If (ascending And Arr(i, sortCol) > Arr(j, sortCol)) Or _
            (Not ascending And Arr(i, sortCol) < Arr(j, sortCol)) Then
            ' 交换整行数据
            For Col = 1 To UBound(Arr, 2)
                tempRow(Col) = Arr(i, Col)
                Arr(i, Col) = Arr(j, Col)
                Arr(j, Col) = tempRow(Col)
            Next Col
        End If
    Next j
Next i
End Sub

Function ArrayToDictWithPipe(Arr As Variant) As Object
    Dim dict As Object
    Dim i As Long
    Dim key As Variant
    Dim Value As Variant
    Set dict = CreateObject("Scripting.Dictionary")
    ' 遍历二维数组的每一行
    For i = LBound(Arr, 1) To UBound(Arr, 1)
        key = Arr(i, 2) ' 假设键是二维数组中的第一列
        Value = Arr(i, 1) ' 假设值是二维数组中的第二列
        ' 将键值对添加到字典中
        If dict.exists(key) Then
            ' 如果键已存在，将新值与旧值用“|”连接
            dict(key) = dict(key) & "|" & Value
        Else
            dict.Add key, Value
        End If
    Next i
    Set ArrayToDictWithPipe = dict
End Function

Function DictTo2DArrayOptimized(dict As Object) As Variant
    Dim keys() As Variant
    Dim items() As Variant
    Dim result() As Variant
    Dim i As Long
    ' 获取字典的键和值的数组
    keys = dict.keys
    items = dict.items
    ' 初始化结果数组
    ReDim result(1 To dict.count, 1 To 2)
    ' 填充结果数组
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
        ' .Filters.Add "Word Files", "*.doc;*.docx;*.docm"
        .filters.Add "All Files", "*.*"
        .InitialFileName = ThisWorkbook.Path & "\.xlsx"
        If .Show = -1 Then
            FileSelected = .SelectedItems(1)
        Else
            Exit Function
        End If
    End With
End Function

Sub rex2(n, nn, drr)
    Dim m, mat, mm, L, LL, i, j
    Dim brr
    Dim d2 As Object, Reg As Object
    Set d2 = CreateObject("Scripting.Dictionary")
    Set Reg = CreateObject("VBScript.Regexp")
    L = Sheets("目录").Range("A1048576").End(xlUp).row
    brr = Sheets("目录").Range("A5:A" & L)
    For j = 1 To L - 4
        d2.Add brr(j, 1), 0
    Next
    For i = 1 To UBound(drr)
        sr = drr(i, 1)
        With Reg
            .Global = True
            .Pattern = nn
            If .Test(sr) = False Then
            Else
                Set mat = .Execute(sr)
                For m = 1 To mat.count
                    d2(drr(i, 2)) = d2(drr(i, 2)) + 1
                Next
            End If
        End With
    Next
    With Sheets("目录")
        mm = .[xfd3].End(xlToLeft).Column
        count = 0
        count2 = 0
        ' 遍历字典中的每个键
        For Each key In d2.keys
            ' 如果值为 0，则计数器加 1
            If d2(key) = 0 Then
                count = count + 1
            Else
                count2 = count2 + d2(key)
            End If
        Next key
        .Cells(5, mm + 1).Resize(d2.count, 1) = Application.Transpose(d2.items)
        .Cells(4, mm + 1) = "字数" & count2 / n
        .Cells(3, mm + 1) = "合计:" & count2
        .Cells(2, mm + 1) = "频率:" & n
        .Cells(1, mm + 1) = "总空:" & d2.count & "_" & count
    End With
End Sub


