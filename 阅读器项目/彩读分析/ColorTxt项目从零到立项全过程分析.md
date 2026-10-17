# ColorTxt（彩读）项目从零到立项全过程分析

> **研究对象**：GitHub ssnangua/ColorTxt — 本地 TXT 小说阅读器  
> **当前版本**：v3.8.11 ｜ Star：1.7k ｜ 协议：MPL-2.0  
> **技术栈**：Electron 35 + Vue 3 + Monaco Editor + TypeScript  
> **分析日期**：2026-09-29  
> **数据来源**：仓库 CHANGELOG.md（v1.1–v3.8.11 全量）、GitHub Releases（24 个版本）、docs/ 五份开发文档、README.md、package.json、源码目录结构、14 份逆向分析报告

---

## 目录

- [一、项目概览与核心定位](#一项目概览与核心定位)
- [二、项目优点（为什么值得学习）](#二项目优点为什么值得学习)
- [三、前期使用的具体工具与技术选型](#三前期使用的具体工具与技术选型)
- [四、积木式窗体拆分组合架构](#四积木式窗体拆分组合架构)
- [五、项目全过程时间线：从需求到立项到成熟](#五项目全过程时间线从需求到立项到成熟)
- [六、前期控制：1.x 时代（打磨阅读器本体）](#六前期控制1x-时代打磨阅读器本体)
- [七、中期控制：2.x 时代（三合一跃迁与架构重构）](#七中期控制2x-时代三合一跃迁与架构重构)
- [八、后期控制：3.x 时代（生态扩展与界面革命）](#八后期控制3x-时代生态扩展与界面革命)
- [九、处理过的核心问题清单](#九处理过的核心问题清单)
- [十、方法论总结：作者的控制哲学](#十方法论总结作者的控制哲学)
- [十一、为效率而生的自动化体系](#十一为效率而生的自动化体系)
- [十二、对比常规项目的优越点：多维度分析](#十二对比常规项目的优越点多维度分析)

---

## 一、项目概览与核心定位

### 1.1 一句话定位

**一款会给内容上色的本地 TXT 小说阅读器** — 将 VS Code 的代码语法高亮体验移植到网文阅读场景。

### 1.2 核心卖点

| 卖点 | 说明 |
|------|------|
| 内容上色 | 使用自定义高亮规则对小说文本着色，对话引号、人物名称、章节标题等自动分色 |
| 多格式支持 | TXT/MD/EPUB/MOBI/AZW3/FB2/FBZ/PDF/CHM，统一转换为 Markdown 中间格式 |
| 多角色朗读 | 7 个 TTS 引擎，AI 识别说话人，角色卡专属音色 |
| AI 阅读助手 | 本地向量库 RAG，分析剧情/生成思维导图/词云/角色卡立绘 |
| 书源找书 | TypeScript 复刻 Legado 书源引擎，兼容数万社区书源 |
| 跨平台 | macOS / Windows / Linux 三平台，CI 五架构并行构建 |

### 1.3 灵感来源

作者从「在 VS Code 里看小说」的体验出发，发现 VS Code 插件 [vscode-txt-syntax](https://github.com/xshrim/vscode-txt-syntax) 的语法高亮可以移植到网文阅读，于是以 Monaco Editor（VS Code 内核）为底层造了彩读这个轮子。

---

## 二、项目优点（为什么值得学习）

### 2.1 极速迭代能力

| 事实 | 数据 |
|------|------|
| 首发 | v1.0.1，2026-04-04（release 正文仅一句"支持空格键跳转到下一屏"） |
| 当前 | v3.8.11，2026-09-08 |
| 周期 | 约 5 个月，24 个 GitHub Release |
| 3.x 高产期 | 7月18日到9月8日连发 14 个版本，平均每 3.7 天一个 release |

这是**全职强度/极高投入的个人开发者**的典型样本。

### 2.2 架构分层清晰

```
┌─────────────────────────────────────────────────┐
│                  Electron 应用                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Main     │  │ Preload  │  │ Renderer (Vue) │ │
│  │ 主进程    │  │ 预加载   │  │ 渲染进程        │ │
│  │ IPC处理   │←→│ context  │←→│ Monaco编辑器    │ │
│  │ 文件I/O  │  │ Bridge   │  │ Vue组件树       │ │
│  │ AI/RAG   │  │          │  │ Composables    │ │
│  │ TTS引擎  │  │          │  │ Stores         │ │
│  │ 书源引擎  │  │          │  │                │ │
│  └──────────┘  └──────────┘  └────────────────┘ │
│  ┌──────────────────────────────────────────┐   │
│  │            Shared (共享层)                │   │
│  │  类型定义、常量、IPC通道、预设配置         │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 2.3 补丁优先于替换

面对 Monaco Editor 的中文排版短板，作者没有换内核，而是建立 **Vite transform 改写 + 运行时补丁** 的双层体系，解决了中文换行、段间距、左右边距、粘性标题、选区渲染等问题。

### 2.4 兼容而不复制的生态策略

| 兼容对象 | 来源 | 做法 |
|----------|------|------|
| Legado 书源 JSON | 安卓阅读器社区数万书源 | TypeScript 复刻规则引擎 |
| CHM 格式 | libmspack (C 库) | 移植为 JavaScript 实现 |
| MOBI/EPUB | foliate-js | 参考实现，集成进自有管线 |
| 词典 | readest | 参考交互 |
| 角色卡 3D | pokemon-cards-css | 引入样式和贴图 |
| AI/朗读基础 | ReadAny | 参考实现 |

README「相关」章节 14 条致谢，全部注明来源与用途。

### 2.5 安全设计逐步收紧

```
密钥存储三阶段演进：
明文 config.json (≤2.2) → 系统钥匙串 (2.3) → 保险库 secrets.v1.json 分槽 (多方案后)
```

- 串行队列 + tmp→rename 原子替换
- 密钥与配置分离，config.json 不含明文 Key
- 多方案后各槽独立：chatProfileKeys / txt2imgProfileKeys / voiceRead.profileKeys / translation.providerKeys

### 2.6 高质量的公开开发闭环

- 24 个 release 全部带结构化中文说明，issue 编号回链
- CHANGELOG.md 与 release 正文同源同步
- 5 个月近百个 issue/PR，其中 #67/#75/#80/#90 为外部贡献者 PR
- issue 直接驱动版本主线（#50 摸鱼、#58 极简、#83 阅读尺）

---

## 三、前期使用的具体工具与技术选型

### 3.1 核心框架

| 工具 | 版本 | 用途 | 选型理由 |
|------|------|------|----------|
| Electron | 35.4.0 | 桌面应用壳 | 跨平台、Node.js 生态、Chromium 渲染 |
| Vue 3 | 3.5.31 | 渲染进程 UI 框架 | 组合式 API、响应式、轻量 |
| Monaco Editor | 0.55.1 | 阅读器核心 | 百万行级性能、行列模型、装饰器体系、Diff 编辑器 |
| TypeScript | 5.8.2 | 全栈类型安全 | 主进程/渲染进程/共享层统一类型 |
| electron-vite | 3.0.0 | 构建工具链 | 统一主进程/preload/渲染三端构建 |

### 3.2 关键依赖（按功能域）

| 功能域 | 依赖 | 用途 |
|--------|------|------|
| 数据库 | better-sqlite3 | 向量库、书源库、分词缓存 |
| 向量检索 | sqlite-vec | SQLite 向量扩展（RAG 检索） |
| AI 嵌入 | @huggingface/transformers | 内置本地嵌入模型（Worker 线程运行） |
| 中文分词 | @node-rs/jieba | 词云生成 |
| 简繁转换 | opencc | 原生模块，展示层转换 |
| 编码探测 | jschardet + iconv-lite | BOM 检测 + 编码启发式 + 解码 |
| Markdown | marked + marked-katex-extension | 电子书中间格式解析 |
| 思维导图 | markmap-lib + markmap-view | AI 生成导图 |
| 词云 | d3-cloud + d3-scale | 词云布局 |
| PDF 解析 | pdfjs-dist | 随包 CMap/wasm |
| ZIP 容器 | jszip | EPUB/书包解析 |
| HTML 解析 | cheerio | 书源规则引擎 |
| JSON 路径 | jsonpath-plus | 书源规则 |
| XPath | @xmldom/xmldom + xpath | 书源规则 |
| HEIC 转码 | heic-convert | 封面格式转换 |
| Cookie | tldts + tough-cookie | 可注册域提取、Cookie Jar |
| WebSocket | ws | TTS 流式合成 |
| 自动更新 | electron-updater | GitHub Releases 发布 |

### 3.3 开发与构建工具链

```
npm run dev          → electron-vite dev    # 本地开发热重载
npm run build        → electron-vite build 
                       → electron-rebuild -f -w better-sqlite3,opencc
                       → scripts/prune-pack-deps.mjs  (裁剪 node_modules)
                       → electron-builder              (打包 DMG/NSIS/AppImage)
npm run typecheck    → vue-tsc --noEmit    # 类型检查
npm run release      → 同 build + --publish always  # 发布到 GitHub
```

### 3.4 CI/CD 配置

GitHub Actions（`.github/workflows/release.yml`），推送版本 tag 后 5 个 job 并行构建：

| 平台 | 架构 | Runner | 产物 |
|------|------|--------|------|
| Windows | x64 | windows-2025-vs2026 | NSIS + Portable |
| macOS | arm64 | macos-latest | DMG |
| macOS | x64 | macos-15-intel（原生 Intel） | DMG |
| Linux | arm64 | ubuntu-24.04-arm | AppImage |
| Linux | x64 | ubuntu-latest | AppImage |

### 3.5 开发辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/prune-pack-deps.mjs` | 打包前裁剪 node_modules（移除非目标平台原生包） |
| `scripts/patch-nested-sharp-stub.mjs` | postinstall：替换 transformers 内嵌 sharp 为占位包 |
| `scripts/patch-monaco-hover-pointer-below.mjs` | postinstall：恢复 Monaco 查找栏 tooltip 向下弹出 |
| `scripts/patch-vite-plugin-monaco-rmdir.mjs` | postinstall：修复 Vite 插件 rmdir 问题 |
| `scripts/patch-xpath-following.mjs` | postinstall：修复 XPath following 轴 |
| `scripts/probe-chm.mjs` | 命令行探测 CHM 解析（开发用） |
| `scripts/llm-extract-top-characters.mjs` | 本地大模型角色提取测试（开发用） |

---

## 四、积木式窗体拆分组合架构

### 4.1 多窗口总览

彩读采用 **Electron 多窗口 + 不同 HTML 入口** 的积木式架构，每个窗口是一个独立「积木块」，可以单独创建、组合使用、互不干扰。

| # | 窗口类型 | 入口 HTML | 渲染根组件 | 创建位置 | 触发方式 |
|---|---------|-----------|-----------|---------|---------|
| 1 | **主阅读窗** | `index.html` | `App.vue`（4452 行） | `windowFactory.ts` | 启动 / 新窗口 / 双击文件 |
| 2 | **找书窗** | `find-book.html` | `FindBookWindow.vue` | 同上（`openFindBook` 参数分流） | F7 / 「更多→找书」/ 桌面快捷方式 |
| 3 | **摸鱼阅读窗** | `stealth-reader.html` | `StealthReaderApp.vue` | `stealthReader.ts` | F9 / 「更多→摸鱼模式」 |
| 4 | **摸鱼设置窗** | `stealth-settings.html` | `StealthSettingsApp.vue` | `stealthSettingsWindow.ts` | 摸鱼窗右键→设置 |
| 5 | **取色器窗** | `eyedropper.html` | 无 Vue（vanilla TS） | `eyedropper.ts` | 配色面板→滴管按钮 |
| 6 | **后台 WebView** | 不显示 | — | `backstageWebView.ts` | 书源登录/校验（主进程内部） |

> **积木式设计要点**：主窗口和找书窗口共用同一套 `BrowserWindow` 工厂（`windowFactory.ts`），通过 `openFindBook` 参数区分加载哪个 HTML；其余窗口各自独立创建。窗口 `closed` 时若无剩余用户窗，则强拆后台 WebView、取色层、摸鱼窗等隐藏窗。

### 4.2 主窗口内部积木式布局

```
┌────────────────── AppHeader 顶部栏 ──────────────────┐
│ 打开文件 │ 编辑/阅读尺/点击模式 │ 主题/字体/格式 │ 更多 │
├────────┬─────────────────────────────────────────────┤
│        │                                             │
│ 侧栏    │             ReaderMain 阅读器               │
│Activity│          （Monaco 编辑器核心）                │
│  栏    │                                             │
│        │                                             │
├────────┴─────────────────────────────────────────────┤
│                AppFooter 底部状态栏                   │
└──────────────────────────────────────────────────────┘
            AppOverlays（弹层面板，浮于其上）
```

侧栏 Activity 栏的积木式标签页（可独立展开/折叠）：

| 图标 | Tab | 展开面板 | 功能 |
|------|-----|---------|------|
| 📚 | files | `FileListPanel` | 文件列表（分类/排序/树形） |
| 📑 | chapters | `ChapterListPanel` | 章节列表（跳转/折叠） |
| 🔍 | search | `SearchPanel` | 全文搜索 |
| 🔖 | bookmarks | `BookmarkListPanel` | 书签管理 |
| 🎨 | highlights | `HighlightListPanel` | 高亮词管理 |
| 📝 | notes | `AnnotationListPanel` | 笔记/标注 |
| 🤖 | aiAssistant | `AiAssistantPanel` | AI 阅读助手 |

### 4.3 窗口间通信机制

```
渲染进程 ←→ Preload (contextBridge) ←→ 主进程 (IPC)
    │                                      │
    └── localStorage 同源共享 ←─────────────┘
         (storage 事件触发多窗同步)
```

- **Preload** 只做一件事：把 IPC 通道包装为 `window.colorTxt.*` API
- `contextIsolation: true`、`nodeIntegration: false`，无直接 Node 暴露
- 多窗口共用同一份 localStorage，写会触发其它窗口的 `storage` 事件
- 多窗口防覆盖：落盘时先读最新快照，仅把本窗有改动的字段盖上去

### 4.4 源码目录的积木式组织

```
src/
├── main/                    # 主进程（系统侧能力）
│   ├── ai/                  # AI 模块
│   │   ├── infra/           #   配置、路径、数据文件系统
│   │   ├── chat/            #   对话、Agent、深度思考、重试
│   │   ├── rag/             #   向量库、分块缓存、嵌入
│   │   ├── txt2img/         #   文生图（多后端路由）
│   │   └── tools/           #   角色立绘、思维导图、词云
│   ├── voiceRead/           # TTS 引擎注册与合成
│   ├── dictionary/          # 词典查词
│   ├── webdav/              # WebDAV 同步
│   ├── bookSource/          # Legado 书源引擎
│   ├── stealthReader.ts     # 摸鱼模式
│   ├── windowFactory.ts     # 窗口创建工厂
│   └── globalShortcuts.ts   # 全局快捷键
├── preload/                 # 预加载（contextBridge）
├── renderer/                # 渲染进程（UI）
│   └── src/
│       ├── components/      # Vue 组件
│       ├── composables/     # 组合式函数（50+ 个）
│       ├── monaco/          # Monaco 阅读器扩展
│       ├── reader/          # 阅读器管线
│       ├── ebook/           # 电子书转 Markdown
│       ├── ai/              # 渲染侧 AI
│       ├── markdown/        # Markdown 章节/内链/图片
│       ├── stores/          # localStorage 状态管理
│       ├── constants/       # UI常量、配色方案
│       └── utils/           # 工具函数
└── shared/                  # 主进程与渲染进程共享（60+ 模块）
```

### 4.5 存储分层积木

```
层级1: localStorage (Chromium 同源隔离)     → UI 偏好、会话快照、文件列表、元数据
层级2: userData 目录 (JSON 文件)            → 窗口位置、AI 配置、密钥保险库、转换缓存
层级3: SQLite 数据库 (better-sqlite3)       → 向量索引、AI 对话、词云分词、书源数据
层级4: 模型缓存目录                          → 内置嵌入模型权重
```

---

## 五、项目全过程时间线：从需求到立项到成熟

### 5.1 全景时间线

```
需求萌芽期                  立项与首发              前期打磨              中期跃迁                后期生态与革命
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
  2026.03 之前              2026.04.04            2026.04                2026.05~06            2026.07~09
  ────────────             ──────────           ──────────           ──────────           ──────────────────
  · 在 VS Code 看小说       · v1.0.1 首发          · 1.1 配色/高亮       · 2.0 语音/AI/编辑     · 3.0 书源找书
  · 发现 vscode-txt-       · 空格键翻屏            · 1.2 电子书格式       · 2.1 加载管线重构     · 3.1 番茄时钟
    syntax 插件            · Electron+Vue         · 1.3 文件管理        · 2.2 .md 支持         · 3.2 书包/WebDAV
  · 确定技术栈              +Monaco                · 1.4 侧栏改版        · 2.3 本地向量模型     · 3.3 marked 迁移
  · 搭建项目骨架            · GitHub 开源           ·                    · 2.4 思维导图/词云   · 3.4 Monaco 补丁里程碑
  · 设计上色规则            · MPL-2.0 协议          ·                    · 2.5 .md 中间格式    · 3.5 树形/高亮AI检索
  · 编写 Monarch 语法       · CHANGELOG 制度        ·                    · 2.6 划线/笔记       · 3.6 词典/翻译
  · 开发流式加载            ·                    ·                    · 2.7 多音色朗读      · 3.7 火山TTS/点击模式
  · 多平台构建配置          ·                    ·                    · 2.8 定时滚动/小米    · 3.8 极简/阅读尺/摸鱼
```

### 5.2 版本演进总表

#### 1.x 时代（2026-04）：打磨"会上色的 TXT 阅读器"本体

| 版本 | 日期 | 核心变化 |
|------|------|----------|
| 1.0.1 | 04-04 | 首发。空格键翻屏 |
| 1.1.1 | 04-08 | 自定义阅读区配色；高亮词与高亮配色；引号/括号跨行匹配；便携版/AppImage |
| 1.2.0 | 04-13 | 电子书格式支持（epub/mobi/azw3/fb2/fbz/pdf/chm），转换为 .txt；包体瘦身 |
| 1.3.1 | 04-19 | 文件分类、排序；拖放逻辑优化；高亮词点击即查找 |
| 1.4.2 | 04-29 | 侧栏改版为类 VS Code 图标+面板；搜索标签页；高亮词标签页；平滑滚动 |

#### 2.x 时代（2026-05~06）：语音朗读 + AI + 编辑模式三合一跃迁

| 版本 | 日期 | 核心变化 |
|------|------|----------|
| 2.0 | 约5月中 | 语音朗读（Edge TTS/系统/阿里通义）；编辑模式；AI 阅读助手；角色卡；Monaco 中文化 |
| 2.1 | CHANGELOG | 流式加载→文本格式化→章节生成逻辑重构；不再重载文件 |
| 2.2.1 | 05-20 | 支持 Markdown；编辑模式小地图；ragContext 优先取章节原文 |
| 2.3.0 | 05-26 | 对话/向量模型支持主流服务商；内置本地向量模型；API 密钥改钥匙串 |
| 2.4.2 | 05-29 | 思维导图 + 词云图；角色卡文生图；3D 倾斜闪卡纹理 |
| 2.5.1 | 06-12 | 电子书转换从 .txt 迁移到 Markdown；AI 智能排版（Diff 预览）；CI 构建 |
| 2.6.5 | 06-15 | 划线标注与记笔记；简繁互转；禁用 Monaco 大文件优化 |
| 2.7.0 | 06-18 | 语音朗读多音色；AI 识别说话人；MiniMax 接入 |
| 2.8.3 | 06-24 | 定时滚动；小米 MiMo；粘性章节标题开关；窗口最小尺寸 |

#### 3.x 时代（2026-07~09）：书源引擎 + 找书生态 + 界面形态革命

| 版本 | 日期 | 核心变化 |
|------|------|----------|
| 3.0.8 | 07-18 | 找书（Legado 书源引擎 JS 复刻）；文本替换；章节导航工具栏 |
| 3.1.10 | 07-28 | 番茄时钟；书架分类；书源编辑体验优化 |
| 3.2.1/.2 | 07-30/08-01 | 彩读书包 .ctz/.ctzx（AES-256-GCM）；WebDAV 同步；Windows SAPI5 |
| 3.3.0 | 08-02 | 原生右键菜单；Markdown 解析改走 marked；书源 TLS 修复 |
| 3.4.3 | 08-05 | Monaco 补丁里程碑：中文换行优化、段间距、左右边距；NSIS 覆盖安装 |
| 3.5.4 | 08-08 | 文件列表树形模式；高亮词 AI 检索；单项多词 |
| 3.6.3/.6 | 08-12/13 | 词典（StarDict/MDict/DICT/Slob/BGL）；翻译（9+ 服务商） |
| 3.7.2 | 08-28 | 火山引擎 TTS 2.0（444 音色）；朗读过滤；点击模式；PDF 三大修复 |
| 3.8.x | 09-02~09-08 | 极简视图（F10）；阅读尺（ADHD）；摸鱼模式；配色方案与背景图；Edge TTS 标点停顿 |

---

## 六、前期控制：1.x 时代（打磨阅读器本体）

### 6.1 控制目标

在一个月内（2026-04）交付一个**可用的、会上色的 TXT 阅读器**，建立项目骨架和核心体验。

### 6.2 具体控制措施

| 控制维度 | 措施 | 证据 |
|----------|------|------|
| 范围控制 | 首发仅"空格键翻屏"一句说明，不堆功能 | v1.0.1 release 正文 |
| 质量控制 | 便携版/AppImage/自定义安装路径一并发布 | v1.1.1 |
| 包体控制 | 剔除语言包、启用 asar | v1.2.0 |
| 架构控制 | 1.0 即采用 Monaco，不自己造渲染引擎 | README 框架声明 |
| 体验控制 | 侧栏改版为类 VS Code 风格，建立用户认知锚点 | v1.4.2 |
| 功能增量 | 每个版本聚焦 2-4 个功能点，不贪多 | 版本间隔 5-11 天 |

### 6.3 前期处理的核心问题

| 问题 | 解决方案 | 版本 |
|------|----------|------|
| TXT 文件编码不一致 | BOM 检测 + jschardet + ANSI 启发式补判 + iconv-lite 解码 | 1.0 |
| 网文单文件数百万字 | 流式按行切分（256KB 分块），不一次性加载 | 1.0 |
| 章节自动识别不准 | 内置常用正则 + "章节最少字数"设置（默认 100） | 1.4 |
| 电子书格式多样 | 统一转换为 .txt 中间格式（v1.2 初版方案） | 1.2 |
| 包体过大 | 剔除 Electron 语言包，启用 asar | 1.2 |

---

## 七、中期控制：2.x 时代（三合一跃迁与架构重构）

### 7.1 控制目标

在两个月内（2026-05~06）完成从"纯阅读器"到"阅读+朗读+AI+编辑"四合一平台的跃迁，同时重构底层管线以支撑后续扩展。

### 7.2 关键架构决策与重构

#### 7.2.1 加载管线重构（v2.1）— 最重要的中期架构决策

**问题**：初版加载流程"流式读取 → 边读边统计字数/匹配章节"，大文件打开慢，改格式化选项要重新加载文件。

**重构方案**：

```
重构前：                          重构后：
文件 → 流式读 → 边读边统计/匹配     文件 → 流式读 → 加载完成后统一处理
                                   ↓
每次改格式化 → 重新加载文件         改格式化 → 基于内存物理文本操作（不重载）
```

**沉淀**：这套"物理行常驻 + 展示层映射 + 装饰视口化"的管线，后来直接支撑了 .md 内链/插图、找书阅读器复用、阅读尺锚点。

#### 7.2.2 电子书中间格式迁移（v2.5）

| 阶段 | 方案 | 问题 |
|------|------|------|
| v1.2 初版 | 转换为 .txt，用 `<<A>>`/`<<ID>>`/`<<IMG>>` 自造标记 | 无法表达层级/图片/链接 |
| v2.5 第一次推翻 | 迁移到 Markdown（ATX 标题、内链/注脚、外链） | 私有标记被标准格式替代 |
| v3.3 第二次推翻 | Markdown 解析从手写正则迁移到 marked | 私有解析器边角问题无穷 |

> 作者两次都在私有方案扩散前完成了切换，并诚实标注"请重新转换"。

#### 7.2.3 密钥安全三阶段演进

```
明文 config.json (≤2.2) → 系统钥匙串 (2.3) → 保险库 secrets.v1.json 分槽 (多方案后)
                                                    │
                                          串行队列 + tmp→rename 原子替换
                                          各槽独立：chat/txt2img/voiceRead/translation
```

#### 7.2.4 构建方式迁移（v2.5）

从本地构建迁移到 CI 构建，支持输出 macOS(x64)/Linux(x64) 包。

### 7.3 中期处理的核心问题

| 问题域 | 问题 | 解决方案 | 版本 |
|--------|------|----------|------|
| Monaco 排版 | 大文件优化与软换行/粘性标题冲突 | 禁用 Monaco 自带大文件优化 | 2.6 |
| AI RAG | 整本小说发给 AI 成本太高 | 本地向量库（SQLite + sqlite-vec），内置嵌入模型 | 2.3 |
| AI 上下文 | ragContext 质量问题 | 优先取章节原文（≤1万字完整，>1万字压缩提要） | 2.2 |
| 密钥安全 | 明文写入配置文件 | 改为系统钥匙串加密保存 | 2.3 |
| TTS | 网文对话密度高，适合多角色 | 多音色（旁白/对白分轨）、AI 识别说话人 | 2.7 |
| 视觉体验 | 长篇阅读视觉疲劳 | 平滑滚动开关、粘性标题开关 | 2.8 |
| 文本质量 | 盗版网文有硬换行/乱码/水印 | AI 智能排版（9 项排版选项，Diff 预览） | 2.5 |

---

## 八、后期控制：3.x 时代（生态扩展与界面革命）

### 8.1 控制目标

在三个月内（2026-07~09）完成从"阅读器"到"阅读生态平台"的转变，同时探索注意力经济方向的界面形态创新。

### 8.2 后期三大子系统建设

#### 8.2.1 书源找书引擎（v3.0）— 项目最大子系统

**工程规模**：
- 主进程 `bookSource/engine/` 完整复刻 AnalyzeRule / AnalyzeUrl / AnalyzeByJSoup / AnalyzeByJSonPath / AnalyzeByRegex 五大解析器
- jsExtensions：java.* 全套 API 桩
- 独立找书窗口：书架/找书/发现 + WebDAV 同步 + 章节缓存 + 封面代理

**最大障碍 — JS 引擎差异**：

| 差异点 | Legado (Rhino/JVM) | 彩读 (Node AsyncFunction) | 修补方案 |
|--------|---------------------|---------------------------|----------|
| 末尾表达式 | 自动返回 | 需 return | `ensureLegadoScriptReturn` 补 return |
| forEach async | 同步阻塞 | 异步不等待 | 改写为串行 |
| 形参与 let 同名 | 允许 | SyntaxError | 预处理改名 |
| `let (x=expr) body` | 支持 | 不支持 | 表达式改写 |
| 正则字面量 | 宽松 | 严格 | 修复 `\\({n,m}` |

#### 8.2.2 词典翻译矩阵（v3.6）

- **词典**：StarDict / MDict / DICT / Slob / BGL + 网络词典（Wiktionary/Wikipedia）
- **翻译**：AI + 微软/Google/Yandex/DeepL/百度/有道/腾讯/火山/阿里

#### 8.2.3 界面形态四部曲（v3.8）

| 形态 | 面向 | 入口 | 设计意图 |
|------|------|------|----------|
| 全屏阅读 | 沉浸式 | 早期 | 禅模式，两侧留白可调 |
| 极简视图 | 专注阅读 | F10 | 阅读区撑满窗口，边缘唤起面板 |
| 阅读尺 | ADHD 人群 | 工具栏 | 聚焦行+淡化其余，翻页按聚焦行数移动 |
| 摸鱼模式 | 隐蔽阅读 | F9 | 无边框透明置顶窗，全局快捷键操作 |

### 8.3 后期处理的核心问题

#### 8.3.1 Monaco 补丁里程碑（v3.4）— 标注"重要体验优化版本，建议更新"

| 补丁 | 实现方式 | 解决的问题 |
|------|----------|------------|
| 中文换行优化 | 全角标点估算 + 汉字校准字宽 | 行尾缺字与溢出 |
| 段间距 | Vite transform 改写 Monaco LinesLayout | 物理行后增加常数像素空隙 |
| 左右边距 | 收窄编辑器区域形成留白 | 阅读区左右留白可调（0~160px） |

#### 8.3.2 摸鱼模式的 bug 修复马拉松（v3.8.1~3.8.11）

11 天连发 11 个小版本，是全项目最密集的一次功能救火：

| 版本 | 日期 | 修复 |
|------|------|------|
| 3.8.5 | 09-04 | 摸鱼模式支持定时滚动 |
| 3.8.9 | 09-08 | Windows 最小窗高用 setShape 绕过；右键菜单与翻页冲突 |
| 3.8.10 | 09-08 | 任务栏 Z 序大战：指针进入任务栏时重申置顶 + 周期兜底 |
| 3.8.11 | 09-09 | 拖动窗口越拖越大：钉死逻辑宽高 |

#### 8.3.3 Edge TTS 标点停顿攻坚（v3.8.9~3.8.11）

**问题**：Edge 端点不支持 SSML `<break>`，带上后服务端直接断连。

**三层解决方案**：
1. **定位**：收集 audio.metadata 中的 WordBoundary 事件，映射全角标点为待替换区间
2. **传输**：区间随 mp3 一并返回，与停顿时长解耦
3. **播放**：decodeAudioData 后把区间替换为干净静音（2ms 淡入淡出）

#### 8.3.4 平台坑清单化

| 平台 | 问题 | 解决方案 | 版本 |
|------|------|----------|------|
| macOS Intel | 交叉编译缺 @node-rs/jieba-darwin-x64 | 改用 macos-15-intel 原生构建 | 3.0 |
| Linux | AppImage 缺 FUSE2 (libfuse.so.2) | 改为静态 AppImage runtime | 3.0 |
| Windows | NSIS 清空安装丢数据 | 改为覆盖安装 | 3.4 |
| Windows | 任务栏 Z 序压摸鱼窗 | 重申置顶 + 周期兜底 | 3.8.11 |
| Windows | 系统最小窗高限制 | setShape 绕过 | 3.8.9 |
| Linux | Wayland 全局快捷键失效 | README 已知问题，暂无解 | — |
| 书源 | Node/undici TLS 被站点重置 | 改用 Chromium session.fetch | 3.3 |

---

## 九、处理过的核心问题清单

### 9.1 被推翻/重写的方案汇总

| # | 推翻内容 | 时点 | 动机 |
|---|----------|------|------|
| 1 | 电子书中间格式 .txt → Markdown | v2.5 | 自造标记无法表达层级/图片/链接 |
| 2 | Markdown 解析：手写正则 → marked | v3.3 | 私有解析器边角问题无穷 |
| 3 | 标题匹配：包含匹配 → 仅精确匹配 | v3.3 | 误升级正文行为标题 |
| 4 | Monaco 大文件优化：启用 → 禁用 | v2.6 | 与软换行/粘性标题冲突 |
| 5 | Monaco 等宽渲染优化：关闭 | v3.7 | 字体宽度估算与实际字形不符 |
| 6 | Monaco 圆角选区抠图：关闭 | v3.8 | 透明底色下抠图露馅 |
| 7 | API 密钥：明文 → 钥匙串 → 保险库分槽 | v2.3→ | 安全 + 多方案架构 |
| 8 | 加载管线重构 | v2.1 | 大文件体验 |
| 9 | 网络：Node/undici → Chromium session.fetch | v3.3 | TLS 指纹被识别拦截 |
| 10 | 构建：本地 → CI | v2.5 | 跨平台打包 |
| 11 | macOS Intel：交叉编译 → 原生构建 | v3.0 | 原生模块架构错配 |
| 12 | NSIS：清空安装 → 覆盖安装 | v3.4 | 升级丢数据 |
| 13 | 排序交互：上移下移按钮 → 拖动排序 | v2.4 | 交互效率（作者自评"呆"） |

### 9.2 Issue/PR 驱动的开发闭环

5 个月近百个 issue/PR，issue 号到 #91，其中 #67/#75/#80/#90 为外部贡献者 PR。

| 典型 Issue | 主题 | 落地版本 | 说明 |
|-----------|------|---------|------|
| #4 | 点击模式 | 3.7 | 左键下屏右键上屏 |
| #5 | WebDAV 同步 | 3.2 | 主窗+找书三线同步 |
| #19 | 配色方案 | 2.8/3.8 | 选项开关 → 内置8套+背景图 |
| #50 | 摸鱼模式 | 3.8 | 无边框透明置顶窗 |
| #53 | 段间距 | 3.4 | Monaco LinesLayout 补丁 |
| #58 | 极简视图 | 3.8 | F10 边缘唤起 |
| #67 (PR) | 火山引擎 TTS | 3.7 | 豆包2.0，444音色 |
| #83 | 阅读尺（ADHD） | 3.8 | 聚焦行+淡化 |
| #90 (PR) | Edge TTS 标点停顿 | 3.8.11 | WordBoundary 插静音 |
| #91 | 任务栏压摸鱼窗口 | 3.8.11 | 重申置顶+周期兜底 |

### 9.3 新功能带来的连锁问题

| 新功能 | 引发的连锁修复 | 时间跨度 |
|--------|---------------|----------|
| 背景图（v3.8） | 粘性标题阴影切开背景图 → 去阴影；圆角选区抠图露底 → 关圆角；堆叠粘性章节标题修复；背景图路径修复 | 两周内 4 个 fix |
| 摸鱼模式（v3.8） | 定时滚动支持；最小窗高 setShape；任务栏 Z 序大战；拖动越拖越大 | 11 天 11 个版本 |

---

## 十、方法论总结：作者的控制哲学

### 10.1 发布即公告

24 个 release 全部带结构化中文说明（新功能/改进/修复），issue 编号直接回链。CHANGELOG.md 与 release 正文同源同步——每个版本前都有 "Update CHANGELOG.md" 提交。

### 10.2 小步快跑

| 节奏 | 数据 |
|------|------|
| 1.x | 每隔 5-11 天一个版本，每版 2-4 个功能点 |
| 2.x | 每隔 3-7 天一个版本，每版聚焦一个子系统 |
| 3.x 高产期 | 每 3.7 天一个 release |

### 10.3 补丁优先于替换

面对 Monaco 的中文排版短板，建立 **Vite transform 改写 + 运行时补丁** 的双层体系，不换内核。上游无解问题（#5311）以 WARNING 明示，不掩盖。

### 10.4 三次"降级即升级"

| 关闭的特性 | 动机 |
|-----------|------|
| 禁用 Monaco 大文件优化 | 为软换行/粘性标题让路 |
| 关闭等宽渲染优化 | 字体保真（京華老宋体英文选区） |
| 关闭圆角选区抠图 | 透明背景下不露馅 |

### 10.5 格式策略两次收敛

电子书中间格式从私有标记收敛到标准 Markdown，Markdown 解析从手写正则收敛到 marked。**"私有方案活得越久，迁移成本越高"**——作者两次都在私有方案扩散前完成了切换。

### 10.6 兼容而不复制

不造新格式，直接兼容已有生态（Legado 书源 JSON、libmspack CHM、foliate-js MOBI），但用 TypeScript 重新实现，不引入 Java/Rhino 依赖。

### 10.7 安全边界逐步收紧

密钥从明文 → 钥匙串 → 保险库分槽 + 原子写 + localStorage 剥离，每一步都带旧数据自动迁移与废弃 slot 清除。

### 10.8 平台坑清单化

跨平台桌面应用的系统级问题（macOS Intel 交叉编译、Linux FUSE2、Windows 任务栏 Z 序/最小窗高、Wayland 全局快捷键）全部进入版本说明与文档，不掩盖。

### 10.9 issue 驱动的公开开发闭环

大量 issue 直接成为版本主线（#50 摸鱼、#58 极简、#83 阅读尺），说明作者按需求池排期，release 说明逐条回链。

### 10.10 诚实的风险声明

- "做不到 100% 复刻……目前算是测试版"（v3.0 书源）
- "请自行测试"（v2.5 AI 智能排版）
- "有一定误还原风险，请自行检查"（乱码还原）
- "这个问题连 VSCode 都没能完美解决"（README 高级换行策略）

---

## 十一、为效率而生的自动化体系

彩读作者在 5 个月内完成 24 个版本、跨 3 平台 5 架构的交付，背后是一整套**从开发到发布全链路自动化**的工程基础设施。以下按「项目拆积木 → 调试效率 → 打包上传自动化」三条线详细拆解。

### 11.1 项目拆积木的自动化：postinstall 补丁体系

#### 11.1.1 核心机制

作者在 `package.json` 的 `postinstall` 钩子中编排了一条**自动化补丁流水线**——每次 `npm install` 之后自动执行 4 个补丁脚本，无需人工干预：

```json
{
  "scripts": {
    "postinstall": "electron-rebuild -f -w better-sqlite3,opencc && node scripts/patch-nested-sharp-stub.mjs && node scripts/patch-monaco-hover-pointer-below.mjs && node scripts/patch-vite-plugin-monaco-rmdir.mjs && node scripts/patch-xpath-following.mjs"
  }
}
```

这条流水线的含义：**安装完依赖后，先重建原生模块，再依次修补 4 个第三方库的源码**，使得项目骨架可以"搭积木"一样拼装第三方库，同时按需改造其行为。

#### 11.1.2 每个补丁的具体作用

| # | 脚本 | 修补目标 | 解决的问题 | 实现方式 |
|---|------|---------|------------|----------|
| 1 | `electron-rebuild -f -w better-sqlite3,opencc` | 原生模块 | Electron 的 ABI 与 Node.js 不同，原生 `.node` 需按 Electron 版本重编译 | 调用 `@electron/rebuild` 强制重建 |
| 2 | `patch-nested-sharp-stub.mjs` | `@huggingface/transformers` 内嵌的 `sharp` | transformers 自带完整 sharp（含原生 image 处理），彩读不需要图像推理；打包时 `package.json` 已用 `file:scripts/sharp-pack-stub` 覆盖顶层 sharp，但**嵌套的 sharp 不受 overrides 控制** | 检测 `node_modules/@huggingface/transformers/node_modules/sharp`，如果版本号不是 `0.0.0-colortxt-stub` 则删除并用 stub 目录替换 |
| 3 | `patch-monaco-hover-pointer-below.mjs` | Monaco 的 `hoverWidget.js` 和 `inputBox.js` | Monaco 0.55+ 移除了 HoverStyle.Pointer 默认 BELOW，查找栏 tooltip 在上方弹出被顶栏裁切 | 向 `hoverWidget.js` 注入 `options.position.hoverPosition ??= 2`（BELOW）+ `forcePosition`；向 `inputBox.js` 将 `setupDelayedHoverAtMouse` 改为 `setupDelayedHover` + Pointer 样式 |
| 4 | `patch-vite-plugin-monaco-rmdir.mjs` | `vite-plugin-monaco-editor` 的 `workerMiddleware.js` | 该插件仍用 `fs.rmdirSync({recursive:true})`，Node 22+ 报 DEP0147 废弃警告 | 替换为 `fs.rmSync({recursive:true,force:true})` |
| 5 | `patch-xpath-following.mjs` | `xpath@0.0.34` 的 `xpath.js` | `following::` 轴在有子节点时误从 firstChild 起步，把后代当 following，永远扫不到 nextSibling——书源规则 `//div[@id='list']/dl/dt[2]/following::dd` 取空 | 将 FOLLOWING case 的起点从 `firstChild` 改为 `nextSibling` |

#### 11.1.3 补丁脚本的共同设计模式

每个补丁脚本都遵循同一套**幂等+安全**的设计模式：

```
1. 检查目标文件是否存在 → 不存在则 warn + exit(0)，不阻断流程
2. 检查是否已打过补丁（marker 注释） → 已打则 exit(0)
3. 精确匹配 needle（原始代码段） → 匹配失败则 warn"结构已变" + exit(0)
4. 字符串替换写入 → 打印成功日志
```

**幂等性**：每个补丁都注入 `colortxt-xxx` 标记注释，重复执行自动跳过。

**安全降级**：如果第三方库升级后代码结构变了，补丁不会崩溃，只会打印 warn 并跳过——开发者能从日志发现需要更新补丁。

#### 11.1.4 electron.vite.config.ts 中的运行时积木

除了 postinstall 补丁，`electron.vite.config.ts` 中还有 4 个 **Vite 插件级**的积木改造，在构建时（而非安装时）自动改写 Monaco 源码：

| 插件 | enforce | 作用 | 改写方式 |
|------|---------|------|----------|
| `monacoCjkWrapStringsPlugin` | pre | 拦截 Monaco `strings.js` 的 import，重定向到自写的 `cjkWrapStrings.ts` | `resolveId` 钩子拦截 |
| `monacoCjkWrapOptimizePlugin` | pre | 在 `monospaceLineBreaksComputer.js` 中注入全角标点判断；在 `fontMeasurements.js` 中将测宽样字从 `ｍ`（U+FF4D）改为 `汉`（U+6C49） | `transform` 钩子代码替换 |
| `monacoLineSpacingPlugin` | pre | 改写 Monaco `LinesLayout.js`（4 处）和 `viewModelImpl.js`（1 处），注入段间距计算 | `transform` 钩子精确字符串替换 |
| `pdfjsAssetsPlugin` | normal | 开发态把 `/pdfjs/*` 映射到 `node_modules/pdfjs-dist`；生产构建拷到 `dist/renderer/pdfjs/` | `configureServer` + `writeBundle` |

> **关键设计**：`optimizeDeps.exclude: ["monaco-editor"]` 确保 esbuild 预构建不会绕过这些 transform——否则开发模式下补丁会失效（生产 Rollup 构建不受影响）。

### 11.2 调试功能的极致效率

#### 11.2.1 开发命令设计

```json
{
  "scripts": {
    "dev": "electron-vite dev",
    "dev:find": "electron-vite dev -- --find-book",
    "preview": "electron-vite preview",
    "typecheck": "vue-tsc --noEmit",
    "test": "node --experimental-strip-types --test src/shared/voiceReadPunctuationPauses.test.ts"
  }
}
```

| 命令 | 用途 | 效率设计 |
|------|------|----------|
| `npm run dev` | 全功能开发热重载 | electron-vite 统一三端（主/preload/渲染）HMR |
| `npm run dev:find` | **只开找书窗口** | 传入 `--find-book` 参数直接跳到找书窗（默认书架页），跳过主窗加载——调试书源时不用等主窗渲染 |
| `npm run preview` | 预览构建结果 | 不打包，直接跑 `dist/` 产物，验证构建是否正确 |
| `npm run typecheck` | TypeScript 类型检查 | `vue-tsc --noEmit`，不产出文件，只检查 |
| `npm run test` | 单元测试 | Node 原生 `--test` runner + `--experimental-strip-types`（直接跑 .ts 无需预编译） |

#### 11.2.2 开发专用探测脚本

作者还写了两个**不参与打包**的开发调试脚本，用于在命令行验证特定功能：

| 脚本 | 用途 | 使用方式 |
|------|------|----------|
| `scripts/probe-chm.mjs` (+ `probe-chm.ts`) | 命令行探测 CHM 解析 | 直接传入 .chm 文件路径，输出解析结果，验证 CHM 引擎正确性 |
| `scripts/llm-extract-top-characters.mjs` | 本地大模型角色提取测试 | 验证"用 LLM 从小说文本中提取主要角色"这一 AI 功能的可行性 |

#### 11.2.3 CI 中的包体大小自动校验

CI 流水线中内置了**包体回归检测**，防止裁剪退化：

```yaml
# release.yml - Linux x64 专属校验
- name: Log node_modules size after prune
  if: matrix.name == 'Linux-x64'
  run: |
    du -sh node_modules
    find node_modules -maxdepth 1 -name 'sqlite-vec-*' | xargs du -sh 2>/dev/null || true
    du -sh node_modules/onnxruntime-node/bin/napi-v3/* 2>/dev/null || true

- name: Verify Linux x64 package size
  if: matrix.name == 'Linux-x64'
  shell: bash
  run: |
    appimage=(release/*.AppImage)
    size=$(stat -c%s "${appimage[0]}")
    if [ "$size" -gt 200000000 ]; then
      echo "Linux x64 AppImage exceeds 200 MB — prune or pack regression"
      exit 1
    fi
```

如果 AppImage 超过 200MB，CI 直接 **fail**——防止裁剪脚本退化或意外引入大依赖。

#### 11.2.4 CI 环境变量优化

```yaml
env:
  # 未配置签名证书时跳过自动签名探测
  CSC_IDENTITY_AUTO_DISCOVERY: false
  # Linux x64 上 onnxruntime-node postinstall 会拉取 CUDA EP（约 300MB+）
  ONNXRUNTIME_NODE_INSTALL_CUDA: skip
```

- `CSC_IDENTITY_AUTO_DISCOVERY=false`：没有 Apple 开发者证书时不尝试签名，避免 CI 失败
- `ONNXRUNTIME_NODE_INSTALL_CUDA=skip`：内置向量只用 CPU，跳过 300MB+ CUDA EP 下载——大幅加速 CI

#### 11.2.5 缓存优化

```yaml
- name: Cache Electron downloads
  uses: actions/cache@v5
  with:
    path: |
      ~/.cache/electron
      ~/.cache/electron-builder
    key: electron-${{ runner.os }}-${{ matrix.arch }}-${{ hashFiles('package-lock.json') }}
    restore-keys: |
      electron-${{ runner.os }}-${{ matrix.arch }}-
      electron-${{ runner.os }}-
```

按 `runner.os + arch + package-lock.json hash` 缓存 Electron 二进制和 electron-builder 工具，避免每次 CI 重新下载。

### 11.3 打包上传的自动化

#### 11.3.1 打包流水线全流程

```
npm run build / npm run release
    │
    ├─ Step 1: electron-vite build
    │          编译主进程 (dist/main/)
    │          编译 preload (dist/preload/)
    │          编译渲染进程 (dist/renderer/)
    │          编译 AI embedding worker (dist/main/ai/rag/embedding/worker.js)
    │          运行 Vite 插件：Monaco 补丁、pdfjs 资源拷贝、HTML 占位替换
    │
    ├─ Step 2: electron-rebuild -f -w better-sqlite3,opencc
    │          按目标 Electron 版本重编译原生 .node 文件
    │          CI 中可指定 --arch 目标架构
    │
    ├─ Step 3: node scripts/prune-pack-deps.mjs [--platform] [--arch]
    │          裁剪 node_modules（详见 11.3.2）
    │          交叉编译时补装目标架构的 optional 原生包
    │          macOS 上用 lipo 校验 Mach-O 架构
    │
    ├─ Step 4: electron-builder
    │          beforePack 钩子 → electron-before-pack.mjs → 再次执行 prune
    │          onNodeModuleFile 钩子 → electron-on-node-module-file.mjs → 排除非目标平台文件
    │          打包为 NSIS/DMG/AppImage
    │          asar 打包 + asarUnpack 解包原生模块
    │
    └─ Step 5 (release only): electron-builder --publish always
               上传到 GitHub Releases
```

#### 11.3.2 打包前 node_modules 裁剪（prune-pack-deps.mjs）

这是打包自动化中最核心的效率脚本，**直接减少安装包体积数十 MB**。

**裁剪分类**：

| 类别 | 被裁剪的内容 | 理由 |
|------|-------------|------|
| 整包移除 | `onnxruntime-web` | Web/WASM 推理，内置向量不用 |
| 整包移除 | 完整 `sharp` + `@img/*` | 不做图像推理；用 `sharp-pack-stub` 占位 |
| 整包移除 | `protobufjs`、`flatbuffers`、`long`、`platform` 等 | 删 onnxruntime-web 后的孤儿依赖 |
| 整包移除 | `prebuild-install`、`napi-build-utils`、`node-abi` 等 | 仅安装阶段使用 |
| 按平台移除 | 非目标平台的 `sqlite-vec-*`、`@node-rs/jieba-*` | 原生包按平台分发，只留当前平台 |
| 按路径裁剪 | 各包移除 `src/`、`deps/`、`*.map`、README 等 | 非运行时文件 |

**交叉编译补装**：`npm ci` 只安装构建机架构的原生包。例如 Apple Silicon 上打 macOS Intel 包时，`prune-pack-deps` 会用 `npm pack` 补装 `@node-rs/jieba-darwin-x64` / `sqlite-vec-darwin-x64`，并用 `lipo -archs` 校验 `.node` 文件的 Mach-O 架构。

**electron-builder 阶段的双层裁剪**：

| 钩子 | 脚本 | 作用 |
|------|------|------|
| `beforePack` | `electron-before-pack.mjs` | 在 electron-builder 收集依赖前执行 prune，写入 `packPlat`/`packArch` 上下文 |
| `onNodeModuleFile` | `electron-on-node-module-file.mjs` | electron-builder 逐文件收集时，通过 `shouldIncludeNodeModuleFile()` 排除非目标平台的 `.node` 文件 |

`shouldIncludeNodeModuleFile()` 的排除规则（按文件路径匹配）：

```
排除 onnxruntime-web 和 @img/* 的所有文件
排除非目标平台的 sqlite-vec-* 包
排除非目标平台的 @node-rs/jieba-* 包
排除非目标平台/架构的 onnxruntime-node/bin/napi-v3/* 二进制
排除 @huggingface/transformers/dist/ 下非 .node.mjs 的文件
排除 opencc 的 deps/src/data/scripts/bin/binding.gyp + 非目标 prebuilds
```

#### 11.3.3 CI 自动发布流程（release.yml）

**触发方式**：

```yaml
on:
  push:
    tags:
      - "v*"          # 推送 v 开头的 tag 自动触发
  workflow_dispatch:   # 也可在 GitHub Actions 页面手动触发（补跑）
```

**完整 CI 流程**（2 个 Job）：

```
Job 1: build（5 个并行矩阵）
┌──────────────────────────────────────────────────────────────┐
│  checkout → setup-node → verify-tag-matches-version          │
│  → cache-electron → npm ci                                   │
│  → electron-vite build                                       │
│  → electron-rebuild --arch <target>                          │
│  → prune-pack-deps --platform <target> --arch <target>      │
│  → [Linux x64] log node_modules size                         │
│  → electron-builder --publish never --<target> --<arch>     │
│  → [Linux x64] verify AppImage < 200MB                       │
│  → remove builder-debug.yml                                  │
│  → upload-artifact (release-<platform-arch>)                 │
└──────────────────────────────────────────────────────────────┘

Job 2: publish（依赖 build 完成）
┌──────────────────────────────────────────────────────────────┐
│  checkout → setup-node → npm ci --ignore-scripts             │
│  → download-artifact (所有 5 个 build job 的产物)             │
│  → collect release assets (exe/dmg/AppImage/yml/blockmap)    │
│  → electron-builder publish --policy always --files ...      │
│  → 统一发布到同一条 GitHub Release                            │
└──────────────────────────────────────────────────────────────┘
```

**发布步骤（开发者视角）**：

```bash
# 1. 提交代码
git commit -a -m "修改了xxx"

# 2. 更新版本号（自动改 package.json + 打 tag）
npm version patch|minor|major

# 3. 推送代码和 tag
git push && git push --tags

# CI 自动完成：5 架构并行构建 → 统一发布到 GitHub Release
# 全程无需人工干预，无需在三台机器上分别打包
```

#### 11.3.4 发布产物管理的自动化细节

| 自动化点 | 实现 | 解决的问题 |
|----------|------|------------|
| Tag 版本校验 | CI Step "Verify tag matches package.json version" | 推送 tag 与 package.json 版本不一致时 CI 直接 fail |
| 中文文件名规避 | `artifactName` 统一用 `${name}`（colortxt-…）而非 `${productName}`（彩读） | electron-builder 不对中文路径做 URL 编码，上传 GitHub Release 会失败 |
| 多架构更新文件隔离 | macOS/Linux 的 `publish.channel` 为 `latest-${arch}` | 避免 arm64 和 x64 的 `latest*.yml` 互相覆盖 |
| builder-debug 清理 | `rm -f release/builder-debug.yml` | 避免调试文件混入 Release 页面 |
| 并发控制 | `concurrency.group: release-${{ github.ref }}` + `cancel-in-progress: false` | 同一 ref 的多次触发不取消（避免半成品 Release） |
| artifact 合并 | `download-artifact` + `merge-multiple: true` | 5 个 build job 的产物合并到一个目录再发布 |
| macOS 未签名处理 | `CSC_IDENTITY_AUTO_DISCOVERY: false` | 没有证书时以未签名包发布，而非 CI 失败 |

#### 11.3.5 撤销发布的自动化

```bash
# 1. 网页端删除 Release 记录
# 2. 删除 tag
git tag -d v1.0.0          # 删本地
git push origin :refs/tags/v1.0.0  # 删远端
```

#### 11.3.6 本地手动发布（CI 不可用时的降级方案）

```bash
# 设置 GitHub Token
export GH_TOKEN='你的TOKEN'  # 需要 repo 权限

# 创建 tag + 推送
git tag v1.0.0
git push origin v1.0.0

# 构建打包并发布
npm run release
# = electron-vite build + electron-rebuild + prune-pack-deps + electron-builder --publish always
```

> 限制：本地 `npm run release` 只能打**当前机器**对应平台/架构的包。多架构需走 CI。

### 11.4 效率体系总结

| 效率维度 | 自动化措施 | 具体工具/脚本 | 效果 |
|----------|-----------|-------------|------|
| 积木拼装 | postinstall 补丁链 | 5 个 patch 脚本 + electron-rebuild | 装完依赖即自动修补第三方库，无需手动操作 |
| 运行时积木 | Vite transform 插件 | 4 个 Vite 插件 | 构建时自动改写 Monaco 源码，开发热重载也生效 |
| 调试效率 | 专用 dev 命令 | `dev:find` 只开找书窗 | 跳过主窗加载，直接调试目标模块 |
| 调试效率 | 探测脚本 | `probe-chm.mjs`、`llm-extract-top-characters.mjs` | 命令行验证特定功能，不用启动完整应用 |
| 测试效率 | 原生 test runner | `node --experimental-strip-types --test` | 直接跑 .ts 无需预编译 |
| 包体控制 | 裁剪脚本 + 双层排除 | `prune-pack-deps.mjs` + `onNodeModuleFile` | 减少数十 MB 安装包体积 |
| 包体校验 | CI 自动校验 | AppImage > 200MB → fail | 防止裁剪退化 |
| CI 缓存 | Electron 下载缓存 | `actions/cache@v5` | 避免每次 CI 重新下载 Electron |
| CI 加速 | CUDA 跳过 | `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` | 跳过 300MB+ CUDA EP 下载 |
| 发布自动化 | Tag 触发 CI | `release.yml` + 5 矩阵并行 | 推 tag 即自动 5 架构构建 + 统一发布 |
| 发布安全 | 版本校验 | Tag 与 package.json 版本必须一致 | 防止版本号不匹配 |
| 发布安全 | 幂等补丁 | 每个补丁带 marker 注释 | 重复执行不报错 |

---

## 十二、对比常规项目的优越点：多维度分析

> 本章将彩读与「常规 Electron 桌面应用 / 常规 Web 阅读器」对比，从架构、交互、存储、状态机、并发、安全、构建、性能、生态九个维度逐一拆解。每条对比均标注源码证据。

### 12.1 架构维度：积木式多窗口 vs 单窗口 SPA

| 对比项 | 常规 Electron 项目 | 彩读 | 优越点 |
|--------|-------------------|------|--------|
| 窗口模型 | 单一 BrowserWindow + 路由切换 | 6 种窗口类型，共用工厂按参数分流 | 功能解耦：关掉找书窗不影响阅读窗；摸鱼窗严格单例不干扰主窗 |
| 入口 HTML | 单一 index.html | 5 个 HTML 入口（主窗/找书/摸鱼/取色器/摸鱼设置）+ 后台 WebView | 每个窗口独立加载、独立卸载，按需启动——找书窗 `dev:find` 可跳过主窗直接调试 |
| 进程边界 | 渲染进程直接 require Node 模块 | `contextIsolation: true` + `nodeIntegration: false`；Preload 仅做 contextBridge 包装 | **安全边界严格**：渲染进程无直接 fs/Node 访问，所有系统操作经 IPC 白名单 |
| 共享层 | 类型定义散落各端 | `src/shared/` 60+ 模块统一跨层类型与常量 | 主进程与渲染进程共用同一套类型定义，重构不漏 |
| 窗口工厂 | 直接 `new BrowserWindow` | `windowFactory.ts` 统一工厂 + 4 张 Map 管理窗口态（shouldRestore / pendingOpen / findBook / findBookInitialTab） | 会话恢复仲裁集中一处：只有"全新的第一个主窗"才恢复上次会话，第二个窗不抢同一本书 |

**核心优越点**：窗口不是"页面"，而是"积木块"——可以单独创建、组合使用、互不干扰，关闭时自动清理关联的隐藏窗（后台 WebView / 取色层 / 摸鱼窗）。

### 12.2 交互维度：6 层事件路由 vs 简单冒泡

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 事件路由 | `@click` + `addEventListener` 单层冒泡 | **6 层路由**：L0 主进程 before-input-event → L1 OS 全局快捷键 → L2 document/window 捕获 → L3 覆盖层状态栈 → L4 Vue/DOM 冒泡 → L5 元素默认行为 | 键盘/鼠标/系统键/弹层/Monaco 默认行为同时存在时"谁先消费谁"有明确仲裁 |
| 弹层协调 | z-index 硬编码 + 手动关闭 | **两套覆盖层状态栈**：modalStack（结构化栈，z-index 6000+深度×10）+ dismissibleOverlayDepth（整数计数） | Esc 优先级不靠注册顺序，靠"每个处理函数查询全局覆盖层状态后主动退让"——这是整套路由的核心设计模式 |
| 快捷键冲突 | 直接绑定 keydown，多功能冲突 | shortcutService **三道闸**：录制拦截 > dismissible 计数闸（有菜单时全部快捷键直接 return）> 朗读重映射 > 空格翻页 > 绑定表 | 有弹层时快捷键自动失效，不会穿透到阅读区触发翻页 |
| 点击穿透 | 关闭弹层时同一点击可能触发下层 | **400ms 时间窗抑制标记**（armClickModeOverlaySkipIfNeeded） | 关闭弹层后同一次点击不穿透为业务动作——不靠 stopPropagation，靠时间窗标记 |
| 右键菜单 | 浏览器原生 contextmenu | 自绘菜单 + outside 捕获关闭 + Esc 关闭 | 不依赖浏览器菜单，可自定义内容和样式 |
| 模态叠加 | 单层 modal，叠加需手动管理 z-index | modalStack 支持多层叠加，Alt 按住反转点击模式时比较**模态深度差**判定是否生效 | 叠了词典管理后 Alt 自动失效——跨层状态感知 |

**核心优越点**：交互路由的核心设计模式是**"查询状态后主动退让"**而非**"抢占+阻断"**——每个处理函数先查全局覆盖层状态再决定是否执行，避免了 stopPropagation 滥用导致的事件黑洞。

### 12.3 存储维度：四层分层 + 双坐标系 vs 扁平 localStorage

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 存储层级 | localStorage + 可选 IndexedDB | **四层分层**：① localStorage（UI 偏好/会话快照）→ ② userData JSON（窗口位置/AI 配置/密钥保险库）→ ③ SQLite（向量索引/AI 对话/书源数据/分词缓存）→ ④ 模型缓存目录 | 按数据生命周期和访问频率分层：热数据在 localStorage 毫秒读写，冷数据在 SQLite，模型权重独立缓存 |
| 落盘策略 | 变更即写 / 关窗全量回写 | **门控 + 防抖 + 多窗合并 + 强制 flush**：进度/书签先入 `pendingFileMetaWrite`，gated/forced 两级优先级合并（forced 不被 gated 降级），防抖到期或关窗时 flush | 拖动滚动高频触发不打爆磁盘 IO；关窗/切书等关键时机强制 flush 不丢数据 |
| 坐标系统 | 行号或字符偏移量单一坐标 | **双坐标系**：物理行（磁盘上的真实行号，永不改变）+ 展示行（经空行压缩/缩进/替换后的 Monaco 行） | 所有持久化（进度/书签/标注）锚定物理行，所有渲染锚定展示行，靠 `displayLineToPhysicalLine` 映射表换算——改变格式化选项不会丢失进度 |
| 多窗写冲突 | 多窗同时写 localStorage 互相覆盖 | 先读最新快照，仅把本窗有改动的字段盖上去（`mergePendingFileMetaMode`） | 多窗编辑不同书的元数据不互相覆盖 |
| 密钥安全 | 明文写入 config.json | **三阶段演进**：明文 → 系统钥匙串 → 保险库 `secrets.v1.json` 分槽（chatProfileKeys / txt2imgProfileKeys / voiceRead.profileKeys / translation.providerKeys）+ 串行队列 + tmp→rename 原子替换 | config.json 不含明文 Key；多方案后各槽独立，一个泄露不影响其他 |
| 关窗兜底 | 仅 beforeunload | **pagehide + beforeunload 双保险**（注释说明 Windows 个别关闭路径对 pagehide 不可靠） | 跨平台关窗数据不丢 |

**核心优越点**：双坐标系是整个存储体系的基石——常规阅读器改一次格式化就丢进度，彩读可以随意切换空行压缩/缩进/替换规则，进度、书签、标注全部精准还原。

### 12.4 状态机维度：显式状态机 + 守卫 vs 布尔标志堆叠

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 状态管理 | `isLoading` / `hasError` 等离散布尔标志 | **12 个显式状态机**（见状态机架构分析）：应用生命周期、阅读会话、持久化落盘、语音朗读、书源搜索、章节缓存、整书下载、后台 WebView、AI 向量索引、AI Agent 对话、文生图、AI 智能排版 | 每个功能域有独立状态机，状态转换有守卫条件，不会出现"不可能的状态" |
| 流式加载 | 全量加载 or 简单分页 | 流式加载有**竞态代际** `activeStreamRequestId`：切书时旧流 `destroy()`，迟到 chunk 因 ID 不匹配被丢弃 | 快速切书时旧流的迟到 chunk 不会污染新会话——竞态防御 |
| 语音朗读 | play/pause 布尔 | 三态 `off/playing/paused` + 合成阶段 `ai/tts` + 代数式会话失效 `playbackSessionGen`（非显式枚举） | 代数式失效比枚举更安全：新会话自动作废旧会话，无需显式重置 |
| 持久化 | 变更即写 | **门控状态机**：空闲 → 待写 gated → 待写 forced → 落盘 → 空闲；forced 覆盖升级 gated（不降级） | 关键时刻（切书/关窗）升级为 forced 立即 flush，日常操作走 gated 防抖 |
| 关窗守卫 | `window.onbeforeunload` 直接 confirm | **二次确认状态机**：首次 close 拦截 → 发 IPC 问渲染层 → 渲染层决定（编辑态 dirty 弹确认框）→ `proceedClose` 放行；`allowNextClose` WeakSet 记录一次性放行 | 编辑态未保存时关窗有确认；找书窗虽无此守卫（已知缺口，见 2.9） |
| 进度恢复 | 从头开始 or 记住 scrollTop | **六级恢复优先级仲裁**：显式锚点 > 显式物理行 > 读完滚底 > Monaco viewState + 校验行 > 仅物理行 > 无 | 电子书第二次打开和旧书恢复一样快——转换结果缓存 + viewState 精准还原 |

**核心优越点**：状态不是"一堆布尔标志"，而是"有转换规则和守卫条件的有限状态机"——每个状态都有明确的入口条件和退出动作，不会出现"加载中又加载"等不可能状态。

### 12.5 并发维度：多窗口同步 vs 单窗口隔离

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 多窗口数据共享 | 不支持多窗口 or 各窗独立数据 | localStorage 同源共享 + `storage` 事件触发多窗同步 | 主题/快捷键/阅读设置在所有窗口实时热更新 |
| 跨窗广播 | 无 | theme:set → 遍历全部窗口 setBackgroundColor + send theme:sync；persistedSettingsChangedEvent → 主窗↔找书窗实时热更新 | 主题变更即时同步到摸鱼窗/取色器窗 |
| 窗口台账 | 无 | 每种窗口有明确的复用/单例策略：主窗可多开（复用最后聚焦窗）、找书窗可多开（复用当前/最后一个）、摸鱼窗严格单例、取色器每显示器一个 | 不靠 instanceof 分类，靠统一谓词函数（isBackstageWebViewWindow / isEyedropperWindow / ...） |
| 单实例锁 | 无 or 简单 | `requestSingleInstanceLock` + second-instance 处理：argv 有 .txt → 有主窗复用打开、无主窗新建带 pendingOpenTxt | 运行中双击 txt 不开新进程，复用已有实例 |
| 摸鱼会话绑定 | 无 | Session 结构含 overlay + owner + payload + pendingPayload + onOwnerClosed；源窗关闭 → 摸鱼窗连带销毁、全局键注销、不回写进度；摸鱼窗自关 → 向源窗回写进度 | **设计最严密的一块**：源窗与摸鱼窗的生命周期完全绑定，幂等 teardown |
| 下载进度隔离 | 无 | 事件按 downloadId 定向回发起方 webContents | 下载进度仅发起窗可见，不广播 |

**核心优越点**：多窗口并发不是"多个独立窗口"而是"有协调的窗口集群"——数据层共享、事件层广播、生命周期绑定，同时有明确的防覆盖机制。

### 12.6 安全维度：渐进式收紧 vs 一次性设计

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 进程隔离 | `nodeIntegration: true`（方便） | `contextIsolation: true` + `nodeIntegration: false`；Preload 仅 contextBridge | 渲染进程无直接 Node 访问，所有系统操作经 IPC 白名单 |
| 密钥存储 | 明文配置文件 | 三阶段演进：明文 → 钥匙串 → 保险库分槽 + 原子写 + localStorage 剥离 | config.json 不含明文 Key；旧数据自动迁移与废弃 slot 清除 |
| 文件协议 | file:// 直接加载 | `colortxt-local://` 自定义协议 + 双 Map ref + 路径穿越防护 | 本地图片/资源加载有路径校验，防 `../` 穿越 |
| 网络请求 | Node fetch / axios | Node/undici → 改用 Chromium `session.fetch`（v3.3）：书源站点 TLS 指纹与浏览器一致 | 被站点按 TLS 指纹拦截的风险大幅降低 |
| Cookie 管理 | 无 or 手动 | tldts 可注册域提取 + tough-cookie Cookie Jar | 书源登录态按域隔离，不串站 |
| 证书校验 | 默认 | `setCertificateVerifyProc` 可控（后台 WebView 取页时跳过自签证书） | 灵活处理自签名证书站点，不影响主进程安全 |
| DevTools | 生产环境保留 | 打包后 `before-input-event` 拦截 F12 / Ctrl+Shift+I | 生产环境无 DevTools 入口 |
| **故意不拦 Esc** | — | 注释明确：拦了渲染进程收不到 Esc，全屏退出/弹窗关闭会失灵 | 安全措施不牺牲功能 |

**核心优越点**：安全不是"一次性设计到位"，而是"随功能增长逐步收紧"——从明文到钥匙串到保险库分槽，每一步都带旧数据迁移，用户无感知。

### 12.7 构建维度：全链路自动化 vs 手动打包

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 依赖安装 | `npm install` | `npm install` + postinstall 自动执行 5 个补丁脚本 | 装完即用，无需手动修补第三方库 |
| 构建命令 | 手动多步 | `npm run build` 一键：electron-vite build → electron-rebuild → prune-pack-deps → electron-builder | 4 步自动化流水线 |
| 包体优化 | 不裁剪 | `prune-pack-deps.mjs` 裁剪非目标平台原生包 + 双层排除（beforePack + onNodeModuleFile） | 减少数十 MB 安装包体积 |
| CI/CD | 无 or 单平台 | 5 架构并行构建 + 统一发布 job | 推 tag 即自动 5 平台构建 + 发布，无需多台机器 |
| 包体校验 | 无 | AppImage > 200MB → CI fail | 防止裁剪退化或意外引入大依赖 |
| 缓存 | 无 | Electron 下载缓存按 `runner.os + arch + lockfile hash` | 避免 CI 重复下载 Electron |
| CI 加速 | 无 | `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` 跳过 300MB CUDA EP | 大幅加速 CI |
| 补丁幂等 | 无 | 每个补丁注入 marker 注释，重复执行自动跳过 | `npm ci` 恢复依赖后重跑不报错 |

**核心优越点**：构建不是"一次性脚本"，而是"幂等+安全降级"的自动化体系——第三方库升级后补丁不崩溃只 warn，CI 包体超限自动 fail。

### 12.8 性能维度：流式加载 + 视口装饰 vs 全量渲染

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 大文件加载 | 全量读入内存 | **流式按行切分**（256KB 分块），`createReadStream({highWaterMark:256KB})` | 数百万字小说不卡顿，边加载边渲染 |
| 编辑器性能 | contenteditable / 自造渲染 | Monaco Editor（百万行级性能，行列模型，装饰器体系） | 复用 VS Code 内核的渲染性能和装饰器体系 |
| 装饰视口化 | 全量 DOM 装饰 | 高亮/标注装饰仅渲染视口内行（Monaco 装饰器 API） | 万条高亮词不卡顿 |
| 缓存命中 | 无 | 电子书转换结果缓存：`convertedMdPath` 存在 && 源文件 mtime 一致 → 直接复用，0 开销 | 电子书第二次打开和旧书恢复一样快 |
| 预加载 | 无 | Edge TTS **4 段在途缓冲**（生产者-消费者模型）：预热 4 段 mp3，播放同时后台拉取下一段 | TTS 朗读不卡顿，网络延迟不阻塞播放 |
| 限流 | 无 | 云 TTS 串行限流槽（链表 Promise + 280ms 最小间隔 + 5 次指数退避） | 防 HTTP 429，自动重试 |
| 内存管理 | 全量常驻 | 物理行常驻内存 + 展示层映射（改变格式化不重载文件） | 切换空行压缩/缩进/替换规则不重新读文件 |

**核心优越点**：性能不是"优化某个函数"，而是"从加载到渲染到缓存的完整管线设计"——流式加载 + 视口装饰 + 转换缓存 + TTS 预缓冲，每个环节都有独立的性能策略。

### 12.9 生态维度：兼容而不复制 vs 造轮子

| 对比项 | 常规项目 | 彩读 | 优越点 |
|--------|---------|------|--------|
| 格式支持 | 自造解析器 | 兼容已有生态：Legado 书源 JSON（TypeScript 复刻规则引擎）、foliate-js（参考 MOBI/EPUB）、libmspack（参考 CHM 移植为 JS） | 不引入 Java/Rhino 依赖，用 TypeScript 重新实现 |
| 社区资源 | 不兼容 | 兼容 Legado 数万社区书源 + vscode-txt-syntax 语法高亮 | 用户可直接使用已有社区资源 |
| 上游致谢 | 无 | README「相关」章节 14 条致谢，全部注明来源与用途 | 尊重开源，不抹杀来源 |
| 格式策略 | 自造标记 | 两次收敛：私有标记 `<<A>>` → 标准 Markdown；手写正则解析 → marked | "私有方案活得越久，迁移成本越高"——在扩散前切换 |
| 补丁策略 | 等 upstream 修 or fork | **Vite transform 改写 + 运行时补丁**双层体系；上游无解问题以 WARNING 明示 | 不换内核，不掩盖问题 |
| 降级即升级 | 不会主动关闭功能 | 三次"降级即升级"：禁用 Monaco 大文件优化（为软换行/粘性标题）、关闭等宽渲染优化（字体保真）、关闭圆角选区抠图（透明背景下不露馅） | 关闭特性不是退步，而是为更高优先级的体验让路 |

**核心优越点**：生态策略是"兼容而不复制"——不造新格式，直接兼容已有生态，但用 TypeScript 重新实现，不引入外部运行时依赖。

### 12.10 优越点总览矩阵

| 维度 | 常规项目做法 | 彩读做法 | 本质优越 |
|------|-------------|---------|----------|
| 架构 | 单窗口 SPA | 6 窗口积木 + 统一工厂 | 功能解耦，按需启动 |
| 交互 | 单层冒泡 | 6 层路由 + 状态栈仲裁 | 查询状态后主动退让，不滥用 stopPropagation |
| 存储 | 扁平 localStorage | 四层分层 + 双坐标系 + 门控落盘 | 改格式化不丢进度，高频写不打爆 IO |
| 状态机 | 布尔标志堆叠 | 12 个显式状态机 + 守卫条件 | 不可能出现不可能的状态 |
| 并发 | 单窗口隔离 | 多窗 localStorage 同步 + 防覆盖 | 多窗数据实时热更新不互相覆盖 |
| 安全 | 一次性设计 | 渐进式三阶段收紧 + 旧数据迁移 | 安全随功能增长，用户无感知 |
| 构建 | 手动多步 | 5 步自动化 + 5 架构 CI + 包体校验 | 推 tag 即发布，CI 防退化 |
| 性能 | 全量渲染 | 流式加载 + 视口装饰 + 缓存 + 预缓冲 | 百万字小说不卡顿 |
| 生态 | 造轮子 | 兼容而不复制 + 两次格式收敛 | 直接利用已有社区资源 |

### 12.11 彩读仍有改进空间的地方（诚实盘点）

| 维度 | 现状 | 改进方向 |
|------|------|----------|
| 磁盘文件外部修改 | 阅读态静默重载，不检查朗读/弹层状态 | 重载前检查语音/弹层，或提供确认选项 |
| 编辑态外部修改 | 编辑时不监听磁盘变更，保存时直接覆盖（无 mtime 比对） | 加 mtime 比对，冲突时提示 |
| 下载失败章 | 写死占位文本 `　　[下载失败]`，用户看到"完成"但内含占位 | 统计失败章数，完成后提示"N 章失败" |
| 找书窗关窗守卫 | 编辑章节后未保存直接关窗无提示 | 接线 dirty 概念到找书窗 |
| localStorage 写满 | 配额溢出只静默不提示用户 | 加配额检测和用户提示 |
| 电源/休眠 | 无 powerMonitor：番茄钟跳秒、休眠后 TTS socket 可能失效 | 接入 powerMonitor，休眠恢复后重连 |
| 书源变更广播 | A 窗增删改书源，B 窗已打开面板不刷新 | 加 sourcesChanged 广播事件 |
| 窗口关闭时 AI abort | 未发现"窗口 closed → 主动 abort 该窗流式 AI 请求" | 加窗口关闭时统一 abort 清理 |
| AI 窗口关闭 TTS | 未发现"关窗 → 取消该窗在途合成" | 加关窗时 cancelSynthesis 联动 |
| Wayland 全局快捷键 | 失效，README 已知问题暂无解 | 探索 Wayland 下的替代方案 |

---

## 附：关键技术依赖全景表

| 依赖 | 用途 | 类型 |
|------|------|------|
| monaco-editor | 阅读器核心编辑器 | devDep |
| better-sqlite3 | SQLite 数据库（向量库、书源库） | dep |
| sqlite-vec | SQLite 向量扩展（RAG 检索） | dep |
| @huggingface/transformers | 内置本地嵌入模型运行 | dep |
| @node-rs/jieba | 中文分词（词云生成） | dep |
| opencc | 简繁互转（原生模块） | dep |
| iconv-lite + jschardet | 编码检测与解码 | dep/devDep |
| marked + marked-katex-extension | Markdown 渲染 | devDep |
| markmap-lib + markmap-view | 思维导图渲染 | devDep |
| d3-cloud + d3-scale | 词云布局 | devDep |
| pdfjs-dist | PDF 解析 | devDep |
| jszip | ZIP 容器解析（EPUB/书包） | devDep |
| cheerio | HTML 解析（书源规则引擎） | devDep |
| jsonpath-plus | JSON 路径查询（书源规则） | devDep |
| @xmldom/xmldom + xpath | XPath 解析 | devDep |
| heic-convert | HEIC 封面转 JPEG | devDep |
| tldts | 可注册域提取（Cookie Jar） | devDep |
| tough-cookie | Cookie 管理 | devDep |
| ws | WebSocket（TTS 流式） | dep |
| electron-updater | 自动更新 | dep |
| sortablejs | 拖拽排序 | devDep |
| socks-proxy-agent | SOCKS 代理 | devDep |
| vue + vue-tsc | UI 框架 + 类型检查 | devDep |
| electron + electron-builder + electron-vite | 桌面应用三件套 | devDep |
| vite | 构建基础 | devDep |
| vite-plugin-monaco-editor | Monaco Vite 插件 | devDep |
| @caitun/speex | Speex 音频转 WAV | dep |
| font-list | 系统字体列表 | dep |
| mdict-js | MDict 词典解析 | dep |
| katex | 数学公式渲染 | devDep |
| pako | 压缩/解压 | devDep |
| js-beautify | HTML 美化 | devDep |

---

> 本报告基于 14 份逆向分析文档、项目 README/CHANGELOG/docs 全量文档、package.json 依赖清单、源码目录结构综合编写。所有版本日期与功能描述均与 CHANGELOG.md 原文核对。
