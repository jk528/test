<script setup lang="ts">
// 红楼梦阅读分析一体化 — M1 主界面
// 布局：顶部工具栏 | 左栏（回目树 + 书签） | 阅读区
import { computed, onMounted, ref } from "vue";
import Reader from "./components/Reader.vue";
import ChapterTree from "./components/ChapterTree.vue";
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
  type Bookmark,
} from "./lib/annotations";
import { analyzeSentiment, analyzeChapters, type EmotionSpan, type ChapterEmotion } from "./lib/sidecar";

const reader = ref<InstanceType<typeof Reader> | null>(null);

const filePath = ref("");
const rawText = ref("");
const chapters = ref<Chapter[]>([]);
const bookmarks = ref<Bookmark[]>([]);
const activeChapter = ref(0);
const loading = ref(false);
const errorMsg = ref("");
const sidebarTab = ref<"toc" | "marks">("toc");
// M2 情感分析（视口驱动 + 缓存）
const currentEmotions = ref<EmotionSpan[]>([]);
const emotionBaseLine = ref(0);
const analyzing = ref(false);
const showEmotions = ref(true);
const chapterEmotions = ref<ChapterEmotion[]>([]);
// 视口缓存：key = 绝对物理行号，value = EmotionSpan（line_offset 存绝对行号）
const emotionCache = new Map<number, EmotionSpan>();
// 已分析行集合（含无情感词的行，避免重复请求 sidecar）
const analyzedLines = new Set<number>();

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
    // 切书清空情感缓存，避免旧书残留污染新书视口
    emotionCache.clear();
    analyzedLines.clear();
    currentEmotions.value = [];
    emotionBaseLine.value = 0;
    // M2：批量分析全章主导情绪（目录着色，固定常量）
    // 正文视口分析由 Reader onMounted 后的初始 view-range 事件触发，不在加载期阻塞
    if (chapters.value.length > 0) {
      void analyzeAllChapters();
      // 预热首屏 + 触发 sidecar 引擎懒加载（_get_engine 首次 1-2s），
      // 这样 Reader onMounted 后初始 view-range 触发时引擎已就绪，首屏延迟显著降低
      void analyzeViewport(0, 40);
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
  if (unanalyzed.length === 0) {
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
  // 立即从缓存渲染（已分析行不延迟、不丢色），后台再分析未分析行
  renderViewport(lineStart, lineEnd);
  void analyzeViewport(lineStart, lineEnd);
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
  const { list } = toggleBookmark(filePath.value, line0);
  bookmarks.value = list;
}

function gotoBookmark(b: Bookmark) {
  activeChapter.value = chapterAtLine(chapters.value, b.line);
  reader.value?.revealLine(b.line);
}

function removeBookmark(b: Bookmark) {
  bookmarks.value = removeBookmarkAt(filePath.value, b.line);
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
        <span v-if="analyzing" class="stat">情感分析中…</span>
      </div>
      <button class="btn primary" :disabled="loading" @click="openFile">
        {{ loading ? "加载中…" : "打开 TXT" }}
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
          @view-range="onViewRange"
          @toggle-bookmark="onToggleBookmark"
          @toggle-emotions="showEmotions = !showEmotions"
        />
        <div v-else class="placeholder">
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
