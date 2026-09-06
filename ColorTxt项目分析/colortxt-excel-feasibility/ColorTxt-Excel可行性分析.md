# ColorTxt 功能在 Excel 中的实现可行性分析

> xlsm（VBA）vs VSTO（C#）— 逐功能对比与实现路径
> 基于 ColorTxt v3.2.2 共 16 项核心功能 | 分析日期：2026-08-07

---

## 一、结论先行

**核心判断：Excel 不是文本阅读器的理想宿主。**

ColorTxt 的核心体验（Monaco 编辑器 + 字符级上色 + 流畅滚动 + 自定义 UI 布局）与 Excel 的单元格模型存在根本性的范式冲突。但在 Excel 平台上，**约 40% 的功能可以完整实现，30% 可以部分实现，30% 无法实现或代价过大**。

| 可完整实现 | 可部分实现 | 无法/极难实现 |
|:---:|:---:|:---:|
| **6 项** | **6 项** | **4 项** |

---

## 二、平台能力对比：xlsm vs VSTO

### xlsm（VBA 宏）

| 维度 | 说明 |
|------|------|
| 运行环境 | Excel 内置，无需额外安装 |
| 语言 | VBA（基于 VB6，语法老旧） |
| UI 能力 | 仅限工作表 + UserForm（窗体），无现代 UI 框架 |
| 网络请求 | XMLHTTP / WinHttp，可调 REST API |
| HTML 解析 | 无原生 DOM 库，需正则或引用 MSHTML |
| 原生模块 | 可通过 Declare 调 Windows API，但无 NuGet 生态 |
| 分发 | .xlsm 文件直接分发，但需用户启用宏 |

### VSTO（C# .NET）

| 维度 | 说明 |
|------|------|
| 运行环境 | 需安装 VSTO Runtime + .NET Framework |
| 语言 | C#（现代语言，强类型，async/await） |
| UI 能力 | Custom Task Pane（WPF/WinForms），可嵌入自定义控件 |
| 网络请求 | HttpClient，完整 .NET 网络栈 |
| HTML 解析 | HtmlAgilityPack / AngleSharp 等成熟库 |
| 原生模块 | NuGet 生态，可引用任意 .NET 库 |
| 分发 | 需打包安装程序（ClickOnce / MSI） |

---

## 三、功能可行性总览矩阵

| # | 功能 | xlsm (VBA) | VSTO (C#) | 关键瓶颈 |
|---|------|:---:|:---:|------|
| 1 | 本地文件阅读（TXT/MD） | ✅ 可实现 | ✅ 可实现 | 无瓶颈，VBA FileSystemObject / C# File 即可 |
| 2 | 电子书格式转换（epub/pdf/mobi/chm） | ❌ 不可行 | ✅ 可实现 | VBA 无解析库；C# 可用 VersOne.Epub / PdfPig 等 |
| 3 | **内容上色（核心特色）** | ⚠️ 部分可行 | ⚠️ 部分可行 | Excel 无 Monaco Tokenizer；Characters 对象性能极差 |
| 4 | 章节识别 | ✅ 可实现 | ✅ 可实现 | 无瓶颈，正则匹配即可 |
| 5 | 划线标注与笔记 | ⚠️ 部分可行 | ⚠️ 部分可行 | Excel 无选区高亮机制；可用背景色/批注模拟 |
| 6 | 简繁/全半角互转 | ✅ 可实现 | ✅ 可实现 | VBA 可调 OpenCC CLI 或内置字典；C# 可直接引用 |
| 7 | 书签与阅读进度 | ✅ 可实现 | ✅ 可实现 | 无瓶颈，隐藏工作表 / CustomXMLParts 存储 |
| 8 | 语音朗读（TTS） | ⚠️ 部分可行 | ✅ 可实现 | VBA 可调 SAPI；多音色/AI识别需 API 调用 |
| 9 | AI 对话助手 | ⚠️ 部分可行 | ✅ 可实现 | VBA 可调 OpenAI API（XMLHTTP）；流式响应处理困难 |
| 10 | RAG 向量检索 | ❌ 不可行 | ⚠️ 部分可行 | VBA 无向量库/嵌入模型；C# 可用 SQLite + ONNX |
| 11 | 角色卡 / 文生图 | ⚠️ 部分可行 | ⚠️ 部分可行 | API 调用可行；3D 卡片效果不可行 |
| 12 | AI 智能排版 | ⚠️ 部分可行 | ✅ 可实现 | VBA 可调 API 但 Diff 预览困难；C# 可用 WPF 渲染 |
| 13 | 书源找书（Legado） | ❌ 极难 | ⚠️ 部分可行 | VBA 无 HTML DOM 库；C# 可用 AngleSharp 复刻引擎 |
| 14 | 摸鱼快捷键 | ⚠️ 部分可行 | ✅ 可实现 | VBA 可调 Win API 隐藏窗口；全局热键不稳定 |
| 15 | 主题切换 | ✅ 可实现 | ✅ 可实现 | 切换 Excel 配色方案 / 工作表样式 |
| 16 | WebDAV 同步 | ⚠️ 部分可行 | ✅ 可实现 | VBA 需手写 WebDAV 协议；C# 可用 WebDav.Client 库 |

