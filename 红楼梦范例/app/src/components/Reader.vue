<script setup lang="ts">
// 只读阅读器：Monaco 承载整篇文本，物理行作为唯一锚点。
// - 章节标题行高亮（与解析结果联动）
// - 书签行：glyph 角标 + 行底色，点击左侧 glyph 槽切换书签
// - 滚动/定位均基于 0 基物理行（Monaco 内部为 1 基）
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { setupMonaco, monaco } from "../lib/monaco";
import type { Chapter } from "../lib/chapters";
import type { Bookmark } from "../lib/annotations";

const props = defineProps<{
  text: string;
  chapters: Chapter[];
  bookmarks: Bookmark[];
}>();

const emit = defineEmits<{
  (e: "view-line", line0: number): void;
  (e: "toggle-bookmark", line0: number): void;
}>();

const container = ref<HTMLDivElement | null>(null);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;
let decoColl: monaco.editor.IEditorDecorationsCollection | null = null;
let scrollRaf = 0;

setupMonaco();

onMounted(() => {
  if (!container.value) return;
  editor = monaco.editor.create(container.value, {
    value: props.text,
    readOnly: true,
    theme: "honglou-read",
    automaticLayout: true,
    fontSize: 17,
    lineHeight: 30,
    fontFamily:
      '"Cascadia Code", Consolas, "Microsoft YaHei", "PingFang SC", "Noto Serif SC", SimSun, serif',
    wordWrap: "on",
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
    padding: { top: 16, bottom: 120 },
    scrollbar: { vertical: "auto", horizontal: "hidden" },
  });

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

  // 顶部可见行变化 → 通知外层高亮章节树
  editor.onDidScrollChange(() => {
    if (scrollRaf) return;
    scrollRaf = requestAnimationFrame(() => {
      scrollRaf = 0;
      if (!editor) return;
      const top = editor.getTopForLineNumber(1);
      const visible = editor.getVisibleRanges()[0];
      void top;
      if (visible) emit("view-line", visible.startLineNumber - 1);
    });
  });

  renderDecorations();

  // 初始定位到第 1 行顶部（规避 dev 预构建 reload / 布局重排导致的中途定位）
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      editor?.setScrollTop(0);
      editor?.setPosition({ lineNumber: 1, column: 1 });
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

// 章节或书签变化 → 重绘装饰
watch(
  () => [props.chapters, props.bookmarks],
  () => renderDecorations(),
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
  editor?.dispose();
  editor = null;
});
</script>

<template>
  <div ref="container" class="reader-container"></div>
</template>

<style>
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
.reader-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.reader-container .monaco-editor,
.reader-container .monaco-editor .margin {
  border-radius: 0;
}
</style>
