# -*- coding: utf-8 -*-
"""
测试修改后的 VBA 代码：调用 DeepAnalyzeFile 相关函数
"""
import win32com.client as win32
import os
import sys

bas_path = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas"
test_file = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\test_sample.txt"

# 创建一个测试文件（有重复章节和不同标题）
test_content = """第一回 甄士隐梦幻识通灵 贾雨村风尘怀闺秀
正文内容第一回第一段
正文内容第一回第二段

第一回 甄士隐梦幻识通灵 贾雨村风尘怀闺秀
第一回重复的正文

第二回 贾夫人仙逝扬州城 冷子兴演说荣国府
第二回正文内容

第二回 不同标题的第二章
这是第二回另一个标题的内容

第三回 贾雨村夤缘复旧职 林黛玉抛父进京都
第三回正文内容

第四回 薄命女偏逢薄命郎 葫芦僧乱判葫芦案
第四回正文内容

第五回 游幻境指迷十二钗 饮仙醪曲演红楼梦
第五回正文内容

第三回 贾雨村夤缘复旧职 林黛玉抛父进京都
第三次出现的第三回
"""

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_content)

print(f"测试文件已创建：{test_file}")
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
    
    # 测试 DeepAnalyzeFile
    print("\n测试 DeepAnalyzeFile...")
    try:
        result = excel.Run("DeepAnalyzeFile", test_file)
        print(f"  ✅ DeepAnalyzeFile 调用成功")
        print(f"  返回值长度: {len(result)} 字符")
        
        # 显示报告的关键部分
        lines = result.split('\n')
        print(f"\n  报告共 {len(lines)} 行")
        print("\n  === 报告预览（前60行）===")
        for i, line in enumerate(lines[:60]):
            print(f"  {i+1:3d}: {line}")
        
        # 查找关键部分
        print("\n  === 查找关键修改 ===")
        found_top = False
        found_titlediff = False
        for line in lines:
            if '重复最严重' in line:
                found_top = True
            if found_top and '章 (' in line and '次)' in line:
                print(f"  ✅ Top重复章节带标题: {line.strip()}")
                found_top = False
            if '章号相同但标题不同' in line:
                found_titlediff = True
                print(f"  ✅ 同章异题: {line.strip()}")
            if found_titlediff and '个不同标题' in line:
                print(f"  ✅ 显示不同标题数量: {line.strip()}")
            if found_titlediff and '· ' in line:
                print(f"  ✅ 完整标题列表: {line.strip()}")
                found_titlediff = False
                
    except Exception as e:
        print(f"  ❌ DeepAnalyzeFile 错误: {e}")
        import traceback
        traceback.print_exc()
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
    # 清理测试文件
    try:
        os.remove(test_file)
    except:
        pass

print(f"\n{'='*50}")
if error_count == 0:
    print("✅ 全部测试通过！")
else:
    print(f"❌ 共 {error_count} 个错误")
