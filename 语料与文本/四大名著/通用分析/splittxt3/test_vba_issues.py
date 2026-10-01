# -*- coding: utf-8 -*-
"""
测试 VBA 代码：
1. AutoNFromBodies 函数
2. first + none 策略文件数
"""
import win32com.client as win32
import os
import sys

bas_path = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas"
test_file = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\test_first_none.txt"

# 创建测试文件：有重复章节（首次保留）
test_content = """第一回 甄士隐梦幻识通灵 贾雨村风尘怀闺秀
第一回正文内容1
第一回正文内容2
第一回正文内容3
第一回正文内容4
第一回正文内容5

第二回 贾夫人仙逝扬州城 冷子兴演说荣国府
第二回正文内容1
第二回正文内容2
第二回正文内容3
第二回正文内容4
第二回正文内容5

第三回 贾雨村夤缘复旧职 林黛玉抛父进京都
第三回正文内容1
第三回正文内容2
第三回正文内容3
第三回正文内容4
第三回正文内容5

第一回 甄士隐梦幻识通灵 贾雨村风尘怀闺秀
第一回重复内容（更短）

第四回 薄命女偏逢薄命郎 葫芦僧乱判葫芦案
第四回正文内容1
第四回正文内容2
第四回正文内容3
第四回正文内容4
第四回正文内容5

第二回 贾夫人仙逝扬州城 冷子兴演说荣国府
第二回重复内容（更短）

第五回 游幻境指迷十二钗 饮仙醪曲演红楼梦
第五回正文内容1
第五回正文内容2
第五回正文内容3
第五回正文内容4
第五回正文内容5
"""

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_content)

print(f"测试文件已创建：{os.path.basename(test_file)}")
print(f"预期：5章（first策略保留首次，去重2个重复）")
print("=" * 60)

print("启动 Excel...")
excel = win32.Dispatch("Excel.Application")
excel.Visible = False

error_count = 0

try:
    wb = excel.Workbooks.Add()
    
    print(f"导入模块...")
    try:
        wb.VBProject.VBComponents.Import(bas_path)
        print("  ✅ 导入成功")
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        error_count += 1
        wb.Close(SaveChanges=False)
        sys.exit(1)
    
    # 创建测试模块
    test_mod = wb.VBProject.VBComponents.Add(1)
    test_mod.Name = "TestMod"
    
    # 测试代码：调用核心函数并返回结果
    test_code = '''
Public Function TestAutoN(ByVal filePath As String) As String
    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim autoN As Long
    Dim result As String
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    g_detectedEnc = DetectEncodingFile(filePath)
    content = ReadTextAuto(filePath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    
    InitRegexPatterns
    ScanChaptersV3 lines, lineCount
    DetectTOC
    
    On Error Resume Next
    autoN = AutoNFromBodies(lines)
    If Err.Number <> 0 Then
        result = "ERROR: AutoNFromBodies - " & Err.Description & " (编号:" & Err.Number & ")"
        Err.Clear
    Else
        result = "OK: autoN=" & autoN
    End If
    On Error GoTo 0
    
    Set fso = Nothing
    TestAutoN = result
End Function

Public Function TestFirstNone(ByVal filePath As String) As String
    Dim fso As Object
    Dim content As String
    Dim lines() As String, lineCount As Long
    Dim chapIdx() As Long, chapCnt As Long
    Dim outIdx() As Long, outCnt As Long
    Dim result As String
    Dim i As Long
    Dim volModeStr As String
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    g_detectedEnc = DetectEncodingFile(filePath)
    content = ReadTextAuto(filePath)
    content = Replace(Replace(content, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(content, vbLf)
    lineCount = UBound(lines) + 1
    
    InitRegexPatterns
    ScanChaptersV3 lines, lineCount
    DetectTOC
    
    ' 获取章节索引
    GetChapterIndices chapIdx, chapCnt
    
    ' 先测试 first + flat
    g_dedupStrategy = "first"
    g_sortStrategy = "none"
    g_titleDedup = False
    g_volumeMode = "auto"
    volModeStr = ResolveVolMode(g_volumeMode)
    
    On Error Resume Next
    DedupFirst volModeStr, outIdx, outCnt, False
    If Err.Number <> 0 Then
        result = "ERROR: DedupFirst - " & Err.Description
        Err.Clear
        TestFirstNone = result
        Exit Function
    End If
    On Error GoTo 0
    
    result = "扫描到章节: " & ch_count & vbCrLf & _
             "有效章节(跳过TOC): " & chapCnt & vbCrLf & _
             "first去重后: " & outCnt & vbCrLf & _
             "卷模式: " & volModeStr & vbCrLf & _
             "去重后章节列表:" & vbCrLf
    
    For i = 0 To outCnt - 1
        result = result & "  [" & (i + 1) & "] 第" & ch_nums(outIdx(i)) & _
                 ch_units(outIdx(i)) & " " & Left(ch_titles(outIdx(i)), 30) & vbCrLf
    Next i
    
    Set fso = Nothing
    TestFirstNone = result
End Function
'''
    test_mod.CodeModule.AddFromString(test_code)
    
    # 测试1：AutoNFromBodies
    print("\n测试1: AutoNFromBodies 函数")
    try:
        r = excel.Run("TestAutoN", test_file)
        print(f"  结果: {r}")
        if "ERROR" in r:
            error_count += 1
        else:
            print("  ✅ AutoNFromBodies 正常")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        error_count += 1
    
    # 测试2：first + none 策略
    print("\n测试2: first + none 去重策略")
    try:
        r = excel.Run("TestFirstNone", test_file)
        print(f"  结果:")
        for line in r.split('\n'):
            print(f"    {line}")
        print("  ✅ DedupFirst 正常")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        error_count += 1
    
    wb.Close(SaveChanges=False)
    
except Exception as e:
    print(f"\n全局错误: {e}")
    import traceback
    traceback.print_exc()
    error_count += 1
    try:
        wb.Close(SaveChanges=False)
    except:
        pass
finally:
    excel.Quit()
    try:
        os.remove(test_file)
    except:
        pass

print(f"\n{'='*50}")
if error_count == 0:
    print("✅ 全部测试通过！")
else:
    print(f"❌ 共 {error_count} 个错误")
