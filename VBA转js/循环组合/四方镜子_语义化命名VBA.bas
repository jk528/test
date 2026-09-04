'============================================================
' 四方镜子 - VBA 语义化命名版
' 设计原则：变量名即注释，函数名即文档，读代码像读文章
'============================================================

Option Explicit

' ------------------------------------------------------------
'  全局变量
' ------------------------------------------------------------

Public 当前连接符号 As String   ' 空字符串 = 不合并，有值 = 用该符号连接各列

' ============================================================
'  第一部分：工具函数 - 消息与输入
' ============================================================

Function 弹窗提示(消息内容 As String, Optional 图标类型 As VbMsgBoxStyle = vbInformation)
    MsgBox 消息内容, 图标类型, "四方镜子"
End Function

Function 弹出输入框(提示文字 As String, Optional 标题 As String = "", _
                    Optional 默认值 As String = "", Optional 输入类型 As Long = 2) As Variant
    弹出输入框 = Application.InputBox(提示文字, 标题, 默认值, , , , , 输入类型)
End Function

' ============================================================
'  第二部分：工具函数 - 循环数学
' ============================================================

' 循环索引：把任意正整数映射到 [1, 周期长度] 的循环范围内
' 就像钟表：第1格=1，第12格=12，第13格=1
Function 循环索引(序号 As Long, 周期长度 As Long) As Long
    循环索引 = ((序号 + 周期长度 - 1) Mod 周期长度) + 1
End Function

' 向上取整除法：ceil(被除数 / 除数)
' 用于计算"第几个周期"
Function 向上取整除法(被除数 As Long, 除数 As Long) As Long
    向上取整除法 = WorksheetFunction.RoundUp(被除数 / 除数, 0)
End Function

' ============================================================
'  第三部分：工具函数 - 工作表读取
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
'  第四部分：核心算法 - 四方循环（笛卡尔积）
' ============================================================

' 计算每列的循环步长
' 步长含义：该列经过多少行才变化一次
'
' 正向循环（左列慢，右列快）：
'   第1列步长 = 1（每行都变）
'   第n列步长 = 前一列步长 × 前一列元素个数
'
' 反向循环（左列快，右列慢）：
'   第n列步长 = 总行数 / 前n列元素个数的乘积
Function 计算循环步长数组(每列元素个数 As Variant, 是否正向 As Boolean) As Variant
    Dim 列数 As Long, 列索引 As Long
    Dim 步长数组() As Long
    Dim 总行数 As Long, 累计乘积 As Long
    
    列数 = UBound(每列元素个数) - LBound(每列元素个数) + 1
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

' 构建笛卡尔积矩阵（列优先存储：结果(列, 行)）
' 每一列按照自己的步长循环取源数据
Function 构建笛卡尔积矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          步长数组 As Variant, 结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 该列元素数 As Long, 该列步长 As Long
    Dim 源行号 As Long
    
    列数 = UBound(每列元素个数) - LBound(每列元素个数) + 1
    ReDim 结果(1 To 列数, 1 To 结果行数)
    
    For 列索引 = 1 To 列数
        该列元素数 = 每列元素个数(列索引)
        该列步长 = 步长数组(列索引)
        
        For 行索引 = 1 To 结果行数
            ' 核心公式：源行号 = 循环索引( 向上取整(行号/步长), 元素数 )
            源行号 = 循环索引(向上取整除法(行索引, 该列步长), 该列元素数)
            结果(列索引, 行索引) = 源数据(源行号, 列索引)
        Next 行索引
    Next 列索引
    
    构建笛卡尔积矩阵 = 结果
End Function

' 矩阵转置：列优先 → 行优先
' 输入: 矩阵(列, 行)   (C列 × R行)
' 输出: 结果(行, 列)   (R行 × C列)
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

' 按行合并字符串：把每一行的多列值用连接符拼成一个字符串
Function 按行合并字符串(矩阵 As Variant, 列数 As Long, 行数 As Long, _
                         是否列优先 As Boolean, 连接符 As String) As Variant
    Dim 结果() As String
    Dim 行 As Long, 列 As Long
    Dim 片段数组() As String
    Dim 索引 As Long
    
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

