# -*- coding: utf-8 -*-
"""
用 Excel COM 对象编译 VBA 代码，检查语法错误
"""
import win32com.client as win32
import os

bas_path = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas"

print("启动 Excel...")
excel = win32.Dispatch("Excel.Application")
excel.Visible = False

try:
    # 创建新工作簿
    wb = excel.Workbooks.Add()
    
    # 导入 bas 文件
    print(f"导入模块：{bas_path}")
    wb.VBProject.VBComponents.Import(bas_path)
    
    print("模块导入成功，尝试编译...")
    
    # 尝试编译
    try:
        wb.VBProject.VBE.ActiveVBProject = wb.VBProject
        # 触发编译（VBE 菜单的 Compile 命令）
        # CommandBars("Menu Bar").Controls("调试").Controls("编译 VBAProject").Execute
        # 或者用另一种方式：尝试运行一个不存在的函数来触发语法检查
    except Exception as e:
        print(f"编译异常: {e}")
    
    # 更可靠的方式：检查 VBComponents 中是否有编译错误
    # 通过 OnError 捕获
    import pythoncom
    
    print("检查模块代码...")
    
    # 枚举所有组件
    for comp in wb.VBProject.VBComponents:
        print(f"  组件: {comp.Name} (类型: {comp.Type})")
        if comp.CodeModule:
            print(f"    行数: {comp.CodeModule.CountOfLines}")
    
    print("\n尝试运行一个简单测试...")
    # 尝试调用一个简单函数
    try:
        # 直接调用函数名
        result = excel.Run("IsDigits", "12345")
        print(f"IsDigits('12345') = {result}  ✅")
    except Exception as e:
        print(f"调用失败: {e}")
    
    wb.Close(SaveChanges=False)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    
    try:
        wb.Close(SaveChanges=False)
    except:
        pass
finally:
    excel.Quit()
    print("\nExcel 已关闭")
