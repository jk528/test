# ColorTxt 鼠标交互逻辑分析（左键 / 中键 / 右键 × 各窗口）

> 与《快捷键管理逻辑分析》同构，本文盘点**鼠标三键 + 滚轮 + 拖放**在每个窗口的具体表现、状态限定与程序插口。
>
> 核心结论先行：
> - **主窗口 / 找书窗是系统原生边框窗**（windowFactory.ts:82-96 未设 `frame:false`），标题栏拖动、最小化/最大化/关闭按钮、窗口边缘缩放全部由 **OS 负责**，应用内不处理（全项目无一处 `-webkit-app-region`）。
> - **摸鱼窗、取色器是无边框窗**（`frame:false`），拖动/缩放/关闭全部由应用自己实现，是鼠标逻辑最重的两个窗口。
> - 鼠标语义最复杂的是**阅读器**：左键/右键的含义随「点击翻页模式 / 文字选择模式 / 编辑模式 / 朗读态 / Alt 按住」五重状态变化；且左键"点击"与"按住拖拽"是同一手势的两种结果。
> - **中键全项目无任何自定义处理**，走 Monaco/浏览器默认行为。
>
> 源码根目录：`.temp/ColorTxt` ｜ 分析日期：2026-09-22

---

## 一、鼠标交互体系总览

### 1.1 窗口形态决定鼠标分工

| 窗口 | 边框 | 标题栏拖动/缩放 | 应用自绘缩放 | 证据 |
|------|------|----------------|-------------|------|
| 主窗口 | 原生 frame | OS 负责 | 无（仅侧栏分隔条拖拽调宽） | windowFactory.ts:82-98 `setMenuBarVisibility(false)+removeMenu()` |
| 找书窗 | 原生 frame | OS 负责 | 无 | 同一工厂（openFindBook 分支仅换图标/标题，:72-78） |
| 摸鱼阅读窗 | **frame:false + transparent** | 无标题栏 | **8 向边缘缩放 + 整窗拖动** | stealthReader.ts:444-452（resizable:false，缩放走 setBounds） |
| 摸鱼设置窗 | 独立小窗 | OS 标题栏 | 无 | stealthSettingsWindow.ts |
| 取色器覆盖窗 | **frame:false**、每显示器一个、全屏置顶不可移动 | — | — | eyedropper.ts:193-211（resizable:false/movable:false/alwaysOnTop） |

### 1.2 五个交互层级

| 层 | 承载者 | 典型交互 |
|----|--------|---------|
| **L1 OS 层** | 系统标题栏/窗口边缘 | 拖动窗口、最大化、关闭、原生边缘缩放 |
| **L2 应用外壳层** | App.vue / FindBookPanel | 按钮单击、侧栏分隔条拖拽、全屏边缘感应、拖放文件、列表右键菜单 |
| **L3 阅读器层** | ReaderMain.vue（主窗与找书阅读器共用同一组件） | 点击翻页手势、文字选择、自定义右键菜单、内链跳转、图片灯箱、滚轮 |
| **L4 弹层/菜单层** | AppModal / useAnchoredAppShellMenu | 遮罩单击关闭、外部点击关菜单、选中浮动工具条 |
| **L5 摸鱼/取色器特殊层** | StealthReaderApp / eyedropperMain | 无边框窗自绘拖动缩放、屏幕取色 |

---

## 二、主窗口 · 阅读器（ReaderMain.vue）—— 语义最复杂

阅读器是同一个 Monaco 编辑器承载"只读阅读"和"编辑"两种模式，鼠标事件全部注册在编辑器宿主 `editorHost` 上，且多用**捕获阶段**（先于 Monaco 默认行为截获）。

### 2.1 左键（button=0）——随模式有 6 种语义

注册点：ReaderMain.vue:4826 `onReaderPointerDownCapture`（pointerdown 捕获）+ :4900-4904。

判定顺序固定（:4838-4884）：

| 优先级 | 条件 | 左键行为 | 代码 |
|-------|------|---------|------|
| ① | 点中**电子书内链**（epub 等转换产物） | 跳转内链，截获 Monaco 默认 | :4839-4846 `tryJumpEbookInternalLinkFromPoint` |
| ② | 点中**正文插图**（readerImageViewZone 内 img） | 打开图片灯箱 `imageLightboxSrc=url`，并取消选区交互 | :4847-4872 |
| ③ | **点击翻页模式**开启（且点的不是忽略目标） | 开始翻页手势 `beginClickModePointerGesture`（:4873-4883） | 见 2.2 |
| ④ | 其他（文字选择模式） | 交给 Monaco：`readerAnn.beginSelectionPointerInteraction` 开始选择（:4884），松开时弹选中工具条 | useReaderAnnotations.ts:214-223 |

