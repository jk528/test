Attribute VB_Name = "modAggregate"
Option Explicit

'==============================================================================
' Phase 4: 可控聚合模块
'   功能: 按用户自定义规则聚合字频列, 生成聚合结果工作表
'   规则格式: "长度,间距|长度,间距"  例: "20,1|50,2"
'     - 第一段: 前20列直接聚合(间距1, 即每列独立)
'     - 第二段: 接下来50列按间距2聚合(每2列合并为1列)
'   优化: 规则解析+边界检查+批量写入
'==============================================================================

'==============================================================================
' 聚合规则解析与执行
'==============================================================================

'------------------------------------------------------------------------------
' 解析聚合规则字符串
'   格式: "20,1|50,2" → segments(0)={len=20,spacing=1}, segments(1)={len=50,spacing=2}
'   返回: 段数 (0=失败)
'------------------------------------------------------------------------------
Public Function ParseAggRule(ByVal ruleStr As String, _
                            ByRef segLengths() As Long, ByRef segSpacings() As Long) As Long
    Dim parts() As String, segs() As String
    Dim i As Long, count As Long
    
    ruleStr = Trim(ruleStr)
    If Len(ruleStr) = 0 Then
        ParseAggRule = 0
        Exit Function
    End If
    
    ' 支持 | 或分号 分隔段
    ruleStr = Replace(ruleStr, ";", "|")
    parts = Split(ruleStr, "|")
    
    count = 0
    For i = 0 To UBound(parts)
        If Len(Trim(parts(i))) > 0 Then count = count + 1
    Next i
    
    If count = 0 Then
        ParseAggRule = 0
        Exit Function
    End If
    
    ReDim segLengths(0 To count - 1)
    ReDim segSpacings(0 To count - 1)
    
    count = 0
    For i = 0 To UBound(parts)
        Dim seg As String
        seg = Trim(parts(i))
        If Len(seg) = 0 Then GoTo NextSeg
        
        ' 解析 "长度,间距"
        segs = Split(seg, ",")
        If UBound(segs) >= 0 Then
            segLengths(count) = CLng(Trim(segs(0)))
        Else
            segLengths(count) = 1
        End If
        If UBound(segs) >= 1 Then
            segSpacings(count) = CLng(Trim(segs(1)))
        Else
            segSpacings(count) = 1
        End If
        
        ' 边界保护
        If segLengths(count) < 1 Then segLengths(count) = 1
        If segSpacings(count) < 1 Then segSpacings(count) = 1
        
        count = count + 1
NextSeg:
    Next i
    
    ParseAggRule = count
End Function

'==============================================================================
' 聚合执行主函数
'==============================================================================

