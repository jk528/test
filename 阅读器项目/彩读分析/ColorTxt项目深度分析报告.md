---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'ae01f265-2e06-4650-9d2e-59b29f2ff1eb'
  PropagateID: 'ae01f265-2e06-4650-9d2e-59b29f2ff1eb'
  ReservedCode1: '91ae6aa0-e720-47db-bc9a-bd5930f7b20f'
  ReservedCode2: '91ae6aa0-e720-47db-bc9a-bd5930f7b20f'
---

# ColorTxt（彩读）项目深度分析报告

> 项目地址：https://github.com/ssnangua/ColorTxt  
> 版本：3.8.11 | Star：1.7k | 协议：MPL-2.0  
> 技术栈：Electron 35 + Vue 3 + Monaco Editor + TypeScript  

---

## 一、项目概述

ColorTxt（彩读）是一款**本地 TXT 小说阅读器**，核心卖点是「给内容上色」——使用自定义高亮规则对小说文本进行着色，带来独特的阅读体验。除基础的 TXT/MD 阅读外，还支持 EPUB/MOBI/AZW3/FB2/PDF/CHM 等电子书格式的转换加载，并集成了章节识别、简繁互转、划线标注、词典翻译、多角色语音朗读、AI 阅读助手（RAG）、书源找书等功能。支持 macOS、Windows、Linux 三平台。

---

## 二、整体架构

### 2.1 技术架构

项目采用 **Electron + electron-vite** 的标准桌面应用架构，分为四个进程/模块层：

```
┌─────────────────────────────────────────────────┐
│                  Electron 应用                   │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Main     │  │ Preload  │  │ Renderer (Vue) │ │
│  │ 主进程    │  │ 预加载   │  │ 渲染进程        │ │
│  │          │  │          │  │                │ │
│  │ IPC处理   │  │ context  │  │ Monaco编辑器    │ │
│  │ 文件I/O  │←→│ Bridge  │←→│ Vue组件树       │ │
│  │ AI/RAG   │  │          │  │ Composables    │ │
│  │ TTS引擎  │  │          │  │ Stores         │ │
│  │ 书源引擎  │  │          │  │                │ │
│  └──────────┘  └──────────┘  └────────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │            Shared (共享层)                │   │
│  │  类型定义、常量、IPC通道、预设配置         │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 2.2 构建管线

```
electron-vite build          # 编译主进程/preload/渲染进程
    ↓
electron-rebuild             # 重编译原生模块 (better-sqlite3, opencc)
    ↓
prune-pack-deps.mjs          # 裁剪 node_modules（移除非目标平台原生包等）
    ↓
electron-builder             # 打包为 DMG/NSIS/AppImage
```

### 2.3 多窗口架构

| 窗口 | HTML入口 | 说明 |
|------|----------|------|
| 主阅读窗 | `index.html` | Vue 3 应用主界面 |
| 找书窗 | `find-book.html` | 独立窗口，Legado 书源引擎 |
| 取色覆盖层 | `eyedropper.html` | 全屏取色，vanilla TS，无 Vue |
| 摸鱼阅读窗 | `stealth-reader.html` | 无边框透明置顶阅读窗 |
| 摸鱼设置窗 | `stealth-settings.html` | 摸鱼模式独立设置 |

---

## 三、源码目录结构

```
src/
├── main/                    # 主进程
│   ├── index.ts             # 入口：协议注册、窗口管理、IPC、单实例
│   ├── ipcHandlers.ts       # 业务 IPC（对话框、文件流、字体、主题等）
│   ├── ai/                  # AI 模块（按域分子目录）
│   │   ├── infra/           # 配置、路径、数据文件系统
│   │   ├── chat/            # 对话、Agent、深度思考、重试
│   │   ├── rag/             # 向量库、分块缓存、嵌入、章节摘要
│   │   ├── txt2img/         # 文生图（A1111/Comfy/云端多后端）
│   │   └── tools/           # 角色立绘、思维导图、词云
│   ├── voiceRead/           # TTS 引擎注册与合成
│   │   ├── providerRegistry.ts
│   │   └── providers/       # edge/dashscope/minimax/mimo/volcengine/winSapi
│   ├── dictionary/          # 词典查词（StarDict/MDict/DICT/Slob/BGL）
│   ├── webdav/              # WebDAV 同步
│   ├── bookSource/          # Legado 书源引擎
│   │   ├── engine/          # 规则解析器（AnalyzeRule/AnalyzeUrl）
│   │   └── store/           # 书源 SQLite 存储
│   ├── stealthReader.ts     # 摸鱼模式
│   ├── windowFactory.ts     # 窗口创建
│   └── globalShortcuts.ts   # 全局快捷键
├── preload/
│   └── index.ts             # contextBridge 暴露 window.colorTxt
├── renderer/
│   ├── index.html           # 主界面 HTML 壳
│   ├── find-book.html       # 找书窗
│   ├── stealth-reader.html  # 摸鱼阅读窗
│   └── src/
│       ├── App.vue          # 根组件：布局与全局编排
│       ├── components/      # Vue 组件
│       ├── composables/      # 组合式函数（50+ 个）
│       ├── monaco/          # Monaco 阅读器扩展
│       ├── reader/          # 阅读器管线（展示行映射、视口锚点等）
│       ├── ebook/           # 电子书转 Markdown
│       ├── ai/              # 渲染侧 AI（建索引、智能排版）
│       ├── markdown/        # Markdown 章节/内链/图片
│       ├── services/        # 快捷键、文件列表、朗读等
│       ├── stores/          # localStorage 状态管理
│       ├── constants/       # UI常量、配色方案、预设
│       └── utils/           # 工具函数
└── shared/                  # 主进程与渲染进程共享
    ├── aiTypes.ts           # AI 共享类型与默认配置
    ├── voiceReadEngines.ts  # TTS 引擎注册表
    ├── bookSource/          # 书源共享类型与 IPC
    └── ...（60+ 共享模块）