补充：
- **边距槽**（水平留白 gutter 区域）左键：点击翻页模式同样进手势；非翻页模式仅 `editor.focus()`（ReaderMain.vue:3985-3998）。
- **编辑模式**下点击翻页模式不生效（见 2.5 Alt 反转的限制），左键即 Monaco 普通光标定位/选择/列选。
- 双击/三击：无自定义处理，走 Monaco 默认（选词/选段）。

### 2.2 点击翻页手势：一次"按下→移动→松开"的状态机

核心：**左键 = 下一页，右键 = 上一页；按住拖动超过阈值 = 抓取滚动（grab scroll），松开不翻页。**

```
pointerdown（beginClickModePointerGesture :3796-3829）
  · 仅接受 button 0/2；focusEditor()（把焦点从侧栏抢回，保证键盘翻页生效）
  · setPointerCapture；记录起点 startX/Y、startScrollTop
  · 挂 window 捕获 pointermove/up/cancel + blur
       ↓
pointermove（onClickModePointerMove :3754-3772）
  · 位移平方和 < 6px²（CLICK_MODE_DRAG_THRESHOLD_PX）→ 仍算"点击"
  · 超过阈值 → dragged=true，document 加 .colortxtClickModeDragging（光标变 grabbing）
              → applyClickModeGrabScroll（:3743-3752）：
                editor.setScrollTop(startScrollTop - (clientY-startY)) 即时抓屏滚动
       ↓
pointerup（endClickModePointerGesture :3731-3741）
  · dragged=true  → 不翻页，仅 scheduleReadingRulerFollowViewport（阅读尺回随）
  · 未拖动且未被抑制 → runClickModePointerAction(button===2 ? -1 : 1)（:3679）
       即 scrollByPageStep(±1) → Monaco 整屏对齐滚动（ReaderMain.vue:4165-4204）
```

**"本次松开不翻页"的抑制条件**（防误触，ReaderMain.vue:3835-3855, 3738）：
- 有 dismissible 弹层（菜单/下拉）正开着（`armClickModeOverlaySkipIfNeeded`）；
- 窗口刚失焦后 400ms 内重新点入（`CLICK_MODE_FOCUS_ACTIVATE_MS`，避免切窗回来第一次点击翻页）；
- 菜单关闭后的抑制（点窗外关菜单，同一次点击不翻页）。

### 2.3 右键（button=2）——双模式分叉

| 模式 | 右键行为 | 链路 |
|------|---------|------|
| **点击翻页模式** | 与左键同手势，但松开 = **上一页**；且 `contextmenu` 被整体拦截，**不弹任何菜单**（:4890-4895 preventDefault+stopImmediatePropagation）；边距槽同样拦截（:4000-4004） | :4827-4837 → beginClickModePointerGesture → 松开 `g.button===2?-1:1`（:3740） |
| **文字选择模式** | 弹**应用自绘右键菜单** AppContextMenu；mousedown 捕获阶段先截断（防止 Monaco 把光标移到落点清空选区），但**不 preventDefault**——保留 contextmenu 事件触发（:4820-4824 注释） | :4886-4889 mousedown 截断 → :4890-4898 contextmenu 打开 `openEditorEditContextMenu`（:4790-4811） |

**自绘右键菜单项随阅读/编辑模式变化**（editorEditContextMenuItems，ReaderMain.vue:283-374）：

| 菜单项 | 只读模式 | 编辑模式 | 点击后落点（onEditorEditContextMenuSelect :3307-3364） |
|--------|---------|---------|------------------------------------------------------|
| 复制 | ✅（需选区） | ✅ | Monaco `editor.action.clipboardCopyAction`（:3331-3335） |
| 剪切 / 粘贴 | ❌ | ✅ | cut：clipboardCutAction；**粘贴**：`pasteClipboardIntoMonacoEditor`（:3352-3359） |
| 全选 | ✅ | ✅ | `editor.action.selectAll`（:3336-3340） |
| 选中本章 | ✅（按落点行判定可用性） | ✅ | `selectCurrentChapter()`（:3341-3344） |
| 网络搜索 ▶ | ✅ 子菜单列搜索引擎 + 搜索管理 | ✅ | 选引擎：拼 URL → **`openExternal` → `shell:openExternal`**（:3314-3327）；"搜索管理"emit openWebSearchManage（:3310） |
| 编辑选中文本 | ✅（只读态局部编辑） | ❌ | `tryOpenPartialEditFromSelection()`（:3345-3349） |
| AI 智能排版：选中文本 | ❌ | ✅（AI 功能开启且非审阅态） | emit `aiSmartFormatSelection`（:3361-3363）→ `ai:text-format:cleanup` |

