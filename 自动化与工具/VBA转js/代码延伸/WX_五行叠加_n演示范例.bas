Attribute VB_Name = "modWX_Overlay"
'============================================================
' 五行生克叠加模型 · n 位演示范例
' 作者: 推导生成  日期: 2026-11-22
'
' 【模型】
'   n 个节点编号 0..n-1。
'   一层 = 一个排列 L(i) = (k*i + c) mod n，其中 k 与 n 互质（保证是单一 n-环），
'        c 为旋转偏移 (0..n-1)。每层共 n*φ(n) 种排法。
'   两层叠加：对每个位置 i，比较下层值 L_b(i) 与上层值 L_a(i) 的差
'        d_i = (L_b(i) - L_a(i)) mod n，得到一个长度为 n 的「签名」。
'   关系：d=0 同；d=±1 生/被生；d=±2 克/被克；其余 d 为扩展关系。
'
' 【用法】
'   1. Excel 按 Alt+F11 打开 VBA 编辑器
'   2. 菜单 插入 → 模块，粘贴本文件全部内容
'   3. 光标放在 WX_叠加演示 内，按 F5 运行
'   4. 输入 n（五行=5，建议 2~11；n 越大组合数增长越快）
'   5. 自动生成三个工作表：层定义、组合明细、签名汇总
'============================================================
Option Explicit

Private m_n As Integer
Private m_labels() As String   ' 关系标签数组，下标 = 差 d
Private m_nodeName() As String ' 节点名称

'---------------- 主入口 ----------------
Public Sub WX_叠加演示()
    Dim n As Variant
    n = Application.InputBox("请输入 n（五行=5，建议 2~11）：", "五行生克叠加演示", 5, Type:=1)
    If VarType(n) = vbBoolean Then Exit Sub   ' 取消
    If n < 2 Or n > 15 Then
        MsgBox "n 必须在 2~15 之间。", vbExclamation
        Exit Sub
    End If
    GenerateDemo CInt(n)
End Sub

'---------------- 核心生成 ----------------
Public Sub GenerateDemo(n As Integer)
    m_n = n
    BuildLabels n
    BuildNodeNames n

    ' 1. 生成所有层
    Dim layers() As Long, perLayer As Long
    layers = BuildLayers(n, perLayer)
    Dim combos As Long: combos = perLayer * perLayer

    ' 2. 输出层定义表
    DumpLayerTable layers, perLayer, n

    ' 3. 统计签名（用字典）
    Dim dict As Object: Set dict = CreateObject("Scripting.Dictionary")
    Dim sig As String, i As Long, j As Long, a As Long, b As Long
    For i = 0 To perLayer - 1
        For j = 0 To perLayer - 1
            sig = SignatureOf(layers, i, j, n)
            If dict.Exists(sig) Then
                dict(sig) = dict(sig) + 1
            Else
                dict.Add sig, 1
            End If
        Next j
    Next i

    ' 4. 输出签名汇总
    DumpSignatureSummary dict, n

    ' 5. 输出组合明细（组合数过大时只给计数，避免卡顿）
    If combos <= 3000 Then
        DumpComboDetail layers, perLayer, n
    Else
        DumpComboCount combos, dict.Count, n
    End If

    MsgBox "完成！n=" & n & vbCrLf & _
           "每层排法: " & perLayer & vbCrLf & _
           "两层组合: " & combos & vbCrLf & _
           "独特签名: " & dict.Count, vbInformation, "五行叠加演示"
End Sub

'---------------- 辅助：标签 ----------------
Private Sub BuildLabels(n As Integer)
    ReDim m_labels(0 To n - 1)
    If n = 5 Then
        ' 五行专用中文标签（d = 下层值 - 上层值 mod 5）：
        ' d=0同, d=1被生(X生Y), d=2被克(X克Y), d=3克(Y克X), d=4生(Y生X)
        m_labels(0) = "同": m_labels(1) = "被生": m_labels(2) = "被克"
        m_labels(3) = "克": m_labels(4) = "生"
    Else
        ' 通用：d=0同，其余按 d 命名（成对互逆）
        m_labels(0) = "同"
        Dim d As Integer
        For d = 1 To n - 1
            If d <= n \ 2 Then
                m_labels(d) = "R" & d          ' 正向关系
            Else
                m_labels(d) = "R'" & (n - d)   ' 逆向关系
            End If
        Next d
    End If