```

---

## 四、各功能模块实现分析

### 4.1 阅读器核心（Monaco Editor 扩展）

**技术方案**：基于 Monaco Editor（VS Code 同款编辑器）进行深度定制，而非自研文本渲染引擎。

**关键实现**：

| 文件 | 功能 |
|------|------|
| `monaco/txtrTextMonarch.ts` | 自定义 `txtr-text` Monarch 语言，实现内容上色 |
| `monaco/txtrHighlightMonarch.ts` | 自定义高亮词 Monarch 规则 |
| `monaco/cjkWrapOptimize.ts` | 中文换行优化（全角标点/特殊符号按全角估算字宽） |
| `monaco/lineSpacing.ts` | 物理行后段间距（通过 Vite transform 改写 Monaco `LinesLayout`） |
| `monaco/chapterStickyScroll.ts` | 黏性章节标题（Monaco `stickyScroll` + DocumentSymbolProvider） |
| `monaco/readerImageViewZones.ts` | Markdown 插图 ViewZone |
| `monaco/readerKeyScroll.ts` | 键盘滚动控制 |

**内容上色**：通过 Monarch 语法规则定义一套高亮规则，对对话引号、人物名称、章节标题、特殊符号等元素自动着色。用户还可自定义高亮词，通过 `txtrHighlightMonarch.ts` 动态注入 Monarch 规则。

**高级换行策略**：默认使用简单换行算法（效率高但不够准确）；可选高级换行策略（更准确但性能差，大文件会卡顿），且 Monaco 已知内存泄漏问题（#5311）。

**段间距实现**：通过 `electron.vite.config.ts` 中的 Vite transform 改写 Monaco 内部的 `LinesLayout` 类——行偏移、行后偏移、whitespace/ViewZone 偏移、视口累加均计入段间距，确保插图 ViewZone 的绝对 top 也正确。

### 4.2 文件加载与流式读取

**大文件处理**：采用流式读取管线，而非一次性加载全文。

```
文件路径 → detectTextEncoding（编码探测）→ 流式按行切分（physicalLineStream）
    → useTxtStreamPipeline（流式解析与映射）→ Monaco setFullText
```

**编码探测**（`detectTextEncoding.ts`）：
- BOM 检测优先
- 使用 `jschardet` 库进行编码检测
- 针对 ANSI 中文编码有启发式补判
- 配合 `iconv-lite` 进行解码

**电子书转换管线**（`ebook/convert/`）：

```
源文件 → readBookAsArrayBuffer → convertBookBufferToArtifacts（按格式分派）
    → parseEpub/parseMobi/parsePdf/parseFb2/parseChm → EbookMarkdownArtifacts
    → writeEbookConversionArtifacts（写出 .md + 插图目录）
    → ensureEbookMarkdown（严格缓存命中检查）
    → 流式读取 .md 进入阅读器