无选区时右键菜单的锚点行用**右键落点行**（`getTargetAtClientPoint`），取不到才退回探针行（:4795-4807）。

### 2.4 中键（button=1）与滚轮

| 操作 | 行为 | 说明 |
|------|------|------|
| 中键按下/单击 | **无自定义**，Monaco 默认（按下后移动 = 自动滚屏 autoscroll） | 全项目 grep 无 `button===1/auxclick` 处理 |
| 滚轮（普通正文区） | Monaco 原生逐行滚动；阅读尺激活时先被 `tryHandleReadingRulerWheel` 捕获改为移阅读尺 | :4911-4917 wheel 捕获（passive:false） |
| 滚轮（左右边距槽） | 委托给编辑器滚动 `delegateEditorWheelFromBrowserEvent`（:3976-3983，注释说明须先委托再 preventDefault，否则 Monaco 见 defaultPrevented 直接 return）；朗读滚动锁定时不处理 |
| 水平边距条本身 | 顶栏边距±按钮旁的窄槽 wheel 调边距（:5189-5191 模板 @wheel） |

### 2.5 Alt 按住：临时反转两种模式（不改设置）

[useReaderClickModeAltHold.ts](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/阅读器项目/彩读分析/.temp/ColorTxt/src/renderer/src/composables/useReaderClickModeAltHold.ts)：

- 只读态按住 Alt：点击翻页 ↔ 文字选择**临时互换**（:52-57 `effectiveClickMode`）；
- **编辑模式不反转**（:53，编辑时左键永远是光标选择）；
- 左键已按下后才按 Alt：本轮不切（:47-48，保证可选模式下仍能做 Monaco 列选）；
- 阻断条件：更深模态打开、阅读器未展示（找书阅读器是 AppModal，只比较模态深度差，:36 注释）、焦点在外部输入框（:23-31）。

### 2.6 选中浮动工具条（左键选择后的二级交互）

触发链：选择模式 pointerdown → `beginSelectionPointerInteraction`（useReaderAnnotations.ts:214）→ 左键 pointerup（:218-222 只认 button 0）→ `finishSelectionPointerInteraction`（:188-212）：
- Monaco `getSelection()` 非空 → `showToolbarFromSelectionIfAny()` 在选区上方显示工具条；
- 无选区但点中已有标注 → `tryShowToolbarFromAnnotationPoint` 显示标注工具；
- 选区滚出视口工具条暂隐（toolbarScrollHidden，滚回恢复，:174-175）。

工具条按钮（5 项可在 设置→阅读 中开关，constants/selectionToolbar.ts:28-35 默认全开）：

| 按钮 | 单击行为 → 插口 |
|------|----------------|
| 复制 | 渲染层剪贴板（Monaco clipboardCopy） |
| 查找 | 按设置开 Monaco 查找栏 或 填入侧栏全文搜索（findTarget，:17-23） |
| 问 AI | emit askAiWithQuote → AI 面板（`ai:chat:*`，见交互文档 11.3） |
| 词典 | 弹词典泡 → `dictionary:lookup` |
| 翻译 | 弹翻译泡 → `translate:translate` |

### 2.7 图片灯箱（ReaderImageLightbox.vue）

- 打开：正文插图左键单击（2.1 优先级②）；
- 关闭：灯箱背景单击 `@click="src = ''"`（ReaderImageLightbox.vue:37）；
- 图片 URL 经 `colortxtLocal:registerPath` 安全协议加载。

---

## 三、主窗口 · 外壳与侧栏

### 3.1 左键