End Sub

Private Sub BuildNodeNames(n As Integer)
    ReDim m_nodeName(0 To n - 1)
    If n = 5 Then
        m_nodeName(0) = "木": m_nodeName(1) = "火": m_nodeName(2) = "土"
        m_nodeName(3) = "金": m_nodeName(4) = "水"
    Else
        Dim i As Integer
        For i = 0 To n - 1: m_nodeName(i) = CStr(i): Next i
    End If
End Sub

'---------------- 辅助：数学 ----------------
Private Function GCD(ByVal a As Long, ByVal b As Long) As Long
    Do While b <> 0
        Dim t As Long: t = b: b = a Mod b: a = t
    Loop
    GCD = a
End Function

Private Function Phi(n As Integer) As Long
    Dim i As Long, c As Long
    For i = 1 To n
        If GCD(i, n) = 1 Then c = c + 1
    Next i
    Phi = c
End Function

' 安全的模运算（结果恒为 0..n-1）
Private Function ModN(ByVal x As Long, ByVal n As Integer) As Long
    ModN = ((x Mod n) + n) Mod n
End Function

'---------------- 生成所有层 ----------------
' 返回二维数组 layers(idx, 0)=k, layers(idx,1)=c；perLayer 为总数
Private Function BuildLayers(n As Integer, ByRef perLayer As Long) As Long()
    Dim k As Integer, c As Integer
    perLayer = 0
    ' 先计数
    For k = 1 To n - 1
        If GCD(k, n) = 1 Then perLayer = perLayer + n
    Next k
    Dim arr() As Long: ReDim arr(0 To perLayer - 1, 0 To 1)
    Dim idx As Long: idx = 0
    For k = 1 To n - 1
        If GCD(k, n) = 1 Then
            For c = 0 To n - 1
                arr(idx, 0) = k: arr(idx, 1) = c
                idx = idx + 1
            Next c
        End If
    Next k
    BuildLayers = arr
End Function

' 层 idx 在位置 i 的值
Private Function LayerVal(layers() As Long, idx As Long, i As Integer, n As Integer) As Long
    LayerVal = ModN(layers(idx, 0) * i + layers(idx, 1), n)
End Function

'---------------- 签名计算 ----------------
Private Function SignatureOf(layers() As Long, ia As Long, ib As Long, n As Integer) As String
    Dim i As Integer, d As Long
    Dim s As String: s = ""
    For i = 0 To n - 1
        d = ModN(LayerVal(layers, ib, i, n) - LayerVal(layers, ia, i, n), n)
        s = s & m_labels(d) & " "
    Next i
    SignatureOf = Left(s, Len(s) - 1)
End Function

' 判断签名类别：齐同 / 齐备 / 普通
Private Function SigCategory(layers() As Long, ia As Long, ib As Long, n As Integer) As String
    Dim i As Integer, d As Long, first As Long, cnt As Long
    first = -1: cnt = 0
    Dim seen As Object: Set seen = CreateObject("Scripting.Dictionary")
    For i = 0 To n - 1
        d = ModN(LayerVal(layers, ib, i, n) - LayerVal(layers, ia, i, n), n)
        If Not seen.Exists(d) Then seen.Add d, 1
    Next i
    If seen.Count = 1 Then
        SigCategory = "齐同"
    ElseIf seen.Count = n Then
        SigCategory = "齐备"
    Else
        SigCategory = "普通"
    End If
End Function

'---------------- 输出：层定义表 ----------------
Private Sub DumpLayerTable(layers() As Long, perLayer As Long, n As Integer)
    Dim ws As Worksheet
    Set ws = NewSheet("层定义_n" & n)
    ws.Cells(1, 1) = "层编号": ws.Cells(1, 2) = "步长k": ws.Cells(1, 3) = "偏移c"
    Dim j As Integer
    For j = 0 To n - 1: ws.Cells(1, 4 + j) = "位" & (j + 1): Next j
    Dim r As Long, i As Integer
    For r = 0 To perLayer - 1
        ws.Cells(r + 2, 1) = r + 1
        ws.Cells(r + 2, 2) = layers(r, 0)
        ws.Cells(r + 2, 3) = layers(r, 1)
        For i = 0 To n - 1
            ws.Cells(r + 2, 4 + i) = m_nodeName(LayerVal(layers, r, i, n))
        Next i
    Next r
    ws.Range(ws.Cells(1, 1), ws.Cells(perLayer + 1, 3 + n)).Columns.AutoFit
    ws.Rows(1).Font.Bold = True
