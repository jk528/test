'============================================================
' 四方镜子 - VBA 代码范例（重构清晰版）
' 功能：多列数据循环组合生成器
' 包含：四方循环（笛卡尔积）+ 双边循环（LCM独立循环）
'============================================================

Option Explicit

' 全局变量：连接符号（空字符串表示不合并）
Public gConnector As String

'============================================================
'  窗体事件过程
'============================================================

Private Sub CheckBox1_Click()
    ' 切换"合并/分开"显示模式
    If Me.CheckBox1 = True Then
        Me.CommandButton1.Caption = "11" & Chr(10) & "12" & Chr(10) & "21" & Chr(10) & "22"
        Me.CommandButton3.Caption = "11" & Chr(10) & "21" & Chr(10) & "12" & Chr(10) & "22"
        Me.CommandButton2.Caption = "11  21  12  22"
        Me.CommandButton4.Caption = "11  12  21  22"
        Me.CommandButton5.Caption = "双边循环_合并_竖"
        Me.CommandButton6.Caption = "双边循环_合并_横"
    Else
        Me.CommandButton1.Caption = "1  1" & Chr(10) & "1  2" & Chr(10) & "2  1" & Chr(10) & "2  2"
        Me.CommandButton3.Caption = "1  1" & Chr(10) & "2  1" & Chr(10) & "1  2" & Chr(10) & "2  2"
        Me.CommandButton2.Caption = "1  2  1  2" & Chr(10) & "1  1  2  2"
        Me.CommandButton4.Caption = "1  1  2  2" & Chr(10) & "1  2  1  2"
        Me.CommandButton5.Caption = "双边循环_分_竖"
        Me.CommandButton6.Caption = "双边循环_分_横"
    End If
    Me.CommandButton1.SetFocus
End Sub

' 按钮1：四方循环 - 正向竖向
Private Sub CommandButton1_Click()
    scct False, False
    Unload Me
End Sub

' 按钮2：四方循环 - 正向横向
Private Sub CommandButton2_Click()
    scct True, True
    Unload Me
End Sub

' 按钮3：四方循环 - 反向竖向
Private Sub CommandButton3_Click()
    scct True, False
    Unload Me
End Sub

' 按钮4：四方循环 - 反向横向
Private Sub CommandButton4_Click()
    scct False, True
    Unload Me
End Sub

' 按钮5：双边循环 - 竖向输出
Private Sub CommandButton5_Click()
    zxgbs True
    Unload Me
End Sub

' 按钮6：双边循环 - 横向输出
Private Sub CommandButton6_Click()
    zxgbs False
    Unload Me
End Sub

Private Sub TextBox1_Change()
    gConnector = TextBox1.Value
End Sub

Private Sub UserForm_Initialize()
    PC_003_组合.Caption = "四方镜"
    Label1.Caption = "连接符号:"
    CheckBox1.Caption = "合并"
    Me.CheckBox1.Value = True
    gConnector = "-"
End Sub

'============================================================
'  核心算法一：四方循环组合（笛卡尔积）
'  参数：
'    js  - True=正向循环(左慢右快), False=反向循环(左快右慢)
'    hs  - True=横向输出(列×行), False=竖向输出(行×列)
'============================================================

Function scct(js As Boolean, hs As Boolean)
    On Error Resume Next
    
    Dim m As Long          ' 总列数
    Dim n As Long, nn As Long
    Dim totalRows As Long  ' 总行数 = 笛卡尔积
    Dim srcData As Variant ' 源数据
    Dim result As Variant  ' 结果数组
    Dim merged As Variant  ' 合并后的字符串数组
    Dim colCounts() As Long ' 每列行数
    Dim fwdSteps() As Long  ' 正向循环步长
    Dim revSteps() As Long  ' 反向循环步长
    Dim useSteps() As Long  ' 当前使用的步长
    Dim mm As String
    
    ' 1. 获取列数
    m = Range("xfd1").End(xlToLeft).Column
    
    ' 2. 计算每列行数及循环步长
    ReDim colCounts(1 To m)
    ReDim fwdSteps(1 To m)
    ReDim revSteps(1 To m)
    
    fwdSteps(1) = 1  ' 第1列正向步长 = 1（每行都变）
    
    For n = 1 To m
        colCounts(n) = Cells(1048576, n).End(xlUp).Row
        If n > 1 Then
            ' 正向步长：第n列每 fwdSteps(n) 行才变化一次
            fwdSteps(n) = fwdSteps(n - 1) * colCounts(n - 1)
        End If
    Next n
    
    ' 计算总行数（笛卡尔积 = 最后一列的累计乘积）
    totalRows = colCounts(m) * fwdSteps(m)
    
    ' 计算反向步长：totalRows / 累计到第n列的乘积
    Dim cumProd As Long
    cumProd = 1
    For n = 1 To m
        cumProd = cumProd * colCounts(n)
        revSteps(n) = totalRows / cumProd
    Next n
    
    ' 3. 超限检查
    If totalRows > 1048576 Then
        MsgBox "已超出表格限制"
        Exit Function
    End If
    
    ' 4. 读取源数据
    srcData = Range(Cells(1, 1), Cells(totalRows, m))
    
    ' 5. 选择使用正向还是反向步长
    If js Then
        useSteps = fwdSteps
    Else
        useSteps = revSteps
    End If
    
    ' 6. 构建结果矩阵 + 可选合并
    If hs Then
        ' ===== 横向输出：result(列, 行) =====
        ReDim result(1 To m, 1 To totalRows)
        
        For nn = 1 To m
            For n = 1 To totalRows
                result(nn, n) = srcData(ys(cd(n, useSteps(nn)), colCounts(nn)), nn)
            Next n
        Next nn
        
        If CheckBox1.Value Then
            ' 合并模式：每行拼成一个字符串
            ReDim merged(1 To totalRows)
            For n = 1 To totalRows
                mm = ""
                For nn = 1 To m
                    mm = mm & result(nn, n) & gConnector
                Next nn
                merged(n) = Left(mm, Len(mm) - Len(gConnector))
            Next n
            [F2].Resize(1, totalRows) = merged
        Else
            ' 分开模式：直接输出矩阵
            [F2].Resize(m, totalRows) = result
        End If
        
    Else
        ' ===== 竖向输出：result(行, 列) =====
        ReDim result(1 To totalRows, 1 To m)
        
        For nn = 1 To m
            For n = 1 To totalRows
                result(n, nn) = srcData(ys(cd(n, useSteps(nn)), colCounts(nn)), nn)
            Next n
        Next nn
        
        If CheckBox1.Value Then
            ' 合并模式：每行拼成一个字符串
            ReDim merged(1 To totalRows, 1 To 1)
            For n = 1 To totalRows
                mm = ""
                For nn = 1 To m
                    mm = mm & result(n, nn) & gConnector
                Next nn
                merged(n, 1) = Left(mm, Len(mm) - Len(gConnector))
            Next n
            [F2].Resize(totalRows, 1) = merged
        Else
            ' 分开模式：直接输出矩阵
            [F2].Resize(totalRows, m) = result
        End If
    End If
