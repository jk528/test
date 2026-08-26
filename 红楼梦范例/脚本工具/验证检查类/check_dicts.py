# -*- coding: utf-8 -*-
"""
检查情感词典完备性：DUTIR 7类情绪词 + Hownet 正负极性词 + 辅助词表规模

口径说明：
- 正面/负面情感词 = Hownet pos.txt / neg.txt（SentimentAnalyzer）
- 7类情绪词 = DUTIR 好/乐/哀/怒/惧/恶/惊（EmotionAnalyzer）
- 同义词.txt / 反义词.txt 为「同义词词林 / 反义词对表」，非情感词典，仅报告规模
"""

import os
import sys

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
sys.path.insert(0, os.path.join(project_dir, '基础'))

from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer


def count_lines(fpath):
    """统计词表文件的非空行数（词林/反义对按行=词组/词对）"""
    for enc in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(fpath, 'r', encoding=enc) as f:
                return sum(1 for line in f if line.strip())
        except UnicodeDecodeError:
            continue
    return 0


ea = EmotionAnalyzer()
sa = SentimentAnalyzer()

print('=== DUTIR 7类情绪词典 ===')
total_dutir = 0
for emo, words in ea.emotion_dicts.items():
    print(f'  {emo}: {len(words)}词')
    total_dutir += len(words)
print(f'  合计: {total_dutir}词')

print('\n=== Hownet 极性词典（正/负情感词来源） ===')
print(f'  正面词(pos.txt): {len(sa.pos_words)}')
print(f'  负面词(neg.txt): {len(sa.neg_words)}')
print(f'  否定词(deny.txt + 自定义): {len(sa.negation_words)}')
print(f'  程度副词(very/more/ish/extreme + 自定义): {len(sa.degree_words)}')

print('\n=== 辅助词表（非情感词典，仅规模） ===')
print(f'  同义词词林(行=同义词组): {count_lines(os.path.join(project_dir, "基础", "同义词.txt"))}')
print(f'  反义词对表(行=反义对): {count_lines(os.path.join(project_dir, "基础", "反义词.txt"))}')