' 计算数组元素的乘积
Function 计算数组乘积(数组 As Variant) As Long
    Dim i As Long
    计算数组乘积 = 1
    For i = LBound(数组) To UBound(数组)
        计算数组乘积 = 计算数组乘积 * 数组(i)
    Next i
End Function

' ============================================================
'  第五部分：核心算法 - 双边循环（LCM独立循环）
' ============================================================

' 计算数组的最小公倍数
Function 计算最小公倍数(数组 As Variant) As Long
    计算最小公倍数 = WorksheetFunction.Lcm(数组)
End Function

' 构建LCM循环矩阵（列优先存储：结果(列, 行)）
' 每列独立循环，总行数 = LCM(各列行数)
Function 构建LCM循环矩阵(源数据 As Variant, 每列元素个数 As Variant, _
                          结果行数 As Long) As Variant
    Dim 列数 As Long, 列索引 As Long, 行索引 As Long
    Dim 结果 As Variant
    Dim 周期长度 As Long, 源行号 As Long
    
    列数 = UBound(每列元素个数) - LBound(每列元素个数) + 1
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
'  第六部分：输出组 - 写入工作表
' ============================================================

' 将结果写入工作表指定位置
' 是否合并模式: True=一维字符串数组(单列或单行), False=二维矩阵
Sub 写入结果(目标工作表 As Worksheet, 起始单元格 As String, _
              数据数组 As Variant, 输出行数 As Long, 输出列数 As Long, _
              是否合并模式 As Boolean)
    Dim 列格式数据 As Variant
    Dim i As Long
    
    If 是否合并模式 Then
        If 输出列数 = 1 Then
            ' 竖排合并：一维数组 → 二维单列
            ReDim 列格式数据(1 To UBound(数据数组), 1 To 1)
            For i = 1 To UBound(数据数组)
                列格式数据(i, 1) = 数据数组(i)
            Next i
            目标工作表.Range(起始单元格).Resize(输出行数, 1).Value2 = 列格式数据
        Else
            ' 横排合并：一维数组直接写入一行
            目标工作表.Range(起始单元格).Resize(1, 输出列数).Value2 = 数据数组
        End If
    Else
        目标工作表.Range(起始单元格).Resize(输出行数, 输出列数).Value2 = 数据数组
    End If
End Sub

' ============================================================
'  第七部分：业务主函数
' ============================================================

' 执行四方循环组合（笛卡尔积）
' 参数:
'   是否正向      - True=左慢右快(正向), False=左快右慢(反向)
'   是否横向输出  - True=列×行横向输出, False=行×列竖向输出
Sub 执行四方循环(是否正向 As Boolean, 是否横向输出 As Boolean)
    Dim 原屏幕刷新状态 As Boolean
    Dim 原计算模式 As XlCalculation
    
    ' 关闭屏幕刷新和自动计算以提升性能
    原屏幕刷新状态 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    On Error GoTo 错误处理
    
    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet
    
    ' 1. 获取列数
    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        弹窗提示 "无有效数据列", vbExclamation
        GoTo 清理退出
    End If
    
    ' 2. 统计每列有多少个元素
    Dim 每列元素个数() As Long
    Dim 列 As Long
    Dim 行数 As Long
    
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列
    
    ' 3. 计算笛卡尔积总行数，检查是否超表格限制
    Dim 结果总行数 As Long
    结果总行数 = 计算数组乘积(每列元素个数)
    
    If 结果总行数 > 1048576 Then
        弹窗提示 "已超出表格限制", vbExclamation
        GoTo 清理退出
    End If
    
    ' 4. 批量读取源数据
    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 结果总行数, 总列数)
    
    ' 5. 计算每列的循环步长
    Dim 步长数组 As Variant
    步长数组 = 计算循环步长数组(每列元素个数, 是否正向)
    
    ' 6. 构建笛卡尔积矩阵（列优先存储）
    Dim 结果矩阵 As Variant
    结果矩阵 = 构建笛卡尔积矩阵(原始数据, 每列元素个数, 步长数组, 结果总行数)
    
    ' 7. 根据输出方向和合并模式准备最终输出
    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")
    
    If 是否横向输出 Then
        ' ---------- 横向输出：列 × 行 ----------
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 1
            输出列数 = 结果总行数
        Else
            输出数据 = 结果矩阵   ' 已经是 (列, 行)
            输出行数 = 总列数
            输出列数 = 结果总行数
        End If
    Else
        ' ---------- 竖向输出：行 × 列 ----------
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, True, 当前连接符号)
            输出行数 = 结果总行数
            输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 结果总行数)
            输出行数 = 结果总行数
            输出列数 = 总列数
        End If
    End If
    
    ' 8. 写入工作表
    写入结果 当前工作表, "F2", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新状态
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    弹窗提示 "执行错误: " & Err.Description, vbCritical
    Resume 清理退出
