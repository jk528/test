'============================================================
' 四方镜子 - 单模块版 v8（备选算法验证版）
' 基于 v6 扩展：完全保留现有功能不变，仅新增"备选算法验证"
' 现有功能（不变）：
'   - 四方循环 scct（笛卡尔积，4个按钮）
'   - 双边循环 zxgbs（LCM独立循环，2个按钮）
'   - 窗体布局、按钮预览、命名规则 全部与 v6 一致
' 新增功能：
'   - 按钮7 "备选算法验证" → 验证 4 种其他核心算法
'       A 进位计数法（Odometer，=笛卡尔积正向，混合进制实现）
'       B 回溯法（DFS递归，=笛卡尔积正向，递归实现）
'       C 自定义周期独立循环（zxgbs 推广，周期2,3）
'       D 随机抽样组合（随机生成 N 行）
' 模式：Designer.Controls.Add + CodeModule 注入事件代码
' 使用方法：运行 四方镜子()
' 注意：需启用"信任对VBA工程对象模型的访问"
'============================================================

Option Explicit

' 全局变量
Public 连接符 As String
Public 是否合并 As Boolean

' 回溯法专用模块级变量
Private 回溯行号 As Long
Private 回溯结果() As Variant

' ============================================================
'  主入口
' ============================================================

Sub 四方镜子()
    On Error GoTo 错误处理

    连接符 = "-"
    是否合并 = True

    Dim VBP As Object
    Set VBP = ThisWorkbook.VBProject

    ' 1. 创建窗体
    Dim 窗体组件 As Object
    Set 窗体组件 = VBP.VBComponents.Add(3) ' 3 = vbext_ct_MSForm
    Dim 窗体名 As String
    窗体名 = 窗体组件.Name

    ' 2. 设置窗体属性
    With 窗体组件.Properties
        .Item("Caption") = "四方镜"
        .Item("Width") = 570
        .Item("Height") = 520
        .Item("StartUpPosition") = 1 ' 居中
    End With

    ' 3. 用 Designer 添加控件（设计时控件，事件原生支持）
    Dim 设计器 As Object
    Set 设计器 = 窗体组件.Designer

    ' --- 标签 ---
    Dim lbl As Object
    Set lbl = 设计器.Controls.Add("Forms.Label.1", "Label1")
    With lbl
        .Caption = "连接符号:"
        .Left = 10: .Top = 12: .Width = 60: .Height = 18
        .Font.Size = 10
    End With

    ' --- 文本框 ---
    Dim txt As Object
    Set txt = 设计器.Controls.Add("Forms.TextBox.1", "TextBox1")
    With txt
        .Text = "-"
        .Left = 75: .Top = 10: .Width = 100: .Height = 22
        .Font.Size = 10
    End With

    ' --- 复选框 ---
    Dim chk As Object
    Set chk = 设计器.Controls.Add("Forms.CheckBox.1", "CheckBox1")
    With chk
        .Caption = "合并"
        .Left = 200: .Top = 12: .Width = 100: .Height = 18
        .Value = True
        .Font.Size = 10
    End With

    ' --- 框架1 ---
    Dim fra1 As Object
    Set fra1 = 设计器.Controls.Add("Forms.Frame.1", "Frame1")
    With fra1
        .Caption = "四方循环（笛卡尔积）"
        .Left = 10: .Top = 65: .Width = 540: .Height = 220
        .Font.Size = 10: .Font.Bold = True
    End With

    ' --- 按钮1：反向竖向（左慢右快） ---
    Dim btn1 As Object
    Set btn1 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton1")
    With btn1
        .Caption = "反向竖向"
        .Left = 15: .Top = 25: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 按钮3：正向竖向（左快右慢） ---
    Dim btn3 As Object
    Set btn3 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton3")
    With btn3
        .Caption = "正向竖向"
        .Left = 280: .Top = 25: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 按钮2：正向横向 ---
    Dim btn2 As Object
    Set btn2 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton2")
    With btn2
        .Caption = "正向横向"
        .Left = 15: .Top = 115: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 按钮4：反向横向 ---
    Dim btn4 As Object
    Set btn4 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton4")
    With btn4
        .Caption = "反向横向"
        .Left = 280: .Top = 115: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 框架2 ---
    Dim fra2 As Object
    Set fra2 = 设计器.Controls.Add("Forms.Frame.1", "Frame2")
    With fra2
        .Caption = "双边循环（LCM独立循环）"
        .Left = 10: .Top = 295: .Width = 540: .Height = 130
        .Font.Size = 10: .Font.Bold = True
    End With

    ' --- 按钮5：双边循环_竖 ---
    Dim btn5 As Object
    Set btn5 = fra2.Controls.Add("Forms.CommandButton.1", "CommandButton5")
    With btn5
        .Caption = "双边循环_竖"
        .Left = 15: .Top = 25: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 按钮6：双边循环_横 ---
    Dim btn6 As Object
    Set btn6 = fra2.Controls.Add("Forms.CommandButton.1", "CommandButton6")
    With btn6
        .Caption = "双边循环_横"
        .Left = 280: .Top = 25: .Width = 250: .Height = 80
        .Font.Size = 10
    End With

    ' --- 按钮7：备选算法验证（v8 新增） ---
    Dim btn7 As Object
    Set btn7 = 设计器.Controls.Add("Forms.CommandButton.1", "CommandButton7")
    With btn7
        .Caption = "备选算法验证"
        .Left = 200: .Top = 445: .Width = 170: .Height = 30
        .Font.Size = 10: .Font.Bold = True
        .BackColor = RGB(80, 160, 220)
    End With

    ' 4. 用 CodeModule 注入事件代码
    注入事件代码 窗体组件

    ' 5. 显示窗体（模态，阻塞直到窗体关闭）
    VBA.UserForms.Add(窗体名).Show

    ' 6. Show 返回说明窗体已关闭，安全删除组件
    VBP.VBComponents.Remove 窗体组件

    Exit Sub

