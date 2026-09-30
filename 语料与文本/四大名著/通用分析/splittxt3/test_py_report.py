# -*- coding: utf-8 -*-
"""快速测试 Python 版分析报告"""
import sys
sys.path.insert(0, r'c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3')

# 创建测试文件
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

test_file = r'c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\test_report.txt'
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_content)

# 导入模块并测试
import importlib.util
spec = importlib.util.spec_from_file_location("split_txt_v3", r'c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("=" * 60)
print("测试深度分析报告")
print("=" * 60)
mod.deep_analyze(test_file)

import os
os.remove(test_file)
print("\n✅ 测试完成")
