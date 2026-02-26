# 编码相关异常类
"""
编码处理相关异常类
"""

from .base import EPUBConversionError

class EncodingError(EPUBConversionError):
    """
    编码错误异常
    """
    def __init__(self, encoding: str, error: Exception = None):
        """
        初始化异常
        
        Args:
            encoding: 编码名称
            error: 原始异常
        """
        if error:
            message = f"编码错误 ({encoding}): {str(error)}"
        else:
            message = f"编码错误: {encoding}"
        super().__init__(message, error_code=3)
