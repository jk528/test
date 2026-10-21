Attribute VB_Name = "PC_006_分拆示意图_优化"
Option Explicit

' ============================================================
' PC_006 分拆示意图 - 优化版
' 优化要点:
'   1. 补充缺失的 Sort2DArray 函数 (原代码调用了但未定义)
'   2. 变量声明集中到过程顶部
'   3. 增加输入校验 (1 <= n <= 15)
'   4. 完善错误处理 (On Error GoTo)
'   5. 移除未使用的 partition 函数, 精简代码
' ============================================================

Sub RunDemoWithCount()
    On Error GoTo ErrorHandler
    Dim inputStr As Variant
    Dim n As Integer

    inputStr = InputBox("分析求和示意图:不能大于15", "输入行数", "10")

    ' 输入校验
    If IsEmpty(inputStr) Or inputStr = "" Then Exit Sub
    If Not IsNumeric(inputStr) Then
        MsgBox "输入的不是有效数字，请重新运行程序。", vbExclamation
        Exit Sub
    End If

    n = CInt(inputStr)
    If n < 1 Or n > 15 Then
        MsgBox "请输入1到15之间的整数。", vbExclamation
        Exit Sub
    End If

    DemoPartitionStatisticsWithCount n
    Exit Sub

ErrorHandler:
    MsgBox "执行过程中发生错误: " & err.Description, vbExclamation, "错误"
End Sub

' ============================================================
' 核心: 生成分拆统计表
'   1. 生成 n 的所有无序分拆 (干)
'   2. 生成 n 的所有有序分拆 (支)
'   3. 对有序分拆按 频率模式+项数 分组
'   4. 遍历每个无序分拆, 匹配同频率的有序分拆, 输出统计
' ============================================================
Sub DemoPartitionStatisticsWithCount(n As Integer)
    On Error GoTo ErrorHandler

    ' --- 变量声明区 ---
    Dim ws As Worksheet
    Dim Arr As Variant
    Dim partitions As Collection
    Dim orderedPartitions As Collection
    Dim orderedFrequencies As Object
    Dim i As Integer, j As Integer, k As Integer
    Dim currentPartition As String
    Dim currentOrdered As String
    Dim freqKey As String
    Dim itemFreqKey As String
    Dim itemCount As Integer
    Dim dryItemCount As Integer
    Dim dryFreqKey As String
    Dim matchCount As Integer
    Dim matchedOrdered As String
    Dim matchedCollection As Collection

    Set ws = ThisWorkbook.Sheets.Add
    ws.Name = "PartitionStats" & Sheets.count

    ' 生成无序分拆 (干)
    Set partitions = GetAllPartitions(n)

    ' 生成有序分拆 (支)
    Set orderedPartitions = New Collection
    GenerateOrderedPartitions "", n, orderedPartitions

    ' 预计算有序分拆的频率分组
    Set orderedFrequencies = CreateObject("Scripting.Dictionary")
    For j = 1 To orderedPartitions.count
        currentOrdered = orderedPartitions(j)
        freqKey = GetFrequencyKey(currentOrdered)
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

    ReDim Arr(1 To partitions.count, 1 To 4)

    ' 遍历每个无序分拆 (干)
    For i = 1 To partitions.count
        currentPartition = partitions(i)
        dryItemCount = UBound(Split(currentPartition, "+")) + 1
        dryFreqKey = GetFrequencyKey(currentPartition)
        itemFreqKey = dryFreqKey & "|" & dryItemCount

        matchedOrdered = ""
        If orderedFrequencies.exists(itemFreqKey) Then
            Set matchedCollection = orderedFrequencies(itemFreqKey)
            matchCount = matchedCollection.count
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

        Arr(i, 1) = currentPartition
        Arr(i, 2) = dryItemCount
        Arr(i, 3) = matchCount
        Arr(i, 4) = matchedOrdered
    Next i

    ' 按项数降序排序
    Arr = Sort2DArray(Arr, 2, False)
    ws.Range("A2").Resize(UBound(Arr), UBound(Arr, 2)) = Arr

    ' 格式化表格
    With ws.Range("A1:D" & (partitions.count + 1))
        .Borders.LineStyle = xlContinuous
        .EntireColumn.AutoFit
    End With
    Exit Sub

ErrorHandler:
    MsgBox "执行过程中发生错误: " & err.Description, vbExclamation, "错误"
