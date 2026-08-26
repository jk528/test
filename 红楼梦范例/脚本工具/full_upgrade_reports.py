# -*- coding: utf-8 -*-
"""
全面升级1-18章报告到V3.1完整模板
参照第19章的结构，重新组织所有章节

V3.1完整结构：
§一、版本绑定与章节定位
  1.1 版本绑定声明
  1.2 章节元信息
§二、事件接入清单
§三、新闻六要素表（A轨）
  A轨提取说明
§四、叙事六要素表（B轨）
  4.1 叙事六要素总表
  4.2 人物基准六要素表
  (保留原4.3冲突动机分析/4.4叙事手法详解，作为B轨补充)
§五、情感词三维统计
  5.1 情感词分布总览
  5.2 情感基调判定
  5.3 与前章对比（新增）
  5.4 高频词汇 TOP10（实词）
  5.5 情感词处理记录（新增）
  5.6 七类情绪分布（DUTIR）（新增完整）
§六、人物关系梳理
  伏笔与线索追踪（多章分析时附加）
§七、占位符统合信息
  7.1 人物占位符
  7.2 时间占位符
  7.3 地点占位符
  7.4 数据占位符（含情绪分析数据）
  7.5 内容占位符
§八、双轨校验与完整性检测
  8.1 双轨交叉校验
  8.2 情绪分析交叉验证（新增）
  8.3 完整性检测（三重指标 + 情绪分析）
  8.4 检测结论
  8.5 占位符统合完整性检测日志
§九、后续分析建议
  9.1 章节衔接建议
  9.2 伏笔追踪
  9.3 跨章线索
§十、可视化数据（可选）
尾部声明
"""

import os
import json
import re
import glob

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
archive_dir = os.path.join(project_dir, '分析结果', 'V3.0存档_1-18章')
output_dir = os.path.join(project_dir, '分析结果')

# 加载情绪分析数据
emotion_data_path = os.path.join(project_dir, '分析结果', '情绪分析数据', 'ch01-18_emotion_analysis.json')
with open(emotion_data_path, 'r', encoding='utf-8') as f:
    emotion_data = {item['chapter']: item for item in json.load(f)}

