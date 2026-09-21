# ColorTxt 快捷键管理逻辑分析

> 核心结论先行：ColorTxt 的快捷键**大部分是通用的**（主窗口与找书窗口共用同一份绑定表、同一套持久化），但**存在 4 类限定**——
> ① 面板展示限定（主窗/找书窗各自隐藏不相关动作）；② 消费上下文限定（阅读器打开时找书面板只保留 6 个动作）；
> ③ 状态限定（编辑态让位 Monaco、朗读态封锁/重映射、弹层打开时屏蔽滚动键）；④ 另有独立的**系统级全局快捷键**（摸鱼导航 + 一键隐身），不属于窗口绑定表。
>
> 源码根目录：`.temp/ColorTxt` ｜ 分析日期：2026-09-22

---

## 一、快捷键体系四层结构

| 层级 | 生效条件 | 注册位置 | 数量 | 可在面板配置 |
|------|---------|---------|------|-------------|
| **L1 系统全局快捷键** | 应用失焦也生效（OS 级） | 主进程 `globalShortcut.register` | 6 个（1 隐身 + 4 摸鱼导航 + 1 摸鱼退出） | 隐身键在快捷键面板；摸鱼键在摸鱼设置窗 |
| **L2 应用窗口快捷键** | 窗口聚焦时，window 捕获阶段 | `bindAppShortcuts`（渲染层） | 38 个动作中的 37 个 `scope:"window"` | 是 |
| **L3 硬编码特殊键** | 视状态生效 | shortcutService.ts / useAppReaderChrome.ts | 空格翻页、朗读 空格/←/→、Esc 层级链 | 否（空格可被绑定表覆盖） |
| **L4 Monaco 原生键** | 编辑模式焦点在编辑器内 | Monaco 自带 | Ctrl+C/V/Z 等 | 否 |

三个消费点（同一函数 `bindAppShortcuts`，同一绑定表）：

