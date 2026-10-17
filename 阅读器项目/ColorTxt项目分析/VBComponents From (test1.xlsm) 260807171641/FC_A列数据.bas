Attribute VB_Name = "FC_A列数据"
Option Explicit

'VBA代码演示以下数据
'输入: 1 1 2 3 4 4 2
'输出:
'1  2
'2  1
'3  1
'4  2
'2  1
'请用数组统计以上数据,判断计数的关键是上一个数据和下一个数据是否一致,如果一致就增加计数,不一致就按照新的数据来计数
'以上数据输入是通过单元格选择,输出到Excel单元格
'<思考过程> {
'    嗯，用户的问题是关于用VBA统计连续重复的数字，输出到Excel单元格。首先我需要仔细理解他的需求。输入的数据是1、1、2、3、4、4、2，输出应该是每个连续段的数值及其出现次数。比如前两个1是连续的，所以输出1出现2次，然后是2出现1次，依此类推。但最后一个2是单独的，所以计数1次。
'
'    用户提到用数组统计，关键是根据前后数据是否一致来计数。所以需要遍历数组，比较当前元素和下一个元素。如果相同，计数器加一；不同的话，记录当前数值和计数器，然后重置计数器。但要注意数组越界的问题，比如最后一个元素的下一个元素不存在，这时候需要直接记录。
'
'    接下来考虑输入的来源是Excel单元格，输出也要到单元格。所以需要用Range对象来读取输入，处理后输出到指定的位置。可能的问题是如何处理输入的单元格区域，将其转换为数组。还有输出的格式，每个数值和次数占一行，分两列。
'
'    常见易错点可能包括：循环的边界条件处理，比如避免索引超出数组范围；计数器初始化的位置；以及如何处理最后一个元素的情况。例如，当循环到倒数第二个元素时，比较下一个元素，如果不同，则记录当前计数器，但最后一个元素可能需要单独处理，或者在循环结束后检查是否还有未记录的计数。
'
'解决方案的大致步骤是:
'    1. 读取输入区域的值到数组。
'    2. 初始化结果数组和计数器。
'    3. 遍历输入数组，比较当前元素和下一个元素。
'    4. 当遇到不同元素时，将当前值和计数存入结果数组，并重置计数器。
'    5. 循环结束后处理最后一个元素的情况。
'    6. 将结果输出到指定单元格。
'
'    代码结构方面，可能需要使用一个动态数组来存储结果，或者预先确定结果数组的大小。由于输入数组的长度不确定，动态数组更灵活。例如，使用ReDim Preserve来扩展结果数组的尺寸。
'
'    在编写代码时，需要确保数组的索引正确，特别是因为VBA的数组默认是基于0还是1的。如果从Excel读取的数组是二维的，因为Excel的Range.Value返回的是一个二维数组（行，列），所以处理时需要遍历每一行的第一个元素（假设输入是单列）。例如，输入数组arr可能是arr(i, 1)的形式，如果输入是一列多行的话。
'
'    另一个需要注意的点是，当比较当前元素和下一个元素时，循环应该到倒数第二个元素为止，以避免索引超出范围。例如，循环从1到UBound(arr)-1，然后在循环结束后处理最后一个元素的情况。
'
'    测试案例中的输入是1 1 2 3 4 4 2，输出应该是：
'    1  2
'    2  1
'    3  1
'    4  2
'    2  1
'
'    所以在处理到第二个4的时候，计数器增加到2，然后下一个元素是2，不同，所以记录4的计数为2，然后处理最后一个元素2时，因为它后面没有元素，所以需要单独记录一次。
'
'总结关键点:
'    - 正确遍历数组并处理边界条件
'    - 动态数组的使用和扩展
'    - Excel Range与数组之间的转换
'    - 计数器的正确初始化和重置
'}

' 问题分析：
' 1. 需要处理连续相同数值的计数问题，边界条件容易出错
' 2. 需要注意数组索引越界问题
' 3. 需要正确处理Excel单元格数据的输入输出