End Sub

' 执行双边循环组合（LCM独立循环）
' 参数:
'   是否竖向输出 - True=行×列竖向输出, False=列×行横向输出
Sub 执行双边循环(是否竖向输出 As Boolean)
    Dim 原屏幕刷新状态 As Boolean
    Dim 原计算模式 As XlCalculation
    
    原屏幕刷新状态 = Application.ScreenUpdating
    原计算模式 = Application.Calculation
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    On Error GoTo 错误处理
    
    Dim 当前工作表 As Worksheet
    Set 当前工作表 = ActiveSheet
    
    ' 1. 获取列数
    Dim 总列数 As Long
    总列数 = 获取最后一列(当前工作表)
    If 总列数 <= 0 Then
        弹窗提示 "无有效数据列", vbExclamation
        GoTo 清理退出
    End If
    
    ' 2. 统计每列元素个数
    Dim 每列元素个数() As Long
    Dim 列 As Long, 行数 As Long
    
    ReDim 每列元素个数(1 To 总列数)
    For 列 = 1 To 总列数
        行数 = 获取最后一行(当前工作表, 列)
        If 行数 < 1 Then 行数 = 1
        每列元素个数(列) = 行数
    Next 列
    
    ' 3. 计算乘积和最小公倍数
    Dim 列数乘积 As Long, 最小公倍数 As Long
    列数乘积 = 计算数组乘积(每列元素个数)
    最小公倍数 = 计算最小公倍数(每列元素个数)
    
    If 最小公倍数 > 1048576 Then
        弹窗提示 "已超出表格限制", vbExclamation
        GoTo 清理退出
    End If
    
    Dim 是否完整循环 As Boolean
    是否完整循环 = (列数乘积 = 最小公倍数)
    
    ' 4. 批量读取源数据
    Dim 原始数据 As Variant
    原始数据 = 批量读取区域(当前工作表, 1, 1, 最小公倍数, 总列数)
    
    ' 5. 构建LCM循环矩阵（列优先）
    Dim 结果矩阵 As Variant
    结果矩阵 = 构建LCM循环矩阵(原始数据, 每列元素个数, 最小公倍数)
    
    ' 6. 新建工作表并命名
    Dim 新工作表 As Worksheet
    Set 新工作表 = Worksheets.Add
    
    If 是否完整循环 Then
        新工作表.Name = "完整_" & 最小公倍数 & "sheet" & Sheets.Count
    Else
        新工作表.Name = "残缺_" & 列数乘积 & "|" & 最小公倍数 & "sheet" & Sheets.Count
    End If
    
    ' 7. 准备输出数据
    Dim 输出数据 As Variant
    Dim 输出行数 As Long, 输出列数 As Long
    Dim 是否合并 As Boolean
    是否合并 = (当前连接符号 <> "")
    
    If 是否竖向输出 Then
        ' ---------- 竖向输出：行 × 列 ----------
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 最小公倍数
            输出列数 = 1
        Else
            输出数据 = 矩阵转置(结果矩阵, 总列数, 最小公倍数)
            输出行数 = 最小公倍数
            输出列数 = 总列数
        End If
    Else
        ' ---------- 横向输出：列 × 行 ----------
        If 是否合并 Then
            输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, True, 当前连接符号)
            输出行数 = 1
            输出列数 = 最小公倍数
        Else
            输出数据 = 结果矩阵
            输出行数 = 总列数
            输出列数 = 最小公倍数
        End If
    End If
    
    ' 8. 写入结果
    写入结果 新工作表, "A1", 输出数据, 输出行数, 输出列数, 是否合并