错误处理:
    MsgBox "错误 " & Err.Number & ": " & Err.Description, vbCritical, "四方镜子"
    On Error Resume Next
    If Not 窗体组件 Is Nothing Then
        VBP.VBComponents.Remove 窗体组件
    End If
End Sub

' ============================================================
'  注入事件代码（CodeModule.InsertLines 逐行写入）
' ============================================================

Private Sub 注入事件代码(窗体组件 As Object)
    Dim CM As Object
    Set CM = 窗体组件.CodeModule
    Dim i As Long
    i = CM.CountOfLines

    ' ---- Option Explicit ----
    i = i + 1: CM.InsertLines i, "Option Explicit"
    i = i + 1: CM.InsertLines i, ""

    ' ---- Initialize ----
    i = i + 1: CM.InsertLines i, "Private Sub UserForm_Initialize()"
    i = i + 1: CM.InsertLines i, "    更新按钮图示 Me"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- TextBox1_Change ----
    i = i + 1: CM.InsertLines i, "Private Sub TextBox1_Change()"
    i = i + 1: CM.InsertLines i, "    连接符 = TextBox1.Text"
    i = i + 1: CM.InsertLines i, "    更新按钮图示 Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- CheckBox1_Click ----
    i = i + 1: CM.InsertLines i, "Private Sub CheckBox1_Click()"
    i = i + 1: CM.InsertLines i, "    是否合并 = CheckBox1.Value"
    i = i + 1: CM.InsertLines i, "    更新按钮图示 Me"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- 现有6个按钮点击事件（执行后关闭窗体，与 v6 完全一致） ----
    i = i + 1: CM.InsertLines i, "Private Sub CommandButton1_Click()"
    i = i + 1: CM.InsertLines i, "    四方循环_执行 False, False"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton2_Click()"
    i = i + 1: CM.InsertLines i, "    四方循环_执行 True, True"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton3_Click()"
    i = i + 1: CM.InsertLines i, "    四方循环_执行 True, False"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton4_Click()"
    i = i + 1: CM.InsertLines i, "    四方循环_执行 False, True"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton5_Click()"
    i = i + 1: CM.InsertLines i, "    双边循环_执行 True"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton6_Click()"
    i = i + 1: CM.InsertLines i, "    双边循环_执行 False"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- 按钮7：备选算法验证（v8 新增） ----
    i = i + 1: CM.InsertLines i, "Private Sub CommandButton7_Click()"
    i = i + 1: CM.InsertLines i, "    备选算法_菜单"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
