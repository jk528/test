'============================================================
' 四方镜子 - 单模块最终版（生成frm文件 + Import导入）
' 原理：运行时生成完整frm文件，Import导入为设计时窗体
'       所有控件和事件都是原生的，兼容性最好
' 使用方法：运行 四方镜子()
'============================================================

Option Explicit

' 全局变量（窗体回调时读取）
Public 连接符 As String
Public 是否合并 As Boolean

' ============================================================
'  主入口
' ============================================================

Sub 四方镜子()
    On Error GoTo 错误处理
    
    连接符 = "-"
    是否合并 = True
    
    Dim 窗体名 As String
    窗体名 = "SFJ" & Format(Now, "hhmmss")
    
    ' 1. 生成frm临时文件
    Dim 临时路径 As String
    临时路径 = Environ("TEMP") & "\" & 窗体名 & ".frm"
    
    Open 临时路径 For Output As #1
    Print #1, 生成窗体代码(窗体名)
    Close #1
    
    ' 2. 导入窗体
    Dim VBP As Object
    Set VBP = ThisWorkbook.VBProject
    VBP.VBComponents.Import 临时路径
    
    ' 3. 显示
    VBA.UserForms.Add(窗体名).Show
    
    ' 4. 清理
    VBP.VBComponents.Remove VBP.VBComponents(窗体名)
    Kill 临时路径
    
    Exit Sub

错误处理:
    MsgBox "错误 " & Err.Number & ": " & Err.Description, vbCritical, "四方镜子"
    ' 清理残留
    On Error Resume Next
    Dim VBP2 As Object
    Set VBP2 = ThisWorkbook.VBProject
    Dim comp As Object
    For Each comp In VBP2.VBComponents
        If comp.Name = 窗体名 Then VBP2.VBComponents.Remove comp
    Next
    If Dir(临时路径) <> "" Then Kill 临时路径
End Sub

' ============================================================
'  生成完整的 .frm 文件内容
' ============================================================

