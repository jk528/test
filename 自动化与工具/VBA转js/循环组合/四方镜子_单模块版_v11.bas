'============================================================
' 四方镜子 - 单模块版 v11.6（四象限真正镜像对称）
' 基于 v11.5 优化：横向布局下"合并/分开"视觉方向不同，镜像公式需分模式
' v11.6 修复：横向合并 [RE,identity,RE]（单行：左右=RE, 上下=identity），横向分开 [R,E,RE]，竖向 [E,R,RE]
' 现有功能（不变）：
'   - 四方循环 scct（笛卡尔积，4个按钮：正竖/反竖/正横/反横）
'   - 双边循环 zxgbs（LCM独立循环，2个按钮）
'   - 备选算法验证（7种：A/B/C/D/E/F/G）
'   - 数据反转开关
' 四象限镜像（v11.6 优化）：
'   - 左上=原始  右上=左右镜像  左下=上下镜像  右下=中心镜像（双反转）
'   - 横向合并: Q2=RE(双反转), Q3=identity(无变换), Q4=RE  [RE,identity,RE]
'   - 横向分开: Q2=R(组合反转), Q3=E(元素反转), Q4=RE     [R,E,RE]
'   - 竖向:     Q2=E(元素反转), Q3=R(行反转),   Q4=RE     [E,R,RE]
'   - 选择布局（竖向/横向），一个按钮生成
'   - 支持合并/分开模式，支持数据反转
'   - 严格满足：左右对称 + 上下对称 + 中心对称
' 模式：Designer.Controls.Add + CodeModule 注入事件代码
' 使用方法：运行 四方镜子()
' 注意：需启用"信任对VBA工程对象模型的访问"
'============================================================

Option Explicit

' 全局变量
Public 连接符 As String
Public 是否合并 As Boolean
Public 数据是否反转 As Boolean  ' v9 新增：数据行序是否反转（从下到上读取）
Public 四象限是否对称 As Boolean  ' v11.5 新增：四方循环按钮是否输出四象限对称版
' v11.6 修复：横向合并 [RE,identity,RE]，横向分开 [R,E,RE]，竖向 [E,R,RE]

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
    数据是否反转 = False  ' v9 新增：默认不反转

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

    ' --- 复选框1：合并 ---
    Dim chk1 As Object
    Set chk1 = 设计器.Controls.Add("Forms.CheckBox.1", "CheckBox1")
    With chk1
        .Caption = "合并"
        .Left = 200: .Top = 12: .Width = 60: .Height = 18
        .Value = True
        .Font.Size = 10
    End With

    ' --- 复选框2：数据反转（v9 新增） ---
    Dim chk2 As Object
    Set chk2 = 设计器.Controls.Add("Forms.CheckBox.1", "CheckBox2")
    With chk2
        .Caption = "数据反转"
        .Left = 280: .Top = 12: .Width = 80: .Height = 18
        .Value = False
        .Font.Size = 10
    End With

    ' --- 复选框3：四象限对称（v11.5 新增） ---
    Dim chk3 As Object
    Set chk3 = 设计器.Controls.Add("Forms.CheckBox.1", "CheckBox3")
    With chk3
        .Caption = "四象限对称"
        .Left = 380: .Top = 12: .Width = 90: .Height = 18
        .Value = False
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
        .Left = 20: .Top = 405: .Width = 520: .Height = 26
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

    ' ---- CheckBox1_Click（合并） ----
    i = i + 1: CM.InsertLines i, "Private Sub CheckBox1_Click()"
    i = i + 1: CM.InsertLines i, "    是否合并 = CheckBox1.Value"
    i = i + 1: CM.InsertLines i, "    更新按钮图示 Me"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- CheckBox2_Click（数据反转，v9 新增） ----
    i = i + 1: CM.InsertLines i, "Private Sub CheckBox2_Click()"
    i = i + 1: CM.InsertLines i, "    数据是否反转 = CheckBox2.Value"
    i = i + 1: CM.InsertLines i, "    更新按钮图示 Me"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- CheckBox3_Click（四象限对称，v11.5 新增） ----
    i = i + 1: CM.InsertLines i, "Private Sub CheckBox3_Click()"
    i = i + 1: CM.InsertLines i, "    四象限是否对称 = CheckBox3.Value"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- 按钮1~4：四方循环（四象限开关打开时生成四象限） ----
    i = i + 1: CM.InsertLines i, "Private Sub CommandButton1_Click()"
    i = i + 1: CM.InsertLines i, "    If 四象限是否对称 Then 四象限_执行 False, False Else 四方循环_执行 False, False"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton2_Click()"
    i = i + 1: CM.InsertLines i, "    If 四象限是否对称 Then 四象限_执行 True, True Else 四方循环_执行 True, True"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton3_Click()"
    i = i + 1: CM.InsertLines i, "    If 四象限是否对称 Then 四象限_执行 True, False Else 四方循环_执行 True, False"
    i = i + 1: CM.InsertLines i, "    Unload Me"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    i = i + 1: CM.InsertLines i, "Private Sub CommandButton4_Click()"
    i = i + 1: CM.InsertLines i, "    If 四象限是否对称 Then 四象限_执行 False, True Else 四方循环_执行 False, True"
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
    i = i + 1: CM.InsertLines i, ""

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

