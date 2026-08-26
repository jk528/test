# -*- coding: utf-8 -*-
"""
第19章情绪分析脚本 - 输出详细的情绪分析数据
"""

import sys
import os
import json

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
sys.path.insert(0, os.path.join(project_dir, '基础'))

from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer


def analyze_chapter_19():
    json_path = os.path.join(project_dir, '红楼梦_分词结果', '019.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                words.append(item)
    
    print(f'分词总数: {len(words)}')
    
    # DUTIR 7类情绪分析
    ea = EmotionAnalyzer()
    emo_result = ea.analyze_words(words)
    
    print('\n=== DUTIR 7类情绪分析 ===')
    for emo in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
        count = emo_result['emotion_counts'].get(emo, 0)
        pct = emo_result['emotion_percentages'].get(emo, 0)
        sample = emo_result['emotion_words'].get(emo, [])[:10]
        print(f'{emo}: {count} ({pct}%) - {sample}')
    
    print(f'\n正面: {emo_result["positive_emotion_count"]}')
    print(f'负面: {emo_result["negative_emotion_count"]}')
    print(f'中性: {emo_result["neutral_emotion_count"]}')
    print(f'总计: {emo_result["total_emotion_words"]}')
    
    # Hownet 极性分析
    sa = SentimentAnalyzer()
    sent_result = sa.analyze_words(words)
    
    print('\n=== Hownet 极性分析 ===')
    print(f'正面词: {sent_result["pos_count"]} ({sent_result["pos_percentage"]}%)')
    print(f'负面词: {sent_result["neg_count"]} ({sent_result["neg_percentage"]}%)')
    print(f'总计: {sent_result["total_sentiment_words"]}')
    print(f'情感得分: {sent_result["sentiment_score"]}')
    print(f'正面加权值: {sent_result["pos_value"]}')
    print(f'负面加权值: {sent_result["neg_value"]}')
    print(f'\n正面词Top15: {sent_result["pos_words"][:15]}')
    print(f'负面词Top15: {sent_result["neg_words"][:15]}')
    
    # 输出JSON格式结果供报告生成使用
    result = {
        'words_count': len(words),
        'dutir': {
            'emotion_counts': emo_result['emotion_counts'],
            'emotion_percentages': emo_result['emotion_percentages'],
            'emotion_words': {k: v[:15] for k, v in emo_result['emotion_words'].items()},
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
            'sentiment_score': sent_result['sentiment_score'],
            'pos_value': sent_result['pos_value'],
            'neg_value': sent_result['neg_value'],
            'pos_words': sent_result['pos_words'][:20],
            'neg_words': sent_result['neg_words'][:20],
        }
    }
    
    output_path = os.path.join(project_dir, '分析结果', 'ch19_emotion_data.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f'\n分析数据已保存到: {output_path}')
    return result


if __name__ == '__main__':
    analyze_chapter_19()
