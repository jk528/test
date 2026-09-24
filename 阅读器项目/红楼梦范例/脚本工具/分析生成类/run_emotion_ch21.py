import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '基础'))
from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..', '..')

with open(os.path.join(project, '红楼梦_分词结果', '021.json'), 'r', encoding='utf-8') as f:
    words = json.load(f)

ea = EmotionAnalyzer()
sa = SentimentAnalyzer()

er = ea.analyze_words(words)
sr = sa.analyze_words(words)

print("=== DUTIR 7 categories ===")
for k in ["好", "乐", "哀", "怒", "惧", "恶", "惊"]:
    c = er['emotion_counts'].get(k, 0)
    p = er['emotion_percentages'].get(k, 0.0)
    wlist = er['emotion_words'].get(k, [])
    print(f"{k}: {c} ({p}%) words={list(set(wlist))[:15]}")
print(f"DUTIR_TOTAL: {er['total_emotion_words']}")
print(f"POS: {er['positive_emotion_count']} NEG: {er['negative_emotion_count']} NEU: {er['neutral_emotion_count']}")

print()
print("=== Hownet ===")
for k, v in sr.items():
    print(f"{k}: {v}")
