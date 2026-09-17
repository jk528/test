<script setup lang="ts">
// 红楼梦阅读分析一体化 — M1 主界面
// 布局：顶部工具栏 | 左栏（回目树 + 书签） | 阅读区
import { computed, onMounted, ref } from "vue";
import Reader from "./components/Reader.vue";
import ChapterTree from "./components/ChapterTree.vue";
import AiPanel from "./components/AiPanel.vue";
import PanoramaPanel from "./components/PanoramaPanel.vue";
import {
  parseChapters,
  chapterAtLine,
  type Chapter,
} from "./lib/chapters";
import {
  isTauri,
  readTextFile,
  probeDefaultBook,
  pickTextFile,
} from "./lib/tauri";
import {
  loadBookmarks,
  toggleBookmark,
  removeBookmarkAt,
  persistBookmarks,
  type Bookmark,
} from "./lib/annotations";
import {
  analyzeSentiment,
  analyzeChapters,
  prepareStatus,
  prepareBook,
  listChapterEmotions,
  saveBook,
  buildIndex,
  indexStatus,
  upsertEmotions,
  getChapterEmotions,
  upsertAnnotation,
  listAnnotations,
  deleteAnnotation,
  importAnalysis,
  overview,
  getEntity,
  listMentions,
  ENTITY_CLASSES,
  type EmotionSpan,
  type ChapterEmotion,
  type ChapterEmotionRow,
  type EntitySpan,
  type Overview,
} from "./lib/sidecar";

const reader = ref<InstanceType<typeof Reader> | null>(null);
const aiPanel = ref<InstanceType<typeof AiPanel> | null>(null);

const filePath = ref("");
const rawText = ref("");
const chapters = ref<Chapter[]>([]);
const bookmarks = ref<Bookmark[]>([]);
const activeChapter = ref(0);
const loading = ref(false);
const errorMsg = ref("");
const sidebarTab = ref<"toc" | "marks" | "pano">("toc");
// M3：AI 问答面板 + SQLite 书目 ID
const showAi = ref(false);
const bookId = ref("");
// M2 情感分析（视口驱动 + 缓存）
const currentEmotions = ref<EmotionSpan[]>([]);
const emotionBaseLine = ref(0);
const analyzing = ref(false);
// M4.5：全书预处理（分析前置）—— 跑一次，之后阅读直接吃库
const preparing = ref(false);
const prepareProgress = ref("");
// 最近一次视口范围（0 基物理行），预处理完成后按它把结果灌回缓存
const lastView = ref<[number, number]>([0, 0]);
const showEmotions = ref(true);
const chapterEmotions = ref<ChapterEmotion[]>([]);
// 视口缓存：key = 绝对物理行号，value = EmotionSpan（line_offset 存绝对行号）
const emotionCache = new Map<number, EmotionSpan>();
// 已分析行集合（含无情感词的行，避免重复请求 sidecar）
const analyzedLines = new Set<number>();
// M3 持久化：已从 SQLite 回放过的章（0 基），避免反复查库
const dbLoadedChapters = new Set<number>();
// M3 标注：物理行 → SQLite annotations.id（删除时需要）
const annotationIds = new Map<number, number>();
// M4 全景：统计 / 回灌状态 / 人物高亮
const panoOverview = ref<Overview | null>(null);
const panoStatus = ref("");
const showEntities = ref(true);
const activeEntity = ref<string | null>(null);
/** 选中人物的全部出场（含各章），按当前章过滤后交给 Reader */
const entitySpansAll = ref<EntitySpan[]>([]);

/** 只把当前章（含下一章缓冲）的高亮片段交给 Reader，避免上千条装饰拖慢滚动 */
const entitySpans = computed(() => {
  const all = entitySpansAll.value;
  if (!all.length) return [];
  const idx = Math.max(0, activeChapter.value - 1);
  const lo = chapters.value[idx]?.line ?? 0;
  const hi = chapters.value[Math.min(idx + 1, chapters.value.length - 1)]?.line ?? lo;
  return all.filter((s) => s.line >= lo && s.line <= hi);
});

const physicalLines = computed(() => rawText.value.split("\n"));
const fileName = computed(() => {
  if (!filePath.value) return "";
  return filePath.value.split(/[\\/]/).pop() || filePath.value;
});

function linePreview(line0: number): string {
  const l = physicalLines.value[line0] ?? "";
  return l.replace(/^[\s　]+/, "").slice(0, 24);
}

