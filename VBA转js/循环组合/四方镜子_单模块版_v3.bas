'============================================================
' 四方镜子 - 单模块版 v3（修复 SetFocus 找不到控件）
' 修复：动态控件用 Me.Controls("名称") 方式访问，不用 Me.名称
' 使用方法：运行 四方镜子_主入口()
'============================================================

Option Explicit

' 全局变量
Private 当前连接符号 As String
Private 是否合并模式 As Boolean
Private 窗体名称 As String

' ============================================================
'  主入口
' ============================================================

Sub 四方镜子_主入口()
    On Error GoTo 错误处理
    
    ' 初始化
    当前连接符号 = "-"
    是否合并模式 = True
    窗体名称 = "frmSFJ_" & Format(Now, "hhmmss")  ' 用时间戳避免重名
    
    ' 1. 动态创建窗体
    Dim VBP As Object
    Set VBP = ThisWorkbook.VBProject
    
    Dim 窗体组件 As Object
    Set 窗体组件 = VBP.VBComponents.Add(3)  ' 3 = vbext_ct_MSForm
    窗体组件.Name = 窗体名称
    
    ' 2. 注入窗体代码
    窗体组件.CodeModule.AddFromString 生成窗体代码()
    
    ' 3. 显示窗体
    VBA.UserForms.Add(窗体名称).Show
    
    ' 4. 清理
    VBP.VBComponents.Remove 窗体组件
    
    Exit Sub

错误处理:
    MsgBox "错误 " & Err.Number & ": " & Err.Description, vbCritical, "四方镜子"
    ' 尝试清理残留窗体
    On Error Resume Next
    Dim VBP2 As Object
    Set VBP2 = ThisWorkbook.VBProject
    Dim comp As Object
    For Each comp In VBP2.VBComponents
        If comp.Name = 窗体名称 Then
            VBP2.VBComponents.Remove comp
            Exit For
        End If
    Next
End Sub

' ============================================================
'  生成窗体代码字符串
'  注意：所有动态控件用 Me.Controls("名称") 访问，不用 Me.名称
' ============================================================

