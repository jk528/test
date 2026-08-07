Attribute VB_Name = "READ_聚合生成折线堆叠图"


' ======================================================
' 数据聚合与图表生成工具
' 版本: 1.0
' 功能: 根据用户定义的规则聚合Excel数据并生成折线堆叠图
' ======================================================
'2025年8月26日20:08:08
'2025年8月29日12:52:41
Option Explicit ' 强制变量声明

' 全局变量声明区
Private dataOffset As Integer ' 用于ParseInputStringToArray函数中的偏移量

' ======================================================
' 主过程: 数据聚合与图表生成
' ======================================================
Sub ProcessAndAggregateData()
    ' 声明变量
    Dim inputRange As Range
    Dim dataArray As Variant ' 存储原始数据的二维数组
    Dim resultArray As Variant ' 存储聚合结果的二维数组
    Dim parsedData As Variant ' 存储解析结果的二维数组
    Dim rowCount As Long
    Dim colCount As Long
    Dim colCount2 As Long
    Dim inputString As String
    Dim modValue As Integer
    Dim wsSource As Worksheet

    ' 设置源工作表
    Set wsSource = ActiveSheet

    ' 获取用户选择的数据范围
    On Error Resume Next
    Set inputRange = Application.InputBox(prompt:="选定要聚合的数据范围", Type:=8, Title:="数据范围选择")
    On Error GoTo ErrorHandler

    ' 检查是否取消选择
    If inputRange Is Nothing Then
        MsgBox "未选择数据范围，程序退出。", vbExclamation, "操作取消"
        Exit Sub
    End If

    ' 从Range读取数据到二维数组（提高性能）
    dataArray = inputRange.Value

    ' 获取数据维度
    rowCount = UBound(dataArray, 1)
    colCount = UBound(dataArray, 2)
    If colCount < 255 Then
        colCount2 = colCount
    Else
        colCount2 = 255
    End If
    ' 获取MOD值
    modValue = GetPositiveInteger("请输入MOD值<=255", "MOD值输入", colCount2)
    If modValue <= 0 Then Exit Sub

    ' 检查MOD值是否超过Excel列数限制
    If modValue > 255 Then ' Excel 2007及以上版本的最大列数
        MsgBox "MOD值不能超过 Excel一个图表中的数据系列个数:255", vbExclamation, "输入错误"
        Exit Sub
    End If

    ' 检查数据范围是否大于MOD值
    If colCount <= modValue Then
        MsgBox "数据列数小于或等于MOD值，无需聚合。", vbInformation, "提示"
        Exit Sub
    End If

    ' 获取输入字符串，格式：长度,间距|长度,间距...
    inputString = Application.InputBox(prompt:="请输入聚合规则，格式：长度,间距|长度,间距...\n例如: 20,1|50,2", _
    Type:=2, Title:="聚合规则输入", Default:="20,1|50,2")
    If inputString = "False" Then ' 用户点击了取消
        MsgBox "操作已取消。", vbInformation, "操作取消"
        Exit Sub
    End If

    ' 检查输入参数
    If Not ValidateParameters(inputString, modValue, colCount) Then
        MsgBox "输入参数无效，请检查后重试。", vbCritical, "参数错误"
        Exit Sub
    End If

    ' 解析输入字符串
    parsedData = ParseInputStringToArray(inputString, colCount, modValue)

    ' 检查解析是否成功
    If IsEmpty(parsedData) Then
        MsgBox "输入字符串解析失败，请检查格式是否正确。", vbCritical, "解析错误"
        Exit Sub
    End If

    ' 初始化结果数组
    ReDim resultArray(1 To rowCount, 1 To modValue) As Double

    ' 在内存中执行二维数组的聚合求和操作（高效处理）
    AggregateDataWithArrays dataArray, parsedData, resultArray, rowCount, modValue

    ' 创建新工作表并输出结果
    Dim newSheet As Worksheet
    On Error Resume Next
    Set newSheet = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
    newSheet.Name = "聚合结果 " & "MOD_ _" & modValue & "颗粒度_ _" & inputString
    On Error GoTo ErrorHandler

    ' 一次性将结果数组写入工作表，避免多次单元格操作（提高性能）
    newSheet.Range("B2").Resize(rowCount, modValue).Value = resultArray

    ' 复制原始表头（如果有）
    If inputRange.row > 1 Then
        inputRange.Offset(-3, 0).Resize(1, inputRange.Columns.count).Copy _
        Destination:=newSheet.Range("B1").Resize(1, inputRange.Columns.count)
    End If

    ' 添加目录列标题
    newSheet.Cells(1, 1).Value = "目录"

    ' 如果源数据有目录列，复制目录
    If inputRange.Column > 1 Then
        wsSource.Range(wsSource.Cells(inputRange.row, 1), wsSource.Cells(inputRange.row + rowCount - 1, 1)).Copy _
        Destination:=newSheet.Range("A2").Resize(rowCount, 1)
    End If

    ' 自动调整列宽
    newSheet.Columns.AutoFit

    ' 生成折线堆叠图
    CreateCombinedChartOnSheet newSheet, newSheet.Range(newSheet.Cells(1, 1), newSheet.Cells(rowCount + 1, modValue + 1)), inputString

    MsgBox "数据聚合完成！结果已输出到 '聚合结果' 工作表并生成图表。", vbInformation, "操作完成"

    Exit Sub

