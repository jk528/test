# ColorTxt 三大方法论漏洞 · 代码修复方案

> 对应《ColorTxt交互方法论补全-事件路由-错误态-多窗口.md》中确认的问题，按**可独立提交的最小补丁**组织。
> 每个任务：问题锚点 → 补丁代码（before/after）→ 影响面 → 验证用例 → 回滚方式。
>
> 优先级：P0 数据安全（C2/C5/C6）→ P1 资源与一致性（C3/C1）→ P2 健壮性（C4/重试/路由）。
> 源码根目录：`.temp/ColorTxt` ｜ 2026-09-22
>
> **重要**：`.temp/ColorTxt` 是分析副本，落地前确认真实工程路径；所有补丁均为最小改动，不做附带重构。

---

## 任务总览

| # | 缺口 | 任务 | 层 | 新增 IPC | 改动文件数 | 优先级 |
|---|------|------|----|---------|-----------|--------|
| T1 | C2 | 找书窗关窗未保存拦截（复用已有确认函数） | 渲染 | 无 | 3 | P0 |
| T2 | C6 | 下载失败章计数与"完成但有失败"提示 | 主+渲染 | 无（扩事件字段） | 4 | P0 |
| T3 | C5 | 保存时外部修改冲突检测（mtime 乐观锁） | 主+渲染 | 无（扩参数） | 5 | P0 |
| T4 | 2.5 | 找书章节加载失败"点击重试" | 渲染 | 无 | 2 | P1 |
| T5 | C3 | 窗口关闭取消在途 AI 请求与 TTS | 渲染（主进程可选加固） | 无 | 3 | P1 |
| T6 | C1 | 书源增删改跨窗广播 | 主+渲染 | 复用事件通道 | 3 | P1 |
| T7 | C4/电源 | 显示器热插拔与休眠恢复 | 主+渲染 | 无 | 3 | P2 |
| T8 | 路由 | 事件路由回归测试矩阵 + dev 追踪开关（**无生产逻辑改动**） | 测试 | 无 | 2 | P2 |

依赖顺序：T1、T2、T3、T4、T6、T7 互相独立可并行；T3 改 `file:writeTextFile` 签名（向后兼容可选参数）；T2 改 done 事件类型（向后兼容新增字段）。

---

# T1（C2）找书窗关窗未保存拦截

## 锚点
- 主窗已有：App.vue:2778-2783 `handleWindowCloseRequest`（dirty 时 appConfirm）。
- 找书窗**无条件放行**：FindBookWindow.vue:21-23、32-34。
- 确认函数已存在且已被切章/退出编辑复用：useFindBookChapterSession.ts:357-363 `confirmIfReaderEditDiscard()`；FindBookReaderPanel.vue:749 已解构，但 defineExpose（:2092-2107）**未暴露**。
- FindBookPanel 持有阅读器引用 `bookReaderPanelRef`（:394）。

## 补丁（3 处）

**① FindBookReaderPanel.vue defineExpose 增加一行（:2092 块内）**
```ts
defineExpose({
  bringToFront: () => { modalRef.value?.bringToFront?.(); },
  refreshChapterCacheStatus,
  clearChapterCacheMarks,
  confirmIfReaderEditDiscard,          // ← 新增
  openChapter: (contentIndex: number) => { /* 原样 */ },
  readerEditMode,
  applyEditFormatTextReplace: (rules: ReplaceRule[]) =>
    readerRef.value?.applyEditFormatTextReplace?.(rules),
});
```

**② FindBookPanel.vue `<script setup>` 末尾新增 defineExpose（该文件当前无 expose，grep 已确认）**
```ts
defineExpose({
  /** 关窗前由 FindBookWindow 调用；返回 false 表示用户取消关窗 */
  async confirmBeforeClose(): Promise<boolean> {
    if (!bookReaderPanelRef.value) return true;
    return bookReaderPanelRef.value.confirmIfReaderEditDiscard
      ? bookReaderPanelRef.value.confirmIfReaderEditDiscard()
      : true;
  },
});
```
并给模板中的 `<FindBookReaderPanel ref="bookReaderPanelRef">` 补 TS 实例类型（沿用现有 ref 声明，不新增）。