End Sub

'---------------- 输出：签名汇总 ----------------
Private Sub DumpSignatureSummary(dict As Object, n As Integer)
    Dim ws As Worksheet
    Set ws = NewSheet("签名汇总_n" & n)
    ws.Cells(1, 1) = "签名": ws.Cells(1, 2) = "出现次数": ws.Cells(1, 3) = "态"
    Dim r As Long: r = 2
    Dim key As Variant
    For Each key In dict.Keys
        ws.Cells(r, 1) = key
        ws.Cells(r, 2) = dict(key)
        ' 判定态：按空格分割，数唯一标签数
        Dim parts() As String: parts = Split(key, " ")
        Dim seen As Object: Set seen = CreateObject("Scripting.Dictionary")
        Dim p As Integer
        For p = 0 To UBound(parts): If Not seen.Exists(parts(p)) Then seen.Add parts(p), 1: Next p
        If seen.Count = 1 Then
            ws.Cells(r, 3) = "齐同"
        ElseIf seen.Count = n Then
            ws.Cells(r, 3) = "齐备"
        Else
            ws.Cells(r, 3) = "普通"
        End If
        r = r + 1
    Next key
    ws.Range(ws.Cells(1, 1), ws.Cells(r - 1, 3)).Sort Key1:=ws.Range("C1"), Order1:=xlAscending, Key2:=ws.Range("B1"), Order1:=xlDescending, Header:=xlYes
    ws.Columns.AutoFit: ws.Rows(1).Font.Bold = True
End Sub

'---------------- 输出：组合明细 ----------------
Private Sub DumpComboDetail(layers() As Long, perLayer As Long, n As Integer)
    Dim ws As Worksheet
    Set ws = NewSheet("组合明细_n" & n)
    ws.Cells(1, 1) = "序号": ws.Cells(1, 2) = "上层": ws.Cells(1, 3) = "下层"
    Dim j As Integer
    For j = 0 To n - 1: ws.Cells(1, 4 + j) = "位" & (j + 1): Next j
    ws.Cells(1, 4 + n) = "签名": ws.Cells(1, 5 + n) = "态"
    Dim r As Long: r = 2: Dim no As Long: no = 0
    Dim i As Long, jj As Long, d As Long
    For i = 0 To perLayer - 1
        For jj = 0 To perLayer - 1
            no = no + 1
            ws.Cells(r, 1) = no: ws.Cells(r, 2) = i + 1: ws.Cells(r, 3) = jj + 1
            For j = 0 To n - 1
                d = ModN(LayerVal(layers, jj, j, n) - LayerVal(layers, i, j, n), n)
                ws.Cells(r, 4 + j) = m_labels(d)
            Next j
            ws.Cells(r, 4 + n) = SignatureOf(layers, i, jj, n)
            ws.Cells(r, 5 + n) = SigCategory(layers, i, jj, n)
            r = r + 1
        Next jj
    Next i
    ws.Columns.AutoFit: ws.Rows(1).Font.Bold = True
End Sub

'---------------- 输出：组合计数（组合过大时） ----------------
Private Sub DumpComboCount(combos As Long, sigCount As Long, n As Integer)
    Dim ws As Worksheet
    Set ws = NewSheet("组合统计_n" & n)
    ws.Cells(1, 1) = "n": ws.Cells(1, 2) = n
    ws.Cells(2, 1) = "每层排法": ws.Cells(2, 2) = Sqr(combos)
    ws.Cells(3, 1) = "两层组合总数": ws.Cells(3, 2) = combos
    ws.Cells(4, 1) = "独特签名数": ws.Cells(4, 2) = sigCount
    ws.Cells(6, 1) = "注：组合数 > 3000，未输出明细行。" & _
                     "如需查看明细，请在 DumpComboDetail 中调整阈值，或缩小 n。"
    ws.Columns.AutoFit
End Sub

'---------------- 工具：新建工作表 ----------------
Private Function NewSheet(name As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Application.DisplayAlerts = False
    ThisWorkbook.Sheets(name).Delete
    Application.DisplayAlerts = True
    On Error GoTo 0
    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
    ws.name = name
    Set NewSheet = ws
End Function
