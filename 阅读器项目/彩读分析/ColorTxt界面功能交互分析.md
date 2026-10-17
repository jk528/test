# ColorTxt 界面与功能交互分析

> 本文档按 **窗口 → 界面分区 → 交互点 → 功能 → 程序插口（IPC / 事件）** 的脉络，串联 ColorTxt 整个项目的界面与功能。
> 源码根目录：`.temp/ColorTxt`
> 分析日期：2026-09-21

---

## 一、窗口总览

ColorTxt 是 Electron 多窗口应用，不同窗口加载不同 HTML 入口，排版与功能差异很大。

| # | 窗口类型 | 入口 HTML | 渲染根组件 | 主进程创建位置 | 触发方式 |
|---|---------|-----------|-----------|---------------|---------|
| 1 | **主窗口**（阅读/编辑） | `renderer/index.html` | `App.vue` | `windowFactory.ts:createMainWindowFactory` | app 启动 / 新窗口 / 打开文件 |
| 2 | **彩读找书窗口** | `renderer/find-book.html` | `FindBookWindow.vue` | 同上，`openFindBook=true` | 主窗口"找书"按钮/快捷键 F7 / 桌面快捷方式 |
| 3 | **隐身（摸鱼）阅读窗** | `renderer/index.html`（复用） | `StealthReaderApp.vue` | `stealthReader.ts` | 主窗口"摸鱼模式" |
| 4 | **摸鱼设置窗** | `renderer/index.html` | `StealthSettingsApp.vue` | `stealthSettingsWindow.ts` | 摸鱼窗内打开设置 |
| 5 | **取色器窗** | `renderer/eyedropper.html` | — | `eyedropper.ts` | 配色面板中取色按钮 |
| 6 | **后台 WebView** | 不显示 | — | `bookSource/engine/backstageWebView.ts` | 书源登录/校验，仅主进程内部使用 |

> 主窗口和找书窗口共用同一套 `BrowserWindow` 工厂（`windowFactory.ts`），通过 `openFindBook` 参数区分加载哪个 HTML；其余窗口为独立创建。

---

## 二、主窗口（App.vue）

主窗口采用 **顶部栏 + 左侧栏 + 中央阅读器 + 底部状态栏 + 弹层面板** 的五段式布局。

```
┌────────────────── AppHeader 顶部栏 ──────────────────┐
│ 打开文件 │ 编辑/阅读尺/点击模式 │ 主题/字体/格式 │ 更多 │
├────────┬─────────────────────────────────────────────┤
│        │                                             │
│ 侧栏    │             ReaderMain 阅读器               │
│Activity│          （Monaco 编辑器核心）               │
│  栏    │                                             │
│        │                                             │
├────────┴─────────────────────────────────────────────┤
│                AppFooter 底部状态栏                  │
└──────────────────────────────────────────────────────┘
            AppOverlays（弹层面板，浮于其上）
```

### 2.1 顶部栏 `components/AppHeader.vue`

| 交互点 | 事件 / 回调 | 功能 | 主进程插口 |
|--------|------------|------|-----------|
| **打开文件** 按钮 | `@openFile` | 弹出文件选择对话框 | `window.colorTxt.showOpenDialog` |
| 编辑模式切换 | `emit('toggleReaderEdit')` | 进入/退出 Monaco 编辑模式 | —（渲染层） |
| 阅读尺开关 | `emit('toggleReadingRuler')` | 阅读助视尺（聚焦行+暗色其余） | — |
| 点击模式 / 选择模式 | `emit('toggleReaderClickMode')` | 点击翻页 vs 文字选择 | — |
| 保存（编辑模式下） | `emit('saveReaderFile')` | 保存编辑后的文件 | `window.colorTxt.writeTextFile` |
| AI 智能排版（编辑模式） | `emit('aiSmartFormatFull')` | 全书 AI 排版 | `window.colorTxt.ai.textFormatCleanup` |
| 书钉（记住位置） | `emit('pinClick')` / `emit('goBackFromPin')` | 钉住当前位置并可回跳 | — |
| 书签 | `emit('bookmarkClick')` | 添加/清除当前行书签 | — |
| 定时滚动 | `emit('timedScrollToggle')` | 自动滚动阅读 | — |
| 语音朗读 | `emit('voiceReadToggle')` | 启动/停止 TTS 朗读 | `window.colorTxt.voiceReadSynthesize` |
| 字体工具条 `HeaderFontToolbar` | `setMonacoFont` / `togglePinOtherFont` / `increaseFontSize` / `decreaseFontSize` / `increaseLineHeight` / `decreaseLineHeight` | 字体选择、固定字体、字号、行高 | `window.colorTxt.listSystemFonts` |
| 格式工具条 `HeaderFormatToolbar` | 文本转换（繁简/字母/数字）、压缩空行、行首缩进、高级换行、打开替换规则面板 | 阅读格式与文本处理 | `window.colorTxt.convertTextOpenCc` |
| 章节规则按钮 | `emit('openChapterRules')` | 打开章节匹配规则面板 | — |
| 内容上色开关 | `emit('toggleMonacoCustomHighlight')` | 高亮词上色开关 | — |
| 明暗主题切换 | `emit('changeTheme', theme)` | 亮/暗主题 | `window.colorTxt.setNativeTheme` |
| 极简模式 | `emit('toggleMinimalist')` | 隐藏顶栏侧栏沉浸阅读 | — |
| 全屏 | `emit('toggleFullscreen')` | 全屏切换 | `window.colorTxt.setFullscreen` |
| 更多菜单 | 见下表 | 聚合菜单入口 | — |

**顶部栏"更多"菜单 `MoreMenu.vue`：**

| 菜单项 | 事件 | 功能 | 插口 |
|--------|------|------|------|
| 查找 | `emit('toggleFind')` | 打开查找小窗 | — |
| 打开最近文件（子菜单） | `emit('openRecentFile')` / `emit('clearRecentFiles')` | 历史记录 | — |
| 新窗口 | `emit('openNewWindow')` | 新开主窗口 | `window.colorTxt.openNewWindow` |
| 快捷键 | `emit('openShortcuts')` | 打开快捷键面板 | — |
| 设置 | `emit('openSettings')` | 打开设置面板 | — |
| 配色 | `emit('openColorScheme')` | 打开配色面板 | — |
| 找书（beta） | `emit('openFindBook')` | 打开找书窗口 | `window.colorTxt.openFindBookWindow` |
| 摸鱼模式 | `emit('enterStealthReader')` | 进入隐身阅读窗 | `window.colorTxt.stealthReaderEnter` |
| 检查更新 | — | 检查版本 | `window.colorTxt.checkForUpdates` |
| 开发者工具 | `window.colorTxt.toggleDevTools()` | 打开 DevTools | `window.colorTxt.toggleDevTools` |
| GitHub | `emit('openGithub')` | 打开仓库 | `window.colorTxt.openExternal` |
| 关于 | `emit('openAbout')` | 关于面板 | — |
| 退出 | `emit('quitApp')` | 退出应用 | `window.colorTxt.quitApp` |

### 2.2 左侧栏 `components/ReaderSidebar.vue`

左侧栏由 **Activity 图标栏** + **展开面板** 组成。

**Activity 主标签（上排）：**

| 图标 | Tab | 展开面板 | 主要功能 |
|------|-----|---------|---------|
| 📚 | files | `FileListPanel` | 文件列表：选择目录/文件、分类、排序、树状/列表、打开、重命名、替换、移除、清空、新窗口打开、关闭当前文件 |
| 📑 | chapters | `ChapterListPanel` | 章节列表：跳转章节、全部展开/折叠、刷新章节、显示字数 |
| 🔍 | search | `SearchPanel` | 全文搜索：关键词、区分大小写、全字匹配、正则、跳转结果 |
| 🔖 | bookmarks | `BookmarkListPanel` | 书签：跳转、编辑、移除、导入/导出 JSON |
| 🎨 | highlights | `HighlightListPanel` | 高亮词：查找、收藏、拆分、合并、提交分组、导入/导出 |
| 📝 | notes | `AnnotationListPanel` | 笔记/标注：跳转、移除、清空、导入/导出 MD/JSON |
| 🤖 | aiAssistant | `AiAssistantPanel` | AI 阅读助手：对话、深度思考、防剧透、技能、词云、思维导图（需 AI 开启） |
| 👤 | character | `CharacterSidebarPanel` | 角色卡：立绘生成、检索（需文生图开启） |

**Activity 次标签（下排）：**

| 图标 | 功能 |
|------|------|
| ☁️ WebDAV | 打开 WebDAV 同步面板（仅配置后显示） |
| 🎨 配色 | 打开配色面板 |
| ⚙️ 设置 | 打开设置面板 |

侧栏头部按钮会随当前 Tab 变化：文件 Tab 有"选择目录""更多"；章节 Tab 有"显示字数开关""刷新章节"等。

### 2.3 中央阅读器 `components/ReaderMain.vue`

阅读器核心是 Monaco Editor，其上叠加多个浮动交互层：

| 浮动层 | 组件 | 触发 | 功能 |
|--------|------|------|------|
| **选中文字工具条** | `ReaderSelectionToolbar` | 选中文字后 | 复制、高亮、马克笔/波浪线/直线划线、笔记、查找、词典查询、翻译、AI 问答 |
| 高亮浮动条 | `ReaderHighlightFloat` | 点击高亮词 | 颜色选择/移除 |
| 词典弹窗 | `ReaderDictionaryPopup` | 工具条"词典" | 查词释义 |
| 翻译弹窗 | `ReaderTranslatePopup` | 工具条"翻译" | 翻译选中文本 |
| 笔记输入 | `ReaderNoteInputPanel` | 工具条"笔记" | 为划线添加笔记 |
| 局部编辑 | `ReaderPartialEditPanel` | 编辑模式选区 | 局部修改物理行 |
| 图片灯箱 | `ReaderImageLightbox` | 点击 Markdown 图片 | 大图预览 |
| 智能排版审阅条 | `SmartFormatReviewBar` | AI 排版后 | 应用/放弃差异 |

**阅读器右键菜单**（`ReaderMain.vue:283`）额外提供：网络搜索、搜索管理、编辑选中文本、AI 智能排版（选区）等。

阅读器对外 emit 的核心事件（由 `App.vue` 接收）：
- `aiSmartFormatFull` / `aiSmartFormatSelection` — AI 排版
- `addHighlightTerm` / `removeHighlightTerm` — 高亮词增删
- `upsertReaderAnnotation` / `removeReaderAnnotation` — 标注增删
- `askAiWithQuote` / `searchWithQuote` — 用引文问 AI / 搜索
- `openDictionaryManage` / `openWebSearchManage` / `openTranslateManage` — 打开对应管理面板
- `readerEditSaveRequest` — 编辑模式保存
- `viewportTopLineChange` / `viewportVisualProgressChange` — 阅读进度

### 2.4 底部状态栏 `components/AppFooter.vue`

| 区域 | 交互 | 功能 | 插口 |
|------|------|------|------|
| 番茄钟 | `pomodoroStart` / `togglePause` / `stop` / `toggleDisplayMode` | 番茄钟计时 | — |
| 文件路径 | `pathRevealInFolder` / `pathReload` / `pathReconvert` / `pathClose` | 在文件夹中显示、重新加载、重新转换电子书、关闭文件 | `window.colorTxt.showItemInFolder` |
| WebDAV 书包 | `pathUploadBookPackWebDav` / `pathUpdateBookPackWebDav` / `pathExportBookPack` | 上传/同步/导出阅读数据 | `window.colorTxt.webdav.*` |
| 清除阅读数据 | `pathClearReadingData` | 清除当前文件阅读数据 | — |
| 编码 | `saveFileAsEncoding` | 另存为指定编码 | `window.colorTxt.writeTextFile` |
| 阅读进度/字数/大小 | （只读展示） | 实时统计 | — |

### 2.5 语音朗读工具条 `VoiceReadToolbar`

朗读激活时浮于阅读器之上：播放/暂停、上一行/下一行、重新生成、停止、发音设置、语速/音量调节。
插口：`window.colorTxt.voiceReadSynthesize` / `voiceReadCancelSynthesis` / `voiceReadListVoices`。

### 2.6 章节导航条 `ReaderChapterNavBar`

上一章 / 下一章按钮（在非全屏时位于阅读器上方，全屏时移到底部栏内）。

---

## 三、弹层面板体系 `AppOverlays.vue`

主窗口所有模态面板均由 `AppOverlays.vue` 统一挂载，通过 `v-model` 布尔开关控制显隐。

### 3.1 设置面板 `SettingsPanel.vue`

设置面板采用顶部 Tab 导航（`SettingsTabBar.vue`），共 10 个标签：

| Tab | 子组件 | 主要设置项 |
|-----|--------|-----------|
| 常规 | `SettingsGeneralPanel` | 启动恢复会话、同步当前文件、最近文件数量、章节最少字数、电子书输出目录、书包解压目录/密码、清除缓存、打开阅读数据 |
| 阅读 | `SettingsReadingPanel` | 字体/字号/行高/字间距/缩进、平滑滚动、CJK 换行优化、滚动灵敏度、黏贴章节标题、阅读尺、Markdown 图片高度、章节导航条、章节标题空行、番茄钟、定时滚动、选中文本工具条按钮配置、词典/搜索/翻译管理入口 |
| 编辑 | `SettingsEditPanel` | 行号、缩略图、编辑时自动刷新章节列表 |
| 语音朗读 | `SettingsVoiceReadPanel` | 引擎、音色、语速、音量、配置文件 |
| AI 阅读助手 | `SettingsAIPanel` | API 配置、模型、密钥、测试连接 |
| 向量模型 | `SettingsVectorModelPanel` | 嵌入模型（内置/远程）、缓存管理 |
| 角色卡 | `SettingsTxt2ImgPanel` | 文生图服务（Stable Diffusion/ComfyUI 等） |
| 技能 | `SettingsSkillsPanel` | AI 自定义技能增删改 |
| 代理 | `FindBookSettingsProxyPanel` | HTTP 代理 |
| WebDAV | `SettingsWebDavPanel` | WebDAV 连接配置 |

> 设置面板中"打开阅读数据""词典管理""搜索管理""翻译管理""发音设置"会进一步打开独立的子面板。

### 3.2 配色面板 `ColorSchemePanel.vue`

3 个标签（`ColorSchemeTabBar.vue`）：

| Tab | 子组件 | 功能 |
|-----|--------|------|
| 阅读器 | `ColorSchemeReaderPanel` | 阅读区背景色/图、文字色、前景色、配色预设 |
| 高亮色 | `ColorSchemeHighlightPanel` | 高亮词颜色组管理 |
| 标注色 | `ColorSchemeLineationPanel` | 划线/笔记颜色组管理 |

顶栏额外提供：主题切换、导出配色、导入配色、导出当前方案。

### 3.3 其他独立弹层

