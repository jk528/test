# ColorTxt 离线缓存存在的问题与改善方案

> **文档用途**：系统梳理 ColorTxt（彩读）找书模块「离线缓存」与「整书下载」两条链路在实际使用中暴露的问题，逐条给出代码级证据与分级改善方案，作为后续改造的依据。
> **项目路径**：`c:\Users\Administrator\Documents\这是什么\JK-temp\阅读器项目\彩读分析\.temp\ColorTxt`
> **整理日期**：2026-09-21
> **关联文档**：[ColorTxt导出缓存功能开发全过程.md](./ColorTxt导出缓存功能开发全过程.md)、[ColorTxt字体下载与设置全过程.md](./ColorTxt字体下载与设置全过程.md)

---

## 一、背景：两条容易混淆的链路

应用里与"离线"相关的功能有两个，入口、参数和产物完全不同：

| 对比项 | 离线缓存 | 整书下载 |
|---|---|---|
| 入口 | 找书阅读器内的「离线缓存」按钮 | 书籍详情页底部「下载」按钮 |
| 请求参数 | `cacheOnly: true`，`outputDir: ""` | 不带 cacheOnly，带用户选择的导出目录 |
| 主进程行为 | 缺章联网拉取 → 写入 book_cache → **直接结束，跳过导出** | 先缓存全部章节 → 再读缓存拼 TXT → 写入磁盘 |
| 关键代码 | downloadService.ts L186-L194 | downloadService.ts L196-L237 |
| 产物 | 仅 book_cache 下的 .nb 缓存文件 | 一个完整 .txt + 缓存文件 |
| 完成事件 | `done`，`filePath` 为空字符串 | `done`，`filePath` 为真实文件路径 |

**核心事实**：「离线缓存」跑完后硬盘上没有 TXT 是**代码的既定行为，不是 Bug**；但完成提示「已完成离线缓存」让用户以为"导出成功"，这是体验问题（详见问题 P1）。

---

## 二、缓存机制速览

```
{userData}/book_cache/
└── {书名前9字}{bookUrl的MD5第8~24位}/     ← 一本书一个文件夹
    └── {chapterUrl的MD5第8~24位}.nb       ← 一章一个文件，UTF-8 明文（非加密）
```

- 命名辅助函数：src/main/bookSource/engine/chapterCache.ts（`bookCacheDir`、`chapterCacheFileName`、`readChapterCache`、`saveChapterCache`）；
- 缓存根目录默认 `{userData}/book_cache`，可被设置里的自定义缓存目录覆盖；
- 现有缓存管理能力**只有"清除"**：单本清除（详情页/阅读器菜单）与全部清除（设置 → 下载），没有占用查看、缺章明细、孤儿目录识别。

---

## 三、存在的问题（共 9 项）

### P1. 「假完成」：完成事件不核对真实缓存数

**现象**：点离线缓存，进度条走完，提示「已完成离线缓存」，但实际可能一章都没缓存成功。

**代码证据**：downloadService.ts L132-L174 的循环无论每章成败都会走完；L186-L194 无条件发出 `done` 事件，事件里**只有书名，没有成功/失败计数**。`BookSourceDownloadDoneEvent` 本身也不携带统计字段。

**影响**：提示与实际状态不一致，用户基于"已完成"去离线阅读或找文件时才发现问题。

### P2. 单章失败被静默吞掉

**代码证据**：L161-L165

```ts
} catch (e) {
  // 单章失败不中断；导出处写占位
  const msg = e instanceof Error ? e.message : String(e);
  logs.push(`缓存章节失败 [${ch.title}]: ${msg}`);
}
```

失败信息只进运行日志；紧接着 L166-L173 仍发出 `current: i + 1` 的进度事件，进度条照常前进。用户不主动打开「日志」无法感知缺章。

### P3. 整书下载：残缺内容也算"导出成功"

**代码证据**：L210-L213，未缓存到的章节在 TXT 中写成占位行：

```ts
const body =
  cached != null && cached.length
    ? formatExportParagraphs(cached)
    : `${EXPORT_PARAGRAPH_INDENT}[下载失败: 章节未缓存]`;
```