Private Function 生成窗体代码() As String
    Dim 代码 As String
    
    代码 = "Option Explicit" & vbCrLf & vbCrLf
    
    ' ===== Initialize 事件：创建所有控件 =====
    代码 = 代码 & "Private Sub UserForm_Initialize()" & vbCrLf
    代码 = 代码 & "    Me.Caption = ""四方镜""" & vbCrLf
    代码 = 代码 & "    Me.Width = 330" & vbCrLf
    代码 = 代码 & "    Me.Height = 460" & vbCrLf
    代码 = 代码 & "    Me.StartUpPosition = 1" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 标签
    代码 = 代码 & "    With Me.Controls.Add(""Forms.Label.1"", ""Label1"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""连接符号:""" & vbCrLf
    代码 = 代码 & "        .Left = 20: .Top = 18: .Width = 60: .Height = 20" & vbCrLf
    代码 = 代码 & "        .Font.Size = 10" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 文本框
    代码 = 代码 & "    With Me.Controls.Add(""Forms.TextBox.1"", ""TextBox1"")" & vbCrLf
    代码 = 代码 & "        .Text = ""-""" & vbCrLf
    代码 = 代码 & "        .Left = 85: .Top = 15: .Width = 80: .Height = 22" & vbCrLf
    代码 = 代码 & "        .Font.Size = 10" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 复选框
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CheckBox.1"", ""CheckBox1"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""合并""" & vbCrLf
    代码 = 代码 & "        .Left = 20: .Top = 45: .Width = 80: .Height = 20" & vbCrLf
    代码 = 代码 & "        .Value = True" & vbCrLf
    代码 = 代码 & "        .Font.Size = 10" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 框架1
    代码 = 代码 & "    With Me.Controls.Add(""Forms.Frame.1"", ""Frame1"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""四方循环（笛卡尔积）""" & vbCrLf
    代码 = 代码 & "        .Left = 15: .Top = 75: .Width = 290: .Height = 175" & vbCrLf
    代码 = 代码 & "        .Font.Size = 10: .Font.Bold = True" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮1：反向竖向
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton1"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""A1B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B1"" & Chr(10) & ""A2B2""" & vbCrLf
    代码 = 代码 & "        .Left = 28: .Top = 102: .Width = 100: .Height = 60" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮3：正向竖向
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton3"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""A1B1"" & Chr(10) & ""A2B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B2""" & vbCrLf
    代码 = 代码 & "        .Left = 170: .Top = 102: .Width = 100: .Height = 60" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮2：正向横向
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton2"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""A1B1 A2B1 A1B2 A2B2""" & vbCrLf
    代码 = 代码 & "        .Left = 28: .Top = 172: .Width = 100: .Height = 30" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮4：反向横向
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton4"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""A1B1 A1B2 A2B1 A2B2""" & vbCrLf
    代码 = 代码 & "        .Left = 170: .Top = 172: .Width = 100: .Height = 30" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 框架2
    代码 = 代码 & "    With Me.Controls.Add(""Forms.Frame.1"", ""Frame2"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""双边循环（LCM独立循环）""" & vbCrLf
    代码 = 代码 & "        .Left = 15: .Top = 260: .Width = 290: .Height = 85" & vbCrLf
    代码 = 代码 & "        .Font.Size = 10: .Font.Bold = True" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮5：双边循环_竖
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton5"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""双边循环_合并_竖""" & vbCrLf
    代码 = 代码 & "        .Left = 28: .Top = 287: .Width = 120: .Height = 30" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 按钮6：双边循环_横
    代码 = 代码 & "    With Me.Controls.Add(""Forms.CommandButton.1"", ""CommandButton6"")" & vbCrLf
    代码 = 代码 & "        .Caption = ""双边循环_合并_横""" & vbCrLf
    代码 = 代码 & "        .Left = 170: .Top = 287: .Width = 120: .Height = 30" & vbCrLf
    代码 = 代码 & "        .Font.Size = 9" & vbCrLf
    代码 = 代码 & "    End With" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' 设置默认焦点（必须用 Controls 集合访问）
    代码 = 代码 & "    Me.Controls(""CommandButton1"").SetFocus" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' ===== 文本框变化 =====
    代码 = 代码 & "Private Sub TextBox1_Change()" & vbCrLf
    代码 = 代码 & "    当前连接符号 = Me.Controls(""TextBox1"").Text" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' ===== 复选框点击 =====
    代码 = 代码 & "Private Sub CheckBox1_Click()" & vbCrLf
    代码 = 代码 & "    是否合并模式 = Me.Controls(""CheckBox1"").Value" & vbCrLf
    代码 = 代码 & "    If 是否合并模式 Then" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton1"").Caption = ""A1B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B1"" & Chr(10) & ""A2B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton3"").Caption = ""A1B1"" & Chr(10) & ""A2B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton2"").Caption = ""A1B1 A2B1 A1B2 A2B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton4"").Caption = ""A1B1 A1B2 A2B1 A2B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton5"").Caption = ""双边循环_合并_竖""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton6"").Caption = ""双边循环_合并_横""" & vbCrLf
    代码 = 代码 & "    Else" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton1"").Caption = ""A1  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A2  B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton3"").Caption = ""A1  B1"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton2"").Caption = ""A1  B1  A2  B1  A1  B2  A2  B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton4"").Caption = ""A1  B1  A1  B2  A2  B1  A2  B2""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton5"").Caption = ""双边循环_分_竖""" & vbCrLf
    代码 = 代码 & "        Me.Controls(""CommandButton6"").Caption = ""双边循环_分_横""" & vbCrLf
    代码 = 代码 & "    End If" & vbCrLf
    代码 = 代码 & "    Me.Controls(""CommandButton1"").SetFocus" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf
    
    ' ===== 按钮点击事件 =====
    代码 = 代码 & "Private Sub CommandButton1_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 False, False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf & vbCrLf
    
    代码 = 代码 & "Private Sub CommandButton2_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 True, True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf & vbCrLf
    
    代码 = 代码 & "Private Sub CommandButton3_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 True, False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf & vbCrLf
    
    代码 = 代码 & "Private Sub CommandButton4_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 False, True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf & vbCrLf
    
    代码 = 代码 & "Private Sub CommandButton5_Click()" & vbCrLf
    代码 = 代码 & "    执行双边循环 True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf & vbCrLf
    
    代码 = 代码 & "Private Sub CommandButton6_Click()" & vbCrLf
    代码 = 代码 & "    执行双边循环 False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    
    生成窗体代码 = 代码
End Function

' ============================================================
'  工具函数 - 循环数学
' ============================================================

Function 循环索引(序号 As Long, 周期长度 As Long) As Long
    循环索引 = ((序号 + 周期长度 - 1) Mod 周期长度) + 1
End Function

Function 向上取整除法(被除数 As Long, 除数 As Long) As Long
    向上取整除法 = WorksheetFunction.RoundUp(被除数 / 除数, 0)
End Function

Function 计算数组乘积(数组 As Variant) As Long
    Dim i As Long
    计算数组乘积 = 1
    For i = LBound(数组) To UBound(数组)
        计算数组乘积 = 计算数组乘积 * 数组(i)
    Next i
