---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'dc4237e7-ae37-43e0-a00b-e004db3ccd19'
  PropagateID: 'dc4237e7-ae37-43e0-a00b-e004db3ccd19'
  ReservedCode1: '9116f642-2a47-4e25-8089-194936df23c6'
  ReservedCode2: '9116f642-2a47-4e25-8089-194936df23c6'
---

# ColorTxt（彩读）运行逻辑全流程深度剖析

> ——从打开到关闭的微观运行追踪 · 新书 / 旧书 / 多窗体 / 迭代史
>
> 项目：GitHub ssnangua/ColorTxt（本地 TXT 小说阅读器）｜分析版本：v3.8.11（Electron 35 + Vue 3 + Monaco Editor + TypeScript）
> 方法：源码级动态追踪，所有结论标注 `文件:行号`（相对 `src/`），基于 v3.8.11 提交 9565e4d
> 姊妹篇：《ColorTxt项目深度分析报告.md》（静态架构与功能模块）、《ColorTxt官方迭代史研究报告.md》（版本演进原始素材）

---

## 〇、阅读指引

本报告回答四个问题：

1. **打开一本新书**，从鼠标点击到能滚动阅读，软件内部每一步发生了什么（第二章）
2. **重新打开一本旧书**，进度、书签、视口如何毫厘不差地回来（第三章）
3. **多个窗口**（主窗 / 找书窗 / 摸鱼窗 / 取色层）如何共存、通信、互不踩踏（第五章）
4. **官方迭代史**：作者为了什么目的做了什么、碰到什么阻碍、怎么解决、新方案又带来什么新问题、最终沉淀了什么（第七章）

第四章是二三章共用的"阅读中循环"细节，第六章是贯穿全文的落盘体系。

**贯穿全文的一个核心认知**：ColorTxt 的一切运行逻辑建立在**双坐标系**之上——磁盘上的**物理行**（physical line，1-based，永不改变）与屏幕上的**展示行**（display line，经过空行压缩、缩进、替换规则后的 Monaco 行）。所有持久化（进度、书签、标注）锚定物理行，所有渲染锚定展示行，两者之间靠 `displayLineToPhysicalLine` 映射表换算。理解了这一点，后面每一步设计都会自然合理。

---

## 一、地基：进程模型、数据总线与启动序列

### 1.1 三层进程分工

```
┌────────────────────────── 主进程 (src/main) ──────────────────────────┐
│ index.ts        入口：协议注册、窗口工厂、单实例、退出收尾              │
│ windowFactory   创建主窗/找书窗（唯一工厂，靠参数分流）                 │
│ ipcHandlers.ts  35KB 业务 IPC：文件流式读取、对话框、字体、背景、快捷键  │
│ stealthReader   摸鱼覆盖层窗口（29KB，全项目最难缠的窗口）              │
│ bookSource/     Legado 书源引擎 + 后台隐藏 webView                     │
│ ai/             RAG/对话/文生图；voiceRead/ TTS 合成；dictionary/ 词典   │
│ secretStorage   密钥保险库（串行队列 + 原子落盘）                       │
└──────────────┬───────────────────────────────────────────────────────┘
               │ IPC（contextBridge 之后的 window.colorTxt.*）
┌──────────────┴───────────────────────────────────────────────────────┐
│ 渲染进程 (src/renderer/src)  App.vue 4452 行 = 总指挥                  │
│   useAppFileSession   文件会话（打开/切书/恢复，43KB）                 │
│   useAppPersistence   持久化（门控/防抖/多窗合并，67KB）               │
│   useAppWindowBindings 窗口事件绑定 + 启动编排（776 行）               │
│   useTxtStreamPipeline 流式管线（物理行→展示行，19KB）                │
│   ReaderMain.vue      Monaco 封装（5150 行，翻页/进度/装饰）           │
│   reader/             展示格式化、视口锚点、章节树、标注装饰            │
│   stores/             localStorage 封装（cacheStore/fileMetaStore）   │
└───────────────────────────────────────────────────────────────────────┘
```

Preload（`preload/index.ts`）只做一件事：把 IPC 通道包装成 `window.colorTxt.*` API，`contextIsolation: true`、`nodeIntegration: false`，无直接 Node 暴露。

### 1.2 渲染进程要读文件，为什么必须绕道主进程流式读

Electron 安全模型下渲染进程没有 Node fs。文件内容经 `file:stream-start / stream-chunk / stream-end` 三段 IPC 推入（`main/ipcHandlers.ts:908-951`）：

```
渲染层调用 streamFile(path)                        useAppFileSession.ts:507
  → 主进程 createReadStream(path, {highWaterMark: 256KB})   ipcHandlers.ts:912
  → detectEncoding(path) 编码探测（BOM → jschardet → ANSI 中文启发式）  detectTextEncoding.ts
  → file:stream-start {encoding, totalBytes}
  → file:stream-chunk {text, readBytes} × N
  → file:stream-end
切书时 prevStream.destroy() 立即掐断旧流          ipcHandlers.ts:874
```

分块 **256KB**。渲染层用 `activeStreamRequestId` 校验每个 chunk 属于当前流（`useAppWindowBindings.ts:365`），防止快速切书时旧流的迟到 chunk 污染新会话——这是一个竞态防御的关键设计。

### 1.3 冷启动序列（谁先谁后，为什么）

```
app.whenReady
 ├─ registerColortxtLocalProtocol()     colortxt-local:// 协议（ready 前已注册特权）
 ├─ setupAutoUpdater()
 ├─ 命令行有 --find-book？→ 直接开找书窗（不开主窗）   main/index.ts:90-91
 ├─ resolveLaunchTxtForStartup(argv)    从命令行解析待打开 txt
 └─ createWindow({ openTxtPath: launchTxt })
```

`createWindow`（windowFactory.ts:51-231）创建窗口时的关键决策：

| 动作 | 代码 | 内在逻辑 |
|---|---|---|
| `show: false` + `ready-to-show` 才 show | :82, :154-159 | 防白屏闪烁 |
| **会话恢复判定** `shouldRestoreSession = 无其它主窗 && 无 openTxtPath && 非找书窗` | :60-69 | 只有"全新的、干净的、第一个"主窗才有资格恢复上次会话。第二个主窗若也恢复，两个窗会抢同一本书 |
| `pendingOpenTxtByWindowId.set(win.id, path)` + 异步 stat 校验 | :178-191 | 新窗带路径时先记下，校验扩展名和存在性，失败则删除——渲染进程启动后主动来"拉"（pull），而不是主进程硬推（push），避免渲染层尚未就绪时消息丢失 |
| resize/move → 300ms debounce 存窗口位置，close → 立即存 | :200-227 | 拖动过程高频触发，直接写文件会打爆磁盘 IO |
| `before-input-event` 拦截 F12 / Ctrl+Shift+I | :161-174 | 打包后禁 DevTools；但**故意不拦 Esc**（:162 注释：拦了渲染进程收不到 Esc，全屏退出/弹窗关闭会失灵） |
| `closed` 时检查是否还有"用户窗" | :110-128 | 没有了就连后台 webView、取色层一起拆——这些 `show:false` 的隐藏窗不触发 `window-all-closed`，不拆进程就退不掉 |

窗口装载完页面后，渲染进程的启动编排在 `useAppWindowBindings.ts:700-770`，顺序严格：

```
onMounted:
 1. 注册 pagehide + beforeunload → persistWindowUnloadState()     :733,738
    （双保险：Windows 个别关闭路径对 pagehide 不可靠，注释 :737）
 2. 注册 onOpenTxtFromShell（运行中外部双击 txt → openFilePath）    :747-750
 3. 注册 onWindowRequestClose（关窗握手，见 5.6）                   :752-756
 4. consumePendingOpenTxtPath()  ← 拉取建窗时携带的路径（最高优先级）:758-761
 5. restoreFileListFromSession()  ← 文件列表【始终】恢复             :763-764
 6. shouldRestoreSession() IPC 问主进程 → true 才 tryRestoreSession() :766-769
 7. App.vue:1981 另有一路 initPersistenceBootstrap()：同步 loadRecentFiles +
    loadFileMeta（须在首个 await 前，否则侧栏"打开时间"排序在空 meta 上拍快照）+
    密钥保险库 hydrate + storage 事件监听绑定
```

注意 4 → 5 → 6 的顺序就是优先级：**外部指定打开 > 列表恢复 > 会话恢复**。文件列表恢复与"恢复上次会话"设置解耦（:763 注释）——书架永远都在，要不要自动翻开最后一本是另一回事。

### 1.4 localStorage 数据总线（渲染进程的"数据库"）