function chapterLabel(line0: number): string {
  const idx = chapterAtLine(chapters.value, line0);
  if (idx <= 0) return "正文前";
  const ch = chapters.value[idx - 1];
  return `第${ch.numberText}${ch.unit}`;
}

/** 物理行 → 0 基章序号；正文前（未落在任何章）返回 -1，不落库。 */
function chapterIdxOfLine(line0: number): number {
  const idx1 = chapterAtLine(chapters.value, line0);
  return idx1 > 0 ? idx1 - 1 : -1;
}

/**
 * 回放某章已持久化的情感结果（M3）。
 * 未命中过才查库；命中则灌入缓存并标记为已分析，视口渲染时直接上色，
 * 不必重新跑一遍 jieba 分词 + 情感分析。
 */
async function loadChapterEmotionsFromDb(chapterIdx: number): Promise<number> {
  const bid = bookId.value;
  if (!bid || chapterIdx < 0 || dbLoadedChapters.has(chapterIdx)) return 0;
  dbLoadedChapters.add(chapterIdx);
  try {
    const { rows } = await getChapterEmotions(bid, chapterIdx);
    for (const r of rows) {
      const line = r.line_start;
      emotionCache.set(line, {
        line_offset: line,
        dutir_top: r.dutir_top,
        polarity: r.polarity,
        intensity: r.intensity,
        weights: r.weights ?? {},
        word_spans: r.word_spans ?? [],
      });
      analyzedLines.add(line);
    }
    return rows.length;
  } catch {
    dbLoadedChapters.delete(chapterIdx); // 失败不标记，下次再试
    return 0;
  }
}

/** 把本批分析结果按章写入 SQLite（增量、幂等，失败不影响阅读）。 */
function persistEmotions(spans: EmotionSpan[]): void {
  const bid = bookId.value;
  if (!bid || spans.length === 0) return;
  const byChapter = new Map<number, typeof spans>();
  for (const sp of spans) {
    const ci = chapterIdxOfLine(sp.line_offset);
    if (ci < 0) continue;
    const bucket = byChapter.get(ci);
    if (bucket) bucket.push(sp);
    else byChapter.set(ci, [sp]);
  }
  for (const [ci, list] of byChapter) {
    void upsertEmotions(
      bid,
      ci,
      list.map((s) => ({
        line_start: s.line_offset,
        line_end: s.line_offset,
        dutir_top: s.dutir_top,
        polarity: s.polarity,
        intensity: s.intensity,
        weights: s.weights,
        word_spans: s.word_spans ?? [],
      }))
    ).catch(() => {
      // 落库失败只影响下次能否复用，不打断阅读
    });
  }
}

/**
 * 建向量索引（幂等）。先问库现状，只有缺失/内容变了才真跑嵌入。
 * 旧实现每次打开书都无条件重建，228 分块白跑一遍，还反复制造向量孤儿。
 */
async function syncIndex(bid: string, text: string): Promise<void> {
  try {
    const st = await indexStatus(bid, text, chapters.value);
    if (!st.need_rebuild) return;
    await buildIndex({ book_id: bid, text, chapters: chapters.value });
  } catch (e) {
    console.warn("[RAG] 向量索引同步失败（不影响阅读与检索降级）：", e);
  }
}

/** 载入书签：SQLite 为权威源，localStorage 作首屏显示与离线兜底。 */
async function loadAnnotationsFromDb(bid: string, path: string): Promise<void> {
  const local = loadBookmarks(path);
  try {
    const { annotations } = await listAnnotations(bid, "bookmark");
    const rows = annotations as
      { id: number; line_start: number; note: string; created_at: number }[];
    if (rows.length === 0) {
      // 库里还没有：把本地存量迁移上去（一次性）
      for (const b of local) {
        const r = await upsertAnnotation({
          book_id: bid,
          kind: "bookmark",
          chapter_idx: chapterIdxOfLine(b.line),
          line_start: b.line,
          line_end: b.line,
          text: linePreview(b.line),
          note: b.note,
        });
        annotationIds.set(b.line, r.id);
      }
      bookmarks.value = local;
      return;
    }
    const list: Bookmark[] = rows.map((r) => ({
      id: `db-${r.id}`,
      line: r.line_start,
      note: r.note || "",
      createdAt: (r.created_at || 0) * 1000,
    }));
    list.sort((a, b) => a.line - b.line);
    bookmarks.value = list;
    persistBookmarks(path, list);
  } catch {
    bookmarks.value = local; // sidecar 未就绪时退回本地
  }
}