```

**缓存策略**：
- 转换后的 `.md` 文件路径记录在 `file.meta` 的 `convertedMdPath` 字段
- 严格缓存命中条件：路径一致 + 源文件 mtime 一致 + 文件存在
- 和解查找：路径无效时按候选顺序（记录路径 → 输出目录 → 源书同目录 → 默认目录）依次 stat

### 4.3 章节识别

**内置规则**（`chapterMatchBuiltinPatterns.ts`）：预置常用章节匹配正则（如「第X章」「第X回」等）。

**自定义规则**：用户可自定义章节匹配规则；`.md` 文件按 ATX 标题（`#`~`######`）识别，侧栏按标题层级缩进。

**AI 生成规则**：启用 AI 阅读助手后，可让 AI 分析文本并生成章节匹配规则。

**章节列表树**（`chapterListTree.ts`）：支持层级、折叠过滤、祖先展开。

### 4.4 划线标注与笔记

**数据模型**（`ReaderAnnotationRecord`）：
- 持久化于 `colorTxt.file.meta → readerAnnotations`
- 记录物理行+物理列范围、原文快照、创建/更新时间戳
- 支持失效标记（`stale`）：物理区间与快照不一致时标记

**实现**（`useReaderAnnotations.ts` + `reader/readerAnnotationDecor.ts`）：
- 选区工具条弹出标注/笔记工具
- Monaco inline 装饰 + 动态 CSS 规则
- 视口内装饰仅注册 ±80 行范围
- 支持导出 Markdown/JSON、导入 JSON

### 4.5 语音朗读（TTS）

**多引擎 Provider 架构**（`voiceRead/providerRegistry.ts`）：

| 引擎 | 实现 | 密钥 | 音频格式 |
|------|------|------|----------|
| Edge TTS | `edgeProvider` + `voiceReadEdgeTts.ts` | 无需 | MP3 |
| 系统语音 | 渲染进程 Web Speech API | 无需 | MP3 |
| Win SAPI5 | PowerShell `System.Speech` | 无需 | WAV |
| 阿里通义 | `dashscopeProvider` | 需要 | PCM |
| MiniMax | `minimaxProvider` | 需要 | MP3 |
| 小米 MiMo | `mimoProvider` | 需要 | MP3 |
| 火山引擎 | `volcengineProvider` | 需要 | 24kHz PCM |

**多音色方案**：
- **单音色**：全书一段音色
- **旁白/对白多音色**：旁白、默认对白、男声对白、女声对白分轨
- **AI 说话人识别**：朗读前按行调用对话模型识别说话人姓名、性别与情绪，匹配角色专属音色

**标点停顿**（仅 Edge TTS）：Edge 端点不支持 SSML `<break>`，改走 WordBoundary 元数据方案——收集音频 metadata 中的词边界，映射全角标点为待替换区间，播放时替换为干净静音。

**朗读过滤**：独立于朗读方案，支持正则规则（括号内、加粗、斜体等），跨行匹配。

### 4.6 AI 阅读助手（RAG）

**整体架构**：

```
用户提问 → Agent 工具循环（ai/chat/agentChat.ts）
    ├── ragSearch（向量检索）→ vectorDb.ts（SQLite + sqlite-vec）
    ├── ragContext（整章原文）→ 渲染进程索取 / 向量分块拼接
    ├── mindmap（思维导图）→ markmap-lib + markmap-view
    └── wordcloud（词云）→ @node-rs/jieba 分词 + d3-cloud
    ↓
对话模型流式回复（OpenAI 兼容接口）
    ↓
渲染进程展示（折叠思考过程、Token 用量、工具结果）
```

**向量索引**（`buildBookVectorIndex.ts`）：
- 渲染进程按章节分块，经 preload 调主进程嵌入
- 写入 `vector.sqlite`（`better-sqlite3` + `sqlite-vec`）
- 支持内置本地模型（BGE Small ZH v1.5 / Multilingual E5 Small）和远程嵌入 API

**内置嵌入模型**：
- 使用 `@huggingface/transformers` 在 Worker 线程运行
- 模型文件经 HF 镜像（默认 `hf-mirror.com`）下载到本地
- 不消耗 Token，本地执行

**Agent 工具**：
- `ragSearch`：向量检索相关片段
- `ragContext`：拉取整章正文（超长章按每万字压缩）
- `mindmap`：生成 Markdown 层级 → markmap 导图
- `wordcloud`：jieba 分词 + d3-cloud 词云（支持语义模式）

