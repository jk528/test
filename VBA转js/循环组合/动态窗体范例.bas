Attribute VB_Name = "DynamicFormModule"
Option Explicit

' ============================================================
'  动态窗体范例 - 纯模块实现
'  功能：代码动态生成 UserForm + 控件
'        关闭窗体后自动删除整个窗体组件（全部清零）
'  前提：需在 信任中心 → 宏设置 中勾选
'        "信任对 VBA 工程对象模型的访问"
'  用法：调用 StartDynamicForm
' ============================================================

' --- 入口：创建并显示动态窗体 ---
Public Sub StartDynamicForm()

    Dim vbProj As Object
    Dim vbComp As Object

    ' 获取当前工程的 VBProject
    On Error Resume Next
    Set vbProj = ThisWorkbook.VBProject
    On Error GoTo 0

    If vbProj Is Nothing Then
        MsgBox "无法访问 VBProject，请在信任中心勾选" & vbCrLf & _
               ""信任对 VBA 工程对象模型的访问"", vbExclamation, "提示"
        Exit Sub
    End If

    ' 如果上次残留同名窗体，先删除
    RemoveExistingForm vbProj, "DynamicForm"

    ' 动态创建 UserForm（类型 3 = vbext_ct_MSForm）
    Set vbComp = vbProj.VBComponents.Add(3)
    vbComp.Name = "DynamicForm"

    Dim frm As Object
    Set frm = vbComp.Designer

    ' ---- 窗体属性 ----
    frm.Caption = "动态生成窗体范例"
    frm.Width = 320
    frm.Height = 220

    ' ---- 控件 1：标题标签 ----
    Dim lbl As Object
    Set lbl = frm.Controls.Add("Forms.Label.1", "lblTitle")
    lbl.Caption = "这是纯代码生成的窗体"
    lbl.Left = 20: lbl.Top = 15
    lbl.Width = 280: lbl.Height = 24
    lbl.TextAlign = 2  ' 居中

    ' ---- 控件 2：输入文本框 ----
    Dim txt As Object
    Set txt = frm.Controls.Add("Forms.TextBox.1", "txtInput")
    txt.Left = 20: txt.Top = 55
    txt.Width = 280: txt.Height = 22
    txt.Text = "在这里输入内容"

    ' ---- 控件 3：确定按钮 ----
    Dim btnOK As Object
    Set btnOK = frm.Controls.Add("Forms.CommandButton.1", "btnOK")
    btnOK.Caption = "确定"
    btnOK.Left = 20: btnOK.Top = 95
    btnOK.Width = 70: btnOK.Height = 28

    ' ---- 控件 4：关闭并删除按钮 ----
    Dim btnClose As Object
    Set btnClose = frm.Controls.Add("Forms.CommandButton.1", "btnClose")
    btnClose.Caption = "关闭并删除"
    btnClose.Left = 110: btnClose.Top = 95
    btnClose.Width = 110: btnClose.Height = 28

    ' ---- 控件 5：说明标签 ----
    Dim lblNote As Object
    Set lblNote = frm.Controls.Add("Forms.Label.1", "lblNote")
    lblNote.Caption = "关闭后窗体将被彻底删除，不留痕迹"
    lblNote.Left = 20: lblNote.Top = 145
    lblNote.Width = 280: lblNote.Height = 20
    lblNote.ForeColor = RGB(128, 128, 128)

    ' ---- 向窗体代码模块注入事件代码 ----
    Dim codeMod As Object
    Set codeMod = vbComp.CodeModule

    Dim sCode As String
    sCode = _
        "Option Explicit" & vbCrLf & vbCrLf & _
        "' --- 确定按钮：读取文本框内容 ---" & vbCrLf & _
        "Private Sub btnOK_Click()" & vbCrLf & _
        "    MsgBox ""输入内容："" & txtInput.Text, vbInformation, ""提示""" & vbCrLf & _
        "End Sub" & vbCrLf & vbCrLf & _
        "' --- 关闭按钮：卸载并安排删除 ---" & vbCrLf & _
        "Private Sub btnClose_Click()" & vbCrLf & _
        "    Unload Me" & vbCrLf & _
        "    Application.OnTime Now + TimeSerial(0, 0, 1), ""DeleteDynamicForm""" & vbCrLf & _
        "End Sub" & vbCrLf & vbCrLf & _
        "' --- 点 X 关闭时也触发删除 ---" & vbCrLf & _
        "Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)" & vbCrLf & _
        "    If CloseMode = vbFormControlMenu Then" & vbCrLf & _
        "        Application.OnTime Now + TimeSerial(0, 0, 1), ""DeleteDynamicForm""" & vbCrLf & _
        "    End If" & vbCrLf & _
        "End Sub"

    codeMod.AddFromString sCode

    ' ---- 显示窗体（非模态可选 vbModeless） ----
    Dim frmInstance As Object
    Set frmInstance = VBA.UserForms.Add("DynamicForm")
    frmInstance.Show vbModal

End Sub

' --- 删除动态窗体（关闭后延迟调用） ---
Public Sub DeleteDynamicForm()

    Dim vbProj As Object
    Dim vbComp As Object

    On Error Resume Next
    Set vbProj = ThisWorkbook.VBProject
    Set vbComp = vbProj.VBComponents("DynamicForm")
    If Not vbComp Is Nothing Then
        vbProj.VBComponents.Remove vbComp
        Debug.Print "DynamicForm 已删除"
    End If
    On Error GoTo 0

End Sub

' --- 辅助：删除已存在的同名窗体 ---
Private Sub RemoveExistingForm(vbProj As Object, sName As String)

    Dim vbComp As Object
    On Error Resume Next
    Set vbComp = vbProj.VBComponents(sName)
    If Not vbComp Is Nothing Then
        vbProj.VBComponents.Remove vbComp
    End If
    On Error GoTo 0

End Sub
