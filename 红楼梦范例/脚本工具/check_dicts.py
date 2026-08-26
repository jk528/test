# -*- coding: utf-8 -*-
"""
检查同义词和反义词词典的词数，对比前面章节的统计口径
"""

import os

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'

def load_words(fpath):
    words = set()
    for enc in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(fpath, 'r', encoding=enc) as f:
                for line in f:
                    w = line.strip()
                    if w:
                        words.add(w)
            break
        except UnicodeDecodeError:
            continue
    return words

# 加载各词典
syn_path = os.path.join(project_dir, '基础', '同义词.txt')
ant_path = os.path.join(project_dir, '基础', '反义词.txt')

syn_words = load_words(syn_path)
ant_words = load_words(ant_path)

print(f'同义词词典词数: {len(syn_words)}')
print(f'反义词词典词数: {len(ant_words)}')

# 检查重叠
overlap = syn_words & ant_words
print(f'正反词典重叠词数: {len(overlap)}')

# 看看前10个词
print(f'\n同义词前20个: {list(syn_words)[:20]}')
print(f'反义词前20个: {list(ant_words)[:20]}')

# 检查DUTIR和Hownet的词典大小
import sys
sys.path.insert(0, os.path.join(project_dir, '基础'))
from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer

ea = EmotionAnalyzer()
sa = SentimentAnalyzer()

print(f'\n=== DUTIR 7类词典 ===')
total_dutir = 0
for emo, s in ea.emotion_dicts.items():
    print(f'  {emo}: {len(s)}词')
    total_dutir += len(s)
print(f'  合计: {total_dutir}词')

print(f'\n=== Hownet 极性词典 ===')
print(f'  正面词: {len(sa.pos_words)}')
print(f'  负面词: {len(sa.neg_words)}')
print(f'  否定词: {len(sa.deny_words)}')
print(f'  程度副词: {len(sa.degree_words)}')
