<script setup lang="ts">
// 只读阅读器：Monaco 承载整篇文本，物理行作为唯一锚点。
// - 章节标题行高亮（与解析结果联动）
// - 书签行：glyph 角标 + 行底色，点击左侧 glyph 槽切换书签
// - M2：情感着色（七类情绪 → 七套低饱和底色，叠加在物理行上）
// - 滚动/定位均基于 0 基物理行（Monaco 内部为 1 基）
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { setupMonaco, monaco } from "../lib/monaco";
import { chapterAtLine, type Chapter } from "../lib/chapters";
import type { Bookmark } from "../lib/annotations";
import type { EmotionSpan, EntitySpan } from "../lib/sidecar";

const props = defineProps<{
  text: string;
  chapters: Chapter[];
  bookmarks: Bookmark[];
  /** 当前章段落级情感数据（line_offset 为章内 0-based 相对行） */
  emotions: EmotionSpan[];
  /** 当前章起始物理行（0-based），用于把 line_offset 映射到全局物理行 */
  emotionBaseLine: number;
  /** 是否显示情感着色 */
  showEmotions: boolean;
  /** M4 人物高亮：绝对物理行 + 行内字符偏移（全角字符按 1 个计） */
  entitySpans: EntitySpan[];
  /** 是否显示人物高亮 */
  showEntities: boolean;
  /** 当前高亮的人物名（空=未选中） */
  entityName: string;
  /** 阅读设置（彩读风格：字号/行高/字体/主题/左右留白/阅读尺） */
  settings: {
    fontSize: number;
    lineHeight: number;
    fontFamily: string;
    theme: "light" | "dark";
    paddingX: number;
    readingRuler: boolean;
  };
}>();

const emit = defineEmits<{
  // 视口驱动：可见行范围 [lineStart, lineEnd]（0 基物理行，含两端）
  (e: "view-range", lineStart: number, lineEnd: number): void;
  (e: "toggle-bookmark", line0: number): void;
  (e: "toggle-emotions"): void;
  // M3：正文中选中文本 → 外层可填入 AI 提问框
  (e: "text-selected", text: string): void;
  // M4：切换人物高亮显隐
  (e: "toggle-entities"): void;
}>();

// 七类情绪中文 → ASCII CSS 类名映射（Monaco decoration 丢非 ASCII 类名）
const EMO_CLASS_MAP: Record<string, string> = {
  好: "hl-emo-hao",
  乐: "hl-emo-le",
  哀: "hl-emo-ai",
  怒: "hl-emo-nu",
  惧: "hl-emo-ju",
  恶: "hl-emo-e",
  惊: "hl-emo-jing",
};
// 字级高亮类名（比整行背景更强：加粗 + 下划线 + 更深底色）
const EMO_WORD_CLASS_MAP: Record<string, string> = {
  好: "hl-word-hao",
  乐: "hl-word-le",
  哀: "hl-word-ai",
  怒: "hl-word-nu",
  惧: "hl-word-ju",
  恶: "hl-word-e",
  惊: "hl-word-jing",
};

const container = ref<HTMLDivElement | null>(null);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;
let decoColl: monaco.editor.IEditorDecorationsCollection | null = null;
let scrollRaf = 0;
let removeResizeListener: (() => void) | null = null;
// 彩读风格：阅读区顶部常驻当前章节标题
const stickyLabel = ref("");
// 阅读尺：当前光标行（Monaco 1-based），开启时高亮该行
let rulerLine = 1;

setupMonaco();

function applyTheme(t: "light" | "dark") {
  monaco.editor.setTheme(t === "dark" ? "honglou-read-dark" : "honglou-read");
}

/** 滚动/跳转后更新顶部粘性章节标题。line1 为 Monaco 1-based 可见行。 */
function updateSticky(line1: number) {
  const idx = chapterAtLine(props.chapters, line1 - 1);
  if (idx > 0) {
    const ch = props.chapters[idx - 1];
    const label = ch.title.trim().replace(/\s+/g, " ");
    stickyLabel.value = label || `第${ch.numberText}${ch.unit}`;
  } else {
    stickyLabel.value = "";
  }
}

function applySettings() {
  if (!editor) return;
  const s = props.settings;
  editor.updateOptions({
    fontSize: s.fontSize,
    lineHeight: s.lineHeight,
    fontFamily: s.fontFamily,
    padding: { top: 16, bottom: 120, left: s.paddingX, right: s.paddingX },
  });
  applyTheme(s.theme);
  renderDecorations();
}

