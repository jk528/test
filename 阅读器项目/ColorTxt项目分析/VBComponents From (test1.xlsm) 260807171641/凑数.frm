VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} 凑数 
   Caption         =   "凑数"
   ClientHeight    =   4155
   ClientLeft      =   110
   ClientTop       =   450
   ClientWidth     =   4990
   OleObjectBlob   =   "凑数.frx":0000
   StartUpPosition =   1  '所有者中心
End
Attribute VB_Name = "凑数"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False





'参数
Private Var '用于列表框显示
Private Arr '用于注释栏显示
Private Cs As Object '用于记录参数信息
'选区
Private She As Object '选区所在表格
Private Txtt$ '全部地址
Private Txtv$ '可见地址
'数据
Private ss As Object '数据字典
'凑数
Private sj(), jg(), Dic, d&, d2&, h, h0#, h1, h2, h3#, k&, L&, l2&, m&, n&, n2&, t2&, cnt&, cnt0&, cnt1&, cnt2&, tms#

'窗体初始化
Private Sub UserForm_Initialize()
    '清空使用痕迹
    CsCmb2_Click
End Sub
'窗体退出
Private Sub UserForm_Terminate()
    Set Cs = Nothing
    Set ss = Nothing
    Set She = Nothing
    Erase Var, Arr, sj, jg
End Sub
'窗体激活时
Private Sub UserForm_Activate()
    '空值无焦点
    If Me.CsTex1.Value = "" Then Exit Sub
    '数值框设置焦点
    With Me.CsTex2
        Debug.Print 1
        .SetFocus: .SelStart = 0: .SelLength = Len(.Value)
    End With
End Sub
    '参数重置
    Private Sub ResetCs()
        '定义参数字典
        If Cs Is Nothing Then Set Cs = CreateObject("scripting.dictionary") Else Cs.RemoveAll
        '默认参数设置
        Cs("求和目标") = 0
        Cs("求和上限") = 0
        Cs("使用元素下限") = 0
        Cs("使用元素上限") = 0
        Cs("结果个数") = 5
        Cs("重复排除") = 1
        Cs("设置深度") = -1
        Cs("回溯次数") = 1
    End Sub
    '注释重置
    Private Sub ResetZs()
        '默认注释设置
        ReDim Arr(1 To 9)
        Arr(1) = "凑数目标求和值（h" & vbCrLf & "[h, h2]=[h, 0]完全匹配h"
        Arr(2) = "凑数目标求和值上限（h2" & vbCrLf & "[h<h2]匹配[h, h2]，[h>h2]匹配[h, h+h2]"
        Arr(3) = "凑数使用元素的下限数量（n" & vbCrLf & "[n, n2]=[0, 0]时不限使用元素数量，[n, 0]时只使用n个元素"
        Arr(4) = "凑数使用元素的上限数量（n2" & vbCrLf & "[n, n2]时使用元素数量在n-n2之间"
        Arr(5) = "凑数规定的结果个数（l" & vbCrLf & "比如，当总结果数有10个时规定输出5个"
        Arr(6) = "是否排除凑数重复结果（Isdp" & vbCrLf & "排除填1，不排除填-1"
        Arr(7) = "凑数遍历深度/次数（Ndep" & vbCrLf & "无限制填-1，有限制填1-32（2的n次方次）"
        Arr(8) = "[设置深度]数值在1-32生效。输入>整数可以在到达递归检查深度之后，不退出而继续回溯t2次以便在附近继续搜索"
        Arr(9) = Cs("重复排除")
    End Sub
    '列表框显示
    Private Sub ResetList()
        '列表框显示
        Dim keys: keys = Cs.keys
        Dim itms: itms = Cs.items
        ReDim Var(1 To Cs.count, 1 To 2)
        For i = 0 To Cs.count - 1
            Var(i + 1, 1) = keys(i): Var(i + 1, 2) = itms(i)
        Next
        Me.ListBox1.ColumnCount = 2
        Me.ListBox1.ColumnWidths = "55;40"
        Me.ListBox1.List = Var
        '释放内存
        Erase keys, itms
    End Sub
