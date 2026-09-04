'============================================================
' 四方镜子 - 单模块版（动态创建窗体）
' 功能：一个标准模块搞定所有事情，运行时自动创建窗体
' 使用方法：直接运行 四方镜子_主入口() 即可
'============================================================

Option Explicit

' 全局变量（在窗体回调中共享）
Private 当前连接符号 As String
Private 是否合并模式 As Boolean
Private 主窗体 As Object

' ============================================================
'  主入口：动态创建窗体并显示
' ============================================================

Sub 四方镜子_主入口()
    On Error GoTo 错误处理

    ' 初始化全局变量
    当前连接符号 = "-"
    是否合并模式 = True

    ' 1. 动态创建用户窗体
    Set 主窗体 = ThisWorkbook.VBProject.VBComponents.Add(3).Designer  ' 3 = vbext_ct_MSForm
    With 主窗体
        .Caption = "四方镜"
        .Width = 320
        .Height = 420
    End With

    ' 2. 添加控件
    添加标签 主窗体, "Label1", "连接符号:", 20, 18, 70, 20
    添加文本框 主窗体, "TextBox1", 95, 15, 80, 22, "-"
    添加复选框 主窗体, "CheckBox1", "合并", 20, 48, 100, 20, True

    ' 分组：四方循环
    添加框架 主窗体, "Frame1", "四方循环（笛卡尔积）", 15, 78, 285, 165

    ' 2×2 按钮布局
    ' 左上：反向竖向（按钮1）
    ' 右上：正向竖向（按钮3）
    ' 左下：正向横向（按钮2）
    ' 右下：反向横向（按钮4）
    Dim 按钮左1 As Long, 按钮左2 As Long, 按钮上1 As Long, 按钮上2 As Long
    按钮左1 = 28
    按钮左2 = 162
    按钮上1 = 105
    按钮上2 = 175

    添加按钮 主窗体, "CommandButton1", "A1B1" & vbCrLf & "A1B2" & vbCrLf & "A2B1" & vbCrLf & "A2B2", _
             按钮左1, 按钮上1, 100, 60
    添加按钮 主窗体, "CommandButton3", "A1B1" & vbCrLf & "A2B1" & vbCrLf & "A1B2" & vbCrLf & "A2B2", _
             按钮左2, 按钮上1, 100, 60
    添加按钮 主窗体, "CommandButton2", "A1B1 A2B1 A1B2 A2B2", _
             按钮左1, 按钮上2, 100, 30
    添加按钮 主窗体, "CommandButton4", "A1B1 A1B2 A2B1 A2B2", _
             按钮左2, 按钮上2, 100, 30

    ' 分组：双边循环
    添加框架 主窗体, "Frame2", "双边循环（LCM独立循环）", 15, 255, 285, 80
    添加按钮 主窗体, "CommandButton5", "双边循环_合并_竖", 28, 285, 120, 30
    添加按钮 主窗体, "CommandButton6", "双边循环_合并_横", 162, 285, 120, 30

    ' 3. 注入事件代码
    注入窗体事件代码

    ' 4. 显示窗体
    VBA.UserForms.Add(主窗体.Name).Show

    ' 5. 清理：移除临时窗体
    ThisWorkbook.VBProject.VBComponents.Remove ThisWorkbook.VBProject.VBComponents(主窗体.Name)

    Exit Sub

错误处理:
    MsgBox "创建窗体失败: " & Err.Description, vbCritical, "四方镜子"
    ' 清理残留
    On Error Resume Next
    If Not 主窗体 Is Nothing Then
        ThisWorkbook.VBProject.VBComponents.Remove ThisWorkbook.VBProject.VBComponents(主窗体.Name)
    End If
End Sub

' ============================================================
'  辅助：添加各种控件到窗体
' ============================================================

Private Sub 添加标签(窗体 As Object, 名称 As String, 标题 As String, _
                      左 As Long, 上 As Long, 宽 As Long, 高 As Long)
    With 窗体.Controls.Add("Forms.Label.1", 名称)
        .Caption = 标题
        .Left = 左
        .Top = 上
        .Width = 宽
        .Height = 高
        .Font.Size = 10
    End With
End Sub

Private Sub 添加文本框(窗体 As Object, 名称 As String, _
                        左 As Long, 上 As Long, 宽 As Long, 高 As Long, _
                        Optional 默认值 As String = "")
    With 窗体.Controls.Add("Forms.TextBox.1", 名称)
        .Text = 默认值
        .Left = 左
        .Top = 上
        .Width = 宽
        .Height = 高
        .Font.Size = 10
    End With
End Sub

Private Sub 添加复选框(窗体 As Object, 名称 As String, 标题 As String, _
                        左 As Long, 上 As Long, 宽 As Long, 高 As Long, _
                        Optional 选中 As Boolean = False)
    With 窗体.Controls.Add("Forms.CheckBox.1", 名称)
        .Caption = 标题
        .Left = 左
        .Top = 上
        .Width = 宽
        .Height = 高
        .Value = 选中
        .Font.Size = 10
    End With
