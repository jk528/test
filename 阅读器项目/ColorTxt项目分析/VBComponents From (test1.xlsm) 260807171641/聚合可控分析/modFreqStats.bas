Attribute VB_Name = "modFreqStats"
Option Explicit

'==============================================================================
' Phase 3: 字频统计模块 (rex2 核心)
'   功能: 对每个自定义字符组, 逐章统计正则命中次数, 横向追加到"目录"工作表
'   原理: 字符组如 "的|了|是" → RegExp.Execute → 累加 mat.count (非布尔)
'   优化: 预编译正则 + 章节文本一次性提取 + 批量写入工作表
'==============================================================================

'==============================================================================
' 字频统计主函数
'==============================================================================

'------------------------------------------------------------------------------
' 对所有字符组执行字频统计, 结果写入"目录"工作表
'   参数: charGroups() - 字符组数组, 如 ("的|了|是", "在|有|为", ...)
'         groupCount - 字符组数量
'         lines() - 全文行数组
'         lineCount - 总行数
'   输出: "目录"工作表从C列起, 每列对应一个字符组的各章命中数
'   返回: 统计的字符组数
'------------------------------------------------------------------------------
Public Function RunFreqStats(charGroups() As String, ByVal groupCount As Long, _
                             lines() As String, ByVal lineCount As Long) As Long
    Dim ws As Worksheet
    Dim titles() As String, starts() As Long, ends() As Long, chapCount As Long
    Dim g As Long, i As Long, c As Long
    Dim reg As Object
    Dim t0 As Double
    
    t0 = Timer
    Debug.Print "[Phase3] 开始字频统计, 字符组数: " & groupCount
    
    ' 1. 获取章节数据
    GetChapterData titles, starts, ends, chapCount
    If chapCount = 0 Then
        MsgBox "未找到章节数据, 请先执行章节分割", vbExclamation, "字频统计失败"
        RunFreqStats = 0
        Exit Function
    End If
    
    Set ws = ThisWorkbook.Worksheets("目录")
    
    ' 2. 结果矩阵: chapCount行 × groupCount列
    Dim resultMatrix() As Long
    ReDim resultMatrix(0 To chapCount - 1, 0 To groupCount - 1)
    
    ' 3. 逐字符组统计
    Set reg = CreateObject("VBScript.RegExp")
    reg.Global = True
    
    For g = 0 To groupCount - 1
        ' 转义字符组中的特殊字符 (保留|作为分隔符)
        Dim pattern As String
        pattern = charGroups(g)
        If Len(pattern) = 0 Then GoTo NextGroup
        
        reg.Pattern = pattern
        
        ' 逐章统计命中次数
        For c = 0 To chapCount - 1
            Dim hitCount As Long
            hitCount = 0
            
            ' 遍历该章节的所有行
            For i = starts(c) To ends(c)
                If i >= 0 And i < lineCount Then
                    If Len(lines(i)) > 0 Then
                        Dim mat As Object
                        Set mat = reg.Execute(lines(i))
                        hitCount = hitCount + mat.Count
                    End If
                End If
            Next i
            
            resultMatrix(c, g) = hitCount
        Next c
        
        Debug.Print "[Phase3] 字符组[" & (g + 1) & "] " & Left(pattern, 30) & _
                    IIf(Len(pattern) > 30, "...", "") & " 完成"
NextGroup:
    Next g
    
    Set reg = Nothing
    
    ' 4. 写入工作表 (从C列开始, 每列一个字符组)
    ' 表头
    For g = 0 To groupCount - 1
        Dim colLetter As String
        colLetter = GetColLetter(g + 3) ' C=3
        ws.Range(colLetter & "1").Value = "组" & (g + 1) & ":" & charGroups(g)
        ws.Range(colLetter & "1").Font.Bold = True
        ws.Range(colLetter & "1").Interior.Color = RGB(252, 228, 214)
    Next g
    
    ' 批量写入数据
    Dim outputData() As Variant
    ReDim outputData(1 To chapCount, 1 To groupCount)
    For c = 0 To chapCount - 1
        For g = 0 To groupCount - 1
            outputData(c + 1, g + 1) = resultMatrix(c, g)
        Next g
    Next c
    
    ws.Range("C2").Resize(chapCount, groupCount).Value = outputData
    
    ' 自动列宽
    For g = 0 To groupCount - 1
        ws.Columns(GetColLetter(g + 3)).AutoFit
    Next g
    
    Debug.Print "[Phase3] 字频统计完成, 耗时: " & Format(Timer - t0, "0.00") & "s"
    RunFreqStats = groupCount
