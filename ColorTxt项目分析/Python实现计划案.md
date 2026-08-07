# Python 实现计划案：test1.xlsm VBA → Python 独立应用

> 基于 test1.xlsm VBA 项目（约 80 个模块）功能分析
> 制定日期：2026-08-07

---

## 一、前置知识

### 1.1 结论：Python 能否实现？

**结论：全部功能均可实现，且性能全面优于 VBA。**

| 评估维度 | VBA 现状 | Python 方案 | 提升幅度 |
|---------|---------|------------|---------|
| 字符级上色 | Characters.Font.Color，10万字3-10分钟 | QSyntaxHighlighter，10万字 < 0.5秒 | **100倍+** |
| TXT 文件读取 | Line Input + &拼接，10MB文件15-30秒 | open() + chardet，10MB文件0.3-1秒 | **15-30倍** |
| EPUB 转换 | 依赖 WinRAR 外部程序 | ebooklib 纯 Python 解析 | 去除外部依赖 |
| 图表 | Excel xlLineStacked 静态图 | matplotlib 交互式 + pyecharts 可选 | 交互性大幅提升 |
| 编码检测 | 手动 BOM + 启发式 | chardet 库（成熟准确） | 准确率更高 |
| 中文分词 | 逐字 Mid 进字典 | jieba 分词库 | 专业分词，支持词组 |
| 跨平台 | 仅 Windows | Windows/macOS/Linux | 三端通吃 |
| 扩展能力 | 无现代生态 | PyPI 生态（AI/网络/数据科学） | 无限扩展 |

### 1.2 VBA 功能 → Python 可行性逐项评估

| VBA 功能 | VBA 模块 | Python 实现方案 | 可行性 | 难度 |
|---------|---------|---------------|:---:|:---:|
| TXT 导入（编码检测） | READ_TXTTOEXCEL.bas | chardet + open() | ✅ 完全可行 | 低 |
| Word 导入 | READ_TXTTOEXCEL.bas | python-docx | ✅ 完全可行 | 低 |
| Excel 导入 | READ_TXTTOEXCEL.bas | openpyxl / pandas | ✅ 完全可行 | 低 |
| 文本清洗（3种模式） | READ_TXTTOEXCEL.bas | re 模块正则替换 | ✅ 完全可行 | 低 |
| 字符级上色（4色循环） | READ_上色.bas | QSyntaxHighlighter | ✅ 完全可行 | 中 |
| 整格底色 | READ_上色.bas | QTextCharFormat.setBackground | ✅ 完全可行 | 低 |
| 章节正则识别 | READ_正则查询替换目录.bas | re 模块（语法一致） | ✅ 完全可行 | 低 |
| 目录补全（向下填充） | READ_正则查询替换目录.bas | 遍历 + lastValid 变量 | ✅ 完全可行 | 低 |
| 目录跳转（精确匹配） | D_CatalogJump.bas | QTextCursor 定位 | ✅ 完全可行 | 中 |
| 目录跳转（模糊匹配） | D_CatalogJump.bas | in 操作符 / re.search | ✅ 完全可行 | 低 |
| 双筛选查询 | Sheet8 事件 | 嵌套列表推导式 | ✅ 完全可行 | 低 |
| 快捷键查找 | 查找一件套合集.bas | QShortcut 绑定 | ✅ 完全可行 | 低 |
| 字典查询（Like模糊） | READ_字典查询.bas | dict + in 操作 | ✅ 完全可行 | 低 |
| 频率矩阵 | READ_字典查询.bas | pandas DataFrame | ✅ 完全可行 | 低 |
| 字频统计 | Read_最新字频.bas | collections.Counter | ✅ 完全可行 | 低 |
| 重复字定位 | READ_最新字频2.bas | dict + 列表存储 | ✅ 完全可行 | 低 |
| 数据聚合 | READ_聚合生成折线堆叠图.bas | numpy reshape + sum | ✅ 完全可行 | 低 |
| 折线堆叠图 | READ_聚合生成折线堆叠图.bas | matplotlib stackplot | ✅ 完全可行 | 中 |
| EPUB 转 TXT | FC_EPUB_TO_TXT.bas | ebooklib + beautifulsoup4 | ✅ 完全可行 | 中 |
| 拼音生成 | FC_拼音.bas（142KB） | pypinyin 库 | ✅ 完全可行 | 低 |
| 批量重命名 | D_批量重命名.bas | os / shutil | ✅ 完全可行 | 低 |
| 工作表分类管理 | SheetManager.bas | QTabWidget / QStackedWidget | ✅ 完全可行 | 中 |
| Ribbon 菜单 (C1-C28) | DLL_自定义ribbon.bas | QToolBar + QAction | ✅ 完全可行 | 中 |
| ProgressBar | ProgressBar.cls | QProgressBar | ✅ 完全可行 | 低 |
| StringBuffer | StringBuffer.cls | Python 原生 str（已优化） | ✅ 完全可行 | 低 |
| 鼠标滚轮 | MouseOverControl.cls | PyQt 原生支持 | ✅ 完全可行 | 低 |
| 到期自毁 | ThisWorkbook | Python 时间检测 | ✅ 可选实现 | 低 |
| 简繁互转（新功能） | 无 | opencc-python-reimplemented | ✅ 新增可行 | 低 |
| 书签进度（新功能） | 无 | sqlite3 存储 | ✅ 新增可行 | 低 |
| 语音朗读（新功能） | 无 | pyttsx3 / edge-tts | ✅ 新增可行 | 中 |

### 1.3 技术栈选型

| 层面 | 选型 | 选型理由 | 对应 VBA 概念 |
|------|------|---------|-------------|
| GUI 框架 | **PyQt6** | 最成熟的 Python GUI，支持富文本/图表/快捷键/拖放 | Excel 窗口 + UserForm |
| 文本显示 | **QTextEdit** | 支持富文本 HTML 渲染，字符级着色 | Excel 单元格 |
| 语法高亮 | **QSyntaxHighlighter** | C++ 底层着色，性能极高 | Characters.Font.Color |
| 图表 | **matplotlib + FigureCanvasQTAgg** | 原生嵌入 PyQt，支持堆叠折线图 | xlLineStacked |
| 编码检测 | **chardet** | 成熟准确，纯 Python | DetectEncoding |
| 中文分词 | **jieba** | 最流行的中文分词库 | VBA 逐字 Mid |
| Word 读取 | **python-docx** | 纯 Python，无需 Word 进程 | Word.Application |
| Excel 读取 | **openpyxl** | 纯 Python，无需 Excel 进程 | ADODB 查询 |
| EPUB 解析 | **ebooklib + beautifulsoup4** | 纯 Python，无需 WinRAR | WinRAR 解压 |
| 数据处理 | **pandas + numpy** | 专业数据分析，替代二维数组 | VBA 二维数组 |
| 数据存储 | **sqlite3** | Python 标准库，零配置 | 隐藏工作表 |
| 简繁转换 | **opencc-python-reimplemented** | 专业简繁转换库 | 无（新功能） |
| 拼音 | **pypinyin** | 轻量级拼音库 | FC_拼音.bas（142KB） |
| 语音朗读 | **pyttsx3** | 离线 TTS，跨平台 | 无（新功能） |
| 打包 | **PyInstaller** | 打包为 exe/dmg/AppImage | — |

