# ColorTxt（彩读）功能大全详解

> GitHub：https://github.com/ssnangua/ColorTxt ｜ 分析版本：v3.8.11（commit 9565e4d）
> 技术栈：Electron 35 + Vue 3 + Monaco Editor + TypeScript ｜ 协议：MPL-2.0
> 定位：本地 TXT 小说阅读器，「给内容上色」是核心卖点
>
> 本文以**功能**为纲，将项目的全部功能逐一展开：每个功能先说清用户能看到什么、怎么用，再讲实现机制（关键文件与函数，标注 `文件:行号`，相对 `src/`）、关键默认值，最后点出值得学习的设计决策。
>
> 姊妹篇：《ColorTxt项目深度分析报告.md》（架构总览）、《ColorTxt运行逻辑全流程深度剖析.md》（启动/打开/恢复/关闭动态流程）、《ColorTxt官方迭代史研究报告.md》（版本演进）。

---

## 〇、功能地图（先看全貌）

```
┌─ 阅读体验 ─────────────────────────────────────────────┐
│ 内容上色 · 自定义高亮词 · 配色方案(15预设) · 背景图 ·     │
│ 字体/字号/字距/行距/段距/边距 · 主题明暗 · 粘性章节标题   │
├─ 文件支持 ─────────────────────────────────────────────┤
│ TXT/MD · 电子书六格式转MD · 编码探测 · 流式加载(256KB)   │
│ 书架列表(分类/树状/排序) · 最近打开 · 书包ctz/ctzx       │
├─ 阅读辅助 ─────────────────────────────────────────────┤
│ 进度恢复 · 书签(置顶pin) · 划线笔记 · 内联/全文搜索 ·    │
│ 阅读尺(ADHD) · 定时滚动 · 点击模式 · 番茄时钟 · HUD ·    │
│ 全屏(时钟/边缘感应/宽度) · 极简视图 · 章节识别与导航      │
├─ 文本处理 ─────────────────────────────────────────────┤
│ 空行压缩 · 行首缩进 · 文本替换规则 · 简繁互转 · 全半角 ·  │
│ 编辑模式(全文/部分) · AI 智能排版(Diff预览)              │
├─ AI 能力 ──────────────────────────────────────────────┤
│ AI 阅读助手(Agent+RAG) · 思维导图 · 词云(语义模式) ·     │
│ 技能系统(11内置) · 防剧透 · 深度思考 · Token统计 ·       │
│ AI 高亮词检索 · 角色卡 · 角色立绘(文生图) · 章节规则生成  │
├─ 语音朗读 ─────────────────────────────────────────────┤
│ 7引擎TTS · 旁白/对白多音色 · AI说话人识别 · 标点停顿 ·    │
│ 朗读过滤 · 自动暂停 · 音色试听                            │
├─ 查词与查询 ────────────────────────────────────────────┤
│ 词典(5格式+2网络) · 翻译(10服务商) · 网络搜索(自定义引擎) │
├─ 内容获取 ─────────────────────────────────────────────┤
│ 书源找书(Legado兼容) · 多源搜索 · 在线阅读 · 整书下载 ·   │
│ 登录验证 · 验证码                                        │
├─ 场景模式 ─────────────────────────────────────────────┤
│ 摸鱼模式(透明置顶窗+老板键) · 多窗口(7种窗型)             │
├─ 数据与同步 ────────────────────────────────────────────┤
│ 四层存储 · 落盘门控 · 多窗防覆盖 · WebDAV · 清除数据 ·    │
│ 数据迁移 · 自动更新 · 文件关联 · 单实例                   │
└─────────────────────────────────────────────────────────┘
```

支撑这一切的两个底层机制（详见姊妹篇，此处只列结论）：

1. **双坐标系**：磁盘物理行（永不改变）与屏幕展示行（格式化后）靠 `displayLineToPhysicalLine` 映射表换算。所有阅读数据锚定物理行，所有渲染锚定展示行——这是「排版参数随便改、阅读数据永不失效」的根基。
2. **流式管线**（v2.1 重构）：加载阶段只累积物理行数组；格式化、章节匹配全部推迟到加载完成后在内存重放，不二次读盘。

---

## 一、阅读器核心：Monaco Editor 深度定制

彩读没有自研文本渲染引擎，而是把 VS Code 的 Monaco Editor 改造成阅读器，原因是小说阅读需要百万行性能、行列定位（书签/笔记锚点）、装饰器体系和 Diff 预览（智能排版）——富文本 div 做不了。作者本就是从「在 VS Code 里看小说」（vscode-txt-syntax 插件）的体验出发造的轮子。

### 1.1 内容上色（项目灵魂）

**用户视角**：打开小说后，对话引号内文字、括号内文字、标点、特殊标记（♡※☆→①Ⅰ…）、数字、英文字母各呈现不同颜色，一眼区分叙事与对白，带来「彩色小说」的阅读体验。灵感来源于 VS Code 插件 vscode-txt-syntax。

**实现**：
- `monaco/txtrTextMonarch.ts`：注册自定义语言 `txtr-text` 的 Monarch 词法规则，把上述六类元素识别为不同 token
- 配色由「配色方案系统」（§15.1）的 9 个颜色槽位驱动：`chapterTitle` / `bodyText` / `txtrQuoteInner` / `txtrBracketInner` / `txtrPunctuation` / `txtrSpecialMarker` / `txtrNumber` / `txtrEnglish` / `readerBg`
- 6 个 `txtr*` 色可单独开关（`readerPalette.ts:42-49`），关闭后回退正文色

### 1.2 自定义高亮词

**用户视角**：选中任意词语后浮出取色器（`ReaderHighlightFloat.vue`），点一个颜色即加入高亮词；适合突出主角名、关键设定词。支持**多词一组**（如「罗峰/罗城主」共用一色），支持全局收藏（跨书共享）与本书专属两级作用域。

**实现**：
- 持久化结构 `HighlightWordsByIndex`：`{ [颜色索引]: string[][] }`（色索引 → 词组列表 → 组内多词），本书的存 `file.meta`，收藏的存 `ui.settings.highlightWordsByIndexGlobal`
- `monaco/txtrHighlightMonarch.ts`：把词组动态注入 Monarch 规则实现着色
- 词组操作（`utils/highlightWords.ts`）：写入前先从其他组移除同词（`upsertHighlightGroupInMap:159`，一词不能同时在两组）、合并词组（`:229`）、拆分单词（`:250`）；合并展示时本书优先覆盖全局（`mergeHighlightWordsByIndex:319`）
- 列表面板 `HighlightListPanel.vue`：全局在前本书在后，多词组显示 `+N` 徽章可展开，点击词项跳到下一个匹配（单词字面量查找、多词组转 `|` 正则）
- **AI 检索高亮词**：详见 §11.8
- 导入导出：JSON 格式，按 colorIndex 分桶，导入时同词去重合并

**默认色板**：亮色 10 色（`#CC0000`~`#CC3399`，色相每 ~36° 一枚）、暗色 10 色（`#FF6666`~`#FFCCCC`），最小 3 色。

### 1.3 中文换行优化与「高级换行策略」

**背景**：Monaco 默认换行算法对中文不准（该换不换），这个问题连 VS Code 都没完美解决。彩读给出的答案是**给 Monaco 打补丁**：

- `monaco/cjkWrapOptimize.ts` + `cjkWrapStrings.ts`：通过 electron-vite 的 transform 改写 Monaco 内部 `strings.js` / `monospaceLineBreaksComputer.js`——网文常见全角符号（♡※☆→①Ⅰ…）按全角估算字宽，测宽样字从拉丁 `ｍ` 改为汉字「汉」
- 补丁集中在构建层，不改 Monaco 源码包，可随 Monaco 升级

**高级换行策略**（可选开关）：Monaco 原生的复杂换行算法，更准但性能差、内存大且难以释放（上游 monaco#5311 无解）。README 直接挂 WARNING 劝退默认使用——「简单换行策略 + 中文补丁」才是主路径。

### 1.4 段间距

**用户视角**：每个自然段（物理行）结束后追加一段额外空白，软换行的中间行不追加——通过快捷键 `Ctrl+;` / `Ctrl+'` 调节。

**实现**（`monaco/lineSpacing.ts`）：Vite transform 改写 Monaco 内部 `LinesLayout` 的四处偏移计算（总高度/行顶/行底/whitespace/视口循环），把段间距计入行偏移。项目 docs 记录踩坑：「若只改行高未改 whitespace 偏移，MD 插图会叠在上方正文上」。额外状态 O(1)，是补丁层的巅峰之作。

### 1.5 粘性章节标题栏

**用户视角**：滚动时当前章节标题常驻阅读区顶部，看到哪里一目了然。

**实现**（`monaco/chapterStickyScroll.ts`）：基于 Monaco stickyScroll + 自定义 DocumentSymbolProvider（把章节树提供给 sticky 组件）+ 标题装饰。翻页时有「预测条高 + 事后校正」双保险的避让逻辑（v3.7 issue #80 成果：相邻两页重叠一条完整行，避免被粘性条盖住）。

### 1.6 Markdown 插图与图片灯箱

**用户视角**：MD 文件（含电子书转换产物）中的 `![](path)` 图片以 ViewZone 形式内联渲染在正文流中，点击放大查看（灯箱 `ReaderImageLightbox.vue`）。

**实现**（`monaco/readerImageViewZones.ts`）：为每个图片 token 创建 ViewZone，宽度按阅读区自适应；插图绝对 top 的正确性依赖段间距补丁对 whitespace 偏移的改写。

### 1.7 键盘滚动与点击模式

- `monaco/readerKeyScroll.ts`：方向键滚动控制
- **点击模式**（`composables/useReaderClickModeAltHold.ts`）：可选模式（默认，可选中文本做标注）与点击模式（左键下一屏、右键上一屏，触屏式操作）二选一；**按住 Alt 临时反转**当前模式（`effectiveClickMode = altHold ? !persisted : persisted`），编辑模式下不反转
- Alt 检测细节：仅「alt 且无 ctrl/meta」才激活；左键已按下后再按 Alt 不切换（防列选误切）；焦点在输入框不激活；更深层模态打开时清除状态
- 点击模式 + 阅读尺联动时，左/右键改为按聚焦行数移动阅读尺锚点而非翻页

### 1.8 只读 IME 防护

**问题**：Monaco 0.55 默认 EditContext 在只读模式下仍会开启 IME（出现空白输入框），并把视口滚回光标位置。

**实现**（`monaco/readerReadOnlyImeGuard.ts`）：在编辑器 DOM 根节点捕获阶段拦截 `beforeinput` / `compositionstart` / `compositionupdate` / `textInput`，仅当 readOnly 且焦点不在查找栏（`.find-widget`）内时拦截；`isComposing || keyCode === 229` 的键盘事件一并拦截。编辑模式切换为可编辑时 dispose。

---

## 二、文件支持与加载

### 2.1 支持的格式总览

