Attribute VB_Name = "modMain"
Option Explicit

'==============================================================================
' 主控模块: 一键自动化聚合分析全流程
'   流程: 选文件 → 编码检测 → TXT导入 → 章节分割 → 字频统计 → 可控聚合 → 堆叠折线图
'   入口:
'     一键聚合分析  — 完整流程, 交互式参数配置
'     快速聚合分析  — 使用默认参数, 最少交互
'     仅生成图表    — 跳过前面步骤, 仅从已有聚合结果生成图表
'==============================================================================

' --- 全局配置 ---
Public g_filePath As String       ' TXT文件路径
Public g_charGroups() As String   ' 字符组数组
Public g_groupCount As Long       ' 字符组数量
Public g_aggRule As String        ' 聚合规则
Public g_chartTitle As String     ' 图表标题

'==============================================================================
' 入口1: 一键聚合分析 (交互式, 完整参数配置)
'==============================================================================
Public Sub 一键聚合分析()
    Dim t0 As Double
    t0 = Timer
    
    Debug.Print "========================================"
    Debug.Print "聚合可控分析 - 一键流程启动"
    Debug.Print "========================================"
    
    ' === 步骤1: 选择TXT文件 ===
    g_filePath = SelectTxtFile("步骤1/5: 选择要分析的TXT文件")
    If Len(g_filePath) = 0 Then
        MsgBox "已取消", vbInformation, "提示"
        Exit Sub
    End If
    Debug.Print "[配置] 文件: " & g_filePath
    
    ' === 步骤2: 配置字符组 ===
    Dim groupInput As String
    groupInput = InputBox( _
        "步骤2/5: 输入字符组（逗号分隔组，竖线分隔组内字符）" & vbCrLf & vbCrLf & _
        "示例:" & vbCrLf & _
        "  的, 了|着|过, 是|为, 在|有, 不|没, 我|你|他, 这|那, 一|二|三" & vbCrLf & vbCrLf & _
        "默认（8组高频虚词）:", _
        "字符组配置", _
        "的, 了|着|过, 是|为, 在|有, 不|没, 我|你|他, 这|那, 一|二|三")
    
    If StrPtr(groupInput) = 0 Then Exit Sub
    If Len(Trim(groupInput)) = 0 Then
        GetDefaultCharGroups g_charGroups, g_groupCount
    Else
        g_groupCount = ParseCharGroups(groupInput, g_charGroups)
        If g_groupCount = 0 Then
            MsgBox "字符组解析失败", vbExclamation, "错误"
            Exit Sub
        End If
    End If
    Debug.Print "[配置] 字符组数: " & g_groupCount
    
    ' === 步骤3: 配置聚合规则 ===
    g_aggRule = InputBox( _
        "步骤3/5: 输入聚合规则（格式: 长度,间距|长度,间距）" & vbCrLf & vbCrLf & _
        "示例:" & vbCrLf & _
        "  20,1|50,2  — 前20列独立, 后50列每2列合并" & vbCrLf & _
        "  10,1|20,2|30,5 — 三段式聚合" & vbCrLf & _
        "  0,1 — 全部独立(不聚合)" & vbCrLf & vbCrLf & _
        "默认:", _
        "聚合规则配置", _
        "20,1|50,2")
    
    If StrPtr(g_aggRule) = 0 Then Exit Sub
    If Len(Trim(g_aggRule)) = 0 Then g_aggRule = "20,1|50,2"
    
    ' 验证规则
    Dim ruleErr As String
    ruleErr = ValidateAggRule(g_aggRule)
    If Len(ruleErr) > 0 Then
        MsgBox "聚合规则错误: " & ruleErr, vbExclamation, "错误"
        Exit Sub
    End If
    Debug.Print "[配置] 聚合规则: " & g_aggRule
    
    ' === 步骤4: 图表标题 ===
    g_chartTitle = InputBox("步骤4/5: 输入图表标题", "图表标题", "字频聚合堆叠折线图")
    If StrPtr(g_chartTitle) = 0 Then Exit Sub
    If Len(Trim(g_chartTitle)) = 0 Then g_chartTitle = "字频聚合堆叠折线图"
    
    ' === 步骤5: 确认执行 ===
    Dim confirm As VbMsgBoxResult
    confirm = MsgBox( _
        "步骤5/5: 确认执行完整流程" & vbCrLf & vbCrLf & _
        "文件: " & g_filePath & vbCrLf & _
        "字符组: " & g_groupCount & " 组" & vbCrLf & _
        "聚合规则: " & g_aggRule & vbCrLf & _
        "图表标题: " & g_chartTitle & vbCrLf & vbCrLf & _
        "点击确定开始执行", _
        vbOKCancel + vbInformation, "确认执行")
    
    If confirm <> vbOK Then Exit Sub
    
    ' === 执行全流程 ===
    If ExecuteFullPipeline() Then
        MsgBox "聚合分析完成!" & vbCrLf & vbCrLf & _
               "总耗时: " & Format(Timer - t0, "0.00") & " 秒" & vbCrLf & _
               "请查看'聚合结果'工作表和图表", _
               vbInformation, "完成"
    End If
    
    Debug.Print "========================================"
    Debug.Print "总耗时: " & Format(Timer - t0, "0.00") & "s"
    Debug.Print "========================================"
