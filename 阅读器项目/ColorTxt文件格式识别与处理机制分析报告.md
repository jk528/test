# ColorTxt 文件格式识别与处理机制分析报告

## 一、格式识别机制

### 1.1 支持的文件格式总览

ColorTxt 支持以下书籍/文本格式：

| 格式类别 | 扩展名 | 说明 |
|---------|--------|------|
| 纯文本 | `.txt` | 核心格式，支持流式读取 |
| Markdown | `.md` | 原生支持，ATX 标题识别 |
| EPUB | `.epub` | 电子书格式 |
| MOBI | `.mobi` | Kindle 格式 |
| AZW3 | `.azw3` | Kindle 格式 |
| FB2 | `.fb2` / `.fbz` | FictionBook 格式（fbz 为 ZIP 压缩） |
| PDF | `.pdf` | 便携式文档格式 |
| CHM | `.chm` | 微软编译 HTML 帮助 |
| 彩读书包 | `.ctz` / `.ctzx` | ColorTxt 自有 ZIP 格式（ctzx 为加密版） |

词典格式（独立于书籍导入）：
- MDX/MDD (mdict-js)
- StarDict (.ifo + .idx + .dict/.dz)
- DICT/dictd (.index + .dict/.dz)
- Slob v1 (Aard 2)
- Babylon BGL

### 1.2 格式识别核心文件与函数

**主进程格式识别：**
- **文件**: `d:\维读项目\ColorTxt\src\shared\ebookExtensions.ts`
- **核心常量**: `EBOOK_DOT_EXTENSIONS` — 电子书扩展名列表
  ```typescript
  export const EBOOK_DOT_EXTENSIONS = [
    ".epub", ".mobi", ".azw3", ".fb2", ".fbz", ".pdf", ".chm",
  ] as const;
  ```
- **函数**: `isSupportedShellOpenPath(filePath)` — 判断是否为支持的书籍路径

**渲染进程格式识别：**
- **文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\ebookFormat.ts`
- **函数**:
  - `isEbookFilePath(filePath)` — 是否为电子书（不含 TXT/MD）
  - `isSupportedBookPath(filePath)` — 是否为支持的书籍路径（TXT/MD/电子书）
  - `isPlainTextBookPath(filePath)` — 是否为纯文本书（.txt/.md）
  - `isMarkdownFilePath(filePath)` — 是否为 Markdown 文件

**主进程 IPC 侧识别：**
- **文件**: `d:\维读项目\ColorTxt\src\main\ipcHandlers.ts`
- **函数**: `isTxtOrEbookFileName(fileName)` — 目录扫描时过滤文件

**对话框过滤器：**
- **文件**: `d:\维读项目\ColorTxt\src\shared\colorTxtOpenSaveDialog.ts`
- **常量**: `COLOR_TXT_OPEN_BOOK_EXTENSIONS` — 打开书籍对话框使用的扩展名
  ```typescript
  export const COLOR_TXT_OPEN_BOOK_EXTENSIONS = [
    "txt", "md", "epub", "mobi", "azw3", "fb2", "fbz", "pdf",
  ] as const;
  ```

### 1.3 格式检测方式

ColorTxt **主要基于文件扩展名**进行格式识别，不使用 MIME type 检测。识别逻辑采用**后缀匹配**（大小写不敏感），通过 `toLowerCase()` 后调用 `endsWith(ext)` 实现。

对于 MOBI/AZW3 格式，存在一个特殊的 ZIP 回退检测：
- **文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parseEpub.ts`
- **函数**: `tryConvertZipAsEpub(buffer, outputBase)` — 先尝试以 ZIP/EPUB 方式解析，若失败再走 MOBI 解析
- 原因：部分 .mobi/.azw3 文件实际是 EPUB 打包的 KF8 格式

---

## 二、各格式处理器详解

### 2.1 TXT 格式处理