| 键 | 内容 | 写入时机 |
|---|---|---|
| `colorTxt.session` | `{currentFile, viewportTopLine, viewportBottomLine}`（物理行） | 仅窗口卸载时（persistReadingSessionSnapshot，useAppPersistence.ts:1754-1769） |
| `colorTxt.file.list` | 书架列表 `[{name, path, size, category, addedAt}]` | 增删合并时 + 卸载时 |
| `colorTxt.file.meta` | **每本书的全部阅读数据**（见下） | 防抖落盘（受门控，见第六章） |
| `colorTxt.recent.files` | 最近打开（MRU 顺序，仅 `{path}`） | 打开/切书/卸载时 |
| `colorTxt.ui.settings` | 界面/排版/功能设置 | 变更时即写；关窗**不**整份回写 |
| `colortxt.findBook.settings` / `colorTxt.stealth.settings` | 找书窗 / 摸鱼窗独立设置 | 各自变更时 |

`colorTxt.file.meta` 中单本书的记录 `FileMetaRecord`（fileMetaStore.ts:67-115）：

```
path, fileName
progress                    阅读进度 %
editorViewState            Monaco saveViewState() 序列化（含光标、视口、折叠）
viewportTopPhysicalLine    与 viewState 配套的"视口首行物理行"，恢复后校验用
convertedMdPath             电子书转换结果路径
sourceMtimeMsAtConvert     转换时源文件 mtime → 缓存失效判断
bookmarks[]                书签
highlightWordsByIndex      高亮词
readerAnnotations[]        划线/笔记（物理行列区间 + 原文快照 + stale 失效标记）
lastOpenedAt / updatedAt   打开时间排序与合并决胜分离
characterRoster             角色卡
```

**所有键在 Electron 中是同源共享的**：多个窗口读写同一份 localStorage，写会触发其它窗口的 `storage` 事件——这是 ColorTxt 多窗同步的主干道（5.4 节），也是它所有"防覆盖"复杂度的来源。

---

> AI生成## 二、新书阅读全流程：从"打开"到"关闭"的时间轴

> "新书"指本机此前没有阅读记录的书（`colorTxt.file.meta` 中无对应 path 记录）。所有入口最终汇聚到同一个函数 `openFilePath`（useAppFileSession.ts:1058-1205）。

### 阶段 0：入口枚举（五种方式打开一本书）

| 入口 | 链路 | 备注 |
|---|---|---|
| Ctrl+O 对话框 | `openFileViaDialog` → `openFilePath` | useAppFileSession.ts:521 |
| 拖放文件/文件夹到窗口 | `importPathsIntoFileList`（入列表不打开）/ 单文件直开 | :964 |
| 资源管理器双击 .txt/.md/.ctz | 主进程 `openTxtInMainWindow`（openTxtInMainWindow.ts:88-111）→ 无主窗则 `createWindow({openTxtPath})`，有主窗则聚焦后 `webContents.send("app:open-txt-path")` → 渲染层 `onOpenTxtFromShell` → `openFilePath` | 运行中双击走推，未运行则冷启动走 pull |
| 命令行/第二个实例 | `launchTxtHandlers` 单实例锁路由（同上） | launchTxtHandlers.ts:66-109 |
| 书架列表点击 | `openFileFromSidebar` → `openFilePath({keepSidebarTab:true, listRow})` | :895-898 |

**设计意图**：五条路一条管道，`openFilePath` 是唯一的会话切换闸门——所有状态清理、进度记忆、恢复仲裁都发生在这一个函数里，不会有第三处状态机。

### 阶段 1：打开前检查（openFilePath 前半段）

```
① 编辑守卫    confirmIfReaderEditDiscard()                    :1079-1084
   当前处于编辑模式且有未保存修改 → 弹确认框；取消则中止（返回 false）
   （skipReaderEditGuard=true 的场景除外：书包命中当前书重载等）

② 书包检测    tryImportReaderBookPack(filePath)               :1086-1088
   looksLikeZipBookPackCandidate 识别 .ctz/.ctzx
   → 解包导入（AES-256-GCM 解密、密码本、覆盖确认）→ 导入后打开其中的书
   → 是书包则本函数到此结束，走书包分支

③ 记忆旧书    rememberCurrentFileLine()                      :1090-1092
   ★ 关键：切书前必须把"上一本书"的进度落盘
   → 流程：calcProgressPercentByViewportDisplay(top, bottom) 用展示行换算物理行
     算出进度 % → touchRecentFile(path, persistMeta:true) 写 meta + recent
   → readingProgressSynced=false 时【跳过】（进度还没恢复完，不能拿顶部视口
     覆盖真实进度——这是防"打开瞬间顶部视口冲掉书包导入锚点"的门控，:373）

④ 路径校验    prepareOpenFile → window.colorTxt.stat          :1099-1111
   文件不存在/不可访问 → 弹窗 + removeRecentFile（从最近打开里剔除）

⑤ 物理路径解析 resolvePhysicalTextForOpen                     :1113-1121
   纯 txt/md：直接返回本路径
   电子书（epub/mobi/pdf/chm…）：
     → ensureEbookMarkdown（convertEbookToMarkdown.ts）
     → 严格缓存命中检查：记录的 convertedMdPath 存在 && 源文件 mtime 与
       sourceMtimeMsAtConvert 一致 → 直接复用转换结果，0 开销
     → 未命中 → 走转换管线（EPUB/MOBI/PDF/CHM 解析 → ATX 标题 + 插图 +
       内链侧车 → 写出 {原名}.epub.md）
     → 转换或缓存信息变化 → setEbookConvertedMeta + persistFileMeta
   ⚠ 所以"电子书第二次打开"和"旧书恢复"一样快：磁盘上真正被流式读取的
     是转换后的 .md（physicalReaderPath），会话路径仍是 .epub（currentFile）
```

**为什么要在打开前就记忆旧书**：如果等切书完成后再补救，需要回滚整个 Monaco 与映射表状态去补拍视口快照，极易出错；在切换前"旧书还活着"的瞬间拍快照，是唯一无歧义的时机。

### 阶段 2：恢复仲裁（新书 vs 旧书在此分岔）

`openFilePath` 读取 `getFileMeta(filePath)` 后按四级优先级决定 `pendingRestore*` 状态（:1123-1178）：

```
优先级 1  options.restoreViewportAnchor 显式锚点
          （编辑切回只读、书包命中当前书重载等场景传入）
优先级 2  options.restorePhysicalLine / restoreLine 显式物理行
优先级 3  meta.progress >= 100（读完）→ RESTORE_PHYSICAL_LINE_SCROLL_TO_END
          直接滚到最底（Number.MAX_SAFE_INTEGER 哨兵值，:56）
          为什么读完不恢复 viewState？——窗口缩放会令 viewState 失准，
          读完了就别在"最后一屏"半空中悬着
优先级 4  meta.editorViewState 存在 && viewportTopPhysicalLine 存在
          → 恢复 Monaco 原生视图状态 + 记下校验行
优先级 5  仅 viewportTopPhysicalLine（书包导入等没有 viewState 的场景）
优先级 6  全无 → 不恢复，留在顶部
```

**新书**走的必然是优先级 6：没有 meta，四个 pendingRestore 全部置 null。

`RESTORE_PHYSICAL_LINE_SCROLL_TO_END = Number.MAX_SAFE_INTEGER` 是一个漂亮的哨兵：它天然大于任何物理行总数，流结束后在 useAppWindowBindings.ts:500 触发 scrollToBottom，无需再传一个"读到结尾"的布尔标志。

### 阶段 3：会话重置（resetSession，:397-416）

```
resetSession(filePath) 一次性清空全部会话状态：
  currentFile = filePath        （★ UI 立即感知到"新书"）
  chapters = [] / activeChapterIdx = -1
  viewportTopLine = viewportEndLine = 1
  totalCharCount = totalLineCount = 0
  fileEncoding = "-"  currentFileSize = null
  readingProgressSynced = false  ★（进度同步门闸关闭，见阶段 7）
  loading = true / loadingProgressPercent = 0
  stream.resetStreamInternals()
  readerRef.clear({ keepStickyHiddenForStream: true })
  readerRef.resetToTop()
```

`keepStickyHiddenForStream`：清空 Monaco 时把粘性章节条藏起来且**保持隐藏到流结束**——否则加载中途旧内容残影会顶着一条幽灵标题。`resetSession` 里还先 `clearReaderBeforeResolve`（:45 注释：先清空再解析，让用户立刻看到"正在加载"而不是旧书内容）。

随后（:1180-1194）：