onMounted(() => {
  if (!container.value) return;
  editor = monaco.editor.create(container.value, {
    value: props.text,
    readOnly: true,
    theme: props.settings.theme === "dark" ? "honglou-read-dark" : "honglou-read",
    automaticLayout: true,
    fontSize: props.settings.fontSize,
    lineHeight: props.settings.lineHeight,
    fontFamily: props.settings.fontFamily,
    wordWrap: "on",
    wrappingStrategy: "advanced",
    wrappingIndent: "same",
    lineNumbers: "on",
    lineNumbersMinChars: 3,
    glyphMargin: true,
    folding: false,
    minimap: { enabled: false },
    scrollBeyondLastLine: true,
    smoothScrolling: true,
    renderWhitespace: "none",
    // 正文以全角空格（U+3000）缩进，中文小说常见，关闭不可见字符高亮与横幅
    unicodeHighlight: {
      ambiguousCharacters: false,
      invisibleCharacters: false,
    },
    cursorBlinking: "smooth",
    padding: {
      top: 16,
      bottom: 120,
      left: props.settings.paddingX,
      right: props.settings.paddingX,
    },
    scrollbar: { vertical: "auto", horizontal: "hidden" },
  });

  // 修复 wordWrap 失效：flex 容器在 onMounted 时可能尚未完成布局，
  // 导致 Monaco 按错误宽度换行。创建后强制重布局（rAF + 延时双保险）。
  const fixLayout = () => editor?.layout();
  requestAnimationFrame(fixLayout);
  const layoutTimer = window.setTimeout(fixLayout, 500);

  // 修复：Tauri WebView2 下 ResizeObserver 偶发漏触发，补一个窗口 resize 监听
  window.addEventListener("resize", fixLayout);
  removeResizeListener = () => {
    window.removeEventListener("resize", fixLayout);
    window.clearTimeout(layoutTimer);
  };

  decoColl = editor.createDecorationsCollection();

  // 点击 glyph 槽 → 切换该行书签
  editor.onMouseDown((ev) => {
    if (
      ev.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN &&
      ev.target.position
    ) {
      emit("toggle-bookmark", ev.target.position.lineNumber - 1);
    }
  });

  // M3：选区变化 → 外层接收（仅当有非空选区时）
  editor.onDidChangeCursorSelection((ev) => {
    const sel = ev.selection;
    if (!sel || sel.isEmpty()) return;
    const model = editor?.getModel();
    if (!model) return;
    const text = model.getValueInRange(sel);
    if (text && text.trim().length >= 4) {
      emit("text-selected", text.trim().slice(0, 300));
    }
  });

  // 可见行范围变化 → 通知外层分析视口（视口驱动 + 缓存）+ 刷新粘性章节标题
  editor.onDidScrollChange(() => {
    if (scrollRaf) return;
    scrollRaf = requestAnimationFrame(() => {
      scrollRaf = 0;
      if (!editor) return;
      const visible = editor.getVisibleRanges()[0];
      if (visible) {
        emit("view-range", visible.startLineNumber - 1, visible.endLineNumber - 1);
        updateSticky(visible.startLineNumber);
      }
    });
  });

  // 阅读尺：光标行变化 → 更新当前行高亮（开启状态下生效）
  editor.onDidChangeCursorPosition((e) => {
    if (rulerLine === e.position.lineNumber) return;
    rulerLine = e.position.lineNumber;
    if (props.settings.readingRuler) renderDecorations();
  });

  renderDecorations();

  // 初始定位到第 1 行顶部（规避 dev 预构建 reload / 布局重排导致的中途定位）
  // 并补发一次视口范围，确保 onMounted 后立即分析可见行（setScrollTop(0) 不触发 onDidScrollChange）
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      if (!editor) return;
      editor.setScrollTop(0);
      editor.setPosition({ lineNumber: 1, column: 1 });
      const visible = editor.getVisibleRanges()[0];
      if (visible) {
        emit("view-range", visible.startLineNumber - 1, visible.endLineNumber - 1);
        updateSticky(visible.startLineNumber);
      }
    })
  );
});

// 文本变化 → 重建 model 内容
watch(
  () => props.text,
  (t) => {
    if (editor && editor.getValue() !== t) editor.setValue(t);
  }
);

// 章节或书签或情感数据变化 → 重绘装饰
watch(
  () => [
    props.chapters,
    props.bookmarks,
    props.emotions,
    props.showEmotions,
    props.entitySpans,
    props.showEntities,
  ],
  () => renderDecorations(),
  { deep: true }
);

// 阅读设置变化 → 应用（字号/行高/字体/留白/主题/阅读尺）
watch(
  () => props.settings,
  () => applySettings(),
  { deep: true }
);

