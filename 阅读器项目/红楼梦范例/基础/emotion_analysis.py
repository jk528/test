# -*- coding: utf-8 -*-
"""
情绪分析模块（基于 cnsenti DUTIR + Hownet 词典整合）

功能：
1. 7大类情绪词统计（好/乐/哀/怒/惧/恶/惊）
2. Hownet 正负情感词统计
3. 否定词翻转 + 程度副词加权
4. 支持读取 JSON 分词结果文件

词典来源：
- DUTIR 情感词汇本体（大连理工大学）
- Hownet 知网情感词典
- cnsenti Python库 (github.com/hiDaDeng/cnsenti)
"""

import os
import json
from collections import defaultdict


class EmotionAnalyzer:
    """7大类情绪分析器（基于 DUTIR 情感词汇本体）"""

    # 7大类情绪及其极性映射
    EMOTION_CATEGORIES = {
        '好': 'positive',
        '乐': 'positive',
        '哀': 'negative',
        '怒': 'negative',
        '惧': 'negative',
        '恶': 'negative',
        '惊': 'neutral',
    }

    # 中文全称
    EMOTION_NAMES = {
        '好': '好（正面褒奖）',
        '乐': '乐（愉悦快乐）',
        '哀': '哀（悲伤痛苦）',
        '怒': '怒（愤怒憎恶）',
        '惧': '惧（恐惧害怕）',
        '恶': '恶（厌恶鄙视）',
        '惊': '惊（惊讶惊奇）',
    }

    def __init__(self, dict_dir=None):
        """
        初始化情绪分析器

        Args:
            dict_dir: DUTIR词典目录，默认 基础/情感词典_DUTIR/
        """
        if dict_dir is None:
            # 默认路径：基础/情感词典_DUTIR/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dict_dir = os.path.join(base_dir, '基础', '情感词典_DUTIR')

        self.dict_dir = dict_dir
        self.emotion_dicts = {}
        self._load_dictionaries()

    def _load_dictionaries(self):
        """加载7类情绪词典"""
        for emo in self.EMOTION_CATEGORIES:
            dict_path = os.path.join(self.dict_dir, f'{emo}.txt')
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    words = set(line.strip() for line in f if line.strip())
                self.emotion_dicts[emo] = words
            else:
                self.emotion_dicts[emo] = set()
                print(f'警告: 未找到词典文件 {dict_path}')

    def analyze_words(self, words):
        """
        对分词后的词列表进行7类情绪分析

        Args:
            words: 分词后的词列表（list of str）

        Returns:
            dict: 分析结果，包含：
                - emotion_counts: {情绪类别: 词数}
                - emotion_words: {情绪类别: [匹配词列表]}
                - emotion_values: {情绪类别: 加权值}
                - positive_emotion_count: 正面情绪词总数
                - negative_emotion_count: 负面情绪词总数
                - neutral_emotion_count: 中性情绪词总数
        """
        emotion_counts = defaultdict(int)
        emotion_words = defaultdict(list)
        emotion_values = defaultdict(float)

        for word in words:
            if not word or not word.strip():
                continue
            word = word.strip()
            for emo, emo_set in self.emotion_dicts.items():
                if word in emo_set:
                    emotion_counts[emo] += 1
                    emotion_words[emo].append(word)
                    emotion_values[emo] += 1.0
                    break  # 一个词只归为一个主要情绪类别

        # 按极性汇总
        pos_count = sum(emotion_counts[e] for e, p in self.EMOTION_CATEGORIES.items() if p == 'positive')
        neg_count = sum(emotion_counts[e] for e, p in self.EMOTION_CATEGORIES.items() if p == 'negative')
        neu_count = sum(emotion_counts[e] for e, p in self.EMOTION_CATEGORIES.items() if p == 'neutral')

        # 确保所有类别都有值
        for emo in self.EMOTION_CATEGORIES:
            if emo not in emotion_counts:
                emotion_counts[emo] = 0
                emotion_words[emo] = []
                emotion_values[emo] = 0.0

        total_emotion = sum(emotion_counts.values())

        return {
            'emotion_counts': dict(emotion_counts),
            'emotion_words': {k: list(set(v)) for k, v in emotion_words.items()},  # 去重
            'emotion_values': dict(emotion_values),
            'positive_emotion_count': pos_count,
            'negative_emotion_count': neg_count,
            'neutral_emotion_count': neu_count,
            'total_emotion_words': total_emotion,
            'emotion_percentages': {
                emo: round(emotion_counts[emo] / total_emotion * 100, 1) if total_emotion > 0 else 0.0
                for emo in self.EMOTION_CATEGORIES
            },
        }

    def analyze_json(self, json_path):
        """
        从JSON分词结果文件进行分析

        Args:
            json_path: JSON分词结果文件路径

        Returns:
            dict: 分析结果（同 analyze_words）
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 提取词列表（兼容多种JSON格式）
        words = self._extract_words(data)
        return self.analyze_words(words)

    def _extract_words(self, data):
        """从JSON数据中提取词列表"""
        words = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    words.append(item)
                elif isinstance(item, dict):
                    # 可能是 {word: xxx, pos: xxx} 格式
                    if 'word' in item:
                        words.append(item['word'])
        elif isinstance(data, dict):
            # 可能是 {words: [...]} 格式
            if 'words' in data and isinstance(data['words'], list):
                words.extend(data['words'])
            # 可能是按词性分组的格式
            for key in data:
                if isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, str):
                            words.append(item)

        return words

    def get_emotion_summary(self, result):
        """
        生成情绪分析摘要文本

        Args:
            result: analyze_words 或 analyze_json 的返回结果

        Returns:
            str: 摘要文本
        """
        lines = []
        lines.append('=== 7大类情绪分析摘要 ===')
        lines.append(f'总情绪词数: {result["total_emotion_words"]}')
        lines.append(f'正面情绪词: {result["positive_emotion_count"]}')
        lines.append(f'负面情绪词: {result["negative_emotion_count"]}')
        lines.append(f'中性情绪词: {result["neutral_emotion_count"]}')
        lines.append('')
        lines.append('各类别分布:')

        # 按词数排序
        sorted_emotions = sorted(
            result['emotion_counts'].items(),
            key=lambda x: x[1], reverse=True
        )

        for emo, count in sorted_emotions:
            name = self.EMOTION_NAMES.get(emo, emo)
            pct = result['emotion_percentages'].get(emo, 0)
            polarity = self.EMOTION_CATEGORIES.get(emo, '?')
            polarity_mark = {'positive': '+', 'negative': '-', 'neutral': '~'}[polarity]
            sample_words = result['emotion_words'].get(emo, [])[:5]
            sample_str = ', '.join(sample_words) if sample_words else '无'
            lines.append(f'  {polarity_mark} {name}: {count} ({pct}%) 示例: {sample_str}')

        return '\n'.join(lines)


class SentimentAnalyzer:
    """正负情感分析器（基于 Hownet 词典 + 否定词 + 程度副词）"""

    def __init__(self, dict_dir=None, negation_file=None, degree_file=None):
        """
        初始化情感分析器

        Args:
            dict_dir: Hownet词典目录，默认 基础/情感词典_Hownet/
            negation_file: 否定词文件路径，默认 基础/否定词.txt
            degree_file: 程度副词文件路径，默认 基础/递进词.txt
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if dict_dir is None:
            dict_dir = os.path.join(base_dir, '基础', '情感词典_Hownet')
        if negation_file is None:
            negation_file = os.path.join(base_dir, '基础', '否定词.txt')
        if degree_file is None:
            degree_file = os.path.join(base_dir, '基础', '递进词.txt')

        self.dict_dir = dict_dir
        self.negation_file = negation_file
        self.degree_file = degree_file

        self.pos_words = set()
        self.neg_words = set()
        self.negation_words = set()
        self.degree_words = {}  # {词: 权重}

        self._load_dictionaries()

    def _load_dictionaries(self):
        """加载词典"""
        # Hownet 正面词
        pos_path = os.path.join(self.dict_dir, 'pos.txt')
        if os.path.exists(pos_path):
            with open(pos_path, 'r', encoding='utf-8') as f:
                self.pos_words = set(line.strip() for line in f if line.strip())

        # Hownet 负面词
        neg_path = os.path.join(self.dict_dir, 'neg.txt')
        if os.path.exists(neg_path):
            with open(neg_path, 'r', encoding='utf-8') as f:
                self.neg_words = set(line.strip() for line in f if line.strip())

        # 否定词
        if os.path.exists(self.negation_file):
            with open(self.negation_file, 'r', encoding='utf-8') as f:
                self.negation_words = set(line.strip() for line in f if line.strip())

        # 程度副词（默认权重1.5）
        if os.path.exists(self.degree_file):
            with open(self.degree_file, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            for w in words:
                self.degree_words[w] = 1.5

        # Hownet 程度副词（补充）
        degree_map = {
            'very.txt': 2.0,    # 极高级
            'extreme.txt': 2.5, # 极端级
            'more.txt': 1.5,    # 比较级
            'ish.txt': 0.75,    # 稍低级
        }
        for fname, weight in degree_map.items():
            fpath = os.path.join(self.dict_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    for line in f:
                        w = line.strip()
                        if w:
                            self.degree_words[w] = weight

        # Hownet 否定词（补充）
        deny_path = os.path.join(self.dict_dir, 'deny.txt')
        if os.path.exists(deny_path):
            with open(deny_path, 'r', encoding='utf-8') as f:
                for line in f:
                    w = line.strip()
                    if w:
                        self.negation_words.add(w)

    def analyze_words(self, words):
        """
        对分词后的词列表进行情感分析（含否定翻转和程度加权）

        Args:
            words: 分词后的词列表

        Returns:
            dict: 分析结果
        """
        pos_count = 0
        neg_count = 0
        pos_value = 0.0
        neg_value = 0.0
        pos_word_list = []
        neg_word_list = []

        # 滑动窗口检测否定词和程度副词（窗口大小=5）
        window_size = 5

        for i, word in enumerate(words):
            if not word or not word.strip():
                continue
            word = word.strip()

            # 检测窗口内的否定词和程度副词
            has_negation = False
            degree_weight = 1.0

            # 向前查找窗口
            start = max(0, i - window_size)
            for j in range(start, i):
                prev_word = words[j].strip() if words[j] else ''
                if not prev_word:
                    continue
                if prev_word in self.negation_words:
                    has_negation = not has_negation  # 奇数次翻转，偶数次还原
                if prev_word in self.degree_words:
                    degree_weight *= self.degree_words[prev_word]

            # 正面词
            if word in self.pos_words:
                if has_negation:
                    neg_count += 1
                    neg_value += degree_weight
                    neg_word_list.append(word)
                else:
                    pos_count += 1
                    pos_value += degree_weight
                    pos_word_list.append(word)

            # 负面词
            elif word in self.neg_words:
                if has_negation:
                    pos_count += 1
                    pos_value += degree_weight
                    pos_word_list.append(word)
                else:
                    neg_count += 1
                    neg_value += degree_weight
                    neg_word_list.append(word)

        total_sentiment = pos_count + neg_count
        sentiment_score = pos_value - neg_value

        return {
            'pos_count': pos_count,
            'neg_count': neg_count,
            'pos_value': round(pos_value, 2),
            'neg_value': round(neg_value, 2),
            'sentiment_score': round(sentiment_score, 2),
            'total_sentiment_words': total_sentiment,
            'pos_percentage': round(pos_count / total_sentiment * 100, 1) if total_sentiment > 0 else 0.0,
            'neg_percentage': round(neg_count / total_sentiment * 100, 1) if total_sentiment > 0 else 0.0,
            'pos_words': list(set(pos_word_list)),
            'neg_words': list(set(neg_word_list)),
            'negation_count': len(self.negation_words),
            'degree_count': len(self.degree_words),
        }

    def analyze_json(self, json_path):
        """从JSON分词结果文件进行分析"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        words = self._extract_words(data)
        return self.analyze_words(words)

    def _extract_words(self, data):
        """从JSON数据中提取词列表"""
        words = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    words.append(item)
                elif isinstance(item, dict) and 'word' in item:
                    words.append(item['word'])
        elif isinstance(data, dict):
            if 'words' in data and isinstance(data['words'], list):
                words.extend(data['words'])
            for key in data:
                if isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, str):
                            words.append(item)
        return words


def dual_track_analysis(json_path):
    """
    双轨情感分析：正负极性 + 7类情绪

    Args:
        json_path: JSON分词结果文件路径

    Returns:
        dict: 综合分析结果
    """
    sentiment_analyzer = SentimentAnalyzer()
    emotion_analyzer = EmotionAnalyzer()

    # 读取JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取词
    words = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                words.append(item)
            elif isinstance(item, dict) and 'word' in item:
                words.append(item['word'])

    sentiment_result = sentiment_analyzer.analyze_words(words)
    emotion_result = emotion_analyzer.analyze_words(words)

    return {
        'sentiment': sentiment_result,
        'emotion': emotion_result,
    }


if __name__ == '__main__':
    # 测试代码
    test_text = '我今天非常开心，感到无比快乐和幸福，但也有些惊讶和不安。'
    import jieba_fast as jieba  # 备用
    words = list(jieba.cut(test_text))

    print('测试分词:', '/'.join(words))
    print()

    # 情绪分析测试
    ea = EmotionAnalyzer()
    emo_result = ea.analyze_words(words)
    print(ea.get_emotion_summary(emo_result))
    print()

    # 情感分析测试
    sa = SentimentAnalyzer()
    sent_result = sa.analyze_words(words)
    print('=== 正负情感分析摘要 ===')
    print(f'正面词: {sent_result["pos_count"]} ({sent_result["pos_percentage"]}%)')
    print(f'负面词: {sent_result["neg_count"]} ({sent_result["neg_percentage"]}%)')
    print(f'情感得分: {sent_result["sentiment_score"]}')
    print(f'正面词示例: {sent_result["pos_words"][:5]}')
    print(f'负面词示例: {sent_result["neg_words"][:5]}')
