# ColorTxt（彩读）项目功能分析

> 项目地址：https://github.com/ssnangua/ColorTxt
> 当前版本：v3.2.2（package.json）/ v2.8.3（Release）
> 许可证：MPL-2.0
> 分析日期：2026-08-07

---

## 一、项目概述

**ColorTxt（彩读）** 是一款基于 Electron 的**本地 TXT 小说阅读器**，核心特色是**会给内容上色**——通过自定义高亮规则对小说文本进行着色，带来独特的阅读体验。

除内容上色外，还集成了章节识别、简繁互转、划线标注、语音朗读、AI 阅读助手、AI 智能排版、书源找书等丰富功能，是一款功能完备的桌面阅读器。

### 技术栈

| 层面 | 技术选型 |
|------|----------|
| 框架 | Electron 35 + Vue 3.5 + TypeScript 5.8 |
| 构建工具 | electron-vite 3 + Vite 6 |
| 代码编辑器 | Monaco Editor（VS Code 同源编辑器内核） |
| 数据库 | better-sqlite3 + sqlite-vec（向量存储） |
| AI 推理 | @huggingface/transformers（本地嵌入模型） |
| 中文分词 | @node-rs/jieba |
| 简繁转换 | OpenCC |
| 编码检测 | jschardet + iconv-lite |
| 打包发布 | electron-builder + GitHub Actions（三端并行 CI） |

### 语言占比

- TypeScript 58.5%
- Vue 36.0%
- JavaScript 3.1%
- CSS 2.4%

---

## 二、项目架构

### 2.1 整体架构：Electron 三进程模型

```
┌─────────────────────────────────────────────────────┐
│                    Main Process                      │
│   (src/main/)  主进程 — Node.js 环境                 │
│   • 窗口管理 / IPC / 文件系统 / 原生模块              │
│   • AI 引擎 / TTS 合成 / 书源引擎 / 自动更新          │
├─────────────────────────────────────────────────────┤
│                    Preload Layer                     │
│   (src/preload/)  预加载脚本                         │
│   • contextBridge 暴露 window.colorTxt 安全 API      │
├─────────────────────────────────────────────────────┤
│                  Renderer Process                    │
│   (src/renderer/)  渲染进程 — Vue 3 应用              │
│   • UI 组件 / 阅读器视图 / 用户交互                   │
│   • Monaco 编辑器 / 电子书转换 / 状态管理             │
├─────────────────────────────────────────────────────┤
│                    Shared Layer                       │
│   (src/shared/)  主进程与渲染进程共享                 │
│   • 类型定义 / 常量 / IPC 通道声明                    │
└─────────────────────────────────────────────────────┘
```

### 2.2 源码目录结构

```
src/
├── main/                          # 主进程
│   ├── index.ts                   # 入口：协议、窗口、IPC、单实例
│   ├── ipcHandlers.ts             # 业务 IPC（对话框、目录、流式读、字体等）
│   ├── detectTextEncoding.ts      # 文本编码探测（BOM/jschardet/中文ANSI启发式）
│   ├── textConvertOpenCc.ts       # OpenCC 简繁转换封装
│   ├── windowFactory.ts           # BrowserWindow 创建与管理
│   ├── globalShortcuts.ts         # 系统级全局快捷键
│   ├── updater.ts                 # 自动更新
│   ├── ai/                        # AI 功能模块
│   │   ├── infra/                 #   配置、路径、密钥管理
│   │   ├── chat/                  #   对话、Agent、深度思考
│   │   ├── rag/                   #   向量检索（vectorDb、embedding、jieba）
│   │   ├── txt2img/               #   文生图（各后端实现）
│   │   └── tools/                 #   角色卡、思维导图、词云
│   ├── voiceRead/                 # 语音朗读模块
│   │   ├── providerRegistry.ts    #   TTS Provider 统一注册
│   │   └── providers/             #   edge/dashscope/minimax/mimo/winSapi
│   ├── bookSource/                # 书源引擎（Legado 兼容）
│   │   ├── engine/                #   规则解析引擎
│   │   └── store/                 #   书源数据存储
│   └── secretStorage.ts           # API 密钥加密存储
├── preload/
│   └── index.ts                   # contextBridge 暴露安全 API
├── renderer/
│   └── src/
│       ├── App.vue                # 根组件：布局与全局编排
│       ├── components/            # Vue 组件
│       ├── composables/           # 组合式函数（职责拆分）
│       ├── services/              # 业务服务层
│       ├── ebook/                 # 电子书解析与转换
│       └── styles/                # 样式文件
└── shared/                        # 跨进程共享常量与类型
```

