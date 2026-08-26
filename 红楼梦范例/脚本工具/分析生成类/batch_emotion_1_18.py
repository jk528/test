# -*- coding: utf-8 -*-
"""
批量运行1-18章的双轨情绪分析（DUTIR 7类 + Hownet 极性）
输出JSON格式数据，供后续报告升级使用
"""

import sys
import os
import json
import glob

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
sys.path.insert(0, os.path.join(project_dir, '基础'))

from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer


def analyze_chapter(chapter_num, ea, sa):
    """分析单章情绪"""
    json_path = os.path.join(project_dir, '红楼梦_分词结果', f'{chapter_num:03d}.json')
    
    if not os.path.exists(json_path):
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        words = json.load(f)
    
    # DUTIR 7类情绪分析
    emo_result = ea.analyze_words(words)
    
    # Hownet 极性分析
    sent_result = sa.analyze_words(words)
    
    # 提取章节标题
    txt_files = glob.glob(os.path.join(project_dir, '红楼梦_拆分', f'{chapter_num:03d}_*.txt'))
    title = ''
    if txt_files:
        basename = os.path.basename(txt_files[0])
        parts = basename.split('_', 2)
        if len(parts) >= 3:
            title = parts[2].replace('.txt', '').replace('第', '').split('章')
            if len(title) > 1:
                title = title[1].strip()
            else:
                title = parts[2].replace('.txt', '')
    
    result = {
        'chapter': chapter_num,
        'title': title,
        'word_count': len(words),
        'dutir': {
            'emotion_counts': emo_result['emotion_counts'],
            'emotion_percentages': emo_result['emotion_percentages'],
            'emotion_words': {k: v[:10] for k, v in emo_result['emotion_words'].items()},
            'positive_count': emo_result['positive_emotion_count'],
            'negative_count': emo_result['negative_emotion_count'],
            'neutral_count': emo_result['neutral_emotion_count'],
            'total': emo_result['total_emotion_words'],
        },
        'hownet': {
            'pos_count': sent_result['pos_count'],
            'neg_count': sent_result['neg_count'],
            'pos_percentage': sent_result['pos_percentage'],
            'neg_percentage': sent_result['neg_percentage'],
            'total': sent_result['total_sentiment_words'],
            'sentiment_score': round(sent_result['sentiment_score'], 2),
            'pos_value': round(sent_result['pos_value'], 2),
            'neg_value': round(sent_result['neg_value'], 2),
            'pos_words_sample': sent_result['pos_words'][:15],
            'neg_words_sample': sent_result['neg_words'][:15],
        }
    }
    
    return result


def main():
    print('=' * 60)
    print('批量情绪分析 第1-18章')
    print('=' * 60)
    
    ea = EmotionAnalyzer()
    sa = SentimentAnalyzer()
    
    all_results = []
    
    for ch in range(1, 19):
        result = analyze_chapter(ch, ea, sa)
        if result:
            all_results.append(result)
            dutir = result['dutir']
            hownet = result['hownet']
            
            # 找主导情绪
            sorted_emos = sorted(dutir['emotion_counts'].items(), key=lambda x: x[1], reverse=True)
            dominant = sorted_emos[0][0] if sorted_emos else '?'
            
            print(f'第{ch:02d}章 {result["title"][:20]:<20} '
                  f'DUTIR:{dutir["total"]:>4}词 '
                  f'(好{dutir["emotion_counts"].get("好",0):>4}/'
                  f'乐{dutir["emotion_counts"].get("乐",0):>3}/'
                  f'哀{dutir["emotion_counts"].get("哀",0):>3}/'
                  f'怒{dutir["emotion_counts"].get("怒",0):>2}/'
                  f'惧{dutir["emotion_counts"].get("惧",0):>2}/'
                  f'恶{dutir["emotion_counts"].get("恶",0):>4}/'
                  f'惊{dutir["emotion_counts"].get("惊",0):>2}) '
                  f'主:{dominant} '
                  f'Hownet:{hownet["total"]:>4}词 '
                  f'(正{hownet["pos_percentage"]}%/负{hownet["neg_percentage"]}%)')
    
    # 保存全部结果
    output_dir = os.path.join(project_dir, '分析结果', '情绪分析数据')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'ch01-18_emotion_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f'\n全部结果已保存到: {output_path}')
    print(f'共分析 {len(all_results)} 章')


if __name__ == '__main__':
    main()
