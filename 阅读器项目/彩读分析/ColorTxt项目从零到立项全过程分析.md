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