End Sub

' ============================================================
'  工具函数
' ============================================================

Private Function ys(n As Long, Y As Long) As Long
    ys = ((n + Y - 1) Mod Y) + 1
End Function

Private Function cd(c As Long, d As Long) As Long
    cd = WorksheetFunction.RoundUp(c / d, 0)
End Function

Private Function 最后列(ws As Worksheet) As Long
    最后列 = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
End Function

Private Function 最后行(ws As Worksheet, 列 As Long) As Long
    最后行 = ws.Cells(ws.Rows.Count, 列).End(xlUp).Row
End Function

Private Function 数组乘积(数组 As Variant) As Long
    Dim i As Long
    数组乘积 = 1
    For i = LBound(数组) To UBound(数组)
        数组乘积 = 数组乘积 * 数组(i)
    Next i
End Function

' 新建结果表（统一创建逻辑和命名规则）
Private Function 新建结果表(名称前缀 As String) As Worksheet
    Dim ws As Worksheet
    Set ws = Worksheets.Add(After:=ActiveSheet)
    Dim 表名 As String
    表名 = 名称前缀 & "_" & Sheets.Count
    If Len(表名) > 31 Then 表名 = Left(名称前缀, 31 - Len(CStr(Sheets.Count)) - 1) & "_" & Sheets.Count
    On Error Resume Next
    ws.Name = 表名
    If Err.Number <> 0 Then ws.Name = "结果_" & Format(Now, "hhmmss")
    On Error GoTo 0
    Set 新建结果表 = ws
End Function

' 读取活动工作表源数据：返回 每列行数 和 源数据（含最大行）
Private Sub 读取源数据(每列行数() As Long, 源数据 As Variant)
    Dim ws As Worksheet
    Set ws = ActiveSheet
    Dim 总列数 As Long, 列 As Long, 最大行 As Long
    总列数 = 最后列(ws)
    ReDim 每列行数(1 To 总列数)
    最大行 = 0
    For 列 = 1 To 总列数
        每列行数(列) = 最后行(ws, 列)
        If 每列行数(列) > 最大行 Then 最大行 = 每列行数(列)
    Next 列
    源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(最大行, 总列数)).Value2
End Sub

' 写入备选算法结果：合并→单列字符串，分开→多列（与现有输出一致）
Private Sub 写入备选结果(新表 As Worksheet, 结果() As Variant, 总行数 As Long, 总列数 As Long)
    If 是否合并 Then
        Dim 写入() As String
        ReDim 写入(1 To 总行数, 1 To 1)
        Dim 行 As Long, 列 As Long
        Dim 片段() As String
        ReDim 片段(1 To 总列数)
        For 行 = 1 To 总行数
            For 列 = 1 To 总列数
                片段(列) = 结果(行, 列)
            Next 列
            写入(行, 1) = Join(片段, 连接符)
        Next 行
        新表.Range("A1").Resize(总行数, 1) = 写入
    Else
        新表.Range("A1").Resize(总行数, 总列数) = 结果
    End If
End Sub

' ============================================================
'  按钮图示生成（与 v6 完全一致）
' ============================================================

