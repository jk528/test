# ColorTxt 交互方法论补全：事件路由 / 错误态 / 多窗口并发

> 本文补全三份交互文档（界面功能、快捷键、鼠标）共同的三个方法论漏洞：
> 1. **缺跨输入设备的事件路由总顺序**——键盘、鼠标、系统键、弹层、Monaco 默认行为同时存在时"谁先消费谁"；
> 2. **只盘点正常路径**——异常/错误态下用户能看到什么、能点什么；
> 3. **没把多窗口并发作为维度**——多个窗口并存时状态归属与广播边界。
>
> 全部结论附源码证据（文件:行号）。源码根目录：`.temp/ColorTxt` ｜ 2026-09-22

---

# 第一部分：跨输入设备事件路由总顺序

## 1.1 一个输入事件经过的 6 层（自上而下）

```
┌─ L0 主进程 before-input-event（Electron，最早，窗口内任何 JS 之前）
│   windowFactory.ts:161-174
│   · 只拦 F12 / Ctrl+Shift+I（打包后连 DevTools 也不开）
│   · 注释明确：全屏 ESC 故意不拦——必须让它到渲染层，模态框要先于"退出全屏"响应
│
├─ L1 OS 全局快捷键（失焦也触发；摸鱼会话期间/隐身键）
│   globalShortcut.ts、stealthReader.ts:319-342
│   · 与窗口事件不在同一通道，不存在冒泡竞争；注册失败的键静默失效
│
├─ L2 document/window 捕获阶段（按"监听器注册先后"执行，先注册先收）
│   ① modalStack 的 Esc 监听（仅栈非空时存在）…… utils/modalStack.ts:114-132
│        document keydown capture，动态挂载/卸载
│   ② shortcutService 动作分发 …… shortcutService.ts:317（window keydown capture）
│        内含：录制拦截 > dismissible 计数闸 > 朗读重映射 > 空格翻页 > 绑定表 > 三道闸
│   ③ 阅读器鼠标捕获 …… ReaderMain.vue:4826/4900（pointerdown/mousedown/wheel capture）
│   ④ 锚定菜单 outside 判定 …… useAnchoredAppShellMenu.ts:188（pointerdown capture）
│   ⑤ 摸鱼窗手势 …… StealthReaderApp.vue:791（div 原生监听，非 window 级）
│
├─ L3 两套"覆盖层状态"（被 L2 各处查询，本身不消费事件）
│   · modalStack：结构化栈（z-index 6000 起，每层 +10），有 close/escClosable 语义
│   · dismissibleOverlayDepth：简单整数计数（菜单/下拉打开 +1）
│
├─ L4 Vue/DOM 目标冒泡层（@click、@contextmenu、AppModal 遮罩 click.self）
│
└─ L5 承载元素默认行为（Monaco 编辑器内部处理 / Chromium 原生菜单 / 文本选择）
```

## 1.2 L2 内部的执行顺序为什么是"注册顺序"，实际谁先谁后

同一元素（window/document）同一阶段（capture）的多个监听器，**按 addEventListener 顺序执行**，任一调用 `stopImmediatePropagation` 则其后同层监听全部收不到。ColorTxt 的实际注册时机：

| 监听器 | 注册时机 | 先于/后于 |
|--------|---------|----------|
| modalStack Esc | 第一个模态/灯箱打开时才挂（modalStack.ts:130-134），全空时卸载 | 挂 **document** capture：捕获方向 window→document，故晚于同链 window 上的 shortcutService；但 shortcutService 无 Esc 绑定直接放行，两者不竞争 |
| shortcutService | 各窗挂载时 bindAppShortcuts，立即挂 window capture | 常驻 |
| 阅读器鼠标 | ReaderMain onMounted，挂在编辑器宿主 | 只影响鼠标，且在编辑器内部监听之前截获 |
| 锚定菜单 outside | 菜单打开期间挂 document pointerdown capture（:188） | 打开才存在 |

### 1.3 document 与 window 的捕获先后（容易搞错的一点）

捕获阶段传播方向是 **window → document → … → target**。所以同一个 Esc：
1. 先经过 **window capture** 上的两个监听（按注册顺序）：shortcutService 无 Esc 绑定直接放行；useAppReaderChrome 的全屏退出链虽也在此层，但执行到 `hasModalOrEscBeforeModalLayer()`（useAppReaderChrome.ts:802）查到有模态/灯箱就主动 return 让路；
2. 再到挂在 **document capture** 的 modalStack 监听——灯箱（escBeforeModalCloseStack）优先，其次关栈顶可 Esc 关闭的模态（modalStack.ts:114-128）；实际关闭时才 preventDefault+stopPropagation，标记为 swallow 的禁关模态只挡默认不阻断（:121-127）；
3. 无模态时 Esc 才一路放行到全屏"两次确认退出"逻辑。