### 1.4 VBA → Python 关键概念映射

理解概念对应关系是迁移的基础：

| VBA 概念 | Python 等价 | 迁移说明 |
|---------|------------|---------|
| `Range.Characters(start,len).Font.Color` | `QTextCharFormat.setForeground(QColor)` | 通过 QSyntaxHighlighter 批量着色，性能提升 100 倍+ |
| `cell.Interior.Color` | `QTextCharFormat.setBackground(QColor)` | 整格底色 |
| `VBScript.RegExp` | `re` 模块 | 语法几乎一致，Python re 更强大 |
| `Scripting.Dictionary` | `dict` / `collections.Counter` / `defaultdict` | Python 原生，功能更强 |
| `Range.Find` | `str.find()` / `re.search()` | 内存操作，无 COM 开销 |
| `Open For Binary` + BOM 检测 | `chardet.detect()` | 成熟库，准确率更高 |
| `ADODB.Stream` (UTF-8 读取) | `open(path, 'r', encoding='utf-8')` | Python 原生 |
| `Line Input` + `&` 拼接 | `f.read()` 一次性读取 | Python str 已优化，无需 StringBuffer |
| `Range.Value = dataArray` 批量写入 | `QTextEdit.setPlainText('\n'.join(lines))` | — |
| `xlLineStacked` 图表 | `matplotlib.pyplot.stackplot()` | 交互式、可保存 |
| `Application.ScreenUpdating` | 无需（PyQt 自动优化重绘） | — |
| Ribbon 菜单 (C1-C28) | `QToolBar` + `QAction` | — |
| 工作表 (Sheet) | `QTabWidget` 页面 | — |
| `ThisWorkbook` 事件 | PyQt 事件系统 / 信号槽 | — |
| `Like "*词条*"` 模糊匹配 | `关键词 in 文本` / `re.search()` | Python 更直观 |
| `CreateObject("Word.Application")` | `python-docx` 库 | 无需启动 Word 进程 |
| `CreateObject("ADODB.Connection")` | `openpyxl` / `pandas.read_excel` | 无需 Excel 进程 |
| `Shell "winrar..."` 解压 | `ebooklib` 直接解析 | 无需 WinRAR |
| `On Error Resume Next` | `try/except` | Python 异常处理更规范 |

### 1.5 技能要求

| 技能 | 当前水平要求 | 学习资源 |
|------|-----------|---------|
| Python 基础 | 掌握语法/数据结构/文件操作 | Python 官方教程 |
| PyQt6 | 掌握窗口/布局/事件/信号槽 | PyQt6 官方文档 |
| 正则表达式 | 已有 VBA 基础，迁移成本低 | regex101.com |
| re 模块 | 掌握 match/search/sub/findall | Python re 文档 |
| pandas | 掌握 DataFrame 基本操作 | 10 Minutes to pandas |
| matplotlib | 掌握基本图表绘制 | matplotlib 官方教程 |
| SQLite | 掌握基本 SQL 语句 | SQLite 教程 |

### 1.6 项目结构预规划

```
novel-reader/
├── main.py                          # 入口：创建 QApplication + 主窗口
├── src/
│   ├── core/                        # 核心业务逻辑（无 GUI 依赖）
│   │   ├── file_import/             # 文件导入（对应 READ_TXTTOEXCEL）
│   │   │   ├── encoding_detect.py   #   编码检测（对应 DetectEncoding）
│   │   │   ├── txt_reader.py        #   TXT 读取
│   │   │   ├── word_reader.py       #   Word 读取
│   │   │   └── excel_reader.py      #   Excel 读取
│   │   ├── chapter_detect/          # 章节识别（对应 READ_正则查询替换目录）
│   │   │   ├── regex_match.py       #   正则匹配
│   │   │   └── catalog_fill.py      #   目录补全
│   │   ├── search/                  # 查询（对应 READ_字典查询）
│   │   │   ├── fuzzy_search.py      #   模糊查询
│   │   │   └── double_filter.py     #   双筛选
│   │   ├── analysis/                # 数据分析（对应 字频/聚合/图表）
│   │   │   ├── frequency_stats.py   #   字频统计
│   │   │   ├── duplicate_finder.py  #   重复字定位
│   │   │   ├── aggregation.py       #   数据聚合
│   │   │   └── chart_data.py        #   图表数据准备
│   │   ├── epub/                    # EPUB 转换（对应 FC_EPUB_TO_TXT）
│   │   │   └── epub_converter.py    #   EPUB → TXT
│   │   ├── text_processing/         # 文本处理
│   │   │   ├── cleaner.py           #   文本清洗（3种模式）
│   │   │   └── convertor.py         #   简繁转换
│   │   └── database/                # 数据存储
│   │       └── db_manager.py        #   SQLite 管理
│   ├── gui/                         # GUI 层（PyQt6）
│   │   ├── main_window.py           # 主窗口（对应 ThisWorkbook）
│   │   ├── toolbar.py               # 工具栏（对应 Ribbon C1-C28）
│   │   ├── views/                   # 页面视图（对应工作表分类）
│   │   │   ├── reader_view.py       #   阅读视图（对应数据源）
│   │   │   ├── catalog_view.py      #   目录视图（对应目录表）
│   │   │   ├── search_view.py       #   查询视图（对应查询表）
│   │   │   ├── analysis_view.py     #   分析视图（对应排序表）
│   │   │   └── chart_view.py        #   图表视图
│   │   ├── widgets/                 # 自定义控件
│   │   │   ├── text_editor.py       #   文本编辑器 + 上色
│   │   │   ├── highlighter.py       #   语法高亮（QSyntaxHighlighter）
│   │   │   ├── progress_bar.py      #   进度条（对应 ProgressBar.cls）
│   │   │   └── chapter_list.py      #   章节列表（对应目录窗体）
│   │   └── dialogs/                 # 对话框（对应 UserForm）
│   │       ├── import_dialog.py     #   导入对话框
│   │       ├── search_dialog.py     #   查询对话框
│   │       └── aggregate_dialog.py  #   聚合配置对话框
│   ├── models/                      # 数据模型
│   │   ├── text_content.py          #   文本内容
│   │   ├── chapter.py               #   章节
│   │   ├── color_rule.py            #   上色规则
│   │   └── search_result.py         #   查询结果
│   └── utils/                       # 工具模块（对应 Utils_*.bas）
│       ├── file_utils.py            #   文件工具
│       ├── text_utils.py            #   文本工具
│       └── pinyin_utils.py          #   拼音工具
├── assets/                          # 资源文件
│   ├── icons/                       #   图标
│   └── styles/                      #   QSS 样式表
├── tests/                           # 测试
├── requirements.txt
└── pyinstaller.spec                 # 打包配置
```