**核心文件**:
- 编码检测: `d:\维读项目\ColorTxt\src\main\detectTextEncoding.ts`
- 流式读取: `d:\维读项目\ColorTxt\src\main\ipcHandlers.ts`（`file:stream` IPC）
- 行分割器: `d:\维读项目\ColorTxt\src\renderer\src\services\physicalLineStream.ts`
- 流式管线: `d:\维读项目\ColorTxt\src\renderer\src\composables\useTxtStreamPipeline.ts`

**编码检测** (`detectTextEncoding.ts`):
- **函数**: `detectTextFileEncoding(filePath, locale?)`
- **库依赖**: `jschardet` + `iconv-lite`
- **检测策略**（优先级从高到低）:
  1. BOM 检测：UTF-8 BOM (EF BB BF)、UTF-16LE (FF FE)、UTF-16BE (FE FF)
  2. 纯 ASCII 判定
  3. 有效 UTF-8 序列验证
  4. jschardet 库检测
  5. 中文 GBK/GB18030 启发式检测（字节结构分析 + locale 辅助）
- **采样大小**: 64KB（`SAMPLE_BYTES = 64 * 1024`）
- **最终输出**: 统一返回 `iconv-lite` 可识别的编码名（如 `utf8`、`gb18030`、`utf16le`）

**流式读取** (`ipcHandlers.ts` 中 `file:stream`):
- 读取方式：Node.js `createReadStream`，块大小 256KB
- 编码：通过 `iconv.getDecoder(encoding)` 流式解码
- 传输：通过 IPC 逐 chunk 发送到渲染进程
- 流协议：`StreamStart` → 多个 `StreamChunkPayload` → `StreamEndPayload`

**物理行分割** (`physicalLineStream.ts`):
- **函数**: `createPhysicalLineSplitter()`
- 处理 `\r\n`、`\r`、`\n` 三种换行符
- 跨 chunk 的 `\r\n` 正确处理（不重复计数）

### 2.2 EPUB 格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parseEpub.ts`

**入口函数**: `convertEpubToArtifacts(buffer, outputBase)`

**依赖库**: `jszip` — 用于解压 EPUB（ZIP 容器）

**解析流程**:
1. **加载 ZIP**: `JSZip.loadAsync(buffer)`
2. **读取容器元数据**: 解析 `META-INF/container.xml` 获取 OPF 文件路径
3. **解析 OPF**: 读取 `.opf` 文件，解析 `manifest` 和 `spine`
4. **构建 spine 映射**: 为每个 HTML 章节分配 `epub-NNNN` 格式的逻辑键
5. **逐章转换**: 遍历 spine 中的 XHTML 文档
   - 解析 XHTML/HTML（优先 XHTML，失败回退 HTML）
   - DOM 遍历，将 HTML 转换为纯文本行
   - 处理图片：提取到 `{outputBase}.Images/` 目录
   - 处理内链：转换为 Markdown 内链格式 `[text](#fragment)`
   - 处理脚注：`epub:type="footnote"` / `endnote` 等特殊处理
6. **提取目录**: 从 `nav.xhtml` 或 `toc.ncx` 提取 TOC 条目
7. **注入目录锚点**: 将目录标题注入到正文对应位置（ATX 格式 `# 标题`）
8. **输出**: 拼接所有行，返回 `EbookMarkdownArtifacts`

**EPUB 专用辅助模块**:
- `ebookEpubNav.ts` — 提取 EPUB 内嵌目录（nav.xhtml / NCX）
- `ebookTocAnchorInjection.ts` — 目录锚点注入逻辑
- `ebookSpineLineMatch.ts` — spine 章节行范围匹配
- `ebookLinkIconHeuristics.ts` — 链接图标启发式识别
- `ebookFootnoteLinkFragments.ts` — 脚注链接片段处理
- `ebookStemOnlyMdLinks.ts` — 仅文件名的 MD 链接锚点注入

### 2.3 PDF 格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parsePdf.ts`

**入口函数**: `convertPdfToArtifacts(buffer, outputBase, onProgress?)`