' v9 新增：反序后缀（用于结果表命名）
Private Function 反序后缀() As String
    If 数据是否反转 Then 反序后缀 = "_反序" Else 反序后缀 = ""
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

    ' v9 新增：数据反转（每列从下到上读取）
    If 数据是否反转 Then
        Dim 反转后() As Variant
        ReDim 反转后(1 To 最大行, 1 To 总列数)
        Dim 行 As Long, 反转行 As Long
        For 列 = 1 To 总列数
            For 行 = 1 To 每列行数(列)
                反转行 = 每列行数(列) - 行 + 1
                反转后(行, 列) = 源数据(反转行, 列)
            Next 行
            ' 空白行（短列的多余行）保持原样（空值）
            For 行 = 每列行数(列) + 1 To 最大行
                反转后(行, 列) = 源数据(行, 列)
            Next 行
        Next 列
        源数据 = 反转后
    End If
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

    ' v9 新增：数据反转时，每列顺序颠倒（a2在上，a1在下）
    If 数据是否反转 Then
        Dim t As String
        t = d1a: d1a = d2a: d2a = t          ' A列：a1↔a2
        t = d1b: d1b = d3b: d3b = t          ' B列：b1↔b3（中间b2不变）
    End If

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

    ' v9 新增：数据反转（每列从下到上读取）
    If 数据是否反转 Then
        Dim 反转源() As Variant
        ReDim 反转源(1 To 总行数, 1 To 总列数)
        Dim r As Long, 反转源行 As Long
        For 列 = 1 To 总列数
            For r = 1 To 每列行数(列)
                反转源行 = 每列行数(列) - r + 1
                反转源(r, 列) = 源数据(反转源行, 列)
            Next r
            ' 短列的多余行保持原样
            For r = 每列行数(列) + 1 To 总行数
                反转源(r, 列) = 源数据(r, 列)
            Next r
        Next 列
        源数据 = 反转源
    End If

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
    Dim 方向名 As String, 合并名 As String, 反转名 As String
    If 是否正向 Then 方向名 = "正" Else 方向名 = "反"
    If 是否横向 Then 方向名 = 方向名 & "横" Else 方向名 = 方向名 & "竖"
    If 是否合并 Then 合并名 = "合并" Else 合并名 = "分开"
    If 数据是否反转 Then 反转名 = "_反序" Else 反转名 = ""
    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("四方_" & 方向名 & "_" & 合并名 & 反转名)

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
            ' 横分开：K行 × M列（每列一个组合，元素从上往下读）
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

    ' v9 新增：数据反转（每列从下到上读取）
    If 数据是否反转 Then
        Dim 反转源2() As Variant
        ReDim 反转源2(1 To 最小公倍数, 1 To 总列数)
        Dim r2 As Long, 反转源行2 As Long
        For 列 = 1 To 总列数
            For r2 = 1 To 每列行数(列)
                反转源行2 = 每列行数(列) - r2 + 1
                反转源2(r2, 列) = 源数据(反转源行2, 列)
            Next r2
            For r2 = 每列行数(列) + 1 To 最小公倍数
                反转源2(r2, 列) = 源数据(r2, 列)
            Next r2
        Next 列
        源数据 = 反转源2
    End If

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
    Dim 方向名 As String, 合并名 As String, 反转名2 As String
    If 是否竖向 Then 方向名 = "竖" Else 方向名 = "横"
    If 是否合并 Then 合并名 = "合并" Else 合并名 = "分开"
    If 数据是否反转 Then 反转名2 = "_反序" Else 反转名2 = ""
    Dim 完整名 As String
    If 是否完整 Then 完整名 = "完整" Else 完整名 = "残缺" & 列乘积 & "-" & 最小公倍数
    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("双边_" & 方向名 & "_" & 完整名 & "_" & 合并名 & 反转名2)

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
'  四象限对称生成（v11.5，四象限开关打开时由按钮1~4触发）
'  是否竖向=True  → 竖向版：每个组合占一行，左右两列并排
'  是否竖向=False → 横向版：每个组合占一列，上下两行堆叠
'  四象限布局：
'    左上：正向（左快右慢，原始数据）
'    右上：反向（右快左慢，原始数据）   ← 左右对称
'    左下：正向（左快右慢，反转数据）   ← 上下对称
'    右下：反向（右快左慢，反转数据）   ← 中心对称
' ============================================================

