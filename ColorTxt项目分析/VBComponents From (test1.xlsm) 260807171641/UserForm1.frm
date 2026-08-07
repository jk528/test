VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} UserForm1 
   Caption         =   "测试用例"
   ClientHeight    =   10500
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   9650.001
   OleObjectBlob   =   "UserForm1.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "UserForm1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False


Public PrevText As String
Public PrevSelstart As Long
Public longer_q As String
Public longer_z As String
Public longer_h As String
Dim newTopIndex2 As Long
Dim istest As Boolean
#If VBA7 Then
    Private Declare PtrSafe Function GetAsyncKeyState Lib "user32" (ByVal vKey As Long) As Integer
#Else
    Declare Function GetAsyncKeyState Lib "user32" (ByVal vKey As Long) As Integer
#End If
Const VK_LBUTTON As Long = &H1
Const VK_RBUTTON As Long = &H2
Const VK_CANCEL As Long = &H3
Const VK_MBUTTON As Long = &H4
Const VK_XBUTTON1 As Long = &H5
Const VK_XBUTTON2 As Long = &H6
Const VK_BACK As Long = &H8
Const VK_TAB As Long = &H9
Const VK_CLEAR As Long = &HC
Const VK_RETURN As Long = &HD
Const VK_SHIFT As Long = &H10
Const VK_CONTROL As Long = &H11
Const VK_MENU As Long = &H12
Const VK_PAUSE As Long = &H13
Const VK_CAPITAL As Long = &H14
Const VK_KANA As Long = &H15
Const VK_HANGUL As Long = &H15
Const VK_IME_ON As Long = &H16
Const VK_JUNJA As Long = &H17
Const VK_FINAL As Long = &H18
Const VK_HANJA As Long = &H19
Const VK_KANJI As Long = &H19
Const VK_IME_OFF As Long = &H1A
Const VK_ESCAPE As Long = &H1B
Const VK_CONVERT As Long = &H1C
Const VK_NONCONVERT As Long = &H1D
Const VK_ACCEPT As Long = &H1E
Const VK_MODECHANGE As Long = &H1F
Const VK_SPACE As Long = &H20
Const VK_PRIOR As Long = &H21
Const VK_NEXT As Long = &H22
Const VK_END As Long = &H23
Const VK_HOME As Long = &H24
Const VK_LEFT As Long = &H25
Const VK_UP As Long = &H26
Const VK_RIGHT As Long = &H27
Const VK_DOWN As Long = &H28
Const VK_SELECT As Long = &H29
Const VK_PRINT As Long = &H2A
Const VK_EXECUTE As Long = &H2B
Const VK_SNAPSHOT As Long = &H2C
Const VK_INSERT As Long = &H2D
Const VK_DELETE As Long = &H2E
Const VK_HELP As Long = &H2F
Const VK_0 As Long = &H30
Const VK_1 As Long = &H31
Const VK_2 As Long = &H32
Const VK_3 As Long = &H33
Const VK_4 As Long = &H34
Const VK_5 As Long = &H35
Const VK_6 As Long = &H36
Const VK_7 As Long = &H37
Const VK_8 As Long = &H38
Const VK_9 As Long = &H39
Const VK_A As Long = &H41
Const VK_B As Long = &H42
Const VK_C As Long = &H43
Const VK_D As Long = &H44
Const VK_E As Long = &H45
Const VK_F As Long = &H46
Const VK_G As Long = &H47
Const VK_H As Long = &H48
Const VK_I As Long = &H49
Const VK_J As Long = &H4A
Const VK_K As Long = &H4B
Const VK_L As Long = &H4C
Const VK_M As Long = &H4D
Const VK_N As Long = &H4E
Const VK_O As Long = &H4F
Const VK_P As Long = &H50
Const VK_Q As Long = &H51
Const VK_R As Long = &H52
Const VK_S As Long = &H53
Const VK_T As Long = &H54
Const VK_U As Long = &H55
Const VK_V As Long = &H56
Const VK_W As Long = &H57
Const VK_X As Long = &H58
Const VK_Y As Long = &H59
Const VK_Z As Long = &H5A
Const VK_LWIN As Long = &H5B
Const VK_RWIN As Long = &H5C
Const VK_APPS As Long = &H5D
Const VK_SLEEP As Long = &H5F
Const VK_NUMPAD0 As Long = &H60
Const VK_NUMPAD1 As Long = &H61
Const VK_NUMPAD2 As Long = &H62
Const VK_NUMPAD3 As Long = &H63
Const VK_NUMPAD4 As Long = &H64
Const VK_NUMPAD5 As Long = &H65
Const VK_NUMPAD6 As Long = &H66
Const VK_NUMPAD7 As Long = &H67
Const VK_NUMPAD8 As Long = &H68
Const VK_NUMPAD9 As Long = &H69
Const VK_MULTIPLY As Long = &H6A
Const VK_ADD As Long = &H6B
Const VK_SEPARATOR As Long = &H6C
Const VK_SUBTRACT As Long = &H6D
Const VK_DECIMAL As Long = &H6E
Const VK_DIVIDE As Long = &H6F
Const VK_F1 As Long = &H70
Const VK_F2 As Long = &H71
Const VK_F3 As Long = &H72
Const VK_F4 As Long = &H73
Const VK_F5 As Long = &H74
Const VK_F6 As Long = &H75
Const VK_F7 As Long = &H76
Const VK_F8 As Long = &H77
Const VK_F9 As Long = &H78
Const VK_F10 As Long = &H79
Const VK_F11 As Long = &H7A
Const VK_F12 As Long = &H7B
Const VK_F13 As Long = &H7C
Const VK_F14 As Long = &H7D
Const VK_F15 As Long = &H7E
Const VK_F16 As Long = &H7F
Const VK_F17 As Long = &H80
Const VK_F18 As Long = &H81
Const VK_F19 As Long = &H82
Const VK_F20 As Long = &H83
Const VK_F21 As Long = &H84
Const VK_F22 As Long = &H85
Const VK_F23 As Long = &H86
Const VK_F24 As Long = &H87
Const VK_NUMLOCK As Long = &H90
Const VK_SCROLL As Long = &H91
Const VK_LSHIFT As Long = &HA0
Const VK_RSHIFT As Long = &HA1
Const VK_LCONTROL As Long = &HA2
Const VK_RCONTROL As Long = &HA3
Const VK_LMENU As Long = &HA4
Const VK_RMENU As Long = &HA5
Const VK_BROWSER_BACK As Long = &HA6
Const VK_BROWSER_FORWARD As Long = &HA7
Const VK_BROWSER_REFRESH As Long = &HA8
Const VK_BROWSER_STOP As Long = &HA9
Const VK_BROWSER_SEARCH As Long = &HAA
Const VK_BROWSER_FAVORITES As Long = &HAB
Const VK_BROWSER_HOME As Long = &HAC
Const VK_VOLUME_MUTE As Long = &HAD
Const VK_VOLUME_DOWN As Long = &HAE
Const VK_VOLUME_UP As Long = &HAF
Const VK_MEDIA_NEXT_TRACK As Long = &HB0
Const VK_MEDIA_PREV_TRACK As Long = &HB1
Const VK_MEDIA_STOP As Long = &HB2
Const VK_MEDIA_PLAY_PAUSE As Long = &HB3
Const VK_LAUNCH_MAIL As Long = &HB4
Const VK_LAUNCH_MEDIA_SELECT As Long = &HB5
Const VK_LAUNCH_APP1 As Long = &HB6
Const VK_LAUNCH_APP2 As Long = &HB7
Const VK_OEM_1 As Long = &HBA
Const VK_OEM_PLUS As Long = &HBB
Const VK_OEM_COMMA As Long = &HBC
Const VK_OEM_MINUS As Long = &HBD
Const VK_OEM_PERIOD As Long = &HBE
Const VK_OEM_2 As Long = &HBF
Const VK_OEM_3 As Long = &HC0
Const VK_OEM_4 As Long = &HDB
Const VK_OEM_5 As Long = &HDC
Const VK_OEM_6 As Long = &HDD
Const VK_OEM_7 As Long = &HDE
Const VK_OEM_8 As Long = &HDF
Const VK_OEM_102 As Long = &HE2
Const VK_PROCESSKEY As Long = &HE5
Const VK_PACKET As Long = &HE7
Const VK_ATTN As Long = &HF6
Const VK_CRSEL As Long = &HF7
Const VK_EXSEL As Long = &HF8
Const VK_EREOF As Long = &HF9
Const VK_PLAY As Long = &HFA
Const VK_ZOOM As Long = &HFB
Const VK_NONAME As Long = &HFC
Const VK_PA1 As Long = &HFD
Const VK_OEM_CLEAR As Long = &HFE