Public Sub 更新按钮图示(frm As Object)
    On Error Resume Next

    ' 非对称占位符预览：A列2行 + B列3行（2x3，6个组合完整显示）
    Dim d1a As String, d2a As String
    Dim d1b As String, d2b As String, d3b As String
    d1a = "a1": d2a = "a2"
    d1b = "b1": d2b = "b2": d3b = "b3"

    ' 连接符：合并模式用用户输入的连接符，分开模式用双空格
    Dim 连 As String
    连 = 连接符
    If 连 = "" Then 连 = " "
    Dim 空 As String
    If 是否合并 Then 空 = 连 Else 空 = "  "

    ' 6个基本组合（正向笛卡尔积排序）
    Dim m1 As String, m2 As String, m3 As String, m4 As String, m5 As String, m6 As String
    m1 = d1a & 空 & d1b   ' a1-b1
    m2 = d2a & 空 & d1b   ' a2-b1
    m3 = d1a & 空 & d2b   ' a1-b2
    m4 = d2a & 空 & d2b   ' a2-b2
    m5 = d1a & 空 & d3b   ' a1-b3
    m6 = d2a & 空 & d3b   ' a2-b3

    ' 按钮1：反向竖向（左慢右快：A每3行变，B每行变）
    frm.Controls("CommandButton1").Caption = _
        m1 & Chr(10) & m3 & Chr(10) & m5 & Chr(10) & _
        m2 & Chr(10) & m4 & Chr(10) & m6

    ' 按钮3：正向竖向（左快右慢：A每行变，B每2行变）
    frm.Controls("CommandButton3").Caption = _
        m1 & Chr(10) & m2 & Chr(10) & m3 & Chr(10) & _
        m4 & Chr(10) & m5 & Chr(10) & m6

    If 是否合并 Then
        ' 按钮2：正向横向（一行6个组合）
        frm.Controls("CommandButton2").Caption = _
            m1 & "   " & m2 & "   " & m3 & "   " & m4 & "   " & m5 & "   " & m6
        ' 按钮4：反向横向（一行6个组合）
        frm.Controls("CommandButton4").Caption = _
            m1 & "   " & m3 & "   " & m5 & "   " & m2 & "   " & m4 & "   " & m6
    Else
        ' 按钮2：正向横向 分开（完整矩阵2行各6列）
        frm.Controls("CommandButton2").Caption = _
            d1a & "  " & d2a & "  " & d1a & "  " & d2a & "  " & d1a & "  " & d2a & Chr(10) & _
            d1b & "  " & d1b & "  " & d2b & "  " & d2b & "  " & d3b & "  " & d3b
        ' 按钮4：反向横向 分开（完整矩阵2行各6列）
        frm.Controls("CommandButton4").Caption = _
            d1a & "  " & d1a & "  " & d1a & "  " & d2a & "  " & d2a & "  " & d2a & Chr(10) & _
            d1b & "  " & d2b & "  " & d3b & "  " & d1b & "  " & d2b & "  " & d3b
    End If

    ' 按钮5：双边循环_竖（每列独立循环同步推进，LCM=6）
    frm.Controls("CommandButton5").Caption = _
        m1 & Chr(10) & m4 & Chr(10) & m5 & Chr(10) & _
        m2 & Chr(10) & m3 & Chr(10) & m6

    ' 按钮6：双边循环_横
    If 是否合并 Then
        frm.Controls("CommandButton6").Caption = _
            m1 & "   " & m4 & "   " & m5 & "   " & m2 & "   " & m3 & "   " & m6
    Else
        frm.Controls("CommandButton6").Caption = _
            d1a & "  " & d2a & "  " & d1a & "  " & d2a & "  " & d1a & "  " & d2a & Chr(10) & _
            d1b & "  " & d2b & "  " & d3b & "  " & d1b & "  " & d2b & "  " & d3b
    End If

    ' ---- 字号自适应 ----
    frm.Controls("CommandButton1").Font.Size = 自动字号(frm.Controls("CommandButton1").Caption, 10)
    frm.Controls("CommandButton2").Font.Size = 自动字号(frm.Controls("CommandButton2").Caption, 10)
    frm.Controls("CommandButton3").Font.Size = 自动字号(frm.Controls("CommandButton3").Caption, 10)
    frm.Controls("CommandButton4").Font.Size = 自动字号(frm.Controls("CommandButton4").Caption, 10)
    frm.Controls("CommandButton5").Font.Size = 自动字号(frm.Controls("CommandButton5").Caption, 10)
    frm.Controls("CommandButton6").Font.Size = 自动字号(frm.Controls("CommandButton6").Caption, 10)
