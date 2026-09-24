VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} UserForm4 
   Caption         =   "UserForm4"
   ClientHeight    =   6120
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   10100
   OleObjectBlob   =   "UserForm4.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "UserForm4"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit



' 窗体初始化事件
Private Sub UserForm_Initialize()
    Dim i As Long
    Dim matchCount As Long
    
    ' 设置窗体属性
    With Me
        .Caption = "目录跳转列表"
        .Width = 560
        .Height = 320
        .StartUpPosition = 1 ' 居中
    End With
    
    ' 设置标签属性
    With Me.lblTitle
        .Caption = "找到 0 个目录项，点击跳转："
        .Left = 10
        .Top = 10
        .Width = 530
        .Height = 20
        .Font.Bold = True
    End With
    
    ' 设置列表框属性
    With Me.lstCatalog
        .Left = 10
        .Top = 40
        .Width = 530
        .Height = 200
        .ColumnCount = 2
        .ColumnWidths = "300;0" ' 第二列隐藏，用于存储行号
        .Font.Size = 20 ' 设置字体大小为24
        .MultiSelect = fmMultiSelectSingle
    End With
    
    ' 设置关闭按钮属性
    With Me.cmdClose
        .Caption = "关闭"
        .Left = 225
        .Top = 250
        .Width = 100
        .Height = 30
        .ForeColor = RGB(255, 255, 255)
        .BackColor = RGB(128, 128, 128)
    End With
    
    ' 填充目录结果
    If IsArray(g_catalogArray) Then
        matchCount = UBound(g_catalogArray, 1)
        
        ' 更新标题
        Me.lblTitle.Caption = "找到 " & matchCount & " 个目录项，点击跳转："
        
'        ' 调整窗体高度
'        If matchCount > 6 Then
'            Me.Height = 200 + matchCount * 25
'            Me.lstCatalog.Height = Me.Height - 100
'        End If
        
        ' 填充列表框
        With Me.lstCatalog
            .Clear
            For i = 1 To matchCount
                .AddItem g_catalogArray(i, 1)
                .List(.ListCount - 1, 1) = g_catalogArray(i, 3) ' 存储行号
            Next i
        End With
    End If
    EnableMouseScroll Me
End Sub

' 列表框点击事件
Private Sub lstCatalog_Click()
    ' 点击列表项跳转
    Dim selectedIndex As Long
    Dim rowIndex As Long
    Dim wsData As Worksheet
    
    Set wsData = Sheets("数据源")
    
    selectedIndex = Me.lstCatalog.ListIndex
    If selectedIndex >= 0 Then
        rowIndex = Me.lstCatalog.List(selectedIndex, 1)
        wsData.Activate
        wsData.Cells(rowIndex, 1).Select
    '    MsgBox "已跳转到目录项对应位置！", vbInformation, "跳转成功"
        ' 注意：这里没有关闭窗体，用户可以继续点击其他目录项
    End If
End Sub

' 关闭按钮点击事件
Private Sub cmdClose_Click()
    ' 关闭窗体
    Me.Hide
    Unload Me
End Sub

' 查询关闭事件

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        Cancel = True
        Me.Hide
    End If
End Sub