'------------------------------------------------------------------------------
' 执行可控聚合, 结果写入"聚合结果"工作表
'   参数: ruleStr - 聚合规则, 如 "20,1|50,2"
'   原理: 读取"目录"工作表的字频矩阵 → 按规则聚合列 → 写入"聚合结果"
'   返回: 聚合后的列数 (0=失败)
'------------------------------------------------------------------------------
Public Function ProcessAndAggregateData(ByVal ruleStr As String) As Long
    Dim wsSrc As Worksheet, wsDst As Worksheet
    Dim matrix() As Long, chapTitles() As String, groupHeaders() As String
    Dim chapCount As Long, groupCount As Long
    Dim segLengths() As Long, segSpacings() As Long, segCount As Long
    Dim aggMatrix() As Long, aggHeaders() As String, aggColCount As Long
    Dim i As Long, j As Long, g As Long, s As Long
    Dim t0 As Double
    
    t0 = Timer
    Debug.Print "[Phase4] 聚合规则: " & ruleStr
    
    ' 1. 读取字频矩阵
    ReadFreqMatrix matrix, chapTitles, groupHeaders, chapCount, groupCount
    If chapCount = 0 Or groupCount = 0 Then
        MsgBox "未找到字频数据, 请先执行字频统计", vbExclamation, "聚合失败"
        ProcessAndAggregateData = 0
        Exit Function
    End If
    
    ' 2. 解析聚合规则
    segCount = ParseAggRule(ruleStr, segLengths, segSpacings)
    If segCount = 0 Then
        MsgBox "聚合规则解析失败: " & ruleStr, vbExclamation, "聚合失败"
        ProcessAndAggregateData = 0
        Exit Function
    End If
    
    Debug.Print "[Phase4] 章节数: " & chapCount & ", 字符组数: " & groupCount & ", 规则段数: " & segCount
    
    ' 3. 计算聚合后的列数
    aggColCount = 0
    Dim colIdx As Long
    colIdx = 0
    For s = 0 To segCount - 1
        Dim colsInSeg As Long
        colsInSeg = segLengths(s) \ segSpacings(s)
        If segLengths(s) Mod segSpacings(s) > 0 Then colsInSeg = colsInSeg + 1
        ' 不超过剩余列数
        If colIdx + segLengths(s) > groupCount Then
            Dim availCols As Long
            availCols = groupCount - colIdx
            If availCols <= 0 Then Exit For
            colsInSeg = availCols \ segSpacings(s)
            If availCols Mod segSpacings(s) > 0 Then colsInSeg = colsInSeg + 1
            aggColCount = aggColCount + colsInSeg
            Exit For
        End If
        aggColCount = aggColCount + colsInSeg
        colIdx = colIdx + segLengths(s)
    Next s
    
    ' 如果规则没覆盖所有列, 剩余列每列独立
    If colIdx < groupCount Then
        aggColCount = aggColCount + (groupCount - colIdx)
    End If
    
    If aggColCount = 0 Then
        MsgBox "聚合后列数为0, 请检查规则", vbExclamation, "聚合失败"
        ProcessAndAggregateData = 0
        Exit Function
    End If
    
    Debug.Print "[Phase4] 聚合后列数: " & aggColCount
    
    ' 4. 执行聚合
    ReDim aggMatrix(0 To chapCount - 1, 0 To aggColCount - 1)
    ReDim aggHeaders(0 To aggColCount - 1)
    
    Dim outCol As Long
    outCol = 0
    colIdx = 0  ' 当前处理到源矩阵的第几列
    
    For s = 0 To segCount - 1
        Dim segLen As Long, segSp As Long
        segLen = segLengths(s)
        segSp = segSpacings(s)
        
        ' 边界: 不超过剩余列
        If colIdx + segLen > groupCount Then
            segLen = groupCount - colIdx
        End If
        If segLen <= 0 Then Exit For
        
        ' 按间距聚合
        Dim pos As Long
        pos = 0
        Do While pos < segLen
            Dim groupSize As Long
            groupSize = segSp
            If pos + groupSize > segLen Then groupSize = segLen - pos
            
            ' 聚合 groupSize 列为 1 列
            For i = 0 To chapCount - 1
                Dim sum As Long
                sum = 0
                For g = 0 To groupSize - 1
                    sum = sum + matrix(i, colIdx + pos + g)
                Next g
                aggMatrix(i, outCol) = sum
            Next i
            
            ' 生成表头
            Dim hdr As String
            hdr = ""
            For g = 0 To groupSize - 1
                If g > 0 Then hdr = hdr & "+"
                hdr = hdr & "组" & (colIdx + pos + g + 1)
            Next g
            aggHeaders(outCol) = hdr
            
            outCol = outCol + 1
            pos = pos + groupSize
        Loop
        
        colIdx = colIdx + segLen
    Next s
    
    ' 剩余列直接拷贝
    Do While colIdx < groupCount And outCol < aggColCount
        For i = 0 To chapCount - 1
            aggMatrix(i, outCol) = matrix(i, colIdx)
        Next i
        aggHeaders(outCol) = "组" & (colIdx + 1)
        outCol = outCol + 1
        colIdx = colIdx + 1
    Loop
    
    ' 5. 写入"聚合结果"工作表
    Set wsDst = GetOrCreateSheet("聚合结果")
    wsDst.Cells.Clear
    
    ' 表头
    wsDst.Range("A1").Value = "章节标题"
    wsDst.Range("A1").Font.Bold = True
    wsDst.Range("A1").Interior.Color = RGB(217, 225, 242)
    
    For j = 0 To outCol - 1
        wsDst.Cells(1, j + 2).Value = aggHeaders(j)
        wsDst.Cells(1, j + 2).Font.Bold = True
        wsDst.Cells(1, j + 2).Interior.Color = RGB(252, 228, 214)
    Next j
    
    ' 批量写入数据
    Dim chapData() As Variant
    ReDim chapData(1 To chapCount, 1 To 1)
    For i = 0 To chapCount - 1
        chapData(i + 1, 1) = chapTitles(i)
    Next i
    wsDst.Range("A2").Resize(chapCount, 1).Value = chapData
    
    Dim aggData() As Variant
    ReDim aggData(1 To chapCount, 1 To outCol)
    For i = 0 To chapCount - 1
        For j = 0 To outCol - 1
            aggData(i + 1, j + 1) = aggMatrix(i, j)
        Next j
    Next i
    wsDst.Range("B2").Resize(chapCount, outCol).Value = aggData
    
    ' 格式
    wsDst.Columns("A").AutoFit
    For j = 0 To outCol - 1
        wsDst.Columns(GetColLetter(j + 2)).AutoFit
    Next j
    
    Debug.Print "[Phase4] 聚合完成, 输出列数: " & outCol & ", 耗时: " & Format(Timer - t0, "0.00") & "s"
    ProcessAndAggregateData = outCol