| 位置 | 交互 | 绑定/函数（行号） | 落点 |
|------|------|------------------|------|
| 顶栏/底栏所有按钮 | 单击触发（打开文件、字号±、更多菜单等） | AppHeader.vue、App.vue:3818-3873 | 见《界面功能交互分析》第十章；更多菜单为锚定浮层 |
| 更多菜单（⋯） | 单击切换；菜单打开后**点外部任意处关闭** | useAnchoredAppShellMenu.ts:188 document **pointerdown 捕获**判定 outside（:155-156 排除浮层自身/自定义下拉），另支持 Esc、window resize 关闭（:189-190） | 渲染层 |
| 侧栏·文件行 | 单击打开文件（单击切行；编辑清单模式下 checkbox 多选，支持 Ctrl/Shift） | FileListPanel.vue:1553-1557 `onFileItemClick`（:579/:591） | 打开走 `file:stream` |
| 侧栏·文件夹 | 单击展开/折叠 | FileListPanel.vue:1431 `onTreeFolderClick` | 渲染层 |
| 侧栏·章节行 | 单击跳转 | ReaderSidebar `@jump-to-chapter`（:1190-1239）→ useAppChapterNavigation | Monaco 滚动 |
| 侧栏·书签行 | 单击跳转（朗读时联动朗读） | BookmarkListPanel | Monaco 滚动 |
| 侧栏·标注行 | 单击跳转 | AnnotationListPanel | Monaco 滚动 |
| 侧栏·搜索结果 | 单击跳转 | ReaderSidebarSearch | Monaco reveal |
| 底栏章节导航条 | 上一章/下一章按钮 | ReaderChapterNavBar.vue:27-63 @click prev/next | 切章链 |
| 侧栏分隔条（resize handle） | **左键按住拖动调侧栏宽** | 模板 @mousedown（App.vue:4043、:4052 普通/全屏各一条）→ startResizeSidebar（useAppReaderChrome.ts:289-293）只置 `resizingSidebar=true` → 真正跟手在 window **mousemove**（useAppWindowBindings.ts:682-696）钳 min/max 宽；全屏时写 fullscreenSidebarWidth | 渲染层（宽度 localStorage 持久化） |

### 3.2 右键（侧栏右键菜单全部为应用自绘）

| 位置 | 绑定 | 菜单项去向（对应插口见交互文档第十章侧栏表） |
|------|------|---------------------------------------------|
| 文件行 | FileListPanel.vue:1558 `onFileItemContextMenu`（:860 → menus.onFileItemContextMenu :862） | 在新窗口打开（`window:new`）、资源管理器显示（`shell:showItemInFolder`）、重命名（`fs:renamePath`）、替换文件、移除、清除阅读数据、归类等 |
| 目录树文件行 | :1470 同一处理器 | 同上 |
| 文件夹 | :1432 `onFolderContextMenu`（:1041） | 目录相关操作 |
| 书签行 | BookmarkListPanel.vue:169 `onItemContextMenu(line)` | 编辑/删除书签 |
| 标注行 | AnnotationListPanel.vue:197 `onItemContextMenu(id)` | 删除标注等 |
| 章节列表 | **无右键菜单**（只有顶部 ⋯ 锚定菜单） | — |

### 3.3 拖放文件进窗口（HTML5 DnD）

注册于 useAppWindowBindings.ts:661-680（window 捕获 dragover/dragenter/dragleave + document drop）：

```
拖入外部文件（dataTransferLikelyHasExternalFiles 判定）
  dragover/dragenter → preventDefault（允许 drop）+ dropEffect="copy" + 显示/定位"打开阅读区"拖放蒙层
  drop（:650-659）→ collectFsPathsFromDataTransfer 取路径
     → openFirstSupportedTopLevelPath(paths) 打开第一个受支持文件
拖到侧栏区域 → isOverSidebarImportDropZone：加入文件列表而非直接打开（useAppWindowBindings.ts:29-31）
```

### 3.4 全屏 / 极简模式的鼠标边缘感应

window mousemove（useAppWindowBindings.ts:697-705）统一调度：

| 行为 | 机制 |
|------|------|
| 顶部/底部/左缘悬停浮出顶栏/底栏/侧栏 | updateFullscreenHeaderHover / FooterHover / SidebarHover；三层互斥（canShowFullscreenPanel useAppReaderChrome.ts:299-310，另两层显示时本层不弹） |
| 停止移动后隐藏 chrome 与光标 | `bumpFullscreenCursorIdle` 重置空闲计时（:703-705）；`recordFullscreenPointer` 记录指针位置（:700-702） |
| 按住指针拖入边缘不唤起浮层 | pointerButtonsHeld（:313-315）；离开感应区前抑制（suppressChromeEdgeRevealUntilPointerLeaves :321） |
| 快捷键唤出的浮动侧栏 | 指针进入前不因 mouseout 收起（stickyFullscreenSidebar… :327） |
| IME 候选窗干扰 | 监听 compositionstart/end（:332-338），避免原生候选窗造成的 relatedTarget=null 误收起 |

### 3.5 弹层与模态的鼠标规则

- **AppModal 遮罩**：`@click.self="onMaskClick"`（AppModal.vue:180）——点遮罩本身关闭，点内容区 `@click.stop`（:198）不关闭；右上角关闭钮 :237。
- **锚定菜单/下拉**：统一 useAnchoredAppShellMenu，pointerdown 捕获 outside 即关（3.1）。
- **输入框右键菜单（主进程注入，非渲染层）**：原生 `<input>/<textarea>` 右键时主进程弹系统菜单：撤销/重做/剪切/复制/粘贴/删除/全选——editableContextMenu.ts:23-45，按 `editFlags` 控制可用性；**Monaco contenteditable 被明确排除**（:3 注释、:26 isNativeTextFormControl 白名单），它走 2.3 的自绘菜单。

