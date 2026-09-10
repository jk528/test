'============================================================
' 四方镜子 - 其他核心算法范例
'
' 现有两种算法回顾：
'   1. 四方循环 scct  = 笛卡尔积（全组合），行数 = 各列行数乘积
'   2. 双边循环 zxgbs = LCM独立循环，行数 = 各列行数最小公倍数
'
' 以下演示 4 种同样能实现"多列循环组合"功能的备选算法：
'   算法A 进位计数法（Odometer/混合进制）→ 与 scct 输出相同，实现不同
'   算法B 回溯法（DFS递归）            → 与 scct 输出相同，递归视角
'   算法C 自定义周期独立循环           → zxgbs 的推广（每列可指定任意周期）
'   算法D 随机抽样组合                 → 随机生成 N 行组合（可重复/不重复）
'
' 运行方法：在活动工作表放好数据（每列一列），运行 演示所有备选算法()
'============================================================

Option Explicit

' 演示主入口
Sub 演示所有备选算法()
    gConnector = "-"
    算法A_进位计数法
    算法B_回溯法
    算法C_自定义周期循环
    算法D_随机抽样 5
    MsgBox "4 种备选算法演示完成！结果见各自新建的工作表。", vbInformation, "四方镜子·备选算法"
End Sub

'============================================================
' 通用工具函数
'============================================================

Private Function ys(n As Long, Y As Long) As Long
    ys = ((n + Y - 1) Mod Y) + 1
End Function

Private Function cd(c As Long, d As Long) As Long
    cd = WorksheetFunction.RoundUp(c / d, 0)
End Function

Private Function 数组乘积(数组 As Variant) As Long
    Dim i As Long
    数组乘积 = 1
    For i = LBound(数组) To UBound(数组)
        数组乘积 = 数组乘积 * 数组(i)
    Next i
End Function

Private Function 最大公约数(a As Long, b As Long) As Long
    Dim t As Long
    Do While b <> 0
        t = b
        b = a Mod b
        a = t
    Loop
    最大公约数 = a
End Function

Private Function 最小公倍数(数组 As Variant) As Long
    Dim i As Long, lcm As Long
    lcm = 数组(LBound(数组))
    For i = LBound(数组) + 1 To UBound(数组)
        lcm = (lcm * 数组(i)) / 最大公约数(lcm, 数组(i))
    Next i
    最小公倍数 = lcm
End Function

Private Function 最后列(ws As Worksheet) As Long
    最后列 = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
End Function

Private Function 最后行(ws As Worksheet, 列 As Long) As Long
    最后行 = ws.Cells(ws.Rows.Count, 列).End(xlUp).Row
End Function

' 读取活动工作表前几列数据，返回(每列行数, 源数据)
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

' 新建结果表（命名 + 序号）
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

'============================================================
' 算法A：进位计数法（Odometer / 混合进制）
'
' 原理：把每一列看成一个"数字位"，
'       整个组合序列 = 一个混合进制计数器（像计程表）。
'       初始每位=1，每次"末位+1"，满则进位（重置为1，前一位+1）。
'       产生"最后一列变化最快"的顺序，与 scct 正向完全相同。
'
' 与 scct 的区别：scct 用"步长 × 循环索引"直接算出每行源行号；
'               进位计数法用"逐位递增+进位"逐行生成，无需预计算步长，
'               实现更直观，天然支持任意列数。
'============================================================
Sub 算法A_进位计数法()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    Dim 索引() As Long: ReDim 索引(1 To 总列数)
    Dim 列 As Long, 行 As Long
    For 列 = 1 To 总列数: 索引(列) = 1: Next

    Dim 结果() As Variant: ReDim 结果(1 To 总行数, 1 To 总列数)
    For 行 = 1 To 总行数
        ' 当前组合
        For 列 = 1 To 总列数
            结果(行, 列) = 源数据(索引(列), 列)
        Next 列
        ' 进位：从末位开始 +1，满则进位
        For 列 = 总列数 To 1 Step -1
            索引(列) = 索引(列) + 1
            If 索引(列) <= 每列行数(列) Then
                Exit For
            Else
                索引(列) = 1   ' 进位到前一位
            End If
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("算法A_进位计数")
    新表.Range("A1").Resize(总行数, 总列数) = 结果
    MsgBox "算法A 进位计数法 完成：" & 总行数 & " 行。", vbInformation, "备选算法A"
    Exit Sub
错误处理:
    MsgBox "算法A错误: " & Err.Description, vbCritical
End Sub

'============================================================
' 算法B：回溯法（DFS 递归生成）
'
' 原理：从第1列开始递归，逐列选择一个元素，
'       选满所有列（到达叶子）时输出一行，然后回溯换下一个。
'       输出顺序：第1列变化最慢、最后一列变化最快（与正向一致）。
'
' 与 scct 的区别：递归视角，逻辑最贴近"数学上的笛卡尔积定义"，
'               容易加约束（例如只输出满足某条件的组合）。
'============================================================
Private 结果行号 As Long
Private 结果矩阵() As Variant

Sub 算法B_回溯法()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 总行数 > 1048576 Then MsgBox "超出表格限制": Exit Sub

    ReDim 结果矩阵(1 To 总行数, 1 To 总列数)
    结果行号 = 0
    Dim 临时行() As Variant: ReDim 临时行(1 To 总列数)
    Call 递归生成(源数据, 每列行数, 总列数, 1, 临时行)

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("算法B_回溯法")
    新表.Range("A1").Resize(总行数, 总列数) = 结果矩阵
    MsgBox "算法B 回溯法 完成：" & 总行数 & " 行。", vbInformation, "备选算法B"
    Exit Sub