| 面板 | 组件 | 打开入口 | 用途 |
|------|------|---------|------|
| 章节匹配规则 | `ChapterRulePanel` | 顶部栏章节规则按钮 | 编辑/测试章节正则 |
| 阅读数据 | `ReadingDataPanel` | 设置→常规→打开阅读数据 | 查看/清除各文件阅读数据 |
| 快捷键 | `ShortcutPanel` | 更多→快捷键 | 查看/修改快捷键绑定 |
| 关于 | `AboutPanel` | 更多→关于 | 版本信息 |
| 词典管理 | `DictionaryManageModal` | 选中工具条/设置 | 导入/删除词典 |
| 网络搜索管理 | `WebSearchManageModal` | 同上 | 搜索引擎配置 |
| 翻译管理 | `TranslateManageModal` | 同上 | 翻译服务配置 |
| 朗读发音设置 | `VoiceReadSpeakSettingsPanel` | 朗读工具条 | 发音参数 |
| 替换规则 | `ReplaceRulePanel` | 顶部栏格式→替换 | 文本替换规则 |
| WebDAV 同步 | `WebDavSyncPanel` | 侧栏 WebDAV 图标 | 上传/下载书包 |
| 添加/编辑书签 | `AppModal` | 书签按钮 | 书签对话框 |
| AI 智能排版进度 | `AiSmartFormatProgressModal` | AI 排版 | 进度与 Token 用量 |

---

## 四、彩读找书窗口

找书窗口是独立 Electron 窗口，入口 `find-book.html` → `FindBookWindow.vue` → `FindBookPanel.vue`（`standalone` 模式）。
**布局与主窗口完全不同**：采用 **顶部工具栏 + 主标签 + 内容区** 的单栏布局，没有左侧 Activity 栏。

```
┌────────── 顶部工具栏（返回主界面 / 主Tab / WebDAV / 主题 / 更多） ──────────┐
│  书架 │ 找书 │ 发现                                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                     内容区（按 mainTab 切换）                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
        弹层：书籍详情 / 在线阅读器 / 书源管理 / 设置 / 配色 / 免责声明 等
```

### 4.1 顶部工具栏

| 控件 | 功能 | 插口 |
|------|------|------|
| 返回 / 主界面按钮 | `focusOrOpenMainWindow()` | `window.colorTxt.focusOrOpenMainWindow` |
| 主标签栏 `AppTabBar` | 书架 / 找书 / 发现 三选一 | — |
| WebDAV 按钮 | WebDAV 同步菜单 | `window.colorTxt.webdav.*` |
| 主题切换 | 亮/暗 | `window.colorTxt.setNativeTheme` |
| 更多菜单 | 见下表 | — |

**找书窗口"更多"菜单：**

| 菜单项 | 功能 | 插口 |
|--------|------|------|
| 主界面 | 返回主窗口 | `focusOrOpenMainWindow` |
| 生成桌面快捷方式 | 创建找书桌面快捷方式 | `window.colorTxt.createFindBookDesktopShortcut` |
| 检查更新 | — | `checkForUpdates` |
| 开发者工具 | — | `toggleDevTools` |
| GitHub | — | `openExternal` |
| 关于 | 关于面板 | — |
| 免责声明 | `DisclaimerPanel` | — |
| 退出 | 退出应用 | `window.colorTxt.quitApp` |

> 书源管理、替换规则、下载目录、设置、配色、快捷键等入口也在更多菜单中。

### 4.2 三大主标签

#### ① 书架 `FindBookshelfPanel.vue`
- 展示已加入书架的书籍（封面、书名、作者、最新章）
- 操作：**阅读**（打开内置阅读器）、**书籍信息**（详情弹窗）、按来源搜索、分类筛选、排序
- 事件：`read-book` / `open-book-info` / `search-source` / `select-category`

#### ② 找书（搜索）
- 搜索框：书名/作者，支持精准搜索、指定书源
- 搜索历史标签、清空历史
- 搜索状态：进度条、已完成/总数、结果数、搜索日志
- 结果列表 `FindBookListItem.vue`：点击 → 书籍详情弹窗
- 插口：`window.colorTxt.bookSourceSearch` / `bookSourceSearchCancel` / `bookSourceSearchLoadMore`

#### ③ 发现 `FindDiscoverPanel.vue`
- 书源分类浏览、探索书籍
- 插口：`bookSourceExploreKinds` / `bookSourceExploreBooks`

### 4.3 书籍详情弹窗 `BookDetailPanel.vue`

| 按钮 | 功能 | 插口 |
|------|------|------|
| 加入书架 / 移出书架 | `onToggleBookshelf` | 本地书架存储 |
| 下载全书 | 下载章节到本地 | `bookSourceDownload` / `bookSourceDownloadCancel` |
| 导出缓存 | 将缓存章节拼接为 TXT 导出 | `findBookDownloadToFileList` |
| 在线阅读 | 打开内置阅读器 | — |

### 4.4 在线阅读器 `FindBookReaderPanel.vue`

找书内置阅读器有独立的头部/侧栏/底部，与主窗口 ReaderMain 不同：

| 区域 | 组件 | 交互 |
|------|------|------|
| 头部 | `FindBookReaderHeader` | 主题、字体、行高、语音、定时滚动、设置、切找书/书架、文本替换、阅读模式 |
| 章节侧栏 | `FindBookReaderChapterSidebar` | 章节列表跳转、缓存标记 |
| 底部 | `FindBookReaderFooter` | 上一章/下一章、进度、阅读设置 |

### 4.5 书源管理 `BookSourcePanel.vue`

从"更多→书源管理"打开，功能：

| 操作 | 插口 |
|------|------|
| 列表/启用/禁用 | `bookSourceList` / `bookSourceToggle` |
| 编辑 | `EditBookSourcePanel` → `bookSourceSave` |
| 删除 | `bookSourceDelete` |
| 导入 | `ImportBookSourcePanel` → `bookSourceImportPreview` / `bookSourceImportCommit` |
| 校验 | `bookSourceFetchUrl` |
| 登录 | `BookSourceLoginPanel` → `bookSourceGetLoginInfo` / `setLoginInfo` / `browserLogin` |
| 探索 | `bookSourceExploreKinds` / `bookSourceExploreBooks` |
| 排序 | `bookSourceReorder` |
| 替换规则 | `ReplaceRulePanel` |

### 4.6 找书设置 `FindBookSettingsPanel.vue`

6 个标签（`FindBookSettingsTabBar.vue`）：下载 / 阅读 / 编辑 / 语音朗读 / 代理 / WebDAV。
注意：找书设置的标签子集与主窗口设置有重叠但不完全相同（无 AI/向量模型/角色卡/技能/常规）。

### 4.7 找书窗口快捷键
- `F7`：打开找书窗口（主窗口中）
- `F8`：在找书窗口中打开书源管理
- 阅读器内有独立快捷键（`useFindBookReaderShortcuts.ts`）

---

## 五、其他独立窗口

### 5.1 隐身（摸鱼）阅读窗 `StealthReaderApp.vue`

- **用途**：伪装成终端/记事本的透明小窗， discreet 阅读
- **入口**：主窗口更多菜单"摸鱼模式" → `window.colorTxt.stealthReaderEnter`
- **交互**：
  - 左右点击翻页、滚轮翻页
  - 右键菜单：字体、行高、透明刷新、打开摸鱼设置、退出
  - 可拖动、调整大小、始终置顶
- **插口**：`stealthReaderEnter` / `stealthReaderGetPayload` / `stealthReaderUpdatePayload` / `stealthReaderChapterNavSettled` / `stealthReaderExit` / `stealthReaderPopupMenu` / `stealthReaderSetBounds` 等
- 拥有独立的章节导航（与源主窗口联动）：`stealthReaderOwnerChapterNav`

### 5.2 摸鱼设置窗 `StealthSettingsApp.vue`

- 从摸鱼窗右键菜单打开，独立 BrowserWindow
- 设置摸鱼窗的字体、字号、行高、颜色、透明度等
- 插口：`openStealthSettingsWindow` / `closeStealthSettingsWindow`

### 5.3 取色器窗 `eyedropper.html` + `eyedropper.ts`

- 全屏覆盖层，屏幕取色
- 入口：配色面板中背景取色按钮
- 插口：`eyedropperPick` / `eyedropperReady` / `eyedropperSubmit` / `eyedropperCancel` / `eyedropperSample` / `eyedropperCopy` / `eyedropperToggleFormat`

---

## 六、程序插口全表（IPC 桥）

所有渲染层→主进程调用统一通过 `window.colorTxt.*`（preload 暴露）。以下按功能域分组。

### 6.1 窗口与应用

| API | 通道 | 用途 |
|-----|------|------|
| `openNewWindow` | `window:new` | 新建主窗口 |
| `openFindBookWindow` | `window:openFindBook` | 打开找书窗 |
| `openNewFindBookWindow` | `window:newFindBook` | 新建找书窗（书架页） |
| `focusOrOpenMainWindow` | `window:focusOrOpenMain` | 聚焦或新建主窗口 |
| `openFileInMainWindow` | `window:openFileInMain` | 在主窗口打开文件 |
| `openFileInNewWindow` | `window:new` | 新窗口打开文件 |
| `setFullscreen` | `window:setFullscreen` | 全屏 |
| `setWindowTitle` | `window:setTitle` | 设置标题 |
| `getWindowContentBounds` | `window:getContentBounds` | 获取窗口尺寸 |
| `shouldRestoreSession` | `window:shouldRestoreSession` | 是否恢复会话 |
| `toggleDevTools` | `window:toggleDevTools` | DevTools |
| `quitApp` | `app:quit` | 退出 |
| `proceedCloseWindow` | `window:proceedClose` | 确认关闭 |
| `setNativeTheme` | `theme:set` | 主题 |

### 6.2 文件与路径

| API | 用途 |
|-----|------|
| `showOpenDialog` / `showSaveDialog` / `showMessageBox` / `alert` / `confirm` | 系统对话框 |
| `listTxtFilesInDirectory` / `onDirListTxtScan` | 列目录 TXT |
| `stat` / `getPath` / `getUserDataPath` | 文件信息/路径 |
| `pathToFileUrl` / `pathToReadableLocalUrl` | 路径转 URL |
| `readFileAsArrayBuffer` / `readWholeTextFile` | 读文件 |
| `writeTextFile` / `writeUtf8File` / `writeBinaryFile` | 写文件 |
| `emptyDir` / `removePath` / `mkdir` / `listFilesRecursive` / `renamePath` | 目录操作 |
| `streamFile` / `onStreamStart` / `onStreamChunk` / `onStreamEnd` | 流式读文件（大文件） |
| `watchCurrentFile` / `onCurrentFileDiskChanged` | 监听磁盘变化 |
| `openPath` / `showItemInFolder` / `openExternal` | shell 操作 |

### 6.3 书源与找书

| API | 用途 |
|-----|------|
| `bookSourceList` / `bookSourceGet` / `bookSourceSave` / `bookSourceDelete` / `bookSourceToggle` | 书源 CRUD |
| `bookSourceImportPreview` / `bookSourceImportCommit` | 导入书源 |
| `bookSourceFetchUrl` / `bookSourceFetchUrlAbort` | 校验/抓取 URL |
| `bookSourceSearch` / `bookSourceSearchCancel` / `bookSourceSearchLoadMore` / `onBookSourceSearchEvent` | 搜索 |
| `bookSourceDownload` / `bookSourceDownloadCancel` / `onBookSourceDownloadEvent` | 下载 |
| `bookSourceGetLoginInfo` / `setLoginInfo` / `getLoginUi` / `browserLogin` / `removeLoginHeader` / `clearCookie` | 登录 |
| `bookSourceExploreKinds` / `exploreBooks` / `exploreClearKindsCache` | 发现 |
| `bookSourceReorder` / `payAction` | 排序/付费 |
| `createFindBookDesktopShortcut` / `supportsFindBookDesktopShortcut` | 桌面快捷方式 |

### 6.4 词典 / 翻译

| API | 用途 |
|-----|------|
| `dictionaryLookup` / `dictionaryImport` / `dictionaryRemove` | 词典 |
| `translateText` | 翻译（OpenCC 文本转换见下） |

### 6.5 文本转换

| API | 用途 |
|-----|------|
| `convertTextOpenCc` | OpenCC 繁简/字母/数字转换 |

### 6.6 语音朗读

| API | 用途 |
|-----|------|
| `voiceReadEdgeTts` / `voiceReadSynthesize` / `voiceReadCancelSynthesis` | TTS 合成/取消 |
| `voiceReadListVoices` / `voiceReadHealthCheck` / `voiceReadAttributeSpeakers` | 音色列表/健康检查 |

### 6.7 AI

`window.colorTxt.ai.*` 命名空间：

| API | 用途 |
|-----|------|
| `configGet` / `configSet` | AI 配置 |
| `embed` / `embedAbort` | 文本嵌入 |
| `indexHasBook` / `indexDeleteBook` / `indexSearch` / `indexReplaceChunks` | 向量索引 |
| `segmentRebuildBook` / `segmentDeleteBook` | 分段缓存 |
| `wordcloudRun` / `wordcloudAbort` | 词云 |
| `chatStart` / `agentStart` / `chatAbort` | 对话/Agent |
| `textFormatCleanup` / `textFormatAbort` | AI 智能排版 |
| `modelsList` / `testChat` / `testEmbedding` / `embeddingProbeDimension` | 模型测试 |
| `embeddingBuiltinList` / `load` / `isCached` / `clearCache` / `onEmbeddingLoadProgress` | 内置嵌入模型 |
| `threadList` / `threadCreate` / `threadRename` / `threadDelete` / `messageList` / `messageAppend` | 对话线程与消息 |
| `portraitExtract` / `portraitGoldenQuotes` / `portraitTranslateSdPrompt` | 角色卡信息提取 |
| `txt2imgInvoke` | 文生图 |
| `exportSave` | 导出保存 |

### 6.8 WebDAV

`window.colorTxt.webdav.*`：`test` / `ensureLayout` / `list` / `getText` / `getToFile` / `putText` / `putFile` / `mkdir` / `delete` / `onTransferProgress` / `abortTransfer`

### 6.9 密钥

`window.colorTxt.secrets.*`：加密能力检测、语音/WebDAV/翻译密钥读写。

### 6.10 隐身阅读 & 取色器

见第五节。

### 6.11 主进程 → 渲染进程推送事件

| 事件 | 触发时机 |
|------|---------|
| `window:fullscreen-changed` | 进入/退出全屏 |
| `window:requestClose` | 请求关闭窗口（用户点关闭） |
| `theme:sync` | 主题同步（多窗口） |
| `file:stream-start/chunk/end/error` | 文件流式读取进度 |
| `file:disk-changed` | 当前文件磁盘变化 |
| `findBook:activateTab` | 激活找书指定标签 |
| `app:open-txt-path` | shell 打开文件时推送路径 |
| `updater:*` | 更新相关（available/download-progress/downloaded/error） |
| `ai:embedding:loadProgress` | 嵌入模型加载进度 |
| `bookSource:searchEvent` / `downloadEvent` | 搜索/下载进度事件 |
| `webdav:transferProgress` | WebDAV 传输进度 |

---

## 七、界面跳转与功能串联

### 7.1 主窗口核心阅读流

```
打开文件（顶部栏/拖拽/最近文件）
  → ReaderMain 渲染文本
  → 侧栏自动切到「文件」或「章节」
  → 选中文字 → 选中工具条 → 高亮/笔记/词典/翻译/AI
  → 顶栏：字体/格式/章节规则/配色调整
  → 底部栏：阅读进度、编码保存、番茄钟
  → 语音朗读工具条：TTS 朗读
```