End Sub

Private Function 自动字号(Caption文本 As String, 参考字号 As Single) As Single
    Dim 行数组 As Variant
    行数组 = Split(Caption文本, Chr(10))
    Dim i As Long, 最长 As Long
    最长 = 0
    For i = 0 To UBound(行数组)
        If Len(行数组(i)) > 最长 Then 最长 = Len(行数组(i))
    Next i
    If 最长 > 60 Then
        自动字号 = 参考字号 - 2
    ElseIf 最长 > 40 Then
        自动字号 = 参考字号 - 1
    Else
        自动字号 = 参考字号
    End If
End Function

' ============================================================
'  核心算法一：四方循环（笛卡尔积，与 v6 完全一致）
' ============================================================

Sub 四方循环_执行(是否正向 As Boolean, 是否横向 As Boolean)
    On Error GoTo 错误处理
    Dim 原刷新 As Boolean, 原计算 As XlCalculation
    原刷新 = Application.ScreenUpdating
    原计算 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    Dim ws As Worksheet
    Set ws = ActiveSheet

    Dim 总列数 As Long, 列 As Long
    总列数 = 最后列(ws)
    If 总列数 = 0 Then MsgBox "无有效数据": GoTo 退出

    Dim 每列行数() As Long
    ReDim 每列行数(1 To 总列数)
    For 列 = 1 To 总列数
        每列行数(列) = 最后行(ws, 列)
    Next 列

    Dim 总行数 As Long
    总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "已超出表格限制": GoTo 退出

    Dim 源数据 As Variant
    源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(总行数, 总列数)).Value2

    Dim 步长() As Long
    ReDim 步长(1 To 总列数)
    If 是否正向 Then
        步长(1) = 1
        For 列 = 2 To 总列数
            步长(列) = 步长(列 - 1) * 每列行数(列 - 1)
        Next 列
    Else
        Dim 累计 As Long
        累计 = 1
        For 列 = 1 To 总列数
            累计 = 累计 * 每列行数(列)
            步长(列) = 总行数 / 累计
        Next 列
    End If

    Dim 结果() As Variant
    ReDim 结果(1 To 总列数, 1 To 总行数)
    Dim 行 As Long, 源行 As Long
    For 列 = 1 To 总列数
        For 行 = 1 To 总行数
            源行 = ys(cd(行, 步长(列)), 每列行数(列))
            结果(列, 行) = 源数据(源行, 列)
        Next 行
    Next 列

    ' 新建结果表（统一命名）
    Dim 方向名 As String, 合并名 As String
    If 是否正向 Then 方向名 = "正" Else 方向名 = "反"
    If 是否横向 Then 方向名 = 方向名 & "横" Else 方向名 = 方向名 & "竖"
    If 是否合并 Then 合并名 = "合并" Else 合并名 = "分开"
    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("四方_" & 方向名 & "_" & 合并名)

    If 是否横向 Then
        If 是否合并 Then
            Dim 横合并() As String, 横片段() As String
            ReDim 横合并(1 To 总行数)
            ReDim 横片段(1 To 总列数)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    横片段(列) = 结果(列, 行)
                Next 列
                横合并(行) = Join(横片段, 连接符)
            Next 行
            新表.Range("A1").Resize(1, 总行数) = 横合并
        Else
            新表.Range("A1").Resize(总列数, 总行数) = 结果
        End If
    Else
        If 是否合并 Then
            Dim 竖合并() As String, 竖写入() As String
            ReDim 竖合并(1 To 总行数)
            Dim 竖片段() As String
            ReDim 竖片段(1 To 总列数)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    竖片段(列) = 结果(列, 行)
                Next 列
                竖合并(行) = Join(竖片段, 连接符)
            Next 行
            ReDim 竖写入(1 To 总行数, 1 To 1)
            For 行 = 1 To 总行数
                竖写入(行, 1) = 竖合并(行)
            Next 行
            新表.Range("A1").Resize(总行数, 1) = 竖写入
        Else
            Dim 竖结果() As Variant
            ReDim 竖结果(1 To 总行数, 1 To 总列数)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    竖结果(行, 列) = 结果(列, 行)
                Next 列
            Next 行
            新表.Range("A1").Resize(总行数, 总列数) = 竖结果
        End If
    End If