| 格式 | 处理方式 |
|---|---|
| `.txt` | 直接流式读取 |
| `.md` | 直接流式读取；章节按 ATX `#`~`######` 识别，按层级缩进成树；支持标题/链接/图片/内链少量语法（服务于小说文本） |
| `.epub` `.mobi` `.azw3` `.fb2` `.fbz` `.pdf` `.chm` | 打开时转换为 `.md` 缓存后加载 |
| `.ctz` / `.ctzx` | 彩读书包（§16.2） |

官方立场（README）：电子书会舍弃自带样式只提取文本，「排版精美的电子书建议用专门阅读器，彩读只适用于纯文本或带简单插图的电子书」。

### 2.2 自动编码识别

**实现**（`main/detectTextEncoding.ts`）：三级探测——BOM 优先 → `jschardet` 检测 → ANSI 中文启发式补判，配合 `iconv-lite` 解码。UTF-8 与 ANSI（GBK 等）都能正常打开。

### 2.3 流式读取管线（大文件不卡）

**链路**：

```
渲染层 streamFile(path)
  → 主进程 createReadStream({highWaterMark: 256KB})     main/ipcHandlers.ts:908-951
  → detectEncoding → iconv 解码
  → file:stream-start {encoding, totalBytes}
  → file:stream-chunk {text, readBytes} × N
  → file:stream-end
切书时 prevStream.destroy() 立即掐断旧流                  ipcHandlers.ts:874
```

- 渲染层用 `activeStreamRequestId` 校验每个 chunk 属于当前流（`useAppWindowBindings.ts:365`）——快速切书时旧流迟到 chunk 不会污染新会话
- 物理行切分（`services/physicalLineStream.ts:14-66`）：单遍 O(n) 扫描按 `\r\n` / `\r` / `\n` 切行，跨 chunk 的孤立 `\r` 暂存拼接（CRLF 恰好被 256KB 切断时不会多算一行）
- 流式阶段**只累积物理行数组**，不统计字数、不匹配章节、不写 Monaco——格式化与章节匹配在加载完成后统一内存重放（v2.1 管线重构的核心）

**写入 Monaco 的轻重两条路**（`ReaderMain.vue:1766 setFullText`）：
- 行数 > 8 万或文本 > 2500 万字符 → heavy 路径：`createModel` + `setModel` + dispose 旧 model（比 `setValue` 快，避免超长文本的重复分词与差异计算），临时关语法高亮延后恢复
- 普通路径：`m.setValue(text)`

**主动关闭 Monaco 三项自带优化**（`monaco/readerEditorOptions.ts`）：

| 选项 | 值 | 原因 |
|---|---|---|
| `largeFileOptimizations` | false | >30 万行时 Monaco 会关闭视口换行与 stickyScroll；网文一行一句极易破 30 万，正确排版优先 |
| `disableMonospaceOptimizations` | true | 京華老宋体被 Monaco 判等宽导致拉丁字母选区左偏 |
| `stopRenderingLineAfter` | -1 | 不截断超长行渲染 |
| `maxTokenizationLineLength` | 1,000,000 | 允许超长段落分词 |

### 2.4 电子书转换管线

**链路**：

```
源文件 → readBookAsArrayBuffer → convertBookBufferToArtifacts（按格式分派）
  → parseEpub / parseMobi / parsePdf / parseFb2 / parseChm
  → EbookMarkdownArtifacts（正文 md + 插图 + 内链侧车）
  → 写出 {原名}.epub.md + {原名}.Images/ 目录
  → ensureEbookMarkdown 严格缓存检查 → 流式读取 .md
```

**缓存策略**：转换结果路径记录在 `file.meta.convertedMdPath`，严格命中条件 = 路径一致 + 源文件 mtime 与 `sourceMtimeMsAtConvert` 一致 + 文件存在。未命中则静默重转并更新 meta；路径失效时按候选顺序（记录路径 → 输出目录 → 源书同目录 → 默认目录）「和解查找」。

**格式深水区**（迭代史沉淀）：
- 为 CHM 移植了整个 libmspack C 库到 JavaScript
- PDF 三连修：CMap/wasm 随包、XObject 抽图「同一对象只解码一次，不再逐页 getOperatorList」、Indexed 调色板 4bit 展开
- 标题匹配从「包含匹配」收紧到「仅精确匹配」——防『卷一』+『周纪一』两行正文被误升为 `# 卷一 周纪一`
- EPUB/MOBI/PDF/FB2 的解析主要参考 foliate-js 的实现
- HEIC 封面转 JPEG（`heic-convert`）

**中间格式两次推翻**：v1.2 转 .txt 自造 `<<A>>/<<IMG>>` 标记 → v2.5 推翻改转 Markdown（私有标记表达不了层级/插图/链接）→ v3.3 手写正则解析 MD 边角无穷 → 推翻改走 marked 的 `Lexer.lexInline`。

**MD 内链/脚注**：电子书的内链与脚注转为 MD 锚点，阅读时可点击跳转（`composables/useReaderEbookInternalLinks.ts` + `reader/ebookAnchorLookup.ts`）；格式化管线会做「MD 内链剥离」把锚点标记从展示文本中清掉。

### 2.5 打开入口与「openFilePath 唯一闸门」

五种打开方式（Ctrl+O 对话框 / 拖放 / 资源管理器双击 / 命令行第二实例 / 书架点击）全部汇聚到 `useAppFileSession.ts:1058` 的 `openFilePath`——所有状态清理、进度记忆、恢复仲裁都发生在这一个函数里，不存在第二处状态机。完整十阶段流程见姊妹篇《运行逻辑全流程深度剖析》第二章。


---

## 三、文件管理（书架）

### 3.1 文件列表

**用户视角**：侧栏「文件」面板即书架。拖放添加文件或目录（**递归读取子目录**），支持分类管理、多种排序、关键字过滤，可切换**列表/树状**两种视图（树状按目录层级展示，`utils/fileListTree.ts`）。

**实现**：
- 列表项结构：`{name, path, size, category, addedAt}`，持久化于 `colorTxt.file.list`
- 分类管理：`FileCategoryManageModal.vue` + `CategoryPickerMenu.vue`，分类是用户自定义标签
- 排序与过滤：`composables/useFileListCategorySort.ts`、`useAppSidebarSearch.ts`
- 选择与多选热键：`useFileListSelection.ts` + `useListSelectionHotkeys.ts`
- 空闲时机优化：打开文件时侧栏 size 列延迟写回（requestIdleCallback + 2s 超时兜底），避免与首帧流式加载抢主线程

### 3.2 最近打开

- MRU（最近使用优先）顺序，仅存 `{path}`，持久化于 `colorTxt.recent.files`
- 打开/切书时 `touchRecentFile` 置顶；文件丢失时从最近列表自动剔除

### 3.3 拖放导入

`utils/dragDropFsPaths.ts`：拖入单文件直接打开；拖入文件/文件夹走 `importPathsIntoFileList` 入列表不打开（递归读取子目录）。

---

## 四、章节系统

### 4.1 章节识别

**三个来源**：

1. **内置规则**（`shared/chapterMatchBuiltinPatterns.ts`）：预置常用正则（「第X章」「第X回」等 3 条）
2. **自定义规则**：用户在「章节匹配规则」面板（`ChapterRulePanel.vue` + `ChapterRuleEditDialog.vue`，快捷键 `Ctrl+R`）自定义正则；支持规则优先级
3. **AI 生成规则**：启用 AI 助手后让 AI 分析文本抽样、产出单行正则（走 `chapter-match-rules` 技能，见 §11.6——该技能禁用 ragContext、必须输出 fenced 单行正则）

**识别流程**（两扫设计，三种任务三种时机互不阻塞）：
- **首扫**（格式化期间，物理行上）：`collectQualifiedChapterTitlePhysicalLines`（`reader/readerDisplayPipeline.ts:217`）跑章节正则，并按 `minCharCount`（默认 100 字）过滤——累计正文字数不足阈值的「标题」不认（防把「第 1 天」误判成章节）；决定哪里插标题上下留白
- **二扫**（写入 Monaco 后，展示行上，requestIdleCallback 异步执行）：`refreshChapterListFromReaderAsync` 构建侧栏目录，不阻塞首屏
- 普通书 getAllText + split 逐行 detect；heavy 书（>5 万行）`getEditorLineContent` 逐行读每 8000 行 yield；MD 书按 ATX 标题构建

**MD 书**：按 `#`~`######` 层级识别，章节列表按标题层级缩进、父级可折叠。

### 4.2 章节列表树

`reader/chapterListTree.ts`：层级树、折叠过滤、祖先展开。当前章高亮，滚动时自动平滑滚动居中到当前章（probe 取视口 3/4 处行判定，`pickActiveChapterIdx`：取 probe 行 ≤ 章节首行中最大者）。

### 4.3 章节导航

- 快捷键 `Ctrl+←/→` 上一章/下一章
- 底栏 `ReaderChapterNavBar.vue`
- 跳章走「视口槽位」统一锚点：目标行对齐到顶部往下第 `max(1, headingLevel)` 条字高带——层级越深留白越少，都为粘性条腾空间

---

## 五、格式化与文本转换

### 5.1 空行压缩与行首缩进

- **空行压缩**：把连续空行压成可配置的行数（可保留 1 行）
- **行首缩进**：行首添加全角缩进
- 两者都作用于**展示层**（`reader/readerDisplayPipeline.ts` 格式化管线），磁盘原文不动；实时修改参数时走「锚点桥接」：采锚 → 内存重放格式化 → 恢复锚点，眼睛几乎感觉不到跳动

### 5.2 文本替换规则

**用户视角**：全局替换文本，典型用途：替换人名、去掉广告文本。正文与标题分轨（可分别设置是否替换）。

**实现**（`shared/bookSource/replaceRule.ts` + `applyReplaceRulesToDisplayText`）：支持正则；持久化于 localStorage `colortxt:replaceRules:app`（主界面）与找书窗独立的一份；书包导出/WebDAV 同步都包含它。

### 5.3 简繁互转与全半角

- **OpenCC**（`main/textConvertOpenCc.ts` + `registerTextConvertIpc.ts`）：主进程 `createRequire` 加载原生模块（打包需 asarUnpack、electron-rebuild 重编译）
- **全半角互转**（`shared/textWidthConvert.ts`）：字母/数字全半角互转
- 两者都只作用于展示层，不改变磁盘原文；开启后全文搜索的列号需经 `displayColumnToPhysicalColumn` 映射回物理列（注释坦承简繁/替换开启时可能轻微错位）

### 5.4 AI 智能排版（编辑模式下的杀手锏）

**用户视角**：编辑模式下，工具栏「AI 智能排版」一键全文排版，或选中文本右键「AI 智能排版：选中文本」局部排版（长文建议分次）。完成后显示 **Diff 预览**——左边原文右边改后（可再编辑），逐处确认后点「应用」一次性写回，「放弃」则主文档不变。

