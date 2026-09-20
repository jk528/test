# ColorTxt 导出缓存功能开发全过程

> **文档用途**：记录给 ColorTxt（彩读）找书模块新增「导出已缓存章节为 TXT」功能（书架菜单 + 详情页按钮 + Ctrl+E 快捷键）的完整设计、实现与调试过程。
> **当前状态（2026-09-21）**：该功能已随「找书模块恢复为 GitHub 官方原版」一并**移除**，官方原版不存在此功能。本文档作为存档与重做依据。
> **项目路径**：`c:\Users\Administrator\Documents\这是什么\JK-temp\彩读分析\.temp\ColorTxt`

---

## 一、背景与需求

### 1.1 官方原有能力

官方只有一个「整书下载」功能（详情页「下载」按钮）：

```
联网解析目录 → 逐章联网拉取正文（边拉边写入本地缓存）→ 全部拉完 → 从缓存拼出一个完整 TXT
```

特点：必须**联网把所有章节拉完**才能得到 TXT；不能只导出本地已有的缓存。

### 1.2 新增需求

用户在书架里阅读书籍时，正文会自动缓存到本地。希望有一种方式：

| 需求点 | 说明 |
|---|---|
| 纯离线导出 | 只读本地缓存章节拼成 TXT，**绝不联网拉正文** |
| 缺章自动跳过 | 未缓存（含空文件）的章节直接跳过，不写占位内容 |
| 书源可能已删除 | 已在书架的书，即使书源后来被删，只要有目录缓存也能导出 |
| 排版一致 | 导出的 TXT 排版与官方整书下载完全一致（书名/作者/简介头 + 两格全角缩进） |
| 两个入口 + 快捷键 | ① 书架行「⋯」菜单；② 详情页底部按钮；③ 详情页 Ctrl+E |

---

## 二、章节缓存存储结构（开发前必须搞清）

导出的本质就是按目录把缓存文件读出来拼接，所以先确认缓存的磁盘结构。辅助函数位于 [src/main/bookSource/engine/chapterCache.ts](./.temp/ColorTxt/src/main/bookSource/engine/chapterCache.ts)。

### 2.1 目录与文件命名规则

```
{userData}/book_cache/
└── {书名前9字}{bookUrl的MD5第8~24位}/        ← 一本书一个文件夹
    ├── {chapterUrl的MD5第8~24位}.nb          ← 一章一个文件（UTF-8 纯文本）
    └── …
```

命名算法：

```ts
const FILE_NAME_INVALID = /[\\/:*?"<>|.]/g;

function md5Encode16(s: string): string {
  return createHash("md5").update(String(s), "utf8").digest("hex").slice(8, 24);
}

/** 书的缓存文件夹名：书名去掉非法字符后取前 9 字 + bookUrl 的 16 位 MD5 片段 */
export function bookCacheFolderName(bookName: string, bookUrl: string): string {
  const cleaned = (bookName || "").replace(FILE_NAME_INVALID, "");
  return `${cleaned.slice(0, Math.min(9, cleaned.length))}${md5Encode16(bookUrl)}`;
}

/** 章的缓存文件名：chapterUrl 的 16 位 MD5 片段 + .nb */
export function chapterCacheFileName(chapterUrl: string): string {
  return `${md5Encode16(chapterUrl)}.nb`;
}
```

### 2.2 命名设计要点

- 用 **URL 的 MD5** 而非章节下标做文件名：目录数组顺序可能变化（最新在前/阅读顺序），URL 哈希稳定；
- MD5 只取 `hex.slice(8,24)` 共 16 位，文件名短且碰撞概率可忽略；
- 书名清洗字符集 `\\/:*?"<>|.` 与 Windows 非法文件名字符一致（含点号）；
- 缓存根目录默认 `{userData}/book_cache`，可被设置里的自定义缓存目录覆盖。

### 2.3 本机实测数据（开发时）

| 书 | 缓存文件夹 | 缓存文件数 |
|---|---|---|
| 红楼梦（120 回） | 红楼梦8e2b38f395428ed0 | 120 |
| 应许之地（23 章） | 应许之地5fd9f45f28342728 | 23 |

> 注意 `book_cache` 下可能存在同一本书的**多个历史缓存文件夹**（目录 URL 变过就会生成新的），开发时通过 leveldb 书架数据反查，确认当前书架条目实际对应的是哪一个。

---

## 三、实现全过程（共 6 步）

### 步骤 1：定义请求/响应类型

在 `src/shared/bookSource/types.ts` 新增：

