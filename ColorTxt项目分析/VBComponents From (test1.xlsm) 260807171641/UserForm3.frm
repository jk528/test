VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} UserForm3 
   Caption         =   "UserForm3"
   ClientHeight    =   6465
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   5280
   OleObjectBlob   =   "UserForm3.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "UserForm3"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False


' --------------------------------------------------
' 以下是匹配结果窗体（UserForm1）的代码
' 请手动创建一个名为UserForm1的用户窗体，并添加相应控件
' --------------------------------------------------
'
'手动创建UserForm1窗体的步骤:
' 1. 在VBE中，右键点击项目资源管理器，选择"插入" > "用户窗体"
' 2. 将窗体名称改为UserForm1
' 3. 添加以下控件：
'    - Label控件：名称lblTitle，标题"找到 X 个匹配结果，点击跳转："
'    - CommandButton控件：名称cmdClose，标题"关闭"
'    - ListBox控件：名称lstMatches，用于显示匹配结果
' 4. 将以下代码粘贴到UserForm1的代码模块中
'
' UserForm1代码 (请手动添加到UserForm1的代码模块)
 Private Sub UserForm_Initialize()
     Dim i As Long
     Dim matchCount As Long
     Me.Caption = "点击跳转"
     ' 获取匹配结果
     matchCount = UBound(g_matchArray, 1)
 
     ' 更新标题
     Me.lblTitle.Caption = "找到 " & matchCount & " 个匹配结果，点击跳转："
    Me.ML.Caption = g_matchArray(1, 2)
     ' 填充列表框
     With Me.lstMatches
         .Clear
         For i = 1 To matchCount
             .AddItem g_matchArray(i, 1)
             .List(.ListCount - 1, 1) = g_matchArray(i, 3) ' 存储行号
         Next i
     End With
 End Sub

 Private Sub lstMatches_Click()
     ' 点击列表项跳转
     Dim selectedIndex As Long
     Dim rowIndex As Long
     Dim wsData As Worksheet

     Set wsData = Sheets("数据源")

     selectedIndex = Me.lstMatches.ListIndex
     If selectedIndex >= 0 Then
         rowIndex = Me.lstMatches.List(selectedIndex, 1)
         wsData.Activate
         wsData.Cells(rowIndex, 1).Select
'         MsgBox "已跳转到匹配文本位置！", vbInformation, "跳转成功"
         ' 注意：这里没有关闭窗体，用户可以继续点击其他匹配项
     End If
 End Sub

 Private Sub cmdClose_Click()
     ' 关闭窗体
     Unload Me
 End Sub

 Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
     ' 处理右上角关闭按钮
     If CloseMode = vbFormControlMenu Then
         Unload Me
     End If
 End Sub

