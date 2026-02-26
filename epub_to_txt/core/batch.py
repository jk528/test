# 批量转换模块
"""
批量转换模块
负责批量处理多个EPUB文件
"""

import os
from typing import List
from ..config.settings import defaults
from ..exceptions import DirectoryNotFoundError
from ..utils.file_utils import FileUtils
from .converter import convert_with_ebooklib, convert_with_epub2txt

def batch_convert(
    epub_dir: str,
    output_dir: str,
    method: str = 'ebooklib',
    generate_jump_marks: bool = True,
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
    sort_chapters: bool = True,
    progress_callback: callable = None
) -> bool:
    """
    批量转换EPUB文件
    
    Args:
        epub_dir: EPUB文件目录
        output_dir: 输出目录
        method: 转换方法
        generate_jump_marks: 是否生成跳转标记
        split_by_size: 是否按大小分割
        max_file_size: 最大文件大小
        output_zip: 是否输出ZIP
        zip_split: 是否分割压缩
        line_split_length: 长行分割长度
        compress_level: 压缩级别
        merge_threshold: 文本合并阈值
        poetry_format: 是否优化诗歌排版
        chapter_title_optimize: 是否优化章节标题
        pure_read: 是否使用纯净读取模式
        sort_chapters: 是否对章节进行排序
        progress_callback: 进度回调函数
    
    Returns:
        是否成功
    
    Raises:
        DirectoryNotFoundError: 目录不存在
    """
    if not os.path.exists(epub_dir):
        raise DirectoryNotFoundError(epub_dir)
    
    # 确保输出目录存在
    FileUtils.ensure_directory(output_dir)
    
    # 获取EPUB文件列表
    epub_files = FileUtils.get_files_by_extension(epub_dir, 'epub')
    
    if not epub_files:
        print(f"错误：目录 {epub_dir} 中没有找到EPUB文件")
        return False
    
    print(f"找到 {len(epub_files)} 个EPUB文件，开始批量转换...")
    
    success_count = 0
    failure_count = 0
    
    for i, epub_file in enumerate(epub_files, 1):
        if progress_callback:
            progress = (i / len(epub_files)) * 100
            progress_callback(progress, f"转换 {i}/{len(epub_files)}: {os.path.basename(epub_file)}")
        
        try:
            # 生成输出文件路径
            epub_name = os.path.basename(epub_file)
            txt_name = os.path.splitext(epub_name)[0] + '.txt'
            output_path = os.path.join(output_dir, txt_name)
            
            # 执行转换
            success = False
            if method == 'epub2txt':
                success = convert_with_epub2txt(epub_file, output_path)
            else:
                success = convert_with_ebooklib(
                    epub_file,
                    output_path,
                    generate_jump_marks=generate_jump_marks,
                    split_into_multiple_files=False,
                    split_by_size=split_by_size,
                    max_file_size=max_file_size,
                    output_zip=output_zip,
                    zip_split=zip_split,
                    line_split_length=line_split_length,
                    compress_level=compress_level,
                    merge_threshold=merge_threshold,
                    poetry_format=poetry_format,
                    chapter_title_optimize=chapter_title_optimize,
                    pure_read=pure_read,
                    sort_chapters=sort_chapters
                )
            
            if success:
                print(f"成功：{epub_name} -> {txt_name}")
                success_count += 1
            else:
                print(f"失败：{epub_name}")
                failure_count += 1
                
        except Exception as e:
            print(f"错误处理 {os.path.basename(epub_file)}: {str(e)}")
            failure_count += 1
            continue
    
    # 输出统计信息
    print("\n批量转换完成！")
    print(f"总文件数: {len(epub_files)}")
    print(f"成功: {success_count}")
    print(f"失败: {failure_count}")
    
    return failure_count == 0