'选择凑数区域
Private Sub CsTex1_DblClick(ByVal Cancel As MSForms.ReturnBoolean)
    '选择凑数区域
    If SelRange("请选择凑数数据区域：", True) = False Then
        MsgBox "当前选区无效（未选区或选区无内容", vbOKOnly, "LELEDY"
        Me.CsTex3.Value = "Tips：请双击选择凑数数据区域..."
        Me.Show 0
        Exit Sub
    End If
    '显示窗体
    Me.Show 0
    '默认选中参数
    Me.ListBox1.Selected(0) = True
    '同步所选参数信息
    Call GoWriting
End Sub
    '选择凑数区域并赋值
    Private Function SelRange(str$, Isv As Boolean) As Boolean
        '选区识别与字典赋值
        On Error Resume Next
        Dim edy As Object: Set edy = CreateObject("scripting.dictionary"): Me.Hide
        Set edy(0) = Application.InputBox(str, "LELEDY", Type:=8)
        Set edy(1) = edy(0).Parent
        Set edy(2) = Application.Intersect(edy(0), edy(1).UsedRange)
        If edy(0) Is Nothing Or edy(2) Is Nothing Then Set edy = Nothing: Exit Function
        '记录选区信息
        Set She = edy(2).Parent
        Txtt = edy(2).Address(1, 1, 1, 1)
        If edy(2).count > 1 And Isv = True Then Set edy(2) = edy(2).SpecialCells(xlCellTypeVisible)
        Txtv = edy(2).Address(1, 1, 1, 1)
        '记录选区地址
        Me.CsTex1.Value = IIf(Cschx1 = True, Txtv, Txtt)
        edy(1).Range(Me.CsTex1.Value).Select
        '存储选区数值数据
        Call SaveSj
        '释放内存
        Set edy = Nothing
        '选区成功标记
        SelRange = True
        '设置控件可用
        Me.CsCmb1.enabled = True: Me.CsCmb2.enabled = True
    End Function
    '储存选区数值
    Private Sub SaveSj()
        Set ss = CreateObject("scripting.dictionary")
        Dim Aea As Range, Ars$, Tmp, Tro&, Trt&
        Ars = IIf(Me.Cschx1.Value, Txtv, Txtt)
        For Each Aea In She.Range(Ars).Areas
            Select Case Aea.count
            Case 1
                Tmp = Aea.Value
                If IsNumeric(Tmp) And Not Tmp = "" Then ss(Aea.Address) = CDec(Tmp)
            Case Else
                Tmp = Aea.Value
                For Tro = 1 To UBound(Tmp, 1)
                    For Trt = 1 To UBound(Tmp, 2)
                        If IsNumeric(Tmp(Tro, Trt)) And Not Tmp(Tro, Trt) = "" Then ss(Aea.Cells(Tro, Trt).Address) = CDec(Tmp(Tro, Trt))
                    Next
                Next
            End Select
        Next Aea
        Set Aea = Nothing: Erase Tmp
    End Sub
'凑数区域可见转换
Private Sub Cschx1_Click()
    Me.CsTex1.Value = IIf(Cschx1, Txtv, Txtt)
    '存储选区数值数据
    Call SaveSj
    '同步所选参数信息
    Call GoWriting
End Sub
'列表框行为
Private Sub ListBox1_Click()
    '单击列表框空白区时退出
    If Me.ListBox1.ListIndex = -1 Then Exit Sub
    '同步所选参数信息
    Call GoWriting
End Sub
    '同步所选参数信息并设置焦点
    Private Sub GoWriting()
        Me.CsLbl3.Caption = Var(Me.ListBox1.ListIndex + 1, 1) & "："
        Me.CsTex2.Value = Var(Me.ListBox1.ListIndex + 1, 2)
        Me.CsTex3.Value = "Tips：" & Arr(Me.ListBox1.ListIndex + 1)
        '空值无焦点
        If Me.CsTex1.Value = "" Then Exit Sub
        '数值框设置焦点
        With Me.CsTex2
            .SetFocus: .SelStart = 0: .SelLength = Len(.Value)
        End With
    End Sub
