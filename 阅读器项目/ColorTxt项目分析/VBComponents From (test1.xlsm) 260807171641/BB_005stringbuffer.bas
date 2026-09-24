Attribute VB_Name = "BB_005stringbuffer"


Public Sub BufferMethodsDemo()
    Dim buff As New StringBuffer
    '
    buff.Append "ABFGH"
    Debug.Print buff.Value 'ABFGH
    '
    buff.Insert 3, "CDE"
    Debug.Print buff 'ABCDEFGH
    '
    buff.Reverse
    Debug.Print buff 'HGFEDCBA
    '
    buff.Replace 2, 2, "XX"
    Debug.Print buff 'HXXEDCBA
    '
    buff.Reverse
    Debug.Print buff 'ABCDEXXH
    '
    buff.Delete 6, 2
    Debug.Print buff 'ABCDEH
    '
    Debug.Print buff.Substring(2, 3) 'BCD
End Sub