**结论：Esc 的优先级不是靠事件注册顺序或 stopPropagation 排定的，而是靠"每个处理函数查询全局覆盖层状态后主动退让"。这是整套路由的核心设计模式——L3 的两套状态栈才是真正的仲裁者，L2 的监听器们只是各自去查它。**

## 1.4 两套覆盖层状态的差异（并存且语义不同）

| | modalStack | dismissibleOverlayDepth |
|--|-----------|------------------------|
| 文件 | utils/modalStack.ts | utils/dismissibleOverlayStack.ts |
| 结构 | 栈：每项含 close/getEscClosable/setZIndex（:19-24） | 一个 ref 整数（:4） |
| 管谁 | AppModal 模态对话框 + 灯箱（灯箱走独立的 escBeforeModalCloseStack，:28） | 更多菜单、下拉框、颜色选择器等"点外部即关"的浮层 |
| 直接关层 | resolveEscapeOnModalStack 调栈顶 close()（:101-107） | 不关，只供查询 |
| z-index | 入栈即分配 6000+深度×10，bringToFront 重排（:42-46、172-180） | 不参与 |
| 谁查询 | Esc 链路、Alt 模式（按深度差判定 :36）、查词泡"点外部关闭"（isPointerOnAppModalAbove :196-205） | shortcutService:251（**有菜单时全部快捷键直接 return**）、全屏 chrome 浮出抑制（useAppReaderChrome.ts 多处）、点击翻页抑制 |

另有第三层浮层：选中工具条/高亮色盘（`.hlFloatRoot`），z-index 被刻意压在模态首层之下
（READER_HL_FLOAT_ROOT_Z_INDEX = 5980，modalStack.ts:11；顶栏弹出层 5995，:17）。

## 1.5 阻断原语清单（每个监听器手里的"武器"）

| 原语 | 使用者 | 效果 |
|------|--------|------|
| `stopImmediatePropagation` | 快捷键录制拦截（shortcutService.ts:246-249）、点击翻页模式右键（ReaderMain.vue:4893）、modalStack Esc 实际关闭时（:126） | 同元素后续监听也收不到 |
| `stopPropagation` | 动作执行前（shortcutService.ts:313）、灯箱背景点击 | 阻止到目标/冒泡，不影响同层前序 |
| `preventDefault`（不阻断传播） | 编辑/选择模式右键 mousedown 捕获（ReaderMain.vue:4820-4824，**故意保留 contextmenu 事件**）、拖放、摸鱼滚轮、边距槽滚轮 | 只取消默认行为 |
| 函数内"查询状态后 return"（不阻断） | 快捷键三道闸、全屏 chrome 的 hasDismissibleOverlay 判定、Esc 退出链的 modal 查询 | **最主要的协调方式** |

## 1.6 复合场景推演（验证路由图的试金石）

**场景：朗读滚动锁定中 + 全屏 + 右键打开自绘菜单 + 在菜单外按下 ↓**

1. ↓ 进 L2② shortcutService：有 dismissibleOverlay（菜单）→ :251 **直接 return**，菜单 outside 监听在 pointerdown 不管键盘——菜单保持打开，↓ 也不滚屏。✅
2. 此时按 Esc：modalStack 无模态（菜单不算模态）→ document Esc 监听放行 → useAppReaderChrome Esc 链查到 dismissible 层由菜单自行监听 Esc 关闭（useAnchoredAppShellMenu.ts:189）→ 全屏链在 :802 被 modal/前置层判断之外，菜单先关。
3. 此时在阅读区左键：L2④ 菜单 outside 捕获先关菜单 → 同一事件继续到达 L2③ 阅读器 pointerdown？
   ——pointerdown 是同一事件依次执行，outside 监听只关菜单不阻断；但点击翻页手势有专门的
   **400ms 抑制**（armClickModeOverlaySkipIfNeeded，ReaderMain.vue:3835-3855），本次松开不翻页。
   这就是"先关弹层、同一次点击不穿透为业务动作"的实现：不是靠 stopPropagation，而是靠时间窗抑制标记。