文件照常生成、照常发 `done` 并提示成功。用户得到的是一本夹着占位文字的残缺书——"提示导出了，实际等于没导出"。

### P4. 空/损坏缓存的判定不严格

**代码证据**：L211 判定条件是 `cached != null && cached.length`：

- 空字符串（0 字节损坏文件）能被拦住，走占位；
- 但**纯空白/纯全角空格的文件**（如 `"　　 \n"`）`length > 0`，会被当作有效正文，经 `formatExportParagraphs` 处理后变成"只有章节标题、正文为空"的章节，混入 TXT。

写入侧也没有校验：chapterCache.ts 的 `saveChapterCache` 直接 `writeFile`，不检查待写内容是否为空。

### P5. 缓存写入非原子，崩溃会产生半截文件

**代码证据**：`saveChapterCache`（chapterCache.ts L98-L113）直接对目标路径 `writeFile`。若写入过程中应用被杀、磁盘满、断电，会留下**写了一半的 .nb 文件**：

- 下次阅读命中该文件，读到的是截断正文，且不会再联网补全（缓存"存在"即命中）；
- 标准做法应是「写临时文件 → fsync → rename 原子替换」。

### P6. 孤儿缓存目录：一本书可能占多份空间

**实测证据**：本机 `book_cache` 下与红楼梦相关的目录有 4 个：

| 目录 | 文件数 |
|---|---|
| 红楼梦78d40e356ea89db5 | 1 |
| 红楼梦7e34252693c31d92 | 8 |
| 红楼梦8e2b38f395428ed0 | 120（当前书架实际使用） |
| 红楼梦c36b25ca2cf4e5ac | 2 |

**成因**：缓存目录名由「书名 + bookUrl 哈希」决定，书源改版导致 bookUrl 变化、或换源重新解析，就会生成新目录；旧目录无人引用也无人清理。

**影响**：磁盘空间被重复占用；没有任何界面提示这些目录的存在；"清除本书缓存"只清当前条目对应的目录，孤儿目录清不到。

### P7. 强依赖"每次重新联网解析目录"，URL 一变全部 miss

**代码证据**：下载/缓存流程每次都重新执行 `getBookInfo` + `getChapterList`（L112-L119），而不是优先使用书架已保存的目录（书架数据里本身存了完整 `chapters`）。

**影响**：书源一旦改版章节 URL 规则，即使本地 120 章缓存完好，新解析出的 URL 哈希与磁盘文件名全部对不上 → 缓存命中率归零 → 重新走全网下载。之前新增的"离线导出"正是为绕开此问题而把目录随请求传入。

### P8. 进度条不反映真实失败

**代码证据**：L136-L143 与 L166-L173，无论该章成功失败，进度 `current` 都从 `i` 推进到 `i + 1`。进度条 100% 的含义只是"循环处理完"，不是"100% 缓存成功"，与 P1/P2 叠加放大误导。

### P9. 缓存可观测性几乎为零

现状：用户看不到 ① 缓存占用空间；② 哪些章已缓存、哪些缺失；③ 失败原因；④ 孤儿目录。唯一的操作是"一删了之"（单本/全部清除），出问题无法自查，只能凭提示猜。

---

## 四、问题汇总与严重度

| 编号 | 问题 | 严重度 | 根因层面 | 用户可感知 |
|---|---|---|---|---|
| P1 | 假完成，不核对缓存数 | 高 | 事件/反馈 | 是 |
| P2 | 单章失败静默 | 高 | 错误处理 | 间接 |
| P3 | 残缺 TXT 算成功 | 高 | 错误处理 | 是 |
| P4 | 空/纯空白缓存判定不严 | 中 | 数据校验 | 间接 |
| P5 | 非原子写入产生半截文件 | 中 | 写入可靠性 | 偶发 |
| P6 | 孤儿缓存目录 | 中 | 生命周期管理 | 否（占空间） |
| P7 | 重新解析目录导致全 miss | 中 | 架构设计 | 偶发 |
| P8 | 进度条不反映失败 | 中 | 事件/反馈 | 是 |
| P9 | 缓存可观测性为零 | 低 | 管理界面 | 是 |

