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

const reader = ref<InstanceType<typeof Reader> | null>(null);

const filePath = ref("");
const rawText = ref("");
const chapters = ref<Chapter[]>([]);
const bookmarks = ref<Bookmark[]>([]);
const activeChapter = ref(0);
const loading = ref(false);
const errorMsg = ref("");
const sidebarTab = ref<"toc" | "marks">("toc");

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
  reader.value?.revealLine(ch.line);
}

function onViewLine(line0: number) {
  activeChapter.value = chapterAtLine(chapters.value, line0);
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
          @view-line="onViewLine"
          @toggle-bookmark="onToggleBookmark"
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