Private Sub ListBox1_Click()

End Sub

Private Sub TextBox1_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    
    If (GetAsyncKeyState(VK_OEM_4) And &H8000) <> 0 Then
        Debug.Print "[ 键被按下 "
    End If
    If (GetAsyncKeyState(VK_OEM_6) And &H8000) <> 0 Then
        Debug.Print "] 键被按下 "
    End If
    Select Case True
        Case (GetAsyncKeyState(VK_A) And &H8000) <> 0
            Debug.Print "A 被按下"
        Case (GetAsyncKeyState(VK_MENU) And &H8000) <> 0 And (GetAsyncKeyState(VK_F4) And &H8000) <> 0
            Debug.Print "Alt 和 F4 同时被按下"
        Case (GetAsyncKeyState(VK_CONTROL) And &H8000) <> 0 And (GetAsyncKeyState(VK_S) And &H8000) <> 0
            Debug.Print "Ctrl 和 S 同时被按下"
        Case (GetAsyncKeyState(VK_SHIFT) And &H8000) <> 0 And (GetAsyncKeyState(VK_ESC) And &H8000) <> 0
            Debug.Print "Shift 和 Esc 同时被按下"
        Case Else
            Select Case True
                Case (GetAsyncKeyState(65) And &H8000) <> 0
                    Debug.Print "A 被按下"
                Case (GetAsyncKeyState(66) And &H8000) <> 0
                    Debug.Print "B 被按下"
                Case (GetAsyncKeyState(67) And &H8000) <> 0
                    Debug.Print "C 被按下"
                Case (GetAsyncKeyState(68) And &H8000) <> 0
                    Debug.Print "D 被按下"
                Case (GetAsyncKeyState(69) And &H8000) <> 0
                    Debug.Print "E 被按下"
                Case (GetAsyncKeyState(70) And &H8000) <> 0
                    Debug.Print "F 被按下"
                Case (GetAsyncKeyState(71) And &H8000) <> 0
                    Debug.Print "G 被按下"
                Case (GetAsyncKeyState(72) And &H8000) <> 0
                    Debug.Print "H 被按下"
                Case (GetAsyncKeyState(73) And &H8000) <> 0
                    Debug.Print "I 被按下"
                Case (GetAsyncKeyState(74) And &H8000) <> 0
                    Debug.Print "J 被按下"
                Case (GetAsyncKeyState(75) And &H8000) <> 0
                    Debug.Print "K 被按下"
                Case (GetAsyncKeyState(76) And &H8000) <> 0
                    Debug.Print "L 被按下"
                Case (GetAsyncKeyState(77) And &H8000) <> 0
                    Debug.Print "M 被按下"
                Case (GetAsyncKeyState(78) And &H8000) <> 0
                    Debug.Print "N 被按下"
                Case (GetAsyncKeyState(79) And &H8000) <> 0
                    Debug.Print "O 被按下"
                Case (GetAsyncKeyState(80) And &H8000) <> 0
                    Debug.Print "P 被按下"
                Case (GetAsyncKeyState(81) And &H8000) <> 0
                    Debug.Print "Q 被按下"
                Case (GetAsyncKeyState(82) And &H8000) <> 0
                    Debug.Print "R 被按下"
                Case (GetAsyncKeyState(83) And &H8000) <> 0
                    Debug.Print "S 被按下"
                Case (GetAsyncKeyState(84) And &H8000) <> 0
                    Debug.Print "T 被按下"
                Case (GetAsyncKeyState(85) And &H8000) <> 0
                    Debug.Print "U 被按下"
                Case (GetAsyncKeyState(86) And &H8000) <> 0
                    Debug.Print "V 被按下"
                Case (GetAsyncKeyState(87) And &H8000) <> 0
                    Debug.Print "W 被按下"
                Case (GetAsyncKeyState(88) And &H8000) <> 0
                    Debug.Print "X 被按下"
                Case (GetAsyncKeyState(89) And &H8000) <> 0
                    Debug.Print "Y 被按下"
                Case (GetAsyncKeyState(90) And &H8000) <> 0
                    Debug.Print "Z 被按下"
                Case (GetAsyncKeyState(189) And &H8000) <> 0
                    KeyCode = 189
                Case (GetAsyncKeyState(187) And &H8000) <> 0
                    KeyCode = 187
            End Select
            Debug.Print "键值:" & KeyCode
            Select Case KeyCode
           
                Case vbKeyReturn
                    If TextBox1 <> "" Then
                    KeyCode = 0
                    TextBox2.text = TextBox2.text & addcomma(TextBox1.Value)
                    TextBox1.text = ""
                    TextBox1.SetFocus
                    End If
                Case vbKey1
               
                 istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 0) & longer_h
                    
                Case vbKey2
                 istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 1) & longer_h
               
                Case vbKey3
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 2) & longer_h
                
                Case vbKey4
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 3) & longer_h
                
                Case vbKey5
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 4) & longer_h
                
                Case vbKey6
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 5) & longer_h
                
                Case vbKey7
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 6) & longer_h
                
                Case vbKey8
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 7) & longer_h
                
                Case vbKey9
                 istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 8) & longer_h
               
                Case vbKey0
                istest = True
                    TextBox1.text = longer_q & ListBox1.List(ListBox1.TopIndex + 9) & longer_h
                
                Case vbKeyUp
                Case 187
                    KeyCode = 0
                    newTopIndex2 = newTopIndex2 + 10
                    ListBox1.TopIndex = newTopIndex2
                Case 189
                    KeyCode = 0
                    newTopIndex2 = newTopIndex2 - 10
                    If newTopIndex2 < 0 Then
                        newTopIndex2 = 0
                    End If
                    ListBox1.TopIndex = newTopIndex2
            End Select
            If KeyCode >= 48 And KeyCode <= 57 Then
            KeyCode = 0
            longer_q = longer_q & longer_z
            longer_z = ""
            PrevText = ""
            newTopIndex2 = 0
            End If
    End Select