**③ FindBookWindow.vue 改为异步确认**
```ts
// before
function closeWindow() {
  window.colorTxt.proceedCloseWindow();
}
// after
const panelRef = ref<InstanceType<typeof FindBookPanel> | null>(null);

async function closeWindow() {
  if (panelRef.value && (await panelRef.value.confirmBeforeClose()) === false) return;
  window.colorTxt.proceedCloseWindow();
}
```
模板：`<FindBookPanel ref="panelRef" standalone @go-main="onGoMain" />`。

## 验证
1. 找书阅读器进编辑、改字不保存 → 点窗口 × → 出现"当前章节已修改但尚未保存"→ 取消则窗不关、内容在；确认则关。
2. 非编辑态关窗不弹框（confirmIfReaderEditDiscard 首行短路 true）。
3. 主窗回归：本地文件编辑 dirty 关窗仍弹原确认框（本次不动主窗路径）。

## 回滚
三处独立还原；无 IPC、无持久化变化。

---

# T2（C6）下载失败章计数与诚实完成提示

## 锚点
- 失败被吞：downloadService.ts:161-165（logs.push，不计数）。
- 占位：:213 `[下载失败: 章节未缓存]`。
- done 事件无失败字段：types.ts:345-351 `BookSourceDownloadDoneEvent`；cacheOnly done 在 :186-193。
- 渲染完成处理：useBookSource.ts:502-509（当前拿不到失败信息）。

## 补丁（4 处）

**① types.ts:345-351 扩 done 事件（新增可选字段，向后兼容）**
```ts
export type BookSourceDownloadDoneEvent = {
  downloadId: string;
  type: "done";
  filePath: string;
  bookName: string;
  /** 缓存失败的章节数（0 表示完整） */
  failedChapters?: number;
  /** 最多前 20 个失败章标题，供提示展开 */
  failedChapterTitles?: string[];
};
```

**② downloadService.ts 循环前加计数（:131 附近）**
```ts
let failedChapters = 0;
const failedChapterTitles: string[] = [];
// catch 块（:161-165）内追加：
} catch (e) {
  const msg = e instanceof Error ? e.message : String(e);
  logs.push(`缓存章节失败 [${ch.title}]: ${msg}`);
  failedChapters += 1;
  if (failedChapterTitles.length < 20) failedChapterTitles.push(ch.title);
}
```

**③ 两处 done 携带计数**
```ts
// cacheOnly done（:187-192）
emit({ downloadId, type: "done", filePath: "", bookName: detail.name,
       failedChapters, failedChapterTitles });
// 导出 done（:232-237）
emit({ downloadId, type: "done", filePath, bookName: detail.name,
       failedChapters, failedChapterTitles });
```
注意：导出循环（:198-215）的占位判定与缓存计数一致（同一缓存读取结果），无需二次统计；`failedChapters>0 且 filePath 非空`即"TXT 已生成但含占位"。

**④ useBookSource.ts download 的完成值携带失败信息（:490-513、finish :534/546）**

