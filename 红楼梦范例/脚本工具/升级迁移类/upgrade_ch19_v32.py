# -*- coding: utf-8 -*-
"""
升级第19章到V3.2：
- 新增 §4.3 冲突动机分析
- 新增 §4.4 叙事手法与章节定位
- 新增 §5.3 情感趋势分析
- 重排 §5 子章节编号
- 更新版本号 V3.1→V3.2, v1.7→v1.8
- 更新数据占位符和完整性检测
"""

import os
import re

output_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例\分析结果'

ch19_path = os.path.join(output_dir, '019_情切切良宵花解语_意绵绵静日玉生香_双轨六要素分析报告.md')

with open(ch19_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ===== §4.3 冲突动机分析 =====
sec4_3 = """本章包含三重冲突，内外交织：

| 序号 | 冲突类型 | 冲突描述 | 驱动角色 | 解决状态 |
|------|---------|---------|---------|---------|
| 1 | 人vs自我 | 宝玉天性厌弃经济仕途 vs 袭人苦心箴规走正路 | 宝玉/袭人 | 暂时妥协（宝玉一一应下，能否持久未知） |
| 2 | 人vs人 | 李嬷嬷不满丫头放肆、自己被忽视 vs 丫头们不理不睬 | 李嬷嬷/众丫头 | 袭人遮掩化解（未正面解决） |
| 3 | 人vs社会 | 宝玉个性自由 vs 封建礼教与家族期望 | 宝玉/贾府 | 长期暗线（本章以袭人箴规侧面体现） |
| 4 | 身份冲突 | 袭人奴婢身份的焦虑与不安 vs 对宝玉的深情 | 袭人 | 假说赎身试探，确认宝玉心意 |"""

# ===== §4.4 叙事手法与章节定位 =====
sec4_4 = """| 维度 | 分析 |
|------|------|
| 叙事视角 | 第三人称·限知。以宝玉视角贯穿全章，从宁府看戏到私访花家，从怡红院夜谈到潇湘馆打趣，读者随宝玉的行动轨迹感知情节。 |
| 叙事节奏 | 舒缓细腻。省亲大场面后的"文戏"章节，以对话和心理活动为主，节奏由慢→渐入佳境→温馨收束，如同工笔画。 |
| 对比手法 | ①繁华戏场（宁府唱戏）vs 寂寞书房（宝玉撞见茗烟），以闹衬静；②省亲的皇家排场 vs 儿女情长的私密细腻，以大衬小；③袭人箴规的庄重 vs 宝黛打趣的俏皮，一张一弛。 |
| 寓言嵌套 | 宝玉编"耗子精偷香芋"故事，寓言式嵌套叙事，既调侃黛玉（香玉=黛玉），又暗点全书"草蛇灰线"的叙事美学。 |
| 章节定位 | 承上启下。承接元妃省亲的宏大场面，将叙事重心从家族礼制转回宝黛钗感情线细腻刻画；"花解语"立贤袭人形象，"玉生香"显娇黛玉情态，为后文宝玉挨打、袭人进言、宝黛感情深化埋下伏笔。 |"""

# ===== §5.3 情感趋势分析 =====
sec5_3 = """本章情感曲线呈"平缓→温馨→小挫→深情→欢快→悬念"的波浪形走势：

| 段落区间 | 情感状态 | 情感基调 | 关键事件 |
|---------|---------|---------|---------|
| 第2-4段 | 中性偏闷 | 省亲余波，繁华褪后的日常 | 元妃回宫、宁府看戏、宝玉嫌闹 |
| 第5-9段 | 正面温馨 | 主仆情深，家常暖意 | 撞见茗烟、私访花家、花家招待 |
| 第10-11段 | 负面小挫 | 怡红院小风波 | 李嬷嬷骂丫头、赌气吃酥酪 |
| 第12-17段 | 正面深情 | 良宵花解语，箴规含深情 | 袭人遮掩、假说赎身、箴规三事 |
| 第18-19段 | 中性偏忧 | 温情后的小变故 | 袭人染风寒、宝玉传医 |
| 第20-24段 | 正面欢快 | 静日玉生香，儿女情长 | 宝黛同卧、暖香讥诮、耗子精故事 |
| 第25段 | 中性悬念 | 余音袅袅，留待下文 | 宝钗到来、忽闻房中吵嚷 |"""

# ===== 1. 插入 §4.3 和 §4.4 =====
# 在 §4.2 之后、## 五、之前插入
sec4_end_pattern = r'(### 4\.2 人物基准六要素表\n\n.*?)(\n\n## 五、)'
sec4_match = re.search(sec4_end_pattern, content, re.DOTALL)

if sec4_match:
    insert_text = '\n\n---\n\n### 4.3 冲突动机分析\n\n' + sec4_3
    insert_text += '\n\n---\n\n### 4.4 叙事手法与章节定位\n\n' + sec4_4
    
    new_sec4 = sec4_match.group(1) + insert_text + sec4_match.group(2)
    content = content[:sec4_match.start()] + new_sec4 + content[sec4_match.end():]
    print('✓ 插入§4.3和§4.4')
else:
    print('✗ 找不到§4.2插入位置')

# ===== 2. 重排 §5 子章节，插入 §5.3 情感趋势分析 =====
# V3.1的§5: 5.1总览, 5.2基调, 5.3与前章对比, 5.4高频词汇, 5.5处理记录, 5.6七类情绪
# V3.2的§5: 5.1总览, 5.2基调, 5.3情感趋势, 5.4与前章对比, 5.5高频词汇, 5.6处理记录, 5.7七类情绪

# 从大到小替换
content = content.replace('### 5.6.1 ', '### 5.7.1 ')
content = content.replace('### 5.6.2 ', '### 5.7.2 ')
content = content.replace('### 5.6.3 ', '### 5.7.3 ')
content = content.replace('### 5.6 七类情绪分布', '### 5.7 七类情绪分布')
content = content.replace('### 5.5 情感词处理记录', '### 5.6 情感词处理记录')
content = content.replace('### 5.4 高频词汇', '### 5.5 高频词汇')
content = content.replace('### 5.3 与前章对比', '### 5.4 与前章对比')

print('✓ 重排§5子章节编号')

# 在 §5.2 之后插入 §5.3 情感趋势分析
# 现在原5.3已经变成5.4了，找5.2结束到5.4开始的位置
sec5_2_pattern = r'(### 5\.2 情感基调判定\n\n.*?)(\n### 5\.4 与前章对比)'
sec5_2_match = re.search(sec5_2_pattern, content, re.DOTALL)

if sec5_2_match:
    insert_5_3 = '\n\n---\n\n### 5.3 情感趋势分析\n\n' + sec5_3 + '\n\n---\n\n'
    new_sec5 = sec5_2_match.group(1) + insert_5_3 + '### 5.4 与前章对比'
    content = content[:sec5_2_match.start()] + new_sec5 + content[sec5_2_match.end():]
    print('✓ 插入§5.3情感趋势分析')
else:
    print('✗ 找不到§5.2插入位置')

# ===== 3. 更新版本号 =====
content = content.replace('V3.1', 'V3.2')
content = content.replace('v1.7', 'v1.8')
print('✓ 更新版本号V3.2/v1.8')

# ===== 4. 更新数据占位符 =====
sec7_4_pattern = r'(### 7\.4 数据占位符\n\n\|.*?\n.*?\n)(.*?)(?=\n### 7\.5)'
sec7_4_match = re.search(sec7_4_pattern, content, re.DOTALL)

if sec7_4_match:
    table_content = sec7_4_match.group(2)
    rows = [l for l in table_content.strip().split('\n') if l.strip().startswith('|')]
    current_count = len(rows)
    
    new_rows = f'\n| {current_count+1} | 冲突动机数量 | 项 | 4 | §4.3 冲突动机分析 |\n'
    new_rows += f'| {current_count+2} | 叙事结构维度 | 项 | 5 | §4.4 叙事手法与章节定位 |\n'
    new_rows += f'| {current_count+3} | 情感趋势分段数 | 段 | 7 | §5.3 情感趋势分析 |'
    
    new_table = table_content.rstrip() + new_rows + '\n'
    content = content[:sec7_4_match.start(2)] + new_table + content[sec7_4_match.end(2):]
    print('✓ 更新数据占位符')

# ===== 5. 更新完整性检测 =====
sec8_3_pattern = r'(### 8\.3 完整性检测.*?\n\n\|.*?\n.*?\n)(.*?)(?=\n### 8\.4)'
sec8_3_match = re.search(sec8_3_pattern, content, re.DOTALL)

if sec8_3_match:
    table_content = sec8_3_match.group(2)
    new_items = '\n| 冲突动机分析 | 完整 | §4.3 四重冲突分析完整 | ✓ |\n'
    new_items += '| 叙事结构分析 | 完整 | §4.4 五维度叙事分析完整 | ✓ |\n'
    new_items += '| 情感趋势分析 | 完整 | §5.3 七段情感曲线完整 | ✓ |'
    
    new_table = table_content.rstrip() + new_items + '\n'
    content = content[:sec8_3_match.start(2)] + new_table + content[sec8_3_match.end(2):]
    print('✓ 更新完整性检测')

# ===== 6. 更新双轨校验中的子章节数 =====
sec8_1_pattern = r'(### 8\.1 双轨交叉校验\n\n\|.*?\n.*?\n)(.*?)(?=\n### 8\.2)'
sec8_1_match = re.search(sec8_1_pattern, content, re.DOTALL)

if sec8_1_match:
    table_content = sec8_1_match.group(2)
    table_content = table_content.replace('10大章节/35子章节', '10大章节/38子章节')
    table_content = table_content.replace('35个子章节', '38个子章节')
    content = content[:sec8_1_match.start(2)] + table_content + content[sec8_1_match.end(2):]
    print('✓ 更新双轨校验子章节数')

# 保存
with open(ch19_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n第19章V3.2升级完成！')