**依赖库**: `pdfjs-dist/legacy/build/pdf.mjs` — PDF.js 库（legacy 构建）

**解析流程**:
1. **配置 Worker**: 设置 `GlobalWorkerOptions.workerSrc`
2. **构建图片目录**: 预扫描 PDF XObject 图片资源（`parsePdfImages.ts`）
3. **加载文档**: `getDocument({ data, disableFontFace, ... })`
4. **逐页提取文本**（支持进度回调）:
   - 调用 `page.getTextContent()` 获取文本片段
   - 调用 `page.getAnnotations()` 获取链接注解
   - 按内容流顺序和纵向位置聚类成行
   - 处理链接：外部链接保留 URL，内部链接转为 Markdown 内链（目标为 `pdf-p{页码}`）
   - 提取页面图片：解码 XObject 图像，保存到 Images 目录
5. **提取大纲**: `doc.getOutline()` 获取 PDF 书签/目录
6. **注入目录标题**: 根据大纲目标页码和 Y 坐标，在对应页内注入 ATX 标题
7. **输出**: 返回 `EbookMarkdownArtifacts`

**PDF 图片处理**: `parsePdfImages.ts`
- 直接解析 PDF XObject，不依赖 PDF.js 的渲染管线
- 支持 WASM 加速解码

### 2.4 MOBI / AZW3 格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parseMobi.ts`

**入口函数**: `convertMobiToArtifacts(buffer, outputBase)`

**依赖库**:
- `pako` (inflate) — zlib 解压
- `./mobi/foliateMobi.js` — 基于 foliate-js 的 MOBI 解析器（MOBI6 / KF8 / PDB）

**解析流程**:
1. **格式验证**: `isMOBI(file)` — 检查是否为 BOOKMOBI 格式
2. **打开 MOBI**: `new MOBI({ unzlib }).open(file)`
3. **构建 filepos 映射**: 扫描所有 section 中的 `id="filepos…"` 锚点，用于 MOBI6 内链解析
4. **逐节转换**: 遍历 `book.sections`
   - 调用 `section.createDocument()` 获取 HTML DOM
   - DOM 遍历转换为文本行
   - 处理图片：通过 `mobi.loadResource(index)` 加载资源，支持 `recindex` 和 `kindle:embed:` 两种引用方式
   - 处理内链：支持 `filepos:`、`kindle:pos:`、同文档 `#id` 等格式
5. **注入目录**:
   - 优先使用 `book.toc`（foliate 解析的目录树）
   - 回退到 NCX 目录（`buildMobiTocTreeFromNcx`）
   - 通过 `splitTOCHref` 或 `resolveHref` 解析目标位置
   - 注入 ATX 格式标题
6. **输出**: 返回 `EbookMarkdownArtifacts`

**AZW3 特殊处理**:
- 先调用 `tryConvertZipAsEpub()` 尝试按 EPUB 解析（部分 AZW3 实际是 KF8+EPUB 打包）
- 失败后回退到 MOBI 解析路径

### 2.5 FB2 / FBZ 格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parseFb2.ts`

**入口函数**: `convertFb2ToArtifacts(buffer, isFbz, outputBase)`

**依赖库**: `jszip`（仅 FBZ 格式需要）

**解析流程**:
1. **解压**（FBZ 格式）: 用 JSZip 解压，找到第一个 `.fb2` 文件
2. **解析 XML**: `DOMParser` 解析 FB2 XML
3. **提取书名**: 从 `<description><book-title>` 获取
4. **收集二进制资源**: 解析 `<binary>` 元素（base64 编码的图片），按 content-type 确定扩展名
5. **转换正文**: 遍历 `<body>` 内的 `<section>` 结构
   - `<title>` → 标题行
   - `<p>` → 段落行
   - `<image xlink:href="#id">` → Markdown 图片
   - `<a href="#id">` → Markdown 内链
6. **生成目录**: 从 `<section id>` + `<title>` 构建
7. **输出**: 返回 `EbookMarkdownArtifacts`