Sub 四象限_执行(是否正向 As Boolean, 是否横向 As Boolean)
    On Error GoTo 错误处理
    Dim 原刷新 As Boolean, 原计算 As XlCalculation
    原刷新 = Application.ScreenUpdating
    原计算 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    ' ---- 所有变量统一声明 ----
    Dim ws As Worksheet
    Dim 总列数 As Long, 列 As Long, 行 As Long
    Dim 每列行数() As Long, 总行数 As Long
    Dim 源数据 As Variant
    Dim 反转数据() As Variant
    Dim r As Long, 反转行 As Long
    ' 四个象限数据（按列存：Q(列, 行)）
    Dim Q1() As Variant  ' 左上 = 基准
    Dim Q2() As Variant  ' 右上 = 左右镜像（元素反转）
    Dim Q3() As Variant  ' 左下 = 上下镜像（行反转）
    Dim Q4() As Variant  ' 右下 = 中心镜像（行+元素双反转）
    Dim 合并名 As String, 反转后缀 As String
    Dim 基准名 As String, 布局名 As String
    Dim 是否竖向 As Boolean
    Dim 新表 As Worksheet
    Dim i As Long, j As Long
    ' 竖向布局用
    Dim 左列() As String, 右列() As String
    Dim 片段竖() As String
    Dim 每象限列数 As Long, 右上起始列 As Long
    Dim 下起始行 As Long
    ' 横向布局用
    Dim 上左横() As String, 上右横() As String
    Dim 下左横() As String, 下右横() As String
    Dim 片段横() As String
    Dim 列索引 As Long
    Dim 右上起始列横 As Long
    Dim 每组合行数 As Long
    Dim 右上起始列横2 As Long
    Dim 下起始行横 As Long
    Dim ci As Long, ri As Long
    ' =========================

    Set ws = ActiveSheet

    总列数 = 最后列(ws)
    If 总列数 = 0 Then MsgBox "无有效数据": GoTo 退出

    ReDim 每列行数(1 To 总列数)
    For 列 = 1 To 总列数
        每列行数(列) = 最后行(ws, 列)
    Next 列

    总行数 = 数组乘积(每列行数)
    If 总行数 > 500000 Then MsgBox "行数过大，四象限暂不支持（单象限需在50万行内）": GoTo 退出

    ' 读取原始数据
    源数据 = ws.Range(ws.Cells(1, 1), ws.Cells(总行数, 总列数)).Value2

    ' 生成反转数据（每列上下颠倒）—— 供数据反转开关使用
    ReDim 反转数据(1 To 总行数, 1 To 总列数)
    For 列 = 1 To 总列数
        For r = 1 To 每列行数(列)
            反转行 = 每列行数(列) - r + 1
            反转数据(r, 列) = 源数据(反转行, 列)
        Next r
        For r = 每列行数(列) + 1 To 总行数
            反转数据(r, 列) = 源数据(r, 列)
        Next r
    Next 列

    ' ---- 计算布局和基准名 ----
    是否竖向 = Not 是否横向
    If 是否正向 Then 基准名 = "正" Else 基准名 = "反"
    If 是否竖向 Then 布局名 = "竖" Else 布局名 = "横"

    ' ---- 生成 Q1 左上 = 基准数据 ----
    If 数据是否反转 Then
        生成scct结果 Q1, 反转数据, 每列行数, 总列数, 总行数, 是否正向
    Else
        生成scct结果 Q1, 源数据, 每列行数, 总列数, 总行数, 是否正向
    End If

    ' ---- 生成 Q2/Q3/Q4：视觉对称 = 字符串反转 ----
    '   变换类型: 0=identity(无变换), 1=R(组合反转), 2=E(元素反转), 3=RE(双反转)
    '   横向合并: Q2=RE(3), Q3=identity(0), Q4=RE(3)  — 单行：左右=RE, 上下=identity
    '   横向分开: Q2=R(1),  Q3=E(2),        Q4=RE(3)  — 多行：左右=R, 上下=E
    '   竖向:     Q2=E(2),  Q3=R(1),        Q4=RE(3)  — 竖向：左右=E, 上下=R
    Dim 变换表(1 To 3) As Long  ' Q2/Q3/Q4 的变换类型
    Dim jj As Long, ii As Long
    If 是否横向 And 是否合并 Then
        变换表(1) = 3: 变换表(2) = 0: 变换表(3) = 3  ' 横向合并: RE, identity, RE
    ElseIf 是否横向 Then
        变换表(1) = 1: 变换表(2) = 2: 变换表(3) = 3  ' 横向分开: R, E, RE
    Else
        变换表(1) = 2: 变换表(2) = 1: 变换表(3) = 3  ' 竖向: E, R, RE
    End If
    ReDim Q2(1 To 总列数, 1 To 总行数)
    ReDim Q3(1 To 总列数, 1 To 总行数)
    ReDim Q4(1 To 总列数, 1 To 总行数)
    For i = 1 To 总行数
        For j = 1 To 总列数
            ' Q2
            jj = j: ii = i
            If 变换表(1) = 2 Or 变换表(1) = 3 Then jj = 总列数 - j + 1  ' E: 反转列(元素)
            If 变换表(1) = 1 Or 变换表(1) = 3 Then ii = 总行数 - i + 1  ' R: 反转行(组合)
            Q2(j, i) = Q1(jj, ii)
            ' Q3
            jj = j: ii = i
            If 变换表(2) = 2 Or 变换表(2) = 3 Then jj = 总列数 - j + 1
            If 变换表(2) = 1 Or 变换表(2) = 3 Then ii = 总行数 - i + 1
            Q3(j, i) = Q1(jj, ii)
            ' Q4
            jj = j: ii = i
            If 变换表(3) = 2 Or 变换表(3) = 3 Then jj = 总列数 - j + 1
            If 变换表(3) = 1 Or 变换表(3) = 3 Then ii = 总行数 - i + 1
            Q4(j, i) = Q1(jj, ii)
        Next j
    Next i

    ' 新建结果表
    If 是否合并 Then 合并名 = "合并" Else 合并名 = "分开"
    If 数据是否反转 Then 反转后缀 = "_反序" Else 反转后缀 = ""
    Set 新表 = 新建结果表("四象限_" & 基准名 & 布局名 & "_" & 合并名 & 反转后缀)

    If 是否竖向 Then
        ' ============== 竖向布局：每个组合一行 ==============
        If 是否合并 Then
            ' 合并模式：每象限1列字符串
            ReDim 左列(1 To 总行数, 1 To 1)
            ReDim 右列(1 To 总行数, 1 To 1)
            ReDim 片段竖(1 To 总列数)

            ' 上半：左上(Q1) + 右上(Q2)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    片段竖(列) = Q1(列, 行)
                Next 列
                左列(行, 1) = Join(片段竖, 连接符)
                For 列 = 1 To 总列数
                    片段竖(列) = Q2(列, 行)
                Next 列
                右列(行, 1) = Join(片段竖, 连接符)
            Next 行
            新表.Range("A2").Resize(总行数, 1) = 左列
            新表.Range("C2").Resize(总行数, 1) = 右列

            ' 下半：左下(Q3) + 右下(Q4)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    片段竖(列) = Q3(列, 行)
                Next 列
                左列(行, 1) = Join(片段竖, 连接符)
                For 列 = 1 To 总列数
                    片段竖(列) = Q4(列, 行)
                Next 列
                右列(行, 1) = Join(片段竖, 连接符)
            Next 行
            新表.Range("A" & 总行数 + 4).Resize(总行数, 1) = 左列
            新表.Range("C" & 总行数 + 4).Resize(总行数, 1) = 右列

            ' 标签（竖合并）
            新表.Cells(1, 1).Value = "【左上 原始】"
            新表.Cells(1, 3).Value = "【右上 左右镜像】"
            新表.Cells(总行数 + 3, 1).Value = "【左下 上下镜像】"
            新表.Cells(总行数 + 3, 3).Value = "【右下 中心镜像】"
        Else
            ' 分开模式：每象限K列，中间空1列
            每象限列数 = 总列数
            右上起始列 = 每象限列数 + 2

            ' 上半
            For 列 = 1 To 每象限列数
                For 行 = 1 To 总行数
                    新表.Cells(行 + 1, 列).Value = Q1(列, 行)
                    新表.Cells(行 + 1, 右上起始列 + 列 - 1).Value = Q2(列, 行)
                Next 行
            Next 列

            ' 下半
            下起始行 = 总行数 + 4
            For 列 = 1 To 每象限列数
                For 行 = 1 To 总行数
                    新表.Cells(下起始行 + 行 - 1, 列).Value = Q3(列, 行)
                    新表.Cells(下起始行 + 行 - 1, 右上起始列 + 列 - 1).Value = Q4(列, 行)
                Next 行
            Next 列

            ' 标签（竖分开）
            新表.Cells(1, 1).Value = "【左上 原始】"
            新表.Cells(1, 右上起始列).Value = "【右上 左右镜像】"
            新表.Cells(下起始行 - 1, 1).Value = "【左下 上下镜像】"
            新表.Cells(下起始行 - 1, 右上起始列).Value = "【右下 中心镜像】"
        End If
    Else
        ' ============== 横向布局：组合横向排列 ==============
        If 是否合并 Then
            ' 合并模式：每象限1行字符串
            ReDim 上左横(1 To 总行数)
            ReDim 上右横(1 To 总行数)
            ReDim 下左横(1 To 总行数)
            ReDim 下右横(1 To 总行数)
            ReDim 片段横(1 To 总列数)
            For 列索引 = 1 To 总行数
                For 列 = 1 To 总列数
                    片段横(列) = Q1(列, 列索引)
                Next 列
                上左横(列索引) = Join(片段横, 连接符)
                For 列 = 1 To 总列数
                    片段横(列) = Q2(列, 列索引)
                Next 列
                上右横(列索引) = Join(片段横, 连接符)
                For 列 = 1 To 总列数
                    片段横(列) = Q3(列, 列索引)
                Next 列
                下左横(列索引) = Join(片段横, 连接符)
                For 列 = 1 To 总列数
                    片段横(列) = Q4(列, 列索引)
                Next 列
                下右横(列索引) = Join(片段横, 连接符)
            Next 列索引

            ' 写入布局
            右上起始列横 = 总行数 + 3
            新表.Range("B2").Resize(1, 总行数) = 上左横
            新表.Cells(2, 右上起始列横).Resize(1, 总行数) = 上右横
            新表.Range("B5").Resize(1, 总行数) = 下左横
            新表.Cells(5, 右上起始列横).Resize(1, 总行数) = 下右横

            ' 标签（横合并）
            新表.Cells(1, 2).Value = "【左上 原始】"
            新表.Cells(1, 右上起始列横).Value = "【右上 左右镜像】"
            新表.Cells(4, 2).Value = "【左下 上下镜像】"
            新表.Cells(4, 右上起始列横).Value = "【右下 中心镜像】"
        Else
            ' 横分开：K行 × M列（每列一个组合，元素从上往下读）
            每组合行数 = 总列数
            右上起始列横2 = 总行数 + 3 ' 中间空2列

            ' 上半：Q1 + Q2
            For ci = 1 To 总行数
                For ri = 1 To 每组合行数
                    新表.Cells(ri + 1, ci + 1).Value = Q1(ri, ci)
                    新表.Cells(ri + 1, 右上起始列横2 + ci - 1).Value = Q2(ri, ci)
                Next ri
            Next ci

            ' 下半起始行
            下起始行横 = 每组合行数 + 4

            ' 下半：Q3 + Q4
            For ci = 1 To 总行数
                For ri = 1 To 每组合行数
                    新表.Cells(下起始行横 + ri - 1, ci + 1).Value = Q3(ri, ci)
                    新表.Cells(下起始行横 + ri - 1, 右上起始列横2 + ci - 1).Value = Q4(ri, ci)
                Next ri
            Next ci

            ' 标签（横分开）
            新表.Cells(1, 2).Value = "【左上 原始】"
            新表.Cells(1, 右上起始列横2).Value = "【右上 左右镜像】"
            新表.Cells(每组合行数 + 3, 2).Value = "【左下 上下镜像】"
            新表.Cells(每组合行数 + 3, 右上起始列横2).Value = "【右下 中心镜像】"
        End If
    End If

    ' 格式化
    新表.Cells.EntireColumn.AutoFit
    新表.Cells.EntireRow.AutoFit

    MsgBox "四象限镜像生成完成（基准：" & 基准名 & 布局名 & "）：" & 总行数 & " 组 × 4 象限。", vbInformation, "四象限镜像"

