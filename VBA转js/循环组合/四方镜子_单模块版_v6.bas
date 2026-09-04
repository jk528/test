'============================================================
' 四方镜子 - 单模块版 v6（模态 + 安全清理）
' 模式：Designer.Controls.Add + CodeModule 注入事件代码
' 原理：模态 Show 会阻塞直到窗体关闭，返回后立即 Remove 安全
' 使用方法：运行 四方镜子()
' 注意：需启用"信任对VBA工程对象模型的访问"
'============================================================

Option Explicit

' 全局变量
Public 连接符 As String
Public 是否合并 As Boolean

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
        .Item("Width") = 300
        .Item("Height") = 300
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
        .Left = 75: .Top = 10: .Width = 80: .Height = 22
        .Font.Size = 10
    End With

    ' --- 复选框 ---
    Dim chk As Object
    Set chk = 设计器.Controls.Add("Forms.CheckBox.1", "CheckBox1")
    With chk
        .Caption = "合并"
        .Left = 10: .Top = 40: .Width = 80: .Height = 18
        .Value = True
        .Font.Size = 10
    End With

    ' --- 框架1 ---
    Dim fra1 As Object
    Set fra1 = 设计器.Controls.Add("Forms.Frame.1", "Frame1")
    With fra1
        .Caption = "四方循环（笛卡尔积）"
        .Left = 10: .Top = 65: .Width = 275: .Height = 120
        .Font.Size = 10: .Font.Bold = True
    End With

    ' --- 按钮1：反向竖向 ---
    Dim btn1 As Object
    Set btn1 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton1")
    With btn1
        .Caption = "A1B1" & Chr(10) & "A1B2" & Chr(10) & "A2B1" & Chr(10) & "A2B2"
        .Left = 10: .Top = 25: .Width = 95: .Height = 55
        .Font.Size = 9
    End With

    ' --- 按钮3：正向竖向 ---
    Dim btn3 As Object
    Set btn3 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton3")
    With btn3
        .Caption = "A1B1" & Chr(10) & "A2B1" & Chr(10) & "A1B2" & Chr(10) & "A2B2"
        .Left = 150: .Top = 25: .Width = 95: .Height = 55
        .Font.Size = 9
    End With

    ' --- 按钮2：正向横向 ---
    Dim btn2 As Object
    Set btn2 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton2")
    With btn2
        .Caption = "A1B1 A2B1 A1B2 A2B2"
        .Left = 10: .Top = 90: .Width = 95: .Height = 25
        .Font.Size = 9
    End With

    ' --- 按钮4：反向横向 ---
    Dim btn4 As Object
    Set btn4 = fra1.Controls.Add("Forms.CommandButton.1", "CommandButton4")
    With btn4
        .Caption = "A1B1 A1B2 A2B1 A2B2"
        .Left = 150: .Top = 90: .Width = 95: .Height = 25
        .Font.Size = 9
    End With

    ' --- 框架2 ---
    Dim fra2 As Object
    Set fra2 = 设计器.Controls.Add("Forms.Frame.1", "Frame2")
    With fra2
        .Caption = "双边循环（LCM独立循环）"
        .Left = 10: .Top = 195: .Width = 275: .Height = 60
        .Font.Size = 10: .Font.Bold = True
    End With

    ' --- 按钮5：双边循环_竖 ---
    Dim btn5 As Object
    Set btn5 = fra2.Controls.Add("Forms.CommandButton.1", "CommandButton5")
    With btn5
        .Caption = "双边循环_合并_竖"
        .Left = 10: .Top = 20: .Width = 110: .Height = 25
        .Font.Size = 9
    End With

    ' --- 按钮6：双边循环_横 ---
    Dim btn6 As Object
    Set btn6 = fra2.Controls.Add("Forms.CommandButton.1", "CommandButton6")
    With btn6
        .Caption = "双边循环_合并_横"
        .Left = 150: .Top = 20: .Width = 110: .Height = 25
        .Font.Size = 9
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
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- TextBox1_Change ----
    i = i + 1: CM.InsertLines i, "Private Sub TextBox1_Change()"
    i = i + 1: CM.InsertLines i, "    连接符 = TextBox1.Text"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- CheckBox1_Click ----
    i = i + 1: CM.InsertLines i, "Private Sub CheckBox1_Click()"
    i = i + 1: CM.InsertLines i, "    是否合并 = CheckBox1.Value"
    i = i + 1: CM.InsertLines i, "    If 是否合并 Then"
    i = i + 1: CM.InsertLines i, "        CommandButton1.Caption = ""A1B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B1"" & Chr(10) & ""A2B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton3.Caption = ""A1B1"" & Chr(10) & ""A2B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton2.Caption = ""A1B1 A2B1 A1B2 A2B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton4.Caption = ""A1B1 A1B2 A2B1 A2B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton5.Caption = ""双边循环_合并_竖"""
    i = i + 1: CM.InsertLines i, "        CommandButton6.Caption = ""双边循环_合并_横"""
    i = i + 1: CM.InsertLines i, "    Else"
    i = i + 1: CM.InsertLines i, "        CommandButton1.Caption = ""A1  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A2  B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton3.Caption = ""A1  B1"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton2.Caption = ""A1  B1  A2  B1  A1  B2  A2  B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton4.Caption = ""A1  B1  A1  B2  A2  B1  A2  B2"""
    i = i + 1: CM.InsertLines i, "        CommandButton5.Caption = ""双边循环_分_竖"""
    i = i + 1: CM.InsertLines i, "        CommandButton6.Caption = ""双边循环_分_横"""
    i = i + 1: CM.InsertLines i, "    End If"
    i = i + 1: CM.InsertLines i, "    CommandButton1.SetFocus"
    i = i + 1: CM.InsertLines i, "End Sub"
    i = i + 1: CM.InsertLines i, ""

    ' ---- 按钮点击事件（执行后关闭窗体） ----
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
    If Len(表名) > 31 Then 表名 = Left(名称前缀, 31 - Len(Sheets.Count) - 1) & "_" & Sheets.Count
    On Error Resume Next
    ws.Name = 表名
    If Err.Number <> 0 Then ws.Name = "结果_" & Format(Now, "hhmmss")
    On Error GoTo 0
    Set 新建结果表 = ws
End Function

' ============================================================
'  核心算法一：四方循环（笛卡尔积）
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
'  核心算法二：双边循环（LCM独立循环）
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