### 7.2 找书串联流

```
主窗口 → 找书（F7/更多菜单）
  → 找书窗口「找书」Tab：搜索 → 结果列表
  → 点击结果 → 书籍详情弹窗
  → 详情底部：①放入书架（+分类）②开始/继续阅读 ③下载/停止（产出 TXT 或仅缓存）
  → 在线阅读 → FindBookReader（独立阅读器，缓存优先加载章节）
  → 书架 Tab：管理已加入书籍，重新阅读
  → 书源管理（F8）：导入/编辑/校验书源
  → 设置：下载目录、代理等
```

### 7.3 主窗口与找书窗口的互通

- 主窗口 → 找书：`openFindBookWindow`
- 找书 → 主窗口：`focusOrOpenMainWindow`
- 找书下载/导出的 TXT 可在主窗口中打开阅读

### 7.4 设置与配色的多入口

同一个设置/配色面板可从多处打开：
- **设置**：顶部栏更多菜单 / 侧栏设置图标 / 快捷键
- **配色**：顶部栏更多菜单 / 侧栏配色图标 / 顶栏主题切换（仅明暗）
- **章节规则**：顶栏章节规则按钮
- **词典/搜索/翻译管理**：选中文本工具条 / 设置面板入口

---

## 八、关键文件索引

| 类别 | 文件路径 |
|------|---------|
| 主进程入口 | `src/main/index.ts` |
| 窗口工厂 | `src/main/windowFactory.ts` |
| IPC 注册（通用） | `src/main/ipcHandlers.ts` |
| 书源 IPC | `src/main/bookSource/registerBookSourceIpc.ts` |
| 词典/翻译/语音/WebDAV/AI/密钥/文本转换 IPC | `src/main/{dictionary,translation,voiceRead,webdav}/register*Ipc.ts`, `registerAiIpc.ts`, `registerSecretsIpc.ts`, `registerTextConvertIpc.ts` |
| preload 桥 | `src/preload/index.ts` |
| 主窗口根 | `src/renderer/src/App.vue` |
| 找书窗口根 | `src/renderer/src/FindBookWindow.vue` |
| 找书面板 | `src/renderer/src/bookSource/components/FindBookPanel.vue` |
| 顶栏/侧栏/底栏/阅读器 | `src/renderer/src/components/{AppHeader,ReaderSidebar,AppFooter,ReaderMain}.vue` |
| 弹层聚合 | `src/renderer/src/components/AppOverlays.vue` |
| 设置面板 | `src/renderer/src/components/SettingsPanel.vue` + `SettingsTabBar.vue` |
| 配色面板 | `src/renderer/src/components/ColorSchemePanel.vue` + `ColorSchemeTabBar.vue` |
| 隐身阅读 | `src/renderer/src/StealthReaderApp.vue`, `src/main/stealthReader.ts` |
| 取色器 | `src/renderer/eyedropper.html`, `src/main/eyedropper.ts` |

---

# 九、各窗口具体功能与交互逻辑（含真实调用链）

> 本章逐个窗口说明"它能做什么、用户怎么操作、内部按什么顺序执行"。
> 调用链格式：`UI 触发（文件:行号）→ 中间处理（函数 文件:行号）→ 最终执行（IPC/存储）`，均可在源码中核对。

## 9.1 主窗口

### 9.1.1 应用启动与会话恢复

主进程决定首窗形态（`src/main/index.ts:87-96`）：

- 命令行带 `--find-book` → 只开找书窗（书架页）：`openFindBookLaunchWindow(createWindow, "bookshelf")`（`index.ts:90`）
- 有关联打开的 txt → `createWindow({ openTxtPath: launchTxt })`（`index.ts:93-94`）
- 普通启动 → 开空白主窗，由渲染层按"是否恢复上次会话"决定加载内容

窗口工厂给每个窗口打标记（`windowFactory.ts:101-109`）：主窗口记 `shouldRestoreSession`，找书窗记 `findBookWindowByWindowId`。
渲染层首屏通过同步 IPC 拿意图：`window.colorTxt.getInitialWindowLoadIntent()` → 通道 `window:getInitialLoadIntent`（`ipcHandlers.ts:414-435`），返回 `{ shouldRestoreSession, hasPendingOpenTxt, isFindBookWindow, findBookInitialTab }`。

### 9.1.2 打开文件：对话框 → 流式读取 → 编码检测 → Monaco 渲染

```
点击「打开文件」AppHeader @openFile（AppHeader.vue:255）
→ App.vue openFileViaDialog
→ useAppFileSession.openFileViaDialog()（useAppFileSession.ts:521-534）
   · window.colorTxt.showOpenDialog(...) 选文件
   · openFilePath(filePath)：计算阅读锚点 → resetSession(path)（:502）
   · window.colorTxt.streamFile(physicalPath)（:507-509）
→ 主进程 ipcMain「file:stream」（ipcHandlers.ts:847-851）
   · detectEncoding() 探测编码（detectTextEncoding.ts:114-164）
   · iconv-lite 解码，分块推送 file:stream-start/chunk/end（ipcHandlers.ts:908-932）
→ 渲染层 useTxtStreamPipeline
   · onStreamChunk → processChunk 按物理行切分累积（useTxtStreamPipeline.ts:247-252）
   · 完成后写入 Monaco 展示层并 afterFullTextInstalled()（:368-380）
```

补充交互：
- 侧栏"选择目录/选择文件"只把书加入文件列表不立即打开（`pickTxtFilesIntoFileList`，`useAppFileSession.ts:537-548`）。
- 支持拖拽到阅读区打开（App.vue 阅读器 `data-drop-zone="reader"`，有 `readerDropOverlay` 遮罩提示）。
- 打开后恢复上次阅读位置：优先用 Monaco viewState，其次书包锚点视口行，再次滚动行（`useAppFileSession.ts:480-501`）。

### 9.1.3 章节识别与跳转

- 章节切分在渲染层 `chapter.ts` 的 `getChapterMatchRules`，用用户配置/内置正则把物理行划分成章节（含"第X回后必须空白或行尾"规则）。
- 侧栏章节点击：`ChapterListPanel @jump-to-chapter` → App.vue `onJumpToChapterFromSidebar`（App.vue:2397-2399）→ `useAppChapterNavigation.jumpToChapter`（:82-101），根据阅读尺/朗读状态选择 `scrollChapterTitleToRulerFocus` 或 `scrollToLineNearTop`，并更新 `activeChapterIdx`。
- 反向同步：滚动时 ReaderMain emit `probeLineChange` → `onProbeLineChange`（useAppChapterNavigation.ts:133-153）反查当前行所属章节高亮侧栏，并在节流后写入最近文件进度。
- 上一章/下一章：`ReaderChapterNavBar` → `jumpToPrevChapterWithVoiceRead/Next`（朗读时会先让朗读跟随）。

### 9.1.4 阅读模式与编辑模式

- 顶栏编辑按钮 `toggleReaderEdit` 切换。阅读态 Monaco 只读；编辑态可改正文。
- 进入编辑：ReaderMain 用探测编码 `readWholeTextFile` 读全文（ipcHandlers.ts:587-593 先 detectEncoding 再 iconv.decode），打开行号/缩略图等（由 `SettingsEditPanel` 配置）。
- 保存：顶栏保存 `saveReaderFile` → ReaderMain `readerEditSaveRequest` → `window.colorTxt.writeTextFile(path, content, encoding)`，写回后刷新章节列表。
- 局部编辑：选区 → `ReaderPartialEditPanel` → `applyPartialPhysicalEdit`（App.vue:4160）只替换物理行片段。
- AI 智能排版：编辑态顶栏按钮全书排版（`aiSmartFormatFull`），或选区右键排版（`aiSmartFormatSelection`）；完成后进入"差异审阅"，`SmartFormatReviewBar` 可应用/放弃。插口 `ai.textFormatCleanup` / `ai.textFormatAbort`，进度弹窗 `AiSmartFormatProgressModal`。

### 9.1.5 选中文字与标注体系（阅读态核心交互）

选中文字弹出 `ReaderSelectionToolbar`，动作分两类（`ReaderSelectionToolbar.vue:11-21`）：

| 动作 | 处理 |
|------|------|
| copy 复制 | 写剪贴板 |
| highlight 高亮 | 弹颜色盘 → `highlightPickConfirm(colorIndex)` → App.vue `onAddHighlightTerm` |
| marker/wavy/straight 划线 | 弹标注色盘 → `lineationPickConfirm` → `upsertReaderAnnotation` |
| note 笔记 | `ReaderNoteInputPanel` 输入 → 与划线绑定写标注 |
| find 查找 | 用选中文本唤起查找 |
| dictionary 词典 | `ReaderDictionaryPopup` → `dictionaryLookup` IPC |
| translate 翻译 | `ReaderTranslatePopup` → `translateText` IPC |
| askAi 问AI | `askAiWithQuote` → 把引文带入 AI 助手 |

落库链路（高亮为例）：
```
onAddHighlightTerm（useAppHighlightTerms.ts:190-200）
→ assignHighlightTermToColorForFile（fileMetaStore.ts:680-694）
→ upsertFileMetaRecord 更新 highlightWordsByIndex 并持久化
→ 合并生成 readerDisplayHighlightWordsByIndex（useAppHighlightTerms.ts:94-124）
→ ReaderMain 用 monacoCustomHighlight 做窗口化上色渲染
```
标注/高亮/笔记都按"文件"隔离存储，可在侧栏对应 Tab 导入/导出 JSON/MD。

### 9.1.6 语音朗读流水线

```
顶栏语音按钮 voiceReadToggle（AppHeader.vue:354-363）
→ useAppVoiceRead（composables/useAppVoiceRead.ts）
   · 从当前视口首行 startFromViewportTop（:848）
   · getReaderLineContent 取行文本（:231），可按说话人拆块 buildLineSpeakChunksWithSpeakers（:249）
   · 合成：services/voiceRead/voiceReadSynthesisClient.ts:74 → window.colorTxt.voiceReadSynthesize
   · 播放：services/voiceRead/voiceReadLinePlayer.ts（音频缓存 voiceReadAudioCache）
   · 播完自动推进到下一行；到章末 handleDocumentEndReached（:542）自动换章
   · applyPlaybackLineHighlight（:581）高亮当前朗读行并跟随滚动
```
- 工具条 `VoiceReadToolbar`：播放/暂停、上一行/下一行、重新生成、停止、语速/音量、发音设置。
- 朗读中章节跳转走专门分支（useAppChapterNavigation.ts:82-98 不用阅读尺居中）。
- 引擎：Edge TTS / 系统 SAPI / 火山 / MiniMax / DashScope（`src/main/voiceRead/providers/*`）。

### 9.1.7 阅读进度、设置数据的持久化

- 统一通过 `stores/cacheStore.ts` 读写浏览器 `localStorage`（键名 `persistKey`，见 cacheStore.ts:823-886）。
- 每本书的元数据（进度、高亮、标注、角色、编码等）在 `fileMetaStore.ts` 的 `FileMetaRecord`。
- 最近文件在 `stores/recentHistoryStore.ts`（`fileHistoryKey` 归一化路径，:12）；滚动探测到行后 `touchRecentFile` 更新进度。
- WebDAV 书包可把这些数据打包上传/恢复（底栏路径菜单 / WebDavSyncPanel）。

### 9.1.8 定时滚动、番茄钟、阅读尺

- 定时滚动：顶栏 `timedScrollToggle`，按 `timedScrollSettings`（范围、间隔毫秒）自动滚；ReaderMain emit `probeLineChange` 供其探测。
- 番茄钟：底栏 `PomodoroFooterControl` 开始/暂停/切显示/停止；专注结束弹 `PomodoroBreakOverlay` 休息遮罩；时长在 设置→阅读 配置。
- 阅读尺：顶栏开关，聚焦当前 N 行、其余压暗（焦点行数/压暗透明度/黏贴标题/过渡均可配）。

### 9.1.9 三种沉浸态：普通 / 极简 / 全屏 / 摸鱼

- 极简 `toggleMinimalist`：隐藏外壳只留阅读。
- 全屏 `toggleFullscreen`：`window.colorTxt.setFullscreen`；主进程推送 `window:fullscreen-changed`（windowFactory.ts:193-198），顶栏/侧栏改为鼠标悬停浮层（`chromeAutoHide`），底栏内嵌章节导航。
- 摸鱼：另开独立隐身窗（见 9.3）。
- 点击模式：顶栏在"点击翻页/文字选择"间切换（ReaderMain 用指针手势 `clickModeGesture`，ReaderMain.vue:3702 起），按住 Alt 临时反转模式（useReaderClickModeAltHold.ts）。

## 9.2 彩读找书窗口

### 9.2.1 窗口打开、复用与独立启动

```
主窗口「找书」按钮 → window.colorTxt.openFindBookWindow（preload:733-735）
→ ipcMain「window:openFindBook」（ipcHandlers.ts:363-368）
→ focusOrOpenFindBookWindow：已有找书窗则聚焦，否则 createWindow({openFindBook:true})
「新建找书窗」→「window:newFindBook」（ipcHandlers.ts:371-373）→ 始终新建且默认书架页
桌面快捷方式/CLI：--find-book（findBookLaunch.ts:11）→ index.ts:90 直接开书架页
```
- 找书窗读 URL 参数 `?tab=bookshelf` 决定首标签（windowFactory.ts:131-153，FindBookPanel 解析于 :115 附近）。
- 找书窗与主窗口是两个独立 BrowserWindow，可同时存在；找书窗"主界面"按钮 `focusOrOpenMainWindow`（preload:754-755 → ipcHandlers.ts:379-385）。
- 桌面快捷方式由 PowerShell 生成 `.lnk`（findBookLaunch.ts:46-97）。

### 9.2.2 搜索：多书源并发 + 事件流 + 分页

```
搜索框回车 onSearchSubmit/onSearchAction（FindBookPanel.vue:998-1008，记录历史）
→ useBookSourceSearch（useBookSource.ts:287-379）
   · window.colorTxt.bookSourceSearch(key,{sourceUrls,precisionSearch}) 拿 searchId
   · onBookSourceSearchEvent 订阅 progress/sourceDone/result/loadMore/done
→ 主进程 searchService
   · startSearch 建会话（:343-386）
   · runInitialSearch 对启用书源并发搜索（:221-280）
   · runLoadMore 仅对 hasMore 书源翻页（:283-340）
   · cancelSearch 取消（:343 附近）
→ 结果增量渲染到 FindBookListItem；滚动触底自动 loadMore（useBookSource.ts:381-402）
```
- UI 显示进度条、完成/总数、结果数、搜索日志按钮；可指定单一书源（`searchScope`）或精准搜索（`precisionSearch`）。
- 搜索历史存本地，标签可点回填、可清空。

### 9.2.3 书籍详情弹窗的四个动作

`BookDetailPanel.vue` 底部（:1170-1222）：

| 按钮 | 函数 | 逻辑 |
|------|------|------|
| 放入书架/从书架移除 | `onToggleBookshelf`（:454） | 写本地书架，加入时同步目录缓存与最新章 |
| 分类 | `onCategoryBtnClick` | `CategoryPickerMenu` 选/建分类 |
| 开始/继续阅读 | `onStartOrContinueReading` | 打开内置阅读器，续读上次章 |
| 下载/停止 | `onDownloadOrStop`（:815） | 走下载会话，可中途停止 |