退出:
    Application.ScreenUpdating = 原刷新
    Application.Calculation = 原计算
    Exit Sub
错误处理:
    MsgBox "四象限错误: " & Err.Description, vbCritical
    Resume 退出
End Sub

' 辅助：生成 scct 结果（按列存），是否正向=True→左快右慢，False→右快左慢
Private Sub 生成scct结果(结果 As Variant, 源数据 As Variant, 每列行数() As Long, 总列数 As Long, 总行数 As Long, 是否正向 As Boolean)
    ReDim 结果(1 To 总列数, 1 To 总行数)
    Dim 步长() As Long
    ReDim 步长(1 To 总列数)
    Dim 列 As Long, 行 As Long, 源行 As Long
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
    For 列 = 1 To 总列数
        For 行 = 1 To 总行数
            源行 = ys(cd(行, 步长(列)), 每列行数(列))
            结果(列, 行) = 源数据(源行, 列)
        Next 行
    Next 列
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
        & "     → 随机生成 N 行（可重复/不重复）" & vbLf & vbLf _
        & " E = 逐列扩展法（Array Expansion）" & vbLf _
        & "     → 输出与 笛卡尔积正向 相同" & vbLf & vbLf _
        & " F = 格雷码遍历（Gray Code）" & vbLf _
        & "     → 相邻组合仅一列变化" & vbLf & vbLf _
        & " G = 混合进制随机访问（区间+正反）" & vbLf _
        & "     → 起始/结束序号+方向，直接取区间组合" & vbLf & vbLf _
        & "输入 A~G 选择算法："
    Dim 输入 As String
    输入 = InputBox(菜单, "备选算法", "A")
    If 输入 = "" Then Exit Sub
    Select Case UCase(Trim(输入))
        Case "A": 备选算法A_进位计数
        Case "B": 备选算法B_回溯法
        Case "C": 备选算法C_自定义周期
        Case "D": 备选算法D_随机抽样
        Case "E": 备选算法E_逐列扩展
        Case "F": 备选算法F_格雷码
        Case "G": 备选算法G_随机访问
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
    Set 新表 = 新建结果表("备选A_进位计数" & 反序后缀)
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
    Set 新表 = 新建结果表("备选B_回溯法" & 反序后缀)
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
    Set 新表 = 新建结果表("备选C_周期循环" & 反序后缀)
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

    ' 询问是否不重复（无放回）
    Dim 去重输入 As String
    去重输入 = InputBox("是否不重复（无放回）？" & vbLf & "  1 = 不重复（各行组合不重复）" & vbLf & "  0 = 可重复（有放回）" & vbLf & vbLf & "输入 1 或 0：", "随机抽样模式", "1")
    Dim 去重 As Boolean
    去重 = (去重输入 = "1")
    If 去重 Then
        If N > 总行数 Then
            MsgBox "不重复模式下抽样数不能超过总组合数（" & 总行数 & "）", vbExclamation
            Exit Sub
        End If
    End If

    Randomize
    Dim 结果() As Variant
    ReDim 结果(1 To N, 1 To 总列数)
    Dim 行 As Long, 列 As Long, 源行 As Long

    If 去重 Then
        ' 不重复：Partial Fisher-Yates 洗牌法（比"随机尝试+查重"高效得多）
        ' 原理：生成 1..总行数 的索引数组，洗牌只洗前 N 个，取前 N 个索引解码成组合。
        ' 特点：O(N) 时间、O(总行数) 空间，零重试、零查重，
        '       即使 N 接近总组合数（如抽 95/100）也不慢。
        Dim 索引数组() As Long
        ReDim 索引数组(1 To 总行数)
        Dim i As Long, j As Long, tmp As Long
        For i = 1 To 总行数: 索引数组(i) = i: Next
        For i = 1 To N
            j = Int(Rnd * (总行数 - i + 1)) + i
            tmp = 索引数组(i): 索引数组(i) = 索引数组(j): 索引数组(j) = tmp
        Next i
        ' 把索引解码为组合（混合进制：列1每行变、列2每n1行变...）
        Dim 余 As Long, 权重 As Long
        For 行 = 1 To N
            余 = 索引数组(行) - 1
            权重 = 1
            For 列 = 1 To 总列数
                结果(行, 列) = 源数据((余 \ 权重) Mod 每列行数(列) + 1, 列)
                权重 = 权重 * 每列行数(列)
            Next 列
        Next 行
    Else
        ' 可重复：直接随机（有放回）
        For 行 = 1 To N
            For 列 = 1 To 总列数
                源行 = Int(Rnd * 每列行数(列)) + 1
                结果(行, 列) = 源数据(源行, 列)
            Next 列
        Next 行
    End If

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选D_随机抽样" & 反序后缀)
    写入备选结果 新表, 结果, N, 总列数
    MsgBox "备选算法D 随机抽样 完成：" & N & " 行（" & IIf(去重, "不重复", "可重复") & "）。", vbInformation, "备选算法D"
    Exit Sub