---

## 二、短期计划：核心功能复刻（1-2 周）

### 2.1 目标

用 Python + PyQt6 复刻 VBA 项目的**核心阅读功能**：文件导入 → 章节识别 → 上色 → 目录跳转。验证技术可行性，建立项目骨架。

### 2.2 实现逻辑

#### 任务 1：项目搭建与环境配置（第 1 天）

```bash
# 创建项目
mkdir novel-reader && cd novel-reader
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装核心依赖
pip install PyQt6 chardet python-docx openpyxl
pip install jieba pandas numpy matplotlib
pip install ebooklib beautifulsoup4 opencc-python-reimplemented
pip install pypinyin pyttsx3

# 生成依赖文件
pip freeze > requirements.txt
```

**实现逻辑**：

```
main.py 入口设计：
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec())

MainWindow 布局（对应 Excel 工作簿）：
  ┌─ QToolBar（对应 Ribbon C1-C28）─────────────────┐
  │ [导入] [目录] [上色] [查询] [字频] [图表] [EPUB] │
  ├─ QSplitter（水平分割）─────────────────────────┤
  │ ┌─ QTabWidget（对应工作表分类）──────────────┐ │
  │ │ [阅读] [目录] [查询] [分析] [图表]         │ │
  │ │                                            │ │
  │ │  当前页面内容区域                           │ │
  │ │                                            │ │
  │ └────────────────────────────────────────────┘ │
  └─ QStatusBar（状态栏：文件名/进度/字数）─────────┘
```

#### 任务 2：文件导入（第 2-3 天）

对应 VBA 模块：READ_TXTTOEXCEL.bas（51KB）

```python
# src/core/file_import/encoding_detect.py
# 对应 VBA: DetectEncoding
import chardet

def detect_encoding(file_path: str) -> str:
    """检测文件编码，替代 VBA 的 BOM 头 + 启发式检测"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(1024 * 100)  # 读取前100KB
    result = chardet.detect(raw_data)
    return result['encoding'] or 'utf-8'


# src/core/file_import/txt_reader.py
# 对应 VBA: ImportTextDataToSheet
def read_txt(file_path: str) -> list[str]:
    """读取 TXT 文件，返回文本行列表（对应数据源 A 列）"""
    encoding = detect_encoding(file_path)
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        text = f.read()  # 一次性读取，替代 VBA 逐行 Line Input
    lines = [line for line in text.split('\n') if line.strip()]
    return lines


# src/core/file_import/word_reader.py
# 对应 VBA: CreateObject("Word.Application")
from docx import Document

def read_docx(file_path: str) -> list[str]:
    """读取 Word 文件，无需启动 Word 进程"""
    doc = Document(file_path)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return lines


# src/core/file_import/excel_reader.py
# 对应 VBA: ADODB SELECT * FROM [sheet$]
import openpyxl

def read_excel(file_path: str, sheet_name: str = None) -> list[str]:
    """读取 Excel 文件，无需 Excel 进程"""
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    lines = [str(cell.value) for row in ws.iter_rows()
             for cell in row if cell.value]
    wb.close()
    return lines
```

**关键差异**：
- VBA 用 `Open For Binary` + 手动 BOM 检测 → Python 用 `chardet` 库（更准确）
- VBA 逐行 `Line Input` + `&` 拼接 → Python `f.read()` 一次性读取（快 15-30 倍）
- VBA 启动 Word 进程（2-5 秒开销）→ Python `python-docx` 纯解析（< 0.5 秒）
- VBA ADODB 查询 Excel → Python `openpyxl` 纯解析（无需 Excel 进程）

#### 任务 3：文本清洗（第 3 天）

对应 VBA 模块：READ_TXTTOEXCEL.bas 中的 ProcessTextWithSpaces 等

```python
# src/core/text_processing/cleaner.py
# 对应 VBA: ProcessTextWithSpaces / ProcessTextWithoutPunctuation
import re

# 对应 VBA 正则: [^\u4e00-\u9fa5a-zA-Z0-9 \u3000]
PUNCTUATION_TO_PIPE = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9 \u3000]')
# 对应 VBA 正则: [^\u4e00-\u9fa5a-zA-Z0-9]
NON_ALPHANUMERIC = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')

def clean_text(text: str, mode: int = 3) -> list[str]:
    """
    文本清洗，对应 VBA 3 种模式
    mode=1: 保留空格，标点→|（按句分割）
    mode=2: 不保留标点（纯文字）
    mode=3: 原样保留（按行分割）
    """
    if mode == 1:
        cleaned = PUNCTUATION_TO_PIPE.sub('|', text)
        return [seg for seg in cleaned.split('|') if seg.strip()]
    elif mode == 2:
        cleaned = NON_ALPHANUMERIC.sub('', text)
        return [cleaned[i:i+1] for i in range(len(cleaned))]
    else:
        return [line for line in text.split('\n') if line.strip()]
```

#### 任务 4：章节识别与目录补全（第 4-5 天）

对应 VBA 模块：READ_正则查询替换目录.bas（16KB）

```python
# src/core/chapter_detect/regex_match.py
# 对应 VBA: 正则查询优化 (Ribbon C5)
import re

def detect_chapters(lines: list[str], patterns: list[str]) -> dict[int, str]:
    """
    正则匹配章节，返回 {行号: 章节名}
    对应 VBA: 多正则合并为"或"模式 + VBScript.RegExp.Global=True
    """
    combined = '|'.join(patterns)
    regex = re.compile(combined)
    matches = {}
    for index, line in enumerate(lines):
        match = regex.match(line)  # 对应 VBA .Execute
        if match:
            matches[index] = match.group()
    return matches


# src/core/chapter_detect/catalog_fill.py
# 对应 VBA: 正则后辅助目录优化 (Ribbon C6)
def fill_catalog(lines: list[str], chapter_matches: dict[int, str]) -> list[str]:
    """
    目录向下填充，对应 VBA lastValidDir 逻辑
    非空→记录，为空→用上一次的有效值填充
    """
    catalog = [''] * len(lines)
    last_valid = ''
    for i in range(len(lines)):
        if i in chapter_matches:
            last_valid = chapter_matches[i]
        catalog[i] = last_valid
    return catalog
```