| 消费点 | 文件:行号 | 动作实现方式 |
|--------|----------|-------------|
| 主窗口 | [useAppWindowBindings.ts:236](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/composables/useAppWindowBindings.ts#L236) | 37 个动作全部接到真实处理函数 |
| 找书面板（书架/搜索/发现/书源管理/设置） | [useFindBookPanelShortcuts.ts:101](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/bookSource/composables/useFindBookPanelShortcuts.ts#L101) | 只实现 6 个动作，其余为空函数 |
| 找书内置阅读器 | [useFindBookReaderShortcuts.ts:111](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/bookSource/composables/useFindBookReaderShortcuts.ts#L111) | 阅读器相关动作接到 ReaderMain，窗口动作留空 |

> 摸鱼阅读窗**不使用** L2 体系：它的翻页/切章/退出全部走 L1 系统全局快捷键（主进程直接向摸鱼窗 `sendCommand`）。

---

## 二、三处真相源（配置 / 展示 / 消费）

快捷键改动必须三处同步，否则会出现"面板不显示 / 按键无效 / 死代码"：

| 真相源 | 文件 | 内容 |
|--------|------|------|
| **① 定义源** | [shortcutRegistry.ts](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/services/shortcutRegistry.ts) | `SHORTCUT_ACTIONS`（38 个动作的 id/scope/描述）、`createDefaultShortcutBindings`（默认键位，:292-333）、主窗/找书窗面板隐藏名单（:54-68） |
| **② 展示源** | [ShortcutPanel.vue](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/components/ShortcutPanel.vue) | 快捷键面板：按 `panelContext: "main" | "findBook"` 显示不同动作集（:33-35）；录制、冲突检测、还原默认 |
| **③ 消费源** | [shortcutService.ts](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/services/shortcutService.ts) `bindAppShortcuts`（:233-319）+ 三个调用点 | keydown 捕获 → 匹配绑定 → 上下文判定 → 执行动作 |

辅助工具：[shortcutUtils.ts](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/services/shortcutUtils.ts)
- `normalizeAccelerator`（:120）统一键位写法（修饰键按 Control→Command→Alt→Shift 排序）
- `mergeShortcutBindings`（:179）默认表 + 磁盘覆盖合并
- `collectShortcutConflicts`（:194-210）检测绑定表内部重复键
- `shortcutBindingOverridesForPersist`（:166-177）**只持久化与默认不同的项**

---

## 三、完整动作 × 默认键位 × 各窗口可用性

默认键位以 Windows 为准（`accel = Control`；Mac 自动换成 Command，见 registry:288-290）。

**列含义**：主窗 = 主窗口面板是否展示/消费；找书面板 = 找书窗非阅读器态；找书阅读器 = 内置阅读器打开时。

### 3.1 文件与导航类

| 动作 id | 描述 | 默认键 | scope | 主窗 | 找书面板 | 找书阅读器 | 限定说明 |
|---------|------|--------|-------|------|---------|-----------|---------|
| openFile | 打开文件 | Ctrl+O | window | ✅实接 | ❌隐藏/空函数 | ❌空函数 | 找书窗不打开本地文件 |
| pickTxtDirectory | 选择目录 | Ctrl+Shift+O | window | ✅ | ❌ | ❌ | 同上 |
| scrollDownLine | 向下滚动（逐行） | ↓ | window | ✅ | ❌空函数 | ✅ReaderMain | 编辑态 Monaco 内让位；朗读态封锁 |
| scrollUpLine | 向上滚动（逐行） | ↑ | window | ✅ | ❌ | ✅ | 同上；查找栏聚焦时也让位 |
| scrollPageUp | 上一屏 | PageUp | window | ✅ | ❌ | ✅ | 同上 |
| scrollPageDown | 下一屏 | PageDown | window | ✅ | ❌ | ✅；**空格也翻页**（L3） | 同上 |
| jumpPrevChapter | 上一章 | Ctrl+← | window | ✅ | ❌ | ✅（含边界切章） | 朗读态封锁 |
| jumpNextChapter | 下一章 | Ctrl+→ | window | ✅ | ❌ | ✅ | 朗读态封锁 |

### 3.2 阅读排版类（仅阅读器有意义）

| 动作 id | 描述 | 默认键 | 主窗 | 找书面板 | 找书阅读器 |
|---------|------|--------|------|---------|-----------|
| decreaseFontSize / increaseFontSize | 字号 − / ＋ | Ctrl+- / Ctrl+= | ✅ | 空函数 | ✅ |
| decreaseLineHeight / increaseLineHeight | 行间距 −/＋ | Ctrl+[ / Ctrl+] | ✅ | 空函数 | ✅ |
| decreaseLetterSpacing / increaseLetterSpacing | 字间距 −/＋ | Ctrl+Shift+[ / Ctrl+Shift+] | ✅ | 空函数 | ✅ |
| decreaseParagraphSpacing / increaseParagraphSpacing | 段间距 −/＋ | Ctrl+; / Ctrl+' | ✅ | 空函数 | ✅ |
| decreaseHorizontalInset / increaseHorizontalInset | 左右边距 −/＋ | Ctrl+Shift+, / Ctrl+Shift+. | ✅ | 空函数 | ✅ |

### 3.3 查找与侧栏类

| 动作 id | 描述 | 默认键 | 主窗 | 找书面板 | 找书阅读器 | 限定 |
|---------|------|--------|------|---------|-----------|------|
| toggleFind | 查找 | Ctrl+F | ✅ Monaco 查找 | 空函数 | ✅ ReaderMain 查找小窗 | 编辑态/查找栏让位；朗读态封锁 |
| openSidebarSearch | 侧栏：搜索 | Ctrl+Shift+F | ✅ | ❌隐藏 | ❌空函数 | 主窗专属 |
| openSidebarFiles | 侧栏：文件 | Ctrl+Shift+E | ✅ | ❌隐藏 | ❌ | 主窗专属 |
| openSidebarChapters | 侧栏：章节 | Ctrl+Shift+C | ✅ | ❌隐藏 | ❌ | 主窗专属（找书阅读器章节侧栏由其内部按钮控制） |
| openSidebarAiAssistant | 侧栏：AI 助手 | Ctrl+Shift+A | ✅ | ❌隐藏 | ❌ | 主窗专属（需 AI 开关） |

### 3.4 编辑类

| 动作 id | 描述 | 默认键 | 限定 |
|---------|------|--------|------|
| toggleReaderEdit | 进入/退出编辑模式 | Ctrl+/ | 主窗与找书阅读器各自实现切换；编辑态滚屏/查找键让位 Monaco |
| editSelectedText | 编辑选中文本 | Ctrl+E | 找书阅读器调 `tryOpenPartialEditFromSelection`（局部编辑） |
| openChapterRules | 章节匹配规则 | Ctrl+R | **主窗专属**（找书窗无本地文本章节规则） |
| toggleBookmark | 添加/移除书签 | Ctrl+D | **主窗专属** |

### 3.5 外壳与窗口类（跨窗口通用）

| 动作 id | 描述 | 默认键 | 主窗 | 找书面板 | 找书阅读器 | 备注 |
|---------|------|--------|------|---------|-----------|------|
| toggleSidebar | 显示/隐藏侧栏 | Ctrl+B | ✅ | 空函数 | ✅阅读器侧栏 | — |
| toggleMinimalistView | 极简视图 | F10 | ✅ | 空函数 | ✅ | — |
| toggleFullscreen | 全屏 | F11 | ✅ | 空函数 | ✅ | 调 `setFullscreen` IPC |
| toggleTheme | 切换明暗主题 | F2 | ✅ | ✅实接 | 空函数 | 主题经主进程多窗同步 |
| openSettings | 设置 | F5 | ✅ | ✅实接 | 空函数（阅读器打开时仍由面板保留，见 4.2） | — |
| openColorScheme | 配色 | F6 | ✅ | ✅实接 | 空函数（同上） | — |
| openFindBook | 找书 / 主界面 | F7 | ✅→开找书窗 | ✅→**回主界面** | 空函数（面板保留） | **同一键双向**：在哪个窗就跳到另一个 |
| openBookSource | 书源管理 | F8 | 主窗面板隐藏；主窗未接线（空函数，按了无反应） | ✅找书窗专属入口，实际生效 | 空函数（面板保留） | 仅找书窗有效，证据见下注 |
| openNewWindow | 新窗口 | Ctrl+Shift+N | ✅主窗新窗 | ✅新建找书窗 | 空函数（面板保留） | 两窗语义不同 |
| enterStealthReader | 进入/退出摸鱼 | F9 | ✅进入摸鱼 | 空函数 | ✅可进入 | 摸鱼窗内退出由**系统全局 F9**负责（见 5.2） |
| toggleAllWindowsVisibility | 显示/隐藏全部窗口（全局） | **Ctrl+`** | scope:**global** | 同左 | 同左 | 唯一的 global 项，主进程注册 |

---

## 四、通用 vs 限定（重点）

### 4.1 绑定表本身：两窗 100% 通用

- 主窗和找书窗读的是**同一个 localStorage 键** `persistKey → data.shortcutBindings`（cacheStore 统一持久化）。
- 默认表 `createDefaultShortcutBindings` 只有一份；Mac/Windows 差异仅在 Control/Command。
- 找书窗挂载时 `loadMainShortcutBindings()` 读主设置（useFindBookPanelShortcuts.ts:39-44）；主窗改键后通过
  `storage` 事件 + `persistedSettingsChangedEvent` 双渠道实时同步到找书窗（:164-177, 213-237）。
- 持久化只存**覆盖项**（shortcutBindingOverridesForPersist :166），"全部还原默认"写空对象清除覆盖。

**结论：不存在"主窗一套键、找书窗另一套键"的情况；用户改一次，两个窗口同时生效。**

### 4.2 限定一：面板展示名单不同（仅影响看不看得到，不影响绑定）

[shortcutRegistry.ts:53-68](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/services/shortcutRegistry.ts#L53-L68)：

- **主场面板隐藏**（1 个）：`openBookSource`（书源管理只在找书窗用）
- **找书场面板隐藏**（8 个）：`openFile`、`pickTxtDirectory`、`openChapterRules`、`toggleBookmark`、
  `openSidebarSearch/Files/Chapters/AiAssistant`（本地文件与主窗侧栏功能）

隐藏只是"不在该窗口的设置面板里列出来"，绑定仍在同一张表中。

### 4.3 限定二：找书阅读器打开时，面板只保留 6 个动作

[useFindBookPanelShortcuts.ts:29-37](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/renderer/src/bookSource/composables/useFindBookPanelShortcuts.ts#L29-L37) 定义
`PANEL_ACTIONS_WHEN_READER_OPEN`：阅读器打开时，面板层只消费

```
openSettings / openColorScheme / openFindBook / openNewWindow / openBookSource / toggleTheme
```

其余键通过 `shouldDeferAction` 返回 true **让位给阅读器快捷键层**（:155-157）。
两层 `bindAppShortcuts` 同时挂在 window 捕获阶段，阅读器层先绑定（阅读器打开时 watch immediate 挂载），
形成"阅读器优先、6 个面板动作共用"的分工。

### 4.4 限定三：运行状态对按键的四种处置

消费时每个匹配到的动作依次过三道闸（shortcutService.ts:245-314）：

**闸 1 · shouldConsumeAction（吞掉，不执行）**
- 朗读播放锁定（`VOICE_READ_SCROLL_BLOCKED_ACTIONS`，:112-121）：↑↓ PageUp/PageDown、Ctrl+←/→、Ctrl+F
  在朗读"滚动锁定"时被吞掉——防止手动滚动与朗读跟随打架。

**闸 2 · shouldDeferAction（放行给下层/原生控件，不执行窗口动作）**

| 条件 | 让位的动作 | 代码 |
|------|-----------|------|
| 焦点在侧栏列表（方向键等） | 滚屏/切章类 | shouldDeferShortcutForReaderSidebar |
| 模态/弹层打开（有 Esc 前置层） | 6 个滚动切章动作（READER_SCROLL_SHORTCUT_ACTIONS :124-131） | useAppWindowBindings.ts:289-294 |
| 焦点在查找小窗内 | ↑/↓（让给查找的上/下一条） | :295-300 |
| **编辑模式 + 焦点在 Monaco 内** | 滚屏 4 键 + Ctrl+F（EDIT_MODE_MONACO_DEFERRED :102-109） | :301-305；找书阅读器同样逻辑 useFindBookReaderShortcuts.ts:186-190 |
| 任何 dismissible 弹层（菜单/下拉）打开 | **全部动作直接 return** | hasDismissibleOverlay()，:251 |

**闸 3 · voiceReadReaderKeys 重映射（朗读态专用键，无修饰键）**
朗读进行中（:253-261）：`空格`=暂停/播放、`←`=上一行、`→`=下一行；
但焦点在输入框/查找栏/按钮上时不重映射（keyboardEventBlocksVoiceReadRemap :155-171），保证还能打字。

**编辑态空格策略**（:279-283）：编辑模式下空格一律不翻页——焦点在输入面正常打字，不在输入面则直接吞掉（避免 Monaco 里翻页）。

### 4.5 限定四：L3 硬编码键

| 键 | 行为 | 条件 |
|----|------|------|
| **空格** | =下一屏（PageDown） | 只读阅读态、焦点不在输入面（keyboardEventBlocksReaderSpacePageDown :184-209）；用户若把空格绑给别的动作则走绑定表（:268-272）；找书面板 `mapUnmodifiedSpaceToPageDown=false`（无阅读器不翻页，:160） |
| **空格 / ← / →** | 朗读 暂停播放 / 上行 / 下行 | 朗读激活且无弹层（:253-261） |
| **Esc** | 层级退出链（见 4.6） | 全屏/极简 chrome 自动隐藏态 |
| **Alt 按住** | 临时切换"点击翻页↔文字选择"模式 | useReaderClickModeAltHold（鼠标交互，非键盘绑定表） |

### 4.6 Esc 层级退出链（useAppReaderChrome.ts:790-839）

Esc 不在可配置绑定表内，按固定优先级逐层退出（每一层只在自身打开时消费）：

```
① 文件重命名输入中        → 不拦截（:792）
② 任意 dismissible 弹层    → 交给弹层自己关（:802）
③ 编辑态焦点在 Monaco      → 交给 Monaco（:804-810）
④ 查找小窗打开            → 关查找栏
⑤ 浮动 chrome 面板打开     → 收起浮动面板
⑥ 全屏中                  → 第一次 Esc"上膛"，第二次 Esc 才真正退出全屏（防误触，:832-838）
非全屏/非自动隐藏态        → 不处理
```

---

## 五、系统全局快捷键（L1，独立于绑定表之外）

### 5.1 一键隐身：Ctrl+`

| 项 | 内容 |
|----|------|
| 默认键 | `Control+``（所有平台统一用 Control，globalShortcuts.ts:14） |
| 注册 | `registerGlobalShortcuts()`（:87-92）→ `toggleAllWindowsVisibility()`（:47-84） |
| 行为 | 第一次：隐藏所有主/找书窗口（setSkipTaskbar + hide，含任务栏/Dock 隐身）并快照最小化状态；第二次：原样恢复（摸鱼中用 showInactive 不抢焦） |
| 配置链路 | 面板改键 → `validateGlobalShortcut`（试注册检测系统占用，:110-127）→ `setGlobalShortcut` IPC（:129-150，失败自动回滚旧键）→ 主窗/找书窗启动时也会同步（useAppWindowBindings.ts:332-337） |
| 录制保护 | 录制快捷键时 `suspendGlobalShortcutsForRecording`（:152-157）临时注销，录完恢复——否则按键被 OS 拦截录不进去 |

### 5.2 摸鱼窗导航 4 键 + 退出键（仅摸鱼会话期间注册）

定义：[stealthNavShortcuts.ts:11-16](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/shared/stealthNavShortcuts.ts#L11-L16)，注册：[stealthReader.ts:319-342](file:///c:/Users/Administrator/Documents/这是什么/JK-temp/彩读分析/.temp/ColorTxt/src/main/stealthReader.ts#L319-L342)

| 动作 | 默认键 | 系统全局 |
|------|--------|---------|
| 上一页 | Ctrl+↑ | ✅ 进入摸鱼时注册，退出时注销 |
| 下一页 | Ctrl+↓ | ✅ |
| 上一章 | Ctrl+← | ✅ |
| 下一章 | Ctrl+→ | ✅ |
| 退出摸鱼 | **F9**（DEFAULT_EXIT_ACCEL，stealthReader.ts:33） | ✅ |

机制要点：
- 触发后主进程 `sendCommand`（:287-291）向摸鱼窗推命令，摸鱼窗内完成翻页/换章（章末再反向请求源窗取章节）。
- 重复键自动去重（`seen` Set，:322-325）；注册失败只 warn 不崩。
- 摸鱼导航键在**摸鱼设置窗**配置（非主快捷键面板），经 `applyStealthNavShortcuts`（:356-361）热更新。
- F9 的双重身份：正常窗口 F9 = 窗口快捷键"进入摸鱼"（L2）；摸鱼窗存在时 F9 = 系统全局"退出摸鱼"（L1），互不冲突。
- 录制快捷键时这些键一并挂起（suspendStealthSessionShortcuts :345-354，与 5.1 联动）。

---

## 六、按键分发流水线（一次按键的完整旅程）

`bindAppShortcuts` 注册在 **window keydown 捕获阶段**（shortcutService.ts:317），判定顺序固定：

```
keydown(捕获)
 │
 ├─ 快捷键面板正在录制？ → 交给录制处理器并 stopImmediatePropagation（:246-249）
 ├─ 有菜单/下拉等 dismissible 弹层？ → 全部不处理（:251）
 ├─ shouldHandleEvent？ ────────────── 找书阅读器层：阅读器没打开直接 return（:252）
 ├─ 朗读激活？ 空格/←/→(无修饰、焦点不在输入面) → 重映射为 暂停/上行/下行（:253-261）
 ├─ 是无修饰空格？
 │    └─ 只读态 → 翻下一屏；编辑态 → 吞掉；输入面 → 放行打字（:262-301）
 ├─ keyboardEventToAccelerator 转换键位（:302，IME 组词中返回空）
 ├─ matchActionFromBindings 查绑定表（:211-222，normalize 后全等匹配）
 ├─ shouldConsumeAction？ → 吞掉（朗读滚动锁定）（:306-310）
 ├─ shouldDeferAction？   → 让位（侧栏/弹层/查找栏/Monaco）（:311）
 └─ preventDefault + stopPropagation + 执行动作（:312-314）
```

键位匹配规则（shortcutUtils.ts:151-163）：
- 修饰键来自 `ev.ctrlKey/metaKey/altKey/shiftKey`，主键优先用 `ev.code`（物理键位，防布局错乱），回退 `keyCode`/`key`；
- IME 组词中（`isComposing`/keyCode 229）和纯修饰键不产生动作；
- 匹配前双方都过 `normalizeAccelerator`，所以 `ctrl+o` / `Control+O` / `Ctrl+o` 等价。

---

## 七、配置与录制流程（ShortcutPanel.vue）

```
打开快捷键面板（更多菜单→快捷键，或 F? 无默认键；从更多菜单进入）
  · visibleActions 按 panelContext(main/findBook) 过滤（:33）
  · draft = 当前绑定副本（:40,51）
点击某一行 → openEditModal → 录制框 focus
  · 立即 suspendGlobalShortcutsForRecording（:93）
       主进程注销 Ctrl+` 与摸鱼全局键，避免 OS 拦截 / 误触发
  · setWindowShortcutRecordingHandler 接管 window 捕获（先于所有动作执行）
录制："先按组合键，再按 Enter 确认"（:270）
  · 实时 collectShortcutConflicts 检测表内冲突 → "该快捷键已被占用"（:171-172）
  · global 动作额外 validateGlobalShortcut 检测系统级占用（:142-146）
确认 → tryApplyDraft（:61-72）
  · 无冲突 + 全局键可用 → emit("apply", 全量表)
       → App.vue applyShortcutBindings：
           ① setGlobalShortcut 同步 Ctrl+` 到主进程
           ② 只把覆盖项写入 localStorage(persistKey.shortcutBindings)
           ③ storage/事件广播，找书窗实时热更新，无需重启
取消/关闭 → resumeGlobalShortcutsAfterRecording（:109）
全部还原默认（:74）→ 同一条 apply 链，磁盘覆盖写空对象
```

---

## 八、按"通用程度"给动作归类（速查）

| 类别 | 动作 | 说明 |
|------|------|------|
| **真正全局**（OS 级，失焦也生效） | Ctrl+`、Ctrl+↑↓←→（摸鱼时）、F9（摸鱼时退出） | 主进程 globalShortcut |
| **两窗通用窗口键** | F2/F5/F6/F7/Ctrl+Shift+N、Ctrl+` 等 | 绑定表共享；各窗实现不同（如 F7 双向、Ctrl+Shift+N 开窗类型不同） |
| **主窗功能键（找书面板隐藏）** | Ctrl+O、Ctrl+Shift+O、Ctrl+R、Ctrl+D、Ctrl+Shift+F/E/C/A | 本地文件/主窗侧栏专属 |
| **找书窗功能键（主窗面板隐藏）** | F8 书源管理 | 主窗按 F8 无反应：useAppWindowBindings 的 `openBookSource` 是可选 dep（:133），App.vue 调用时未传入，兜底空函数（:242）；仅找书窗实接（useFindBookPanelShortcuts.ts:106） |
| **阅读器专用键** | 滚屏/切章/字号行高/排版/Ctrl+/、Ctrl+E、Ctrl+F、Ctrl+B、F10、F11、F9 | 找书窗内只有阅读器打开时才生效，未打开时为空操作 |
| **阅读器打开时面板保留键** | F2/F5/F6/F7/F8/Ctrl+Shift+N | 共 6 个，两层快捷键共存 |
| **状态条件键** | ↑↓PageUp/Down/Ctrl+←→/Ctrl+F/空格 | 随编辑态/朗读态/弹层/侧栏焦点动态让位或封锁 |
| **不可配置固定键** | Esc（层级退出）、Alt 按住（点击模式反转）、朗读 空格←→ | 硬编码在消费层 |

---

## 九、关键文件索引

| 角色 | 文件 |
|------|------|
| 动作注册表 + 默认键位 + 面板名单 | `src/renderer/src/services/shortcutRegistry.ts` |
| 键位工具（归一化/合并/冲突/持久化覆盖） | `src/renderer/src/services/shortcutUtils.ts` |
| 分发引擎（录制拦截/朗读重映射/空格/三道闸） | `src/renderer/src/services/shortcutService.ts` |
| 快捷键面板（录制/校验/还原） | `src/renderer/src/components/ShortcutPanel.vue` |
| 主窗消费点 | `src/renderer/src/composables/useAppWindowBindings.ts:236-321` |
| 找书面板消费点 | `src/renderer/src/bookSource/composables/useFindBookPanelShortcuts.ts` |
| 找书阅读器消费点 | `src/renderer/src/bookSource/composables/useFindBookReaderShortcuts.ts` |
| Esc 层级退出 | `src/renderer/src/composables/useAppReaderChrome.ts:790-839` |
| 一键隐身全局键 | `src/main/globalShortcuts.ts` |
| 摸鱼导航/退出全局键 | `src/shared/stealthNavShortcuts.ts` + `src/main/stealthReader.ts:300-361` |
| 全局键 IPC（validate/set/suspend/resume） | `src/preload/index.ts:763-781` → `shortcut:*` 通道 → globalShortcuts.ts |

---

# 十、逐键程序插口与调用链细节

> 本章回答："按下每一个键后，代码实际怎么走、最终调到哪个插口"。
> 链路统一格式：**按键 → shortcutService 分发 → 消费点处理函数（文件:行号）→ 最终插口（IPC 通道 / Monaco API / localStorage）**。
>
> 先给总体结论：**38 个窗口动作里，绝大多数是"渲染层动作"（Monaco 滚动/改 option、切面板、写 localStorage），只有 8 个动作的链路终点是 IPC**——
> `openFile`、`pickTxtDirectory`（对话框+文件流）、`openNewWindow`、`openFindBook`（主窗侧）、`toggleFullscreen`、`toggleTheme`、`enterStealthReader`、
> `toggleAllWindowsVisibility`（全局）。

## 10.1 分发起点（所有窗口键共用的前 4 跳）

```
keydown（window 捕获阶段，shortcutService.ts:317 注册）
  → matchActionFromBindings（:211）按归一化键位查 shortcutBindings
  → 过三道闸（shouldConsume / shouldDefer / voiceRead 重映射，见正文第六章）
  → preventDefault + stopPropagation
  → actions[action]()
       ├─ 主窗：useAppWindowBindings.ts:236-284 的动作表
       ├─ 找书面板：useFindBookPanelShortcuts.ts:101-145
       └─ 找书阅读器：useFindBookReaderShortcuts.ts:111-177
```
注意：动作表传入的多是 **App.vue/Panel 里的包装函数**，真正业务逻辑还要再跳 1~3 层才到插口。下面逐键展开。

## 10.2 主窗口逐键调用链

### A. 文件类（终点是 IPC）

| 键/动作 | 调用链 | 终点插口 |
|---------|--------|---------|
| Ctrl+O `openFile` | 动作表 → `deps.openFileViaDialog`（useAppWindowBindings.ts:264）→ App.vue `openFileViaDialog`（useAppFileSession.ts:521） | ① `showOpenDialog` preload:193 → `dialog:showOpenDialog`；② 选定后 `streamFile` preload:664 → `file:stream`（chunk 经 onStreamStart/Chunk/End 回流，useAppWindowBindings.ts:345-374） |
| Ctrl+Shift+O `pickTxtDirectory` | 动作表 :265 → App.vue `pickTxtDirectory`（useAppFileSession.ts:537） | `showOpenDialog` → `dialog:showOpenDialog`；扫描 `listTxtFilesInDirectory` preload:261 → `dir:listTxtFiles`（扫描进度 `dir:listTxtFiles:scan`） |
| F7 `openFindBook` | 动作表 :240 → App.vue `openFindBookWindow`（:2862-2864） | `window.colorTxt.openFindBookWindow()` preload:734 → **`window:openFindBook`**（主进程聚焦已有找书窗或新建） |
| Ctrl+Shift+N `openNewWindow` | 动作表 :263 → App.vue `openNewWindow`（:2858-2860） | `openNewWindow()` preload:731 → **`window:new`** |
| F9 `enterStealthReader` | 动作表 :241 → App.vue `enterStealthMode`（:2892-2922）：先取全文 `readerRef.getAllText()`、当前行、章节表、屏幕区域 | ① `getWindowContentBounds` preload → `window:getContentBounds`；② `stealthReaderEnter(payload)` preload:539 → **`stealthReader:enter`**（主进程 stealthReader.ts 建透明窗 + 注册 5 个摸鱼全局键） |
| F8 `openBookSource` | 主窗未传 dep，兜底空函数（useAppWindowBindings.ts:242） | **无插口，按键无效果** |

### B. 外壳类（部分 IPC、部分渲染层）

| 键/动作 | 调用链 | 终点插口 |
|---------|--------|---------|
| F11 `toggleFullscreen` | 动作表 :243 → `enterOrExitFullscreenView`（useAppReaderChrome.ts:216-235） | `setFullscreen(bool)` preload:681 → **`window:setFullscreen`**；状态回流监听 `onFullscreenChanged` → `window:fullscreen-changed`（preload:815） |
| F2 `toggleTheme` | 动作表 :262 → App.vue `applyShellTheme`（:3625 附近） | `setNativeTheme(theme)` preload:710 → **`theme:set`**；主进程再向其他窗广播 `theme:sync`（useAppWindowBindings.ts:227 接收） |
| F10 `toggleMinimalistView` | 动作表 :261 → App.vue `toggleMinimalistView` | **渲染层**：切外壳显隐 class + localStorage 持久化 |
| Ctrl+B `toggleSidebar` | 动作表内联（:254-260）：全屏自动隐藏态走 `revealFullscreenSidebar()`，否则翻转 `showSidebar` | **渲染层**（localStorage 记侧栏宽/开关） |
| F5 `openSettings` | 动作表 :238 → App.vue 内联（:3701-3703）置 `showSettingsPanel=true` | **渲染层弹层**（面板内部个别控件才有 IPC，见交互文档 11.2） |
| F6 `openColorScheme` | 动作表 :239 → 内联（:3704-3706）置 `showColorSchemePanel=true` | **渲染层弹层**（取色按钮除外 → `eyedropper:pick`） |

### C. 阅读排版类（终点是 Monaco option + localStorage，全部渲染层）

10 个排版动作同构，以字号为例：

```
Ctrl+= increaseFontSize
  → 动作表 :244 → App.vue dep（useAppReaderUiPrefs.ts:78-92）
    · readerFontSize.value += 1（钳制 maxFontSize）
    · readerRef.setFontSize(n) → ReaderMain 内 monaco editor.updateOptions({fontSize})
    · persistSettings() → cacheStore 写 localStorage（data.readerFontSize）
    · HUD 提示"字号：n"
  ✦ 无 IPC
```

| 动作（默认键） | 处理函数（useAppReaderUiPrefs.ts） | ReaderMain 落点 |
|---------------|-----------------------------------|-----------------|
| increase/decreaseFontSize（Ctrl+= / -） | :78 / :94 | `setFontSize` → editor.updateOptions |
| increase/decreaseLineHeight（Ctrl+] / [） | :105 起 | `setLineHeightMultiple` |
| increase/decreaseLetterSpacing（Ctrl+Shift+] / [） | 同文件 | `setLetterSpacingPx`（常规模式禁用，仅临时态生效） |
| increase/decreaseParagraphSpacing（Ctrl+' / ;） | 同文件 | 段间距 option |
| increase/decreaseHorizontalInset（Ctrl+Shift+. / ,） | 同文件 | CSS padding + 编辑器 layout |

### D. 滚动 / 翻页 / 切章（终点是 Monaco 滚动 API，全部渲染层）

| 键/动作 | 调用链 | 最终 API |
|---------|--------|---------|
| ↓/↑ `scrollDownLine/UpLine` | 动作表 :280-281 → App.vue:3723-3724 `readerRef.scrollByLineStep(±1)` → ReaderMain.vue:4006-4019：阅读尺激活时先移尺子，否则取 `lineHeight` 后 `scrollByDeltaY(±lineHeight)` | Monaco `editor.setScrollTop()`（封装在 scrollByDeltaY） |
| PageDown/Up `scrollPageDown/Up` | App.vue:3725-3726 → ReaderMain.vue:4165-4204（及 :3658 反向）：计算末行位置、粘性章头条高度、按整屏对齐滚动 + rAF 二次校准（pageTurnStickyAlign） | Monaco `getTopForPosition`/`setScrollTop` |
| **空格**（L3 翻页） | shortcutService.ts:262-272 直接重映射为 `scrollPageDown`（不走绑定表） | 同上 |
| Ctrl+→/← `jumpNextChapter/PrevChapter` | 动作表 :271-272 → App.vue 包一层朗读守卫 `jumpToPrevChapterWithVoiceRead`（:2405）→ useAppChapterNavigation.ts:111-118：`pickActiveChapterIdx` 按探针行定位当前章 → `jumpToChapter`（:82-101） | 阅读尺态：`readerRef.scrollChapterTitleToRulerFocus`；普通态：`readerRef.scrollToLineNearTop(line, smooth, anchor)` → Monaco 滚动；同时更新 `activeChapterIdx`（侧栏高亮），进度由探针节流写 localStorage |

### E. 查找 / 侧栏 / 书签 / 章节规则（渲染层）

| 键/动作 | 调用链 | 落点 |
|---------|--------|------|
| Ctrl+F `toggleFind` | 动作表 :273 → App.vue `onToggleFind`（useAppReaderUiPrefs.ts:357-359）→ `toggleReaderFind`（:352，朗读锁定时直接 return）→ `readerRef.toggleFindWidget()` | Monaco 内置 find widget（`editor.getAction('actions.find').run()`），无 IPC |
| Ctrl+Shift+F `openSidebarSearch` | 动作表 :274 → App.vue `openSidebarSearch`（:3405-3412）：取选中文本 → `openReaderSidebarTab("search")` → nextTick 聚焦搜索框 | 渲染层（侧栏 Tab 状态 + localStorage） |
| Ctrl+Shift+E/C/A `openSidebarFiles/Chapters/AiAssistant` | 动作表 :275-277 → App.vue:3713-3715 `openReaderSidebarTab(tab)`（:3398-3403；AI Tab 先查 `aiFeaturesEnabled`） | 渲染层 |
| Ctrl+D `toggleBookmark` | 动作表 :270 → `onBookmarkClick` | 渲染层：弹添加书签对话框 → fileMetaStore 写 localStorage |
| Ctrl+R `openChapterRules` | 动作表内联（:266-269）置 `showChapterRulePanel=true` | 渲染层弹层（应用后重算章节，无 IPC） |

### F. 编辑类

| 键/动作 | 调用链 | 落点 / 插口 |
|---------|--------|------------|
| Ctrl+/ `toggleReaderEdit` | 动作表 :278 → App.vue:3717-3719 → `onToggleReaderEdit`（:2548 起）：只读→编辑时先取全文 | `readWholeTextFile` preload:472 → **`file:readWholeTextFile`**（一次性读全文进 Monaco 可写模型）；编辑→只读时若有改动走保存链 `writeTextFile` → **`file:writeTextFile`** |
| Ctrl+E `editSelectedText` | 动作表 :279 → App.vue:3720-3722 → `readerRef.tryOpenPartialEditFromSelection()`（ReaderMain.vue:3373） | **渲染层**：只读态下对选区开局部物理行编辑浮层（保存时合入展示模型；落盘仍走 file:writeTextFile） |

### G. 朗读重映射三键（shortcutService 直接消费，无对应 action id）

| 键 | 条件 | 调用链 | 插口 |
|----|------|--------|------|
| 空格 | 朗读激活、无弹层、焦点不在输入面 | shortcutService.ts:255-258 → `voiceReaderKeys.togglePlayPause`（动作表 :314）→ App.vue `voiceReadTogglePlayPause` | `voiceReadSynthesize` preload:237 → **`voiceRead:synthesize`**；停止 `voiceRead:cancelSynthesis` |
| ← / → | 同上 | :315-316 → `voiceReadPlayPrevLine/NextLine`（App.vue:2387 附近）→ 取相邻物理行文本再合成 | 同上 `voiceRead:synthesize` |

## 10.3 找书窗·面板层 6 个可用键（书架/搜索/发现/书源/设置态）

消费点：useFindBookPanelShortcuts.ts:101-145；其余 31 个动作为空函数或被 `shouldDeferAction`（:155-157）让位。

| 键 | 调用链 | 终点插口 |
|----|--------|---------|
| F2 `toggleTheme` | :141 → `ctx.emit("toggle-theme")` → FindBookPanel.vue `onToggleTheme`（:1459） | `setNativeTheme` preload:710 → **`theme:set`**（多窗同步） |
| F5 `openSettings` | :105 → FindBookPanel `openSettings`（:1801）置 `panel="settings"` | 渲染层 |
| F6 `openColorScheme` | :106 → emit `color-scheme` → 打开配色面板 | 渲染层 |
| F7 `openFindBook` | :104 → `ctx.goMain()` → FindBookPanel `onGoMain`（:1825） | `focusOrOpenMainWindow` preload:755 → **`window:focusOrOpenMain`**（与主窗 F7 方向相反） |
| F8 `openBookSource` | :106 附近 → `ctx.openBookSources()` → FindBookPanel `onOpenBookSources`（:1758）置 `panel="bookSources"` | 渲染层（书源 CRUD 在面板内才走 `bookSource:*`） |
| Ctrl+Shift+N `openNewWindow` | :107 → FindBookPanel `onOpenNewWindow`（:1781） | `openNewFindBookWindow` preload:738 → **`window:newFindBook`** |

## 10.4 找书窗·内置阅读器层（阅读器打开时与面板层并存）

消费点：useFindBookReaderShortcuts.ts:111-177，ctx 实现在 FindBookReaderPanel.vue:1284-1313。

| 键类 | 调用链 | 终点 |
|------|--------|------|
| ↑↓ PageUp/Down、空格 | ctx → `readerRef.scrollByLineStep/scrollByPageStep`（同一个 ReaderMain 组件） | Monaco 滚动（同 10.2-D），渲染层 |
| Ctrl+←/→ 切章 | ctx `jumpPrevChapter/jumpNextChapter`（FindBookReaderPanel）→ useFindBookChapterSession `chapterPrev/Next` | 章内滚动渲染层；跨章 `bookSourceGetChapterContent` → **`bookSource:getChapterContent`**（缓存优先，见交互文档 12.2） |
| 10 个排版键 | :1287 `increaseFontSize: () => readerUi.increaseFontSize()` | 同主窗，渲染层（localStorage） |
| Ctrl+F | `readerRef.toggleFindWidget()` | Monaco find，渲染层 |
| Ctrl+/ | `ctx.toggleEdit`（阅读器只读/编辑切换）；编辑保存 | **`bookSource:saveChapterCache`**（编辑后的正文写回 .nb 缓存） |
| Ctrl+E | `readerRef.tryOpenPartialEditFromSelection()` | 渲染层局部编辑 |
| Ctrl+B / F10 | `ctx.toggleSidebar` / `onToggleMinimalist`（:1300） | 渲染层 |
| F11 | `toggleFullscreen`（FindBookReaderPanel.vue:1842） | `setFullscreen` → **`window:setFullscreen`** |
| F9 | :1311-1313 → FindBookReaderPanel `enterStealthMode`（:1199-1215）：载荷是**当前单章文本**而非全书 | `stealthReaderEnter` → **`stealthReader:enter`** |
| F2/F5/F6/F7/F8/Ctrl+Shift+N | 面板层 6 键保留（PANEL_ACTIONS_WHEN_READER_OPEN，:29-37） | 同 10.3 |

**摸鱼章边界跨界链（找书阅读器特有）**：

```
摸鱼窗内 Ctrl+→ 到本章末
  → chapterNext()（StealthReaderApp.vue:455-483）发现 ownerHasNextChapter
  → requestOwnerChapterNav("next")（:415-430）
  → stealthReaderOwnerChapterNav preload:555（send）→ 通道 stealthReader:ownerChapterNav
  → 主进程 stealthReader.ts:728-743 转发给源窗
  → FindBookReaderPanel.onStealthOwnerChapterNav（:1226）：切章 + 取正文
  → stealthReaderUpdatePayload preload:546 → stealthReader:updatePayload（热换正文，不关窗）
  → 摸鱼窗 onStealthReaderCommand/pullAndApplyPendingPayload 应用新页
失败/无邻章 → stealthReaderChapterNavSettled（preload:563）解除加载态（15s 超时兜底 :424-428）
```

## 10.5 系统全局键调用链（OS 级，不经 shortcutService）

### Ctrl+` 一键隐身

```
OS 按键（窗口失焦也能收到）
  → globalShortcut 回调（globalShortcuts.ts:87-92 注册）
  → toggleAllWindowsVisibility()（:47-84）
      隐藏态：遍历 BrowserWindow.getAllWindows()
        · 快照每个窗 isMinimized（供恢复）
        · setSkipTaskbar(true) + win.hide()（含 mac Dock 处理）
        · 标记全局 hidden=true
      恢复态：逐个 win.show() / restore()（摸鱼会话中用 showInactive 不抢焦 :74）
✦ 纯主进程窗口操作，无渲染层参与；无 IPC 往返。
配置链：ShortcutPanel → setGlobalShortcut preload:774 → shortcut:setGlobalToggle
      → globalShortcuts.ts:129-150（先 unregister 旧键再 register，失败回滚并返回 {ok:false}）
```

### 摸鱼 5 键（Ctrl+↑↓←→、F9）

```
进入摸鱼时 stealthReader.ts:319-342 registerStealthNavShortcuts(session)
  · 对 4 个导航键逐个 globalShortcut.register(accel, () => sendCommand(wc, cmd))
  · 退出键 F9 注册 → sendCommand(wc, "exit")
  · 重复 accel 去重；注册失败仅 warn
按键后 sendCommand（:287-291）
  → webContents.send(STEALTH_READER_IPC.command, command)
  → preload onStealthReaderCommand（preload:603-610，通道 stealthReader:command）
  → StealthReaderApp.onCommand（:716-720）
      pagePrev/pageNext → requestPageFlip(±1)（:295，页内切片渲染，无 IPC）
      chapterPrev/chapterNext → 章内 goToLine / 跨界走 10.4 的 ownerChapterNav 链
      exit → exitStealth（:709-714）
退出：stealthReaderExit(currentLine) preload:565（send）→ stealthReader:exit
  → 主进程 :810 handler：unregister 5 个全局键、关摸鱼窗
  → 向源窗 send(stealthReader:ownerProgress, {line})（:512）
      源窗 onStealthOwnerProgress（App.vue:537）接收 → 阅读器跳回对应行（退出回写）
```

## 10.6 不可配置固定键调用链

| 键 | 链路 | 插口 |
|----|------|------|
| Esc | window keydown（useAppReaderChrome.ts 挂载）→ `handleReaderChromeEscape`（:790-839）按 6 层优先级判定：重命名框→dismissible 弹层→Monaco→查找栏→浮动面板→全屏二次确认 | 渲染层；全屏分支内部调 `enterOrExitFullscreenView` → `window:setFullscreen` |
| Alt 按住 | useReaderClickModeAltHold 监听 mousedown/keydown | 渲染层：临时反转"点击翻页/文字选择"，松开还原 |
| 朗读 空格/←/→ | 见 10.2-G | voiceRead:synthesize |

## 10.7 配置/录制动作自身的 IPC 链

| 操作 | 调用链 | 插口 |
|------|--------|------|
| 打开录制 | ShortcutPanel `suspendGlobalShortcutsForRecording` | preload:779 → **`shortcut:suspendForRecording`**：主进程临时注销 Ctrl+` + 摸鱼 5 键（globalShortcuts.ts:152-157 及 stealthReader.ts:345-354） |
| 录制全局键校验 | `validateGlobalShortcut(accel)` | preload:765 → **`shortcut:validateGlobalToggle`**（试注册检测系统占用后立即注销，:110-127） |
| 应用绑定 | App.vue `applyShortcutBindings`（:2924）：① `setGlobalShortcut` 同步 Ctrl+`；② 覆盖项写 localStorage；③ storage 事件广播找书窗热更新 | `shortcut:setGlobalToggle`；其余渲染层 |
| 取消录制 | `resumeGlobalShortcutsAfterRecording` | **`shortcut:resumeAfterRecording`**（preload:781） |

## 10.8 按"插口类型"汇总（一眼看哪些键真的进了主进程）

| 插口类型 | 动作 |
|---------|------|
| **窗口管理 IPC**（window:*） | F7 双向（openFindBook / focusOrOpenMain）、Ctrl+Shift+N（new / newFindBook）、F11（setFullscreen） |
| **对话框 + 文件流 IPC** | Ctrl+O（dialog + file:stream）、Ctrl+Shift+O（dialog + dir:listTxtFiles） |
| **文件读写 IPC**（编辑链） | Ctrl+/ 进编辑读全文 file:readWholeTextFile；保存 file:writeTextFile；找书阅读器保存 bookSource:saveChapterCache |
| **主题 IPC** | F2（theme:set → theme:sync 广播） |
| **摸鱼 IPC 组** | F9 进入（stealthReader:enter）；摸鱼窗内 F9/Ctrl+方向（stealthReader:command/exit/ownerChapterNav/updatePayload/ownerProgress） |
| **OS 全局键** | Ctrl+`（globalShortcut 直接 hide/show）、摸鱼 5 键 |
| **书源 IPC** | 找书阅读器 Ctrl+←/→ 跨章（bookSource:getChapterContent） |
| **语音 IPC** | 朗读态 空格/←/→（voiceRead:synthesize） |
| **配置 IPC** | 录制 suspend/resume、全局键 validate/set（shortcut:*） |
| **纯渲染层（无 IPC）** | 10 个排版键、4 个滚动键、Ctrl+F、Ctrl+B、F10、F5、F6、Ctrl+R、Ctrl+D、Ctrl+Shift+F/E/C/A、Ctrl+E、空格普通翻页 |

---

*基于源码静态分析，行号随版本可能变动；新增可配置快捷键时务必同步注册表、面板、三个消费点三处真相源。*
