# 目录修复工具模块
"""
目录修复工具
负责处理EPUB转换后可能出现的重复目录问题
"""

import re
from typing import List


class TOCFixer:
    """
    目录修复器类
    用于处理EPUB转换后可能出现的重复目录问题
    """
    
    @staticmethod
    def fix_duplicate_toc(content: str) -> str:
        """
        修复重复目录问题
        
        Args:
            content: 原始文本内容
        
        Returns:
            修复后的文本内容
        """
        # 分割内容为行
        lines = content.split('\n')
        
        # 处理后的行
        processed_lines = []
        
        # 标记是否正在处理章节标题部分
        processing_chapter_header = False
        # 章节标题模式
        chapter_header_pattern = re.compile(r'^=+\s+第[一二三四五六七八九十百千0-9]+[回章节卷].*=+$')
        # 标准章节标题模式
        standard_chapter_pattern = re.compile(r'^\s*第[一二三四五六七八九十百千0-9]+[回章节卷].*$')
        # 跳转标记模式
        jump_mark_pattern = re.compile(r'^\[跳转标记: \d+\]$')
        # 单行章节标题模式（如"第一回"）
        single_line_chapter_pattern = re.compile(r'^\s*第[一二三四五六七八九十百千0-9]+[回章节卷]\s*$')
        # 章节副标题模式（如"灵根育孕源流出"）
        chapter_subtitle_pattern = re.compile(r'^\s*[\u4e00-\u9fa5]+\s*$')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检查是否是分隔线行
            if line_stripped.startswith('=') and line_stripped.endswith('='):
                # 跳过分隔线
                processing_chapter_header = True
                continue
            
            # 检查是否是跳转标记行
            if jump_mark_pattern.match(line_stripped):
                # 保留跳转标记
                processed_lines.append(line)
                # 继续处理章节标题部分，跳过后续的空行和副标题
                processing_chapter_header = True
                continue
            
            # 检查是否是单行章节标题（如"第一回"）
            if single_line_chapter_pattern.match(line_stripped):
                # 跳过单行章节标题
                continue
            
            # 检查是否是章节副标题（如"灵根育孕源流出"）
            if chapter_subtitle_pattern.match(line_stripped):
                # 跳过章节副标题
                continue
            
            # 检查是否是空行
            if not line_stripped:
                # 如果正在处理章节标题部分，跳过空行
                if processing_chapter_header:
                    continue
            
            # 检查是否是标准章节标题
            if standard_chapter_pattern.match(line_stripped):
                # 保留标准章节标题
                processed_lines.append(line)
                processing_chapter_header = False
                continue
            
            # 如果不是空行，说明章节标题部分处理完成
            if line_stripped:
                processing_chapter_header = False
            
            # 添加当前行到处理后的行
            processed_lines.append(line)
        
        # 合并处理后的行
        return '\n'.join(processed_lines)
    
    @staticmethod
    def fix_file(input_file: str, output_file: str) -> bool:
        """
        修复文件中的重复目录问题
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        
        Returns:
            是否成功
        """
        try:
            # 读取文件
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复重复目录
            fixed_content = TOCFixer.fix_duplicate_toc(content)
            
            # 写入修复后的内容
            from ..utils.file_utils import FileUtils
            FileUtils.write_file_safely(output_file, fixed_content)
            
            return True
        except Exception as e:
            print(f"修复文件失败: {e}")
            return False