function renderDecorations() {
  if (!editor || !decoColl) return;
  const decos: monaco.editor.IModelDeltaDecoration[] = [];

  // 章节标题行
  for (const ch of props.chapters) {
    const ln = ch.line + 1;
    decos.push({
      range: new monaco.Range(ln, 1, ln, 1),
      options: {
        isWholeLine: true,
        className: "hl-chapter-title",
        marginClassName: "hl-chapter-margin",
      },
    });
  }

  // 书签行
  for (const b of props.bookmarks) {
    const ln = b.line + 1;
    decos.push({
      range: new monaco.Range(ln, 1, ln, 1),
      options: {
        isWholeLine: true,
        className: "hl-bookmark-line",
        glyphMarginClassName: "codicon codicon-bookmark glyph-bookmark",
        glyphMarginHoverMessage: { value: b.note || "书签（点击移除）" },
      },
    });
  }

  // M2 情感着色：七类情绪 → 七套低饱和底色（叠加在物理行上）
  // 注意：className 必须用 ASCII —— Monaco decoration 渲染管线会丢失非 ASCII 类名
  if (props.showEmotions) {
    for (const e of props.emotions) {
      const ln = props.emotionBaseLine + e.line_offset + 1; // Monaco 1-based
      // 1. 整行浅色背景：段落情绪概览（有 dutir_top 才着色）
      if (e.dutir_top) {
        const lineCls = EMO_CLASS_MAP[e.dutir_top];
        if (lineCls) {
          decos.push({
            range: new monaco.Range(ln, 1, ln, 1),
            options: { isWholeLine: true, className: lineCls },
          });
        }
      }
      // 2. 字级高亮：具体情感词（更强色 + 加粗 + 下划线，定位到字）
      if (e.word_spans) {
        for (const ws of e.word_spans) {
          const wordCls = EMO_WORD_CLASS_MAP[ws.emotion];
          if (!wordCls) continue;
          // start/end 是 0-based 字符偏移，Monaco column 是 1-based
          decos.push({
            range: new monaco.Range(ln, ws.start + 1, ln, ws.end + 1),
            options: { className: wordCls },
          });
        }
      }
    }
  }

  // M4 人物高亮：同一人物的所有出场统一配色（className 由外层给，ASCII 安全）
  if (props.showEntities && props.entitySpans.length > 0) {
    for (const e of props.entitySpans) {
      decos.push({
        range: new monaco.Range(e.line + 1, e.charStart + 1, e.line + 1, e.charEnd + 1),
        options: {
          className: e.cls,
          hoverMessage: { value: `${e.name}（点击人物榜可切换）` },
          overviewRuler: {
            color: "#c9a35c",
            position: monaco.editor.OverviewRulerLane.Right,
          },
        },
      });
    }
  }

  // 彩读风格：阅读尺 —— 高亮当前光标行（聚焦阅读行，淡化由背景对比实现）
  if (props.settings.readingRuler && rulerLine > 0) {
    decos.push({
      range: new monaco.Range(rulerLine, 1, rulerLine, 1),
      options: {
        isWholeLine: true,
        className: "hl-ruler-line",
        marginClassName: "hl-ruler-margin",
      },
    });
  }

  decoColl.set(decos);
}

/** 外部调用：滚动到指定 0 基物理行并居中靠上 */
function revealLine(line0: number) {
  if (!editor) return;
  const ln = line0 + 1;
  editor.revealLineNearTop(ln, monaco.editor.ScrollType.Smooth);
  editor.setPosition({ lineNumber: ln, column: 1 });
  editor.focus();
}

defineExpose({ revealLine });

onBeforeUnmount(() => {
  if (scrollRaf) cancelAnimationFrame(scrollRaf);
  removeResizeListener?.();
  removeResizeListener = null;
  editor?.dispose();
  editor = null;
});
</script>

<template>
  <div class="reader-wrap">
    <!-- 彩读风格：阅读区顶部常驻当前章节标题 -->
    <div class="sticky-title" v-if="stickyLabel">{{ stickyLabel }}</div>
    <div class="emotion-legend" v-if="emotions.length > 0 || entityName">
      <button class="legend-toggle" @click="emit('toggle-emotions')">
        {{ showEmotions ? "◉ 情感" : "○ 情感" }}
      </button>
      <button
        v-if="entityName"
        class="legend-toggle ent-on"
        @click="emit('toggle-entities')"
      >
        {{ showEntities ? "◉" : "○" }} {{ entityName }}
      </button>
      <template v-if="showEmotions">
        <span class="legend-item"><i class="emo-swatch emo-hao"></i>好</span>
        <span class="legend-item"><i class="emo-swatch emo-le"></i>乐</span>
        <span class="legend-item"><i class="emo-swatch emo-ai"></i>哀</span>
        <span class="legend-item"><i class="emo-swatch emo-nu"></i>怒</span>
        <span class="legend-item"><i class="emo-swatch emo-ju"></i>惧</span>
        <span class="legend-item"><i class="emo-swatch emo-e"></i>恶</span>
        <span class="legend-item"><i class="emo-swatch emo-jing"></i>惊</span>
      </template>
    </div>
    <div ref="container" class="reader-container"></div>
  </div>
