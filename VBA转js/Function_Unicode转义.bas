Attribute VB_Name = "Function_Unicode转义"
Option Explicit

' ============================================================
' Function_Unicode转义.bas  v1.0
' 中文 ↔ Unicode 转义序列 互转
'
' 核心函数（2 个）：
'   =中文转Unicode(A1)          →  \u4E2D\u6587          （中文转义）
'   =Unicode转中文(A1)          →  中文                  （反转义还原）
'
' 设计说明：
'   - 仅转义非 ASCII 字符（>127），保留 ASCII 可读性
'   - 十六进制大写，与 JavaScript 转义风格一致
'   - 完整支持 UTF-16 代理对（emoji 等 >U+FFFF 字符）
'   - 适用于 WPS / Excel VBA（AscW / ChrW 基于 UTF-16）
'
' 与 Python 的区别：
'   Python 内置 unicode_escape 编解码器可一行完成；
'   VBA 无内置支持，需用 AscW/ChrW 手写。AscW 返回
'   UTF-16 码元（非码点），且对码元 >32767 返回负数，
'   需 +65536 修正；补充平面字符需手动配对代理对。
'
' 日期：2026-08-13
' ============================================================

' ============================================================
' 一、中文转 Unicode 转义序列
' 参数：
'   s - 原始字符串
' 返回：非 ASCII 字符转为 \uXXXX，ASCII 原样保留
' 边界：空串返回空串；代理对输出 \uXXXX\uXXXX
' ============================================================
Public Function 中文转Unicode(ByVal s As String) As String
    Dim n As Long, i As Long, idx As Long
    Dim code As Long, lo As Long
    Dim c As String
    Dim result() As String

    n = Len(s)
    If n = 0 Then
        中文转Unicode = ""
        Exit Function
    End If
    ReDim result(0 To n - 1)
    idx = 0
    i = 1
    Do While i <= n
        c = Mid$(s, i, 1)
        code = AscW(c)
        ' AscW 对码元 >32767 返回负数，需修正
        If code < 0 Then code = code + 65536
        If code >= &HD800& And code <= &HDBFF& And i < n Then
            ' 高代理：检查下一字符是否为低代理（代理对）
            lo = AscW(Mid$(s, i + 1, 1))
            If lo < 0 Then lo = lo + 65536
            If lo >= &HDC00& And lo <= &HDFFF& Then
                result(idx) = "\u" & PadHex4(code) & "\u" & PadHex4(lo)
                idx = idx + 1
                i = i + 2
            Else
                result(idx) = "\u" & PadHex4(code)
                idx = idx + 1
                i = i + 1
            End If
        ElseIf code > 127 Then
            result(idx) = "\u" & PadHex4(code)
            idx = idx + 1
            i = i + 1
        Else
            result(idx) = c
            idx = idx + 1
            i = i + 1
        End If
    Loop
    中文转Unicode = Join(result, "")
End Function

' ============================================================
' 二、Unicode 转义序列转中文
' 参数：
'   s - 含 \uXXXX 转义序列的字符串
' 返回：转义序列还原为字符，其余原样保留
' 边界：非法序列保留原字面量；支持代理对 \uD83D\uDE00
' ============================================================
Public Function Unicode转中文(ByVal s As String) As String
    Dim n As Long, pos As Long, idx As Long
    Dim code As Long, lo As Long
    Dim hexStr As String
    Dim result() As String

    n = Len(s)
    If n = 0 Then
        Unicode转中文 = ""
        Exit Function
    End If
    ReDim result(0 To n)
    idx = 0
    pos = 1
    Do While pos <= n
        If pos + 1 <= n Then
            If Mid$(s, pos, 2) = "\u" And pos + 5 <= n Then
                hexStr = Mid$(s, pos + 2, 4)
                code = HexToLong(hexStr)
                If code >= 0 Then
                    If code >= &HD800& And code <= &HDBFF& Then
                        ' 高代理：尝试配对下一个 \uXXXX 低代理
                        If pos + 11 <= n And Mid$(s, pos + 6, 2) = "\u" Then
                            lo = HexToLong(Mid$(s, pos + 8, 4))
                            If lo >= &HDC00& And lo <= &HDFFF& Then
                                result(idx) = ChrW(code) & ChrW(lo)
                                idx = idx + 1
                                pos = pos + 12
                            Else
                                result(idx) = ChrW(code)
                                idx = idx + 1
                                pos = pos + 6
                            End If
                        Else
                            result(idx) = ChrW(code)
                            idx = idx + 1
                            pos = pos + 6
                        End If
                    Else
                        result(idx) = ChrW(code)
                        idx = idx + 1
                        pos = pos + 6
                    End If
                Else
                    ' 非法十六进制，保留原字面量
                    result(idx) = Mid$(s, pos, 1)
                    idx = idx + 1
                    pos = pos + 1
                End If
            Else
                result(idx) = Mid$(s, pos, 1)
                idx = idx + 1
                pos = pos + 1
            End If
        Else
            result(idx) = Mid$(s, pos, 1)
            idx = idx + 1
            pos = pos + 1
        End If
    Loop
    Unicode转中文 = Join(result, "")