End Function

Function 计算最小公倍数(数组 As Variant) As Long
    计算最小公倍数 = WorksheetFunction.Lcm(数组)
End Function

' ============================================================
'  工具函数 - 工作表读取
' ============================================================

Function 获取最后一列(工作表 As Worksheet) As Long
    获取最后一列 = 工作表.Cells(1, 工作表.Columns.Count).End(xlToLeft).Column
End Function

Function 获取最后一行(工作表 As Worksheet, 列号 As Long) As Long
    获取最后一行 = 工作表.Cells(工作表.Rows.Count, 列号).End(xlUp).Row
End Function

Function 批量读取区域(工作表 As Worksheet, 起始行 As Long, 起始列 As Long, _
                       结束行 As Long, 结束列 As Long) As Variant
    批量读取区域 = 工作表.Range(工作表.Cells(起始行, 起始列), 工作表.Cells(结束行, 结束列)).Value2
End Function

' ============================================================
'  核心算法 - 四方循环
' ============================================================

Function 计算循环步长数组(每列元素个数 As Variant, 是否正向 As Boolean) As Variant
    Dim 列数 As Long, 列索引 As Long
    Dim 步长数组() As Long
    Dim 总行数 As Long, 累计乘积 As Long

    列数 = UBound(每列元素个数)
    ReDim 步长数组(1 To 列数)

    If 是否正向 Then
        步长数组(1) = 1
        For 列索引 = 2 To 列数
            步长数组(列索引) = 步长数组(列索引 - 1) * 每列元素个数(列索引 - 1)
        Next 列索引
    Else
        总行数 = 1
        For 列索引 = 1 To 列数
            总行数 = 总行数 * 每列元素个数(列索引)
        Next 列索引
        累计乘积 = 1
        For 列索引 = 1 To 列数
            累计乘积 = 累计乘积 * 每列元素个数(列索引)
            步长数组(列索引) = 总行数 / 累计乘积
        Next 列索引
    End If

    计算循环步长数组 = 步长数组
End Function

Function 构建笛卡尔积矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          步长数组 As Variant, 结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 该列元素数 As Long, 该列步长 As Long
    Dim 源行号 As Long

    列数 = UBound(每列元素个数)
    ReDim 结果(1 To 列数, 1 To 结果行数)

    For 列索引 = 1 To 列数
        该列元素数 = 每列元素个数(列索引)
        该列步长 = 步长数组(列索引)
        For 行索引 = 1 To 结果行数
            源行号 = 循环索引(向上取整除法(行索引, 该列步长), 该列元素数)
            结果(列索引, 行索引) = 源数据(源行号, 列索引)
        Next 行索引
    Next 列索引

    构建笛卡尔积矩阵 = 结果
End Function

Function 矩阵转置(矩阵 As Variant, 列数 As Long, 行数 As Long) As Variant
    Dim 结果 As Variant
    Dim 行 As Long, 列 As Long
    ReDim 结果(1 To 行数, 1 To 列数)
    For 行 = 1 To 行数
        For 列 = 1 To 列数
            结果(行, 列) = 矩阵(列, 行)
        Next 列
    Next 行
    矩阵转置 = 结果
End Function

Function 按行合并字符串(矩阵 As Variant, 列数 As Long, 行数 As Long, _
                         是否列优先 As Boolean, 连接符 As String) As Variant
    Dim 结果() As String
    Dim 行 As Long, 列 As Long
    Dim 片段数组() As String
    ReDim 结果(1 To 行数)
    ReDim 片段数组(1 To 列数)

    For 行 = 1 To 行数
        For 列 = 1 To 列数
            If 是否列优先 Then
                片段数组(列) = 矩阵(列, 行)
            Else
                片段数组(列) = 矩阵(行, 列)
            End If
        Next 列
        结果(行) = Join(片段数组, 连接符)
    Next 行

    按行合并字符串 = 结果
End Function

' ============================================================
'  核心算法 - 双边循环
' ============================================================

Function 构建LCM循环矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 周期长度 As Long, 源行号 As Long

    列数 = UBound(每列元素个数)
    ReDim 结果(1 To 列数, 1 To 结果行数)

    For 列索引 = 1 To 列数
        周期长度 = 每列元素个数(列索引)
        For 行索引 = 1 To 结果行数
            源行号 = 循环索引(行索引, 周期长度)
            结果(列索引, 行索引) = 源数据(源行号, 列索引)
        Next 行索引
    Next 列索引

    构建LCM循环矩阵 = 结果
End Function

' ============================================================
'  输出
' ============================================================

