# -*- coding: utf-8 -*-
"""
完整测试 VBA 代码：调用各函数，触发编译检查
Option Explicit 下，如果有未声明变量，调用函数时会报错
"""
import win32com.client as win32
import os
import sys

bas_path = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas"

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
    
    # 测试各个函数/过程，看是否有运行时/编译错误
    # 注意：有些函数需要全局变量初始化，我们跳过那些
    test_funcs = [
        ("IsDigits", ["123"]),
        ("NormalizeSeparators", ["第　一  章  测  试"]),
        ("SanitizeFileName", ["test/file?.txt"]),
        ("JoinArr", ["a,b,c", 3, 3]),  # 可能需要数组
        ("JoinCollection", [None, ","]),
        ("JoinDictKeys", [None, ","]),
        ("FormatRange", ["1,2,3,5,6,8"]),
    ]
    
    print("\n测试纯函数...")
    for func_name, args in test_funcs:
        try:
            if func_name == "IsDigits":
                result = excel.Run(func_name, "12345")
                print(f"  ✅ {func_name}('12345') = {result}")
            elif func_name == "NormalizeSeparators":
                result = excel.Run(func_name, "第　一  章  测  试")
                print(f"  ✅ {func_name} = '{result}'")
            elif func_name == "SanitizeFileName":
                result = excel.Run(func_name, "test/file?.txt")
                print(f"  ✅ {func_name} = '{result}'")
            elif func_name == "FormatRange":
                result = excel.Run(func_name, "1,2,3,5,6,8")
                print(f"  ✅ {func_name} = '{result}'")
            else:
                print(f"  ⏭ {func_name} (跳过，参数复杂)")
        except Exception as e:
            print(f"  ❌ {func_name} 错误: {e}")
            error_count += 1
    
    # 测试 CnToInt（中文数字转整数）
    print("\n测试 CnToInt...")
    test_cases = ["第一", "第二十三", "第一百零八", "第三千二百一十五"]
    for tc in test_cases:
        try:
            result = excel.Run("CnToInt", tc)
            print(f"  ✅ CnToInt('{tc}') = {result}")
        except Exception as e:
            print(f"  ❌ CnToInt('{tc}') 错误: {e}")
            error_count += 1
    
    # 测试 NormalizeTitle
    print("\n测试 NormalizeTitle...")
    try:
        result = excel.Run("NormalizeTitle", "第 一 回　测试章节")
        print(f"  ✅ NormalizeTitle = '{result}'")
    except Exception as e:
        print(f"  ❌ NormalizeTitle 错误: {e}")
        error_count += 1
    
    # 测试 NormalizeLineForMatch
    print("\n测试 NormalizeLineForMatch...")
    try:
        result = excel.Run("NormalizeLineForMatch", "第　一  章  测  试")
        print(f"  ✅ NormalizeLineForMatch = '{result}'")
    except Exception as e:
        print(f"  ❌ NormalizeLineForMatch 错误: {e}")
        error_count += 1
    
    # 测试 ExpandGroups
    print("\n测试 ExpandGroups...")
    try:
        result = excel.Run("ExpandGroups", "1-3,5,7-9")
        print(f"  ✅ ExpandGroups = '{result}'")
    except Exception as e:
        print(f"  ❌ ExpandGroups 错误: {e}")
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

print(f"\n{'='*50}")
if error_count == 0:
    print("✅ 全部测试通过！")
else:
    print(f"❌ 共 {error_count} 个错误")