composable 内不引 toast（它当前只返回状态，grep 确认无 appToast），最小改法是把 Promise 完成值由 `string | null` 扩为对象：
```ts
type DownloadResult = {
  filePath: string | null;          // 原有语义：cacheOnly 成功为 ""，失败为 null
  failedChapters: number;
  failedChapterTitles: string[];
};
// done 分支：
const failed = ev.failedChapters ?? 0;
finish({
  filePath: cacheOnly ? "" : (ev.filePath || null),
  failedChapters: failed,
  failedChapterTitles: ev.failedChapterTitles ?? [],
});
// error / cancel / catch 分支统一 finish({ filePath: null, failedChapters: 0, failedChapterTitles: [] })
```
调用方 BookDetailPanel.vue `onDownloadOrStop`（:815 附近，UI 组件可直接用 appToast/appDialog）：
```ts
const r = await downloadBook(/* 原参数 */);
if (r.filePath === null) { /* 原有失败/取消提示不动 */ }
else if (r.failedChapters > 0) {
  appToast(
    cacheOnly
      ? `离线缓存完成，${r.failedChapters} 章失败（重新下载将只补缺失章）`
      : `已导出 TXT，但 ${r.failedChapters} 章失败，正文中已标注占位`,
    { kind: "warning", duration: 8000 },
  );
}
```
onDone 回调（:505 处当前签名 (filePath)）同步改为接收对象或仅在内部使用，保持 FindBookPanel.vue:990 `onBookDownloaded(path, size)` 原签名（它处理"下载完加入主界面书架"，与失败提示无关，不改动）。

## 验证
- 断网点下载 3 章的书 → 完成 toast 明确"3 章失败"；联网后重新下载 → 缺章补齐、toast 不再告警。
- cacheOnly 模式同样有失败计数；正常全成功无任何新增提示。

## 回滚
事件字段为可选；删除四处追加即恢复。

---

# T3（C5）保存时外部修改冲突检测（mtime 乐观锁）

## 设计
不引入锁文件、不做三方合并。保存时把"打开时看到的 mtime"带给主进程；主进程写盘前 stat 比对，不一致则拒绝覆盖并返回专用错误码，渲染层给"重新加载 / 强制覆盖"二选一。编辑态继续不监听磁盘（维持现状），冲突在保存点一次性裁决。

## 锚点
- 打开时已 stat：ipcHandlers.ts:888 `const st = await stat(physicalPath)`，stream-start 在 :916。
- 保存：ipcHandlers.ts:602-630，preload writeTextFile(path, content, encoding)。
- 渲染保存失败提示：App.vue:2505（`appAlert(written.message ?? "保存失败")`）；另存 :1045。
- 磁盘变更推送：`file:disk-changed`（ipcHandlers.ts:237-315）。

## 补丁（5 处）

**① 主进程 stream-start 携带 mtime（ipcHandlers.ts:916-921）**
```ts
sender.send("file:stream-start", {
  requestId,
  ...streamMeta,
  totalBytes,
  fileMtimeMs: st.mtimeMs,   // ← 新增
});
```

**② 主进程 writeTextFile 增加可选乐观锁参数（:602-630）**
```ts
ipcMain.handle(
  "file:writeTextFile",
  async (_evt, filePath: string, content: string, encodingRaw: unknown,
          opts?: { expectedMtimeMs?: number | null }) => {
    const resolved = path.resolve(String(filePath ?? "").trim());
    if (!resolved) return { ok: false as const, message: "路径为空" };
    const encoding = typeof encodingRaw === "string" && encodingRaw.trim()
      ? encodingRaw.trim() : "utf8";
    try {
      if (typeof opts?.expectedMtimeMs === "number") {
        const cur = await stat(resolved).catch(() => null);
        if (cur && Math.abs(cur.mtimeMs - opts.expectedMtimeMs) > 1000) {
          return { ok: false as const, code: "file_changed_externally" as const,
                   message: "文件已被其他程序修改", currentMtimeMs: cur.mtimeMs };
        }
      }
      const buf = iconv.encode(content, encoding);
      await mkdir(path.dirname(resolved), { recursive: true });
      // 原子写：临时文件 + rename，顺带消除"写一半崩溃留半截"风险（2.4 缺口）
      const tmp = `${resolved}.colortxt-tmp-${process.pid}`;
      await writeFile(tmp, buf);
      await rename(tmp, resolved);
      const after = await stat(resolved);
      return { ok: true as const, fileMtimeMs: after.mtimeMs };
    } catch (e) {
      return { ok: false as const, message: e instanceof Error ? e.message : String(e) };
    }
  },
);
```
> 若评审认为原子写超出本任务范围，可只保留 mtime 分支，把 tmp+rename 拆为独立提交；两者代码互不依赖。
> 需要 import 中已有 rename（fs/promises）；无则在文件顶部 import 列表追加。

