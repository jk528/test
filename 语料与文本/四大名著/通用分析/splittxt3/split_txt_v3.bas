Option Explicit

'==============================================================================
' TXT章节拆分工具 v3.4（去重+乱序修复+卷级感知增强版）
'   以 splittxt2 多正则版为底本，增加：
'     - 中文数字转阿拉伯数字（支持万/亿/大写/繁体/俗写）
'     - 卷/部/册/篇 级别识别与卷感知去重
'     - 3种去重策略（none/first/longest）× 2种排序（none/sort）= 6组合
'     - 乱序自动修复（按章号重排；LIS保留为兼容选项）
'     - 深度分析报告（重复/乱序/多轨/格式/连续性 七大维度）
'     - 按卷分目录输出
'     - 无号章节识别（序章/楔子/番外/尾声等）
'   定位：TXT质量修复工具（上游：splittxt2 拆分；下游：彩读阅读/静读天下等阅读器）
'
'   复制粘贴到 VBA 编辑器（WPS/Excel/Word）即可运行，无需导入其他模块
'
' v3.4 变更摘要：
'   - 主流程弹窗由 9~10 个压缩为 4 个（文件→正则→去重排序组合→输出模式）
'   - 去重与排序合并为一次六选一（SelectDedupSortCombo）
'   - 新增独立设置入口 设置TXTv3（广告清理/标题去重/卷模式，SaveSetting持久化）
'   - 清洁模式同时生成 保留≥N 与 清理<N 两个合并文件（MergeFlag=2）
'   - 完成报告与分析报告改为 总-分 结构
'   - 新增自动化入口 自动TXTv3（自动判定组合与清洁N，一次确认即执行）
'   - 删除旧的"按章节一一拆分"模式（清洁模式本身即输出每章单文件）
'   - 删除 adjacent 相邻重复去重策略（双标题场景由目录区检测+清洁模式覆盖）
'
' 入口：运行 拆分TXTv3（选择文件 → 选择正则 → 选择组合 → 输出模式 → 生成）
'       运行 分析TXTv3（仅分析不拆分，输出总-分结构详细报告）
'       运行 自动TXTv3（全自动决策，一次确认即完成拆分）
'       运行 设置TXTv3（查看/修改默认设置）
'
' 去重×排序 6组合（弹窗3六选一）：
'   1. none+none    不去重+不排序（原样保留）
'   2. none+sort    不去重+按章号重排
'   3. first+none   保留首次+不排序（双标题/简单重复）
'   4. first+sort   保留首次+重排
'   5. longest+none 保留最长+不排序（整块重复）
'   6. longest+sort 保留最长+重排 ★推荐（默认）
'
' 卷模式：
'   auto         — 自动检测：有多卷则卷感知，无则扁平
'   flat         — 强制扁平：忽略卷结构
'   by_volume    — 按卷分目录输出
'==============================================================================

' --- 全局计时 ---
Private g_tSelect As Double
Private g_tTotal0 As Double
Private g_detectedEnc As String
Private g_regexName As String

' --- 多正则存储（与splittxt2一致）---
Private Const MAX_REGEX As Long = 10
Private g_regexNames(1 To MAX_REGEX) As String
Private g_regexPatterns(1 To MAX_REGEX) As String
Private g_regexUnitGroups(1 To MAX_REGEX) As Long
Private g_regexDefaultUnits(1 To MAX_REGEX) As String
Private g_regexCount As Long

Private g_selPatterns() As String
Private g_selUnitGroups() As Long
Private g_selDefaultUnits() As String
Private g_selOrigIndices() As Long
Private g_selCount As Long

' --- v3 新增：去重、排序与卷 ---
Private g_dedupStrategy As String       ' none/first/longest
Private g_sortStrategy As String        ' none/lis/sort
Private g_volumeMode As String          ' auto/flat/by_volume

' --- 章节数据（v3 增强版，含章号/卷号/正文行数等）---
' 使用平行数组存储（VBA 不支持自定义类型的动态数组友好操作）
Private ch_nums() As Long          ' 章号（无号章节=0）
Private ch_vols() As Long          ' 卷号（无卷=0）
Private ch_units() As String       ' 单位词
Private ch_levels() As String      ' chapter/volume/special
Private ch_patterns() As String    ' 匹配的正则类型
Private ch_bodyLines() As Long     ' 正文行数
Private ch_isTOC() As Boolean      ' v3.2 新增：是否为目录区章节
' v3.6 优化：扫描时预计算，消除重复遍历
Private ch_charCounts() As Long    ' 每章总字符数（含换行），预计算
Private ch_hanziCounts() As Long   ' 每章正文汉字数，预计算

' 原有数组（保持兼容）
Private ch_starts() As Long
Private ch_ends() As Long
Private ch_titles() As String
Private ch_count As Long
Private ch_unit As String

' v3.6 优化：全局复用正则对象，避免反复创建
Private g_regCn As Object          ' 汉字匹配正则，全局唯一实例

' 去重后的索引映射（原索引 → 是否保留，以及新顺序）
Private dedup_indices() As Long    ' 去重后第i个 = 原第 dedup_indices(i) 个
Private dedup_count As Long

' v3.2 新增：目录区检测结果
Private g_tocStartIdx As Long      ' 目录区起始索引
Private g_tocEndIdx As Long        ' 目录区结束索引
Private g_tocChapterCount As Long  ' 目录区章节数

' v3.2 新增：广告/垃圾行清理开关
Private g_cleanAds As Boolean      ' 是否启用广告清理
Private g_adRemovedCount As Long   ' 已移除的广告行数

' v3.3 新增：标题级去重开关
Private g_titleDedup As Boolean    ' 是否启用标题级去重
Private g_titleDiffCount As Long   ' 同章异题的章号数量（分析用）

' v3.4 新增：统计信息（总-分报告用）
Private g_dedupRemoved As Long     ' 去重减少的章数
Private g_oooFixed As Long         ' 排序修复的乱序处数（排序前后章号回退计数差）
Private g_actualVolMode As String  ' 实际使用的卷模式（flat/volume）
Private g_skipTitleOnly As Long    ' 跳过章节中仅标题的数量
Private g_skipShortBody As Long    ' 跳过章节中正文不足的数量


'==============================================================================
' 第零部分：初始化与入口
'==============================================================================

'------------------------------------------------------------------------------
' 初始化预设正则表达式（与splittxt2一致）
'------------------------------------------------------------------------------
Private Sub InitRegexPatterns()
    g_regexCount = 0

    ' 1. 标准中文（终极数字字符类）
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "标准中文（第N章/回/节/卷，含中文数字含〇含大写）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(章|回|节|卷)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = 1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 2. 纯阿拉伯数字
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "纯阿拉伯数字（第N章/回/节/卷）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*第([0-9０-９]+)(章|回|节|卷)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = 1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 3. 英文Chapter
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "英文Chapter（Chapter N - Title）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*[Cc]hapter\s+([0-9０-９]+)(?:[ \t　]*[:\.\-]?[ \t　]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = -1
    g_regexDefaultUnits(g_regexCount) = "Chapter"

    ' 4. 序章/楔子/番外（无章号）
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "序章/楔子/番外（无章号）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*(序章|楔子|尾声|番外|引子|后记|终章|序言|前言|跋)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = -1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 5. 数字+标题（无"第"字）
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "数字+标题（无""第""字，如 1章 标题）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*([0-9０-９]+)(章|回|节|卷)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = 1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 6. 精简中文
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "精简中文（仅章节，含〇，限1-7字）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*第([零〇○一二三四五六七八九十百千两兩]{1,7})(章|节)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = 1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 7. 宽松匹配
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "宽松匹配（第+任意内容+章/回/节/卷）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*第(.+?)(章|回|节|卷)(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = 1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 8. 纯数字起始
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "纯数字起始（3-4位数字开头，如 001 标题）"
    g_regexPatterns(g_regexCount) = "^[ \t　]*([0-9０-９]{3,4})(?:[ \t　：:]+(.*))?$"
    g_regexUnitGroups(g_regexCount) = -1
    g_regexDefaultUnits(g_regexCount) = "章"

    ' 9. 自定义正则
    g_regexCount = g_regexCount + 1
    g_regexNames(g_regexCount) = "自定义正则（手动输入）"
    g_regexPatterns(g_regexCount) = ""
    g_regexUnitGroups(g_regexCount) = -1
    g_regexDefaultUnits(g_regexCount) = "章"
End Sub

'------------------------------------------------------------------------------
' 正则选择对话框（与splittxt2一致，支持多选）
'------------------------------------------------------------------------------
Private Function SelectRegexPattern() As Boolean
    Dim prompt As String, i As Long, inputVal As String
    Dim regTest As Object, parts() As String, p As Long, idx As Long
    Dim nameParts() As String, hasCustom As Boolean

    prompt = "请选择章节正则表达式（可多选并列）：" & vbCrLf & vbCrLf
    For i = 1 To g_regexCount
        prompt = prompt & "  " & i & ". " & g_regexNames(i) & vbCrLf
    Next i
    prompt = prompt & vbCrLf & _
             "输入格式：" & vbCrLf & _
             "  单选:  1" & vbCrLf & _
             "  多选:  1,2,3  或  1 2 3" & vbCrLf & _
             "  示例:  1,4      同时使用 标准中文 + 序章/楔子" & vbCrLf & vbCrLf & _
             "请输入序号："

    inputVal = InputBox(prompt, "选择正则表达式（可多选）", "1,4")
    If StrPtr(inputVal) = 0 Then
        SelectRegexPattern = False
        Exit Function
    End If

    inputVal = NormalizeSeparators(inputVal)
    inputVal = Replace(Trim(inputVal), " ", ",")
    Do While InStr(inputVal, ",,") > 0
        inputVal = Replace(inputVal, ",,", ",")
    Loop
    If Left(inputVal, 1) = "," Then inputVal = Mid(inputVal, 2)
    If Right(inputVal, 1) = "," Then inputVal = Left(inputVal, Len(inputVal) - 1)
    If Len(inputVal) = 0 Then
        MsgBox "未输入序号。", vbExclamation, "提示"
        SelectRegexPattern = False
        Exit Function
    End If

    parts = Split(inputVal, ",")
    ReDim g_selPatterns(0 To UBound(parts))
    ReDim g_selUnitGroups(0 To UBound(parts))
    ReDim g_selDefaultUnits(0 To UBound(parts))
    ReDim g_selOrigIndices(0 To UBound(parts))
    ReDim nameParts(0 To UBound(parts))
    g_selCount = 0
    hasCustom = False

    For p = 0 To UBound(parts)
        If Not IsDigits(Trim(parts(p))) Then
            MsgBox "包含无效数字：" & parts(p), vbExclamation, "提示"
            SelectRegexPattern = False
            Exit Function
        End If
        idx = CLng(Trim(parts(p)))
        If idx < 1 Or idx > g_regexCount Then
            MsgBox "序号 " & idx & " 超出范围（1-" & g_regexCount & "）。", vbExclamation, "提示"
            SelectRegexPattern = False
            Exit Function
        End If
        If idx = g_regexCount And Len(g_regexPatterns(idx)) = 0 Then
            hasCustom = True
        End If
    Next p

    ' 处理自定义正则
    If hasCustom Then
        Dim customPattern As String
        Dim defaultPat As String
        ' v3.6 优化：更宽泛的默认值，允许缩进+可选第字+多种单位词，减少用户输入
        defaultPat = "^[ \t　]*(?:第)?([0-9０-９一二三四五六七八九十百千万亿零〇○两]+)[章回节卷篇集话]?.*$"
        customPattern = InputBox("请输入自定义正则表达式：" & vbCrLf & vbCrLf & _
                                  "示例：" & vbCrLf & _
                                  "  ^第(\d+)章\s*(.*)$" & vbCrLf & _
                                  "  ^卷(\d+)\s*(.*)$" & vbCrLf & vbCrLf & _
                                  "默认值（宽泛匹配：缩进+可选第+章/回/节/卷等）：" & vbCrLf & _
                                  "  " & defaultPat & vbCrLf & vbCrLf & _
                                  "提示：数字建议写 [0-9０-９] 同时匹配半角/全角。", _
                                  "自定义正则", defaultPat)
        If StrPtr(customPattern) = 0 Then
            SelectRegexPattern = False
            Exit Function
        End If
        customPattern = Trim(customPattern)
        If Len(customPattern) = 0 Then
            SelectRegexPattern = False
            Exit Function
        End If
        g_regexPatterns(g_regexCount) = customPattern
    End If

    ' 填充选中数组 + 验证
    Set regTest = CreateObject("VBScript.RegExp")
    regTest.IgnoreCase = True
    For p = 0 To UBound(parts)
        idx = CLng(Trim(parts(p)))
        g_selPatterns(g_selCount) = g_regexPatterns(idx)
        g_selUnitGroups(g_selCount) = g_regexUnitGroups(idx)
        g_selDefaultUnits(g_selCount) = g_regexDefaultUnits(idx)
        g_selOrigIndices(g_selCount) = idx
        nameParts(g_selCount) = g_regexNames(idx)

        On Error Resume Next
        regTest.Pattern = g_selPatterns(g_selCount)
        regTest.Test "test"
        If Err.Number <> 0 Then
            MsgBox "正则[" & idx & "]错误：" & Err.Description & vbCrLf & vbCrLf & _
                   "正则：" & g_selPatterns(g_selCount), vbExclamation, "正则错误"
            On Error GoTo 0
            Set regTest = Nothing
            SelectRegexPattern = False
            Exit Function
        End If
        On Error GoTo 0
        g_selCount = g_selCount + 1
    Next p
    Set regTest = Nothing

    g_regexName = Join(nameParts, " + ")
    If g_selCount > 1 Then
        g_regexName = g_selCount & "套正则: " & g_regexName
    End If

    Debug.Print "[正则选择] " & g_selCount & "套: " & g_regexName
    SelectRegexPattern = True
End Function

'------------------------------------------------------------------------------
' v3.4 新增：去重+排序组合选择对话框（一次六选一，替代原来的两个弹窗）
'------------------------------------------------------------------------------
Private Function SelectDedupSortCombo() As Boolean
    Dim prompt As String, inputVal As String
    Dim dedupArr As Variant, sortArr As Variant, i As Long

    dedupArr = Array("none", "none", "first", "first", "longest", "longest")
    sortArr = Array("none", "sort", "none", "sort", "none", "sort")

    prompt = "【步骤3/4】请选择去重+排序组合：" & vbCrLf & vbCrLf & _
             "  1. 不去重 + 不排序（原样保留）" & vbCrLf & _
             "  2. 不去重 + 排序（仅按章号重排）" & vbCrLf & _
             "  3. 保留首次 + 不排序" & vbCrLf & _
             "  4. 保留首次 + 排序" & vbCrLf & _
             "  5. 保留最长 + 不排序" & vbCrLf & _
             "  6. 保留最长 + 排序 ★推荐" & vbCrLf & vbCrLf & _
             "说明：乱序严重选排序；想保留最全内容选保留最长。" & vbCrLf & vbCrLf & _
             "请输入序号："

    inputVal = InputBox(prompt, "选择去重+排序组合", "6")
    If StrPtr(inputVal) = 0 Then
        SelectDedupSortCombo = False
        Exit Function
    End If

    inputVal = Trim(inputVal)
    If Not IsDigits(inputVal) Then
        MsgBox "请输入数字序号。", vbExclamation, "提示"
        SelectDedupSortCombo = False
        Exit Function
    End If

    i = CLng(inputVal) - 1
    If i < 0 Or i > 5 Then
        MsgBox "序号超出范围（1-6）。", vbExclamation, "提示"
        SelectDedupSortCombo = False
        Exit Function
    End If

    g_dedupStrategy = dedupArr(i)
    g_sortStrategy = sortArr(i)
    Debug.Print "[去重+排序组合] 去重=" & g_dedupStrategy & " 排序=" & g_sortStrategy
    SelectDedupSortCombo = True
End Function

'------------------------------------------------------------------------------
' v3.4 新增：从注册表读取默认设置（缺省 "0","1","1"）
'------------------------------------------------------------------------------
Private Sub LoadSettings()
    Dim sAd As String, sTitle As String, sVol As String
    sAd = GetSetting("SplitTxtV3", "Defaults", "AdClean", "0")
    sTitle = GetSetting("SplitTxtV3", "Defaults", "TitleDedup", "1")
    sVol = GetSetting("SplitTxtV3", "Defaults", "VolMode", "1")

    g_cleanAds = (sAd = "1")
    g_titleDedup = (sTitle = "1")
    Select Case sVol
        Case "2": g_volumeMode = "flat"
        Case "3": g_volumeMode = "by_volume"
        Case Else: g_volumeMode = "auto"
    End Select
End Sub

'------------------------------------------------------------------------------
' v3.4 新增：独立设置入口（直接回车=保持不变）
'------------------------------------------------------------------------------
Public Sub 设置TXTv3()
    Dim sAd As String, sTitle As String, sVol As String
    Dim prompt As String, inputVal As String, parts() As String
    Dim newAd As String, newTitle As String, newVol As String

    sAd = GetSetting("SplitTxtV3", "Defaults", "AdClean", "0")
    sTitle = GetSetting("SplitTxtV3", "Defaults", "TitleDedup", "1")
    sVol = GetSetting("SplitTxtV3", "Defaults", "VolMode", "1")

    prompt = "默认设置（当前值 " & sAd & "," & sTitle & "," & sVol & "）：" & vbCrLf & vbCrLf & _
             "  第1位 广告/垃圾行清理：0=不清理(默认) 1=清理" & vbCrLf & _
             "  第2位 标题级去重：1=双重判定(默认，章号+标题) 0=仅章号" & vbCrLf & _
             "  第3位 卷级别处理：1=自动判定(默认) 2=强制扁平 3=按卷分目录" & vbCrLf & vbCrLf & _
             "输入格式 0,1,1（直接回车=保持不变）："

    inputVal = InputBox(prompt, "设置TXTv3 - 默认设置", sAd & "," & sTitle & "," & sVol)
    If StrPtr(inputVal) = 0 Then Exit Sub

    inputVal = NormalizeSeparators(inputVal)
    inputVal = Replace(Trim(inputVal), " ", ",")
    If Len(inputVal) = 0 Then Exit Sub

    parts = Split(inputVal, ",")
    newAd = sAd: newTitle = sTitle: newVol = sVol
    If UBound(parts) >= 0 Then
        If Trim(parts(0)) = "0" Or Trim(parts(0)) = "1" Then newAd = Trim(parts(0))
    End If
    If UBound(parts) >= 1 Then
        If Trim(parts(1)) = "0" Or Trim(parts(1)) = "1" Then newTitle = Trim(parts(1))
    End If
    If UBound(parts) >= 2 Then
        If Trim(parts(2)) = "1" Or Trim(parts(2)) = "2" Or Trim(parts(2)) = "3" Then newVol = Trim(parts(2))
    End If

    SaveSetting "SplitTxtV3", "Defaults", "AdClean", newAd
    SaveSetting "SplitTxtV3", "Defaults", "TitleDedup", newTitle
    SaveSetting "SplitTxtV3", "Defaults", "VolMode", newVol

    MsgBox "设置已保存：" & vbCrLf & vbCrLf & _
           "  广告/垃圾行清理：" & newAd & vbCrLf & _
           "  标题级去重：" & newTitle & vbCrLf & _
           "  卷级别处理：" & newVol, vbInformation, "设置完成"