---

## 四、找书窗口

### 4.1 顶栏 / 菜单 / 滚动

| 交互 | 行为 | 证据 |
|------|------|------|
| 更多（⋯）左键 | 锚定菜单（同 useAnchoredAppShellMenu，点外部关闭） | FindBookPanel.vue:1468-1471、:415-440 |
| 返回/搜索/各图标 | 左键单击切换面板/状态 | 同文件 |
| 搜索结果列表滚动 | 触底距底 ≤48px 自动 loadMore | FindBookPanel.vue:636-641（VirtualList） |
| 结果卡片左键 | 单击打开书籍详情弹窗 `onOpenBook`（:851-853、模板 :2034） | 渲染层 |
| 卡片内作者/来源链接 | 左键：以作者名/该书源发起新搜索 | FindBookPanel 模板内 |
| 搜索历史标签 | 左键填入关键词搜索；清空按钮单独 | 渲染层 |

### 4.2 书架（FindBookshelfPanel + ListItem）

| 交互 | 行为 | 证据 |
|------|------|------|
| 普通模式·卡片左键 | **单击直接开始阅读**（非双击） | FindBookshelfPanel.vue:419-423 `emit("readBook")` |
| 管理模式·左键 | 单选 | :464-466 |
| 管理模式·Ctrl/Cmd+左键 | 多选切换 | :454-462 |
| 管理模式·Shift+左键 | 从锚点连选（与资源管理器一致） | :429-452 |
| 卡片 ⋯ 左键 | 行菜单（更新/分类/删除/导出缓存等） | onRowMoreClick :469-473 |
| 拖拽排序 | **SortableJS**：手柄 `.sortableRowHandle` 拖动（ListItem 引用 SORTABLE_ROW_HANDLE_CLASS）→ onReorder → reorderBookshelfManualOrders | useSortableReorder.ts:52-70；FindBookshelfPanel.vue:287-297；落点 localStorage |
| 分类标签/排序栏 | 左键筛选排序 | 渲染层 |

### 4.3 书源管理（BookSourcePanel）

| 交互 | 行为 | 插口 |
|------|------|------|
| 书源行左键 | 展开/进入编辑（EditBookSourcePanel） | 渲染层 |
| 启用复选框 | 切换启用 | `bookSourceToggle` → `bookSource:toggle` |
| 行手柄拖拽排序 | SortableJS（li，仅"手动排序"模式生效 canDragReorder :230）→ 重算 customOrder → applySourceCustomOrders | **`bookSource:applyCustomOrders`**（:232-249） |
| 删除/新建/导入/校验 | 左键按钮 | 对应 `bookSource:delete/save/importPreview/importCommit/checkStart` |
| 拖文件导入 | 文件选择对话框为主（本地导入按钮） | `bookSource:readFile` |

### 4.4 替换规则面板

- 规则行同样用 SortableJS 手柄拖拽排序（ReplaceRulePanel.vue:315）；落点 localStorage（replaceRuleLocalStore）。

### 4.5 书籍详情弹窗（BookDetailPanel，AppModal）

| 交互 | 行为 | 证据 |
|------|------|------|
| 遮罩左键 | 关闭弹窗（AppModal click.self，3.5） | BookDetailPanel.vue:833 用 AppModal |
| 封面左键 | 打开封面大图灯箱 `openCoverLightbox` | :697、:1007 |
| 章节目录行左键 | 进入内置阅读器读该章 `onReadChapter(index)` | :1099 |
| 顶部按钮（书架/分类/阅读/下载/日志/刷新/登录） | 左键单击，详见交互文档 10.9 | 下载 → `bookSource:download` 等 |
| 章节列表右键 | 无自定义菜单 | — |

### 4.6 找书内置阅读器

**与主窗 ReaderMain 是同一组件**，第二章全部规则适用（点击翻页手势、自绘右键菜单、选中工具条、Alt 反转、图片灯箱、边距槽、阅读尺滚轮）。差异仅在数据插口：

- 右键菜单"网络搜索"仍走 `shell:openExternal`；"编辑选中文本"后保存走 **`bookSource:saveChapterCache`**（而非 file:writeTextFile）；
- 阅读器外壳按钮（头部 FindBookReaderHeader）左键单击，含主题/字号/语音/设置等；
- 章节侧栏章节行：左键切章，缓存章有标记（`bookSource:chapterCacheStatus`）；
- 阅读器是 AppModal 形态，Alt 反转按"模态深度差"判定（2.5）。