End Sub

Private Sub TextBox1_Change()
    Dim currentText As String
    Dim CurrentSelstart As Long
    Dim addedChars As String
    Dim delta As Long
    

If istest Then
istest = False
Exit Sub

Else


    
    currentText = TextBox1.text
    CurrentSelstart = TextBox1.SelStart
    If Len(PrevText) = 0 Then
        addedChars = currentText
    Else
        If Len(currentText) > Len(PrevText) Then
            delta = Len(currentText) - Len(PrevText)
            addedChars = Mid(currentText, CurrentSelstart - delta + 1, delta)
        Else
            If Len(currentText) = Len(PrevText) Then
                If currentText <> PrevText Then
                    If CurrentSelstart > Len(currentText) Then
                        addedChars = ""
                    Else
                        addedChars = Mid(currentText, CurrentSelstart, 1)
                    End If
                Else
                    addedChars = ""
                End If
            Else
                addedChars = ""
            End If
        End If
    End If
    PrevText = currentText
    PrevSelstart = CurrentSelstart
    Label1.Caption = Mid(TextBox1.text, 1, TextBox1.SelStart - Len(addedChars))
    Label2.Caption = addedChars
    Label3.Caption = Mid(TextBox1.text, TextBox1.SelStart + 1)
    longer_q = Mid(TextBox1.text, 1, TextBox1.SelStart - Len(addedChars))
    longer_z = addedChars
    longer_h = Mid(TextBox1.text, TextBox1.SelStart + 1)
    find (addedChars)
    
    End If