/**
 * M4：加载全景数据。库为空时自动回灌既有 120 章 V3.4 报告。
 * 回灌是一次性重活（实测 ~3.7s），后台走，不挡阅读。
 */
async function loadPanorama(bid: string, text: string): Promise<void> {
  if (!bid) return;
  try {
    panoOverview.value = await overview(bid);
    if (panoOverview.value.events === 0) {
      panoStatus.value = "回灌既有分析报告…";
      const st = await importAnalysis(bid, text);
      panoOverview.value = await overview(bid);
      panoStatus.value =
        `已回灌 ${st.events} 事件 / ${st.entities} 人物 / ${st.foreshadows} 伏笔`;
      setTimeout(() => (panoStatus.value = ""), 4000);
    }
  } catch (e) {
    panoStatus.value = `全景数据加载失败：${String(e).slice(0, 80)}`;
  }
}

/** 选中人物 → 取全部出场并转成正文高亮片段（配色按实体 id 轮转）。 */
async function onPickEntity(canonical: string | null): Promise<void> {
  activeEntity.value = canonical;
  entitySpansAll.value = [];
  if (!canonical || !bookId.value) return;
  try {
    const card = await getEntity(bookId.value, canonical);
    const cls = ENTITY_CLASSES[card.entity.id % ENTITY_CLASSES.length];
    const { mentions } = await listMentions(bookId.value, undefined, card.entity.id, 4000);
    entitySpansAll.value = mentions.map((m) => ({
      line: m.line_start,
      charStart: m.char_start,
      charEnd: m.char_end,
      cls,
      name: `${m.surface}（${canonical}）`,
    }));
    showEntities.value = true;
  } catch (e) {
    console.warn("[M4] 人物高亮失败：", e);
  }
}

async function loadBook(path: string) {
  loading.value = true;
  errorMsg.value = "";
  try {
    const text = await readTextFile(path);
    filePath.value = path;
    rawText.value = text;
    chapters.value = parseChapters(text);
    bookmarks.value = loadBookmarks(path);
    activeChapter.value = chapters.value.length ? 1 : 0;
    // 切书清空全部按书缓存的派生状态，避免旧书残留污染新书
    emotionCache.clear();
    analyzedLines.clear();
    dbLoadedChapters.clear();
    annotationIds.clear();
    currentEmotions.value = [];
    emotionBaseLine.value = 0;
    bookId.value = "";
    panoOverview.value = null;
    panoStatus.value = "";
    activeEntity.value = null;
    entitySpansAll.value = [];
    preparing.value = false;
    prepareProgress.value = "";
    lastView.value = [0, 0];
    if (chapters.value.length > 0) {
      // M3：写 SQLite 主库拿 book_id（rawText 已赋值，不阻塞正文显示）
      try {
        const r = await saveBook({
          title: fileName.value || "红楼梦",
          source_path: path,
          text,
        });
        bookId.value = r.book_id;
        // 索引与书签都在后台走，不挡阅读
        void syncIndex(r.book_id, text);
        void loadPanorama(r.book_id, text);
        await loadAnnotationsFromDb(r.book_id, path);
        // M4.5：全书预处理（分析前置）—— 已备秒回，缺则分片补
        void syncPrepare(r.book_id, text);
      } catch (e) {
        // sidecar 未就绪：阅读功能照常，仅失去持久化能力
        bookId.value = "";
        console.warn("[M3] 主库写入失败：", e);
        // 无主库时退回 M2 的实时分析，保证仍能着色
        void analyzeAllChapters();
      }
      // 先回放已存情感，再补算缺口（引擎懒加载预热也在这一轮完成）
      void loadChapterEmotionsFromDb(0).then(() => analyzeViewport(0, 40));
    }
  } catch (e) {
    errorMsg.value = String(e);
  } finally {
    loading.value = false;
  }
}

async function openFile() {
  const p = await pickTextFile();
  if (p) await loadBook(p);
}

function selectChapter(index1: number) {
  const ch = chapters.value[index1 - 1];
  if (!ch) return;
  activeChapter.value = index1;
  // 切章立即预分析目标章首屏，不等 revealLine 滚动到位才触发
  // 这样平滑滚动到位时首屏多已在缓存，renderViewport 立即上色无延迟
  void analyzeViewport(ch.line, ch.line + 40);
  reader.value?.revealLine(ch.line);
  // revealLine 触发的 view-range 会再补一次渲染（从缓存取已分析行）
}

