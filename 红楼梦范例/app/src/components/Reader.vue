<script setup lang="ts">
// 只读阅读器：Monaco 承载整篇文本，物理行作为唯一锚点。
// - 章节标题行高亮（与解析结果联动）
// - 书签行：glyph 角标 + 行底色，点击左侧 glyph 槽切换书签
// - M2：情感着色（七类情绪 → 七套低饱和底色，叠加在物理行上）
// - 滚动/定位均基于 0 基物理行（Monaco 内部为 1 基）
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { setupMonaco, monaco } from "../lib/monaco";
import type { Chapter } from "../lib/chapters";
import type { Bookmark } from "../lib/annotations";
import type { EmotionSpan } from "../lib/sidecar";

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
}>();

const emit = defineEmits<{
  (e: "view-line", line0: number): void;
  (e: "toggle-bookmark", line0: number): void;
  (e: "toggle-emotions"): void;
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

// 章节或书签或情感数据变化 → 重绘装饰
watch(
  () => [props.chapters, props.bookmarks, props.emotions, props.showEmotions],
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

  // M2 情感着色：七类情绪 → 七套低饱和底色（叠加在物理行上）
  // 注意：className 必须用 ASCII —— Monaco decoration 渲染管线会丢失非 ASCII 类名
  if (props.showEmotions) {
    for (const e of props.emotions) {
      if (!e.dutir_top) continue; // 无情感词不着色
      const cls = EMO_CLASS_MAP[e.dutir_top];
      if (!cls) continue;
      const ln = props.emotionBaseLine + e.line_offset + 1; // Monaco 1-based
      decos.push({
        range: new monaco.Range(ln, 1, ln, 1),
        options: {
          isWholeLine: true,
          className: cls,
        },
      });
    }
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
  <div class="reader-wrap">
    <div class="emotion-legend" v-if="emotions.length > 0">
      <button class="legend-toggle" @click="emit('toggle-emotions')">
        {{ showEmotions ? "◉ 情感" : "○ 情感" }}
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
/* 图例栏 */
.reader-wrap {
  width: 100%;
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
  background: #fafafa;
  border-bottom: 1px solid #e0e0e0;
  font-size: 12px;
  flex-shrink: 0;
}
.legend-toggle {
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 3px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: 12px;
}
.legend-toggle:hover {
  background: #f0f0f0;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #555;
}
.emo-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 2px;
  border: 1px solid #ddd;
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