Sub 写入结果(目标工作表 As Worksheet, 起始单元格 As String, _
              数据数组 As Variant, 输出行数 As Long, 输出列数 As Long, _
              是否合并模式 As Boolean)
    Dim 列格式数据 As Variant
    Dim i As Long

    If 是否合并模式 Then
        If 输出列数 = 1 Then
            ReDim 列格式数据(1 To UBound(数据数组), 1 To 1)
            For i = 1 To UBound(数据数组)
                列格式数据(i, 1) = 数据数组(i)
            Next i
            目标工作表.Range(起始单元格).Resize(输出行数, 1).Value2 = 列格式数据
        Else
            目标工作表.Range(起始单元格).Resize(1, 输出列数).Value2 = 数据数组
        End If
    Else
        目标工作表.Range(起始单元格).Resize(输出行数, 输出列数).Value2 = 数据数组
    End If
End Sub

' ============================================================
'  业务主函数：四方循环
' ============================================================

Sub 执行四方循环(是否正向 As Boolean, 是否横向输出 As Boolean)
    Dim 原屏幕刷新 As Boolean
    Dim 原计算模式 As XlCalculation

    原屏幕刷新 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    On Error GoTo 错误处理

    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet

    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        MsgBox "无有效数据列", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If

    Dim 每列元素个数() As Long
    Dim 列 As Long, 行数 As Long
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列

    Dim 结果总行数 As Long
    结果总行数 = 计算数组乘积(每列元素个数)
    If 结果总行数 > 1048576 Then
        MsgBox "已超出表格限制", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If

    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 结果总行数, 总列数)

    Dim 步长数组 As Variant
    步长数组 = 计算循环步长数组(每列元素个数, 是否正向)

    Dim 结果矩阵 As Variant
    结果矩阵 = 构建笛卡尔积矩阵(原始数据, 每列元素个数, 步长数组, 结果总行数)

    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")

    If 是否横向输出 Then
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 1: 输出列数 = 结果总行数
        Else
            输出数据 = 结果矩阵
            输出行数 = 总列数: 输出列数 = 结果总行数
        End If
    Else
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 结果总行数: 输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 结果总行数)
            输出行数 = 结果总行数: 输出列数 = 总列数
        End If
    End If

    写入结果 当前工作表, "F2", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    MsgBox "执行错误: " & Err.Description, vbCritical, "四方镜子"
    Resume 清理退出
End Sub

' ============================================================
'  业务主函数：双边循环
' ============================================================

Sub 执行双边循环(是否竖向输出 As Boolean)
    Dim 原屏幕刷新 As Boolean
    Dim 原计算模式 As XlCalculation

    原屏幕刷新 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    On Error GoTo 错误处理

    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet

    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        MsgBox "无有效数据列", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If

    Dim 每列元素个数() As Long
    Dim 列 As Long, 行数 As Long
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列

    Dim 列数乘积 As Long, 最小公倍数 As Long
    列数乘积 = 计算数组乘积(每列元素个数)
    最小公倍数 = 计算最小公倍数(每列元素个数)
    If 最小公倍数 > 1048576 Then
        MsgBox "已超出表格限制", vbExclamation, "四方镜子"
        GoTo 清理退出
    End If

    Dim 是否完整循环 As Boolean
    是否完整循环 = (列数乘积 = 最小公倍数)

    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 最小公倍数, 总列数)

    Dim 结果矩阵 As Variant
    结果矩阵 = 构建LCM循环矩阵(原始数据, 每列元素个数, 最小公倍数)

    Dim 新工作表 As Worksheet
    On Error Resume Next
    Set 新工作表 = Worksheets.Add(After:=Worksheets("重复字"))
    If Err.Number <> 0 Then
        Set 新工作表 = Worksheets.Add
    End If
    On Error GoTo 错误处理

    If 是否完整循环 Then
        新工作表.Name = "完整_" & 最小公倍数 & "sheet" & Sheets.Count
    Else
        新工作表.Name = "残缺_" & 列数乘积 & "|" & 最小公倍数 & "sheet" & Sheets.Count
    End If

    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")

    If 是否竖向输出 Then
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 最小公倍数: 输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 最小公倍数)
            输出行数 = 最小公倍数: 输出列数 = 总列数
        End If
    Else
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 1: 输出列数 = 最小公倍数
        Else
            输出数据 = 结果矩阵
            输出行数 = 总列数: 输出列数 = 最小公倍数
        End If
    End If

    写入结果 新工作表, "A1", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    MsgBox "执行错误: " & Err.Description, vbCritical, "四方镜子"
    Resume 清理退出
End Sub