// 分析序号：连续滚动时丢弃过时调用的渲染（缓存照存，避免竞争渲染）
let analysisSeq = 0;
// 预取行数：视口上下各 prefetch 行，让小幅滚动提前命中缓存
const PREFETCH = 40;

/** 从缓存同步渲染可见范围（已分析行立即上色，不延迟、不丢色）。 */
function renderViewport(lineStart: number, lineEnd: number) {
  if (lineStart < 0 || lineEnd < lineStart) return;
  const total = physicalLines.value.length;
  const visEnd = Math.min(lineEnd, total - 1);
  const visible: EmotionSpan[] = [];
  for (let l = lineStart; l <= visEnd; l++) {
    const sp = emotionCache.get(l);
    if (sp) visible.push({ ...sp, line_offset: l - lineStart });
  }
  currentEmotions.value = visible;
  emotionBaseLine.value = lineStart;
}

/** M2：后台分析视口（含预取范围），结果存缓存，完成后补渲染。 */
async function analyzeViewport(lineStart: number, lineEnd: number) {
  if (lineStart < 0 || lineEnd < lineStart) return;
  const seq = ++analysisSeq;
  const total = physicalLines.value.length;
  // 预取范围：视口上下各 PREFETCH 行，小幅滚动时新行已在缓存
  const pfStart = Math.max(0, lineStart - PREFETCH);
  const pfEnd = Math.min(total - 1, lineEnd + PREFETCH);
  // 找未分析过的行（缓存驱动：已分析行不重复送 sidecar）
  const unanalyzed: number[] = [];
  for (let l = pfStart; l <= pfEnd; l++) {
    if (!analyzedLines.has(l)) unanalyzed.push(l);
  }
  if (unanalyzed.length === 0 || preparing.value) {
    // 全在缓存里，无需 sidecar，直接渲染（最新序号才渲染）
    if (seq === analysisSeq) renderViewport(lineStart, lineEnd);
    return;
  }
  analyzing.value = true;
  errorMsg.value = "";
  try {
    // 把未分析行的文本拼成 sidecar 输入（line_offset 是相对此输入的 0 基偏移）
    const text = unanalyzed.map((l) => physicalLines.value[l]).join("\n");
    const spans = await analyzeSentiment(text);
    // 结果按绝对行号存缓存（line_offset 改写为绝对行号，便于跨视口复用）
    for (const sp of spans) {
      const absLine = unanalyzed[sp.line_offset];
      if (absLine === undefined) continue;
      emotionCache.set(absLine, { ...sp, line_offset: absLine });
    }
    // 标记这批行为已分析（含无情感词的行，避免重复请求）
    for (const l of unanalyzed) analyzedLines.add(l);
    // M3：写库，重启后可直接回放，不必重算
    persistEmotions(spans.map((sp) => ({
      ...sp,
      line_offset: unanalyzed[sp.line_offset] ?? sp.line_offset,
    })));
    // 仅最新序号触发渲染：中间调用的结果已进缓存，渲染交给最新序号
    if (seq === analysisSeq) renderViewport(lineStart, lineEnd);
  } catch (e) {
    if (seq === analysisSeq) errorMsg.value = `情感分析失败: ${e}`;
  } finally {
    if (seq === analysisSeq) analyzing.value = false;
  }
}

function onViewRange(lineStart: number, lineEnd: number) {
  activeChapter.value = chapterAtLine(chapters.value, lineStart);
  lastView.value = [lineStart, lineEnd];
  // 立即从缓存渲染（已分析行不延迟、不丢色），后台再分析未分析行
  renderViewport(lineStart, lineEnd);
  // M4.5：已预处理的章从库按章回放（每章只查一次），之后滚动零请求
  const ci = chapterIdxOfLine(lineStart);
  if (ci >= 0) {
    void loadChapterEmotionsFromDb(ci).then((n) => {
      if (n > 0) renderViewport(lineStart, lineEnd);
    });
  }
  void analyzeViewport(lineStart, lineEnd);
}

/**
 * M4.5：章级情感 —— 优先读预处理产物（库），失败或为空时退回实时批量分析。
 * 目录着色因此不再需要每次开书都跑一遍全书 jieba。
 */
