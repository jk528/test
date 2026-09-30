# -*- coding: utf-8 -*-
"""
验证 VBA 代码编译通过
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
    if wb is None:
        print("❌ 无法创建工作簿")
        sys.exit(1)
    
    print(f"导入模块: {os.path.basename(bas_path)}")
    try:
        wb.VBProject.VBComponents.Import(bas_path)
        print("  ✅ 导入成功（Option Explicit 下无编译错误）")
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        error_count += 1
        wb.Close(SaveChanges=False)
        sys.exit(1)
    
    # 验证模块
    print("\n模块信息:")
    for comp in wb.VBProject.VBComponents:
        if comp.Type == 1:  # 标准模块
            print(f"  {comp.Name}: {comp.CodeModule.CountOfLines} 行")
    
    # 测试几个基础函数
    print("\n基础函数测试:")
    tests = [
        ("IsDigits", "12345"),
        ("NormalizeTitle", "第　一  回  测 试 章 节"),
        ("CnToInt", "第二十三"),
        ("SanitizeFileName", "test/name?.txt"),
    ]
    for func, arg in tests:
        try:
            r = excel.Run(func, arg)
            print(f"  ✅ {func}('{arg}') = {r}")
        except Exception as e:
            print(f"  ❌ {func} 错误: {e}")
            error_count += 1
    
    print(f"\n{'='*50}")
    if error_count == 0:
        print("✅ 编译通过，基础函数运行正常")
    else:
        print(f"❌ {error_count} 个错误")
    
    wb.Close(SaveChanges=False)
except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    excel.Quit()