头部更多菜单还有：复制书名链接/目录链接、编辑书源、设置来源/书籍变量、清除本章缓存（:914-957）。

### 9.2.4 书架数据存储

`bookSource/findBookBookshelf.ts`：
- `loadFindBookBookshelf()` 读 `localStorage["colortxt:findBookBookshelf"]`（:107 附近）
- `saveFindBookBookshelf()` 写回；`addToFindBookBookshelf()` 去重新增
- 书架项含书名、作者、来源、封面、最新章、分类、上次阅读章、缓存的目录（tocUrl+chapters）

书架页 `FindBookshelfPanel` 支持筛选、分类、排序、管理态；点书 → `bookshelfOpenReader.loadBookshelfReaderPayload`（bookshelfOpenReader.ts:20-99）：已有缓存目录直接用；否则 `bookSourceGetBookInfo` + `bookSourceGetChapterList` 拉目录并回写书架。

### 9.2.5 在线阅读：缓存优先 + 展示管线 + 进度回写

`useFindBookChapterSession.loadChapterAtDisplayIndex`（useFindBookChapterSession.ts:556-679）：

```
切章（侧栏/上一章/下一章，考虑正倒序 chapterReadingOrder）
→ isChapterCached(ch)？命中缓存则不显示遮罩，否则置 loading
→ scrollChapterListToCurrent 先跑侧栏居中动画
→ loadChapterContent({bookSourceUrl,chapterUrl,cacheDir,preferCache,nextChapterUrl,chapterUrls})
   · 主进程 getChapterContentWithCache.ts / chapterCache.ts：先查 book_cache，未命中走网络
→ markChapterCached(url) 标记（:659）
→ renderChapterText（:276）：套用替换规则 + 文本转换（繁简/全半角）+ 压缩空行/缩进
→ 在书架中则 updateReadProgress 回写上次章（:667-669）
→ 滚动到顶部（或上一章边界切章时滚动到底部）
```
- 分卷标题不拉正文，仅显示卷名（:574-591）。
- 编辑保存：`onSaveReaderChapter`（:429）/局部编辑 `onApplyPartialPhysicalEdit`（:474）写回缓存并 `markChapterCached`。
- 阅读器头/侧栏/底是独立三件套（FindBookReaderHeader / ChapterSidebar / Footer）。

### 9.2.6 下载全书：TXT 文件 与 仅缓存 两种模式

```
详情「下载」→ useBookSourceDownload.download(item, outputDir, cacheDir, {cacheOnly})
   （useBookSource.ts:473-537）
   · onBookSourceDownloadEvent 收 progress/done/error
   · bookSourceDownload IPC → 主进程 downloadService.ts 并发拉章、写盘
   · cacheOnly:true 时 outputDir 传空，只写 book_cache；否则拼写成 .txt 写到下载目录
   · bookSourceDownloadCancel 停止（:540-548）
→ 完成回调 runFindBookDownloadAfterAction（findBookDownloadActions.ts:11-42）
   · 可选加入主界面文件列表（findBookDownloadToFileList.ts 写 localStorage 文件清单+分类）
   · afterAction：none / openMain（openFileInMainWindow）/ openNewWindow（openFileInNewWindow）
```
下载目录、并发数、完成后动作在 找书设置→下载（FindBookSettingsDownloadPanel）配置。

### 9.2.7 书源管理与三种导入

入口：找书窗"更多→书源管理"（快捷键 F8）。列表 `BookSourcePanel`：启用开关、编辑、删除、勾选、排序、校验、批量探索、导出所选。

三种导入（BookSourcePanel.vue:695-735 / 按钮 :837-843）：

| 来源 | 读取方式 | 插口 |
|------|---------|------|
| 本地导入 | `importFromFile` 选 JSON 文件 | `bookSourceReadFile` |
| 网络导入 | `importFromNetwork` 拉 URL（可中止） | `bookSourceFetchUrl` / `bookSourceFetchUrlAbort` |
| 剪贴板导入 | `navigator.clipboard.readText` 解析 | 纯渲染层 |

三者都先得到预览列表 → 打开 `ImportBookSourcePanel`（默认勾选 status 为 new/update 的项，可筛选/全选/编辑）→ `commitImport` → `bookSourceImportCommit` 落库（主进程 `bookSourceStore.ts`）。
登录类书源用 `BookSourceLoginPanel`：`bookSourceGetLoginUi/browserLogin/getLoginInfo/setLoginInfo/clearCookie`。

### 9.2.8 发现页

`FindDiscoverPanel` → 先 `bookSourceExploreKinds(sourceUrl)` 拿某源的发现分类，再 `bookSourceExploreBooks(payload)` 按分类列书；可清分类缓存。主进程 `bookSource/engine/exploreKinds.ts`。

### 9.2.9 找书设置（6 Tab）

`FindBookSettingsTabBar`：下载（目录/并发/完成动作）、阅读、编辑、语音朗读、代理、WebDAV。
与主窗口设置相比，找书设置**没有**常规/AI/向量模型/角色卡/技能这些标签；代理设置经 `syncPersistedFindBookProxyToMain` 同步给主进程网络层。

## 9.3 隐身（摸鱼）阅读窗

**用途**：透明、无边框、可伪装成终端的小窗，供 discreet 阅读，内容由主窗口"投影"过来。

**启动**：主窗口"摸鱼模式" → `window.colorTxt.stealthReaderEnter(payload)`，主进程 `stealthReader.ts` 建窗加载 `StealthReaderApp.vue`；payload 带当前页文本、章节列表、起始行。

**交互逻辑**（StealthReaderApp.vue）：

| 操作 | 处理（行号） |
|------|------------|
| 左/右半屏点击 | `requestPageFlip(-1/1)`（:295）：本页翻不动时自动 `chapterPrev/chapterNext`（:311-318） |
| 滚轮（悬停时） | `onWheel`（:942-970）：默认逐行滚；Ctrl+滚轮改字号，Ctrl+Alt 改行高，Alt 改透明度，Shift 改文字透明度 |
| 右键 | `onContextMenu`（:702-707）→ 主进程原生菜单 `stealthReaderPopupMenu` |
| 拖动窗口 | `onPointerDown/onPointerMove/onPointerUp`（:791 起），点边缘 8 个 `.edge` 手柄缩放（:825 `applyResize`） |
| 双击 | `onDoubleClick`（:1067） |
| 首次点击提示 | 左右半屏"上一页/下一页"引导层，点过消失 |

**与源窗联动换章**：
- 菜单/快捷键命令经 `onStealthReaderCommand` → `onCommand`（:716-731）：pagePrev/pageNext/chapterPrev/chapterNext/exit/openSettings/toggleTimedScroll/reloadPayload。
- 到章末翻页 → `chapterNext` 请求源主窗取下一章 → 主进程回推 `onStealthOwnerChapterNav` → 热换章 `applyPagePayload`（:997）不重启提示层；加载中显示"加载中"。
- 设置窗：`openStealthSettingsWindow`（摸鱼设置窗改字体/颜色/透明/快捷键，存 localStorage `STEALTH_SETTINGS_KEY`）。
- 退出：`exitStealth`（:709-714）先存设置与窗口尺寸，再 `stealthReaderExit(currentLine)` 把当前行回写源窗定位。
- 透明刷新：`stealthReaderRefreshTransparency(nudge)` 应对 Windows DWM 不重绘。

## 9.4 摸鱼设置窗

- 独立小窗 `StealthSettingsApp.vue`，由摸鱼窗右键菜单打开。
- 改字体族（含"终端默认"，主进程 `fonts:getTerminalDefaultFace` 解析）、字号、行高、文字/背景色、透明度、导航快捷键。
- 保存写 localStorage，摸鱼窗监听 `storage` 事件即时生效（StealthReaderApp.vue `onSettingsStorage` :636）。
- 插口：`STEALTH_SETTINGS_IPC.open/close`（stealthSettingsWindow.ts:143-152）。

## 9.5 取色器窗

**用途**：在配色面板里拾取屏幕任意像素颜色（含跨显示器）。

调用链（`src/main/eyedropper.ts:264-313`）：
```
配色面板取色按钮 → window.colorTxt.eyedropperPick()
→ registerEyedropperIpc「pick」（:266）
   · 若摸鱼窗存在先 prepareStealthForEyedropper 临时处理
   · captureAllDisplays() 截所有显示器
   · 每个显示器建一个全屏覆盖 BrowserWindow（加载 eyedropper.html）
→ 覆盖窗 ready（EYEDROPPER_IPC.ready，:293）→ 主进程回传当前指针像素信息 pointer
→ 用户移动/点击：渲染层 eyedropperHover/Sample 实时显示，单击 eyedropperSubmit(hex)（:307-313）
→ finish(hex) 关闭全部覆盖层、恢复摸鱼窗，把 hex 返回给配色面板
   · Esc/EyedropperCancel 取消；eyedropperCopy 复制；eyedropperToggleFormat 切换 HEX/RGB
```

## 9.6 后台 WebView（不可见辅助窗）

- `src/main/bookSource/engine/backstageWebView.ts` 创建 `show:false` 的隐藏 BrowserWindow。
- 用于需要真实浏览器环境的书源：登录态、Cookie、JS 渲染校验（`BookSourceLoginPanel` 的浏览器登录、`checkSourceService` 校验）。
- 用户窗口全部关闭时统一 `destroyAllBackstageWebViews`（windowFactory.ts:115-127，index.ts:122-125），防止进程不退。

## 9.7 数据与状态落点汇总

| 数据 | 位置 |
|------|------|
| 设置/UI 偏好/文件元数据/最近文件/文件清单 | 渲染层 `localStorage`（经 `cacheStore.ts`，键 `persistKey` / `fileListKey`） |
| 找书书架 | `localStorage["colortxt:findBookBookshelf"]`（findBookBookshelf.ts） |
| 找书章节缓存 | 用户配置下载/缓存目录下 `book_cache`（MD5 名 `.nb` 明文） |
| 下载的 TXT | 用户配置下载目录（`DownloadedBooks` 等） |
| 密钥（API Key / WebDAV 密码） | Electron safeStorage（`secretStorage.ts`，`secrets:*` IPC） |
| 窗口尺寸/位置 | `windowBounds.ts`（resize/move 防抖写、close 兜底） |
| 用户数据根目录 | `app.getPath("userData")`（安装版 `%AppData%/colortxt`） |

---

# 十、交互点 ↔ 程序插口 ↔ 调用链速查（逐点对应）

> 阅读方法：每个交互点一行，五段对应——
> **UI 事件**（组件模板绑定，行号在 App.vue / FindBookPanel.vue）→ **处理函数**（App.vue 或 composables）→ **window.colorTxt API**（preload/index.ts 行号）→ **IPC 通道** → **主进程注册点**。
> 标注"渲染层"表示不经过 IPC（Monaco 操作 / localStorage 持久化 / 组件内状态）。
> 行号基于当前版本，通道名以 `src/shared/bookSource/ipc.ts` 与 preload 为准。

## 10.1 主窗口 · 顶部栏 AppHeader

| 交互点 | App.vue 绑定(行号) → 处理函数 | 插口 API（preload:行号） | IPC 通道 → 主进程 |
|--------|------------------------------|--------------------------|------------------|
| 打开文件 | `@open-file`（:3818）→ `openFileViaDialog` | `showOpenDialog`（:193）→ `streamFile`（:664） | `dialog:showOpenDialog`、`file:stream` → ipcHandlers.ts:847 |
| 书钉 | `@pin-click`（:3819）→ `onPinClick` | 渲染层（行状态） | — |
| 书签 | `@bookmark-click`（:3820）→ `onBookmarkClick` | 渲染层（弹添加书签对话框，存 fileMetaStore） | — |
| 书钉回跳 | `@go-back-from-pin`（:3821）→ `onGoBackFromPin` | 渲染层（Monaco reveal） | — |
| 明暗主题 | `@change-theme`（:3822）→ `applyShellTheme`（:3625） | `setNativeTheme`（:710） | `theme:set` → ipcHandlers.ts |
| 极简模式 | `@toggle-minimalist`（:3823）→ `toggleMinimalistView` | 渲染层（外壳显隐） | — |
| 全屏 | `@toggle-fullscreen`（:3824）→ `enterOrExitFullscreenView`（:3625，useAppReaderChrome.ts:216-235） | `setFullscreen`（:681） | `window:setFullscreen` → ipcHandlers.ts；回推 `window:fullscreen-changed`（:815） |
| 字体选择 | `@set-monaco-font`（:3825）→ `setMonacoFontFamily` | 渲染层（首次可选字体时 `listSystemFonts`:713 → `fonts:listSystemFonts`） | — |
| 固定字体 | `@toggle-pin-other-font`（:3826）→ `togglePinnedOtherFont` | 渲染层 + localStorage | — |
| 字号 ± | `@increase/decrease-font-size`（:3827-3828） | 渲染层（更新 monaco options） | — |
| 行高 ± | `@increase/decrease-line-height`（:3829-3830） | 渲染层 | — |
| 高级换行 | `@toggle-monaco-advanced-wrapping`（:3831） | 渲染层（Monaco wordWrap） | — |
| 内容上色 | `@toggle-monaco-custom-highlight`（:3832） | 渲染层（高亮窗口化渲染开关） | — |
| 压缩空行（阅读） | `@toggle-compress-blank-lines`（:3833） | 渲染层（展示管线重排） | — |
| 行首缩进（阅读） | `@toggle-lead-indent-full-width`（:3834） | 渲染层 | — |
| 压缩空行（编辑） | `@format-edit-compress-blank-lines`（:3835）→ `onFormatEditCompressBlankLines` | 渲染层（ReaderMain.applyEditFormat*，App.vue:2603-2665） | — |
| 行首缩进（编辑） | `@format-edit-lead-indent-full-width`（:3836） | 渲染层 | — |
| 繁简/字母/数字转换（阅读） | `@select-text-convert-*`（:3837-3839） | 渲染层（展示管线；批量转换见 `convertTextOpenCc`:718 → `text-convert:opencc` → registerTextConvertIpc.ts） | — |
| 繁简/字母/数字转换（编辑·落盘） | `@apply-text-convert-*-edit`（:3840-3842）→ `onApplyTextConvertZhEdit` 等 | `convertTextOpenCc`（:718） | `text-convert:opencc` → registerTextConvertIpc.ts:6-27 |
| 查找 | `@toggle-find`（:3843）→ `onToggleFind` | 渲染层（Monaco find 小窗） | — |
| 打开替换规则 | `@open-text-replace`（:3849）→ 置 `showReplaceRulePanel` | 渲染层（弹层） | — |
| 编辑/阅读切换 | `@toggle-reader-edit`（:3862）→ `onToggleReaderEdit`（:2548） | 进编辑读全文 `readWholeTextFile`（:472） | `file:readWholeTextFile` → ipcHandlers.ts:587-593 |
| 点击翻页模式 | `@toggle-reader-click-mode`（:3863）→ `toggleReaderClickMode` | 渲染层 | — |
| 阅读尺 | `@toggle-reading-ruler`（:3864）→ `toggleReadingRuler` | 渲染层 | — |
| 保存文件 | `@save-reader-file`（:3865）→ `onSaveReaderFile`（:2548-2600）→ `saveReaderBufferWithIpcEncoding`（:1032-1057） | `writeTextFile`（:476-478） | `file:writeTextFile` → ipcHandlers.ts |
| AI 全书排版 | `@ai-smart-format-full`（:3871）→ `onAiSmartFormatFull` | `ai.textFormatCleanup`（:962）/ `ai.textFormatAbort`（:967）；进度 `on("ai:text-format:progress")`（:1245） | `ai:text-format:cleanup/abort/progress` → registerAiIpc.ts |
| 语音朗读 | `@voice-read-toggle`（:3872）→ `onVoiceReadToggle`（:2387）→ voiceReadSynthesisClient.ts:74 | `voiceReadSynthesize`（:237）/`voiceReadCancelSynthesis`（:242）/`voiceReadListVoices`（:246） | `voiceRead:synthesize` 等 → registerVoiceReadIpc.ts:96-177 |
| 定时滚动 | `@timed-scroll-toggle`（:3873）→ `toggleTimedScroll` | 渲染层（定时器驱动滚动） | — |

