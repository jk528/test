<script setup lang="ts">
// 只读阅读器：Monaco 承载整篇文本，物理行作为唯一锚点。
// - 章节标题行高亮（与解析结果联动）
// - 书签行：glyph 角标 + 行底色，点击左侧 glyph 槽切换书签
// - M2：情感着色（七类情绪 → 七套低饱和底色，叠加在物理行上）
// - 滚动/定位均基于 0 基物理行（Monaco 内部为 1 基）
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { setupMonaco, monaco } from "../lib/monaco";
import { chapterEndLine, type Chapter } from "../lib/chapters";
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
  /** 阅读设置（彩读风格全量） */
  settings: {
    fontSize: number;
    lineHeight: number;
    fontFamily: string;
    theme: "light" | "dark";
    paddingX: number;
    readingRuler: boolean;
    showLineNumbers: boolean;
    letterSpacing: number;
    paragraphSpacing: number;
    firstLineIndent: number;
    clickToPage: boolean;
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
// OPT-6: StickyScroll 章节粘性条 provider 的销毁句柄
let stickyProviderDisposable: monaco.IDisposable | null = null;
// 彩读风格：阅读进度（0~1）
const readProgress = ref(0);
const progressText = ref("0%");
// 彩读风格：查找栏
const showFindBar = ref(false);
const findQuery = ref("");
const findMatchCase = ref(false);
const findMatches = ref<{ line: number; start: number; end: number }[]>([]);
const findCurrentIndex = ref(0);
// 行首缩进的 CSS 变量（px）
const indentPx = ref(0);
const paraGapPx = ref(0);

// ===== OPT-1: 视口装饰渲染 =====
// 视口缓冲行数：上下各多渲染 N 行，避免快速滚动时出现短暂空白
const VIEWPORT_BUFFER = 80;
// 当前视口范围（0 基物理行，含两端）。初始为 [0, Infinity] 表示全量渲染，
// 首次滚动后会被更新为真实视口范围，此后仅渲染视口 ± 缓冲内的装饰。
let viewportStart = 0;
let viewportEnd = Infinity;
let viewportRaf = 0;

// ===== OPT-3: 视觉行级阅读尺 =====
// 阅读尺锚点（视觉行精度，Monaco 1-based）
type RulerPos = { lineNumber: number; column: number };
let rulerAnchor: RulerPos = { lineNumber: 1, column: 1 };
// 聚焦带行数（奇数：中间行是锚点；偶数：多出的一行在下方）
const RULER_FOCUS_LINES = 3;
// 二分查找精度阈值（像素）
const TOP_EPS = 0.5;

/** 二分查找：给定行内某列，找到该视觉行的起始列（最左同 top 的列） */
function visualRowStart(line: number, column: number): RulerPos {
  if (!editor) return { lineNumber: line, column: 1 };
  const top = editor.getTopForPosition(line, column);
  if (!Number.isFinite(top)) return { lineNumber: line, column: 1 };
  let lo = 1;
  let hi = Math.max(1, column);
  let best = column;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const t = editor.getTopForPosition(line, mid);
    if (Number.isFinite(t) && Math.abs(t - top) <= TOP_EPS) {
      best = mid;
      hi = mid - 1; // 继续向左找更左的同 top 列
    } else {
      lo = mid + 1;
    }
  }
  return { lineNumber: line, column: Math.max(1, best) };
}

/** 二分查找：给定行内某列，找到该视觉行的结束列（最右同 top 的列） */
function visualRowEndColumn(line: number, column: number): number {
  if (!editor) return column;
  const model = editor.getModel();
  if (!model) return column;
  if (line < 1 || line > model.getLineCount()) return column;
  const maxCol = model.getLineMaxColumn(line);
  const top = editor.getTopForPosition(line, column);
  if (!Number.isFinite(top)) return maxCol;
  let lo = Math.max(1, column);
  let hi = maxCol;
  let best = column;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const t = editor.getTopForPosition(line, mid);
    if (Number.isFinite(t) && Math.abs(t - top) <= TOP_EPS) {
      best = mid;
      lo = mid + 1; // 继续向右找更右的同 top 列
    } else {
      hi = mid - 1;
    }
  }
  return Math.max(1, Math.min(maxCol, best));
}