**API 密钥保险库**（`secretStorage.ts`）：
- 加密写入 `userData/ai/secrets.v1.json`
- 串行队列 + 原子落盘（`.tmp` → `rename`）
- 密钥与配置分离，`config.json` 不含明文 Key

### 4.7 书源找书（Legado 兼容引擎）

**架构**：在主进程用 TypeScript 复刻 Legado 书源解析引擎，渲染进程提供独立找书窗口。

```
渲染进程（FindBookWindow → FindBookPanel）
    │  window.colorTxt.bookSource* (preload → IPC)
    ▼
registerBookSourceIpc.ts
    ├── bookSourceStore（SQLite：书源/登录/缓存/Cookie）
    ├── searchService（多源并发搜索）
    ├── downloadService（整书下载）
    └── engine/webBook.ts → AnalyzeUrl + AnalyzeRule + jsExtensions
```

**规则引擎**（`engine/analyzeRule.ts`）：
- 支持 5 种规则模式：Default（Cheerio/Jsoup）、JSON（JsonPath）、XPath、JS（Node AsyncFunction）、Regex
- 链式解析：前段输出作后段 `result`
- `makeUpRule`：展开 `@get:`、`{{…}}` 模板表达式
- `evalJS`：Node `AsyncFunction` 执行书源 JS（非 Rhino JVM），注入 `java`/`source`/`book`/`chapter`/`result` 等绑定

**AnalyzeUrl**（`engine/analyzeUrl.ts`）：
- 解析带规则的书源 URL（含 `@js:`、`{{key}}` 模板、`,{JSON}` 后缀）
- 合并 headers/body，发起请求
- 使用 Chromium `session.fetch`（浏览器 TLS 指纹），仅书源显式 `webView:true` 才开隐藏窗

**并发控制**：`concurrentRateLimiter.ts` 实现书源 `concurrentRate` 限制，未配置时默认每源最多 3 路并发。

**存储**：
- `book-sources.db`（SQLite）：书源 JSON、登录字段、source 级缓存
- `book_cache/`：章节正文离线缓存
- `DownloadedBooks/`：整书导出目录
- Cookie Jar：按可注册域（eTLD+1）归档

### 4.8 角色卡与文生图

**角色卡 3D 效果**：
- 基于 `pokemon-cards-css` 的实现思路
- 指针 3D 倾斜（`useCharacterCardTilt`）+ 弹簧动画（`characterCardSpring.ts`）
- 12 种闪卡纹理效果（`characterCardHoloEffects.css`）
- 原位放大查看（`useCharacterCardPopoverZoom`）
- 网格拖动排序（SortableJS）

**文生图**（`ai/txt2img/`）：
- 多后端路由：A1111 WebUI、ComfyUI、OpenAI Images、Agnes AI、通义万相、MiniMax、Stability AI
- 角色立绘流程：对话模型整理画风+角色形象 → 自然语言 prompt 或 SD tag → 文生图 → 保存到 `CharacterPortrait/`

### 4.9 摸鱼模式

**摸鱼阅读窗**（`stealthReader.ts`）：
- 无边框、透明背景、始终置顶的阅读窗口
- 全局快捷键 `Ctrl+↑/↓` 翻页、`Ctrl+←/→` 切章
- 右键菜单开关定时滚动
- 独立 `localStorage`（`colorTxt.stealth.settings`），不与主窗互通

**摸鱼快捷键**：快速隐藏阅读器（窗口+任务栏按钮+程序坞图标），默认 `Ctrl+``。

### 4.10 WebDAV 同步

**远端目录结构**：
```
ColorTxt/
  Main/               # 主界面配置（settings.json、replaceRules.json、背景图）
  Books/              # 上传的书包
  FindBook/           # 找书数据（书架、书源、设置）