## 10.2 主窗口 · 更多菜单 MoreMenu（App.vue 绑定 :3843-3861）

| 菜单项 | 处理函数 | 插口（preload:行号） | 通道 → 主进程 |
|--------|---------|---------------------|--------------|
| GitHub | `openGithubRepo`（:3850） | `openExternal`（:723） | `shell:openExternal` |
| 检查更新 | `requestCheckForUpdates`（:3851） | `updater.check`（:827）/`updater.download`（:831）/`quitAndInstall`（:835）；事件 `updater:*`（:838-867） | `updater:check/download/quitAndInstall` → registerUpdaterIpc.ts |
| 快捷键 | 置 `showShortcutPanel`（:3852） | 保存绑定时 `setGlobalShortcut`（:774） | `shortcut:setGlobalToggle` → globalShortcuts.ts |
| 设置 | 置 `showSettingsPanel`（:3853） | 渲染层（弹层） | — |
| 配色 | 置 `showColorSchemePanel`（:3854） | 渲染层（弹层；取色见 10.13） | — |
| 找书 | `openFindBookWindow`（:3855，函数 App.vue:2858） | `openFindBookWindow`（:734） | `window:openFindBook` → ipcHandlers.ts:363-368 |
| 摸鱼模式 | `enterStealthMode`（:3856） | `stealthReaderEnter` 等一组 stealth IPC | `stealthReader:*` → stealthReader.ts |
| 新窗口 | `openNewWindow`（:3857，App.vue:2858） | `openNewWindow`（:731） | `window:new` → ipcHandlers.ts:355-361 |
| 最近文件 | `openRecentFileFromHistory`（:3858） | 渲染层历史 → 复用打开文件链（10.1 打开文件） | — |
| 清除最近文件 | `clearRecentFiles`（:3859） | 渲染层（recentHistoryStore/localStorage） | — |
| 关于 | 置 `showAboutPanel`（:3860） | 版本号 `isPackaged`（:823） | `app:isPackaged` |
| 退出 | `quitApp`（:3861，App.vue:2858-2864） | `quitApp`（:783） | `app:quit` |
| 开发者工具（菜单内直接调） | MoreMenu.vue `onToggleDevTools` | `toggleDevTools`（:762） | `window:toggleDevTools` → ipcHandlers.ts:401-405 |

## 10.3 主窗口 · 侧栏 ReaderSidebar（绑定 App.vue:3959-4036）

**文件 Tab（FileListPanel）**

| 交互点 | 处理函数 | 插口（preload:行号） | 通道 |
|--------|---------|---------------------|------|
| 选择目录 | `pickTxtDirectory`（:3959） | `showOpenDialog`（:193）+ `listTxtFilesInDirectory`（:261） | `dialog:showOpenDialog`、`dir:listTxtFiles`（:262，扫描事件 `dir:listTxtFiles:scan`:268） |
| 选择文件加入列表 | `pickTxtFilesIntoFileList`（:3960，useAppFileSession.ts:537） | `showOpenDialog`（:193） | `dialog:showOpenDialog` |
| 拖入路径 | `onImportDroppedPathsFromList`（:3961） | 电子书转换走文件链 | — |
| 打开文件 | `openFileFromSidebar`（:3962） | 同 10.1 打开文件链 | `file:stream` |
| 清空列表/按分类清空 | `clearFileList` / `clearFileListForCategory`（:3968-3969） | 渲染层（localStorage 文件清单） | — |
| 移除条目 | `removeFileList`（:3970） | 渲染层 | — |
| 清除阅读数据 | `onClearFileMeta`（:3971，App.vue:1701-1707） | 渲染层（fileMetaRecords） | — |
| 重命名 | `onRenameFilePath`（:3972，App.vue:1419-1425） | `renamePath`（:499） | `fs:renamePath` |
| 替换文件 | `onReplaceFilePath`（:3973） | 渲染层改路径后重开 | — |
| 新窗口打开 | `onOpenFileInNewWindow`（:3974，App.vue:1696-1699） | `openFileInNewWindow`（:759） | `window:new`（带路径，ipcHandlers.ts:355-361） |
| 关闭当前文件 | `closeCurrentFile`（:3975） | 渲染层（清会话） | — |

**章节 / 书签 / 高亮 / 标注 / 搜索 / AI / 角色卡 Tab**

| 交互点 | 处理函数（App.vue:行号） | 插口 | 通道/落点 |
|--------|------------------------|------|----------|
| 点章节跳转 | `onJumpToChapterFromSidebar`（:3963，:2397） | 渲染层（Monaco reveal） | useAppChapterNavigation.ts:82-101 |
| AI 内跳章 | `jumpToChapterFromAiAssistant`（:3964） | 渲染层 | — |
| 刷新章节 | `applyChaptersFromReaderPlainText`（:3976） | 渲染层（重算正则） | — |
| 书签跳转 | `jumpToBookmarkWithVoiceRead`（:3977） | 渲染层 | — |
| 书签 清/删/编辑 | `clearCurrentFileBookmarks`/`removeCurrentFileBookmarks`/`onEditBookmark`/`onRemoveBookmark`（:3978-3981） | 渲染层（fileMetaStore） | — |
| 书签 导出/导入 JSON | `onExportBookmarksJson`/`onImportBookmarksJson`（:3982-3983） | `showSaveDialog`（:198）/`showOpenDialog`（:193）+ `writeUtf8File`（:468）/`readWholeTextFile`（:472） | `dialog:*`、`file:writeUtf8File`、`file:readWholeTextFile` |
| 全文搜索跳转 | `onJumpToSearchResult`（:3990） | 渲染层（Monaco find/reveal） | — |
| 高亮词 查找/移除/收藏/拆分/合并/提交分组/清空 | `onFindHighlightTermFromSidebar`/`onRemoveHighlightTerm`/`onFavoriteHighlightTerm`/`onUnfavoriteHighlightTerm`/`onCommitHighlightGroup`/`onMergeHighlightGroups`/`onSplitHighlightTerm`/`clearCurrentFileHighlightTerms`（:3984,3991-3997） | 渲染层（fileMetaStore） | — |
| 高亮/收藏 导入导出（4 项） | `onExportBookHighlightsJson` 等（:3998-4001） | 文件对话框 + `file:writeUtf8File`/`file:readWholeTextFile` | 同上 |
| 标注 跳转/删除/清空/清失效 | `onJumpToReaderAnnotation`/`onRemoveReaderAnnotation`/`onClearReaderAnnotationsWithConfirm`/`onClearStaleReaderAnnotations`（:4002-4005） | 渲染层（fileMetaStore）；确认框 `showMessageBox`（:203） | `dialog:showMessageBox` |
| 标注 导出 MD/JSON、导入 | `onExportAnnotationsMd`/`onExportAnnotationsJson`/`onImportAnnotationsJson`（:4006-4008） | 对话框 + `writeUtf8File`/`readWholeTextFile` | `file:*` |
| 角色卡补丁 | `onCharacterFileMetaPatch`（:4009） | 渲染层；立绘生成走 `ai.portrait.txt2imgToPath`（:1205） | `ai:portrait:txt2imgToPath` |
| 分类目录/归类 | `onApplyCategoryCatalog`/`onSetFilesCategory`（:4014-4015） | 渲染层（localStorage） | — |
| 侧栏 WebDAV/配色/设置 图标 | 置面板开关（:4033-4036） | 渲染层 | — |

## 10.4 主窗口 · 阅读器浮动交互（ReaderMain emit，绑定 App.vue:4133-4160）

| 交互点 | 处理函数（App.vue:行号） | 插口 | 通道 → 主进程 |
|--------|------------------------|------|--------------|
| AI 选区排版 | `onAiSmartFormatSelection`（:4134） | `ai.textFormatCleanup`（:962） | `ai:text-format:cleanup` |
| 审阅 应用/放弃 | `applySmartFormatReview`/`discardSmartFormatReview`（:4135-4136） | 渲染层 | — |
| 行探测（定时滚动/章节高亮） | `onProbeLineChangeForTimedScroll`（:4137） | 渲染层 | — |
| 视口行/进度变化 | `onViewportTopLineChange`/`onViewportEndLineChange`/`onViewportVisualProgressChange`（:4139-4141） | 渲染层（节流写 fileMetaStore/最近文件） | — |
| 加/删高亮词 | `onAddHighlightTerm`（:4142，useAppHighlightTerms.ts:190）/`onRemoveHighlightTerm`（:4143） | 渲染层（fileMetaStore.ts:680 upsertFileMetaRecord） | — |
| 增/删划线标注 | `onUpsertReaderAnnotation`/`onRemoveReaderAnnotation`（:4144-4145） | 渲染层（fileMetaStore） | — |
| 引文问 AI | `onAskAiWithQuote`（:4148） | AI 助手会话（`ai.agentStart`/`ai.chatStart` 等） | `ai:chat:*`/`ai:agent:event` |
| 引文网络搜索 | `onSearchWithQuote`（:4149） | `openExternal`（:723）按搜索引擎 URL | `shell:openExternal` |
| 打开词典/搜索/翻译管理 | 置面板开关（:4150-4152） | 渲染层 | — |
| 词典查询（弹窗内） | ReaderDictionaryPopup | `dictionaryLookup` | `dictionary:lookup` → registerDictionaryIpc.ts:28-123 |
| 翻译（弹窗内） | ReaderTranslatePopup | `translateText`（preload:1600 附近） | `translate:translate`（通道常量 translationTypes.ts:188）→ registerTranslationIpc.ts:9-28 |
| 编辑态内容/光标/加载 | `onReaderEditContentChange`/`onReaderEditCursorChange`/`onReaderEditLoaded`（:4155-4159） | 渲染层；加载用 `readWholeTextFile`（:472） | `file:readWholeTextFile` |
| 保存请求（编辑器内） | `onSaveReaderFile`（:4158） | `writeTextFile`（:476） | `file:writeTextFile` |
| 局部物理行编辑 | `onApplyPartialPhysicalEdit`（:4160） | 渲染层（编辑态内存改，保存时落盘） | — |
| 右键菜单 | ReaderMain.vue:283 生成 | 网络搜索 `openExternal`、AI 排版 `ai.textFormatCleanup` 等 | 同上 |

## 10.5 主窗口 · 朗读工具条 / 章节导航 / 底栏

**VoiceReadToolbar（绑定 :4174-4179）**

| 交互 | 处理 | 插口 |
|------|------|------|
| 播放/暂停 | `voiceReadTogglePlayPause`（:4174） | `voiceReadSynthesize`（:237）→ `voiceRead:synthesize` |
| 上一行/下一行 | `voiceReadPlayPrevLine/NextLine`（:4175-4176） | 渲染层取行 + 合成 IPC |
| 重新生成 | `voiceReadRegenerateCurrentLine`（:4177） | `voiceReadSynthesize`（:237） |
| 停止 | `exitVoiceRead`（:4178） | `voiceReadCancelSynthesis`（:242）→ `voiceRead:cancelSynthesis` |
| 发音设置 | 置 `showVoiceReadSpeakSettingsPanel`（:4179） | 渲染层 |

**ReaderChapterNavBar / 全屏底栏章节按钮（:4187-4188,4251-4252）**：`jumpToPrevChapterWithVoiceRead/Next` → 渲染层（朗读时联动）。

**AppFooter 路径/编码/番茄钟（绑定 :4286-4299）**

| 交互点 | 处理函数 | 插口（preload:行号） | 通道 → 主进程 |
|--------|---------|---------------------|--------------|
| 在文件夹中显示 | `revealCurrentFileInFolder`（:4286） | `showItemInFolder`（:725） | `shell:showItemInFolder` |
| 重新加载 | `reloadCurrentFileFromDisk`（:4287，:2946-2959） | 重新走 `streamFile`（:664） | `file:stream` |
| 重新转换电子书 | `reconvertCurrentEbookFromDisk`（:4288） | 转换后重新 `streamFile` | `file:stream` |
| 上传书包 WebDAV | `uploadCurrentReaderBookPackToWebDav`（:4289，:3024-3109） | `getPath`（:279）+`mkdir`（:492）+`writeBinaryFile`（:484）+ `webdav.putFile` | `app:getPath`、`fs:mkdir`、`file:writeBinaryFile`、`webdav:putFile` → registerWebDavIpc.ts:244-369 |
| 更新书包 WebDAV | `updateCurrentReaderBookPackFromWebDav`（:4290） | `webdav.getToFile`/`list` | `webdav:getToFile/list` → registerWebDavIpc.ts:88-242 |
| 导出书包 | `exportCurrentReaderBookPack`（:4291-4292） | `showSaveDialog`（:198）+`writeBinaryFile`（:484） | `dialog:showSaveDialog`、`file:writeBinaryFile` |
| 清除阅读数据 | `clearCurrentFileReadingData`（:4293） | 渲染层（fileMetaStore） | — |
| 关闭文件 | `closeCurrentFile`（:4294） | 渲染层 | — |
| 另存为编码 | `onFooterSaveFileAsEncoding`（:4295，:2714-2716） | `writeTextFile`（:476，带编码参数） | `file:writeTextFile` |
| 番茄钟 开始/暂停/切显示/停止 | `startPomodoro`/`togglePomodoroPause`/`togglePomodoroDisplayMode`/`stopPomodoro`（:4296-4299） | 渲染层（无 IPC） | — |
| 番茄休息结束 | `finishPomodoroBreakEarly`（:4306） | 渲染层 | — |

## 10.6 主窗口 · 弹层面板按钮（AppOverlays，绑定 :4435-4457）