### 2.6 CHM 格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\parseChm.ts`

**入口函数**: `convertChmToArtifacts(buffer, outputBase)`

**依赖模块**: `./chm/chmArchive` — 自研 CHM 归档解析器

**解析流程**:
1. **打开 CHM 归档**: `new ChmArchive(buffer)`
2. **定位正文文件**: 查找 `/txt/*.txt` 路径下的文件（按名称排序）
3. **逐文件转换**:
   - 编码检测：先尝试 UTF-8 严格解码，失败则回退 GB18030/GBK（中文 CHM 常见）
   - 特殊处理：检测 `document.write('...')` 模式，提取其中的 HTML 再解析
   - 纯文本直接按行输出；HTML 内容走 DOM 遍历
4. **图片处理**: 从 CHM 归档中读取图片资源
5. **输出**: 返回 `EbookMarkdownArtifacts`

### 2.7 Markdown 格式处理

**核心文件**:
- 章节识别: `d:\维读项目\ColorTxt\src\renderer\src\markdown\markdownChapter.ts`
- 图片解析: `d:\维读项目\ColorTxt\src\renderer\src\markdown\markdownImages.ts`
- 内链处理: `d:\维读项目\ColorTxt\src\renderer\src\markdown\markdownInternalLinks.ts`
- 块级上下文: `d:\维读项目\ColorTxt\src\renderer\src\markdown\markdownBlockContext.ts`

**章节识别** (`markdownChapter.ts`):
- **函数**: `scanMarkdownHeadingsOnPhysicalLines(physicalLines)`
- **规则**: ATX 标题语法（`#` 至 `######`）
- **特性**: 跳过代码块内的 `#`（使用 `MarkdownBlockContextTracker` 跟踪代码块状态）
- **函数**: `buildChaptersFromMarkdownPhysicalLines()` — 构建章节列表（含字数统计、层级折叠）

**图片处理** (`markdownImages.ts`):
- **库依赖**: `marked` (Lexer) — 用于解析 `![alt](url)` 语法
- **函数**: `resolveMarkdownBlockImageAbsPath(url, mdFileAbsPath)` — 解析图片绝对路径
- 支持远程图片（https://）、绝对路径、相对路径

**内链处理** (`markdownInternalLinks.ts`):
- 剥离 Markdown 内链语法，生成侧车数据（sidecar）
- 支持点击跳转、内链锚点定位

### 2.8 词典格式处理

**核心文件**: `d:\维读项目\ColorTxt\src\main\dictionary\dictionaryService.ts`

**支持的词典格式**:

| 格式 | 解析器文件 | 依赖 | 说明 |
|------|-----------|------|------|
| MDX/MDD | `mdictReader.ts` | `mdict-js` | 金山词霸/MDict 格式 |
| StarDict | `stardictReader.ts` | 自研 | .ifo + .idx + .dict(.dz) + .syn |
| DICT/dictd | `dictReader.ts` | 自研 | .index + .dict(.dz)，base64 偏移 |
| Slob v1 | `slobReader.ts` | `pako` (zlib) | Aard 2 词典格式 |
| Babylon BGL | `bglReader.ts` | `pako` (gzip) | Babylon 词典格式 |
| 网络词典 | `networkProviders.ts` | - | Wikipedia / Wiktionary |

**词典导入**:
- **文件**: `d:\维读项目\ColorTxt\src\main\dictionary\importBundles.ts`
- 支持从文件夹导入，自动识别格式
- 导入后存储到 `userData/dictionaries/` 目录

---

## 三、统一格式与渲染机制

### 3.1 统一格式：Markdown

所有电子书格式最终都转换为 **Markdown 格式**（UTF-8 编码），输出到 `{源文件名}.md` 文件。

**统一产物类型** (`ebookTypes.ts`):
```typescript
export type EbookMarkdownArtifacts = {
  utf8: string;                                          // 转换后的 Markdown 文本
  imageWrites?: Array<{ relativePath: string; data: ArrayBuffer }>; // 图片资源
};
```