---

## 五、改善方案（按优先级分三级）

### 第一级 S1：让反馈变"诚实"（最小改动，先做）

**目标**：提示与实际完全一致，消除假完成。改动集中在主进程统计 + 事件字段扩展 + 前端文案。

**S1-1 主进程统计真实成败**

在 L132-L174 循环中维护计数器：

```ts
let succeeded = 0;
const failedChapters: { title: string; url: string; message: string }[] = [];
// getChapterContentWithCache 成功后 succeeded++；catch 中 failedChapters.push(...)
```

**S1-2 扩展 done 事件携带统计**

在 src/shared/bookSource/types.ts 的 `BookSourceDownloadDoneEvent` 增加字段（旧字段保留，向后兼容）：

```ts
cachedChapters: number;      // 真实缓存成功数
totalChapters: number;       // 目录总章数
failedChapters: { title: string; url: string; message: string }[];
```

**S1-3 前端按统计给出真实提示**

- 离线缓存（FindBookReaderPanel.vue L1768-L1771）：
  - 全部成功：「已完成离线缓存（x/y 章）」；
  - 部分失败：警告「已缓存 x/y 章，z 章失败」，并提供「查看明细」；
  - 全部失败：错误提示，不弹成功 toast；
- 整书下载：有失败章时 done 提示「已导出，含 x 章未缓存内容」而非纯成功。

**S1-4 进度事件增加成功/失败口径**

`BookSourceDownloadProgressEvent` 增加累计失败数，进度条可区分"处理进度"与"成功进度"（如失败段标红）。

> 对应修复：P1、P2、P3、P8。

### 第二级 S2：提高缓存读写可靠性

**S2-1 缓存写入原子化 + 非空校验**

改造 chapterCache.ts 的 `saveChapterCache`：

```ts
// 1) 内容为空/纯空白直接拒绝写入
if (!content.trim()) throw new Error("章节内容为空，不写入缓存");
// 2) 写临时文件 → rename 原子替换
const tmp = `${target}.${process.pid}.tmp`;
await writeFile(tmp, content, "utf8");
await rename(tmp, target);
```

**S2-2 读取侧统一严格判定**

把"缓存是否有效"收敛为一个函数（替代各处分散的 `length` 判定）：

```ts
/** 缓存有效 = 存在且 trim 后非空；纯空白视为无效 */
export function isValidChapterCache(text: string | null): text is string {
  return text != null && text.trim().length > 0;
}
```

阅读命中、整书导出、缓存状态标记三处全部复用，杜绝 P4 场景。

**S2-3 命中失效缓存时自动回退联网**

`getChapterContentWithCache` 读到无效/损坏缓存时，不应直接返回坏内容，而应删除坏文件并联网重新拉取（失败再走失败分支），实现"缓存自愈"。

> 对应修复：P4、P5，并降低 P2 的实际危害。

### 第三级 S3：体验与生命周期管理

**S3-1 失败章明细 + 单章重试**

详情页/阅读器提供"未缓存章节"列表（标题 + 失败原因 + 重试按钮），重试只请求该章，不必整书重跑。对应 P2、P9。

**S3-2 缓存完成后一键导出**

离线缓存 `done` 且存在失败为零/部分失败时，弹询问「是否立即导出为 TXT？」，确认后用当前目录直接拼 TXT（复用 `readChapterCache` + 排版函数），让"缓存"与"得到文件"无缝衔接。对应 P1 的认知落差。

**S3-3 缓存管理面板**

设置 → 下载中新增：缓存总占用、每本书占用/章数、未缓存章数、孤儿目录扫描结果；支持"仅清理孤儿目录"（删除不被任何书架条目引用的缓存文件夹）。对应 P6、P9。

**S3-4 目录离线优先**

下载/缓存流程优先使用书架保存的 `chapters`，无法命中或用户手动刷新时才联网重新解析；目录可作为参数一路传到缓存命中与导出环节。对应 P7。

> 说明：S3-4 涉及主进程流程调整，需配套"目录过期检测"（如用户主动点刷新、或缓存命中率异常低时提示重新解析），避免用过旧目录。

---

## 六、分阶段实施路线图