**排版选项**（`shared/aiSmartFormatTypes.ts:6`，设置→编辑）：

| 选项 | 默认 | 执行者 |
|---|---|---|
| 清理 HTML 残留（解码 `&#35498;`/`&nbsp;`、去 `<br/>`） | 开 | 本地预处理 |
| 修正硬换行（合并段内句中强行换行） | 开 | LLM |
| 修正标点符号（引号括号配对、半角转全角、断句补标点；不动数字小数点与英文对白半角标点） | 开 | LLM |
| 统一对话符号（统一为 `""` 或 `「」`） | `""` | LLM |
| 移除广告/引流信息（`发布于 xxx` 等站宣） | 开 | LLM |
| 移除盗版水印（句中插入的防盗版杂符） | 开 | LLM |
| 修正乱码（`锟斤拷` `�` 还原汉字） | 开 | LLM |
| 还原 \* 屏蔽（根据上下文还原和谐字；不处理整行分隔线） | 开 | LLM |
| 自动压缩空行 | 开 | 本地后置 |
| 自动行首缩进 | 开 | 本地后置 |

**分块处理**（`shared/aiSmartFormatChunkLimits.ts`）：1 字 ≈ 0.9 completion token（留 10% 余量）→ 单段上限 `max(1500, min(8000, floor(maxTokens × 0.9)))`，优先在换行处切。maxTokens 调高（如 8192）可减少分段数与请求次数。

**LLM 调用**（`main/ai/chat/textFormatCleanup.ts:212`）：
- 系统提示以技能 `smart-format` 的 prompt 为基础，按启用项动态拼段，附 7 条硬性约束（禁止改剧情/人名/语序，禁止的/地/得互替等）
- 用户消息含【上文参考】【待校对正文】【下文参考】三段
- temperature=0 + `withAiRequestRetries` 重试（最多 3 次，延迟 2s/4s/8s）

**防跑偏三件套**（渲染层编排 `useAiSmartFormat.ts`）：
1. `revertDeDiDeParticleSubstitutions`——还原被模型擅自改动的「的/地/得」
2. `tryRecoverFormatOutputScope`——尝试恢复模型越界修改
3. `validateFormatOutputPreserved`——校验输出保真，不通过则整段跳过

**Diff 预览**（`useReaderSmartFormatDiff.ts`）：Monaco `createDiffEditor`，支持上下条跳转、空白 diff 开关、折叠未变更区域、右键 revert 单处。

---

## 六、阅读辅助功能群

### 6.1 阅读进度恢复

自动记录阅读进度，下次打开继续。这是全项目最精密的子系统之一：

- **六级恢复仲裁**（`useAppFileSession.ts:1123-1178`）：显式锚点 > 显式物理行 > 读完全书直接到底（`MAX_SAFE_INTEGER` 哨兵）> Monaco viewState（含光标/水平滚动/折叠/选区的「完整底片」）> 仅锚点行 > 顶部
- **布局无关锚点**：存 `{物理行, 折行内下标}` 而非 scrollTop（`reader/readerViewportAnchor.ts:6`）——空行漂移、段间距、折行参数变化都不会让恢复错位；采锚落在空行时上移到非空行
- **进度门闸** `readingProgressSynced`：false 期间（加载中/恢复中）一切 live 视口信息都不许写 meta，防止「加载中停在顶部的视口」冲掉真实进度；把关三处：切书记忆、视口捕获、gated 写盘
- **文件变更自愈**：电子书源更新（mtime 变）静默重转；正文被编辑过则标注标 `stale`；viewState 与实际布局不符时按锚点兜底

### 6.2 书签

**用户视角**：`Ctrl+D` 在当前视口添加带备注的书签（备注默认取选中文本）；侧栏列表管理；**置顶 pin**（书钉）记录当前滚动位置，跳走后一键返回。

**实现**：
- 结构 `FileBookmarkItem = { line（物理行）, note?, createdAt, updatedAt }`，存于 `file.meta.bookmarks`
- 视口内自动检测：当前视口物理行范围内有书签时高亮，再按 `Ctrl+D` 变为移除
- **pin 机制**（`useAppBookmarkPins.ts:45-65`）：`pinnedScrollTop` 记录添加/跳转时的 scrollTop；打开查找栏前自动 pin（`ensurePinBeforeRevealFindWidget`），查找跳转后可一键回原位
- 跳转走「视口槽位」slot=2；保存锚取 `scrollTop + 1 lineHeight` 处的行，与跳回后光标行一致，避免「差一行」
- 导出 `{书名}.bookmarks.json`（schemaVersion 1），导入时同行以导入侧为准

### 6.3 划线标注与笔记

**用户视角**：选中文本浮出工具条，可选「划线」（马克笔半透明/波浪线/直线三样式 × 5 色）或「笔记」（写想法）。侧栏列表管理全部标注，支持导出 MD/JSON、导入 JSON。

**实现**：
- 数据模型 `ReaderAnnotationRecord`：物理行+物理列区间、**原文快照**、时间戳；存于 `file.meta.readerAnnotations`
- **失效自愈**：物理区间与快照不符（正文被外部/编辑改动）→ 标 `stale:true`，UI 显示失效标记而非错误高亮
- 装饰（`reader/readerAnnotationDecor.ts`）：Monaco inline 装饰 + 动态 CSS 规则；视口内仅注册 ±80 行范围（性能）
- 交互参考微信读书网页版；划线颜色的色板即「标注色」（§15.1）
- 选区工具条 `ReaderSelectionToolbar.vue` 统一承载：划线/笔记/编辑/词典/翻译/高亮/复制等按钮

### 6.4 内联搜索与全文搜索（两套系统）

| 维度 | 内联搜索 | 全文搜索 |
|---|---|---|
| 入口 | `Ctrl+F` 阅读区查找栏 | `Ctrl+Shift+F` 侧栏搜索面板 |
| UI | Monaco 内高亮 + 逐个导航 | 结果列表（行号+命中预览） |
| 引擎 | Monaco `findMatches` | 自研逐行扫描 |
| 上限 | 19999 处 | 20000 条 |
| 特性 | 大小写/全字/正则 | 大小写/全字/正则 + 结果复制（带行列号） |

**全文搜索实现**（`useAppSidebarSearch.ts:158`）：180ms 防抖 + 竞态 token；编辑态扫物理行、只读态扫展示行后映射回物理行列；同一行多次匹配各占一条结果；VirtualList 虚拟滚动渲染结果；点击结果 → 滚动居中选中 + 联动设置内联高亮的当前匹配。

### 6.5 阅读尺（明确面向 ADHD 人群）

**用户视角**：高亮聚焦行（1~10 行），淡化其余行（透明度 0~1 可调），帮助注意力不集中的人聚焦当前阅读位置。切换有 200ms 过渡动画，粘性标题可配置是否一并淡化。

**实现**（`reader/readingRuler.ts`，619 行）：
- 按**视觉行**（wrapped visual row）而非物理行计算聚焦带——二分查找视觉行起止列（`visualRowStart/visualRowEndColumn`）、跨物理行步进（`stepVisualLine`）
- 空行不计入聚焦带、不作为锚点（`snapRulerPosToContent` 先下后上找最近内容行）
- 跟随视口：视口扣粘性条后取中点最近行做锚（平局取偏上，防刷新时锚点逐次下移）
- 聚焦行渲染为 Monaco `inlineClassName` 装饰，刚离开的行有淡出动画
- 与点击模式联动：左右键按聚焦行数移动锚点而非翻页

### 6.6 定时滚动

**用户视角**：定时自动滚动一屏或一行，间隔 200ms~10 分钟（默认 3 秒）。手动滚动/翻页后自动重置计时。

**实现**（`useAppTimedScroll.ts`）：`setInterval` 每 tick 检查视口是否到底；自动停止条件——切文件/进编辑模式/加载中/语音朗读/到底部（找书场景支持 `continueAtBottom` 到底自动切下一章）。

### 6.7 番茄时钟

**用户视角**：阅读 25 分钟 → 短休 5 分钟 → 每 4 轮长休 15 分钟（均可调 1~180 分钟）。休息时全屏毛玻璃遮罩「休息一下」+ 大号倒计时 + 「我休息好了」按钮；底栏饼图倒计时控制（点击展开暂停/停止）。全屏时左下角系统时钟旁可同显番茄饼图。

**实现**（`usePomodoroTimer.ts`）：`phase: idle | focus | break` 状态机，`endsAtMs` 时间戳 + 250ms tick；饼图用 `conic-gradient` 绘制已流逝/剩余扇区。

### 6.8 全屏阅读（禅模式）

**用户视角**：F11 进入，一切 UI 隐藏。**阅读区宽度 30%~100% 可调**（默认 50%，居中）；鼠标移到窗口**边缘感应区**唤出浮动顶栏/章节侧栏/底栏（三栏互斥）；指针静止 2 秒隐藏光标；左下角半透明系统时钟（默认开启）；连按两次 Esc 退出。

**实现**：
- 边缘感应（`useAppReaderChrome.ts`，921 行统一模型，与极简视图共用）：左/顶/底边缘 20px 感应；唤起需「在感应区内 + 未按鼠标 + 无更深层模态」；拖入边缘后抑制至指针先离开感应区；`elementFromPoint` 判断指针是否仍在面板子树内再决定收起
- 阅读区两侧空白区域转发交互：空白区点击转发点击模式手势、滚轮转发给 Monaco、右侧 20px 滚动条槽不触发翻页（`useAppFullscreenReaderLayout.ts`）
- Esc 按层关闭的统一模型：输入框 → 蒙版 → 菜单 → 查找栏 → 面板 → 退全屏（连按两次确认，2 秒窗口，repeat 不计）

### 6.9 极简视图

F10 切换，阅读区撑满窗口但**不进系统全屏**；边缘感应与全屏共用 `chromeAutoHide`；极简中的 Esc 只关浮动面板不退出极简。

### 6.10 HUD 提示

阅读区中央的胶囊形短暂提示（类似视频播放器音量 OSD），用于快捷键即时反馈（字号变化等）。显示 1 秒 + 淡出 250ms，连按只显示最后一次（`useReaderHudTip.ts`）。


---

## 七、编辑模式

**用户视角**：「错别字坚决不能忍！」——`Ctrl+/` 进入全文编辑模式，Monaco 变可编辑（可选显示行号/小地图，默认都关）；选中文本后 `Ctrl+E` 或工具条「编辑」打开**部分编辑**弹窗（1000 字符以内），改完写回选区。标题栏 dirty 时加 `*` 前缀。

**实现**：
- 编辑态 Monaco 切换只读开关；`monaco/readerDiffEditorOptions.ts` 提供 Diff 编辑器选项（智能排版预览复用）
- **未保存守卫**：切书/关书（`confirmIfReaderEditDiscard`）、关窗（主进程 preventDefault → 渲染层确认 → 二次 close 握手）三处把关
- **自动刷新章节列表**：编辑改动内容时同步更新章节（< 30 万行才开，`appUi.ts:354`）
- 部分编辑面板（`ReaderPartialEditPanel.vue`）：textarea 自适应高度（最小 3 行最大 10 行超出滚动）、`Ctrl+Enter` 快速确认
- 编辑模式下：定时滚动自动停止、Alt 反转点击模式失效、光标常显不隐藏