| 交互点 | 处理 | 插口 / 落点 |
|--------|------|-------------|
| 设置面板"应用" | `applySettings`（:4435，App.vue:3424-3512） | 渲染层持久化；角色立绘目录变更时 `ai.migrateDataCacheRoot`（:1001）→ `ai:migrateDataCacheRoot` |
| 设置内固定字体 | `togglePinnedOtherFont`（:4436） | 渲染层 |
| 快捷键面板"应用" | `applyShortcutBindings`（:4437，App.vue:2924-2935） | `setGlobalShortcut`（:774）、`suspendForRecording`（:779）、`resumeAfterRecording`（:781）→ globalShortcuts.ts:86-164 |
| 章节规则"应用" | `applyChapterMatchRules`（:4438） | 渲染层（重算章节） |
| 添加/删除书签确认 | `confirmAddBookmark`/`confirmRemoveActiveBookmark`（:4439,4443） | 渲染层（fileMetaStore） |
| 配色"应用" | `onApplyColorScheme`（:4444，App.vue:3258-3308） | 渲染层（palette 持久化）；取色按钮走取色器（10.13） |
| 配色面板切主题 | `applyShellTheme`（:4445） | `setNativeTheme`（:710）→ `theme:set` |
| 阅读数据面板 打开/清理 | `openReadingDataPanel`/`onClearReadingDataPaths`/`onClearAllReadingData`/`onRemoveMissingReadingDataFiles`（:4446,4453-4455） | 渲染层（fileMetaStore/localStorage） |
| 替换规则"应用格式" | `onApplyReplaceRuleFormat`（:4457） | 渲染层（展示管线/编辑区重排） |
| WebDAV 面板配置下载 | `onWebDavConfigDownloaded`（:4334） | `webdav.*`（preload:364-445） |

## 10.7 找书窗口 · 顶部栏与更多菜单（FindBookPanel.vue）

| 交互点 | 处理函数（行号） | 插口（preload:行号） | 通道 → 主进程 |
|--------|-----------------|---------------------|--------------|
| 返回主界面 | `onGoMain`（:1416,1825） | `focusOrOpenMainWindow`（:755） | `window:focusOrOpenMain` → ipcHandlers.ts:379-385 |
| 顶栏返回箭头 | `onBack`（:1426） | 渲染层（面板内返回） | — |
| WebDAV 菜单 | `toggleWebDavMenu`（:1452）；书架/书源/设置 6 个同步项 `onUpload/UpdateFindBook*WebDav`（:1687-1739） | `webdav.test/ensureLayout/list/getToFile/putText` 等（:364-445） | `webdav:*` → registerWebDavIpc.ts |
| 主题切换 | `onToggleTheme`（:1459） | `setNativeTheme`（:710） | `theme:set` |
| 书源管理 | `onOpenBookSources`（:1758） | 渲染层（切 BookSourcePanel） | — |
| 下载目录 | `onOpenDownloadDir`（:1771） | `showOpenDialog`（:193）选目录（打开目录用 `openPath`:727） | `dialog:showOpenDialog`/`shell:openPath` |
| 新建找书窗 | `onOpenNewWindow`（:1781） | `openNewFindBookWindow`（:738） | `window:newFindBook` → ipcHandlers.ts:371-373 |
| 快捷键 | `openShortcuts`（:1792） | 渲染层（绑定保存走 `shortcut:setGlobalToggle`） | — |
| 设置 | `openSettings`（:1801） | 渲染层（切 FindBookSettingsPanel） | — |
| 配色 | `openColorScheme`（:1811） | 渲染层（切配色面板） | — |
| 桌面快捷方式 | `onCreateDesktopShortcut`（:1840） | `createFindBookDesktopShortcut`（:741） | `findBook:createDesktopShortcut` → ipcHandlers.ts:375-377 → findBookLaunch.ts:46-97 |
| 检查更新 | `onCheckForUpdates`（:1849） | `updater.check`（:827） | `updater:check` |
| DevTools | `onToggleDevTools`（:1858） | `toggleDevTools`（:762） | `window:toggleDevTools` |
| GitHub | `onOpenGithub`（:1867） | `openExternal`（:723） | `shell:openExternal` |
| 关于 | `onOpenAbout`（:1879） | 渲染层 | — |
| 免责声明 | `openDisclaimer`（:1888） | 渲染层（DisclaimerPanel） | — |
| 退出 | `onQuitApp`（:1897） | `quitApp`（:783） | `app:quit` |

## 10.8 找书窗口 · 搜索 / 书架 / 发现

**搜索区**

| 交互点 | 处理（FindBookPanel.vue:行号） | 插口 → 通道 |
|--------|------------------------------|-------------|
| 搜索/取消（同一按钮） | `onSearchAction`（:1525；提交 :998-1008） | `bookSourceSearch` → `bookSource:search`；取消 `bookSourceSearchCancel` → `bookSource:searchCancel`；事件订阅 `onBookSourceSearchEvent` → `bookSource:searchEvent`（registerBookSourceIpc.ts:90-182，searchService.ts:221-386） |
| 精准搜索 | `onPrecisionSearchChange`（:1661） | 渲染层（作为 search 参数 `precisionSearch`） |
| 限定书源 | `toggleSearchOptionsMenu`（:1538）/`clearSearchScope`（:1502） | 渲染层（参数 `sourceUrls`） |
| 触底加载更多 | `onSearchScroll`/`onSearchVisibleIndices`（:1960,2025） | `bookSourceSearchLoadMore` → `bookSource:searchLoadMore`（searchService.ts:283-340） |
| 搜索日志 | `onShowSearchLogs`（:1956） | 渲染层（展示事件流日志） |
| 历史标签/清空 | `onHistoryPick`/`onClearHistory`（:1984,1969） | 渲染层（localStorage 搜索历史） |
| 点结果 | `onOpenBook`（:2033） | 渲染层（开 BookDetailPanel） |

**书架区（FindBookshelfPanel，绑定 :1912-1918,1566,1590-1643）**

| 交互点 | 处理 | 插口 → 通道 / 落点 |
|--------|------|------------------|
| 阅读 | `onReadBookshelfBook`（:1912）→ `loadBookshelfReaderPayload`（bookshelfOpenReader.ts:20-99） | 有缓存目录直接渲染；无则 `bookSourceGetBookInfo`→`bookSource:getBookInfo` + `bookSourceGetChapterList`→`bookSource:getChapterList`（registerBookSourceIpc.ts:224-439） |
| 书籍信息 | `onOpenBook`（:1913） | 渲染层（开详情弹窗） |
| 按来源搜索 | `onSearchFromSource`（:1914,2055） | 渲染层切搜索并带 sourceUrls |
| 作者/书名搜索 | `onSearchAuthor`（:1916-1917） | 渲染层填关键词 |
| 分类筛选 | `onBookshelfCategorySelect`（:1915）/`onBookshelfCategoryAction`（:1566） | 渲染层（书架 localStorage） |
| 书架管理（排序等） | `onBookshelfManage`（:1632） | 渲染层 |
| 全部更新/更新日志 | `onBookshelfUpdateAll`/`onBookshelfUpdateLogs`（:1622,1643） | 更新走 `bookSource:getBookInfo`/`getChapterList`；日志渲染层 |
| 加入/移除书架（详情内触发） | `onToggleBookshelf`（BookDetailPanel.vue:454） | 渲染层 `localStorage["colortxt:findBookBookshelf"]`（findBookBookshelf.ts:107-166） |

**发现区（FindDiscoverPanel，绑定 :2053-2056）**

| 交互点 | 插口 → 通道 |
|--------|-----------|
| 选书源/选分类 | `bookSourceExploreKinds` → `bookSource:exploreKinds` |
| 浏览分类书籍/翻页 | `bookSourceExploreBooks` → `bookSource:exploreBooks`（engine/exploreKinds.ts） |
| 点书 | 渲染层开详情；`onSearchFromSource` 同上 |
| 书源变更 | 渲染层刷新 |

## 10.9 找书 · 书籍详情弹窗（BookDetailPanel.vue）

| 交互点 | 函数（行号） | 插口 → 通道 |
|--------|-------------|-------------|
| 放入/移出书架 | `onToggleBookshelf`（:454,1175） | 渲染层 localStorage 书架 |
| 分类选择 | `onCategoryBtnClick`（:1186）/`onCategoryPicked` | 渲染层 |
| 开始/继续阅读 | `onStartOrContinueReading`（:1202） | 渲染层开阅读器（数据经 10.8 书架链路） |
| 下载/停止 | `onDownloadOrStop`（:815,1213）→ useBookSourceDownload（useBookSource.ts:473-548） | `bookSourceDownload`→`bookSource:download`；事件 `onBookSourceDownloadEvent`→`bookSource:downloadEvent`；停止 `bookSourceDownloadCancel`→`bookSource:downloadCancel`（downloadService.ts） |
| 下载完成后动作 | `onBookDownloaded`（FindBookPanel.vue:2067）→ findBookDownloadActions.ts:11-42 | 加主界面列表（localStorage）；`openFileInMainWindow`（:757）→`window:openFileInMain` 或 `openFileInNewWindow`（:759）→`window:new` |
| 日志/刷新/登录 | `onShowLogs`（:870）/`onRefresh`（:877）/`onLogin`（:886） | 刷新走 getBookInfo/getChapterList；登录见 10.11 |
| 复制书名链接/目录链接 | `onCopyBookUrl`/`onCopyTocUrl`（:914,923） | 渲染层剪贴板 |
| 编辑书源 | `onEditBookSource`（:932） | 渲染层开 EditBookSourcePanel（保存 `bookSourceSave`→`bookSource:save`） |
| 来源变量/书籍变量 | `onSetSourceVariable`/`onSetBookVariable`（:940,948） | `bookSourceSetSourceVariable`→`bookSource:setSourceVariable`；`bookSourceSetBookVariable`→`bookSource:setBookVariable` |
| 清除本章缓存 | `onClearChapterCache`（:957） | `bookSourceClearChapterCache` → `bookSource:clearChapterCache` |
| 章节排序/标签 | `toggleChapterSort`/`toggleShowChapterTag`（:1073,1053） | 渲染层 |
| 点章节阅读 | `onReadChapter`（:779,1099）→ emit `read-chapter` → FindBookPanel `onReadChapter`（:2068） | 渲染层开 FindBookReaderPanel |
| 封面大图 | `openCoverLightbox`（:1007） | 渲染层（图片源经 `pathToReadableLocalUrl`:453 注册 `colortxtLocal:registerPath`） |

## 10.10 找书 · 在线阅读器（FindBookReaderPanel + Header/Footer/Sidebar）

阅读器头部与主窗口 AppHeader 同构（FindBookReaderHeader.vue:107-129 同名事件），字体/格式/主题/朗读/全屏插口同 10.1/10.5。下表列找书阅读器特有交互：

| 交互点 | 处理（FindBookPanel.vue:行号） | 插口 → 通道 |
|--------|------------------------------|-------------|
| 切章（侧栏/上一章/下一章） | `loadChapterAtDisplayIndex`（useFindBookChapterSession.ts:556-679） | `bookSourceGetChapterContent` → `bookSource:getChapterContent`（缓存优先 chapterCache.ts / getChapterContentWithCache.ts）；缓存状态 `bookSourceChapterCacheStatus`→`bookSource:chapterCacheStatus` |
| 章节缓存标记 | `markChapterCached`（:659） | 渲染层 Set（真实缓存由主进程 getChapterContent 写入 book_cache） |
| 阅读器内编辑保存 | `onSaveReaderChapter`（useFindBookChapterSession.ts:429）/`onApplyPartialPhysicalEdit`（:474） | `bookSourceSaveChapterCache` → `bookSource:saveChapterCache` |
| 阅读器设置/配色 | `onOpenSettingsFromReader`/`onOpenColorSchemeFromReader`（:2088-2089） | 渲染层 |
| 书籍详情 | `onOpenBookDetailFromReader`（:2090） | 渲染层 |
| 清缓存（阅读器内） | `onChapterCacheCleared`（:2091,2101） | `bookSource:clearChapterCache` |
| 目录刷新 | `onReaderTocRefreshed`（:2092） | `bookSourceGetChapterList` → `bookSource:getChapterList` |
| 文本替换 | `onOpenReplaceRules`/`onApplyReplaceRuleFormat`（:2093,2145） | 渲染层（ReplaceRule 应用在 renderChapterText :276） |
| 发音设置 | 置 `showVoiceReadSpeakSettingsPanel`（:2095,2102） | 渲染层 |

## 10.11 找书 · 书源管理 / 登录 / 校验

**BookSourcePanel**

| 交互点 | 插口 → 通道（composable: useBookSourceApi，useBookSource.ts:57-78） |
|--------|------------------------------------------------------------------|
| 列表加载 | `bookSourceList` → `bookSource:list` |
| 新建/编辑保存（EditBookSourcePanel） | `bookSourceSave` → `bookSource:save` |
| 删除 | `bookSourceDelete` → `bookSource:delete` |
| 启用开关 | `bookSourceToggle` → `bookSource:toggle` |
| 置顶/置底/拖拽排序 | `bookSourceReorder`→`bookSource:reorder`；`bookSourceApplyCustomOrders`→`bookSource:applyCustomOrders` |
| 校验（CheckSourceConfigPanel） | `bookSourceCheckStart`→`bookSource:checkStart`；事件 `onBookSourceCheckEvent`→`bookSource:checkEvent`；取消 `bookSourceCheckCancel`；配置 `bookSourceCheckGetConfig/checkSetConfig`（checkSourceService.ts） |
| 批量探索 | `bookSourceExploreKinds/exploreBooks` |
| 导出所选书源 | `showSaveDialog`（:198）+ `writeUtf8File`（:468） |
| 本地导入 | `importFromFile`（BookSourcePanel.vue:696）→ `bookSourceReadFile` → `bookSource:readFile` |
| 网络导入 | `importFromNetwork`（:702）→ `bookSourceFetchUrl`/`bookSourceFetchUrlAbort` → `bookSource:fetchUrl/fetchUrlAbort` |
| 剪贴板导入 | `importFromClipboard`（:718） | 渲染层 `navigator.clipboard.readText()` |
| 导入预览→提交 | ImportBookSourcePanel `commitImport` | `bookSourceImportPreview`→`bookSource:importPreview`；`bookSourceImportCommit`→`bookSource:importCommit`（registerBookSourceIpc.ts:90-182，落库 bookSourceStore.ts） |

**BookSourceLoginPanel**

| 交互点 | 插口 → 通道 |
|--------|-------------|
| 打开登录面板取信息 | `bookSourceGetLoginInfo` → `bookSource:getLoginInfo` |
| 求值登录 UI | `bookSourceGetLoginUi` → `bookSource:getLoginUi` |
| 浏览器登录（弹窗 webView） | `bookSourceBrowserLogin` → `bookSource:browserLogin`（用后台 WebView） |
| 提交登录 | `bookSourceLogin` → `bookSource:login` |
| 保存登录信息 | `bookSourceSetLoginInfo` → `bookSource:setLoginInfo` |
| 取/移除登录头 | `bookSourceGetLoginHeader`/`bookSourceRemoveLoginHeader` |
| 清 Cookie | `bookSourceClearCookie` → `bookSource:clearCookie` |
| 验证码弹框（主→渲染） | `onBookSourceCaptchaRequest`→`bookSource:captchaRequest`；提交 `bookSourceCaptchaReply`→`bookSource:captchaReply`；关闭 `bookSource:captchaDismiss` |
| 正文购买/解锁 | `bookSourcePayAction` → `bookSource:payAction` |

## 10.12 找书 · 设置面板（FindBookSettingsPanel，6 Tab）

