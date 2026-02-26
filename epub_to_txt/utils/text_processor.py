# 文本处理工具模块
"""
文本处理工具
负责文本的分割、格式化、排版等操作
"""

import re
from typing import List, Tuple, Optional
from ..config.settings import defaults, regex_patterns

class TextProcessor:
    """
    文本处理器
    """
    
    def __init__(self, line_split_length: int = None, merge_threshold: int = None):
        """
        初始化文本处理器
        
        Args:
            line_split_length: 长行分割长度
            merge_threshold: 文本合并阈值
        """
        self.line_split_length = line_split_length or defaults['line_split_length']
        self.merge_threshold = merge_threshold or 30
    
    def split_long_lines(self, text: str) -> List[str]:
        """
        分割长行
        
        Args:
            text: 原始文本
        
        Returns:
            分割后的文本行列表
        """
        lines = text.split('\n')
        result = []
        
        for line in lines:
            if not line:
                result.append('')
                continue
            
            # 检测前缀空格
            prefix_spaces = ''
            for char in line:
                if char == ' ':
                    prefix_spaces += ' '
                else:
                    break
            
            # 清理行内多余空格，保持文本的整洁
            content = ' '.join(line.split())
            
            # 计算可用长度
            available_length = self.line_split_length - len(prefix_spaces)
            
            if len(content) <= available_length:
                result.append(prefix_spaces + content)
                continue
            
            # 分割长行
            current_position = 0
            total_length = len(content)
            
            while current_position < total_length:
                end_position = current_position + available_length
                if end_position >= total_length:
                    segment = content[current_position:].strip()
                    if segment:
                        result.append(prefix_spaces + segment)
                    break
                
                # 尝试在标点符号后分割，优先考虑句子的完整性
                # 优先在句号、分号、冒号后分割，其次是逗号、顿号
                split_pos = -1
                # 第一优先级：句号、分号、冒号
                priority1 = ['。', '；', '：']
                # 第二优先级：逗号、顿号
                priority2 = ['，', '、']
                # 第三优先级：感叹号、问号
                priority3 = ['！', '？']
                # 第四优先级：引号、括号
                priority4 = ['"', "'", '）', '】']
                
                # 从后往前查找标点符号，按优先级顺序
                for punctuation_list in [priority1, priority2, priority3, priority4]:
                    for i in range(end_position, current_position, -1):
                        if i < total_length and content[i] in punctuation_list:
                            split_pos = i + 1
                            break
                    if split_pos != -1:
                        break
                
                # 如果没有找到标点符号，尝试在空格处分割
                if split_pos == -1:
                    split_pos = content.rfind(' ', current_position, end_position)
                    if split_pos > current_position:
                        split_pos += 1
                    else:
                        # 强制分割
                        split_pos = end_position
                
                segment = content[current_position:split_pos].strip()
                current_position = split_pos
                
                if segment:
                    result.append(prefix_spaces + segment)
        
        return result
    
    def clean_text(self, text: str) -> str:
        """
        清理文本
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        # 移除行尾空白
        lines = [line.rstrip() for line in text.split('\n')]
        
        # 清理和格式化文本
        cleaned_lines = []
        
        for line in lines:
            # 移除行首行尾空格
            cleaned_line = line.strip()
            
            # 跳过空行
            if not cleaned_line:
                continue
            
            # 清理行内多余空格
            cleaned_line = ' '.join(cleaned_line.split())
            
            # 修复标点符号位置（将行首标点移到上行末尾）
            if cleaned_line and cleaned_line[0] in '，。！？；：""（）【】':
                if cleaned_lines:
                    # 将标点添加到上一行末尾
                    cleaned_lines[-1] = cleaned_lines[-1] + cleaned_line[0]
                    # 保留剩余部分
                    if len(cleaned_line) > 1:
                        cleaned_line = cleaned_line[1:].strip()
                        if cleaned_line:
                            cleaned_lines.append(cleaned_line)
                else:
                    # 如果是第一行，直接移除行首标点
                    cleaned_line = cleaned_line[1:].strip()
                    if cleaned_line:
                        cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(cleaned_line)
        
        # 智能合并行（优化版）
        merged_lines = []
        i = 0
        
        while i < len(cleaned_lines):
            current_line = cleaned_lines[i]
            
            # 检查是否需要合并后续行
            if i + 1 < len(cleaned_lines):
                next_line = cleaned_lines[i + 1]
                
                # 情况1：当前行以逗号或顿号结尾，下一行是短行
                if current_line and current_line[-1] in '，、' and len(next_line) < self.merge_threshold:
                    merged = current_line + ' ' + next_line
                    merged_lines.append(merged)
                    i += 2  # 跳过下一行
                    continue
                
                # 情况2：当前行很短（可能是被分割的词语）
                elif len(current_line) < 10 and len(next_line) < 20:
                    # 检查是否为词语分割
                    merged = current_line + next_line
                    merged_lines.append(merged)
                    i += 2  # 跳过下一行
                    continue
                
                # 情况3：诗歌处理（短行且以标点结尾）
                elif len(current_line) < 20 and current_line and current_line[-1] in '，。！？；：':
                    # 尝试合并后续短行
                    merged = current_line
                    j = i + 1
                    while j < len(cleaned_lines) and len(cleaned_lines[j]) < 20:
                        next_line_poem = cleaned_lines[j]
                        if next_line_poem and next_line_poem[-1] in '。！？':
                            merged += ' ' + next_line_poem
                            i = j
                            break
                        elif next_line_poem:
                            merged += ' ' + next_line_poem
                        j += 1
                    merged_lines.append(merged)
                    i += 1
                    continue
            
            # 普通行，直接添加
            merged_lines.append(current_line)
            i += 1
        
        # 保留空行，作为段落分隔
        final_lines = []
        last_was_empty = False
        
        for line in merged_lines:
            if line.strip():
                final_lines.append(line)
                last_was_empty = False
            else:
                if not last_was_empty:
                    final_lines.append('')
                    last_was_empty = True
        
        return '\n'.join(final_lines)
    
    def optimize_poetry_format(self, text: str) -> str:
        """
        优化诗歌排版
        
        Args:
            text: 原始文本
        
        Returns:
            优化排版后的文本
        """
        lines = text.split('\n')
        optimized_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测诗歌段落
            if line:
                # 检查是否为诗歌的开始
                if any(pattern in line for pattern in ['诗曰', '词曰', '但见他', '有诗为证', '诗云', '真个是：']):
                    # 诗歌引言，保留原样
                    optimized_lines.append(lines[i])
                    i += 1
                    
                    # 收集诗歌行
                    poetry_lines = []
                    j = i
                    while j < len(lines):
                        poetry_line = lines[j].strip()
                        if poetry_line:
                            poetry_lines.append(poetry_line)
                            j += 1
                        else:
                            break
                    
                    # 优化诗歌排版
                    if poetry_lines:
                        # 合并行内的标点符号
                        merged_poetry = []
                        current_line = ''
                        
                        for pl in poetry_lines:
                            if pl.startswith('，') or pl.startswith('。') or pl.startswith('！') or pl.startswith('？') or pl.startswith('；'):
                                if current_line:
                                    current_line += pl
                                else:
                                    # 如果current_line为空，可能是前面的内容被丢失了
                                    # 暂时保存该行，等待后续处理
                                    if merged_poetry:
                                        # 将该行添加到前一行的末尾
                                        merged_poetry[-1] += pl
                                    else:
                                        # 如果merged_poetry也为空，说明这是诗歌的第一行
                                        # 直接添加该行
                                        merged_poetry.append(pl)
                            else:
                                if current_line:
                                    merged_poetry.append(current_line)
                                current_line = pl
                        
                        if current_line:
                            merged_poetry.append(current_line)
                        
                        # 添加缩进和格式化
                        for pl in merged_poetry:
                            optimized_lines.append('    ' + pl)
                        
                        # 添加空行
                        optimized_lines.append('')
                    
                    i = j
                    continue
                
                # 检测可能的诗歌行
                elif (line.endswith('，') or line.endswith('。') or line.endswith('！') or line.endswith('？') or line.endswith('；')):
                    # 检查是否为诗歌的一部分
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and (next_line.endswith('，') or next_line.endswith('。') or next_line.endswith('！') or next_line.endswith('？') or next_line.endswith('；')):
                            # 收集诗歌行，向前搜索诗歌的真正开始
                            poetry_lines = []
                            # 向前搜索，找到诗歌的真正开始
                            k = i
                            while k >= 0:
                                prev_line = lines[k].strip()
                                if prev_line:
                                    # 检查前一行是否可能是诗歌的开始
                                    if not (prev_line.startswith('，') or prev_line.startswith('。') or prev_line.startswith('！') or prev_line.startswith('？') or prev_line.startswith('；')):
                                        # 前一行不是以标点开头，可能是诗歌的开始
                                        poetry_lines.insert(0, prev_line)
                                        break
                                    else:
                                        # 前一行是以标点开头，可能是诗歌的一部分
                                        poetry_lines.insert(0, prev_line)
                                else:
                                    # 遇到空行，停止向前搜索
                                    break
                                k -= 1
                            
                            # 如果没有找到诗歌的开始，使用当前行
                            if not poetry_lines:
                                poetry_lines = [line]
                            
                            # 向后收集诗歌行
                            j = i + 1
                            while j < len(lines):
                                pl = lines[j].strip()
                                if pl and (pl.endswith('，') or pl.endswith('。') or pl.endswith('！') or pl.endswith('？') or pl.endswith('；')):
                                    poetry_lines.append(pl)
                                    j += 1
                                else:
                                    break
                            
                            # 合并行内的标点符号
                            merged_poetry = []
                            current_line = ''
                            
                            for pl in poetry_lines:
                                if pl.startswith('，') or pl.startswith('。') or pl.startswith('！') or pl.startswith('？') or pl.startswith('；'):
                                    if current_line:
                                        current_line += pl
                                    else:
                                        merged_poetry.append(pl)
                                else:
                                    if current_line:
                                        merged_poetry.append(current_line)
                                    current_line = pl
                            
                            if current_line:
                                merged_poetry.append(current_line)
                            
                            # 添加缩进和格式化
                            for pl in merged_poetry:
                                optimized_lines.append('    ' + pl)
                            
                            # 添加空行
                            optimized_lines.append('')
                            
                            i = j
                            continue
            
            optimized_lines.append(lines[i])
            i += 1
        
        return '\n'.join(optimized_lines)
    
    def optimize_chapter_title(self, title: str) -> str:
        """
        优化章节标题
        
        Args:
            title: 原始标题
        
        Returns:
            优化后的标题
        """
        # 清理标题
        cleaned_title = title.strip()
        
        # 移除方括号
        if cleaned_title.startswith('【') and cleaned_title.endswith('】'):
            cleaned_title = cleaned_title[1:-1].strip()
        elif cleaned_title.startswith('"') and cleaned_title.endswith('"'):
            cleaned_title = cleaned_title[1:-1].strip()
        
        # 在章节编号后添加空格
        patterns = [
            (r'(第[一二三四五六七八九十百千]+[回章节卷])', r'\1 '),
            (r'(第\d+[回章节卷])', r'\1 '),
            (r'(卷[一二三四五六七八九十百千]+)', r'\1 '),
            (r'(卷\d+)', r'\1 '),
            (r'([一二三四五六七八九十百千]+[回章节卷])', r'\1 ')
        ]
        
        for pattern, replacement in patterns:
            cleaned_title = re.sub(pattern, replacement, cleaned_title)
        
        # 清理多余空格
        cleaned_title = ' '.join(cleaned_title.split())
        
        return cleaned_title
    
    def format_chapter_text(self, title: str, content: str, jump_mark: Optional[str] = None) -> str:
        """
        格式化章节文本
        
        Args:
            title: 章节标题
            content: 章节内容
            jump_mark: 跳转标记
        
        Returns:
            格式化后的章节文本
        """
        optimized_title = self.optimize_chapter_title(title)
        
        # 创建章节格式
        chapter_lines = []
        
        # 只有当标题不为空时，才生成章节标题部分
        if optimized_title:
            chapter_lines.append('\n' + '=' * 120)
            chapter_lines.append(' ' * 50 + optimized_title)
            chapter_lines.append('=' * 120)
            
            if jump_mark:
                chapter_lines.append(f'[跳转标记: {jump_mark}]')
            
            chapter_lines.append('')
            chapter_lines.append('【正文开始】')
            chapter_lines.append('')
            chapter_lines.append(content)
            chapter_lines.append('')
            chapter_lines.append('【本章结束】')
            chapter_lines.append('')
        else:
            # 如果标题为空，直接返回内容
            chapter_lines.append(content)
        
        return '\n'.join(chapter_lines)