**场景：找书阅读器（AppModal 内）打开词典管理（再叠一个 AppModal）时按 Alt**
- useReaderClickModeAltHold 比较的是模态**深度差**（modalStack.ts:65 getModalStackDepth），只有"阅读器之上没有更深模态"才允许 Alt 反转——叠了词典管理后 Alt 失效。

**场景：摸鱼窗存在时按 F9**
- F9 在摸鱼会话期间被注册为 OS 全局键（L1，stealthReader.ts:33），主窗的窗口级 F9（L2）在源窗失焦时根本无焦点事件；源窗仍聚焦时两者理论上都可能触发——全局键由 OS 先派发，退出摸鱼后全局 F9 注销，窗口级 F9 恢复。**切换边界靠注册/注销时序，而非互斥标志**。

---

# 第二部分：错误态与边界交互清单

> 标注：✅已处理 ｜ ⚠️部分处理（有风险点）｜ ❌缺口

## 2.1 磁盘文件被外部程序修改 ⚠️

| 项 | 现状 | 证据 |
|----|------|------|
| 监听机制 | 主进程 fs.watch，变更推 `file:disk-changed` | ipcHandlers.ts:237-315；preload:668-678 |
| 启用条件 | 已加载完、非电子书解析中、进度已同步、**编辑态强制关闭** | useAppSyncCurrentFileWatch.ts:49-59 |
| 用户表现 | **无确认弹窗**：防抖 380ms 后静默重新打开文件并恢复到对应物理行（:95-117） | 同上 |
| 风险点 1 | 阅读态静默重载会打断：正在朗读？选中工具条？右键菜单？——重载换模型后选区/工具条状态无专门迁移 | 代码中重载前仅检查 loading/编辑态，不检查语音/弹层 |
| 风险点 2 | 编辑态不监听 → 用户编辑时外部改动被完全忽略；保存时**直接覆盖**外部版本（file:writeTextFile 无 mtime 比对），外部改动静默丢失 | useAppSyncCurrentFileWatch.ts:15 注释自述"避免冲突"，实际是单向保护编辑内容 |
| watcher 可靠性 | 发送前检查 sender.isDestroyed()（ipcHandlers.ts:271、280）；窗口销毁时清理 watcher | ✅ |

## 2.2 找书下载 / 离线缓存失败 ⚠️

| 项 | 现状 | 证据 |
|----|------|------|
| 单章失败 | try/catch 吞掉，**不中断整书**，原因写 logs（downloadService.ts:161-165） | ✅不崩 |
| TXT 导出 | 失败章写死占位文本 `　　[下载失败: 章节未缓存]`（:213） | 文件表面"完整"，失败内嵌在正文 |
| 完成判定 | 全部循环走完即发 done，**不统计/不阻断失败章**；用户看到"下载完成"但 TXT 内含占位 | ⚠️ 与此前离线缓存问题分析一致 |
| 用户取消 | session.cancelled → 发 error 事件，文案"已停止下载/已停止离线缓存"（:176-183） | ✅ |
| 空内容 | body 为空 → error"没有可保存的内容"（:218-220） | ✅ |
| 失败后补救 | 无"只重试失败章"按钮；重新点下载会复用已有缓存（缺章重拉），是唯一补救路径 | ⚠️ |

## 2.3 网络超时矩阵 ✅/⚠️

| 操作 | 超时 | 证据 | 取消方式 |
|------|------|------|---------|
| 书源搜索（单源） | 30s | searchService.ts:23 | `bookSource:searchCancel`；并发池 4 |
| 书源校验（普通） | 截止时间动态延长 | searchService.ts:34-41 | 校验面板停止 |
| 书源校验（整体） | 180s | checkSourceService.ts:72 | — |
| fetchUrl 通用 | 30s + AbortController 按 requestId 管理 | registerBookSourceIpc.ts:148-157、:88 | 按 id abort |
| 后台 WebView 取页 | 默认 60s | backstageWebView.ts:225 | — |
| URL 分析 | 15s | analyzeUrl.ts:954 | — |
| AI 请求 | AbortSignal.timeout(20s) 等，各通道独立 abort（chat/text-format/wordcloud/embedding/portrait 共 6 个 abort 通道） | registerAiIpc.ts:825、908、707、551、1445 | ✅ 取消体系完整 |

超时后 UI：搜索失败源不进结果列表（无"超时源"单列标记，仅在全部失败时提示）；⚠️ 用户无法区分"该书源无结果"与"该书源超时"。

## 2.4 保存失败（本地文件） ✅