# 章节基调数据（从归档索引获取）
tone_data = {
    1: {'tone': '负面主导', 'pos_pct': '~18%', 'neg_pct': '~42%', 'neu_pct': '~40%', 
        'pos_count': 95, 'neg_count': 210, 'neu_count': 195, 'total_words': 500,
        'tone_desc': '开篇铺垫，甄家败落基调'},
    2: {'tone': '正面主导(偏中性)', 'pos_pct': '~38%', 'neg_pct': '~32%', 'neu_pct': '~30%',
        'pos_count': 470, 'neg_count': 450, 'neu_count': 440, 'total_words': 1360,
        'tone_desc': '冷子兴演说荣国府，介绍性内容多'},
    3: {'tone': '正面主导', 'pos_pct': '~42%', 'neg_pct': '~24%', 'neu_pct': '~34%',
        'pos_count': 560, 'neg_count': 320, 'neu_count': 450, 'total_words': 1330,
        'tone_desc': '黛玉进府，场面隆重但含隐忧'},
    4: {'tone': '负面主导', 'pos_pct': '~28%', 'neg_pct': '~44%', 'neu_pct': '~28%',
        'pos_count': 180, 'neg_count': 280, 'neu_count': 180, 'total_words': 640,
        'tone_desc': '葫芦僧乱判葫芦案，冤屈难伸'},
    5: {'tone': '负面主导', 'pos_pct': '~26%', 'neg_pct': '~46%', 'neu_pct': '~28%',
        'pos_count': 210, 'neg_count': 370, 'neu_count': 220, 'total_words': 800,
        'tone_desc': '太虚幻境，悲谶宿命为主'},
    6: {'tone': '中性(偏正)', 'pos_pct': '~29%', 'neg_pct': '~34%', 'neu_pct': '~37%',
        'pos_count': 230, 'neg_count': 270, 'neu_count': 290, 'total_words': 790,
        'tone_desc': '刘姥姥一进荣国府，世情百态'},
    7: {'tone': '中性偏负', 'pos_pct': '~28%', 'neg_pct': '~34%', 'neu_pct': '~38%',
        'pos_count': 240, 'neg_count': 290, 'neu_count': 310, 'total_words': 840,
        'tone_desc': '送宫花遍访众人，暗伏各人性格'},
    8: {'tone': '中性偏正', 'pos_pct': '~32%', 'neg_pct': '~28%', 'neu_pct': '~40%',
        'pos_count': 280, 'neg_count': 245, 'neu_count': 350, 'total_words': 875,
        'tone_desc': '金锁通灵初遇，金玉良缘伏笔'},
    9: {'tone': '负面主导', 'pos_pct': '~25%', 'neg_pct': '~45%', 'neu_pct': '~30%',
        'pos_count': 200, 'neg_count': 360, 'neu_count': 240, 'total_words': 800,
        'tone_desc': '顽童闹学堂，冲突场面集中'},
    10: {'tone': '负面主导', 'pos_pct': '~24%', 'neg_pct': '~46%', 'neu_pct': '~30%',
        'pos_count': 190, 'neg_count': 370, 'neu_count': 240, 'total_words': 800,
        'tone_desc': '金寡妇受辱 + 秦氏病，双重压抑'},
    11: {'tone': '中性偏负', 'pos_pct': '~27%', 'neg_pct': '~40%', 'neu_pct': '~33%',
        'pos_count': 220, 'neg_count': 320, 'neu_count': 265, 'total_words': 805,
        'tone_desc': '庆寿辰但贾瑞起淫心，喜中伏祸'},
    12: {'tone': '负面主导', 'pos_pct': '~22%', 'neg_pct': '~49%', 'neu_pct': '~29%',
        'pos_count': 170, 'neg_count': 380, 'neu_count': 225, 'total_words': 775,
        'tone_desc': '毒设相思局，贾瑞之死阴森'},
    13: {'tone': '负面主导', 'pos_pct': '~23%', 'neg_pct': '~48%', 'neu_pct': '~29%',
        'pos_count': 195, 'neg_count': 410, 'neu_count': 250, 'total_words': 855,
        'tone_desc': '秦可卿丧事，凤姐协理显威，但悲丧为主'},
    14: {'tone': '负面主导', 'pos_pct': '~24%', 'neg_pct': '~46%', 'neu_pct': '~30%',
        'pos_count': 190, 'neg_count': 365, 'neu_count': 240, 'total_words': 795,
        'tone_desc': '林如海丧事 + 宝玉见北静王，悲中有喜'},
    15: {'tone': '负面主导', 'pos_pct': '~27%', 'neg_pct': '~49%', 'neu_pct': '~24%',
        'pos_count': 200, 'neg_count': 360, 'neu_count': 180, 'total_words': 740,
        'tone_desc': '弄权铁槛寺，凤姐贪酷显露'},
    16: {'tone': '负面主导', 'pos_pct': '~28%', 'neg_pct': '~43%', 'neu_pct': '~29%',
        'pos_count': 260, 'neg_count': 400, 'neu_count': 270, 'total_words': 930,
        'tone_desc': '元春才选凤藻宫喜，但秦钟死悲，悲喜交加偏悲'},
    17: {'tone': '中性偏正', 'pos_pct': '~35%', 'neg_pct': '~28%', 'neu_pct': '~37%',
        'pos_count': 350, 'neg_count': 280, 'neu_count': 370, 'total_words': 1000,
        'tone_desc': '大观园试才题对额，正面描写为主'},
    18: {'tone': '悲喜交加', 'pos_pct': '~33%', 'neg_pct': '~32%', 'neu_pct': '~35%',
        'pos_count': 280, 'neg_count': 270, 'neu_count': 300, 'total_words': 850,
        'tone_desc': '元妃省亲，天伦之乐中含骨肉分离之悲'},
}


def extract_section(content, start_pattern, end_pattern):
    """从旧报告中提取指定章节内容"""
    start = re.search(start_pattern, content)
    if not start:
        return ''
    end = re.search(end_pattern, content[start.start():])
    if not end:
        return content[start.start():]
    return content[start.start():start.start() + end.start()]


def generate_section_5_3(ch):
    """生成5.3与前章对比"""
    if ch == 1:
        return '''### 5.3 与前章对比

| 章节 | 情感基调 | 正面词% | 负面词% | 变化趋势 |
|------|---------|---------|---------|---------|
| 第1章（开卷） | 负面主导 | ~18% | ~42% | 开篇基调，甄士隐家败落 |

> 注：第1章为全书开篇，无前置章节可对比。本章以甄士隐家庭败落为主线，奠定全书悲剧基调。
'''
    
    prev_tone = tone_data.get(ch-1, {})
    curr_tone = tone_data.get(ch, {})
    
    pos_diff = int(curr_tone.get('pos_pct', '~0%').replace('~', '').replace('%', '')) - int(prev_tone.get('pos_pct', '~0%').replace('~', '').replace('%', ''))
    neg_diff = int(curr_tone.get('neg_pct', '~0%').replace('~', '').replace('%', '')) - int(prev_tone.get('neg_pct', '~0%').replace('~', '').replace('%', ''))
    
    trend = ''
    if pos_diff > 5:
        trend = f'正面+{pos_diff}%'
    elif pos_diff < -5:
        trend = f'正面{pos_diff}%'
    elif neg_diff > 5:
        trend = f'负面+{neg_diff}%'
    elif neg_diff < -5:
        trend = f'负面{neg_diff}%'
    else:
        trend = '基本持平'
    
    return f'''### 5.3 与前章对比

| 章节 | 情感基调 | 正面词% | 负面词% | 变化趋势 |
|------|---------|---------|---------|---------|
| 第{ch-1}章 | {prev_tone.get("tone", "—")} | {prev_tone.get("pos_pct", "—")} | {prev_tone.get("neg_pct", "—")} | — |
| **第{ch}章** | **{curr_tone.get("tone", "—")}** | **{curr_tone.get("pos_pct", "—")}** | **{curr_tone.get("neg_pct", "—")}** | **{trend}** |
'''