**③ preload/index.ts writeTextFile 透传第 4 参（:476 附近）**
```ts
writeTextFile: (filePath, content, encoding, opts) =>
  ipcRenderer.invoke("file:writeTextFile", filePath, content, encoding, opts),
```
同步更新 preload 的 API 类型声明（window.colorTxt 接口）。

**④ 渲染层记录基线 mtime**
- useAppWindowBindings.ts 的 onStreamStart 处理（:345 附近）把 `ev.fileMtimeMs` 存入新增 ref `currentFileMtimeMs`（与 currentFile 同生命周期；切文件/流错误时置 null）。
- 通过 useAppFileSession 返回或 props 传到保存调用点。

**⑤ App.vue 保存函数（:2505 附近）裁决**
```ts
const written = await window.colorTxt.writeTextFile(
  filePath, text, encoding,
  readerEditMode.value ? { expectedMtimeMs: currentFileMtimeMs.value } : undefined,
);
if (!written.ok) {
  if (written.code === "file_changed_externally") {
    const choice = await appConfirmThree(          // 复用现有 AppDialog 三按钮能力
      "文件已在外部被修改。\n重新加载会放弃本次编辑；强制覆盖会丢弃外部改动。",
      "保存冲突", ["重新加载", "强制覆盖", "取消"]);
    if (choice === 0) { void reloadCurrentFile(); return; }       // 走 openFilePath 重开
    if (choice === 1) {
      const forced = await window.colorTxt.writeTextFile(filePath, text, encoding);
      if (!forced.ok) { void appAlert(forced.message ?? "保存失败"); return; }
      currentFileMtimeMs.value = forced.fileMtimeMs ?? null;
    }
    return; // 取消：留在编辑态
  }
  void appAlert(written.message ?? "保存失败");
  return;
}
currentFileMtimeMs.value = written.fileMtimeMs ?? null;
```
三按钮确认若现有 AppDialogHost 只支持双按钮，降级为：先 confirm"重新加载放弃编辑？"→ 否 → 再 confirm"仍要强制覆盖外部改动？"，不新增组件能力。

## 验证
1. 打开文件 → 外部记事本改并保存 → 回彩读进编辑改字 → 保存 → 弹冲突；选重新加载内容为外部版；选强制覆盖磁盘为编辑版。
2. 无外部改动时保存零感知（mtime 差 ≤1s 容忍，防杀毒软件改时间戳）。
3. 只读阅读态不参与比对（opts 不传）。
4. 另存为路径（:1045）不传 expectedMtimeMs，保持原行为。

## 回滚
writeTextFile 第 4 参可选；不传时行为与旧版完全一致（除原子写——如需彻底回滚还原为 writeFile 直写）。

---

# T4 找书章节加载失败"点击重试"

## 锚点
- 错误态模板只有文案无按钮：FindBookReaderPanel.vue:2448-2457（`chapterError`）。
- 重试所需动作已存在：重新加载当前显示章 = `loadChapterAtDisplayIndex(currentDisplayIndex, { forceNetwork: true })`（useFindBookChapterSession.ts，缓存优先链同函数）。
- 网络书源导入已有重试文案模式：useBookSource.ts:113。

## 补丁（2 处）