ErrorHandler:
    Select Case err.number
        Case 1004
            If InStr(err.Description, "名称") > 0 Then
                MsgBox "无法创建名为'聚合结果'的工作表，该名称已存在。", vbExclamation, "工作表名称冲突"
            Else
                MsgBox "发生错误: " & err.Description, vbCritical, "错误"
            End If
        Case 424
            MsgBox "操作已取消。", vbInformation, "操作取消"
        Case Else
            MsgBox "发生错误: " & err.Description, vbCritical, "错误"
    End Select
End Sub

' ======================================================
' 辅助函数: 获取正整数输入
' ======================================================
Function GetPositiveInteger(prompt As String, Title As String, colCount2 As Long) As Long
    Dim inputValue As Variant
    Dim numericValue As Long

    Do
        inputValue = Application.InputBox(prompt:=prompt, Type:=2, Title:=Title, Default:=colCount2)

        ' 检查用户是否点击了取消
        If inputValue = False Then
            GetPositiveInteger = -1
            Exit Function
        End If

        ' 检查输入是否为正整数
        If IsNumeric(inputValue) Then
            numericValue = CLng(inputValue)
            If numericValue > 0 And numericValue = inputValue Then
                GetPositiveInteger = numericValue
                Exit Function
            Else
                MsgBox "请输入一个正整数！", vbExclamation, "输入错误"
            End If
        Else
            MsgBox "请输入一个有效的数字！", vbExclamation, "输入错误"
        End If
    Loop
End Function

' ======================================================
' 辅助函数: 验证输入参数
' ======================================================
Function ValidateParameters(inputStr As String, modVal As Integer, maxColumns As Long) As Boolean
    ' 检查输入字符串是否为空
    If Len(inputStr) = 0 Then
        Debug.Print "输入字符串为空"
        ValidateParameters = False
        Exit Function
    End If

    ' 检查modValue是否为正数
    If modVal <= 0 Then
        Debug.Print "MOD值必须为正数"
        ValidateParameters = False
        Exit Function
    End If

    ' 检查是否超出Excel列数限制
    If modVal > 255 Then ' Excel一个图表中的数据系列个数:255
        Debug.Print "MOD值不能超过 Excel一个图表中的数据系列个数:255"
        ValidateParameters = False
        Exit Function
    End If

    ' 检查输入字符串格式
    Dim parts() As String
    Dim partDetails() As String
    Dim i As Integer

    parts = Split(inputStr, "|")
    For i = 0 To UBound(parts)
        partDetails = Split(parts(i), ",")
        If UBound(partDetails) < 1 Then
            Debug.Print "输入字符串格式错误: " & parts(i)
            ValidateParameters = False
            Exit Function
        End If

        If Not IsNumeric(partDetails(0)) Or Not IsNumeric(partDetails(1)) Then
            Debug.Print "输入字符串包含非数字字符: " & parts(i)
            ValidateParameters = False
            Exit Function
        End If

        If CInt(partDetails(0)) <= 0 Or CInt(partDetails(1)) <= 0 Then
            Debug.Print "长度和间距必须为正数: " & parts(i)
            ValidateParameters = False
            Exit Function
        End If
    Next i

    ValidateParameters = True