Private Function 生成窗体代码(窗体名 As String) As String
    Dim s As String
    
    ' ===== 窗体属性头 =====
    s = "VERSION 5.00" & vbCrLf
    s = s & "Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} " & 窗体名 & vbCrLf
    s = s & "   Caption         =   ""四方镜""" & vbCrLf
    s = s & "   ClientHeight    =   7200" & vbCrLf
    s = s & "   ClientLeft      =   120" & vbCrLf
    s = s & "   ClientTop       =   465" & vbCrLf
    s = s & "   ClientWidth     =   6000" & vbCrLf
    s = s & "   OleObjectBlob   =   """ & 窗体名 & ".frx"":0000" & vbCrLf
    s = s & "   StartUpPosition =   1" & vbCrLf
    
    ' ---- 控件：标签 ----
    s = s & "   Begin VB.Label Label1 " & vbCrLf
    s = s & "      Caption         =   ""连接符号:""" & vbCrLf
    s = s & "      Height          =   255" & vbCrLf
    s = s & "      Left            =   360" & vbCrLf
    s = s & "      TabIndex        =   0" & vbCrLf
    s = s & "      Top             =   300" & vbCrLf
    s = s & "      Width           =   975" & vbCrLf
    s = s & "   End" & vbCrLf
    
    ' ---- 控件：文本框 ----
    s = s & "   Begin VB.TextBox TextBox1 " & vbCrLf
    s = s & "      Height          =   375" & vbCrLf
    s = s & "      Left            =   1440" & vbCrLf
    s = s & "      TabIndex        =   1" & vbCrLf
    s = s & "      Text            =   ""-""" & vbCrLf
    s = s & "      Top             =   240" & vbCrLf
    s = s & "      Width           =   1215" & vbCrLf
    s = s & "   End" & vbCrLf
    
    ' ---- 控件：复选框 ----
    s = s & "   Begin VB.CheckBox CheckBox1 " & vbCrLf
    s = s & "      Caption         =   ""合并""" & vbCrLf
    s = s & "      Height          =   255" & vbCrLf
    s = s & "      Left            =   360" & vbCrLf
    s = s & "      TabIndex        =   2" & vbCrLf
    s = s & "      Top             =   720" & vbCrLf
    s = s & "      Value           =   1  'Checked" & vbCrLf
    s = s & "      Width           =   1215" & vbCrLf
    s = s & "   End" & vbCrLf
    
    ' ---- 控件：框架1（四方循环） ----
    s = s & "   Begin VB.Frame Frame1 " & vbCrLf
    s = s & "      Caption         =   ""四方循环（笛卡尔积）""" & vbCrLf
    s = s & "      Height          =   2775" & vbCrLf
    s = s & "      Left            =   240" & vbCrLf
    s = s & "      TabIndex        =   3" & vbCrLf
    s = s & "      Top             =   1200" & vbCrLf
    s = s & "      Width           =   5415" & vbCrLf
    
    ' 按钮1：反向竖向
    s = s & "      Begin VB.CommandButton CommandButton1 " & vbCrLf
    s = s & "         Caption         =   ""A1B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B1"" & Chr(10) & ""A2B2""" & vbCrLf
    s = s & "         Height          =   975" & vbCrLf
    s = s & "         Left            =   360" & vbCrLf
    s = s & "         TabIndex        =   4" & vbCrLf
    s = s & "         Top             =   360" & vbCrLf
    s = s & "         Width           =   1815" & vbCrLf
    s = s & "      End" & vbCrLf
    
    ' 按钮3：正向竖向
    s = s & "      Begin VB.CommandButton CommandButton3 " & vbCrLf
    s = s & "         Caption         =   ""A1B1"" & Chr(10) & ""A2B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B2""" & vbCrLf
    s = s & "         Height          =   975" & vbCrLf
    s = s & "         Left            =   2880" & vbCrLf
    s = s & "         TabIndex        =   5" & vbCrLf
    s = s & "         Top             =   360" & vbCrLf
    s = s & "         Width           =   1815" & vbCrLf
    s = s & "      End" & vbCrLf
    
    ' 按钮2：正向横向
    s = s & "      Begin VB.CommandButton CommandButton2 " & vbCrLf
    s = s & "         Caption         =   ""A1B1 A2B1 A1B2 A2B2""" & vbCrLf
    s = s & "         Height          =   495" & vbCrLf
    s = s & "         Left            =   360" & vbCrLf
    s = s & "         TabIndex        =   6" & vbCrLf
    s = s & "         Top             =   1560" & vbCrLf
    s = s & "         Width           =   1815" & vbCrLf
    s = s & "      End" & vbCrLf
    
    ' 按钮4：反向横向
    s = s & "      Begin VB.CommandButton CommandButton4 " & vbCrLf
    s = s & "         Caption         =   ""A1B1 A1B2 A2B1 A2B2""" & vbCrLf
    s = s & "         Height          =   495" & vbCrLf
    s = s & "         Left            =   2880" & vbCrLf
    s = s & "         TabIndex        =   7" & vbCrLf
    s = s & "         Top             =   1560" & vbCrLf
    s = s & "         Width           =   1815" & vbCrLf
    s = s & "      End" & vbCrLf
    
    s = s & "   End" & vbCrLf  ' Frame1 结束
    
    ' ---- 控件：框架2（双边循环） ----
    s = s & "   Begin VB.Frame Frame2 " & vbCrLf
    s = s & "      Caption         =   ""双边循环（LCM独立循环）""" & vbCrLf
    s = s & "      Height          =   1335" & vbCrLf
    s = s & "      Left            =   240" & vbCrLf
    s = s & "      TabIndex        =   8" & vbCrLf
    s = s & "      Top             =   4080" & vbCrLf
    s = s & "      Width           =   5415" & vbCrLf
    
    ' 按钮5：双边循环_竖
    s = s & "      Begin VB.CommandButton CommandButton5 " & vbCrLf
    s = s & "         Caption         =   ""双边循环_合并_竖""" & vbCrLf
    s = s & "         Height          =   495" & vbCrLf
    s = s & "         Left            =   360" & vbCrLf
    s = s & "         TabIndex        =   9" & vbCrLf
    s = s & "         Top             =   480" & vbCrLf
    s = s & "         Width           =   2175" & vbCrLf
    s = s & "      End" & vbCrLf
    
    ' 按钮6：双边循环_横
    s = s & "      Begin VB.CommandButton CommandButton6 " & vbCrLf
    s = s & "         Caption         =   ""双边循环_合并_横""" & vbCrLf
    s = s & "         Height          =   495" & vbCrLf
    s = s & "         Left            =   2880" & vbCrLf
    s = s & "         TabIndex        =   10" & vbCrLf
    s = s & "         Top             =   480" & vbCrLf
    s = s & "         Width           =   2175" & vbCrLf
    s = s & "      End" & vbCrLf
    
    s = s & "   End" & vbCrLf  ' Frame2 结束
    
    s = s & "End" & vbCrLf  ' 窗体定义结束
    
    ' ===== 窗体代码部分 =====
    s = s & "Attribute VB_Name = """ & 窗体名 & """" & vbCrLf
    s = s & "Attribute VB_GlobalNameSpace = False" & vbCrLf
    s = s & "Attribute VB_Creatable = False" & vbCrLf
    s = s & "Attribute VB_PredeclaredId = True" & vbCrLf
    s = s & "Attribute VB_Exposed = False" & vbCrLf
    s = s & "Option Explicit" & vbCrLf & vbCrLf
    
    ' Initialize
    s = s & "Private Sub UserForm_Initialize()" & vbCrLf
    s = s & "    CommandButton1.SetFocus" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    
    ' 文本框变化
    s = s & "Private Sub TextBox1_Change()" & vbCrLf
    s = s & "    连接符 = TextBox1.Text" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    
    ' 复选框点击
    s = s & "Private Sub CheckBox1_Click()" & vbCrLf
    s = s & "    是否合并 = CheckBox1.Value" & vbCrLf
    s = s & "    If 是否合并 Then" & vbCrLf
    s = s & "        CommandButton1.Caption = ""A1B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B1"" & Chr(10) & ""A2B2""" & vbCrLf
    s = s & "        CommandButton3.Caption = ""A1B1"" & Chr(10) & ""A2B1"" & Chr(10) & ""A1B2"" & Chr(10) & ""A2B2""" & vbCrLf
    s = s & "        CommandButton2.Caption = ""A1B1 A2B1 A1B2 A2B2""" & vbCrLf
    s = s & "        CommandButton4.Caption = ""A1B1 A1B2 A2B1 A2B2""" & vbCrLf
    s = s & "        CommandButton5.Caption = ""双边循环_合并_竖""" & vbCrLf
    s = s & "        CommandButton6.Caption = ""双边循环_合并_横""" & vbCrLf
    s = s & "    Else" & vbCrLf
    s = s & "        CommandButton1.Caption = ""A1  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A2  B2""" & vbCrLf
    s = s & "        CommandButton3.Caption = ""A1  B1"" & Chr(10) & ""A2  B1"" & Chr(10) & ""A1  B2"" & Chr(10) & ""A2  B2""" & vbCrLf
    s = s & "        CommandButton2.Caption = ""A1  B1  A2  B1  A1  B2  A2  B2""" & vbCrLf
    s = s & "        CommandButton4.Caption = ""A1  B1  A1  B2  A2  B1  A2  B2""" & vbCrLf
    s = s & "        CommandButton5.Caption = ""双边循环_分_竖""" & vbCrLf
    s = s & "        CommandButton6.Caption = ""双边循环_分_横""" & vbCrLf
    s = s & "    End If" & vbCrLf
    s = s & "    CommandButton1.SetFocus" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    
    ' 按钮点击事件
    s = s & "Private Sub CommandButton1_Click(): 四方循环_执行 False, False: Unload Me: End Sub" & vbCrLf
    s = s & "Private Sub CommandButton2_Click(): 四方循环_执行 True, True: Unload Me: End Sub" & vbCrLf
    s = s & "Private Sub CommandButton3_Click(): 四方循环_执行 True, False: Unload Me: End Sub" & vbCrLf
    s = s & "Private Sub CommandButton4_Click(): 四方循环_执行 False, True: Unload Me: End Sub" & vbCrLf
    s = s & "Private Sub CommandButton5_Click(): 双边循环_执行 True: Unload Me: End Sub" & vbCrLf
    s = s & "Private Sub CommandButton6_Click(): 双边循环_执行 False: Unload Me: End Sub" & vbCrLf
    
    生成窗体代码 = s