**关键差异**：
- VBA `VBScript.RegExp` → Python `re` 模块（语法几乎一致，Python 更强大）
- VBA `Scripting.Dictionary` → Python `dict`（原生支持，更高效）
- 向下填充逻辑完全一致：遍历 + `last_valid` 变量

#### 任务 5：QSyntaxHighlighter 上色（第 6-7 天）

对应 VBA 模块：READ_上色.bas（10.5KB）— **这是迁移的核心突破点**

```python
# src/gui/widgets/highlighter.py
# 对应 VBA: Color_SS_TO_SS_22（但实现方式完全不同）
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import QRegularExpression

# 对应 VBA 4 色循环: RGB(255,0,0) / RGB(0,255,0) / RGB(0,0,255) / RGB(0,255,255)
COLORS = [
    QColor(255, 0, 0),      # 红
    QColor(0, 255, 0),      # 绿
    QColor(0, 0, 255),      # 蓝
    QColor(0, 255, 255),    # 青
]

class NovelHighlighter(QSyntaxHighlighter):
    """
    小说上色器，替代 VBA Characters.Font.Color
    核心差异：QSyntaxHighlighter 由 C++ 底层批量着色，
    无需逐个 COM 调用，性能提升 100 倍+
    """

    def __init__(self, document):
        super().__init__(document)
        self.rules = []  # [(关键词, 颜色索引), ...]

    def set_keywords(self, keywords: list[str]):
        """设置上色关键词，对应 VBA searchTexts 数组"""
        self.rules = []
        for i, word in enumerate(keywords):
            color = COLORS[i % 4]  # 对应 VBA Select Case mm 循环 4 色
            fmt = QTextCharFormat()
            fmt.setForeground(color)  # 对应 Font.Color
            # 对应 VBA InStr 循环定位，但由 C++ 一次扫描完成
            pattern = QRegularExpression(re.escape(word))
            self.rules.append((pattern, fmt))

    def highlightBlock(self, text: str):
        """重写着色方法，对应 VBA While pos > 0 循环"""
        for pattern, fmt in self.rules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )
```

**性能对比**：

| 方式 | 10 万字上色耗时 | 原理 |
|------|:---:|------|
| VBA: Characters.Font.Color | 3-10 分钟 | 每个子串 1 次 COM 调用 |
| Python: QSyntaxHighlighter | **< 0.5 秒** | C++ 底层一次扫描全部着色 |

**关键差异**：
- VBA：`Characters(start,len).Font.Color = RGB(...)` 逐个 COM 调用 → 极慢
- Python：`QSyntaxHighlighter` 注册规则后，C++ 底层自动批量着色 → 极快
- VBA 4 色循环 `Select Case mm` → Python `COLORS[i % 4]` 列表取色
- VBA `InStr` 循环定位 → Python `QRegularExpression.globalMatch` 一次匹配

#### 任务 6：目录跳转（第 8-9 天）

对应 VBA 模块：D_CatalogJump.bas + Sheet6/Sheet8 事件

```python
# src/gui/widgets/text_editor.py
# 对应 VBA: D_CatalogJump.InitializeCatalogJump
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor

class NovelTextEditor(QTextEdit):
    """文本编辑器，对应 Excel 数据源工作表"""

    def jump_to_line(self, line_index: int):
        """
        跳转到指定行，对应 VBA Cells(行号, 1).Select
        """
        block = self.document().findBlockByNumber(line_index)
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()  # 对应 Excel 滚动到可见

    def search_in_text(self, keyword: str) -> list[dict]:
        """
        模糊查询，对应 VBA Like "*词条*"
        """
        results = []
        document = self.document()
        cursor = QTextCursor(document)

        while True:
            cursor = document.find(keyword, cursor)  # 对应 Range.Find
            if cursor.isNull():
                break
            line_num = cursor.blockNumber()
            results.append({
                'line': line_num,
                'text': cursor.block().text(),
                'position': cursor.position(),
            })
        return results
```

**关键差异**：
- VBA `Cells.Select` → Python `QTextCursor` + `ensureCursorVisible()`
- VBA `Range.Find` → Python `document.find()`（内存操作，无 COM 开销）
- VBA 全局变量 `htcz` 控制跳转开关 → Python 信号槽机制
- VBA UserForm3/4 多匹配选择 → Python QDialog 弹窗

#### 任务 7：工具栏与页面切换（第 10 天）

对应 VBA 模块：DLL_自定义ribbon.bas + SheetManager.bas

```python
# src/gui/toolbar.py
# 对应 VBA: DLL_自定义ribbon (Ribbon C1-C28)
from PyQt6.QtWidgets import QToolBar, QAction
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal

class MainToolBar(QToolBar):
    """主工具栏，对应 VBA Ribbon 菜单"""

    # 信号定义（对应 VBA Ribbon 回调）
    import_triggered = pyqtSignal()
    detect_chapter_triggered = pyqtSignal()
    fill_catalog_triggered = pyqtSignal()
    color_triggered = pyqtSignal()
    search_triggered = pyqtSignal()
    frequency_triggered = pyqtSignal()
    chart_triggered = pyqtSignal()
    epub_convert_triggered = pyqtSignal()

    def __init__(self):
        super().__init__("主工具栏")

        # 对应 Ribbon C1: 综合数据导入
        self.addAction(self._create_action("导入", "📁", self.import_triggered))
        self.addSeparator()

        # 对应 Ribbon C5: 正则查询优化
        self.addAction(self._create_action("识别目录", "📑", self.detect_chapter_triggered))
        # 对应 Ribbon C6: 正则后辅助目录优化
        self.addAction(self._create_action("补全目录", "📝", self.fill_catalog_triggered))
        self.addSeparator()

        # 对应 READ_上色
        self.addAction(self._create_action("上色", "🎨", self.color_triggered))
        # 对应 READ_字典查询
        self.addAction(self._create_action("查询", "🔍", self.search_triggered))
        self.addSeparator()

        # 对应 to___字频音333
        self.addAction(self._create_action("字频", "📊", self.frequency_triggered))
        # 对应 ProcessAndAggregateData
        self.addAction(self._create_action("图表", "📈", self.chart_triggered))
        # 对应 FC_EPUB_TO_TXT
        self.addAction(self._create_action("EPUB", "📚", self.epub_convert_triggered))

    def _create_action(self, text, icon, signal):
        action = QAction(text, self)
        action.triggered.connect(signal.emit)
        return action


# src/gui/main_window.py
# 对应 VBA: ThisWorkbook + SheetManager
class MainWindow(QMainWindow):
    """主窗口，对应 Excel 工作簿"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("小说阅读分析工具")

        # 工具栏（对应 Ribbon）
        self.toolbar = MainToolBar()
        self.addToolBar(self.toolbar)

        # 标签页（对应 SheetManager 6 大分类）
        self.tabs = QTabWidget()
        self.reader_view = ReaderView()    # 对应"数据源"
        self.catalog_view = CatalogView()  # 对应"目录"
        self.search_view = SearchView()    # 对应"查询"
        self.analysis_view = AnalysisView()  # 对应"排序"
        self.chart_view = ChartView()      # 对应图表

        self.tabs.addTab(self.reader_view, "阅读")
        self.tabs.addTab(self.catalog_view, "目录")
        self.tabs.addTab(self.search_view, "查询")
        self.tabs.addTab(self.analysis_view, "分析")
        self.tabs.addTab(self.chart_view, "图表")

        self.setCentralWidget(self.tabs)

        # 状态栏（对应 Excel 底部状态栏）
        self.statusBar().showMessage("就绪")

        # 连接信号（对应 VBA Ribbon 回调分发）
        self._connect_signals()
```