```
readerEditMode = readerEditorDirty = false     编辑态强制退出
physicalReaderPath = resolved.physicalPath      磁盘实际读取路径
currentFileSize = resolved.displaySize
scheduleDeferredFileListSizeSync(...)           侧栏 size 列延迟写回
  → requestIdleCallback 挂起（2s 超时兜底），避免与首帧流式加载抢主线程 :148-178
touchRecentFile(filePath, moveToTop:true, persistRecent:true, updateMeta:false)
  → 写入最近打开（MRU 置顶）但不动 meta —— meta 由后续进度快照负责
await waitNextPaintFrame()                      ★ 等一帧 requestAnimationFrame
  → 让 Monaco 在空文档上完成一次绘制，避免黏性章节标题滞留（:45-50 注释）
window.colorTxt.streamFile(physicalReaderPath, { sessionFilePath })
  → 发起 IPC 流式读取，进入阶段 4
```

`waitNextPaintFrame` 是典型的"一帧换正确性"：0ms 的代价换取 Monaco 内部在空模型上刷掉旧 sticky widget，否则新书加载完成后视口顶上会残留旧书的章节条。

### 阶段 4：流式加载（主进程 → 渲染进程的搬运）

```
主进程 ipcHandlers.ts:908-951
  detectEncoding（BOM → jschardet → ANSI 启发式）→ iconv decoder
  createReadStream 256KB 分块
  file:stream-start {encoding, totalBytes}   → 渲染层记 requestId、置进度 0
  file:stream-chunk {text, readBytes}   ×N
      渲染层 useAppWindowBindings.ts:365-368：
        校验 requestId 一致 → processChunk(payload.text) → loadingProgressPercent 更新
  file:stream-end → 渲染层 await flushCarry()

渲染层物理行切分 services/physicalLineStream.ts:14-66
  createPhysicalLineSplitter()：单遍 O(n) 扫描，按 \r\n / \r / \n 切行
  ★ 跨 chunk 的孤立 \r 暂存到 buf 等下一块拼接（:39-41）——CRLF 恰好被
    256KB 切断时不会多算一行
  flushEof() 吐出文件末尾没有换行符的最后一行

useTxtStreamPipeline.ts:247-252 processChunk
  lineSplitter.push(chunk) → 逐行 physicalLineContents.push(rawLine)
  ★ 流式阶段【只做一件事：累积物理行数组】，不统计字数、不匹配章节、
    不写 Monaco（:40 注释原文："仅累积物理行与加载进度；展示格式化与
    章节匹配在加载完成后统一处理"）
```

**这是 v2.1 加载管线重构的核心**（CHANGELOG："加载期间不统计字数、不匹配章节……对大文件的体验有明显优化"）。旧版边读边格式化，导致改一个空行压缩选项都要重新读盘；重构后物理行成为"唯一事实源"常驻内存，所有格式化都在内存数组上重放（见阶段 5 与 4.4）。

### 阶段 5：格式化管线（流结束后的内存加工）

```
flushCarry → finalizeReaderMonaco → applyReaderDisplayFromPhysicalLines
（useTxtStreamPipeline.ts:292-358）

① formatPhysicalLinesForReaderAsync（readerDisplayPipeline.ts:577）
   异步版每 8000 行 yieldToUi 让出 UI 一次（yieldEvery = 8000）
   步骤：
     a. MD 内链剥离（电子书脚注/锚点）
     b. collectQualifiedChapterTitlePhysicalLines（:217）
        ★ 首扫章节：在【物理行】上跑章节正则（内置 3 条 + 自定义规则，
          chapter.ts:33/222），并按 minCharCount（默认 100 字）过滤——
          累计正文字数不足阈值的"标题"不认（防把"第 1 天"误判成章节）
     c. 逐物理行处理：空行压缩（可保留 1 行）、章节标题上下留白插入、
        行首缩进、MD 锚点行跳过
   产出 ReaderDisplayFormatResult（:66）：
     text                                展示全文（\n 连接）
     displayLineToPhysicalLine: number[]  展示行 → 物理行 映射表 ★
     chapterTitleDisplayLineByPhysical   标题行双坐标登记
     ebookSidecar                        MD 内链/插图侧车

② 后处理（useTxtStreamPipeline.ts:317-358）
   applyReplaceRulesToDisplayText   自定义文本替换规则（正文/标题分轨）
   applyTextDisplayConverts          简繁互转 / 全半角（OpenCC 在主进程，
                                    仅作用于【展示层】，磁盘原文不动）

③ 同步映射缓存
   filteredDisplayToPhysicalLine / lastFormattedDisplayLines / 章节双坐标表
```

为什么空行压缩/缩进/替换规则都改"展示层"而不改原文：①原文是用户的文件，软件无权篡改；②阅读数据（书签/标注/进度）全部锚定物理行，只要映射表在，格式化参数随便改、重放映射即可，阅读数据永不失效——这就是"双坐标系"的回报。

### 阶段 6：写入 Monaco（setFullText 的轻重两条路）

```
ReaderMain.vue:1766 setFullText(text, {heavy})
  heavy 判定（useTxtStreamPipeline.ts:362）：
    lineCount > 80_000 || displayText.length > 25_000_000

  普通路径 :1811  m.setValue(text)
  heavy 路径 :1789 createModel(text, langId, Uri) → editor.setModel(nextModel)
               → 旧 model dispose()
               + 临时关闭语法高亮，setTimeout 延后恢复（:1779/1818）
               ★ 为什么换 model 而不是 setValue：setValue 对超长文本要做
                 重复分词与差异计算，createModel 是一次性构建，快得多
  之后 await yieldToUi() + afterNextPaints() 等两帧（:1813-1814）
```

配套的防降级选项（readerEditorOptions.ts）——**三次主动关闭 Monaco 自带优化**：

| 选项 | 值 | 为什么关 |
|---|---|---|
| `largeFileOptimizations` | false（:165） | Monaco 在 >30 万行时会切换到 `ViewModelLinesFromModelAsIs` 彻底关闭视口换行并跳过 stickyScroll。网文转载 txt 一行一句，行数极易破 30 万——关掉换取"正确排版" |
| `disableMonospaceOptimizations` | true（:172） | 京華老宋体 `@font-face` 被 Monaco 判等宽，拉丁字母选区左偏（issue #22） |
| `stopRenderingLineAfter` | -1 | 不截断超长行渲染 |
| `maxTokenizationLineLength` | 1,000,000 | 允许超长段落分词 |

### 阶段 7：视口落位与进度同步翻转（新书=顶部，但门闸同样要走）

流结束后 useAppWindowBindings.ts:389-559 执行视口恢复。新书无锚点 → 落位到顶部。但紧接着有一件所有书都一样的大事：

```
视口恢复完成 → readingProgressSynced = true（openFile 后置 false，:400）

watch(readingProgressSynced)（useAppPersistence.ts:982-995）
  false → true 翻转瞬间：
    ① touchFileLastOpened(path)     写 lastOpenedAt（forced 模式防抖写盘）
    ② touchRecentFile(p, updateMeta:false)
       ★ 补一次"位置快照"：就算用户此后一页没翻，viewState 也已落进内存
         meta——书包导入只有锚点行、用户没滚动时也能落盘 viewState（:989 注释）
    ③ scheduleFileMetaDiskWrite("gated")   排一次受门控的写盘
```

**`readingProgressSynced` 是整个持久化体系的总门闸**：false 期间（加载中/恢复中），一切 live 视口信息都不许写 meta——因为此刻 Monaco 很可能还停在顶部，拿这个视口去覆盖 meta 等于清空用户的真实进度。它在三个地方把关：rememberCurrentFileLine（:373）、touchRecentFile 的 canCaptureLiveViewport（:862）、runScheduledFileMetaWrite 的 gated 分支（:616）。

### 阶段 8：章节列表异步构建（不阻塞首屏）

```
视口恢复 + probe 更新完成后
syncChaptersAfterViewportSettled（App.vue:2157）
  → requestIdleCallback({timeout:3000})（useAppWindowBindings.ts:414-426）
  → refreshChapterListFromReaderAsync（useAppChapterNavigation.ts:177）

普通书：buildChaptersFromReaderDisplayText——getAllText + split 后逐行
        detectChapterTitle（展示行上二扫，与阶段 5 首扫互补）
heavy（>50,000 行，:195）：reader.getEditorLineContent 逐行读，每 8000 行
        yieldToUi——避免 getAllText+split 双倍内存峰值
MD 书：buildChaptersFromMarkdownPhysicalLines（按 ATX #~######）

产出 → applyChapterListResult（:156）
  chapters = filtered（支持层级树/折叠，chapterListTree.ts）
  reader.setChapters() → Monaco 粘性标题同步（DocumentSymbolProvider
  章节树 + folding ranges + 标题装饰，ReaderMain.vue:1966）
  activeChapterIdx = pickActiveChapterIdx（chapterIndex.ts:7：
  取 probe 行 ≤ 章节首行中最大者；同行多节取 tocOrder 更深者）
```