- 写入返回 `{ok:false}` → `appAlert(message ?? "保存失败")` 弹窗（App.vue:2505；另存路径 :1045）。
- **内容保留**：失败后不切换出编辑态、不清空 Monaco 模型，用户可改后重试（alert 是异步确认，编辑器状态不动）。✅
- 主进程写盘为 iconv.encode 后直接 fs.writeFile，覆盖写（无写临时文件+rename 的原子写）。⚠️ 写到一半进程崩溃会留半截文件。

## 2.5 找书阅读器章节加载失败 ⚠️

- 阅读区错误态模板：显示错误主句 + 日志块（FindBookReaderPanel.vue:2448-2457）；目录加载失败显示"目录加载失败：{{error}}"（:1078）。
- **没有"点击重试"按钮**：唯一恢复方式是切到别的章再切回（重新走 getChapterContent 缓存优先链）。
- 网络书源导入有自动重试（useBookSource.ts:95-127：间隔重试 + "获取失败，正在重试 n/N"进度文案，入参无效不重试），但阅读章节拉取不走这套。⚠️ 两处重试策略不一致。

## 2.6 AI 流式中断 ✅

- 每个长任务（对话/排版/词云/嵌入/立绘）都有 requestId + 独立 AbortController 与 abort IPC；abort 后统一回 `{ok:false, error:"已停止/已中止", aborted:true}`（registerAiIpc.ts:688-689、1574-1578）。
- 退出应用：before-quit 只显式释放本地嵌入后端（:525-527）；进行中的云端流式请求靠进程终止回收。
- ⚠️ 未发现"发起 AI 的窗口关闭时主动 abort 该窗流式请求"的统一清理：窗口销毁后主进程推送 chunk 会撞到 isDestroyed 检查（各推送点有防护），请求本身可能继续跑到结束才丢弃——浪费 token/算力但不崩溃。

## 2.7 TTS 朗读与窗口生命周期 ⚠️

- 渲染层有 voiceRead:cancelSynthesis 通道；快捷键停止/切章会调。
- 全项目未发现"窗口 closed → 取消该窗在途合成"的主进程挂钩（grep 无 cancel 与 closed 的联动）。⚠️ 关窗后短时间可能仍有音频播放至当前句结束。

## 2.8 封面 / 图片加载失败 ✅

- 书架封面：硬失败后默认封面兜底，并暴露手动 retryCover（useBookshelfCoverUrls.ts:49、267-288）。
- 本地图片协议：colortxt-local 路径不存在/目录穿越拒绝 → 协议返回错误，img 走 onerror（协议层有双 Map ref 与穿越防护，colortxtLocalProtocol.ts:83）。

## 2.9 关窗拦截的两窗差异 ⚠️（确认缺口）

| | 主窗 | 找书窗 |
|--|------|--------|
| 主进程拦截 | 都挂 attachWindowCloseRequestGuard（windowFactory.ts:227，对所有窗） | 同左 |
| 渲染响应 | useAppWindowBindings.ts:754 → handleWindowCloseRequest（App.vue:2778-2783）：**编辑态 dirty 时弹"修改未保存，放弃改动？"确认框**（:1062-1066），取消则不关 | FindBookWindow.vue:32-34：收到 requestClose **无条件 proceedCloseWindow()** |
| 结论 | ✅ | ❌ **找书内置阅读器里编辑章节后未保存，点关闭直接关窗，无提示**（章节编辑内容是否已即时落缓存取决于编辑保存流程，但 dirty 概念在找书窗未接线） |

app.quit() 期间用 appIsQuitting 标志绕过拦截（windowCloseGuard.ts:35），避免 macOS quit 被取消进程残留；WeakSet allowNextClose 保证只放行一次。

## 2.10 其他边界（速查）

| 边界 | 现状 |
|------|------|
| localStorage 写满 | cacheStore 等持久化点有 try/catch 包裹（appUi.ts:110 注释提及 pagehide 时不回写已清空存储）；⚠️ 配额溢出只静默不提示用户 |
| 空文件/编码失败 | streamFile 错误路径回流到渲染层打开失败提示（非白屏） |
| 关窗前刷盘 | pagehide + beforeunload 双保险 flushPersistence（useAppWindowBindings.ts:737-740，注释说明 Windows pagehide 不可靠） |
| 取色器跨屏 | 每显示器一个覆盖窗；提交/取消时 destroyEyedropperOverlays 一次性销毁全部（eyedropper.ts:57、358）✅ |
| 电源/休眠 | 全项目无 powerMonitor ❌：番茄钟按真实时间差计时会"跳秒"、休眠后 TTS socket 可能失效 |

