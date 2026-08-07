Attribute VB_Name = "READ_初始化"
Sub 还原_目录__排序()
    Sheets("目录").UsedRange.Clear
    Sheets("排序").UsedRange.Clear
    Sheets("数据源").Range("E2:Z1048576").Clear
End Sub

Sub 还原_排序()
    Sheets("排序").UsedRange.Clear
    Sheets("数据源").Range("E2:Z1048576").Clear
End Sub

Sub 还原_初始化()
    Sheets("目录").UsedRange.Clear
    Sheets("目录2").UsedRange.Clear
    Sheets("排序").UsedRange.Clear
    Sheets("数据源").UsedRange.Clear
    Sheets("查询").Range("A6:D1048576").ClearContents
    ar = Array("目录", "匹配词", "替换词/匹配②", "正则匹配", "频率", "出现顺序", "频率", "XXX", "全词")
    Sheets("数据源").[B1].Resize(1, UBound(ar) + 1) = ar
    
End Sub