```ts
/** 导出已缓存章节请求 */
export interface BookSourceExportCachedRequest {
  bookSourceUrl: string;          // 书源 URL（origin）
  bookUrl: string;                // 书籍详情页 URL
  name: string;
  author: string;
  intro?: string;
  outputDir: string;              // 用户选择的导出目录
  chapters?: BookChapter[];       // 书架/详情页已有的目录；有则全程离线
  cacheDir?: string;              // 自定义缓存目录；空则用默认 userData/book_cache
}

/** 导出结果 */
export interface BookSourceExportCachedResult {
  filePath: string;               // 生成的 TXT 完整路径
  exportedChapters: number;       // 实际导出章数
  totalChapters: number;          // 目录总章数
}
```

### 步骤 2：定义 IPC 通道

在 `src/shared/bookSource/ipc.ts`：

```ts
export const BOOK_SOURCE_IPC = {
  // …
  exportCachedBook: "bookSource:exportCachedBook",
};

export interface BookSourceIpcApi {
  // …
  bookSourceExportCachedBook: (
    req: BookSourceExportCachedRequest,
  ) => Promise<
    { ok: true } & BookSourceExportCachedResult |
    { ok: false; message: string }
  >;
}
```

### 步骤 3：实现主进程导出逻辑（核心新文件）

新建 `src/main/bookSource/exportCachedBook.ts`，导出 `exportCachedBook(req)`。

**整体流程**：

```
① 确定目录 chapters
   ├─ req.chapters 非空 → 直接用，完全离线，不查书源（书源已删也不怕）
   └─ req.chapters 为空 → 需书源联网只取一次目录（正文仍只读缓存）
② contentChaptersInReadingOrder() 过滤分卷、按阅读顺序（第一章起）排好
③ 一次 readdir 列出该书缓存文件夹的全部文件名
④ 逐章算 chapterCacheFileName(url)，命中的才加入读取任务
⑤ 8 路并发读 .nb 文件，读完按章节下标归位
⑥ 按目录顺序拼接：信息头 + Σ(章节标题 + 正文)，空缓存章跳过
⑦ 一次写入 outputDir/{书名}作者：{作者}.txt
```

关键实现要点：

```ts
const READ_CONCURRENCY = 8;

// ① 离线路径：有目录缓存就完全不检查书源
if (req.chapters?.length) {
  chapters = req.chapters;
} else {
  const source = getBookSource(req.bookSourceUrl);
  if (!source) throw new Error("书源不存在");
  // …仅联网取目录
}

// ③ 缓存文件夹读不到直接给明确错误
try {
  fileNames = new Set(await readdir(cacheBookDir));
} catch {
  throw new Error("没有已缓存的章节可导出");
}

// ⑤ 分批并发读，单个文件失败只置 null，不影响其他章
let cursor = 0;
async function worker() {
  while (cursor < tasks.length) {
    const task = tasks[cursor++]!;
    try {
      texts[task.index] = await readFile(`${cacheBookDir}/${task.file}`, "utf8");
    } catch {
      texts[task.index] = null;
    }
  }
}
await Promise.all(
  Array.from({ length: Math.min(READ_CONCURRENCY, tasks.length) }, () => worker()),
);

// ⑥ 空文本章跳过；标题缺失时用「第N章」兜底
if (text == null || !text.trim()) continue;
parts.push(`\n\n${heading}\n\n${formatExportParagraphs(text)}`);
```

**三条固定错误文案**（用户看到的 toast 即来源于此）：

| 抛出时机 | 文案 |
|---|---|
| 书源不存在且未带目录 | 书源不存在 |
| 目录过滤后没有正文章 | 没有可导出的章节 |
| 缓存文件夹不存在 / 一章都没拼出来 | 没有已缓存的章节可导出 |

### 步骤 4：注册 IPC handler + preload 暴露

`src/main/bookSource/registerBookSourceIpc.ts`：

```ts
ipcMain.handle(BOOK_SOURCE_IPC.exportCachedBook, async (_e, req: unknown) => {
  try {
    const result = await exportCachedBook(req as BookSourceExportCachedRequest);
    return { ok: true, ...result };
  } catch (e) {
    // 关键：把真实错误 message 返回给渲染层，而不是笼统的"失败请重试"
    return { ok: false, message: e instanceof Error ? e.message : String(e) };
  }
});
```

`src/preload/index.ts`：

```ts
bookSourceExportCachedBook: (req) =>
  ipcRenderer.invoke(BOOK_SOURCE_IPC.exportCachedBook, req),
```

