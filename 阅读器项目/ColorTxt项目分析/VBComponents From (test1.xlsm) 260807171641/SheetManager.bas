Attribute VB_Name = "SheetManager"
' 页面管理模块 - 按分类组织工作表

' 页面分类常量定义
Public Const CATEGORY_DEV As String = "开发"
Public Const CATEGORY_READ As String = "阅读"
Public Const CATEGORY_ANALYZE As String = "分析"
Public Const CATEGORY_TYPE As String = "打字"
Public Const CATEGORY_COMMON As String = "常识"
Public Const CATEGORY_OTHER As String = "其他"

' 页面常量定义 - 开发类
Public Const PAGE_HOME As String = "首页"
Public Const PAGE_NOTIFY As String = "通知"
Public Const PAGE_VAR_MANAGER As String = "变量管理器"
Public Const PAGE_VERSION As String = "版本"
Public Const PAGE_TEST As String = "测试"

' 页面常量定义 - 阅读类
Public Const PAGE_QUERY As String = "查询"
Public Const PAGE_DATA_SOURCE As String = "数据源"
Public Const PAGE_CATALOG As String = "目录"
Public Const PAGE_px As String = "目录2"
Public Const PAGE_cf As String = "重复字"
' 页面常量定义 - 分析类
Public Const PAGE_SORT As String = "排序"
Public Const PAGE_CATALOG_DETAIL As String = "对应目录详细"
Public Const PAGE_WORD_FREQ As String = "词频"
Public Const PAGE_DUPLICATE As String = "重复字"
Public Const PAGE_HIGHLIGHT As String = "标红"

' 页面常量定义 - 打字类
Public Const PAGE_TYPE_PAGE As String = "打字页面"
Public Const PAGE_TYPE_DB As String = "打字数据库"
Public Const PAGE_TYPE_STATS As String = "码字数据统计"

' 页面常量定义 - 常识类
Public Const PAGE_FIVE_ELEMENTS As String = "五行"
Public Const PAGE_REGEX As String = "正则"
Public Const PAGE_LEGEND As String = "图例"

' 开发者工具页面
Public Const PAGE_DEV_TOOLS As String = "开发者工具"

' 获取指定分类的页面数组
Function GetCategoryPages(category As String) As Variant
    Dim pages() As Variant
    
    Select Case category
        Case CATEGORY_DEV
            pages = Array(PAGE_HOME, PAGE_NOTIFY, PAGE_VAR_MANAGER, PAGE_VERSION, PAGE_TEST, PAGE_DEV_TOOLS)
        Case CATEGORY_READ
            pages = Array(PAGE_DATA_SOURCE, PAGE_QUERY, PAGE_SORT, PAGE_CATALOG, PAGE_cf, PAGE_px)
        Case CATEGORY_ANALYZE
            pages = Array(PAGE_SORT, PAGE_CATALOG, PAGE_CATALOG_DETAIL, PAGE_WORD_FREQ, PAGE_DUPLICATE, PAGE_HIGHLIGHT)
        Case CATEGORY_TYPE
            pages = Array(PAGE_TYPE_PAGE, PAGE_TYPE_DB, PAGE_TYPE_STATS)
        Case CATEGORY_COMMON
            pages = Array(PAGE_FIVE_ELEMENTS, PAGE_REGEX, PAGE_LEGEND)
        Case Else
            pages = Array() ' 空数组
    End Select
    
    GetCategoryPages = pages
End Function

' 获取所有已定义的页面数组
Function GetAllDefinedPages() As Variant
    Dim allPages() As Variant
    Dim devPages() As Variant, readPages() As Variant, analyzePages() As Variant
    Dim typePages() As Variant, commonPages() As Variant
    Dim totalCount As Integer, i As Integer, j As Integer
    
    ' 获取各分类页面
    devPages = GetCategoryPages(CATEGORY_DEV)
    readPages = GetCategoryPages(CATEGORY_READ)
    analyzePages = GetCategoryPages(CATEGORY_ANALYZE)
    typePages = GetCategoryPages(CATEGORY_TYPE)
    commonPages = GetCategoryPages(CATEGORY_COMMON)
    
    ' 计算总页数
    totalCount = UBound(devPages) + 1 + UBound(readPages) + 1 + UBound(analyzePages) + 1 + _
                 UBound(typePages) + 1 + UBound(commonPages) + 1
    
    ' 重新分配数组大小
    ReDim allPages(totalCount - 1)
    
    ' 复制各分类页面到总数组
    j = 0
    For i = 0 To UBound(devPages)
        allPages(j) = devPages(i)
        j = j + 1
    Next
    
    For i = 0 To UBound(readPages)
        allPages(j) = readPages(i)
        j = j + 1
    Next
    
    For i = 0 To UBound(analyzePages)
        allPages(j) = analyzePages(i)
        j = j + 1
    Next
    
    For i = 0 To UBound(typePages)
        allPages(j) = typePages(i)
        j = j + 1
    Next
    
    For i = 0 To UBound(commonPages)
        allPages(j) = commonPages(i)
        j = j + 1
    Next
    
    GetAllDefinedPages = allPages
