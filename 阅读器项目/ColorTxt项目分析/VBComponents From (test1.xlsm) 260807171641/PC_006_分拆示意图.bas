Attribute VB_Name = "PC_006_分拆示意图"
' 使用示例2025年8月26日20:11:43
'p(10)其中分割线是9,可以通过C n m ___C 2 9  得到 9*8/2/1=36,10的项数3和C 2 9是一样的运算.
Sub RunDemoWithCount()
    On Error GoTo ErrorHandler
    ' 增加input输入
    Dim inputStr As Integer
    inputStr = InputBox("分析求和示意图:不能大于15", "输入行数", "10")
    ' 验证输入
    If Not IsNumeric(inputStr) Then
'        MsgBox "输入的不是有效数字，请重新运行程序。", vbExclamation
        Exit Sub
    End If
    DemoPartitionStatisticsWithCount inputStr
ErrorHandler:
End Sub

Sub DemoPartitionStatisticsWithCount(n As Integer)
    ' 创建新的工作表用于显示结果
    Dim ws As Worksheet, Arr
    Set ws = ThisWorkbook.Sheets.Add
    ws.Name = "PartitionStats" & Sheets.count
    ' 生成n的所有无序分拆 (干)
    Dim partitions As Collection
    Set partitions = GetAllPartitions(n)
    ' 生成n的所有有序分拆 (支)
    Dim orderedPartitions As Collection
    Set orderedPartitions = New Collection
    GenerateOrderedPartitions "", n, orderedPartitions
    ' 预计算所有有序分拆的频率模式和项数
    Dim orderedFrequencies As Object
    Set orderedFrequencies = CreateObject("Scripting.Dictionary")
    Dim j As Integer
    ReDim Arr(1 To partitions.count, 1 To 4)
    For j = 1 To orderedPartitions.count
        Dim currentOrdered As String
        currentOrdered = orderedPartitions(j)
        Dim freqKey As String
        freqKey = GetFrequencyKey(currentOrdered)
        ' 组合频率键和项数作为唯一键
        Dim itemFreqKey As String
        Dim itemCount As Integer
        itemCount = UBound(Split(currentOrdered, "+")) + 1
        itemFreqKey = freqKey & "|" & itemCount
        If Not orderedFrequencies.exists(itemFreqKey) Then
            orderedFrequencies.Add itemFreqKey, New Collection
        End If
        orderedFrequencies(itemFreqKey).Add currentOrdered
    Next j
    ' 输出表头
    ws.Range("A1").Value = "干"
    ws.Range("B1").Value = "项数"
    ws.Range("C1").Value = "词频"
    ws.Range("D1").Value = "支"
    Dim i As Integer
    ' 遍历每个无序分拆 (干)
    For i = 1 To partitions.count
        Dim currentPartition As String
        currentPartition = partitions(i)
        ' 计算当前无序分拆的项数
        Dim dryItemCount As Integer
        dryItemCount = UBound(Split(currentPartition, "+")) + 1
        ' 获取当前无序分拆的频率键
        Dim dryFreqKey As String
        dryFreqKey = GetFrequencyKey(currentPartition)
        ' 组合频率键和项数作为唯一键
        '        Dim itemFreqKey As String
        itemFreqKey = dryFreqKey & "|" & dryItemCount
        ' 查找匹配的有序分拆
        Dim matchCount As Integer
        Dim matchedOrdered As String
        matchedOrdered = ""
        If orderedFrequencies.exists(itemFreqKey) Then
            Dim matchedCollection As Collection
            Set matchedCollection = orderedFrequencies(itemFreqKey)
            matchCount = matchedCollection.count
            Dim k As Integer
            For k = 1 To matchedCollection.count
                If matchedOrdered <> "" Then
                    matchedOrdered = matchedOrdered & ", " & matchedCollection(k)
                Else
                    matchedOrdered = matchedCollection(k)
                End If
            Next k
        Else
            matchCount = 0
        End If
        ' 输出结果到工作表
        Arr(i, 1) = currentPartition
        Arr(i, 2) = dryItemCount
        Arr(i, 3) = matchCount
        Arr(i, 4) = matchedOrdered
    Next i
    Arr = Sort2DArray(Arr, 2, False)
    [a2].Resize(UBound(Arr), UBound(Arr, 2)) = Arr
    ' 格式化表格
    With ws.Range("A1:D" & (partitions.count + 1))
        .Borders.LineStyle = xlContinuous
        .EntireColumn.AutoFit
    End With
End Sub