End Sub

Sub find(n)
    Dim i, j, k, irow
    Dim str As String
    str = n
    If str = "" Then
    Exit Sub
    Else
    
    Dim ar, br()
    With Sheets("数据源")
        irow = .[a1048576].End(3).row
        ar = .Range("a2:b" & irow)
    End With
    ReDim br(1 To UBound(ar), 1 To UBound(ar, 2))
    For i = 1 To UBound(ar)
        If ar(i, 1) Like "*" & str & "*" Then
            k = k + 1
            For j = 1 To UBound(br, 2)
                br(k, j) = ar(i, j)
            Next j
        End If
    Next i
    ListBox1.ColumnCount = 3
    ListBox1.ColumnWidths = "250,100,20"
    ListBox1.fontSize = 22
    ListBox1.List = br
    End If
End Sub

Private Sub TextBox2_Change()
TextBox2.fontSize = 22
TextBox2.MultiLine = True
TextBox2.WordWrap = True
TextBox2.ScrollBars = fmScrollBarsVertical
TextBox2.SetFocus
TextBox2.SelStart = Len(TextBox2.text)
TextBox1.text = ""
TextBox1.SetFocus
End Sub

Private Sub UserForm_Initialize()
    Me.StartUpPosition = 0
    Me.Left = Application.Left + Application.Width / 2 - Me.Width / 2
    Me.Top = Application.Top + Application.Height / 2 - Me.Height / 2
    AddDemoData
    EnableMouseScroll Me
    PrevText = TextBox1.text
    PrevSelstart = TextBox1.SelStart
