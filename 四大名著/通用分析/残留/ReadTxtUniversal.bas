'Attribute VB_Name = "ReadTxtUniversal"
Option Explicit

'==============================================================================
' 模块名称：ReadTxtUniversal
' 功能描述：通用TXT文件读取模块，自动检测编码并读取
'   支持: ANSI(GBK) / UTF-8(含BOM) / UTF-8(无BOM) / UTF-16LE / UTF-16BE
'   参考: READ_TXTTOEXCEL.bas 的 DetectEncoding / ReadTextFileANSI 等逻辑
' 用法:
'   Dim content As String
'   content = ReadTextAuto("D:\红楼梦.txt")   ' 自动检测编码并读取
'   ' 或仅检测编码:
'   Dim enc As String
'   enc = DetectEncodingFile("D:\红楼梦.txt")  ' 返回 "ANSI" / "UTF-8 BOM" / "UTF-8" / "UTF-16LE" / "UTF-16BE"
' 工程约定：
'   - 所有Dim在过程顶部声明（WPS VBA严格性要求）
'   - 二进制读取使用原生 Open Binary（不受编码限制）
'   - ANSI 读取使用原生 Line Input（系统默认编码，中文Windows=GBK）
'   - UTF-8 读取使用 ADODB.Stream（Charset="utf-8"，自动跳过BOM）
'   - UTF-16 读取使用 FileSystemObject（TristateTrue/-1 自动处理LE/BE+BOM）
'==============================================================================

'------------------------------------------------------------------------------
' 对外接口 1：自动检测编码并读取TXT文件内容
'   filePath  源TXT完整路径
'   返回      文件全文文本（失败返回空串）
'------------------------------------------------------------------------------
Public Function ReadTextAuto(ByVal filePath As String) As String
    Dim enc As String
    enc = DetectEncodingFile(filePath)
    Select Case enc
        Case "ANSI"
            ReadTextAuto = ReadTextANSI(filePath)
        Case "UTF-8 BOM", "UTF-8"
            ReadTextAuto = ReadTextUTF8(filePath)
        Case "UTF-16LE", "UTF-16BE"
            ReadTextAuto = ReadTextUTF16(filePath)
        Case Else
            ' 未知编码，尝试UTF-8兜底
            ReadTextAuto = ReadTextUTF8(filePath)
    End Select
End Function

