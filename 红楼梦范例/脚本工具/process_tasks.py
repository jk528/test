# -*- coding: utf-8 -*-
"""
任务1：将所有分词JSON转换为TXT格式，保存到新文件夹
任务2：更新归档索引，添加第19章数据
"""

import json
import os
import glob

project_dir = r'c:\Users\Administrator\Documents\这是什么\JK-temp\红楼梦范例'

# ============================================
# 任务1：JSON转TXT
# ============================================
def convert_json_to_txt():
    json_dir = os.path.join(project_dir, '红楼梦_分词结果')
    txt_dir = os.path.join(project_dir, '红楼梦_分词结果_txt')
    
    os.makedirs(txt_dir, exist_ok=True)
    
    json_files = sorted(glob.glob(os.path.join(json_dir, '*.json')))
    count = 0
    
    for json_path in json_files:
        basename = os.path.basename(json_path)
        txt_name = basename.replace('.json', '.txt')
        txt_path = os.path.join(txt_dir, txt_name)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                words = json.load(f)
            
            # 写入TXT，每行一个词
            with open(txt_path, 'w', encoding='utf-8') as f:
                for word in words:
                    f.write(word + '\n')
            
            count += 1
        except Exception as e:
            print(f'  失败: {basename} - {e}')
    
    print(f'[任务1完成] 共转换 {count} 个文件')
    print(f'  源目录: {json_dir}')
    print(f'  目标目录: {txt_dir}')
    return count


