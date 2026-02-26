# 核心转换模块
"""
核心转换模块
负责EPUB文件到TXT文件的转换
"""

import os
import datetime
import re
from typing import List, Optional, Callable, Dict, Any
from bs4 import BeautifulSoup
from ebooklib import epub

from ..config.settings import defaults, constants
from ..exceptions import (
    FileNotFoundError, DirectoryNotFoundError, PermissionError,
    EncodingError, InvalidEPUBError, MemoryError
)
from ..utils.text_processor import TextProcessor
from ..utils.file_utils import FileUtils
from ..utils.zip_utils import ZipUtils

class EPUBConverter:
    """
    EPUB转换器类
    """
    
    def __init__(self):
        """
        初始化转换器
        """
        self.text_processor = TextProcessor()
    
    def convert_with_epub2txt(self, epub_path: str, output_path: str) -> bool:
        """
        使用epub2txt库转换EPUB
        
        Args:
            epub_path: EPUB文件路径
            output_path: 输出TXT文件路径
        
        Returns:
            是否成功
        """
        try:
            from epub2txt import epub2txt
            
            text = epub2txt(epub_path)
            FileUtils.write_file_safely(output_path, text)
            
            return True
        except ImportError:
            print("错误：epub2txt库未安装，请运行 'pip install epub2txt'")
            return False
        except Exception as e:
            print(f"转换失败：{str(e)}")
            return False
    
    def convert_with_ebooklib(
        self,
        epub_path: str,
        output_path: str,
        generate_jump_marks: bool = True,
        split_into_multiple_files: bool = False,
        multi_book_split_mode: str = 'merge',
        progress_callback: Optional[Callable[[float, str], None]] = None,
        split_by_size: bool = False,
        max_file_size: int = None,
        output_zip: bool = False,
        zip_split: bool = False,
        line_split_length: int = None,
        compress_level: int = 9,
        merge_threshold: int = None,
        poetry_format: bool = True,
        chapter_title_optimize: bool = True,
        pure_read: bool = False,
        sort_chapters: bool = True
    ) -> bool:
        """
        使用ebooklib转换EPUB
        
        Args:
            epub_path: EPUB文件路径
            output_path: 输出TXT文件路径
            generate_jump_marks: 是否生成跳转标记
            split_into_multiple_files: 是否拆分多文件
            multi_book_split_mode: 多书籍拆分模式
            progress_callback: 进度回调函数
            split_by_size: 是否按大小分割
            max_file_size: 最大文件大小
            output_zip: 是否输出ZIP
            zip_split: 是否分割压缩
            line_split_length: 长行分割长度
            compress_level: 压缩级别（0-9，0=无压缩，9=最高压缩）
            merge_threshold: 文本合并阈值
            poetry_format: 是否优化诗歌排版
        chapter_title_optimize: 是否优化章节标题
        pure_read: 是否使用纯净读取模式（保留原EPUB排版）
        sort_chapters: 是否对章节进行排序
        
        Returns:
            是否成功
        """
        try:
            # 检查文件存在
            if not os.path.exists(epub_path):
                raise FileNotFoundError(epub_path)
            
            if progress_callback:
                progress_callback(10, "分析EPUB文件...")
            
            # 读取EPUB文件
            book = epub.read_epub(epub_path)
            
            if progress_callback:
                progress_callback(20, "解析EPUB结构...")
            
            # 提取书籍信息
            book_info = self._extract_book_info(book)
            
            if progress_callback:
                progress_callback(30, "提取目录信息...")
            
            # 提取目录
            toc_items = self._extract_toc(book)
            
            if progress_callback:
                progress_callback(40, "提取章节内容...")
            
            # 创建文本处理器实例，使用传递的排版参数
            text_processor = TextProcessor(
                line_split_length, 
                merge_threshold
            )
            
            # 提取章节内容（临时跳转标记）
            chapter_contents = self._extract_chapters(
                book, 
                False,  # 先不生成跳转标记
                line_split_length,
                text_processor,
                poetry_format,
                chapter_title_optimize,
                pure_read
            )
            
            # 无论是否排序，都进行去重处理，避免章节重复
            # 对目录项进行去重
            unique_toc_items = []
            seen_toc = set()
            for item in toc_items:
                if item not in seen_toc:
                    seen_toc.add(item)
                    unique_toc_items.append(item)
            toc_items = unique_toc_items
            
            # 对章节内容进行去重（基于章节编号）
            def get_chapter_number(chapter: str) -> int:
                """
                提取章节编号
                """
                # 匹配中文数字和阿拉伯数字，添加对"两"和"零"的支持
                match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', chapter)
                if match:
                    number_str = match.group(1)
                    # 转换中文数字为阿拉伯数字
                    if number_str.isdigit():
                        return int(number_str)
                    else:
                        # 增强的中文数字转换
                        return self._chinese_to_arabic(number_str)
                return 9999  # 非章节内容返回一个大数字，放在最后
            
            # 去重章节内容
            chapter_dict = {}
            for chapter in chapter_contents:
                if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', chapter):
                    chapter_num = get_chapter_number(chapter)
                    # 保留内容最完整的章节
                    if chapter_num not in chapter_dict or len(chapter) > len(chapter_dict[chapter_num]):
                        chapter_dict[chapter_num] = chapter
                else:
                    # 非章节内容直接添加
                    chapter_dict[len(chapter_dict)] = chapter
            
            # 根据参数决定是否对章节进行排序
            if sort_chapters:
                # 对目录项进行排序
                toc_items = self._sort_toc_items(toc_items)
                # 对章节内容进行排序
                chapter_contents = [chapter_dict[num] for num in sorted(chapter_dict.keys())]
            else:
                # 不排序，保持原始顺序，但去重
                chapter_contents = list(chapter_dict.values())
            
            # 从章节内容提取目录，确保不遗漏任何章节
            if chapter_contents:
                extracted_toc = self._extract_toc_from_chapters(chapter_contents)
                # 合并目录并基于章节编号去重
                if extracted_toc:
                    # 合并两个目录列表
                    combined_toc = toc_items + extracted_toc
                    # 基于章节编号去重
                    seen_chapter_numbers = set()
                    toc_items = []
                    for item in combined_toc:
                        # 提取章节编号
                        match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', item)
                        if match:
                            number_str = match.group(1)
                            # 转换为阿拉伯数字用于去重
                            if number_str.isdigit():
                                chapter_num = int(number_str)
                            else:
                                chapter_num = self._chinese_to_arabic(number_str)
                            
                            # 基于章节编号去重
                            if chapter_num not in seen_chapter_numbers:
                                seen_chapter_numbers.add(chapter_num)
                                toc_items.append(item)
            
            # 统一处理跳转标记，确保目录和章节内容对应
            if generate_jump_marks and toc_items and chapter_contents:
                # 为目录和章节内容重新分配跳转标记
                toc_items, chapter_contents = self._align_jump_marks(toc_items, chapter_contents)
            
            if progress_callback:
                progress_callback(50, "处理文本内容...")
            
            # 检测多书籍
            is_multi_book = self._detect_multi_book(book)
            
            if split_into_multiple_files:
                # 拆分多文件模式
                # 使用用户指定的输出目录，而不是基于输入文件名生成
                output_dir = os.path.dirname(output_path)
                # 如果output_path是一个文件名而不是路径，使用当前目录
                if not output_dir:
                    output_dir = os.getcwd()
                # 使用输入文件名作为子目录名
                subdir_name = os.path.splitext(os.path.basename(output_path))[0]
                output_dir = os.path.join(output_dir, subdir_name)
                
                self._split_into_multiple_files(
                    output_dir, 
                    book_info, 
                    toc_items, 
                    chapter_contents,
                    is_multi_book,
                    multi_book_split_mode,
                    progress_callback
                )
            else:
                # 单文件模式
                final_content = self._generate_single_file(
                    book_info, 
                    toc_items, 
                    chapter_contents,
                    is_multi_book,
                    generate_jump_marks
                )
                FileUtils.write_file_safely(output_path, final_content)
            
            if progress_callback:
                progress_callback(80, "整理输出文件...")
            
            # 处理文本分割
            split_files = []
            if split_by_size:
                split_files = self._handle_split_by_size(
                    output_path, 
                    max_file_size or defaults['max_file_size']
                )
            
            # 处理压缩
            # 只有明确选择了"以ZIP格式输出"时才生成压缩文件
            if output_zip:
                self._handle_compression(
                    output_path, 
                    split_files, 
                    zip_split,
                    compress_level
                )
            
            if progress_callback:
                progress_callback(100, "转换完成！")
            
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"错误：{str(e)}")
            print(f"转换失败：{str(e)}")
            return False
    
    def _extract_book_info(self, book: epub.EpubBook) -> Dict[str, str]:
        """
        提取书籍信息
        """
        title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '未知'
        author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '未知'
        
        return {
            'title': title,
            'author': author,
            'conversion_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _extract_toc(self, book: epub.EpubBook) -> List[str]:
        """
        提取目录
        """
        toc_items = []
        nav_items = []
        
        # 搜索导航文件
        for item in book.get_items():
            item_name = item.get_name() or ''
            item_type = item.get_type()
            
            if item_type == epub.EpubNav:
                nav_items.append(item)
            elif 'toc.ncx' in item_name.lower():
                nav_items.append(item)
            elif 'nav' in item_name.lower() and (item_name.endswith('.html') or item_name.endswith('.xhtml')):
                nav_items.append(item)
        
        # 解析导航文件
        for nav_item in nav_items:
            try:
                content = nav_item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                
                # 提取导航项
                for a in soup.find_all('a', href=True):
                    title = a.get_text(strip=True)
                    if title and len(title) > 2:
                        # 过滤非目录项（如出版信息、版权信息等）
                        if not self._is_non_toc_item(title):
                            toc_items.append(title)
            except Exception:
                continue
        
        return toc_items
    
    def _sort_toc_items(self, toc_items: List[str]) -> List[str]:
        """
        对目录项按章节编号排序并去重
        
        Args:
            toc_items: 目录项列表
        
        Returns:
            排序并去重后的目录项列表
        """
        def get_chapter_number(item: str) -> int:
            """
            提取章节编号
            """
            # 匹配中文数字和阿拉伯数字，添加对"两"和"零"的支持
            match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', item)
            if match:
                number_str = match.group(1)
                # 转换中文数字为阿拉伯数字
                if number_str.isdigit():
                    chapter_num = int(number_str)
                else:
                    # 增强的中文数字转换
                    chapter_num = self._chinese_to_arabic(number_str)

                return chapter_num
            return 9999  # 非章节内容返回一个大数字，放在最后
        
        # 按章节编号排序
        sorted_items = sorted(toc_items, key=get_chapter_number)
        
        # 过滤掉非章节内容并去重（基于章节编号）
        filtered_items = []
        seen_chapter_numbers = set()
        
        for item in sorted_items:
            if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', item):
                chapter_num = get_chapter_number(item)
                if chapter_num not in seen_chapter_numbers:
                    seen_chapter_numbers.add(chapter_num)
                    filtered_items.append(item)
        
        return filtered_items
    
    def _is_non_toc_item(self, item: str) -> bool:
        """
        判断是否为非目录项
        """
        # 常见的非目录项模式
        non_toc_patterns = [
            r'\d+年\d+月第\d+版',  # 出版信息
            r'\d+年\d+月第\d+次发行',  # 发行信息
            r'版权所有',
            r'©',
            r'ISBN',
            r'出版者',
            r'出版社',
            r'定价:',
            r'字数:',
            r'印数:'
        ]
        
        for pattern in non_toc_patterns:
            if re.search(pattern, item):
                return True
        
        return False
    
    def _align_jump_marks(self, toc_items: List[str], chapter_contents: List[str]) -> tuple:
        """
        对齐目录和章节内容的跳转标记
        
        Args:
            toc_items: 目录项列表
            chapter_contents: 章节内容列表
        
        Returns:
            (对齐后的目录项列表, 对齐后的章节内容列表)
        """
        aligned_chapters = []
        
        # 过滤掉非章节内容的目录项
        filtered_toc = []
        for item in toc_items:
            if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', item):
                filtered_toc.append(item)
        
        # 确保目录项和章节内容数量一致
        # 不再截断章节内容，而是确保目录项数量与章节内容数量匹配
        if len(filtered_toc) < len(chapter_contents):
            # 提取已有的章节编号，用于去重
            existing_chapter_numbers = set()
            for item in filtered_toc:
                match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', item)
                if match:
                    number_str = match.group(1)
                    if number_str.isdigit():
                        chapter_num = int(number_str)
                    else:
                        chapter_num = self._chinese_to_arabic(number_str)
                    existing_chapter_numbers.add(chapter_num)
            
            # 如果目录项数量少于章节内容数量，尝试从章节内容中提取缺失的目录项
            for i in range(len(filtered_toc), len(chapter_contents)):
                chapter = chapter_contents[i]
                # 尝试从章节内容中提取标题
                for line in chapter.split('\n'):
                    line = line.strip()
                    match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', line)
                    if match:
                        # 提取章节编号
                        number_str = match.group(1)
                        if number_str.isdigit():
                            chapter_num = int(number_str)
                        else:
                            chapter_num = self._chinese_to_arabic(number_str)
                        
                        # 检查是否已经存在相同章节编号的目录项
                        if chapter_num not in existing_chapter_numbers:
                            # 清理标题
                            cleaned_title = re.sub(r'[^\u4e00-\u9fa50-9一二两三四五六七八九十百千零回章节卷\s]', '', line).strip()
                            if cleaned_title and len(cleaned_title) > 2:
                                filtered_toc.append(cleaned_title)
                                existing_chapter_numbers.add(chapter_num)
                                print(f"为章节 {i+1} 添加目录项: {cleaned_title}")
                                break
        
        # 确保目录项数量不超过章节内容数量
        if len(filtered_toc) > len(chapter_contents):
            filtered_toc = filtered_toc[:len(chapter_contents)]
        
        # 为每个章节分配对应的跳转标记（基于章节编号）
        # 为每个章节添加跳转标记
        for chapter in chapter_contents:
            # 清理章节内容中的所有跳转标记
            lines = chapter.split('\n')
            cleaned_lines = []
            
            # 第一遍：清理所有跳转标记
            temp_lines = []
            for line in lines:
                if '[跳转标记:' not in line:
                    temp_lines.append(line)
            
            # 第二遍：添加正确的跳转标记
            title_added = False
            chapter_num = None
            
            # 重新构建章节内容，添加跳转标记
            for line in temp_lines:
                if re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', line) and not title_added:
                    # 添加章节标题行
                    cleaned_lines.append(line)
                    
                    # 提取章节编号并使用它作为跳转标记
                    match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', line)
                    if match:
                        number_str = match.group(1)
                        # 转换中文数字为阿拉伯数字
                        if number_str.isdigit():
                            chapter_num = int(number_str)
                        else:
                            # 增强的中文数字转换
                            chapter_num = self._chinese_to_arabic(number_str)
                        # 直接使用章节编号作为跳转标记
                        cleaned_lines.append(f'[跳转标记: {chapter_num}]')
                    else:
                        # 如果无法提取章节编号，使用默认索引
                        chapter_idx = len(aligned_chapters) + 1
                        cleaned_lines.append(f'[跳转标记: {chapter_idx}]')
                        chapter_num = chapter_idx
                    title_added = True
                else:
                    # 添加普通内容行
                    cleaned_lines.append(line)
            

            
            # 重新组合章节内容
            aligned_chapters.append('\n'.join(cleaned_lines))
        

        
        # 返回过滤后的目录项和对齐后的章节内容
        return filtered_toc, aligned_chapters
    
    def _extract_chapters(
        self,
        book: epub.EpubBook,
        generate_jump_marks: bool,
        line_split_length: Optional[int],
        text_processor: Optional[TextProcessor] = None,
        poetry_format: bool = True,
        chapter_title_optimize: bool = True,
        pure_read: bool = False
    ) -> List[str]:
        """
        提取章节内容
        """
        chapters = []
        content_count = 0
        
        # 使用传递的文本处理器或默认实例
        processor = text_processor or self.text_processor
        
        for item in book.get_items():
            item_type = item.get_type()
            item_name = item.get_name() or ''
            
            # 检查是否为内容文件
            is_content = False
            if item_type == epub.EpubHtml:
                is_content = True
            elif item_name.endswith(('.html', '.xhtml', '.htm')):
                is_content = True
            
            # 跳过目录文件
            if is_content:
                # 检查是否为目录文件
                item_name_lower = item_name.lower()
                if any(keyword in item_name_lower for keyword in ['toc', 'nav', '目录', 'contents', 'content']):
                    print(f"跳过目录文件: {item_name}")
                    is_content = False
            
            if is_content:
                content_count += 1
                try:
                    # 提取内容
                    content = item.get_content()
                    
                    # 尝试不同编码
                    decoded_content = None
                    for encoding in defaults['fallback_encodings']:
                        try:
                            decoded_content = content.decode(encoding)
                            break
                        except:
                            continue
                    
                    if not decoded_content:
                        decoded_content = content.decode('utf-8', errors='ignore')
                    
                    # 解析HTML
                    soup = BeautifulSoup(decoded_content, 'html.parser')
                    
                    # 提取标题
                    chapter_title = self._extract_chapter_title(soup)
                    
                    # 提取文本，确保完整提取所有内容
                    raw_text = ''
                    if pure_read:
                        # 纯净读取模式：尽可能保留原EPUB的排版
                        # 使用更保守的文本提取方法，保留段落结构
                        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'br']):
                            if element.name == 'br':
                                raw_text += '\n'
                            else:
                                text = element.get_text(separator=' ', strip=False)
                                if text:
                                    raw_text += text + '\n'
                        # 如果没有找到上述元素，使用原始方法
                        if not raw_text:
                            raw_text = soup.get_text(separator='\n', strip=False)
                        
                        # 纯净读取模式：最小化文本处理，保留原始排版
                        processed_text = raw_text
                    else:
                        # 标准模式：使用更全面的文本提取方法
                        # 先提取所有段落和标题
                        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
                            text = element.get_text(separator=' ', strip=True)
                            if text:
                                raw_text += text + '\n'
                        # 如果没有找到上述元素，使用原始方法
                        if not raw_text:
                            raw_text = soup.get_text(separator='\n', strip=True)
                        
                        # 处理文本
                        processed_text = self._process_chapter_text(raw_text, line_split_length, processor)
                        
                        # 优化诗歌排版
                        if poetry_format:
                            processed_text = processor.optimize_poetry_format(processed_text)
                    
                    # 格式化章节，不生成跳转标记，跳转标记会在 _align_jump_marks 中统一处理
                    # 从处理后的文本中提取标题，避免使用数字章节标题格式
                    extracted_title = chapter_title
                    if not extracted_title:
                        # 尝试从处理后的文本中提取标题
                        for line in processed_text.split('\n'):
                            line_stripped = line.strip()
                            if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', line_stripped):
                                extracted_title = line_stripped
                               
                               
                               
                    

                    
                    if pure_read:
                        # 纯净读取模式：简单格式化，保留原始内容
                        chapter_text = processed_text
                    else:
                        # 标准模式：使用完整的格式化
                        if extracted_title:
                            chapter_text = processor.format_chapter_text(
                                extracted_title,
                                processed_text,
                                None  # 不生成跳转标记
                            )
                        else:
                            # 如果没有找到标题，使用空标题
                            chapter_text = processor.format_chapter_text(
                                "",
                                processed_text,
                                None  # 不生成跳转标记
                            )
                    
                    chapters.append(chapter_text)
                except Exception as e:
                    # 增加错误处理，确保即使出错也能继续处理其他章节
                    print(f"提取章节内容时出错: {str(e)}")
                    continue
        
        return chapters
    
    def _chinese_to_arabic(self, chinese_num: str) -> int:
        """
        将中文数字转换为阿拉伯数字
        
        Args:
            chinese_num: 中文数字字符串
        
        Returns:
            对应的阿拉伯数字
        """
        # 基本数字，添加对"两"的支持
        num_map = {
            '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
        }
        # 单位
        unit_map = {
            '十': 10, '百': 100, '千': 1000, '万': 10000
        }
        
        # 处理纯数字情况（如"两零零"、"一二三"）
        if all(char in num_map for char in chinese_num):
            result = 0
            for char in chinese_num:
                result = result * 10 + num_map[char]
            return result
        
        # 处理包含"零"的情况，如"一百零一"、"一百一十"等
        if '零' in chinese_num:
            # 分割数字
            parts = chinese_num.split('零')
            if len(parts) > 1:
                # 计算前半部分
                front = 0
                temp_front = 0
                for char in parts[0]:
                    if char in num_map:
                        temp_front = num_map[char]
                    elif char in unit_map:
                        unit = unit_map[char]
                        front += temp_front * unit
                        temp_front = 0
                if temp_front > 0:
                    front += temp_front
                
                # 计算后半部分
                back = 0
                temp_back = 0
                for char in parts[1]:
                    if char in num_map:
                        temp_back = num_map[char]
                    elif char in unit_map:
                        unit = unit_map[char]
                        back += temp_back * unit
                        temp_back = 0
                if temp_back > 0:
                    back += temp_back
                
                # 组合结果
                return front + back
        
        # 处理特殊情况
        if chinese_num == '十':
            return 10
        
        # 处理普通中文数字
        result = 0
        temp = 0
        
        for char in chinese_num:
            if char in num_map:
                temp = num_map[char]
            elif char in unit_map:
                unit = unit_map[char]
                if temp == 0:
                    # 处理类似"十"、"百"这样的情况
                    if unit == 10:
                        temp = 1
                result += temp * unit
                temp = 0
        
        # 处理最后一个数字（没有单位的情况）
        if temp > 0:
            result += temp
        
        return result
    
    def _sort_chapters(self, chapters: List[str]) -> List[str]:
        """
        对章节内容按章节编号排序并去重
        
        Args:
            chapters: 章节内容列表
        
        Returns:
            排序并去重后的章节内容列表
        """
        def get_chapter_number(chapter: str) -> int:
            """
            提取章节编号
            """
            # 匹配中文数字和阿拉伯数字，添加对"两"和"零"的支持
            match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', chapter)
            if match:
                number_str = match.group(1)
                # 转换中文数字为阿拉伯数字
                if number_str.isdigit():
                    return int(number_str)
                else:
                    # 增强的中文数字转换
                    return self._chinese_to_arabic(number_str)
            return 9999  # 非章节内容返回一个大数字，放在最后
        
        # 按章节编号排序
        sorted_chapters = sorted(chapters, key=get_chapter_number)
        
        # 过滤掉非章节内容并去重（基于章节编号），保留内容最完整的章节
        chapter_dict = {}
        
        for chapter in sorted_chapters:
            if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', chapter):
                chapter_num = get_chapter_number(chapter)
                # 保留内容最完整的章节
                if chapter_num not in chapter_dict or len(chapter) > len(chapter_dict[chapter_num]):
                    chapter_dict[chapter_num] = chapter
        
        # 按章节编号排序
        filtered_chapters = [chapter_dict[num] for num in sorted(chapter_dict.keys())]
        
        return filtered_chapters
    
    def _extract_chapter_title(self, soup: BeautifulSoup) -> str:
        """
        提取章节标题
        """
        for level in range(1, 7):
            title_tag = soup.find(f'h{level}')
            if title_tag:
                return title_tag.get_text(strip=True)
        return ""
    
    def _process_chapter_text(self, text: str, line_split_length: Optional[int], text_processor: Optional[TextProcessor] = None) -> str:
        """
        处理章节文本
        """
        # 使用传递的文本处理器或默认实例
        processor = text_processor or self.text_processor
        
        # 清理文本
        cleaned = processor.clean_text(text)
        
        # 分割长行
        if line_split_length:
            processor.line_split_length = line_split_length
        
        # 确保完整处理所有文本，不截断
        split_lines = processor.split_long_lines(cleaned)
        processed_text = '\n'.join(split_lines)
        
        # 验证处理后的文本长度，确保没有丢失内容
        if len(processed_text) < len(cleaned) * 0.9:  # 确保至少保留90%的内容
            print(f"警告：文本处理后内容减少较多，原始长度: {len(cleaned)}, 处理后长度: {len(processed_text)}")
            # 如果内容减少过多，返回原始清理后的文本
            return cleaned
        
        return processed_text
    
    def _extract_toc_from_chapters(self, chapters: List[str]) -> List[str]:
        """
        从章节内容提取目录
        """
        toc_items = []
        seen_chapter_numbers = set()  # 基于章节编号去重
        
        for chapter in chapters:
            # 查找标题行
            lines = chapter.split('\n')
            for line in lines:  # 检查所有行
                line = line.strip()
                # 检查是否为章节标题格式
                chapter_match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', line)
                if chapter_match:
                    # 提取章节编号
                    number_str = chapter_match.group(1)
                    # 转换为阿拉伯数字用于去重
                    if number_str.isdigit():
                        chapter_num = int(number_str)
                    else:
                        chapter_num = self._chinese_to_arabic(number_str)
                    
                    # 提取完整的章节标题，包括章节编号和标题文本
                    # 匹配从"第"开始到第一个标点符号或行尾的内容
                    # 确保能匹配"第一百零一章时机已到！"和"第六百零二章时空狭缝！"这样的格式
                    title_match = re.match(r'(第[一二两三四五六七八九十百千0-9零]+[回章节卷].*?)(?:[，。！？；：]|$)', line)
                    if title_match:
                        cleaned_title = title_match.group(1).strip()
                    else:
                        # 如果没有标点符号，使用整行作为标题
                        cleaned_title = line.strip()
                    
                    # 进一步清理标题，确保只包含文字和必要的标点
                    cleaned_title = re.sub(r'[^\u4e00-\u9fa50-9一二两三四五六七八九十百千零回章节卷\s]', '', cleaned_title).strip()
                    
                    if cleaned_title and len(cleaned_title) > 2:
                        # 过滤非目录项
                        if not self._is_non_toc_item(cleaned_title):
                            # 基于章节编号去重
                            if chapter_num not in seen_chapter_numbers:
                                seen_chapter_numbers.add(chapter_num)
                                toc_items.append(cleaned_title)
                    # 找到标题后，跳出当前章节的循环
                    break
        

        
        return toc_items
    
    def _detect_multi_book(self, book: epub.EpubBook) -> bool:
        """
        检测多书籍
        """
        # 简单检测：检查目录结构
        directories = set()
        for item in book.get_items():
            item_name = item.get_name() or ''
            if '/' in item_name:
                dir_path = os.path.dirname(item_name)
                directories.add(dir_path)
        
        return len(directories) > 1
    
    def _generate_single_file(
        self,
        book_info: Dict[str, str],
        toc_items: List[str],
        chapter_contents: List[str],
        is_multi_book: bool,
        generate_jump_marks: bool = True
    ) -> str:
        """
        生成单个文件内容
        """
        content = []
        
        # 添加书籍信息
        content.extend([
            '=' * 120,
            ' ' * 50 + "【电子书合集】",
            '=' * 120,
            f"合集名称: {book_info['title']}",
            f"作者: {book_info['author']}",
            f"转换时间: {book_info['conversion_time']}",
            '=' * 120
        ])
        
        # 添加目录
        if toc_items:
            content.extend([
                '',
                '=' * 120,
                ' ' * 50 + "【目录】",
                '=' * 120
            ])
            
            # 创建目录项到跳转标记的映射（基于章节编号）
            toc_jump_marks = []
            for i, item in enumerate(toc_items, 1):
                # 提取章节编号，添加对"两"和"零"的支持
                match = re.search(r'第([一二两三四五六七八九十百千0-9零]+)[回章节卷]', item)
                if match:
                    number_str = match.group(1)
                    # 转换中文数字为阿拉伯数字
                    if number_str.isdigit():
                        chapter_num = int(number_str)
                    else:
                        # 增强的中文数字转换
                        chapter_num = self._chinese_to_arabic(number_str)
                    # 使用章节编号作为跳转标记
                    jump_mark = chapter_num
                else:
                    # 如果无法提取章节编号，使用索引作为跳转标记
                    jump_mark = i
                
                # 保持目录项的原始格式，不做任何特殊处理
                if generate_jump_marks:
                    content.append(f"{jump_mark}. {item}  [跳转标记: {jump_mark}]")
                else:
                    content.append(f"{jump_mark}. {item}")
            
            content.extend([
                '=' * 120,
                '',
                "【正文开始】",
                '',
                '=' * 120
            ])
        
        # 添加章节内容，处理标题重复问题
        total_chapters = len(chapter_contents)
        
        # 创建目录项的清理版本集合，用于检测重复
        cleaned_toc_set = set()
        for toc_item in toc_items:
            # 清理目录项，去除非文字字符
            cleaned_toc = re.sub(r'[^\u4e00-\u9fa50-9一二两三四五六七八九十百千零回章节卷\s]', '', toc_item).strip()
            cleaned_toc_set.add(cleaned_toc)
        
        for idx, chapter in enumerate(chapter_contents, 1):
            # 清理章节内容，确保不包含重复的目录信息
            # 分割章节内容为行
            chapter_lines = chapter.split('\n')
            cleaned_chapter_lines = []
            
            # 跳过章节内容中的目录部分
            in_toc = False
            title_added = False
            
            for line in chapter_lines:
                line_stripped = line.strip()
                
                # 检测目录开始
                if '【目录】' in line_stripped:
                    in_toc = True
                    continue
                
                # 检测目录结束
                if in_toc and '【正文开始】' in line_stripped:
                    in_toc = False
                    continue
                
                # 跳过目录中的行
                if in_toc:
                    continue
                
                # 跳过空行
                if not line_stripped:
                    cleaned_chapter_lines.append(line)
                    continue
                
                # 跳过数字章节标题格式（如"===== 1章 ====="）
                if re.search(r'^=+\s*\d+章\s*=+$', line_stripped):
                    continue
                
                # 跳过数字章节标题行（如"第1章"）
                if re.search(r'^\s*第\d+章\s*$', line_stripped):
                    continue
                
                # 检查是否是章节标题行
                if re.search(r'第[一二两三四五六七八九十百千0-9零]+[回章节卷]', line_stripped):
                    # 清理该行，去除非文字字符
                    cleaned_line = re.sub(r'[^\u4e00-\u9fa50-9一二两三四五六七八九十百千零回章节卷\s]', '', line_stripped).strip()
                    # 检查是否与目录中的某个标题重复
                    if cleaned_line in cleaned_toc_set:
                        # 如果是重复的标题且还没有添加标题，则添加该行
                        if not title_added:
                            cleaned_chapter_lines.append(line)
                            title_added = True
                        # 否则跳过该行
                        continue
                    else:
                        # 不是重复的标题，正常添加
                        cleaned_chapter_lines.append(line)
                        title_added = True
                else:
                    # 不是标题行，正常添加
                    cleaned_chapter_lines.append(line)
            
            # 重新组合章节内容
            cleaned_chapter = '\n'.join(cleaned_chapter_lines)
            
            # 确保章节内容不为空
            if cleaned_chapter:
                content.append(cleaned_chapter)
        
        # 生成原始内容
        raw_content = '\n'.join(content)
        
        # 集成目录修复逻辑
        # 分割内容为行
        lines = raw_content.split('\n')
        
        # 处理后的行
        processed_lines = []
        
        # 标记是否正在处理章节标题部分
        processing_chapter_header = False
        # 标记是否已经处理过正文开始
        body_start_processed = False
        # 章节标题模式
        chapter_header_pattern = re.compile(r'^=+\s+第[一二三四五六七八九十百千0-9]+[回章节卷].*=+$')
        # 数字章节标题模式（如"1章"）
        number_chapter_pattern = re.compile(r'^=+\s*\d+章\s*=+$')
        # 标准章节标题模式
        standard_chapter_pattern = re.compile(r'^\s*第[一二三四五六七八九十百千0-9]+[回章节卷].*$')
        # 跳转标记模式
        jump_mark_pattern = re.compile(r'^\[跳转标记: \d+\]$')
        # 单行章节标题模式（如"第一回"）
        single_line_chapter_pattern = re.compile(r'^\s*第[一二三四五六七八九十百千0-9]+[回章节卷]\s*$')
        # 正文开始标记
        body_start_pattern = re.compile(r'^【正文开始】$')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检查是否是正文开始标记
            if body_start_pattern.match(line_stripped):
                # 只保留第一个正文开始标记
                if not body_start_processed:
                    processed_lines.append(line)
                    body_start_processed = True
                continue
            
            # 检查是否是分隔线行
            if line_stripped.startswith('=') and line_stripped.endswith('='):
                # 跳过数字章节标题分隔线（如"===== 1章 ====="）
                if number_chapter_pattern.match(line_stripped):
                    continue
                # 保留其他分隔线
                processed_lines.append(line)
                processing_chapter_header = True
                continue
            
            # 检查是否是跳转标记行
            if jump_mark_pattern.match(line_stripped):
                # 保留跳转标记
                processed_lines.append(line)
                # 不设置processing_chapter_header=True，避免跳过后续内容
                continue
            
            # 检查是否是单行章节标题（如"第一回"）
            if single_line_chapter_pattern.match(line_stripped):
                # 保留单行章节标题，不跳过
                processed_lines.append(line)
                processing_chapter_header = False
                continue
            
            # 检查是否是空行
            if not line_stripped:
                # 保留空行，不跳过
                processed_lines.append(line)
                processing_chapter_header = False
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
        
        final_content = '\n'.join(processed_lines)
        
        # 验证内容完整性
        if len(final_content) < len(raw_content) * 0.95:  # 确保至少保留95%的内容
            return raw_content
        
        return final_content
    
    def _split_into_multiple_files(
        self,
        output_dir: str,
        book_info: Dict[str, str],
        toc_items: List[str],
        chapter_contents: List[str],
        is_multi_book: bool,
        multi_book_mode: str,
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> None:
        """
        拆分多文件
        """
        FileUtils.ensure_directory(output_dir)
        
        # 生成目录文件
        toc_content = []
        toc_content.extend([
            '=' * 100,
            ' ' * 40 + "【目录】",
            '=' * 100
        ])
        
        for i, item in enumerate(toc_items, 1):
            toc_content.append(f"{i}. {item}")
        
        toc_content.append('=' * 100)
        
        toc_path = os.path.join(output_dir, "目录.txt")
        FileUtils.write_file_safely(toc_path, '\n'.join(toc_content))
        
        # 生成章节文件
        for i, (chapter, toc_item) in enumerate(zip(chapter_contents, toc_items), 1):
            if progress_callback:
                progress = 60 + (i / len(chapter_contents)) * 30
                progress_callback(progress, f"处理章节 {i}/{len(chapter_contents)}")
            
            safe_title = FileUtils.safe_filename(toc_item)
            chapter_path = os.path.join(output_dir, f"{i:03d}_{safe_title}.txt")
            FileUtils.write_file_safely(chapter_path, chapter)
    
    def _handle_split_by_size(self, output_path: str, max_file_size: int) -> List[str]:
        """
        处理按大小分割
        """
        split_dir = os.path.splitext(output_path)[0] + '_split'
        return FileUtils.split_file_by_size(output_path, split_dir, max_file_size)
    
    def _handle_compression(
        self,
        output_path: str,
        split_files: List[str],
        zip_split: bool,
        compress_level: int = 6
    ) -> None:
        """
        处理压缩
        """
        if split_files:
            if zip_split:
                # 创建以时间+TXT文件名+split命名的文件夹
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                txt_file_name = os.path.splitext(os.path.basename(output_path))[0]
                folder_name = f"{timestamp}_{txt_file_name}_split"
                output_dir = os.path.dirname(output_path)
                zip_folder = os.path.join(output_dir, folder_name)
                
                # 确保文件夹存在
                if not os.path.exists(zip_folder):
                    os.makedirs(zip_folder)
                    print(f"创建输出文件夹: {zip_folder}")
                
                # 为每个拆分的文件创建ZIP文件并放入新文件夹
                for file_path in split_files:
                    zip_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.zip"
                    zip_path = os.path.join(zip_folder, zip_name)
                    
                    if ZipUtils.create_zip_archive([file_path], zip_path, compress_level):
                        print(f"创建ZIP文件: {zip_path}")
                
                # 删除多余的拆分TXT文件
                for file_path in split_files:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"删除多余的拆分文件: {file_path}")
                        except Exception as e:
                            print(f"删除文件失败: {str(e)}")
                
                # 删除空的_split目录
                split_dir = os.path.splitext(output_path)[0] + '_split'
                if os.path.exists(split_dir) and os.path.isdir(split_dir):
                    if not os.listdir(split_dir):
                        try:
                            os.rmdir(split_dir)
                            print(f"删除空目录: {split_dir}")
                        except Exception as e:
                            print(f"删除目录失败: {str(e)}")
            else:
                zip_path = os.path.splitext(output_path)[0] + '.zip'
                ZipUtils.create_zip_archive(split_files, zip_path, compress_level)
        else:
            zip_path = os.path.splitext(output_path)[0] + '.zip'
            ZipUtils.create_zip_archive([output_path], zip_path, compress_level)

# 导出函数
converter = EPUBConverter()


def convert_with_ebooklib(*args, **kwargs) -> bool:
    """
    使用ebooklib转换EPUB
    """
    return converter.convert_with_ebooklib(*args, **kwargs)


def convert_with_epub2txt(*args, **kwargs) -> bool:
    """
    使用epub2txt转换EPUB
    """
    return converter.convert_with_epub2txt(*args, **kwargs)