错误处理:
    MsgBox "备选算法D错误: " & Err.Description, vbCritical
End Sub

' ============================================================
'  备选算法E：逐列扩展法（Array Expansion）
'  从第1列开始，每列把已有数组复制该列行数份，第 i 份追加该列第 i 个元素
'  输出 = 笛卡尔积正向（与 scct 正向一致）
' ============================================================

Sub 备选算法E_逐列扩展()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    ' 初始：第1列
    Dim 结果() As Variant
    ReDim 结果(1 To 每列行数(1), 1 To 1)
    Dim 行 As Long
    For 行 = 1 To 每列行数(1): 结果(行, 1) = 源数据(行, 1): Next

    Dim 列 As Long
    For 列 = 2 To 总列数
        Dim 新行数 As Long
        新行数 = UBound(结果, 1) * 每列行数(列)
        Dim 新结果() As Variant
        ReDim 新结果(1 To 新行数, 1 To 列)
        Dim k As Long, 旧列 As Long
        ' 外层按新列元素份数复制，内层展开已有组合 → 旧列（A）快变 = 正向顺序
        For k = 1 To 每列行数(列)
            For 行 = 1 To UBound(结果, 1)
                For 旧列 = 1 To 列 - 1
                    新结果((k - 1) * UBound(结果, 1) + 行, 旧列) = 结果(行, 旧列)
                Next 旧列
                新结果((k - 1) * UBound(结果, 1) + 行, 列) = 源数据(k, 列)
            Next 行
        Next k
        ' 结果 = 新结果（动态数组整体赋值）
        ReDim 结果(1 To 新行数, 1 To 列)
        For 行 = 1 To 新行数
            For 旧列 = 1 To 列
                结果(行, 旧列) = 新结果(行, 旧列)
            Next 旧列
        Next 行
    Next 列

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选E_逐列扩展" & 反序后缀)
    写入备选结果 新表, 结果, 总行数, 总列数
    MsgBox "备选算法E 逐列扩展法 完成：" & 总行数 & " 行（与笛卡尔积正向一致）。", vbInformation, "备选算法E"
    Exit Sub