**① useFindBookChapterSession.ts 导出重试函数（return 块 :719 附近追加）**
```ts
async function retryCurrentChapter() {
  if (chapterError.value) {
    await loadChapterAtDisplayIndex(deps.currentDisplayIndex.value, { forceNetwork: true });
  }
}
// return { ..., retryCurrentChapter }
```
（forceNetwork 选项若不存在，最小实现：在 loadChapterAtDisplayIndex 增加 `bypassCache` 参数透传给 getChapterContent IPC；主进程 getChapterContent 已支持网络回退，缺的只是"缓存失败标记后强制走网络"开关——若改动需深入主进程，则本任务降级为"整章重载"按钮，不传 forceNetwork，简单重跑同一函数即可让用户重试瞬时错误。）

**② FindBookReaderPanel.vue 错误模板加按钮（:2448-2457）**
```html
<p v-else-if="chapterError && !readerContentKey" class="findBookReaderError">
  <span class="findBookReaderErrorMain">{{ chapterError }}</span>
  <button type="button" class="btn" @click="retryCurrentChapter">重新加载本章</button>
  <span v-if="logs.length" class="findBookReaderErrorLogs">{{ logs.join("\n\n") }}</span>
</p>
```
从 chapterSession 解构 retryCurrentChapter（:740 附近解构块）。

## 验证
- 断网进章显示错误 → 联网点按钮 → 内容加载、错误消失。
- 加载中按钮禁用（复用 chapterContentBusy）。

---

# T5（C3）窗口关闭取消在途 AI 请求与 TTS

## 方案（渲染层最小修复先行，主进程加固可选）

### 5A. 渲染层随窗销毁清理（P1，必做）

**锚点**
- 已有 beforeunload/pagehide 刷盘点：useAppWindowBindings.ts:737-740 `flushPersistence`。
- AI 中止 IPC 已齐：`ai:chat:abort`（registerAiIpc.ts:825）、ai:text-format:abort(:908)、ai:wordcloud:abort(:707)、ai:embedding:abort(:551)、ai:portrait:retrieve:abort(:1445)。
- TTS：voiceReadSynthesisClient.ts:64 `voiceReadCancelSynthesis({requestId})`。

**补丁**
① AI 助手面板（AiAssistantPanel.vue / useAiAssistant 组合式）：维护"本窗活跃 requestId 集合"（发起 add、done/error remove，本就是流式回调现有节点，加 Set 即可），新增：
```ts
function abortAllActiveRequests() {
  for (const id of activeRequestIds) {
    window.colorTxt.ai.chatAbort(id);   // 真实插口：preload:947 ai.chatAbort → ai:chat:abort
  }
  activeRequestIds.clear();
}
onBeforeUnmount(abortAllActiveRequests);
```
词云/立绘/排版面板同理在各自 onBeforeUnmount 调对应 abort（preload 中各自通道：ai.textFormatAbort?./ai wordcloud/embedding/portrait abort，落地时以 preload/index.ts 的 ai 命名空间实际方法名为准；通道名见 registerAiIpc.ts:551/707/908/1445）。

② TTS：主窗在持有语音会话的组件卸载时调用已有的 `exitVoiceRead()`（App.vue:2203 已从语音组合式解构，@stop 也用它，:4178）；找书阅读器侧已有同名 dep（useFindBookChapterSession.ts:398 `deps.exitVoiceRead()`），在阅读器面板 onBeforeUnmount 统一调一次即可停止并取消在途合成（内部经 voiceReadSynthesisClient.ts:64 voiceReadCancelSynthesis）。

③ useAppWindowBindings.ts 的 flushPersistence 同级增加统一兜底：
```ts
function flushOnUnload() {
  flushPersistence();
  deps.abortWindowTasks?.();   // App.vue 传入：AI 面板 abortAll + TTS stop 的聚合函数
}
window.addEventListener("beforeunload", flushOnUnload);
```
注意 beforeunload 中异步 IPC 可能不完成，因此主面板的 onBeforeUnmount（Vue 卸载先于页面销毁）是主路径，beforeunload 只兜底。

### 5B. 主进程按 webContents 销毁清扫（P2，可选加固）