End Function

' 创建已定义页面的字典
Function CreateDefinedPagesDictionary() As Object
    Dim definedPages As Object
    Dim allPages As Variant
    Dim pageName As Variant
    
    Set definedPages = CreateObject("Scripting.Dictionary")
    allPages = GetAllDefinedPages()
    
    ' 添加所有已定义的页面名称到字典
    For Each pageName In allPages
        definedPages(pageName) = True
    Next
    
    Set CreateDefinedPagesDictionary = definedPages
End Function

' 显示一（显示指定分类的页面，隐藏其他页面到底层）
Sub ShowCategory(category As String)

    Application.ScreenUpdating = False
    Dim ws As Worksheet
    Dim categoryPages As Variant
    Dim showPages As Object
    Dim hasVisibleSheet As Boolean
    
    ' 创建字典用于快速查找
    Set showPages = CreateObject("Scripting.Dictionary")
    categoryPages = GetCategoryPages(category)
    
    ' 将需要显示的页面添加到字典
    For Each pageName In categoryPages
        showPages(pageName) = True
    Next
    ShowAllPages
    ' 处理所有工作表
    For Each ws In ThisWorkbook.Worksheets
        If showPages.exists(ws.Name) Then
            ' 显示页面
            ws.Visible = xlSheetVisible
            hasVisibleSheet = True
        Else
            ' 隐藏到最底层
            ws.Visible = xlSheetVeryHidden
        End If
    Next
    

    
    ' 激活第一个页面（如果存在）
    If showPages.count > 0 And SheetExists(categoryPages(0)) Then
        ThisWorkbook.Worksheets(categoryPages(0)).Activate
    End If
    
  Application.ScreenUpdating = True
End Sub

' 显示全部页面
Sub ShowAllPages()
    On Error Resume Next
    
    Dim ws As Worksheet
    
    ' 显示所有工作表
    For Each ws In ThisWorkbook.Worksheets
        ws.Visible = xlSheetVisible
    Next
    
    ' 激活首页（如果存在）
    If SheetExists(PAGE_HOME) Then
        ThisWorkbook.Worksheets(PAGE_HOME).Activate
    ElseIf ThisWorkbook.Worksheets.count > 0 Then
        ThisWorkbook.Worksheets(1).Activate
    End If
    
    On Error GoTo 0
End Sub

' 显示其他分类的工作表（非已定义常量的页面）
Sub ShowOtherPages()
    On Error Resume Next
    
    Dim ws As Worksheet
    Dim definedPages As Object
    Dim hasVisibleSheet As Boolean
    
    ' 创建已定义页面的字典
    Set definedPages = CreateDefinedPagesDictionary()
    
    ' 隐藏已定义的页面，显示其他页面
    For Each ws In ThisWorkbook.Worksheets
        If definedPages.exists(ws.Name) Then
            ' 隐藏已定义的页面
            ws.Visible = xlSheetVeryHidden
        Else
            ' 显示其他页面
            ws.Visible = xlSheetVisible
            hasVisibleSheet = True
        End If
    Next
    
    ' 确保始终显示开发者工具页面
    If SheetExists(PAGE_DEV_TOOLS) Then
        ThisWorkbook.Worksheets(PAGE_DEV_TOOLS).Visible = xlSheetVisible
        hasVisibleSheet = True
    End If
    
    ' 激活第一个可见页面
    If hasVisibleSheet Then
        For Each ws In ThisWorkbook.Worksheets
            If ws.Visible = xlSheetVisible Then
                ws.Activate
                Exit For
            End If
        Next
    End If
    
    On Error GoTo 0
End Sub