End Sub

Private Sub AddDemoData()
    Dim i As Long
    For i = 1 To 10
        ListBox2.AddItem i
    Next i
    ListBox2.fontSize = 22
    ListBox2.ColumnWidths = "20"
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        Cancel = True
        Me.Hide
    End If
End Sub



Function addcomma(TEXTVALUE As String)
    On Error Resume Next '标点符号补全
    Dim n, mm, i
    n = Array(-24157, -23617, -23647, -23621, -23636, -24144, -24143, -23622, 13)
    mm = False
            If Asc(Left(TEXTVALUE, 1)) = 34 Then TEXTVALUE = Chr(-24144) & Mid(TEXTVALUE, 2, Len(TEXTVALUE) - 1)
            If Asc(Right(TEXTVALUE, 1)) = -23622 Then TEXTVALUE = TEXTVALUE & Chr(-24144)
            If Asc(Right(TEXTVALUE, 1)) = 34 Then TEXTVALUE = Left(TEXTVALUE, Len(TEXTVALUE) - 1) & Chr(-24143)
            If Asc(Right(TEXTVALUE, 1)) = 46 Then TEXTVALUE = Left(TEXTVALUE, Len(TEXTVALUE) - 1) & Chr(-24157)
            If Asc(Right(TEXTVALUE, 1)) = 32 Then TEXTVALUE = Left(TEXTVALUE, Len(TEXTVALUE) - 1) & Chr(13)
            For i = 0 To UBound(n)
                If Asc(Right(TEXTVALUE, 1)) = n(i) Then
'                MsgBox Asc(Right(TEXTVALUE, 1))
                    mm = True
                    Exit For
                End If
                
            Next
            If mm = False Then TEXTVALUE = TEXTVALUE & Chr(-23636)
          addcomma = TEXTVALUE
End Function


