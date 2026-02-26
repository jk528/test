# EPUB转TXT工具包初始化文件
"""
EPUB转TXT工具包
功能：将EPUB电子书转换为TXT文本文件
"""

from .core.converter import convert_with_ebooklib, convert_with_epub2txt
from .core.batch import batch_convert
from .gui.app import create_gui
from .utils.toc_fixer import TOCFixer

__version__ = "1.0.0"
__author__ = "EPUB to TXT Team"
__all__ = [
    "convert_with_ebooklib",
    "convert_with_epub2txt",
    "batch_convert",
    "create_gui",
    "TOCFixer"
]

# 便捷函数
def fix_toc(input_file, output_file):
    """
    修复文件中的重复目录问题
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    
    Returns:
        是否成功
    """
    return TOCFixer.fix_file(input_file, output_file)