End Sub

'------------------------------------------------------------------------------
' v3.5 清理注册表痕迹：删除 SplitTxtV3 在注册表中的所有设置项
'   日常使用可忽略，仅在需要彻底清除工具痕迹时运行
'   删除后下次运行自动恢复默认值（0,1,1）
'------------------------------------------------------------------------------
Public Sub 清理注册表痕迹TXTv3()
    Dim prompt As String, resp As VbMsgBoxResult
    Dim sAd As String, sTitle As String, sVol As String

    ' 先读取当前值显示给用户
    sAd = GetSetting("SplitTxtV3", "Defaults", "AdClean", "0")
    sTitle = GetSetting("SplitTxtV3", "Defaults", "TitleDedup", "1")
    sVol = GetSetting("SplitTxtV3", "Defaults", "VolMode", "1")

    prompt = "⚠ 确定要清理 SplitTxtV3 的注册表痕迹吗？" & vbCrLf & vbCrLf & _
             "当前注册表中保存的设置：" & vbCrLf & _
             "  广告清理：" & sAd & vbCrLf & _
             "  标题级去重：" & sTitle & vbCrLf & _
             "  卷模式：" & sVol & vbCrLf & vbCrLf & _
             "清理后注册表中将不再留有 SplitTxtV3 任何记录" & vbCrLf & _
             "下次运行时自动恢复默认值（0,1,1）" & vbCrLf & vbCrLf & _
             "是否继续？"

    resp = MsgBox(prompt, vbYesNo + vbQuestion + vbDefaultButton2, "清理注册表痕迹")
    If resp <> vbYes Then Exit Sub

    ' 删除整个应用的注册表项（包括所有节和键）
    On Error Resume Next
    DeleteSetting "SplitTxtV3"
    On Error GoTo 0

    MsgBox "✓ 注册表痕迹已清理完毕。" & vbCrLf & vbCrLf & _
           "SplitTxtV3 在注册表中已无任何记录。" & vbCrLf & _
           "下次运行时将使用默认值：" & vbCrLf & _
           "  广告清理=关、标题级去重=开、卷模式=自动", _
           vbInformation, "清理完成"
End Sub

'------------------------------------------------------------------------------
' v3.4 新增：统计章号回退次数（乱序处数，仅用 ch_num>0 且非目录区章节）
'------------------------------------------------------------------------------
Private Function CountOOO() As Long
    Dim i As Long, prevNum As Long, cnt As Long
    cnt = 0: prevNum = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 And Not ch_isTOC(i) Then
            If prevNum > 0 And ch_nums(i) < prevNum Then cnt = cnt + 1
            prevNum = ch_nums(i)
        End If
    Next i
    CountOOO = cnt
End Function

'------------------------------------------------------------------------------
' v3.4 新增：统计 dedup_indices 当前顺序中的章号回退次数（排序前后对比用）
'------------------------------------------------------------------------------
Private Function CountOOOInDedup() As Long
    Dim i As Long, prevNum As Long, cnt As Long
    Dim oIdx As Long
    cnt = 0: prevNum = 0
    For i = 0 To dedup_count - 1
        oIdx = dedup_indices(i)
        If ch_nums(oIdx) > 0 Then
            If prevNum > 0 And ch_nums(oIdx) < prevNum Then cnt = cnt + 1
            prevNum = ch_nums(oIdx)
        End If
    Next i
    CountOOOInDedup = cnt
End Function

'------------------------------------------------------------------------------
'------------------------------------------------------------------------------
' v3.5 优化：Long 数组快速排序（章节数>1000 时性能远优于冒泡）
'------------------------------------------------------------------------------
Private Sub QuickSortLong(arr() As Long, ByVal left As Long, ByVal right As Long)
    Dim pivot As Long, i As Long, j As Long, tmp As Long
    If left >= right Then Exit Sub
    pivot = arr((left + right) \ 2)
    i = left: j = right
    Do While i <= j
        Do While arr(i) < pivot: i = i + 1: Loop
        Do While arr(j) > pivot: j = j - 1: Loop
        If i <= j Then
            tmp = arr(i): arr(i) = arr(j): arr(j) = tmp
            i = i + 1: j = j - 1
        End If
    Loop
    If left < j Then QuickSortLong arr, left, j
    If i < right Then QuickSortLong arr, i, right
End Sub

'------------------------------------------------------------------------------
' v3.5 优化：按 (卷号, 章号) 对索引数组快速排序（三数组并行交换）
'------------------------------------------------------------------------------
Private Sub QuickSortByVolCh( _
    idxArr() As Long, volArr() As Long, chArr() As Long, _
    ByVal left As Long, ByVal right As Long)
    Dim pv As Long, pc As Long
    Dim i As Long, j As Long
    Dim ti As Long, tv As Long, tc As Long
    If left >= right Then Exit Sub
    pv = volArr((left + right) \ 2)
    pc = chArr((left + right) \ 2)
    i = left: j = right
    Do While i <= j
        Do While volArr(i) < pv Or (volArr(i) = pv And chArr(i) < pc)
            i = i + 1
        Loop
        Do While volArr(j) > pv Or (volArr(j) = pv And chArr(j) > pc)
            j = j - 1
        Loop
        If i <= j Then
            ti = idxArr(i): idxArr(i) = idxArr(j): idxArr(j) = ti
            tv = volArr(i): volArr(i) = volArr(j): volArr(j) = tv
            tc = chArr(i): chArr(i) = chArr(j): chArr(j) = tc
            i = i + 1: j = j - 1
        End If
    Loop
    If left < j Then QuickSortByVolCh idxArr, volArr, chArr, left, j
    If i < right Then QuickSortByVolCh idxArr, volArr, chArr, i, right
End Sub

'------------------------------------------------------------------------------
' v3.5 优化：自动判定清洁模式的最小正文字数 N
'   性能优化：逐行正则计数（避免大字符串拼接）、>1000章用快速排序
'   规则：收集所有章节正文汉字数，升序排序，在下半区（≤中位数）找最大相邻间隔 gap，
'         N=间隔中点取整到10，clamp[50,1000]；
'         章节<20 或 gap<50 或 最大gap<次大gap×2 → N=100
'------------------------------------------------------------------------------
' v3.6 优化：直接读取预计算的汉字数，无需再次遍历行
'   性能收益：从 O(总行数) 降到 O(章节数)
Private Function AutoNFromBodies() As Long
    Dim cnts() As Long, cnt As Long
    Dim i As Long
    Dim lowerCnt As Long, k As Long
    Dim gap As Long, maxGap As Long, maxGapAt As Long, secondGap As Long
    Dim nResult As Long

    AutoNFromBodies = 100
    If ch_count = 0 Then Exit Function

    ReDim cnts(0 To ch_count - 1)
    cnt = 0
    For i = 0 To ch_count - 1
        If (ch_levels(i) = "chapter" Or ch_levels(i) = "special") _
           And Not ch_isTOC(i) Then
            If ch_hanziCounts(i) > 0 Then
                cnts(cnt) = ch_hanziCounts(i)
                cnt = cnt + 1
            End If
        End If
    Next i

    If cnt < 20 Then Exit Function
    ReDim Preserve cnts(0 To cnt - 1)

    ' 快速排序 O(n log n)
    QuickSortLong cnts, 0, cnt - 1

    ' 在下半区（≤中位数）找最大相邻间隔
    lowerCnt = cnt \ 2 + 1
    If lowerCnt < 2 Then Exit Function
    maxGap = 0: secondGap = 0: maxGapAt = -1
    For k = 0 To lowerCnt - 2
        gap = cnts(k + 1) - cnts(k)
        If gap > maxGap Then
            secondGap = maxGap
            maxGap = gap
            maxGapAt = k
        ElseIf gap > secondGap Then
            secondGap = gap
        End If
    Next k

    If maxGap < 50 Then Exit Function
    If secondGap > 0 Then
        If maxGap < secondGap * 2 Then Exit Function
    End If

    ' N=间隔中点取整到10，上限锁死 1000
    nResult = (cnts(maxGapAt) + cnts(maxGapAt + 1)) \ 2
    nResult = ((nResult + 5) \ 10) * 10
    If nResult < 50 Then nResult = 50
    If nResult > 1000 Then nResult = 1000
    AutoNFromBodies = nResult
End Function


'==============================================================================
' 第一部分：通用编码检测与读写（与splittxt2一致，略作精简引用）
'==============================================================================