End Sub

'==============================================================================
' 入口2: 快速聚合分析 (最少交互, 默认参数)
'==============================================================================
Public Sub 快速聚合分析()
    Dim t0 As Double
    t0 = Timer
    
    ' 选择文件
    g_filePath = SelectTxtFile("选择TXT文件")
    If Len(g_filePath) = 0 Then Exit Sub
    
    ' 使用默认参数
    GetDefaultCharGroups g_charGroups, g_groupCount
    g_aggRule = "20,1|50,2"
    g_chartTitle = "字频聚合堆叠折线图"
    
    Debug.Print "[快速] 文件: " & g_filePath
    Debug.Print "[快速] 字符组: " & g_groupCount & "组, 规则: " & g_aggRule
    
    ' 执行
    If ExecuteFullPipeline() Then
        MsgBox "快速聚合分析完成!" & vbCrLf & _
               "耗时: " & Format(Timer - t0, "0.00") & " 秒", _
               vbInformation, "完成"
    End If
End Sub

'==============================================================================
' 入口3: 仅生成图表 (从已有聚合结果)
'==============================================================================
Public Sub 仅生成图表()
    Dim title As String
    title = InputBox("输入图表标题", "图表标题", "字频聚合堆叠折线图")
    If StrPtr(title) = 0 Then Exit Sub
    If Len(Trim(title)) = 0 Then title = "字频聚合堆叠折线图"
    
    Dim chtObj As Object
    Set chtObj = CreateStackedLineChart(title)
    
    If Not chtObj Is Nothing Then
        MsgBox "图表已生成!", vbInformation, "完成"
    End If
End Sub

'==============================================================================
' 入口4: 分步执行 (调试用)
'==============================================================================

' 仅执行 Phase 0+1: 导入TXT
Public Sub 步骤1_导入TXT()
    g_filePath = SelectTxtFile("选择TXT文件")
    If Len(g_filePath) = 0 Then Exit Sub
    
    Dim enc As String
    enc = DetectEncoding(g_filePath)
    
    Dim lineCount As Long
    lineCount = ImportTxtToDataSource(g_filePath)
    
    If lineCount > 0 Then
        MsgBox "导入成功!" & vbCrLf & _
               "编码: " & GetEncodingName(enc) & vbCrLf & _
               "行数: " & lineCount, vbInformation, "完成"
    End If
End Sub

' 仅执行 Phase 2: 章节分割
Public Sub 步骤2_章节分割()
    Dim lines() As String
    lines = ReadLinesFromDataSource()
    
    Dim patterns() As String, patternCount As Long
    GetDefaultPatterns patterns, patternCount
    
    ScanChapters lines, UBound(lines) + 1, patterns, patternCount
    
    Dim chapCount As Long
    chapCount = WriteChaptersToSheet()
    
    If chapCount > 0 Then
        MsgBox "章节分割完成!" & vbCrLf & _
               "识别章节: " & chapCount & " 章", vbInformation, "完成"
    Else
        MsgBox "未识别到章节, 请检查正则或文本格式", vbExclamation, "提示"
    End If
End Sub

' 仅执行 Phase 3: 字频统计
Public Sub 步骤3_字频统计()
    Dim groupInput As String
    groupInput = InputBox("输入字符组(逗号分隔组, 竖线分隔组内字符)", "字符组", _
                          "的, 了|着|过, 是|为, 在|有, 不|没, 我|你|他, 这|那, 一|二|三")
    If StrPtr(groupInput) = 0 Then Exit Sub
    
    If Len(Trim(groupInput)) = 0 Then
        GetDefaultCharGroups g_charGroups, g_groupCount
    Else
        g_groupCount = ParseCharGroups(groupInput, g_charGroups)
    End If
    
    If g_groupCount = 0 Then
        MsgBox "字符组解析失败", vbExclamation, "错误"
        Exit Sub
    End If
    
    Dim lines() As String
    lines = ReadLinesFromDataSource()
    
    Dim resultCount As Long
    resultCount = RunFreqStats(g_charGroups, g_groupCount, lines, UBound(lines) + 1)
    
    If resultCount > 0 Then
        MsgBox "字频统计完成!" & vbCrLf & _
               "字符组数: " & resultCount, vbInformation, "完成"
    End If
