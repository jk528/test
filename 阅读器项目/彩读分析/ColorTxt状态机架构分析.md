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

# ColorTxt（彩读）状态机架构分析

> 项目：GitHub [ssnangua/ColorTxt](https://github.com/ssnangua/ColorTxt)（本地 TXT 小说阅读器）
> 分析版本：v3.8.11 ｜ 技术栈：Electron 35 + Vue 3 + Monaco Editor + TypeScript
> 方法：源码级静态 + 动态追踪，所有结论标注 `文件:行号`（相对 `src/`）
> 姊妹篇：《ColorTxt项目深度分析报告.md》（静态架构与功能模块）、《ColorTxt运行逻辑全流程深度剖析.md》（运行过程线）

---

## 一、总体架构与状态机地图

ColorTxt 采用 Electron 标准三层进程模型：**主进程**（`src/main`）持有系统侧能力与"无状态服务"（TTS 合成、词典、RAG、书源引擎），**Preload**（`src/preload/index.ts`）仅把 IPC 通道包装为 `window.colorTxt.*`，**渲染进程**（`src/renderer/src`）持有绝大多数**会话级状态机**（阅读、语音朗读、AI 交互、找书 UI）。`src/shared` 提供跨层类型与常量。

| 状态机 | 所属模块 | 状态持有方 | 核心状态 |
| --- | --- | --- | --- |
| 应用/窗口生命周期 | `main/index.ts` + `windowFactory.ts` + `windowCloseGuard.ts` | 主进程 | 启动序列、关窗守卫、退出收尾 |
| 阅读会话（文件加载） | `useAppFileSession.ts` + `useTxtStreamPipeline.ts` | 渲染进程 | `loading` / 流式 `phase` / 竞态代际 |
| 持久化落盘 | `useAppPersistence.ts` | 渲染进程 | 门控 `gated`/`forced` / 防抖 / flush |
| 语音朗读 | `useAppVoiceRead.ts` + `voiceReadLinePlayer.ts` | 渲染进程（主进程仅无状态合成） | `off`/`playing`/`paused` + 合成阶段 `ai`/`tts` |
| 书源搜索 | `searchService.ts` + `useBookSource.ts` | 主进程会话 + 渲染代际 | `Idle`/`Searching`/`LoadingMore`/`Completed`/`Stopped` |
| 章节加载与缓存 | `getChapterContentWithCache.ts` + `useFindBookChapterSession.ts` | 主进程缓存 + 渲染会话 | 缓存命中/未命中/联网/渲染 |
| 整书下载 | `downloadService.ts` + `useBookSource.ts` | 主进程会话 | 排队/缓存/导出/取消 |
| 后台 WebView 会话 | `backstageWebView.ts` + `sourceVerification.ts` | 主进程 | 登录/验证码/JS 挑战重试 |
| AI 向量索引 | `buildBookVectorIndex.ts` + `embedding/*` | 主进程(嵌入 worker) + 渲染(阶段) | `chunking`/`embedding`/`indexing`/就绪/失效 |
| AI Agent 对话 | `agentChat.ts` + `chat.ts` | 主进程 | 流式回合/工具调用/收尾/中断 |
| 文生图/角色卡 | `characterPortrait.ts` + `txt2img/index.ts` | 主进程单例会话 | 检索/生成/中止 |
| AI 智能排版 | `useAiSmartFormat.ts` + `useReaderSmartFormatDiff.ts` | 渲染进程 | 运行/中断/Diff 预览/应用/放弃 |

---

## 二、应用/窗口生命周期状态机

### 2.1 启动序列

启动入口 `main/index.ts:87-110`。协议在 `app.ready` 之前注册（`index.ts:32-43`），`whenReady` 后分支决定开主窗还是找书窗（`--find-book` 标志），并注册全局快捷键。

```mermaid
stateDiagram-v2
    [*] --> 协议注册: module 顶层, app.ready 前
    协议注册 --> whenReady: app.whenReady()
    whenReady --> 开找书窗: argv 含 --find-book
    whenReady --> 开主窗: 常规启动(可带 openTxtPath)
    开主窗 --> ready: createWindow({openTxtPath})
    开找书窗 --> ready: openFindBookLaunchWindow(bookshelf)
    ready --> 运行中: ready-to-show 后 win.show()+focus
    运行中 --> 激活补窗: app.on("activate") 且无用户窗
    运行中 --> 退出: window-all-closed
    退出 --> 收尾: before-quit 销毁摸鱼/取色/后台webView
    收尾 --> [*]: will-quit 注销全局快捷键
```

### 2.2 关窗守卫（防误关/防退出残留）

`windowCloseGuard.ts` 是典型的"二次确认"状态机：首次关窗由渲染进程决定是否 `preventDefault`，确认后经 `window:proceedClose` 再次 `close()` 才真正放行；`allowNextClose` 用 WeakSet 记录一次性放行，`appIsQuitting` 标志在 `app.quit()` 阶段绕过拦截。

```mermaid
stateDiagram-v2
    [*] --> 运行中
    运行中 --> 拦截: 用户点击关闭 → close 事件
    state 拦截 {
        [*] --> 一次性放行: allowNextClose.has(win) → 删除并放行
        [*] --> 放行: appIsQuitting=true(quit 流程)
        [*] --> 询问渲染层: 否则 preventDefault + 发 window:requestClose
        询问渲染层 --> 二次关闭: 渲染层决定关闭 → window:proceedClose → add(win)。再 close()
    }
    拦截 --> 已关闭
    已关闭 --> [*]
```

证据：`windowCloseGuard.ts:3-6`（`allowNextClose` WeakSet、`appIsQuitting`）、`17-22`（proceedClose 放行）、`29-41`（attachWindowCloseRequestGuard 拦截逻辑）；`index.ts:118-129`（before-quit / will-quit / window-all-closed 收尾）。

### 2.3 多窗口互斥与清理

`windowFactory.ts` 用四张 Map（`shouldRestoreSession` / `pendingOpenTxt` / `findBookWindow` / `findBookInitialTab`）以 `windowId` 为键管理窗口态；窗口 `closed` 时清空 Map，并在"无剩余用户窗"时强拆后台 WebView、取色覆盖层、摸鱼窗（`windowFactory.ts:110-128`）。用户窗白名单见 `openTxtInMainWindow.ts:9-21`（排除 findBook / backstage / eyedropper / stealth）。

---

## 三、阅读会话状态机（文件加载）

### 3.1 流式加载管线

渲染进程无 Node fs，文件内容经 `file:stream-start / stream-chunk / stream-end` 三段 IPC 推入（`ipcHandlers.ts`），主进程用 `createReadStream(…{highWaterMark:256KB})` 分块。渲染层以 `activeStreamRequestId` 校验每个 chunk 属于当前流，防御快速切书时旧流迟到 chunk 污染新会话。

```mermaid
stateDiagram-v2
    [*] --> 空闲: loading=false
    空闲 --> 装载中: 打开文件 → loading=true, progress=0
    装载中 --> 流开始: 收到 stream-start {encoding,totalBytes}
    流开始 --> 接收分块: stream-chunk × N, 进度累加
    接收分块 --> 切书竞态: 新请求到来 → prevStream.destroy(), 旧 chunk 因 activeStreamRequestId 不匹配被丢弃
    流开始 --> 切书竞态
    接收分块 --> 流结束: stream-end
    流结束 --> 就绪: loading=false, progress=null, 渲染
    切书竞态 --> 装载中: 新流接管
    就绪 --> 空闲
    装载中 --> 错误: 流异常/文件不可读
    错误 --> 空闲
```

证据：`useAppFileSession.ts:75-76`（`loading`/`loadingProgressPercent` 状态）、`411-412`（置 loading）、`355-356`（复位）、`902`（`p.phase === "start"` 流阶段判断）；运行逻辑报告已论证 `activeStreamRequestId` 竞态防御（`useAppWindowBindings.ts`）。

### 3.2 持久化落盘门控

`useAppPersistence.ts` 是贯穿全文的落盘体系，核心是"门控 + 防抖 + 多窗合并 + 强制 flush"：进度/书签等元数据写入先入 `pendingFileMetaWrite`，按 `gated`/`forced` 两级优先级合并（`force > gate`），窗口关闭或关键时机 `flush` 强制落盘。

```mermaid
stateDiagram-v2
    [*] --> 空闲: pendingFileMetaWrite=null
    空闲 --> 待写gated: scheduleFileMetaDiskWrite("gated")
    空闲 --> 待写forced: scheduleFileMetaDiskWrite("forced")
    待写gated --> 待写forced: forced 覆盖升级(gate 不降级 force)
    待写gated --> 落盘: flush(防抖到期/关窗兜底)
    待写forced --> 落盘: immediate flush
    落盘 --> 空闲: pending 清空
```

证据：`useAppPersistence.ts:541-556`（`mergePendingFileMetaMode`：forced 不被 gated 降级）、`618-627`（`scheduleFileMetaDiskWrite`）、`709`（gated 调度）、`985`（forced 调度）、`725`（`flushRecentFilesAndFileMetaToDisk`）。

---

## 四、语音朗读状态机

### 4.1 分层概览

主进程 `voiceRead/`、`voiceReadEdgeTts.ts`、`ai/voiceReadSpeaker.ts` 都是**无状态的单次合成/分类服务**；真正的会话状态机在渲染进程：顶层 `useAppVoiceRead.ts`（会话三态 `off/playing/paused`）+ `voiceReadLinePlayer.ts`（播放器子状态，用代数式会话失效 `playbackSessionGen` 而非显式枚举）。

### 4.2 顶层会话状态机

```mermaid
stateDiagram-v2
    [*] --> off
    off --> playing: 启动朗读(守卫 canStartVoiceRead: 有文件/非loading/非编辑/有行)
    playing --> paused: 手动暂停 / 自动暂停(达章节或时长阈值) / 加载中断(pauseOnLoading) / 切文件
    paused --> playing: 恢复(resumeFromPause)
    playing --> off: 停止 / 文档末尾 / 进入编辑态 / 加载中 / 切文件
    paused --> off: 停止 / 进入编辑态 / 加载中
    state playing {
        [*] --> 准备AI分类: 需多音色且开启AI → synthesizingPhase="ai"
        准备AI分类 --> TTS合成: synthesizeChunks → synthesizingPhase="tts"
        TTS合成 --> 播放中: onChunkChange 首段回执, 高亮+滚动锚点
        播放中 --> 准备AI分类: 下一批次 while 循环
    }
```

关键状态与守卫（证据：`useAppVoiceRead.ts`）：

| 状态/事件 | 守卫/条件 | 证据 |
| --- | --- | --- |
| 三态定义 | `VoiceReadMode = "off"\|"playing"\|"paused"` | `useAppVoiceRead.ts:56,86-88` |
| 合成阶段 | `synthesizingPhase = "ai"\|"tts"\|null`，`busy = prepareDepth>0 \|\| playerActive \|\| ttsBridge` | `useAppVoiceRead.ts:112-122` |
| 启动守卫 | `canStartVoiceRead`：当前文件非空且非 loading 且非编辑态且行数>0 | `useAppVoiceRead.ts:1132-1139` |
| 循环有效性 | `isPlaybackAlive(gen,mode)`：`gen===playbackLoopGen && mode!=="off"` | `useAppVoiceRead.ts:163-165` |
| 暂停挂起 | `waitIfPaused()`：while(paused) 挂到 `resumeWaiters` | `useAppVoiceRead.ts:200-206` |
| 自动暂停 | 时长模式 1s 轮询累计；章节模式预扫换章点 | `useAppVoiceRead.ts:170-198,447-492` |
| 播放器停止三态 | `stop()` / `pausePlayback()` / `stopForLineJump()` 均走 `abortActivePlayback()`（作废异步+关 AudioContext+取消 speechSynthesis） | `voiceReadLinePlayer.ts:880,889,899,1037-1082` |
| 排播完成判定 | `currentTime >= scheduledEnd-0.05` | `voiceReadLinePlayer.ts:468-474` |

### 4.3 多音色/合成限流

多音色（`VoiceReadScheme = "single"|"multi"`，`voiceReadProfiles.ts:27`）**不改变会话状态**，只改变每个 chunk 的合成输入（音色/情绪/角色卡）；有对白段且开启 AI 时进入 `ai` 合成阶段，否则直达 TTS。主进程设全局串行限流防 HTTP 429：`dashscopeSynthQueue.ts:23-40` / `volcengineSynthQueue.ts:23-73` 用链表 Promise 槽 + 280ms 最小间隔 + 5 次指数退避；Edge 单次重试 3 次（`voiceReadEdgeTts.ts:377-395`）。渲染层 Edge 维持 4 段在途缓冲（`EDGE_BUFFER_SIZE=4`，`voiceReadLinePlayer.ts:286`）。

IPC 合成通道：`voiceRead:synthesize / cancelSynthesis / listVoices / healthCheck`（`shared/voiceReadSynthesisIpc.ts:10-14`），主进程以 `senderId:requestId` 为键挂 `AbortController`，同键新请求先 abort 旧请求（`registerVoiceReadIpc.ts:97-126`）。

### 4.4 端到端合并时序图（合成阶段 → 引擎预处理 → 主进程合成）

纵贯三层的一条真实链路：会话层 `useAppVoiceRead` 先经过 **AI 分类 / TTS 两段合成阶段**，再交给播放器 `voiceReadLinePlayer` 按引擎分流——**Edge 走「预热 4 段 + 生产者/消费者缓冲」**，**云 TTS（DashScope/Volcengine）走主进程串行限流槽**。两类引擎在主进程都是无状态单次合成。

```mermaid
sequenceDiagram
    autonumber
    participant App as 渲染·会话层 useAppVoiceRead
    participant P as 渲染·播放器 voiceReadLinePlayer
    participant M as 主进程 voiceRead IPC + provider
    participant Q as 限流槽 dashscopeSynthQueue

    App->>App: mode="playing", runPlaybackLoop (724)
    App->>App: beginPrepareSynthesis → phase="ai" (752)
    Note over App,M: 需要多音色且开启 AI 时才进入 ai 阶段
    App->>M: voiceRead:attributeSpeakers 引号分类(带缓存/去重, ipcHandlers:1040)
    M-->>App: quotes[] + narrationEmotion + tokenUsage
    App->>App: buildBatchSpeakChunks 切 chunk(音色/情绪落点) (754)
    App->>App: endPrepareSynthesis → phase="tts" (763)
    App->>P: player.speakChunks(settings, chunks) (803)

    alt Edge 引擎：4 段缓冲 生产者-消费者
        P->>P: 预热 prewarm=min(BUFFER=4, n) 段 enqueueEdgeMp3Fetch (1240-1246)
        P->>M: voiceRead:synthesize × 预热段 (edgeProvider)
        M->>M: synthesizeEdgeTtsMp3: WebSocket + 标点停顿 + 最多3次重试
        M-->>P: mp3 + pauses
        par 生产者 runEdgeProducer (1315-1335)
            loop 每段补位 (buffer.size<4 才推进)
                P->>M: voiceRead:synthesize 下段
                M-->>P: mp3
            end
        and 消费者主循环 (1250-1273)
            loop i in chunks
                P->>P: awaitEdgePlaybackCaughtUp → decode 排时间线
                P-->>App: onChunkChange(i,total) 高亮+滚动锚点
                P->>P: edgeFetchBuffer.delete(i) → edgeProducerWake 唤醒生产者
            end
        end
        P->>P: awaitEdgePlaybackDrain 等本行真正播完 (1284)
    else 云 TTS：DashScope/Volcengine 串行限流
        loop 逐段串行合成 (无预取缓冲)
            P->>Q: withDashScopeSynthSlot 链表槽 + 280ms 最小间隔 (23-40)
            Q->>M: fetchDashScopeTts 429/502/503 最多5次指数退避 (42-76)
            M-->>P: SSE 流式 PCM
        end
    end

    P-->>App: speakChunks resolve → waitForPlaybackSettled (804)
    App->>App: while 循环取下一批次 → 重复 (724)
```

时序图要点：

- **AI/TTS 阶段是会话层的两个连续窗口**：`beginPrepareSynthesis` 置 `phase="ai"` → `buildBatchSpeakChunks` 内若需多音色则先经 `voiceRead:attributeSpeakers` 做引号/说话人分类 → `endPrepareSynthesis` 回落到 `phase="tts"`（`useAppVoiceRead.ts:112-122` 的 `syncSynthesizingState` 派生）。
- **Edge 的 4 段缓冲是「预热 + 双循环」**：生产者在 `edgeFetchBuffer.size >= BUFFER` 时挂起等待 `edgeProducerWake`（`voiceReadLinePlayer.ts:1323-1329`），消费者每播完一段 `delete(i)` 并 `wake()` 生产者（`voiceReadLinePlayer.ts:1271-1272`）。
- **云 TTS 无缓冲、只串行限流**：其 4 段预取被 `voiceReadRequiresSerialChunkFetch()` 语义替代（`voiceReadEngineRouting.ts:34-43`），靠主进程 `withDashScopeSynthSlot` 的链表槽 + 最小间隔防 429。
- Edge 的"3 次重试"在 `voiceReadEdgeTts.ts:377-395`，云 TTS 的"5 次退避"在 `dashscopeSynthQueue.ts:49-54`，二者对称但方向相反：一个为稳定订阅、一个为限流避让。

---

## 五、书源找书状态机

### 5.1 搜索流程

主进程持有 `SearchSession`（`searchService.ts:110-122`），渲染层以 `searchSeq` 自增代际丢弃迟到事件。

```mermaid
stateDiagram-v2
    [*] --> Idle: searchPhase=null
    Idle --> Searching: startSearch 建会话 + setImmediate
    Searching --> Searching: sourceDone 累积统计 / result 事件300ms节流(按相关度排序整体下发)
    Searching --> LoadingMore: loadMoreSearch 且 hasMore
    LoadingMore --> LoadingMore: 每源 nextPage+1, hasMore=!failed&&newCount>0
    LoadingMore --> Searching: loadMoreDone 收尾
    Searching --> Stopped: cancelSearch(cancelled=true+撤销验证弹窗+删会话)
    Searching --> Stopped: 渲染层 searchSeq+1 丢弃迟到事件
    Searching --> Completed: 全源结束 → done{cancelled:false,hasMore}
    Stopped --> Idle
    Completed --> [*]
```

关键点：并发池 `SOURCE_CONCURRENCY=4`（`searchService.ts:70`）；单源超时 30s，验证码激活时延展到 600s，`settle` 防双解（`searchService.ts:23-68`）；分页能力需 searchUrl 含 `{{page}}`/`<a,b>`/`@js:`（`searchService.ts:133-141`）。

### 5.2 章节加载与缓存

主进程 `getChapterContentWithCache.ts` 统一"读缓存→回写→再回写"闭环；渲染层 `useFindBookChapterSession.ts` 以 `loadSeq` 作废旧请求。

```mermaid
stateDiagram-v2
    [*] --> ReadCache: 请求第 index 章
    ReadCache --> SkipCache: contentRule 以 <js> 开头且章页URL==书籍页URL(保新鲜)
    ReadCache --> CacheHit: preferCache 且缓存非空
    ReadCache --> CacheMiss: 缓存缺失或 preferCache=false 或 skipChapterCache
    SkipCache --> NetworkFetch
    CacheMiss --> NetworkFetch: getChapterContent 联网解析
    CacheHit --> 渲染管线: 剥重复标题→变化则回写缓存→fromCache=true
    NetworkFetch --> 翻页: fetchContentPage + nextUrl 循环(到下一章边界即停)
    翻页 --> PostProcess: subContent/replaceRegex/标题规则
    PostProcess --> SaveCache: 成功→saveChapterCache(失败仅记日志)
    PostProcess --> Error: 内容为空→统一"获取正文失败"
    SaveCache --> 渲染管线: fromCache=false
    渲染管线 --> 完成: 剥标题→替换净化→简繁全半角→formatPhysical→setFullText→复位loading
```

缓存布局：`userData/book_cache` + 书名前 9 字 + `md5-16(bookUrl)` + 章节 `md5-16(chapterUrl).nb`（`chapterCache.ts:22-34`）。渲染层预判命中时不显示加载遮罩（`useFindBookChapterSession.ts:594-599`）。

### 5.3 整书下载

```mermaid
stateDiagram-v2
    [*] --> Queued: startDownload 建会话(randomUUID) 异步
    Queued --> Preparing: getBookInfo+getChapterList(按阅读序)
    Preparing --> Caching: 逐章 emit, 缺章联网拉取写 book_cache
    Caching --> Caching: 单章失败→仅logs占位, 不中断不重试
    Caching --> Cancelled: session.cancelled→发error(不发done)
    Caching --> CacheOnly: cacheOnly=true→done{filePath:""}
    Caching --> Exporting: 阶段2 仅读缓存拼 .txt
    Exporting --> Completed: done{filePath,bookName}
    Exporting --> Error: body为空→"没有可保存的内容"
    Completed --> [*]: finally 删会话
    Cancelled --> [*]
    Error --> [*]
```

关键点：取消只置 `cancelled` 标志、循环边界检查，会话由 `finally` 统一清理（`downloadService.ts:15-26,85-95,176-243`）；导出阶段读不到的章节写 `[下载失败: 章节未缓存]` 占位（`downloadService.ts:210-213`）。

### 5.4 后台 WebView / 验证会话

手动登录/验证码/JS 挑战页触发后台隐藏 WebView（`backstageWebView.ts`），是唯一带重试的组件（空结果/挑战页重试最多 30 次 × 1s）。

```mermaid
stateDiagram-v2
    [*] --> CreateHidden: 触发后台webView(new BrowserWindow show:false)
    CreateHidden --> SeedCookies: 先清残留再种Cookie/登录态
    SeedCookies --> LoadPage: loadWebViewContent(软错误-3/-7容忍)
    LoadPage --> WaitDelay: 1s+delay对齐Legado onPageFinished
    WaitDelay --> EvalScript: 可选window.result注入+async IIFE包裹
    EvalScript --> RetryLoop: 空结果/JS挑战页→最多重试30次×1s
    RetryLoop --> TimeoutFail: 空结果超时→抛错
    RetryLoop --> PersistCookies: 成功→persistWebViewCookies+flushStore
    PersistCookies --> Destroy: finally销毁
    TimeoutFail --> Destroy
    LoadPage --> OverrideResolve: overrideUrlRegex 导航匹配即resolve
    OverrideResolve --> Destroy
    Destroy --> [*]
```

验证/登录会话由 `sourceVerification.ts` 管理，`activeWindows` 记录 browser/captcha 两类，每源判定 `hasActiveVerification` 联动搜索超时延展；搜索取消时 `dismissAllActiveVerifications()` 一并关弹窗（`sourceVerification.ts:80-86,269+,275+`）。

---

## 六、AI 功能状态机

### 6.1 向量索引构建

阶段类型 `chunking`/`embedding`/`indexing`（`buildBookVectorIndex.ts:10`）。

```mermaid
stateDiagram-v2
    [*] --> 未索引: indexHasBook=false
    未索引 --> 校验失败: 内置模型未下载/未配置
    未索引 --> 分段: 校验通过→clearError→onPhase(chunking)
    校验失败 --> [*]: setPhaseError
    分段 --> 嵌入中: onPhase(embedding), 分批embed+进度回调
    嵌入中 --> 写入: onPhase(indexing)
    写入 --> 就绪: indexReplaceChunks ok→setPhaseIdle
    写入 --> 错误: !ok→setPhaseError
    分段 --> 中断: abortAsConfigured→setPhaseIdle
    嵌入中 --> 中断
    就绪 --> 失效重建: 维度/配置变更→resetEmbeddingDimension→dropVecTables
    失效重建 --> 分段
```

主进程嵌入子状态：`ensureBuiltinModelReady` → `MODEL_NOT_CONFIGURED/MODEL_NOT_DOWNLOADED/loadBuiltinEmbeddingModel`（`embedding/index.ts:19-27`）；worker 发 `load:progress/done/error`、`embed:progress/done/error`、`embed:abort`（`worker.ts:73-122`）。维度变化在 `vectorDb.ts:160-178` 触发 `dropVecTables+createVecTables`。

### 6.2 Agent 对话流

主循环 `runAgentChat`（`agentChat.ts:1266-1687`），流式解析 `chat.ts:389-523`。

```mermaid
stateDiagram-v2
    [*] --> 提问: runAgentChat 校验payload+装配system prompt
    提问 --> 流式回合: streamOneRound(round<maxRounds)
    流式回合 --> 流式回复: content_delta/reasoning_delta
    流式回合 --> 工具调用: 收到tool_calls
    流式回合 --> 完成: 无tool_calls→落库→emit done
    流式回合 --> 异常: EMPTY_STREAM/HTTP错误
    工具调用 --> 工具执行中: dispatchTool(ragSearch/ragContext/mindmap/wordcloud…)
    工具执行中 --> 工具结果: tool_executing/tool_progress/tool_result
    工具结果 --> 流式回合: round_end→continue
    工具结果 --> 强制收尾: 相同工具指纹连续≥3轮→pendingFinalizeNudge
    流式回复 --> 完成
    提问 --> 中断: AbortError→done
    异常 --> [*]
    完成 --> [*]
```

关键点：工具死循环防护（同参数指纹连续 3 轮判定错误，`agentChat.ts:1491-1508`）；`ragContext` 超 1 万字触发压缩摘要 `compressChapterToDigest`；abort 在 `chat.ts:515-518` 被归为 `done`。渲染事件 `ai:chat:chunk / done / error` 驱动 UI 状态（思考块 `sealed`、工具 `running|done|error`，`aiAssistantTypes.ts:22-50`）。

### 6.3 文生图/角色卡生成

```mermaid
stateDiagram-v2
    [*] --> 校验: 角色名/bookHash/embeddingEnabled
    校验 --> 别名发现: mergedRagHitsForPortrait
    别名发现 --> RAG检索: portraitSearchQueries 多查询
    RAG检索 --> 无结果错误: 防剧透全过滤/无命中
    RAG检索 --> LLM生成: callPortraitLlm
    LLM生成 --> JSON解析: parse成功
    LLM生成 --> 修复重试: parse失败→再对话修复JSON→再失败回退默认
    JSON解析 --> 别名回填: resolvePortraitAliases
    别名回填 --> [*]
    无结果错误 --> [*]

    [*] --> 启生成: runTxt2ImgToAbsolutePath
    启生成 --> 中止旧会话: portraitTxt2ImgSessionAc.abort
    中止旧会话 --> 提示词译英: adaptive prompt(失败同样修复重试)
    提示词译英 --> 调后端: fetchTxt2ImgImageBuffer(a1111/comfy/openai/wanx/minimax/stability…)
    调后端 --> 保存PNG: mkdir+writeFile→ok
    调后端 --> 失败: ok:false,error
    保存PNG --> [*]
```

单例会话 + 中止：`portraitTxt2ImgSessionAc` 单例在每次开始生成前 abort 旧会话（`registerAiIpc.ts:107-108,1541-1544`），并有独立 `:abort` 通道（`registerAiIpc.ts:1597-1600`）。

### 6.4 AI 智能排版 Diff 预览

```mermaid
stateDiagram-v2
    [*] --> 空闲: running=false, reviewOpen=false
    空闲 --> 校验: runSmartFormat
    校验 --> 空闲: 未启用/未配置模型→toast/alert返回
    校验 --> 切分规划: planFullTextSegments/planSelectionSegments
    切分规划 --> 运行中: running=true, progressOpen=true
    运行中 --> 运行中: 逐段 cleanup→校验写回
    运行中 --> 中断: stopSmartFormat→abort
    运行中 --> 无变更: applied=0且无变更→toast
    运行中 --> Diff预览: finishWithProposedReview→openReview
    Diff预览 --> 应用: applySmartFormatReview→写回主文档
    Diff预览 --> 放弃: discardSmartFormatReview(带确认)
    应用 --> [*]
    放弃 --> [*]
    中断 --> Diff预览: 已有部分结果→stopped:true 部分预览
    中断 --> [*]
```

Diff 会话结构 `{startLine,endLine,originalText,proposedText,scope}`（`aiSmartFormatReviewTypes.ts:3-11`），左原文只读、右提议可编辑（`useReaderSmartFormatDiff.ts:100-114`）。底层清理服务 `textFormatCleanup.ts:212-311` 拆分子任务（硬换行/标点/引号/去广告/去水印/乱码/屏蔽还原），无 LLM 子任务时直接返回原文。

---

## 七、跨状态机设计共性

1. **主进程持会话、渲染层持代际号**：搜索 `searchSeq`、下载 `sessionGen`、章节 `loadSeq`、语音 `playbackLoopGen`、流式 `activeStreamRequestId` 同一模式——每次新操作自增代际，回调先校验代际/会话 id，迟到事件静默丢弃（`useBookSource.ts`、`useAppVoiceRead.ts`）。
2. **取消 = 标志位 + 循环边界检查，而非中断线程**：`cancelled` 只在循环头检查；搜索取消仍发一次 `done{cancelled:true}`（`searchService.ts:272-280`），下载发 `error`（`downloadService.ts:176-183`），会话由 `finally` 统一清理。
3. **失败不重试、只降级**：网络请求层无自动重试；搜索单源失败发 `sourceDone{failed}` 继续，下载单章失败占位。唯一例外是后台 WebView（30×1s）与 TTS 合成（3~5 次退避），专治 JS 挑战页与 429。
4. **缓存是"读-回写-再回写"闭环**：章节缓存既服务阅读又服务整书下载；`<js>` 动态规则跳缓存保新鲜，下载导出只读缓存、保证导出即缓存原文。
5. **状态集中持有于渲染进程，主进程提供无状态服务**：TTS、词典、RAG、书源引擎主进程均为"请求-响应"，会话状态（含 UI 状态）归渲染层 `useApp*` composables 管理，符合 Electron 安全模型（渲染层无 Node 直访）。

---

## 附：证据索引

| 状态机 | 关键文件（相对 `src/`） |
| --- | --- |
| 窗口生命周期 | `main/index.ts`、`main/windowFactory.ts`、`main/windowCloseGuard.ts`、`main/openTxtInMainWindow.ts` |
| 阅读会话 | `renderer/src/composables/useAppFileSession.ts`、`useTxtStreamPipeline.ts`、`useAppPersistence.ts` |
| 语音朗读 | `renderer/src/composables/useAppVoiceRead.ts`、`renderer/src/services/voiceRead/voiceReadLinePlayer.ts`、`main/voiceRead/*`、`main/registerVoiceReadIpc.ts` |
| 书源找书 | `main/bookSource/searchService.ts`、`downloadService.ts`、`engine/getChapterContentWithCache.ts`、`engine/chapterCache.ts`、`engine/backstageWebView.ts`、`engine/sourceVerification.ts`、`renderer/src/bookSource/*` |
| AI | `main/ai/chat/agentChat.ts`、`chat.ts`、`ai/rag/*`、`ai/tools/characterPortrait.ts`、`ai/txt2img/index.ts`、`renderer/src/ai/buildBookVectorIndex.ts`、`renderer/src/composables/useAiSmartFormat.ts`、`useReaderSmartFormatDiff.ts` |