Sub CountConsecutiveNumbers()
    ' 声明变量
    Dim arrInput As Variant   ' 输入数组
    Dim arrResult() As Variant ' 结果数组
    Dim i As Long, j As Long   ' 循环计数器
    Dim currentValue As Variant ' 当前处理值
    Dim count As Long          ' 计数器
    
    ' 从A1单元格开始读取输入数据（假设纵向排列）
    arrInput = Range("A1:A" & Range("A" & rows.count).End(xlUp).row).Value
    ReDim arrResult(1 To UBound(arrInput), 1 To 2) ' 预定义结果数组
    
    ' 初始化第一个元素
    currentValue = arrInput(1, 1)
    count = 1
    j = 0 ' 结果数组索引
    
    ' 遍历输入数组（从第二个元素开始）
    For i = 2 To UBound(arrInput)
        If arrInput(i, 1) = currentValue Then
            count = count + 1
        Else
            ' 存储当前结果
            j = j + 1
            arrResult(j, 1) = currentValue
            arrResult(j, 2) = count
            ' 重置计数器和当前值
            currentValue = arrInput(i, 1)
            count = 1
        End If
    Next i
    
    ' 处理最后一个元素
    j = j + 1
    arrResult(j, 1) = currentValue
    arrResult(j, 2) = count
    

    
        ' 结果输出到C列
    With ThisWorkbook.ActiveSheet
        .Range("C1:D1").Value = Array("项目", "出现次数") ' 标题
        .Range("C2").Resize(UBound(arrResult), 2).Value = arrResult
    End With

End Sub

' 关键知识点总结：
' 1. 使用双指针法处理连续数值统计
' 2. 注意数组索引从1开始（Excel单元格转数组的特性）
' 3. 必须单独处理最后一个元素的存储
' 4. 结果数组需要动态处理尺寸
' 5. 使用Resize方法实现批量数据输出







'A列数据出现次数统计
Sub CountOccurrences()
    Dim lastRow As Long
    Dim i As Long
    Dim countDict As Object
    Dim currentValue As Variant
    Dim outputArray() As Variant
    
    ' 获取A列最后一行
    lastRow = Cells(rows.count, 1).End(xlUp).row
    
    ' 创建字典对象
    Set countDict = CreateObject("Scripting.Dictionary")
    
    ' 初始化输出数组
    ReDim outputArray(1 To lastRow + 1, 1 To 2)
    
    ' 添加标题
    outputArray(1, 1) = "数据"
    outputArray(1, 2) = "次数"
    
    ' 遍历A列数据并统计出现次数
    For i = 1 To lastRow
        currentValue = Cells(i, 1).Value
        
        If countDict.exists(currentValue) Then
            countDict(currentValue) = countDict(currentValue) + 1
        Else
            countDict.Add currentValue, 1
        End If
        
        ' 将结果存入数组
        outputArray(i + 1, 1) = currentValue
        outputArray(i + 1, 2) = countDict(currentValue)
    Next i
    ' 将数组输出到C列和D列
    Range("C1").Resize(UBound(outputArray, 1), 2).Value = outputArray
End Sub



Sub DictionarySortByColumnA()
    Dim dict As Object
    Dim arrData As Variant, arrResult() As Variant
    Dim i As Long, j As Long, lastRow As Long
    Dim key As Variant, Temp As Variant
    
    ' 创建字典对象
    Set dict = CreateObject("Scripting.Dictionary")
    
    ' 读取A列数据（从A1开始，跳过空值）
    With ThisWorkbook.ActiveSheet ' 修改为你的工作表名称
        lastRow = .Cells(.rows.count, "A").End(xlUp).row
        arrData = .Range("A1:A" & lastRow).Value
    End With
    
    ' 统计词频
    For i = 1 To UBound(arrData)
        If Not IsEmpty(arrData(i, 1)) Then
            If dict.exists(arrData(i, 1)) Then
                dict(arrData(i, 1)) = dict(arrData(i, 1)) + 1
            Else
                dict.Add arrData(i, 1), 1
            End If
        End If
    Next i
    
    ' 将字典转为二维数组
    ReDim arrResult(1 To dict.count, 1 To 2)
    i = 1
    For Each key In dict.keys
        arrResult(i, 1) = key
        arrResult(i, 2) = dict(key)
        i = i + 1
    Next key
    
    ' 冒泡排序（按第二列从大到小）
    For i = 1 To UBound(arrResult) - 1
        For j = i + 1 To UBound(arrResult)
            If arrResult(i, 2) < arrResult(j, 2) Then
                ' 交换两行数据
                Temp = arrResult(i, 1)
                arrResult(i, 1) = arrResult(j, 1)
                arrResult(j, 1) = Temp
                
                Temp = arrResult(i, 2)
                arrResult(i, 2) = arrResult(j, 2)
                arrResult(j, 2) = Temp
            End If
        Next j
    Next i
    
    ' 结果输出到C列
    With ThisWorkbook.ActiveSheet
        .Range("C1:D1").Value = Array("项目", "出现次数") ' 标题
        .Range("C2").Resize(UBound(arrResult), 2).Value = arrResult
    End With
    
    Set dict = Nothing
End Sub