'------------------------------------------------------------------------------
' 对外接口 2：检测TXT文件编码（传入文件路径）
'   filePath  源TXT完整路径
'   返回      "ANSI" / "UTF-8 BOM" / "UTF-8" / "UTF-16LE" / "UTF-16BE"
'------------------------------------------------------------------------------
Public Function DetectEncodingFile(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    DetectEncodingFile = DetectEncodingBytes(fileBytes)
End Function

'------------------------------------------------------------------------------
' 检测编码（传入字节数组）
'   逻辑:
'     1. BOM 检测：FF FE = UTF-16LE; FE FF = UTF-16BE; EF BB BF = UTF-8 BOM
'     2. 无BOM时扫描前100字节，检查高位字节模式：
'        - 3字节序列 E0~EF + 80~BF + 80~BF → UTF-8
'        - 4字节序列 F0~F7 + 80~BF + 80~BF + 80~BF → UTF-8
'        - 其他高位字节 → ANSI
'     3. 全ASCII（无高位字节）→ ANSI（兼容纯英文）
'------------------------------------------------------------------------------
Public Function DetectEncodingBytes(fileBytes() As Byte) As String
    Dim i As Long, scanLen As Long, b1 As Byte

    If UBound(fileBytes) < 0 Then
        DetectEncodingBytes = "ANSI"
        Exit Function
    End If

    ' --- BOM 检测 ---
    If UBound(fileBytes) >= 1 Then
        If fileBytes(0) = &HFF And fileBytes(1) = &HFE Then
            DetectEncodingBytes = "UTF-16LE"
            Exit Function
        End If
        If fileBytes(0) = &HFE And fileBytes(1) = &HFF Then
            DetectEncodingBytes = "UTF-16BE"
            Exit Function
        End If
    End If
    If UBound(fileBytes) >= 2 Then
        If fileBytes(0) = &HEF And fileBytes(1) = &HBB And fileBytes(2) = &HBF Then
            DetectEncodingBytes = "UTF-8 BOM"
            Exit Function
        End If
    End If

    ' --- 无BOM：扫描字节模式判断 UTF-8 vs ANSI ---
    scanLen = UBound(fileBytes)
    If scanLen > 100 Then scanLen = 100

    For i = 0 To scanLen
        If fileBytes(i) > &H7F Then
            b1 = fileBytes(i)
            Select Case True
                ' 3字节UTF-8序列: E0~EF + 80~BF + 80~BF
                Case (b1 And &HF0) = &HE0
                    If i + 2 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                ' 4字节UTF-8序列: F0~F7 + 80~BF + 80~BF + 80~BF
                Case (b1 And &HF8) = &HF0
                    If i + 3 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 And _
                           (fileBytes(i + 3) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                ' 2字节UTF-8序列: C0~DF + 80~BF
                Case (b1 And &HE0) = &HC0
                    If i + 1 <= UBound(fileBytes) Then
                        If (fileBytes(i + 1) And &HC0) = &H80 Then
                            DetectEncodingBytes = "UTF-8"
                            Exit Function
                        End If
                    End If
                    DetectEncodingBytes = "ANSI"
                    Exit Function
                Case Else
                    ' 高位字节不符合UTF-8前导字节模式 → ANSI
                    DetectEncodingBytes = "ANSI"
                    Exit Function
            End Select
        End If
    Next i

    ' 全ASCII（无高位字节）→ 视为ANSI（纯英文文件两者兼容）
    DetectEncodingBytes = "ANSI"
End Function

'------------------------------------------------------------------------------
' 读取文件原始字节数组
'   filePath  源文件完整路径
'   返回      Byte数组（0-based）
'------------------------------------------------------------------------------
Public Function ReadFileBytes(ByVal filePath As String) As Byte()
    Dim fileNo As Integer
    Dim fileBytes() As Byte
    fileNo = FreeFile
    Open filePath For Binary Access Read As #fileNo
    ReDim fileBytes(0 To LOF(fileNo) - 1)
    Get #fileNo, , fileBytes
    Close #fileNo
    ReadFileBytes = fileBytes
End Function

'------------------------------------------------------------------------------
' 读取ANSI编码TXT（系统默认编码，中文Windows=GBK）
'   使用原生 Line Input 逐行读取，兼容大文件
'------------------------------------------------------------------------------
Public Function ReadTextANSI(ByVal filePath As String) As String
    Dim fileNo As Integer
    Dim lineText As String
    Dim content As String
    fileNo = FreeFile()
    Open filePath For Input As #fileNo
    Do While Not EOF(fileNo)
        Line Input #fileNo, lineText
        If Len(content) = 0 Then
            content = lineText
        Else
            content = content & vbCrLf & lineText
        End If
    Loop
    Close #fileNo
    ReadTextANSI = content
End Function

'------------------------------------------------------------------------------
' 读取UTF-8编码TXT（ADODB.Stream，自动处理有无BOM）
'------------------------------------------------------------------------------
Public Function ReadTextUTF8(ByVal filePath As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile filePath
    ReadTextUTF8 = stm.ReadText(-1)   ' adReadAll
    stm.Close
End Function

'------------------------------------------------------------------------------
' 读取UTF-16编码TXT（FileSystemObject TristateTrue，自动处理LE/BE+BOM）
'------------------------------------------------------------------------------
Public Function ReadTextUTF16(ByVal filePath As String) As String
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(filePath, 1, False, -1)  ' -1 = TristateTrue(Unicode)
    ReadTextUTF16 = ts.ReadAll
    ts.Close
End Function

'------------------------------------------------------------------------------
' 写入UTF-8文本（无BOM）
'   ADODB.Stream 默认写3字节BOM，需切二进制模式裁掉
'------------------------------------------------------------------------------
Public Sub WriteTextUTF8NoBOM(ByVal filePath As String, ByVal text As String)
    Dim stm As Object, bin As Variant
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText text
    ' 切二进制模式剥离BOM
    stm.Position = 0
    stm.Type = 1          ' adTypeBinary
    stm.Position = 3      ' 跳过 UTF-8 BOM (EF BB BF)
    bin = stm.Read
    stm.Close
    ' 干净二进制流写出
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 1          ' adTypeBinary
    stm.Open
    stm.Write bin
    stm.SaveToFile filePath, 2    ' adSaveCreateOverWrite
    stm.Close
End Sub

'------------------------------------------------------------------------------
' 写入ANSI编码文本（系统默认编码，中文Windows=GBK）
'------------------------------------------------------------------------------
Public Sub WriteTextANSI(ByVal filePath As String, ByVal text As String)
    Dim fileNo As Integer
    fileNo = FreeFile()
    Open filePath For Output As #fileNo
    Print #fileNo, text;
    Close #fileNo
End Sub

'------------------------------------------------------------------------------
' 写入UTF-8文本（含BOM）
'------------------------------------------------------------------------------
Public Sub WriteTextUTF8BOM(ByVal filePath As String, ByVal text As String)
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2          ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText text
    stm.SaveToFile filePath, 2    ' adSaveCreateOverWrite（含BOM）
    stm.Close
End Sub