**图片输出目录**: `{basename}.Images/`（与 `.md` 文件同级）

### 3.2 转换输出路径策略

**文件**: `d:\维读项目\ColorTxt\src\renderer\src\ebook\convert\convertEbookToMarkdown.ts`

**函数**: `resolveConvertedMdOutputPaths(params)`
- 默认：与源书同目录
- 可配置：`ebookConvertOutputDir` 设置统一输出目录
- 回退：默认电子书转换缓存目录

**缓存机制** (`ensureEbookMarkdown`):
- 记录源文件 mtime，若未变化且转换结果存在则跳过转换
- 支持多路径查找（记录的路径、配置目录、源书旁、默认缓存目录）

### 3.3 章节提取逻辑

**两种章节识别模式**:

**模式一：正则匹配（纯文本 TXT）**
- **文件**: `d:\维读项目\ColorTxt\src\renderer\src\chapter.ts`
- **函数**: `detectChapterTitle(line)`
- **内置规则**（3 条）:
  - `builtin-main`: 主规则（第X章/回/卷/节等）
  - `builtin-alt`: 备选规则
  - `builtin-num-ordered`: 数字序号规则（默认禁用）
- 用户可自定义正则规则
- 支持最少字数过滤（`minCharCount`）

**模式二：ATX 标题（Markdown / 转换后的电子书）**
- **文件**: `d:\维读项目\ColorTxt\src\renderer\src\markdown\markdownChapter.ts`
- **函数**: `scanMarkdownHeadingsOnPhysicalLines()`
- 识别 `#` ~ `######` ATX 标题
- 跳过代码块内的 `#` 符号
- 支持标题层级（headingLevel）与字数汇总（子级字数累加到父级）

**章节数据结构**:
```typescript
type Chapter = {
  title: string;        // 章节标题
  lineNumber: number;   // 所在行号（Monaco 展示行，1-based）
  charCount: number;    // 章节字数
  headingLevel?: number; // 标题层级（1=顶级）
  tocOrder?: number;    // 目录顺序
};
```

### 3.4 渲染机制：Monaco Editor

**核心文件**: `d:\维读项目\ColorTxt\src\renderer\src\components\ReaderMain.vue`

**渲染引擎**: Monaco Editor（VS Code 同款编辑器）

**显示流水线** (`readerDisplayPipeline.ts`):
1. 物理行 → 格式化展示行
   - 压缩空行（可选）
   - 章节标题留白（before1 / before1After1 / before2After1）
   - 行首全角缩进（两个全角空格「　　」）
   - Markdown ATX 标题剥离 `#` 前缀（只读模式）
2. 行映射维护：展示行号 ↔ 物理行号
3. 章节定位与粘性滚动

**特殊渲染 Zone**:
- 图片：Monaco Content Widget（`readerImageViewZones.ts`）
- 内联装饰：高亮、批注等（`readerInlineDecorations.ts`）
- 章节粘性滚动（`chapterStickyScroll.ts`）

**自定义语言**: `txtrTextMonarch.ts` — 彩读文本的 Monarch 语法高亮

---

## 四、文件导入完整流程

### 4.1 导入入口

**用户触发方式**:
1. 对话框打开：`openFileViaDialog()` → `dialog:showOpenDialog`
2. 拖放文件：`App.vue` 中监听 `drop` 事件
3. 侧边栏列表点击：`openFileFromSidebar()`
4. 最近文件：`openRecentFileFromHistory()`
5. 关联打开：系统双击文件 → `launchTxtHandlers.ts` → `openTxtInMainWindow()`
6. 彩读书包：`.ctz` / `.ctzx` → `tryImportReaderBookPack()`

### 4.2 完整导入链路

以下是从用户选择文件到加入书架并渲染的完整流程：