### 2.3 交付物

| 交付物 | 验收标准 |
|--------|---------|
| 项目骨架 | PyQt6 窗口 + 工具栏 + 5 个标签页 |
| TXT 导入 | 支持 UTF-8/GBK 自动检测，10MB 文件 < 1 秒 |
| 章节识别 | 正则匹配 + 目录补全，与 VBA 结果一致 |
| 字符级上色 | QSyntaxHighlighter 4 色循环，10 万字 < 0.5 秒 |
| 目录跳转 | 点击目录跳转 + 模糊查询 |
| Word/Excel 导入 | 无需启动 Word/Excel 进程 |

---

## 三、中期计划：数据分析整合（第 3-4 周）

### 3.1 目标

复刻 VBA 项目的**数据分析功能**：字典查询、字频统计、重复字定位、数据聚合、折线堆叠图。

### 3.2 实现逻辑

#### 任务 1：字典查询与频率矩阵（第 11-12 天）

对应 VBA 模块：READ_字典查询.bas（8.2KB）

```python
# src/core/search/fuzzy_search.py
# 对应 VBA: ExecuteSearch + UpdateBackendData
from collections import defaultdict
import pandas as pd

def fuzzy_search(
    lines: list[str],
    catalogs: list[str],
    search_term: str
) -> pd.DataFrame:
    """
    模糊查询 + 按章节累计频率，对应 VBA:
    1. Like "*" & searchTerm & "*" 模糊匹配
    2. Scripting.Dictionary 按 B 列章节累计
    3. 频率对齐到目录表章节列表，横向追加列
    """
    # 对应 VBA Like "*词条*"
    chapter_counts = defaultdict(lambda: defaultdict(int))

    for line, catalog in zip(lines, catalogs):
        if search_term in line:  # 对应 Like "*词条*"
            chapter_counts[catalog][search_term] += line.count(search_term)

    # 构建频率矩阵（对应"查询词 × 章节"频率矩阵横向追加到目录表）
    df = pd.DataFrame(chapter_counts).T.fillna(0).astype(int)
    df.index.name = '章节'
    return df
```

**关键差异**：
- VBA `Like "*词条*"` → Python `关键词 in 文本`（更直观）
- VBA `Scripting.Dictionary` → Python `defaultdict`（原生支持嵌套）
- VBA 手动对齐章节列表 → Python `pandas.DataFrame`（自动对齐索引）

#### 任务 2：字频统计（第 13-14 天）

对应 VBA 模块：Read_最新字频.bas（6KB）

```python
# src/core/analysis/frequency_stats.py
# 对应 VBA: to___字频音333
from collections import Counter
import re
import jieba

def char_frequency(text: str) -> list[tuple[str, int]]:
    """
    字频统计，对应 VBA:
    1. 正则 [^\u4e00-\u9fa5] 过滤非中文
    2. 逐字 Mid 进字典
    3. 按频率分组
    """
    # 对应 VBA 正则过滤非中文
    chinese_only = re.sub(r'[^\u4e00-\u9fa5]', '', text)
    # 对应 VBA 逐字 Mid 进字典（Counter 一步到位）
    counter = Counter(chinese_only)
    # 按频率降序排序（对应 VBA BubbleSort2DArray）
    return counter.most_common()

def word_frequency(text: str) -> list[tuple[str, int]]:
    """
    词频统计（VBA 无此功能，jieba 分词是新功能）
    """
    words = jieba.cut(text)
    counter = Counter(w for w in words if len(w) > 1)
    return counter.most_common()

def frequency_by_chapter(
    lines: list[str],
    catalogs: list[str],
    char: str
) -> dict[str, int]:
    """
    按章节统计某字出现次数，对应 VBA rex2
    """
    chapter_counts = defaultdict(int)
    for line, catalog in zip(lines, catalogs):
        count = line.count(char)
        if count > 0:
            chapter_counts[catalog] += count
    return dict(chapter_counts)
```

**关键差异**：
- VBA 逐字 `Mid` 进字典 → Python `Counter`（一行代码完成）
- VBA `BubbleSort2DArray` 冒泡排序 → Python `Counter.most_common()`（C 底层排序）
- VBA `rex2` 逐章正则统计 → Python `str.count()`（直接计数）
- 新增：`jieba` 分词支持词组级别统计（VBA 只能逐字）

#### 任务 3：重复字定位（第 15 天）

对应 VBA 模块：READ_最新字频2.bas

```python
# src/core/analysis/duplicate_finder.py
# 对应 VBA: to_字频音__重复字
def find_duplicates(
    lines: list[str],
    catalogs: list[str],
    min_count: int = 2
) -> list[dict]:
    """
    重复字定位，对应 VBA:
    1. 字频统计 → 找出现>1次的字
    2. d3 字典: key="行号|字|语句"，value=分类
    3. 结果写入"重复字"表
    """
    results = []
    # 统计所有字
    all_text = ''.join(lines)
    counter = Counter(c for c in all_text if '\u4e00' <= c <= '\u9fa5')

    for char, count in counter.items():
        if count >= min_count:
            for line_idx, (line, catalog) in enumerate(zip(lines, catalogs)):
                if char in line:
                    results.append({
                        '行号': line_idx,
                        '字': char,
                        '语句': line,
                        '章节': catalog,
                        '总次数': count,
                    })
    return results
```

#### 任务 4：数据聚合（第 16-17 天）

对应 VBA 模块：READ_聚合生成折线堆叠图.bas（16KB）