# ============================================
# 任务2：更新归档索引
# ============================================
def update_archive_index():
    index_path = os.path.join(project_dir, '分析结果', '_归档索引.md')
    
    # 读取原始文件
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 第19章数据
    ch19_row = ('| 019 | 情切切良宵花解语 意绵绵静日玉生香 '
                '| 019_情切切良宵花解语_意绵绵静日玉生香_双轨六要素分析报告.md '
                '| 已归档 | 正面主导（温情含箴规） | ~51.2% | ~48.8% | — | 5★(总13) | 18 | 5 | 2026-08-26 |')
    
    # 在第18章行后插入第19章
    old_line = '| 018 | 皇恩重元妃省父母 天伦乐宝玉呈才藻 | 018_皇恩重元妃省父母_分析报告_V3.md | 已归档 | 悲喜交加 | ~33% | ~32% | ~35% | 13★(总19) | 17 | 3 | 2026-08-26 |'
    new_lines = old_line + '\n' + ch19_row
    
    if old_line in content:
        content = content.replace(old_line, new_lines)
        print('[任务2-1] 归档索引表已更新（第19章已添加）')
    else:
        print('[任务2-1] 警告：未找到第18章行，跳过索引表更新')
    
    # 更新索引统计
    old_stats = '- 已归档：18/120章\n- 待复测：0章\n- 草稿：0章\n- 未分析：102章'
    new_stats = '- 已归档：19/120章\n- 待复测：0章\n- 草稿：0章\n- 未分析：101章'
    
    if old_stats in content:
        content = content.replace(old_stats, new_stats)
        print('[任务2-2] 索引统计已更新（18→19章）')
    
    # 更新逐章累计统计 - 在第18章行后插入第19章
    old_ch18_cum = '| 018 | ~280 | ~270 | ~300 | 19 | 17 | 4520 | 5950 | 5015 | 293 | 173 |'
    # 第19章数据（基于Hownet情感词分析）
    ch19_cum = '| 019 | ~111 | ~106 | — | 13 | 18 | 4631 | 6056 | 5015 | 306 | 178 |'
    new_cum_lines = old_ch18_cum + '\n' + ch19_cum
    
    if old_ch18_cum in content:
        content = content.replace(old_ch18_cum, new_cum_lines)
        print('[任务2-3] 逐章累计统计已更新（第19章已添加）')
    
    # 更新019~020占位行
    old_placeholder = '| 019~020 | — | — | — | — | — | 4520 | 5950 | 5015 | 293 | 173 |'
    new_placeholder = '| 020~030 | — | — | — | — | — | 4631 | 6056 | 5015 | 306 | 178 |'
    
    if old_placeholder in content:
        content = content.replace(old_placeholder, new_placeholder)
        print('[任务2-4] 占位行已更新（019→020~030）')
    
    # 更新后续所有占位行的累计值
    # 旧累计：正面4520 负面5950 中性5015 事件293 人物173
    # 新累计：正面4631 负面6056 中性5015 事件306 人物178
    old_cum_values = '4520 | 5950 | 5015 | 293 | 173'
    new_cum_values = '4631 | 6056 | 5015 | 306 | 178'
    
    # 只替换占位行中的累计值（021~030及以后）
    lines = content.split('\n')
    in_cum_section = False
    replaced_count = 0
    new_lines = []
    
    for line in lines:
        if '## 三、逐章累计统计' in line:
            in_cum_section = True
        elif in_cum_section and line.startswith('## 四、'):
            in_cum_section = False
        
        # 只替换占位行（含"~"或"—"的行，且是累计表中的行）
        if in_cum_section and '|' in line and old_cum_values in line and '—' in line:
            line = line.replace(old_cum_values, new_cum_values)
            replaced_count += 1
        
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    if replaced_count > 0:
        print(f'[任务2-5] 后续占位行累计值已更新（共{replaced_count}行）')
    
    # 更新全书总计
    old_total = '| **全书总计** | — | — | — | — | — | **4520** | **5950** | **5015** | **293** | **173** |'
    new_total = '| **全书总计** | — | — | — | — | — | **4631** | **6056** | **5015** | **306** | **178** |'
    
    if old_total in content:
        content = content.replace(old_total, new_total)
        print('[任务2-6] 全书总计已更新')
    
    # 更新人物出场档案 - 添加第19章新人物
    # 第19章新出场人物：花自芳、花母、万儿（茗烟情人）
    # 花自芳和花母在第19章首次正面出场（之前可能被提及）
    # 万儿是首次出场
    
    old_person_end = '| 龄官 | 第18章 | 十二官之一，小旦 | 第78-79段 | 初登场→抗命做本角戏→元妃甚喜→第30回画蔷→第36回情悟梨香院 |'
    new_persons = old_person_end + '''
| 万儿 | 第19章 | 宁府丫鬟，茗烟情人 | 第5-6段 | 初登场→与茗烟偷情被宝玉撞见 |
| 花自芳 | 第19章 | 袭人之兄，花家掌柜 | 第7-9段 | 初登场→接待宝玉→雇车送回 |
| 花母 | 第19章 | 袭人之母 | 第7-9段 | 初登场→招待宝玉→死心不赎 |'''
    
    if old_person_end in content:
        content = content.replace(old_person_end, new_persons)
        print('[任务2-7] 人物出场档案已更新（新增万儿/花自芳/花母）')
    
    # 更新最后更新日期
    old_date = '*最后更新：2026-08-26（第8-18章归档+人物档案更新+逐章累计+伏笔追踪更新）*'
    new_date = '*最后更新：2026-08-26（第19章归档+人物档案更新+逐章累计+情绪分析整合）*'
    
    if old_date in content:
        content = content.replace(old_date, new_date)
        print('[任务2-8] 更新日期已更新')
    
    # 更新流程版本
    old_ver = '*流程版本：v1.6*'
    new_ver = '*流程版本：v1.7*'
    
    if old_ver in content:
        content = content.replace(old_ver, new_ver)
        print('[任务2-9] 流程版本已更新（v1.6→v1.7）')
    
    # 写入文件
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'\n[任务2完成] 归档索引已更新: {index_path}')


if __name__ == '__main__':
    print('=' * 60)
    print('任务1：分词JSON转TXT')
    print('=' * 60)
    count = convert_json_to_txt()
    
    print('\n' + '=' * 60)
    print('任务2：更新归档索引（第19章）')
    print('=' * 60)
    update_archive_index()
    
    print('\n' + '=' * 60)
    print('全部任务完成！')
    print('=' * 60)