---

## 八、语音朗读（TTS）

### 8.1 七引擎矩阵

| 引擎 | 密钥 | 实现要点 |
|---|---|---|
| Edge TTS | 免 | `main/voiceReadEdgeTts.ts`，WebSocket 流式 |
| 系统语音 | 免 | 渲染进程 Web Speech API |
| 讲述人自然语音（Win SAPI5） | 免 | PowerShell `System.Speech`，需装 NaturalVoiceSAPIAdapter 适配器；专为用上 Windows 讲述人自然音色 |
| 阿里通义 Qwen3-TTS | 需要 | dashscopeProvider，PCM |
| MiniMax | 需要 | MP3 |
| 小米 MiMo | 需要 | MP3；支持**音色定制/克隆**（目前限免） |
| 火山豆包 2.0 | 需要 | 24kHz PCM；内置**官方 444 个音色**，可切方言 |

Provider 注册表架构（`main/voiceRead/providerRegistry.ts` + `providers/`），新引擎即插即用。渲染层每引擎配独立音色选择器（如 `voiceReadVolcengineVoiceSelect.ts` 按语种/方言分组）。

### 8.2 多音色方案

- **单音色**：全书一段音色
- **旁白/对白多音色**：旁白、默认对白、男声对白、女声对白分轨配置
- **角色专属音色**：角色卡中给每个角色绑定专属音色（§12.7），AI 识别说话人后按角色分派

### 8.3 AI 说话人识别

**用户视角**：开启多音色 + AI 识别后，朗读前应用自动判断每条引号内文本是谁说的（或旁白），分配对应音色；甚至能识别情绪。

**实现**（`main/ai/voiceReadSpeaker.ts:115` `attributeVoiceReadSpeakers`）：
- 输入：当前行原文 + 引号内文本列表 + 上下文行 + 角色表（角色名+别名）
- 系统提示词规则：非对白（旁白强调/术语/招式名/书名）→ `narration`；对白 → `male/female/unknown` + speaker（可用别名推断）；引导语可在引号前后（「杨过道：""」或「""杨过道。」）；无引导语结合上下文推断；**不仅凭引号就假设是对白**
- 输出 JSON：`{ quotes: [{ kind, speaker, emotion }], narrationEmotion }`，emotion 为 10~30 字自然语言描述
- 别名匹配：`buildRosterNameMap` 把角色名+别名映射到 displayName，LLM 输出的说话人名标准化
- 参数：maxTokens ≤ 768、temperature ≤ 0.3（低温保一致性）、非流式
- 解析失败全部回退 `unknown`；兼容旧格式

### 8.4 标点停顿（Edge TTS 的 WordBoundary 攻坚，v3.8.9~3.8.11）

**问题**：朗读在标点处自然停顿的标准答案是 SSML `<break>`，但 Edge readaloud 端点不支持（带上直接断连）。

**三层发明**：
1. 主进程收集音频 metadata 的 **WordBoundary** 词边界事件，按词序把全角标点映射为音频内待替换区间 `[fromMs, toMs]`（词与标点粘连按文本比例插值、连续标点合并、ASCII 标点不参与防误伤 IP/URL）
2. 区间随 mp3 一并缓存——**区间只依赖音频内容，与停顿时长解耦**，调滑块不废已缓存音频
3. 播放端 `decodeAudioData` 后把区间整体替换为干净静音（2ms 淡入淡出，时长随语速同比缩放）

结果：句中/句末两个独立滑块；仅 Edge 生效（其他引擎音频流无词级时间戳）。

### 8.5 朗读过滤与自动暂停

- **朗读过滤**：独立于朗读方案的正则规则（括号内、加粗、斜体等），跨行匹配，朗读时忽略
- **自动暂停**：朗读指定章节数或时长后自动暂停
- 持久化于 localStorage `colortxt:voiceReadSpeak`（不随朗读方案）
- **继续朗读向导**（`VoiceReadResumeGuide.vue`）：跨会话恢复朗读位置的引导

---

## 九、词典、翻译与网络搜索

### 9.1 词典

**用户视角**：选中文本 → 工具条「词典」→ 弹窗中**所有启用的词典同时以卡片形式**给出释义（本地+网络混合）；释义内可点 `entry://` 链接在卡片内跳转查新词（带返回栈）；齿轮进入管理面板：导入词库、开关、拖拽排序优先级、改名、删除。

**格式支持**（5 种本地 + 2 种网络，解析器全部自研，仅 MDX 查词用 mdict-js 库）：

| 格式 | 解析 | 要点 |
|---|---|---|
| StarDict（.ifo/.idx/.dict.dz） | 自研 | `.idx` 二分查找；`.syn` 同义词；DictZip 分块解压（自研 `dictZip.ts`）；导入时预扫生成 `.idx.offsets` SDOF sidecar 加速启动 |
| MDict（.mdx/.mdd） | mdict-js + 自研资源解析 | `@@@LINK=` 最多跟 5 跳；MDD 图片/音频/CSS 转内联 data URL；Speex 音频自研转 WAV |
| DICT/dictd（.index/.dict.dz） | 自研 | dictd base64 偏移解析 + 二分 |
| Slob/Aard2 | 自研 | 二进制格式 magic `!-1SLOB\x1F`、refs 二分、zlib |
| BGL/Babylon | 自研 | gzip 偏移 → 块流 → headword/definition |
| Wiktionary（网络） | 内置 | 中文词走 wikitext 解析（重定向/拼音/释义），其余走 REST API；经 Chromium 网络栈（支持系统代理） |
| Wikipedia（网络） | 内置 | 自动检测中英文语言，取 summary |

**调度策略**（`main/dictionary/dictionaryService.ts:320`）：本地词典**串行**（防多本大词库抢磁盘 IO）+ 网络词典**并行**，两组重叠执行——总等待 = max(本地串行, 网络最慢)；结果按用户优先级排序。

**细节**：
- 查词候选变体：原文 → 小写 → Title Case → 去尾部标点变体，6 个候选依次尝试提高命中率
- `DictHtmlFrame.vue`：**Shadow DOM 隔离**的词典 HTML 渲染器——词典自带 CSS 不污染整页；暗色主题下检测词库硬编码浅色时自动垫浅底板；拦截发音链接（emit 播放）与词条跳转链接
- 加密 MDX、非 zlib Slob、混合 sametypesequence 的 StarDict 标记 unsupported
- 网络词典超时 8s/预算 10s；StarDict LRU 256 条
- 词典下载建议（README）：优先 StarDict 和 MDict；离线维基用 Slob；多语对译用 FreeDict

### 9.2 翻译

**用户视角**：选中文本 → 工具条「翻译」→ 弹窗自动翻译；可切目标语言、翻译服务（AI 时还可切方案）；可显示/隐藏原文；AI 翻译附 Token 消耗条与预估花费。

**10 个服务商**：

| 类别 | 服务商 | 鉴权 |
|---|---|---|
| 免费通道 | 微软（Edge 公开端点）/ Google（网页接口 client=gtx）/ Yandex（Android 通道伪装 UA） | 无需配置 |
| API Key | DeepL（官方/DeepLX 自动识别）/ 百度（MD5 签名）/ 有道（SHA256 签名）/ 腾讯（TC3-HMAC-SHA256 四层派生）/ 火山（HMAC-SHA256）/ 阿里（HMAC-SHA1 RPC） | 各自平台申请 |
| AI | OpenAI 兼容接口，独立方案（最多 12 套，独立 baseUrl/key/model/maxTokens 默认 8192） | 密钥保险库 |

**关键技术**：
- **分块**（`shared/translationChunk.ts`）：各服务商上限 600~10000 字符不等；切分优先级 段落空行 > 换行 > 句读 > 空格（各需达上限 35%~50% 位置）；避免切开 UTF-16 代理对；多块结果 `\n\n` 连接
- **缩进保持**（`shared/translationIndent.ts:18`）：把原文行首缩进（空格/Tab/NBSP/全角空格）套到译文——行数一致按行号对齐，不一致按非空行对齐
- AI Prompt：专业译者人设 + 只输出译文 + 中文目标的文言文转白话特殊规则 + temperature 0.3
- 所有请求经 Chromium 网络栈（支持系统代理），超时 20s；`translateSeq` 防竞态
- 语言映射：各厂商语言码不同（百度繁体 `cht`、有道中文 `zh-CHS`），`mapLang` 统一
- 目标语言当前启用 5 种：简中/繁中/英/日/韩

### 9.3 网络搜索（右键菜单）

**用户视角**：选中文本 → 右键 → 「网络搜索」子菜单 → 选引擎，在系统默认浏览器打开搜索结果页。默认 5 引擎（Google/Bing/百度/DuckDuckGo/维基百科），可自定义添加（名称 + 含 `%s` 的 URL 模板，支持自定义协议如 Everything 的 `es:`），可拖拽排序。

**实现**（`shared/webSearchTypes.ts` + `WebSearchManageModal.vue`）：纯前端功能，`buildWebSearchUrl` 替换 `%s` 为 URL 编码的选中文本后 `openExternal`；设置在主阅读器与找书阅读器间共享。这是全项目最轻量的功能——不涉及 AI、不涉及 IPC 业务逻辑。


---

## 十、AI 阅读助手（Agent + RAG）

这是项目最大的 AI 子系统。官方对「为什么需要向量模型」的清醒认知（README 原话）：对话模型擅长「思考」和「说」，却不擅长「找」，也不可能每提一个问题都把整本小说发给服务器——所以用向量模型提前给整本小说建索引，提问时先在本地找到相关片段再交给 AI，**索引在本地执行不消耗 Token，发给服务器的只剩几个片段**。

### 10.1 Agent 工具循环

**用户视角**：侧栏「AI 阅读助手」提问（`Ctrl+Shift+A`），助手自动判断要不要先检索正文、要不要出图，然后流式回复；回答中的章节名带 `（ch=N）` 可点击跳转；可开「深度思考」「防剧透」。

**实现**（`main/ai/chat/agentChat.ts:1266` `runAgentChat`）：

```
while (round < maxRounds)          默认 8 轮，上限 64
  组装 messages = [system, ...history]
  streamOneRound() → SSE 解析 → content/reasoning/toolCalls 增量
  ├─ 有 toolCalls → 执行工具 → 结果作 role:"tool" 消息入 history → 下一轮
  └─ 无 toolCalls → 写 DB → done 事件 → 结束
```

