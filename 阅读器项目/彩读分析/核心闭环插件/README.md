# 彩读项目 · 核心闭环插件包

> 来源：[彩读项目全链路复盘与软件构造方法论.md](../ColorTxt项目分析/彩读项目全链路复盘与软件构造方法论.md)
> 拆分范围：**核心闭环**（6 项）。扩展能力、前沿探索按当前决策暂缓。
> 技术栈：**Python 纯逻辑插件**（core/gui 分离，标准库优先，可独立运行、可单独测试）

## 一、三层切分回顾

复盘文件把 16 项能力按「必须闭环 / 锦上添花 / 前沿探索」切为三层：

| 层 | 功能 | 处置 |
|---|---|---|
| 核心闭环 | 文件导入 → 编码识别 → 章节识别 → 内容上色 → 目录跳转 → 书签进度 | **本包实现** |
| 扩展能力 | 简繁互转、语音朗读、划线笔记、主题、电子书转换、定时滚动 | 暂缓 |
| 前沿探索 | AI 对话与 RAG、文生图、角色卡、智能排版、Legado 书源找书、WebDAV 同步 | 暂缓（预留接口桩） |

## 二、核心闭环 6 项功能拆分（输入 / 处理 / 输出 / 关键差异）

| # | 功能 | 插件文件 | 输入 | 处理逻辑 | 输出 | 关键差异（vs VBA） |
|---|---|---|---|---|---|---|
| 1 | 文件导入 | `plugin_01_file_import.py` | 本地文件路径(TXT/MD/DOCX/XLSX) | 按扩展名分发 → TXT 先探编码再一次性 `read()` → 切行去空 | `TextContent{lines,encoding,total_lines}` | 一次性读取替代「逐行 Line Input + & 拼接」，快 15~30 倍 |
| 2 | 编码识别 | `plugin_02_encoding_detect.py` | 字节流 / 文件路径 | 三级策略：BOM 头 → chardet 统计 → UTF-8 试探 + GBK 启发式 | `EncodingResult{encoding,confidence,method}` | 引入 chardet 并给出置信度，准确率更高 |
| 3 | 章节识别 | `plugin_03_chapter_detect.py` | 文本行 + 正则规则 | 多正则合并「或」模式逐行 match → 目录向下填充(last_valid) | `Chapter{title,line_index,level}` + 补全目录列 | `VBScript.RegExp`→`re`；向下填充逻辑逐字迁移 |
| 4 | 内容上色 | `plugin_04_coloring.py` | 文本 + 关键词 + 颜色 | 编译规则(4色循环) → `re.finditer` 一次扫描产出区间流 → 重叠裁决 | `Span{start,end,word,color}` 区间流 | 逐子串 COM 调用 → 一次 re 扫描，性能提升百倍 |
| 5 | 目录跳转 | `plugin_05_catalog_jump.py` | 章节列表 + 总行数 + 目标 | 构建章节 [start,end) 区间 → 行号定位 / 标题精确 / 关键词模糊 | `JumpResult{chapter,start_line,end_line}` | `Cells.Select`→纯逻辑行号区间，GUI 层再定位 |
| 6 | 书签进度 | `plugin_06_bookmark_progress.py` | 书号 + 操作 | sqlite3 建表 → 书签增删查 / 进度 upsert 真实行号 | `Bookmark` / `Progress` 记录 | 隐藏工作表→SQLite，事务原子写、诚信计数 |

完整链路数据流：

```
文件路径 ─▶ [01 文件导入] ─▶ [02 编码识别] ─▶ 文本行 lines
                                              │
                    ┌─────────────────────────┘
                    ▼
             [03 章节识别] ─▶ Chapter 列表 ─┬─▶ [05 目录跳转] ─▶ 定位区间
                    │                       └─▶ [06 书签进度] ─▶ 持久化
                    ▼
             [04 内容上色] ─▶ Span 区间流 ─▶ 渲染层(PyQt6 QSyntaxHighlighter / Monaco)
```

## 三、插件清单与依赖

| 文件 | 可独立运行 | 外部依赖 |
|---|---|---|
| `plugin_01_file_import.py` | ✅ | TXT 零依赖；DOCX 需 `python-docx`，XLSX 需 `openpyxl`（可选，缺则明确报错） |
| `plugin_02_encoding_detect.py` | ✅ | `chardet` 可选（未安装自动降级 BOM+启发式） |
| `plugin_03_chapter_detect.py` | ✅ | 仅标准库 `re` |
| `plugin_04_coloring.py` | ✅ | 仅标准库 `re`/`html` |
| `plugin_05_catalog_jump.py` | ✅ | 仅标准库，`import` 了 `plugin_03` 的 `Chapter` |
| `plugin_06_bookmark_progress.py` | ✅ | 仅标准库 `sqlite3` |

## 四、运行方式

```bash
cd 核心闭环插件

# 串成最小闭环（6 环全链路一次跑通：导入→编码→章节→上色→跳转→书签）
python main.py

# 逐个独立运行（每个都带内置演示数据，不需要任何输入就能看效果）
python plugin_01_file_import.py
python plugin_02_encoding_detect.py
python plugin_03_chapter_detect.py
python plugin_04_coloring.py
python plugin_05_catalog_jump.py
python plugin_06_bookmark_progress.py

# 部分插件支持命令行传参
python plugin_01_file_import.py 某本小说.txt   # 导入真实文件
python plugin_02_encoding_detect.py 某文件      # 探测真实编码
```

## 五、设计说明

- **纯逻辑、可独立运行**：每个插件 `python xxx.py` 即可跑通内置演示，无 GUI 依赖；对外只暴露返回纯数据结构的函数，方便单独写测试、也方便上层 PyQt6/Monaco 直接调用。
- **core/gui 分离**：上色插件产出的是「着色区间流」而非直接画色，目录跳转产出「行号区间」而非滚动动作——渲染/定位动作留给 GUI 层，核心逻辑与界面彻底解耦（对应复盘「分层架构」）。
- **对齐复盘教训**：编码三级策略（可观测）、上色换机制不换优化（换底层一次扫描）、书签诚信计数（防假完成）。
- **后续扩展**：扩展能力与前沿探索暂缓；将来要接 AI 功能时，按「接口桩 + 可插拔」模式新增插件，AI 相关函数先 mock、再无缝切换真实模型/API。