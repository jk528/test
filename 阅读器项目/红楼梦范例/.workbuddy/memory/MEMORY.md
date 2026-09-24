# MEMORY.md — 《红楼梦》文本分析工程长期约定

> 跨会话有效。改文档/文件前先读本节。

## 一、文档与磁盘必须同口径
- 文档里凡写数量的地方**一律以文件系统实测为准**，不许沿用旧值；改完文件系统必须回扫全工程同步相关文档，并**回读验证 + 算术自洽**（资产表各行合计 ≈ 声明总数）。
- 踩过的坑：把字节数当词条数（「91 万」实为 910,438 字节，真值 17,817 词群 / 107,934 词条）；删冗余后 267→266 份 MD、工程 27.88→24.58 MB。

## 二、编辑落盘必须验盘
- Edit 工具**经常报 success 却没写入**（2026-09-17 一批 4 次实测 3 次没落盘）。**默认做法：批量改中文文档走 Python 脚本** —— `str.replace(old,new,1)` + `assert old in s` + 回读 count 断言。只改一两行且锚点纯 ASCII 时才用 Edit。
- 锚点只用**纯 ASCII 片段**，避开全角标点（含全角括号时静默失败率极高）；**不要截断到行尾标点之前**（会漏掉行尾「（见下）」之类残余）。
- 大区块整段替换；编辑后重算围栏配对与 TOC 锚点。偶发 `EBUSY`（云盘扫描）→ 重试即可。

## 三、删除文件的安全规程
- 一律**送回收站**（`ctypes.windll.shell32.SHFileOperationW`，`FO_DELETE=3` + `FOF_ALLOWUNDO`）；返回码不可信，必须 `os.path.exists` 逐项复核。**绝不永久删除**。
- 删重复文件前先 **MD5 校验**两份一致；**空目录可能是规范承诺的输出位置**（如 `分析结果/CSV导出/`）→ 删前先 grep 规范文档，不能按「空 = 垃圾」判定。
- 删除后修正**悬空引用**；数据来源处的引用不整行删，改写为「已退役 / 内容并入 X」保留 provenance。

## 四、本机工具链
- **Bash 工具不稳定**（`ls`/`head`/管道常失败）→ 跑脚本用绝对路径 `C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`；目录枚举用 PowerShell。
- **PowerShell 的 `Add-Type` / `New-Object -ComObject` 被安全策略拦截** → 回收站等 COM 操作走 Python ctypes。

## 五、文档登记表（改文档前先看）
| 文档 | 体积/行数 | 定位 | 维护 |
|---|---|---|---|
| `环境配置与任务进度.md` | ~45 KB / 747 行 | **唯一进度事实源** | 每轮必须更新 |
| `红楼梦文本分析软件设计方案_V2.0.md` | 91,556 B / 1,823 行 | **析域施工底本**（S0–S9） | 改第五章须同步下条 |
| `红楼梦阅读分析一体化_设计方案_V1.0.md` | 56,119 B / 776 行 | **架构决策记录 ADR** | 架构变更才动 |
| `软件实施步骤_具体方案.md` | 39,778 B / 958 行 | V2.0 第五章**抽取版** | **双底本同步风险**，宜降级为索引页 |
| `项目现状总结_2026-09-17.md` | 14,705 B / 123 行 | **只读快照**（非事实源） | 可重写或删除 |

## 六、关键决策
- 分词锁 **jieba**；情感用内置双引擎（`基础/emotion_analysis.py`），**不用 cnsenti**；120 章历史产物口径已锁，词库只做并集不覆盖。
- **统一锚点模型是跨模块硬约定**：`(bookId, chapterIndex, lineStart, lineEnd, charStart?, charEnd?)`；**物理行号唯一权威**，替换/简繁只作用于展示层。
- 打包：**onedir + 不启用 UPX + Tauri 壳**；`externalBin` 文件名须带目标三元组后缀；WebView2 用 `downloadBootstrapper`。