- **系统提示词动态拼装**（`buildAgentSystemPrompt:111`）：基础角色（「资深中文小说阅读助手」+「预训练知识不包含本书全文」）→ RAG 检索纪律段（含章节引用规则）→ 词云工具说明 → 书籍信息（书名/总章节数/当前章节）→ 阅读位置周边节选 → 防剧透段（若开）→ 技能列表 → 用户附加提示词 → 思维导图/词云注入提示
- **阅读位置锚点每轮注入**（`augmentLatestUserWithReadingAnchor:540`）：在最后一条 user 消息前注入「【本轮阅读位置｜须与此对齐】」，防止对话历史中旧章节的 ragContext 残留导致模型误判「本章」
- **防死循环**：连续 3 轮 toolCalls 指纹（name+args 排序）完全相同 → 重复轮跳过执行 + `pendingFinalizeNudge` 强迫下一轮不发送 tools 直接输出最终回答（兼容不支持 `tool_choice:"none"` 的本地推理服务）
- **重试**：网络错误/502/503/504/429 可重试（最多 3 次，2s/4s/8s）；401/403/400/abort 不重试

### 10.2 向量索引（建库）

**分块**（`utils/aiChunkBook.ts:58` `chunkNovelForAi`）：逐章分块，章内逐行累积；Token 估算 `字符数/1.5`；默认参数——目标块 300 token、最小 50、**相邻块 20% 重叠**（提高跨块语义连续性）。

**向量库**（`main/ai/rag/vectorDb.ts`）：`better-sqlite3` + `sqlite-vec`，`vector.sqlite`：

| 表 | 用途 |
|---|---|
| `chunks` | 文本分块（book_hash/章节/内容/行列/token 数） |
| `vec_embeddings` | `vec0(embedding float[dim])` 虚拟表，KNN 检索 |
| `id_mapping` | rowid ↔ chunk_id ↔ book_hash |
| `threads` / `messages` | 按书的 Agent 会话与消息 |

维度变更时自动 drop+recreate 向量表并清空分块。BookHash = SHA-1(路径+大小+mtime) 前 16 位。

**嵌入引擎**：
- **内置本地模型**（`@huggingface/transformers`，Worker 线程）：BGE Small ZH v1.5（~47MB，512 维，推荐）/ Multilingual E5 Small（~118MB，384 维）；模型经 **hf-mirror.com 镜像**下载（国内可用性）；每批 20 条；不消耗 Token
- **远程嵌入 API**：OpenAI 兼容 `/embeddings`，每批默认 10 条（可配 1~64）
- 索引构建三阶段：chunking → embedding（分批）→ indexing（写 SQLite），进度在侧栏顶部横幅展示（`AiIndexProgressBanner.vue`）

### 10.3 检索工具：ragSearch 与 ragContext（清醒取舍）

- **ragSearch**（语义检索）：query 嵌入 → sqlite-vec KNN（先全局取 `min(2048, max(64, topK×40))` 近邻再按书过滤）→ 每条命中截断 900 字 → 返回 JSON。用于跨章语义检索（「xxx 在第几章出场？」）
- **ragContext**（整章原文）：**优先从阅读器直接取章节原文**（IPC 桥，20s 超时，512K 字符上限）而不是向量拼接 chunk——章节级问题直接给整章；原文 ≤1 万字原样返回，**>1 万字分段压缩为全章提要**（`ragChapterDigest.ts`，按每万字切段、每段独立调对话模型压缩、按段长比例分配输出预算、合并后 ≤1 万字）
- 设计哲学：RAG 不是万能锤，向量检索只做跨章语义检索

### 10.4 防剧透（spoilerSafe）

- 判定：开启且当前章节索引 ≥ 0 → `spoilerMaxChapterIndex = 当前章节`
- 四层过滤：ragSearch 结果过滤（先多取候选再筛）、ragContext 超前章节直接报错、角色检索同样过滤、系统提示词明确「第 N 章之后全部为后文，不得主动泄露」
- 当前阅读位置由渲染进程视口探针（3/4 处行）推导传入
- 例外：`chapter-match-rules` 技能需要全书抽样章节标题，不受防剧透截断

### 10.5 深度思考（reasoning）

`main/ai/chat/chatThinking.ts:158`：深度思考时 temperature 强制 1，并按 baseUrl 注入各厂商思考开关——本地 `think:true`、DeepSeek `thinking.type`、智谱/DashScope/Moonshot/SiliconFlow `enable_thinking`、OpenRouter/Gemini `reasoning_effort:"high"`、MiniMax `thinking.type+reasoning_split`。流式 reasoning 提取兼容 `reasoning_content`/`reasoning`/`thinking`/`thought` 四种字段名。UI 折叠展示思考过程（`AiAssistantDetailsFold.vue`）。

### 10.6 技能系统

**用户视角**：设置→技能，11 个内置技能可开关、可改描述与提示词（覆盖默认），也可新建自定义技能。启用后助手对话中注册对应 `skill_*` 工具，模型按需调用获取该技能的 SOP 提示词并据此格式化回答。

**11 个内置技能**（`shared/aiSkills.ts:39`）：智能摘要 / 概念解释 / 论证分析 / 人物追踪 / 金句收藏 / 阅读向导 / 智能翻译 / 词汇助手 / 章节匹配 / **智能排版**（仅编辑管线用，不注册到对话）/ 角色立绘。每个含数百到上千字的完整 SOP prompt。默认除 smart-format 外全部启用。

**注入链**：启用收集（排除 pipeline-only）→ 工具注册（`skill_{清洗后的id}`，名称只留 `[a-zA-Z0-9_-]`）→ 系统提示列举 name+description → 模型调用时返回 skillPrompt + instruction（要求事实内容须来自本书，须先 ragSearch/ragContext）。

### 10.7 思维导图

- 工具 `mindmap`（`main/ai/tools/mindmapTool.ts:75`）：模型生成 `#/##/###/-` 层级 Markdown；**误用 Mermaid mindmap 语法时自动按缩进深度转换**；返回节点数与最大深度统计
- 渲染：markmap-lib + markmap-view（`AiMindmapView.vue`）
- **自动出图判定**（`shared/aiMindmapIntent.ts:111`）：三档——explicit（明确提到「思维导图/知识图/结构图」）、auto（开放型问题：概括/总结/梳理/关系/结构，且非定位类）、none（排除模式：「不要图/简短/纯文字」）；检索后未出图时插入 nudge 追问迫使模型出图
- 与词云双工具互斥仲裁：同时显式提到都注入，否则默认优先词云

### 10.8 词云（含语义模式）

**general 模式**（高频词）：逐章取正文 → `@node-rs/jieba` 分词（过滤纯数字标点/单字符非中文）→ 词频缓存到 `segment.sqlite`（按 content_hash+seg_version 校验，章节变更自动重建，侧栏可全书预热）→ 合并过滤停用词 → Top N（默认 80，可配 10~200）→ d3-cloud 渲染。

**semantic 模式**（语义词云，如「武功招式」「武器装备」）：
1. 分层抽样章节（12 章或含首尾的 48 章）
2. 抽样正文送 LLM 抽取词项（System prompt 不预设类别，仅依赖 semanticQuery 自由文本；候选上限 120）
3. 二次 LLM 筛选仅保留符合语义的词项
4. 在**全部章节正文**中对保留词精确计数（不是只数抽样）
5. Top N 渲染

**AI 检索高亮词**（`useHighlightAiSearch.ts:34`）：复用语义词云管线的加强版——`unlimitedTerms` 模式（候选上限 2000、抽样 48 章、每章 4000 字、分批抽取每 8 章一批、maxTokens 8192），始终全书范围不受防剧透限制；结果预填进高亮词添加面板。侧栏预设「人名」「地名」一键检索 + 自定义语义输入。

### 10.9 Token 用量统计

- 提取：`prompt/completion/total_tokens` + 缓存命中（DeepSeek `prompt_cache_hit_tokens` / OpenAI `prompt_tokens_details.cached_tokens` / Anthropic `cache_read_input_tokens` 三种格式兼容）
- Agent 跨轮累加（含 ragContext 压缩与词云抽取的用量）；流式请求带 `stream_options: { include_usage: true }`
- 花费估算：输入分缓存命中/未命中两种单价 + 输出单价（每百万 Token 价格），格式如「本次对话消耗 Token：12,345（输入 8,000（缓存命中 5,000），输出 4,345），总花费约：¥0.12」

### 10.10 API 方案管理与预设

- **对话方案（Profile）**：最多 12 套，各含 baseUrl/apiKey/model/temperature/maxTokens/slidingWindowSize（默认 0.7/4096/8）；活跃方案一键切换；密钥存保险库不落明文（`stripProfileApiKeysForDisk`），方案 id 变化时孤儿密钥自动挂回
- **14 个服务商预设**（`shared/apiEndpointPresets.ts:171`）：LM Studio/Ollama（本地）、DeepSeek、通义、智谱、Kimi、硅基流动、Agnes、MiniMax、MiMo、OpenAI、OpenRouter、Gemini（OpenAI 兼容）+ 自定义；MiMo 用 `api-key` 头，其余 `Bearer`
- **系统提示词预设**：无 / 虚构文学分析（视为虚构创作，减少敏感拒答）/ 摘录与客观描述 / 自定义
- 对话历史导出（`aiAssistantExport.ts`）、按书分线程管理、清空入口

---

## 十一、角色卡与立绘

**用户视角**：侧栏「角色」面板。输入角色名（可带别名），AI 检索小说正文自动生成角色档案（外貌/性别/年龄/身份/简介/关系/别名/经典台词），再通过文生图生成角色立绘。角色卡正面立绘+竖排名字，背面详细信息；悬停 3D 倾斜+全息纹理，点击翻面，拖拽排序，原位放大。角色可绑定专属朗读音色。

### 11.1 角色数据结构

`shared/characterTypes.ts:13` `CharacterRosterEntry`（按书持久化于 `file.meta.characterRoster`，上限 200 个）：

```
id / displayName / aliases（中文逗号拼接）/ gender / ageText / identity / bio / relations
promptZh（形象描述，文生图正面提示词）/ negativeZh（负面）
retrieveThinkingText（检索折叠区正文）
voiceReadVoiceId / Language / Dialect（火山专属语种方言）/ SampleLine / SampleQuotes / SampleQuoteIndex
```

书籍级画风：`stylePrefixZh`（画风前缀）+ `styleNoteZh`，所有角色共享。

### 11.2 AI 检索生成链路（`main/ai/tools/characterPortrait.ts:844`）

```
① 别名发现：RAG 多查询（「{n} 人称/绰号/外号…」）→ LLM 产出别名列表
② 合并别名：用户输入优先 + 检索发现（去重、排除与角色名相同，最多 12 条）
③ 外貌检索：RAG 多查询（「{n} 外貌/容貌/身穿/长相…」topK 28，防剧透过滤）→ ≤14000 字上下文
④ LLM 提取：输出 JSON（excerpts/appearance/sd_prompt/negative/gender/age/identity/bio/relations/aliases）
   解析失败 → 二次 LLM 修正 → 仍失败回退检索片段摘要
⑤ 别名兜底：从「人称XX」「绰号XX」等文本正则抽取
```