End Function

' ======================================================
' 核心函数: 使用二维数组进行数据聚合
' ======================================================
Sub AggregateDataWithArrays(dataArray As Variant, parsedData As Variant, _
    resultArray As Variant, rowCount As Long, modValue As Integer)
    Dim i As Long, L As Integer, u As Integer, m As Integer, k As Integer
    Dim currentLength As Integer
    Dim currentSpacing As Integer
    Dim cellValue As Double
    Dim sumValue As Double
    Dim aggregateColumnIndex As Integer

    ' 初始化结果数组为0
    For i = 1 To rowCount
        For aggregateColumnIndex = 1 To modValue
            resultArray(i, aggregateColumnIndex) = 0
        Next aggregateColumnIndex
    Next i

    ' 对每一行数据进行处理
    For i = 1 To rowCount
        aggregateColumnIndex = 0
        k = 0

        ' 遍历解析后的数据
        For L = 0 To UBound(parsedData, 1) - dataOffset
            currentLength = parsedData(L, 0) ' 增加的列数目
            currentSpacing = parsedData(L, 1) ' 需要合并求和的列间距

            ' 当前聚合组的长度
            For u = 1 To currentLength
                sumValue = 0 ' 重置当前行的和

                ' 当前聚合组的间距
                For m = 1 To currentSpacing
                    k = k + 1

                    ' 确保不越界
                    If k <= UBound(dataArray, 2) Then
                        ' 检查单元格是否为数值
                        If IsNumeric(dataArray(i, k)) Then
                            cellValue = CDbl(dataArray(i, k)) ' 转换为Double以保持精度
                            sumValue = sumValue + cellValue
                        End If
                    End If
                Next m

                ' 确保聚合列索引不越界
                If aggregateColumnIndex < modValue Then
                    aggregateColumnIndex = aggregateColumnIndex + 1
                    resultArray(i, aggregateColumnIndex) = sumValue
                End If
            Next u
        Next L
    Next i
End Sub

' ======================================================
' 辅助函数: 解析输入字符串并返回二维数组
' ======================================================
Function ParseInputStringToArray(inputStr As String, totalColumns As Long, modValue As Integer) As Variant
    ' 检查输入字符串是否为空
    If Len(inputStr) = 0 Then
        ParseInputStringToArray = Empty
        Exit Function
    End If

    Dim parts() As String
    Dim result() As Variant
    Dim i As Integer, totalColumns2 As Integer, totalColumns3 As Integer
    Dim remainder As Integer, loopCount As Integer, remainingColumns As Integer, granularity As Integer

    parts = Split(inputStr, "|")

    ' 初始化二维数组，留出额外空间处理余数
    ReDim result(0 To UBound(parts) + 2, 0 To 2)

    ' 解析每一部分
    For i = 0 To UBound(parts)
        Dim partDetails() As String
        partDetails = Split(parts(i), ",")

        ' 检查格式和数值有效性
        If Not ParsePartDetails(partDetails, result, i) Then
            ParseInputStringToArray = Empty
            Exit Function
        End If
    Next i

    ' 计算已使用列数
    totalColumns2 = 0 ' 实际使用的列数
    totalColumns3 = 0 ' 聚合后的列数
    For i = 0 To UBound(parts)
        totalColumns3 = totalColumns3 + result(i, 0)
        totalColumns2 = totalColumns2 + result(i, 2)
    Next i

    ' 检查列数是否超出限制
    If totalColumns2 > totalColumns Or totalColumns3 > modValue Then
        Debug.Print "已使用列数超出限制"
        ParseInputStringToArray = Empty
        Exit Function
    End If

    ' 计算剩余列和颗粒度
    remainingColumns = (totalColumns - totalColumns2)
    granularity = (modValue - totalColumns3)

    ' 如果没有剩余列和颗粒度
    If remainingColumns = 0 And granularity = 0 Then
        dataOffset = 2
        GoTo ParseComplete
    End If

    ' 如果颗粒度为0但剩余列不为0，则无法处理
    If granularity = 0 And remainingColumns > 0 Then
        Debug.Print "颗粒度为0，无法处理剩余列"
        ParseInputStringToArray = Empty
        Exit Function
    End If

    ' 处理余数
    remainder = remainingColumns Mod granularity
    loopCount = remainingColumns \ granularity

    If remainder = 0 Then
        dataOffset = 1
        result(UBound(result, 1) - 1, 0) = granularity
        result(UBound(result, 1) - 1, 1) = loopCount
        result(UBound(result, 1) - 1, 2) = loopCount * granularity
    Else
        dataOffset = 0
        result(UBound(result, 1), 0) = remainder
        result(UBound(result, 1), 1) = loopCount + 1
        result(UBound(result, 1), 2) = (loopCount + 1) * remainder
        result(UBound(result, 1) - 1, 0) = granularity - remainder
        result(UBound(result, 1) - 1, 1) = loopCount
        result(UBound(result, 1) - 1, 2) = (granularity - remainder) * loopCount
    End If

