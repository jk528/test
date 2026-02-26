# GUI应用模块
"""
GUI应用模块
提供图形用户界面
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sys
import os

from ..core.converter import convert_with_ebooklib, convert_with_epub2txt
from ..core.batch import batch_convert
from ..config.settings import defaults


class EPUBConverterApp:
    """
    EPUB转换器GUI应用类
    """
    
    def __init__(self, root):
        """
        初始化应用
        
        Args:
            root: Tk根窗口
        """
        self.root = root
        self.root.title("EPUB转TXT工具 v1.0")
        # 获取屏幕大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # 设置窗口大小为屏幕大小，保留窗口控制按钮
        self.root.geometry(f"{screen_width}x{screen_height}")
        # 允许调整大小
        self.root.resizable(True, True)
        
        # 设置字体
        self.font_style = ("微软雅黑", 10)
        self.font_title = ("微软雅黑", 11, "bold")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建界面
        self._create_widgets()
        
        # 重定向标准输出
        self._redirect_stdout()
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self._on_window_resize)
    
    def _on_window_resize(self, event):
        """
        窗口大小变化事件处理
        """
        # 当窗口大小变化时，更新控件布局
        pass
    
    def _create_widgets(self):
        """
        创建界面控件
        """
        # 创建顶部标题
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            title_frame, 
            text="EPUB转TXT工具", 
            font=("微软雅黑", 14, "bold"),
            foreground="#2c3e50"
        ).pack(anchor=tk.W)
        
        # 创建使用说明区域
        self._create_usage_instructions()
        
        # 创建转换状态区域（默认显示）
        self._create_status_display(self.main_frame)
        
        # 进度显示区域
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=(15, 0))
        self._create_progress_display(progress_frame)
        
        # 按钮区域 - 移到上面一点
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self._create_buttons(button_frame)
        
        # 创建主内容区域
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧区域：文件和输出设置
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 文件选择区域
        self._create_file_selection(left_frame)
        
        # 输出设置区域
        self._create_output_settings(left_frame)
        
        # 右侧区域：转换设置
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 转换设置区域
        self._create_conversion_settings(right_frame)
        
        # 添加样式
        self._apply_styles()
    
    def _create_file_selection(self, parent):
        """
        创建文件选择区域
        """
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="15")
        file_frame.pack(fill=tk.X, pady=10)
        
        # 批量模式选择
        batch_frame = ttk.Frame(file_frame)
        batch_frame.pack(fill=tk.X, pady=8)
        
        self.batch_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            batch_frame, 
            text="批量转换模式", 
            variable=self.batch_mode_var,
            command=self._toggle_batch_mode,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 单个文件选择
        self.single_file_frame = ttk.Frame(file_frame)
        self.single_file_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(self.single_file_frame, text="EPUB文件:", font=self.font_style).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.epub_file_var = tk.StringVar()
        self.epub_file_entry = ttk.Entry(
            self.single_file_frame, 
            textvariable=self.epub_file_var, 
            font=self.font_style
        )
        self.epub_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            self.single_file_frame, 
            text="浏览", 
            command=self._browse_file,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # 批量文件选择
        self.batch_dir_frame = ttk.Frame(file_frame)
        # 初始不打包，由_toggle_batch_mode控制
        
        ttk.Label(self.batch_dir_frame, text="EPUB目录:", font=self.font_style).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.epub_dir_var = tk.StringVar()
        self.epub_dir_entry = ttk.Entry(
            self.batch_dir_frame, 
            textvariable=self.epub_dir_var, 
            font=self.font_style
        )
        self.epub_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            self.batch_dir_frame, 
            text="浏览", 
            command=self._browse_directory,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # 默认隐藏批量模式控件
        self._toggle_batch_mode()
    
    def _create_output_settings(self, parent):
        """
        创建输出设置区域
        """
        output_frame = ttk.LabelFrame(parent, text="输出设置", padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        # 输出路径容器
        self.output_path_frame = ttk.Frame(output_frame)
        self.output_path_frame.pack(fill=tk.X, pady=8)
        
        # 单个文件输出
        self.single_output_frame = ttk.Frame(self.output_path_frame)
        self.single_output_frame.pack(fill=tk.X)
        
        ttk.Label(self.single_output_frame, text="输出文件:", font=self.font_style, width=10).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.output_file_var = tk.StringVar()
        self.output_file_entry = ttk.Entry(
            self.single_output_frame, 
            textvariable=self.output_file_var, 
            font=self.font_style
        )
        self.output_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            self.single_output_frame, 
            text="浏览", 
            command=self._browse_output_file,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # 批量输出目录
        self.batch_output_frame = ttk.Frame(self.output_path_frame)
        # 初始不打包，由_toggle_batch_mode控制
        
        ttk.Label(self.batch_output_frame, text="输出文件夹:", font=self.font_style, width=10).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(
            self.batch_output_frame, 
            textvariable=self.output_dir_var, 
            font=self.font_style
        )
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            self.batch_output_frame, 
            text="浏览", 
            command=self._browse_output_directory,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
    
    def _create_conversion_settings(self, parent):
        """
        创建转换设置区域
        """
        convert_frame = ttk.LabelFrame(parent, text="转换设置", padding="15")
        convert_frame.pack(fill=tk.X, pady=10)
        
        # 创建左右两栏布局
        left_frame = ttk.Frame(convert_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        right_frame = ttk.Frame(convert_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # 左侧：TXT输出设置
        ttk.Label(left_frame, text="TXT输出设置", font=self.font_title, foreground="#3498db").pack(anchor=tk.W, pady=10)

        # 纯净读取选项
        pure_read_frame = ttk.Frame(left_frame)
        pure_read_frame.pack(fill=tk.X, pady=8)
        
        self.pure_read_var = tk.BooleanVar(value=False)
        # 添加回调函数，当勾选纯净模式时，其他选项都变为否
        self.pure_read_var.trace_add("write", self._on_pure_read_change)
        ttk.Checkbutton(
            pure_read_frame, 
            text="纯净读取（保留原EPUB排版）", 
            variable=self.pure_read_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)

        # 转换方法选择
        method_frame = ttk.Frame(left_frame)
        method_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(method_frame, text="转换方法:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.method_var = tk.StringVar(value="ebooklib")
        ttk.Combobox(
            method_frame, 
            textvariable=self.method_var, 
            values=["ebooklib", "epub2txt"], 
            state="readonly", 
            font=self.font_style,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # 跳转标记选项
        jump_mark_frame = ttk.Frame(left_frame)
        jump_mark_frame.pack(fill=tk.X, pady=8)
        
        self.jump_mark_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            jump_mark_frame, 
            text="生成跳转标记", 
            variable=self.jump_mark_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 多文本拆分选项
        split_frame = ttk.Frame(left_frame)
        split_frame.pack(fill=tk.X, pady=8)
        
        self.split_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            split_frame, 
            text="拆分多文本为单独文件", 
            variable=self.split_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 多书籍拆分模式
        multi_book_frame = ttk.Frame(left_frame)
        multi_book_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(multi_book_frame, text="多书籍拆分模式:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.multi_book_mode_var = tk.StringVar(value="merge")
        ttk.Combobox(
            multi_book_frame, 
            textvariable=self.multi_book_mode_var, 
            values=["merge", "split"], 
            state="readonly", 
            font=self.font_style,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # 排版设置
        ttk.Label(left_frame, text="排版设置", font=self.font_title, foreground="#3498db").pack(anchor=tk.W, pady=10)
        
        # 长行分割长度
        line_split_frame = ttk.Frame(left_frame)
        line_split_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(line_split_frame, text="长行分割长度:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.line_split_length_var = tk.StringVar(value="500")
        ttk.Entry(
            line_split_frame, 
            textvariable=self.line_split_length_var, 
            width=8, 
            font=self.font_style
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(line_split_frame, text="默认值：500", font=self.font_style, foreground="#666666").pack(side=tk.LEFT, padx=10)
        
        # 文本合并阈值
        merge_threshold_frame = ttk.Frame(left_frame)
        merge_threshold_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(merge_threshold_frame, text="文本合并阈值:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.merge_threshold_var = tk.StringVar(value="30")
        ttk.Entry(
            merge_threshold_frame, 
            textvariable=self.merge_threshold_var, 
            width=8, 
            font=self.font_style
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(merge_threshold_frame, text="默认值：30", font=self.font_style, foreground="#666666").pack(side=tk.LEFT, padx=10)
        
        # 诗歌排版选项
        poetry_frame = ttk.Frame(left_frame)
        poetry_frame.pack(fill=tk.X, pady=8)
        
        self.poetry_format_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            poetry_frame, 
            text="优化诗歌排版", 
            variable=self.poetry_format_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 章节标题优化
        chapter_title_frame = ttk.Frame(left_frame)
        chapter_title_frame.pack(fill=tk.X, pady=8)
        
        self.chapter_title_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            chapter_title_frame, 
            text="优化章节标题", 
            variable=self.chapter_title_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 章节排序选项
        sort_frame = ttk.Frame(left_frame)
        sort_frame.pack(fill=tk.X, pady=8)
        
        self.sort_chapters_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            sort_frame, 
            text="排序后输出", 
            variable=self.sort_chapters_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 右侧：压缩和高级设置
        ttk.Label(right_frame, text="压缩和高级设置", font=self.font_title, foreground="#e74c3c").pack(anchor=tk.W, pady=10)
        
        # Zip输出选项
        zip_output_frame = ttk.Frame(right_frame)
        zip_output_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(zip_output_frame, text="以ZIP格式输出:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.output_zip_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            zip_output_frame, 
            variable=self.output_zip_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 文本分割选项
        split_size_frame = ttk.Frame(right_frame)
        split_size_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(split_size_frame, text="是否按大小分割文本:", font=self.font_style, width=18).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.split_by_size_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            split_size_frame, 
            variable=self.split_by_size_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(split_size_frame, text="分割大小 (MB):", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.max_size_var = tk.StringVar(value="20")
        ttk.Entry(
            split_size_frame, 
            textvariable=self.max_size_var, 
            width=8, 
            font=self.font_style
        ).pack(side=tk.LEFT, padx=5)
        
        # Zip分割压缩选项
        zip_split_frame = ttk.Frame(right_frame)
        zip_split_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(zip_split_frame, text="是否分割后单独压缩:", font=self.font_style, width=18).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.zip_split_var = tk.BooleanVar(value=False)
        # 添加回调函数，当勾选时自动勾选其他必要选项
        self.zip_split_var.trace_add("write", self._on_zip_split_change)
        ttk.Checkbutton(
            zip_split_frame, 
            variable=self.zip_split_var,
            style="TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        

        
        # 压缩级别选项
        compress_level_frame = ttk.Frame(right_frame)
        compress_level_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(compress_level_frame, text="压缩级别:", font=self.font_style, width=12).pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
        
        self.compress_level_var = tk.StringVar(value="6")
        ttk.Combobox(
            compress_level_frame, 
            textvariable=self.compress_level_var, 
            values=["0", "1", "3", "5", "6", "7", "9"], 
            state="readonly", 
            font=self.font_style,
            width=5
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(compress_level_frame, text="(0=无压缩, 9=最高压缩)", font=self.font_style, foreground="#666666").pack(side=tk.LEFT, padx=5, anchor=tk.CENTER)
    
    def _create_progress_display(self, parent):
        """
        创建进度显示区域
        """
        progress_frame = ttk.LabelFrame(parent, text="转换进度", padding="15")
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100, 
            style="Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=8)
        
        self.progress_label = ttk.Label(progress_frame, text="准备就绪", font=self.font_style, foreground="#27ae60")
        self.progress_label.pack(side=tk.LEFT, padx=5)
    
    def _create_usage_instructions(self):
        """
        创建使用说明区域
        """
        # 创建使用说明容器
        self.instructions_container = ttk.Frame(self.main_frame)
        self.instructions_container.pack(fill=tk.X, pady=(0, 15))
        
        # 创建显示/隐藏按钮
        toggle_frame = ttk.Frame(self.instructions_container)
        toggle_frame.pack(fill=tk.X)
        
        self.instructions_visible = False
        self.instructions_button = ttk.Button(
            toggle_frame, 
            text="显示使用说明", 
            command=self._toggle_instructions
        )
        self.instructions_button.pack(side=tk.LEFT, padx=5)
        
        # 创建说明框架（默认隐藏）
        self.instructions_frame = ttk.LabelFrame(self.instructions_container, text="使用说明", padding="15")
        
        # 创建说明文本
        self.instructions_text = tk.Text(
            self.instructions_frame, 
            height=8, 
            font=self.font_style, 
            wrap=tk.WORD, 
            bg="#f8f9fa", 
            fg="#34495e",
            state=tk.DISABLED
        )
        self.instructions_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加使用说明内容
        instructions_content = """
        【使用说明】
        
        1. 文件选择：
           - 单个文件：选择单个EPUB文件进行转换
           - 批量模式：选择包含多个EPUB文件的目录
        
        2. 输出设置：
           - 单个文件：指定输出TXT文件路径，所在位置即为输出目录
           - 批量模式：指定输出目录
        
        3. 转换设置：
           - 转换方法：选择使用ebooklib或epub2txt
           - 生成跳转标记：在章节标题后添加跳转标记
           - 拆分多文本：将EPUB中的多个文本拆分为单独文件
           - 多书籍拆分模式：merge（合并）或split（拆分）
        
        4. 高级设置：
           - 按大小分割文本：根据指定大小分割输出文件
           - 分割大小：设置分割文件的最大大小（MB）
           - 长行分割长度：设置长行的分割长度（字符）
           - 以ZIP格式输出：将输出文件压缩为ZIP格式
           - 分割后单独压缩：每个分割文件单独压缩为ZIP文件
           - 压缩级别：设置ZIP文件的压缩级别（0-9，0=无压缩，9=最高压缩），默认值为6
        
        5. 常用选项组合：
           - 基本转换：仅勾选"生成跳转标记"，生成单个TXT文件
           - 大文件处理：勾选"按大小分割文本"，设置分割大小为20MB
           - 压缩输出：勾选"以ZIP格式输出"，生成压缩文件
           - 批量压缩：勾选"按大小分割文本"和"分割后单独压缩"，每个分割文件单独压缩
        
        6. 输出格式：
           - TXT格式：默认输出格式，包含完整的章节内容
           - ZIP格式：压缩后的输出格式
        
        7. 注意事项：
           - 对于大文件，建议使用按大小分割功能
           - 诗歌会自动保持原有的排版格式
           - 压缩级别默认值为6，为平衡压缩效果和速度的最佳设置
        """
        
        # 插入说明内容
        self.instructions_text.config(state=tk.NORMAL)
        self.instructions_text.insert(tk.END, instructions_content)
        self.instructions_text.config(state=tk.DISABLED)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.instructions_frame, command=self.instructions_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.instructions_text.config(yscrollcommand=scrollbar.set)
    
    def _create_status_display(self, parent):
        """
        创建状态显示区域
        """
        # 创建状态显示容器
        self.status_container = ttk.Frame(parent)
        self.status_container.pack(fill=tk.X, pady=10)
        
        # 创建显示/隐藏按钮
        toggle_frame = ttk.Frame(self.status_container)
        toggle_frame.pack(fill=tk.X)
        
        self.status_visible = False
        self.status_button = ttk.Button(
            toggle_frame, 
            text="显示转换状态", 
            command=self._toggle_status
        )
        self.status_button.pack(side=tk.LEFT, padx=5)
        
        # 创建状态框架（默认隐藏）
        self.status_frame = ttk.LabelFrame(self.status_container, text="转换状态", padding="15")
        # 默认不显示，需要点击按钮才显示
        # self.status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(self.status_frame, height=10, font=self.font_style, wrap=tk.WORD, bg="#f8f9fa", fg="#34495e")
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.status_frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # 添加复制按钮
        button_frame = ttk.Frame(self.status_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            button_frame, 
            text="清空", 
            command=lambda: self.status_text.delete(1.0, tk.END),
            width=8
        ).pack(side=tk.RIGHT, padx=5)
    
    def _create_buttons(self, parent):
        """
        创建按钮区域
        """
        # 左侧：开始转换按钮
        start_button_frame = ttk.Frame(parent)
        start_button_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            start_button_frame, 
            text="开始转换", 
            command=self._start_conversion,
            style="Accent.TButton"
        ).pack()
        
        # 右侧：退出按钮
        exit_button_frame = ttk.Frame(parent)
        exit_button_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            exit_button_frame, 
            text="退出", 
            command=self._exit_app
        ).pack()
    
    def _apply_styles(self):
        """
        应用样式
        """
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except:
            pass
        
        # 按钮样式
        style.configure("TButton", font=self.font_style, padding=10, foreground="#000000")
        style.configure("Accent.TButton", font=self.font_title, padding=14, foreground="#000000", background="#ffffff", relief="raised")
        style.map("Accent.TButton", 
                  foreground=[('pressed', '#000000'), ('active', '#000000')],
                  background=[('pressed', '#3498db'), ('active', '#3498db')])
        
        # 进度条样式
        style.configure("Horizontal.TProgressbar", thickness=15, troughcolor="#e0e0e0", background="#3498db")
        
        # 标签样式
        style.configure("TLabel", font=self.font_style)
        
        # 输入框样式
        style.configure("TEntry", font=self.font_style, padding=6)
        
        # 组合框样式
        style.configure("TCombobox", font=self.font_style, padding=6)
        
        # 复选框样式
        style.configure("TCheckbutton", font=self.font_style)
        
        # 框架样式
        style.configure("TLabelframe", font=self.font_title, foreground="#2c3e50")
        style.configure("TLabelframe.Label", font=self.font_title, foreground="#2c3e50")
    
    def _redirect_stdout(self):
        """
        重定向标准输出到状态文本框
        """
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
            
            def write(self, string):
                self.text_widget.insert(tk.END, string)
                self.text_widget.see(tk.END)
            
            def flush(self):
                pass
        
        self.old_stdout = sys.stdout
        sys.stdout = StdoutRedirector(self.status_text)
    
    def _toggle_batch_mode(self):
        """
        切换批量模式
        """
        # 确保所有属性都已创建
        if not hasattr(self, 'batch_dir_frame') or not hasattr(self, 'single_file_frame') or not hasattr(self, 'single_output_frame') or not hasattr(self, 'batch_output_frame'):
            return
        
        # 先隐藏所有相关控件，确保布局一致性
        self.single_file_frame.pack_forget()
        self.single_output_frame.pack_forget()
        self.batch_dir_frame.pack_forget()
        self.batch_output_frame.pack_forget()
        
        if self.batch_mode_var.get():
            # 批量模式：显示批量控件
            self.batch_dir_frame.pack(fill=tk.X, pady=8)
            self.batch_output_frame.pack(fill=tk.X, pady=8)
        else:
            # 单转换模式：显示单个文件控件
            self.single_file_frame.pack(fill=tk.X, pady=8)
            self.single_output_frame.pack(fill=tk.X)
    
    def _browse_file(self):
        """
        浏览文件
        """
        file_path = filedialog.askopenfilename(
            title="选择EPUB文件",
            filetypes=[("EPUB文件", "*.epub"), ("所有文件", "*.*")]
        )
        if file_path:
            self.epub_file_var.set(file_path)
            # 自动设置输出文件的默认名称为EPUB文件的名称（去掉.epub扩展名，加上.txt扩展名）
            epub_filename = os.path.basename(file_path)
            txt_filename = os.path.splitext(epub_filename)[0] + ".txt"
            output_dir = os.path.dirname(file_path)
            output_path = os.path.join(output_dir, txt_filename)
            self.output_file_var.set(output_path)
            # 同步更新输出目录
            self.output_dir_var.set(output_dir)
    
    def _browse_directory(self):
        """
        浏览目录
        """
        dir_path = filedialog.askdirectory(title="选择EPUB文件目录")
        if dir_path:
            self.epub_dir_var.set(dir_path)
            # 同步更新输出目录
            self.output_dir_var.set(dir_path)
    
    def _browse_output_file(self):
        """
        浏览输出文件
        """
        # 获取当前输出文件路径
        current_output_path = self.output_file_var.get()
        # 提取当前文件名
        initialfile = ""
        if current_output_path:
            initialfile = os.path.basename(current_output_path)
        
        file_path = filedialog.asksaveasfilename(
            title="选择输出TXT文件",
            defaultextension=".txt",
            filetypes=[("TXT文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=initialfile  # 添加初始文件名
        )
        if file_path:
            self.output_file_var.set(file_path)
            # 从输出文件路径中提取目录，并设置为输出目录
            output_dir = os.path.dirname(file_path)
            self.output_dir_var.set(output_dir)
    
    def _browse_output_directory(self):
        """
        浏览输出目录
        """
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def _start_conversion(self):
        """
        开始转换
        """
        import time
        try:
            # 显示转换状态区域
            if not self.status_visible:
                self._toggle_status()
            
            # 清空状态文本
            self.status_text.delete(1.0, tk.END)
            
            # 重置进度条
            self.progress_var.set(0)
            self.progress_label.config(text="准备就绪")
            self.root.update_idletasks()
            
            # 检查批量模式
            if self.batch_mode_var.get():
                # 记录开始时间
                self.start_time = time.time()
                self._batch_conversion()
            else:
                # 检查强相关的选项
                error_message = ""
                
                # 检查是否分割后单独压缩与其他选项的相关性
                if self.zip_split_var.get():
                    if not self.split_by_size_var.get():
                        error_message += "请勾选'是否按大小分割文本'选项，因为您选择了'是否分割后单独压缩'\n"
                    if not self.output_zip_var.get():
                        error_message += "请勾选'以ZIP格式输出'选项，因为您选择了'是否分割后单独压缩'\n"
                
                # 检查是否按大小分割文本与分割大小的相关性
                if self.split_by_size_var.get():
                    try:
                        split_size = float(self.max_size_var.get())
                        if split_size <= 0:
                            error_message += "请设置有效的分割大小（大于0）\n"
                    except:
                        error_message += "请设置有效的分割大小\n"
                
                # 如果有错误信息，提示用户
                if error_message:
                    self._show_error(error_message)
                    return
                
                # 记录开始时间
                self.start_time = time.time()
                
                # 执行转换
                self._single_conversion()
        except Exception as e:
            self._show_error(f"转换过程中发生错误：{str(e)}")
    
    def _single_conversion(self):
        """
        单个文件转换
        """
        epub_path = self.epub_file_var.get()
        output_path = self.output_file_var.get()
        
        if not epub_path:
            self._show_error("请选择EPUB文件")
            return
        
        if not output_path:
            self._show_error("请选择输出文件")
            return
        
        if not os.path.exists(epub_path):
            self._show_error("EPUB文件不存在")
            return
        
        # 获取参数
        generate_jump_marks = self.jump_mark_var.get()
        split_files = self.split_var.get()
        multi_book_mode = self.multi_book_mode_var.get()
        output_zip = self.output_zip_var.get()
        zip_split = self.zip_split_var.get()
        
        # 直接使用split_by_size_var的值
        split_by_size = self.split_by_size_var.get()
        
        # 获取分割大小
        try:
            max_size = float(self.max_size_var.get()) * 1024 * 1024
        except:
            max_size = 20 * 1024 * 1024  # 默认值：20MB
        
        # 获取长行分割长度
        try:
            line_split_length = int(self.line_split_length_var.get())
        except:
            line_split_length = defaults['line_split_length']
        

        
        # 获取压缩级别
        try:
            compress_level = int(self.compress_level_var.get())
        except:
            compress_level = 6
        
        # 获取文本合并阈值
        try:
            merge_threshold = int(self.merge_threshold_var.get())
        except:
            merge_threshold = 30  # 默认值：30
        
        # 获取诗歌排版选项
        poetry_format = self.poetry_format_var.get()
        
        # 获取章节标题优化选项
        chapter_title_optimize = self.chapter_title_var.get()
        
        # 获取纯净读取选项
        pure_read = self.pure_read_var.get()
        
        # 获取章节排序选项
        sort_chapters = self.sort_chapters_var.get()
        
        # 开始转换
        self.progress_var.set(10)
        self.progress_label.config(text="分析EPUB文件...")
        self.root.update_idletasks()
        
        # 定义进度回调
        def progress_callback(progress, status):
            self.progress_var.set(progress)
            self.progress_label.config(text=status)
            self.root.update_idletasks()
        
        # 执行转换
        method = self.method_var.get()
        success = False
        
        if method == "epub2txt":
            success = convert_with_epub2txt(epub_path, output_path)
        else:
            success = convert_with_ebooklib(
                epub_path, 
                output_path, 
                generate_jump_marks,
                False,  # split_into_multiple_files
                multi_book_mode,
                progress_callback,
                split_by_size,
                max_size,
                output_zip,
                zip_split,
                line_split_length,
                compress_level,
                merge_threshold,
                poetry_format,
                chapter_title_optimize,
                pure_read,
                sort_chapters
            )
        
        # 添加转换状态记录
        if success:
            status_info = "\n【转换状态详情】\n"
            status_info += f"- 输入文件: {epub_path}\n"
            status_info += f"- 输出文件: {output_path}\n"
            
            # 记录纯净读取状态
            if pure_read:
                status_info += "- 纯净读取: 是 (保留原EPUB排版)\n"
            else:
                status_info += "- 纯净读取: 否\n"
            
            # 记录输出TXT拆分状态
            if split_by_size:
                status_info += f"- 输出TXT拆分: 是 (分割大小: {self.max_size_var.get()}MB)\n"
            else:
                status_info += "- 输出TXT拆分: 否\n"
            
            # 记录ZIP输出状态
            if output_zip:
                status_info += f"- ZIP输出: 是 (压缩级别: {compress_level})\n"
            else:
                status_info += "- ZIP输出: 否\n"
            
            # 记录TXT单独压缩输出状态
            if zip_split:
                status_info += "- TXT单独压缩输出: 是\n"
            else:
                status_info += "- TXT单独压缩输出: 否\n"
            
            self.status_text.insert(tk.END, status_info)
        
        if success:
            self._show_success("转换完成！")
        else:
            self._show_error("转换失败，请查看状态信息")
    
    def _batch_conversion(self):
        """
        批量转换
        """
        epub_dir = self.epub_dir_var.get()
        output_dir = self.output_dir_var.get()
        
        # 如果未设置输出目录，使用当前工作目录
        if not output_dir:
            output_dir = os.getcwd()
        
        if not epub_dir:
            self._show_error("请选择EPUB文件目录")
            return
        
        if not os.path.exists(epub_dir):
            self._show_error("EPUB文件目录不存在")
            return
        
        # 获取EPUB文件列表
        epub_files = [f for f in os.listdir(epub_dir) if f.lower().endswith('.epub')]
        if not epub_files:
            self._show_error(f"目录 {epub_dir} 中没有找到EPUB文件")
            return
        
        # 开始批量转换
        generate_jump_marks = self.jump_mark_var.get()
        method = self.method_var.get()
        split_by_size = self.split_by_size_var.get()
        
        # 获取分割大小
        try:
            max_size = float(self.max_size_var.get()) * 1024 * 1024
        except:
            max_size = 20 * 1024 * 1024  # 默认值：20MB
        
        # 获取长行分割长度
        try:
            line_split_length = int(self.line_split_length_var.get())
        except:
            line_split_length = None
        
        # 获取压缩相关选项
        output_zip = self.output_zip_var.get()
        zip_split = self.zip_split_var.get()
        
        # 获取压缩级别
        try:
            compress_level = int(self.compress_level_var.get())
        except:
            compress_level = 6
        
        # 获取文本合并阈值
        try:
            merge_threshold = int(self.merge_threshold_var.get())
        except:
            merge_threshold = 30  # 默认值：30
        
        # 获取排版选项
        poetry_format = self.poetry_format_var.get()
        chapter_title_optimize = self.chapter_title_var.get()
        
        # 获取纯净读取选项
        pure_read = self.pure_read_var.get()
        
        # 获取章节排序选项
        sort_chapters = self.sort_chapters_var.get()
        
        # 定义进度回调
        def progress_callback(progress, status):
            self.progress_var.set(progress)
            self.progress_label.config(text=status)
            self.root.update_idletasks()
        
        # 执行批量转换
        success = batch_convert(
            epub_dir, 
            output_dir, 
            method, 
            generate_jump_marks,
            split_by_size,
            max_size,
            output_zip,
            zip_split,
            line_split_length,
            compress_level,
            merge_threshold,
            poetry_format,
            chapter_title_optimize,
            pure_read,
            sort_chapters,
            progress_callback
        )
        
        if success:
            self._show_success("批量转换完成！")
        else:
            self._show_error("批量转换失败，请查看状态信息")
    
    def _show_error(self, message):
        """
        显示错误信息
        """
        import time
        # 计算耗时
        elapsed_time = time.time() - self.start_time
        time_str = f"转换耗时：{elapsed_time:.2f} 秒"
        
        # 在状态文本中显示耗时
        self.status_text.insert(tk.END, f"\n{time_str}\n")
        
        messagebox.showerror("错误", f"{message}\n{time_str}")
        self.progress_var.set(0)
        self.progress_label.config(text="错误")
        self.root.update_idletasks()
        
        # 显示转换状态区域，以便用户查看详细的错误信息
        if not self.status_visible:
            self._toggle_status()
    
    def _show_success(self, message):
        """
        显示成功信息
        """
        import time
        # 计算耗时
        elapsed_time = time.time() - self.start_time
        time_str = f"转换耗时：{elapsed_time:.2f} 秒"
        
        # 在状态文本中显示耗时
        self.status_text.insert(tk.END, f"\n{time_str}\n")
        
        messagebox.showinfo("成功", f"{message}\n{time_str}")
        self.progress_var.set(100)
        self.progress_label.config(text="转换完成！")
        self.root.update_idletasks()
        
        # 显示转换状态区域
        if not self.status_visible:
            self._toggle_status()
        
        # 重置进度条
        self.root.after(1000, lambda: self.progress_var.set(0))
        self.root.after(1000, lambda: self.progress_label.config(text="准备就绪"))
    
    def _toggle_instructions(self):
        """
        切换使用说明的显示状态
        """
        if self.instructions_visible:
            # 隐藏使用说明
            self.instructions_frame.pack_forget()
            self.instructions_button.config(text="显示使用说明")
            self.instructions_visible = False
        else:
            # 显示使用说明
            self.instructions_frame.pack(fill=tk.X, pady=5)
            self.instructions_button.config(text="隐藏使用说明")
            self.instructions_visible = True
    
    def _toggle_status(self):
        """
        切换转换状态的显示状态
        """
        if self.status_visible:
            # 隐藏转换状态
            self.status_frame.pack_forget()
            self.status_button.config(text="显示转换状态")
            self.status_visible = False
        else:
            # 显示转换状态
            self.status_frame.pack(fill=tk.BOTH, expand=True)
            self.status_button.config(text="隐藏转换状态")
            self.status_visible = True
    
    def _on_zip_split_change(self, *args):
        """
        当是否分割后单独压缩选项变化时的回调函数
        """
        if self.zip_split_var.get():
            # 自动勾选其他必要的选项
            self.split_by_size_var.set(True)
            self.output_zip_var.set(True)
    
    def _on_pure_read_change(self, *args):
        """
        当纯净读取选项变化时的回调函数
        """
        if self.pure_read_var.get():
            # 当勾选纯净模式时，其他选项都变为否
            self.jump_mark_var.set(False)
            self.split_var.set(False)
            self.poetry_format_var.set(False)
            self.chapter_title_var.set(False)
    
    def _exit_app(self):
        """
        退出应用
        """
        # 恢复标准输出
        sys.stdout = self.old_stdout
        self.root.destroy()

def create_gui():
    """
    创建GUI界面
    """
    root = tk.Tk()
    
    # 窗口关闭事件
    def on_closing():
        sys.stdout = sys.__stdout__
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    app = EPUBConverterApp(root)
    root.mainloop()