```

**同步策略**：一律覆盖（不比较时间）；书架按内容 hash 增量；自定义背景图按文件名+大小增量。

### 4.11 全屏阅读与极简视图

**全屏模式**：
- 正文居中、两侧空白可滚轮委托给 Monaco
- 顶/底/侧栏边缘感应唤出（`useAppReaderChrome.ts`）
- 指针静止 2 秒隐藏光标
- Esc 连按两次退出

**极简视图**：
- 阅读区撑满窗口，不进系统全屏
- 边缘感应与全屏共用 `chromeAutoHide`
- 不退出极简的 Esc 只关浮动面板

### 4.12 简繁互转与全半角转换

**OpenCC**（`registerTextConvertIpc.ts` + `textConvertOpenCc.ts`）：
- 主进程使用 `createRequire` 加载原生模块（Electroll 打包需 `asarUnpack`）
- `electron-rebuild` 重编译为 Electron 兼容版本
- 转换作用于**展示层**，不改变磁盘原文（`physicalLineContents`）

**全半角互转**（`textWidthConvert.ts`）：字母/数字全半角互转，同样作用于展示层。

---

## 五、存储与释放存储逻辑

### 5.1 存储分层架构

ColorTxt 的数据存储分为**四个层级**：

```
┌─────────────────────────────────────────────────────────┐
│                    存储分层架构                           │
│                                                          │
│  层级1: 渲染进程 localStorage (Chromium 同源隔离)         │
│    ├── colorTxt.ui.settings    # 界面与阅读偏好          │
│    ├── colortxt:voiceReadSpeak # 朗读过滤/自动暂停       │
│    ├── colorTxt.session         # 会话快照               │
│    ├── colorTxt.file.list       # 文件列表缓存           │
│    ├── colorTxt.file.meta       # 按文件聚合的元数据      │
│    ├── colorTxt.recent.files    # 最近打开记录            │
│    ├── colorTxt.stealth.settings # 摸鱼模式偏好          │
│    └── colortxt.findBook.settings # 找书设置              │
│                                                          │
│  层级2: 主进程 userData 目录 (JSON 文件)                  │
│    ├── window-bounds.json      # 窗口位置与尺寸          │
│    ├── ai/data/config.json      # AI 配置（不含密钥）     │
│    ├── ai/secrets.v1.json      # API 密钥保险库（加密）    │
│    ├── ai/data-cache-root.json  # AI 数据缓存根路径       │
│    ├── ConvertedTxt/            # 电子书转换缓存          │
│    ├── UnpackedBooks/          # 书包解压目录             │
│    └── CharacterPortrait/     # 角色立绘缓存             │
│                                                          │
│  层级3: SQLite 数据库 (better-sqlite3)                    │
│    ├── ai/data/vector.sqlite   # 向量索引+AI对话+消息    │
│    ├── ai/data/segment.sqlite   # 词云分词缓存            │
│    └── book-sources.db         # 书源/登录/Cookie        │
│                                                          │
│  层级4: 模型缓存目录                                      │
│    └── ai/model-cache/transformers-cache/ # 内置嵌入模型 │
└─────────────────────────────────────────────────────────┘
```

### 5.2 localStorage 详细键值

| 键名 | 内容 | 落盘时机 |
|------|------|----------|
| `colorTxt.ui.settings` | 字体/字号/行间距/段间距/字间距、空行压缩/行首缩进、主题、侧栏、配色方案、高亮色/标注色、快捷键覆盖、AI 与立绘缓存相关字段等 | 顶栏/侧栏偏好变更时即时写入；设置弹窗点「确定」后写入 |
| `colortxt:voiceReadSpeak` | 朗读过滤规则与自动暂停（不随朗读方案） | 点「保存」后落盘 |
| `colorTxt.session` | 当前文件路径、视口底部物理行号 | 窗口卸载时写入 |
| `colorTxt.file.list` | 文件列表缓存（path/name/size/category/addedAt） | 列表清空/移除/合并/恢复时写入 |
| `colorTxt.file.meta` | 按文件路径聚合的元数据：书签、阅读进度、Monaco saveViewState()、highlightWordsByIndex、readerAnnotations、电子书转换路径、角色卡数据等 | 切书/关窗时 `persistFileMeta` 落盘 |
| `colorTxt.recent.files` | 最近打开记录（仅 `{path}`，MRU 顺序） | 打开新书/切书/窗口卸载时写入 |
| `colorTxt.stealth.settings` | 摸鱼模式偏好（字体/颜色/不透明度/快捷键等） | 摸鱼设置窗与覆盖层经 `storage` 事件同步 |
| `colortxt.findBook.settings` | 找书缓存/下载目录、网络代理等 | 变更时写入 |

### 5.3 落盘时机与门控机制

**核心原则**：数据落盘遵循「变更时即时写」与「卸载时批量写」两条路径，配合多种门控机制防止数据冲突。

#### 5.3.1 常规落盘路径

```
                    ┌─────────────────────┐
                    │   数据变更事件       │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   顶栏/侧栏偏好变更      切书/关窗/卸载      设置弹窗「确定」
            │                  │                  │
            ▼                  ▼                  ▼
   persistSettings()    persistFileMeta()    emit('apply')
   (即时写 localStorage)  (受门控)          (AI密钥→保险库)