'参数输入限制
Private Sub CsTex2_KeyPress(ByVal KeyAscii As MSForms.ReturnInteger)
    '允许输入数字、负号和小数点
    If Not (KeyAscii >= 48 And KeyAscii <= 57) And KeyAscii <> 45 And KeyAscii <> 46 And KeyAscii <> 8 Then KeyAscii = 0
    '确保负号只能出现在第一位
    If KeyAscii = 45 And Me.CsTex2.SelStart <> 0 Then KeyAscii = 0
    '确保小数点只能输入一次
    If KeyAscii = 46 And InStr(Me.CsTex2.text, ".") > 0 Then KeyAscii = 0
End Sub
'回车时保存并切换参数（保持焦点并选中内容）
Private Sub CsTex2_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If Me.ListBox1.ListIndex = -1 Then Exit Sub
    If KeyCode = vbKeyReturn Then
        If Me.CsTex2.Value = "" Or Not (IsNumeric(Me.CsTex2.Value)) Then Me.CsTex2.Value = 0
        '保存参数数值
        Cs(Me.ListBox1.List(Me.ListBox1.ListIndex, 0)) = Me.CsTex2.Value + 0
        '注释重置
        Call ResetZs
        '列表框显示
        Call ResetList
        '切换下一个参数
        Dim Ind As Integer
        If Me.ListBox1.ListIndex = Me.ListBox1.ListCount - 1 Then Ind = 0 Else Ind = Me.ListBox1.ListIndex + 1
        Me.ListBox1.Selected(Ind) = True
        '取消回车键默认行为
        KeyCode = 0
    End If
End Sub
'清空使用痕迹
Private Sub CsCmb2_Click()
    '选区清除
    Me.CsTex1.Value = ""
    Txtt = "": Txtv = ""
    '参数重置
    Call ResetCs
    '注释重置
    Call ResetZs
    '列表框显示
    Call ResetList
    '默认选中参数
    Me.ListBox1.Selected(0) = True
    '选区提示
    Me.CsTex3.Value = "Tips：请双击选择凑数数据区域..."
End Sub
    '判断参数有效性
    Private Sub Validity()
        Dim Txtt$
        Txtt = "使用元素下限"
        If InStr(1, Cs(Txtt), ".") Or InStr(1, Cs(Txtt), "-") Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 不能为负数或小数", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
        Txtt = "使用元素上限"
        If InStr(1, Cs(Txtt), ".") Or InStr(1, Cs(Txtt), "-") Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 不能为负数或小数", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
        Txtt = "结果个数"
        If InStr(1, Cs(Txtt), ".") Or InStr(1, Cs(Txtt), "-") Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 不能为负数或小数", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
        Txtt = "重复排除"
        If Not (Cs(Txtt) + 0 <> -1) And Not (Cs(Txtt) + 0 <> 1) Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 只能为1或者-1", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
        Txtt = "设置深度"
        If InStr(1, Cs(Txtt), ".") Or Cs(Txtt) + 0 < -1 Or Cs(Txtt) + 0 > 32 Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 只能为-1或者1-32之间的整数", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
        Txtt = "回溯次数"
        If InStr(1, Cs(Txtt), ".") Or InStr(1, Cs(Txtt), "-") Then
            If MsgBox("参数 [" & Replace(Txtt, "：", "") & "] 不能为负数或小数", vbOKOnly, "LELEDY") = vbOK Then Exit Sub
        End If
    End Sub
'开始凑数
Private Sub CsCmb1_Click()
    '判断参数有效性
    Call Validity
    '获取升序数组
    Dim Aupo: Aupo = ss.keys
    Dim Aupt: Aupt = ss.items
    Call SortOfList(Aupo, Aupt, 0, ss.count - 1, 2)
    '凑数
    Call kagawa_42(ss.count, Aupo, Aupt)