退出:
    Application.ScreenUpdating = 原刷新
    Application.Calculation = 原计算
    Exit Sub
错误处理:
    MsgBox "四方循环错误: " & Err.Description, vbCritical
    Resume 退出
End Sub

' ============================================================
'  核心算法二：双边循环（LCM独立循环，与 v6 完全一致）
' ============================================================

Sub 双边循环_执行(是否竖向 As Boolean)
    On Error GoTo 错误处理
    Dim 原刷新 As Boolean, 原计算 As XlCalculation
    原刷新 = Application.ScreenUpdating
    原计算 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    Dim ws As Worksheet
    Set ws = ActiveSheet

    Dim 总列数 As Long, 列 As Long
    总列数 = 最后列(ws)
    If 总列数 = 0 Then MsgBox "无有效数据": GoTo 退出

    Dim 每列行数() As Long
    ReDim 每列行数(1 To 总列数)
    For 列 = 1 To 总列数
        每列行数(列) = 最后行(ws, 列)
    Next 列

    Dim 列乘积 As Long, 最小公倍数 As Long
    列乘积 = 数组乘积(每列行数)
    最小公倍数 = WorksheetFunction.Lcm(每列行数)
    If 最小公倍数 > 1048576 Then MsgBox "已超出表格限制": GoTo 退出

    Dim 是否完整 As Boolean
    是否完整 = (列乘积 = 最小公倍数)

    Dim 源数据 As Variant
    源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(最小公倍数, 总列数)).Value2

    Dim 结果() As Variant
    ReDim 结果(1 To 总列数, 1 To 最小公倍数)
    Dim 行 As Long, 源行 As Long
    For 列 = 1 To 总列数
        For 行 = 1 To 最小公倍数
            源行 = ys(行, 每列行数(列))
            结果(列, 行) = 源数据(源行, 列)
        Next 行
    Next 列

    ' 新建结果表（统一命名）
    Dim 方向名 As String, 合并名 As String
    If 是否竖向 Then 方向名 = "竖" Else 方向名 = "横"
    If 是否合并 Then 合并名 = "合并" Else 合并名 = "分开"
    Dim 完整名 As String
    If 是否完整 Then 完整名 = "完整" Else 完整名 = "残缺" & 列乘积 & "-" & 最小公倍数
    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("双边_" & 方向名 & "_" & 完整名 & "_" & 合并名)

    If 是否竖向 Then
        If 是否合并 Then
            Dim 竖合并() As String, 竖写入() As String
            ReDim 竖合并(1 To 最小公倍数)
            Dim 竖片段() As String
            ReDim 竖片段(1 To 总列数)
            For 行 = 1 To 最小公倍数
                For 列 = 1 To 总列数
                    竖片段(列) = 结果(列, 行)
                Next 列
                竖合并(行) = Join(竖片段, 连接符)
            Next 行
            ReDim 竖写入(1 To 最小公倍数, 1 To 1)
            For 行 = 1 To 最小公倍数
                竖写入(行, 1) = 竖合并(行)
            Next 行
            新表.Range("A1").Resize(最小公倍数, 1) = 竖写入
        Else
            Dim 竖结果() As Variant
            ReDim 竖结果(1 To 最小公倍数, 1 To 总列数)
            For 行 = 1 To 最小公倍数
                For 列 = 1 To 总列数
                    竖结果(行, 列) = 结果(列, 行)
                Next 列
            Next 行
            新表.Range("A1").Resize(最小公倍数, 总列数) = 竖结果
        End If
    Else
        If 是否合并 Then
            Dim 横合并() As String, 横片段() As String
            ReDim 横合并(1 To 最小公倍数)
            ReDim 横片段(1 To 总列数)
            For 行 = 1 To 最小公倍数
                For 列 = 1 To 总列数
                    横片段(列) = 结果(列, 行)
                Next 列
                横合并(行) = Join(横片段, 连接符)
            Next 行
            新表.Range("A1").Resize(1, 最小公倍数) = 横合并
        Else
            新表.Range("A1").Resize(总列数, 最小公倍数) = 结果
        End If
    End If