渲染器崩溃时 5A 不执行。补丁点 chat.ts：
- 现有 `chatAbortControllers = new Map<number, AbortController>()`（:107）旁加属主索引：
```ts
const chatOwnerByRequestId = new Map<number, number>(); // requestId -> wc.id
// trackChatRequest（:112 附近）写入；releaseChatRequest 删除
```
- registerAiIpc.ts 注册期对每个传入 webContents（handler 的 evt.sender）：
```ts
evt.sender.once("destroyed", () => {
  for (const [rid, ownerId] of chatOwnerByRequestId) {
    if (ownerId === evt.sender.id) abortChatRequest(rid);
  }
});
```
TTS 主进程合成队列同理按发起 wc.id 在 destroyed 时取消该来源。
> 该方案为可选：仅崩溃/强杀场景才有差异，正常关窗 5A 已覆盖。建议单列为一个提交，评审通过后再做。

## 验证
- AI 回答生成中点窗口 × → 主进程日志显示 abort、不再收到 chunk；关窗瞬间无异常 toast。
- 朗读中关窗 → 音频立即停止。
- 正常完成的对话不受影响（done 时已从 Set 移除，abort 集合为空）。

---

# T6（C1）书源增删改跨窗广播

## 锚点
- 写操作 4 个：registerBookSourceIpc.ts:98(save)、:111(delete)、:117(toggle)、:236(applyCustomOrders)，另有 importCommit(:129)。
- 已有"主进程定向推送"范式：bookSourceToast.ts:17 `win.webContents.send(BOOK_SOURCE_IPC.toast, payload)`。
- 渲染书源列表加载：BookSourcePanel 挂载时查询；编辑保存成功在 EditBookSourcePanel emit done。

## 补丁（3 处）

**① shared/bookSource/ipc.ts 增事件常量（与 toast 并列）**
```ts
/** 书源库被任意窗口写操作改变：其他窗口收到后刷新列表（不回传数据，只发 changed 信号） */
sourcesChanged: "bookSource:sourcesChanged",
```

**② registerBookSourceIpc.ts 写操作成功后广播（排除发起窗，避免它打断正在进行的编辑）**
```ts
function broadcastSourcesChanged(senderId: number, reason: string) {
  for (const w of BrowserWindow.getAllWindows()) {
    if (w.isDestroyed() || w.webContents.id === senderId) continue;
    w.webContents.send(BOOK_SOURCE_IPC.sourcesChanged, { reason, at: Date.now() });
  }
}
// save 成功 return 前、delete 后、toggle 后、applyCustomOrders 成功后、importCommit 后各调一次
```
注意：只广播给"找书窗"。可在发送前用 windowFactory 的 findBookWindowByWindowId 谓词过滤（registerBookSourceIpc 已能拿到窗口判定工具，沿用 isXxxWindow 模式），避免主窗无谓唤醒。

**③ preload 暴露订阅 + BookSourcePanel 响应**
```ts
onBookSourceSourcesChanged: (fn) => {
  const h = (_e: unknown, p: unknown) => fn(p as { reason: string });
  ipcRenderer.on(BOOK_SOURCE_IPC.sourcesChanged, h);
  return () => ipcRenderer.off(BOOK_SOURCE_IPC.sourcesChanged, h);
},
```
BookSourcePanel.vue：
```ts
onMounted(() => {
  offChanged = window.colorTxt.onBookSourceSourcesChanged((p) => {
    // 编辑面板打开时不打断（EditBookSourcePanel 是模态）；仅刷新列表数据
    if (!editPanelOpen.value) void reloadSourceList({ preserveSelection: true });
    else pendingRefreshAfterEditClose.value = true;   // 编辑关闭后补刷
  });
});
onBeforeUnmount(() => offChanged?.());
```
书架封面/启用态若有内存缓存，同样在该事件后失效相关查询缓存（最小范围：书源管理列表 + 搜索页书源选择器）。