End Sub
    '灰袍法师（希尔排序
    Private Sub SortOfList(ByRef Tpkey, ByRef Tpitm, L&, R&, Ind&)
        temp_h2 = Array(1, 5, 19, 41, 109, 211, 503, 929, 2161, 3907, 8929, 16001, 36293, 64763, 146309, 260609, 587527, 1045055, 2354689, 4188161, 9427969)
        ReDim h_arr(LBound(temp_h2) To UBound(temp_h2))
        h_arr(LBound(h_arr)) = 1
        For i = LBound(h_arr) + 1 To UBound(h_arr)
            h_arr(i) = temp_h2(i)
            If h_arr(i) < (R - L) / 9 Then max_h = i
        Next i
        If max_h < LBound(h_arr) Then max_h = LBound(h_arr)
        one = 1
        For i = max_h To LBound(h_arr) Step -one
            h = h_arr(i)
            For Offset = 0 To h - 1
                For j = L + Offset To R Step h
                    Insert = Tpitm(j): swap1 = Tpkey(j)
                    For k = j - h To L + Offset Step -h
                        If Choose(Ind, Insert > Tpitm(k), Insert < Tpitm(k)) Then
                            Tpitm(k + h) = Tpitm(k): Tpitm(k) = Insert
                            Tpkey(k + h) = Tpkey(k): Tpkey(k) = swap1
                        Else
                            Exit For
                        End If
                    Next k
                Next j
            Next Offset
        Next i
    End Sub
    '香川群子（双列超级凑数递归算法： 小数d [h,h2]范围 [n,n2]范围 增加行序号位置标记的输出
    Private Sub kagawa_42(Rws&, Aupo, Aupt) 'Aupo和Aupt为(0-n)，Rws为Ubound(Aupo)+1
        '算法要点：
        '1.逆序递归差值计算
        '2.末位正序检索
        '3.次位=[r,r+h2]剪枝: 累计和不足<r 或组合后 >r+h2时剪枝停止
        Dim sj0, i&, j&, tms1#
        tms = Timer
        '指定小数位d记录和值范围[h0,h3] 并转为十进制的和上限h以及差值h2
        h0 = Cs("求和目标")
        h3 = Cs("求和上限")
        If h3 = 0 Then h3 = h0 Else If h3 < h0 Then h3 = h0 + h3
        h = CDec(h0): h2 = CDec(h3 - h0)
        '允许回溯t2 以及递归设置深度cnt0默认2^16=65536 实际最大深度记录cnt2
        t2 = Cs("回溯次数") + 1
        cnt0 = Cs("设置深度")
        If cnt0 < 0 Then cnt0 = 0 Else If cnt0 < 32 Then cnt0 = 2 ^ IIf(cnt0, cnt0, 16)
        '使用元素
        m = Rws
        n = Cs("使用元素下限")
        n2 = Cs("使用元素上限")
        If n2 = 0 Then If n = 0 Then n2 = m Else n2 = n
        '重复元素d2统计 负数总和h1统计 初始化
        ReDim sj(m, 3)
        d2 = 0: h1 = CDec(0)
        Set Dic = CreateObject("Scripting.Dictionary")
        For i = 1 To m
            '读入数量/金额的原始数据
            sj(i, 1) = Aupo(i - 1): sj(i, 2) = CDec(Aupt(i - 1)): sj(i, 3) = CDec(0)
            j = Dic(sj(i, 2)): Dic(sj(i, 2)) = j + 1: If j = 1 Then d2 = d2 + 2 Else If j > 1 Then d2 = d2 + 1 '数据重复时
            '凑数项的累计和（负数时扩大求和值
            If sj(i, 2) < 0 Then Arr(9) = Arr(9) + 1: h1 = h1 - sj(i, 2) Else sj(i, 0) = sj(i - 1, 0) + sj(i, 2)
        Next
        '重复项数
        If d2 Then If Arr(9) < 0 Then d2 = -d2: Arr(9) = d2 Else Arr(9) = d2
        '结果数组
        L = Cs("结果个数")
        If L = 0 Then ReDim jg(20000, 7) Else If L < 1048570 Then ReDim jg(L + 1, 7) Else L = 1048570: ReDim jg(L + 1, 7)
        jg(0, 0) = "cnt": jg(0, 1) = "tms": jg(0, 2) = "cnt1": jg(0, 3) = "n": jg(0, 4) = "sum": jg(0, 5) = "ttl": jg(0, 6) = "adr": jg(0, 7) = "detail:"
        '递归
        Application.EnableCancelKey = xlErrorHandler
        On Error GoTo Err_Handler
        k = 0: l2 = 0: cnt = 0: cnt1 = 0: cnt2 = 0: tms1 = Timer
        Call dgH421(h, 0, "", 0, "", m + 1, 1)
        Application.StatusBar = ""
