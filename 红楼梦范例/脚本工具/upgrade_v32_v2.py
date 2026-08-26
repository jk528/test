# -*- coding: utf-8 -*-
"""
V3.1 → V3.2 升级脚本 v2
适配V3.0各章不同格式，提取所有有价值的文学分析内容
"""

import os
import re
import glob

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'
output_dir = os.path.join(project_dir, '分析结果')
archive_dir = os.path.join(output_dir, 'V3.0存档_1-18章')


def find_v30_file(chapter_num):
    pattern = os.path.join(archive_dir, f'{chapter_num:03d}_*_分析报告_V3.md')
    files = glob.glob(pattern)
    return files[0] if files else None


def find_v31_file(chapter_num):
    pattern = os.path.join(output_dir, f'{chapter_num:03d}_*_双轨六要素分析报告.md')
    files = glob.glob(pattern)
    files = [f for f in files if 'V3.0存档' not in f]
    return files[0] if files else None


def extract_section_by_title(content, title_pattern):
    """按标题提取章节内容，标题支持正则"""
    pattern = rf'### ({title_pattern})\n\n(.*?)(?=\n### |\n## |\n---\n\n## )'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1), match.group(2).strip()
    return None, None


def upgrade_chapter(ch):
    v30_path = find_v30_file(ch)
    v31_path = find_v31_file(ch)
    
    if not v30_path or not v31_path:
        return False, f'找不到文件'
    
    with open(v30_path, 'r', encoding='utf-8') as f:
        v30 = f.read()
    
    with open(v31_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # ===== 提取V3.0内容 =====
    
    # §4.3 冲突动机分析
    _, sec4_3 = extract_section_by_title(v30, r'4\.3 冲突动机分析')
    
    # §4.4 可能是"叙事手法详解"或"章节定位分析"
    sec4_4_title, sec4_4_content = extract_section_by_title(v30, r'4\.4 (叙事手法详解|章节定位分析)')
    
    # §5 情感趋势分析（可能在5.3或5.6位置）
    sec5_trend_title, sec5_trend = extract_section_by_title(v30, r'5\.[36] 情感趋势分析')
    
    if not sec4_3:
        return False, '缺少§4.3冲突动机分析'
    if not sec4_4_content:
        return False, '缺少§4.4内容'
    if not sec5_trend:
        return False, '缺少情感趋势分析'
    
    # ===== 1. 插入 §4.3 和 §4.4 =====
    # 在 §4.2 之后、## 五、之前插入
    
    sec4_end_pattern = r'(### 4\.2 人物基准六要素表\n\n.*?)(\n\n## 五、)'
    sec4_match = re.search(sec4_end_pattern, content, re.DOTALL)
    
    if not sec4_match:
        return False, '找不到§4.2位置'
    
    # 统一§4.4标题为"叙事结构分析"以涵盖两种内容
    # 如果是"章节定位分析"，内容不同，我们保留原始内容但统一标题
    sec4_4_display_title = '4.4 叙事手法与章节定位'
    # 如果原标题是"叙事手法详解"，我们也用统一标题
    # 内容保持原样
    
    insert_text = '\n\n---\n\n### 4.3 冲突动机分析\n\n' + sec4_3
    insert_text += '\n\n---\n\n### ' + sec4_4_display_title + '\n\n' + sec4_4_content
    
    new_sec4 = sec4_match.group(1) + insert_text + sec4_match.group(2)
    content = content[:sec4_match.start()] + new_sec4 + content[sec4_match.end():]
    
    # ===== 2. 插入 §5.3 情感趋势分析，重排后续编号 =====
    # V3.1的§5: 5.1总览, 5.2基调, 5.3与前章对比, 5.4高频词汇, 5.5处理记录, 5.6七类情绪
    # 目标V3.2的§5: 5.1总览, 5.2基调, 5.3情感趋势, 5.4与前章对比, 5.5高频词汇, 5.6处理记录, 5.7七类情绪
    
    # 从大到小替换，避免冲突
    # 5.6.1/2/3 → 5.7.1/2/3
    content = content.replace('### 5.6.1 ', '### 5.7.1 ')
    content = content.replace('### 5.6.2 ', '### 5.7.2 ')
    content = content.replace('### 5.6.3 ', '### 5.7.3 ')
    
    # 5.6 七类情绪分布 → 5.7
    content = content.replace('### 5.6 七类情绪分布', '### 5.7 七类情绪分布')
    
    # 5.5 情感词处理记录 → 5.6
    content = content.replace('### 5.5 情感词处理记录', '### 5.6 情感词处理记录')
    
    # 5.4 高频词汇 → 5.5
    content = content.replace('### 5.4 高频词汇', '### 5.5 高频词汇')
    
    # 5.3 与前章对比 → 5.4
    content = content.replace('### 5.3 与前章对比', '### 5.4 与前章对比')
    
    # 在 §5.2 之后插入新的 §5.3 情感趋势分析
    sec5_2_pattern = r'(### 5\.2 情感基调判定\n\n.*?)(\n### 5\.4 )'  # 5.3已经改成5.4了
    sec5_2_match = re.search(sec5_2_pattern, content, re.DOTALL)
    
    if not sec5_2_match:
        return False, '找不到§5.2插入位置'
    
    insert_5_3 = '\n\n---\n\n### 5.3 情感趋势分析\n\n' + sec5_trend + '\n\n---\n\n### 5.4 '
    
    new_sec5 = sec5_2_match.group(1) + insert_5_3 + content[sec5_2_match.end():]
    # 不对，上面的替换方式有问题。让我修正。
    # sec5_2_match.group(2) 是 "### 5.4 "，我需要保留后面的内容
    
    # 重新来：找到5.2结束到5.4开始之间的位置
    # 因为已经把5.3改成5.4了，所以下一个###应该是### 5.4
    
    # 让我用更简单的方式：直接在"### 5.4 与前章对比"前插入
    # 等等，上面已经替换了，现在应该是"### 5.4 与前章对比"
    # 让我重新搜索
    
    # 算了，我重新组织这部分逻辑
    
    # 先撤销之前的编号修改，重新从插入开始
    # 不对，已经修改了。让我用另一种方式。
    
    # 找到 "### 5.4 与前章对比"（原5.3改过来的）
    insert_pos = content.find('### 5.4 与前章对比')
    if insert_pos == -1:
        return False, '找不到5.4与前章对比的位置'
    
    # 在它前面插入5.3
    insert_text_5_3 = '### 5.3 情感趋势分析\n\n' + sec5_trend + '\n\n---\n\n'
    content = content[:insert_pos] + insert_text_5_3 + content[insert_pos:]
    
    # ===== 3. 更新版本号 =====
    content = content.replace('V3.1', 'V3.2')
    content = content.replace('v1.7', 'v1.8')
    
    # ===== 4. 更新数据占位符 =====
    sec7_4_pattern = r'(### 7\.4 数据占位符\n\n\|.*?\n.*?\n)(.*?)(?=\n### 7\.5)'
    sec7_4_match = re.search(sec7_4_pattern, content, re.DOTALL)
    
    if sec7_4_match:
        table_content = sec7_4_match.group(2)
        rows = [l for l in table_content.strip().split('\n') if l.strip().startswith('|')]
        current_count = len(rows)
        
        new_rows = f'\n| {current_count+1} | 冲突动机数量 | 项 | — | §4.3 冲突动机分析 |\n'
        new_rows += f'| {current_count+2} | 叙事结构维度 | 项 | — | §4.4 叙事手法与章节定位 |\n'
        new_rows += f'| {current_count+3} | 情感趋势分段数 | 段 | — | §5.3 情感趋势分析 |'
        
        new_table = table_content.rstrip() + new_rows + '\n'
        content = content[:sec7_4_match.start(2)] + new_table + content[sec7_4_match.end(2):]
    
    # ===== 5. 更新完整性检测 =====
    sec8_3_pattern = r'(### 8\.3 完整性检测.*?\n\n\|.*?\n.*?\n)(.*?)(?=\n### 8\.4)'
    sec8_3_match = re.search(sec8_3_pattern, content, re.DOTALL)
    
    if sec8_3_match:
        table_content = sec8_3_match.group(2)
        new_items = '\n| 冲突动机分析 | 完整 | §4.3 冲突分析完整 | ✓ |\n'
        new_items += '| 叙事结构分析 | 完整 | §4.4 叙事分析完整 | ✓ |\n'
        new_items += '| 情感趋势分析 | 完整 | §5.3 分段曲线完整 | ✓ |'
        
        new_table = table_content.rstrip() + new_items + '\n'
        content = content[:sec8_3_match.start(2)] + new_table + content[sec8_3_match.end(2):]
    
    # ===== 6. 更新双轨校验中的子章节数 =====
    sec8_1_pattern = r'(### 8\.1 双轨交叉校验\n\n\|.*?\n.*?\n)(.*?)(?=\n### 8\.2)'
    sec8_1_match = re.search(sec8_1_pattern, content, re.DOTALL)
    
    if sec8_1_match:
        table_content = sec8_1_match.group(2)
        table_content = table_content.replace('10大章节/35子章节', '10大章节/38子章节')
        table_content = table_content.replace('35个子章节', '38个子章节')
        content = content[:sec8_1_match.start(2)] + table_content + content[sec8_1_match.end(2):]
    
    # 保存
    with open(v31_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True, f'sec4_4={sec4_4_title}'


def main():
    print('=' * 60)
    print('V3.1 → V3.2 升级（1-18章）')
    print('=' * 60)
    
    success = 0
    failed = []
    
    for ch in range(1, 19):
        ok, info = upgrade_chapter(ch)
        if ok:
            print(f'  第{ch:02d}章：✓ 完成（{info}）')
            success += 1
        else:
            print(f'  第{ch:02d}章：✗ 失败 - {info}')
            failed.append(ch)
    
    print(f'\n{"=" * 60}')
    print(f'完成：{success}/18 章')
    if failed:
        print(f'失败章节：{failed}')


if __name__ == '__main__':
    main()