错误处理:
    MsgBox "备选算法E错误: " & Err.Description, vbCritical
End Sub

' ============================================================
'  备选算法F：格雷码遍历（Gray Code）
'  相邻两个组合只差一列元素变化（递归反射构造）
'  应用：穷举测试相邻用例只改一个参数
' ============================================================

Sub 备选算法F_格雷码()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    ReDim 回溯结果(1 To 总行数, 1 To 总列数)
    回溯行号 = 0
    Dim 当前行() As Variant
    ReDim 当前行(1 To 总列数)
    Call 格雷递归(源数据, 每列行数, 总列数, 1, 1, 当前行)

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选F_格雷码" & 反序后缀)
    写入备选结果 新表, 回溯结果, 总行数, 总列数
    MsgBox "备选算法F 格雷码遍历 完成：" & 总行数 & " 行（相邻组合仅一列变化）。", vbInformation, "备选算法F"
    Exit Sub
错误处理:
    MsgBox "备选算法F错误: " & Err.Description, vbCritical
End Sub

' 格雷码递归反射：每层按方向取元素，子层方向按位置奇偶交替（奇→正向，偶→反向）
Private Sub 格雷递归(源数据 As Variant, 每列行数() As Long, 总列数 As Long, 当前列 As Long, 方向 As Long, 当前行() As Variant)
    If 当前列 > 总列数 Then
        回溯行号 = 回溯行号 + 1
        Dim 列 As Long
        For 列 = 1 To 总列数
            回溯结果(回溯行号, 列) = 当前行(列)
        Next 列
        Exit Sub
    End If
    Dim i As Long, 位置 As Long, 子方向 As Long
    If 方向 = 1 Then
        ' 正向：1..n
        For i = 1 To 每列行数(当前列)
            当前行(当前列) = 源数据(i, 当前列)
            位置 = i
            子方向 = IIf(位置 Mod 2 = 1, 1, -1)
            Call 格雷递归(源数据, 每列行数, 总列数, 当前列 + 1, 子方向, 当前行)
        Next i
    Else
        ' 反向：n..1（反射）
        For i = 每列行数(当前列) To 1 Step -1
            当前行(当前列) = 源数据(i, 当前列)
            位置 = 每列行数(当前列) - i + 1
            子方向 = IIf(位置 Mod 2 = 1, 1, -1)
            Call 格雷递归(源数据, 每列行数, 总列数, 当前列 + 1, 子方向, 当前行)
        Next i
    End If