清理退出:
    Application.ScreenUpdating = 原屏幕刷新状态
    Application.Calculation = 原计算模式
    Exit Sub

错误处理:
    弹窗提示 "执行错误: " & Err.Description, vbCritical
    Resume 清理退出
End Sub

' ============================================================
'  第八部分：窗体入口（与UserForm配合使用）
' ============================================================

' 按钮1：四方循环 - 反向竖向（对应原 CommandButton1）
Sub 四方镜子_合并_竖()
    Dim 连接符 As Variant
    连接符 = 弹出输入框("请输入连接符号:", "连接符号", "-", 2)
    If 连接符 = False Then Exit Sub
    当前连接符号 = CStr(连接符)
    执行四方循环 False, False   ' 反向 + 竖向
End Sub

' 按钮2：四方循环 - 正向横向（对应原 CommandButton2）
Sub 四方镜子_合并_横()
    Dim 连接符 As Variant
    连接符 = 弹出输入框("请输入连接符号:", "连接符号", "-", 2)
    If 连接符 = False Then Exit Sub
    当前连接符号 = CStr(连接符)
    执行四方循环 True, True     ' 正向 + 横向
End Sub

Sub 四方镜子_分开_竖()
    当前连接符号 = ""
    执行四方循环 False, False
End Sub

Sub 四方镜子_分开_横()
    当前连接符号 = ""
    执行四方循环 True, True
End Sub

Sub 四方镜子_双边循环_合并_竖()
    Dim 连接符 As Variant
    连接符 = 弹出输入框("请输入连接符号:", "连接符号", "-", 2)
    If 连接符 = False Then Exit Sub
    当前连接符号 = CStr(连接符)
    执行双边循环 True
End Sub

Sub 四方镜子_双边循环_合并_横()
    Dim 连接符 As Variant
    连接符 = 弹出输入框("请输入连接符号:", "连接符号", "-", 2)
    If 连接符 = False Then Exit Sub
    当前连接符号 = CStr(连接符)
    执行双边循环 False
End Sub

Sub 四方镜子_双边循环_分_竖()
    当前连接符号 = ""
    执行双边循环 True
End Sub

Sub 四方镜子_双边循环_分_横()
    当前连接符号 = ""
    执行双边循环 False
End Sub

' ============================================================
'  第九部分：主入口
' ============================================================

Sub 四方镜子_主入口()
    Dim 选择 As Variant
    选择 = 弹出输入框( _
        "请选择操作：" & vbCrLf & _
        "1: 四方循环_合并_竖" & vbCrLf & _
        "2: 四方循环_合并_横" & vbCrLf & _
        "3: 四方循环_分_竖" & vbCrLf & _
        "4: 四方循环_分_横" & vbCrLf & _
        "5: 双边循环_合并_竖" & vbCrLf & _
        "6: 双边循环_合并_横" & vbCrLf & _
        "7: 双边循环_分_竖" & vbCrLf & _
        "8: 双边循环_分_横", _
        "四方镜子", "1", 1)
    
    If 选择 = False Then Exit Sub
    选择 = CLng(选择)
    
    Select Case 选择
        Case 1: 四方镜子_合并_竖
        Case 2: 四方镜子_合并_横
        Case 3: 四方镜子_分开_竖
        Case 4: 四方镜子_分开_横
        Case 5: 四方镜子_双边循环_合并_竖
        Case 6: 四方镜子_双边循环_合并_横
        Case 7: 四方镜子_双边循环_分_竖
        Case 8: 四方镜子_双边循环_分_横
        Case Else: 弹窗提示 "无效选择", vbExclamation
    End Select
End Sub
