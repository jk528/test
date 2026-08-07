Attribute VB_Name = "BB_003MouseOverControl"
Option Explicit

Sub ShowDemoForm()
    With New DemoForm
        .Caption = "MODELESS form"
        .Show vbModeless
    End With
End Sub