async function loadChapterEmotionsFromDbAll(bid: string): Promise<boolean> {
  try {
    const rows = await listChapterEmotions(bid);
    if (!rows.length) return false;
    chapterEmotions.value = rows.map((r: ChapterEmotionRow) => ({
      index: r.chapter_idx + 1,
      dutir_top: r.dutir_top,
      polarity: r.polarity,
      intensity: r.intensity,
      weights: r.weights ?? {},
    }));
    return true;
  } catch {
    return false;
  }
}

/**
 * M4.5：全书预处理 —— 把分析前置到开书时，读的时候直接吃库。
 *
 * 已备好 → 秒回（实测 <20ms），直接读库着色；
 * 未备好 → 按 20 章一片跑，顶栏报进度（全书约 13s，只跑一次）。
 * 跑完把当前视口从库灌回缓存，之后滚动不再发起任何分析请求。
 */
async function syncPrepare(bid: string, text: string): Promise<void> {
  try {
    const st = await prepareStatus(bid, chapters.value.length);
    if (!st.ready) {
      preparing.value = true;
      const total = chapters.value.length;
      const BATCH = 20;
      for (let from = 0; from < total; from += BATCH) {
        const to = Math.min(from + BATCH - 1, total - 1);
        prepareProgress.value = `${to + 1}/${total} 章`;
        await prepareBook({
          book_id: bid,
          text,
          chapters: chapters.value,
          chapter_from: from,
          chapter_to: to,
        });
      }
      preparing.value = false;
      prepareProgress.value = "";
    }
    await loadChapterEmotionsFromDbAll(bid);
    // 预处理产物已入库：清掉「已回放」标记，把当前视口从库灌回缓存
    dbLoadedChapters.clear();
    const [ls, le] = lastView.value;
    const ci = Math.max(0, chapterIdxOfLine(ls));
    await loadChapterEmotionsFromDb(ci);
    renderViewport(ls, le);
  } catch (e) {
    preparing.value = false;
    prepareProgress.value = "";
    console.warn("[M4.5] 全书预处理失败（退回实时分析）：", e);
  }
}

/** M2：批量分析全章主导情绪（目录着色，不阻塞正文分析）。 */
async function analyzeAllChapters() {
  try {
    const emotions = await analyzeChapters(rawText.value, chapters.value);
    chapterEmotions.value = emotions;
  } catch (e) {
    // 目录着色失败不影响阅读，静默
    chapterEmotions.value = [];
  }
}

function onToggleBookmark(line0: number) {
  // localStorage 先行：UI 立即响应，且在 sidecar 未就绪时仍可用
  const { list, active } = toggleBookmark(filePath.value, line0);
  bookmarks.value = list;
  const bid = bookId.value;
  if (!bid) return;
  // M3：SQLite 为权威源，双写（失败只记日志，不影响已生效的书签）
  if (active) {
    void upsertAnnotation({
      book_id: bid,
      kind: "bookmark",
      chapter_idx: chapterIdxOfLine(line0),
      line_start: line0,
      line_end: line0,
      text: linePreview(line0),
    })
      .then((r) => annotationIds.set(line0, r.id))
      .catch((e) => console.warn("[标注] 写库失败：", e));
  } else {
    void deleteBookmarkInDb(line0);
  }
}

/** 删除某行书签的 SQLite 记录（本地已删，这里只补库侧）。 */
async function deleteBookmarkInDb(line0: number): Promise<void> {
  const bid = bookId.value;
  if (!bid) return;
  try {
    let id = annotationIds.get(line0);
    if (id === undefined) {
      // 极端情况（跨会话、id 未回填）：按行反查一次
      const { annotations } = await listAnnotations(bid, "bookmark");
      const hit = (annotations as { id: number; line_start: number }[]).find(
        (a) => a.line_start === line0
      );
      id = hit?.id;
    }
    if (id !== undefined) {
      await deleteAnnotation(id);
      annotationIds.delete(line0);
    }
  } catch (e) {
    console.warn("[标注] 删除库记录失败：", e);
  }
}

function gotoBookmark(b: Bookmark) {
  activeChapter.value = chapterAtLine(chapters.value, b.line);
  reader.value?.revealLine(b.line);
}

function removeBookmark(b: Bookmark) {
  bookmarks.value = removeBookmarkAt(filePath.value, b.line);
  void deleteBookmarkInDb(b.line);
}

// M3：AI 面板相关
function onAiSelected(text: string) {
  if (showAi.value) aiPanel.value?.pickQuestion(text);
}

function onAiJump(line0: number) {
  activeChapter.value = chapterAtLine(chapters.value, line0);
  reader.value?.revealLine(line0);
}