章节识别故意分两扫：格式化期间在物理行上扫（决定哪里插留白），写入 Monaco 后在展示行上扫（构建侧栏目录），idle 回调执行（不挡首屏渲染）。三层任务三种时机，互不阻塞。

### 阶段 9：新书"可读"了——阅读循环开始

至此新书完全就绪。用户进入阅读循环（详见第四章）。对新书而言的第一件事通常是滚动——每次滚动 probe 都会以 `touchRecentFile(updateMeta:false)` **原地改**内存 meta 的 progress（不重建数组、不触发防抖写盘，见 6.3），保证"看到哪、记到哪"而不付出每帧 IO。

### 阶段 10：关闭（两条路径）

**A. 只关书不关窗**（closeCurrentFile，useAppFileSession.ts:338-369）：

```
编辑守卫 → rememberCurrentFileLine()（进度+viewState 落盘）
  → 四个 pendingRestore* 清空
  → readingProgressSynced = true（没有打开文件时门闸常开）
  → 全字段清零 + stream.resetStreamInternals()
  → readerRef.clear() + resetToTop()
  （currentFile = null，UI 回到空态；书架和 meta 里的记录全保留）
```

**B. 关闭整个窗口**——这是"直到关闭"的最后一段，发生的事远比想象多：

```
用户点 ×
→ 主进程 windowCloseGuard.ts:29-40 三规则仲裁：
   ① allowNextClose 集合中有此窗 → 放行（渲染层已确认过的"第二次 close"）
   ② appIsQuitting == true → 放行（quit 进行中必须绕过，否则 macOS 上
      Cmd+Q 会被 preventDefault 卡住，进程残留）
   ③ 其余 → preventDefault + webContents.send("window:requestClose")
      ★ 把"关不关"的决定权交给渲染进程
→ 渲染层 handleWindowCloseRequest（App.vue:2773）
   编辑模式且有未保存修改 → 确认框；否则直接 proceedCloseWindow
→ IPC window:proceedClose → 主进程 allowNextClose.add(win) + win.close()
→ 二次 close 命中规则①，真关
→ 关窗瞬间渲染层 pagehide / beforeunload → persistWindowUnloadState()
   （useAppPersistence.ts:1772-1788，细节见 6.4）
→ 主进程 win "closed"（windowFactory.ts:110-128）：清理 4 个 Map；
   若已无任何用户窗 → destroyEyedropperOverlays + destroyAllBackstageWebViews
→ 若是最后一个窗 → window-all-closed（main/index.ts:122-129）：
   再拆一遍隐藏窗 + markAppQuittingForClose + app.quit() 二次收尾
   （macOS Cmd+Q 首次常被 close 拦截 cancel，靠这条路径兜底）
```

**为什么要绕这么大一圈（拦截→问渲染层→再 close）**：因为"未保存的编辑"只存在于渲染进程内存里，主进程不知道；同时 pagehide 落盘必须发生在渲染进程还活着的时候。这套握手保证：确认框有机会弹出、落盘有机会执行、quit 不会死锁。

---

> AI生成## 三、旧书阅读全流程：进度如何毫厘不差地回来

> "旧书"三种场景：①启动应用自动恢复上次会话；②从书架/最近打开点开一本读过的书（走 openFilePath，阶段 2 仲裁到优先级 3/4/5）；③读完 100% 再开。本节以场景①为主线（最完整），场景②③只差在仲裁入口。

### 阶段 0：谁有资格恢复——主进程的会话恢复门

```typescript
// windowFactory.ts:60-69
const shouldRestoreSession =
  !hasOtherMainWindow && !openTxtPath && !openFindBook;
shouldRestoreSessionByWindowId.set(win.id, shouldRestoreSession);
```

三个条件缺一不可：**没有其它主窗**（两个窗恢复同一本书会互踩进度）、**不是带路径启动**（外部双击打开的书优先于"上次的书"）、**不是找书窗**。这个布尔值按窗口 id 存在主进程 Map 里，渲染进程启动后经 IPC `window:shouldRestoreSession` 拉取（useAppWindowBindings.ts:766）。

用户设置里还有一层开关 `restoreSessionOnStartup`（settings）：
- 关闭时：卸载落盘的 session 快照直接写 `currentFile: null`（persistReadingSessionSnapshot，useAppPersistence.ts:1763-1768）——不存任何可恢复内容
- 设置面板取消勾选的瞬间：`clearPersistedSession()` 清掉既有快照（App.vue:3558-3560）

### 阶段 1：tryRestoreSession（useAppFileSession.ts:433-519）

```
① loadSessionSnapshot(localStorage, sessionKey)
   读 {currentFile, viewportTopLine, viewportBottomLine}（都是物理行）
   无快照 → 直接结束
② restoreFileListFromSession()   书架恢复（已在启动编排第 5 步做过，
   这里防御性再走一次）
③ 无 currentFile（上次关窗时书是关着的）→ 侧栏切到"文件"页，结束
④ window.colorTxt.stat(path)     上次的文件被删/移动了？→ 侧栏回"文件"页
⑤ clearReaderBeforeResolve()     先清空阅读区（让"正在加载"可感知）
⑥ resolvePhysicalTextForOpen(path)
   电子书的严格缓存在此命中：convertedMdPath 存在 && mtime 一致
   → 秒开；不一致 → 静默重新转换并更新 meta
⑦ meta = getFileMeta(path)  → 恢复仲裁（与新书阶段 2 同一套代码，:464-501）
⑧ resetSession(path) → waitNextPaintFrame() → streamFile(physicalPath)
```

**注意**：恢复路径与打开路径共用 `resolvePhysicalTextForOpen` + 仲裁 + `resetSession` + `streamFile`——旧书恢复不是另一套代码，而是"新书管线 + 预先注入的四个 pendingRestore 状态"。单一管线，两种体验。

### 阶段 2：恢复仲裁（旧书与 session 的合并裁决）

恢复时数据有**两个来源**要融合：session 快照（视口底行）与 file.meta（viewState + 锚点 + progress）。仲裁逻辑（:474-501）：

```
① meta.progress >= 100 → pendingRestorePhysicalLine = MAX_SAFE_INTEGER
   （读完的书直接到底部，不信任缩放后失准的 viewState）
② meta.editorViewState + viewportTopPhysicalLine 齐全
   → pendingRestoreEditorViewState = savedVs（Monaco 原生状态恢复）
   → pendingRestoreViewportTopPhysicalLine = anchor（校验用）
③ 只有 viewportTopPhysicalLine（书包导入的书只有锚点行）
   → pendingRestorePhysicalLine = anchor
④ session.viewportTopLine == 1（上次打开后没翻过页）
   → 不恢复，留顶部（:497-499 注释："说明可能只是打开过文件未开始阅读"）
⑤ 否则 → pendingRestorePhysicalLine = session.viewportBottomLine
   （视口底行对齐语义）
```

### 阶段 3：流结束后的视口恢复执行（useAppWindowBindings.ts:389-559）

这是整个恢复体系的精密部分。为什么不能"存 scrollTop、恢复 scrollTop"？三个原因都写在代码注释里：

1. **空行漂移**：空行压缩会在同一物理行下插入空白展示行；如果锚点恰好落在空行，恢复时对齐到首条正文行，"每次切换下移一行"（readerViewportAnchor.ts:69-72 注释原文）
2. **段间距改变高度语义**：lineSpacing 补丁改写了 `getTopForLineNumber`，同一 scrollTop 在段间距 0 和 40px 下对应完全不同的物理行
3. **折行参数改变视觉行数**：字号/折行策略变了，一物理行折出的视觉行数就变了

所以 ColorTxt 存的是**布局无关锚点** `ReaderViewportRestoreAnchor`：

```typescript
// readerViewportAnchor.ts:6
type ReaderViewportRestoreAnchor = {
  physicalLine: number;     // 源物理行号
  wrappedLineIndex: number;  // 该物理行折行后的第几条视觉行（0-based）
};
```

采锚（captureReaderViewportRestoreAnchor，:86）与恢复（computeScrollTopForReaderViewportRestoreAnchor，:146）：

