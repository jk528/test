# 压缩工具模块
"""
压缩工具
负责文件压缩和解压缩操作
"""

import os
import zipfile
from typing import List
from ..config.settings import defaults
from ..exceptions.file import FileNotFoundError, PermissionError

class ZipUtils:
    """
    压缩工具类
    """
    
    @staticmethod
    def create_zip_archive(files: List[str], zip_path: str, compress_level: int = 6) -> bool:
        """
        创建ZIP压缩文件
        
        Args:
            files: 要压缩的文件列表
            zip_path: 输出ZIP文件路径
            compress_level: 压缩级别（0-9，0=无压缩，9=最高压缩）
        
        Returns:
            是否成功
        
        Raises:
            FileNotFoundError: 文件不存在
            PermissionError: 权限不足
        """
        # 检查文件是否存在
        for file_path in files:
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(zip_path)
        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                raise PermissionError(output_dir, "创建目录") from e
        
        try:
            # 根据压缩级别选择压缩方法
            if compress_level == 0:
                compression = zipfile.ZIP_STORED
            else:
                compression = zipfile.ZIP_DEFLATED
            
            with zipfile.ZipFile(zip_path, 'w', compression) as zipf:
                # 设置压缩级别
                zipf.compression = compression
                for file_path in files:
                    if os.path.isfile(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            
            return True
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError)):
                raise
            raise PermissionError(zip_path, "创建ZIP文件") from e
    
    @staticmethod
    def create_split_zip(files: List[str], base_path: str, compress_level: int = 6) -> List[str]:
        """
        创建分割的ZIP文件
        
        Args:
            files: 要压缩的文件列表
            base_path: 基础路径
            compress_level: 压缩级别（0-9，0=无压缩，9=最高压缩）
        
        Returns:
            创建的ZIP文件路径列表
        """
        zip_files = []
        
        for i, file_path in enumerate(files, 1):
            zip_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.zip"
            zip_path = os.path.join(os.path.dirname(base_path), zip_name)
            
            if ZipUtils.create_zip_archive([file_path], zip_path, compress_level):
                zip_files.append(zip_path)
        
        return zip_files
    
    @staticmethod
    def zip_directory(directory: str, zip_path: str, compress_level: int = 6) -> bool:
        """
        压缩整个目录
        
        Args:
            directory: 要压缩的目录
            zip_path: 输出ZIP文件路径
            compress_level: 压缩级别（0-9，0=无压缩，9=最高压缩）
        
        Returns:
            是否成功
        
        Raises:
            FileNotFoundError: 目录不存在
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(directory)
        
        files_to_zip = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    files_to_zip.append(file_path)
        
        if not files_to_zip:
            return False
        
        return ZipUtils.create_zip_archive(files_to_zip, zip_path, compress_level)
