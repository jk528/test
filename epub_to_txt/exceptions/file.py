# 文件相关异常类
"""
文件操作相关异常类
"""

from .base import EPUBConversionError

class FileNotFoundError(EPUBConversionError):
    """
    文件不存在异常
    """
    def __init__(self, file_path: str):
        """
        初始化异常
        
        Args:
            file_path: 文件路径
        """
        message = f"文件不存在: {file_path}"
        super().__init__(message, error_code=1)

class DirectoryNotFoundError(EPUBConversionError):
    """
    目录不存在异常
    """
    def __init__(self, directory_path: str):
        """
        初始化异常
        
        Args:
            directory_path: 目录路径
        """
        message = f"目录不存在: {directory_path}"
        super().__init__(message, error_code=1)

class PermissionError(EPUBConversionError):
    """
    权限错误异常
    """
    def __init__(self, path: str, operation: str = "操作"):
        """
        初始化异常
        
        Args:
            path: 路径
            operation: 操作类型
        """
        message = f"权限不足，无法{operation}: {path}"
        super().__init__(message, error_code=5)
