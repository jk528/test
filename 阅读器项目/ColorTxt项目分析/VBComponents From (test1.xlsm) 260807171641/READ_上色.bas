Attribute VB_Name = "READ_上色"
Sub Color_ONE_TO_SS()
    Dim rng As Range
    Dim cell As Range
    Dim searchTexts As String
    Dim txt As String
    Dim pos As Long
    Set rng = Selection
    searchTexts = "特定词"
    For Each cell In rng
        txt = cell.Value
        pos = InStr(1, txt, searchTexts, vbTextCompare)
        While pos > 0
            mm = mm + 1
            Select Case mm
                Case 1
                    cell.Characters(pos, Len(searchTexts)).Font.Color = RGB(255, 0, 0)
                Case 2
                    cell.Characters(pos, Len(searchTexts)).Font.Color = RGB(0, 255, 0)
                Case 3
                    cell.Characters(pos, Len(searchTexts)).Font.Color = RGB(0, 0, 255)
                Case Else
                    cell.Characters(pos, Len(searchTexts)).Font.Color = RGB(0, 255, 255)
            End Select
            pos = InStr(pos + Len(searchTexts), txt, searchTexts, vbTextCompare)
        Wend
        mm = 0
    Next
End Sub

'Sub Color_ONE_TO_ONE()
'End Sub
Sub Color_SS_TO_SS()
    '每个单元格看作独立的个体
    Dim rng As Range
    Dim cell As Range
    Dim searchTexts
    Dim txt As String
    Dim pos As Long
    Set rng = Selection
    searchTexts = Array("完成", "通过", "合格")
    For Each cell In rng
        If Not IsEmpty(cell.Value) Then
            txt = cell.Value
            For i = LBound(searchTexts) To UBound(searchTexts)
                pos = InStr(1, cell.Value, searchTexts(i), vbTextCompare)
                While pos > 0
                    mm = mm + 1
                    Select Case mm
                        Case 1
                            cell.Characters(pos, Len(searchTexts(i))).Font.Color = RGB(255, 0, 0)
                        Case 2
                            cell.Characters(pos, Len(searchTexts(i))).Font.Color = RGB(0, 255, 0)
                        Case 3
                            cell.Characters(pos, Len(searchTexts(i))).Font.Color = RGB(0, 0, 255)
                        Case Else
                            cell.Characters(pos, Len(searchTexts(i))).Font.Color = RGB(0, 255, 255)
                    End Select
                    pos = InStr(pos + Len(searchTexts(i)), txt, searchTexts(i), vbTextCompare)
                Wend
                mm = 0
            Next
        End If
    Next
End Sub

Sub Color_SS_TO_SS_2()
    '所有单元格看作整体,一个单元格只上色一次
    ' 2025年3月5日21:40:55 增加统计第一次字数所在章节
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    Dim wb As Workbook
    Dim rng As Range
    Dim rng2, err
    Dim cell As Range
    Dim searchText As Range
    Dim searchTexts As Variant
    Dim i As Long, j As Long, irow As Long
    Dim startPos As Integer
    Dim textLength As Integer
    Set wb = ThisWorkbook 'Worksheets("test")
    Application.ScreenUpdating = True
    On Error Resume Next
    Set searchText = Application.InputBox(prompt:="输入文本：", Type:=8)
    Application.ScreenUpdating = False
    If searchText Is Nothing Then
        Exit Sub
    End If
    irow = wb.Sheets("数据源").[a1048576].End(xlUp).row
    ' 定义要搜索的文本数组
    Set rng = wb.Sheets("数据源").Range("A1:A" & irow) ' 替换为你的范围
    rng2 = wb.Sheets("数据源").Range("b1:b" & irow)
    searchTexts = searchText.Value ' 替换为你要查找的文本
    For i = LBound(searchTexts, 1) To UBound(searchTexts, 1)
        For j = LBound(searchTexts, 2) To UBound(searchTexts, 2)
            ' 遍历范围中的每个单元格
            For Each cell In rng
                ' 检查单元格中是否包含搜索文本
                startPos = InStr(cell.Value, searchTexts(i, j))
                mm = mm + 1
                If startPos > 0 Then
                    ' 如果找到匹配项，设置文本颜色
                    textLength = Len(searchTexts(i, j))
                    cell.Characters(startPos, textLength).Font.Color = RGB(255, 0, 0) ' 红色文本
                    If dict.exists(rng2(mm, 1)) Then
                        dict(rng2(mm, 1)) = dict(rng2(mm, 1)) + 1
                    Else
                        dict.Add rng2(mm, 1), 1
                    End If
                    Exit For ' 退出内部循环
                End If
            Next
            mm = 0
        Next
    Next
    With Sheets("目录")
        Q = .[a1048576].End(xlUp).row
        qq = .[xfd1].End(xlToLeft).Column
        err = .Range("a1:a" & Q)
    End With
    For i = 1 To Q
        If dict.exists(err(i, 1)) Then
            err(i, 1) = dict.item(err(i, 1))
        Else
            err(i, 1) = ""
        End If
    Next
    With Sheets("目录")
        .Cells(1, qq + 1).Resize(Q) = err
        .Cells(1, qq + 1) = "字所在目录数:" & dict.count
        .Cells(2, qq + 1) = "第一次出现的字"
    End With
End Sub

Sub Color_SS_TO_ONE()
End Sub

