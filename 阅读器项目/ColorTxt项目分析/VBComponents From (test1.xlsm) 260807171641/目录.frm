VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} 目录 
   Caption         =   "UserForm1"
   ClientHeight    =   8205.001
   ClientLeft      =   -270
   ClientTop       =   -860
   ClientWidth     =   2330
   OleObjectBlob   =   "目录.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "目录"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False





Private Sub CommandButton1_Click()
    Dim sheetName As String
    Dim foundsheet As Boolean
    Dim sheetlist()
    ListBox1.Clear
    sheetName = TextBox1.Value
    For Each Sheet In Worksheets
        If InStr(1, Sheet.Name, sheetName, 0) Then
            n = n + 1
            ReDim Preserve sheetlist(1 To n)
            sheetlist(n) = Sheet.Name
            foundsheet = True
        End If
    Next
    If Not foundsheet Then
        MsgBox "找不到名为" & sheetName & "的sheet页"
    Else
        If UBound(sheetlist) = 1 Then
            Sheets(CStr(sheetlist(1))).Activate
     
        End If
        ListBox1.List = sheetlist
    End If
End Sub






Private Sub ListBox1_Click()
    Target = ListBox1.List(ListBox1.ListIndex)
    For Each Sheet In Worksheets
        If Target = Sheet.Name Then
            Sheet.Name = CStr(Target)
            Sheets(Sheet.Name).Activate
        End If
    Next
End Sub

'UserForm_Activate事件：激活窗体时触发的事件
'本例代码的功能是显示窗体时将所有表的名称导入到列表框中，然后根据表的数量调整窗体与列表框的高度
Private Sub UserForm_Activate()
    Me.Caption = "工作表目录"      '设置窗体的标题文字，其中Me代表窗体
    ListBox1.Width = 80            '设置列表框的宽度
    Dim Sht As Worksheet           '声明一个Worksheet型的变量
    For Each Sht In Sheets         '遍历所有表
        Me.ListBox1.AddItem Sht.Name '通过列表框的AddItem方法将表名称添加到列表框中
    Next
    '让窗体的高度等于列表框的行数乘以列表框的字体大小，再加50
    '列表框的字体大小相当于列表框的行高，加35是因为窗体还包含包框的空白区域
    'Me.Height = ListBox1.ListCount * ListBox1.Font.Size + 240
    '让列表框的高度等于列表框的行数乘以列表框的字体大小，再加5
    '加5的目的是因为列表框的上下边界需要一定空间，必须比行高乘行数稍大才能完全容纳所有数据
    'ListBox1.Height = ListBox1.ListCount * ListBox1.Font.Size + 200
End Sub

Private Sub UserForm_Initialize()
ShowAllPages
EnableMouseScroll Me
End Sub


Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        Cancel = True
        Me.Hide
    End If
End Sub