| 交互点 | 插口 → 通道 |
|--------|-------------|
| 下载目录选择 | `showOpenDialog`（:193）→ `dialog:showOpenDialog`；设置本身存 localStorage |
| 打开下载目录 | `openPath`（:727）→ `shell:openPath` |
| 清全部章节缓存 | `bookSourceClearAllChapterCache` → `bookSource:clearAllChapterCache` |
| 代理保存/读取/测试 | `bookSourceSetHttpProxy`/`getHttpProxy`/`testHttpProxy` → `bookSource:setHttpProxy/getHttpProxy/testHttpProxy` |
| 阅读/编辑/语音 偏好 | 渲染层 localStorage（语音引擎测试走 `voiceReadHealthCheck`（:251）→ `voiceRead:healthCheck`） |
| WebDAV Tab | `webdav.test` 等（preload:364-445） |

## 10.13 隐身窗 / 摸鱼设置窗 / 取色器窗

**StealthReaderApp.vue（preload stealthReader* 一组，主进程 stealthReader.ts）**

| 交互点 | 函数（行号） | 插口 → 说明 |
|--------|------------|-------------|
| 进入摸鱼 | App.vue `enterStealthMode` | `stealthReaderEnter`（携带页文本/章节/起始行） |
| 翻页 | `requestPageFlip`（:295）→ 章末 `chapterPrev/Next`（:433,455） | 渲染层翻页；换章请求源窗，回推事件后 `stealthReaderGetPendingPayload`（:734 `pullAndApplyPendingPayload`） |
| 右键菜单 | `onContextMenu`（:702） | `stealthReaderPopupMenu`（主进程原生菜单） |
| 菜单命令 | `onCommand`（:716-731） | `stealthReaderExit`（:712）、`openStealthSettingsWindow`（:723）等 |
| 拖动/8 向缩放 | `onPointerDown`（:791）/`applyResize`（:825） | `stealthReaderGetBounds`/`stealthReaderSetBounds`/`stealthReaderGetCursorScreenPoint` |
| 滚轮调字号/行高/透明 | `onWheel`（:942-970） | 渲染层设置；透明刷新 `stealthReaderRefreshTransparency` |
| 导航快捷键 | `boot`（:984） | `stealthReaderSetNavShortcuts`；主进程 globalShortcuts 联动 |
| 退出回写行 | `exitStealth`（:709-714） | `stealthReaderExit(currentLine)` |

**摸鱼设置窗 StealthSettingsApp.vue**：`STEALTH_SETTINGS_IPC.open/close`（stealthSettingsWindow.ts:143-152）；终端字体 `fonts:getTerminalDefaultFace`（preload:716）；其余设置存 localStorage，摸鱼窗通过 `storage` 事件即时生效（StealthReaderApp.vue:636）。

**取色器（eyedropper.ts:264-362）**

| 交互点 | 插口 → 通道 |
|--------|-------------|
| 发起取色 | `eyedropperPick` → `eyedropper:pick`（截全屏+每显示器建覆盖窗） |
| 覆盖窗就绪 | 主进程收 `eyedropper:ready` 后回推 pointer |
| 移动采样 | `eyedropperHover`/`eyedropperSample` |
| 单击确认 | `eyedropperSubmit` → `eyedropper:submit`（:307-313，回 hex 给配色面板） |
| 取消/复制/切格式 | `eyedropperCancel`/`eyedropperCopy`/`eyedropperToggleFormat` |

## 10.14 插口通道命名规律（便于反查）

| 前缀 | 功能域 | 主进程注册文件 |
|------|--------|---------------|
| `window:*` / `app:*` / `theme:*` | 窗口/应用/主题 | ipcHandlers.ts、index.ts |
| `dialog:*` / `shell:*` | 系统对话框/shell | ipcHandlers.ts |
| `file:*` / `fs:*` / `dir:*` / `path:*` | 文件读写/目录/路径 | ipcHandlers.ts:572-720 |
| `bookSource:*` | 找书/书源全部能力 | registerBookSourceIpc.ts（通道常量 shared/bookSource/ipc.ts:18-88） |
| `voiceRead:*` | 语音朗读 | registerVoiceReadIpc.ts |
| `dictionary:*` / `translate:translate` | 词典/翻译 | registerDictionaryIpc.ts / registerTranslationIpc.ts（通道常量 dictionaryTypes.ts:111、translationTypes.ts:187） |
| `ai:*` | AI/嵌入/向量/文生图/角色卡 | registerAiIpc.ts |
| `webdav:*` / `secrets:*` | WebDAV/密钥 | registerWebDavIpc.ts / registerSecretsIpc.ts |
| `text-convert:*` | OpenCC 文本转换 | registerTextConvertIpc.ts |
| `shortcut:*` | 全局快捷键 | globalShortcuts.ts |
| `updater:*` | 自动更新 | registerUpdaterIpc.ts |
| `stealthReader:*` / `stealthSettings:*` / `eyedropper:*` | 摸鱼/取色器 | stealthReader.ts / stealthSettingsWindow.ts / eyedropper.ts |
| `fonts:*` / `characterPortrait:*` | 字体/立绘 | ipcHandlers.ts |
| `colortxt-local://` | 本地文件安全协议（图片等） | colortxtLocalProtocol.ts（index.ts:88 注册） |

---

# 十一、交互点补遗（设置/AI/角色卡/管理面板/窗口生命周期）

> 第十章覆盖了外壳与主流程交互，本章补齐"面板内部控件"与"系统推送类交互"。
> 系统推送类交互方向相反：**主进程 webContents.send → 渲染层 window.colorTxt.onXxx 监听**，不由用户点击发起。

## 11.1 窗口生命周期与系统推送（非点击触发）

注册集中在 `composables/useAppWindowBindings.ts`（主窗口）与 `FindBookWindow.vue` / `FindBookPanel.vue`（找书窗）。

| 交互场景 | 监听注册（渲染层:行号） | 推送方（主进程） | 处理 → 最终动作 |
|---------|------------------------|-----------------|----------------|
| 点窗口关闭按钮（主进程拦截） | `onWindowRequestClose`（useAppWindowBindings.ts:753；找书窗 FindBookWindow.vue:32） | 窗口 `close` 事件被 preventDefault 后推 `window:requestClose` | `handleWindowCloseRequest`（App.vue:2778，可弹保存确认）→ `proceedCloseWindow` → 通道 `window:proceedClose` 放行关闭 |
| 外部双击 txt / 另一窗口要求打开 | `onOpenTxtFromShell`（useAppWindowBindings.ts:747） | openTxtInMainWindow.ts 推 `app:open-txt-path` | `fileSession.openFilePath(filePath)` 走文件流链 |
| 启动瞬间带文件（单实例锁第二实例） | `consumePendingOpenTxtPath()`（useAppWindowBindings.ts:758） | ipcHandlers.ts 待打开文件队列 | 消费一次后清空，立即 openFilePath |
| 启动恢复会话 | `shouldRestoreSession()`（:766，通道 `window:shouldRestoreSession`） | windowFactory.ts:101-109 按窗口标记返回 | `tryRestoreSession()` 恢复上次文件+位置 |
| 多窗口主题同步 | `onThemeSync`（useAppWindowBindings.ts:227） | 任一窗口 `theme:set` 后广播 `theme:sync` | 跟换主题但不再回写，避免循环 |
| 当前文件被外部修改 | `onCurrentFileDiskChanged`（useAppSyncCurrentFileWatch.ts:76） | `file:watchCurrent` 注册的 fs.watch（ipcHandlers.ts） | 提示"文件已在磁盘变化，是否重新加载" |
| 全屏状态变化（F11/系统全屏） | `onFullscreenChanged`（preload:815） | windowFactory.ts:193-198 推 `window:fullscreen-changed` | 切换外壳 autoHide 布局 |
| 找书窗被外部要求切 Tab | `onFindBookActivateTab`（FindBookPanel.vue:1323） | ipcHandlers 推 `findBook:activateTab`（如新建快捷方式带 tab=bookshelf） | 切 mainTab |
| 更新事件 | `onUpdate*`（preload:838-867） | registerUpdaterIpc.ts 推 `updater:available/download-progress/downloaded/error` | 顶栏/关于面板显示更新状态 |
| 关窗/刷新前最后保存 | `beforeunload → flushPersistence`（useAppWindowBindings.ts:733-741） | — | localStorage 立即刷盘 |

## 11.2 设置面板内部控件（AppOverlays → SettingsPanel 10 Tab）

| Tab | 交互点 | 插口（证据:行号） | 通道 / 落点 |
|-----|--------|------------------|-------------|
| 常规 | 选择电子书输出目录/书包解压目录 | `showOpenDialog`（preload:193） | `dialog:showOpenDialog`；结果存 localStorage |
| 常规 | 打开输出/缓存目录 | `openPath`（preload:727） | `shell:openPath` |
| 常规 | 清除缓存目录 | `emptyDir`/`removePath`（preload:493-496） | `fs:emptyDir`/`fs:removePath`（ipcHandlers.ts:642-647 实现 rm+mkdir） |
| AI | 读取/保存 AI 配置 | `ai.configGet/configSet` | `ai:config:get/set`（registerAiIpc.ts:317-361，主进程 saveAiConfig） |
| AI | API Key 等密钥 | `secrets.set` | `secrets:set`（registerSecretsIpc.ts:56-89，写 safeStorage 而非 localStorage） |
| AI | 拉取模型列表/测试连接 | `ai.modelsList`（AiAssistantPanel.vue:566）/ 测试对话 `ai.testChat` | `ai:models:list`/`ai:testChat` |
| 向量模型 | 内置模型 列表/状态/是否已下载/加载 | `ai.embedding.builtin.*` | `ai:embedding:builtin:list/status/isCached/load`（registerAiIpc.ts:430-499 → localBackend.ts:68-132，worker 下载加载） |
| 向量模型 | 默认缓存目录查询/打开目录 | `getDefaultAiDataCacheDir`/`getDefaultBuiltinModelCacheDir`（preload:293-302）；`ai.paths.openDataCacheDir/openModelCacheDir`（registerAiIpc.ts:405-428） | `ai:paths:*` |
| 向量模型 | 重建/删除本书索引 | `ai.segmentRebuildBook`（AiAssistantPanel.vue:1190）/`ai.indexDeleteBook`（:1232）/`ai.segmentDeleteBook`（:1262） | `ai:segment:*`/`ai:index:*` |
| 角色卡（文生图） | 连接测试 | — | `ai:txt2img:test`（testConnection.ts:154-180 按 A1111/ComfyUI/OpenAI/DashScope/MiniMax/Stability 分发） |
| WebDAV | 测试连接/保存 | `webdav.test`（preload:367）+ `secrets.setWebDavPassword` | `webdav:test`、`secrets:setWebDavPassword` |
| 语音朗读 | 引擎健康检查/音色列表 | `voiceReadHealthCheck`（preload:251）/`voiceReadListVoices`（:246） | `voiceRead:healthCheck/listVoices` |
| 阅读 | 选中文本工具条按钮排序等 | 渲染层 | localStorage |
| 全部 Tab | 设置面板"应用" | 见 10.6 | localStorage（cacheStore 统一持久化） |

## 11.3 AI 阅读助手面板（AiAssistantPanel.vue）

| 交互点 | 函数/证据（行号） | 插口 → 通道 |
|--------|------------------|-------------|
| 发送消息 | `messageAppend(tid,"user",text)`（:1456）→ `agentStart({...})`（:1523） | `ai:message:append`、`ai:agent:start`（registerAiIpc.ts:917-939） |
| 接收流式回答/工具调用 | `onAgentEvent`（:982） | 推送事件 `ai:agent:event`（含 token delta、工具状态） |
| 停止生成 | `chatAbort`/`embedAbort`（:420-421） | `ai:chat:abort`（registerAiIpc.ts:825）/`ai:embedding:abort` |
| 新对话 | `threadDeleteEmptyForBook` → `threadCreate(bh,"新对话")`（:778-779） | `ai:thread:deleteEmptyForBook`、`ai:thread:create` |
| 会话列表/切换 | `threadList(bookHash)`（:667）→ `messageList(tid)`（:678） | `ai:thread:list`、`ai:message:list` |
| 重命名会话 | `threadRename(tid,title,true)`（:384 手动 / :687 自动） | `ai:thread:rename` |
| 删除会话 | `threadDelete`（:1298） | `ai:thread:delete` |
| 工具调用内容编辑（结果回填） | `messageUpdateToolContent`（:765） | `ai:message:updateToolContent` |
| 深度思考/防剧透/技能 | 作为 agentStart 请求参数（:1523 组装） | 同一 `ai:agent:start`，主进程按参数组装系统提示 |
| 引用正文追问 | App.vue `onAskAiWithQuote`（:4148）→ 打开本面板并带入引文 | 同上 |
| 构建本书知识库 | `segmentRebuildBook`（:1190） | 分段→嵌入→索引（`ai:segment:*`+`ai:embedding:embed`+`ai:index:replaceChunks`） |
| 检查知识库状态 | `indexHasBook`（:1376） | `ai:index:hasBook` |
| 拉模型下拉 | `configGet`（:563）+`modelsList`（:566） | `ai:config:get`、`ai:models:list` |

## 11.4 角色卡侧栏（CharacterSidebarPanel + CharacterEditDrawer + useCharacterPortraitRetrieve）

| 交互点 | 证据（文件:行号） | 插口 → 通道/落点 |
|--------|------------------|------------------|
| AI 提取角色信息 | `ai.portraitExtract`（useCharacterPortraitRetrieve.ts:396） | `ai:portrait:extract` |
| 生成金句 | `ai.portraitGoldenQuotes`（:425） | `ai:portrait:goldenQuotes` |
| 立绘 SD prompt 翻译 | `ai.portraitTranslateSdPrompt` | `ai:portrait:translateSdPrompt` |
| AI 生成立绘 | ai 命名空间文生图接口 → 图片写主进程缓存目录后注册本地 URL | `ai:portrait:txt2imgToPath`（preload:1205 附近） |
| 手动上传本地图片当立绘 | `characterPortrait.copyFileTo`（CharacterEditDrawer.vue:779） | `characterPortrait:copyFileTo`（ipcHandlers.ts:572-720）→ 复制进 userData |
| 角色资料增改 | CharacterEditDrawer 保存 | 渲染层 fileMetaStore（随书包同步） |

## 11.5 词典 / 网络搜索 / 翻译管理弹窗

| 弹窗 | 交互点 | 证据（文件:行号） | 插口 → 通道 |
|------|--------|------------------|-------------|
| DictionaryManageModal | 导入词典文件 | `dictionaryImport`（DictionaryManageModal.vue:247） | `dictionary:import`（dictionaryTypes.ts:113）→ registerDictionaryIpc.ts |
| DictionaryManageModal | 删除词典 | `dictionaryRemove`（:296） | `dictionary:remove`（:115） |
| DictionaryManageModal | 选中词查询（同阅读器弹窗） | `dictionaryLookup` | `dictionary:lookup`（:112） |
| WebSearchManageModal | 搜索引擎增删改 | 渲染层 | localStorage（查询时拼 URL 走 `shell:openExternal`） |
| TranslateManageModal | 翻译服务配置 | 渲染层配置 + 密钥 `secrets.set` | safeStorage；翻译时 `translate:translate` |

## 11.6 WebDAV 同步面板（WebDavSyncPanel.vue）