End Function

' ============================================================
' 内部：码点 → 4 位补零十六进制（大写）
' ============================================================
Private Function PadHex4(ByVal code As Long) As String
    Dim h As String
    h = Hex$(code)
    PadHex4 = String$(4 - Len(h), "0") & h
End Function

' ============================================================
' 内部：十六进制字符串 → Long，非法返回 -1
' 手动解析避免 CLng 的区域设置/异常问题，WPS 兼容
' ============================================================
Private Function HexToLong(ByVal h As String) As Long
    Dim i As Long, ch As Long, v As Long
    h = UCase$(h)
    If Len(h) = 0 Then
        HexToLong = -1
        Exit Function
    End If
    v = 0
    For i = 1 To Len(h)
        ch = Asc(Mid$(h, i, 1))
        If ch >= 48 And ch <= 57 Then
            v = v * 16 + (ch - 48)
        ElseIf ch >= 65 And ch <= 70 Then
            v = v * 16 + (ch - 55)
        Else
            HexToLong = -1
            Exit Function
        End If
    Next i
    HexToLong = v
End Function

' ============================================================
' 三、测试过程：覆盖标准场景 / 边界条件 / 往返一致
' 运行：在立即窗口执行 Test_Unicode转义，或绑定到按钮
' ============================================================
Public Sub Test_Unicode转义()
    Dim pass As Long, fail As Long
    Dim msg As String

    pass = 0
    fail = 0

    ' --- 标准场景 ---
    Check "中文转Unicode", 中文转Unicode("中文"), "\u4E2D\u6587", pass, fail
    Check "中英混合", 中文转Unicode("Hello 世界"), "Hello \u4E16\u754C", pass, fail
    Check "纯ASCII不转义", 中文转Unicode("ABC123"), "ABC123", pass, fail
    Check "高位汉字(>U+8000)", 中文转Unicode("鹤"), "\u9E64", pass, fail

    ' --- 解码还原 ---
    Check "标准解码", Unicode转中文("\u4E2D\u6587"), "中文", pass, fail
    Check "小写转义解码", Unicode转中文("\u4e2d\u6587"), "中文", pass, fail
    Check "混合文本解码", Unicode转中文("Hello \u4E16\u754C"), "Hello 世界", pass, fail
    Check "无转义原样", Unicode转中文("普通文本"), "普通文本", pass, fail

    ' --- 代理对(emoji) ---
    Check "emoji编码", 中文转Unicode("😀"), "\uD83D\uDE00", pass, fail
    Check "emoji解码", Unicode转中文("\uD83D\uDE00"), "😀", pass, fail

    ' --- 边界条件 ---
    Check "空串编码", 中文转Unicode(""), "", pass, fail
    Check "空串解码", Unicode转中文(""), "", pass, fail
    Check "非法码点保留", Unicode转中文("\uXYZW"), "\uXYZW", pass, fail

    ' --- 往返一致性 ---
    Check "往返-中文", Unicode转中文(中文转Unicode("排列组合四象限")), "排列组合四象限", pass, fail
    Check "往返-混合", Unicode转中文(中文转Unicode("C(n,k)=组合数")), "C(n,k)=组合数", pass, fail
    Check "往返-emoji", Unicode转中文(中文转Unicode("开心😀")), "开心😀", pass, fail

    ' --- 演示 ---
    msg = "通过: " & pass & "  失败: " & fail & vbCrLf & vbCrLf
    msg = msg & "=== 演示 ===" & vbCrLf
    msg = msg & "原文: 排列组合四象限：C(n,k)" & vbCrLf
    msg = msg & "编码: " & 中文转Unicode("排列组合四象限：C(n,k)") & vbCrLf
    msg = msg & "解码: " & Unicode转中文(中文转Unicode("排列组合四象限：C(n,k)"))
    MsgBox msg, vbInformation, "Unicode 转义测试 (" & IIf(fail = 0, "全部通过", "存在失败") & ")"
End Sub

' 内部：断言比较
Private Sub Check(ByVal label As String, ByVal actual As String, ByVal expected As String, ByRef pass As Long, ByRef fail As Long)
    If actual = expected Then
        pass = pass + 1
    Else
        fail = fail + 1
        Debug.Print "[FAIL] " & label & " | 期望:" & expected & " 实际:" & actual
    End If
End Sub