### 4.7 发现页

- 书源选择器、分类标签：左键切换；
- 书籍卡片：左键打开详情；
- 触底加载更多 → `bookSource:exploreBooks`。

---

## 五、摸鱼阅读窗（StealthReaderApp.vue）—— 自绘窗口，三键语义完全不同

窗口参数：frame:false / transparent / alwaysOnTop / resizable:false（stealthReader.ts:444-452），没有任何系统按钮。

### 5.1 左键（唯一被接受的按键，pointerdown :791 只处理 button===0）

一次按下按"是否移动、起点在哪"分三种结果：

```
pointerdown（onPointerDown :791-823）
  · ev.detail>1（多击）→ 不开始手势（:795）
  · 清选区；setPointerCapture；resizing = edgeFromTarget（8 向 data-edge 边缘热区，:753-769）
  · 异步取真实 bounds（stealthReaderGetBounds IPC）
       ↓
pointermove（onPointerMove :901-931）
  · 起点在 8 向边缘热区 → applyResize（:825 起）→ stealthReaderSetBounds（IPC，自带 8px 最小尺寸钳制）
  · 否则位移 ≥ DRAG_THRESH_PX → dragging=true → 整窗 stealthReaderSetBounds（带宽高一起 set，
    注释 :921 说明 Win11 上 setPosition 会让 HWND 尺寸漂移）
       ↓
pointerup（finishPointer :861-899）
  · 发生过 resize/drag → persistBoundsNow（bounds 持久化）+ 缩放后 scheduleRelayout
  · 未移动（=单击）→ 抑制标记检查（菜单刚关 400ms 内/点按提示层期间不翻页，:883-894）
      → 按水平位置：clientX ≥ 窗宽/2 翻下一页，否则翻上一页（:895-898）
      → requestPageFlip(±1)（:295-326，rAF 合帧、单帧最多 12 页；到边界自动 chapterPrev/Next）
```

即摸鱼窗**没有"点击翻页模式"开关**：左键永远同时承担 单击翻页（左右半屏）/ 按住拖窗 / 边缘缩放。

### 5.2 右键（button=2）

- `onContextMenu`（:702-707）：**preventDefault 后发 IPC** `stealthReaderPopupMenu` → 主进程弹**原生系统菜单**（stealthReader.ts:818 注册；菜单模板 :668-695）：
  - **定时滚动**（勾选态，命令 `toggleTimedScroll`）
  - **设置**（`openSettings` → openStealthSettingsWindow IPC）
  - **退出摸鱼模式**（`exit` → exitStealth :709-714：存设置/尺寸 → `stealthReader:exit` 回写当前行）
- 菜单弹出期间主进程推 `stealthReader:menuOpen`，渲染层设 menuOpen，并吞掉菜单关闭后 400ms 内的点击翻页（preload:611-615、StealthReaderApp:1101-1114）。
- 右键不参与翻页/拖窗。

### 5.3 中键与滚轮

- **中键：无处理。**
- **滚轮 onWheel（:942-969）按修饰键 5 种语义**（均 preventDefault）：

| 组合 | 行为 |
|------|------|
| Ctrl/Cmd+Alt+滚轮 | 行高 ±（bumpLineHeight） |
| Ctrl/Cmd+滚轮 | 字号 ±（bumpFontSize） |
| Alt+滚轮 | 窗口不透明度 ±0.05（bumpOpacity）→ stealthReaderRefreshTransparency |
| Shift+滚轮 | 字体不透明度（文字颜色深浅）±0.05（兼容 Windows 上 Shift+轮变 deltaX，:960-963） |
| 无修饰（hover 时） | 逐行滚动 requestLineScroll（:966-969） |

### 5.4 摸鱼窗的"命令注入"（与鼠标等价的第二条触发路径）

鼠标翻页/右键菜单的最终动作，与摸鱼全局快捷键（Ctrl+↑↓←→/F9）汇合到同一组函数：
主进程 `sendCommand`（stealthReader:command）→ onCommand（:716-731）pagePrev/pageNext/chapterPrev/chapterNext/exit/openSettings/toggleTimedScroll；
章边界跨界时经 `stealthReader:ownerChapterNav` ↔ `stealthReader:updatePayload` 与源窗热换章（详见快捷键文档 10.4）。

---

## 六、取色器覆盖窗（eyedropperMain.ts）

窗口：每个显示器一个 frame:false / 不可移动缩放 / 置顶全屏覆盖层（eyedropper.ts:193-211）；显示的是主进程截屏位图 + Canvas 放大镜，不接收真实桌面事件。

