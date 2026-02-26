# EPUB转TXT文件的Python实现
# 方法1：使用epub2txt库（简单方法）
# 方法2：使用ebooklib和BeautifulSoup库（更灵活）

import os
import sys
import datetime
import re
import zipfile
from bs4 import BeautifulSoup
from ebooklib import epub
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def split_text_by_size(input_path, output_dir, max_size, encoding='utf-8'):
    """
    按大小分割文本文件
    input_path: 输入文件路径
    output_dir: 输出目录
    max_size: 最大文件大小（字节）
    encoding: 文件编码
    """
    try:
        # 读取文件内容
        with open(input_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # 计算文件大小
        content_size = len(content.encode(encoding))
        print(f"原始文件大小：{content_size} 字节")
        print(f"分割大小：{max_size} 字节")
        
        if content_size <= max_size:
            print("文件大小小于分割阈值，不需要分割")
            return [input_path]
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 分割文件
        parts = []
        current_size = 0
        current_content = []
        part_number = 1
        
        # 按段落分割
        paragraphs = content.split('\n')
        
        for paragraph in paragraphs:
            # 计算段落大小
            para_size = len((paragraph + '\n').encode(encoding))
            
            # 如果添加当前段落会超过最大大小，则保存当前部分
            if current_size + para_size > max_size and current_content:
                # 保存当前部分
                part_filename = os.path.join(output_dir, f"part_{part_number:03d}.txt")
                with open(part_filename, 'w', encoding=encoding) as f:
                    f.write('\n'.join(current_content))
                parts.append(part_filename)
                print(f"生成分割文件：{part_filename}")
                
                # 重置计数器
                current_size = 0
                current_content = []
                part_number += 1
            
            # 添加当前段落
            current_content.append(paragraph)
            current_size += para_size
        
        # 保存最后一部分
        if current_content:
            part_filename = os.path.join(output_dir, f"part_{part_number:03d}.txt")
            with open(part_filename, 'w', encoding=encoding) as f:
                f.write('\n'.join(current_content))
            parts.append(part_filename)
            print(f"生成分割文件：{part_filename}")
        
        print(f"成功分割为 {len(parts)} 个文件")
        return parts
    except Exception as e:
        print(f"分割文件失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return [input_path]


def create_zip_archive(files, zip_path):
    """
    创建zip压缩文件
    files: 文件列表
    zip_path: 输出zip文件路径
    """
    try:
        print(f"开始创建zip压缩文件：{zip_path}")
        
        # 创建zip文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if os.path.exists(file_path):
                    # 获取相对路径
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
                    print(f"添加文件到zip：{arcname}")
        
        print(f"成功创建zip文件：{zip_path}")
        print(f"zip文件大小：{os.path.getsize(zip_path)} 字节")
        return True
    except Exception as e:
        print(f"创建zip文件失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def convert_with_epub2txt(epub_path, output_path):
    """
    使用epub2txt库将EPUB转换为TXT
    需要先安装：pip install epub2txt
    """
    try:
        from epub2txt import epub2txt
        print(f"开始使用epub2txt转换：{epub_path}")
        text = epub2txt(epub_path)
        print(f"提取到文本长度：{len(text)} 字符")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        file_size = os.path.getsize(output_path)
        print(f"成功写入TXT文件，大小：{file_size} 字节")
        print(f"使用epub2txt成功转换：{epub_path} -> {output_path}")
        return True
    except ImportError:
        print("错误：epub2txt库未安装，请运行 'pip install epub2txt'")
        return False
    except Exception as e:
        print(f"转换失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def convert_with_ebooklib(epub_path, output_path, generate_jump_marks=True, split_into_multiple_files=False, multi_book_split_mode="merge", progress_callback=None, split_by_size=False, max_file_size=10485760, output_zip=False, zip_split=False, line_split_length=500):
    """
    使用ebooklib和BeautifulSoup将EPUB转换为TXT
    需要先安装：pip install ebooklib beautifulsoup4 lxml
    """
    try:
        # 打开EPUB文件
        book = epub.read_epub(epub_path)
        
        # 提取文本
        text_content = []
        toc_items = []  # 目录项
        chapter_contents = []  # 章节内容
        
        # 打印EPUB信息
        print(f"EPUB标题: {book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '未知'}")
        print(f"EPUB作者: {book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '未知'}")
        
        # 1. 尝试提取导航文件（目录）
        print("\n=== 提取目录信息 ===")
        nav_items = []
        
        # 搜索所有可能的导航和目录文件
        for item in book.get_items():
            item_name = item.get_name() or ''
            item_type = item.get_type()
            
            # 打印所有项目，帮助调试
            print(f"  检查项目: {item_name}, 类型: {item_type}")
            
            # 检查是否为导航文件
            if item_type == epub.EpubNav:
                nav_items.append(item)
                print(f"  找到导航文件: {item_name}")
            # 检查toc.ncx文件
            elif 'toc.ncx' in item_name.lower():
                nav_items.append(item)
                print(f"  找到目录文件: {item_name}")
            # 检查nav文件
            elif 'nav' in item_name.lower() and (item_name.endswith('.html') or item_name.endswith('.xhtml')):
                nav_items.append(item)
                print(f"  找到导航文件: {item_name}")
            # 检查目录相关文件
            elif 'tableofcontents' in item_name.lower() or 'contents' in item_name.lower():
                nav_items.append(item)
                print(f"  找到目录相关文件: {item_name}")
        
        print(f"\n总共找到 {len(nav_items)} 个导航/目录文件")
        
        # 解析导航文件
        if nav_items:
            for nav_item in nav_items:
                try:
                    nav_content = nav_item.get_content().decode('utf-8', errors='ignore')
                    print(f"\n  解析文件: {nav_item.get_name()}")
                    
                    # 尝试HTML解析
                    soup = BeautifulSoup(nav_content, 'html.parser')
                    
                    # 提取导航项 - 尝试多种可能的结构
                    nav_points = []
                    
                    # 尝试常见的导航结构
                    nav_points.extend(soup.find_all(['li', 'a'], class_=['navPoint', 'nav-item', 'toc-item', 'chapter', 'section']))
                    nav_points.extend(soup.find_all('a', href=True))
                    nav_points.extend(soup.find_all('li'))
                    
                    print(f"  找到 {len(nav_points)} 个可能的导航项")
                    
                    for point in nav_points:
                        link = point.find('a') if point.name != 'a' else point
                        if link and link.get('href'):
                            title = link.get_text(strip=True)
                            href = link.get('href')
                            if title and len(title) > 2:  # 过滤过短的标题
                                if title not in toc_items:
                                    toc_items.append(title)
                                    print(f"  目录项: {title}")
                    
                    # 对于NCX文件或XML格式
                    if not toc_items:
                        try:
                            from xml.etree import ElementTree as ET
                            root = ET.fromstring(nav_content)
                            
                            # 处理不同的命名空间
                            namespaces = {
                                'ncx': 'http://www.daisy.org/z3986/2005/ncx/',
                                'xhtml': 'http://www.w3.org/1999/xhtml'
                            }
                            
                            # 尝试不同的导航点路径
                            for ns in namespaces.values():
                                try:
                                    ns_prefix = '{' + ns + '}'
                                    nav_points = root.findall('.//' + ns_prefix + 'navPoint')
                                    for point in nav_points:
                                        text_elem = point.find(ns_prefix + 'text')
                                        if text_elem is not None and text_elem.text:
                                            title = text_elem.text.strip()
                                            if title and len(title) > 2:
                                                if title not in toc_items:
                                                    toc_items.append(title)
                                                    print(f"  目录项: {title}")
                                except:
                                    continue
                        except Exception as xml_error:
                            print(f"  XML解析出错: {str(xml_error)}")
                except Exception as e:
                    print(f"  解析导航文件出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        print(f"\n从导航文件提取到 {len(toc_items)} 个目录项")
        
        # 2. 处理内容文件
        print("\n=== 处理内容文件 ===")
        items = list(book.get_items())
        print(f"EPUB中共有 {len(items)} 个项目")
        
        content_count = 0
        for item in items:
            # 获取项目信息
            item_type = item.get_type()
            item_name = item.get_name()
            item_id = item.get_id()
            
            # 打印项目详细信息
            print(f"项目类型: {item_type}, 项目ID: {item_id}, 项目名称: {item_name}")
            
            # 检查是否为HTML或XHTML文件
            is_content_file = False
            
            # 方法1：检查项目类型
            if item_type == epub.EpubHtml:
                is_content_file = True
                print("  识别为: EpubHtml类型")
            
            # 方法2：检查文件扩展名
            elif item_name and (item_name.endswith('.html') or item_name.endswith('.xhtml') or item_name.endswith('.htm')):
                is_content_file = True
                print("  识别为: HTML/XHTML文件 (通过扩展名)")
            
            # 方法3：检查媒体类型
            media_type = getattr(item, 'media_type', None)
            if media_type:
                print(f"  媒体类型: {media_type}")
                if 'html' in media_type.lower() or 'xhtml' in media_type.lower():
                    is_content_file = True
                    print("  识别为: HTML/XHTML文件 (通过媒体类型)")
            
            # 处理内容文件
            if is_content_file:
                content_count += 1
                try:
                    # 获取文件内容
                    content = item.get_content()
                    
                    # 尝试不同编码解码
                    encodings = ['utf-8', 'gbk', 'latin-1', 'utf-16']
                    decoded_content = None
                    for encoding in encodings:
                        try:
                            decoded_content = content.decode(encoding)
                            print(f"  使用 {encoding} 编码成功解码")
                            break
                        except:
                            continue
                    
                    if not decoded_content:
                        decoded_content = content.decode('utf-8', errors='ignore')
                        print(f"  使用 utf-8 (ignore) 编码解码")
                    
                    # 使用BeautifulSoup解析
                    soup = BeautifulSoup(decoded_content, 'html.parser')
                    
                    # 提取章节标题
                    chapter_title = ""
                    # 尝试从h1-h6标签中提取标题
                    for level in range(1, 7):
                        title_tag = soup.find(f'h{level}')
                        if title_tag:
                            chapter_title = title_tag.get_text(strip=True)
                            if chapter_title:
                                print(f"  提取到章节标题: {chapter_title}")
                                break
                    
                    # 提取文本并清理
                    raw_text = soup.get_text(separator='\n', strip=True)
                    
                    # 清理和格式化文本
                    print(f"  提取到原始文本长度: {len(raw_text)} 字符")
                    
                    # 1. 清理文本
                    lines = raw_text.split('\n')
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
                    
                    # 2. 智能合并行（改进版）
                    merged_lines = []
                    i = 0
                    
                    while i < len(cleaned_lines):
                        current_line = cleaned_lines[i]
                        
                        # 检查是否需要合并后续行
                        if i + 1 < len(cleaned_lines):
                            next_line = cleaned_lines[i + 1]
                            
                            # 情况1：当前行以逗号或顿号结尾，下一行是短行
                            if current_line and current_line[-1] in '，、' and len(next_line) < 30:
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
                    
                    # 3. 严格控制文本长度，确保所有段都不超过设定值
                    formatted_lines = []
                    
                    for line in merged_lines:
                        # 移除行尾空格
                        line = line.rstrip()
                        
                        # 保留空行，作为段落分隔
                        if not line:
                            formatted_lines.append('')
                            continue
                        
                        # 检测前缀空格，保留段落缩进
                        prefix_spaces = ''
                        for char in line:
                            if char == ' ':
                                prefix_spaces += ' '
                            else:
                                break
                        
                        # 清理行内多余空格
                        content = ' '.join(line.split())
                        
                        # 计算前缀空格长度
                        prefix_length = len(prefix_spaces)
                        # 计算实际可用的内容长度
                        available_length = line_split_length - prefix_length
                        
                        # 严格按照设定长度分割，确保所有段都不超过限制
                        current_position = 0
                        total_length = len(content)
                        
                        while current_position < total_length:
                            # 计算剩余长度
                            remaining_length = total_length - current_position
                            
                            # 如果剩余长度小于等于可用长度，直接添加
                            if remaining_length <= available_length:
                                current_line = content[current_position:].strip()
                                if current_line:
                                    # 确保最终长度不超过限制
                                    final_line = prefix_spaces + current_line
                                    if len(final_line) > line_split_length:
                                        # 如果超过限制，截断到可用长度
                                        current_line = content[current_position:current_position + available_length].strip()
                                        final_line = prefix_spaces + current_line
                                    formatted_lines.append(final_line)
                                break
                            
                            # 剩余长度超过可用长度，需要分割
                            # 强制分割，不考虑空格
                            end_position = current_position + available_length
                            current_segment = content[current_position:end_position].strip()
                            
                            # 添加到结果中，保留前缀空格
                            if current_segment:
                                formatted_lines.append(prefix_spaces + current_segment)
                            
                            # 更新当前位置
                            current_position = end_position
                    
                    # 5. 清理空行
                    # 移除连续的空行，最多保留一个空行
                    cleaned_formatted_lines = []
                    last_was_empty = False
                    
                    for line in formatted_lines:
                        if line.strip():
                            cleaned_formatted_lines.append(line)
                            last_was_empty = False
                        else:
                            if not last_was_empty:
                                cleaned_formatted_lines.append('')
                                last_was_empty = True
                    
                    # 6. 高级排版优化
                    final_formatted_lines = []
                    in_dialogue = False
                    dialogue_lines = []
                    
                    for line in cleaned_formatted_lines:
                        # 检查对话处理
                        if line and (line.startswith('"') or line.startswith('“') or line.startswith('‘')):
                            if not in_dialogue:
                                # 开始新对话
                                in_dialogue = True
                                dialogue_lines = [line]
                            else:
                                # 继续对话
                                dialogue_lines.append(line)
                        elif in_dialogue and (line.endswith('"') or line.endswith('”') or line.endswith('’')):
                            # 对话结束
                            dialogue_lines.append(line)
                            # 合并对话行
                            dialogue_text = ' '.join(dialogue_lines)
                            final_formatted_lines.append(dialogue_text)
                            final_formatted_lines.append('')
                            in_dialogue = False
                            dialogue_lines = []
                        elif in_dialogue:
                            # 对话中间行
                            dialogue_lines.append(line)
                        else:
                            # 普通行
                            final_formatted_lines.append(line)
                    
                    # 处理未结束的对话
                    if dialogue_lines:
                        dialogue_text = ' '.join(dialogue_lines)
                        final_formatted_lines.append(dialogue_text)
                        final_formatted_lines.append('')
                    
                    # 7. 诗歌特殊处理
                    poetry_lines = []
                    is_poetry = False
                    optimized_lines = []
                    
                    for line in final_formatted_lines:
                        # 检查是否为诗歌（短行且包含标点）
                        if line and len(line) < 30 and any(p in line for p in '，。！？；：'):
                            if not is_poetry:
                                # 开始诗歌
                                is_poetry = True
                                poetry_lines = [line]
                            else:
                                # 继续诗歌
                                poetry_lines.append(line)
                        else:
                            if is_poetry:
                                # 诗歌结束，保持诗歌格式
                                optimized_lines.extend(poetry_lines)
                                optimized_lines.append('')
                                is_poetry = False
                                poetry_lines = []
                            # 添加普通行
                            optimized_lines.append(line)
                    
                    # 处理未结束的诗歌
                    if poetry_lines:
                        optimized_lines.extend(poetry_lines)
                        optimized_lines.append('')
                    
                    # 8. 最终清理
                    # 移除首尾空行
                    while optimized_lines and not optimized_lines[0].strip():
                        optimized_lines.pop(0)
                    while optimized_lines and not optimized_lines[-1].strip():
                        optimized_lines.pop()
                    
                    # 9. 构建最终文本
                    text = '\n'.join(optimized_lines)
                    print(f"  清理后文本长度: {len(text)} 字符")
                    print(f"  行数: {len(optimized_lines)}")
                    print(f"  段落数: {optimized_lines.count('') + 1}")
                    
                    # 过滤空内容
                    if text.strip():
                        # 构建章节内容，特殊标记标题（美化版）
                        chapter_text = ""
                        if chapter_title:
                            # 清理标题格式（去掉方括号，添加空格）
                            cleaned_title = chapter_title.strip()
                            # 去掉可能的方括号
                            if cleaned_title.startswith('【') and cleaned_title.endswith('】'):
                                cleaned_title = cleaned_title[1:-1].strip()
                            elif cleaned_title.startswith('"') and cleaned_title.endswith('"'):
                                cleaned_title = cleaned_title[1:-1].strip()
                            
                            # 使用正则表达式在章节编号后添加空格
                            # 匹配模式：第X回、第X章、卷X、第X节等
                            patterns = [
                                (r'(第[一二三四五六七八九十百千]+[回章节卷])', r'\1 '),  # 第X回/章/节/卷
                                (r'(第\d+[回章节卷])', r'\1 '),  # 第1回/章/节/卷
                                (r'(卷[一二三四五六七八九十百千]+)', r'\1 '),  # 卷X
                                (r'(卷\d+)', r'\1 '),  # 卷1
                                (r'([一二三四五六七八九十百千]+[回章节卷])', r'\1 ')  # X回/章/节/卷
                            ]
                            
                            # 应用所有模式
                            for pattern, replacement in patterns:
                                cleaned_title = re.sub(pattern, replacement, cleaned_title)
                            
                            # 清理多余的空格
                            cleaned_title = ' '.join(cleaned_title.split())
                            
                            # 创建章节内容
                            if generate_jump_marks:
                                # 创建章节跳转标记（数字格式）
                                # 使用章节序号作为跳转标记
                                jump_mark_num = len(chapter_contents) + 1
                                jump_mark = f"{jump_mark_num}"
                                
                                # 特殊标记章节标题（无方括号版本），添加跳转标记
                                chapter_text = f"\n{'=' * 100}\n{' ' * 40}{cleaned_title}\n{'=' * 100}\n[跳转标记: {jump_mark}]\n\n{text}"
                            else:
                                # 不添加跳转标记
                                chapter_text = f"\n{'=' * 100}\n{' ' * 40}{cleaned_title}\n{'=' * 100}\n\n{text}"
                        else:
                            # 如果没有标题，使用文件名作为标题
                            if item_name:
                                chapter_title = os.path.splitext(os.path.basename(item_name))[0]
                                if generate_jump_marks:
                                    # 创建章节跳转标记（数字格式）
                                    jump_mark_num = len(chapter_contents) + 1
                                    jump_mark = f"{jump_mark_num}"
                                    # 特殊标记章节标题，添加跳转标记
                                    chapter_text = f"\n{'=' * 100}\n{' ' * 40}{chapter_title}\n{'=' * 100}\n[跳转标记: {jump_mark}]\n\n{text}"
                                else:
                                    # 不添加跳转标记
                                    chapter_text = f"\n{'=' * 100}\n{' ' * 40}{chapter_title}\n{'=' * 100}\n\n{text}"
                            else:
                                # 使用章节序号作为标题
                                chapter_num = len(chapter_contents) + 1
                                chapter_title = f"章节{chapter_num}"
                                if generate_jump_marks:
                                    jump_mark = f"{chapter_num}"
                                    chapter_text = f"\n{'=' * 100}\n{' ' * 40}{chapter_title}\n{'=' * 100}\n[跳转标记: {jump_mark}]\n\n{text}"
                                else:
                                    chapter_text = f"\n{'=' * 100}\n{' ' * 40}{chapter_title}\n{'=' * 100}\n\n{text}"
                        
                        chapter_contents.append(chapter_text)
                        print(f"  成功添加章节内容")
                except Exception as e:
                    print(f"  处理内容文件时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        print(f"\n总共处理了 {content_count} 个内容文件")
        print(f"成功提取了 {len(chapter_contents)} 个章节的内容")
        
        # 尝试从章节内容中提取目录（如果之前没有找到）
        if not toc_items and chapter_contents:
            print("\n=== 从章节内容提取目录 ===")
            # 从章节内容中提取标题生成目录
            for i, chapter in enumerate(chapter_contents, 1):
                # 尝试从章节内容中提取标题
                lines = chapter.split('\n')
                
                # 只从章节开头的前几行中提取标题，避免提取正文中的内容
                # 查找包含等号分隔线的行，通常章节标题会在等号分隔线之间
                found_title = False
                for j, line in enumerate(lines[:20]):  # 只检查前20行
                    # 检查是否为章节标题行（在等号分隔线之间）
                    if j > 0 and '=' * 50 in lines[j-1] and '=' * 50 in lines[j+1] if j+1 < len(lines) else False:
                        # 这一行可能是章节标题
                        title = line.strip()
                        if title and len(title) > 2:
                            # 清理标题格式
                            cleaned_title = title
                            
                            # 使用正则表达式在章节编号后添加空格
                            # 匹配模式：第X回、第X章、卷X、第X节等
                            patterns = [
                                (r'(第[一二三四五六七八九十百千]+[回章节卷])', r'\1 '),  # 第X回/章/节/卷
                                (r'(第\d+[回章节卷])', r'\1 '),  # 第1回/章/节/卷
                                (r'(卷[一二三四五六七八九十百千]+)', r'\1 '),  # 卷X
                                (r'(卷\d+)', r'\1 '),  # 卷1
                                (r'([一二三四五六七八九十百千]+[回章节卷])', r'\1 ')  # X回/章/节/卷
                            ]
                            
                            # 应用所有模式
                            for pattern, replacement in patterns:
                                cleaned_title = re.sub(pattern, replacement, cleaned_title)
                            
                            # 清理多余的空格
                            cleaned_title = ' '.join(cleaned_title.split())
                            
                            # 检查是否为有效的章节标题（包含章节编号模式）
                            chapter_patterns = [
                                r'第[一二三四五六七八九十百千]+[回章节卷]',
                                r'第\d+[回章节卷]',
                                r'卷[一二三四五六七八九十百千]+',
                                r'卷\d+'
                            ]
                            
                            is_chapter_title = any(re.search(pattern, cleaned_title) for pattern in chapter_patterns)
                            
                            if is_chapter_title and cleaned_title not in toc_items:
                                toc_items.append(cleaned_title)
                                print(f"  从章节提取目录项: {cleaned_title}")
                                found_title = True
                                break
                
                # 如果没有找到符合条件的标题，尝试使用章节索引作为标题
                if not found_title:
                    chapter_title = f"第{i}章"
                    if chapter_title not in toc_items:
                        toc_items.append(chapter_title)
                        print(f"  从章节索引生成目录项: {chapter_title}")
        
        print(f"最终提取到 {len(toc_items)} 个目录项")
        
        # 3. 检测是否为多书籍EPUB
        print("\n=== 检测多书籍结构 ===")
        
        # 分析EPUB结构，尝试识别多书籍情况
        # 方法1：检查导航文件的层次结构
        is_multi_book = False
        book_groups = []  # 存储多书籍的信息
        
        # 检查导航文件中的层次结构
        if nav_items:
            for nav_item in nav_items:
                try:
                    nav_content = nav_item.get_content().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(nav_content, 'html.parser')
                    
                    # 查找可能的书籍分组元素（如h1, h2标签或带有特定class的元素）
                    book_headers = soup.find_all(['h1', 'h2'], class_=['book', 'title', 'volume'])
                    if len(book_headers) > 1:
                        is_multi_book = True
                        print(f"  检测到多书籍结构：{len(book_headers)} 本书籍")
                        
                        # 提取书籍标题
                        for header in book_headers:
                            book_title = header.get_text(strip=True)
                            if book_title:
                                book_groups.append({"title": book_title, "toc": [], "content": []})
                        break
                except Exception as e:
                    print(f"  分析导航文件出错: {str(e)}")
        
        # 方法2：检查内容文件的路径结构
        if not is_multi_book:
            # 分析内容文件的路径，看是否有按书籍分组的文件夹
            content_items = []
            for item in book.get_items():
                if item.get_type() == epub.EpubHtml:
                    content_items.append(item)
            
            # 提取所有内容文件的目录路径
            directories = set()
            for item in content_items:
                item_name = item.get_name() or ''
                if '/' in item_name:
                    dir_path = os.path.dirname(item_name)
                    directories.add(dir_path)
            
            # 如果有多个目录，可能是多书籍结构
            if len(directories) > 1:
                is_multi_book = True
                print(f"  检测到多书籍结构：{len(directories)} 个目录")
                
                # 为每个目录创建书籍信息
                for i, dir_path in enumerate(directories, 1):
                    book_title = f"书籍{i} - {os.path.basename(dir_path)}"
                    book_groups.append({"title": book_title, "toc": [], "content": []})
        
        print(f"  多书籍检测结果: {'是' if is_multi_book else '否'}")
        
        # 4. 生成最终TXT内容
        final_content = []
        
        # 添加书籍信息（美化版）
        book_title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '未知'
        book_author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '未知'
        
        # 表头
        final_content.append(f"{'=' * 120}")
        final_content.append(f"{' ' * 50}【电子书合集】")
        final_content.append(f"{'=' * 120}")
        final_content.append(f"合集名称: {book_title}")
        final_content.append(f"作者: {book_author}")
        final_content.append(f"转换时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if is_multi_book:
            final_content.append(f"包含书籍数量: {len(book_groups)}")
        final_content.append(f"{'=' * 120}")
        
        if is_multi_book and book_groups:
            # 多书籍处理
            print("\n=== 处理多书籍结构 ===")
            
            # 为每个书籍生成目录
            final_content.append("\n" + "=" * 120)
            final_content.append(f"{' ' * 50}【总目录】")
            final_content.append("=" * 120)
            
            for i, book_info in enumerate(book_groups, 1):
                final_content.append(f"{i}. {book_info['title']}")
            
            final_content.append("=" * 120)
            
            # 为每个书籍生成详细内容
            for i, book_info in enumerate(book_groups, 1):
                final_content.append("\n" + "=" * 120)
                final_content.append(f"{' ' * 45}【{book_info['title']}】")
                final_content.append("=" * 120)
                
                # 这里简化处理，实际项目中需要根据EPUB结构提取每个书籍的具体目录和内容
                # 暂时使用原有的目录和内容，后续可以根据实际结构进行优化
                final_content.append("\n【目录】")
                for j, toc_item in enumerate(toc_items[:10], 1):  # 暂时取前10个目录项作为示例
                    # 为多书籍模式也添加数字跳转标记
                    jump_mark = f"{j}"
                    final_content.append(f"{j}. {toc_item}  [跳转标记: {jump_mark}]")
                
                final_content.append("\n【正文开始】")
                # 这里可以根据书籍结构提取对应内容，暂时省略
                final_content.append(f"\n本部分包含《{book_info['title']}》的内容...")
                final_content.append("=" * 120)
        else:
            # 单书籍处理（原有逻辑）
            # 添加目录（美化版）
            if toc_items:
                final_content.append("\n" + "=" * 120)
                final_content.append(f"{' ' * 50}【目录】")
                final_content.append("=" * 120)
                
                # 为目录添加页码占位符（实际页码需要计算，这里使用章节序号）
                for i, toc_item in enumerate(toc_items, 1):
                    # 清理目录项格式（去掉方括号）
                    cleaned_toc_item = toc_item.strip()
                    if cleaned_toc_item.startswith('【') and cleaned_toc_item.endswith('】'):
                        cleaned_toc_item = cleaned_toc_item[1:-1].strip()
                    elif cleaned_toc_item.startswith('"') and cleaned_toc_item.endswith('"'):
                        cleaned_toc_item = cleaned_toc_item[1:-1].strip()
                    
                    # 使用正则表达式在章节编号后添加空格
                    # 匹配模式：第X回、第X章、卷X、第X节等
                    patterns = [
                        (r'(第[一二三四五六七八九十百千]+[回章节卷])', r'\1 '),  # 第X回/章/节/卷
                        (r'(第\d+[回章节卷])', r'\1 '),  # 第1回/章/节/卷
                        (r'(卷[一二三四五六七八九十百千]+)', r'\1 '),  # 卷X
                        (r'(卷\d+)', r'\1 '),  # 卷1
                        (r'([一二三四五六七八九十百千]+[回章节卷])', r'\1 ')  # X回/章/节/卷
                    ]
                    
                    # 应用所有模式
                    for pattern, replacement in patterns:
                        cleaned_toc_item = re.sub(pattern, replacement, cleaned_toc_item)
                    
                    # 清理多余的空格
                    cleaned_toc_item = ' '.join(cleaned_toc_item.split())
                    
                    # 格式化目录项
                    if generate_jump_marks:
                        # 添加数字跳转标记
                        jump_mark = f"{i}"
                        # 计算填充空格，使标记右对齐
                        padding = ' ' * (90 - len(cleaned_toc_item))
                        final_content.append(f"{i}. {cleaned_toc_item}{padding}[跳转标记: {jump_mark}]")
                    else:
                        # 不添加跳转标记
                        final_content.append(f"{i}. {cleaned_toc_item}")
                
                final_content.append("=" * 120)
                final_content.append("\n【正文开始】\n")
                final_content.append("=" * 120)
            else:
                final_content.append("\n【正文开始】\n")
                final_content.append("=" * 120)
            
            # 添加章节内容
            final_content.extend(chapter_contents)
        
        # 4. 处理输出
        if split_into_multiple_files and chapter_contents:
            # 多文本拆分模式
            print("\n=== 拆分多文本为单独文件 ===")
            
            # 创建输出目录
            output_dir = os.path.splitext(output_path)[0]
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"创建输出目录: {output_dir}")
            
            if is_multi_book and book_groups:
                # 多书籍拆分模式
                print("\n=== 按书籍拆分模式 ===")
                print(f"多书籍拆分子模式: {multi_book_split_mode}")
                
                # 生成总目录文件
                toc_file_path = os.path.join(output_dir, "总目录.txt")
                with open(toc_file_path, 'w', encoding='utf-8') as f:
                    f.write('=' * 100 + '\n')
                    f.write(' ' * 40 + "【总目录】\n")
                    f.write('=' * 100 + '\n')
                    f.write(f"合集名称: {book_title}\n")
                    f.write(f"作者: {book_author}\n")
                    f.write(f"包含书籍数量: {len(book_groups)}\n")
                    f.write(f"拆分模式: {multi_book_split_mode}\n")
                    f.write('=' * 100 + '\n')
                    
                    for i, book_info in enumerate(book_groups, 1):
                        f.write(f"{i}. {book_info['title']}\n")
                    
                    f.write('=' * 100 + '\n')
                
                print(f"生成总目录文件: {toc_file_path}")
                
                if progress_callback:
                    progress_callback(60, "生成总目录文件")
                
                # 按书籍拆分
                total_books = len(book_groups)
                for i, book_info in enumerate(book_groups, 1):
                    # 创建书籍子目录
                    book_subdir = os.path.join(output_dir, f"{i:02d}_{re.sub(r'[<>:"/\\|?*]', '', book_info['title'])[:30]}")
                    if not os.path.exists(book_subdir):
                        os.makedirs(book_subdir)
                        print(f"创建书籍目录: {book_subdir}")
                    
                    if progress_callback:
                        progress = 60 + (i / total_books) * 30
                        progress_callback(progress, f"处理书籍 {i}/{total_books}: {book_info['title']}")
                    
                    # 生成书籍目录文件
                    book_toc_path = os.path.join(book_subdir, "目录.txt")
                    with open(book_toc_path, 'w', encoding='utf-8') as f:
                        f.write('=' * 100 + '\n')
                        f.write(' ' * 40 + f"【{book_info['title']}】\n")
                        f.write('=' * 100 + '\n')
                        
                        # 这里简化处理，实际项目中需要根据EPUB结构提取每个书籍的具体目录
                        # 暂时使用原有的目录项，后续可以根据实际结构进行优化
                        for j, toc_item in enumerate(toc_items[:10], 1):
                            if generate_jump_marks:
                                jump_mark = f"{j}"
                                f.write(f"{j}. {toc_item}  [跳转标记: {jump_mark}]\n")
                            else:
                                f.write(f"{j}. {toc_item}\n")
                        
                        f.write('=' * 100 + '\n')
                    
                    print(f"生成书籍目录文件: {book_toc_path}")
                    
                    if multi_book_split_mode == "merge":
                        # 全合并模式：每本书合并为一个文件
                        print(f"\n=== 书籍 {i}: {book_info['title']} - 全合并模式 ===")
                        book_content_path = os.path.join(book_subdir, f"{book_info['title'][:30]}_内容.txt")
                        with open(book_content_path, 'w', encoding='utf-8') as f:
                            # 添加书籍信息
                            f.write('=' * 100 + '\n')
                            f.write(' ' * 40 + f"【{book_info['title']}】\n")
                            f.write('=' * 100 + '\n')
                            f.write(f"书名: {book_info['title']}\n")
                            f.write(f"作者: {book_author}\n")
                            f.write(f"转换时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write('=' * 100 + '\n')
                            f.write("\n【正文开始】\n\n")
                            
                            # 这里简化处理，实际项目中需要根据EPUB结构提取每个书籍的具体内容
                            # 暂时写入所有章节内容，后续可以根据实际结构进行优化
                            for chapter in chapter_contents:
                                f.write(chapter)
                                f.write('\n')
                        
                        print(f"生成书籍内容文件: {book_content_path}")
                    else:
                        # 拆分模式：每本书按章节拆分
                        print(f"\n=== 书籍 {i}: {book_info['title']} - 按章节拆分模式 ===")
                        # 拆分章节为单独文件
                        total_chapters = len(chapter_contents)
                        for j, chapter in enumerate(chapter_contents, 1):
                            # 提取章节标题作为文件名
                            chapter_title = toc_items[j-1] if j-1 < len(toc_items) else f"第{j}章"
                            
                            # 清理文件名（移除非法字符）
                            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter_title)
                            safe_title = safe_title[:50]  # 限制文件名长度
                            
                            # 创建章节文件
                            chapter_file_path = os.path.join(book_subdir, f"{j:03d}_{safe_title}.txt")
                            
                            with open(chapter_file_path, 'w', encoding='utf-8') as f:
                                f.write(chapter)
                            
                            print(f"生成章节文件: {chapter_file_path}")
                            
                            # 更新章节级进度
                            if progress_callback and total_chapters > 0:
                                chapter_progress = 60 + (i / total_books) * 30 + (j / total_chapters) * 10
                                if chapter_progress > 90:
                                    chapter_progress = 90
                                progress_callback(chapter_progress, f"处理章节 {j}/{total_chapters}")
            else:
                # 单书籍拆分模式：按章节拆分
                print("\n=== 按章节拆分模式 ===")
                
                # 生成目录文件
                toc_file_path = os.path.join(output_dir, "目录.txt")
                with open(toc_file_path, 'w', encoding='utf-8') as f:
                    f.write('=' * 100 + '\n')
                    f.write(' ' * 40 + "【目录】\n")
                    f.write('=' * 100 + '\n')
                    
                    for i, toc_item in enumerate(toc_items, 1):
                        if generate_jump_marks:
                            jump_mark = f"{i}"
                            f.write(f"{i}. {toc_item}  [跳转标记: {jump_mark}]\n")
                        else:
                            f.write(f"{i}. {toc_item}\n")
                    
                    f.write('=' * 100 + '\n')
                
                print(f"生成目录文件: {toc_file_path}")
                
                if progress_callback:
                    progress_callback(60, "生成目录文件")
                
                # 拆分章节为单独文件
                total_chapters = len(chapter_contents)
                for i, chapter in enumerate(chapter_contents, 1):
                    # 提取章节标题作为文件名
                    chapter_title = toc_items[i-1] if i-1 < len(toc_items) else f"第{i}章"
                    
                    # 清理文件名（移除非法字符）
                    safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter_title)
                    safe_title = safe_title[:50]  # 限制文件名长度
                    
                    # 创建章节文件
                    chapter_file_path = os.path.join(output_dir, f"{i:03d}_{safe_title}.txt")
                    
                    with open(chapter_file_path, 'w', encoding='utf-8') as f:
                        f.write(chapter)
                    
                    print(f"生成章节文件: {chapter_file_path}")
                    
                    # 更新章节级进度
                    if progress_callback and total_chapters > 0:
                        chapter_progress = 60 + (i / total_chapters) * 30
                        progress_callback(chapter_progress, f"处理章节 {i}/{total_chapters}")
                

            
            print(f"成功拆分到目录: {output_dir}")
            print(f"使用ebooklib完成拆分：{epub_path} -> {output_dir}")
        else:
            # 单文件模式（原有逻辑）
            if final_content:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(final_content))
                print(f"成功写入TXT文件，大小: {os.path.getsize(output_path)} 字节")
            else:
                # 即使没有提取到内容，也创建空文件并提示
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('')
                print("警告：没有提取到任何文本内容，创建了空文件")
            
            print(f"使用ebooklib完成转换：{epub_path} -> {output_path}")
        
        # 处理文本分割
        if split_by_size:
            print("\n=== 按大小分割文本 ===")
            if split_into_multiple_files:
                # 如果已经拆分了多个文件，对每个文件进行分割
                if is_multi_book and book_groups:
                    # 多书籍模式
                    for i, book_info in enumerate(book_groups, 1):
                        book_subdir = os.path.join(output_dir, f"{i:02d}_{re.sub(r'[<>:"/\\|?*]', '', book_info['title'])[:30]}")
                        if os.path.exists(book_subdir):
                            # 查找书籍内容文件
                            for root, dirs, files in os.walk(book_subdir):
                                for file in files:
                                    if file.endswith('.txt') and '内容' in file:
                                        file_path = os.path.join(root, file)
                                        split_dir = os.path.join(book_subdir, 'split_parts')
                                        split_files = split_text_by_size(file_path, split_dir, max_file_size)
                else:
                    # 单书籍模式
                    for root, dirs, files in os.walk(output_dir):
                        for file in files:
                            if file.endswith('.txt') and not file.startswith('目录'):
                                file_path = os.path.join(root, file)
                                split_dir = os.path.join(os.path.dirname(file_path), 'split_parts')
                                split_files = split_text_by_size(file_path, split_dir, max_file_size)
            else:
                # 对单个文件进行分割
                split_dir = os.path.splitext(output_path)[0] + '_split'
                split_files = split_text_by_size(output_path, split_dir, max_file_size)
        
        # 处理zip压缩输出
        if output_zip:
            print("\n=== 生成ZIP压缩文件 ===")
            if split_into_multiple_files:
                # 压缩整个输出目录
                zip_path = os.path.splitext(output_path)[0] + '.zip'
                # 收集所有文件
                files_to_zip = []
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith('.txt'):
                            files_to_zip.append(os.path.join(root, file))
                create_zip_archive(files_to_zip, zip_path)
            else:
                # 压缩单个文件或分割后的文件
                if split_by_size and 'split_files' in locals():
                    if zip_split:
                        # 每个分割文件单独压缩为zip文件
                        for i, split_file in enumerate(split_files, 1):
                            zip_path = os.path.splitext(split_file)[0] + '.zip'
                            create_zip_archive([split_file], zip_path)
                    else:
                        # 压缩所有分割文件到一个zip文件
                        zip_path = os.path.splitext(output_path)[0] + '.zip'
                        create_zip_archive(split_files, zip_path)
                else:
                    # 压缩单个文件
                    zip_path = os.path.splitext(output_path)[0] + '.zip'
                    create_zip_archive([output_path], zip_path)
        
        return True
    except ImportError as e:
        print(f"错误：缺少依赖库，请运行 'pip install ebooklib beautifulsoup4 lxml'")
        return False
    except Exception as e:
        print(f"转换失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def batch_convert(epub_dir, output_dir, method='ebooklib', generate_jump_marks=True):
    """
    批量转换目录中的所有EPUB文件
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取目录中的所有EPUB文件
    epub_files = [f for f in os.listdir(epub_dir) if f.lower().endswith('.epub')]
    
    if not epub_files:
        print(f"错误：目录 {epub_dir} 中没有找到EPUB文件")
        return
    
    print(f"找到 {len(epub_files)} 个EPUB文件，开始转换...")
    
    for epub_file in epub_files:
        epub_path = os.path.join(epub_dir, epub_file)
        txt_file = os.path.splitext(epub_file)[0] + '.txt'
        output_path = os.path.join(output_dir, txt_file)
        
        if method == 'epub2txt':
            convert_with_epub2txt(epub_path, output_path)
        else:
            convert_with_ebooklib(epub_path, output_path, generate_jump_marks)
    
    print("批量转换完成！")


def main():
    """
    主函数
    """
    print("EPUB转TXT文件工具")
    print("=" * 50)
    
    # 检查命令行参数
    if len(sys.argv) < 3:
        print("用法1：python epub_to_txt.py <epub文件路径> <输出txt文件路径>")
        print("用法2：python epub_to_txt.py batch <epub目录> <输出目录> [method]")
        print("method可选值：ebooklib (默认) 或 epub2txt")
        return
    
    # 处理单个文件转换
    if sys.argv[1] != 'batch':
        epub_path = sys.argv[1]
        output_path = sys.argv[2]
        method = sys.argv[3] if len(sys.argv) > 3 else 'ebooklib'
        
        if not os.path.exists(epub_path):
            print(f"错误：文件 {epub_path} 不存在")
            return
        
        if method == 'epub2txt':
            convert_with_epub2txt(epub_path, output_path)
        else:
            convert_with_ebooklib(epub_path, output_path)
    
    # 处理批量转换
    else:
        if len(sys.argv) < 4:
            print("批量转换用法：python epub_to_txt.py batch <epub目录> <输出目录> [method]")
            return
        
        epub_dir = sys.argv[2]
        output_dir = sys.argv[3]
        method = sys.argv[4] if len(sys.argv) > 4 else 'ebooklib'
        
        if not os.path.exists(epub_dir):
            print(f"错误：目录 {epub_dir} 不存在")
            return
        
        batch_convert(epub_dir, output_dir, method)


def create_gui():
    """
    创建GUI界面
    """
    # 创建主窗口
    root = tk.Tk()
    root.title("EPUB转TXT工具")
    root.geometry("600x400")
    root.resizable(True, True)
    
    # 设置字体
    font_style = ("微软雅黑", 10)
    
    # 创建主框架
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 文件选择区域
    file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
    file_frame.pack(fill=tk.X, pady=10)
    
    # 单个文件选择
    single_file_frame = ttk.Frame(file_frame)
    single_file_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(single_file_frame, text="EPUB文件:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    epub_file_var = tk.StringVar()
    epub_file_entry = ttk.Entry(single_file_frame, textvariable=epub_file_var, width=50, font=font_style)
    epub_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_file():
        file_path = filedialog.askopenfilename(
            title="选择EPUB文件",
            filetypes=[("EPUB文件", "*.epub"), ("所有文件", "*.*")]
        )
        if file_path:
            epub_file_var.set(file_path)
    
    ttk.Button(single_file_frame, text="浏览", command=browse_file).pack(side=tk.RIGHT, padx=5)
    
    # 批量文件选择
    batch_frame = ttk.Frame(file_frame)
    batch_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(batch_frame, text="批量模式:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    batch_mode_var = tk.BooleanVar(value=False)
    batch_mode_check = ttk.Checkbutton(batch_frame, text="启用批量转换", variable=batch_mode_var)
    batch_mode_check.pack(side=tk.LEFT, padx=5)
    
    # 批量目录选择
    batch_dir_frame = ttk.Frame(file_frame)
    batch_dir_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(batch_dir_frame, text="EPUB目录:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    epub_dir_var = tk.StringVar()
    epub_dir_entry = ttk.Entry(batch_dir_frame, textvariable=epub_dir_var, width=50, font=font_style)
    epub_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_dir():
        dir_path = filedialog.askdirectory(title="选择EPUB文件目录")
        if dir_path:
            epub_dir_var.set(dir_path)
    
    ttk.Button(batch_dir_frame, text="浏览", command=browse_dir).pack(side=tk.RIGHT, padx=5)
    
    # 输出设置区域
    output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
    output_frame.pack(fill=tk.X, pady=10)
    
    # 单个文件输出
    single_output_frame = ttk.Frame(output_frame)
    single_output_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(single_output_frame, text="输出文件:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    output_file_var = tk.StringVar()
    output_file_entry = ttk.Entry(single_output_frame, textvariable=output_file_var, width=50, font=font_style)
    output_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_output_file():
        file_path = filedialog.asksaveasfilename(
            title="选择输出TXT文件",
            defaultextension=".txt",
            filetypes=[("TXT文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            output_file_var.set(file_path)
    
    ttk.Button(single_output_frame, text="浏览", command=browse_output_file).pack(side=tk.RIGHT, padx=5)
    
    # 批量输出目录
    batch_output_frame = ttk.Frame(output_frame)
    batch_output_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(batch_output_frame, text="输出目录:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    output_dir_var = tk.StringVar()
    output_dir_entry = ttk.Entry(batch_output_frame, textvariable=output_dir_var, width=50, font=font_style)
    output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_output_dir():
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            output_dir_var.set(dir_path)
    
    ttk.Button(batch_output_frame, text="浏览", command=browse_output_dir).pack(side=tk.RIGHT, padx=5)
    
    # 转换设置区域
    convert_frame = ttk.LabelFrame(main_frame, text="转换设置", padding="10")
    convert_frame.pack(fill=tk.X, pady=10)
    
    # 创建左右两栏布局
    left_frame = ttk.Frame(convert_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    
    right_frame = ttk.Frame(convert_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    
    # 左侧：正常的TXT流程选项
    ttk.Label(left_frame, text="TXT输出设置", font=font_style, foreground="blue").pack(anchor=tk.W, pady=5)
    
    # 转换方法选择
    method_frame = ttk.Frame(left_frame)
    method_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(method_frame, text="转换方法:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    method_var = tk.StringVar(value="ebooklib")
    method_combobox = ttk.Combobox(method_frame, textvariable=method_var, values=["ebooklib", "epub2txt"], state="readonly", font=font_style)
    method_combobox.pack(side=tk.LEFT, padx=5)
    
    # 跳转标记选项
    jump_mark_frame = ttk.Frame(left_frame)
    jump_mark_frame.pack(fill=tk.X, pady=5)
    
    jump_mark_var = tk.BooleanVar(value=True)  # 默认启用跳转标记
    jump_mark_check = ttk.Checkbutton(jump_mark_frame, text="生成跳转标记", variable=jump_mark_var, onvalue=True, offvalue=False)
    jump_mark_check.pack(side=tk.LEFT, padx=5)
    
    # 多文本拆分选项
    split_frame = ttk.Frame(left_frame)
    split_frame.pack(fill=tk.X, pady=5)
    
    split_var = tk.BooleanVar(value=False)  # 默认不拆分
    split_check = ttk.Checkbutton(split_frame, text="拆分多文本为单独文件", variable=split_var, onvalue=True, offvalue=False)
    split_check.pack(side=tk.LEFT, padx=5)
    
    # 多书籍拆分模式选项
    multi_book_split_frame = ttk.Frame(left_frame)
    multi_book_split_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(multi_book_split_frame, text="多书籍拆分模式:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    multi_book_split_var = tk.StringVar(value="merge")  # 默认全合并
    multi_book_split_combobox = ttk.Combobox(multi_book_split_frame, textvariable=multi_book_split_var, values=["merge", "split"], state="readonly", font=font_style)
    multi_book_split_combobox.pack(side=tk.LEFT, padx=5)
    
    # 添加选项说明
    ttk.Label(multi_book_split_frame, text="merge: 合并, split: 拆分", font=font_style).pack(side=tk.LEFT, padx=5)
    
    # 文本分割选项
    split_size_frame = ttk.Frame(left_frame)
    split_size_frame.pack(fill=tk.X, pady=5)
    
    split_by_size_var = tk.BooleanVar(value=False)  # 默认不分割
    split_by_size_check = ttk.Checkbutton(split_size_frame, text="按大小分割文本", variable=split_by_size_var, onvalue=True, offvalue=False)
    split_by_size_check.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(split_size_frame, text="分割大小 (MB):", font=font_style).pack(side=tk.LEFT, padx=5)
    
    max_size_var = tk.StringVar(value="10")  # 默认10MB
    max_size_entry = ttk.Entry(split_size_frame, textvariable=max_size_var, width=10, font=font_style)
    max_size_entry.pack(side=tk.LEFT, padx=5)
    
    # 长行分割选项
    line_split_frame = ttk.Frame(left_frame)
    line_split_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(line_split_frame, text="长行分割长度:", font=font_style).pack(side=tk.LEFT, padx=5)
    
    line_split_length_var = tk.StringVar(value="500")  # 默认500字符
    line_split_length_entry = ttk.Entry(line_split_frame, textvariable=line_split_length_var, width=10, font=font_style)
    line_split_length_entry.pack(side=tk.LEFT, padx=5)
    
    # 右侧：ZIP输出选项
    ttk.Label(right_frame, text="ZIP输出设置", font=font_style, foreground="red").pack(anchor=tk.W, pady=5)
    
    # Zip输出选项
    zip_output_frame = ttk.Frame(right_frame)
    zip_output_frame.pack(fill=tk.X, pady=5)
    
    output_zip_var = tk.BooleanVar(value=False)  # 默认不压缩
    output_zip_check = ttk.Checkbutton(zip_output_frame, text="以ZIP格式输出", variable=output_zip_var, onvalue=True, offvalue=False)
    output_zip_check.pack(side=tk.LEFT, padx=5)
    
    # Zip分割压缩选项
    zip_split_frame = ttk.Frame(right_frame)
    zip_split_frame.pack(fill=tk.X, pady=5)
    
    zip_split_var = tk.BooleanVar(value=False)  # 默认不分割压缩
    zip_split_check = ttk.Checkbutton(zip_split_frame, text="分割后单独压缩", variable=zip_split_var, onvalue=True, offvalue=False)
    zip_split_check.pack(side=tk.LEFT, padx=5)
    
    # 添加选项说明
    ttk.Label(zip_split_frame, text="每个分割文件单独压缩为ZIP", font=font_style).pack(side=tk.LEFT, padx=5)
    
    # 进度条区域
    progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="10")
    progress_frame.pack(fill=tk.X, pady=10)
    
    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
    progress_bar.pack(fill=tk.X, padx=5, pady=5)
    
    progress_label = ttk.Label(progress_frame, text="准备就绪", font=font_style)
    progress_label.pack(side=tk.LEFT, padx=5)
    
    # 状态显示区域
    status_frame = ttk.LabelFrame(main_frame, text="转换状态", padding="10")
    status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    status_text = tk.Text(status_frame, height=8)
    status_text.pack(fill=tk.BOTH, expand=True)
    
    # 重定向print函数到状态文本框
    class StdoutRedirector:
        def __init__(self, text_widget):
            self.text_widget = text_widget
        
        def write(self, string):
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
        
        def flush(self):
            pass
    
    # 重定向标准输出
    old_stdout = sys.stdout
    sys.stdout = StdoutRedirector(status_text)
    
    # 转换函数
    def start_conversion():
        try:
            # 清空状态文本
            status_text.delete(1.0, tk.END)
            
            # 重置进度条
            progress_var.set(0)
            progress_label.config(text="准备就绪")
            root.update_idletasks()
            
            # 检查批量模式
            if batch_mode_var.get():
                # 批量转换
                epub_dir = epub_dir_var.get()
                output_dir = output_dir_var.get()
                method = method_var.get()
                
                if not epub_dir:
                    messagebox.showerror("错误", "请选择EPUB文件目录")
                    return
                
                if not output_dir:
                    messagebox.showerror("错误", "请选择输出目录")
                    return
                
                if not os.path.exists(epub_dir):
                    messagebox.showerror("错误", "EPUB文件目录不存在")
                    return
                
                # 获取EPUB文件列表
                epub_files = [f for f in os.listdir(epub_dir) if f.lower().endswith('.epub')]
                if not epub_files:
                    messagebox.showerror("错误", f"目录 {epub_dir} 中没有找到EPUB文件")
                    return
                
                # 开始批量转换
                generate_jump_marks = jump_mark_var.get()
                
                # 更新进度条
                progress_var.set(0)
                progress_label.config(text=f"准备转换 {len(epub_files)} 个文件")
                root.update_idletasks()
                
                # 逐个转换文件并更新进度
                total_files = len(epub_files)
                for i, epub_file in enumerate(epub_files, 1):
                    epub_path = os.path.join(epub_dir, epub_file)
                    txt_file = os.path.splitext(epub_file)[0] + '.txt'
                    output_path = os.path.join(output_dir, txt_file)
                    
                    # 更新进度
                    progress = (i / total_files) * 100
                    progress_var.set(progress)
                    progress_label.config(text=f"转换中 ({i}/{total_files}): {epub_file}")
                    root.update_idletasks()
                    
                    # 执行转换
                    if method == 'epub2txt':
                        convert_with_epub2txt(epub_path, output_path)
                    else:
                        # 获取分割大小
                        try:
                            max_size = float(max_size_var.get()) * 1024 * 1024  # 转换为字节
                        except:
                            max_size = 10 * 1024 * 1024  # 默认10MB
                        
                        # 获取长行分割长度
                        try:
                            line_split_length = int(line_split_length_var.get())
                        except:
                            line_split_length = 500  # 默认500字符
                        
                        convert_with_ebooklib(
                            epub_path, 
                            output_path, 
                            generate_jump_marks, 
                            split_var.get(), 
                            multi_book_split_var.get(),
                            None,  # 批量模式下不使用进度回调
                            split_by_size_var.get(),
                            max_size,
                            output_zip_var.get(),
                            zip_split_var.get(),
                            line_split_length
                        )
                
                # 转换完成
                progress_var.set(100)
                progress_label.config(text="批量转换完成！")
                root.update_idletasks()
                messagebox.showinfo("成功", "批量转换完成！")
                
                # 重置进度条
                root.after(1000, lambda: progress_var.set(0))
                root.after(1000, lambda: progress_label.config(text="准备就绪"))
            else:
                # 单个文件转换
                epub_path = epub_file_var.get()
                output_path = output_file_var.get()
                method = method_var.get()
                
                if not epub_path:
                    messagebox.showerror("错误", "请选择EPUB文件")
                    return
                
                if not output_path:
                    messagebox.showerror("错误", "请选择输出文件")
                    return
                
                if not os.path.exists(epub_path):
                    messagebox.showerror("错误", "EPUB文件不存在")
                    return
                
                # 更新进度条
                progress_var.set(0)
                progress_label.config(text="准备转换...")
                root.update_idletasks()
                
                # 开始单个文件转换
                generate_jump_marks = jump_mark_var.get()
                split_files = split_var.get()
                multi_book_mode = multi_book_split_var.get()
                
                progress_var.set(10)
                progress_label.config(text="分析EPUB文件...")
                root.update_idletasks()
                
                progress_var.set(20)
                progress_label.config(text="解析EPUB结构...")
                root.update_idletasks()
                
                progress_var.set(30)
                progress_label.config(text="提取目录信息...")
                root.update_idletasks()
                
                progress_var.set(40)
                progress_label.config(text="提取章节内容...")
                root.update_idletasks()
                
                if method == "epub2txt":
                    success = convert_with_epub2txt(epub_path, output_path)
                else:
                    # 定义进度回调函数
                    def progress_callback(progress, status):
                        progress_var.set(progress)
                        progress_label.config(text=status)
                        root.update_idletasks()
                    
                    # 对于ebooklib方法，使用进度回调
                    progress_var.set(50)
                    progress_label.config(text="处理文本内容...")
                    root.update_idletasks()
                    
                    # 获取分割大小
                    try:
                        max_size = float(max_size_var.get()) * 1024 * 1024  # 转换为字节
                    except:
                        max_size = 10 * 1024 * 1024  # 默认10MB
                    
                    # 获取长行分割长度
                    try:
                        line_split_length = int(line_split_length_var.get())
                    except:
                        line_split_length = 500  # 默认500字符
                    
                    success = convert_with_ebooklib(
                        epub_path, 
                        output_path, 
                        generate_jump_marks, 
                        split_files, 
                        multi_book_mode, 
                        progress_callback,
                        split_by_size_var.get(),
                        max_size,
                        output_zip_var.get(),
                        zip_split_var.get(),
                        line_split_length
                    )
                
                progress_var.set(80)
                progress_label.config(text="整理输出文件...")
                root.update_idletasks()
                
                if success:
                    progress_var.set(100)
                    progress_label.config(text="转换完成！")
                    root.update_idletasks()
                    messagebox.showinfo("成功", "转换完成！")
                else:
                    progress_var.set(0)
                    progress_label.config(text="转换失败")
                    root.update_idletasks()
                    messagebox.showerror("错误", "转换失败，请查看状态信息")
                
                # 重置进度条
                root.after(1000, lambda: progress_var.set(0))
                root.after(1000, lambda: progress_label.config(text="准备就绪"))
                    
        except Exception as e:
            # 发生错误时重置进度条
            progress_var.set(0)
            progress_label.config(text="错误")
            root.update_idletasks()
            messagebox.showerror("错误", f"转换过程中发生错误：{str(e)}")
            # 重置进度条
            root.after(1000, lambda: progress_var.set(0))
            root.after(1000, lambda: progress_label.config(text="准备就绪"))
    
    # 按钮区域
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="开始转换", command=start_conversion, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
    
    def exit_app():
        # 恢复标准输出
        sys.stdout = old_stdout
        root.destroy()
    
    ttk.Button(button_frame, text="退出", command=exit_app).pack(side=tk.RIGHT, padx=5)
    
    # 添加样式
    style = ttk.Style()
    try:
        # 尝试使用Windows主题
        style.theme_use('vista')
    except:
        pass
    
    # 配置按钮样式
    style.configure("Accent.TButton", font=font_style, padding=10)
    
    # 窗口关闭事件
    def on_closing():
        sys.stdout = old_stdout
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 运行主循环
    root.mainloop()


def main():
    """
    主函数
    """
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        print("EPUB转TXT文件工具")
        print("=" * 50)
        
        # 检查命令行参数
        if len(sys.argv) < 3:
            print("用法1：python epub_to_txt.py <epub文件路径> <输出txt文件路径>")
            print("用法2：python epub_to_txt.py batch <epub目录> <输出目录> [method]")
            print("method可选值：ebooklib (默认) 或 epub2txt")
            print("\n无命令行参数时将启动GUI界面")
            return
        
        # 处理单个文件转换
        if sys.argv[1] != 'batch':
            epub_path = sys.argv[1]
            output_path = sys.argv[2]
            method = sys.argv[3] if len(sys.argv) > 3 else 'ebooklib'
            generate_jump_marks = not (len(sys.argv) > 4 and sys.argv[4] == 'no_jump')
            
            if not os.path.exists(epub_path):
                print(f"错误：文件 {epub_path} 不存在")
                return
            
            if method == 'epub2txt':
                convert_with_epub2txt(epub_path, output_path)
            else:
                convert_with_ebooklib(epub_path, output_path, generate_jump_marks)
        
        # 处理批量转换
        else:
            if len(sys.argv) < 4:
                print("批量转换用法：python epub_to_txt.py batch <epub目录> <输出目录> [method] [no_jump]")
                return
            
            epub_dir = sys.argv[2]
            output_dir = sys.argv[3]
            method = sys.argv[4] if len(sys.argv) > 4 else 'ebooklib'
            generate_jump_marks = not (len(sys.argv) > 5 and sys.argv[5] == 'no_jump')
            
            if not os.path.exists(epub_dir):
                print(f"错误：目录 {epub_dir} 不存在")
                return
            
            batch_convert(epub_dir, output_dir, method, generate_jump_marks)
    else:
        # GUI模式
        create_gui()


if __name__ == "__main__":
    main()