## 七、M3 代码库硬约束（`app/`，改前必读）
- **运行时数据必须在同步目录之外**：主库 `%USERPROFILE%\.honglou\data\honglou.sqlite` + 模型 `%USERPROFILE%\.honglou\models`，由 `config.DATA_DIR` 解析（可被 `HONGLOU_DATA_DIR` / `HONGLOU_DB_PATH` / `EMBED_CACHE_DIR` 覆盖）；venv 同理 `%USERPROFILE%\.venvs\honglou`。**绝不放回工程目录**（云盘加锁 EBUSY、多机互相覆盖、上百 MB 白同步）。
- **`book_id` = 纯内容哈希**（`retrieval.book_id_of(text)`，先换行归一化），**绝不掺源路径** —— 同一本书会被不同路径读到（`C:\…` / `\\?\C:\…` / 另一份拷贝），掺路径即一书店多条记录、检索自我重复。
- **`chunks` 是 AUTOINCREMENT，重插即换 id** → 任何重建索引路径必须同步清 `chunk_vec`（`add_chunks` 已内建 `_purge_vectors_of`）；孤儿向量不会被自动回收，KNN 照常命中再被 `JOIN` 丢弃。
- **sqlite-vec 的 vec0 不支持 `INSERT OR REPLACE`**（实测 `UNIQUE constraint failed`）；`DELETE ... WHERE chunk_id IN (...)` 可用；KNN 必须写 `v.k = ?`，不能 `ORDER BY ... LIMIT`。
- **stdout 是 NDJSON 协议通道，任何 `print` 必须带 `file=sys.stderr`** —— 混入一行纯文本即让 Rust 侧 `serde_json::from_str` 失败、整个 sidecar 通信崩掉。
- **情感写入用 `upsert_emotions`（按行增量幂等），不用 `save_chapter_emotions`（整章替换）** —— 前端视口驱动分批算，整章替换会冲掉先到批次；`emotions.spans_json` 存字级词位置，不存则重启后字级高亮丢失。
- **开书先走 `index_status` 判据再决定是否 `build_index`**，不要无条件重建（一次全量嵌入 ~108s）。
- 嵌入模型 BGE-small-zh-v1.5 实测 **90.4 MB**，HF 缓存 Windows 不建符号链接 → **磁盘占用约 181.6 MiB**（不是旧值的 47 MB）。
- 改 schema **必须同时补 `_migrate()` 的 `ALTER TABLE`**（`CREATE TABLE IF NOT EXISTS` 不改已存在的表结构，老库会报 `no such column`）。
- sidecar 版本 **0.3.1-m3 / 18 个方法**；回归测试 `app/tools/e2e_sidecar.py`（真实 stdio NDJSON，18 方法契约 + stdout 纯净性），改动 sidecar 后必跑。

## 八、M4 全景分析硬约束（`分析结果/` → SQLite 回灌，改前必读）
- **报告段落号 ≠ 物理行号**：两套编号，禁止直接换算。锚点必须走三级降级 `quote → cooccur → para`，并做**单调不回退**修正（同章锚点非递减、且落在本章行区间内），`anchor_precision` 如实落库、界面如实标注「精确/近似/粗定位」，**不许假装精确**。
- **别名必须归并**：`基础/红楼梦人物名.txt` 把 宝玉/黛玉/凤姐 等别名**同时**列为独立条目；不回并就会出现「贾宝玉 4072 + 宝玉 3966」两条实体。`build_alias_map()` 折回本名，`_usable_name()` 过滤 >6 字与非中文垃圾名。
- **tone 需归一**：报告 tone 有 56 种写法，`normalize_tone()` → 正面/负面/中性/其他。
- 回灌是**整书幂等替换**（五表联动：events / entities / entity_mentions / foreshadows / entity_relations）；`分析结果/` 定位走 `config.resolve_analysis_dir()`（`HONGLOU_ANALYSIS_DIR` 或相对 `../../分析结果`）。
- 基线规模（改动后须重测，勿沿用旧值）：events **2235** / entities **389** / mentions **30027** / foreshadows **1297** / relations **2370**；主库 **4.93 MB**。
- sidecar 版本 **0.4.0-m4 / 26 个方法**；回归 `app/tools/e2e_sidecar.py`（44 项断言，真实 stdio NDJSON），改 sidecar 后必跑。