## 验证
- A 窗新建书源 → B 窗书源管理自动出现；A 删除 → B 行消失；A 调顺序 → B 重排。
- B 窗正开着某书源编辑框时收到广播不打断、不覆盖未保存表单，关闭后补刷。
- 发起窗自身不收到事件（无重复加载）。

## 回滚
新通道独立；移除广播与订阅即可，原有查询加载路径不受影响。

---

# T7（C4/电源）显示器热插拔与休眠恢复

## 7A. 显示器热插拔（主进程）

**锚点**：index.ts:87 app.whenReady；取色器每屏建窗 eyedropper.ts；窗口 bounds 持久化 windowFactory.ts:218-226；摸鱼 bounds 钳制 stealthReader.ts:595-597 已有 clampBoundsToDisplay 可复用。

**补丁（index.ts whenReady 内）**
```ts
import { screen } from "electron";
screen.on("display-removed", () => {
  // 窗口可能落在已拔出的屏（负坐标/越界）：逐个钳回现存显示器工作区
  for (const w of BrowserWindow.getAllWindows()) {
    if (w.isDestroyed()) continue;
    clampWindowIntoNearestDisplay(w);   // 新工具函数，逻辑同 clampBoundsToDisplay
  }
  destroyEyedropperOverlays();          // 覆盖窗按旧屏幕集建立，直接重建
});
screen.on("display-added", () => {
  // 无需移动窗口；下次唤起取色器自然覆盖新屏。仅记录日志
});
screen.on("display-metrics-changed", () => {
  // DPI/分辨率变化：Monaco 自适配；摸鱼透明窗重算一次 bounds 钳制
  for (const w of BrowserWindow.getAllWindows()) {
    if (!w.isDestroyed() && isStealthReaderWindow(w)) clampWindowIntoNearestDisplay(w);
  }
});
```
`clampWindowIntoNearestDisplay`：getDisplayNearestPoint(w.getBounds()) → 若 bounds 与 workArea 无交集则 setBounds 到 workArea 内（保持宽高，取 min）。

**取色器**：display-removed 时 destroyEyedropperOverlays 即可（取色器是短生命周期，用户下次唤起重建）。

## 7B. 休眠恢复（番茄钟/TTS/定时滚动）

**现状**：无 powerMonitor（已验证）。番茄钟若用 Date 差值计时休眠后"跳秒"属预期；真正风险是 TTS 的网络流与 WebDAV 长连接。

**补丁（主进程广播 + 渲染重置）**
```ts
import { powerMonitor } from "electron";
powerMonitor.on("resume", () => {
  for (const w of BrowserWindow.getAllWindows()) {
    if (!w.isDestroyed()) w.webContents.send("system:resumed");
  }
});
```
preload 增 `onSystemResumed`；渲染层：
- useVoiceRead：收到后若处于播放态，重置当前句合成（cancel + 重新合成当前行），避免 socket 已死导致"显示播放中但无声"；
- 番茄钟/定时滚动：确认基于时间戳差值（而非 setInterval 计数）即可，无需改；若为计数式则在 resume 时重算基准。
- WebDAV 同步面板：下次手动操作自然重建连接，不主动处理。

## 验证
- 副屏放窗 → 拔掉副屏（或 Win+P 切仅主屏）→ 窗回到主屏可见区。
- 朗读中合盖 10 秒再开 → 声音自动恢复或状态正确变为暂停（二选一，按实现定）。

## 优先级说明
7A 用户可感知（窗口丢失），P2 中靠前；7B 在桌面端触发率低，可只做 powerMonitor 广播骨架，语音重置按反馈再补。

---

# T8 事件路由：回归测试矩阵 + dev 追踪（不改生产逻辑）

## 结论
第一部分（事件路由）经核实**设计自洽，无功能缺陷**：L0 拦截、两套覆盖层状态、处理函数查询退让、400ms 抑制标记构成完整仲裁。生产代码不建议改动（任何"统一仲裁器"重构都是高风险无收益）。补的是**防回归**。