End Sub

Private Sub 添加框架(窗体 As Object, 名称 As String, 标题 As String, _
                      左 As Long, 上 As Long, 宽 As Long, 高 As Long)
    With 窗体.Controls.Add("Forms.Frame.1", 名称)
        .Caption = 标题
        .Left = 左
        .Top = 上
        .Width = 宽
        .Height = 高
        .Font.Size = 10
        .Font.Bold = True
    End With
End Sub

Private Sub 添加按钮(窗体 As Object, 名称 As String, 标题 As String, _
                       左 As Long, 上 As Long, 宽 As Long, 高 As Long)
    With 窗体.Controls.Add("Forms.CommandButton.1", 名称)
        .Caption = 标题
        .Left = 左
        .Top = 上
        .Width = 宽
        .Height = 高
        .Font.Size = 9
    End With
End Sub

' ============================================================
'  辅助：向窗体模块注入事件代码
' ============================================================

Private Sub 注入窗体事件代码()
    Dim 代码模块 As Object
    Set 代码模块 = ThisWorkbook.VBProject.VBComponents(主窗体.Name).CodeModule

    Dim 代码 As String
    代码 = ""
    代码 = 代码 & "Option Explicit" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 文本框变化事件
    代码 = 代码 & "Private Sub TextBox1_Change()" & vbCrLf
    代码 = 代码 & "    当前连接符号 = TextBox1.Text" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 复选框点击事件 - 切换合并模式时更新按钮图示
    代码 = 代码 & "Private Sub CheckBox1_Click()" & vbCrLf
    代码 = 代码 & "    是否合并模式 = CheckBox1.Value" & vbCrLf
    代码 = 代码 & "    If 是否合并模式 Then" & vbCrLf
    代码 = 代码 & "        CommandButton1.Caption = ""A1B1"" & vbCrLf & ""A1B2"" & vbCrLf & ""A2B1"" & vbCrLf & ""A2B2""" & vbCrLf
    代码 = 代码 & "        CommandButton3.Caption = ""A1B1"" & vbCrLf & ""A2B1"" & vbCrLf & ""A1B2"" & vbCrLf & ""A2B2""" & vbCrLf
    代码 = 代码 & "        CommandButton2.Caption = ""A1B1 A2B1 A1B2 A2B2""" & vbCrLf
    代码 = 代码 & "        CommandButton4.Caption = ""A1B1 A1B2 A2B1 A2B2""" & vbCrLf
    代码 = 代码 & "        CommandButton5.Caption = ""双边循环_合并_竖""" & vbCrLf
    代码 = 代码 & "        CommandButton6.Caption = ""双边循环_合并_横""" & vbCrLf
    代码 = 代码 & "    Else" & vbCrLf
    代码 = 代码 & "        CommandButton1.Caption = ""A1  B1"" & vbCrLf & ""A1  B2"" & vbCrLf & ""A2  B1"" & vbCrLf & ""A2  B2""" & vbCrLf
    代码 = 代码 & "        CommandButton3.Caption = ""A1  B1"" & vbCrLf & ""A2  B1"" & vbCrLf & ""A1  B2"" & vbCrLf & ""A2  B2""" & vbCrLf
    代码 = 代码 & "        CommandButton2.Caption = ""A1  B1  A2  B1  A1  B2  A2  B2""" & vbCrLf
    代码 = 代码 & "        CommandButton4.Caption = ""A1  B1  A1  B2  A2  B1  A2  B2""" & vbCrLf
    代码 = 代码 & "        CommandButton5.Caption = ""双边循环_分_竖""" & vbCrLf
    代码 = 代码 & "        CommandButton6.Caption = ""双边循环_分_横""" & vbCrLf
    代码 = 代码 & "    End If" & vbCrLf
    代码 = 代码 & "    CommandButton1.SetFocus" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮1：反向竖向
    代码 = 代码 & "Private Sub CommandButton1_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 False, False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮2：正向横向
    代码 = 代码 & "Private Sub CommandButton2_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 True, True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮3：正向竖向
    代码 = 代码 & "Private Sub CommandButton3_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 True, False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮4：反向横向
    代码 = 代码 & "Private Sub CommandButton4_Click()" & vbCrLf
    代码 = 代码 & "    执行四方循环 False, True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮5：双边循环-竖向
    代码 = 代码 & "Private Sub CommandButton5_Click()" & vbCrLf
    代码 = 代码 & "    执行双边循环 True" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf
    代码 = 代码 & vbCrLf

    ' 按钮6：双边循环-横向
    代码 = 代码 & "Private Sub CommandButton6_Click()" & vbCrLf
    代码 = 代码 & "    执行双边循环 False" & vbCrLf
    代码 = 代码 & "    Unload Me" & vbCrLf
    代码 = 代码 & "End Sub" & vbCrLf

    代码模块.AddFromString 代码
End Sub

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
'  核心算法 - 四方循环（笛卡尔积）
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
'  核心算法 - 双边循环（LCM独立循环）
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
'  输出 - 写入工作表
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