/** 移动一个视觉行（向上/向下），返回新位置的视觉行起始列 */
function stepVisualLine(pos: RulerPos, direction: -1 | 1): RulerPos {
  if (!editor) return pos;
  const model = editor.getModel();
  if (!model) return pos;
  const lc = Math.max(1, model.getLineCount());
  const cur = visualRowStart(pos.lineNumber, pos.column);
  if (direction > 0) {
    // 向下：先看当前视觉行是否在物理行内还有下一条
    const endCol = visualRowEndColumn(cur.lineNumber, cur.column);
    const maxCol = model.getLineMaxColumn(cur.lineNumber);
    if (endCol < maxCol) {
      // 同一物理行内还有下一视觉行
      return visualRowStart(cur.lineNumber, endCol + 1);
    }
    // 到下一个物理行
    if (cur.lineNumber < lc) {
      return visualRowStart(cur.lineNumber + 1, 1);
    }
    return cur;
  }
  // 向上
  if (cur.column > 1) {
    // 同一物理行内还有上一视觉行
    return visualRowStart(cur.lineNumber, cur.column - 1);
  }
  if (cur.lineNumber > 1) {
    const prevMax = model.getLineMaxColumn(cur.lineNumber - 1);
    return visualRowStart(cur.lineNumber - 1, prevMax);
  }
  return cur;
}

/** 视觉行是否有内容（非全空白） */
function visualRowHasContent(pos: RulerPos): boolean {
  if (!editor) return false;
  const model = editor.getModel();
  if (!model) return false;
  if (pos.lineNumber < 1 || pos.lineNumber > model.getLineCount()) return false;
  const start = visualRowStart(pos.lineNumber, pos.column);
  const endCol = visualRowEndColumn(start.lineNumber, start.column);
  const text = model.getLineContent(start.lineNumber).slice(start.column - 1, endCol);
  return text.trim().length > 0;
}

/** 跳过空行：向下/上移动到最近的有内容视觉行 */
function snapToContentVisualRow(pos: RulerPos, direction: -1 | 1): RulerPos {
  if (!editor) return pos;
  const model = editor.getModel();
  if (!model) return pos;
  let p = visualRowStart(pos.lineNumber, pos.column);
  if (visualRowHasContent(p)) return p;
  // 先向指定方向找
  const first = stepVisualLine(p, direction);
  if (first.lineNumber !== p.lineNumber || first.column !== p.column) {
    p = first;
    const guard = Math.max(64, model.getLineCount() * 8);
    for (let i = 0; i < guard; i++) {
      if (visualRowHasContent(p)) return p;
      const next = stepVisualLine(p, direction);
      if (next.lineNumber === p.lineNumber && next.column === p.column) break;
      p = next;
    }
  }
  // 反向再找
  const revDir = direction > 0 ? -1 : 1;
  p = visualRowStart(pos.lineNumber, pos.column);
  const guard = Math.max(64, model.getLineCount() * 8);
  for (let i = 0; i < guard; i++) {
    if (visualRowHasContent(p)) return p;
    const next = stepVisualLine(p, revDir);
    if (next.lineNumber === p.lineNumber && next.column === p.column) break;
    p = next;
  }
  return pos;
}