End Function

'==============================================================================
' 预设字符组
'==============================================================================

'------------------------------------------------------------------------------
' 获取默认字符组 (中文高频虚词分组)
'   分组策略: 按词性/功能分类, 每组3-6个字
'------------------------------------------------------------------------------
Public Sub GetDefaultCharGroups(ByRef groups() As String, ByRef count As Long)
    count = 8
    ReDim groups(0 To count - 1)
    groups(0) = "的"                    ' 结构助词
    groups(1) = "了|着|过"              ' 动态助词
    groups(2) = "是|为|乃"              ' 判断动词
    groups(3) = "在|有|无"              ' 存在动词
    groups(4) = "不|没|未"              ' 否定副词
    groups(5) = "我|你|他|她|它"        ' 人称代词
    groups(6) = "这|那|其|此"           ' 指示代词
    groups(7) = "一|二|三|四|五|六|七|八|九|十"  ' 数字
End Sub

'------------------------------------------------------------------------------
' 从用户输入解析字符组
'   格式: "的, 了|着|过, 是|为, 在|有"
'   分隔: 逗号分隔组, 竖线分隔组内字符
'------------------------------------------------------------------------------
Public Function ParseCharGroups(ByVal input As String, ByRef groups() As String) As Long
    Dim parts() As String, i As Long, count As Long
    
    input = Trim(input)
    If Len(input) = 0 Then
        ParseCharGroups = 0
        Exit Function
    End If
    
    ' 支持中英文逗号
    input = Replace(input, "，", ",")
    parts = Split(input, ",")
    
    count = 0
    For i = 0 To UBound(parts)
        If Len(Trim(parts(i))) > 0 Then count = count + 1
    Next i
    
    If count = 0 Then
        ParseCharGroups = 0
        Exit Function
    End If
    
    ReDim groups(0 To count - 1)
    count = 0
    For i = 0 To UBound(parts)
        If Len(Trim(parts(i))) > 0 Then
            groups(count) = Trim(parts(i))
            count = count + 1
        End If
    Next i
    
    ParseCharGroups = count
End Function

'------------------------------------------------------------------------------
' 从"目录"工作表读取字频统计结果
'   返回: matrix() - chapCount×groupCount 矩阵
'         chapTitles() - 章节标题
'         groupHeaders() - 字符组表头
'------------------------------------------------------------------------------
Public Sub ReadFreqMatrix(ByRef matrix() As Long, ByRef chapTitles() As String, _
                          ByRef groupHeaders() As String, _
                          ByRef chapCount As Long, ByRef groupCount As Long)
    Dim ws As Worksheet
    Dim lastRow As Long, lastCol As Long
    Dim i As Long, j As Long
    Dim arr As Variant
    
    Set ws = ThisWorkbook.Worksheets("目录")
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    
    chapCount = lastRow - 1
    groupCount = lastCol - 2  ' A=标题, B=章号, C起=字频
    
    If chapCount <= 0 Or groupCount <= 0 Then Exit Sub
    
    ReDim chapTitles(0 To chapCount - 1)
    ReDim groupHeaders(0 To groupCount - 1)
    ReDim matrix(0 To chapCount - 1, 0 To groupCount - 1)
    
    ' 读取章节标题
    Dim titleArr As Variant
    titleArr = ws.Range("A2:A" & lastRow).Value
    For i = 1 To chapCount
        chapTitles(i - 1) = CStr(titleArr(i, 1))
    Next i
    
    ' 读取表头
    For j = 3 To lastCol
        groupHeaders(j - 3) = CStr(ws.Cells(1, j).Value)
    Next j
    
    ' 读取字频矩阵
    arr = ws.Range(ws.Cells(2, 3), ws.Cells(lastRow, lastCol)).Value
    For i = 1 To chapCount
        For j = 1 To groupCount
            matrix(i - 1, j - 1) = CLng(arr(i, j))
        Next j
    Next i
End Sub