Err_Handler:
        '输出结果
        Dim msg$: msg = "找到解数" & k & "，递归次数" & cnt & "，最大深度" & cnt2 & "，耗时" & Format(Timer - tms1, "0.0000s")
        Me.CsTex3.Value = IIf(err = 18, "Ctrl+Break ", "") & "Tips：" & msg & "。凑数数据中的重复项数" & Abs(d2) & "。"
        '可见控件
        Me.CsSpn2.enabled = True: Me.CsCmb3.enabled = True: Me.CsCmb4.enabled = True
        If k Then Me.CsSpn2.min = 1: Me.CsSpn2.max = k: Me.CsSpn2.Value = 1 Else Me.CsSpn2.min = 1: Me.CsSpn2.max = 1: Me.CsSpn2.Value = 1
    End Sub
    Private Sub dgH421(R, rs#, s$, amt#, adr$, j&, t&) 'Call dgH4(h, 0, "", m + 1, 1)
        Dim i&, i2&, t1, r2, rr#, ss$, tt#, ad$
        If L > 0 Then If k >= L Then Exit Sub '指定输出个数l时退出
        cnt = cnt + 1: If cnt Mod 10000 = 0 Then DoEvents: Application.StatusBar = Format(Timer - tms, "0.0s K= ") & k & Format(cnt, " #,##0") & "..." & Left(s, 99)
        '指定计算深度cnt0时 当计数cnt1超过cnt0时 开始回溯 如果t回溯到小于t2个数时则允许重新计数 这样可以在剩余t2个数之后延长计算深度
        cnt1 = cnt1 + 1: If cnt0 Then If cnt1 > cnt0 Then If t > t2 Then Exit Sub Else cnt1 = 0 '允许回溯到t2时 重新向下开始计数
        If t >= n And t <= n2 Then '在指定个数范围内
            r2 = R + h2 + IIf(err = 18, "Ctrl+Break ", 0) '当前剩余和值上限r2 → 剩余目标和值范围[r,r2]
            For i = 1 To j - 1 '从最小元素开始向上遍历检索匹配剩余值
                t1 = sj(i, 2) '当前值读入t1
                If R <= t1 And t1 <= r2 Then 't1正好落在剩余目标和值范围[r,r2]内时得到一组满足条件的组合
                    rr = rs + sj(i, 2) '得到凑数组合的求和结果
                    ss = s & "+" & sj(i, 2) '得到凑数组合的文本字符串算式
                    tt = amt + sj(i, 3) '得到实际组合的关联汇总结果
                    ad = adr & "+" & sj(i, 1) '得到凑数组合的序号字符串
                    If d2 > 0 Then If Dic.exists(ss) Then GoTo DicExt Else Dic(ss) = ss '使用字典排除重复组合
                    k = k + 1 '计数+1
                    If L = -1 Then
                        'Print #1, k; rr; ss; tt; ad
                    ElseIf L > 0 Or k < 20000 Then '一般性输出限制
                        jg(k, 0) = cnt '递归计算总次数
                        jg(k, 1) = Format(Timer - tms, "0.000") '计算耗时
                        jg(k, 2) = cnt1 '深度次数
                        jg(k, 3) = t '组合个数n
                        jg(k, 4) = rr 's + sj(i, 2)
                        jg(k, 5) = tt 'amt + sj(i, 3)
                        jg(k, 6) = ad 'adr & "+" & sj(i, 1)
                        If h1 Then ss = Replace(ss, "+-", "-") '含负数时
                        jg(k, 7) = ss 's & "+" & sj(i, 2)
                        If Len(ss) > l2 Then l2 = Len(ss) 'arr output Len=911
                    End If
DicExt:
                    If cnt1 > cnt2 Then cnt2 = cnt1 '更新最大深度
                    cnt1 = 0 '重置计算深度
                ElseIf t1 > r2 Then
                    Exit For
                End If
            Next
        End If
        If t = n2 Then Exit Sub '指定个数上限n2时退出
        For i = j - 1 To 2 Step -1 '降序递归检查
            If sj(i, 2) <= R + h1 + h2 Then '十进制数加入后不超过(负数h1以及和差h2) 超过剪枝退出
                If sj(i, 0) < R Then '剩余累计和不足时 剪枝退出
                    Exit For
                Else
                    Call dgH421(R - sj(i, 2), rs + sj(i, 2), s & "+" & sj(i, 2), amt + sj(i, 3), adr & "+" & sj(i, 1), i, t + 1)
                End If
            End If
        Next
    End Sub
'查看日志
Private Sub CsCmb4_Click()
    If k Then Else Me.CsTex3.Value = "当前凑数解数为零，无日志": Exit Sub
    Dim Istxt: Istxt = MsgBox("请选择输出方式：" & vbCrLf & "    [Yes]选择区域输出  [No]文本文件输出", vbYesNo, "LELEDY")
    Select Case Istxt
    Case 7
        '文本输出
        Dim Pah$: Pah = ActiveWorkbook.Path
        If InStr(Pah, "https://d.docs.live.net/") Then _
            Pah = Replace(Replace(Pah, "https://d.docs.live.net/" & Split(Pah, "/")(3), Environ("OneDrive")), "/", "\")
        Open Pah & "\" & "CouShu-ReSult" & Format(Now, "yyyymmddhhmmss") & ".txt" For Output As #1
        Print #1, "求和目标h=" & h & "；解数k=" & k & "；递归次数cnt=" & cnt & "；耗时tms=" & Format(Timer - tms, "0.000s") & vbCrLf
        For i = 0 To k
            Print #1, jg(i, 1) & "；"; jg(i, 2) & "；"; jg(i, 3) & "；"; jg(i, 4) & "；"; jg(i, 5) & "；"; jg(i, 6) & "；"; jg(i, 7) & IIf(err = 18, "Ctrl+Break ", "")
        Next
        Close #1
    Case 6
        If L > 0 Or k < 20000 Then
            On Error Resume Next
            Dim Rg As Object: Set Rg = Application.InputBox("请选择日志输出区域位置：", "LELEDY", Type:=8)
            Dim Se As Object: Set Se = Rg.Parent
            If Rg Is Nothing Then Me.CsTex3.Value = "未选择输出区域位置，已退出": Exit Sub
            Set Rg = Rg.Cells(1)
            With Se.Range(Rg.Address)
                If l2 > 911 Then '文本长度超过911时 不能进行数组输出
                    .Resize(k + 1, 8) = jg
                    For i = 1 To k
                        Se.Cells(.row - 1 + i, .Column + 7) = jg(i, 7) & IIf(err = 18, "Ctrl+Break ", "")
                    Next
                Else
                    .Resize(k + 1, 8) = jg
                End If
                .Resize(k + 1, 8).Sort [m1], 1, [l1], , 1, , , 1
            End With
            Set Rg = Nothing: Set Se = Nothing
        End If
    End Select
End Sub
'切换结果
Private Sub CsSpn2_Change()
    Me.CsCmb3.Caption = "第" & Me.CsSpn2.Value & "种"
End Sub
'标记颜色
Private Sub CsCmb3_Click()
    Call SignCell
End Sub
Private Sub SignCell()
    With She.Range(IIf(Me.Cschx1.Value, Txtv, Txtt))
        .Interior.ColorIndex = 0
        Dim Num&: Num = Replace(Replace(Me.CsCmb3.Caption, "种", ""), "第", "") + 0
        Dim Tarr: Tarr = Split(jg(Num, 6), "+")
        For i = 1 To UBound(Tarr)
            She.Range(Tarr(i)).Interior.ColorIndex = 6 & IIf(err = 18, "Ctrl+Break ", "")
        Next
    End With
End Sub