**画风推断**（`runBookStyleInference:787`）：RAG 检索「文笔 文风 叙事」「画面感 氛围」「场景 意象 镜头」「{书名} 封面 插画」→ LLM 输出画风前缀与备注；默认回退「戏剧性光影，氛围感强，小说插画风格」。

**中文译英**（`runPortraitPromptZhToEn:580`）：画风+正面+负面三段中文 → SD 英文 tag（自然语言或 tag 风格）。

**经典台词检索**：RAG 查「{n} 说/道/台词/名言」→ LLM 最多 8 条，供音色试听「换一句」轮换。

### 11.3 文生图（7 后端）

A1111 WebUI / ComfyUI（本地）/ OpenAI Images / Agnes AI / 通义万相 / MiniMax / Stability AI / 自定义 OpenAI 兼容。流程：AI 整理画风+形象 → 自然语言 prompt 或 SD tag → 生成 → 先写 `_tmp.png` 预览，用户点「应用」后才转正式立绘。立绘存 `CharacterPortrait/{书名}/`，编辑期间草稿用 `_char_draft_` 前缀隔离，保存时才提交。

### 11.4 3D 卡片效果（pokemon-cards-css 同源）

- **12 种全息纹理**（`characterCardTextureEffects.ts:25`）：细腻光泽（默认）/迷离反闪/梦幻竖纹/幻彩波纹/波纹钢印/幻彩极光/极光异画/梦幻虹彩/彩虹秘稀/彩虹异画/星云幻彩/关闭
- **倾斜弹簧物理**（`characterCardSpring.ts`）：指针跟手刚度 210/阻尼 19；移出回正低阻尼 32/1.9（ζ≈0.17 欠阻尼）+ 1.65 倍回正初速度——实体卡片般的弹性过冲手感
- **倾斜角为唯一驱动**：光泽/纹理 CSS 变量全部由 rotateX/rotateY 反推，回弹时纹理与卡片同步
- **原位放大**：360° rotateY 翻转入场 → 居中放大（max 420px，2.4 倍）；列表小卡倾斜幅度 0.4 倍
- **拖拽排序**：SortableJS（forceFallback + 8px 容差区分点击翻面与拖动），拖动克隆层 scale 1.1，松手飞回落位动画（280ms easeOutCubic）

### 11.5 与 TTS 联动

角色卡绑定专属音色 → 朗读时 AI 识别说话人 → `speaker` 匹配角色 → 取该角色 `voiceReadVoiceId`；无专属音色按 gender 回退男/女声对白音色；再回退全局对白默认。试听：切单音色方案 + 角色 voiceId 直接合成一段（可用 AI 检索的经典台词轮换）。

### 11.6 角色卡包

独立导出/导入 `.characters.zip`（manifest + portraits/），同名角色以导入侧字段为准但保留本地 id（避免立绘缓存失效）。


---

## 十二、书源找书（Legado 兼容引擎）

**定位**：在主进程用 TypeScript 复刻 Legado（阅读 App）的 Java 书源解析引擎，直接兼容数万社区书源 JSON。官方声明坦诚到罕见：「移植了一套 JavaScript 实现，做不到 100% 复刻……只能通过迭代不断纠错兼容，目前算是测试版」「不提供、不内置、不分发任何书源」。这也是项目出圈的主因（科技爱好者周刊、LINUX DO 收录）。

### 12.1 架构

```
找书窗（独立窗口 find-book.html，入口「更多 → 找书」或 F7）
    │  window.colorTxt.bookSource* (preload → IPC)
    ▼
registerBookSourceIpc.ts
    ├── bookSourceStore（SQLite：书源/登录/缓存/Cookie）
    ├── searchService（多源并发搜索）
    ├── downloadService（整书下载导出 txt）
    └── engine/webBook.ts → AnalyzeUrl + AnalyzeRule + jsExtensions
```

找书窗自带完整阅读器（复用主阅读器的阅读管线），书源书可在线阅读。

### 12.2 规则引擎

- **5 种规则模式**：Default（Cheerio/Jsoup）、JSON（JsonPath）、XPath、JS（Node AsyncFunction）、Regex；链式解析（前段输出作后段 `result`）
- `makeUpRule` 展开 `@get:`、`{{…}}` 模板表达式；`evalJS` 注入 `java`/`source`/`book`/`chapter`/`result` 绑定
- **Rhino(JVM) vs V8 语义差异修补**（成体系）：末尾表达式补 return、`forEach(async…)` 改串行、形参与 let 同名重命名、Mozilla `let()` 表达式改写、正则字面量修复、零宽字符剥离；Java 桩（DES/AES/Base64/Jsoup.connect）；Jsoup vs Cheerio 行为对齐（`[attr~=val]` 语义、孤立 tr/td 包 table、破损页面先 parse5 纠错再给 xmldom）

### 12.3 网络层

- **Chromium `session.fetch`**（浏览器 TLS 指纹）：undici fetch 曾被 Tengine 类站点 TLS 重置，v3.3 换血
- 仅书源显式 `webView:true` 才开隐藏后台 webView 抓取（每次任务一窗即抛）
- **Cookie 体系**：按可注册域（eTLD+1，tldts 提取）归档；WebView Cookie 从 extraHeaders 改 session 注入——docs 记录惨案：「extraHeaders 只作用于首个请求，页面内 AJAX 走空 session → 站点发回游客会话 → persistWebViewCookies 把游客 Cookie 覆盖回 jar，**登录态被静默摧毁**」
- **并发控制**：`concurrentRateLimiter.ts` 实现书源 `concurrentRate` 限制，未配置默认每源 3 路并发

### 12.4 登录验证与验证码

- **登录验证窗**（`sourceVerification.ts:448`）：主窗体 + footer 工具栏双 BrowserView 结构，加载远程页
- **验证码**：`bookSource:captchaRequest` 经 `sendToAppRenderers` 按 URL 过滤广播到各 app 窗，内嵌到找书界面（`AppCaptchaHost.vue`）
- 书源可配代理

### 12.5 存储

| 存储 | 内容 |
|---|---|
| `book-sources.db` | `book_sources`（完整 JSON+enabled+更新时间）/ `book_source_login` / `book_source_cache`（source 级 KV）/ `book_source_cookies`（全局 Cookie Jar） |
| `book_cache/` | 章节正文离线缓存 |
| `DownloadedBooks/` | 整书导出目录 |
| `book-source/files/` | importScript/cacheFile 本地脚本 |

### 12.6 找书窗 WebDAV

找书数据（书架一书一文件增量同步、书源合并导入、设置、搜索历史）可独立 WebDAV 同步，见 §14.3。

---

## 十三、摸鱼模式

**官方吐槽**：「不知道有什么用」（README 原话）。实际是把「无边框透明置顶窗」在三大平台的系统级坑位清单趟了一遍的功能。

### 13.1 摸鱼阅读窗（F9）

- 无边框、透明背景、无任务栏、**始终置顶**（screen-saver 层级）且 **focusable:false**（点击不激活，翻页全靠全局键）
- 全局键 `Ctrl+↑/↓` 翻页、`Ctrl+←/→` 切章；右键菜单开关定时滚动
- 独立设置窗（故意不设 parent——透明子窗在 Windows 会垫白底）；独立 localStorage `colorTxt.stealth.settings`，经 storage 事件跨窗同步

### 13.2 运行机制（多窗口体系的集大成者）

- **进入**：源窗收集 payload（整本全文快照/视口顶行/章节快照/bounds）→ IPC 中转 → 覆盖层拉取后清空；源窗连任务栏图标一起隐藏；overlay `showInactive` 不抢焦点；启动 z-order 看护
- **翻页数据完全本地化**：进入时全文一次性搬运，覆盖层自己**离屏测量分页**（`stealthPaginate.ts`：fitsSlice → fitPageEnd 排页 → pageStack 翻页栈 → rAF 预取下一页）；连点合并到下一帧、单帧最多 12 页
- **切章三段式请求-应答**（找书窗单章场景）：覆盖层贴边 → ownerChapterNav → 主进程转发源窗 → 源窗换章 → updatePayload（只走 pending+command，避免大正文双通道 IPC）→ 覆盖层拉取应用；15s 超时解锁
- **进度只在退出时回传**：exit 携带当前逻辑行 → 源窗 jumpToLine（摸鱼期间源窗不滚动）
- **退出**：5 条销毁路径全部汇入 teardown（置空 session → 停看护 → 注销全局键 → 连坐关设置窗 → 清 shape → destroy → 恢复源窗）

### 13.3 老板键（摸鱼快捷键）

默认 `Ctrl+``（可自定义）。隐藏：每窗记最小化快照 → `setSkipTaskbar(true)` + `hide()`（Windows 连任务栏图标一起去掉）+ 摸鱼中 overlay.hide()（**不注销翻页键，藏着也能翻**）+ macOS `app.dock.hide()`。恢复：`showInactive` 不抢焦点 → 重申置顶 → 重启看护 → 还原各自最小化状态。

### 13.4 Windows 专属补丁群（11 天修复马拉松的沉淀）

| 问题 | 补丁 |
|---|---|
| 无边框窗最小高约 39px，单行窗做不到 | `setShape` 把可视/点击区裁回逻辑尺寸 |
| 点任务栏系统强抬任务栏压过置顶窗（#91） | 指针进入任务栏条带立即重申置顶 + 700ms 周期兜底 |
| 高 DPI 拖动物理/逻辑像素混算越拖越大（#89） | 拖动时钉死逻辑宽高 |
| Win11 DWM 对透明窗垫实心底 | `backgroundMaterial:"none"` + 抢焦点后水平微移 1px 逼重绘 |

已知无解：Linux Wayland 全局快捷键失效。

---

## 十四、个性化

### 14.1 配色方案系统（项目核心卖点之一）

**用户视角**：`F6` 打开配色面板，三个标签页——**阅读器**（9 色表面配色 + 背景图叠层）、**高亮色**（高亮词前景色板，亮/暗各一套）、**标注色**（马克笔/波浪线/直线 5 色）。内置 15 套预设，可复制为自定义方案编辑、重命名、删除，可导入导出配色包。

**阅读器 9 色槽位**（`readerPalette.ts:5-16`）：

| 槽位 | 亮色默认 | 暗色默认 |
|---|---|---|
| 背景 | `#f4ead7` | `#1e1e1e` |
| 章节标题 | `#b88230` | `#569cd6` |
| 正文 | `#000000` | `#d4d4d4` |
| 引号内 | `#a31515` | `#ce9178` |
| 括号内 | `#001080` | `#9cdcfe` |
| 标点 | `#267f99` | `#4ec9b0` |
| 特殊标记 | `#f56c6c` | `#f56c6c` |
| 数字 | `#795e26` | `#dcdcaa` |
| 字母 | `#af00db` | `#c586c0` |

**15 套内置预设**（亮 8 暗 7）：默认 / 素纸 / 羊皮纸 / 护眼 / 毛绒地毯 / 墨竹 / 雪梅 / 星空（暗）——后七者各绑定一张内置背景纹理。