### 2.3 IPC 通信机制

主进程与渲染进程通过 IPC（进程间通信）交互，preload 层使用 `contextBridge` 暴露 `window.colorTxt` 全局对象，按功能域划分通道：

| IPC 通道前缀 | 功能域 | 注册文件 |
|-------------|--------|---------|
| `file:*` | 文件读写、目录枚举 | `ipcHandlers.ts` |
| `ai:*` | AI 对话、嵌入、文生图 | `registerAiIpc.ts` |
| `voiceRead:*` | TTS 合成、音色列表 | `registerVoiceReadIpc.ts` |
| `bookSource:*` | 书源搜索、下载、阅读 | `registerBookSourceIpc.ts` |
| `secrets:*` | 密钥读写（加密存储） | `registerSecretsIpc.ts` |
| `text-convert:*` | 简繁/全半角转换 | `registerTextConvertIpc.ts` |

---

## 三、核心功能模块分析

### 3.1 本地文件阅读与编码识别

#### 功能描述
- 支持打开 `.txt` / `.md` 单文件及整个目录（递归读取子目录）
- 支持电子书格式（`.epub` / `.mobi` / `.azw3` / `.fb2` / `.fbz` / `.pdf` / `.chm`），打开时转换为 `.md` 加载
- 流式读取大文件，降低内存压力
- 自动识别 `UTF-8` 和 `ANSI` 编码

#### 实现逻辑

**编码探测**（`src/main/detectTextEncoding.ts`）采用三级策略：
1. **BOM 检测**：检查文件头部的 BOM（Byte Order Mark）标记
2. **jschardet 检测**：基于统计的编码检测库进行识别
3. **中文 ANSI 启发式**：针对中文环境的补充判断，提高 GBK/GB2312 识别准确率

**流式读取**：按块（chunk）读取文件内容，避免一次性加载大文件导致内存溢出。主进程通过 IPC 将数据流式传回渲染进程。

**电子书转换管线**（`src/renderer/src/ebook/`）：
```
源文件 → readBookAsArrayBuffer → convertBookBufferToArtifacts
  → 按格式分派解析器(parseEpub/parseMobi/parsePdf/parseChm/parseFb2)
  → 生成 EbookMarkdownArtifacts（UTF-8 正文 + 插图）
  → writeEbookConversionArtifacts 写出 .md 文件
  → 阅读器加载 .md
```

**缓存与和解机制**：
- 转换后的 `.md` 路径记录在 `file.meta.convertedMdPath`
- 严格缓存命中条件：路径一致 + 源文件 mtime 一致 + 文件存在
- 路径无效时执行「和解查找」：按候选路径优先级（记录路径→输出目录→源目录→默认目录）依次探测

---

### 3.2 内容上色（核心特色）