ParseComplete:
    ParseInputStringToArray = result
End Function

' ======================================================
' 辅助函数: 解析单个部分的详细信息
' ======================================================
Function ParsePartDetails(partDetails() As String, result() As Variant, Index As Integer) As Boolean
    ' 检查是否有足够的参数
    If UBound(partDetails) < 1 Then
        Debug.Print "输入字符串格式错误: " & partDetails(0)
        ParsePartDetails = False
        Exit Function
    End If

    ' 检查参数是否为数字
    If Not IsNumeric(partDetails(0)) Or Not IsNumeric(partDetails(1)) Then
        Debug.Print "输入字符串包含非数字字符: " & partDetails(0) & "," & partDetails(1)
        ParsePartDetails = False
        Exit Function
    End If

    Dim Length As Integer
    Dim spacing As Integer

    Length = CInt(partDetails(0))
    spacing = CInt(partDetails(1))

    ' 检查参数是否为正数
    If Length <= 0 Or spacing <= 0 Then
        Debug.Print "长度和间距必须为正数: " & partDetails(0) & "," & partDetails(1)
        ParsePartDetails = False
        Exit Function
    End If

    ' 存储到二维数组中
    result(Index, 0) = Length
    result(Index, 1) = spacing
    result(Index, 2) = Length * spacing

    ParsePartDetails = True
End Function

' ======================================================
' 辅助函数: 在指定工作表上创建组合图表
' ======================================================
Sub CreateCombinedChartOnSheet(ws As Worksheet, dataRange As Range, inputString As String)
    ' 清除之前可能存在的图表
    On Error Resume Next
    ws.ChartObjects.Delete
    On Error GoTo 0

    ' 创建图表对象
    Dim chartObj As ChartObject
    Set chartObj = ws.ChartObjects.Add(Left:=0, Top:=0, Width:=1400, Height:=900)

    With chartObj.Chart
        ' 设置图表类型为堆叠折线图
        .ChartType = xlLineStacked

        ' 设置数据源范围
        .SetSourceData Source:=dataRange

        ' 按列绘制数据
        .PlotBy = xlColumns

        ' 设置图表标题
        .HasTitle = True
        .ChartTitle.text = "聚合数据堆叠图: " & inputString
        .ChartTitle.Font.Size = 14
        .ChartTitle.Font.Bold = True

        ' 设置坐标轴标题
        .Axes(xlCategory, xlPrimary).HasTitle = True
        .Axes(xlCategory, xlPrimary).AxisTitle.text = "目录"
        .Axes(xlCategory, xlPrimary).AxisTitle.Font.Size = 12

        .Axes(xlValue, xlPrimary).HasTitle = True
        .Axes(xlValue, xlPrimary).AxisTitle.text = "词量"
        .Axes(xlValue, xlPrimary).AxisTitle.Font.Size = 12

        ' 设置图例位置在底部
        .HasLegend = True
        .Legend.Position = xlLegendPositionBottom
        .Legend.Font.Size = 10

        ' 设置数据标签（可选）
        '.SeriesCollection(1).HasDataLabels = True

        '        ' 设置网格线
        '        .Axes(xlValue, xlPrimary).HasMajorGridlines = True
        '        .Axes(xlValue, xlPrimary).MajorGridlines.LineStyle = xlContinuous
    End With
End Sub