onMounted(async () => {
  if (!isTauri) {
    errorMsg.value =
      "当前为普通浏览器预览，无法读取本地文件。请运行 pnpm tauri dev 在桌面窗口中使用。";
    return;
  }
  const def = await probeDefaultBook();
  if (def) await loadBook(def);
});
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">📖 红楼梦阅读分析</div>
      <div class="topbar-meta">
        <span v-if="fileName" class="fname">{{ fileName }}</span>
        <span v-if="chapters.length" class="stat"
          >共 {{ chapters.length }} 回 · {{ physicalLines.length }} 行</span
        >
        <span v-if="preparing" class="stat">预析 {{ prepareProgress }}</span>
        <span v-if="analyzing" class="stat">情感分析中…</span>
      </div>
      <button class="btn primary" :disabled="loading" @click="openFile">
        {{ loading ? "加载中…" : "打开 TXT" }}
      </button>
      <button
        class="btn"
        :class="{ active: showAi }"
        :disabled="!rawText"
        @click="showAi = !showAi"
      >
        AI
      </button>
    </header>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <main class="main">
      <aside class="sidebar">
        <div class="tabs">
          <button
            :class="{ on: sidebarTab === 'toc' }"
            @click="sidebarTab = 'toc'"
          >
            回目
          </button>
          <button
            :class="{ on: sidebarTab === 'marks' }"
            @click="sidebarTab = 'marks'"
          >
            书签 ({{ bookmarks.length }})
          </button>
          <button
            :class="{ on: sidebarTab === 'pano' }"
            @click="sidebarTab = 'pano'"
          >
            全景{{ panoOverview ? ` ${panoOverview.events}` : "" }}
          </button>
        </div>

        <div v-show="sidebarTab === 'toc'" class="tab-panel">
          <ChapterTree
            :chapters="chapters"
            :active-index="activeChapter"
            :chapter-emotions="chapterEmotions"
            :show-emotions="showEmotions"
            @select="selectChapter"
          />
        </div>

        <div v-show="sidebarTab === 'pano'" class="tab-panel">
          <div v-if="panoStatus" class="pano-status">{{ panoStatus }}</div>
          <PanoramaPanel
            v-if="bookId"
            :book-id="bookId"
            :chapters="chapters"
            :active-entity="activeEntity"
            @jump="onAiJump"
            @pick-entity="onPickEntity"
          />
          <div v-else class="marks-empty">等待主库就绪…</div>
        </div>

        <div v-show="sidebarTab === 'marks'" class="tab-panel">
          <div class="marks-list">
            <div v-if="bookmarks.length === 0" class="marks-empty">
              还没有书签。
              <br />在正文最左侧灰色槽位点击即可添加/移除书签。
            </div>
            <div
              v-for="b in bookmarks"
              :key="b.id"
              class="mark-item"
              @click="gotoBookmark(b)"
            >
              <div class="mark-main">
                <span class="mark-ch">{{ chapterLabel(b.line) }}</span>
                <span class="mark-text">{{ linePreview(b.line) || "（空行）" }}</span>
              </div>
              <button
                class="mark-del"
                title="删除书签"
                @click.stop="removeBookmark(b)"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </aside>

      <section class="content">
        <Reader
          v-if="rawText"
          ref="reader"
          :text="rawText"
          :chapters="chapters"
          :bookmarks="bookmarks"
          :emotions="currentEmotions"
          :emotion-base-line="emotionBaseLine"
          :show-emotions="showEmotions"
          :entity-spans="entitySpans"
          :show-entities="showEntities"
          :entity-name="activeEntity ?? ''"
          @toggle-entities="showEntities = !showEntities"
          @view-range="onViewRange"
          @toggle-bookmark="onToggleBookmark"
          @toggle-emotions="showEmotions = !showEmotions"
          @text-selected="onAiSelected"
        />
        <AiPanel
          v-if="showAi && bookId"
          ref="aiPanel"
          class="ai-side"
          :book-id="bookId"
          :chapters="chapters"
          @jump="onAiJump"
        />
        <div v-if="!rawText" class="placeholder">
          <div class="ph-card">
            <div class="ph-title">红楼梦阅读分析一体化</div>
            <div class="ph-sub">M1 · 读起来</div>
            <button class="btn primary big" @click="openFile">打开《红楼梦.txt》</button>
            <div class="ph-hint">
              开发模式将自动定位到项目中的 红楼梦.txt；也可手动选择任意章节式 TXT。
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
