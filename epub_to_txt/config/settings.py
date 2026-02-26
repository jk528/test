# 配置模块 - 集中管理所有配置选项和常量
"""
配置设置模块
集中管理工具的所有配置选项、默认值和常量
"""

import os
from typing import Dict, Any

# 默认配置
defaults: Dict[str, Any] = {
    # 转换设置
    'default_method': 'ebooklib',  # 默认转换方法
    'generate_jump_marks': True,   # 默认生成跳转标记
    'split_into_multiple_files': False,  # 默认不拆分多文件
    'multi_book_split_mode': 'merge',  # 默认多书籍合并模式
    
    # 文本处理设置
    'line_split_length': 500,  # 默认长行分割长度
    'max_file_size': 10 * 1024 * 1024,  # 默认分割大小 (10MB)
    
    # 压缩设置
    'output_zip': False,  # 默认不输出ZIP
    'zip_split': False,  # 默认不分割压缩
    
    # 编码设置
    'default_encoding': 'utf-8',  # 默认编码
    'fallback_encodings': ['utf-8', 'gbk', 'latin-1', 'utf-16'],  # 回退编码
    
    # 进度条设置
    'progress_update_interval': 0.1,  # 进度更新间隔（秒）
    
    # 文件和目录设置
    'max_filename_length': 50,  # 最大文件名长度
    'temp_dir': os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'epub_to_txt', 'temp'),  # 临时目录
    
    # 性能设置
    'chunk_size': 8192,  # 文件读取块大小
    'max_memory_usage': 1024 * 1024 * 1024,  # 最大内存使用 (1GB)
}

# 错误消息
error_messages: Dict[str, str] = {
    'file_not_found': '文件不存在: {}',
    'directory_not_found': '目录不存在: {}',
    'invalid_epub': '无效的EPUB文件: {}',
    'conversion_failed': '转换失败: {}',
    'encoding_error': '编码错误: {}',
    'memory_error': '内存不足，无法处理大文件',
    'permission_error': '权限错误: {}',
}

# 成功消息
success_messages: Dict[str, str] = {
    'conversion_success': '转换成功: {}',
    'batch_conversion_success': '批量转换完成，处理了 {} 个文件',
    'split_success': '成功分割为 {} 个文件',
    'zip_success': '成功创建ZIP文件: {}',
}

# 正则表达式模式
regex_patterns: Dict[str, str] = {
    # 章节标题模式
    'chapter_title': r'(第[一二三四五六七八九十百千]+[回章节卷]|卷[一二三四五六七八九十百千]+)',
    'chapter_number': r'第(\d+)[回章节卷]',
    
    # 文件名清理模式
    'invalid_filename_chars': r'[<>:"/\\|?*]',
    
    # 文本处理模式
    'multiple_spaces': r'\s+',
    'trailing_whitespace': r'\s+$',
    
    # 导航标记模式
    'jump_mark': r'\[跳转标记: (\d+)\]',
}

# 常量定义
class Constants:
    # EPUB项目类型
    EPUB_HTML = 1
    EPUB_IMAGE = 2
    EPUB_STYLE = 3
    EPUB_SCRIPT = 4
    EPUB_OTHER = 5
    
    # 分割模式
    SPLIT_MODE_NONE = 'none'
    SPLIT_MODE_CHAPTER = 'chapter'
    SPLIT_MODE_SIZE = 'size'
    
    # 多书籍模式
    MULTI_BOOK_MODE_MERGE = 'merge'
    MULTI_BOOK_MODE_SPLIT = 'split'
    
    # 转换方法
    METHOD_EBOOKLIB = 'ebooklib'
    METHOD_EPUB2TXT = 'epub2txt'
    
    # 错误码
    ERROR_SUCCESS = 0
    ERROR_FILE_NOT_FOUND = 1
    ERROR_INVALID_FORMAT = 2
    ERROR_ENCODING = 3
    ERROR_MEMORY = 4
    ERROR_PERMISSION = 5
    ERROR_UNKNOWN = 99

# 导出配置
def get_config() -> Dict[str, Any]:
    """
    获取完整配置
    """
    return {
        'defaults': defaults,
        'error_messages': error_messages,
        'success_messages': success_messages,
        'regex_patterns': regex_patterns,
        'constants': Constants,
    }

# 导出常量
constants = Constants()
