# 格式相关异常类
"""
文件格式相关异常类
"""

from .base import EPUBConversionError

class InvalidEPUBError(EPUBConversionError):
    """
    无效的EPUB文件异常
    """
    def __init__(self, epub_path: str, error: Exception = None):
        """
        初始化异常
        
        Args:
            epub_path: EPUB文件路径
            error: 原始异常
        """
        if error:
            message = f"无效的EPUB文件: {epub_path} - {str(error)}"
        else:
            message = f"无效的EPUB文件: {epub_path}"
        super().__init__(message, error_code=2)

class FormatError(EPUBConversionError):
    """
    格式错误异常
    """
    def __init__(self, message: str):
        """
        初始化异常
        
        Args:
            message: 错误消息
        """
        super().__init__(message, error_code=2)