' 编码检测
Public Function DetectEncodingFile(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    DetectEncodingFile = DetectEncodingBytes(fileBytes)
End Function

Public Function DetectEncodingBytes(fileBytes() As Byte) As String
    Dim totalLen As Long, scanLen As Long
    Dim result As String
    If UBound(fileBytes) < 0 Then
        DetectEncodingBytes = "ANSI"
        Exit Function
    End If
    totalLen = UBound(fileBytes) + 1
    ' BOM检测
    If UBound(fileBytes) >= 1 Then
        If fileBytes(0) = &HFF And fileBytes(1) = &HFE Then
            DetectEncodingBytes = "UTF-16LE": Exit Function
        End If
        If fileBytes(0) = &HFE And fileBytes(1) = &HFF Then
            DetectEncodingBytes = "UTF-16BE": Exit Function
        End If
    End If
    If UBound(fileBytes) >= 2 Then
        If fileBytes(0) = &HEF And fileBytes(1) = &HBB And fileBytes(2) = &HBF Then
            DetectEncodingBytes = "UTF-8 BOM": Exit Function
        End If
    End If
    ' 三段采样
    scanLen = 100
    If totalLen < scanLen * 3 Then
        result = ScanBytesForEncoding(fileBytes, 0, UBound(fileBytes))
        If Len(result) > 0 Then DetectEncodingBytes = result Else DetectEncodingBytes = "ANSI"
        Exit Function
    End If
    result = ScanBytesForEncoding(fileBytes, 0, scanLen - 1)
    If Len(result) > 0 Then DetectEncodingBytes = result: Exit Function
    Dim midStart As Long
    midStart = (totalLen \ 2) - (scanLen \ 2)
    If midStart < scanLen Then midStart = scanLen
    result = ScanBytesForEncoding(fileBytes, midStart, midStart + scanLen - 1)
    If Len(result) > 0 Then DetectEncodingBytes = result: Exit Function
    result = ScanBytesForEncoding(fileBytes, totalLen - scanLen, UBound(fileBytes))
    If Len(result) > 0 Then DetectEncodingBytes = result: Exit Function
    DetectEncodingBytes = "ANSI"
End Function

Private Function ScanBytesForEncoding(fileBytes() As Byte, _
        ByVal startIdx As Long, ByVal endIdx As Long) As String
    Dim i As Long, b1 As Byte, ub As Long
    ub = UBound(fileBytes)
    If startIdx < 0 Then startIdx = 0
    If endIdx > ub Then endIdx = ub
    If startIdx > endIdx Then Exit Function
    For i = startIdx To endIdx
        If fileBytes(i) > &H7F Then
            b1 = fileBytes(i)
            If (b1 And &HC0) = &H80 Then GoTo NextByte2
            Select Case True
                Case (b1 And &HF0) = &HE0
                    If i + 2 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 Then
                            ScanBytesForEncoding = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEncoding = "ANSI": Exit Function
                Case (b1 And &HF8) = &HF0
                    If i + 3 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 And _
                           (fileBytes(i + 3) And &HC0) = &H80 Then
                            ScanBytesForEncoding = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEncoding = "ANSI": Exit Function
                Case (b1 And &HE0) = &HC0
                    If i + 1 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 Then
                            ScanBytesForEncoding = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEncoding = "ANSI": Exit Function
                Case Else
                    ScanBytesForEncoding = "ANSI": Exit Function
            End Select
        End If
NextByte2:
    Next i
End Function

' 文件读写
Public Function ReadFileBytes(ByVal filePath As String) As Byte()
    Dim fileNo As Integer
    fileNo = FreeFile
    Open filePath For Binary Access Read As #fileNo
    ReDim ReadFileBytes(0 To LOF(fileNo) - 1)
    Get #fileNo, , ReadFileBytes
    Close #fileNo
End Function

Public Function ReadTextAuto(ByVal filePath As String) As String
    Dim enc As String
    enc = DetectEncodingFile(filePath)
    Select Case enc
        Case "ANSI": ReadTextAuto = ReadTextANSI(filePath)
        Case "UTF-8 BOM", "UTF-8": ReadTextAuto = ReadTextUTF8(filePath)
        Case "UTF-16LE", "UTF-16BE": ReadTextAuto = ReadTextUTF16(filePath)
        Case Else: ReadTextAuto = ReadTextUTF8(filePath)
    End Select
End Function

Public Function ReadTextANSI(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    If UBound(fileBytes) < 0 Then Exit Function
    ReadTextANSI = StrConv(fileBytes, vbUnicode)
End Function

Public Function ReadTextUTF8(ByVal filePath As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2: stm.Charset = "utf-8": stm.Open
    stm.LoadFromFile filePath
    ReadTextUTF8 = stm.ReadText(-1)
    stm.Close: Set stm = Nothing
End Function

Public Function ReadTextUTF16(ByVal filePath As String) As String
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(filePath, 1, False, -1)
    ReadTextUTF16 = ts.ReadAll
    ts.Close: Set ts = Nothing: Set fso = Nothing
End Function

Public Sub WriteTextUTF8NoBOM(ByVal filePath As String, ByVal text As String)
    Dim stm As Object, bin As Variant
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2: stm.Charset = "utf-8": stm.Open
    stm.WriteText text
    stm.Position = 0: stm.Type = 1: stm.Position = 3
    bin = stm.Read
    stm.Close: Set stm = Nothing
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 1: stm.Open: stm.Write bin
    stm.SaveToFile filePath, 2
    stm.Close: Set stm = Nothing
End Sub


'==============================================================================
' 第二部分：v3 核心新增 —— 中文数字转阿拉伯数字
'==============================================================================

'------------------------------------------------------------------------------
' 中文数字转阿拉伯数字
'   支持：阿拉伯数字、全角数字、中文数字（含〇/零）、万/亿、大写/繁体、廿卅卌皕
'   示例："三百一十" → 310, "一万二千三百四十五" → 12345
'------------------------------------------------------------------------------
Public Function CnToInt(ByVal s As String) As Long
    Dim cnNum As Object
    Set cnNum = CreateObject("Scripting.Dictionary")

    ' 填充字典
    cnNum("零") = 0: cnNum("〇") = 0: cnNum("○") = 0
    cnNum("一") = 1: cnNum("二") = 2: cnNum("三") = 3: cnNum("四") = 4
    cnNum("五") = 5: cnNum("六") = 6: cnNum("七") = 7: cnNum("八") = 8: cnNum("九") = 9
    cnNum("十") = 10: cnNum("百") = 100: cnNum("千") = 1000
    cnNum("万") = 10000: cnNum("亿") = 100000000
    cnNum("兩") = 2: cnNum("两") = 2
    cnNum("壹") = 1: cnNum("貳") = 2: cnNum("贰") = 2
    cnNum("參") = 3: cnNum("叁") = 3: cnNum("肆") = 4: cnNum("伍") = 5
    cnNum("陸") = 6: cnNum("陆") = 6: cnNum("柒") = 7: cnNum("捌") = 8: cnNum("玖") = 9
    cnNum("拾") = 10: cnNum("佰") = 100: cnNum("仟") = 1000
    cnNum("萬") = 10000: cnNum("億") = 100000000
    cnNum("廿") = 20: cnNum("卅") = 30: cnNum("卌") = 40: cnNum("皕") = 200

    Dim ss As String, i As Long, ch As String
    ss = Trim(s)
    ' 全角转半角
    For i = 0 To 9
        ss = Replace(ss, ChrW(&HFF10 + i), CStr(i))
    Next i
    ' 纯数字直接转（防溢出：超过Long范围返回0）
    If IsDigits(ss) Then
        If Len(ss) > 10 Then  ' Long最大约21亿，10位以内安全
            CnToInt = 0
            Set cnNum = Nothing
            Exit Function
        End If
        On Error Resume Next
        CnToInt = CLng(ss)
        If Err.Number <> 0 Then CnToInt = 0
        On Error GoTo 0
        Set cnNum = Nothing
        Exit Function
    End If

    Dim total As Long, section As Long, current As Long, lastDigit As Long
    Dim val As Long
    total = 0: section = 0: current = 0: lastDigit = 0

    For i = 1 To Len(ss)
        ch = Mid(ss, i, 1)
        If Not cnNum.Exists(ch) Then GoTo NextChar3

        val = cnNum(ch)
        If val < 10 Then
            lastDigit = val
        ElseIf val = 10 Then
            If lastDigit > 0 Then
                current = current + lastDigit * 10
            Else
                current = current + 10
            End If
            lastDigit = 0
        ElseIf val = 100 Then
            If lastDigit > 0 Then
                current = current + lastDigit * 100
            Else
                current = current + 100
            End If
            lastDigit = 0
        ElseIf val = 1000 Then
            If lastDigit > 0 Then
                current = current + lastDigit * 1000
            Else
                current = current + 1000
            End If
            lastDigit = 0
        ElseIf val = 10000 Then
            If lastDigit > 0 Then
                current = current + lastDigit
                lastDigit = 0
            End If
            section = (section + current) * 10000
            current = 0
        ElseIf val = 100000000 Then
            If lastDigit > 0 Then
                current = current + lastDigit
                lastDigit = 0
            End If
            total = (total + section + current) * 100000000
            section = 0: current = 0
        End If
NextChar3:
    Next i

    If lastDigit > 0 Then current = current + lastDigit
    
    ' 防溢出：结果超过Long范围返回0
    On Error Resume Next
    CnToInt = total + section + current
    If Err.Number <> 0 Then CnToInt = 0
    On Error GoTo 0
    Set cnNum = Nothing
End Function


'==============================================================================
' 第三部分：v3 核心新增 —— 增强章节扫描（卷识别+章号提取）
'==============================================================================

'------------------------------------------------------------------------------
' 卷级标题正则（用于检测第N卷/部/册/篇）
'------------------------------------------------------------------------------
Private Function GetVolumePattern() As String
    GetVolumePattern = "^[ \t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(卷|部|册|篇|集|季)(?:[ \t　：:]+(.*))?$"
End Function

'------------------------------------------------------------------------------
' 增强版章节扫描：识别卷+章，提取章号/卷号等信息
'   输出：ch_starts, ch_ends, ch_titles, ch_count, ch_unit（原有数组）
'         ch_nums, ch_vols, ch_units, ch_levels, ch_patterns, ch_bodyLines（新增）
'------------------------------------------------------------------------------
Private Sub ScanChaptersV3(lines() As String, ByVal lineCount As Long)
    Dim regs() As Object, regVol As Object
    Dim i As Long, r As Long, matched As Boolean, matchRegIdx As Long
    Dim m As Object, currentVol As Long, currentVolUnit As String
    Dim numStr As String, chNum As Long, unitStr As String
    Dim patType As String, lvl As String

    ' 回退默认
    If g_selCount = 0 Then
        ReDim g_selPatterns(0 To 0)
        ReDim g_selUnitGroups(0 To 0)
        ReDim g_selDefaultUnits(0 To 0)
        g_selPatterns(0) = "^[ \t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(章|回|节|卷)(?:[ \t　：:]+(.*))?$"
        g_selUnitGroups(0) = 1
        g_selDefaultUnits(0) = "章"
        g_selCount = 1
        g_regexName = "标准中文（默认回退）"
    End If

    ' v3.6 优化：初始容量 2048（万章级只需扩容3次），倍增扩容
    Dim initCap As Long
    initCap = 2048
    ReDim ch_starts(0 To initCap - 1)
    ReDim ch_ends(0 To initCap - 1)
    ReDim ch_titles(0 To initCap - 1)
    ReDim ch_nums(0 To initCap - 1)
    ReDim ch_vols(0 To initCap - 1)
    ReDim ch_units(0 To initCap - 1)
    ReDim ch_levels(0 To initCap - 1)
    ReDim ch_patterns(0 To initCap - 1)
    ReDim ch_bodyLines(0 To initCap - 1)
    ReDim ch_isTOC(0 To initCap - 1)
    ReDim ch_charCounts(0 To initCap - 1)   ' v3.6：预计算字符数
    ReDim ch_hanziCounts(0 To initCap - 1)  ' v3.6：预计算汉字数
    ch_count = 0
    
    ' v3.6 优化：全局汉字正则对象，只创建一次
    If g_regCn Is Nothing Then
        Set g_regCn = CreateObject("VBScript.RegExp")
        g_regCn.Global = True
        g_regCn.Pattern = "[" & ChrW(&H4E00) & "-" & ChrW(&H9FFF) & "]"
    End If
    ch_unit = g_selDefaultUnits(0)
    currentVol = 0
    currentVolUnit = ""
    
    ' 重置目录区检测
    g_tocStartIdx = -1
    g_tocEndIdx = -1
    g_tocChapterCount = 0

    ' 预编译卷级正则
    Set regVol = CreateObject("VBScript.RegExp")
    regVol.Pattern = GetVolumePattern()
    regVol.IgnoreCase = True

    ' 预编译章节正则
    ReDim regs(0 To g_selCount - 1)
    For r = 0 To g_selCount - 1
        Set regs(r) = CreateObject("VBScript.RegExp")
        regs(r).Pattern = g_selPatterns(r)
        regs(r).IgnoreCase = True
    Next r

    For i = 0 To lineCount - 1
        Dim line As String
        line = lines(i)
        If Len(Trim(line)) = 0 Then GoTo NextLine5
        
        ' v3.2 新增：行归一化（用于正则匹配，不影响原始内容）
        Dim normLine As String
        normLine = NormalizeLineForMatch(line)

        matched = False
        matchRegIdx = -1

        ' 先检查卷级标题
        If regVol.Test(normLine) Then
            Set m = regVol.Execute(normLine)
            numStr = m(0).SubMatches(0)
            unitStr = m(0).SubMatches(1)
            chNum = CnToInt(numStr)

            currentVol = chNum
            currentVolUnit = unitStr

            ' 卷级也记录为一个结构项
            If ch_count > 0 Then ch_ends(ch_count - 1) = i - 1
            ch_starts(ch_count) = i
            ch_titles(ch_count) = Trim(m(0).Value)
            ch_nums(ch_count) = 0
            ch_vols(ch_count) = chNum
            ch_units(ch_count) = unitStr
            ch_levels(ch_count) = "volume"
            ch_patterns(ch_count) = "volume"
            ch_bodyLines(ch_count) = 0
            ch_count = ch_count + 1
            ' v3.6 优化：倍增扩容，万章级只需扩容3次（2048→4096→8192→16384）
            If ch_count > UBound(ch_starts) Then
                Dim newCap As Long
                newCap = (UBound(ch_starts) + 1) * 2
                ReDim Preserve ch_starts(0 To newCap - 1)
                ReDim Preserve ch_ends(0 To newCap - 1)
                ReDim Preserve ch_titles(0 To newCap - 1)
                ReDim Preserve ch_nums(0 To newCap - 1)
                ReDim Preserve ch_vols(0 To newCap - 1)
                ReDim Preserve ch_units(0 To newCap - 1)
                ReDim Preserve ch_levels(0 To newCap - 1)
                ReDim Preserve ch_patterns(0 To newCap - 1)
                ReDim Preserve ch_bodyLines(0 To newCap - 1)
                ReDim Preserve ch_isTOC(0 To newCap - 1)
                ReDim Preserve ch_charCounts(0 To newCap - 1)
                ReDim Preserve ch_hanziCounts(0 To newCap - 1)
            End If
            GoTo NextLine5
        End If

        ' 再检查章节级正则
        For r = 0 To g_selCount - 1
            If regs(r).Test(normLine) Then
                matched = True
                matchRegIdx = r
                Exit For
            End If
        Next r

        If matched Then
            Set m = regs(matchRegIdx).Execute(normLine)
            Dim fullTitle As String
            fullTitle = Trim(m(0).Value)

            ' 提取章号
            If g_selUnitGroups(matchRegIdx) >= 0 Then
                ' 有单位组：数字组是SubMatches(0)
                If m(0).SubMatches.Count >= 1 Then
                    numStr = m(0).SubMatches(0)
                    chNum = CnToInt(numStr)
                Else
                    chNum = 0
                End If
                If m(0).SubMatches.Count > g_selUnitGroups(matchRegIdx) Then
                    unitStr = m(0).SubMatches(g_selUnitGroups(matchRegIdx))
                Else
                    unitStr = g_selDefaultUnits(matchRegIdx)
                End If
            Else
                ' 无单位组：尝试从第一个子匹配提取数字
                If m(0).SubMatches.Count >= 1 Then
                    numStr = m(0).SubMatches(0)
                    If IsDigits(Replace(numStr, "０", "0")) Then
                        chNum = CnToInt(numStr)
                    Else
                        chNum = 0
                    End If
                Else
                    chNum = 0
                End If
                unitStr = g_selDefaultUnits(matchRegIdx)
            End If

            ' 判断是否为无号特殊章节
            lvl = "chapter"
            patType = "standard"
            If chNum = 0 Then
                ' 检查是否匹配了无号章节正则（第4套）
                If g_selOrigIndices(matchRegIdx) = 4 Then
                    lvl = "special"
                    patType = "no_num"
                Else
                    ' 宽松匹配可能提取不出数字
                    patType = "loose"
                End If
            End If

            If ch_count = 0 Then ch_unit = unitStr

            If ch_count > 0 Then ch_ends(ch_count - 1) = i - 1
            ch_starts(ch_count) = i
            ch_titles(ch_count) = fullTitle
            ch_nums(ch_count) = chNum
            ch_vols(ch_count) = currentVol
            ch_units(ch_count) = unitStr
            ch_levels(ch_count) = lvl
            ch_patterns(ch_count) = patType
            ch_bodyLines(ch_count) = 0
            ch_charCounts(ch_count) = 0    ' v3.6：预计算初始值
            ch_hanziCounts(ch_count) = 0   ' v3.6：预计算初始值
            ch_count = ch_count + 1

            ' v3.6 优化：倍增扩容
            If ch_count > UBound(ch_starts) Then
                newCap = (UBound(ch_starts) + 1) * 2
                ReDim Preserve ch_starts(0 To newCap - 1)
                ReDim Preserve ch_ends(0 To newCap - 1)
                ReDim Preserve ch_titles(0 To newCap - 1)
                ReDim Preserve ch_nums(0 To newCap - 1)
                ReDim Preserve ch_vols(0 To newCap - 1)
                ReDim Preserve ch_units(0 To newCap - 1)
                ReDim Preserve ch_levels(0 To newCap - 1)
                ReDim Preserve ch_patterns(0 To newCap - 1)
                ReDim Preserve ch_bodyLines(0 To newCap - 1)
                ReDim Preserve ch_isTOC(0 To newCap - 1)
                ReDim Preserve ch_charCounts(0 To newCap - 1)
                ReDim Preserve ch_hanziCounts(0 To newCap - 1)
            End If
        End If
NextLine5:
    Next i

    If ch_count > 0 Then ch_ends(ch_count - 1) = lineCount - 1

    ' 计算正文行数
    For i = 0 To ch_count - 1
        If ch_ends(i) >= ch_starts(i) Then
            ch_bodyLines(i) = ch_ends(i) - ch_starts(i)
        Else
            ch_bodyLines(i) = 0
        End If
    Next i

    ' v3.6 优化：一次预计算字符数+汉字数，后续所有环节直接读取
    PrecomputeChapterCounts lines, lineCount
    
    ' 释放
    Set regVol = Nothing
    For r = 0 To g_selCount - 1
        Set regs(r) = Nothing
    Next r
End Sub

'------------------------------------------------------------------------------
' v3.6 优化：预计算每章的字符数和汉字数（一次遍历，后续所有环节复用）
'   性能收益：消除 AutoN、清洁模式、预计算字数 三处的重复行遍历
'   复杂度：O(总行数)，一次性完成
'------------------------------------------------------------------------------
Private Sub PrecomputeChapterCounts(ByRef lines() As String, ByVal lineCount As Long)
    Dim i As Long, j As Long, curChar As Long, curHanzi As Long
    Dim nLines As Long
    
    If ch_count = 0 Then Exit Sub
    
    ' 确保全局正则对象存在
    If g_regCn Is Nothing Then
        Set g_regCn = CreateObject("VBScript.RegExp")
        g_regCn.Global = True
        g_regCn.Pattern = "[" & ChrW(&H4E00) & "-" & ChrW(&H9FFF) & "]"
    End If
    
    For i = 0 To ch_count - 1
        nLines = ch_ends(i) - ch_starts(i) + 1
        If nLines < 1 Then nLines = 1
        
        curChar = 0
        curHanzi = 0
        
        ' 逐行累计：字符数（含换行）+ 汉字数
        For j = ch_starts(i) To ch_ends(i)
            curChar = curChar + Len(lines(j))
            ' 正文行（标题行之后）才计汉字
            If j > ch_starts(i) Then
                curHanzi = curHanzi + g_regCn.Execute(lines(j)).Count
            End If
        Next j
        
        ' 加上换行符数（和之前 Join(vbLf) 结果一致）
        If nLines > 1 Then curChar = curChar + (nLines - 1)
        
        ch_charCounts(i) = curChar
        ch_hanziCounts(i) = curHanzi
    Next i
End Sub

'------------------------------------------------------------------------------
' v3.2 新增：目录区自动检测
'   原理：文件开头连续 N 个章节正文都极短（<=2行）且章号递增 → 判定为目录区
'   参数：minTOCchapters - 最少目录章节数（默认10）
'         maxBodyLines   - 目录章最大正文行数（默认2）
'   效果：将目录区章节标记为 ch_isTOC=True，并设置全局变量
'------------------------------------------------------------------------------
Private Sub DetectTOC(Optional ByVal minTOCchapters As Long = 10, _
                      Optional ByVal maxBodyLines As Long = 2)
    Dim i As Long, chapStart As Long, chapEnd As Long
    Dim inTOC As Boolean
    Dim prevNum As Long, consecCount As Long
    Dim bodyLn As Long
    
    g_tocStartIdx = -1
    g_tocEndIdx = -1
    g_tocChapterCount = 0
    
    If ch_count < minTOCchapters Then Exit Sub
    
    ' 先计算每个章节的正文行数（ch_ends - ch_starts）
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then
            bodyLn = ch_ends(i) - ch_starts(i)
            If bodyLn < 0 Then bodyLn = 0
            ch_bodyLines(i) = bodyLn
        End If
    Next i
    
    ' 从头扫描，找第一段连续的短正文章节
    inTOC = False
    consecCount = 0
    prevNum = 0
    chapStart = -1
    
    For i = 0 To ch_count - 1
        ' 只看章节级（跳过volume）
        If ch_levels(i) <> "chapter" Then GoTo NextTOCScan
        
        bodyLn = ch_bodyLines(i)
        
        If bodyLn <= maxBodyLines Then
            ' 正文很短，可能是目录项
            If Not inTOC Then
                ' 检查是否在文件开头位置（前30%的章节内）
                If i > ch_count * 0.3 Then Exit For  ' 不在开头，不用找了
                chapStart = i
                consecCount = 1
                prevNum = ch_nums(i)
                inTOC = True
            Else
                ' 检查章号是否递增（目录通常是顺序的）
                If ch_nums(i) > prevNum Or ch_nums(i) = 0 Then
                    consecCount = consecCount + 1
                    prevNum = ch_nums(i)
                Else
                    ' 章号回退，可能目录结束了
                    If consecCount >= minTOCchapters Then
                        ' 确认是目录区
                        g_tocStartIdx = chapStart
                        g_tocEndIdx = i - 1
                        g_tocChapterCount = consecCount
                        Exit For
                    Else
                        ' 不够长，重置
                        inTOC = False
                        consecCount = 0
                        chapStart = -1
                    End If
                End If
            End If
        Else
            ' 正文足够长
            If inTOC Then
                If consecCount >= minTOCchapters Then
                    ' 确认是目录区，到前一个为止
                    g_tocStartIdx = chapStart
                    g_tocEndIdx = i - 1
                    g_tocChapterCount = consecCount
                    Exit For
                Else
                    ' 连续短章不够多，不是目录
                    inTOC = False
                    consecCount = 0
                    chapStart = -1
                End If
            End If
        End If
NextTOCScan:
    Next i
    
    ' 处理循环结束时还在 TOC 中的情况
    If inTOC And consecCount >= minTOCchapters Then
        g_tocStartIdx = chapStart
        g_tocEndIdx = ch_count - 1
        g_tocChapterCount = consecCount
    End If
    
    ' 标记 TOC 章节
    If g_tocChapterCount > 0 Then
        For i = g_tocStartIdx To g_tocEndIdx
            ch_isTOC(i) = True
        Next i
    End If
End Sub

'------------------------------------------------------------------------------
' 获取仅章节（排除volume，排除目录区）的数量和索引映射
'   v3.2 更新：默认跳过目录区章节
'   输出：chapIndices — 仅章节级别的原索引数组
'         chapCount   — 章节数量
'------------------------------------------------------------------------------
Private Sub GetChapterIndices(ByRef chapIndices() As Long, ByRef chapCount As Long)
    Dim i As Long, cnt As Long
    ReDim chapIndices(0 To ch_count - 1)
    cnt = 0
    For i = 0 To ch_count - 1
        If (ch_levels(i) = "chapter" Or ch_levels(i) = "special") _
           And Not ch_isTOC(i) Then
            chapIndices(cnt) = i
            cnt = cnt + 1
        End If
    Next i
    chapCount = cnt
    If cnt > 0 Then ReDim Preserve chapIndices(0 To cnt - 1)
End Sub


'==============================================================================
' 第四部分：v3 核心新增 —— 5种去重策略
'==============================================================================

'------------------------------------------------------------------------------
' 获取去重键（卷感知 + 可选标题级）
'------------------------------------------------------------------------------
Private Function DedupKey(ByVal idx As Long, ByVal volMode As String, _
        Optional ByVal titleDedup As Boolean = False) As String
    Dim chNum As Long, volNum As Long, unitStr As String
    Dim normTitle As String
    chNum = ch_nums(idx)
    volNum = ch_vols(idx)
    unitStr = ch_units(idx)

    If volMode = "flat" Or volNum = 0 Then
        DedupKey = "F|" & chNum & "|" & unitStr
    Else
        DedupKey = "V|" & volNum & "|" & chNum & "|" & unitStr
    End If
    
    ' 标题级去重：追加规范化标题到键中
    If titleDedup And chNum > 0 Then
        normTitle = NormalizeTitle(ch_titles(idx))
        DedupKey = DedupKey & "|T|" & normTitle
    End If
End Function

'------------------------------------------------------------------------------
' 策略1：保留首次出现
'------------------------------------------------------------------------------
Private Sub DedupFirst(ByVal volMode As String, _
        ByRef outIndices() As Long, ByRef outCount As Long, _
        Optional ByVal titleDedup As Boolean = False)
    Dim chapIdx() As Long, chapCnt As Long
    Dim i As Long, resultCnt As Long
    Dim seen As Object, key As String

    Set seen = CreateObject("Scripting.Dictionary")
    GetChapterIndices chapIdx, chapCnt
    If chapCnt = 0 Then outCount = 0: Exit Sub

    ReDim outIndices(0 To chapCnt - 1)
    resultCnt = 0

    For i = 0 To chapCnt - 1
        If ch_nums(chapIdx(i)) <= 0 And ch_levels(chapIdx(i)) = "special" Then
            key = "S|" & ch_titles(chapIdx(i))
        Else
            key = DedupKey(chapIdx(i), volMode, titleDedup)
        End If

        If Not seen.Exists(key) Then
            seen.Add key, 1
            outIndices(resultCnt) = chapIdx(i)
            resultCnt = resultCnt + 1
        End If
    Next i

    outCount = resultCnt
    Set seen = Nothing
End Sub

'------------------------------------------------------------------------------
' 策略2：保留内容最长的
'------------------------------------------------------------------------------
Private Sub DedupLongest(ByVal volMode As String, _
        ByRef outIndices() As Long, ByRef outCount As Long, _
        Optional ByVal titleDedup As Boolean = False)
    Dim chapIdx() As Long, chapCnt As Long
    Dim i As Long, resultCnt As Long
    Dim best As Object, orderList As Object
    Dim key As String

    Set best = CreateObject("Scripting.Dictionary")
    Set orderList = CreateObject("Scripting.Dictionary")

    GetChapterIndices chapIdx, chapCnt
    If chapCnt = 0 Then outCount = 0: Exit Sub

    For i = 0 To chapCnt - 1
        If ch_nums(chapIdx(i)) <= 0 And ch_levels(chapIdx(i)) = "special" Then
            key = "S|" & ch_titles(chapIdx(i))
        Else
            key = DedupKey(chapIdx(i), volMode, titleDedup)
        End If

        If Not best.Exists(key) Then
            best.Add key, chapIdx(i)
            orderList.Add orderList.Count, key
        Else
            If ch_bodyLines(chapIdx(i)) > ch_bodyLines(best(key)) Then
                best(key) = chapIdx(i)
            End If
        End If
    Next i

    resultCnt = orderList.Count
    ReDim outIndices(0 To resultCnt - 1)
    For i = 0 To resultCnt - 1
        outIndices(i) = best(orderList(i))
    Next i

    outCount = resultCnt
    Set best = Nothing
    Set orderList = Nothing
End Sub

'------------------------------------------------------------------------------
' 策略4：最长递增子序列（LIS）—— O(n log n)
'   排序键：(卷号, 章号)，严格递增
'------------------------------------------------------------------------------
' v3.4.1：已删除 DedupLIS / DedupSort / ParseDedupKey 三个死代码函数
'   （旧版"去重即排序"架构遗留，现由 ApplyDedup + ApplySort 两段式架构替代）
'------------------------------------------------------------------------------

'------------------------------------------------------------------------------
' 执行去重（调度函数）
'   strategy: none/first/longest（双标题场景由目录区检测+清洁模式覆盖）
'   volMode:  flat/volume
'   输出：dedup_indices, dedup_count（全局）
'------------------------------------------------------------------------------
Private Sub ApplyDedup(ByVal strategy As String, ByVal volMode As String, _
        Optional ByVal titleDedup As Boolean = False)
    If strategy = "none" Then
        ' 不去重：直接使用所有章节
        GetChapterIndices dedup_indices, dedup_count
    Else
        Select Case strategy
            Case "first":    DedupFirst volMode, dedup_indices, dedup_count, titleDedup
            Case "longest":  DedupLongest volMode, dedup_indices, dedup_count, titleDedup
            Case Else
                MsgBox "未知去重策略：" & strategy, vbExclamation, "错误"
                dedup_count = 0
        End Select
    End If
End Sub

'------------------------------------------------------------------------------
' 排序（在去重结果基础上继续排序）
'------------------------------------------------------------------------------
Private Sub ApplySort(ByVal strategy As String, ByVal volMode As String)
    If strategy = "none" Then Exit Sub   ' 不排序，保持去重结果
    
    Select Case strategy
        Case "lis":  SortLISFromIndices volMode
        Case "sort": SortFullFromIndices volMode
        Case Else
            MsgBox "未知排序策略：" & strategy, vbExclamation, "错误"
            dedup_count = 0
    End Select
End Sub

'------------------------------------------------------------------------------
' 在 dedup_indices 基础上应用 LIS 排序（输入输出都是 dedup_indices）
'------------------------------------------------------------------------------
Private Sub SortLISFromIndices(ByVal volMode As String)
    Dim n As Long, i As Long
    Dim tails_val_vol() As Long, tails_val_ch() As Long
    Dim tails_idx() As Long
    Dim prevArr() As Long
    Dim left As Long, right As Long, pos As Long
    Dim tailLen As Long
    Dim vol_i As Long, ch_i As Long
    Dim mid As Long
    Dim curr As Long
    Dim resultIdx() As Long, resultCnt As Long
    
    n = dedup_count
    If n = 0 Then Exit Sub
    
    ReDim tails_val_vol(0 To n - 1)
    ReDim tails_val_ch(0 To n - 1)
    ReDim tails_idx(0 To n - 1)
    ReDim prevArr(0 To n - 1)
    For i = 0 To n - 1
        prevArr(i) = -1
    Next i
    
    tailLen = 0
    
    For i = 0 To n - 1
        Dim origIdx As Long
        origIdx = dedup_indices(i)
        vol_i = ch_vols(origIdx)
        ch_i = ch_nums(origIdx)
        If ch_i = 0 Then ch_i = -1   ' 无号章节放最前面
        If volMode = "flat" Then vol_i = 0
        
        ' 二分查找：找第一个 >= (vol_i, ch_i) 的位置
        left = 0: right = tailLen
        Do While left < right
            mid = (left + right) \ 2
            If tails_val_vol(mid) < vol_i Then
                left = mid + 1
            ElseIf tails_val_vol(mid) > vol_i Then
                right = mid
            Else
                If tails_val_ch(mid) < ch_i Then
                    left = mid + 1
                Else
                    right = mid
                End If
            End If
        Loop
        pos = left
        
        If pos = tailLen Then
            tails_val_vol(tailLen) = vol_i
            tails_val_ch(tailLen) = ch_i
            tails_idx(tailLen) = i
            tailLen = tailLen + 1
        Else
            tails_val_vol(pos) = vol_i
            tails_val_ch(pos) = ch_i
            tails_idx(pos) = i
        End If
        
        If pos > 0 Then
            prevArr(i) = tails_idx(pos - 1)
        End If
    Next i
    
    ' 回溯
    If tailLen = 0 Then
        dedup_count = 0
        Exit Sub
    End If
    
    ReDim resultIdx(0 To tailLen - 1)
    curr = tails_idx(tailLen - 1)
    For i = tailLen - 1 To 0 Step -1
        resultIdx(i) = dedup_indices(curr)
        If i > 0 Then curr = prevArr(curr)
    Next i
    
    ' 写回 dedup_indices
    dedup_count = tailLen
    For i = 0 To tailLen - 1
        dedup_indices(i) = resultIdx(i)
    Next i
End Sub

'------------------------------------------------------------------------------
' v3.5 优化：在 dedup_indices 基础上按(卷号,章号)完全重排（快速排序版）
'------------------------------------------------------------------------------
Private Sub SortFullFromIndices(ByVal volMode As String)
    Dim n As Long, i As Long
    Dim nVol() As Long, nCh() As Long, nIdx() As Long  ' normal 数组
    Dim sIdx() As Long                                    ' special 数组
    Dim specialCnt As Long, normalCnt As Long
    Dim origIdx As Long
    
    n = dedup_count
    If n = 0 Then Exit Sub
    
    ReDim nVol(0 To n - 1)
    ReDim nCh(0 To n - 1)
    ReDim nIdx(0 To n - 1)
    ReDim sIdx(0 To n - 1)
    
    ' 分离 special 和 normal（与去重键逻辑一致：无号+special才算）
    specialCnt = 0
    normalCnt = 0
    For i = 0 To n - 1
        origIdx = dedup_indices(i)
        If ch_nums(origIdx) <= 0 And ch_levels(origIdx) = "special" Then
            sIdx(specialCnt) = origIdx
            specialCnt = specialCnt + 1
        Else
            nIdx(normalCnt) = origIdx
            nVol(normalCnt) = ch_vols(origIdx)
            If ch_nums(origIdx) = 0 Then
                nCh(normalCnt) = 999999
            Else
                nCh(normalCnt) = ch_nums(origIdx)
            End If
            If volMode = "flat" Then nVol(normalCnt) = 0
            normalCnt = normalCnt + 1
        End If
    Next i
    
    ' v3.5 优化：normal 部分用快速排序 O(n log n)
    If normalCnt > 1 Then
        QuickSortByVolCh nIdx, nVol, nCh, 0, normalCnt - 1
    End If
    
    ' 写回：special 在前（保持原顺序），normal 在后（排序后）
    Dim outIdx As Long
    outIdx = 0
    For i = 0 To specialCnt - 1
        dedup_indices(outIdx) = sIdx(i)
        outIdx = outIdx + 1
    Next i
    For i = 0 To normalCnt - 1
        dedup_indices(outIdx) = nIdx(i)
        outIdx = outIdx + 1
    Next i
    ' dedup_count 不变
End Sub


'==============================================================================
' 第五部分：v3 核心新增 —— 深度分析报告
'==============================================================================

'------------------------------------------------------------------------------
' 深度分析入口
'------------------------------------------------------------------------------
Public Sub 分析TXTv3()
    Dim filePath As String
    Dim tSel0 As Double

    g_tTotal0 = Timer
    g_tSelect = 0
    g_regexName = ""
    g_selCount = 0
    g_adRemovedCount = 0

    ' 选择文件
    tSel0 = Timer
    filePath = SelectTxtFile("选择要分析的TXT文件")
    g_tSelect = Timer - tSel0
    If Len(filePath) = 0 Then Exit Sub

    ' v3.4：读取默认设置（卷模式/广告清理/标题级去重）
    LoadSettings

    ' 选择正则
    InitRegexPatterns
    If Not SelectRegexPattern() Then Exit Sub

    ' 执行分析
    DeepAnalyzeFile filePath
End Sub

'------------------------------------------------------------------------------
' 深度分析核心
'------------------------------------------------------------------------------
Private Sub DeepAnalyzeFile(ByVal filePath As String, Optional ByVal outputDir As String = "")
    ' ===== 所有变量集中声明（Option Explicit 要求必须声明）=====
    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim tRead As Double, tScan As Double, t0 As Double
    Dim report As String, lines_arr() As String, rptIdx As Long
    
    ' 统计用
    Dim volCnt As Long, chapCnt As Long, i As Long
    Dim k As Variant           ' 用于 For Each 循环（字典键）
    
    ' 卷结构分析
    Dim volSet As Object, volUnitSet As Object, volChapterCnt As Object
    Dim curVol As Long, curVolLabel As String
    Dim vk As Variant          ' volChapterCnt 的键枚举
    Dim volChs As Object
    Dim firstVolKey As String, secondVolKey As String
    Dim firstDone As Boolean
    Dim vkey As String, vvkey As String
    Dim commonCnt As Long, commonList As String
    Dim cnKey As Variant          ' For Each 遍历字典键必须用 Variant
    Dim firstSet As Object, secondSet As Object
    
    ' 重复分析
    Dim flatMap As Object
    Dim numKey As Variant       ' For Each 遍历字典键必须用 Variant
    Dim uniqueCnt As Long, dupCnt As Long
    Dim topNums() As Long, topCounts() As Long, topCount As Long
    Dim vv As Long, insPos As Long, mv As Long
    Dim countDist As Object
    Dim cc As String
    Dim ntKey As Variant        ' For Each 遍历标题字典键（必须 Variant）
    
    ' 乱序分析
    Dim oooCnt As Long, maxDrop As Long, prevNum As Long
    Dim maxDropInfo_prev As Long, maxDropInfo_cur As Long
    Dim drop As Long
    
    ' 多轨检测
    Dim adjDup As Long, prevChIdx As Long
    Dim adjRatio As Double
    Dim seqLen As Long, maxSeq As Long
    
    ' 格式多样性
    Dim patCnt As Object, unitCnt As Object
    
    ' 章号连续性
    Dim numSet As Object, minNum As Long, maxNum As Long
    Dim expected As Long, missing As Long
    Dim missList As String, missCount As Long, nn As Long
    
    ' 各策略预览
    Dim strategies As Variant, stratNames As Variant
    Dim s_idx As Long, tmpIdx() As Long, tmpCnt As Long, oooAfter As Long, p As Long
    
    ' 输出
    Dim outPath As String
    ' ================================================================

    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(filePath) Then
        MsgBox "源文件不存在：" & vbCrLf & filePath, vbExclamation, "错误"
        Exit Sub
    End If

    ' 读取
    t0 = Timer
    g_detectedEnc = DetectEncodingFile(filePath)
    content = ReadTextAuto(filePath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead = Timer - t0

    ' 扫描
    t0 = Timer
    ScanChaptersV3 lines, lineCount
    DetectTOC                       ' v3.2 新增：目录区自动检测
    tScan = Timer - t0

    ' 构建报告
    ReDim lines_arr(0 To 200)
    rptIdx = 0

    AddRptLine lines_arr, rptIdx, String(70, "=")
    AddRptLine lines_arr, rptIdx, "  深度分析报告: " & fso.GetFileName(filePath)
    AddRptLine lines_arr, rptIdx, String(70, "=")
    AddRptLine lines_arr, rptIdx, "总行数: " & Format(lineCount, "#,##0")
    AddRptLine lines_arr, rptIdx, "总字符: " & Format(Len(content), "#,##0")
    AddRptLine lines_arr, rptIdx, "编码: " & g_detectedEnc

    ' 统计卷和章
    volCnt = 0: chapCnt = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "volume" Then volCnt = volCnt + 1
        If ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then chapCnt = chapCnt + 1
    Next i
    AddRptLine lines_arr, rptIdx, "识别结构: 卷级 " & volCnt & " 个, 章节级 " & chapCnt & " 个"
    If g_tocChapterCount > 0 Then
        AddRptLine lines_arr, rptIdx, "              其中目录区 " & g_tocChapterCount & " 章（已跳过）"
    End If
    AddRptLine lines_arr, rptIdx, "使用正则: " & g_regexName
    AddRptLine lines_arr, rptIdx, ""

    ' 一、卷结构分析
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【一、卷/部结构分析】"
    If volCnt > 0 Then
        Set volSet = CreateObject("Scripting.Dictionary")
        Set volUnitSet = CreateObject("Scripting.Dictionary")
        Set volChapterCnt = CreateObject("Scripting.Dictionary")

        curVol = 0
        curVolLabel = "无卷"
        If Not volChapterCnt.Exists(curVolLabel) Then _
            volChapterCnt.Add curVolLabel, 0

        For i = 0 To ch_count - 1
            If ch_levels(i) = "volume" Then
                curVol = ch_vols(i)
                curVolLabel = "第" & ch_vols(i) & ch_units(i)
                If Not volSet.Exists(ch_vols(i)) Then volSet.Add ch_vols(i), 1
                If Not volUnitSet.Exists(ch_units(i)) Then volUnitSet.Add ch_units(i), 1
                If Not volChapterCnt.Exists(curVolLabel) Then _
                    volChapterCnt.Add curVolLabel, 0
            ElseIf ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then
                volChapterCnt(curVolLabel) = volChapterCnt(curVolLabel) + 1
            End If
        Next i

        AddRptLine lines_arr, rptIdx, "  卷级标题数: " & volCnt
        AddRptLine lines_arr, rptIdx, "  不同卷号数: " & volSet.Count
        AddRptLine lines_arr, rptIdx, "  卷单位词: " & JoinDictKeys(volUnitSet)
        AddRptLine lines_arr, rptIdx, "  各卷章节数:"
        For Each vk In volChapterCnt.Keys
            AddRptLine lines_arr, rptIdx, "    " & vk & ": " & volChapterCnt(vk) & " 章"
        Next vk

        ' 卷间章号重复检测
        If volSet.Count >= 2 Then
            Set volChs = CreateObject("Scripting.Dictionary")
            curVol = 0
            firstDone = False
            firstVolKey = ""
            secondVolKey = ""

            For i = 0 To ch_count - 1
                If ch_levels(i) = "volume" Then
                    curVol = ch_vols(i)
                    vkey = "vol_" & curVol
                    If Not volChs.Exists(vkey) Then
                        volChs.Add vkey, CreateObject("Scripting.Dictionary")
                        If Not firstDone Then
                            firstVolKey = vkey
                            firstDone = True
                        ElseIf Len(secondVolKey) = 0 Then
                            secondVolKey = vkey
                        End If
                    End If
                ElseIf ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
                    vvkey = "vol_" & curVol
                    If Not volChs.Exists(vvkey) Then _
                        volChs.Add vvkey, CreateObject("Scripting.Dictionary")
                    If Not volChs(vvkey).Exists(ch_nums(i)) Then _
                        volChs(vvkey).Add ch_nums(i), 1
                End If
            Next i

            If Len(firstVolKey) > 0 And Len(secondVolKey) > 0 Then
                commonCnt = 0
                commonList = ""
                Set firstSet = volChs(firstVolKey)
                Set secondSet = volChs(secondVolKey)
                If firstSet.Count > 0 And secondSet.Count > 0 Then
                    For Each cnKey In firstSet.Keys
                        If secondSet.Exists(cnKey) Then
                            commonCnt = commonCnt + 1
                            If commonCnt <= 10 Then
                                If Len(commonList) > 0 Then commonList = commonList & ","
                                commonList = commonList & cnKey
                            End If
                        End If
                    Next cnKey
                End If
                If commonCnt > 0 Then
                    AddRptLine lines_arr, rptIdx, ""
                    AddRptLine lines_arr, rptIdx, "  ⚠ 卷间章号重复: " & firstVolKey & " 和 " & secondVolKey & _
                              " 共享 " & commonCnt & " 个章号"
                    AddRptLine lines_arr, rptIdx, "    示例: " & commonList & "..."
                End If
            End If
            Set volChs = Nothing
        End If

        Set volSet = Nothing
        Set volUnitSet = Nothing
        Set volChapterCnt = Nothing
    Else
        AddRptLine lines_arr, rptIdx, "  未检测到卷/部/册级结构"
    End If
    AddRptLine lines_arr, rptIdx, ""

    ' 二、重复分析
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【二、重复章节分析】"
    AddRptLine lines_arr, rptIdx, "  扁平视角（忽略卷）:"

    Set flatMap = CreateObject("Scripting.Dictionary")
    ' v3.5 优化：同时建立章号信息索引（标题+前5行号），避免Top10时O(M*N)遍历
    Dim infoMap As Object
    Set infoMap = CreateObject("Scripting.Dictionary")
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
            numKey = CStr(ch_nums(i))
            If Not flatMap.Exists(numKey) Then
                flatMap.Add numKey, 1
                ' 首次出现：记录标题和行号
                infoMap.Add numKey, ch_titles(i) & "|" & (ch_starts(i) + 1)
            Else
                flatMap(numKey) = flatMap(numKey) + 1
                ' 后续出现：追加行号（最多5个）
                Dim infoParts() As String, lineList As String, lineCnt As Long
                infoParts = Split(infoMap(numKey), "|")
                lineList = infoParts(1)
                lineCnt = UBound(Split(lineList, "、")) + 1
                If lineCnt < 5 Then
                    infoMap(numKey) = infoParts(0) & "|" & lineList & "、" & (ch_starts(i) + 1)
                End If
            End If
        End If
    Next i

    uniqueCnt = flatMap.Count
    dupCnt = 0
    For Each k In flatMap.Keys
        If flatMap(k) > 1 Then dupCnt = dupCnt + 1
    Next k

    AddRptLine lines_arr, rptIdx, "    不重复章号数: " & uniqueCnt
    AddRptLine lines_arr, rptIdx, "    存在重复的章号数: " & dupCnt

    If dupCnt > 0 Then
        ' 找重复最严重的10个（带标题和行号，避免只看章号混淆）
        topCount = 0
        ReDim topNums(0 To 9)
        ReDim topCounts(0 To 9)
        ReDim topTitles(0 To 9)       ' 首次出现的完整标题
        ReDim topLineInfo(0 To 9)     ' 前几次出现的行号

        For Each k In flatMap.Keys
            If flatMap(k) > 1 Then
                vv = flatMap(k)
                insPos = topCount
                ' 注意：VBA 的 And 不短路求值，必须分开判断，
                ' 否则 insPos=0 时 topCounts(-1) 会报"下标越界"
                Do While insPos > 0
                    If topCounts(insPos - 1) < vv Then
                        insPos = insPos - 1
                    Else
                        Exit Do
                    End If
                Loop
                If insPos < 10 Then
                    For mv = IIf(topCount < 9, topCount, 9) To insPos + 1 Step -1
                        topNums(mv) = topNums(mv - 1)
                        topCounts(mv) = topCounts(mv - 1)
                        topTitles(mv) = topTitles(mv - 1)
                        topLineInfo(mv) = topLineInfo(mv - 1)
                    Next mv
                    topNums(insPos) = CLng(k)
                    topCounts(insPos) = vv
                    ' v3.5 优化：直接从预建索引取标题和行号（O(1)，不再O(N)遍历）
                    Dim infoArr() As String
                    infoArr = Split(infoMap(CStr(k)), "|")
                    topTitles(insPos) = infoArr(0)
                    topLineInfo(insPos) = infoArr(1)
                    If topCount < 10 Then topCount = topCount + 1
                End If
            End If
        Next k

        AddRptLine lines_arr, rptIdx, ""
        AddRptLine lines_arr, rptIdx, "    重复最严重的前10个章号："
        For i = 0 To topCount - 1
            AddRptLine lines_arr, rptIdx, "      第" & topNums(i) & "章 (" & topCounts(i) & "次): " & topTitles(i)
            AddRptLine lines_arr, rptIdx, "        出现行号: " & topLineInfo(i)
        Next i

        ' 重复次数分布
        Set countDist = CreateObject("Scripting.Dictionary")
        For Each k In flatMap.Keys
            cc = CStr(flatMap(k))
            If Not countDist.Exists(cc) Then countDist.Add cc, 0
            countDist(cc) = countDist(cc) + 1
        Next k
        AddRptLine lines_arr, rptIdx, ""
        AddRptLine lines_arr, rptIdx, "    重复次数分布："
        For Each k In countDist.Keys
            AddRptLine lines_arr, rptIdx, "      出现" & k & "次的章号: " & countDist(k) & "个"
        Next k
        Set countDist = Nothing
        
        ' v3.3 新增：同章异题统计（章号相同但标题不同，全部列出）
        Dim titleDiffCnt As Long
        Dim titleDiffDict As Object, titleDiffCntDict As Object
        Dim normTitles As Object, chk As Long
        Dim ntStr As String, tdTitles As String, ttIdx As Long
        Set titleDiffDict = CreateObject("Scripting.Dictionary")    ' 章号 → 所有不同标题（换行分隔）
        Set titleDiffCntDict = CreateObject("Scripting.Dictionary") ' 章号 → 不同标题数
        titleDiffCnt = 0
        
        For Each numKey In flatMap.Keys
            cc = CStr(flatMap(numKey))
            If CLng(cc) <= 1 Then GoTo NextNumKey
            
            Set normTitles = CreateObject("Scripting.Dictionary")
            For chk = 0 To ch_count - 1
                If ch_levels(chk) = "chapter" And ch_nums(chk) = CLng(numKey) Then
                    ntStr = NormalizeTitle(ch_titles(chk))
                    If Not normTitles.Exists(ntStr) Then normTitles.Add ntStr, 1
                End If
            Next chk
            
            If normTitles.Count > 1 Then
                titleDiffCnt = titleDiffCnt + 1
                ' 收集所有不同的标题（完整显示，不截断，避免混淆）
                ttIdx = 0
                tdTitles = ""
                For Each ntKey In normTitles.Keys
                    If ttIdx > 0 Then tdTitles = tdTitles & vbCrLf
                    tdTitles = tdTitles & "        · " & CStr(ntKey)
                    ttIdx = ttIdx + 1
                Next ntKey
                titleDiffDict.Add CStr(numKey), tdTitles
                titleDiffCntDict.Add CStr(numKey), normTitles.Count
            End If
            Set normTitles = Nothing
NextNumKey:
        Next numKey
        
        g_titleDiffCount = titleDiffCnt
        If titleDiffCnt > 0 Then
            AddRptLine lines_arr, rptIdx, ""
            AddRptLine lines_arr, rptIdx, "  ⚠ 章号相同但标题不同: " & titleDiffCnt & " 个章号"
            AddRptLine lines_arr, rptIdx, "    （仅按章号去重可能误删，建议启用标题级去重）"
            AddRptLine lines_arr, rptIdx, "    完整列表："
            Dim tdKey As Variant
            For Each tdKey In titleDiffDict.Keys
                AddRptLine lines_arr, rptIdx, "      第" & tdKey & "章（" & titleDiffCntDict(tdKey) & "个不同标题）:"
                AddRptLine lines_arr, rptIdx, titleDiffDict(tdKey)
            Next tdKey
        End If
        Set titleDiffDict = Nothing
        Set titleDiffCntDict = Nothing
    End If
    Set infoMap = Nothing
    Set flatMap = Nothing
    AddRptLine lines_arr, rptIdx, ""

    ' 三、乱序分析
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【三、乱序分析】"
    AddRptLine lines_arr, rptIdx, "  扁平视角（忽略卷）:"

    oooCnt = 0: maxDrop = 0: prevNum = 0
    maxDropInfo_prev = 0: maxDropInfo_cur = 0

    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
            If prevNum > 0 And ch_nums(i) < prevNum Then
                oooCnt = oooCnt + 1
                drop = prevNum - ch_nums(i)
                If drop > maxDrop Then
                    maxDrop = drop
                    maxDropInfo_prev = prevNum
                    maxDropInfo_cur = ch_nums(i)
                End If
            End If
            prevNum = ch_nums(i)
        End If
    Next i

    AddRptLine lines_arr, rptIdx, "    乱序次数: " & oooCnt
    If maxDrop > 0 Then
        AddRptLine lines_arr, rptIdx, "    最大跌幅: 第" & maxDropInfo_prev & _
                                  "章 → 第" & maxDropInfo_cur & "章 (跌" & maxDrop & ")"
    End If
    AddRptLine lines_arr, rptIdx, ""

    ' 四、多轨目录检测
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【四、多轨目录检测】"
    
    ' v3.2 新增：目录区自动检测结果
    If g_tocChapterCount > 0 Then
        AddRptLine lines_arr, rptIdx, "  ⚠ 检测到目录区（已自动跳过，不参与去重/排序）"
        AddRptLine lines_arr, rptIdx, "    目录章节数: " & g_tocChapterCount & " 章"
        AddRptLine lines_arr, rptIdx, "    目录位置: 第 " & (g_tocStartIdx + 1) & " - " & (g_tocEndIdx + 1) & " 个识别项"
        If g_tocStartIdx >= 0 And g_tocStartIdx < ch_count Then
            AddRptLine lines_arr, rptIdx, "    起始标题: " & ch_titles(g_tocStartIdx)
        End If
    Else
        AddRptLine lines_arr, rptIdx, "  未检测到独立目录区"
    End If
    AddRptLine lines_arr, rptIdx, ""

    ' 相邻双标题比例
    adjDup = 0: prevChIdx = -1
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
            If prevChIdx >= 0 Then
                If ch_nums(i) = ch_nums(prevChIdx) And _
                   ch_starts(i) - ch_starts(prevChIdx) <= 2 Then
                    adjDup = adjDup + 1
                End If
            End If
            prevChIdx = i
        End If
    Next i

    If chapCnt > 0 Then adjRatio = adjDup / chapCnt
    AddRptLine lines_arr, rptIdx, "  相邻双标题数: " & adjDup & " (占比 " & Format(adjRatio, "0.0%") & ")"
    If adjRatio > 0.3 Then
        AddRptLine lines_arr, rptIdx, "  → 疑似每章双标题结构（目录式+正文式各一次）"
    End If

    ' 最长连续递增段
    If chapCnt > 1 Then
        seqLen = 1: maxSeq = 1
        prevNum = 0
        For i = 0 To ch_count - 1
            If ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
                If prevNum > 0 And ch_nums(i) = prevNum + 1 Then
                    seqLen = seqLen + 1
                    If seqLen > maxSeq Then maxSeq = seqLen
                Else
                    seqLen = 1
                End If
                prevNum = ch_nums(i)
            End If
        Next i
        AddRptLine lines_arr, rptIdx, "  最长连续递增章号段长度: " & maxSeq
    End If
    AddRptLine lines_arr, rptIdx, ""

    ' 五、格式多样性
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【五、格式多样性分析】"
    Set patCnt = CreateObject("Scripting.Dictionary")
    Set unitCnt = CreateObject("Scripting.Dictionary")
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" Or ch_levels(i) = "special" Then
            If Not patCnt.Exists(ch_patterns(i)) Then patCnt.Add ch_patterns(i), 0
            patCnt(ch_patterns(i)) = patCnt(ch_patterns(i)) + 1
            If Not unitCnt.Exists(ch_units(i)) Then unitCnt.Add ch_units(i), 0
            unitCnt(ch_units(i)) = unitCnt(ch_units(i)) + 1
        End If
    Next i

    AddRptLine lines_arr, rptIdx, "  正则类型分布:"
    For Each k In patCnt.Keys
        AddRptLine lines_arr, rptIdx, "    " & Left(k & Space(15), 15) & ": " & _
                patCnt(k) & " 章"
    Next k

    AddRptLine lines_arr, rptIdx, "  单位词分布:"
    For Each k In unitCnt.Keys
        AddRptLine lines_arr, rptIdx, "    " & Left(k & Space(6), 6) & ": " & unitCnt(k) & " 章"
    Next k
    Set patCnt = Nothing
    Set unitCnt = Nothing
    AddRptLine lines_arr, rptIdx, ""

    ' 六、章号连续性
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【六、章号连续性分析】"
    Set numSet = CreateObject("Scripting.Dictionary")
    minNum = 999999: maxNum = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 Then
            If Not numSet.Exists(ch_nums(i)) Then numSet.Add ch_nums(i), 1
            If ch_nums(i) < minNum Then minNum = ch_nums(i)
            If ch_nums(i) > maxNum Then maxNum = ch_nums(i)
        End If
    Next i

    If numSet.Count > 0 Then
        expected = maxNum - minNum + 1
        missing = expected - numSet.Count
        AddRptLine lines_arr, rptIdx, "  章号范围: " & minNum & " - " & maxNum
        AddRptLine lines_arr, rptIdx, "  应有章节数: " & expected
        AddRptLine lines_arr, rptIdx, "  实际章号数: " & numSet.Count
        AddRptLine lines_arr, rptIdx, "  缺失章号数: " & missing

        If missing > 0 Then
            AddRptLine lines_arr, rptIdx, "  缺失章号（全部列出，共" & missing & "个）:"
            missCount = 0
            missList = ""
            For nn = minNum To maxNum
                If Not numSet.Exists(nn) Then
                    If missCount > 0 And missCount Mod 20 = 0 Then
                        AddRptLine lines_arr, rptIdx, "    " & missList & ","
                        missList = ""
                    End If
                    If Len(missList) > 0 Then missList = missList & ","
                    missList = missList & nn
                    missCount = missCount + 1
                End If
            Next nn
            If Len(missList) > 0 Then
                AddRptLine lines_arr, rptIdx, "    " & missList
            End If
        End If
    End If
    Set numSet = Nothing
    AddRptLine lines_arr, rptIdx, ""

    ' 七、各策略效果预览
    AddRptLine lines_arr, rptIdx, String(50, "-")
    AddRptLine lines_arr, rptIdx, "【七、各策略组合效果预览（扁平模式）】"
    
    ' v3.2 修复：原代码将 lis/sort 作为去重策略传入导致溢出
    ' 正确做法：6种组合（去重策略 + 排序策略配对），与Python版一致
    Dim comboLabels() As String, comboDedup() As String, comboSort() As String
    ReDim comboLabels(0 To 5)
    ReDim comboDedup(0 To 5)
    ReDim comboSort(0 To 5)
    comboLabels(0) = "none+none":     comboDedup(0) = "none":    comboSort(0) = "none"
    comboLabels(1) = "none+sort":     comboDedup(1) = "none":    comboSort(1) = "sort"
    comboLabels(2) = "first+none":    comboDedup(2) = "first":   comboSort(2) = "none"
    comboLabels(3) = "first+sort":    comboDedup(3) = "first":   comboSort(3) = "sort"
    comboLabels(4) = "longest+none":  comboDedup(4) = "longest": comboSort(4) = "none"
    comboLabels(5) = "longest+sort":  comboDedup(5) = "longest": comboSort(5) = "sort"

    For s_idx = 0 To 5
        ApplyDedup comboDedup(s_idx), "flat", g_titleDedup
        ApplySort comboSort(s_idx), "flat"
        tmpIdx = dedup_indices
        tmpCnt = dedup_count

        ' 统计乱序
        oooAfter = 0
        prevNum = 0
        For p = 0 To tmpCnt - 1
            If ch_nums(tmpIdx(p)) > 0 Then
                If prevNum > 0 And ch_nums(tmpIdx(p)) < prevNum Then
                    oooAfter = oooAfter + 1
                End If
                prevNum = ch_nums(tmpIdx(p))
            End If
        Next p

        AddRptLine lines_arr, rptIdx, "  " & Left(comboLabels(s_idx) & Space(14), 14) & _
                ": 剩" & Format(tmpCnt, "@@@") & "章, 乱序" & Format(oooAfter, "@@@") & "处"
    Next s_idx

    AddRptLine lines_arr, rptIdx, ""

    ' 处理建议
    AddRptLine lines_arr, rptIdx, String(70, "=")
    AddRptLine lines_arr, rptIdx, "  处理建议："

    If oooCnt > 10 Then
        AddRptLine lines_arr, rptIdx, "  • 乱序严重，推荐 sort 策略（最彻底）或 lis 策略（智能）"
    ElseIf dupCnt > 0 Then
        AddRptLine lines_arr, rptIdx, "  • 有重复但乱序轻微，推荐 longest 策略（保留内容最长的）"
    End If
    If adjRatio > 0.3 Then
        AddRptLine lines_arr, rptIdx, "  • 每章双标题明显，组合3（保留最长+不排序）即可解决大部分问题"
    End If
    If volCnt > 1 Then
        AddRptLine lines_arr, rptIdx, "  • 检测到多卷结构，注意选择正确的卷模式"
    End If

    AddRptLine lines_arr, rptIdx, String(70, "=")

    ' v3.4：构建【总】结论与建议（置于报告开头，明细保留在【分】之后）
    Dim summary As String
    Dim recCombo As String
    Dim autoN As Long
    Dim volStructDesc As String, tocDesc As String

    ' 推荐组合（与自动TXTv3相同的自动决策规则）
    If dupCnt = 0 And oooCnt = 0 Then
        recCombo = "none+none（干净型：不去重不排序）"
    ElseIf adjRatio >= 0.3 And oooCnt < 10 Then
        recCombo = "longest+none（双标题型：保留最长不排序）"
    ElseIf oooCnt >= 10 Then
        recCombo = "longest+sort（乱序严重：保留最长并排序）"
    ElseIf dupCnt > 0 Then
        recCombo = "longest+none（仅重复：保留最长不排序）"
    Else
        recCombo = "longest+sort（稳妥默认）"
    End If

    ' 建议清洁N值（v3.6：直接读预计算结果，O(章节数)）
    autoN = AutoNFromBodies()

    If volCnt > 0 Then
        volStructDesc = "有卷（卷级标题 " & volCnt & " 个）"
    Else
        volStructDesc = "无卷"
    End If
    If g_tocChapterCount > 0 Then
        tocDesc = "有（" & g_tocChapterCount & " 章，已跳过）"
    Else
        tocDesc = "无"
    End If

    summary = "【总】结论与建议" & vbCrLf & _
              "  问题计数：" & vbCrLf & _
              "    重复章号数：" & dupCnt & vbCrLf & _
              "    乱序处数：" & oooCnt & vbCrLf & _
              "    卷结构：" & volStructDesc & vbCrLf & _
              "    同章异题数：" & g_titleDiffCount & vbCrLf & _
              "    目录区：" & tocDesc & vbCrLf & _
              "  推荐组合：" & recCombo & vbCrLf & _
              "  建议清洁N值：" & autoN & vbCrLf & _
              String(50, "-") & vbCrLf & _
              "【分】各维度明细" & vbCrLf

    ' 输出报告（总-分结构）
    report = summary & JoinArr(lines_arr, rptIdx)
    Debug.Print report

    ' 写报告文件
    If Len(outputDir) > 0 Then
        outPath = outputDir & "\分析报告.txt"
    Else
        outPath = fso.GetParentFolderName(filePath) & "\" & fso.GetBaseName(filePath) & "_分析报告.txt"
    End If
    WriteTextUTF8NoBOM outPath, report
    If Len(outputDir) = 0 Then
        MsgBox "【总】分析完成" & vbCrLf & _
               "  重复章号 " & dupCnt & "｜乱序 " & oooCnt & " 处｜同章异题 " & g_titleDiffCount & vbCrLf & _
               "  推荐组合：" & recCombo & vbCrLf & _
               "  建议清洁N值：" & autoN & vbCrLf & vbCrLf & _
               "报告已保存：" & vbCrLf & outPath, _
               vbInformation, "分析完成"
    End If

    Set fso = Nothing
End Sub

' 辅助：报告行追加
Private Sub AddRptLine(arr() As String, ByRef idx As Long, ByVal line As String)
    If idx > UBound(arr) Then ReDim Preserve arr(0 To UBound(arr) + 100)
    arr(idx) = line
    idx = idx + 1
End Sub

' 辅助：数组合并
Private Function JoinArr(arr() As String, ByVal count As Long) As String
    Dim result As String, i As Long
    result = ""
    For i = 0 To count - 1
        If i > 0 Then result = result & vbCrLf
        result = result & arr(i)
    Next i
    JoinArr = result
End Function

' 辅助：字典键值拼接
Private Function JoinDictKeys(d As Object) As String
    Dim result As String, k As Variant
    result = ""
    For Each k In d.Keys
        If Len(result) > 0 Then result = result & ", "
        result = result & k
    Next k
    JoinDictKeys = result
End Function


'==============================================================================
' 第六部分：主入口 —— 拆分TXTv3
'==============================================================================

Public Sub 拆分TXTv3()
    Dim filePath As String
    Dim tSel0 As Double
    Dim prompt As String
    Dim outInput As String, modeStr As String, paramStr As String
    Dim spPos As Long
    Dim cleanN As Long
    Dim chunkStr As String
    Dim selIdx As Long
    Dim unitInput As String

    ' 初始化
    g_tTotal0 = Timer
    g_tSelect = 0
    g_regexName = ""
    g_selCount = 0
    g_dedupStrategy = "longest"
    g_sortStrategy = "sort"
    g_adRemovedCount = 0
    g_dedupRemoved = 0
    g_oooFixed = 0
    g_skipTitleOnly = 0
    g_skipShortBody = 0

    ' 弹窗1：选择文件
    tSel0 = Timer
    filePath = SelectTxtFile("选择要拆分的TXT文件")
    g_tSelect = Timer - tSel0
    If Len(filePath) = 0 Then Exit Sub

    ' 弹窗2：选择正则（多选）
    InitRegexPatterns
    If Not SelectRegexPattern() Then Exit Sub

    ' 弹窗3：去重+排序组合（六选一）
    If Not SelectDedupSortCombo() Then Exit Sub

    ' 卷模式/广告清理/标题级去重：改由设置读取（见 设置TXTv3）
    LoadSettings

    ' 弹窗4：输出模式+参数一体输入
    prompt = "【步骤4/4】请选择输出模式（可带参数）：" & vbCrLf & vbCrLf & _
             "  1. 清洁模式（默认）" & vbCrLf & _
             "       每章一个文件 + 生成 保留≥N / 清理<N 两个合并文件" & vbCrLf & _
             "       输入 1 → N=100；输入 1 200 → N=200" & vbCrLf & _
             "  2. 聚合模式（多章合并为一份）" & vbCrLf & _
             "       输入 2 → 40,3；输入 2 20,1|20,1|80,1 → 自定义" & vbCrLf & vbCrLf & _
             "请输入："
    outInput = InputBox(prompt, "输出模式+参数", "1")
    If StrPtr(outInput) = 0 Then Exit Sub

    outInput = NormalizeSeparators(outInput)
    outInput = Trim(outInput)
    If Len(outInput) = 0 Then
        MsgBox "未输入模式。", vbExclamation, "提示"
        Exit Sub
    End If

    ' 解析：按第一个空格切开，前段=模式，后段=参数（参数内可含逗号和竖线）
    spPos = InStr(outInput, " ")
    If spPos > 0 Then
        modeStr = Trim(Left(outInput, spPos - 1))
        paramStr = Trim(Mid(outInput, spPos + 1))
    Else
        modeStr = outInput
        paramStr = ""
    End If

    If modeStr = "1" Then
        ' 清洁模式（每章一个文件 + 两个合并文件）
        If Len(paramStr) = 0 Then
            cleanN = 100
        Else
            If Not IsDigits(paramStr) Then
                MsgBox "清洁模式参数应为正整数（最小正文字数）。", vbExclamation, "提示"
                Exit Sub
            End If
            cleanN = CLng(paramStr)
        End If
        SplitByChapterV3 InputPath:=filePath, GenerateTitleOnly:=False, _
                         MinBodyLen:=cleanN, MergeFlag:=2
    ElseIf modeStr = "2" Then
        ' 聚合模式
        If Len(paramStr) = 0 Then
            chunkStr = "40,3"
        Else
            chunkStr = paramStr
        End If

        ' 自定义正则的单位词询问（聚合时保留）
        For selIdx = 0 To g_selCount - 1
            If g_selOrigIndices(selIdx) = g_regexCount Then
                unitInput = InputBox("检测到自定义正则，请输入聚合拆分用的单位词：", _
                                      "聚合拆分单位词", "章")
                If StrPtr(unitInput) = 0 Or Len(Trim(unitInput)) = 0 Then
                    g_selDefaultUnits(selIdx) = "章"
                Else
                    g_selDefaultUnits(selIdx) = Trim(unitInput)
                End If
            End If
        Next selIdx

        SplitByGroupsV3 InputPath:=filePath, ChunkStr:=chunkStr
    Else
        MsgBox "无效模式：" & modeStr & "（应为 1 或 2）。", vbExclamation, "提示"
        Exit Sub
    End If
End Sub

'------------------------------------------------------------------------------
' v3.4 新增：自动化入口
'   弹窗1选文件 → LoadSettings → 读取+扫描+DetectTOC → 自动决策 → 确认 → 执行 → 总-分报告
'------------------------------------------------------------------------------
Public Sub 自动TXTv3()
    Dim filePath As String
    Dim tSel0 As Double
    Dim content As String, lines() As String, lineCount As Long
    Dim tRead As Double, tScan As Double, t0 As Double
    Dim fso As Object
    Dim autoDir As String, autoSubDir As String
    Dim dupCnt As Long, oooCnt As Long, adjRatio As Double
    Dim recDedup As String, recSort As String, recComboStr As String
    Dim autoN As Long
    Dim confirmMsg As String
    Dim volCnt As Long, i As Long

    ' 初始化
    g_tTotal0 = Timer
    g_tSelect = 0
    g_regexName = ""
    g_selCount = 0
    g_adRemovedCount = 0
    g_dedupRemoved = 0
    g_oooFixed = 0
    g_skipTitleOnly = 0
    g_skipShortBody = 0

    ' 弹窗1：选择文件
    tSel0 = Timer
    filePath = SelectTxtFile("选择要自动拆分的TXT文件")
    g_tSelect = Timer - tSel0
    If Len(filePath) = 0 Then Exit Sub

    ' 读取设置（卷模式/广告/标题）
    LoadSettings

    Set fso = CreateObject("Scripting.FileSystemObject")

    ' 读取并扫描
    t0 = Timer
    g_detectedEnc = DetectEncodingFile(filePath)
    content = ReadTextAuto(filePath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead = Timer - t0

    ' 自动正则：固定 "1,4"（标准中文+无号）
    InitRegexPatterns
    Dim autoPatterns As String
    autoPatterns = "1,4"
    autoPatterns = Replace(Trim(autoPatterns), " ", ",")
    ' 直接填充正则数组（不弹InputBox）
    Dim parts() As String, p As Long, idx As Long
    parts = Split(autoPatterns, ",")
    ReDim g_selPatterns(0 To UBound(parts))
    ReDim g_selUnitGroups(0 To UBound(parts))
    ReDim g_selDefaultUnits(0 To UBound(parts))
    ReDim g_selOrigIndices(0 To UBound(parts))
    g_selCount = 0
    For p = 0 To UBound(parts)
        idx = CLng(Trim(parts(p)))
        g_selPatterns(g_selCount) = g_regexPatterns(idx)
        g_selUnitGroups(g_selCount) = g_regexUnitGroups(idx)
        g_selDefaultUnits(g_selCount) = g_regexDefaultUnits(idx)
        g_selOrigIndices(g_selCount) = idx
        g_selCount = g_selCount + 1
    Next p
    g_regexName = "标准中文 + 序章/楔子"

    t0 = Timer
    ScanChaptersV3 lines, lineCount
    DetectTOC
    tScan = Timer - t0
    If ch_count = 0 Then
        MsgBox "未识别到任何章节标题。", vbExclamation, "提示"
        Exit Sub
    End If

    ' 自动决策：统计（仅用 ch_num>0 且非目录区章节）
    Dim flatMap As Object
    Dim numKey As Variant, adjDup As Long, prevChIdx As Long
    Dim seqLen As Long, maxSeq As Long, prevNum As Long
    Dim chapCnt As Long
    chapCnt = 0: dupCnt = 0: oooCnt = 0: adjDup = 0: prevChIdx = -1

    Set flatMap = CreateObject("Scripting.Dictionary")
    For i = 0 To ch_count - 1
        If ch_levels(i) = "chapter" And ch_nums(i) > 0 And Not ch_isTOC(i) Then
            chapCnt = chapCnt + 1
            numKey = CStr(ch_nums(i))
            If Not flatMap.Exists(numKey) Then flatMap.Add numKey, 0
            flatMap(numKey) = flatMap(numKey) + 1

            ' 乱序
            If prevNum > 0 And ch_nums(i) < prevNum Then oooCnt = oooCnt + 1
            prevNum = ch_nums(i)

            ' 相邻双标题
            If prevChIdx >= 0 Then
                If ch_nums(i) = ch_nums(prevChIdx) And _
                   ch_starts(i) - ch_starts(prevChIdx) <= 2 Then
                    adjDup = adjDup + 1
                End If
            End If
            prevChIdx = i
        End If
    Next i
    For Each numKey In flatMap.Keys
        If flatMap(numKey) > 1 Then dupCnt = dupCnt + 1
    Next numKey
    Set flatMap = Nothing
    If chapCnt > 0 Then adjRatio = adjDup / chapCnt

    ' 自动决策规则
    If dupCnt = 0 And oooCnt = 0 Then
        recDedup = "none": recSort = "none"
        recComboStr = "none+none（干净型）"
    ElseIf adjRatio >= 0.3 And oooCnt < 10 Then
        recDedup = "longest": recSort = "none"
        recComboStr = "longest+none（双标题型）"
    ElseIf oooCnt >= 10 Then
        recDedup = "longest": recSort = "sort"
        recComboStr = "longest+sort（乱序严重）"
    ElseIf dupCnt > 0 Then
        recDedup = "longest": recSort = "none"
        recComboStr = "longest+none（仅重复）"
    Else
        recDedup = "longest": recSort = "sort"
        recComboStr = "longest+sort（稳妥默认）"
    End If

    ' 自动判定N（v3.6：直接读预计算结果，O(章节数)）
    autoN = AutoNFromBodies()

    ' 卷结构统计
    volCnt = 0
    For i = 0 To ch_count - 1
        If ch_levels(i) = "volume" Then volCnt = volCnt + 1
    Next i

    ' 确认弹窗
    confirmMsg = "【自动方案】" & vbCrLf & _
                 "  正则：标准中文 + 无号章节" & vbCrLf & _
                 "  去重+排序：" & recComboStr & vbCrLf & _
                 "  理由：重复章号=" & dupCnt & "，乱序=" & oooCnt & "，相邻双标题占比=" & Format(adjRatio, "0.0%") & vbCrLf & _
                 "  清洁N值：" & autoN & vbCrLf & _
                 "  卷模式：" & g_volumeMode & "（" & IIf(volCnt > 1, "检测多卷", "扁平") & "）" & vbCrLf & _
                 "  广告清理：" & IIf(g_cleanAds, "是", "否") & vbCrLf & _
                 "  标题级去重：" & IIf(g_titleDedup, "是", "否") & vbCrLf & vbCrLf & _
                 "[确定]执行   [取消]退出"
    If MsgBox(confirmMsg, vbOKCancel + vbQuestion, "自动TXTv3 - 确认方案") <> vbOK Then Exit Sub

    ' 执行
    g_dedupStrategy = recDedup
    g_sortStrategy = recSort

    autoDir = fso.GetParentFolderName(filePath) & "\" & fso.GetBaseName(filePath) & "_自动"
    autoSubDir = autoDir & "\拆分文档"
    If Dir(autoDir, vbDirectory) = "" Then MkDir autoDir
    If Dir(autoSubDir, vbDirectory) = "" Then MkDir autoSubDir

    ' 生成分析报告
    DeepAnalyzeFile filePath, autoDir

    ' 拆分（清洁模式，MergeFlag=2，合并文件直接写到 autoDir）
    SplitByChapterV3 InputPath:=filePath, OutputDir:=autoSubDir, _
                     GenerateTitleOnly:=False, MinBodyLen:=autoN, _
                     MergeFlag:=2, MergeOutputDir:=autoDir

End Sub


'==============================================================================
' 第七部分：核心拆分过程 v3（含去重+卷感知）
'==============================================================================

'------------------------------------------------------------------------------
' 确定实际卷模式
'------------------------------------------------------------------------------
Private Function ResolveVolMode(ByVal mode As String) As String
    If mode = "flat" Then
        ResolveVolMode = "flat"
        Exit Function
    End If
    ' auto 或 by_volume：先检测是否有卷
    Dim hasVol As Boolean, i As Long
    hasVol = False
    Dim volSet As Object
    Set volSet = CreateObject("Scripting.Dictionary")
    For i = 0 To ch_count - 1
        If ch_levels(i) = "volume" And ch_vols(i) > 0 Then
            If Not volSet.Exists(ch_vols(i)) Then volSet.Add ch_vols(i), 1
            If volSet.Count >= 2 Then
                hasVol = True
                Exit For
            End If
        End If
    Next i
    Set volSet = Nothing

    If hasVol Then
        ResolveVolMode = "volume"
    Else
        ResolveVolMode = "flat"
    End If
End Function

'------------------------------------------------------------------------------
' 按章节一一拆分 v3
'------------------------------------------------------------------------------
Public Sub SplitByChapterV3(ByVal InputPath As String, _
                            Optional ByVal OutputDir As String = "", _
                            Optional ByVal FileNamePrefix As String = "", _
                            Optional ByVal SerialWidth As Long = 3, _
                            Optional ByVal GenerateTitleOnly As Boolean = False, _
                            Optional ByVal MinBodyLen As Long = 0, _
                            Optional ByVal MergeFlag As Long = -1, _
                            Optional ByVal MergeOutputDir As String = "")
    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim tRead As Double, tScan As Double, tDedup As Double, tWrite As Double
    Dim t0 As Double
    Dim outDirFull As String
    Dim actualVolMode As String, byVolFlag As Boolean
    Dim chapIdxTmp() As Long
    Dim chapBefore As Long, tSort As Double, oooBefore As Long

    If g_tTotal0 = 0 Then g_tTotal0 = Timer

    ' 1. 读取
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(InputPath) Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    t0 = Timer
    g_detectedEnc = DetectEncodingFile(InputPath)
    content = ReadTextAuto(InputPath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead = Timer - t0

    ' 2. 扫描（v3增强版）
    t0 = Timer
    ScanChaptersV3 lines, lineCount
    DetectTOC                       ' v3.2 新增：目录区自动检测
    tScan = Timer - t0
    If ch_count = 0 Then
        MsgBox "未识别到任何章节标题。" & vbCrLf & _
               "使用正则：" & g_regexName, vbExclamation, "提示"
        Exit Sub
    End If

    ' 3. 确定卷模式
    actualVolMode = ResolveVolMode(g_volumeMode)
    byVolFlag = (g_volumeMode = "by_volume" And actualVolMode = "volume")
    g_actualVolMode = actualVolMode

    ' 4. 去重（统计减少章数）
    GetChapterIndices chapIdxTmp, chapBefore
    t0 = Timer
    ApplyDedup g_dedupStrategy, actualVolMode, g_titleDedup
    tDedup = Timer - t0
    g_dedupRemoved = chapBefore - dedup_count

    If dedup_count = 0 Then
        MsgBox "去重后无有效章节！", vbExclamation, "错误"
        Exit Sub
    End If

    ' 4b. 排序（统计乱序修复处数）
    t0 = Timer
    oooBefore = CountOOOInDedup()
    ApplySort g_sortStrategy, actualVolMode
    tSort = Timer - t0
    g_oooFixed = oooBefore - CountOOOInDedup()

    If dedup_count = 0 Then
        MsgBox "排序后无有效章节！", vbExclamation, "错误"
        Exit Sub
    End If

    ' 5. 输出目录
    outDirFull = ResolveOutputDir(fso, InputPath, OutputDir, "_拆分")
    If Dir(outDirFull, vbDirectory) = "" Then MkDir outDirFull
    CleanOutputDir outDirFull

    ' 6. 序号位数
    If Len(CStr(dedup_count)) > SerialWidth Then SerialWidth = Len(CStr(dedup_count))
    Dim serialFmt As String
    serialFmt = String(SerialWidth, "0")

    ' 7. 预计算字数（v3.6 优化：直接读扫描时预计算的结果，O(章节数)）
    Dim charCounts() As Long, maxChars As Long, charWidth As Long, charFmt As String
    ReDim charCounts(0 To dedup_count - 1)
    maxChars = 0
    Dim i As Long, j As Long, origIdx As Long, n As Long
    For i = 0 To dedup_count - 1
        origIdx = dedup_indices(i)
        charCounts(i) = ch_charCounts(origIdx)
        If charCounts(i) > maxChars Then maxChars = charCounts(i)
    Next i
    charWidth = Len(CStr(maxChars))
    If charWidth < 1 Then charWidth = 1
    charFmt = String(charWidth, "0")

    ' 8. 写文件
    Dim titleOnlyCount As Long, writtenCount As Long, skippedCount As Long
    Dim shortBodyCount As Long, bodyLen As Long, isInsufficient As Boolean
    Dim top1 As Long, top2 As Long, top3 As Long, topStr As String
    Dim keptTexts As Collection, skippedTexts As Collection
    Dim skippedTitles As Collection, skippedBodyLens As Collection
    titleOnlyCount = 0: writtenCount = 0: skippedCount = 0
    shortBodyCount = 0: top1 = 0: top2 = 0: top3 = 0
    Set keptTexts = New Collection
    Set skippedTexts = New Collection
    Set skippedTitles = New Collection
    Set skippedBodyLens = New Collection
    ' v3.6：全局正则对象只创建一次，此处无需再创建

    t0 = Timer
    On Error GoTo WriteErrV3
    For i = 0 To dedup_count - 1
        origIdx = dedup_indices(i)
        n = ch_ends(origIdx) - ch_starts(origIdx) + 1
        If n < 1 Then n = 1

        ' 提取正文
        ReDim bodyLines(0 To n - 1)
        For j = 0 To n - 1
            bodyLines(j) = lines(ch_starts(origIdx) + j)
        Next j
        body = Join(bodyLines, vbLf)

        ' v3.6 优化：正文汉字数直接读预计算结果，O(1)
        bodyLen = ch_hanziCounts(origIdx)

        ' 判断不足
        isInsufficient = False
        If n = 1 Then
            titleOnlyCount = titleOnlyCount + 1
            isInsufficient = True
        ElseIf MinBodyLen > 0 And bodyLen < MinBodyLen Then
            shortBodyCount = shortBodyCount + 1
            isInsufficient = True
        End If

        If isInsufficient And Not GenerateTitleOnly Then
            skippedCount = skippedCount + 1
            ' v3.4 新增：跳过原因统计（总-分报告用）
            If n = 1 Then
                g_skipTitleOnly = g_skipTitleOnly + 1
            ElseIf MinBodyLen > 0 And bodyLen < MinBodyLen Then
                g_skipShortBody = g_skipShortBody + 1
            End If
            If bodyLen >= top1 Then
                top3 = top2: top2 = top1: top1 = bodyLen
            ElseIf bodyLen >= top2 Then
                top3 = top2: top2 = bodyLen
            ElseIf bodyLen >= top3 Then
                top3 = bodyLen
            End If
            If MergeFlag >= 0 Then
                skippedTitles.Add ch_titles(origIdx)
                skippedBodyLens.Add bodyLen
                skippedTexts.Add body
            End If
            GoTo NextChapterV3
        End If

        ' 文件名
        Dim serial As String, charCnt As String, safeTitle As String
        Dim fileName As String, outPath As String
        serial = Format(writtenCount + 1, serialFmt)
        charCnt = Format(charCounts(i), charFmt)
        safeTitle = SanitizeFileName(ch_titles(origIdx))

        If Len(FileNamePrefix) > 0 Then
            fileName = FileNamePrefix & "_" & serial & "_" & charCnt & "_" & safeTitle & ".txt"
        Else
            fileName = serial & "_" & charCnt & "_" & safeTitle & ".txt"
        End If

        ' 按卷分目录
        Dim fileDir As String
        If byVolFlag And ch_vols(origIdx) > 0 Then
            Dim volDir As String
            volDir = "第" & ch_vols(origIdx) & ch_units(origIdx)
            volDir = SanitizeFileName(volDir)
            fileDir = outDirFull & "\" & volDir
            If Dir(fileDir, vbDirectory) = "" Then MkDir fileDir
        Else
            fileDir = outDirFull
        End If

        outPath = fileDir & "\" & fileName
        
        ' v3.2 新增：广告/垃圾行清理
        Dim finalBody As String
        finalBody = body
        If g_cleanAds Then
            finalBody = CleanAdLines(body)
        End If
        
        WriteTextUTF8NoBOM outPath, finalBody
        If MergeFlag = 1 Or MergeFlag = 2 Then keptTexts.Add finalBody

        If writtenCount < 3 Or i >= dedup_count - 2 Then
            Dim tag As String, volTag As String
            If n = 1 Then
                tag = "  (仅标题)"
            ElseIf MinBodyLen > 0 And bodyLen < MinBodyLen Then
                tag = "  (" & n & "行,正文" & bodyLen & "字)"
            Else
                tag = "  (" & n & "行)"
            End If
            If ch_vols(origIdx) > 0 Then
                volTag = "[卷" & ch_vols(origIdx) & "] "
            Else
                volTag = ""
            End If
            Debug.Print "  [" & serial & "] " & volTag & fileName & tag
        ElseIf writtenCount = 3 Then
            Debug.Print "  ..."
        End If

        writtenCount = writtenCount + 1
NextChapterV3:
    Next i
    On Error GoTo 0
    tWrite = Timer - t0

    ' 清洁模式合并文件（MergeFlag=2 同时输出保留和清理两个合并文件）
    If MergeFlag >= 0 Then
        Dim srcBaseName As String
        Dim mergeName2 As String, mergeBody2 As String
        Dim mergeDir As String
        srcBaseName = fso.GetBaseName(InputPath)
        
        ' v3.4.1：优先使用 MergeOutputDir，否则用 outDirFull
        If Len(MergeOutputDir) > 0 Then
            mergeDir = MergeOutputDir
        Else
            mergeDir = outDirFull
        End If
        ' 确保目录存在
        If Dir(mergeDir, vbDirectory) = "" Then MkDir mergeDir

        If keptTexts.Count > 0 Then
            mergeName2 = "保留大于等于" & MinBodyLen & "_" & srcBaseName & ".txt"
            mergeBody2 = JoinCollection(keptTexts)
            WriteTextUTF8NoBOM mergeDir & "\" & mergeName2, mergeBody2
            Debug.Print "合并文件：" & mergeName2 & "（" & keptTexts.Count & "章合并）"
        End If
        If MergeFlag = 2 And skippedTexts.Count > 0 Then
            mergeName2 = "清理小于" & MinBodyLen & "_" & srcBaseName & ".txt"
            mergeBody2 = JoinCollection(skippedTexts)
            WriteTextUTF8NoBOM mergeDir & "\" & mergeName2, mergeBody2
            Debug.Print "合并文件：" & mergeName2 & "（" & skippedTexts.Count & "章合并）"
        End If
    End If

    ' 完成报告
    Dim extraInfo As String, skipDetail As String
    extraInfo = ""
    skipDetail = ""
    If titleOnlyCount > 0 Then skipDetail = titleOnlyCount & "个仅有标题"
    If shortBodyCount > 0 Then
        If Len(skipDetail) > 0 Then skipDetail = skipDetail & "、"
        skipDetail = skipDetail & shortBodyCount & "个正文不足"
    End If

    ' v3.4：统计信息改由模块级变量传递（g_dedupRemoved/g_oooFixed/g_skip*），
    ' extraInfo 仅保留补充说明
    If skippedCount > 0 Then
        topStr = top1 & "字"
        If skippedCount >= 2 Then topStr = topStr & "、" & top2 & "字"
        If skippedCount >= 3 Then topStr = topStr & "、" & top3 & "字"
        extraInfo = "  跳过章节前三正文：" & topStr
    ElseIf Len(skipDetail) > 0 Then
        extraInfo = "  " & skipDetail & "（已生成）"
    End If

    ' v3.4：清洁模式（MergeFlag>=0）报告标题
    Dim rptTitle As String
    If MergeFlag >= 0 Then
        rptTitle = "清洁模式"
    Else
        rptTitle = "按章节拆分"
    End If

    ' v3.4.1：拆分完成报告文件路径
    Dim rptPath As String
    If MergeFlag >= 0 And Len(mergeDir) > 0 Then
        rptPath = mergeDir & "\拆分完成报告.txt"
    Else
        rptPath = ""
    End If

    ShowCompleteReportV3 rptTitle, writtenCount, outDirFull, _
                         tRead, tScan, tDedup, tWrite, extraInfo, rptPath
    Exit Sub

WriteErrV3:
    MsgBox "写入第 " & (i + 1) & " 个文件时出错：" & vbCrLf & _
           outPath & vbCrLf & _
           "错误：" & Err.Description, vbExclamation, "写入错误"
End Sub

'------------------------------------------------------------------------------
' 聚合拆分 v3
'------------------------------------------------------------------------------
Public Sub SplitByGroupsV3(ByVal InputPath As String, _
    Optional ByVal OutputDir As String = "", _
    Optional ByVal ChunkStr As String = "40,3", _
    Optional ByVal FileNamePrefix As String = "", _
    Optional ByVal SerialWidth As Long = 3)

    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim tRead As Double, tScan As Double, tDedup As Double, tWrite As Double
    Dim t0 As Double
    Dim outDirFull As String
    Dim actualVolMode As String
    Dim unitStr As String
    Dim chapIdxTmp2() As Long, chapBefore2 As Long, oooBefore2 As Long

    If g_tTotal0 = 0 Then g_tTotal0 = Timer

    ' 1. 读取
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(InputPath) Then
        MsgBox "源文件不存在：" & vbCrLf & InputPath, vbExclamation, "错误"
        Exit Sub
    End If
    t0 = Timer
    g_detectedEnc = DetectEncodingFile(InputPath)
    content = ReadTextAuto(InputPath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    tRead = Timer - t0

    ' 2. 扫描
    t0 = Timer
    ScanChaptersV3 lines, lineCount
    DetectTOC                       ' v3.2 新增：目录区自动检测
    tScan = Timer - t0
    If ch_count = 0 Then
        MsgBox "未识别到任何章节标题。", vbExclamation, "提示"
        Exit Sub
    End If

    ' 3. 卷模式
    actualVolMode = ResolveVolMode(g_volumeMode)
    ' v3.5: 聚合优先级大于卷——聚合按全局章号连续切块，卷分组无意义，强制扁平
    If actualVolMode <> "flat" Then
        actualVolMode = "flat"
        Application.Echo "卷模式: 聚合拆分优先 → 强制扁平（忽略卷结构）"
    End If
    g_actualVolMode = actualVolMode

    ' 4. 去重（统计减少章数）
    GetChapterIndices chapIdxTmp2, chapBefore2
    t0 = Timer
    ApplyDedup g_dedupStrategy, actualVolMode, g_titleDedup
    tDedup = Timer - t0
    g_dedupRemoved = chapBefore2 - dedup_count

    If dedup_count = 0 Then
        MsgBox "去重后无有效章节！", vbExclamation, "错误"
        Exit Sub
    End If

    ' 4b. 排序（统计乱序修复处数）
    Dim tSort2 As Double
    t0 = Timer
    oooBefore2 = CountOOOInDedup()
    ApplySort g_sortStrategy, actualVolMode
    tSort2 = Timer - t0
    g_oooFixed = oooBefore2 - CountOOOInDedup()

    If dedup_count = 0 Then
        MsgBox "排序后无有效章节！", vbExclamation, "错误"
        Exit Sub
    End If

    unitStr = ch_unit

    ' 5. 解析聚合格式
    Dim groupLens() As Long, groupSpaces() As Long, groupCount As Long
    Dim errMsg As String
    errMsg = ParseGroups(ChunkStr, dedup_count, groupLens, groupSpaces, groupCount)
    If Len(errMsg) > 0 Then
        MsgBox "聚合格式错误：" & vbCrLf & errMsg, vbExclamation, "错误"
        Exit Sub
    End If

    ' 6. 展开文件列表
    Dim fileChStart() As Long, fileChEnd() As Long, fileCount As Long
    ExpandGroups groupLens, groupSpaces, groupCount, dedup_count, _
                 fileChStart, fileChEnd, fileCount

    ' 7. 序号位数
    If Len(CStr(fileCount)) > SerialWidth Then SerialWidth = Len(CStr(fileCount))
    Dim serialFmt As String
    serialFmt = String(SerialWidth, "0")

    ' 8. 输出目录
    outDirFull = ResolveOutputDir(fso, InputPath, OutputDir, "_分组")
    If Dir(outDirFull, vbDirectory) = "" Then MkDir outDirFull
    CleanOutputDir outDirFull

    ' 9. 预览信息（v3.4：不再弹确认框，仅输出到立即窗口）
    Dim rangeStr As String, f As Long
    Debug.Print "【聚合拆分】源文件：" & InputPath & "，总行数：" & lineCount & _
                "，聚合格式：" & ChunkStr & "，将生成 " & fileCount & " 个文件"
    For f = 0 To fileCount - 1
        If f >= 12 Then Exit For
        rangeStr = FormatRange(fileChStart(f), fileChEnd(f), unitStr)
        Debug.Print "  " & Format(f + 1, serialFmt) & "  " & rangeStr
    Next f
    If fileCount > 12 Then Debug.Print "  ...（其余 " & (fileCount - 12) & " 份省略）"

    ' 10. 写文件
    t0 = Timer
    On Error GoTo GroupWriteErrV3
    Dim startLine As Long, endLine As Long, segCount As Long
    Dim parts() As String, li As Long, body As String
    Dim serial As String, safe As String, fname As String
    Dim origIdx_s As Long, origIdx_e As Long

    For f = 0 To fileCount - 1
        origIdx_s = dedup_indices(fileChStart(f) - 1)
        startLine = ch_starts(origIdx_s)

        If fileChEnd(f) < dedup_count Then
            origIdx_e = dedup_indices(fileChEnd(f))
            endLine = ch_starts(origIdx_e) - 1
        Else
            endLine = lineCount - 1
        End If

        segCount = endLine - startLine
        ReDim parts(0 To segCount)
        For li = 0 To segCount
            parts(li) = lines(startLine + li)
        Next li
        body = Join(parts, vbLf)

        rangeStr = FormatRange(fileChStart(f), fileChEnd(f), unitStr)
        safe = SanitizeFileName(rangeStr)
        serial = Format(f + 1, serialFmt)
        fname = serial & "_" & safe & ".txt"
        If Len(FileNamePrefix) > 0 Then fname = FileNamePrefix & "_" & fname

        ' v3.2 新增：广告/垃圾行清理
        Dim groupFinalBody As String
        groupFinalBody = body
        If g_cleanAds Then
            groupFinalBody = CleanAdLines(body)
        End If
        
        WriteTextUTF8NoBOM outDirFull & "\" & fname, groupFinalBody
    Next f
    On Error GoTo 0
    tWrite = Timer - t0

    ' 完成报告（v3.4：统计信息由模块级变量传递）
    Dim extraInfo As String
    extraInfo = "  聚合格式：" & ChunkStr & "（单位：" & unitStr & "）"

    ShowCompleteReportV3 "聚合模式", fileCount, outDirFull, _
                         tRead, tScan, tDedup, tWrite, extraInfo
    Exit Sub

GroupWriteErrV3:
    MsgBox "写入第 " & (f + 1) & " 份文件时出错：" & vbCrLf & _
           outDirFull & "\" & fname & vbCrLf & _
           "错误：" & Err.Description, vbExclamation, "写入错误"
End Sub


'==============================================================================
' 第八部分：共享工具函数（与splittxt2一致）
'==============================================================================

Private Function SelectTxtFile(ByVal title As String) As String
    Dim fd As Object
    On Error Resume Next
    Set fd = Application.FileDialog(3)
    On Error GoTo 0
    If fd Is Nothing Then
        MsgBox "当前环境不支持文件选择对话框。", vbExclamation, "提示"
        Exit Function
    End If
    fd.Title = title
    On Error Resume Next
    fd.Filters.Clear
    fd.Filters.Add "文本文件", "*.txt"
    On Error GoTo 0
    If fd.Show <> -1 Then Exit Function
    SelectTxtFile = fd.SelectedItems(1)
End Function

Private Function SanitizeFileName(ByVal name As String) As String
    Dim s As String, chars As String, k As Long
    s = Replace(name, " ", "　")
    chars = "\/:*?""<>|"
    For k = 1 To Len(chars)
        s = Replace(s, Mid(chars, k, 1), "　")
    Next k
    Do While InStr(s, "　　") > 0
        s = Replace(s, "　　", "　")
    Loop
    s = Trim(s)
    If Len(s) = 0 Then s = "untitled"
    If Len(s) > 60 Then s = Left(s, 60)
    SanitizeFileName = s
End Function

Private Function JoinCollection(col As Collection) As String
    Dim parts() As String, i As Long
    If col.Count = 0 Then Exit Function
    ReDim parts(1 To col.Count)
    For i = 1 To col.Count
        parts(i) = col(i)
    Next i
    JoinCollection = Join(parts, vbLf)
End Function

Private Function ResolveOutputDir(fso As Object, ByVal InputPath As String, _
        ByVal OutputDir As String, ByVal suffix As String) As String
    If Len(OutputDir) = 0 Then
        ResolveOutputDir = fso.GetParentFolderName(InputPath) & "\" & _
                           fso.GetBaseName(InputPath) & suffix
    Else
        ResolveOutputDir = OutputDir
    End If
End Function

Private Sub CleanOutputDir(ByVal outDir As String)
    Dim fso As Object, folder As Object, file As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FolderExists(outDir) Then
        Set folder = fso.GetFolder(outDir)
        For Each file In folder.Files
            If StrComp(fso.GetExtensionName(file.Name), "txt", vbTextCompare) = 0 Then
                file.Delete
            End If
        Next file
    End If
End Sub

Private Function FormatRange(ByVal chStart As Long, ByVal chEnd As Long, _
        ByVal unit As String) As String
    If chStart = chEnd Then
        FormatRange = "第" & chStart & unit
    Else
        FormatRange = "第" & chStart & "-" & chEnd & unit
    End If
End Function

Private Sub ShowCompleteReportV3(ByVal title As String, ByVal fileCount As Long, _
        ByVal outDir As String, ByVal tRead As Double, _
        ByVal tScan As Double, ByVal tDedup As Double, _
        ByVal tWrite As Double, Optional ByVal extraInfo As String = "", _
        Optional ByVal ReportPath As String = "")
    ' v3.4：重构为 总-分 结构
    Dim tTotal As Double, msg As String
    Dim skippedTotal As Long
    tTotal = Timer - g_tTotal0
    skippedTotal = g_skipTitleOnly + g_skipShortBody

    ' 【总】
    msg = "【总】" & title & "完成：生成 " & fileCount & " 个文件（耗时 " & _
          Format(tTotal, "0.0") & " 秒）" & vbCrLf & _
          "输出：" & outDir & vbCrLf & _
          String(30, "-") & vbCrLf

    ' 【分】
    msg = msg & "【分】" & vbCrLf
    msg = msg & "  来源：编码 " & g_detectedEnc & "→UTF-8｜正则 " & g_regexName & _
          "｜识别章节 " & ch_count & vbCrLf

    ' 质量行：去重(-N章)｜排序(修N处)｜卷模式（无数据的部分省略）
    Dim qualityLine As String
    qualityLine = "  质量："
    If g_dedupStrategy <> "none" Then
        qualityLine = qualityLine & "去重 " & g_dedupStrategy & "(-" & g_dedupRemoved & "章)｜"
    Else
        qualityLine = qualityLine & "去重 none｜"
    End If
    If g_sortStrategy <> "none" Then
        qualityLine = qualityLine & "排序 " & g_sortStrategy & "(修" & g_oooFixed & "处)｜"
    Else
        qualityLine = qualityLine & "排序 none｜"
    End If
    qualityLine = qualityLine & "卷模式 " & g_actualVolMode
    msg = msg & qualityLine & vbCrLf

    ' 清理行：广告行 -N｜跳过 N 章（无数据的行省略）
    If g_cleanAds Or skippedTotal > 0 Then
        Dim cleanLine As String
        cleanLine = "  清理："
        If g_cleanAds Then
            cleanLine = cleanLine & "广告行 -" & g_adRemovedCount
            If skippedTotal > 0 Then cleanLine = cleanLine & "｜"
        End If
        If skippedTotal > 0 Then
            cleanLine = cleanLine & "跳过 " & skippedTotal & " 章"
            If g_skipTitleOnly > 0 Or g_skipShortBody > 0 Then
                cleanLine = cleanLine & "（仅标题" & g_skipTitleOnly & "/正文不足" & g_skipShortBody & "）"
            End If
        End If
        msg = msg & cleanLine & vbCrLf
    End If

    msg = msg & "  计时：读取 " & Format(tRead, "0.00") & "s｜识别 " & _
          Format(tScan, "0.00") & "s｜去重 " & Format(tDedup, "0.00") & "s｜写入 " & _
          Format(tWrite, "0.00") & "s｜总计 " & Format(tTotal, "0.00") & "s"

    If Len(extraInfo) > 0 Then
        msg = msg & vbCrLf & extraInfo
    End If
    
    ' v3.4.1：写入拆分完成报告文件
    If Len(ReportPath) > 0 Then
        WriteTextUTF8NoBOM ReportPath, msg
        Debug.Print "完成报告：" & ReportPath
    End If

    MsgBox msg, vbInformation, "完成"
End Sub

' 聚合格式解析
Private Function ParseGroups(ByVal chunkStr As String, ByVal total As Long, _
        ByRef groupLens() As Long, ByRef groupSpaces() As Long, _
        ByRef groupCount As Long) As String
    Dim s As String, parts() As String, p As Long, part As String
    Dim detail() As String, length As Long, spacing As Long
    Dim consumed As Long, n As Long, cnt As Long

    s = Trim(chunkStr)
    If Len(s) = 0 Then ParseGroups = "聚合字符串为空": Exit Function

    ReDim groupLens(0 To 31)
    ReDim groupSpaces(0 To 31)
    groupCount = 0
    consumed = 0

    If InStr(s, ",") = 0 And InStr(s, "|") = 0 Then
        If Not IsDigits(s) Then ParseGroups = "便捷模式需为正整数: " & s: Exit Function
        n = CLng(s)
        If n <= 0 Then ParseGroups = "每份章数必须为正数: " & s: Exit Function
        cnt = total \ n
        If total Mod n > 0 Then cnt = cnt + 1
        groupLens(0) = cnt
        groupSpaces(0) = n
        groupCount = 1
        ParseGroups = ""
        Exit Function
    End If

    parts = Split(s, "|")
    For p = 0 To UBound(parts)
        part = Trim(parts(p))
        If Len(part) = 0 Then GoTo NextPart2
        detail = Split(part, ",")
        If UBound(detail) <> 1 Then
            ParseGroups = "段格式错误: " & part & "（应为 每份章数,份数）"
            Exit Function
        End If
        If Not IsDigits(Trim(detail(0))) Or Not IsDigits(Trim(detail(1))) Then
            ParseGroups = "每份章数和份数需为正整数: " & part
            Exit Function
        End If
        spacing = CLng(Trim(detail(0)))
        length = CLng(Trim(detail(1)))
        If length <= 0 Or spacing <= 0 Then
            ParseGroups = "每份章数和份数必须为正数: " & part
            Exit Function
        End If
        groupLens(groupCount) = length
        groupSpaces(groupCount) = spacing
        groupCount = groupCount + 1
        If groupCount > UBound(groupLens) Then
            ReDim Preserve groupLens(0 To groupCount + 31)
            ReDim Preserve groupSpaces(0 To groupCount + 31)
        End If
        consumed = consumed + length * spacing
NextPart2:
    Next p

    If consumed > total Then
        ParseGroups = "消耗章节数 " & consumed & " 超过总章节数 " & total
        Exit Function
    End If
    If consumed < total Then
        groupLens(groupCount) = 1
        groupSpaces(groupCount) = total - consumed
        groupCount = groupCount + 1
    End If
    ParseGroups = ""
End Function

Private Sub ExpandGroups(groupLens() As Long, groupSpaces() As Long, _
        ByVal groupCount As Long, ByVal total As Long, _
        ByRef fileChStart() As Long, ByRef fileChEnd() As Long, _
        ByRef fileCount As Long)
    Dim g As Long, k As Long, ch As Long
    ReDim fileChStart(0 To 31)
    ReDim fileChEnd(0 To 31)
    fileCount = 0
    ch = 0
    For g = 0 To groupCount - 1
        For k = 1 To groupLens(g)
            If ch >= total Then Exit For
            fileChStart(fileCount) = ch + 1
            If ch + groupSpaces(g) < total Then
                fileChEnd(fileCount) = ch + groupSpaces(g)
            Else
                fileChEnd(fileCount) = total
            End If
            ch = fileChEnd(fileCount)
            fileCount = fileCount + 1
            If fileCount > UBound(fileChStart) Then
                ReDim Preserve fileChStart(0 To fileCount + 31)
                ReDim Preserve fileChEnd(0 To fileCount + 31)
            End If
        Next k
        If ch >= total Then Exit For
    Next g
End Sub

Private Function NormalizeSeparators(ByVal s As String) As String
    Dim r As String
    r = s
    r = Replace(r, "，", ",")
    r = Replace(r, "｜", "|")
    r = Replace(r, "　", " ")
    r = Replace(r, "０", "0"): r = Replace(r, "１", "1")
    r = Replace(r, "２", "2"): r = Replace(r, "３", "3")
    r = Replace(r, "４", "4"): r = Replace(r, "５", "5")
    r = Replace(r, "６", "6"): r = Replace(r, "７", "7")
    r = Replace(r, "８", "8"): r = Replace(r, "９", "9")
    NormalizeSeparators = r
End Function

'------------------------------------------------------------------------------
' v3.2 新增：行归一化（用于章节标题匹配前的预处理）
'   处理：全角数字→半角、全角空格→半角、空白压缩、不可见字符清理、全角冒号统一
'   注意：仅用于匹配正则，原始行内容保留用于输出
'------------------------------------------------------------------------------
Private Function NormalizeLineForMatch(ByVal s As String) As String
    Dim r As String
    Dim i As Long, c As String, code As Long
    Dim result As String
    Dim prevSpace As Boolean
    
    r = s
    
    ' 1. 全角数字 → 半角
    r = Replace(r, "０", "0"): r = Replace(r, "１", "1")
    r = Replace(r, "２", "2"): r = Replace(r, "３", "3")
    r = Replace(r, "４", "4"): r = Replace(r, "５", "5")
    r = Replace(r, "６", "6"): r = Replace(r, "７", "7")
    r = Replace(r, "８", "8"): r = Replace(r, "９", "9")
    
    ' 2. 全角空格 → 半角空格
    r = Replace(r, ChrW(12288), " ")   ' 全角空格
    r = Replace(r, ChrW(&H3000), " ")   ' 另一种全角空格
    
    ' 3. 全角冒号 → 半角冒号（统一"第N章：标题"中的冒号）
    r = Replace(r, "：", ":")
    
    ' 4. 清理不可见字符（保留常用的，移除零宽字符等）
    r = Replace(r, ChrW(&H200B), "")   ' 零宽空格
    r = Replace(r, ChrW(&H200C), "")   ' 零宽非连字符
    r = Replace(r, ChrW(&H200D), "")   ' 零宽连字符
    r = Replace(r, ChrW(&HFEFF), "")   ' BOM/零宽无间断空格
    
    ' 5. Tab → 空格
    r = Replace(r, vbTab, " ")
    
    ' 6. 压缩多个连续空格为一个（提升正则匹配率）
    result = ""
    prevSpace = False
    For i = 1 To Len(r)
        c = Mid(r, i, 1)
        If c = " " Then
            If Not prevSpace Then
                result = result & c
                prevSpace = True
            End If
        Else
            result = result & c
            prevSpace = False
        End If
    Next i
    
    NormalizeLineForMatch = result
End Function

'------------------------------------------------------------------------------
' v3.3 新增：标题规范化（用于标题级去重的键生成）
'   处理：全角半角统一、空白删除、标点清理、转小写
'   目的：章号相同但标题仅差标点/空格/全角时，仍视为同一章
'------------------------------------------------------------------------------
Private Function NormalizeTitle(ByVal s As String) As String
    Dim r As String
    Dim i As Long, c As String
    Dim result As String
    Dim code As Long
    
    r = Trim(s)
    
    ' 1. 全角数字 → 半角
    r = Replace(r, "０", "0"): r = Replace(r, "１", "1")
    r = Replace(r, "２", "2"): r = Replace(r, "３", "3")
    r = Replace(r, "４", "4"): r = Replace(r, "５", "5")
    r = Replace(r, "６", "6"): r = Replace(r, "７", "7")
    r = Replace(r, "８", "8"): r = Replace(r, "９", "9")
    
    ' 2. 全角字母 → 半角（小写+大写）
    For i = 0 To 25
        r = Replace(r, ChrW(&HFF41 + i), Chr(97 + i))   ' 全角小写
        r = Replace(r, ChrW(&HFF21 + i), Chr(65 + i))   ' 全角大写
    Next i
    
    ' 3. 全角空格 → 删除
    r = Replace(r, ChrW(&H3000), "")
    r = Replace(r, " ", "")
    r = Replace(r, vbTab, "")
    
    ' 4. 全角冒号/分号/逗号/句号等 → 删除
    r = Replace(r, "：", "")
    r = Replace(r, "；", "")
    r = Replace(r, "，", "")
    r = Replace(r, "。", "")
    r = Replace(r, "、", "")
    
    ' 5. 零宽字符
    r = Replace(r, ChrW(&H200B), "")
    r = Replace(r, ChrW(&H200C), "")
    r = Replace(r, ChrW(&H200D), "")
    r = Replace(r, ChrW(&HFEFF), "")
    
    ' 6. 半角标点清理
    r = Replace(r, ",", "")
    r = Replace(r, ".", "")
    r = Replace(r, ":", "")
    r = Replace(r, ";", "")
    r = Replace(r, "!", "")
    r = Replace(r, "?", "")
    r = Replace(r, "'", "")
    r = Replace(r, """", "")
    r = Replace(r, "(", "")
    r = Replace(r, ")", "")
    r = Replace(r, "[", "")
    r = Replace(r, "]", "")
    r = Replace(r, "<", "")
    r = Replace(r, ">", "")
    r = Replace(r, "-", "")
    r = Replace(r, "_", "")
    
    ' 7. 中文标点清理
    r = Replace(r, "（", "")
    r = Replace(r, "）", "")
    r = Replace(r, "《", "")
    r = Replace(r, "》", "")
    r = Replace(r, "【", "")
    r = Replace(r, "】", "")
    r = Replace(r, "「", "")
    r = Replace(r, "」", "")
    r = Replace(r, "『", "")
    r = Replace(r, "』", "")
    r = Replace(r, "！", "")
    r = Replace(r, "？", "")
    r = Replace(r, "·", "")
    r = Replace(r, "…", "")
    r = Replace(r, "—", "")
    r = Replace(r, "～", "")
    
    ' 8. 转小写（字母）
    r = LCase(r)
    
    NormalizeTitle = r
End Function

'------------------------------------------------------------------------------
' v3.2 新增：广告/垃圾行清理
'   清理常见的盗版TXT广告、水印、推广语等垃圾行
'   参数：text - 原始文本（vbLf分隔）
'   返回：清理后的文本
'   注意：全局变量 g_adRemovedCount 累计移除行数
'------------------------------------------------------------------------------
Private Function CleanAdLines(ByVal text As String) As String
    Dim linesArr() As String
    Dim resultArr() As String
    Dim i As Long, cnt As Long
    Dim line As String, tline As String
    Dim isAd As Boolean
    
    linesArr = Split(text, vbLf)
    ReDim resultArr(0 To UBound(linesArr))
    cnt = 0
    
    For i = 0 To UBound(linesArr)
        line = linesArr(i)
        tline = Trim(line)
        isAd = False
        
        ' 1. 空行保留（不视为广告）
        If Len(tline) = 0 Then
            isAd = False
            
        ' 2. 网址行（http/https/www.xxx.com等）
        ElseIf InStr(1, tline, "http://", vbTextCompare) > 0 _
            Or InStr(1, tline, "https://", vbTextCompare) > 0 _
            Or InStr(1, tline, "www.", vbTextCompare) > 0 Then
            isAd = True
            
        ' 3. 常见域名后缀（xx.com / xx.net / xx.cc 等）
        ElseIf Len(tline) < 60 And _
            (InStr(1, tline, ".com", vbTextCompare) > 0 _
             Or InStr(1, tline, ".net", vbTextCompare) > 0 _
             Or InStr(1, tline, ".cc", vbTextCompare) > 0 _
             Or InStr(1, tline, ".cn", vbTextCompare) > 0 _
             Or InStr(1, tline, ".org", vbTextCompare) > 0 _
             Or InStr(1, tline, ".info", vbTextCompare) > 0) Then
            ' 进一步确认：短行且包含疑似域名
            If Len(tline) < 40 Then isAd = True
            
        ' 4. 站点推广语
        ElseIf InStr(1, tline, "记住本站", vbTextCompare) > 0 _
            Or InStr(1, tline, "收藏本站", vbTextCompare) > 0 _
            Or InStr(1, tline, "推荐收藏", vbTextCompare) > 0 _
            Or InStr(1, tline, "手机用户", vbTextCompare) > 0 _
            Or InStr(1, tline, "请访问", vbTextCompare) > 0 _
            Or InStr(1, tline, "永久域名", vbTextCompare) > 0 _
            Or InStr(1, tline, "最新地址", vbTextCompare) > 0 _
            Or InStr(1, tline, "笔趣阁", vbTextCompare) > 0 _
            Or InStr(1, tline, "顶点小说", vbTextCompare) > 0 Then
            isAd = True
            
        ' 5. 分页提示语
        ElseIf InStr(1, tline, "本章未完", vbTextCompare) > 0 _
            Or InStr(1, tline, "下一页继续", vbTextCompare) > 0 _
            Or InStr(1, tline, "点击下一页", vbTextCompare) > 0 _
            Or InStr(1, tline, "上一页", vbTextCompare) > 0 _
            Or InStr(1, tline, "返回目录", vbTextCompare) > 0 _
            Or InStr(1, tline, "加入书架", vbTextCompare) > 0 Then
            isAd = True
            
        ' 6. 求票/求收藏类作者推广
        ElseIf (InStr(1, tline, "求月票", vbTextCompare) > 0 _
                Or InStr(1, tline, "求推荐", vbTextCompare) > 0 _
                Or InStr(1, tline, "求收藏", vbTextCompare) > 0 _
                Or InStr(1, tline, "求打赏", vbTextCompare) > 0 _
                Or InStr(1, tline, "感谢打赏", vbTextCompare) > 0 _
                Or InStr(1, tline, "感谢订阅", vbTextCompare) > 0) _
            And Len(tline) < 40 Then
            isAd = True
            
        ' 7. 纯符号分隔线（*、-、=、~ 等重复 >=5 个）
        ElseIf Len(tline) >= 5 Then
            Dim firstCh As String
            firstCh = Left(tline, 1)
            If firstCh = "*" Or firstCh = "-" Or firstCh = "=" Or _
               firstCh = "~" Or firstCh = "·" Or firstCh = "—" Or _
               firstCh = "＋" Or firstCh = "+" Then
                Dim allSame As Boolean
                allSame = True
                Dim j As Long
                For j = 2 To Len(tline)
                    If Mid(tline, j, 1) <> firstCh Then
                        allSame = False
                        Exit For
                    End If
                Next j
                If allSame Then isAd = True
            End If
        End If
        
        If Not isAd Then
            resultArr(cnt) = line
            cnt = cnt + 1
        Else
            g_adRemovedCount = g_adRemovedCount + 1
        End If
    Next i
    
    If cnt > 0 Then
        ReDim Preserve resultArr(0 To cnt - 1)
        CleanAdLines = Join(resultArr, vbLf)
    Else
        CleanAdLines = ""
    End If
End Function

Private Function IsDigits(ByVal s As String) As Boolean
    Dim i As Long, c As String
    If Len(s) = 0 Then Exit Function
    For i = 1 To Len(s)
        c = Mid(s, i, 1)
        If c < "0" Or c > "9" Then Exit Function
    Next i
    IsDigits = True
End Function