End Sub

' ============================================================
'  备选算法G：混合进制随机访问（区间版 + 正/反向）
'  输入起始序号、结束序号、方向，直接解码输出该区间内所有组合
'  正向：左快右慢（= scct 正向）；反向：右快左慢（= scct 反向）
'  无需生成前面的组合，可随机访问任意区间（断点续算/并行分区基础）
' ============================================================

Sub 备选算法G_随机访问()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)

    ' 选择方向
    Dim 方向输入 As String
    方向输入 = InputBox("选择方向：" & vbLf & "  1 = 正向（左快右慢，= scct正向）" & vbLf & "  0 = 反向（右快左慢，= scct反向）" & vbLf & vbLf & "输入 1 或 0：", "混合进制随机访问 - 方向", "1")
    If 方向输入 = "" Then Exit Sub
    Dim 是否正向 As Boolean
    是否正向 = (方向输入 = "1")

    ' 输入起始序号
    Dim 起始输入 As String
    起始输入 = InputBox("输入起始序号（1~" & 总行数 & "）:", "混合进制随机访问 - 起始", "1")
    If 起始输入 = "" Then Exit Sub
    Dim 起始 As Long
    起始 = Val(起始输入)
    If 起始 < 1 Or 起始 > 总行数 Then
        MsgBox "起始序号超出范围（1~" & 总行数 & "）", vbExclamation
        Exit Sub
    End If

    ' 输入结束序号
    Dim 结束输入 As String
    结束输入 = InputBox("输入结束序号（" & 起始 & "~" & 总行数 & "）:", "混合进制随机访问 - 结束", CStr(起始))
    If 结束输入 = "" Then Exit Sub
    Dim 结束 As Long
    结束 = Val(结束输入)
    If 结束 < 起始 Or 结束 > 总行数 Then
        MsgBox "结束序号超出范围（" & 起始 & "~" & 总行数 & "）", vbExclamation
        Exit Sub
    End If

    Dim 输出行数 As Long
    输出行数 = 结束 - 起始 + 1
    If 输出行数 > 1048576 Then MsgBox "输出行数超出表格限制": Exit Sub

    ' 预计算权重数组
    '   正向（左快右慢）：权重(1)=1，权重(列)=权重(列-1)*每列行数(列-1)
    '   反向（右快左慢）：权重(总列数)=1，权重(列)=权重(列+1)*每列行数(列+1)
    Dim 权重() As Long
    ReDim 权重(1 To 总列数)
    Dim 列 As Long
    If 是否正向 Then
        权重(1) = 1
        For 列 = 2 To 总列数
            权重(列) = 权重(列 - 1) * 每列行数(列 - 1)
        Next 列
    Else
        权重(总列数) = 1
        For 列 = 总列数 - 1 To 1 Step -1
            权重(列) = 权重(列 + 1) * 每列行数(列 + 1)
        Next 列
    End If

    ' 混合进制解码：逐行计算
    Dim 结果() As Variant
    ReDim 结果(1 To 输出行数, 1 To 总列数)
    Dim 行 As Long, 余 As Long, k As Long
    For 行 = 1 To 输出行数
        k = 起始 + 行 - 1
        余 = k - 1
        For 列 = 1 To 总列数
            结果(行, 列) = 源数据((余 \ 权重(列)) Mod 每列行数(列) + 1, 列)
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("备选G_随机访问" & 反序后缀)
    写入备选结果 新表, 结果, 输出行数, 总列数
    MsgBox "备选算法G 混合进制随机访问：" & IIf(是否正向, "正向", "反向") & "，第 " & 起始 & " ~ " & 结束 & " 个组合，共 " & 输出行数 & " 行。", vbInformation, "备选算法G"
    Exit Sub
错误处理:
    MsgBox "备选算法G错误: " & Err.Description, vbCritical
End Sub