## 8A. dev-only 事件追踪开关（新增，不影响打包）

新文件 `src/renderer/src/services/inputRouteTrace.ts`：
```ts
// 仅在 URL 参数 ?inputTrace=1 或 localStorage colortxt:inputTrace=1 时输出
const TRACE_KEYS = ["keydown", "pointerdown", "contextmenu", "wheel"];
export function installInputRouteTrace() {
  if (!localStorage.getItem("colortxt:inputTrace")) return;
  for (const type of TRACE_KEYS) {
    window.addEventListener(type, (e) => {
      const t = e.target instanceof Element ? e.target.closest("[class]")?.className : null;
      // eslint-disable-next-line no-console
      console.debug(`[route] ${type}`, {
        defaultPrevented: e.defaultPrevented,
        modalDepth: Number(document.querySelectorAll(".appModalBackdrop").length),
        target: typeof t === "string" ? t.slice(0, 60) : null,
      });
    }, true);   // 捕获最外层，只观察不阻断
  }
}
```
在 main.ts/findBookMain.ts 开发模式调用。作用：今后任何交互回归（"按键没反应/点穿了"）可一眼看到事件到达时的覆盖层深度。

## 8B. 手工回归矩阵（纳入发版 checklist，对应方法论文档 1.6）

| 编号 | 前置态 | 操作 | 期望 |
|------|--------|------|------|
| R1 | 更多菜单打开 | 按任意快捷键 | 菜单关闭前快捷键全不执行（shortcutService:251） |
| R2 | 模态 A 上叠模态 B | Esc×N | 只关 B 再关 A，不穿透到下层/全屏 |
| R3 | 灯箱打开时打开模态 | Esc | 先关模态后关灯箱（escBeforeModal 优先级） |
| R4 | 禁 Esc 模态（escClosable=false） | Esc | 不关窗，事件可到内部输入控件 |
| R5 | 点击翻页模式 + 右键菜单打开 | 菜单外左键 | 菜单关、本次不翻页（400ms 抑制） |
| R6 | 朗读滚动锁定 | ↓/PageDown/Ctrl+← | 被吞，视图不动 |
| R7 | 朗读中焦点在搜索框 | 空格 | 正常打字空格，不触发暂停 |
| R8 | 全屏+弹层 | 左键弹层外 | 浮层先关，不翻页不退出全屏 |
| R9 | 找书阅读器打开 | F5/F6/F7 与 ↑/Ctrl+→ | 6 个面板键可用，其余走阅读器 |
| R10 | 编辑模式焦点在 Monaco | ↑↓/Ctrl+F | Monaco 默认行为，窗口动作让位 |
| R11 | 摸鱼会话中源窗关闭 | — | 摸鱼窗连带销毁、全局键注销、无残留进程 |
| R12 | 摸鱼设置窗打开后关 | — | 录制挂起的全局键恢复（onSettingsWindowClosed） |

---

## 落地顺序建议

1. **第一批（P0，互不冲突）**：T1 → T2 → T3。三者文件无重叠（T1 找书窗渲染、T2 bookSource、T3 file 链）。
2. **第二批（P1）**：T6（独立通道）→ T4（小改）→ T5（面板 onBeforeUnmount，注意与 T1 同测关窗路径但代码不重叠）。
3. **第三批（P2）**：T7A → T7B → T8。
4. 每批完成后跑 8B 矩阵相关行；T1/T5 都涉及关窗，合验 R11/R12。

## 不在本次范围（避免范围漂移）
- 触控/触屏统一适配（需产品决策，属功能而非缺陷修复）。
- 编辑态三方合并、下载失败章自动断点续传重试（需要新 UI，另立项）。
- localStorage 配额溢出的用户提示（低发，建议随 cacheStore 改造统一做）。

---

*所有补丁均基于 2026-09-22 源码行号锚定；行号随版本漂移时以函数名/常量名为准定位。*