| 鼠标操作 | 行为 | 证据 / 插口 |
|---------|------|------------|
| 移动（mousemove） | 放大镜跟随、绘制像素、显示坐标/HEX、节流采样屏幕像素 | onMove :250-252 → updateAt :240-248 scheduleSample |
| 鼠标进入/离开 | 进入 window.focus；离开隐藏放大镜 | :335-340 |
| **左键 mousedown** | 确认取色 | onClick :254-262 → **`eyedropperSubmit(hex)`** → `eyedropper:submit`，结果回配色面板 |
| **右键/其他键 mousedown** | 取消 | :257-259 → `eyedropperCancel`；另有 contextmenu 拦截取消（:342-345） |
| 中键 | 与其他非左键同 → 取消 | :257 |
| 滚轮 | 无滚轮逻辑（键盘 C 复制、Shift 切格式、Esc 取消） | onKeyDown :264-284 |
| 跨屏 | 主进程根据 pointerPayloadForWin 把全局光标坐标推给对应覆盖窗（eyedropperOnPointer） | eyedropper.ts:93-112；渲染层 :323-325 |

---

## 七、三键 × 各窗口行为矩阵（速查）

| 窗口/区域 | 左键 | 右键 | 中键 | 滚轮 |
|-----------|------|------|------|------|
| 主/找书窗·标题栏（OS） | OS 拖动/按钮 | OS 菜单 | OS 默认 | — |
| 主/找书窗·边缘（OS） | OS 缩放 | — | — | — |
| 阅读器·点击翻页模式 | 下一页（按住拖动=抓屏滚动） | 上一页（同手势），**无菜单** | Monaco autoscroll | 滚屏/移阅读尺 |
| 阅读器·选择模式 | 定位/选择 → 工具条 | 自绘菜单（复制/搜索/编辑/AI…） | Monaco autoscroll | 同上 |
| 阅读器·编辑模式 | Monaco 光标/选择/列选（Alt 不反转） | 自绘菜单（含剪切粘贴/AI排版） | Monaco autoscroll | 同上 |
| 阅读器·内链/插图 | 跳链 / 开灯箱 | — | — | — |
| 阅读器·边距槽 | 翻页手势或聚焦 | 翻页模式时拦截 | — | 委托编辑器滚动 |
| 选中工具条 | 5 个动作按钮 | — | — | — |
| 侧栏·文件/夹/书签/标注行 | 单击打开/跳转 | 自绘上下文菜单 | — | — |
| 侧栏·分隔条 | 按住拖宽 | — | — | — |
| 任意 input/textarea | 输入 | **主进程注入**系统编辑菜单 | — | — |
| 找书·结果/卡片 | 单击详情/阅读 | 无 | — | 触底加载更多 |
| 书架·普通/管理模式 | 阅读 / 单选·Ctrl多选·Shift连选 | 行 ⋯ 菜单（左键） | — | — |
| 书架/书源/规则列表 | 手柄拖拽排序（SortableJS） | — | — | — |
| AppModal | 遮罩单击关闭 | — | — | — |
| 摸鱼窗 | 单击左右半屏翻页/按住拖窗/边缘缩放 | 原生菜单（定时滚动/设置/退出） | 无 | 5 种修饰语义 |
| 取色器 | 确认提交 hex | 取消 | 取消 | 无 |

---

## 八、程序插口与调用链汇总（鼠标相关）

### 8.1 终点是 IPC 的鼠标动作（其余全部渲染层/Monaco）

| 鼠标动作 | 调用链 | 插口 |
|---------|--------|------|
| 右键菜单→网络搜索 | ReaderMain onEditorEditContextMenuSelect:3326 | `openExternal` → **`shell:openExternal`** |
| 右键菜单→AI排版 | emit aiSmartFormatSelection | **`ai:text-format:cleanup`** |
| 侧栏文件右键→新窗口/资源管理器/重命名 | FileListPanel 菜单 → App.vue 处理 | `window:new`、`shell:showItemInFolder`、`fs:renamePath` |
| 书源行拖拽排序结束 | BookSourcePanel:247 applySourceCustomOrders | **`bookSource:applyCustomOrders`** |
| 书源启用勾选 | BookSourcePanel | `bookSource:toggle` |
| 详情弹窗各按钮 | BookDetailPanel | 见交互文档 10.9（download/getChapterContent 等） |
| 找书阅读器编辑保存 | 局部编辑保存 | `bookSource:saveChapterCache` |
| 拖放文件进窗 | useAppWindowBindings:650 → openFirstSupportedTopLevelPath | `file:stream` |
| 摸鱼左键·拖窗/缩放 | StealthReaderApp:858/929 | `stealthReader:getBounds`、`stealthReader:setBounds` |
| 摸鱼右键菜单 | :704 | `stealthReader:popupMenu`（主进程原生 Menu.popup） |
| 摸鱼菜单→设置/退出 | onCommand:722/721 | `stealthSettings:open`、`stealthReader:exit` |
| 摸鱼 Alt+轮透明度 | bumpOpacity | `stealthReader:refreshTransparency` |
| 摸鱼跨章（翻页到边界） | requestOwnerChapterNav:429 | `stealthReader:ownerChapterNav` → 源窗 → `stealthReader:updatePayload` |
| 取色左键/右键 | eyedropperMain:261/258 | `eyedropper:submit` / `eyedropper:cancel` |
| 图片显示（灯箱/封面/插图） | pathToReadableLocalUrl | `colortxtLocal:registerPath` + `colortxt-local://` 协议 |