### 步骤 5：复用整书下载的排版函数

为保证导出 TXT 与官方下载观感一致，在 `src/main/bookSource/downloadService.ts` 中把原本内部使用的 4 个辅助函数导出，供导出逻辑复用：

| 函数 | 作用 |
|---|---|
| `buildDownloadFileHeader(name, author, intro)` | 文件头：书名 / 作者：xx / 简介：…（简介也做两格缩进） |
| `buildDownloadFileBaseName(name, author)` | 文件名：`《书名》作者：作者`（过非法文件名字符清洗） |
| `formatExportParagraphs(text)` | 正文排版：统一换行、去每段首尾空白（含全角空格）、每段前加两个全角空格「　　」 |
| `writeDownloadFile(dir, baseName, text)` | `mkdir -p` 后写入 `{baseName}.txt`，同名直接覆盖 |

### 步骤 6：两个 UI 入口与快捷键

#### 6.1 书架行菜单 —— FindBookshelfPanel.vue

- 书架行「⋯」菜单第一项加「导出缓存为TXT」按钮，导出中显示「正在导出…」并禁用；
- 处理函数 `onRowMenuExportCached()`：
  - 弹系统目录选择框（`showOpenDialog`，属性 `openDirectory, createDirectory`）；
  - 缓存/下载目录用 `useFindBookSettings()` 的 `effectiveCacheDir / effectiveDownloadDir`；
  - 调用 `window.colorTxt.bookSourceExportCachedBook()`，按 `res.ok` 弹成功/警告 toast。

#### 6.2 详情页底部按钮 —— BookDetailPanel.vue

- 底部按钮区「阅读」与「下载」之间新增「导出缓存」按钮（`icons.export` 图标）；
- `title="导出已缓存章节为 TXT（Ctrl+E）"`，导出中按钮显示「导出中…」并禁用；
- 按钮容器加 `flex-wrap: wrap`，防止窄窗口时按钮被挤出可视区（用户一开始找不到按钮就是此原因）；
- 处理函数 `onExportCached()`：详情页已加载完整目录，把 `chapters.value` 连同请求一起传，主进程走完全离线路径；
- 结果提示：成功 `已导出 x/y 章`，失败显示 `res.message` 真实文案。

#### 6.3 详情页快捷键

```ts
function onDetailKeydown(e: KeyboardEvent) {
  if (!modelValue.value) return;
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey
      && e.key.toLowerCase() === "e") {
    e.preventDefault();
    void onExportCached();          // Ctrl/Cmd + E 导出
    return;
  }
  if (e.key === "Escape") {
    e.preventDefault();
    onBack();                       // Esc 返回书架
  }
}

// 必须在 document 捕获阶段监听，才能抢在 Monaco/其他控件之前
onMounted(() => document.addEventListener("keydown", onDetailKeydown, true));
onBeforeUnmount(() => document.removeEventListener("keydown", onDetailKeydown, true));
```

---

## 四、涉及文件总清单

| # | 文件 | 改动类型 | 作用 |
|---|---|---|---|
| 1 | src/shared/bookSource/types.ts | 修改 | 请求/结果类型 |
| 2 | src/shared/bookSource/ipc.ts | 修改 | IPC 通道与 API 类型 |
| 3 | src/main/bookSource/exportCachedBook.ts | **新增** | 导出核心逻辑 |
| 4 | src/main/bookSource/registerBookSourceIpc.ts | 修改 | 注册 handler |
| 5 | src/main/bookSource/downloadService.ts | 修改 | 导出 4 个排版辅助函数复用 |
| 6 | src/preload/index.ts | 修改 | 暴露 bookSourceExportCachedBook |
| 7 | src/renderer/src/bookSource/components/FindBookshelfPanel.vue | 修改 | 书架行菜单入口 |
| 8 | src/renderer/src/bookSource/components/BookDetailPanel.vue | 修改 | 详情页按钮 + Ctrl+E/Esc 快捷键 |

> 以上 8 项在 2026-09-21 恢复找书模块时全部回退/删除，当前工作区已无此功能。

---

## 五、调试过程与报错分析（如实记录）

### 5.1 已定位并修复的问题