```
采锚：targetY = scrollTop + (slot-1)*lineHeight（slot=2：视口顶沿往下第 2 条字高带）
  → 二分查找 findModelLineAtContentY 命中模型行
  → preferNonBlankDisplayLineForAnchor：落在空行则上移到非空行（防漂移）
  → display→物理行换算 + computeWrappedLineIndexInModelLine 记折行内下标

恢复：物理行 → resolveDisplayLineForViewportRestore（优先非空正文展示行）
  → lineTop = getTopForLineNumber(displayLine)
  → blockH 扣除段间距（lineSpacing.ts 注入的偏移）
  → targetTop = lineTop + wrappedIdx*lineHeight - (slot-1)*lineHeight
  → 使锚点精确落回"第 2 条字高带"——与采锚时同一个相对位置
```

viewState 路径的**校验兜底**：`restoreEditorViewState` 恢复 Monaco 原生状态后，校验"恢复后视口首行的物理行"是否等于当初存的 `viewportTopPhysicalLine`（:429）；不一致（文件被外部改动/格式化参数变了）→ 按锚点行兜底 jumpToLine。**原生恢复 + 双坐标校验 + 兜底**，三层保险。

viewState 里还有什么：光标位置、水平滚动、折叠状态、选区——这些是"你合上书时编辑器长什么样"的完整底片，物理行锚点只保底不保真。

### 阶段 4：进度同步翻转后的补偿（与新书阶段 7 相同，但意义不同）

旧书恢复完视口，`readingProgressSynced` 翻 true，watch 触发"补一次位置快照"。对旧书这次快照尤其重要：**viewState 只有在保存过一次后下次才能恢复**——刚恢复完立即再存一次，形成"存→恢复→再存"的闭环。如果用户开着书直接关机（异常退出），下一次还能恢复。

### 阶段 5：阅读循环 → 关闭

与新书完全一致（第四章 + 阶段 10）。唯一的差异在关窗落盘时：`persistReadingSessionSnapshot` 写 session 快照记录的是**本窗**的 currentFile 与物理行（useAppPersistence.ts:1754-1769）——多窗时谁最后关，下次启动恢复谁的书（:1763-1768 经 `restoreOnStartup` 门控）。

### 补充：三种"书变了"的自愈

旧书最怕的是"文件变了、旧数据失效"。ColorTxt 的三道防线：

| 变化 | 检测 | 自愈 |
|---|---|---|
| 电子书源文件更新（mtime 变） | ensureEbookMarkdown 严格缓存检查 | 静默重新转换，meta 更新 convertedMdPath/mtime；进度按物理行锚点尽力恢复 |
| 正文被编辑过、标注错位 | ReaderAnnotationRecord 存原文快照 text | 区间与快照不符 → 标 `stale:true`，UI 显示失效标记而非错误高亮 |
| viewState 与实际布局不符 | 视口首行物理行校验 | 弃用 viewState，按锚点行兜底滚动 |

---

## 四、阅读中的微观循环（新旧书共用）

### 4.1 滚动一帧：从滚轮到侧栏的完整事件链

```
用户滚轮
→ Monaco onDidScrollChange（ReaderMain.vue:4714）
   同时触发三件事：emitProbeLine(true) / flushReaderBackgroundStickyAlign
                  / scheduleReadingRulerFollowViewport（阅读尺跟随）
→ emitProbeLine（:4447）
   probeLine = 视口内约 3/4 处的行（startLine + floor(span*0.75)，:4326）
   atBottom / percent 计算 → emit 四个事件：
   probeLineChange / viewportTopLineChange / viewportEndLineChange
   / viewportVisualProgressChange
→ programmaticScrollDepth 判定（:1691-1698）
   程序性滚动（跳转/恢复）beginProgrammaticScroll() 递增、500ms 自减；
   fromReadingScroll = 用户滚动才为 true —— 区分"用户在读书"和"程序在搬视口"
→ App 层 onProbeLineChangeForTimedScroll（App.vue:2373）
   ① chapterNav.onProbeLineChange：重算 activeChapterIdx，变了则侧栏
      平滑滚动居中到当前章（useAppChapterNavigation.ts:133-153）
   ② nudgeTimedScrollTimer()：手动滚动重置自动滚动计时（防"刚翻完
      立刻被自动滚一屏"）
   ③ 进度同步：readingProgressSynced && currentFile 时
      touchRecentFile(path, false, {updateMeta:false, progress})
      —— updateMeta:false = 原地改内存 meta，不重建数组（:902-912），
        防抖写盘交给后续时机；滚动每帧绝不能整表重建（:832 注释原文：
        "滚动 probe 切勿开启 rebuildProgressMap，否则每帧整表重建映射会卡死滚动"）
```

probe 取 3/4 处而不是视口顶/底：章节判定要"你正在看的这一段"属于哪章，视口中间偏下才是视觉重心。

### 4.2 翻页（空格/PageDown）：粘性标题避让

```
scrollByPageStep(+1)（ReaderMain.vue:4128）
  lastCompletelyVisibleModelPosition 取最后完整可见行
  → predictStickyChapterScrollHeight 预测翻过去后粘性章节条会占多高
  → alignLineBelowSticky：把落点行顶对齐到【粘性条下沿】
  → scheduleAfterPageTurnScrollSettled：等 smooth 滚动稳定后再校正一次
     （动画期间布局仍在变，一次对齐不够）
向上翻：取粘性条下首条完整可见行 → 对齐到视口底（重叠一行，防丢行）
兜底：scrollByDeltaY(viewportHeight - reserveSticky - lineHeight)
```

v3.7 #80 的成果："翻页时相邻两页重叠一条完整行，避免被粘性章节标题盖住"——预测条高 + 事后校正双保险。

### 4.3 跳章/书签/搜索：锚点 slot 统一定位

三种跳转全部走"视口槽位"（readerViewportAnchor.ts）——目标行不必滚到视口顶，而是对齐到**顶部往下第 N 条字高带**：

| 跳转类型 | slot | 为什么 |
|---|---|---|
| 章节跳转 | `max(1, headingLevel)` | 层级越深留白越少，都为粘性条腾空间（:16） |
| 书签跳转 | 固定 2（:21） | 单层粘性条 |
| 搜索命中 | 居中再上移半行（useReaderInlineSearch.ts:224-233） | 命中行偏上一行便于看上下文 |

书签的存取对称设计：保存锚取 `scrollTop + 1 lineHeight` 处的行（`getBookmarkSaveAnchorDisplayLine`，ReaderMain.vue:3123）——与跳回后光标行一致，避免"跳回去位置差一行"。

### 4.4 实时改格式化参数：锚点桥接

改字号/段间距/空行压缩/章节规则时（App.vue:3564-3610）：

```
captureViewportRestoreAnchor()（采锚）
  → applyReaderDisplayFromPhysicalLines(anchor)（内存重放格式化，不读盘）
  → 恢复锚点（同物理行同折行下标 → 同"第 2 字高带"相对位置）
→ syncChaptersAfterViewportSettled()（章节列表按需重建）
```

**v2.1 重构的直接回报**：改排版参数 = 纯内存操作 + 锚点保持。用户的眼睛几乎感觉不到跳动。

### 4.5 语音朗读与 AI 助手的运行时介入点（概览）

- **TTS**：朗读前按行送 AI 识别说话人（上下文 = 角色表 + 邻近非对白行，缓存结果）；合成在主进程 provider（edge/dashscope/minimax/mimo/volcengine/winSapi），音频与"标点停顿区间"（Edge WordBoundary 方案）一并回渲染层播放
- **AI 助手**：提问 → agentChat 工具循环 → ragSearch（vector.sqlite + sqlite-vec 本地向量检索）/ ragContext（优先从阅读器直接取整章原文，≤1 万字全量、超长压缩）/ mindmap / wordcloud → 流式回复
- **防剧透 spoilerSafe**：限制 RAG 检索章节上限——只准查"已读过的章节"

---

> AI生成## 五、多窗体运行逻辑

### 5.1 窗口类型全景（7 种）

