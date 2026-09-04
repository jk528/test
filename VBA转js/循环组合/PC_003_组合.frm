VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} PC_003_组合 
   Caption         =   "四方镜"
   ClientHeight    =   5880
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   6000
   OleObjectBlob   =   "PC_003_组合.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "PC_003_组合"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
'============================================================
' 四方镜子 - 窗体模块（语义化命名版）
' 窗体控件布局：
'   Label1        - "连接符号:"
'   TextBox1      - 输入连接符号
'   CheckBox1     - "合并" 复选框（切换合并/分开模式）
'   CommandButton1 - 四方循环：反向竖向（按钮图示 11/12/21/22）
'   CommandButton2 - 四方循环：正向横向
'   CommandButton3 - 四方循环：正向竖向
'   CommandButton4 - 四方循环：反向横向
'   CommandButton5 - 双边循环：竖向输出
'   CommandButton6 - 双边循环：横向输出
'============================================================

Option Explicit

' ------------------------------------------------------------
'  窗体事件
' ------------------------------------------------------------

' 窗体初始化
Private Sub UserForm_Initialize()
    Me.Caption = "四方镜"
    Label1.Caption = "连接符号:"
    CheckBox1.Caption = "合并"
    CheckBox1.Value = True          ' 默认合并模式
    TextBox1.Text = "-"             ' 默认连接符
    当前连接符号 = "-"
End Sub

' 连接符号文本框变化时更新全局变量
Private Sub TextBox1_Change()
    当前连接符号 = TextBox1.Text
End Sub

' 合并复选框切换时，更新各按钮的显示文字
' 合并模式下按钮文字是"A1B1"等紧凑图示（A列+B列拼在一起）
' 分开模式下按钮文字是"A1  B1"等带空格图示（A列 B列 分明）
Private Sub CheckBox1_Click()
    If Me.CheckBox1.Value = True Then
        ' ===== 合并模式按钮标题（A列+B列紧凑拼接） =====
        ' 按钮1：反向竖向 - A列慢，B列快
        CommandButton1.Caption = "A1B1" & Chr(10) & "A1B2" & Chr(10) & "A2B1" & Chr(10) & "A2B2"
        ' 按钮3：正向竖向 - A列快，B列慢
        CommandButton3.Caption = "A1B1" & Chr(10) & "A2B1" & Chr(10) & "A1B2" & Chr(10) & "A2B2"
        ' 按钮2：正向横向
        CommandButton2.Caption = "A1B1 A2B1 A1B2 A2B2"
        ' 按钮4：反向横向
        CommandButton4.Caption = "A1B1 A1B2 A2B1 A2B2"
        ' 按钮5-6：双边循环
        CommandButton5.Caption = "双边循环_合并_竖"
        CommandButton6.Caption = "双边循环_合并_横"
    Else
        ' ===== 分开模式按钮标题（A列  B列 分明） =====
        CommandButton1.Caption = "A1  B1" & Chr(10) & "A1  B2" & Chr(10) & "A2  B1" & Chr(10) & "A2  B2"
        CommandButton3.Caption = "A1  B1" & Chr(10) & "A2  B1" & Chr(10) & "A1  B2" & Chr(10) & "A2  B2"
        CommandButton2.Caption = "A1  B1  A2  B1  A1  B2  A2  B2"
        CommandButton4.Caption = "A1  B1  A1  B2  A2  B1  A2  B2"
        CommandButton5.Caption = "双边循环_分_竖"
        CommandButton6.Caption = "双边循环_分_横"
    End If
    CommandButton1.SetFocus
End Sub

' ------------------------------------------------------------
'  四方循环 - 四个按钮
'  参数映射：
'    scct(js, hs)
'      js = True  → 正向循环(左慢右快)
'      js = False → 反向循环(左快右慢)
'      hs = True  → 横向输出(列×行)
'      hs = False → 竖向输出(行×列)
' ------------------------------------------------------------

' 按钮1：反向 + 竖向（左列变化最快，结果竖向排列）
Private Sub CommandButton1_Click()
    执行四方循环 False, False
    Unload Me
End Sub

' 按钮2：正向 + 横向（左列变化最慢，结果横向排列）
Private Sub CommandButton2_Click()
    执行四方循环 True, True
    Unload Me
End Sub

' 按钮3：正向 + 竖向
Private Sub CommandButton3_Click()
    执行四方循环 True, False
    Unload Me
End Sub

' 按钮4：反向 + 横向
Private Sub CommandButton4_Click()
    执行四方循环 False, True
    Unload Me
End Sub

' ------------------------------------------------------------
'  双边循环 - 两个按钮
'  参数映射：
'    zxgbs(hs)
'      hs = True  → 竖向输出(行×列)
'      hs = False → 横向输出(列×行)
' ------------------------------------------------------------

' 按钮5：双边循环 - 竖向输出
Private Sub CommandButton5_Click()
    执行双边循环 True
    Unload Me
End Sub

' 按钮6：双边循环 - 横向输出
Private Sub CommandButton6_Click()
    执行双边循环 False
    Unload Me
End Sub