```

#### 5.3.2 `persistFileMeta` 门控

```typescript
// 伪代码
function persistFileMeta() {
  // 仅当「当前无打开文件」或「阅读进度已同步」时才真正写入 localStorage
  if (!currentFile || readingProgressSynced === true) {
    localStorage.setItem('colorTxt.file.meta', JSON.stringify(meta));
  } else {
    // 跳过写盘，保留磁盘上上一份可靠数据
    return;
  }
}
```

**设计意图**：避免在阅读进度尚未同步到内存 meta 时，将不完整的元数据覆盖写盘。

#### 5.3.3 `touchRecentFile` 保护

在 `readingProgressSynced === false` 时，不用 live Monaco 视口 / `editorViewState` 覆盖 meta，避免打开瞬间顶部视口冲掉书包导入的锚点。同步完成后补一次位置快照再门控写盘。

#### 5.3.4 多窗口防覆盖

多窗口共用且不实时同步的字段（阅读/编辑/语音/侧栏宽度等）：
- 落盘时先读 localStorage 最新快照
- 仅把本窗相对打开/上次写入基线**有改动**的字段盖上去再写回
- 读到的快照**只用于拼写回盘，不合并进本窗内存**
- 语音方案在本窗有改动时仍按 `id` 与磁盘合并（保留它窗新增、落实本窗删除）

### 5.4 API 密钥保险库（secretStorage.ts）

**存储位置**：`userData/ai/secrets.v1.json`（与 `config.json`、向量库分离）

**安全机制**：
- 写入经**串行队列**串行化
- 落盘为 `secrets.v1.json.tmp` → `rename` 原子替换
- 避免关窗/并发写导致整文件损坏

**密钥槽位**：

| 槽位 | 内容 |
|------|------|
| `ai.embedding.apiKey` | 向量嵌入远程 API 密钥 |
| `ai.chatProfileKeys` | 对话方案密钥 JSON（profileId → apiKey） |
| `ai.txt2imgProfileKeys` | 文生图方案密钥 JSON |
| `voiceRead.profileKeys` | 朗读方案密钥 JSON |
| `translation.providerKeys` | 翻译服务凭证 JSON |

**写入时机**：仅在设置**确定**（AI → `ai:config:set`；语音 → `persistVoiceReadSecretsToVault`）或启动迁移时写入；**关窗 `persistWindowUnloadState()` 不写**保险库。

**启动灌回**：`hydrateApiKeysFromVault` 从保险库读回内存，并将已废弃旧槽一次性迁入 profile 映射后删除。

### 5.5 SQLite 数据库存储

#### 5.5.1 向量库（`vector.sqlite`）

**技术**：`better-sqlite3`（同步 SQLite）+ `sqlite-vec`（向量扩展）

**存储内容**：
- 分块向量（按书籍内容哈希索引）
- 按书的 Agent 会话与消息（`threads` / `messages` 表）

**路径**：默认 `userData/ai/data/vector.sqlite`（+ WAL/SHM），受 `aiDataCacheDir` 设置控制

**目录迁移**：设置中修改数据缓存目录并确定时，关闭向量库连接后合并迁移 `config.json` 与 `vector.sqlite*`

#### 5.5.2 词云分词缓存（`segment.sqlite`）

**存储内容**：按 `bookHash + chapterIndex` 缓存章级词频

**重建机制**：章节正文变更时按 content hash 重建；侧栏「更多 → 重建词云分词」可全书预热

#### 5.5.3 书源数据库（`book-sources.db`）

**表结构**：

| 表 | 内容 |
|----|------|
| `book_sources` | 完整书源 JSON + enabled + last_update_time |
| `book_source_login` | 登录信息字段 |
| `book_source_cache` | source 级缓存（`cache.get/put`、`source.get/put`） |
| `book_source_cookies` | 全局 Cookie Jar（按可注册域 eTLD+1 归档） |

### 5.6 缓存目录体系

| 目录 | 默认路径 | 可配置 | 内容 |
|------|----------|--------|------|
| 电子书转换缓存 | `userData/ConvertedTxt/` | `ebookConvertOutputDir` | 转换后的 `.md` 文件 |
| 书包解压目录 | `userData/UnpackedBooks/` | `bookPackUnpackDir` | 导入的书包解压内容 |
| AI 数据缓存根 | `userData/ai/data/` | `aiDataCacheDir` | config.json、vector.sqlite、segment.sqlite |
| 内置模型缓存 | `userData/ai/model-cache/` | `builtinModelCacheDir` | Transformers.js 权重 |
| 角色立绘缓存 | `userData/CharacterPortrait/` | `characterPortraitCacheDir` | 角色立绘 PNG（按书名分子目录） |
| 找书章节缓存 | `book_cache/` | 找书设置 | 章节正文离线缓存 |
| 找书下载目录 | `DownloadedBooks/` | 找书设置 | 整书导出 `.txt` |
| 词典缓存 | — | 词典管理 | 本地词库数据 |
| 书源文件 | `book-source/files/` | — | importScript / cacheFile 本地脚本 |

### 5.7 释放存储（清除缓存与阅读数据）

#### 5.7.1 清除阅读数据

**入口**：设置 → 常规 → 数据管理 → 「阅读数据」面板

**作用范围**：从 `file.meta` 删除指定路径的：
- 阅读进度
- 书签
- 高亮词
- 笔记
- 角色卡（含立绘目录）
- AI 对话 / 向量索引 / 分词缓存
- 移出最近打开

**不删**：文件本身、文件列表、收藏高亮词、界面设置

**流程**：
```
clearReadingDataForPaths(paths)
    → 内存删除 meta 并移出最近打开
    → 直接覆盖写盘（不走合并）
    → 他窗 storage 事件以磁盘为准重载内存
    → 本窗正在读且磁盘仍有的书仅盖回未落盘进度