错误处理:
    MsgBox "算法B错误: " & Err.Description, vbCritical
End Sub

Private Sub 递归生成(源数据 As Variant, 每列行数() As Long, 总列数 As Long, 当前列 As Long, 临时行() As Variant)
    If 当前列 > 总列数 Then
        结果行号 = 结果行号 + 1
        Dim 列 As Long
        For 列 = 1 To 总列数
            结果矩阵(结果行号, 列) = 临时行(列)
        Next 列
        Exit Sub
    End If
    Dim i As Long
    For i = 1 To 每列行数(当前列)
        临时行(当前列) = 源数据(i, 当前列)
        Call 递归生成(源数据, 每列行数, 总列数, 当前列 + 1, 临时行)
    Next i
End Sub

'============================================================
' 算法C：自定义周期独立循环（zxgbs 的推广）
'
' 原理：zxgbs 里每列周期 = 该列行数；这里允许用户给每列指定任意周期，
'       每列按各自周期独立循环，总行数 = LCM(所有周期)。
'
' 比 zxgbs 更通用：可以做到"A列每2行循环、B列每3行循环"
'       （此时并不要求 B 列真的只有 3 个元素，可循环使用数据）。
' 演示：使用前两列数据，周期分别取 2 和 3。
'============================================================
Sub 算法C_自定义周期循环()
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    If 总列数 < 2 Then MsgBox "至少需要2列": Exit Sub

    ' 自定义周期：第1列周期=2，第2列周期=3（可自行修改）
    Dim 周期() As Long: ReDim 周期(1 To 总列数)
    Dim 列 As Long
    周期(1) = 2: 周期(2) = 3
    For 列 = 3 To 总列数: 周期(列) = 每列行数(列): Next

    Dim lcm As Long: lcm = 最小公倍数(周期)
    If lcm > 1048576 Then MsgBox "超出表格限制": Exit Sub

    Dim 行 As Long, 源行 As Long
    Dim 结果() As Variant: ReDim 结果(1 To lcm, 1 To 总列数)
    For 行 = 1 To lcm
        For 列 = 1 To 总列数
            源行 = ys(行, 周期(列))
            结果(行, 列) = 源数据(源行, 列)
        Next 列
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("算法C_周期循环")
    新表.Range("A1").Resize(lcm, 总列数) = 结果
    MsgBox "算法C 自定义周期循环 完成：周期(" & Join(周期, ",") & ") → " & lcm & " 行。", vbInformation, "备选算法C"
    Exit Sub
错误处理:
    MsgBox "算法C错误: " & Err.Description, vbCritical
End Sub

'============================================================
' 算法D：随机抽样组合
'
' 原理：不生成全组合，而是每次随机从每列各取一个元素组成一行。
'       支持 有放回（可能重复）和无放回（不重复）两种模式。
'       适合随机测试用例、抽样、彩票式组合等场景。
'
' 参数 抽样数：要生成的行数；去重：是否要求各行不重复。
'============================================================
Sub 算法D_随机抽样(抽样数 As Long, Optional 去重 As Boolean = False)
    On Error GoTo 错误处理
    Dim 每列行数() As Long, 源数据 As Variant
    读取源数据 每列行数, 源数据
    Dim 总列数 As Long: 总列数 = UBound(每列行数)
    Dim 总行数 As Long: 总行数 = 数组乘积(每列行数)
    If 去重 And 抽样数 > 总行数 Then MsgBox "去重模式下抽样数不能超过总组合数": Exit Sub

    Randomize
    Dim 行 As Long, 列 As Long, 源行 As Long
    Dim 结果() As Variant: ReDim 结果(1 To 抽样数, 1 To 总列数)
    Dim 已用 As Object
    Set 已用 = CreateObject("Scripting.Dictionary")

    Dim 尝试 As Long, 键 As String
    For 行 = 1 To 抽样数
        If 去重 Then
            ' 无放回：随机尝试直到生成不重复组合
            尝试 = 0
            Do
                For 列 = 1 To 总列数
                    源行 = Int(Rnd * 每列行数(列)) + 1
                    结果(行, 列) = 源数据(源行, 列)
                Next 列
                键 = ""
                For 列 = 1 To 总列数: 键 = 键 & "|" & CStr(结果(行, 列)): Next
                尝试 = 尝试 + 1
            Loop While 已用.Exists(键) And 尝试 < 10000
            已用(键) = True
        Else
            ' 有放回：直接随机
            For 列 = 1 To 总列数
                源行 = Int(Rnd * 每列行数(列)) + 1
                结果(行, 列) = 源数据(源行, 列)
            Next 列
        End If
    Next 行

    Dim 新表 As Worksheet
    Set 新表 = 新建结果表("算法D_随机抽样")
    新表.Range("A1").Resize(抽样数, 总列数) = 结果
    MsgBox "算法D 随机抽样 完成：" & 抽样数 & " 行" & IIf(去重, "（不重复）", "（可重复）") & "。", vbInformation, "备选算法D"
    Exit Sub
错误处理:
    MsgBox "算法D错误: " & Err.Description, vbCritical
End Sub

'============================================================
' 附：2×3 数据（A列A1,A2；B列B1,B2,B3）各算法输出对比
'============================================================
' 算法A/B（= scct 正向，6行）：
'   A1-B1
'   A2-B1
'   A1-B2
'   A2-B2
'   A1-B3
'   A2-B3
'
' 算法C（周期 2,3，LCM=6，6行）：
'   A1-B1
'   A2-B2
'   A1-B3
'   A2-B1
'   A1-B2
'   A2-B3
'
' 算法D（随机抽 3 行，示例）：
'   A1-B3
'   A2-B1
'   A1-B2
'============================================================