' 生成n的所有有序分拆
' 参数:
'   current: 当前已生成的部分分拆
'   remaining: 剩余需要分拆的数值
'   results: 存储所有有序分拆结果的集合
Sub GenerateOrderedPartitions(current As String, remaining As Integer, ByRef results As Collection)
    ' 递归终止条件：当剩余值为0时，将当前分拆添加到结果集中
    If remaining = 0 Then
        If current <> "" Then
            results.Add current
        End If
        Exit Sub
    End If
    ' 递归生成所有可能的有序分拆
    Dim i As Integer
    For i = 1 To remaining
        Dim newPartition As String
        If current = "" Then
            newPartition = i
        Else
            newPartition = current & "+" & i
        End If
        ' 递归调用，继续分拆剩余值
        GenerateOrderedPartitions newPartition, remaining - i, results
    Next i
End Sub

' 获取所有无序分拆
' 参数:
'   n: 需要分拆的整数
' 返回值: 包含所有无序分拆的集合
Function GetAllPartitions(n As Integer) As Collection
    Dim partitions As Collection
    Set partitions = New Collection
    ' 调用递归函数生成分拆
    GeneratePartitions n, n, "", partitions
    Set GetAllPartitions = partitions
End Function

' 递归生成无序分拆
' 参数:
'   n: 需要分拆的整数
'   max: 当前允许的最大分拆项
'   current: 当前已生成的部分分拆
'   partitions: 存储所有无序分拆结果的集合
Sub GeneratePartitions(n As Integer, max As Integer, current As String, ByRef partitions As Collection)
    ' 递归终止条件：当n为0时，表示完成一次分拆
    If n = 0 Then
        If current <> "" Then
            partitions.Add current
        End If
        Exit Sub
    End If
    ' 递归生成所有可能的无序分拆
    Dim i As Integer
    ' 确保生成的分拆项不会超过当前允许的最大值，以避免重复
    For i = 1 To Application.min(n, max)
        Dim newPartition As String
        If current = "" Then
            newPartition = i
        Else
            newPartition = i & "+" & current
        End If
        ' 递归调用，继续分拆剩余值，并更新最大允许分拆项
        GeneratePartitions n - i, i, newPartition, partitions
    Next i
End Sub

' 创建频率键（用于哈希表的键）
' 参数:
'   partition: 分拆字符串，如"1+2+2"
' 返回值: 频率键，如"1:1,2:2"表示1出现1次，2出现2次
Function GetFrequencyKey(partition As String) As String
    ' 创建字典用于统计各数字出现的频率
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    ' 将分拆字符串按"+"分割成数组
    Dim elements As Variant
    elements = Split(partition, "+")
    ' 统计各数字出现的频率
    Dim i As Integer
    For i = 0 To UBound(elements)
        Dim element As String
        element = CStr(elements(i))
        If dict.exists(element) Then
            dict(element) = dict(element) + 1
        Else
            dict.Add element, 1
        End If
    Next i
    ' 构建排序后的键
    Dim keys As Variant
    keys = dict.keys
    ' 使用冒泡排序对键进行排序
    Dim sorted As Boolean
    sorted = False
    Do While Not sorted
        sorted = True
        Dim idx As Integer
        For idx = 0 To UBound(keys) - 1
            If keys(idx) > keys(idx + 1) Then
                Dim Temp As Variant
                Temp = keys(idx)
                keys(idx) = keys(idx + 1)
                keys(idx + 1) = Temp
                sorted = False
            End If
        Next idx
    Loop
    ' 构建键字符串
    Dim keyString As String
    keyString = ""
    For idx = 0 To UBound(keys)
        If keyString <> "" Then
            keyString = keyString & ","
        End If
        keyString = keyString & keys(idx) & ":" & dict(keys(idx))
    Next idx
    GetFrequencyKey = keyString
End Function

' 使用五边形数定理计算分拆数
' 参数:
'   n: 需要计算分拆数的整数
' 返回值: n的分拆数
Function partition(n As Long) As Double
    ' 创建数组存储分拆数
    Dim p() As Double
    Dim i As Long, k As Long
    Dim pentagonal As Long
    Dim sign As Integer
    ' 处理边界情况
    If n < 0 Then
        partition = 0
        Exit Function
    End If
    If n = 0 Then
        partition = 1
        Exit Function
    End If
    ' 初始化数组
    ReDim p(0 To n)
    p(0) = 1
    ' 使用五边形数定理计算分拆数
    For i = 1 To n
        p(i) = 0
        k = 1
        sign = 1
        ' 计算五边形数并累加
        Do
            pentagonal = k * (3 * k - 1) \ 2
            If pentagonal > i Then Exit Do
            p(i) = p(i) + sign * p(i - pentagonal)
            pentagonal = k * (3 * k + 1) \ 2
            If pentagonal <= i Then
                p(i) = p(i) + sign * p(i - pentagonal)
            End If
            ' 改变符号
            sign = -sign
            k = k + 1
        Loop
    Next i
    partition = p(n)
End Function