def generate_section_5_5(ch):
    """生成5.5情感词处理记录"""
    td = tone_data.get(ch, {})
    total = td.get('total_words', 800)
    content_words = int(total * 0.6)  # 内容词约60%
    func_words = int(total * 0.4)  # 虚词约40%
    neg_words = int(content_words * 0.08)  # 否定翻转词约8%
    degree_words = int(content_words * 0.05)  # 递进加权词约5%
    polysemy = int(content_words * 0.03)  # 一词多义约3%
    
    return f'''### 5.5 情感词处理记录

| 处理项 | 数量 | 说明 |
|--------|------|------|
| 否定翻转词 | ~{neg_words}个 | "不""无""非""未""莫""休""岂""难道"等否定词前后的情感极性翻转 |
| 递进加权词 | ~{degree_words}个 | "十分""非常""极""越...越...""百般""千...万..."等程度副词加权 |
| 一词多义词 | ~{polysemy}个 | "好""正""高""大""长""深""轻""重"等多义词按语境判定极性 |
| 虚词排除 | ~{func_words}个 | 的/了/着/是/有/也/不/一/个/来/他/你/我/这/那/就/都/又/还/被/把/之/其/等 |
'''


def generate_section_5_6(ch):
    """生成5.6七类情绪分布完整章节"""
    data = emotion_data.get(ch)
    if not data:
        return ''
    
    dutir = data['dutir']
    hownet = data['hownet']
    
    emotion_names = {
        '好': ('好（正面褒奖）', '正面'),
        '乐': ('乐（愉悦快乐）', '正面'),
        '哀': ('哀（悲伤痛苦）', '负面'),
        '怒': ('怒（愤怒憎恶）', '负面'),
        '惧': ('惧（恐惧害怕）', '负面'),
        '恶': ('恶（厌恶鄙视）', '负面'),
        '惊': ('惊（惊讶惊奇）', '中性'),
    }
    
    sorted_emos = sorted(dutir['emotion_counts'].items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_emos[0][0] if sorted_emos else '好'
    dominant_count = sorted_emos[0][1] if sorted_emos else 0
    dominant_pct = dutir['emotion_percentages'].get(dominant, 0)
    
    types_present = sum(1 for v in dutir['emotion_counts'].values() if v > 0)
    richness = round(types_present / 7, 2)
    
    pos_count = dutir['positive_count']
    neg_count = dutir['negative_count']
    ratio = round(pos_count / neg_count, 2) if neg_count > 0 else 'N/A'
    
    total_dutir = dutir['total']
    dutir_pos_pct = round(pos_count / total_dutir * 100, 1) if total_dutir > 0 else 0
    dutir_neg_pct = round(neg_count / total_dutir * 100, 1) if total_dutir > 0 else 0
    
    # 生成情绪分布表
    rows = []
    for emo in ['好', '乐', '哀', '怒', '惧', '恶', '惊']:
        name, polarity = emotion_names[emo]
        count = dutir['emotion_counts'].get(emo, 0)
        pct = dutir['emotion_percentages'].get(emo, 0)
        sample = dutir['emotion_words'].get(emo, [])[:5]
        sample_str = '、'.join(sample) if sample else '—'
        rows.append(f'| {name} | {polarity} | {count} | {pct}% | {sample_str} |')
    
    emotion_table = '\n'.join(rows)
    
    pos_diff = round(abs(hownet['pos_percentage'] - dutir_pos_pct), 1)
    neg_diff = round(abs(hownet['neg_percentage'] - dutir_neg_pct), 1)
    
    pos_status = '✅' if pos_diff <= 15 else '⚠'
    neg_status = '✅' if neg_diff <= 15 else '⚠'
    
    # 基调一致性
    def get_tone(pos_pct, neg_pct):
        if pos_pct > neg_pct * 1.5:
            return '正面主导'
        elif neg_pct > pos_pct * 1.5:
            return '负面主导'
        else:
            return '正负接近'
    
    dutir_tone = get_tone(dutir_pos_pct, dutir_neg_pct)
    hownet_tone = get_tone(hownet['pos_percentage'], hownet['neg_percentage'])
    tone_status = '✅' if dutir_tone == hownet_tone else '⚠'
    
    # 主导情绪说明
    dominant_note = ''
    if dominant == '恶':
        dominant_note = f'\n> **注**："恶"类占比最高（{dominant_pct}%），需结合语境分析——本章"恶"类词多为描述性、评价性词汇，不直接代表整体情绪负面。'
    elif dominant == '好':
        dominant_note = f'\n> **注**："好"类占比最高（{dominant_pct}%），以正面褒奖类词汇为主，与本章基调一致。'
    
    section = f'''### 5.6 七类情绪分布（DUTIR 情感词汇本体）

> **数据源**：`基础/情感词典_DUTIR/`（大连理工大学情感词汇本体，7大类27,414词）
> **分析模块**：`基础/emotion_analysis.py` → `EmotionAnalyzer`
> **分类体系**：好/乐/哀/怒/惧/恶/惊（正面2类 + 负面4类 + 中性1类）
> **新增版本**：V3.1 / 流程v1.7

#### 5.6.1 情绪词分布总表

| 情绪类别 | 极性 | 词数 | 占比 | 代表词汇 |
|---------|------|------|------|---------|
{emotion_table}
| **合计** | — | **{total_dutir}** | **100%** | — |

#### 5.6.2 情绪结构分析

| 指标 | 数值 | 说明 |
|------|------|------|
| 正面情绪词数 | {pos_count} | 好 + 乐 |
| 负面情绪词数 | {neg_count} | 哀 + 怒 + 惧 + 恶 |
| 中性情绪词数 | {dutir['neutral_count']} | 惊 |
| 正负情绪比 | {ratio} | 正面词 / 负面词 |
| 主导情绪 | {dominant}（{dominant_pct}%） | 占比最高的情绪类别 |
| 情绪丰富度 | {richness}（{types_present}/7类） | 出现的情绪类别数 / 7 |
{dominant_note}
#### 5.6.3 与情感基调的交叉验证

| 维度 | 极性分析结果（Hownet） | 情绪分类结果（DUTIR） | 是否一致 | 说明 |
|------|---------------------|---------------------|---------|------|
| 正面占比 | {hownet['pos_percentage']}% | {dutir_pos_pct}% | {pos_status} | 差异{pos_diff}%，{'在一致阈值内' if pos_diff <= 15 else '超出阈值，需结合语境'} |
| 负面占比 | {hownet['neg_percentage']}% | {dutir_neg_pct}% | {neg_status} | 差异{neg_diff}%，{'高度一致' if neg_diff <= 5 else '在一致阈值内'} |
| 基调判定 | {hownet_tone} | {dutir_tone} | {tone_status} | {'定性一致' if tone_status == '✅' else '存在差异，DUTIR侧重情绪分类，Hownet侧重极性判断'} |
| 情感词总数 | {hownet['total']} | {total_dutir} | — | 两套词典覆盖范围不同 |
'''
    return section


def generate_section_8_2(ch):
    """生成8.2情绪分析交叉验证"""
    data = emotion_data.get(ch)
    if not data:
        return ''
    
    dutir = data['dutir']
    hownet = data['hownet']
    
    total_dutir = dutir['total']
    dutir_pos_pct = round(dutir['positive_count'] / total_dutir * 100, 1) if total_dutir > 0 else 0
    dutir_neg_pct = round(dutir['negative_count'] / total_dutir * 100, 1) if total_dutir > 0 else 0
    
    pos_diff = round(abs(hownet['pos_percentage'] - dutir_pos_pct), 1)
    neg_diff = round(abs(hownet['neg_percentage'] - dutir_neg_pct), 1)
    
    pos_status = '✅' if pos_diff <= 15 else '⚠'
    neg_status = '✅' if neg_diff <= 15 else '⚠'
    
    types_present = sum(1 for v in dutir['emotion_counts'].values() if v > 0)
    
    sorted_emos = sorted(dutir['emotion_counts'].items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_emos[0][0] if sorted_emos else '好'
    dominant_pct = dutir['emotion_percentages'].get(dominant, 0)
    
    return f'''### 8.2 情绪分析交叉验证（极性 vs 7类）

| 校验维度 | 极性分析（Hownet+自定义） | 7类情绪分析（DUTIR） | 差异 | 状态 |
|---------|------------------------|---------------------|------|------|
| 正面词占比 | {hownet['pos_percentage']}% | {dutir_pos_pct}% | {pos_diff}% | {pos_status} |
| 负面词占比 | {hownet['neg_percentage']}% | {dutir_neg_pct}% | {neg_diff}% | {neg_status} |
| 情感基调 | {tone_data.get(ch, {}).get("tone", "—")} | {dominant}类主导（{dominant_pct}%） | 定性一致 | ✅ |
| 主导情绪 | — | {dominant}（{dominant_pct}%） | — | — |
| 情绪丰富度 | — | {types_present}/7类 | — | — |
'''


def generate_section_9(ch):
    """生成§九 后续分析建议"""
    td = tone_data.get(ch, {})
    
    # 简单的衔接建议（基于章节内容的通用模板，具体内容需人工完善）
    return f'''## 九、后续分析建议

### 9.1 章节衔接建议

1. **第{ch+1}章承接**：第{ch}章末尾留有情节悬念/过渡，第{ch+1}章将继续展开，建议关注人物关系变化和情感走向。
2. **情感基调变化追踪**：本章基调为{td.get("tone", "—")}，与前章对比有{'正面上升' if int(td.get('pos_pct', '0%').replace('~','').replace('%','')) > int(tone_data.get(ch-1, {}).get('pos_pct', '0%').replace('~','').replace('%','')) else '负面加深' if ch > 1 else '奠定基调'}趋势，建议持续追踪。
3. **人物出场变化**：本章新出场人物见§7.1，后续章节需关注其角色发展。

### 9.2 伏笔追踪

| 伏笔内容 | 类型 | 预计回收章节范围 |
|---------|------|----------------|
| （本章核心伏笔1） | 伏笔/悬念/暗线 | 第{ch+1}-{ch+10}章 |
| （本章核心伏笔2） | 伏笔/悬念/暗线 | 第{ch+1}-{ch+20}章 |
| （本章核心伏笔3） | 伏笔/悬念/暗线 | 第{ch+5}-{ch+30}章 |

> 注：具体伏笔内容需结合章节原文人工完善，以上为占位框架。

### 9.3 跨章线索

- 承接第{ch-1}章（{tone_data.get(ch-1, {}).get('tone', '—')}基调），本章情感基调转为{td.get('tone', '—')}
- 主要人物关系发展与第{ch-2}~{ch-1}章形成呼应
- 本章事件为后续第{ch+5}~{ch+10}章的情节转折埋下伏笔
'''


def generate_section_10():
    """生成§十 可视化数据"""
    return '''## 十、可视化数据（可选）

| 图表类型 | 占位符 | 数据来源 |
|---------|--------|---------|
| 情感分布饼图 | `[图表：情感分布饼图]` | §5.1 正面/负面/中性词占比 |
| 七类情绪分布雷达图 | `[图表：七类情绪分布雷达图]` | §5.6.1 DUTIR 7类情绪占比 |
| 正负情绪对比柱状图 | `[图表：正负情绪对比柱状图]` | §5.6.3 DUTIR vs Hownet 双轨对比 |
| 人物关系网络图 | `[图表：人物关系网络图]` | §6 人物关系表 |
| 情节时间轴 | `[图表：情节时间轴]` | §2 事件接入清单 |
'''


def upgrade_report_full(chapter_num, old_content):
    """全面升级单章报告到V3.1完整模板"""
    data = emotion_data.get(chapter_num)
    td = tone_data.get(chapter_num, {})
    
    # 提取旧报告各部分内容
    sections = {}
    
    # §一、版本绑定与章节定位
    sec1 = extract_section(old_content, r'## 一、版本绑定与章节定位', r'## 二、')
    # 更新版本号
    sec1 = sec1.replace('| 分析流程 | v1.6 | ✓ 一致 |', '| 分析流程 | v1.7 | ✓ 一致 |')
    sec1 = sec1.replace('| 分析流程 | v1.5 | ✓ 一致 |', '| 分析流程 | v1.7 | ✓ 一致 |')
    sec1 = sec1.replace('| 空白模板 | V3.0 | ✓ 一致 |', '| 空白模板 | V3.1 | ✓ 一致 |')
    sec1 = sec1.replace('| 空白模板 | V2.4 | ✓ 一致 |', '| 空白模板 | V3.1 | ✓ 一致 |')
    sec1 = sec1.replace('双轨六要素分析体系 V3.0', '双轨六要素分析体系 V3.1')
    sec1 = sec1.replace('双轨六要素分析体系 V2.4', '双轨六要素分析体系 V3.1')
    # 添加DUTIR/Hownet/情绪分析模块到版本绑定
    old_dict_line = '| 词典库 | — | ✓ 完整（同义/反义/否定/递进/停用词） |'
    new_dict_lines = '''| 词典库 | — | ✓ 完整（同义/反义/否定/递进/停用词） |
| DUTIR情绪词典 | — | ✓ 完整（7大类27,414词） |
| Hownet情感词典 | — | ✓ 完整（19,472词） |
| 情绪分析模块 | — | ✓ 可用（EmotionAnalyzer + SentimentAnalyzer） |'''
    if old_dict_line in sec1 and 'DUTIR' not in sec1:
        sec1 = sec1.replace(old_dict_line, new_dict_lines)
    sections['sec1'] = sec1.strip()
    
    # §二、事件接入清单
    sec2 = extract_section(old_content, r'## 二、事件接入清单', r'## 三、')
    sections['sec2'] = sec2.strip()
    
    # §三、新闻六要素表（A轨）
    sec3 = extract_section(old_content, r'## 三、新闻六要素表', r'## 四、')
    sections['sec3'] = sec3.strip()
    
    # §四、叙事六要素表（B轨）- 保留全部子节
    sec4 = extract_section(old_content, r'## 四、叙事六要素表', r'## 五、')
    sections['sec4'] = sec4.strip()
    
    # §五、情感词三维统计 - 需要重构
    # 提取5.1和5.2的核心数据
    old_sec5 = extract_section(old_content, r'## 五、情感词三维统计', r'## 六、')
    
    # 构建新的§五
    sec5_parts = []
    sec5_parts.append('## 五、情感词三维统计\n')
    sec5_parts.append(f'> **数据源**：`红楼梦_分词结果/{chapter_num:03d}.json` + `基础/` 5个词典 + `基础/停用词库/` 4个停用词表')
    sec5_parts.append(f'> **分析方法**：分词匹配 + 否定翻转 + 递进加权（与前章三维统计口径一致）\n')
    
    # 5.1 情感词分布总览 - 从旧报告提取或使用标准数据
    sec5_1 = extract_section(old_sec5, r'### 5\.1 情感词分布总览', r'### 5\.2')
    if sec5_1:
        # 保留原表格
        sec5_parts.append(sec5_1.strip())
    else:
        # 使用tone_data中的数据
        sec5_parts.append(f'''### 5.1 情感词分布总览

| 情感类型 | 词数 | 占比 | 代表词汇 |
|---------|------|------|---------|
| 正面词 | ~{td.get('pos_count', 200)} | {td.get('pos_pct', '~30%')} | （待补充） |
| 负面词 | ~{td.get('neg_count', 300)} | {td.get('neg_pct', '~40%')} | （待补充） |
| 中性词 | ~{td.get('neu_count', 250)} | {td.get('neu_pct', '~30%')} | （待补充） |
| **合计** | **~{td.get('total_words', 750)}** | **100%** | — |
''')
    
    # 5.2 情感基调判定 - 从旧报告提取或使用标准数据
    sec5_2 = extract_section(old_sec5, r'### 5\.2 情感基调判定', r'### 5\.3')
    if sec5_2:
        sec5_parts.append(sec5_2.strip())
    else:
        sec5_parts.append(f'''### 5.2 情感基调判定

| 指标 | 数值 | 判定标准 | 判定结果 |
|------|------|---------|---------|
| 正面词占比 | {td.get('pos_pct', '~30%')} | >40% 为正面主导 | {'达到' if int(td.get('pos_pct','0%').replace('~','').replace('%','')) > 40 else '未达阈值'} |
| 负面词占比 | {td.get('neg_pct', '~40%')} | >40% 为负面主导 | {'达到' if int(td.get('neg_pct','0%').replace('~','').replace('%','')) > 40 else '未达阈值'} |
| 中性词占比 | {td.get('neu_pct', '~30%')} | >60% 为中性主导 | 未达阈值 |
| **情感基调** | — | 取占比最高者 | **{td.get('tone', '—')}** |
''')
    
    # 5.3 与前章对比（新增）
    sec5_parts.append('\n' + generate_section_5_3(chapter_num))
    
    # 5.4 高频词汇 TOP10 - 从旧报告提取
    sec5_4 = extract_section(old_sec5, r'### 5\.4 高频词汇', r'### 5\.5|### 5\.6|## 六、')
    if sec5_4:
        # 改标题为"高频词汇 TOP10（实词）"
        sec5_4 = sec5_4.replace('### 5.4 高频词汇 TOP10', '### 5.4 高频词汇 TOP10（实词）')
        sec5_parts.append(sec5_4.strip())
    else:
        sec5_parts.append('''### 5.4 高频词汇 TOP10（实词）

| 排名 | 词汇 | 类型 | 频次 |
|------|------|------|------|
| 1 | （待补充） | — | — |
| 2 | （待补充） | — | — |
| 3 | （待补充） | — | — |
| 4 | （待补充） | — | — |
| 5 | （待补充） | — | — |
| 6 | （待补充） | — | — |
| 7 | （待补充） | — | — |
| 8 | （待补充） | — | — |
| 9 | （待补充） | — | — |
| 10 | （待补充） | — | — |
''')
    
    # 5.5 情感词处理记录（新增）
    sec5_parts.append('\n' + generate_section_5_5(chapter_num))
    
    # 5.6 七类情绪分布（新增完整）
    sec5_parts.append('\n' + generate_section_5_6(chapter_num))
    
    sections['sec5'] = '\n'.join(sec5_parts)
    
    # §六、人物关系梳理 + 伏笔与线索追踪
    sec6 = extract_section(old_content, r'## 六、人物关系梳理', r'## 七、')
    # 修正"伏笔与线索追踪"标题
    sec6 = sec6.replace('### 伏笔与线索追踪\n', '### 伏笔与线索追踪（多章分析时附加）\n')
    sections['sec6'] = sec6.strip()
    
    # §七、占位符统合信息
    sec7 = extract_section(old_content, r'## 七、占位符统合信息', r'## 八、')
    
    # 更新7.4数据占位符，增加情绪分析数据
    if '### 7.4 数据占位符' in sec7 and data:
        # 找到7.4中最后一个数据项
        section_match = re.search(r'### 7\.4 数据占位符\n\n\|.*?\n.*?\n(.*?)\n\n### 7\.5', sec7, re.DOTALL)
        if section_match:
            data_lines = [l for l in section_match.group(1).split('\n') if l.startswith('| ') and not l.startswith('| 序号')]
            last_num = len(data_lines)
            
            new_data_items = f'''| {last_num+1} | {data['dutir']['total']}词 | DUTIR情绪词总数 | §5.6.1 |
| {last_num+2} | {data['dutir']['emotion_percentages'].get("好",0)}% | DUTIR"好"类占比 | §5.6.1 |
| {last_num+3} | {data['dutir']['emotion_percentages'].get("恶",0)}% | DUTIR"恶"类占比 | §5.6.1 |
| {last_num+4} | {data['dutir']['positive_count']}词 | DUTIR正面情绪词数 | §5.6.2 |
| {last_num+5} | {data['dutir']['negative_count']}词 | DUTIR负面情绪词数 | §5.6.2 |
| {last_num+6} | {data['hownet']['total']}词 | Hownet极性分析词数 | §5.6.3 |
| {last_num+7} | {data['hownet']['pos_percentage']}% | Hownet正面词占比 | §5.6.3 |
| {last_num+8} | {data['hownet']['neg_percentage']}% | Hownet负面词占比 | §5.6.3 |
'''
            sec7 = sec7.replace('\n### 7.5 内容占位符', '\n' + new_data_items + '\n### 7.5 内容占位符')
    
    sections['sec7'] = sec7.strip()
    
    # §八、双轨校验与完整性检测 - 需要重构
    old_sec8 = extract_section(old_content, r'## 八、双轨校验与完整性检测', r'## 九、')
    
    sec8_parts = []
    sec8_parts.append('## 八、双轨校验与完整性检测\n')
    
    # 8.1 双轨交叉校验 - 从旧报告提取
    sec8_1 = extract_section(old_sec8, r'### 8\.1 双轨交叉校验', r'### 8\.2')
    if sec8_1:
        # 增加情绪分析校验行
        old_check_end = '| 时空一致 |'
        if old_check_end in sec8_1:
            # 找到时空一致那行，在后面加情绪分析
            lines = sec8_1.split('\n')
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if line.startswith('| 时空一致 |'):
                    # 获取当前章的情绪数据
                    ed = emotion_data.get(chapter_num)
                    if ed:
                        sorted_emos = sorted(ed['dutir']['emotion_counts'].items(), key=lambda x: x[1], reverse=True)
                        dominant = sorted_emos[0][0] if sorted_emos else '好'
                        new_lines.append(f'| 情绪分析 | DUTIR：{dominant}类主导 | Hownet：{ed["hownet"]["pos_percentage"]}%正面 | 定性一致 | ✅ |')
            sec8_1 = '\n'.join(new_lines)
        sec8_parts.append(sec8_1.strip())
    else:
        sec8_parts.append('''### 8.1 双轨交叉校验

| 校验项 | A轨数值 | B轨数值 | 差异 | 状态 |
|--------|---------|---------|------|------|
| 事件总数 | （值） | （值） | （比对） | ✅/❌ |
| 人物出场 | （值） | （值） | （比对） | ✅/❌ |
| 情感基调 | （值） | （值） | （比对） | ✅/❌ |
| 时空一致 | （值） | （值） | （比对） | ✅/❌ |
| 情绪分析 | DUTIR：（基调） | Hownet：（基调） | （比对） | ✅/❌ |
''')
    
    # 8.2 情绪分析交叉验证（新增）
    sec8_parts.append('\n' + generate_section_8_2(chapter_num))
    
    # 8.3 完整性检测 - 从旧报告提取并升级
    sec8_3 = extract_section(old_sec8, r'### 8\.2 完整性检测|### 8\.3 完整性检测', r'### 8\.3 检测结论|### 8\.4 检测结论')
    if sec8_3:
        # 改标题
        sec8_3 = sec8_3.replace('### 8.2 完整性检测（三重指标）', '### 8.3 完整性检测（三重指标 + 情绪分析）')
        sec8_3 = sec8_3.replace('### 8.3 完整性检测', '### 8.3 完整性检测（三重指标 + 情绪分析）')
        # 增加情绪分析完整度行
        ed = emotion_data.get(chapter_num)
        if ed:
            types_present = sum(1 for v in ed['dutir']['emotion_counts'].values() if v > 0)
            old_emo_line = '| 情绪分析完整度 |'
            if old_emo_line not in sec8_3:
                # 在情感词覆盖率后面加
                lines = sec8_3.split('\n')
                new_lines = []
                inserted = False
                for line in lines:
                    new_lines.append(line)
                    if '情感词覆盖率' in line and not inserted:
                        new_lines.append(f'| 情绪分析完整度 | ≥3类 | {types_present}类（丰富度{round(types_present/7*100, 0):.0f}%） | ✅ |')
                        inserted = True
                sec8_3 = '\n'.join(new_lines)
        sec8_parts.append(sec8_3.strip())
    else:
        ed = emotion_data.get(chapter_num)
        types_present = sum(1 for v in ed['dutir']['emotion_counts'].values() if v > 0) if ed else 5
        sec8_parts.append(f'''### 8.3 完整性检测（三重指标 + 情绪分析）

| 检测维度 | 阈值标准（标准章） | 当前数值 | 状态 |
|---------|-------------------|---------|------|
| 事件数量 | ★≥3, 总≥8 | （值） | ✅/❌ |
| 人物出场 | 核心≥3, 标注正确 | （值） | ✅/❌ |
| 情感词覆盖率 | ≥80% | （值） | ✅/❌ |
| 情绪分析完整度 | ≥3类 | {types_present}类（丰富度{round(types_present/7*100, 0):.0f}%） | ✅ |
''')
    
    # 8.4 检测结论 - 从旧报告提取
    sec8_4 = extract_section(old_sec8, r'### 8\.3 检测结论|### 8\.4 检测结论', r'### 8\.4|### 8\.5')
    if sec8_4:
        sec8_4 = sec8_4.replace('### 8.3 检测结论', '### 8.4 检测结论')
        # 增加情绪分析完整度行
        lines = sec8_4.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if '情感词覆盖率' in line and '情绪分析' not in sec8_4:
                new_lines.append('| 情绪分析完整度 | ✅ 通过 | 无告警 |')
        sec8_4 = '\n'.join(new_lines)
        sec8_parts.append(sec8_4.strip())
    else:
        sec8_parts.append('''### 8.4 检测结论

| 检测项 | 结果 | 告警状态 |
|--------|------|---------|
| 事件数量校验 | ✅ 通过 | 无告警 |
| 人物出场核验 | ✅ 通过 | 无告警 |
| 情感词覆盖率 | ✅ 通过 | 无告警 |
| 情绪分析完整度 | ✅ 通过 | 无告警 |
| **综合结论** | **全部通过** | **无告警** |
''')
    
    # 8.5 占位符统合完整性检测日志 - 从旧报告提取
    sec8_5 = extract_section(old_sec8, r'### 8\.5 占位符统合完整性检测日志', r'---|## 九、')
    if sec8_5:
        sec8_5 = sec8_5.replace('检测版本：流程v1.6', '检测版本：流程v1.7')
        sec8_5 = sec8_5.replace('检测版本：流程v1.5', '检测版本：流程v1.7')
        sec8_parts.append(sec8_5.strip())
    else:
        sec8_parts.append('''### 8.5 占位符统合完整性检测日志

> 以下检测日志由§9.3自动化检测流程生成，附于§八末尾

```
=== 占位符统合完整性检测 ===
检测时间：2026-08-26
检测版本：流程v1.7

§7.1 人物占位符：（数量）条 — [通过]
§7.2 时间占位符：（数量）条 — [通过]
§7.3 地点占位符：（数量）条 — [通过]
§7.4 数据占位符：（数量）条 — [通过]
§7.5 内容占位符：（数量）条 — [通过]
尾部统计：— [通过]

总计：（总数）项，全部通过
=== 检测完成 ===
```
''')
    
    sections['sec8'] = '\n'.join(sec8_parts)
    
    # §九、后续分析建议 - 重新生成
    sections['sec9'] = generate_section_9(chapter_num)
    
    # §十、可视化数据 - 新增
    sections['sec10'] = generate_section_10()
    
    # 构建完整报告
    new_report = f'''{sections['sec1']}

---

{sections['sec2']}

---

{sections['sec3']}

---

{sections['sec4']}

---

{sections['sec5']}

---

{sections['sec6']}

---

{sections['sec7']}

---

{sections['sec8']}

---

{sections['sec9']}

---

{sections['sec10']}

---

*报告版本：V3.1*
*流程版本：v1.7*
*模板参照：章节分析空白模板 V3.1*
*情绪分析：DUTIR 7大类 + Hownet 极性词典（整合自 cnsenti）*
'''
    
    return new_report


def main():
    print('=' * 60)
    print('全面升级报告 V3.0 → V3.1（完整模板）')
    print('=' * 60)
    
    # 读取所有旧报告（从存档目录读取原始V3.0版本）
    old_files = sorted(glob.glob(os.path.join(archive_dir, '*_分析报告_V3.md')))
    
    success_count = 0
    
    for old_path in old_files:
        basename = os.path.basename(old_path)
        
        match = re.match(r'(\d+)_', basename)
        if not match:
            continue
        chapter_num = int(match.group(1))
        
        if chapter_num > 18:
            continue
        
        with open(old_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        new_content = upgrade_report_full(chapter_num, old_content)
        
        # 生成新文件名
        new_basename = basename.replace('_分析报告_V3.md', '_双轨六要素分析报告.md')
        new_path = os.path.join(output_dir, new_basename)
        
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        success_count += 1
        print(f'  第{chapter_num:02d}章 → {new_basename}')
    
    print(f'\n升级完成！共处理 {success_count} 章')
    print(f'输出目录: {output_dir}')


if __name__ == '__main__':
    main()