End Sub

' 仅执行 Phase 4: 可控聚合
Public Sub 步骤4_可控聚合()
    g_aggRule = InputBox("输入聚合规则(格式: 长度,间距|长度,间距)", "聚合规则", "20,1|50,2")
    If StrPtr(g_aggRule) = 0 Then Exit Sub
    If Len(Trim(g_aggRule)) = 0 Then g_aggRule = "20,1|50,2"
    
    Dim ruleErr As String
    ruleErr = ValidateAggRule(g_aggRule)
    If Len(ruleErr) > 0 Then
        MsgBox "规则错误: " & ruleErr, vbExclamation, "错误"
        Exit Sub
    End If
    
    ' 显示规则说明
    Debug.Print ExplainAggRule(g_aggRule)
    
    Dim colCount As Long
    colCount = ProcessAndAggregateData(g_aggRule)
    
    If colCount > 0 Then
        MsgBox "聚合完成!" & vbCrLf & _
               "输出列数: " & colCount, vbInformation, "完成"
    End If
End Sub

' 仅执行 Phase 5: 生成图表
Public Sub 步骤5_生成图表()
    仅生成图表
End Sub

'==============================================================================
' 全流程执行引擎
'==============================================================================

'------------------------------------------------------------------------------
' 执行完整聚合分析流程
'   依赖全局变量: g_filePath, g_charGroups, g_groupCount, g_aggRule, g_chartTitle
'   返回: True=成功, False=失败
'------------------------------------------------------------------------------
Private Function ExecuteFullPipeline() As Boolean
    Dim lines() As String, lineCount As Long
    Dim patterns() As String, patternCount As Long
    Dim chapCount As Long, groupResult As Long, aggResult As Long
    Dim enc As String
    Dim t0 As Double
    
    ExecuteFullPipeline = False
    t0 = Timer
    
    ' Phase 0+1: 编码检测 + TXT导入
    Debug.Print "--- Phase 0+1: 编码检测 + TXT导入 ---"
    enc = DetectEncoding(g_filePath)
    Debug.Print "  编码: " & enc
    
    lineCount = ImportTxtToDataSource(g_filePath)
    If lineCount = 0 Then
        MsgBox "TXT导入失败", vbExclamation, "错误"
        Exit Function
    End If
    
    ' 读取文本行 (供后续章节分割和字频统计使用)
    lines = ReadLinesFromDataSource()
    
    ' Phase 2: 章节分割
    Debug.Print "--- Phase 2: 章节分割 ---"
    GetDefaultPatterns patterns, patternCount
    ScanChapters lines, UBound(lines) + 1, patterns, patternCount
    
    chapCount = WriteChaptersToSheet()
    If chapCount = 0 Then
        MsgBox "未识别到章节, 请检查文本格式", vbExclamation, "错误"
        Exit Function
    End If
    
    ' Phase 3: 字频统计
    Debug.Print "--- Phase 3: 字频统计 ---"
    groupResult = RunFreqStats(g_charGroups, g_groupCount, lines, UBound(lines) + 1)
    If groupResult = 0 Then
        MsgBox "字频统计失败", vbExclamation, "错误"
        Exit Function
    End If
    
    ' Phase 4: 可控聚合
    Debug.Print "--- Phase 4: 可控聚合 ---"
    aggResult = ProcessAndAggregateData(g_aggRule)
    If aggResult = 0 Then
        MsgBox "聚合失败", vbExclamation, "错误"
        Exit Function
    End If
    
    ' Phase 5: 生成图表
    Debug.Print "--- Phase 5: 生成图表 ---"
    Dim chtObj As Object
    Set chtObj = CreateStackedLineChart(g_chartTitle)
    If chtObj Is Nothing Then
        MsgBox "图表生成失败, 但聚合结果已保存", vbExclamation, "部分完成"
    End If
    
    Debug.Print "--- 全流程完成, 耗时: " & Format(Timer - t0, "0.00") & "s ---"
    ExecuteFullPipeline = True
End Function

'==============================================================================
' 工具: 显示当前配置
'==============================================================================
Public Sub 显示配置()
    Dim info As String
    info = "当前配置:" & vbCrLf & vbCrLf
    info = info & "文件路径: " & g_filePath & vbCrLf
    info = info & "字符组数: " & g_groupCount & vbCrLf
    info = info & "聚合规则: " & g_aggRule & vbCrLf
    info = info & "图表标题: " & g_chartTitle & vbCrLf
    
    If Len(g_aggRule) > 0 Then
        info = info & vbCrLf & ExplainAggRule(g_aggRule)
    End If
    
    MsgBox info, vbInformation, "配置信息"
End Sub
