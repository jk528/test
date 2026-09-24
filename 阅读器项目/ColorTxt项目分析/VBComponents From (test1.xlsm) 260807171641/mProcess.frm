VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} mProcess 
   Caption         =   "mProcess"
   ClientHeight    =   2085
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   8990.001
   OleObjectBlob   =   "mProcess.frx":0000
   ShowModal       =   0   'False
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "mProcess"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False


Option Explicit


'-------------------------------------------------------------------------------------------------------------------------------
' 窗体 mProcess 用于显示进度条。
' 版本号 Version：0.2
' 最终更新日期 Last Update Date：2022-04-05
' 作者 Author：JunYi
' 网址 Link：https://gitee.com/junyii/vba-code-base

' 更新内容 0.2 Updates 2022-04-05：
'       1. Process方法：将参数 CurrentTask 和 TotalTask 数据类型从 Integer 改为 Variant（为了适应赋值变量类型是 Long 的情况）

' 更新内容 0.1 Updates 2020-12-28：
'       1. Init方法：初始化进度条。
'       2. Process方法：显示进度条。
'-------------------------------------------------------------------------------------------------------------------------------

' 注意：调用窗体里的全局函数必须加前缀：mProcess.Init



Const ProcessBarMaxWidth As Integer = 410  ' 前景进度条的最大宽度


'--------------------------------
' 1. 初始化
'--------------------------------
Public Function Init()
        Me.Caption = "进度条"
        Me.ProcessBarFrame.BorderStyle = fmBorderStyleNone  ' 隐藏边框
        Me.ProcessBarFrame.Caption = ""
        Me.ProcessBarBack.Caption = ""
        Me.ProcessBarBack.BackColor = &HC0C0C0   ' 灰色
        Me.ProcessBarFront.Caption = ""
        Me.ProcessBarFront.BackColor = &HECF57F  ' 亮青色
        Me.ProcessBarFront.BackColor = &HF6DC44   ' 亮蓝色
        Me.Show
End Function



'--------------------------------
' 2. 显示进度
'--------------------------------
Public Function Process(mProcessString As String, CurrentTask As Variant, TotalTask As Variant)
        Me.ProcessString = mProcessString
        Me.ProcessPercentage = CurrentTask & "/" & TotalTask & " (" & Format(CurrentTask / TotalTask * 100, "0.00") & "%)"
        Me.ProcessBarFront.Width = CurrentTask / TotalTask * ProcessBarMaxWidth
        DoEvents
       
End Function


Private Sub ProcessString_Click()

End Sub