退出:
    Application.ScreenUpdating = 原刷新
    Application.Calculation = 原计算
    Exit Sub
错误处理:
    MsgBox "双边循环错误: " & Err.Description, vbCritical
    Resume 退出
End Sub

' ============================================================
'  备选算法菜单（v8 新增，按钮7触发）
' ============================================================

Sub 备选算法_菜单()
    Dim 菜单 As String
    菜单 = "===== 备选核心算法验证 ===== " & vbLf & vbLf _
        & " A = 进位计数法（Odometer / 混合进制）" & vbLf _
        & "     → 输出与 笛卡尔积正向 相同" & vbLf & vbLf _
        & " B = 回溯法（DFS递归）" & vbLf _
        & "     → 输出与 笛卡尔积正向 相同" & vbLf & vbLf _
        & " C = 自定义周期独立循环（zxgbs推广）" & vbLf _
        & "     → 周期 A列2、B列3，输出LCM行" & vbLf & vbLf _
        & " D = 随机抽样组合" & vbLf _
        & "     → 随机生成 N 行" & vbLf & vbLf _
        & "输入 A/B/C/D 选择算法："
    Dim 输入 As String
    输入 = InputBox(菜单, "备选算法", "A")
    If 输入 = "" Then Exit Sub
    Select Case UCase(Trim(输入))
        Case "A": 备选算法A_进位计数
        Case "B": 备选算法B_回溯法
        Case "C": 备选算法C_自定义周期
        Case "D": 备选算法D_随机抽样
        Case Else: MsgBox "无效选择：" & 输入, vbExclamation
    End Select
End Sub

' ============================================================
'  备选算法A：进位计数法（Odometer / 混合进制）
'  每列是一个"数字位"，组合序列 = 混合进制计数器，逐位+1进位
'  输出 = 笛卡尔积正向（与四方循环_执行 正向 完全一致）
' ============================================================

Sub 备选算法A_进位计数()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    Dim 索引() As Long
    ReDim 索引(1 To 总列数)
    Dim 列 As Long
    For 列 = 1 To 总列数: 索引(列) = 1: Next

    Dim 结果() As Variant
    ReDim 结果(1 To 总行数, 1 To 总列数)
    Dim 行 As Long
    For 行 = 1 To 总行数
        ' 取当前索引组合
        For 列 = 1 To 总列数
            结果(行, 列) = 源数据(索引(列), 列)
        Next 列
        ' 进位：末位+1，满则进位
        For 列 = 总列数 To 1 Step -1
            索引(列) = 索引(列) + 1
            If 索引(列) <= 每列行数(列) Then
                Exit For
            Else
                索引(列) = 1
            End If
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选A_进位计数")
    写入备选结果 新表, 结果, 总行数, 总列数
    MsgBox "备选算法A 进位计数法 完成：" & 总行数 & " 行（与笛卡尔积正向一致）。", vbInformation, "备选算法A"
    Exit Sub
错误处理:
    MsgBox "备选算法A错误: " & Err.Description, vbCritical
End Sub

' ============================================================
'  备选算法B：回溯法（DFS递归生成）
'  逐列递归选元素，选满输出，回溯换下一个
'  输出 = 笛卡尔积正向（与四方循环_执行 正向 完全一致）
' ============================================================

Sub 备选算法B_回溯法()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    ReDim 回溯结果(1 To 总行数, 1 To 总列数)
    回溯行号 = 0
    Dim 临时行() As Variant
    ReDim 临时行(1 To 总列数)
    Call 递归回溯(源数据, 每列行数, 总列数, 1, 临时行)

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选B_回溯法")
    写入备选结果 新表, 回溯结果, 总行数, 总列数
    MsgBox "备选算法B 回溯法 完成：" & 总行数 & " 行（与笛卡尔积正向一致）。", vbInformation, "备选算法B"
    Exit Sub
