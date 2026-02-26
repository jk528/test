# 内存相关异常类
"""
内存使用相关异常类
"""

from .base import EPUBConversionError

class MemoryError(EPUBConversionError):
    """
    内存错误异常
    """
    def __init__(self, message: str = "内存不足"):
        """
        初始化异常
        
        Args:
            message: 错误消息
        """
        super().__init__(message, error_code=4)
