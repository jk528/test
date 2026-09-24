Attribute VB_Name = "DLL_自定义ribbon"
' 全局变量声明
Public htcz As Boolean   ' 后台状态标志
Public Sub DDD(control As IRibbonControl, pressed As Boolean)
    On Error GoTo ErrorHandler

    Application.ScreenUpdating = False

    ' 根据控件ID更新对应状态标志
    Select Case control.ID
        Case "C23"
            htcz = pressed
'            MsgBox htcz
    End Select

    Application.ScreenUpdating = True
    Exit Sub

ErrorHandler:
    ' 错误处理
    Application.ScreenUpdating = True
End Sub



Sub AA(control As IRibbonControl)
    '    Application.ScreenUpdating = False
    Select Case control.ID
        Case "b1"
            生成_统合三角
        Case "b2"
            组合排列_范围选取_示例
        Case "b3"
            PC_003_组合.Show 0
        Case "b4"
            TestPermutations2D
        Case "b5"
            分词和缺失分析
        Case "b6"
            RunDemoWithCount
        Case "b7"
            凑数.Show 0
    End Select
    '    Application.ScreenUpdating = True
End Sub

Sub BB(control As IRibbonControl)
    Select Case control.ID
        Case "A1"
            ShowDevelopmentCategory
            '            MsgBox "开发"
        Case "A2"
            ShowReadingCategory
            '            MsgBox "阅读"
        Case "A3"
            ShowAnalysisCategory
            '            MsgBox "分析"
        Case "A4"
            ShowTypingCategory
            '            MsgBox "打字"
        Case "A5"
            ShowCommonCategory
            '            MsgBox "常识"
        Case "A6"
            ShowOtherPages
            '            MsgBox "其他"
        Case "A7"
            目录.Show 0
            '            MsgBox "目录"
        Case "A8"
            InitializeDevelopmentCategory
            '            MsgBox "开发"
        Case "A9"
            InitializeReadingCategory
            '            MsgBox "阅读"
        Case "A10"
            InitializeAnalysisCategory
            '            MsgBox "分析"
        Case "A11"
            InitializeTypingCategory
            '            MsgBox "打字"
        Case "A12"
            InitializeCommonCategory
            '            MsgBox "常识"
            '''        Case "A13"
            '''        ShowOtherPages
            ''''            MsgBox "其他"
    End Select
    Application.ScreenUpdating = True
End Sub

'Callback for C1 onAction
Sub CC(control As IRibbonControl)
'    Application.ScreenUpdating = False
    Select Case control.ID
        Case "C1"
            ComprehensiveDataImport
        Case "C2"
            还原_排序
        Case "C3"
            还原_目录__排序
        Case "C4"
            还原_初始化
        Case "C5"
            正则查询优化
        Case "C6"
            正则后辅助目录优化
        Case "C7"
            正则查询优化2
        Case "C8"
            字频音统计
        Case "C9"
            to___字频音333 '字频数据源
        Case "C10"
            ProcessAndAggregateData '字频图生成
        Case "C11"
            Color_SS_TO_SS_22
        Case "C12"
            to_字频音__重复字
        Case "C13"
            正则替换优化
        Case "C14"
            ExportToTXT
        Case "C15"
            ExportToWord
        Case "C16"
            showpy
        Case "C17"
            epubtotxt
        Case "C18"
            DictionarySortByColumnA
        Case "C19"
            CountConsecutiveNumbers
        Case "C20"
            CountOccurrences
        Case "C21"
        Columns("B:L").Delete Shift:=xlToLeft
         [C2] = "^第[零一二三四五六七八九十百千万亿1234567890]{1,}(章|回)(| |　).*" '目录正则通用
        Case "C22"
        Columns("B:L").Delete Shift:=xlToLeft
         [C2] = "^第.*第[零一二三四五六七八九十百千万亿1234567890]{1,}(章|回)(| |　).*" '目录正则通用2
        Case "C24"
        批量词条查询
        Case "C25"
        FormatSheet
        Case "C26"
        获取文件信息
        Case "C27"
        批量重命名并另存
        Case "C28"
        重命名活动工作表为数据源
    End Select
'    Application.ScreenUpdating = True
End Sub

'Callback for D1 onAction
Sub DD(control As IRibbonControl)
    Application.ScreenUpdating = False
    Select Case control.ID
        Case "D1"
        Case "D2"
        Case "D3"
        Case "D4"
        Case "D5"
        Case "D6"
        Case "D7"
        Case "D8"
    End Select
    Application.ScreenUpdating = True
End Sub
'代码
'-----------------------------------------------------------------------------------------------------------------------------------------------------------------
'-----------------------------------------------------------------------------------------------------------------------------------------------------------------
'多项筛选
Public Sub ManyFilter(control As IRibbonControl)
    On Error Resume Next
    '判断当前单元格所在列是否为筛选区域
    Dim rng As Object: Set rng = Application.Intersect(ActiveSheet.AutoFilter.Range, Selection.Columns(1))
    Dim She As Object: Set She = rng.Parent
    If rng Is Nothing Then If MsgBox("当前单元格不在筛选区域内", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
    '编辑筛选列文本
    With She.Cells(ActiveSheet.AutoFilter.Range.rows(1).row, rng.Column)
        Dim str As String, Num&
        str = "将对单元格 " & "[" & .Address & "]" & .Value & " 所在列进行多项筛选" & vbCrLf & "请选择要筛选的数据"
        Num = rng.Column - ActiveSheet.AutoFilter.Range.Column + 1
    End With
    '获取选区非重复值数组
    Dim edy As Object: Set edy = CreateObject("scripting.dictionary")
    Dim Dic As Object: Set Dic = CreateObject("scripting.dictionary")
    Set edy(0) = Application.InputBox(str, "LELEDY", Type:=8) '选区（可不连续）
    Set edy(1) = edy(0).Parent '选区所在表
    Set edy(2) = Application.Intersect(edy(0), edy(1).UsedRange) '选区是否在已用区域中
    '选区内容存入字典
    If TypeName(edy(0)) = "Range" Then
        If TypeName(edy(2)) = "Nothing" Then
            Dic("") = ""
        Else
            If edy(2).count > 1 Then Set edy(2) = edy(2).SpecialCells(xlCellTypeVisible)  '选区为区域识别为可见
            Dim Tro&, Trt&, Trh&, cnt&, Arr, Var: Arr = Split(edy(2).Address, ",") '将选区处理后的地址转为一维数组
            For Tro = 0 To UBound(Arr)
                With edy(1).Range(Arr(Tro))
                    Var = .Value '每个地址的二维内容数组
                    cnt = .count + IIf(err = 18, "Ctrl+Break ", 0) '每个地址的单元格数量
                    If cnt = 1 Then If IsError(Var) Then Dic(.text) = "" Else Dic(CStr(Var)) = ""
                    If cnt > 1 Then
                        For Trt = 1 To UBound(Var, 1)
                            For Trh = 1 To UBound(Var, 2)
                                If IsError(Var(Trt, Trh)) Then Dic(.Cells(Trt, Trh).text) = "" Else Dic(CStr(Var(Trt, Trh))) = ""
                            Next
                        Next
                    End If
                End With
            Next
        End If
        '多项指定筛选
        With She.AutoFilter.Range
            .AutoFilter Field:=Num, Criteria1:=Dic.keys, Operator:=xlFilterValues
        End With
    End If
    '释放内存
    Set rng = Nothing
    Set She = Nothing
    Set edy = Nothing
    Set Dic = Nothing
    Erase Arr, Var
End Sub
'指定筛选
Public Sub AutoFilter(control As IRibbonControl)
    On Error Resume Next
    '判断当前单元格所在列是否为筛选区域
    Dim rng As Object: Set rng = Application.Intersect(ActiveSheet.AutoFilter.Range, Selection.Columns(1))
    Dim She As Object: Set She = rng.Parent
    If rng Is Nothing Then If MsgBox("当前单元格不在筛选区域内", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
    '获取单元格值
    Dim Dic As Object: Set Dic = CreateObject("scripting.dictionary")
    With Selection.Cells(1)
        If IsError(.Value) Then Dic(.text) = "" Else Dic(CStr(.Value)) = ""
    End With
    '指定筛选
    With She.AutoFilter.Range
        .AutoFilter Field:=rng.Column - ActiveSheet.AutoFilter.Range.Column + 1, Criteria1:=Dic.keys, Operator:=xlFilterValues
    End With
    '释放内存
    Set rng = Nothing
    Set She = Nothing
    Set Dic = Nothing
End Sub
'反向筛选
Public Sub AntiFilter(control As IRibbonControl)
    '判断当前单元格所在列是否为筛选区域
    On Error Resume Next
    Dim rng As Object: Set rng = Application.Intersect(ActiveSheet.AutoFilter.Range, Selection.Columns(1).EntireColumn)
    Dim She As Object: Set She = rng.Parent
    If rng Is Nothing Then If MsgBox("当前单元格不在筛选区域内", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
    '判断当前单元格所在列是否进行过筛选
    Dim Col&: Col = ActiveSheet.AutoFilter.Range.Column
    Dim Rwo&: Rwo = ActiveSheet.AutoFilter.Range.row
    Dim Num&: Num = rng.Column - Col + 1
    With She.AutoFilter.filters(Num)
        If .On Then
            '获取整列数据
            Dim Tro&, Dic As Object: Set Dic = CreateObject("scripting.dictionary")
            Dim Var1: Var1 = She.Range(rng.Address).Value
            For Tro = 2 To UBound(Var1, 1)
                For Trt = 1 To UBound(Var1, 2)
                    If IsError(Var1(Tro, Trt)) Then Dic(She.Cells(Rwo + Tro - 1, rng.Column).text) = "" Else Dic(Trim(CStr(Var1(Tro, Trt)))) = ""
                Next
            Next
            '获取当前选项
            arr1 = .Criteria1
            arr2 = .Criteria2
            err.number = 0: Col = UBound(arr1)
            If err.number Then
                If arr1 = "=" And Len(arr2) = 0 Then Dic.Remove ""
                If arr1 = "=" And Len(arr2) > 0 Then Dic.Remove "": Dic.Remove Mid(arr2, 2)
                If Len(arr1) > 0 And Len(arr2) = 0 Then Dic.Remove Mid(arr1, 2)
            Else
                If Len(arr2) = 0 Then
                    For Tro = 1 To UBound(arr1)
                        Dic.Remove Mid(arr1(Tro), 2, Len(arr1(Tro)))
                    Next
                End If
            End If
        Else
            If MsgBox("当前单元格所在列未进行指定筛选", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
    End With
    '反向筛选
    With She.AutoFilter.Range
        .AutoFilter Field:=Num, Criteria1:=Dic.keys, Operator:=xlFilterValues
    End With
    '释放内存
    Set rng = Nothing: Set She = Nothing: Set Dic = Nothing
    Erase Var1, arr1, arr2
End Sub


