Attribute VB_Name = "modEncoding"
Option Explicit

'==============================================================================
' Phase 0: TXT 编码自动检测与读取
'   改编自 splittxt3 (split_txt_v3.bas) 的编码检测逻辑
'   支持: ANSI / UTF-8(BOM/无BOM) / UTF-16LE / UTF-16BE 自动识别
'   优化: 三段采样检测 + BOM 优先 + 连续字节序列验证
'==============================================================================

'------------------------------------------------------------------------------
' 公开接口: 检测文件编码
'------------------------------------------------------------------------------
Public Function DetectEncoding(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    DetectEncoding = DetectEncodingFromBytes(fileBytes)
End Function

'------------------------------------------------------------------------------
' 从字节数组检测编码
'   策略: BOM标记 → 三段采样(头/中/尾各100字节) → 默认ANSI
'------------------------------------------------------------------------------
Public Function DetectEncodingFromBytes(fileBytes() As Byte) As String
    Dim totalLen As Long, scanLen As Long
    Dim result As String
    
    If UBound(fileBytes) < 0 Then
        DetectEncodingFromBytes = "ANSI"
        Exit Function
    End If
    
    totalLen = UBound(fileBytes) + 1
    
    ' 1. BOM 检测（最高优先级）
    If UBound(fileBytes) >= 1 Then
        If fileBytes(0) = &HFF And fileBytes(1) = &HFE Then
            DetectEncodingFromBytes = "UTF-16LE": Exit Function
        End If
        If fileBytes(0) = &HFE And fileBytes(1) = &HFF Then
            DetectEncodingFromBytes = "UTF-16BE": Exit Function
        End If
    End If
    If UBound(fileBytes) >= 2 Then
        If fileBytes(0) = &HEF And fileBytes(1) = &HBB And fileBytes(2) = &HBF Then
            DetectEncodingFromBytes = "UTF-8-BOM": Exit Function
        End If
    End If
    
    ' 2. 三段采样检测
    scanLen = 100
    If totalLen < scanLen * 3 Then
        ' 文件太小，一次扫描全部
        result = ScanBytesForEnc(fileBytes, 0, UBound(fileBytes))
        If Len(result) > 0 Then DetectEncodingFromBytes = result Else DetectEncodingFromBytes = "ANSI"
        Exit Function
    End If
    
    ' 头部采样
    result = ScanBytesForEnc(fileBytes, 0, scanLen - 1)
    If Len(result) > 0 Then DetectEncodingFromBytes = result: Exit Function
    
    ' 中部采样
    Dim midStart As Long
    midStart = (totalLen \ 2) - (scanLen \ 2)
    If midStart < scanLen Then midStart = scanLen
    result = ScanBytesForEnc(fileBytes, midStart, midStart + scanLen - 1)
    If Len(result) > 0 Then DetectEncodingFromBytes = result: Exit Function
    
    ' 尾部采样
    result = ScanBytesForEnc(fileBytes, totalLen - scanLen, UBound(fileBytes))
    If Len(result) > 0 Then DetectEncodingFromBytes = result: Exit Function
    
    ' 3. 默认 ANSI（可能是 GBK/GB2312/GB18030）
    DetectEncodingFromBytes = "ANSI"
End Function

'------------------------------------------------------------------------------
' 扫描字节段判断编码
'   原理: 检查高位字节(>0x7F)的后续字节是否符合 UTF-8 多字节序列规则
'------------------------------------------------------------------------------
Private Function ScanBytesForEnc(fileBytes() As Byte, _
        ByVal startIdx As Long, ByVal endIdx As Long) As String
    Dim i As Long, b1 As Byte, ub As Long
    ub = UBound(fileBytes)
    If startIdx < 0 Then startIdx = 0
    If endIdx > ub Then endIdx = ub
    If startIdx > endIdx Then Exit Function
    
    For i = startIdx To endIdx
        If fileBytes(i) > &H7F Then
            b1 = fileBytes(i)
            ' 跳过 UTF-8 连续字节 (10xxxxxx)
            If (b1 And &HC0) = &H80 Then GoTo NextByte
            
            Select Case True
                ' 3字节序列 (1110xxxx)
                Case (b1 And &HF0) = &HE0
                    If i + 2 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 Then
                            ScanBytesForEnc = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEnc = "ANSI": Exit Function
                    
                ' 4字节序列 (11110xxx)
                Case (b1 And &HF8) = &HF0
                    If i + 3 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 And _
                           (fileBytes(i + 2) And &HC0) = &H80 And _
                           (fileBytes(i + 3) And &HC0) = &H80 Then
                            ScanBytesForEnc = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEnc = "ANSI": Exit Function
                    
                ' 2字节序列 (110xxxxx)
                Case (b1 And &HE0) = &HC0
                    If i + 1 <= ub Then
                        If (fileBytes(i + 1) And &HC0) = &H80 Then
                            ScanBytesForEnc = "UTF-8": Exit Function
                        End If
                    End If
                    ScanBytesForEnc = "ANSI": Exit Function
                    
                Case Else
                    ScanBytesForEnc = "ANSI": Exit Function
            End Select
        End If
NextByte:
    Next i
End Function

'==============================================================================
' 文件读写函数
'==============================================================================

' 读取文件全部字节
Public Function ReadFileBytes(ByVal filePath As String) As Byte()
    Dim fileNo As Integer
    fileNo = FreeFile
    Open filePath For Binary Access Read As #fileNo
    ReDim ReadFileBytes(0 To LOF(fileNo) - 1)
    Get #fileNo, , ReadFileBytes
    Close #fileNo
End Function

' 自动检测编码并读取文本
Public Function ReadTextAuto(ByVal filePath As String) As String
    Dim enc As String
    enc = DetectEncoding(filePath)
    Select Case enc
        Case "ANSI":     ReadTextAuto = ReadTextANSI(filePath)
        Case "UTF-8-BOM", "UTF-8": ReadTextAuto = ReadTextUTF8(filePath)
        Case "UTF-16LE", "UTF-16BE": ReadTextAuto = ReadTextUTF16(filePath)
        Case Else:       ReadTextAuto = ReadTextUTF8(filePath)
    End Select
End Function

' ANSI (GBK/GB2312/GB18030) 读取
Public Function ReadTextANSI(ByVal filePath As String) As String
    Dim fileBytes() As Byte
    fileBytes = ReadFileBytes(filePath)
    If UBound(fileBytes) < 0 Then Exit Function
    ReadTextANSI = StrConv(fileBytes, vbUnicode)
End Function

' UTF-8 读取 (ADODB.Stream, 自动处理 BOM)
Public Function ReadTextUTF8(ByVal filePath As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile filePath
    ReadTextUTF8 = stm.ReadText(-1)
    stm.Close
    Set stm = Nothing
End Function

' UTF-16 读取 (FileSystemObject, -1 = TristateUseDefault)
Public Function ReadTextUTF16(ByVal filePath As String) As String
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(filePath, 1, False, -1)
    ReadTextUTF16 = ts.ReadAll
    ts.Close
    Set ts = Nothing
    Set fso = Nothing
End Function

' UTF-8 无 BOM 写入
Public Sub WriteTextUTF8NoBOM(ByVal filePath As String, ByVal text As String)
    Dim stm As Object, bin As Variant
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText text
    stm.Position = 0
    stm.Type = 1
    stm.Position = 3  ' 跳过 BOM (3字节)
    bin = stm.Read
    stm.Close
    Set stm = Nothing
    
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 1
    stm.Open
    stm.Write bin
    stm.SaveToFile filePath, 2
    stm.Close
    Set stm = Nothing
End Sub

' 获取文件编码的中文说明
Public Function GetEncodingName(ByVal enc As String) As String
    Select Case enc
        Case "ANSI":     GetEncodingName = "ANSI/GBK (中文编码)"
        Case "UTF-8":    GetEncodingName = "UTF-8 (无BOM)"
        Case "UTF-8-BOM": GetEncodingName = "UTF-8 (含BOM)"
        Case "UTF-16LE": GetEncodingName = "UTF-16LE (小端)"
        Case "UTF-16BE": GetEncodingName = "UTF-16BE (大端)"
        Case Else:       GetEncodingName = enc
    End Select
End Function