#### 功能描述
- 使用自定义高亮规则对小说内容进行着色
- 支持自定义高亮词（突出主要角色、关键词语等）
- 可定制阅读区、高亮词、划线标注的配色
- 灵感来源于 VS Code 插件 [vscode-txt-syntax](https://github.com/xshrim/vscode-txt-syntax)

#### 实现逻辑

阅读器基于 **Monaco Editor**（VS Code 同源编辑器内核），内容上色利用 Monaco 的 Tokenizer 机制实现：

1. **语法规则定义**：将自定义高亮规则注册为 Monaco 的语言 token 规则，类似语法高亮
2. **Token 着色**：Monaco 根据 token 类型应用对应的 CSS 颜色（通过主题定义）
3. **自定义高亮词**：用户指定的高亮词作为独立 token 类型，应用专属颜色
4. **主题切换**：内置明亮/暗黑主题，通过 Monaco 主题 API 切换 token 颜色映射

> 注：Monaco Editor 同时承载了阅读、编辑、查找、AI 智能排版 Diff 预览等功能，是应用的核心组件。

---

### 3.3 章节识别

#### 功能描述
- 内置常用章节匹配规则（如「第X章」「Chapter X」等）
- 支持自定义匹配规则
- `.md` 文件按 ATX 标题（`#`）识别，章节列表按标题层级缩进
- 章节标题常驻顶部

#### 实现逻辑

章节检测在 `src/renderer/src/chapter.ts` 中实现：
- **正则匹配**：内置多套章节标题正则表达式，覆盖中英文常见格式
- **自定义规则**：用户可在「章节匹配规则」面板中添加正则
- **Markdown 章节**：识别 ATX 标题（`#` ~ `######`，行首最多 3 个空白），`markdownBlockContext` 在代码块内跳过 `#`
- **物理行扫描**：章节扫描基于物理行，避免展示层「行首缩进」造成误判
- **标题常驻**：章节标题通过 Monaco 的 sticky scroll 能力常驻顶部

---

### 3.4 划线标注与笔记

#### 功能描述
- 选中文本进行划线标注
- 可对划线内容添加笔记
- 交互参考微信读书网页版

#### 实现逻辑

- **选区工具条**（`ReaderSelectionToolbar`）：选中文本后弹出工具条，提供划线、笔记、问 AI 等操作
- **问 AI**：选区工具条「问 AI」→ `App.vue` 的 `onAskAiWithQuote` → 切换到 AI 助手侧栏 → `AiAssistantPanel.prefillQuotedText` 将原文以 blockquote 格式填入输入框
- **数据持久化**：标注与笔记存储在 `colorTxt.ui.settings` 中，按文件路径关联

---

### 3.5 简繁互转与全半角互转

#### 功能描述
- 支持简体中文 ↔ 繁体中文互转
- 支持字母数字全角 ↔ 半角互转

#### 实现逻辑

**简繁转换**（`src/main/textConvertOpenCc.ts`）：
- 基于 **OpenCC**（开放中文转换）库
- 主进程封装：使用 `createRequire` 加载原生模块（因 electron-vite 构建时 `opencc` 被 external）
- IPC 通道 `text-convert:opencc` 暴露给渲染进程
- `electron-rebuild` 重新编译原生模块以适配 Electron ABI
- 打包时 `asarUnpack` 解出原生 `.node` 与词典数据 `.ocd2`

**全半角转换**：在渲染进程通过字符编码映射实现，无需原生模块。

---

### 3.6 书签与阅读进度

#### 功能描述
- 书签功能，书签可添加备注
- 自动记录阅读进度，下次打开继续阅读
- 最近打开记录（默认 20 个文件）

#### 实现逻辑

- **书签**（`useAppBookmarkPins.ts`）：以行号锚点 + 章节名记录，支持弹窗预览、Teleport 菜单
- **阅读进度**：滚动位置自动记录到 `colorTxt.ui.settings`，按文件路径索引
- **最近打开**：维护最近 20 个文件列表，记录打开时间
- **持久化**：所有数据写入 `colorTxt.ui.settings`（通过 `useAppPersistence` 统一管理）

---

### 3.7 语音朗读（TTS）

#### 功能描述
- 支持多种 TTS 引擎：Edge TTS、系统语音、阿里云通义 Qwen3-TTS、MiniMax、小米 MiMo、Windows SAPI5
- 支持单音色或旁白/对白多音色朗读
- AI 说话人识别（自动识别对白说话人、性别、情绪）
- 角色专属音色

#### 实现逻辑

**多引擎 Provider 架构**（`src/main/voiceRead/providerRegistry.ts`）：

```
providerRegistry（统一接口：synthesize / listVoices / healthCheck）
  ├── edgeProvider        → Edge TTS（微软 Neural 语音，MP3）
  ├── systemProvider      → Web Speech API（离线，渲染进程）
  ├── winSapiProvider     → Windows SAPI5（PowerShell System.Speech，WAV）
  ├── dashscopeProvider   → 阿里云通义 Qwen3-TTS（PCM）
  ├── minimaxProvider     → MiniMax TTS（MP3）
  └── mimoProvider        → 小米 MiMo TTS（MP3）
```

**多音色朗读流程**：
```
文本切段（voiceReadLineBuild.ts）
  → 每段解析 voiceId（voiceReadVoiceResolve.ts）
    ├── 单音色：统一使用一个 voiceId
    └── 多音色：旁白/对白分轨
        ├── 按引号样式识别对白（"" / '' / 「」 / 『』）
        ├── AI 识别说话人（attributeVoiceReadSpeakers）
        │   → 输入：当前行 + 角色表 + 邻近参考行
        │   → 输出：说话人姓名、性别、情绪
        │   → 结果缓存（voiceReadSpeakerCache.ts）
        └── 匹配角色专属音色或按性别回退
  → 统一合成入口（voiceReadLinePlayer.ts）
    → 预取 + 排播 + IPC 合成
```

**密钥安全**：各 TTS 引擎的 API 密钥加密存储于 `userData/ai/secrets.v1.json`，与 AI 对话/文生图密钥分槽保存，`localStorage` 与 `config.json` 不含明文。

---

### 3.8 AI 阅读助手

#### 功能描述
- AI 分析剧情、回答小说相关问题
- 支持生成思维导图与词云图
- 基于向量检索（RAG）的上下文增强
- 角色卡生成（AI 检索角色信息 + 文生图生成角色立绘）
- AI 智能排版（处理硬换行、修正标点等）

#### 实现逻辑

**整体架构**（`src/main/ai/`）：

```
ai/
├── infra/           # 基础设施
│   ├── config.ts    # AI 配置管理
│   ├── paths.ts     # 数据缓存路径
│   └── dataFs.ts    # 数据文件系统操作
├── chat/            # 对话模块
│   ├── agentChat.ts # Agent 流式对话（工具调用）
│   ├── agentTools.ts # Agent 工具定义
│   ├── chatThinking.ts # 深度思考参数注入
│   └── requestRetry.ts # 请求重试
├── rag/             # 向量检索
│   ├── vectorDb.ts  # 向量数据库（sqlite-vec）
│   ├── embedding/   # 嵌入模型（本地/远程）
│   │   └── worker   # Worker 线程跑 @huggingface/transformers
│   ├── segmentCache.ts # 分块缓存
│   └── jieba.ts     # 中文分词
├── txt2img/         # 文生图
│   ├── index.ts     # 统一入口
│   ├── openAI.ts    # OpenAI Images
│   ├── minimax.ts   # MiniMax 专用
│   ├── agnes.ts     # Agnes AI 专用
│   └── testConnection.ts # 连接测试
└── tools/           # AI 工具
    ├── characterPortrait.ts # 角色立绘
    ├── mindmap.ts   # 思维导图
    └── wordcloud*.ts # 词云图
```

**对话模型配置**：
- 支持多套独立命名方案（`chatProfiles`，最多 12 套）
- 所有对话走 OpenAI 兼容接口 `POST {baseUrl}/chat/completions`
- 预设 13 家服务商（LM Studio、Ollama、DeepSeek、通义、智谱、Kimi、硅基流动、MiniMax、MiMo、OpenAI、OpenRouter、Gemini 等）
- 深度思考：按 `baseUrl` 识别服务商，注入对应思考开关参数

**RAG 向量检索流程**：
```
建索引：按章节分块 → 调嵌入模型生成向量 → 写入 vector.sqlite（sqlite-vec）
查询：用户提问 → 嵌入查询向量 → sqlite-vec 相似度检索 TopK → 拼接上下文 → AI 对话
```

**嵌入模型双模式**：
- **内置本地模型**：`@huggingface/transformers` 在 Worker 线程运行
  - BGE Small ZH v1.5（~47MB，512 维）— 高质量中文嵌入
  - Multilingual E5 Small（~118MB，384 维）— 多语言支持
- **远程嵌入 API**：OpenAI 兼容 `POST {baseUrl}/embeddings`

**角色卡生成流程**：
```
AI 检索小说中角色信息（RAG）→ 生成角色摘要
  → AI 整理画风 + 角色形象为 prompt（natural / sd 族）
  → 文生图 API 生成角色立绘
  → 立绘存储于 userData/CharacterPortrait/（按书名分子目录）
```

**AI 智能排版**：
- 编辑模式下，通过工具栏一键全文排版或选中文本局部排版
- 排版选项：清理 HTML 残留、修正硬换行、修正标点、统一对话符号、修正乱码、还原屏蔽字、移除水印/广告、压缩空行、行首缩进
- 排版完成后显示 **Diff 预览**，逐一确认后写回
- 根据「最大 Token 数」分段处理长文

---

### 3.9 书源找书（Legado 兼容）

#### 功能描述
- 兼容 [legado-E（阅读Sigma）](https://github.com/Luoyacheng/legado-E) 文本书源 JSON 格式
- 独立找书窗口：书架、搜索、发现、详情、在线阅读、书源管理
- 整书下载

#### 实现逻辑

**架构**（`src/main/bookSource/`）：

```
渲染进程 (FindBookWindow → FindBookPanel)
    │  window.colorTxt.bookSource* (preload → IPC)
    ▼
registerBookSourceIpc.ts
    ├── bookSourceStore     # 书源存储（book-sources.db）
    ├── searchService       # 多源并发搜索
    ├── downloadService     # 整书下载
    ├── checkSourceService  # 书源校验
    └── engine/             # Legado 规则引擎
        ├── webBook.ts      # 网络书籍操作
        ├── analyzeRule.ts  # 规则解析器
        ├── analyzeUrl.ts   # URL 分析器
        ├── jsExtensions.ts # JS 扩展环境
        └── chapterCache.ts # 章节缓存
```

**核心解析链路**：
```
搜索：searchService 多源并发 → searchEvent 流式推送
发现：exploreKinds → webBook.exploreBook（ruleExplore）
详情→目录→正文：
  搜索结果 → searchBookToBook（未完善 Book）
  → getBookInfo（写入真目录地址）
  → getChapterList / getChapterContentWithCache
  → 章节正文缓存于 book_cache/
```

**Legado 规则引擎**：在主进程用 TypeScript 复刻 Legado 的核心解析链路，包括 `AnalyzeRule`（规则解析）、`AnalyzeUrl`（URL 分析）、`jsExtensions`（JS 运行时扩展）等，支持 Legado 书源 JSON 格式的导入和使用。

**持久化位置**：
| 路径 | 说明 |
|------|------|
| `book-sources.db` | 书源 JSON、登录字段、source 级缓存 |
| `book_source_cookies` | 按域名 Cookie |
| `book-source/files/` | importScript / cacheFile 本地脚本 |
| `DownloadedBooks/` | 默认整书导出目录 |
| `book_cache/` | 章节正文离线缓存 |
| `localStorage: colortxt:findBookBookshelf` | 书架（进度、目录缓存） |

---

### 3.10 其他功能

#### 摸鱼快捷键
- 默认 `Ctrl` + `` ` `` 快速隐藏阅读器
- 隐藏窗口、任务栏按钮（Windows）、程序坞图标（macOS）
- 通过 `globalShortcuts.ts` 注册系统级全局快捷键

#### 主题切换
- 内置明亮和暗黑两种主题
- 通过 Monaco 主题 API + CSS 变量实现

#### 多窗口支持
- 可同时打开多个阅读窗口
- `windowFactory.ts` 管理窗口创建

#### 彩读书包（.ctz / .ctzx）
- `.ctz`：明文书包（ZIP 封装）
- `.ctzx`：加密书包（AES-256-GCM + PBKDF2 加密）
- 支持书包批量导入导出

#### WebDAV 同步
- 跨设备同步主窗配置、书包与找书数据
- 远端目录结构：`ColorTxt/Main/`（配置）、`ColorTxt/Books/`（书包）、`ColorTxt/FindBook/`（找书数据）
- 冲突策略：一律覆盖（不比较时间）
- 密码进 secrets vault，不写入 settings

#### 定时滚动
- 自动滚动阅读，可设间隔
- 与语音朗读互斥

---

## 四、数据存储与安全

### 4.1 持久化架构

```
userData/
├── colorTxt.ui.settings          # 主配置（UI 偏好、阅读设置等，JSON）
├── ai/
│   ├── secrets.v1.json           # API 密钥保险库（加密）
│   ├── config.json               # AI 运行时配置（不含聊天正文、不含明文密钥）
│   └── vector.sqlite             # 向量数据库（better-sqlite3 + sqlite-vec）
├── CharacterPortrait/            # 角色立绘缓存（按书名分子目录）
├── ConvertedTxt/                 # 电子书转换输出目录
├── UnpackedBooks/                # 书包解压目录
├── book-sources.db               # 书源数据库
├── book_cache/                   # 章节正文离线缓存
└── DownloadedBooks/              # 整书下载目录
```

### 4.2 API 密钥保险库

所有 API 密钥（AI 对话、文生图、TTS、WebDAV）均加密存储于 `userData/ai/secrets.v1.json`，采用串行队列 + 原子落盘写入，确保并发安全。

| 功能 | 保险库字段 | 说明 |
|------|----------|------|
| AI 对话 | `ai.chatProfileKeys` | 按方案 ID 索引 |
| 文生图 | `ai.txt2imgProfileKeys` | 按方案 ID 索引 |
| 向量嵌入 | `ai.embedding.apiKey` | 全局单一 |
| 语音朗读 | `voiceRead.profileKeys` | 按方案 ID 索引 |
| WebDAV | `webdav.password` | 全局单一 |

> 各功能密钥分槽保存、互不同步，`localStorage` 与 `config.json` 均不含明文。

---

## 五、构建与发布

### 5.1 构建流程

```
npm run build
  → electron-vite build          # 编译三端（main/preload/renderer）
  → electron-rebuild             # 重编译原生模块（better-sqlite3, opencc）
  → prune-pack-deps.mjs          # 裁剪 node_modules（减小包体）
  → electron-builder             # 打包
```

### 5.2 打包产物

| 平台 | 产物格式 | 说明 |
|------|---------|------|
| Windows | NSIS + Portable | 安装包 + 便携版 |
| macOS | DMG | 支持 arm64 + x64 |
| Linux | AppImage | 支持 arm64 + x64 |

### 5.3 CI/CD

- GitHub Actions 三端并行构建（5 个 job：Windows x64、macOS arm64、macOS x64、Linux arm64、Linux x64）
- 推送 `v` + version 的 tag 触发 CI
- 统一 Publish job 汇总上传到同一 GitHub Release
- 通过 `electron-updater` 实现自动更新

---

## 六、关键开源依赖

| 依赖 | 用途 |
|------|------|
| [Monaco Editor](https://microsoft.github.io/monaco-editor/) | 阅读器/编辑器内核（内容上色、查找、编辑） |
| [jschardet](https://github.com/aadsm/jschardet) | 文本编码检测 |
| [iconv-lite](https://github.com/pillarjs/iconv-lite) | 编码解码（ANSI → UTF-8） |
| [OpenCC](https://github.com/byvoid/opencc) | 简繁中文转换 |
| [@node-rs/jieba](https://github.com/napi-rs/node-rs) | 中文分词（词云生成） |
| [@huggingface/transformers](https://github.com/huggingface/transformers.js) | 本地嵌入模型推理 |
| [better-sqlite3](https://github.com/WiseLibs/better-sqlite3) | SQLite 数据库 |
| [sqlite-vec](https://github.com/asg017/sqlite-vec) | SQLite 向量扩展（相似度检索） |
| [pdfjs-dist](https://github.com/mozilla/pdf.js) | PDF 文本提取 |
| [marked](https://github.com/markedjs/marked) | Markdown 解析 |
| [markmap-lib](https://github.com/markmap/markmap) | 思维导图生成 |
| [d3-cloud](https://github.com/holtzy/D3-graph-gallery) | 词云图布局 |
| [font-list](https://github.com/oldj/node-font-list) | 系统字体列表获取 |
| [foliate-js](https://github.com/johnfactotum/foliate-js) | 电子书格式解析参考 |
| [libmspack](https://github.com/kyz/libmspack) | CHM 格式解析（JS 移植版） |

---

## 七、功能架构总览图

```
┌──────────────────────────────────────────────────────────────────┐
│                        ColorTxt（彩读）                           │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│  文件管理  │  阅读核心  │  AI 能力  │  语音朗读  │     书源找书        │
├──────────┼──────────┼──────────┼──────────┼─────────────────────┤
│ 文件列表   │ Monaco编辑器│ AI对话   │ Edge TTS  │ Legado规则引擎      │
│ 分类/排序  │ 内容上色   │ RAG检索  │ 系统语音   │ 书架/搜索/发现       │
│ 树状视图   │ 章节识别   │ 角色卡   │ 通义TTS   │ 在线阅读            │
│ 拖放导入   │ 划线笔记   │ 文生图   │ MiniMax   │ 整书下载            │
│ 电子书转换 │ 书签进度   │ 思维导图 │ MiMo TTS  │ 书源管理            │
│ 书包导入   │ 简繁互转   │ 词云图   │ SAPI5    │                    │
│ WebDAV同步│ 全半角互转 │ 智能排版 │ AI说话人  │                    │
│          │ 主题切换   │ Agent    │ 识别     │                    │
│          │ 查找/搜索   │          │          │                    │
│          │ 编辑模式   │          │          │                    │
│          │ 摸鱼快捷键 │          │          │                    │
├──────────┴──────────┴──────────┴──────────┴─────────────────────┤
│                    Electron + Vue 3 + TypeScript                 │
│              Main Process / Preload / Renderer / Shared           │
├──────────────────────────────────────────────────────────────────┤
│  better-sqlite3 │ sqlite-vec │ transformers.js │ OpenCC │ Monaco  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 八、设计亮点总结

1. **Monaco Editor 作为阅读器内核**：复用 VS Code 的编辑器能力（语法高亮、查找、编辑、Diff 预览），使「内容上色」天然具备语法高亮的基础设施

2. **多 TTS Provider 统一接口**：通过 `providerRegistry` 统一 6 种 TTS 引擎的 `synthesize / listVoices / healthCheck` 接口，新增引擎只需实现 Provider 接口

3. **RAG 向量检索本地化**：内置 `@huggingface/transformers` 在 Worker 线程运行嵌入模型，无需外部 API 即可实现 RAG，兼顾隐私与成本

4. **Legado 书源引擎 TypeScript 复刻**：在主进程完整复刻 Legado 的规则解析链路，实现书源生态兼容

5. **密钥安全架构**：所有 API 密钥加密存储于独立保险库文件，按功能分槽，`localStorage` 与配置文件零明文

6. **多方案配置管理**：对话模型、文生图、语音朗读各自支持最多 12 套独立命名方案，互不绑定

7. **CI/CD 三端并行**：GitHub Actions 5 个 job 并行构建（覆盖 Windows/macOS/Linux × x64/arm64），统一发布

8. **精细的打包裁剪**：`prune-pack-deps.mjs` 在打包前裁剪 `node_modules`（移除 source map、README、非目标平台原生包等），显著减小安装包体积