/** 从锚点向两侧收集 N 条有内容的视觉行，形成聚焦带 */
function collectFocusBand(anchor: RulerPos, count: number): RulerPos[] {
  if (!editor) return [];
  const model = editor.getModel();
  if (!model) return [];
  const n = Math.max(1, Math.floor(count));
  const mid = snapToContentVisualRow(anchor, 1);
  if (!visualRowHasContent(mid)) return [];
  const wantBelow = Math.ceil((n - 1) / 2);
  const wantAbove = Math.floor((n - 1) / 2);

  const collect = (from: RulerPos, dir: -1 | 1, max: number): RulerPos[] => {
    const out: RulerPos[] = [];
    let p = from;
    const guard = Math.max(64, model.getLineCount() * 8);
    for (let i = 0; i < guard && out.length < max; i++) {
      const next = stepVisualLine(p, dir);
      if (next.lineNumber === p.lineNumber && next.column === p.column) break;
      p = next;
      if (visualRowHasContent(p)) out.push(p);
    }
    return out;
  };

  const below = collect(mid, 1, wantBelow);
  const above = collect(mid, -1, wantAbove);
  // 一侧不够时补另一侧
  let remaining = n - 1 - below.length - above.length;
  if (remaining > 0) {
    const moreBelow = collect(below[below.length - 1] ?? mid, 1, remaining);
    below.push(...moreBelow);
    remaining -= moreBelow.length;
  }
  if (remaining > 0) {
    const moreAbove = collect(above[above.length - 1] ?? mid, -1, remaining);
    above.push(...moreAbove);
  }
  return [...above.reverse(), mid, ...below];
}