| 阶段 | 现象 | 根因 | 修复 |
|---|---|---|---|
| 第一版 | 点导出提示笼统的「失败请重试」 | 当时运行的是**旧 Electron 实例**，没有新 IPC 接口；且离线导出分支错误地要求书源必须存在 | 重启应用加载新 preload/主进程；移除有目录时的书源检查；handler 返回真实 `message` |
| 第二版 | 详情页找不到导出按钮 | 找书窗口偏窄，底部 5 个按钮（书架/分类/阅读/导出/下载）把导出按钮挤出可视区 | 按钮容器加 `flex-wrap: wrap`，窄时自动换行 |
| 排查阶段 | 需要确认书架目录与缓存是否匹配 | better-sqlite3 只能在 Electron 内运行（ABI 不匹配普通 Node） | 用 classic-level 读 localStorage leveldb 副本，脚本化核对章节 URL 哈希与磁盘 .nb 文件 |

### 5.2 缓存命中实测结论

用 leveldb 书架数据（key：`colortxt:findBookBookshelf`，值为「1 字节前缀 + UTF-16LE」）解析后脚本核对：

- 红楼梦：书架目录 120 章，缓存文件命中 **120/120**；
- 应许之地：书架目录 23 章，缓存命中 **23/23**。

且详情页目录每一行都显示缓存对勾 ✓（缓存标记与导出共用同一套 MD5 命名），**证明「缓存找不到」不是报错原因**。

### 5.3 最终报错未定论（诚实说明）

在恢复原版之前，用户最后一次点击导出看到的**具体提示文案未取得**：

- 静态分析与磁盘证据均表明目录、缓存、命名全部正确；
- 推测若仍报错，只可能发生在最后的**文件写入阶段**（如所选目录权限、杀软占用、路径问题），但未来得及加日志复现即应用户要求恢复了原版；
- 教训：此类问题应第一时间在主进程关键节点（取目录/readdir/读取/拼接/写入）打 `console.log`，重启后复现一次即可从日志定位，而不是靠静态推测。

---

## 六、重做指引（后期需要时）

### 6.1 快速重做顺序

1. 按「三、实现全过程」步骤 1～6 依次改，顺序不要乱（类型 → IPC → 主进程 → handler/preload → 排版复用 → UI）；
2. 每完成一步执行 `npm run typecheck`；
3. 因为改了**主进程 + preload**，必须完全停掉 `npm run dev`（确认任务管理器无残留 electron 进程）再重新启动；
4. 打开找书窗口（F7）→ 书架点蓝色书名进详情页 → 测 Ctrl+E、Esc、底部按钮、行菜单四个路径。

### 6.2 重做时建议直接加上诊断日志

在 `exportCachedBook()` 各节点输出：

```ts
console.log("[exportCached] 目录章数:", chapters.length);
console.log("[exportCached] 缓存目录:", cacheBookDir, "文件数:", fileNames.size);
console.log("[exportCached] 待读任务:", tasks.length);
console.log("[exportCached] 实际拼出章数:", exportedChapters);
console.log("[exportCached] 写入路径:", filePath);
```

日志随 `npm run dev` 的后台输出文件查看，验证完再删。

### 6.3 相关数据位置速查

| 数据 | 路径 |
|---|---|
| userData 根目录 | C:\Users\Administrator\AppData\Roaming\colortxt |
| 章节缓存 | C:\Users\Administrator\AppData\Roaming\colortxt\book_cache |
| 书源库（SQLite） | C:\Users\Administrator\AppData\Roaming\colortxt\book-sources.db |
| 书架数据（localStorage） | …\colortxt\Local Storage\leveldb（key 含 findBookBookshelf） |
| leveldb 只读排查脚本目录 | C:\Users\Administrator\AppData\Local\Temp\lvread |
| 书源备份（1255 个） | 桌面\colortxt书源备份_20260921_060133.json |

---

## 七、注意事项汇总

1. **改主进程/preload 必须彻底重启**，否则渲染层调用旧接口必然失败——这是本功能第一次报错的根因；
2. **离线路径不得依赖书源**：书架书的源可能已被删除，有 `chapters` 时跳过一切书源检查；
3. **并发读取要容错**：单个缓存文件读失败只跳过该章，不能让整个导出 reject；
4. **空文本判定用 `trim()`**：存在 0 字节或纯空白的损坏缓存文件；
5. **快捷键监听用捕获阶段**：`addEventListener(..., true)` 挂在 document，否则 Monaco 等控件先吞掉按键；
6. **错误信息必须透传真实文案**：handler catch 后返回 `e.message`，不要给笼统提示，否则无法排查；
7. **leveldb 被运行中应用锁定**：排查时先复制数据库副本再用 classic-level 打开；
8. **better-sqlite3 不能用普通 Node 调**（Electron ABI 与 Node ABI 不一致），书源库排查要在 Electron 内或换纯 JS 方案。