```

#### 5.7.2 清除缓存

**入口**：设置 → 常规 → 数据管理 → 「清除缓存」

**完整流程**：
```
1. 设置 sessionStorage colorTxt.skipUnloadPersistence（防回写标记）
2. ai:thread:deleteAll → 清除全部 AI 对话（threads / messages）
3. ai:index:deleteAll → 清除全部向量索引与分词缓存
4. 删除角色立绘缓存根目录（characterPortraitCacheDir）
5. 从 colorTxt.ui.settings 中去掉 highlightWordsByIndexGlobal（收藏高亮词）
6. localStorage.clear() → 写回处理后的 settings
7. window.location.reload()
```

**会清除**：
- 会话快照
- 最近打开记录
- 文件列表
- 全部 file.meta 阅读数据
- 收藏高亮词
- 立绘文件
- 全部 AI 对话记录
- 向量索引与分词缓存
- 其他非 settings 的 localStorage 键

**不会清除**：
- 电子书转换 `.md` 缓存
- 书包解压目录
- 找书下载目录
- `userData/ai/secrets.v1.json`（API 密钥保险库）
- AI 配置 / 密钥
- 界面设置（字号、主题、配色等，除收藏高亮词字段）

#### 5.7.3 防回写机制（关键设计）

**问题**：窗口在 `pagehide` / `beforeunload` 时会调用 `persistWindowUnloadState()`，把内存中的会话、文件列表、最近打开和 meta 写回磁盘。若在 `localStorage.clear()` 之后直接刷新，卸载事件仍会执行，**会把清缓存前的内存状态再次写入**，导致「清不干净」。

**解决方案**：
```
清缓存前 → sessionStorage 设置 skipUnloadPersistenceSessionKey
    ↓
persistWindowUnloadState() 检测到该标记 → 直接 return（跳过卸载落盘）
    ↓
window.location.reload()
    ↓