### 8.2 终点是 Monaco API / 渲染层状态的鼠标动作（无 IPC）

| 类型 | 代表动作 | 最终 API/落点 |
|------|---------|--------------|
| 翻页/抓屏滚动 | scrollByPageStep、applyClickModeGrabScroll | editor.setScrollTop / getTopForPosition（ReaderMain.vue:3751、4165-4204） |
| 选择/光标 | beginSelectionPointerInteraction、Monaco 默认 mousedown | editor.getSelection / selectionchange |
| 复制/剪切/全选 | 右键菜单项 | editor.trigger("keyboard","editor.action.clipboard*")（:3331-3355） |
| 工具条定位 | showToolbarFromSelectionIfAny | getScrolledVisiblePosition 计算坐标 |
| 侧栏宽度 | startResizeSidebar + window mousemove | CSS 宽度 + localStorage |
| 排序（书架/规则） | SortableJS onEnd | localStorage |
| 菜单/弹窗开关 | useAnchoredAppShellMenu、AppModal | 组件 ref 状态 + modalStack |
| 全屏 chrome 感应 | updateFullscreen*Hover、bumpFullscreenCursorIdle | class 切换 + 定时器 |

---

## 九、关键文件索引

| 角色 | 文件:关键行 |
|------|------------|
| 阅读器鼠标总入口（pointerdown/mousedown/contextmenu 捕获） | `components/ReaderMain.vue:4820-4917` |
| 点击翻页手势状态机 | `components/ReaderMain.vue:3702-3855` |
| 行/页滚动（左键翻页最终落点） | `components/ReaderMain.vue:4006-4019、4165-4204` |
| 自绘右键菜单定义与选择分发 | `components/ReaderMain.vue:283-374、3307-3364、4790-4811` |
| 选中工具条触发 | `composables/useReaderAnnotations.ts:170-228` |
| 工具条按钮配置 | `constants/selectionToolbar.ts:5-35` |
| Alt 临时反转模式 | `composables/useReaderClickModeAltHold.ts:39-79` |
| 侧栏 resize / 全屏边缘感应 | `composables/useAppReaderChrome.ts:289-343`；`composables/useAppWindowBindings.ts:682-706` |
| 拖放文件 | `composables/useAppWindowBindings.ts:621-680` |
| 锚定菜单外部点击关闭 | `composables/useAnchoredAppShellMenu.ts:134-200` |
| 模态遮罩关闭 | `components/AppModal.vue:167-198` |
| 侧栏列表右键 | `components/FileListPanel.vue:860-862、1041、1558`；`BookmarkListPanel.vue:169`；`AnnotationListPanel.vue:197` |
| 输入框原生右键菜单（主进程） | `main/editableContextMenu.ts:23-45` |
| 窗口形态（原生 frame） | `main/windowFactory.ts:82-98` |
| 书架选择/拖拽 | `bookSource/components/FindBookshelfPanel.vue:287-297、418-473` |
| 通用拖拽排序（SortableJS） | `composables/useSortableReorder.ts:7-70` |
| 书源拖拽/列表 | `bookSource/components/BookSourcePanel.vue:232-249` |
| 详情弹窗 | `bookSource/components/BookDetailPanel.vue:697、1007、1099` |
| 摸鱼窗鼠标全部 | `StealthReaderApp.vue:702-707、739-969`；窗口参数 `main/stealthReader.ts:444-452、668-695` |
| 取色器鼠标 | `renderer/src/eyedropperMain.ts:250-349`；窗口参数 `main/eyedropper.ts:93-112、193-211` |

---

*基于源码静态分析，行号随版本可能变动；新增鼠标交互时注意阅读器事件多用捕获阶段且与点击模式状态机耦合，改动需同时验证"点击/拖拽/右键/弹层抑制"四条路径。*