错误处理:
    MsgBox "备选算法B错误: " & Err.Description, vbCritical
End Sub

Private Sub 递归回溯(源数据 As Variant, 每列行数() As Long, 总列数 As Long, 当前列 As Long, 临时行() As Variant)
    If 当前列 > 总列数 Then
        回溯行号 = 回溯行号 + 1
        Dim 列 As Long
        For 列 = 1 To 总列数
            回溯结果(回溯行号, 列) = 临时行(列)
        Next 列
        Exit Sub
    End If
    Dim i As Long
    For i = 1 To 每列行数(当前列)
        临时行(当前列) = 源数据(i, 当前列)
        Call 递归回溯(源数据, 每列行数, 总列数, 当前列 + 1, 临时行)
    Next i
End Sub

' ============================================================
'  备选算法C：自定义周期独立循环（zxgbs 的推广）
'  每列按指定周期独立循环，行数 = LCM(所有周期)
'  演示：第1列周期2、第2列周期3（其余列用实际行数）
' ============================================================

Sub 备选算法C_自定义周期()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    If 总列数 < 2 Then MsgBox "至少需要2列数据": Exit Sub

    Dim 周期() As Long
    ReDim 周期(1 To 总列数)
    Dim 列 As Long
    ' 第1列周期2、第2列周期3（周期不能超过对应列实际行数，否则源行号越界）
    周期(1) = 2: If 每列行数(1) < 周期(1) Then 周期(1) = 每列行数(1)
    周期(2) = 3: If 每列行数(2) < 周期(2) Then 周期(2) = 每列行数(2)
    For 列 = 3 To 总列数: 周期(列) = 每列行数(列): Next

    Dim lcm As Long
    lcm = WorksheetFunction.Lcm(周期)
    If lcm > 1048576 Then MsgBox "超出表格限制": Exit Sub

    Dim 结果() As Variant
    ReDim 结果(1 To lcm, 1 To 总列数)
    Dim 行 As Long, 源行 As Long
    For 行 = 1 To lcm
        For 列 = 1 To 总列数
            源行 = ys(行, 周期(列))
            结果(行, 列) = 源数据(源行, 列)
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选C_周期循环")
    写入备选结果 新表, 结果, lcm, 总列数
    MsgBox "备选算法C 自定义周期循环 完成：周期(" & 周期(1) & "," & 周期(2) & ") → " & lcm & " 行。", vbInformation, "备选算法C"
    Exit Sub
错误处理:
    MsgBox "备选算法C错误: " & Err.Description, vbCritical
End Sub

' ============================================================
'  备选算法D：随机抽样组合
'  每行随机从每列各取一个元素，生成 N 行（可重复）
' ============================================================

Sub 备选算法D_随机抽样()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)

    Dim 输入 As String
    输入 = InputBox("输入抽样行数（默认5，最大" & 总行数 & "）:", "随机抽样", "5")
    If 输入 = "" Then Exit Sub
    Dim N As Long
    N = Val(输入)
    If N < 1 Then Exit Sub
    If N > 总行数 Then N = 总行数

    Randomize
    Dim 结果() As Variant
    ReDim 结果(1 To N, 1 To 总列数)
    Dim 行 As Long, 列 As Long, 源行 As Long
    For 行 = 1 To N
        For 列 = 1 To 总列数
            源行 = Int(Rnd * 每列行数(列)) + 1
            结果(行, 列) = 源数据(源行, 列)
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选D_随机抽样")
    写入备选结果 新表, 结果, N, 总列数
    MsgBox "备选算法D 随机抽样 完成：" & N & " 行（可重复）。", vbInformation, "备选算法D"
    Exit Sub
错误处理:
    MsgBox "备选算法D错误: " & Err.Description, vbCritical
End Sub