```
用户选择文件
    │
    ▼
[1] openFilePath(filePath)                     useAppFileSession.ts
    │
    ├─ 检查编辑未保存确认
    ├─ 尝试导入彩读书包 (.ctz/.ctzx)
    │
    ▼
[2] prepareOpenFile()                          fileOpenService.ts
    │  验证文件存在、获取文件大小
    │
    ▼
[3] resolvePhysicalTextForOpen()               useAppFileSession.ts
    │
    ├─ 若是 TXT/MD：
    │   └─ 直接返回 physicalPath = filePath
    │
    └─ 若是电子书（EPUB/PDF/MOBI/...）:
        │
        ▼
[3a] ensureEbookMarkdown()                     convertEbookToMarkdown.ts
     │
     ├─ 检查缓存（mtime + 已转换文件）
     ├─ 命中缓存 → 跳过转换
     │
     └─ 未命中 → 执行转换:
         │
         ▼
[3b] convertBookBufferToArtifacts()            convertEbookToMarkdown.ts
     │  根据扩展名分发到对应解析器:
     │  .epub → convertEpubToArtifacts()
     │  .mobi/.azw3 → tryConvertZipAsEpub() → convertMobiToArtifacts()
     │  .fb2/.fbz → convertFb2ToArtifacts()
     │  .pdf → convertPdfToArtifacts()
     │  .chm → convertChmToArtifacts()
     │
     ▼
[3c] writeEbookConversionArtifacts()           convertEbookToMarkdown.ts
     │  写入 {basename}.md + {basename}.Images/
     │
     ▼
     返回 convertedMdPath（转换后的 .md 路径）
    │
    ▼
[4] resetSession(filePath)                     useAppFileSession.ts
    │  重置当前会话状态
    │  设置 physicalReaderPath
    │
    ▼
[5] window.colorTxt.streamFile(physicalPath)   preload/index.ts → IPC → 主进程
    │
    ▼
[6] ipcMain.on("file:stream")                  ipcHandlers.ts
    │
    ├─ detectEncoding() — 检测文件编码（TXT 专用）
    ├─ iconv.getDecoder(encoding) — 创建解码器
    ├─ createReadStream() — 创建文件读取流（256KB chunks）
    └─ 通过 webContents.send 逐块发送文本
    │
    ▼
[7] 渲染进程接收流数据                          useTxtStreamPipeline.ts
    │
    ├─ createPhysicalLineSplitter() — 分割物理行
    ├─ 累积 physicalLineContents
    ├─ 更新加载进度
    │
    ▼
[8] 流结束 → formatPhysicalLinesForReader()    readerDisplayPipeline.ts
    │
    ├─ 压缩空行 / 章节留白 / 行首缩进
    ├─ Markdown：剥离 ATX # 前缀、处理内链
    ├─ 构建章节列表
    ├─ 写入 Monaco Editor
    │
    ▼
[9] 加入文件列表 / 书架                        fileListService.ts
    │
    └─ 持久化列表缓存 + 更新最近文件记录
```

### 4.3 关键 IPC 通道

| IPC 通道 | 方向 | 用途 |
|---------|------|------|
| `file:stream` | 渲染→主（on） | 启动文件流式读取 |
| `file:stat` | 渲染→主（handle） | 获取文件状态 |
| `file:readFileAsBuffer` | 渲染→主（handle） | 读取文件为 Buffer |
| `file:readWholeTextFile` | 渲染→主（handle） | 读取整个文本文件 |
| `dialog:showOpenDialog` | 渲染→主（handle） | 显示打开文件对话框 |
| `file:watchCurrent` | 渲染→主（handle） | 监视文件变化 |

### 4.4 数据持久化

**文件列表/书架**:
- **存储**: localStorage（渲染进程）
- **文件**: `stores/cacheStore.ts`、`stores/fileMetaStore.ts`
- **内容**: 文件路径、大小、阅读进度、元数据

**文件元数据** (`fileMetaStore.ts`):
- 阅读进度（行号 / 百分比）
- 编辑器视图状态
- 电子书转换结果路径
- 源文件 mtime（用于缓存判断）

