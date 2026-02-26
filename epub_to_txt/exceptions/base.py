# 基础异常类
"""
基础异常类定义
所有EPUB转换相关异常的基类
"""

class EPUBConversionError(Exception):
    """
    EPUB转换异常基类
    """
    def __init__(self, message: str, error_code: int = 99):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """
        返回错误消息
        """
        return f"[错误 {self.error_code}] {self.message}"