---

## 四、关键功能深度分析

### 4.1 内容上色 — 核心特色（最大瓶颈）

ColorTxt 的核心卖点是「给内容上色」，基于 Monaco Editor 的 Tokenizer 机制实现字符级语法高亮。这是在 Excel 中最难复刻的功能。

**xlsm (VBA) 方案 — ⚠️ 部分可行，性能极差**

- **思路**：将每行文本放入一个单元格，使用 `Range.Characters(start, length).Font.Color` 设置字符颜色
- **致命问题**：Characters 对象操作极慢。一篇 10 万字小说可能需要数万次 COM 调用，耗时数分钟甚至更久
- **替代方案**：使用条件格式（Formula-based），但只能按规则着色整行或单元格，无法实现「高亮特定词语」的细粒度控制
- **自定义高亮词**：可用条件格式 `SEARCH("关键词", A1)` 匹配，但只能改变整个单元格颜色，不能只给关键词上色

**VSTO (C#) 方案 — ⚠️ 部分可行，需 WebBrowser 辅助**

- **方案 A：纯 Excel 单元格**：与 VBA 相同的 Characters 对象限制，性能同样差
- **方案 B：Custom Task Pane + WebBrowser 控件**：在侧边任务窗格中嵌入 WebBrowser，加载本地 HTML + CSS + JS 实现上色逻辑。可完全复刻 ColorTxt 的着色效果，但本质上是在 Excel 里嵌入了一个浏览器
- **方案 C：Custom Task Pane + WPF RichTextBox**：用 WPF 的 FlowDocument 实现字符级着色，性能优于 Excel Characters，但需要自己实现 tokenizer 逻辑

> **结论**：纯 Excel 单元格方案无法实现流畅的字符级上色。如果要在 Excel 中复刻「内容上色」，必须使用 VSTO + 任务窗格 + WebBrowser/WPF，此时 Excel 只是充当一个外壳。

---

### 4.2 RAG 向量检索 — AI 阅读助手的核心

ColorTxt 使用 sqlite-vec + @huggingface/transformers 实现本地向量检索（RAG），支持 AI 基于小说上下文回答问题。

**xlsm (VBA) 方案 — ❌ 不可行**

- VBA 没有本地嵌入模型推理能力（无 ONNX Runtime、无 transformers.js 等价物）
- VBA 没有向量数据库（无 sqlite-vec 等价物）
- **妥协方案**：调用远程嵌入 API（如 OpenAI Embeddings），向量存储用 VBA 数组 + 余弦相似度计算（仅适用于小规模数据，性能差）

**VSTO (C#) 方案 — ⚠️ 部分可行**

- **本地嵌入**：可用 `Microsoft.ML.OnnxRuntime` 加载 BGE/E5 ONNX 模型，在 .NET 中推理
- **向量存储**：可用 `Microsoft.Data.Sqlite` + sqlite-vec（需 C# 绑定），或用纯 .NET 实现余弦相似度检索
- **远程嵌入**：直接调 OpenAI Embeddings API，完全可行
- **限制**：ONNX 模型加载占内存较大，Excel 进程中运行可能有稳定性风险

---

### 4.3 书源找书（Legado 引擎）— 复杂度最高

ColorTxt 用 TypeScript 复刻了 Legado 的完整规则解析链路（AnalyzeRule / AnalyzeUrl / JS 扩展），这是一个高度复杂的引擎。

**xlsm (VBA) 方案 — ❌ 极难实现**

- VBA 无原生 HTML DOM 解析库（只能引用 MSHTML，API 笨重）
- Legado 规则中的 CSS 选择器 / XPath / JSONPath 在 VBA 中实现成本极高
- 书源中的 `<js>` JS 脚本执行在 VBA 中无法实现
- **妥协方案**：仅实现最简单的正则匹配规则，放弃复杂书源兼容性

**VSTO (C#) 方案 — ⚠️ 部分可行**

- HTML 解析：`AngleSharp` 或 `HtmlAgilityPack`，CSS 选择器支持完善
- JSONPath：`JsonPathPlus` 或 `Newtonsoft.Json` + JPath
- JS 脚本执行：可用 `Jint`（.NET JS 引擎）或 `ClearScript`（V8）
- **工作量**：虽然技术可行，但复刻完整 Legado 引擎工作量巨大（ColorTxt 花了数百 commits）

---

### 4.4 语音朗读（TTS）— 可行性较好

ColorTxt 支持 6 种 TTS 引擎，含多音色和 AI 说话人识别。

**xlsm (VBA) 方案 — ⚠️ 部分可行**

- **系统语音**：`CreateObject("SAPI.SpVoice")` 直接可用，零依赖
- **Edge TTS**：可通过 XMLHTTP 调用 Edge TTS WebSocket 接口，但 VBA 处理 WebSocket 较复杂
- **通义/MiniMax/MiMo**：可通过 XMLHTTP 调 REST API，获取音频后用 API 播放
- **多音色**：需自己实现文本切段 + 引号识别逻辑，可行但繁琐
- **AI 说话人识别**：可调 AI API，但结果缓存管理较麻烦

**VSTO (C#) 方案 — ✅ 可实现**

- 完整 `System.Speech.Synthesis` 支持（SAPI5）
- 可用 `WebSocket.Client` 接 Edge TTS
- 各云 TTS API 调用与 ColorTxt 主进程实现几乎一致
- 多音色、AI 识别、缓存管理均可完整实现

---

### 4.5 电子书格式转换 — VBA 的硬伤

ColorTxt 支持 epub/mobi/azw3/fb2/pdf/chm 转 Markdown。

**xlsm (VBA) — ❌ 不可行**

- VBA 生态中不存在 epub/mobi/azw3/chm 的解析库
- PDF 文本提取：可引用 Adobe Acrobat Type Library（需用户安装 Acrobat），通用性差
- **妥协方案**：调用 Calibre 命令行工具（`ebook-convert`）做外部转换，但需用户安装 Calibre

**VSTO (C#) — ✅ 可实现**

- EPUB：`VersOne.Epub`（NuGet，纯 C# EPUB 解析）
- PDF：`PdfPig` 或 `iText7`（文本提取 + 目录）
- MOBI/AZW3：可参考 foliate-js 逻辑用 C# 复刻，或调 Calibre CLI
- CHM：可移植 libmspack 的 C# 版本

---

### 4.6 AI 智能排版 — Diff 预览是关键

ColorTxt 的 AI 排版支持逐行 Diff 预览，确认后写回。

**xlsm (VBA) — ⚠️ 部分可行**

- AI 排版请求：可调 OpenAI API（XMLHTTP）
- **Diff 预览**：VBA 无 Diff 渲染控件，只能用双列单元格对比或纯文本输出
- **分段处理**：可在 VBA 中实现文本分块逻辑

**VSTO (C#) — ✅ 可实现**

- AI 排版请求：`HttpClient` 调 OpenAI API
- **Diff 预览**：可用 WPF `FlowDocument` + 差异算法（如 DiffPlex）渲染逐行对比
- 可嵌入 Custom Task Pane 中展示

---

## 五、三种实现路径对比

| 方案 | 上色体验 | AI 能力 | 开发成本 | 适用场景 |
|------|:---:|:---:|:---:|------|
| **A. 纯 xlsm**（VBA + 单元格） | ❌ 差 | ❌ 极有限 | ✅ 低 | 仅需文本分析、章节提取等数据处理场景，不适合做阅读器 |
| **B. VSTO + Excel**（C# + 单元格） | ⚠️ 一般 | ⚠️ 部分 | ⚠️ 中 | 需要 Excel 数据交互 + 部分 AI 能力，可接受单元格显示 |
| **C. VSTO + 任务窗格**（C# + WPF/WebBrowser） | ✅ 好 | ✅ 完整 | ❌ 高 | 想完整复刻 ColorTxt 体验，但需在 Excel 环境中运行 |

> **方案 C 的悖论**：方案 C（VSTO + WebBrowser 任务窗格）可以复刻 ColorTxt 的绝大部分功能，但此时 Excel 只是一个外壳容器，真正的阅读器逻辑全在 WebBrowser 里。与其这样做，不如直接用 Electron / Tauri 做一个独立应用——这正是 ColorTxt 本身的做法。

---

## 六、最终建议

### 场景一：目标是「在 Excel 中做小说阅读器」

**不建议。** Excel 的单元格模型与连续文本阅读是两种完全不同的范式。核心的「内容上色」功能在纯 Excel 中无法流畅实现，强行用 Characters 对象会导致严重的性能问题。

### 场景二：目标是「在 Excel 中做文本分析工具」

**xlsm (VBA) 足够。** 以下功能可以轻松实现：

- TXT 文件导入 + 章节识别（正则匹配）
- 简繁互转 + 全半角互转
- 书签 + 阅读进度（隐藏工作表存储）
- 主题切换（Excel 配色方案）
- 语音朗读（SAPI.SpVoice）
- AI 对话（XMLHTTP 调 OpenAI API）

这些功能组合起来，可以做一个「Excel 版文本分析助手」，但不是「阅读器」。

### 场景三：目标是「必须用 Excel 但要尽可能接近 ColorTxt」

**选择 VSTO + Custom Task Pane + WebBrowser：**

- 用 C# 开发 VSTO 插件，在 Excel 侧边创建任务窗格
- 任务窗格内嵌入 WebBrowser 控件，加载本地 HTML/CSS/JS
- 着色、编辑、Diff 等复杂 UI 在 WebBrowser 中实现
- 文件读写、AI API 调用等在 C# 主进程完成
- Excel 工作表用于数据存储和结构化分析

这是唯一能在 Excel 中完整复刻 ColorTxt 体验的方案，但开发成本高，且分发需要安装 VSTO Runtime。

### 最佳建议

如果你的需求确实是「做一个像 ColorTxt 一样的阅读器」，**直接用 Electron / Tauri + Vue/React 做独立应用**是更合理的选择。Excel 适合数据处理，不适合做文本阅读器。如果只是想在 Excel 中利用部分功能（如章节分析、简繁转换、AI 问答），用 **xlsm + VBA** 即可，无需 VSTO。

---

## 参考来源

1. [ssnangua, ColorTxt GitHub 仓库](https://github.com/ssnangua/ColorTxt) — 项目源码、README、开发文档
2. [ColorTxt 开发文档 DOCS.md](https://github.com/ssnangua/ColorTxt/blob/main/DOCS.md) — 开发构建、基础功能、AI功能、语音朗读、书源找书五份文档