新页加载 → initPersistenceBootstrap() 开头清除该标记
```

**关窗不整份回写**：关窗时不再整份回写 `colorTxt.ui.settings`（界面设置仅在变更时落盘），避免本窗旧内存覆盖其它窗已保存值。

#### 5.7.4 底栏菜单清除

- **清除阅读数据**（danger）：确认后调用 `clearReadingDataForPaths`，从 file.meta 删除当前会话路径的所有阅读数据
- **重新转换**（仅电子书）：忽略缓存、强制重跑 `convertBookBufferToArtifacts`

### 5.8 旧版数据迁移

**AI 数据布局升级**：
- 首次启动时若存在旧版 `userData/ai/config.json` 或旧 `vector.sqlite`
- 主进程 `upgradeLegacyAiDataLayoutIfNeeded` 自动迁入 `ai/data/` 并写 bootstrap
- `data-cache-root.json` 记录当前生效的 AI 数据缓存绝对路径

**高亮词数据迁移**：
- `normalizeHighlightWordsByIndex` 兼容旧版扁平 `string[]`（每个词迁成单词语组 `[词]`）

**配色方案迁移**：
- `migrateLegacyReaderPaletteOverrides` 迁移旧版配色覆盖，迁完写回并删旧键

**API 密钥迁移**：
- `hydrateApiKeysFromVault` 启动时将旧版单密钥 slot 迁入 profile 映射后删除

---

## 六、关键技术依赖

| 依赖 | 用途 |
|------|------|
| `monaco-editor` | 阅读器核心编辑器 |
| `better-sqlite3` | SQLite 数据库（向量库、书源库） |
| `sqlite-vec` | SQLite 向量扩展（RAG 检索） |
| `@huggingface/transformers` | 内置本地嵌入模型运行 |
| `@node-rs/jieba` | 中文分词（词云生成） |
| `opencc` | 简繁互转（原生模块） |
| `iconv-lite` + `jschardet` | 编码检测与解码 |
| `marked` + `marked-katex-extension` | Markdown 渲染 |
| `markmap-lib` + `markmap-view` | 思维导图渲染 |
| `d3-cloud` | 词云布局 |
| `pdfjs-dist` | PDF 解析 |
| `jszip` | ZIP 容器解析（EPUB/书包） |
| `cheerio` | HTML 解析（书源规则引擎） |
| `jsonpath-plus` | JSON 路径查询（书源规则） |
| `@xmldom/xmldom` | XPath 解析 |
| `heic-convert` | HEIC 封面转 JPEG |
| `tldts` | 可注册域提取（Cookie Jar） |
| `ws` | WebSocket（TTS 流式） |
| `electron-updater` | 自动更新 |

---

## 七、打包优化

### 7.1 node_modules 裁剪（`prune-pack-deps.mjs`）

打包前自动裁剪 `node_modules`，减少安装包体积：

- **整包移除**：`onnxruntime-web`（Web/WASM 推理不需要）、完整 `sharp`（用占位包替代）、`protobufjs` 等孤儿依赖、`prebuild-install` 等安装阶段工具
- **按平台移除**：非目标平台的 `sqlite-vec-*`、`@node-rs/jieba-*` 原生包
- **按路径裁剪**：各包移除 `src/`、`deps/`、`*.map`、README 等非运行时文件

### 7.2 asarUnpack

以下原生模块通过 `asarUnpack` 解包到 `app.asar.unpacked`：
- `better-sqlite3`（SQLite 原生绑定）
- `sqlite-vec*`（向量扩展）
- `onnxruntime-node/bin`（ONNX 运行时）
- `opencc`（简繁转换原生模块 + 词典数据）
- `@node-rs/jieba*`（分词原生扩展）

### 7.3 CI 多平台并行构建

推送版本 tag 后，GitHub Actions 在 5 个 job 上并行构建：
- Windows x64 → NSIS + Portable
- macOS arm64 → DMG
- macOS x64 → DMG（使用 Intel 原生 Runner）
- Linux arm64 → AppImage
- Linux x64 → AppImage

---

## 八、总结

ColorTxt 是一个**工程复杂度极高**的 Electron 桌面应用，其核心亮点在于：

1. **Monaco Editor 深度定制**：通过 Vite transform 改写 Monaco 内部 `LinesLayout`，实现段间距、中文换行优化等自定义布局，远超普通 Monaco 用法
2. **Legado 书源引擎 TypeScript 复刻**：在主进程完整复刻了 Legado 的规则解析链路（AnalyzeRule/AnalyzeUrl/jsExtensions），支持 JS 规则执行、多模式解析、Cookie Jar 等
3. **本地 AI RAG**：使用 SQLite + sqlite-vec 实现本地向量检索，内置 Transformers.js 模型在 Worker 线程运行，无需外部 API 即可实现全文检索
4. **分层存储设计**：localStorage（UI 偏好）+ userData JSON（配置/密钥）+ SQLite（向量/书源）+ 文件系统缓存（电子书/立绘/模型），各层职责清晰
5. **安全落盘机制**：串行队列 + 原子替换 + 门控写盘 + 防回写标记 + 多窗口防覆盖，确保数据一致性

> AI生成