End Sub

' ============================================================
' 生成 n 的所有有序分拆 (递归)
'   current:  已生成的部分分拆
'   remaining: 剩余需分拆的值
'   results:  存储结果集
' ============================================================
Sub GenerateOrderedPartitions(current As String, remaining As Integer, ByRef results As Collection)
    Dim i As Integer
    Dim newPartition As String

    If remaining = 0 Then
        If current <> "" Then results.Add current
        Exit Sub
    End If

    For i = 1 To remaining
        If current = "" Then
            newPartition = CStr(i)
        Else
            newPartition = current & "+" & CStr(i)
        End If
        GenerateOrderedPartitions newPartition, remaining - i, results
    Next i
End Sub

' ============================================================
' 获取 n 的所有无序分拆
' ============================================================
Function GetAllPartitions(n As Integer) As Collection
    Dim partitions As Collection
    Set partitions = New Collection
    GeneratePartitions n, n, "", partitions
    Set GetAllPartitions = partitions
End Function

' ============================================================
' 递归生成无序分拆
'   max: 当前允许的最大分拆项 (保证非递增, 避免重复)
' ============================================================
Sub GeneratePartitions(n As Integer, max As Integer, current As String, ByRef partitions As Collection)
    Dim i As Integer
    Dim newPartition As String

    If n = 0 Then
        If current <> "" Then partitions.Add current
        Exit Sub
    End If

    For i = 1 To Application.Min(n, max)
        If current = "" Then
            newPartition = CStr(i)
        Else
            newPartition = CStr(i) & "+" & current
        End If
        GeneratePartitions n - i, i, newPartition, partitions
    Next i
End Sub

' ============================================================
' 创建频率键 (用于匹配无序分拆与有序分拆)
'   "1+2+2" -> "1:1,2:2" (1出现1次, 2出现2次)
' ============================================================
Function GetFrequencyKey(partition As String) As String
    Dim dict As Object
    Dim elements As Variant
    Dim i As Integer, idx As Integer
    Dim element As String
    Dim keys As Variant
    Dim sorted As Boolean
    Dim Temp As Variant
    Dim keyString As String

    Set dict = CreateObject("Scripting.Dictionary")
    elements = Split(partition, "+")

    For i = 0 To UBound(elements)
        element = CStr(elements(i))
        If dict.exists(element) Then
            dict(element) = dict(element) + 1
        Else
            dict.Add element, 1
        End If
    Next i

    ' 对键排序 (冒泡排序, 键数量很小)
    keys = dict.keys
    sorted = False
    Do While Not sorted
        sorted = True
        For idx = 0 To UBound(keys) - 1
            If keys(idx) > keys(idx + 1) Then
                Temp = keys(idx)
                keys(idx) = keys(idx + 1)
                keys(idx + 1) = Temp
                sorted = False
            End If
        Next idx
    Loop

    ' 构建键字符串
    keyString = ""
    For idx = 0 To UBound(keys)
        If keyString <> "" Then keyString = keyString & ","
        keyString = keyString & keys(idx) & ":" & dict(keys(idx))
    Next idx
    GetFrequencyKey = keyString
End Function

' ============================================================
' 新增: 对二维数组按指定列排序 (原代码缺失此函数)
'   sortCol: 排序依据的列号
'   ascending: True=升序, False=降序
' 算法: 选择排序 (分拆数不大, 简单可靠)
' ============================================================
Function Sort2DArray(arr As Variant, sortCol As Long, ascending As Boolean) As Variant
    Dim i As Long, j As Long
    Dim minIdx As Long
    Dim Temp As Variant
    Dim numRows As Long, numCols As Long

    numRows = UBound(arr, 1)
    numCols = UBound(arr, 2)

    For i = 1 To numRows - 1
        minIdx = i
        For j = i + 1 To numRows
            If ascending Then
                If arr(j, sortCol) < arr(minIdx, sortCol) Then minIdx = j
            Else
                If arr(j, sortCol) > arr(minIdx, sortCol) Then minIdx = j
            End If
        Next j
        If minIdx <> i Then
            For j = 1 To numCols
                Temp = arr(i, j)
                arr(i, j) = arr(minIdx, j)
                arr(minIdx, j) = Temp
            Next j
        End If
    Next i

    Sort2DArray = arr
End Function