---

## 五、核心文件索引

### 5.1 格式识别
| 文件路径 | 作用 |
|---------|------|
| `src/shared/ebookExtensions.ts` | 电子书扩展名常量、shell 打开判断 |
| `src/renderer/src/ebook/ebookFormat.ts` | 渲染进程格式判断函数 |
| `src/shared/colorTxtOpenSaveDialog.ts` | 对话框过滤器扩展名 |
| `src/main/detectTextEncoding.ts` | TXT 编码检测 |

### 5.2 格式转换
| 文件路径 | 格式 | 关键函数 |
|---------|------|---------|
| `src/renderer/src/ebook/convert/convertEbookToMarkdown.ts` | 调度中心 | `convertBookBufferToArtifacts`, `ensureEbookMarkdown` |
| `src/renderer/src/ebook/convert/parseEpub.ts` | EPUB | `convertEpubToArtifacts`, `tryConvertZipAsEpub` |
| `src/renderer/src/ebook/convert/parsePdf.ts` | PDF | `convertPdfToArtifacts` |
| `src/renderer/src/ebook/convert/parseMobi.ts` | MOBI/AZW3 | `convertMobiToArtifacts` |
| `src/renderer/src/ebook/convert/parseFb2.ts` | FB2/FBZ | `convertFb2ToArtifacts` |
| `src/renderer/src/ebook/convert/parseChm.ts` | CHM | `convertChmToArtifacts` |
| `src/renderer/src/ebook/convert/ebookTypes.ts` | 通用 | `EbookMarkdownArtifacts` 类型 |

### 5.3 章节与目录
| 文件路径 | 作用 |
|---------|------|
| `src/renderer/src/chapter.ts` | 纯文本章节正则匹配 |
| `src/renderer/src/markdown/markdownChapter.ts` | Markdown ATX 标题章节识别 |
| `src/renderer/src/ebook/convert/ebookTocTypes.ts` | 内嵌目录类型定义 |
| `src/renderer/src/ebook/convert/ebookTocAnchorInjection.ts` | 目录锚点注入 |
| `src/renderer/src/ebook/convert/ebookEpubNav.ts` | EPUB 目录提取 |

### 5.4 导入流程
| 文件路径 | 作用 |
|---------|------|
| `src/renderer/src/composables/useAppFileSession.ts` | 文件会话管理（打开/关闭/列表） |
| `src/renderer/src/services/fileOpenService.ts` | 文件打开前置检查 |
| `src/renderer/src/services/physicalLineStream.ts` | 物理行分割器 |
| `src/renderer/src/composables/useTxtStreamPipeline.ts` | TXT 流式读取管线 |
| `src/main/ipcHandlers.ts` | 主进程 IPC 处理器（文件流等） |
| `src/preload/index.ts` | preload 桥接层（colorTxt API） |

### 5.5 词典格式
| 文件路径 | 格式 |
|---------|------|
| `src/main/dictionary/dictionaryService.ts` | 词典服务总调度 |
| `src/main/dictionary/mdictReader.ts` | MDX/MDD (mdict-js) |
| `src/main/dictionary/stardictReader.ts` | StarDict |
| `src/main/dictionary/dictReader.ts` | DICT/dictd |
| `src/main/dictionary/slobReader.ts` | Slob v1 (Aard 2) |
| `src/main/dictionary/bglReader.ts` | Babylon BGL |
| `src/main/dictionary/importBundles.ts` | 词典导入 |

### 5.6 渲染与显示
| 文件路径 | 作用 |
|---------|------|
| `src/renderer/src/components/ReaderMain.vue` | 阅读器主组件（Monaco 封装） |
| `src/renderer/src/reader/readerDisplayPipeline.ts` | 阅读器显示格式化流水线 |
| `src/renderer/src/markdown/markdownImages.ts` | Markdown 图片解析 |
| `src/renderer/src/markdown/markdownInternalLinks.ts` | Markdown 内链处理 |