---

# 第三部分：多窗口并发维度

## 3.1 窗口台账（多开策略）

| 窗口 | 能否多开 | 复用/单例逻辑 | 证据 |
|------|---------|--------------|------|
| 主阅读窗 | 可多开（Ctrl+Shift+N），F7 类入口复用 | focusOrOpenMainReaderWindow：有则按"最后聚焦窗 lastId"复用，无则新建 | openTxtInMainWindow.ts:50-68；windowFactory.ts:60-69 |
| 找书窗 | 可多开（Ctrl+Shift+N → window:newFindBook）；F7/主窗入口复用"当前聚焦或最后一个" | pickPreferredFindBookWindow :42-48、:70-85 |
| 摸鱼阅读窗 | **严格单例**：全局单个 session 变量，enter 时已在会话中则拒绝/替换 | stealthReader.ts:34-45、:77-95 |
| 摸鱼设置窗 | **单例**：settingsWin 存在直接 showSettingsWindow | stealthSettingsWindow.ts:16、:87-90 |
| 取色器覆盖窗 | 每显示器一个（逻辑多实例、用户感知单功能）；功能结束全销毁 | eyedropper.ts:193-211；windowFactory.ts:124-126 |
| 后台登录 WebView | 按书源登录需要创建，show:false；最后一个用户窗关闭时全部销毁 | backstageWebView.ts；windowFactory.ts:115-127 |

窗口分类不靠 instanceof，而靠统一谓词：isBackstageWebViewWindow / isEyedropperWindow / isStealthReaderWindow / isStealthSettingsWindow + findBookWindowByWindowId Map（openTxtInMainWindow.ts:9-30）。

## 3.2 单实例与外部唤起

```
第二个进程启动 → app.requestSingleInstanceLock() 失败 → 新进程退出
成功的老进程收到 second-instance（launchTxtHandlers.ts:70）
  → argv 中有 .txt → focusAndOpenTxtPath：
       有主窗：复用 lastId 主窗打开（最小化先 restore）
       无主窗：新建并带 pendingOpenTxtByWindowId（windowFactory.ts:112、:178-179）
macOS open-file（:87）：就绪后直接 focusAndOpenTxtPath；启动前路径进 macPendingTxtPaths 队列
```

## 3.3 跨窗广播清单

| 数据 | 机制 | 范围 | 证据 |
|------|------|------|------|
| 主题 | theme:set → nativeTheme + **遍历全部窗口** setBackgroundColor + send theme:sync | 所有窗（含摸鱼/取色器） | ipcHandlers.ts:836-845 |
| 快捷键/阅读设置 | localStorage 同源共享 + storage 事件 + persistedSettingsChangedEvent | 主窗 ↔ 找书窗实时热更新 | 快捷键文档 4.1；FindBookWindow.vue:31 listenPersistedSettingsSync |
| 书源数据 | 共享主进程 SQLite（book-sources.db，单例 store） | 数据层共享 | bookSourceStore.ts |
| 书源**变更通知** | ❌ **无广播**：A 找书窗增删改书源，B 找书窗已打开的面板不刷新，需重开面板重新查询 | grep 全 bookSource 模块无 sourcesChanged 广播，仅有 toast/校验事件定向 send（bookSourceToast.ts:17） |
| 下载进度 | 事件按 downloadId 定向回发起方 webContents | 仅发起窗可见 | downloadService emit |

## 3.4 摸鱼会话的并发绑定（设计最严密的一块）

Session 结构（stealthReader.ts:34-45）：overlay（摸鱼窗）+ owner（源窗）+ payload + pendingPayload + onOwnerClosed。

| 事件 | 处理 | 证据 |
|------|------|------|
| 源窗关闭 | owner.on("closed") → teardown(false)：摸鱼窗连带销毁、全局键注销、不回写进度 | :600-602、:635 |
| 摸鱼窗自己关 | overlay.on("closed") → teardown(true)：向源窗回写当前行 ownerProgress | :630-634 |
| 源窗/摸鱼窗顺序 | teardown 内 removeListener 解绑并清空 session，幂等 | :530 |
| 会话中再次 F9 进入 | isStealthModeActive 判定（:77-95），单例不允许第二个会话 |
| 热换章 | pendingPayload 暂存，摸鱼窗拉取时 apply（快捷键文档 10.4 已述） | :42 |
| 摸鱼设置窗 | 不 parent 摸鱼透明窗（Windows 会丢透明，stealthSettingsWindow.ts:13 注释）；抢焦后微移重申透明（:83-84） |