```python
# src/core/analysis/aggregation.py
# 对应 VBA: AggregateDataWithArrays
import numpy as np

def aggregate_data(
    data: np.ndarray,  # 原始数据矩阵（对应 VBA 二维数组）
    rules: list[tuple[int, int]]  # 对应 VBA 规则字符串 "20,1|50,2"
) -> np.ndarray:
    """
    数据聚合，对应 VBA:
    规则格式：长度,间距|长度,间距...
    20,1 = 生成20列，每列1个原始列（不聚合）
    50,2 = 生成50列，每列2个原始列求和
    """
    result_cols = sum(length for length, _ in rules)
    result = np.zeros((data.shape[0], result_cols))

    col_idx = 0
    for length, step in rules:
        for i in range(length):
            start = col_idx * step
            end = start + step
            if end <= data.shape[1]:
                # 对应 VBA 分组求和
                result[:, col_idx] = data[:, start:end].sum(axis=1)
            col_idx += 1

    return result


def parse_rules(rule_string: str) -> list[tuple[int, int]]:
    """
    解析规则字符串，对应 VBA: "20,1|50,2" → [(20,1), (50,2)]
    """
    rules = []
    for part in rule_string.split('|'):
        length, step = map(int, part.split(','))
        rules.append((length, step))
    return rules
```

**关键差异**：
- VBA 二维数组手动循环 → Python `numpy` 矩阵运算（C 底层，快 10-100 倍）
- VBA `BubbleSort2DArray` → Python `numpy.sum(axis=1)`（一行代码）
- VBA 规则字符串解析 → Python `split` + 列表推导式（更简洁）

#### 任务 5：matplotlib 折线堆叠图（第 18-19 天）

对应 VBA 模块：READ_聚合生成折线堆叠图.bas 中的 CreateCombinedChartOnSheet

```python
# src/gui/views/chart_view.py
# 对应 VBA: CreateCombinedChartOnSheet (xlLineStacked)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

class ChartView(QWidget):
    """图表面板，对应 VBA Excel 图表"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # matplotlib 画布嵌入 PyQt
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

    def plot_stacked_line(
        self,
        x_labels: list[str],      # 对应 VBA X轴="目录"
        series_data: np.ndarray,   # 聚合后数据
        series_names: list[str]    # 对应 VBA 图例
    ):
        """绘制折线堆叠图，对应 VBA xlLineStacked"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # 对应 VBA xlLineStacked 折线堆叠图
        ax.stackplot(
            range(len(x_labels)),
            *series_data,
            labels=series_names,
            baseline='zero'
        )

        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha='right')
        ax.set_xlabel('目录')   # 对应 VBA X轴
        ax.set_ylabel('词量')   # 对应 VBA Y轴
        ax.legend(loc='upper left')
        ax.set_title('章节词频堆叠图')

        self.figure.tight_layout()
        self.canvas.draw()
```

**关键差异**：
- VBA `xlLineStacked` 静态图表 → matplotlib 交互式（缩放、平移、保存）
- VBA 图表绑定单元格区域 → matplotlib 绑定 numpy 数组（自动更新）
- VBA 图表导出需截图 → matplotlib 原生支持保存 PNG/SVG/PDF

#### 任务 6：EPUB 转换（第 20 天）

对应 VBA 模块：FC_EPUB_TO_TXT.bas（5.7KB）

```python
# src/core/epub/epub_converter.py
# 对应 VBA: FC_EPUB_TO_TXT（但无需 WinRAR）
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

def epub_to_txt(file_path: str) -> list[str]:
    """
    EPUB 转 TXT，对应 VBA:
    1. 选择 .epub → 重命名为 .zip
    2. 调用 WinRAR 解压
    3. 遍历 HTML/XHTML 文件
    4. HTML 清洗
    5. 输出 TXT
    ---
    Python 版：ebooklib 直接解析，无需 WinRAR
    """
    book = epub.read_epub(file_path)  # 纯 Python 解析，无需 WinRAR

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html_content = item.get_content().decode('utf-8', errors='replace')
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取标题（对应 VBA 提取 <title>）
        title = soup.find('title')
        if title:
            chapters.append(title.get_text())

        # 提取正文（对应 VBA extracttextfromhtml）
        text = soup.get_text(separator='\n')
        # 对应 VBA 正则保留中文/英文/数字/标点
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；：""''（）]', '', text)
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        chapters.extend(lines)

    return chapters
```

**关键差异**：
- VBA 重命名 .epub → .zip + WinRAR 解压 → Python `ebooklib` 直接解析
- VBA 递归遍历 HTML 文件 + 手动正则清洗 → Python `BeautifulSoup` 自动解析
- VBA 依赖 WinRAR 外部程序 → Python 纯库实现（跨平台）

### 3.3 交付物

| 交付物 | 验收标准 |
|--------|---------|
| 字典查询 | 模糊匹配 + 频率矩阵（pandas DataFrame） |
| 字频统计 | 逐字统计 + 按章节分布 + jieba 词组分词 |
| 重复字定位 | 出现 >1 次的字 + 语句定位 |
| 数据聚合 | 规则字符串解析 + numpy 矩阵聚合 |
| 折线堆叠图 | matplotlib 交互式图表，嵌入 PyQt |
| EPUB 转换 | 无需 WinRAR，纯 Python 解析 |

---

## 四、长期计划：完整应用与功能扩展（第 5-8 周）

### 4.1 目标

将所有功能整合为完整应用，添加 VBA 无法实现的新功能，打包发布。

### 4.2 实现逻辑

#### 功能整合矩阵

| 来源 | 功能 | 实现优先级 | 技术方案 | VBA 对应 |
|------|------|:---:|------|---------|
| test1.xlsm | TXT/Word/Excel 导入 | P0 | chardet + python-docx + openpyxl | READ_TXTTOEXCEL |
| test1.xlsm | 文本清洗（3种模式） | P0 | re 模块 | ProcessTextWithSpaces |
| test1.xlsm | 章节正则识别 | P0 | re 模块 | 正则查询优化 |
| test1.xlsm | 目录补全 | P0 | 遍历 + lastValid | 正则后辅助目录优化 |
| test1.xlsm | 字符级上色 | P0 | QSyntaxHighlighter | Color_SS_TO_SS_22 |
| test1.xlsm | 目录跳转 | P0 | QTextCursor | D_CatalogJump |
| test1.xlsm | 字典查询+频率矩阵 | P1 | dict + pandas | READ_字典查询 |
| test1.xlsm | 字频统计 | P1 | Counter + jieba | to___字频音333 |
| test1.xlsm | 重复字定位 | P1 | dict + 列表 | to_字频音__重复字 |
| test1.xlsm | 数据聚合 | P1 | numpy | AggregateDataWithArrays |
| test1.xlsm | 折线堆叠图 | P1 | matplotlib stackplot | xlLineStacked |
| test1.xlsm | EPUB 转换 | P2 | ebooklib + bs4 | FC_EPUB_TO_TXT |
| test1.xlsm | 拼音生成 | P2 | pypinyin | FC_拼音.bas |
| test1.xlsm | 批量重命名 | P2 | os / shutil | D_批量重命名 |
| test1.xlsm | 正则替换 | P2 | re.sub | 正则替换优化 |
| 新功能 | 简繁互转 | P2 | opencc | 无 |
| 新功能 | 书签进度 | P2 | sqlite3 | 无 |
| 新功能 | 主题切换 | P2 | QSS 样式表 | 无（页面级） |
| 新功能 | 语音朗读 | P3 | pyttsx3 | 无 |
| 新功能 | 导出 PDF | P3 | reportlab | 无 |
| 新功能 | 数据导出 Excel | P3 | openpyxl / pandas | 无 |