**交互模型**：
- **草稿-应用模式**：所有改动先进内存草稿，点「应用」才一次性提交；关闭时脏检测（JSON 对比基线）弹确认
- **主题锁定**：编辑时锁定明暗切换；亮/暗两套选中状态独立（`selectedIdLight`/`selectedIdDark`）
- 内置方案需先复制为用户方案才可编辑（`u-` 前缀 id）
- **配色包**（`.color-scheme.zip`，JSZip）：`color-scheme.json` + `textures/` 自定义背景图；「导出配色」（全部）或「导出当前方案」（仅选中用户方案）；导入后进草稿需手动应用

### 14.2 背景图系统

- **8 张内置纹理**：素纸/羊皮纸/护眼/毛绒地毯/星空/墨竹/雪梅 + 无（内置图由 ChatGPT Images 2.0 生成）；已下架的 sand/cardboard/moon 读入时当「无」
- **自定义导入**：png/jpg/jpeg/webp，单文件上限 12MB，复制到 `userData/reader-backgrounds/{uuid}.{ext}`
- **每张图独立参数**（亮暗分开）：不透明度（0~100% 步长 5）/ 填充方式（填满 cover/包含 contain/原始 auto）/ 平铺开关 / **9 宫格对齐锚点**（`ColorSchemeBackgroundAlignPad.vue`，3×3 格子对应 `background-position`）/ **7 种混合模式**（normal/multiply/lighten/overlay/soft-light/screen/darken，内置图有推荐默认值）
- **应用到文档**：6 个 CSS 变量写入 `document.documentElement`（`--reader-bg-image` 等）；`auto` 模式用 `image-set()` 标注 devicePixelRatio 使 1 图像素=1 屏幕像素，DPR 变化自动重刷；粘性标题条背景对齐单独计算偏移（ResizeObserver + MutationObserver 防错位）
- 上传 WebDAV 时按文件名+大小增量、自动清理远端孤儿文件

### 14.3 屏幕取色器

- `HexColorPickerField.vue`：三种模式——HSV 色盘（方形 SV + 竖向色相条，Pointer 拖拽）/ HSL 滑条（三滑条+数值输入）/ **屏幕取色**；模式持久化；弹层智能上下翻转；draftHex 实时预览
- **屏幕取色实现**（`main/eyedropper.ts`）：**每屏一窗 + 冻结截图**——`desktopCapturer` 截每个显示器 → 每屏建无框全屏覆盖窗贴截图 → 实时采样鼠标下颜色（HEX/RGB 可切，进程级记忆）→ 左键确认 / Esc 右键取消 → 结果写剪贴板；标记 `__colortxtEyedropper` 防被当用户窗误关；取色前临时处理摸鱼状态、取色后恢复

### 14.4 字体系统

- **4 个预设字体**（平台自适应）：京華老宋体（内置打包，仅供学习交流）/ 黑体 UI 无衬线（Win 微软雅黑 / Mac 苹方 / Linux 思源黑体）/ 宋体（SimSun / 宋体-简 / 思源宋体）/ 楷体（KaiTi / 楷体-简 / 文鼎 UKai）
- **系统字体枚举**：`font-list` 包主进程枚举，去重按中文排序缓存；FontPicker 虚拟列表 + 过滤搜索 + 已选「其他字体」可 pin 钉住
- 摸鱼模式额外提供「系统默认」与「终端默认」（`terminalFont.ts`：Windows 读 Windows Terminal settings.json → 注册表 `HKCU\Console\FaceName` → 回退 Cascadia Mono）
- **排版参数范围**：字号 10~100（`Ctrl+=/-`）、行间距 1.0 起（上限按字号动态算，Monaco lineHeight ≤150px，`Ctrl+[/]`）、字间距 -5~20px（`Ctrl+Shift+[/]`）、段间距（`Ctrl+;/'`）、左右边距 0~160px（`Ctrl+Shift+,/.`）

### 14.5 主题

内置明亮/暗黑两种（`vs`/`vs-dark`），F2 切换。三处同步：应用外壳（class dark + colorScheme）、Monaco 主题、原生标题栏/滚动条（`setNativeTheme`）；多窗经 storage 事件同步；配色变更 deep watch 同步 CSS 变量。

### 14.6 快捷键体系（38 个可自定义命令）

`shortcutRegistry.ts:70-274` 定义全部命令，`ShortcutPanel.vue` 可视化录制 + 实时冲突检测（同 accelerator 报「已被占用」）：

| 类别 | 命令（默认键） |
|---|---|
| 文件 | 打开 `Ctrl+O` / 选目录 `Ctrl+Shift+O` |
| 滚动 | 上/下 `Up/Down` / 上下屏 `PageUp/Down` / 上下章 `Ctrl+←/→` |
| 排版 | 字号 `Ctrl+=/-` / 行距 `Ctrl+[/]` / 字距 `Ctrl+Shift+[/]` / 段距 `Ctrl+;/'` / 边距 `Ctrl+Shift+,/.` |
| 侧栏 | 搜索 `Ctrl+Shift+F` / 文件 `Ctrl+Shift+E` / 章节 `Ctrl+Shift+C` / AI `Ctrl+Shift+A` / 显隐 `Ctrl+B` |
| 功能 | 查找 `Ctrl+F` / 编辑 `Ctrl+/` / 编辑选中 `Ctrl+E` / 章节规则 `Ctrl+R` / 书签 `Ctrl+D` |
| 视图 | 极简 `F10` / 全屏 `F11` / 主题 `F2` / 设置 `F5` / 配色 `F6` / 找书 `F7` / 书源 `F8` / 摸鱼 `F9` |
| 窗口 | 新窗口 `Ctrl+Shift+N` |
| **全局** | 显示/隐藏阅读器 `Ctrl+`` （老板键，唯一全局键，Electron globalShortcut） |

- Mac 用 Command 替代 Control；修饰键顺序固定 Control > Command > Alt > Shift
- 物理键位解析优先 `ev.code`（防 IME/全角污染 `ev.key`）
- 录制时临时注销全局热键；弹窗/模态打开时快捷键被 `hasDismissibleOverlay` 拦截


---

## 十五、数据与同步

### 15.1 四层存储架构

```
层1 渲染进程 localStorage（多窗同源共享，storage 事件跨窗同步）
   colorTxt.ui.settings / file.list / file.meta / recent.files / session
   colortxt:voiceReadSpeak / stealth.settings / findBook.settings / replaceRules
层2 主进程 userData JSON
   window-bounds.json（窗口位置）/ ai/data/config.json（AI 配置，不含密钥）
   ai/secrets.v1.json（密钥保险库，AES 加密）/ ConvertedTxt/（电子书转换缓存）
   UnpackedBooks/（书包解压）/ CharacterPortrait/（立绘）/ reader-backgrounds/（背景图）
   dictionaries/（导入词库）
层3 SQLite（better-sqlite3）
   ai/data/vector.sqlite（向量索引+AI对话）/ segment.sqlite（词云分词缓存）
   book-sources.db（书源/登录/Cookie）
层4 模型缓存
   ai/model-cache/transformers-cache/（内置嵌入模型权重）
```

**密钥保险库**（`main/secretStorage.ts`）：密钥与配置分离（config.json 无明文 Key）；写入经**串行队列 + tmp→rename 原子落盘**（防关窗/并发写损坏整文件）；分槽存储（对话方案/文生图方案/朗读方案/翻译/WebDAV 密码——后者用 Electron safeStorage）；启动 hydrate 灌回内存，旧槽一次性迁移后删除；**关窗落盘不写保险库**。

**落盘纪律**（详见姊妹篇第六章）：滚动每帧只原地改内存 meta 不写盘；meta 写盘统一防抖合并；gated（受进度门控）/ forced（关窗前取消防抖落尽）两级；写盘前先读磁盘合并（防多窗互踩）；关窗不整份回写 ui.settings。

### 15.2 彩读书包（.ctz / .ctzx）

**用户视角**：把当前书连同全部阅读数据打包分享/跨设备同步。`.ctz` 普通压缩包 / `.ctzx` 加密包（设密码）。

**包结构**：

```
{文件名}.ctz|ctzx/
  characters/manifest.json + portraits/{角色}.png   ← 角色卡与立绘
  content/{文件名}.txt|md + {文件名}.Images/        ← 正文与插图
  bookmarks.json / highlights.json / notes.json     ← 书签/高亮/笔记
  manifest.json                                     ← 配置（含进度锚点 viewportTopPhysicalLine）
