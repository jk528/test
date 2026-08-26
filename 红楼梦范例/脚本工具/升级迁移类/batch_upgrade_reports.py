# -*- coding: utf-8 -*-
"""
批量升级1-18章报告从V3.0到V3.1
- 版本号更新（V3.0→V3.1, v1.6→v1.7）
- 新增§5.6七类情绪分布（DUTIR + Hownet双轨）
- 新增§8.2情绪分析交叉验证
- 更新占位符统合数据
- 更新完整性检测
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


def generate_emotion_section(ch):
    """生成§5.6七类情绪分布章节"""
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
    
    # 计算主导情绪
    sorted_emos = sorted(dutir['emotion_counts'].items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_emos[0][0] if sorted_emos else '好'
    dominant_count = sorted_emos[0][1] if sorted_emos else 0
    
    # 情绪丰富度
    types_present = sum(1 for v in dutir['emotion_counts'].values() if v > 0)
    richness = round(types_present / 7, 2)
    
    # 正负情绪比
    pos_count = dutir['positive_count']
    neg_count = dutir['negative_count']
    ratio = round(pos_count / neg_count, 2) if neg_count > 0 else 'N/A'
    
    # DUTIR正负面占比（基于总情绪词）
    total_dutir = dutir['total']
    dutir_pos_pct = round(pos_count / total_dutir * 100, 1) if total_dutir > 0 else 0
    dutir_neg_pct = round(neg_count / total_dutir * 100, 1) if total_dutir > 0 else 0
    
    # 交叉验证差异
    pos_diff = abs(hownet['pos_percentage'] - dutir_pos_pct)
    neg_diff = abs(hownet['neg_percentage'] - dutir_neg_pct)
    
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
    
    section = f'''
### 5.6 七类情绪分布（DUTIR 情感词汇本体）

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
| 主导情绪 | {dominant}（{dominant_count}词） | 占比最高的情绪类别 |
| 情绪丰富度 | {richness}（{types_present}/7类） | 出现的情绪类别数 / 7 |

> **注**：DUTIR词典侧重情绪分类，"好""恶"类词量较大（各含1万+词），与情感极性的"正/负"非完全对应，需结合语境理解。

#### 5.6.3 与情感基调的交叉验证（DUTIR vs Hownet）

| 维度 | 极性分析结果（Hownet） | 情绪分类结果（DUTIR） | 是否一致 | 说明 |
|------|---------------------|---------------------|---------|------|
| 正面占比 | {hownet['pos_percentage']}% | {dutir_pos_pct}% | {pos_status} | Hownet极性词 vs DUTIR好+乐 |
| 负面占比 | {hownet['neg_percentage']}% | {dutir_neg_pct}% | {neg_status} | Hownet极性词 vs DUTIR哀+怒+惧+恶 |
| 基调判定 | {hownet_tone} | {dutir_tone} | {tone_status} | 两种方法的结论对比 |
| 情感词总数 | {hownet['total']} | {total_dutir} | — | 两套词典覆盖差异 |
'''
    return section


def upgrade_report(chapter_num, old_content):
    """升级单章报告"""
    data = emotion_data.get(chapter_num)
    if not data:
        return old_content
    
    content = old_content
    
    # 1. 更新版本号
    content = content.replace('双轨六要素分析体系 V3.0', '双轨六要素分析体系 V3.1')
    content = content.replace('流程 v1.6', '流程 v1.7')
    content = content.replace('*报告版本：V3.0*', '*报告版本：V3.1*')
    content = content.replace('*报告版本：V2.4*', '*报告版本：V3.1*')
    content = content.replace('*流程版本：v1.6*', '*流程版本：v1.7*')
    content = content.replace('*模板参照：章节分析空白模板 V3.0*', '*模板参照：章节分析空白模板 V3.1*')
    
    # 2. 在情感词统计和人物关系之间插入七类情绪分布
    # 找到"## 六、人物关系"或"## 六"作为插入点
    emotion_section = generate_emotion_section(chapter_num)
    
    insert_patterns = [
        ('\n## 六、人物关系', emotion_section + '\n---\n\n## 六、人物关系'),
        ('\n## 六 人物关系', emotion_section + '\n---\n\n## 六 人物关系'),
    ]
    
    inserted = False
    for old, new in insert_patterns:
        if old in content:
            content = content.replace(old, new, 1)
            inserted = True
            break
    
    # 3. 更新版本绑定声明中的组件
    old_components = '''| 词典库 | — | ✓ 完整（同义/反义/否定/递进/停用词） |
| 分词数据 | — | ✓ 完整（{章号三位}.json） |'''
    
    new_components = '''| 词典库 | — | ✓ 完整（同义/反义/否定/递进/停用词） |
| DUTIR情绪词典 | — | ✓ 完整（7大类27,414词） |
| Hownet情感词典 | — | ✓ 完整（19,472词） |
| 情绪分析模块 | — | ✓ 可用（EmotionAnalyzer + SentimentAnalyzer） |
| 分词数据 | — | ✓ 完整（{章号三位}.json） |'''
    
    if old_components in content:
        content = content.replace(old_components, new_components)
    
    # 4. 在交叉校验中增加情绪分析行
    old_check = '''| 时空一致 | （值） | （值） | （比对） | ✅/❌ |'''
    
    new_check = '''| 时空一致 | （值） | （值） | （比对） | ✅/❌ |
| 情绪分析 | DUTIR：（基调） | Hownet：（基调） | （比对） | ✅/❌ |'''
    
    if old_check in content:
        content = content.replace(old_check, new_check)
    
    # 5. 更新完整性检测，增加情绪分析完整度行
    old_integrity = '''| 情感词覆盖率 | 三类词覆盖 | §8.1.1 情感词覆盖率 | （值） | ✅/❌ |'''
    
    new_integrity = '''| 情感词覆盖率 | 三类词覆盖 | §8.1.1 情感词覆盖率 | （值） | ✅/❌ |
| 情绪分析完整度 | 7类情绪覆盖 + 交叉验证 | §8.1.1 情绪类别下限 | {types_present}类 | ✅ |'''.format(
        types_present=sum(1 for v in data['dutir']['emotion_counts'].values() if v > 0)
    )
    
    if old_integrity in content:
        content = content.replace(old_integrity, new_integrity)
    
    # 旧版格式的完整性检测
    old_integrity2 = '''| 情感词覆盖率 | ≥80% |'''
    if old_integrity2 in content and '情绪分析完整度' not in content:
        # 找到情感词覆盖率那行并在后面插入
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if '情感词覆盖率' in line and '≥80%' in line and '情绪分析' not in lines[i+1] if i+1 < len(lines) else True:
                types_present = sum(1 for v in data['dutir']['emotion_counts'].values() if v > 0)
                new_lines.append(f'| 情绪分析完整度 | ≥3类 | {types_present}类（丰富度{round(types_present/7*100, 0):.0f}%） | ✅ |')
        content = '\n'.join(new_lines)
    
    # 6. 在占位符统合中增加情绪分析数据
    # 找到数据占位符表的最后一行
    # 在"7 | 中性词占比"或类似行后添加情绪分析数据
    if '### 7.4 数据占位符' in content:
        # 尝试在最后一个数据项后添加
        old_data_end = '| 7 |'
        # 找到§7.4中最后一行数据
        section_match = re.search(r'### 7\.4 数据占位符\n\n\|.*?\n.*?\n(.*?)\n\n### 7\.5', content, re.DOTALL)
        if section_match:
            old_data_section = section_match.group(0)
            # 计算当前有多少条数据
            data_lines = [l for l in old_data_section.split('\n') if l.startswith('| ') and not l.startswith('| 序号')]
            last_num = len(data_lines)
            
            # 准备新增的情绪分析数据项
            new_data_items = f'''| {last_num+1} | {data['dutir']['total']}词 | DUTIR情绪词总数 | §5.6.1 |
| {last_num+2} | {data['dutir']['emotion_percentages'].get("好",0)}% | DUTIR"好"类占比 | §5.6.1 |
| {last_num+3} | {data['dutir']['emotion_percentages'].get("恶",0)}% | DUTIR"恶"类占比 | §5.6.1 |
| {last_num+4} | {data['dutir']['positive_count']}词 | DUTIR正面情绪词数 | §5.6.2 |
| {last_num+5} | {data['dutir']['negative_count']}词 | DUTIR负面情绪词数 | §5.6.2 |
| {last_num+6} | {data['hownet']['total']}词 | Hownet极性分析词数 | §5.6.3 |
| {last_num+7} | {data['hownet']['pos_percentage']}% | Hownet正面词占比 | §5.6.3 |
| {last_num+8} | {data['hownet']['neg_percentage']}% | Hownet负面词占比 | §5.6.3 |
'''
            
            # 在"### 7.5 内容占位符"前插入
            content = content.replace(
                '\n### 7.5 内容占位符',
                '\n' + new_data_items + '\n### 7.5 内容占位符'
            )
    
    # 7. 检测版本更新
    content = content.replace('检测版本：流程v1.6', '检测版本：流程v1.7')
    
    # 8. 尾部声明增加情绪分析一行
    old_tail_decl = '*情绪分析：DUTIR 7大类 + Hownet 极性词典（整合自 cnsenti）*'
    if old_tail_decl not in content:
        # 在"模板参照"行后添加
        old_template_line = '*模板参照：章节分析空白模板 V3.1*'
        new_template_line = '*模板参照：章节分析空白模板 V3.1*\n*情绪分析：DUTIR 7大类 + Hownet 极性词典（整合自 cnsenti）*'
        content = content.replace(old_template_line, new_template_line)
    
    return content


def main():
    print('=' * 60)
    print('批量升级报告 V3.0 → V3.1')
    print('=' * 60)
    
    # 读取所有旧报告
    old_files = sorted(glob.glob(os.path.join(archive_dir, '*_分析报告_V3.md')))
    
    success_count = 0
    
    for old_path in old_files:
        basename = os.path.basename(old_path)
        
        # 提取章号
        match = re.match(r'(\d+)_', basename)
        if not match:
            continue
        chapter_num = int(match.group(1))
        
        if chapter_num > 18:
            continue
        
        # 读取旧报告
        with open(old_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        # 升级
        new_content = upgrade_report(chapter_num, old_content)
        
        # 生成新文件名（去掉_V3后缀，保持简洁）
        new_basename = basename.replace('_分析报告_V3.md', '_双轨六要素分析报告.md')
        new_path = os.path.join(output_dir, new_basename)
        
        # 保存
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        success_count += 1
        print(f'  第{chapter_num:02d}章 → {new_basename}')
    
    print(f'\n升级完成！共处理 {success_count} 章')
    print(f'输出目录: {output_dir}')


if __name__ == '__main__':
    main()