' 初始化一（初始化指定分类的所有页面）
Sub InitializeCategory(category As String)
    On Error Resume Next
    
    Dim pages As Variant
    Dim pageName
    Dim ws As Worksheet
    
    pages = GetCategoryPages(category)
    
    For Each pageName In pages
        If Not SheetExists(pageName) Then
            ' 创建新工作表
            Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.count))
            ws.Name = pageName
        Else
            Set ws = ThisWorkbook.Worksheets(pageName)
        End If
        
        ' 初始化工作表内容
        InitializeSheet ws
    Next
    
    On Error GoTo 0
End Sub

' 初始化工作表内容
Sub InitializeSheet(ws As Worksheet)
    On Error Resume Next
    
    ' 清空工作表内容
    ws.Cells.Clear
    
    Select Case ws.Name
        ' 开发类页面
        Case PAGE_HOME
            With ws
                .Cells(1, 1).Value = "首页"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "系统首页功能说明："
                .Cells(4, 1).Value = "- 快速访问各功能模块"
                .Cells(5, 1).Value = "- 查看系统通知"
                .Cells(6, 1).Value = "- 管理系统设置"
            End With
            
        Case PAGE_NOTIFY
            With ws
                .Cells(1, 1).Value = "通知"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "通知列表："
                .Cells(4, 1).Value = "标题"
                .Cells(4, 2).Value = "内容"
                .Cells(4, 3).Value = "时间"
                .Range("A4:C4").Font.Bold = True
                .Range("A4:C4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_VAR_MANAGER
            With ws
                .Cells(1, 1).Value = "变量管理器"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "系统变量列表："
                .Cells(4, 1).Value = "变量名"
                .Cells(4, 2).Value = "变量值"
                .Cells(4, 3).Value = "变量说明"
                .Range("A4:C4").Font.Bold = True
                .Range("A4:C4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_VERSION
            With ws
                .Cells(1, 1).Value = "版本"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "版本信息："
                .Cells(4, 1).Value = "当前版本：1.0.0"
                .Cells(5, 1).Value = "更新时间：2023-01-01"
            End With
            
        Case PAGE_TEST
            With ws
                .Cells(1, 1).Value = "测试"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "测试功能："
                .Cells(4, 1).Value = "- 功能测试"
                .Cells(5, 1).Value = "- 性能测试"
                .Cells(6, 1).Value = "- 兼容性测试"
            End With
            
        ' 阅读类页面
        Case PAGE_QUERY
            With ws
                ' 合并A1:D1并设置标题
                .Range("A1:D1").Merge
                .Cells(1, 1).Value = "测试"
                .Range("A1:D1").HorizontalAlignment = xlCenter
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "查询字："
                
                ' 设置表头并添加背景色
                With .Range("A5:D5")
                    .Cells(1, 1).Value = "全文"
                    .Cells(1, 2).Value = "目录"
                    .Cells(1, 3).Value = "章节"
                    .Cells(1, 4).Value = "词频"
                    ' 添加背景色（浅蓝色）
                    .Interior.Color = RGB(217, 225, 242)
                    .Font.Bold = True
                    .HorizontalAlignment = xlCenter
                End With

                ' 添加开发者功能按钮，位置同步到查询字后面，间隔一个单元格
                Dim btnfind As Button
                Dim queryCell As Range
                Set queryCell = .Cells(3, 1) ' 查询字单元格
                ' 计算按钮位置：查询字单元格右侧第2列，垂直居中对齐
                Dim btnLeft As Double
                Dim btnTop As Double
                btnLeft = queryCell.Offset(0, 2).Left ' 间隔一个单元格
                btnTop = queryCell.Top + (queryCell.Height - 30) / 2 ' 垂直居中，按钮高度30
                
                Set btnfind = .Buttons.Add(btnLeft, btnTop, 100, 20)
                With btnfind
                    .Caption = "查询"
                    .OnAction = "字典查询"
'                    ' 设置按钮背景色为浅蓝色，与表头保持视觉一致
'                    .Interior.Color = RGB(111, 231, 221)
'                    ' 设置按钮文字为深蓝色，提高可读性
                    .Font.Color = RGB(111, 231, 221)
                    .Font.Bold = True
                End With
                
                ' 冻结前5行
                .rows(6).Select
                ActiveWindow.FreezePanes = True
                .Range("A1").Select ' 回到A1单元格
            End With
            
        Case PAGE_DATA_SOURCE
'            With ws
'                .Cells(1, 1).Value = "数据源"
'                .Cells(1, 1).Font.Bold = True
'                .Cells(1, 1).Font.size = 16
'                .Cells(3, 1).Value = "数据源管理："
'                .Cells(4, 1).Value = "数据源名称"
'                .Cells(4, 2).Value = "类型"
'                .Cells(4, 3).Value = "状态"
'                .Range("A4:C4").Font.Bold = True
'                .Range("A4:C4").Interior.ColorIndex = 15
'            End With
            
        ' 分析类页面
        Case PAGE_SORT
            With ws
                .Cells(1, 1).Value = "- 按查找顺序排序"
                .Cells(1, 4).Value = "- 按词频排序"
                .Cells(1, 7).Value = "- 按顺序(去词频)排序"
                With .Range("A1:A10")
                    ' 添加背景色（浅蓝色）
                    .Interior.Color = RGB(217, 225, 242)
                    .Font.Bold = True
                    .HorizontalAlignment = xlCenter
                End With
                ' 冻结前1行
                .rows(1).Select
                ActiveWindow.FreezePanes = True
                .Range("A1").Select ' 回到A1单元格
            End With

        Case PAGE_CATALOG_DETAIL
            With ws
                .Cells(1, 1).Value = "对应目录详细"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "目录详细信息："
                .Cells(4, 1).Value = "章节"
                .Cells(4, 2).Value = "内容"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_WORD_FREQ
            With ws
                .Cells(1, 1).Value = "词频"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "词频统计："
                .Cells(4, 1).Value = "词语"
                .Cells(4, 2).Value = "频次"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_DUPLICATE
            With ws
                .Cells(1, 1).Value = "重复字"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "重复字检测："
                .Cells(4, 1).Value = "重复字"
                .Cells(4, 2).Value = "位置"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_HIGHLIGHT
            With ws
                .Cells(1, 1).Value = "标红"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "内容标红："
                .Cells(4, 1).Value = "关键词"
                .Cells(4, 2).Value = "出现次数"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        ' 打字类页面
        Case PAGE_TYPE_PAGE
            With ws
                .Cells(1, 1).Value = "打字页面"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "打字练习："
                .Cells(4, 1).Value = "请在此处进行打字练习"
            End With
            
        Case PAGE_TYPE_DB
            With ws
                .Cells(1, 1).Value = "打字数据库"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "打字数据存储："
                .Cells(4, 1).Value = "日期"
                .Cells(4, 2).Value = "打字内容"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_TYPE_STATS
            With ws
                .Cells(1, 1).Value = "码字数据统计"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "统计信息："
                .Cells(4, 1).Value = "总字数"
                .Cells(4, 2).Value = "今日字数"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        ' 常识类页面
        Case PAGE_FIVE_ELEMENTS
            With ws
                .Cells(1, 1).Value = "五行"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "五行知识："
                .Cells(4, 1).Value = "金"
                .Cells(4, 2).Value = "木"
                .Cells(4, 3).Value = "水"
                .Cells(4, 4).Value = "火"
                .Cells(4, 5).Value = "土"
                .Range("A4:E4").Font.Bold = True
            End With
            
        Case PAGE_REGEX
            With ws
                .Cells(1, 1).Value = "正则"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "正则表达式："
                .Cells(4, 1).Value = "表达式"
                .Cells(4, 2).Value = "说明"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        Case PAGE_LEGEND
            With ws
                .Cells(1, 1).Value = "图例"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "图例说明："
                .Cells(4, 1).Value = "符号"
                .Cells(4, 2).Value = "含义"
                .Range("A4:B4").Font.Bold = True
                .Range("A4:B4").Interior.ColorIndex = 15
            End With
            
        ' 开发者工具页面
        Case PAGE_DEV_TOOLS
            With ws
                .Cells(1, 1).Value = "开发者工具"
                .Cells(1, 1).Font.Bold = True
                .Cells(1, 1).Font.Size = 16
                .Cells(3, 1).Value = "工作表管理"
                .Cells(3, 1).Font.Bold = True
                
                .Cells(4, 1).Value = "1. 显示开发类页面"
                .Cells(5, 1).Value = "2. 显示阅读类页面"
                .Cells(6, 1).Value = "3. 显示分析类页面"
                .Cells(7, 1).Value = "4. 显示打字类页面"
                .Cells(8, 1).Value = "5. 显示常识类页面"
                .Cells(9, 1).Value = "6. 显示其他页面"
                .Cells(10, 1).Value = "7. 显示全部页面"
                .Cells(11, 1).Value = "8. 初始化开发类页面"
                .Cells(12, 1).Value = "9. 初始化阅读类页面"
                .Cells(13, 1).Value = "10. 初始化分析类页面"
                .Cells(14, 1).Value = "11. 初始化打字类页面"
                .Cells(15, 1).Value = "12. 初始化常识类页面"
                
                ' 添加开发者功能按钮
                Dim btnShowDev As Button, btnShowRead As Button, btnShowAnalyze As Button
                Dim btnShowType As Button, btnShowCommon As Button, btnShowOther As Button, btnShowAll As Button
                Dim btnInitDev As Button, btnInitRead As Button, btnInitAnalyze As Button
                Dim btnInitType As Button, btnInitCommon As Button
                
                Set btnShowDev = .Buttons.Add(10, 200, 120, 30)
                With btnShowDev
                    .Caption = "显示开发类"
                    .OnAction = "ShowDevelopmentCategory"
                End With
                
                Set btnShowRead = .Buttons.Add(140, 200, 120, 30)
                With btnShowRead
                    .Caption = "显示阅读类"
                    .OnAction = "ShowReadingCategory"
                End With
                
                Set btnShowAnalyze = .Buttons.Add(10, 240, 120, 30)
                With btnShowAnalyze
                    .Caption = "显示分析类"
                    .OnAction = "ShowAnalysisCategory"
                End With
                
                Set btnShowType = .Buttons.Add(140, 240, 120, 30)
                With btnShowType
                    .Caption = "显示打字类"
                    .OnAction = "ShowTypingCategory"
                End With
                
                Set btnShowCommon = .Buttons.Add(10, 280, 120, 30)
                With btnShowCommon
                    .Caption = "显示常识类"
                    .OnAction = "ShowCommonCategory"
                End With
                
                Set btnShowOther = .Buttons.Add(140, 280, 120, 30)
                With btnShowOther
                    .Caption = "显示其他页面"
                    .OnAction = "ShowOtherPages"
                End With
                
                Set btnShowAll = .Buttons.Add(270, 280, 120, 30)
                With btnShowAll
                    .Caption = "显示全部页面"
                    .OnAction = "ShowAllPages"
                End With
                
                Set btnInitDev = .Buttons.Add(270, 200, 120, 30)
                With btnInitDev
                    .Caption = "初始化开发类"
                    .OnAction = "InitializeDevelopmentCategory"
                End With
                
                Set btnInitRead = .Buttons.Add(400, 200, 120, 30)
                With btnInitRead
                    .Caption = "初始化阅读类"
                    .OnAction = "InitializeReadingCategory"
                End With
                
                Set btnInitAnalyze = .Buttons.Add(270, 240, 120, 30)
                With btnInitAnalyze
                    .Caption = "初始化分析类"
                    .OnAction = "InitializeAnalysisCategory"
                End With
                
                Set btnInitType = .Buttons.Add(400, 240, 120, 30)
                With btnInitType
                    .Caption = "初始化打字类"
                    .OnAction = "InitializeTypingCategory"
                End With
                
                Set btnInitCommon = .Buttons.Add(400, 280, 120, 30)
                With btnInitCommon
                    .Caption = "初始化常识类"
                    .OnAction = "InitializeCommonCategory"
                End With
            End With
    End Select
    
    On Error GoTo 0
End Sub

' 检查工作表是否存在
Function SheetExists(sheetName) As Boolean
    Dim ws As Worksheet
    
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    SheetExists = Not ws Is Nothing
    On Error GoTo 0
End Function

' 显示分类的快捷方法
Sub ShowDevelopmentCategory()
    ShowCategory CATEGORY_DEV
End Sub

Sub ShowReadingCategory()
    ShowCategory CATEGORY_READ
End Sub

Sub ShowAnalysisCategory()
    ShowCategory CATEGORY_ANALYZE
End Sub

Sub ShowTypingCategory()
    ShowCategory CATEGORY_TYPE
End Sub

Sub ShowCommonCategory()
    ShowCategory CATEGORY_COMMON
End Sub

' 初始化分类的快捷方法
Sub InitializeDevelopmentCategory()
    InitializeCategory CATEGORY_DEV
End Sub

Sub InitializeReadingCategory()
    InitializeCategory CATEGORY_READ
End Sub

Sub InitializeAnalysisCategory()
    InitializeCategory CATEGORY_ANALYZE
End Sub

Sub InitializeTypingCategory()
    InitializeCategory CATEGORY_TYPE
End Sub

Sub InitializeCommonCategory()
    InitializeCategory CATEGORY_COMMON
End Sub