#### 架构演进路线

```
阶段 1（第 1-2 周）：核心阅读器
  ┌─────────────────────────────────────┐
  │  Python + PyQt6 + QSyntaxHighlighter│
  │  ├── TXT/Word/Excel 导入             │
  │  ├── 章节识别 + 目录跳转             │
  │  ├── QSyntaxHighlighter 上色         │
  │  └── 基础查询                        │
  └─────────────────────────────────────┘

阶段 2（第 3-4 周）：数据分析整合
  ┌─────────────────────────────────────┐
  │  + 数据分析层                        │
  │  ├── 字频统计 + jieba 词组分析       │
  │  ├── 数据聚合 + numpy 矩阵运算       │
  │  ├── matplotlib 折线堆叠图           │
  │  ├── 重复字定位                      │
  │  └── EPUB 纯 Python 转换             │
  └─────────────────────────────────────┘

阶段 3（第 5-6 周）：阅读增强
  ┌─────────────────────────────────────┐
  │  + 阅读增强功能                      │
  │  ├── 简繁互转（OpenCC）              │
  │  ├── 书签进度（SQLite 持久化）       │
  │  ├── 主题切换（QSS 暗色/亮色）       │
  │  ├── 拼音显示（pypinyin）            │
  │  └── 数据导出（Excel/PDF）           │
  └─────────────────────────────────────┘

阶段 4（第 7-8 周）：打包发布
  ┌─────────────────────────────────────┐
  │  + 完善与发布                        │
  │  ├── 语音朗读（pyttsx3）             │
  │  ├── PyInstaller 打包 exe            │
  │  ├── 自动更新机制                    │
  │  └── 用户文档                        │
  └─────────────────────────────────────┘
```

#### 数据模型设计

```python
# src/models/text_content.py
from dataclasses import dataclass, field

@dataclass
class TextContent:
    """文本内容，对应数据源 A 列"""
    id: str
    lines: list[str]              # 文本行
    source_path: str              # 源文件路径
    encoding: str                 # 编码
    total_lines: int = 0

@dataclass
class Chapter:
    """章节目录，对应数据源 B 列 + 目录表"""
    title: str
    line_index: int               # 起始行号
    end_index: int = 0            # 结束行号
    level: int = 1                # 层级

@dataclass
class ColorRule:
    """上色规则，对应 READ_上色.bas 的 searchTexts 数组"""
    keyword: str
    color_index: int              # 0-3 对应红绿蓝青
    enabled: bool = True

@dataclass
class SearchResult:
    """查询结果，对应字典查询结果"""
    line_index: int
    text: str
    chapter: str
    match_count: int

@dataclass
class FrequencyStat:
    """字频统计，对应 to___字频音333"""
    character: str
    total_count: int
    by_chapter: dict[str, int]    # 章节→出现次数

@dataclass
class AggregationRule:
    """聚合规则，对应 VBA 规则字符串 "20,1|50,2""""
    length: int                   # 生成列数
    step: int                     # 每列合并原始列数
```

#### SQLite 数据库设计

```python
# src/core/database/db_manager.py
# 对应 VBA: 隐藏工作表存储数据
import sqlite3
from pathlib import Path

class DBManager:
    """SQLite 数据库管理，替代 VBA 隐藏工作表"""

    def __init__(self, db_path: str = "novel_reader.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        """初始化数据表"""
        self.conn.executescript("""
            -- 文件记录（对应文件列表）
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                encoding TEXT,
                total_lines INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 章节目录（对应目录表）
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                title TEXT NOT NULL,
                line_index INTEGER NOT NULL,
                end_index INTEGER,
                level INTEGER DEFAULT 1,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- 书签进度（新功能，VBA 无）
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                line_index INTEGER NOT NULL,
                label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- 上色规则（对应 searchTexts 数组）
            CREATE TABLE IF NOT EXISTS color_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                keyword TEXT NOT NULL,
                color_index INTEGER NOT NULL,
                enabled BOOLEAN DEFAULT 1
            );

            -- 字频统计缓存（对应字频统计结果）
            CREATE TABLE IF NOT EXISTS frequency_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                character TEXT NOT NULL,
                total_count INTEGER NOT NULL,
                chapter_data TEXT,  -- JSON: {章节: 次数}
                FOREIGN KEY (file_id) REFERENCES files(id)
            );
        """)
        self.conn.commit()
```

#### 简繁互转（新功能）

```python
# src/core/text_processing/convertor.py
# VBA 无此功能，新增
import opencc

class TextConvertor:
    """简繁互转，新增功能"""

    def __init__(self):
        self.t2s = opencc.OpenCC('t2s')  # 繁→简
        self.s2t = opencc.OpenCC('s2t')  # 简→繁

    def to_simplified(self, text: str) -> str:
        """繁体转简体"""
        return self.t2s.convert(text)

    def to_traditional(self, text: str) -> str:
        """简体转繁体"""
        return self.s2t.convert(text)
```

#### 语音朗读（新功能）

```python
# VBA 无此功能，新增
import pyttsx3

class TextToSpeech:
    """语音朗读，新增功能"""

    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)  # 语速

    def speak(self, text: str):
        """朗读文本"""
        self.engine.say(text)
        self.engine.runAndWait()

    def save_to_file(self, text: str, output_path: str):
        """保存为音频文件"""
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()
```

#### 主题切换（新功能）