| 窗口 | 创建入口 | 标记方式 | 页面 | 关键参数 |
|---|---|---|---|---|
| 主阅读窗 | windowFactory.ts:51 | Map 排除法 | index.html | show:false → ready-to-show；bounds 持久化 |
| 找书窗 | 同工厂 openFindBook:true | `findBookWindowByWindowId` Map | find-book.html | 同一工厂不同页面；标题/图标独立 |
| 摸鱼阅读窗 | stealthReader.ts:433 | 实例挂 `__colortxtStealthReader` | stealth-reader.html | 无边框/透明/置顶/skipTaskbar/**focusable:false** |
| 摸鱼设置窗 | stealthSettingsWindow.ts:87 | `__colortxtStealthSettings` | stealth-settings.html | 故意不设 parent（透明子窗在 Win 会垫白底，:108 注释） |
| 取色覆盖层 | eyedropper.ts:191 | `__colortxtEyedropper` | eyedropper.html | 每屏一窗、贴冻结截图、非真透明 |
| 书源后台 webView | backstageWebView.ts:256 | `__colortxtBackstageWebView` | 远程 URL / data: | show:false/sandbox/无 preload，每次任务一窗即抛 |
| 登录验证窗 | sourceVerification.ts:448 | activeWindows Map | 远程页 + 2 个 BrowserView | 主窗体 + footer 工具栏双 View 结构 |

**统一的窗口识别模式**：所有"隐藏/工具型"窗口靠给 BrowserWindow 实例挂私有属性打标记；`BrowserWindow.getAllWindows()` + 排除法判断"用户窗"。这套过滤器在 5 处重复出现（globalShortcuts.ts:27、windowFactory.ts:60/116、index.ts:100、openTxtInMainWindow.ts:9）——新增窗口类型必须同步维护，否则会被老板键误操作或挡住退出。这是该架构最明显的脆弱点。

### 5.2 多主窗并存：谁恢复会话、外部文件给谁

- **会话恢复**：只有第一个主窗（shouldRestoreSession 三条件，见 3.1）
- **外部双击 txt**：`openTxtInMainWindow` 优先发给**最近获得焦点的主窗**（mainWindowFocusState.lastId，openTxtInMainWindow.ts:32-40）；无主窗才新建
- **多主窗各读各的书**：互不干扰，但共享同一份 localStorage（meta/recent）——防覆盖见 5.5

### 5.3 摸鱼模式全链路（多窗口体系的集大成者）

**进入**（F9，App.vue:2887）：

```
源窗收集 payload：整本全文（getAllText）/ 视口顶行 / 章节快照 / bounds
  （bounds 优先用 localStorage 存的上次位置，首次用 Monaco 阅读区的
    屏幕 bounds：DOM rect + window:getContentBounds 原点叠加，App.vue:2866）
→ IPC stealthReader:enter
→ enterFromOwner（stealthReader.ts:572-599）
   单例：已有会话且同源窗 → 唤回显示；其它源窗抢占 → 先 teardown 恢复旧源窗
→ createOverlayWindow（:433-470）：透明/无边框/置顶(screen-saver 层级)
   /skipTaskbar/focusable:false（点击不激活，翻页全靠全局键）
   Windows 加 type:"toolbar" + backgroundMaterial:"none"（防 Win11 失焦垫底）
→ ready-to-show 后：★ 先藏源窗 owner.setSkipTaskbar(true)+hide()
   （连任务栏图标一起藏）→ overlay showInactive（不抢焦点）→ 注册翻页
   全局键 → 启动 z-order 看护
```

**运行中**：

- 翻页数据**完全本地化**：进入时全文快照一次性搬运（payload 经主进程中转、boot 拉取后即清），覆盖层自己离屏测量分页（stealthPaginate：fitsSlice → fitPageEnd 排页 → pageStack 翻页栈 → rAF 预取下一页）；连点合并到下一帧、单帧最多 12 页
- **切章三段式请求-应答**（找书窗单章场景）：覆盖层贴边 → `ownerChapterNav` → 主进程转发源窗 → 源窗换章 → `updatePayload`（写 pending + reloadPayload 命令，注释明确"只走 pending+command，避免大正文双通道 IPC"）→ 覆盖层拉取应用；15s 超时解锁
- **设置同步**：设置窗写 localStorage `colorTxt.stealth.settings` → storage 事件跨窗触发 → 覆盖层即时应用 + 主进程重注册全局键
- **进度只在退出时回传**：exit 携带当前逻辑行 → `ownerProgress` → 源窗 jumpToLine（摸鱼期间源窗不滚动）

**老板键（Ctrl+`，可自定义）**（globalShortcuts.ts:47-84）：

```
隐藏：每窗记最小化快照 → setSkipTaskbar(true) + hide()（Windows 靠这个
      去任务栏图标）+ 摸鱼中 overlay.hide()（★ 不注销翻页键，藏着也能翻）
      macOS 走 app.dock.hide()
恢复：skipTaskbar(false) → 摸鱼中 showInactive（不抢焦点防盖覆盖层）
      → 重申置顶 → 重启 z-order 看护；还原各自最小化状态
```

**Windows 专属补丁群**（全项目 Windows 工程补丁最密集处）：

| 问题 | 补丁 |
|---|---|
| 无边框窗最小高约 39px，单行窗做不到 | `setShape` 把可视/点击区裁回逻辑尺寸（overlayLogicalBounds 机制，:239-262） |
| 点任务栏时系统强抬任务栏，压过置顶摸鱼窗（#91） | 指针进入任务栏条带立即重申置顶 + 700ms 周期兜底（:158-226） |
| 高 DPI 拖动把物理/逻辑像素混算，越拖越大（#89） | 拖动时钉死逻辑宽高 |
| Win11 DWM 对透明窗垫实心底 | backgroundMaterial:"none" + 设置窗抢焦点后水平微移 1px 逼重绘 |

**退出**（teardown，:519-542，5 条销毁路径全部汇入）：置空 session → 停看护 → 注销全局键 → 连坐关闭设置窗 → 清 shape → destroy → restoreOwner（源窗 show + focus + ownerProgress 回传行号）。

### 5.4 跨窗通信全景

| 通道 | 机制 | 用途 |
|---|---|---|
| `stealthReader:*` 全家 | IPC invoke/send | 摸鱼进出场/翻页/切章/bounds |
| localStorage storage 事件 | 同源自动跨窗 | file.list / file.meta / recent / ui.settings / stealth.settings / 主题 |
| `theme:sync`、`window:fullscreen-changed` | 主进程广播 | 主题与全屏态多窗一致 |
| `app:open-txt-path` | 主进程 → 目标主窗 | 外部打开路由（preload 有队列+回调集合防丢） |
| `bookSource:toast/captchaRequest` | `sendToAppRenderers` 按 URL 过滤广播 | 找书验证码内嵌到各 app 窗（AppCaptchaHost） |
| `window:requestClose/proceedClose` | 双向握手 | 关窗仲裁 |

### 5.5 多主窗防覆盖：合并写盘算法

问题：两窗共用一份 `colorTxt.file.meta`，A 窗整表 setItem 会把 B 窗刚写的进度抹掉。解法（useAppPersistence.ts）：

```
写盘前 mergeFileMetaWithDiskAndPersist（:557-566）
  先读磁盘最新 → mergeFileMetaRecords(本窗内存, 磁盘, {
    preferLocalReadingPath: 本窗正在读的书,   ← 本窗打开的书本窗说了算
    tieBreak: "local"                          ← 同条冲突时本窗 updatedAt 新鲜
  }) → 合并结果再写回
读他窗写盘（onStorageSync → fileMetaKey，:769-811）
  syncFileMetaFromOtherWindow（:737-766）：
  以磁盘为权威重载，但【本窗正在读的书】若仍在磁盘上 → 仅保留本窗
  未落盘的 progress/editorViewState/viewportTopPhysicalLine 三个字段盖回去
  （读到的快照只用于拼写回盘，不合并进本窗内存——:1700 注释）
```

一套"写时合并、读时让权、活跃文件特权"的三原则。UI 设置同理：`buildSettingsPersistPatch` 只把本窗**相对基线有改动**的字段盖上去；侧栏宽度/极简/朗读等"每窗独立"字段在 storage 事件里显式不 apply（:802-810）。

### 5.6 关闭握手与退出收尾

关窗握手已在 2.10 详述。退出收尾是三段式：

```
before-quit（index.ts:112-116）：销毁摸鱼窗/取色层/全部后台 webView
  （这些窗不挂 close guard，直接 destroy）
→ 各用户窗 close：appIsQuitting=true 直通
→ will-quit：注销全局快捷键 + macOS 恢复 Dock
→ window-all-closed：再拆一遍隐藏窗 + markAppQuittingForClose
  + app.quit()（macOS Cmd+Q 首次被 close cancel 后的二次收尾，:126 注释）
```

---

## 六、落盘体系总表：什么时候写、写到哪、怎么防冲突

### 6.1 写盘时机全景

| 时机 | 动作 | 函数 |
|---|---|---|
| 滚动中（每帧） | 进度原地改进内存 meta，**不写盘** | touchRecentFile(updateMeta:false) |
| 打开新书 | recent 置顶写盘；meta 不动 | :1190 |
| 切书/关书前 | 进度 + viewState 落盘（合并防抖 gated） | rememberCurrentFileLine |
| 阅读位置同步翻转 | lastOpenedAt 落盘（forced 防抖）+ 补位置快照 | watch(useAppPersistence.ts:982) |
| 书签/标注变更 | 即时改内存 + 防抖写盘 | upsertBookmark 等 |
| 设置变更 | nextTick 合并后写 ui.settings | persistSettings |
| 关窗（pagehide） | 见 6.4 | persistWindowUnloadState |
| 清缓存/清阅读数据 | sessionStorage 标记 skip → localStorage.clear → reload | 7 步流程 |

### 6.2 两级写盘模式：gated 与 forced

```
persistFileMeta()         → scheduleFileMetaDiskWrite("gated")
persistFileMetaImmediate() → 取消防抖，直接合并写盘（关窗前必须落尽）

runScheduledFileMetaWrite（:610-619）
  mode === "gated" 且 currentFile && !readingProgressSynced → 跳过！
  ★ 门控本尊：进度还没恢复完时，任何常规写盘都直接放弃，
    保留磁盘上上一份可靠数据（宁可晚写，不可写错）
  mergePendingFileMetaMode：pending 中有 forced 则 forced（:537-543）
```

### 6.3 防抖与性能设计

- meta 写盘统一走 `FILE_META_DISK_DEBOUNCE_MS` 防抖合并（:621-628）
- 文件列表写盘前比对 JSON 字符串，相同跳过（`lastPersistedTxtFilesJson`，:659-679）
- 打开时侧栏 size 同步挂 `requestIdleCallback`（2s 兜底）
- 滚动路径上**永不**触发整表重建（多处注释反复强调"否则卡死滚动"）
- 关窗落盘前 `persistFileMetaImmediate` 会把当前打开文件的 `updatedAt` 抬到 now（:709-714）——多窗合并决胜时本窗进度胜出，这是"关窗的书是最新鲜的"的显式声明

### 6.4 关窗卸载落盘（persistWindowUnloadState，:1772-1788）

```
① sessionStorage 有 skipUnloadPersistenceSessionKey="1"？
   → 直接 return（清缓存流程专用防回写，见下）
② 排队中的设置同步落盘 flushPersistSettings()
   （:1779 注释：nextTick 在关窗路径上可能来不及跑）
③ persistReadingSessionSnapshot()  写 colorTxt.session
   （currentFile/物理行，受 restoreOnStartup 门控）
④ persistFileListCache({force:true})  写书架
⑤ flushRecentFilesAndFileMetaToDisk()  recent + meta 立即合并写盘
```

**防回写问题**（清缓存场景）：`localStorage.clear()` 后若直接 reload，卸载事件仍会执行，把清掉前的内存状态原样写回——"清不干净"。解法：clear 前先设 sessionStorage 标记 → 卸载钩子检测到即跳过 → reload → 新页 `initPersistenceBootstrap` 开头清除标记（:1790-1796）。sessionStorage（每窗独立、不跨页存活）恰如其分。

**关窗不整份回写 ui.settings**（useAppWindowBindings.ts:728-731 注释）：界面设置仅在变更时落盘——关窗时用本窗旧内存整份覆盖，会抹掉其它窗刚保存的值（例如找书窗改的主题）。

---

> AI生成## 七、官方迭代史：目的 → 阻碍 → 解决 → 新问题 → 亮点 → 现状

> 完整原始素材（版本时间线总表、issue 对应表、release 原文存档）见姊妹篇《ColorTxt官方迭代史研究报告.md》。本章按"问题驱动的工程叙事"重组。

### 7.0 迭代节奏：5 个月 24 个 release

2026-04-04 v1.0.1 首发 → 2026-09-08 v3.8.11。主线：**1.x 打磨阅读器本体 → 2.0 语音/AI/编辑三合一 → 2.x 深化 → 3.0 书源引擎 → 3.x 全面开花**。7 月中到 9 月初连发 14 版，平均每 3.7 天一个 release，issue 编号直接回链 release 说明——issue 驱动的公开开发闭环。

### 7.1 阅读器内核：选择 Monaco，然后连续四次"关掉它的优化"

**目的**：小说阅读器需要百万行性能、行列定位（书签/笔记锚点）、装饰器体系、Diff 预览（智能排版）——富文本 div 做不了，Monaco（VS Code 内核）天然全有。作者本就是从"在 VS Code 里看小说"（vscode-txt-syntax 插件）的体验出发造的轮子。

**阻碍**：Monaco 是为写代码设计的，不是为读小说——四连撞：

| 阻碍 | 解决 | 版本 |
|---|---|---|
| 中文换行不准（该换不换、连 VS Code 都没完美解决） | **给 Monaco 打补丁**：Vite transform 改写 strings.js / monospaceLineBreaksComputer.js，网文符号（♡※☆→①Ⅰ…）按全角估算字宽、测宽样字从 ｍ 改"汉" | 3.4 |
| 高级换行策略内存大且难释放（上游 monaco#5311，**无解**） | README 直接挂 WARNING 劝退默认使用，转身把"简单换行策略 + 中文补丁"做成主路径 | 3.4 起 |
| 大文件优化反噬（>30 万行禁换行/粘性标题） | `largeFileOptimizations:false` 整体关闭——网文一行一句行数易破 30 万，正确排版优先 | 2.6 |
| 京華老宋体英文选区错位 / 圆角选区抠图露底 | 再关等宽渲染优化、再关圆角选区抠图 | 3.7 / 3.8 |

**段间距**（#53）是补丁层的巅峰：Vite transform 改写 Monaco 内部 `LinesLayout` 四处偏移计算（总高度/行顶/行底/whitespace/视口循环），每物理行结束加常数像素，软换行中间行不加，额外状态 O(1)。docs 里记着踩坑："若只改行高未改 whitespace 偏移，md 插图会叠在上方正文上"。

**新问题**：背景图（3.8）引入后两周内连环修 4 个 bug——粘性标题阴影切开背景图（去阴影）、圆角选区抠图露底（关圆角）、路径问题、堆叠粘性标题（3.8.11 仍在修）。

**现状**：Monaco 补丁体系（中文换行/段间距/左右边距/粘性标题/阅读尺锚点/翻页避让）成为项目护城河；唯一无解项（#5311）诚实挂出。

### 7.2 加载管线：v2.1 的"流式重构"

**目的**：网文 10MB+ 常态，初版边读边统计字数/匹配章节，改一个格式化选项要重新读盘。
**解决**：流式阶段只累积物理行数组；格式化、章节匹配全部推迟到加载完成后，且**全部在内存重放**。
**回报链**：这次重构直接支撑了后来的一切——.md 内链/插图（2.5）、找书阅读器复用（3.0）、阅读尺锚点（3.8）、改字号不跳动（4.4 节的锚点桥接）。

### 7.3 电子书支持：两次推翻自己的中间格式

**第一次（1.2）**：转 .txt，自造 `<<A>>/<<IMG>>` 标记 → **阻碍**：私有标记表达不了层级/插图/链接 → **推翻（2.5）**：改转 Markdown（目录→ATX 标题、内链/注脚、外链），坦率公告"旧文件请重新转换"。
**第二次（3.3）**：手写正则解析 Markdown 边角无穷 → **推翻**：改走 marked 的 `Lexer.lexInline`（与 AI 助手规则一致），移除非标准兜底。
**深水区**：为一个 CHM 格式移植了整个 libmspack C 库到 JS；PDF 三连修（CMap/wasm 随包、XObject 抽图"同一对象只解码一次，不再逐页 getOperatorList"——后者会把整页文字路径搬上主线程、Indexed 调色板 4bit 展开）；标题匹配从"包含匹配"收紧到"仅精确匹配"（防『卷一』+『周纪一』两行正文被误升为 `# 卷一 周纪一`）。
**现状**：统一 .md 中间格式 + 严格缓存（mtime 校验）+ 多候选路径和解查找 = 所有格式的公共底座，新增格式只需写一个 parse*.ts。

### 7.4 语音朗读：七引擎矩阵与 Edge TTS 的 WordBoundary 攻坚

**扩张线**：2.0 三引擎（Edge/系统/通义）→ 2.7 MiniMax + 多音色（旁白/对白分轨、AI 识别说话人）→ 2.8 小米 MiMo → 3.2 Windows SAPI5（为用上讲述人自然语音专门写 winSapiProvider）→ 3.7 火山豆包 2.0（444 音色）。

**最精彩的攻坚（3.8.9-3.8.11，PR #90）**——Edge TTS 标点停顿：
- **目的**：朗读在标点处自然停顿。标准答案是 SSML `<break>`
- **阻碍**：Edge readaloud 端点**不支持 SSML break**，带上直接断连
- **解决**：三层发明——① 主进程收集音频 metadata 的 **WordBoundary** 词边界事件，按词序把全角标点映射为音频内待替换区间 `[fromMs, toMs]`（词与标点粘连按文本比例插值、连续标点合并、ASCII 标点不参与防误伤 12.5/URL）；② 区间随 mp3 一并缓存，"**区间只依赖音频内容，与停顿时长解耦**"——调滑块不废已缓存音频；③ 播放端 decodeAudioData 后把区间整体替换为干净静音（2ms 淡入淡出，时长随语速同比缩放）
- **结果**：仅 Edge 生效（其他引擎的音频流没有词级时间戳），句中/句末两个独立滑块，成为桌面开源阅读器里最完整的 TTS 方案

### 7.5 AI 阅读助手 / RAG：本地向量库与密钥三阶段

**目的**（README 原话的清醒认知）："对话模型擅长思考会说，却不擅长找，也不可能每次提问都把整本小说发给服务器"。
**技术沉淀**：better-sqlite3 + sqlite-vec 本地向量库；内置嵌入模型（BGE Small ZH / E5，Transformers.js Worker 运行，**默认 hf-mirror.com 镜像**——国内可用性）；ragContext 的清醒取舍：章节级问题直接给整章原文（≤1 万字全量、超长压缩），向量检索只做跨章语义检索。
**ragContext 策略（2.2）**：优先从阅读器直接取章节原文而不是向量拼接 chunk——RAG 不是万能锤。
**密钥三阶段**：明文 config.json（≤2.2）→ 系统钥匙串（2.3）→ **保险库 secrets.v1.json 分槽**（多方案时代：chat/txt2img/voice/translation 各自独立），写入经"串行队列 + tmp→rename 原子替换，避免关窗/并发写导致整文件损坏"，旧槽启动迁移后删除。

### 7.6 书源找书：用 TypeScript 复刻 Legado 的 Java 引擎

**目的**：Legado 书源生态（数万社区 JSON）是现成财富，桌面端无人兼容。作者选择不造新格式，直接兼容。
**声明（3.0 CHANGELOG，坦诚到罕见）**："移植了一套 JavaScript 实现，做不到 100% 复刻……只能通过迭代不断纠错兼容，目前算是测试版"。同时明确"不提供、不内置、不分发任何书源"。
**最大阻碍：Rhino(JVM) vs V8 的语义差异**——文档记录了成体系的修补：末尾表达式补 return（对齐 Rhino completion）、`forEach(async…)` 改串行（Rhino 同步阻塞）、形参与 let 同名重命名、Mozilla `let()` 表达式改写、正则字面量修复、零宽字符剥离；Java 桩（DES/AES/Base64/Jsoup.connect）；Jsoup vs Cheerio 行为对齐（`[attr~=val]` 语义、孤立 tr/td 包 table、破损页面先 parse5 纠错再给 xmldom）。
**网络层两次换血**：undici fetch 被 Tengine 类站点 TLS 重置 → 改 Chromium `session.fetch`（浏览器 TLS 指纹，3.3）；WebView Cookie 从 extraHeaders 改 session 注入——docs 记录了惨案："extraHeaders 只作用于首个请求，页面内 AJAX 走空 session → 站点发回游客会话 → persistWebViewCookies 把游客 Cookie 覆盖回 jar，**登录态被静默摧毁**"。Cookie 按 eTLD+1 归档（accounts 子域写 .example.com 会话 Cookie，www 业务域才取得到）。
**结果**：项目最大子系统（独立找书窗 + 书源库 + 章节缓存 + 登录验证窗 + 验证码广播），也是项目出圈主因（科技爱好者周刊、LINUX DO 收录）。

### 7.7 摸鱼模式：11 天 bug 修复马拉松（3.8.0-3.8.11）

一个"不知道有什么用"（作者原话）的功能，上线后 11 天连发版本修复：`setShape` 绕 Windows 最小窗高（单行窗做不到的系统限制）、任务栏 Z 序大战（#91：点任务栏系统强抬任务栏压过置顶窗 → 指针进入任务栏条带立即重申置顶 + 周期兜底）、拖动越拖越大（#89：钉死逻辑宽高）、右键菜单与翻页点击的事件语义分流。
**价值**：把"无边框透明置顶窗"在三大平台的系统级坑位清单趟了一遍，全部沉淀在 stealthReader.ts 的注释里。

### 7.8 注意力经济四部曲与交互统一模型

全屏（1.x，禅模式）→ 极简视图（3.8 #58，F10 边缘唤起）→ 阅读尺（3.8 #83，**明确面向 ADHD 人群**：聚焦行+淡化）→ 摸鱼（3.8 #50）。番茄时钟（3.1，"保护眼睛，健康阅读"）、点击模式（3.7 #4，左键下屏右键上屏，触屏式）。
统一交互模型（docs 详载）：边缘感应唤起、Esc 按层关闭（输入框→蒙版→菜单→查找栏→面板→退全屏，全屏连按两次）、IME 候选框防误收。3.8 的修复列表里 10+ 条极简/全屏修补，全部源于这套模型在真实使用中的边角暴露。

### 7.9 分发工程的三次翻车

- macOS Intel 交叉编译缺 `@node-rs/jieba-darwin-x64` 开即崩 → 改 `macos-15-intel` **原生构建并校验 Mach-O 架构**（3.0）
- AppImage 在缺 FUSE2 的 Ubuntu 24.04 起不来 → 改**静态 AppImage runtime**（#28）
- NSIS 清空安装升级丢数据 → 改**覆盖安装**（3.4）

### 7.10 推翻重来清单（精选 10 条，全 20 条见姊妹篇）

| 推翻 | 时点 | 一句话动机 |
|---|---|---|
| 电子书中间格式 .txt → Markdown | v2.5 | 私有标记表达不了层级/图片 |
| Markdown 解析手写正则 → marked | v3.3 | 私有解析器边角无穷 |
| Monaco 大文件优化：启→禁 | v2.6 | 与软换行/粘性标题冲突 |
| API 密钥：明文→钥匙串→保险库分槽 | v2.3→ | 安全 + 多方案 |
| undici → session.fetch | v3.3 | TLS 指纹被识别 |
| WebView Cookie extraHeaders → session 注入 | 书源期 | 登录态被静默降级 |
| 标题匹配包含 → 仅精确 | ~v3.3 | 正文行误升标题 |
| 列表排序按钮 → 拖动 | v2.4 | 作者自评"上移下移有点呆" |
| macOS 交叉编译 → 原生构建 | v3.0 | 原生模块架构错配 |
| NSIS 清空 → 覆盖安装 | v3.4 | 升级丢数据 |

---

## 八、结语：这个项目的工程哲学

从运行逻辑倒推，ColorTxt 的每一层设计都贯穿着同一条原则：

1. **单一事实源 + 映射层**：磁盘物理行是唯一真相，展示层的一切（格式化/替换/简繁/缩进）都是可重放的映射——所以格式化参数随便改、阅读数据永不失效、锚点跨布局稳定。
2. **门闸优先**：`readingProgressSynced` 一个布尔守住了"加载中不许写进度"；`appIsQuitting` 守住了退出死锁；`skipUnloadPersistence` 守住了清缓存。宁可晚写、宁可重算，不可写错。
3. **诚实面对无解**：上游 Monaco #5311 直接挂 WARNING；书源引擎公告"做不到 100% 复刻"；旧数据不兼容就明说"请重新转换"。
4. **补丁不打洞**：对 Monaco 的六处定制全部集中在 vite transform / 注册回调 / 注入层，不动 Monaco 源码包——可随 Monaco 升级。
5. **Windows 的坑用 Windows 的招**：setShape、screen-saver 层级、toolbar type、周期兜底重申——平台补丁全部带注释说明"为什么"，成为后来者的路标。

它不是最优雅的架构（同一套"用户窗排除法"复制 5 处、App.vue 4452 行单文件编排），但它在 5 个月里以每 3.7 天一版的速度持续吸收真实用户反馈而不崩坏——靠的正是上述纪律。

> 分析基于 v3.8.11 源码（commit 9565e4d）。配套文件：《ColorTxt项目深度分析报告.md》（静态架构/功能/存储）、《ColorTxt官方迭代史研究报告.md》（版本演进原始素材）。

> AI生成