| 交互点（模板:行号） | 插口（行号） | 通道 |
|--------------------|-------------|------|
| 刷新远程列表（:666） | `webdav.ensureLayout`（:368）→`webdav.list`（:369） | `webdav:ensureLayout`、`webdav:list`（registerWebDavIpc.ts:88-242） |
| 点远程文件项（:700） | 渲染层展开/下载菜单 | — |
| 下载选中（:801） | `webdav.getToFile`（:401） | `webdav:getToFile`（下载到本地临时文件再恢复书包） |
| 上传配置（:772） | `webdav.putFile`/`putText` | `webdav:putFile/putText`（:244-369） |
| 更新配置（:782） | 先 getToFile 再合并再 putFile | 同上 |
| 传输进度条 | `webdav.onTransferProgress`（:298） | 推送 `webdav:transferProgress`；中止 `webdav.abortTransfer`（preload 同组） |
| 建远程目录/删除 | `webdav.mkdir`/`webdav.delete` | `webdav:mkdir/delete` |

## 11.7 找书补遗

| 交互点 | 证据 | 插口/落点 |
|--------|------|-----------|
| 替换规则 增删改/启用/导入导出 | ReplaceRulePanel → replaceRuleLocalStore.ts:11-51 | 纯渲染层 localStorage（两个 bucket：`STORAGE_KEY` :11） |
| 找书阅读器底部番茄钟 | FindBookReaderFooter.vue:62-65（4 个 emit） | 渲染层（与主窗口同一番茄钟状态模型） |
| 书源登录验证码弹框 | 主进程推 `bookSource:captchaRequest` → 渲染弹框 → `bookSourceCaptchaReply`/`bookSource:captchaDismiss` | 见 10.11 |
| 书架"全部更新" | onBookshelfUpdateAll（FindBookPanel.vue:1622） | 逐书 `bookSource:getBookInfo`+`getChapterList`，日志渲染层 |
| 书架分类管理 | onBookshelfManage（:1632） | localStorage 书架 |
| 免责声明确认 | DisclaimerPanel | localStorage 记录已同意 |

## 11.8 配色面板内部 / 图片资源

| 交互点 | 插口 → 通道/落点 |
|--------|-----------------|
| 导出当前方案 | `showSaveDialog`（preload:198）+ `writeUtf8File`（:468）→ `file:writeUtf8File` |
| 导入方案 | `showOpenDialog`（:193）+ `readWholeTextFile`（:472）→ `file:readWholeTextFile` |
| 背景图选择 | `showOpenDialog` → `colortxtLocal:registerPath` 注册后引用 `colortxt-local://` |
| 颜色拾取按钮 | `eyedropperPick` → `eyedropper:pick`（详见 10.13、12.8） |
| 阅读器 Markdown 图片/书封面显示 | `pathToReadableLocalUrl`（preload:453）→ `colortxtLocal:registerPath` → 协议处理器读盘；远程封面主进程 `registerRemoteCoverBytes`（colortxtLocalProtocol.ts:26，缓存上限 300，:21） |
| ReaderImageLightbox 大图 | 同上，纯渲染层放大控件 |

---

# 十二、核心交互的主进程深度调用链（handler → service → 落地）

> 第十章的链路止于"主进程注册文件"。本章进入 handler 内部，按 **入口 → 调度 → 关键分支 → 副作用 → 回流** 五段展开。
> 节点标注输入/输出，可据此判断每一步的数据形态。

## 12.1 多书源搜索（bookSource:search）

```
渲染层 useBookSourceSearch.search()（useBookSource.ts:287）
  入：keyword、sourceUrls?、precisionSearch?
  → invoke(bookSource:search) 拿 searchId；订阅 onBookSourceSearchEvent
      ↓
主进程 registerBookSourceIpc.ts:199-221 handler
  · 校验 keyword / 解析参与书源 URL
  → startSearch(...)（searchService.ts:352-379）
      · 建 session{sources, cancelled, hasNextPage, sendTo}，setImmediate 启动
      → runInitialSearch（:221-280）
          · 过滤启用书源，SOURCE_CONCURRENCY=4 并发池
          · 每源 → searchOneSource（:203-218）→ searchBook(source,key,page,logs)
              ↓（引擎层 engine/）
            HTTP 抓取搜索页 → Legado 规则解析（legadoCompositeRule.ts）
            → 标准化为 Book 列表（coerceBook）
          · 每源结束 sendTo(wc, searchEvent, {type:"progress"|"sourceDone"|"result"})
          · 全结束发 {type:"done"}
      ↓ webContents.send
渲染层事件回调增量合并结果（result 去重、sourceDone 更新计数）
```
- **翻页**：`bookSource:searchLoadMore` → `loadMoreSearch`（:343-386 校验 session）→ `runLoadMore`（:283-340）只对 `hasNextPage=true` 的源请求下一页，发 `loadMoreStart/loadMoreDone`。
- **取消**：`bookSource:searchCancel` → `cancelSearch` 删 session 并置标志，进行中的 fetch 被 abort。
- 副作用：仅网络请求 + 内存 session（Map），不写盘。

## 12.2 章节正文：缓存优先读取（bookSource:getChapterContent）

```
渲染层 loadChapterContent（useFindBookChapterSession.ts:632）
  → invoke(bookSource:getChapterContent, {sourceUrl,chapterUrl,book,cacheDir,preferCache,...})
      ↓
主进程 handler → getChapterContentWithCache()（getChapterContentWithCache.ts:25-117）
  入：source 书源规则、chapterUrl、book、chapter、nextChapterUrl
  ① skipChapterCache 判定（:44-46）：正文规则以 <js> 开头且章节页==书页时不缓存
  ② preferCache 且非 skip：
       readChapterCache（chapterCache.ts:83-96）
       路径 = {cacheRoot}/{书名前9字+md5(bookUrl)[8:24]}/{md5(chapterUrl)[8:24]}.nb
         · cacheRoot 默认 userData/BOOK_SOURCE_CHAPTER_CACHE_SUBDIR（chapterCache.ts:32-34）
       命中 → stripLeadingDuplicateChapterTitle 剥重复章名，必要时回写清理后内容（:63-80）
            → 返回 {content, fromCache:true}
  ③ 未命中 → getChapterContent()（engine/webBook.ts）联网抓正文 → 规则解析
       成功且非空 → saveChapterCache（chapterCache.ts:98-113）mkdir recursive + writeFile utf8
       返回 {content, fromCache:false}
```
- 缓存状态批量查询：`bookSource:chapterCacheStatus` → `filterCachedChapterUrls`（chapterCache.ts:116-136），一次 readdir 用 Set 判定，用于侧栏缓存标记。
- 删除：`clearChapterCache`→`deleteChapterCache` rm 单文件（:139-153）；`clearAllChapterCache` rm 根目录（:172-182）。

## 12.3 下载全书 / 仅缓存（bookSource:download）

```
渲染层 useBookSourceDownload.download(item,outputDir,cacheDir,{cacheOnly})（useBookSource.ts:473）
  → invoke(bookSource:download) 拿 downloadId；订阅 onBookSourceDownloadEvent
      ↓
startDownload（downloadService.ts:85-95）：建 session Map（downloadId→{cancelled,emit}）
  → runDownload（:101-244）
  ① getBookInfo（书源引擎抓详情）→ getChapterList 抓目录
  ② contentChaptersInReadingOrder 过滤分卷、按阅读序排列
  ③ 逐章 for 循环（:132-174）：
       每章前/后各 emit 一次 progress{current,total,chapterName}
       → getChapterContentWithCache（复用 12.2，已缓存不联网）
       单章失败只 push logs 不中断（:161-165，失败章导出时写占位）
  ④ cacheOnly=true → 不导 TXT，直接 emit done（:186 起）
  ⑤ 否则读全部缓存拼接 fullText（加书名/作者/简介头 buildDownloadFileHeader :60-71）
       → writeDownloadFile（:73-83）：
            mkdir(outputDir, recursive)
            writeFile(outputDir/{书名}.txt, iconv.encode(fullText,"utf8"))  // 同名直接覆盖
       emit done{filePath}
取消：bookSource:downloadCancel → session.cancelled=true（循环点 :133 检查）
      ↓
渲染层 runFindBookDownloadAfterAction（findBookDownloadActions.ts:11-42）
  → 可选写主界面文件列表(localStorage) + none/openMain/openNewWindow 后动作
```

## 12.4 打开大文件（file:stream）

```
渲染层 streamFile(physicalPath)（preload:664）→ ipcMain.on("file:stream")（ipcHandlers.ts:848）
  ① 每发送方维护 activeStreamBySenderId：新流先 destroy 旧流（:872-877）——切文件防串包
  ② requestId 自增（streamRequestSeqBySenderId），所有 chunk 回调先校验序号（:925,938,953）
  ③ stat 校验是文件、拿 totalBytes（:888-906）
  ④ detectEncoding（:909，→ detectTextFileEncoding 按字节头推断）
  ⑤ iconv.getDecoder(encoding) 增量解码器；createReadStream(highWaterMark=256KB)（:911）
  ⑥ 推流序列：
       file:stream-start{encoding,totalBytes}（:916）
       data → decoder.write(buf) → file:stream-chunk{text,readBytes,totalBytes}（:924-936）
       end  → decoder.end() 尾部 → file:stream-end（:937-951）
       error→ file:stream-error
      ↓
渲染层 useTxtStreamPipeline 按 requestId 丢弃过期流，chunk 按物理行切分累积，
end 后一次性写入 Monaco 展示层（afterFullTextInstalled）。
```

## 12.5 保存文件（file:writeTextFile）

```
saveReaderBufferWithIpcEncoding(codec)（App.vue:1032-1057）
  → invoke("file:writeTextFile", filePath, content, encoding)
      ↓
handler（ipcHandlers.ts:602-630）
  · path.resolve 规范化，空路径返回 {ok:false}
  · encoding 默认 utf8
  · buf = iconv.encode(content, encoding)        // GB2312 等编码在此转换
  · mkdir(path.dirname, {recursive:true})        // 目录不存在自动建
  · writeFile(resolved, buf)                     // 直接覆盖写（非 tmp+rename）
  · 返回 {ok:true} / {ok:false,message}
      ↓
渲染层据 ok 提示成功/失败 → 重新跑章节切分刷新侧栏
二进制写：file:writeBinaryFile（:632-640）Buffer.from(base64,"base64")，用于书包/图片导出。
```

## 12.6 语音合成（voiceRead:synthesize）

```
voiceReadSynthesisClient.ts:74 → invoke(voiceRead:synthesize, {engine,text,voice,rate,...})
      ↓
registerVoiceReadIpc.ts:96-177（参数校验/错误序列化）
  → getVoiceReadTtsProvider(engine)（providerRegistry.ts:30）
      注册表（:18-22）：edgeTtsProvider / winSapiProvider / volcengineProvider
                       / minimaxProvider / dashscopeProvider / mimoProvider
  → provider.synthesize() 返回音频
      · Edge：网络 TTS
      · winSapi：本地 SAPI（voiceRead/winSapi/），无网可用
      · 火山/Minimax/DashScope/MiMo：云端 API，密钥从 secrets vault 读
      · volcengine/dashscope 有独立 synthQueue（串行+排队）
  ← 返回音频字节/URL
渲染层 voiceReadLinePlayer 播放（voiceReadAudioCache 缓存本行音频），
onended 推进下一行，章末 handleDocumentEndReached 自动换章。
取消：voiceRead:cancelSynthesis → 中断合成并清播放队列。
```

## 12.7 AI 对话（ai:agent:start 流式）

```
AiAssistantPanel 发送（:1456 messageAppend 落库用户消息 → :1523 agentStart）
      ↓
registerAiIpc.ts:917-939 handler
  → runAgentChat({...})（import 自 ai/chat/agentChat.ts，:64）
      · 读用户配置（endpoint/key/model，key 经 secrets 解密）
      · 组装消息（系统提示 + 深度思考/防剧透/技能参数 + 历史消息 + 知识库检索片段
                 —— 知识片段来自 ai:index:search 向量召回）
      · 发 HTTP 流式请求，逐 chunk 解析
  → webContents.send("ai:agent:event", {type:"delta"|"tool"|"done"|"error",...})
      ↓
渲染层 onAgentEvent（AiAssistantPanel.vue:982）增量渲染；工具调用经
  messageUpdateToolContent（:765）可回填修改后再续问。
中止：ai:chat:abort（:825）abort 控制器取消 HTTP 请求。
普通（非 Agent）对话走 ai:chat:start（:800）。
```

## 12.8 colortxt-local 安全文件协议

```
渲染层拿到本地图片路径
  → pathToReadableLocalUrl（preload:453）→ invoke("colortxtLocal:registerPath", absPath)
      ↓
colortxtLocalProtocol.ts：
  · 主进程内存双 Map：pathByRef(ref→绝对路径) + refByPathKey(规范化路径→ref)（:17-19）
      —— 同一路径复用同一 ref，避免注册表无限膨胀
  · 返回 colortxt-local://local/{ref}
  · 远程封面另走 registerRemoteCoverBytes（:26），字节直接存 Map，上限 300（:21）
<img src=该URL> 发起请求
  → protocol.handle：用 ref 反查注册路径 → 校验扩展名白名单（IMAGE_MIME :6-14）
  → readFile 返回带 MIME 的 Response
安全性：渲染层无法构造路径直接读盘，只能读"先经 IPC 注册过"的路径（防目录穿越）。
取色器（eyedropper.ts:264-313）是另一条屏幕像素通道：截屏→多显示器覆盖窗→hover/sample→submit 回 hex。
```

## 12.9 主进程持久化落点（非 localStorage 的部分）

| 数据 | 位置 | 实现证据 |
|------|------|---------|
| 书源/书源变量/域名变量 | `userData/book-sources.db`（**SQLite**，json 列存整条记录，UPSERT `ON CONFLICT … DO UPDATE`） | bookSourceStore.ts:14、:180、:265、:401 |
| 章节正文缓存 | `userData/{缓存子目录}/{书名前9字+md5(bookUrl)16位}/{md5(chapterUrl)16位}.nb`（明文 utf8） | chapterCache.ts:22-62 |
| 下载的 TXT | 用户配置下载目录 `/{书名}.txt`（utf8，同名覆盖） | downloadService.ts:73-83 |
| Android ID（书源伪装） | `userData/bookSourceAndroidId.txt` | bookSourceUserAgent.ts:26 |
| 书源脚本附件 | `userData/book-source/files` | scriptImport.ts:17 |
| AI 配置 | 主进程配置文件 saveAiConfig | registerAiIpc.ts:317-361 |
| 各类密钥/密码 | Electron safeStorage（系统凭据库） | registerSecretsIpc.ts:56-89 |
| AI 内置嵌入模型 | 模型缓存目录（localBackend worker 下载） | localBackend.ts:68-132 |
| 手动立绘 | characterPortrait 复制进 userData | ipcHandlers.ts `characterPortrait:*` |
| 窗口尺寸/位置 | windowBounds.ts（防抖写 + close 兜底） | windowFactory 中接线 |

> 渲染层侧数据（设置、文件元数据、最近文件、找书书架、替换规则等）全部在各窗口的 `localStorage`，跨窗口不共享；需要跨设备/跨窗口一致时走 WebDAV 书包。

---

*文档基于源码静态分析生成，行号可能随版本变化，建议结合文件内容核对。*
