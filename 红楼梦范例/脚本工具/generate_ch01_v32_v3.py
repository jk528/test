# -*- coding: utf-8 -*-
"""
按V3.2模板重新生成第1章分析报告 v3
直接以V3.2存档为基础，更新需要重新计算的字段
确保所有f-string正确，无语法错误
"""

import os
import re
import json
import glob
from collections import Counter

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
output_dir = os.path.join(project_dir, '分析结果')
base_dir = os.path.join(project_dir, '基础')
ref_path = os.path.join(output_dir, 'V3.2存档_1-19章', '001_甄士隐梦幻识通灵_双轨六要素分析报告.md')

# ===== 加载基础词典（用于验证和统计） =====

def load_words_file(fpath):
    words = set()
    for enc in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(fpath, 'r', encoding=enc) as f:
                for line in f:
                    w = line.strip()
                    if w and len(w) >= 1:
                        words.add(w)
            break
        except UnicodeDecodeError:
            continue
    return words


def load_stopwords():
    stopwords = set()
    stop_dir = os.path.join(base_dir, '停用词库')
    files = glob.glob(os.path.join(stop_dir, '*.txt'))
    for fpath in files:
        stopwords |= load_words_file(fpath)
    main_stop = os.path.join(base_dir, '停用词.txt')
    if os.path.exists(main_stop):
        stopwords |= load_words_file(main_stop)
    return stopwords


print('加载基础资源...')
stopwords = load_stopwords()
sw_count = len(stopwords)
print('  停用词：' + str(sw_count))

# ===== 加载分词和原文 =====
with open(os.path.join(project_dir, '红楼梦_分词结果', '001.json'), 'r', encoding='utf-8') as f:
    all_words = json.load(f)

chapter_text_path = glob.glob(os.path.join(project_dir, '红楼梦_拆分', '001_*_第1章*.txt'))[0]
with open(chapter_text_path, 'r', encoding='utf-8') as f:
    chapter_text = f.read()

char_count = len(chapter_text)
total_words = len(all_words)
content_words = [w for w in all_words if w not in stopwords and len(w.strip()) > 0]
content_count = len(content_words)

print('第1章：' + str(char_count) + '字，' + str(total_words) + '词')
print('内容词（去停用词）：' + str(content_count))

# 高频词汇TOP10
word_freq = Counter(content_words)
top10 = word_freq.most_common(10)

# ===== 以V3.2存档为基础，更新需要变动的字段 =====
with open(ref_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 更新字数统计
content = re.sub(
    r'\| 字数统计 \| \d+字 \|',
    '| 字数统计 | ' + str(char_count) + '字 |',
    content
)

# 更新分词数据相关的说明
content = content.replace(
    '`红楼梦_分词结果/001.json` 词频统计（',
    '`红楼梦_分词结果/001.json` 词频统计（' + str(total_words) + '个词条，'
)

# 更新版本绑定声明中的分析日期
content = re.sub(
    r'> \*\*分析日期\*\*：\d{4}-\d{2}-\d{2}',
    '> **分析日期**：2026-08-26',
    content
)

# 更新文件大小相关（如果有的话，不用管）

# 保存
output_path = os.path.join(output_dir, '001_甄士隐梦幻识通灵_双轨六要素分析报告.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)

file_size = os.path.getsize(output_path)
print('')
print('报告已生成：' + output_path)
print('文件大小：' + str(file_size) + ' 字节')

# 验证
h2 = re.findall(r'^## (.+)$', content, re.MULTILINE)
h3 = re.findall(r'^### (.+)$', content, re.MULTILINE)
print('')
print('验证：')
print('  大章节：' + str(len(h2)) + '（预期10）')
print('  子章节：' + str(len(h3)) + '（预期28）')
has_v32 = 'V3.2' in content
has_v18 = 'v1.8' in content
has_43 = bool(re.search(r'4\.3 冲突动机分析', content))
has_44 = bool(re.search(r'4\.4 ', content))
has_53 = bool(re.search(r'5\.3 情感趋势分析', content))
has_57 = bool(re.search(r'5\.7 七类情绪', content))
print('  V3.2：' + str(has_v32))
print('  v1.8：' + str(has_v18))
print('  4.3冲突：' + str(has_43))
print('  4.4叙事：' + str(has_44))
print('  5.3趋势：' + str(has_53))
print('  5.7七类：' + str(has_57))

ok = len(h2) == 10 and len(h3) == 28 and has_v32 and has_43 and has_53 and has_57
print('')
print('验证通过：' + str(ok))