Sub ColorCellsByMultipleTextsOnce()
    Dim cell As Range
    Dim targetRange As Range
    Dim searchTexts As Variant
    Dim i As Integer
    ' 设置目标范围
    Set targetRange = Range("A1:A20") ' 修改为你的数据范围
    ' 设置要查找的多个文本
    searchTexts = Array("完成", "通过", "合格") ' 修改为你的目标文本
    ' 遍历每个单元格
    For Each cell In targetRange
        If Not IsEmpty(cell.Value) Then
            ' 遍历每个目标文本
            For i = LBound(searchTexts) To UBound(searchTexts)
                If InStr(1, cell.Value, searchTexts(i), vbTextCompare) > 0 Then
                    cell.Interior.Color = RGB(0, 255, 0) ' 绿色
                    Exit For ' 找到匹配后退出循环
                Else
                    cell.Interior.ColorIndex = xlNone ' 清除颜色
                End If
            Next i
        End If
    Next cell
End Sub

Sub ColorCellsByMultipleTextsMultipleTimes()
    Dim cell As Range
    Dim targetRange As Range
    Dim searchTexts As Variant
    Dim i As Integer
    ' 设置目标范围
    Set targetRange = Range("A1:A20") ' 修改为你的数据范围
    ' 设置要查找的多个文本
    searchTexts = Array("完成", "通过", "合格") ' 修改为你的目标文本
    ' 遍历每个单元格
    For Each cell In targetRange
        If Not IsEmpty(cell.Value) Then
            ' 遍历每个目标文本
            For i = LBound(searchTexts) To UBound(searchTexts)
                If InStr(1, cell.Value, searchTexts(i), vbTextCompare) > 0 Then
                    cell.Interior.Color = RGB(0, 255, 0) ' 绿色
                End If
            Next i
        End If
    Next cell
End Sub

Sub Color_SS_TO_SS_22()
    '所有单元格看作整体,一个单元格多次上色
    ' 2025年3月5日21:40:55 增加统计第一次字数所在章节
    '2025年5月6日12:50:17 修改多次上色
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    Dim wb As Workbook
    Dim rng As Range
    Dim rng2, err
    Dim cell As Range
    Dim searchText As Range
    Dim searchTexts As Variant
    Dim i As Long, j As Long, irow As Long
    Dim startPos As Integer
    Dim textLength As Integer
    Set wb = ThisWorkbook 'Worksheets("test")
    Application.ScreenUpdating = True
    On Error Resume Next
    Set searchText = Application.InputBox(prompt:="选择要上色的字：", Type:=8)
    Application.ScreenUpdating = False
    If searchText Is Nothing Then
        Exit Sub
    End If
    irow = wb.Sheets("数据源").[a1048576].End(xlUp).row
    ' 定义要搜索的文本数组
    Set rng = wb.Sheets("数据源").Range("A1:A" & irow) ' 替换为你的范围
    rng2 = wb.Sheets("数据源").Range("b1:b" & irow)
    searchTexts = searchText.Value ' 替换为你要查找的文本
    For i = LBound(searchTexts, 1) To UBound(searchTexts, 1)
        For j = LBound(searchTexts, 2) To UBound(searchTexts, 2)
            ' 遍历范围中的每个单元格
            For Each cell In rng
                '                ' 检查单元格中是否包含搜索文本
                '                startPos = InStr(cell.Value, searchTexts(I, j))
                '                mm = mm + 1
                '                If startPos > 0 Then
                '                    ' 如果找到匹配项，设置文本颜色
                '                    textLength = Len(searchTexts(I, j))
                '                    cell.Characters(startPos, textLength).Font.Color = RGB(255, 0, 0) ' 红色文本
                '                    If dict.exists(rng2(mm, 1)) Then
                '                        dict(rng2(mm, 1)) = dict(rng2(mm, 1)) + 1
                '                    Else
                '                        dict.Add rng2(mm, 1), 1
                '                    End If
                '                    Exit For ' 退出内部循环
                '                End If
                txt = cell.Value
                pos = InStr(1, txt, searchTexts(i, j), vbTextCompare)
                mm = mm + 1 '第几个单元格
                While pos > 0
                    mmm = mmm + 1 '第几次上色
                    Select Case mmm
                        Case 1
                            cell.Characters(pos, Len(searchTexts(i, j))).Font.Color = RGB(255, 0, 0)
                        Case 2
                            cell.Characters(pos, Len(searchTexts(i, j))).Font.Color = RGB(0, 255, 0)
                        Case 3
                            cell.Characters(pos, Len(searchTexts(i, j))).Font.Color = RGB(0, 0, 255)
                        Case Else
                            cell.Characters(pos, Len(searchTexts(i, j))).Font.Color = RGB(0, 255, 255)
                    End Select
                    pos = InStr(pos + Len(searchTexts(i, j)), txt, searchTexts(i, j), vbTextCompare)
                    
                    If dict.exists(rng2(mm, 1)) Then
                        dict(rng2(mm, 1)) = dict(rng2(mm, 1)) + 1
                    Else
                        dict.Add rng2(mm, 1), 1
                    End If
                Wend
                mmm = 0
            Next
                mm = 0
        Next
    Next
    With Sheets("目录")
        Q = .[a1048576].End(xlUp).row
        qq = .[xfd1].End(xlToLeft).Column
        err = .Range("a1:a" & Q)
    End With
    For i = 1 To Q
        If dict.exists(err(i, 1)) Then
            err(i, 1) = dict.item(err(i, 1))
        Else
            err(i, 1) = ""
        End If
    Next
    With Sheets("目录")
        .Cells(1, qq + 1).Resize(Q) = err
        .Cells(1, qq + 1) = "字所在目录数:" & dict.count
        .Cells(2, qq + 1) = "第一次出现的字"
    End With
End Sub