| 阶段 | 内容 | 改动范围 | 预估工作量 | 价值 |
|---|---|---|---|---|
| 阶段一 | S1 全部（诚实反馈） | shared 事件类型 + downloadService + 2 个渲染组件 | 小 | 立刻消除"假完成"投诉 |
| 阶段二 | S2-1、S2-2（原子写 + 严格校验） | chapterCache.ts + 各判定点 | 小 | 数据可靠性底座 |
| 阶段三 | S2-3 + S3-1（自愈 + 失败重试） | getChapterContentWithCache + UI | 中 | 缺章可补齐 |
| 阶段四 | S3-2 + S3-4（一键导出 + 离线优先） | 主进程流程 + 交互 | 中 | 体验闭环 |
| 阶段五 | S3-3（缓存管理面板） | 设置面板 + 主进程统计 IPC | 中 | 长期可维护 |

每个阶段独立交付、独立验证；阶段一即可解决用户最直接的痛点，后续按需推进。

---

## 七、验证清单（改造后逐项实测）

| # | 场景构造 | 期望表现 |
|---|---|---|
| 1 | 断网后点离线缓存（零缓存书） | 提示 0/y 章、明确失败，不出现「已完成」 |
| 2 | 用防火墙拦截部分章节域名 | 提示 x/y 章 + z 章失败，可查看明细 |
| 3 | 正常网络完整缓存 | 提示 x/y 章且 x=y，目录全部出现缓存对勾 |
| 4 | 手动构造 0 字节 .nb | 读取判无效；阅读时自动重拉；导出走占位/跳过 |
| 5 | 手动构造纯空白 .nb | 同上，不得出现"标题在、正文空"的章节 |
| 6 | 缓存写入中强杀进程 | 不残留半截目标文件（临时文件可存在但不被命中） |
| 7 | book_cache 中预置一个孤儿目录 | 管理面板能扫出并支持仅清理孤儿 |
| 8 | 整书下载含失败章 | done 提示明确含未缓存章数，TXT 占位可定位 |
| 9 | 重启应用 | 缓存与统计设置保持，不重复下载已缓存章 |
| 10 | `npm run typecheck` | 0 错误 |

---

## 八、涉及文件速查表

| 文件 | 承担职责 | 关联方案 |
|---|---|---|
| src/main/bookSource/downloadService.ts | 下载/缓存主流程、事件发出 | S1 全部、S3-2 |
| src/shared/bookSource/types.ts | 下载事件与请求类型 | S1-2、S1-4、S3-4 |
| src/main/bookSource/engine/chapterCache.ts | 缓存命名、读写、清除 | S2-1、S2-2 |
| src/main/bookSource/engine/getChapterContentWithCache.ts | 缓存命中与联网拉取 | S2-3、S3-1 |
| src/renderer/src/bookSource/components/FindBookReaderPanel.vue | 离线缓存入口与提示 | S1-3、S3-2 |
| src/renderer/src/bookSource/components/BookDetailPanel.vue | 详情页下载/缓存状态 | S1-3、S3-1 |
| src/renderer/src/bookSource/components/FindBookSettingsDownloadPanel.vue | 下载设置、清除缓存入口 | S3-3 |
| src/renderer/src/bookSource/composables/useBookSource.ts | 下载状态机与事件订阅 | S1 全部 |
| src/renderer/src/bookSource/services/clearBookChapterCache.ts | 清除缓存交互 | S3-3 |

---

## 九、结论

1. 用户反馈的"提示导出/缓存完成，实际没有"**现象成立**：根因是完成事件只表示"循环跑完"，不统计真实缓存数（P1），叠加单章失败静默（P2）与残缺 TXT 占位（P3）；
2. 「离线缓存」本身**不生成 TXT 是设计行为**，需要在文案上消除"导出成功"的误导，或提供完成后一键导出（S3-2）；
3. 改造遵循"**先让提示诚实（S1），再保证数据可靠（S2），最后完善管理（S3）**"的顺序，阶段一改动小、见效最快，可独立交付；
4. 所有方案均复用现有 IPC 与缓存命名体系，不改动主界面阅读器，风险可控。