```

**加密**：整包 ZIP DEFLATE 压缩后 AES-256-GCM 加密，PBKDF2-SHA256 派生密钥（**210,000 次迭代**），文件头 `[CTZE(4B)][Version(1B)][Salt(16B)][IV(12B)][密文+Tag]`。密码只存用户脑中，包内无密码本。

**导入匹配**（`readerBookPackImport.ts:302`）：当前打开文件 > 最近打开同名 > 文件列表同名 > 都没有则解压到 UnpackedBooks；正文不同弹覆盖确认（电子书只覆盖转换 md 不动本体）；meta 合并策略——书签/高亮/笔记合并且去重、角色同名以导入侧为准（保留本地 id）、进度仅显式要求时覆盖。

**安全**：manifest 中 contentFileName/imagesDirName 校验不含路径穿越；立绘排除 `_tmp`、`_char_draft_` 前缀。

### 15.3 WebDAV 同步

**三个独立场景**：

| 场景 | 内容 | 策略 |
|---|---|---|
| 主界面（侧栏 WebDAV 面板） | settings.json + replaceRules.json + 背景图 | 全量覆盖；**上传前剥离语音 API 密钥**；背景图按文件名+大小增量、清理远端孤儿 |
| 书包（底栏文件路径菜单） | 当前书带进度的书包（可加密） | 全量上传 `Books/`；可从远端列表过滤/排序/下载导入；「同步」= 下载合并更新当前书 |
| 找书窗（顶栏 WebDAV 菜单） | 书架 / 书源 / 设置 | **书架一书一文件**（content hash 增量 + 删远端孤儿，下载保留本地独有）；**书源合并导入**（新增+更新，不删本地多出）；设置全量 |

**远端目录**：`ColorTxt/{Main, Books, FindBook}`，remoteDir 名可改。认证仅 Basic Auth，密码经 safeStorage 存保险库；测试连接时临时密码优先。

**客户端**（`main/webdav/webDavClient.ts`）：PROPFIND/MKCOL/PUT/GET/DELETE 标准操作；流式传输带进度回调和 AbortController 中止（中止删半成品）；**坚果云兼容三重兜底**（已存在目录返回 400 而非 405：探测/父目录列表/PUT 占位文件触发建目录）；默认超时 45s，大文件不限时。

### 15.4 清除阅读数据与清除缓存

**清除阅读数据**（按路径，设置→常规→数据管理）：删该书的进度/书签/高亮/笔记/角色卡（含立绘目录）/AI 对话/向量索引/分词缓存，移出最近打开；**不删**文件本身、文件列表、收藏高亮词、界面设置。直接覆盖写盘不走合并；他窗以磁盘为准重载。

**清除缓存**（7 步流程）：

```
1. sessionStorage 设 skipUnloadPersistence 防回写标记
2. 删全部 AI 对话（threads/messages）
3. 删全部向量索引与分词缓存
4. 删角色立绘缓存根目录
5. 从 ui.settings 去掉收藏高亮词
6. localStorage.clear() → 写回处理后的 settings
7. reload
```

**防回写机制**（关键设计）：`localStorage.clear()` 后直接 reload，卸载事件仍会执行把清掉前的内存状态原样写回——「清不干净」。解法：clear 前设 sessionStorage 标记 → 卸载钩子检测到即 return → reload 后新页开头清除标记。sessionStorage（每窗独立、不跨页存活）恰如其分。

**不会清除**：电子书转换 .md 缓存、书包解压目录、找书下载目录、密钥保险库、AI 配置、界面设置（除收藏高亮词）。

**底栏菜单**：清除阅读数据（danger 确认）；「重新转换」（仅电子书）：忽略缓存强制重跑转换。

### 15.5 旧版数据迁移

- AI 数据布局：旧版 `userData/ai/config.json` / 旧 vector.sqlite 自动迁入 `ai/data/`；`data-cache-root.json` 记录当前生效缓存路径；改缓存目录时关连接后合并迁移
- 高亮词：旧版扁平 `string[]` 迁成单词组 `[词]`
- 配色方案：旧版配色覆盖迁完写回删旧键
- API 密钥：旧单密钥槽启动时迁入 profile 映射后删除

---

## 十六、多窗口与系统集成

### 16.1 七种窗口

| 窗口 | 标记 | 特点 |
|---|---|---|
| 主阅读窗 | Map 排除法 | `show:false`→ready-to-show 防白屏；bounds 持久化（resize 300ms 防抖） |
| 找书窗 | `findBookWindowByWindowId` | 同一 windowFactory 不同页面 |
| 摸鱼阅读窗 | `__colortxtStealthReader` | 透明/置顶/focusable:false |
| 摸鱼设置窗 | `__colortxtStealthSettings` | 故意不设 parent |
| 取色覆盖层 | `__colortxtEyedropper` | 每屏一窗贴冻结截图 |
| 书源后台 webView | `__colortxtBackstageWebView` | show:false/sandbox/无 preload，一窗即抛 |
| 登录验证窗 | activeWindows Map | 主窗体 + footer 双 BrowserView |

已知架构脆弱点：隐藏窗识别靠挂私有属性 + `getAllWindows()` 排除法，该过滤器在 5 处重复（新增窗口类型必须同步维护）。

### 16.2 多主窗行为

- 会话恢复：只有第一个干净主窗有资格（无其它主窗 + 无 openTxtPath + 非找书窗，三条件）
- 外部双击 txt：发给最近获焦点的主窗；无主窗才新建
- 各窗各读各的书；共享同一份 localStorage——防覆盖三原则（写时合并/读时让权/活跃文件特权）
- 关窗握手：主进程 preventDefault → 渲染层确认未保存编辑 → `allowNextClose` 二次 close 放行（保证确认框、pagehide 落盘、quit 不死锁）

### 16.3 自动更新

- electron-updater：`autoDownload:false`（用户确认才下载）+ `autoInstallOnAppQuit:true`（稍后也会在退出时装）
- 五态模态流：检查中 → 发现新版本（下载/打开下载页）→ 下载中（进度条）→ 就绪（退出并安装）→ 信息提示
- 平台分流：macOS 与 Windows 便携版无应用内更新，引导 GitHub Releases 页
- 错误翻译（`updaterMessages.ts`）：28 个 electron-updater 错误码 + 7 个 Node 网络/TLS 错误码译为中文（如签名不一致已中止、差分更新失败将完整下载），主进程统一翻译后广播

### 16.4 文件关联与命令行

- 资源管理器双击 .txt/.md/.ctz：未运行 → 冷启动带路径（渲染层 pull）；运行中 → 单实例锁路由 → 聚焦最近主窗 → `app:open-txt-path` 推送（preload 有队列+回调集合防丢）
- `--find-book` 参数直接开找书窗不开主窗
- 外部链接一律系统浏览器打开（`webContentsExternalLinks.ts`）

### 16.5 打包与分发

- 构建链：electron-vite → electron-rebuild（原生模块）→ prune-pack-deps.mjs 裁剪 → electron-builder
- node_modules 裁剪：移除 onnxruntime-web/完整 sharp/孤儿依赖；按平台移除非目标原生包；按路径裁 src/*.map/README
- asarUnpack：better-sqlite3 / sqlite-vec / onnxruntime-node/bin / opencc / @node-rs/jieba
- CI 五 job 并行：Win x64（NSIS+Portable）/ macOS arm64+x64（DMG，Intel 用原生 Runner 校验 Mach-O）/ Linux arm64+x64（AppImage 静态 runtime）
- 分发翻车史：macOS 交叉编译缺 darwin-x64 原生包 → 原生构建；AppImage 缺 FUSE2 → 静态 runtime；NSIS 清空安装丢数据 → 覆盖安装

---

## 附录：功能 → 关键文件速查表

| 功能 | 关键文件（相对 src/） |
|---|---|
| 内容上色 | renderer/monaco/txtrTextMonarch.ts |
| 高亮词 | renderer/monaco/txtrHighlightMonarch.ts、utils/highlightWords.ts |
| 中文换行 | renderer/monaco/cjkWrapOptimize.ts |
| 段间距 | renderer/monaco/lineSpacing.ts |
| 粘性标题 | renderer/monaco/chapterStickyScroll.ts |
| 流式读取 | main/ipcHandlers.ts、renderer/services/physicalLineStream.ts |
| 格式化管线 | renderer/reader/readerDisplayPipeline.ts |
| 视口锚点 | renderer/reader/readerViewportAnchor.ts |
| 电子书转换 | renderer/ebook/convert/、utils（ensureEbookMarkdown） |
| 章节识别 | shared/chapterMatchBuiltinPatterns.ts、reader/chapterIndex.ts |
| 书签 | composables/useAppBookmarkPins.ts、utils/readerBookmarkExport.ts |
| 划线笔记 | composables/useReaderAnnotations.ts、reader/readerAnnotationDecor.ts |
| 全文搜索 | composables/useAppSidebarSearch.ts、components/SearchPanel.vue |
| 阅读尺 | renderer/reader/readingRuler.ts |
| 定时滚动 | composables/useAppTimedScroll.ts |
| 番茄时钟 | composables/usePomodoroTimer.ts、components/PomodoroBreakOverlay.vue |
| 点击模式 | composables/useReaderClickModeAltHold.ts |
| 全屏/极简 | composables/useAppReaderChrome.ts、useAppFullscreenReaderLayout.ts |
| 编辑模式 | components/ReaderPartialEditPanel.vue、monaco/readerReadOnlyImeGuard.ts |
| AI 智能排版 | shared/aiSmartFormatTypes.ts、main/ai/chat/textFormatCleanup.ts、composables/useAiSmartFormat.ts |
| TTS | main/voiceRead/（providerRegistry + providers）、voiceReadEdgeTts.ts |
| 说话人识别 | main/ai/voiceReadSpeaker.ts |
| 词典 | main/dictionary/（5 Reader + networkProviders + importBundles） |
| 翻译 | main/translation/、shared/translationChunk.ts、translationIndent.ts |
| 网络搜索 | shared/webSearchTypes.ts、components/WebSearchManageModal.vue |
| Agent 循环 | main/ai/chat/agentChat.ts、agentTools.ts |
| 向量库 | main/ai/rag/vectorDb.ts、renderer/ai/buildBookVectorIndex.ts |
| 分块 | renderer/utils/aiChunkBook.ts |
| 技能 | shared/aiSkills.ts |
| 思维导图 | main/ai/tools/mindmapTool.ts、shared/aiMindmapIntent.ts |
| 词云 | main/ai/tools/wordcloudTool.ts、rag/segmentCache.ts |
| AI 高亮词检索 | composables/useHighlightAiSearch.ts |
| 角色卡 | shared/characterTypes.ts、main/ai/tools/characterPortrait.ts |
| 3D 卡片 | utils/characterCardSpring.ts、composables/useCharacterCardTilt.ts |
| 书包 | utils/readerBookPack.ts、readerBookPackCrypto.ts、readerBookPackImport.ts |
| 书源引擎 | main/bookSource/engine/（AnalyzeRule/AnalyzeUrl）、store/ |
| 摸鱼 | main/stealthReader.ts、utils/stealthPaginate.ts |
| 配色方案 | shared + components/ColorScheme*、composables/useColorSchemePresetDraft.ts |
| 背景图 | shared/readerBackground.ts、main/readerBackgroundIpc.ts |
| 取色 | main/eyedropper.ts、components/HexColorPickerField.vue |
| 字体 | shared/presetFontDefinitions.ts、main/terminalFont.ts |
| 快捷键 | renderer/services/shortcutRegistry.ts、main/globalShortcuts.ts |
| 持久化 | composables/useAppPersistence.ts、stores/fileMetaStore.ts |
| 密钥保险库 | main/secretStorage.ts |
| WebDAV | main/webdav/、renderer/utils/webDav*Sync.ts |
| 清除数据 | App.vue（clearReadingDataForPaths / 清缓存 7 步） |
| 自动更新 | main/updater.ts、updaterMessages.ts、components/AppUpdateFlow.vue |
| 窗口管理 | main/windowFactory.ts、windowCloseGuard.ts、stealthReader.ts |

---

## 结语：功能背后的四条工程纪律

把 30+ 个功能全部展开后，能清晰看到贯穿始终的纪律：

1. **单一事实源 + 映射层**：磁盘物理行是唯一真相，上色/压缩/替换/简繁/缩进全是可重放的展示层映射——所以格式化参数随便改、书签笔记进度永不失效、书包里的 `viewportTopPhysicalLine` 跨设备通用。
2. **门闸优先**：进度门闸（加载中不许写进度）、quit 门闸（防退出死锁）、防回写标记（清缓存清得干净）——宁可晚写、宁可重算，不可写错。
3. **诚实面对无解**：Monaco #5311 挂 WARNING、书源引擎公告「做不到 100% 复刻」、旧数据不兼容明说「请重新转换」。
4. **补丁不打洞**：对 Monaco 的定制全部集中在构建 transform / 注册回调 / 注入层；对 Windows 的坑用 Windows 的招且全部注释「为什么」——setShape、screen-saver 层级、周期兜底重申，都成为后来者的路标。

> 本文基于 v3.8.11 源码（commit 9565e4d）整理。动态流程（启动/打开/恢复/关闭的完整时间轴）与版本演进叙事见两份姊妹篇。