</template>

<style>
/* 彩读风格：粘性章节标题条（阅读区顶部常驻） */
.sticky-title {
  flex-shrink: 0;
  padding: 6px 16px;
  background: var(--paper-2);
  border-bottom: 1px solid var(--line);
  color: var(--accent-ink);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
/* 彩读风格：阅读尺 —— 当前光标行高亮 */
.hl-ruler-line {
  background: var(--ruler-bg) !important;
  border-top: 1px solid var(--ruler-line);
  border-bottom: 1px solid var(--ruler-line);
}
.hl-ruler-margin {
  background: var(--ruler-bg) !important;
}
/* 章节标题行 */
.hl-chapter-title {
  background: #f6ead0 !important;
  font-weight: 700;
  color: #7a5410;
  border-left: 3px solid #c9a35c;
}
.hl-chapter-margin {
  background: #f6ead0;
}
/* 书签行 */
.hl-bookmark-line {
  background: #fdecc8 !important;
  border-left: 3px solid #e0a33e;
}
.glyph-bookmark {
  color: #d98a1f;
  font-size: 14px;
  cursor: pointer;
}
/* M2 情感着色：七类情绪 → 七套低饱和底色（ASCII 类名，Monaco decoration 安全） */
.hl-emo-hao {
  background: #c8e6c9 !important; /* 好 - 浅绿 */
}
.hl-emo-le {
  background: #ffecb3 !important; /* 乐 - 浅黄 */
}
.hl-emo-ai {
  background: #bbdefb !important; /* 哀 - 浅蓝 */
}
.hl-emo-nu {
  background: #ffcdd2 !important; /* 怒 - 浅红 */
}
.hl-emo-ju {
  background: #e1bee7 !important; /* 惧 - 浅紫 */
}
.hl-emo-e {
  background: #cfd8dc !important; /* 恶 - 浅灰 */
}
.hl-emo-jing {
  background: #ffe0b2 !important; /* 惊 - 浅橙 */
}
/* 字级情感词高亮：更深底色 + 加粗 + 下划线（定位到具体字） */
.hl-word-hao {
  background: #a5d6a7 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #2e7d32 !important;
}
.hl-word-le {
  background: #ffd54f !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #f57f17 !important;
}
.hl-word-ai {
  background: #90caf9 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #1565c0 !important;
}
.hl-word-nu {
  background: #ef9a9a !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #c62828 !important;
}
.hl-word-ju {
  background: #ce93d8 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #6a1b9a !important;
}
.hl-word-e {
  background: #b0bec5 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #37474f !important;
}
.hl-word-jing {
  background: #ffcc80 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #e65100 !important;
}
/* M4 人物高亮：6 色轮转（与实体 id 取模配对）。下划线 + 半透明底色，
   不覆盖情感行底色，两者可叠加阅读。 */
.ent-c0 {
  background: rgba(198, 40, 40, 0.16) !important;
  border-bottom: 2px solid #c62828;
}
.ent-c1 {
  background: rgba(21, 101, 192, 0.16) !important;
  border-bottom: 2px solid #1565c0;
}
.ent-c2 {
  background: rgba(46, 125, 50, 0.16) !important;
  border-bottom: 2px solid #2e7d32;
}
.ent-c3 {
  background: rgba(106, 27, 154, 0.16) !important;
  border-bottom: 2px solid #6a1b9a;
}
.ent-c4 {
  background: rgba(230, 81, 0, 0.16) !important;
  border-bottom: 2px solid #e65100;
}
.ent-c5 {
  background: rgba(0, 121, 107, 0.16) !important;
  border-bottom: 2px solid #00796b;
}
.legend-toggle.ent-on {
  border-color: #c9a35c;
  color: #7a5410;
}
/* 图例栏 */
.reader-wrap {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.emotion-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 12px;
  background: var(--paper-2);
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  flex-shrink: 0;
}
.legend-toggle {
  border: 1px solid var(--line);
  background: var(--paper);
  border-radius: 3px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: 12px;
}
.legend-toggle:hover {
  background: var(--paper-2);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--ink-soft);
}
.emo-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 2px;
  border: 1px solid var(--line);
}
.emo-hao {
  background: #c8e6c9;
}
.emo-le {
  background: #ffecb3;
}
.emo-ai {
  background: #bbdefb;
}
.emo-nu {
  background: #ffcdd2;
}
.emo-ju {
  background: #e1bee7;
}
.emo-e {
  background: #cfd8dc;
}
.emo-jing {
  background: #ffe0b2;
}
.reader-container {
  width: 100%;
  flex: 1;
  overflow: hidden;
}
.reader-container .monaco-editor,
.reader-container .monaco-editor .margin {
  border-radius: 0;
}
</style>