```python
# 对应 VBA SheetManager 分类页面切换（但这里是配色级，非页面级）
DARK_THEME = """
QWidget { background-color: #1e1e1e; color: #e0e0e0; }
QTextEdit { background-color: #2d2d2d; color: #e0e0e0; font-size: 18px; }
QToolBar { background-color: #252525; border: none; }
QTabWidget::pane { border: 1px solid #3d3d3d; }
"""

LIGHT_THEME = """
QWidget { background-color: #ffffff; color: #1a1a1a; }
QTextEdit { background-color: #ffffff; color: #1a1a1a; font-size: 18px; }
QToolBar { background-color: #f0f0f0; border: none; }
QTabWidget::pane { border: 1px solid #d0d0d0; }
"""

def apply_theme(app, theme: str = 'light'):
    """切换主题"""
    app.setStyleSheet(DARK_THEME if theme == 'dark' else LIGHT_THEME)
```

#### PyInstaller 打包

```python
# pyinstaller.spec
# 打包为独立 exe，无需 Python 环境
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons', 'assets/icons'),
        ('assets/styles', 'assets/styles'),
    ],
    hiddenimports=['jieba', 'opencc', 'ebooklib'],
    hookspath=[],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name='NovelReader',
    console=False,  # 无控制台窗口
    icon='assets/icons/app.ico',
)
```

### 4.3 交付物

| 交付物 | 验收标准 |
|--------|---------|
| 完整 Python 应用 | Windows/macOS/Linux 三端可运行 |
| 数据分析面板 | 字频统计 + 聚合图表 + 频率矩阵 |
| 阅读增强 | 简繁互转 + 书签进度 + 主题切换 |
| EPUB 支持 | 无需 WinRAR，纯 Python 解析 |
| 语音朗读 | pyttsx3 离线 TTS |
| 打包发布 | PyInstaller 打包 exe，无需 Python 环境 |
| 性能指标 | 100 万字文件导入 < 2 秒，上色 < 0.5 秒 |

---

## 五、VBA vs Python vs Electron 三方案对比

| 维度 | VBA (现有) | Python + PyQt6 | Electron + Vue |
|------|-----------|---------------|----------------|
| 上色性能 | 3-10分钟/10万字 | < 0.5秒/10万字 | < 1秒/10万字 |
| 文件读取 | 15-30秒/10MB | 0.3-1秒/10MB | 0.5-2秒/10MB |
| 跨平台 | 仅 Windows | Windows/macOS/Linux | Windows/macOS/Linux |
| 学习成本 | 已掌握 | 中等（PyQt6） | 较高（Vue+TS+Electron） |
| 开发效率 | 低（无调试器） | 高（IDE 支持） | 高（热重载） |
| 生态 | 无 | PyPI（40万包） | npm（200万包） |
| 打包体积 | 0（Excel 内置） | 50-100MB | 80-150MB |
| UI 美观度 | 低（Excel 限制） | 中（PyQt 原生） | 高（CSS 自由） |
| 数据分析 | 强（Excel 原生） | 强（pandas/numpy） | 中（需 JS 库） |
| AI 扩展 | 不可行 | 可行（丰富库） | 可行（丰富库） |
| 迁移工作量 | — | 中（2-4 周） | 大（1-2 月） |

### 选型建议

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 快速复刻，重视数据分析 | **Python + PyQt6** | pandas/numpy 天然优势，学习成本低 |
| 追求最佳 UI 体验 | Electron + Vue | CSS 自由度最高，UI 最美观 |
| 仅 Windows，不愿迁移 | 继续用 VBA + 优化 | 短期优化即可解决痛点 |
| 需要网页版 | Electron + Vue | 可复用为 Web 应用 |

---

## 六、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|:---:|:---:|------|
| PyQt6 学习曲线 | 中 | 中 | 参考 Qt 官方示例，优先学 QTextEdit/QSyntaxHighlighter |
| QSyntaxHighlighter 大文本性能 | 低 | 高 | 分块着色，仅着色可见区域 |
| chardet 编码检测准确率 | 低 | 中 | chardet + 手动 BOM 检测双保险 |
| ebooklib EPUB 兼容性 | 中 | 低 | 备选方案：直接 zipfile 解压 + BeautifulSoup |
| PyInstaller 打包体积大 | 中 | 低 | 排除不需要的库，使用 --exclude-module |
| jieba 分词内存占用 | 低 | 低 | 延迟加载，仅分析时初始化 |
| matplotlib 中文字体显示 | 中 | 低 | 配置 SimHei / Microsoft YaHei 字体 |

---

## 七、时间线总览

```
第1-2周    ████████████  短期：核心功能复刻
                         （项目搭建 / 文件导入 / 章节识别 / QSyntaxHighlighter上色 / 目录跳转）

第3-4周    ████████████  中期：数据分析整合
                         （字典查询 / 字频统计 / 重复字定位 / 数据聚合 / matplotlib图表 / EPUB转换）

第5-6周    ████████████  长期阶段3：阅读增强
                         （简繁互转 / 书签进度 / 主题切换 / 拼音显示 / 数据导出）

第7-8周    ████████████  长期阶段4：打包发布
                         （语音朗读 / PyInstaller打包 / 自动更新 / 用户文档）
```

每个阶段结束时都有一个**可独立使用的版本**，不依赖后续阶段的完成。

---

## 八、快速启动清单

### 环境准备

```bash
# 1. 安装 Python 3.11+
python --version

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install PyQt6 chardet python-docx openpyxl jieba pandas numpy matplotlib
pip install ebooklib beautifulsoup4 opencc-python-reimplemented pypinyin pyttsx3

# 4. 验证安装
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
python -c "import chardet; print('chardet OK')"
python -c "import jieba; print('jieba OK')"
python -c "import matplotlib; print('matplotlib OK')"
```

### 第一个可运行版本（最小化验证）

```python
# main.py — 最小化验证版本
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QToolBar, QPushButton
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QRegularExpression

class SimpleHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.keywords = []

    def set_keywords(self, words):
        self.keywords = words
        self.rehighlight()

    def highlightBlock(self, text):
        colors = [QColor(255,0,0), QColor(0,255,0), QColor(0,0,255), QColor(0,255,255)]
        for i, word in enumerate(self.keywords):
            fmt = QTextCharFormat()
            fmt.setForeground(colors[i % 4])
            pattern = QRegularExpression(word)
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小说阅读分析工具 - Python版")
        self.resize(1200, 800)

        self.editor = QTextEdit()
        self.highlighter = SimpleHighlighter(self.editor.document())
        self.setCentralWidget(self.editor)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        btn_color = QPushButton("上色测试")
        btn_color.clicked.connect(self.test_color)
        toolbar.addWidget(btn_color)

    def test_color(self):
        self.highlighter.set_keywords(["测试", "小说", "章节"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

运行 `python main.py` 即可验证 PyQt6 + QSyntaxHighlighter 上色功能是否正常。