End Function

'==============================================================================
' 聚合规则验证与说明
'==============================================================================

'------------------------------------------------------------------------------
' 验证聚合规则格式
'   返回: 空字符串=合法, 否则返回错误说明
'------------------------------------------------------------------------------
Public Function ValidateAggRule(ByVal ruleStr As String) As String
    Dim segLengths() As Long, segSpacings() As Long
    Dim segCount As Long, i As Long
    
    segCount = ParseAggRule(ruleStr, segLengths, segSpacings)
    If segCount = 0 Then
        ValidateAggRule = "规则为空或格式错误"
        Exit Function
    End If
    
    For i = 0 To segCount - 1
        If segLengths(i) < 1 Then
            ValidateAggRule = "第" & (i + 1) & "段长度不能小于1"
            Exit Function
        End If
        If segSpacings(i) < 1 Then
            ValidateAggRule = "第" & (i + 1) & "段间距不能小于1"
            Exit Function
        End If
        If segSpacings(i) > segLengths(i) Then
            ValidateAggRule = "第" & (i + 1) & "段间距(" & segSpacings(i) & ")超过长度(" & segLengths(i) & ")"
            Exit Function
        End If
    Next i
    
    ValidateAggRule = ""  ' 合法
End Function

'------------------------------------------------------------------------------
' 生成聚合规则说明文本
'------------------------------------------------------------------------------
Public Function ExplainAggRule(ByVal ruleStr As String) As String
    Dim segLengths() As Long, segSpacings() As Long
    Dim segCount As Long, i As Long
    Dim sb As String
    
    segCount = ParseAggRule(ruleStr, segLengths, segSpacings)
    If segCount = 0 Then
        ExplainAggRule = "无效规则"
        Exit Function
    End If
    
    sb = "聚合规则: " & ruleStr & vbCrLf & vbCrLf
    
    Dim colStart As Long
    colStart = 1
    For i = 0 To segCount - 1
        Dim colsOut As Long
        colsOut = segLengths(i) \ segSpacings(i)
        If segLengths(i) Mod segSpacings(i) > 0 Then colsOut = colsOut + 1
        
        sb = sb & "第" & (i + 1) & "段: 第" & colStart & "~" & (colStart + segLengths(i) - 1) & "列"
        sb = sb & " (共" & segLengths(i) & "列, 间距" & segSpacings(i) & ")"
        If segSpacings(i) = 1 Then
            sb = sb & " → 每列独立, 输出" & colsOut & "列" & vbCrLf
        Else
            sb = sb & " → 每" & segSpacings(i) & "列合并, 输出" & colsOut & "列" & vbCrLf
        End If
        colStart = colStart + segLengths(i)
    Next i
    
    ExplainAggRule = sb
End Function
