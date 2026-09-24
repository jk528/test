Attribute VB_Name = "D_CatalogJump"
'目录点击跳转功能的完整标准模块代码 (复制到标准模块中)

'
' 全局变量，用于存储目录匹配结果
Public g_catalogArray As Variant
Public g_matchArray As Variant
'
' 获取目录项数组
Function GetCatalogItems() As Variant
    Dim wsCatalog As Worksheet, wsData As Worksheet
    Dim irowCatalog As Long, irowData As Long
    Dim arCatalog As Variant, arData As Variant
    Dim i As Long, j As Long, k As Long
    Dim catalogTerm As String
    Dim matchCount As Long
    Dim resultArray() As Variant
    
    ' 设置工作表对象
    Set wsCatalog = Sheets("目录")
    Set wsData = Sheets("数据源")
    
    ' 获取目录数据（A5到最下层连续非空单元格）
    irowCatalog = wsCatalog.Cells(wsCatalog.rows.count, "A").End(xlUp).row
    If irowCatalog < 5 Then
        GetCatalogItems = Empty
        Exit Function
    End If
    
    arCatalog = wsCatalog.Range("A5:A" & irowCatalog).Value
    
    ' 获取数据源数据
    irowData = wsData.Cells(wsData.rows.count, "A").End(xlUp).row
    If irowData < 2 Then
        GetCatalogItems = Empty
        Exit Function
    End If
    
    arData = wsData.Range("A1:A" & irowData).Value
    
    ' 统计匹配数量
    matchCount = 0
    For i = 1 To UBound(arCatalog, 1)
        catalogTerm = arCatalog(i, 1)
        If catalogTerm <> "" Then
            ' 在数据源中查找匹配项
            For j = 1 To UBound(arData, 1)
                If LCase(arData(j, 1)) = LCase(catalogTerm) Then
                    matchCount = matchCount + 1
                    Exit For
                End If
            Next j
        End If
    Next i
    
    ' 创建结果数组
    If matchCount = 0 Then
        GetCatalogItems = Empty
        Exit Function
    End If
    
    ReDim resultArray(1 To matchCount, 1 To 3)
    
    ' 填充结果数组
    k = 1
    For i = 1 To UBound(arCatalog, 1)
        catalogTerm = arCatalog(i, 1)
        If catalogTerm <> "" Then
            ' 在数据源中查找匹配项
            For j = 1 To UBound(arData, 1)
                If LCase(arData(j, 1)) = LCase(catalogTerm) Then
                    resultArray(k, 1) = catalogTerm ' Catalog Term
                    resultArray(k, 2) = arData(j, 1) ' Data Source Term
                    resultArray(k, 3) = j ' RowIndex (实际行号)
                    k = k + 1
                    Exit For
                End If
            Next j
        End If
    Next i
    
    GetCatalogItems = resultArray
End Function
'
' 处理目录匹配结果
Sub ProcessCatalogResult(catalogArray As Variant)
    Dim wsData As Worksheet
    
    Set wsData = Sheets("数据源")
    
    ' 根据匹配结果数量决定操作
    Select Case UBound(catalogArray, 1)
        Case 1
            ' 只有一个匹配结果，跳转到对应位置
            wsData.Activate
            wsData.Cells(catalogArray(1, 3), 1).Select
            MsgBox "已跳转到目录项对应位置！", vbInformation, "跳转成功"
        Case Else
            ' 多个匹配结果，显示选择窗体
            ' 存储匹配结果到全局变量
            g_catalogArray = catalogArray
            ' 显示匹配结果窗体
            UserForm4.Show 0
    End Select
End Sub
'
' 初始化宏 - 目录点击跳转
Sub InitializeCatalogJump()
    Dim catalogArray As Variant
    
    ' 获取目录匹配结果
    catalogArray = GetCatalogItems()
    
    ' 根据匹配结果决定操作
    If IsEmpty(catalogArray) Then
        ' 无匹配，显示提示
        MsgBox "未找到匹配的目录项！", vbInformation, "目录结果"
    Else
        ' 处理目录匹配结果
        ProcessCatalogResult catalogArray
    End If
End Sub