End Function

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

' ============================================================
'  核心算法一：四方循环（笛卡尔积）
'  参数：是否正向, 是否横向
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

    ' 1. 读取数据
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

    ' 2. 计算步长
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

    ' 3. 构建结果（列优先）
    Dim 结果() As Variant
    ReDim 结果(1 To 总列数, 1 To 总行数)
    Dim 行 As Long, 源行 As Long
    For 列 = 1 To 总列数
        For 行 = 1 To 总行数
            源行 = ys(cd(行, 步长(列)), 每列行数(列))
            结果(列, 行) = 源数据(源行, 列)
        Next 行
    Next 列

    ' 4. 输出
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
            ws.Range("F2").Resize(1, 总行数) = 横合并
        Else
            ws.Range("F2").Resize(总列数, 总行数) = 结果
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
            ws.Range("F2").Resize(总行数, 1) = 竖写入
        Else
            Dim 竖结果() As Variant
            ReDim 竖结果(1 To 总行数, 1 To 总列数)
            For 行 = 1 To 总行数
                For 列 = 1 To 总列数
                    竖结果(行, 列) = 结果(列, 行)
                Next 列
            Next 行
            ws.Range("F2").Resize(总行数, 总列数) = 竖结果
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
'  参数：是否竖向
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

    ' 1. 读取数据
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

    ' 2. 构建结果（列优先）
    Dim 结果() As Variant
    ReDim 结果(1 To 总列数, 1 To 最小公倍数)
    Dim 行 As Long, 源行 As Long
    For 列 = 1 To 总列数
        For 行 = 1 To 最小公倍数
            源行 = ys(行, 每列行数(列))
            结果(列, 行) = 源数据(源行, 列)
        Next 行
    Next 列

    ' 3. 新建工作表
    Dim 新表 As Worksheet
    On Error Resume Next
    Set 新表 = Worksheets.Add(After:=Worksheets("重复字"))
    If Err.Number <> 0 Then Set 新表 = Worksheets.Add
    On Error GoTo 错误处理

    If 是否完整 Then
        新表.Name = "完整_" & 最小公倍数 & "sheet" & Sheets.Count
    Else
        新表.Name = "残缺_" & 列乘积 & "|" & 最小公倍数 & "sheet" & Sheets.Count
    End If

    ' 4. 输出
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
