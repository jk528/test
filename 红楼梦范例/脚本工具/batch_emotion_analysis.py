import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '基础'))
from emotion_analysis import EmotionAnalyzer, SentimentAnalyzer
from collections import Counter

base = os.path.dirname(os.path.abspath(__file__))
project = os.path.join(base, '..')

ea = EmotionAnalyzer()
sa = SentimentAnalyzer()

chapter = sys.argv[1] if len(sys.argv) > 1 else "021"
json_path = os.path.join(project, '红楼梦_分词结果', f'{chapter}.json')

if not os.path.exists(json_path):
    print(f"ERROR: {json_path} not found")
    sys.exit(1)

with open(json_path, 'r', encoding='utf-8') as f:
    words = json.load(f)

er = ea.analyze_words(words)
sr = sa.analyze_words(words)

# Word frequency
freq = Counter(words)
top30 = freq.most_common(30)

print(f"=== Chapter {chapter} ===")
print(f"Total words: {len(words)}")
print()
print("--- DUTIR 7 categories ---")
for k in ["好", "乐", "哀", "怒", "惧", "恶", "惊"]:
    c = er['emotion_counts'].get(k, 0)
    p = er['emotion_percentages'].get(k, 0.0)
    wlist = list(set(er['emotion_words'].get(k, [])))
    print(f"{k}: {c} ({p}%) words={wlist[:15]}")
print(f"DUTIR_TOTAL: {er['total_emotion_words']}")
print(f"POS: {er['positive_emotion_count']} NEG: {er['negative_emotion_count']} NEU: {er['neutral_emotion_count']}")

print()
print("--- Hownet ---")
print(f"pos: {sr['pos_count']} neg: {sr['neg_count']}")
print(f"pos%: {sr['pos_percentage']} neg%: {sr['neg_percentage']}")
print(f"total: {sr['total_sentiment_words']}")
print(f"pos_words: {sr['pos_words'][:30]}")
print(f"neg_words: {sr['neg_words'][:30]}")

print()
print("--- Top 30 words ---")
for w, c in top30:
    print(f"  {w}: {c}")