/** 构建聚焦带装饰（视觉行级，inlineClassName 方式） */
function buildRulerDecorations(rows: RulerPos[]): monaco.editor.IModelDeltaDecoration[] {
  if (!editor) return [];
  const model = editor.getModel();
  if (!model) return [];
  const seen = new Set<string>();
  const out: monaco.editor.IModelDeltaDecoration[] = [];
  for (const row of rows) {
    if (row.lineNumber < 1 || row.lineNumber > model.getLineCount()) continue;
    const start = visualRowStart(row.lineNumber, row.column);
    const key = `${start.lineNumber}:${start.column}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const endCol = visualRowEndColumn(start.lineNumber, start.column);
    const maxCol = model.getLineMaxColumn(start.lineNumber);
    const exclusiveEnd = endCol < maxCol ? Math.min(maxCol, endCol + 1) : maxCol;
    const emptyLine = maxCol <= 1;
    out.push({
      range: new monaco.Range(
        start.lineNumber, start.column,
        start.lineNumber, Math.max(start.column, exclusiveEnd),
      ),
      options: {
        inlineClassName: "hl-ruler-focus",
        ...(emptyLine ? { afterContentClassName: "hl-ruler-focus" } : {}),
        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
      },
    });
  }
  return out;
}

setupMonaco();

function applyTheme(t: "light" | "dark") {
  monaco.editor.setTheme(t === "dark" ? "honglou-read-dark" : "honglou-read");
}

function applySettings() {
  if (!editor) return;
  const s = props.settings;
  editor.updateOptions({
    fontSize: s.fontSize,
    lineHeight: s.lineHeight,
    fontFamily: s.fontFamily,
    letterSpacing: s.letterSpacing,
    lineNumbers: s.showLineNumbers ? "on" : "off",
    glyphMargin: s.showLineNumbers,
    padding: { top: 16, bottom: 120, left: s.paddingX, right: s.paddingX },
  });
  // 行首缩进：按字号 * 缩进字符数（2 字符 = 标准中文缩进）
  indentPx.value = Math.round(s.fontSize * s.firstLineIndent);
  // 段间距：按行距比例
  paraGapPx.value = Math.round(s.lineHeight * 0.4 * s.paragraphSpacing);
  // 设置 CSS 变量供装饰类使用
  const el = container.value;
  if (el) {
    el.style.setProperty("--indent-w", `${indentPx.value}px`);
    el.style.setProperty("--para-gap", `${paraGapPx.value}px`);
  }
  applyTheme(s.theme);
  renderDecorations();
}

onMounted(() => {
  if (!container.value) return;
  editor = monaco.editor.create(container.value, {
    value: props.text,
    language: "plaintext",
    readOnly: true,
    theme: props.settings.theme === "dark" ? "honglou-read-dark" : "honglou-read",
    automaticLayout: true,
    fontSize: props.settings.fontSize,
    lineHeight: props.settings.lineHeight,
    fontFamily: props.settings.fontFamily,
    wordWrap: "on",
    wrappingStrategy: "advanced",
    wrappingIndent: "same",
    lineNumbers: props.settings.showLineNumbers ? "on" : "off",
    lineNumbersMinChars: 3,
    glyphMargin: props.settings.showLineNumbers,
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
    // OPT-6: 启用粘性滚动章节条（由 DocumentSymbolProvider 提供章节树）
    stickyScroll: {
      enabled: true,
      maxLineCount: 2,
      scrollWithEditor: false,
    },
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

  // OPT-6: 注册章节文档符号提供者，供 Monaco StickyScroll 使用
  // 把章节列表转为 DocumentSymbol 树，Monaco 自动管理粘性条渲染与滚动同步
  const registerStickyProvider = () => {
    if (!editor) return;
    const model = editor.getModel();
    if (!model) return;
    const totalLines = model.getLineCount();
    stickyProviderDisposable?.dispose();
    stickyProviderDisposable = monaco.languages.registerDocumentSymbolProvider(
      "plaintext",
      {
        provideDocumentSymbols() {
          const symbols: monaco.languages.DocumentSymbol[] = [];
          for (const ch of props.chapters) {
            const startLine = ch.line + 1; // Monaco 1-based
            const endLine = chapterEndLine(props.chapters, ch.index - 1, totalLines) + 1;
            // Monaco 只为至少跨 3 行的符号创建 sticky 候选
            const realEnd = Math.max(startLine + 2, endLine);
            symbols.push({
              name: ch.title.trim().replace(/\s+/g, " ") || `第${ch.numberText}${ch.unit}`,
              detail: "",
              kind: monaco.languages.SymbolKind.Namespace,
              range: new monaco.Range(
                startLine, 1,
                realEnd, model.getLineMaxColumn(realEnd)
              ),
              selectionRange: new monaco.Range(
                startLine, 1,
                startLine, model.getLineMaxColumn(startLine)
              ),
              tags: [],
              children: [],
            });
          }
          return symbols;
        },
      }
    );
  };
  registerStickyProvider();

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

  // 可见行范围变化 → 通知外层分析视口 + 进度 + OPT-1: 重绘视口装饰
  editor.onDidScrollChange(() => {
    if (scrollRaf) return;
    scrollRaf = requestAnimationFrame(() => {
      scrollRaf = 0;
      if (!editor) return;
      const visible = editor.getVisibleRanges()[0];
      if (visible) {
        const vs = visible.startLineNumber - 1;
        const ve = visible.endLineNumber - 1;
        emit("view-range", vs, ve);
        // 彩读风格：计算阅读进度
        const model = editor.getModel();
        if (model) {
          const total = model.getLineCount();
          const current = visible.endLineNumber;
          const pct = Math.min(100, Math.round((current / total) * 100));
          readProgress.value = pct / 100;
          progressText.value = `${pct}%`;
        }
        // OPT-1: 视口变化 → 更新视口范围并重绘装饰（仅大体量装饰受视口限制）
        const newStart = Math.max(0, vs - VIEWPORT_BUFFER);
        const newEnd = ve + VIEWPORT_BUFFER;
        if (newStart !== viewportStart || newEnd !== viewportEnd) {
          viewportStart = newStart;
          viewportEnd = newEnd;
          renderDecorations();
        }
      }
    });
  });

  // OPT-3: 阅读尺：光标行变化 → 更新锚点并重绘聚焦带（开启状态下生效）
  editor.onDidChangeCursorPosition((e) => {
    const newPos = { lineNumber: e.position.lineNumber, column: e.position.column };
    // 只在行号变化时更新（列变化可能是同一视觉行内的移动）
    if (rulerAnchor.lineNumber === newPos.lineNumber && rulerAnchor.column === newPos.column) return;
    rulerAnchor = visualRowStart(newPos.lineNumber, newPos.column);
    if (props.settings.readingRuler) renderDecorations();
  });

  // OPT-3: 阅读尺键盘导航：开启时上下箭头按「有内容的视觉行」移动
  editor.onKeyDown((e) => {
    if (!props.settings.readingRuler) return;
    const model = editor?.getModel();
    if (!model) return;
    let handled = false;
    if (e.keyCode === monaco.KeyCode.UpArrow) {
      const next = snapToContentVisualRow(
        stepVisualLine(rulerAnchor, -1), -1
      );
      if (next.lineNumber !== rulerAnchor.lineNumber || next.column !== rulerAnchor.column) {
        rulerAnchor = next;
        editor.setPosition({ lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column });
        editor.revealPositionInCenterIfOutsideViewport(
          { lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column },
          monaco.editor.ScrollType.Smooth
        );
        renderDecorations();
        handled = true;
      }
    } else if (e.keyCode === monaco.KeyCode.DownArrow) {
      const next = snapToContentVisualRow(
        stepVisualLine(rulerAnchor, 1), 1
      );
      if (next.lineNumber !== rulerAnchor.lineNumber || next.column !== rulerAnchor.column) {
        rulerAnchor = next;
        editor.setPosition({ lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column });
        editor.revealPositionInCenterIfOutsideViewport(
          { lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column },
          monaco.editor.ScrollType.Smooth
        );
        renderDecorations();
        handled = true;
      }
    } else if (e.keyCode === monaco.KeyCode.PageUp) {
      // 向上翻一个聚焦带大小
      let p = rulerAnchor;
      for (let i = 0; i < RULER_FOCUS_LINES; i++) {
        const next = snapToContentVisualRow(stepVisualLine(p, -1), -1);
        if (next.lineNumber === p.lineNumber && next.column === p.column) break;
        p = next;
      }
      if (p.lineNumber !== rulerAnchor.lineNumber || p.column !== rulerAnchor.column) {
        rulerAnchor = p;
        editor.setPosition({ lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column });
        editor.revealPositionNearTop(
          { lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column },
          monaco.editor.ScrollType.Smooth
        );
        renderDecorations();
        handled = true;
      }
    } else if (e.keyCode === monaco.KeyCode.PageDown) {
      // 向下翻一个聚焦带大小
      let p = rulerAnchor;
      for (let i = 0; i < RULER_FOCUS_LINES; i++) {
        const next = snapToContentVisualRow(stepVisualLine(p, 1), 1);
        if (next.lineNumber === p.lineNumber && next.column === p.column) break;
        p = next;
      }
      if (p.lineNumber !== rulerAnchor.lineNumber || p.column !== rulerAnchor.column) {
        rulerAnchor = p;
        editor.setPosition({ lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column });
        editor.revealPositionNearTop(
          { lineNumber: rulerAnchor.lineNumber, column: rulerAnchor.column },
          monaco.editor.ScrollType.Smooth
        );
        renderDecorations();
        handled = true;
      }
    }
    if (handled) {
      e.preventDefault();
      e.stopPropagation();
    }
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
        const vs = visible.startLineNumber - 1;
        const ve = visible.endLineNumber - 1;
        emit("view-range", vs, ve);
        // OPT-1: 初始化视口范围，立即启用视口装饰优化
        viewportStart = Math.max(0, vs - VIEWPORT_BUFFER);
        viewportEnd = ve + VIEWPORT_BUFFER;
        renderDecorations();
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

// OPT-6: 章节变化 → 重新注册 StickyScroll DocumentSymbolProvider
watch(
  () => props.chapters,
  () => {
    if (!editor) return;
    const model = editor.getModel();
    if (!model) return;
    const totalLines = model.getLineCount();
    stickyProviderDisposable?.dispose();
    stickyProviderDisposable = monaco.languages.registerDocumentSymbolProvider(
      "plaintext",
      {
        provideDocumentSymbols() {
          const symbols: monaco.languages.DocumentSymbol[] = [];
          for (const ch of props.chapters) {
            const startLine = ch.line + 1;
            const endLine = chapterEndLine(props.chapters, ch.index - 1, totalLines) + 1;
            const realEnd = Math.max(startLine + 2, endLine);
            symbols.push({
              name: ch.title.trim().replace(/\s+/g, " ") || `第${ch.numberText}${ch.unit}`,
              detail: "",
              kind: monaco.languages.SymbolKind.Namespace,
              range: new monaco.Range(
                startLine, 1,
                realEnd, model.getLineMaxColumn(realEnd)
              ),
              selectionRange: new monaco.Range(
                startLine, 1,
                startLine, model.getLineMaxColumn(startLine)
              ),
              tags: [],
              children: [],
            });
          }
          return symbols;
        },
      }
    );
    // 触发 Monaco 重新计算粘性条
    editor.updateOptions({ stickyScroll: { enabled: false } });
    requestAnimationFrame(() => {
      editor?.updateOptions({
        stickyScroll: { enabled: true, maxLineCount: 2, scrollWithEditor: false },
      });
    });
  },
  { deep: true }
);

// 阅读设置变化 → 应用（字号/行高/字体/留白/主题/阅读尺）
watch(
  () => props.settings,
  () => applySettings(),
  { deep: true }
);

// ===== 彩读风格：查找功能 =====
function doFind(query: string, matchCase: boolean) {
  findQuery.value = query;
  findMatchCase.value = matchCase;
  findMatches.value = [];
  findCurrentIndex.value = 0;
  if (!editor || !query) {
    renderDecorations();
    return;
  }
  const model = editor.getModel();
  if (!model) return;
  // OPT-5: 使用 Monaco 内置 findMatches（Boyer-Moore 等优化算法，性能更好）
  const matches = model.findMatches(
    query,
    false,       // searchOnlyEditableRange
    false,       // isRegex
    matchCase,   // matchCase: true=区分大小写
    null,        // wordSeparators
    false        // captureMatches
  );
  const results = matches.map((m) => ({
    line: m.range.startLineNumber - 1,  // 转为 0 基物理行
    start: m.range.startColumn - 1,     // 转为 0 基列
    end: m.range.endColumn - 1,
  }));
  findMatches.value = results;
  // 跳到第一个当前视口附近的匹配
  if (results.length > 0) {
    const visible = editor.getVisibleRanges()[0];
    const visStart = visible ? visible.startLineNumber - 1 : 0;
    let nearIdx = results.findIndex((r) => r.line >= visStart);
    if (nearIdx < 0) nearIdx = 0;
    findCurrentIndex.value = nearIdx;
    revealMatch(nearIdx);
  }
  renderDecorations();
}

function revealMatch(idx: number) {
  if (!editor || findMatches.value.length === 0) return;
  const m = findMatches.value[idx];
  if (!m) return;
  findCurrentIndex.value = idx;
  editor.revealLineNearTop(m.line + 1, monaco.editor.ScrollType.Smooth);
  editor.setPosition({ lineNumber: m.line + 1, column: m.start + 1 });
  renderDecorations();
}

function findNext() {
  if (findMatches.value.length === 0) return;
  const next = (findCurrentIndex.value + 1) % findMatches.value.length;
  revealMatch(next);
}

function findPrev() {
  if (findMatches.value.length === 0) return;
  const prev =
    (findCurrentIndex.value - 1 + findMatches.value.length) % findMatches.value.length;
  revealMatch(prev);
}

function toggleFindBar() {
  showFindBar.value = !showFindBar.value;
  if (!showFindBar.value) {
    findMatches.value = [];
    findQuery.value = "";
    renderDecorations();
  }
}

// ===== 彩读风格：点击翻页 =====
function pageUp() {
  if (!editor) return;
  editor.trigger("page-zone", "pageUp", null);
}
function pageDown() {
  if (!editor) return;
  editor.trigger("page-zone", "pageDown", null);
}

// ===== 彩读风格：判断段落首行（空行之后 / 章节标题之后 / 正文第一行） =====
// 注意：章节标题行本身不算段落开始
function isParagraphStart(lines: string[], line0: number, chapterLinesSet: Set<number>): boolean {
  if (line0 >= lines.length) return false;
  if (!lines[line0].trim()) return false;
  // 章节标题行本身不是段落开始
  if (chapterLinesSet.has(line0)) return false;
  if (line0 === 0) return true;
  const prev = lines[line0 - 1];
  if (!prev || !prev.trim()) return true;
  if (chapterLinesSet.has(line0 - 1)) return true;
  return false;
}

function renderDecorations() {
  if (!editor || !decoColl) return;
  const decos: monaco.editor.IModelDeltaDecoration[] = [];
  // OPT-1: 视口范围（Monaco 1-based）。大体量装饰仅在视口 ± 缓冲内渲染。
  const vpStart1 = viewportStart + 1;
  const vpEnd1 = viewportEnd + 1;

  // 章节标题行（小体量，全量渲染）
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

  // 书签行（小体量，全量渲染）
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
  // OPT-1: 大体量，仅渲染视口范围内
  // 注意：className 必须用 ASCII —— Monaco decoration 渲染管线会丢失非 ASCII 类名
  if (props.showEmotions) {
    const baseL = props.emotionBaseLine + 1;
    for (const e of props.emotions) {
      const ln = baseL + e.line_offset; // Monaco 1-based
      // OPT-1: 视口过滤
      if (ln < vpStart1 || ln > vpEnd1) continue;
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
  // OPT-1: 大体量（30000+），仅渲染视口范围内
  if (props.showEntities && props.entitySpans.length > 0) {
    for (const e of props.entitySpans) {
      const ln = e.line + 1;
      if (ln < vpStart1 || ln > vpEnd1) continue;
      decos.push({
        range: new monaco.Range(ln, e.charStart + 1, ln, e.charEnd + 1),
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

  // OPT-3: 阅读尺聚焦带 —— 视觉行级精度 + N 行聚焦带 + 空行跳过
  if (props.settings.readingRuler) {
    const bandRows = collectFocusBand(rulerAnchor, RULER_FOCUS_LINES);
    const rulerDecos = buildRulerDecorations(bandRows);
    decos.push(...rulerDecos);
  }

  // 彩读风格：查找结果高亮
  // OPT-1: 匹配数多时大体量，仅渲染视口范围内
  if (findMatches.value.length > 0) {
    for (let i = 0; i < findMatches.value.length; i++) {
      const m = findMatches.value[i];
      const ln = m.line + 1;
      if (ln < vpStart1 || ln > vpEnd1) continue;
      const isCurrent = i === findCurrentIndex.value;
      decos.push({
        range: new monaco.Range(ln, m.start + 1, ln, m.end + 1),
        options: {
          className: isCurrent ? "hl-find-current" : "hl-find-match",
          overviewRuler: {
            color: isCurrent ? "#ff9800" : "#ffd54f",
            position: monaco.editor.OverviewRulerLane.Right,
          },
        },
      });
    }
  }

  // 彩读风格：段间距 + 行首缩进（作用于全部段落首行）
  // OPT-1: 大体量（3000+ 段落 × 1~2 个装饰），仅渲染视口范围内
  if (props.settings.paragraphSpacing > 0 || props.settings.firstLineIndent > 0) {
    const lines = props.text.split("\n");
    const chapterLinesSet = new Set(props.chapters.map((ch) => ch.line));
    // OPT-1: 只遍历视口范围内的行
    const scanStart = Math.max(0, viewportStart);
    const scanEnd = Math.min(lines.length - 1, viewportEnd);
    for (let l = scanStart; l <= scanEnd; l++) {
      if (!lines[l]?.trim()) continue;
      if (!isParagraphStart(lines, l, chapterLinesSet)) continue;
      const ln = l + 1;
      // 段间距：段落首行上方加空白
      if (props.settings.paragraphSpacing > 0) {
        decos.push({
          range: new monaco.Range(ln, 1, ln, 1),
          options: {
            isWholeLine: true,
            className: "hl-para-spacing",
          },
        });
      }
      // 行首缩进：给段落首行第一个字符加左侧内边距
      if (props.settings.firstLineIndent > 0) {
        decos.push({
          range: new monaco.Range(ln, 1, ln, 2),
          options: {
            className: "indent-first-char",
          },
        });
      }
    }
  }

  decoColl.set(decos);
}

/** 外部调用：滚动到指定 0 基物理行并居中靠上 */
function revealLine(line0: number) {
  if (!editor) return;
  const ln = line0 + 1;
  // OPT-3: 同步更新阅读尺锚点到该行开头
  rulerAnchor = visualRowStart(ln, 1);
  editor.revealLineNearTop(ln, monaco.editor.ScrollType.Smooth);
  editor.setPosition({ lineNumber: ln, column: 1 });
  editor.focus();
}

defineExpose({ revealLine, toggleFindBar, doFind, findNext, findPrev, pageUp, pageDown });

onBeforeUnmount(() => {
  if (scrollRaf) cancelAnimationFrame(scrollRaf);
  removeResizeListener?.();
  removeResizeListener = null;
  // OPT-6: 销毁 StickyScroll provider
  stickyProviderDisposable?.dispose();
  stickyProviderDisposable = null;
  editor?.dispose();
  editor = null;
});
</script>

<template>
  <div class="reader-wrap">
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
    <!-- 彩读风格：查找栏 -->
    <div v-if="showFindBar" class="find-bar">
      <input
        type="text"
        :value="findQuery"
        placeholder="查找关键词…"
        @input="doFind(($event.target as HTMLInputElement).value, findMatchCase)"
        @keydown.enter="findNext"
        @keydown.esc="toggleFindBar"
        ref="findInput"
      />
      <span class="find-count">
        {{ findMatches.length ? `${findCurrentIndex + 1}/${findMatches.length}` : "0/0" }}
      </span>
      <button @click="findPrev" :disabled="!findMatches.length">▲</button>
      <button @click="findNext" :disabled="!findMatches.length">▼</button>
      <label>
        <input type="checkbox" :checked="findMatchCase" @change="doFind(findQuery, !findMatchCase)" />
        区分大小写
      </label>
      <button @click="toggleFindBar">✕</button>
    </div>
    <div ref="container" class="reader-container"></div>
    <!-- 彩读风格：底部阅读进度条 -->
    <div class="read-progress">
      <div class="read-progress-bar" :style="{ width: progressText }"></div>
      <span class="read-progress-tip">{{ progressText }}</span>
    </div>
    <!-- 彩读风格：点击翻页热区（左右各 25%） -->
    <div v-if="settings.clickToPage" class="page-zones active">
      <div class="page-zone prev" @click="pageUp" title="上一页 (PageUp)"></div>
      <div class="page-zone next" @click="pageDown" title="下一页 (PageDown / Space)"></div>
    </div>
  </div>
</template>

<style>
/* OPT-6: Monaco 粘性章节条样式 —— 与阅读主题统一 */
.reader-container .monaco-editor .sticky-widget {
  background-color: var(--paper-2) !important;
  border-bottom: 1px solid var(--line);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  z-index: 10;
}
.reader-container .monaco-editor .sticky-widget .sticky-line-content {
  color: var(--accent-ink, #7a5410) !important;
  font-weight: 700 !important;
  font-size: 13px;
  letter-spacing: 0.5px;
  background-color: var(--paper-2) !important;
  padding: 2px 0;
}
.reader-container .monaco-editor .sticky-widget .sticky-widget-line-numbers,
.reader-container .monaco-editor .sticky-widget .sticky-widget-lines-scrollable {
  background-color: var(--paper-2) !important;
}
.reader-container .monaco-editor .sticky-widget .sticky-line-number {
  background-color: var(--paper-2) !important;
  color: var(--accent-ink, #8a6d3b) !important;
}
/* OPT-3: 阅读尺聚焦带 —— 视觉行级精度，inline 方式高亮整行文字 */
.hl-ruler-focus {
  background: var(--ruler-bg) !important;
  border-radius: 2px;
  display: inline-block;
  width: 100%;
  box-shadow: inset 0 1px 0 var(--ruler-line), inset 0 -1px 0 var(--ruler-line);
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