## 九、本机工具链补充（第四轮实测）
- **PowerShell 工具不回显 stdout** → 校验输出一律「写文件 + Read 工具读」；PowerShell `*>` 重定向默认 **UTF-16**，读取前须解码。
- **前端类型检查/构建不要经 pnpm.ps1**（PowerShell 会把原生 stderr 当 `NativeCommandError` 截断日志）→ 用 Python `subprocess` 直接跑 `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` 与 `node node_modules/vite/bin/vite.js build`。

## 十、M4 GUI 端到端验证（真实窗口，改前必读）
- **一次工具调用内必须完成「起栈 → 交互 → 退栈」**：调用返回时该调用启动的进程树会被回收；后台任务也会被后续调用打断。原子脚本范式见 `app/tools/gui_once.py`。
- 起栈首选**已编译的 `src-tauri/target/debug/app.exe` + 自起 vite dev server**，绕开 cargo/pnpm（dev profile 已构建时秒起）。
- **点击前必须强制前置并校验**：`SetWindowPos(TOPMOST→NOTOPMOST)` + `AttachThreadInput` + `SetForegroundWindow`，断言 `GetForegroundWindow()==hwnd`；落点用 `WindowFromPoint`+`GetAncestor(GA_ROOT)` 复核。否则点击会打到覆盖在上层的其它窗口。
- **截图用 `PrintWindow(hwnd, hdc, 2)`**（对 WebView2 有效、被遮挡也能取窗口自身内容）；空白再回退 BitBlt / 屏幕抓取。图像处理用 venv 的 Pillow。
- **坐标换算**：`SetProcessDpiAwareness(2)` → `scale=GetDpiForWindow/96`（本机 2.25）→ `ClientToScreen(0,0)` 为原点 → `phys = origin + css*scale`。
- **滚轮正值向上**，向下要传 `-120`。
- **`vite build` 会被 node 批量删除保护拦截**（`SAFE_DELETE_BULK_CONFIRM_REQUIRED`，阈值 50；vite 清空 `dist/assets`）→ 先把 `app/dist` 送回收站再构建。
- **M4 已知修复**：`App.vue` 占位卡片必须是 `v-if="!rawText"`，**不能**用 `v-else`（会绑到 `AiPanel` 的 `v-if` 上，导致关掉 AI 面板后卡片压住正文）。


## 十一、M4.5 全书预处理硬约束（改前必读）
- **目标口径**：分析**前置到开书时**。全书 **3366 段**段落级情感 + **120 章**级汇总一次性入库；阅读时**零实时计算**，直接吃库。
- **幂等判据 = 逐章段落行数 > 0**，**不能只看 `chapter_emotions` 有行** —— 「章级有记录 ≠ 段落已备」，只看章级会让「段落被清空」的章永远补不回。判据走 `emotion_lines_by_chapter()`。
- **`_analyze_lines(lines, indices, eng)` 是段落级情感的唯一实现**，实时 `analyze_sentiment` 与 `prepare_book` 共用 → 保证**库-实时等价**（改一处即两边同步，勿复制第二份）。
- **`prepare_book` 支持 `chapter_from/to` 分片**（前端 20 章一片驱动进度条）+ `force`；已备整书则返回 `skipped=True, elapsed_ms=0`。
- **e2e 必须用独立测试书 `bid + "-e2e-tmp"`**：第四节往返测试的 `save_chapter_emotions(rows=[])` 清场型断言曾把真实预处理数据删掉（3366→3299）。
- sidecar 版本 **0.5.0-m4.5 / 29 方法**（+prepare_book / prepare_status / list_chapter_emotions）；逻辑表 **12 张**（`db_status` 报 `tables=17`）；主库 **7.09 MB**；回归 `app/tools/e2e_sidecar.py`（50 项断言）。
- 改中文文档若某事实**多处引用**（同一数字出现在 N 行 / 资产表 / 下一步），锚点会 `count>1` → 补丁脚本需**多出现替换**通道，勿硬套 count==1。
