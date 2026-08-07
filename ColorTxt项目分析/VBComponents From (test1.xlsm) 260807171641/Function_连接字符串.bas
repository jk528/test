Attribute VB_Name = "Function_Á¬½Ó×Ö·û´®"

Function ConcatCells(rng As Range, Optional delimiter As String = "") As String
    Dim cell As Range
    Dim result As String
    
    For Each cell In rng
        If cell.Value <> "" Then
            If result <> "" Then
                result = result & delimiter
            End If
            result = result & cell.Value
        End If
    Next cell
    
    ConcatCells = result
End Function