## 3.5 一键隐身的多窗策略

toggleAllWindowsVisibility（globalShortcuts.ts:47-84）：
- 遍历所有窗，排除判定谓词过滤的特殊窗，逐个快照最小化状态、setSkipTaskbar、hide；
- 恢复时普通窗 show，**摸鱼会话中的源窗用 showInactive 不抢焦点**（:74 注释）；
- hidden 是全局布尔：一次按键影响全部窗，不按"当前聚焦窗"局部隐藏。

## 3.6 关窗与退出的级联

```
用户点某窗关闭按钮
  → 主进程 close guard 拦截 → window:requestClose
       主窗：dirty 确认（2.9）；找书窗：直接放行；摸鱼/取色器：各自销毁路径不经 guard
  → proceedClose → win.close() → "closed"：
       清 4 个 ByWindowId Map（windowFactory.ts:110-114）
       统计剩余"用户窗口"（排除 4 类特殊窗）
       若为 0：销毁取色器 + 所有后台 WebView（:116-127）
最后一个用户窗关闭 → app 退出
  → before-quit：appIsQuitting=true（绕拦截）、卸载本地嵌入模型（registerAiIpc.ts:525）
  → will-quit：globalShortcuts 注销（部分环境末期不可调，globalShortcuts.ts:101 注释）
```

并发缺口：⚠️ **摸鱼窗/后台 WebView 不计入"用户窗口"**，如果所有主窗/找书窗关闭而摸鱼会话还在（源窗已关其实会连带 teardown，不会残留）；但 TTS/AI 在途请求无窗口级取消钩子（见 2.6/2.7）。

## 3.7 窗口尺寸/位置持久化

- 每个窗 resize/move 节流 requestSaveWindowBounds，close 时再强制存一次（windowFactory.ts:218-226）；
- 摸鱼窗独立持久化 bounds（persistBoundsNow），多显示器位置由 clampBoundsToDisplay 钳制（stealthReader.ts:595-597）；
- ⚠️ 未监听 display-added/removed/metrics-changed（已验证）：窗口在已拔出的显示器坐标上、取色器对新插入显示器不可用（要重新唤起取色器才建窗）。

## 3.8 多窗口并发风险登记

| # | 风险 | 严重度 | 位置 |
|---|------|--------|------|
| C1 | 书源多窗编辑无变更广播，B 窗面板状态过期（重复编辑/启用态不一致） | 中 | bookSource 模块无广播 |
| C2 | 找书窗关窗无 dirty 拦截 | 中 | FindBookWindow.vue:21-23 |
| C3 | 窗口关闭不取消该窗 AI/TTS 在途任务（继续耗资源/短暂有声） | 低 | registerAiIpc / voiceRead 无 closed 钩子 |
| C4 | 显示器热插拔不响应 | 低 | 无 screen 事件监听 |
| C5 | 编辑态外部改文件后保存互相覆盖（无 mtime 冲突检测） | 中 | useAppSyncCurrentFileWatch + writeTextFile |
| C6 | 下载"成功"提示不反映失败章数 | 中 | downloadService.ts:186-193 |
| C7 | 全局键靠注册/注销时序切换（F9 双重身份），注册失败仅 warn 用户无感知 | 低 | stealthReader.ts:319-342 |

---

# 第四部分：对三份既有文档的修订指引

| 既有文档 | 应补充的要点 |
|---------|-------------|
| 快捷键分析 | L0 主进程 before-input-event 是比所有渲染层更早的一层（F12 拦截、全屏 ESC 故意放行，windowFactory.ts:161-174）；Esc 的优先级靠处理函数查询 modalStack 主动退让，而非事件注册顺序 |
| 鼠标分析 | 点击翻页的"点外关菜单不穿透"靠 400ms 抑制标记而非 stopPropagation（ReaderMain.vue:3835-3855）；右键 mousedown 只截断不 preventDefault 的原因（ReaderMain.vue:4820-4824） |
| 界面交互分析 | 错误态用户触点（2.x 全部）；窗口复用 lastId 策略；书源 SQLite 共享但无广播；最后用户窗关闭的资源销毁级联 |

---

*基于源码静态分析，行号随版本可能变动；C1-C7 为经代码证据确认的并发/错误态缺口，建议按严重度排期，其中 C2/C5/C6 可在不改动架构的前提下最小修复。*
