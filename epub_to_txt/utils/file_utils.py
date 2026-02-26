# 文件操作工具模块
"""
文件操作工具
负责文件读写、目录管理、路径处理等操作
"""

import os
import re
from typing import List, Optional
from ..config.settings import defaults, regex_patterns
from ..exceptions.file import FileNotFoundError, DirectoryNotFoundError, PermissionError

class FileUtils:
    """
    文件操作工具类
    """
    
    @staticmethod
    def ensure_directory(directory: str) -> None:
        """
        确保目录存在
        
        Args:
            directory: 目录路径
        
        Raises:
            PermissionError: 权限不足
        """
        if not directory:
            return
        
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        except Exception as e:
            raise PermissionError(directory, "创建目录") from e
    
    @staticmethod
    def safe_filename(filename: str, max_length: int = None) -> str:
        """
        生成安全的文件名
        
        Args:
            filename: 原始文件名
            max_length: 最大长度
        
        Returns:
            安全的文件名
        """
        if not filename:
            return "unknown"
        
        # 移除非法字符
        safe_name = re.sub(regex_patterns['invalid_filename_chars'], '', filename)
        
        # 限制长度
        max_len = max_length or defaults['max_filename_length']
        if len(safe_name) > max_len:
            safe_name = safe_name[:max_len]
        
        # 确保文件名不为空
        if not safe_name:
            safe_name = "unknown"
        
        return safe_name
    
    @staticmethod
    def split_file_by_size(file_path: str, output_dir: str, max_size: int) -> List[str]:
        """
        按大小分割文件
        
        Args:
            file_path: 输入文件路径
            output_dir: 输出目录
            max_size: 最大文件大小（字节）
        
        Returns:
            分割后的文件路径列表
        
        Raises:
            FileNotFoundError: 文件不存在
            PermissionError: 权限不足
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        
        FileUtils.ensure_directory(output_dir)
        
        try:
            # 使用指定的分割大小
            print(f"分割大小: {max_size} 字节")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            if file_size <= max_size:
                return [file_path]
            
            parts = []
            part_number = 1
            current_size = 0
            current_content = []
            
            # 读取文件
            with open(file_path, 'r', encoding=defaults['default_encoding']) as f:
                for line in f:
                    line_size = len(line.encode(defaults['default_encoding']))
                    
                    if current_size + line_size > max_size and current_content:
                        # 保存当前部分
                        part_filename = os.path.join(output_dir, f"part_{part_number:03d}.txt")
                        with open(part_filename, 'w', encoding=defaults['default_encoding']) as part_file:
                            part_file.writelines(current_content)
                        parts.append(part_filename)
                        
                        # 重置
                        current_size = 0
                        current_content = []
                        part_number += 1
                    
                    current_content.append(line)
                    current_size += line_size
            
            # 保存最后一部分
            if current_content:
                part_filename = os.path.join(output_dir, f"part_{part_number:03d}.txt")
                with open(part_filename, 'w', encoding=defaults['default_encoding']) as part_file:
                    part_file.writelines(current_content)
                parts.append(part_filename)
            
            return parts
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError)):
                raise
            raise PermissionError(file_path, "分割文件") from e
    
    @staticmethod
    def read_file_chunked(file_path: str, chunk_size: int = None) -> str:
        """
        分块读取文件
        
        Args:
            file_path: 文件路径
            chunk_size: 块大小
        
        Returns:
            文件内容
        
        Raises:
            FileNotFoundError: 文件不存在
            PermissionError: 权限不足
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        
        chunk = chunk_size or defaults['chunk_size']
        content = []
        
        try:
            with open(file_path, 'r', encoding=defaults['default_encoding']) as f:
                while True:
                    data = f.read(chunk)
                    if not data:
                        break
                    content.append(data)
            
            return ''.join(content)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise PermissionError(file_path, "读取文件") from e
    
    @staticmethod
    def write_file_safely(file_path: str, content: str) -> None:
        """
        安全写入文件
        
        Args:
            file_path: 文件路径
            content: 内容
        
        Raises:
            PermissionError: 权限不足
        """
        # 确保目录存在
        FileUtils.ensure_directory(os.path.dirname(file_path))
        
        try:
            # 使用utf-8编码确保中文字符正确处理
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise PermissionError(file_path, "写入文件") from e
    
    @staticmethod
    def get_files_by_extension(directory: str, extension: str) -> List[str]:
        """
        获取目录中指定扩展名的文件
        
        Args:
            directory: 目录路径
            extension: 扩展名（不含点）
        
        Returns:
            文件路径列表
        
        Raises:
            DirectoryNotFoundError: 目录不存在
        """
        if not os.path.exists(directory):
            raise DirectoryNotFoundError(directory)
        
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.lower().endswith(f".{extension.lower()}"):
                    files.append(os.path.join(root, filename))
        
        return files