End Function

'============================================================
'  核心算法二：双边循环组合（LCM独立循环）
'  参数：
'    hs  - True=竖向输出(行×列), False=横向输出(列×行)
'  说明：每列独立循环，总行数 = 各列行数的最小公倍数(LCM)
'============================================================

Function zxgbs(hs As Boolean)
    Dim 最右列 As Long
    Dim i As Long, ii As Long, iii As Long
    Dim Arr() As Long     ' 每列行数
    Dim brr As Variant    ' 结果矩阵
    Dim crr As Variant    ' 合并字符串（横排用）
    Dim drr As Variant    ' 合并字符串（竖排用）
    Dim 最小公倍数 As Long
    Dim mm As String
    Dim 源 As Variant
    Dim 积 As Long
    Dim 相等 As Boolean
    
    ' 1. 获取列数和每列行数
    最右列 = Cells(1, Columns.Count).End(xlToLeft).Column
    ReDim Arr(1 To 最右列)
    积 = 1
    相等 = False
    
    For i = 1 To UBound(Arr)
        Arr(i) = Cells(Rows.Count, i).End(xlUp).Row
        积 = 积 * Arr(i)
    Next i
    
    ' 2. 计算最小公倍数
    最小公倍数 = Application.WorksheetFunction.Lcm(Arr)
    
    If 最小公倍数 > 1048576 Then
        MsgBox "已超出表格限制"
        Exit Function
    End If
    
    ' 3. 判断是否完整循环（乘积=LCM说明各列互质或等长）
    If 积 - 最小公倍数 = 0 Then
        相等 = True
    End If
    
    ' 4. 读取源数据
    源 = Range(Cells(1, 1), Cells(最小公倍数, 最右列))
    
    ' 5. 新建工作表
    Sheets.Add After:=Sheets("重复字")
    If 相等 Then
        ActiveSheet.Name = "完整_" & 最小公倍数 & "sheet" & Sheets.Count
    Else
        ActiveSheet.Name = "残缺_" & 积 & "|" & 最小公倍数 & "sheet" & Sheets.Count
    End If
    
    ' 6. 构建循环结果
    If hs Then
        ' ===== 竖向输出 =====
        ReDim brr(1 To 最小公倍数, 1 To 最右列)
        ReDim drr(1 To 最小公倍数, 1 To 1)
        
        For ii = 1 To 最小公倍数
            mm = ""
            For iii = 1 To 最右列
                brr(ii, iii) = 源(ys(ii, Arr(iii)), iii)
                mm = mm & brr(ii, iii) & gConnector
            Next iii
            drr(ii, 1) = Left(mm, Len(mm) - Len(gConnector))
        Next ii
        
        If CheckBox1.Value Then
            [a1].Resize(UBound(brr), 1) = drr
        Else
            [a1].Resize(UBound(brr), UBound(brr, 2)) = brr
        End If
        
    Else
        ' ===== 横向输出 =====
        ReDim brr(1 To 最右列, 1 To 最小公倍数)
        ReDim crr(1 To 最小公倍数)
        
        For ii = 1 To 最小公倍数
            mm = ""
            For iii = 1 To 最右列
                brr(iii, ii) = 源(ys(ii, Arr(iii)), iii)
                mm = mm & brr(iii, ii) & gConnector
            Next iii
            crr(ii) = Left(mm, Len(mm) - Len(gConnector))
        Next ii
        
        If CheckBox1.Value Then
            [a1].Resize(1, UBound(brr, 2)) = crr
        Else
            [a1].Resize(UBound(brr), UBound(brr, 2)) = brr
        End If
    End If
End Function

'============================================================
'  工具函数
'============================================================

' 循环索引：将任意正整数 n 映射到 1~Y 的循环范围内
' 例如：ys(1,3)=1, ys(3,3)=3, ys(4,3)=1
Function ys(n, Y)
    ys = ((n + Y - 1) Mod Y) + 1
End Function

' 向上取整除法
Function cd(c, d)
    cd = Application.WorksheetFunction.RoundUp(c / d, 0)
End Function
