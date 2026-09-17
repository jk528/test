// 前端 → Rust invoke → Python sidecar 的调用封装。
// M2 提供：analyzeSentiment —— 段落级（物理行级）情感分析。
// Rust 侧 call_sidecar 命令已返回 sidecar 响应的 result 字段内容。

import { invoke } from "@tauri-apps/api/core";

/** 字级情感词位置：start/end 为行内字符偏移（0-based，含前导空白），Monaco column 需 +1。 */
export interface WordSpan {
  start: number;
  end: number;
  /** DUTIR 情绪类别：好/乐/哀/怒/惧/恶/惊 */
  emotion: string;
  /** 匹配到的具体词 */
  word: string;
}

/** 单段（物理行）的情感分析结果。line_offset 为章内 0-based 相对行号。 */
export interface EmotionSpan {
  line_offset: number;
  /** DUTIR 主导情绪：好/乐/哀/怒/惧/恶/惊；null=无情感词（不着色） */
  dutir_top: string | null;
  /** 极性 -1~1：(正面 - 负面) / 总情感词数 */
  polarity: number;
  /** 强度 0~1：情感词密度 = 总情感词数 / 分词数 */
  intensity: number;
  /** 七类分量计数 */
  weights: Record<string, number>;
  /** 字级情感词位置列表（用于 inline decoration 高亮具体字） */
  word_spans: WordSpan[];
}

/** 调用 sidecar 的 analyze_sentiment，返回段落级情感区间数组。 */
export async function analyzeSentiment(text: string): Promise<EmotionSpan[]> {
  const resp = await invoke<{ paragraphs: EmotionSpan[] }>("call_sidecar", {
    method: "analyze_sentiment",
    params: { text },
  });
  return resp.paragraphs ?? [];
}

/** 单章主导情绪（用于目录着色）。 */
export interface ChapterEmotion {
  index: number;
  dutir_top: string | null;
  polarity: number;
  intensity: number;
  weights: Record<string, number>;
}

/** 批量分析所有章节主导情绪（用于目录着色）。 */
export async function analyzeChapters(
  text: string,
  chapters: { line: number }[]
): Promise<ChapterEmotion[]> {
  const resp = await invoke<{ chapter_emotions: ChapterEmotion[] }>(
    "call_sidecar",
    { method: "analyze_chapters", params: { text, chapters } }
  );
  return resp.chapter_emotions ?? [];
}

/** 调用 sidecar 的 ping，用于连通性自检。 */
export async function pingSidecar(): Promise<{
  protocol: string;
  version: string;
  python: string;
  db_path: string;
}> {
  return invoke("call_sidecar", { method: "ping", params: {} });
}

// ─────────────────── M3：SQLite 主库 + RAG 问答 ───────────────────

/** sidecar 状态（库路径 / 向量是否可用 / LLM 是否配置）。 */
export interface DbStatus {
  db_path: string;
  vec_ready: boolean;
  tables: string[];
  llm_configured: boolean;
}

export async function dbStatus(): Promise<DbStatus> {
  return invoke("call_sidecar", { method: "db_status", params: {} });
}

/** 保存书目元数据 + 章节到 SQLite，返回 book_id。 */
export async function saveBook(params: {
  title: string;
  source_path: string;
  text: string;
  book_id?: string;
}): Promise<{ book_id: string; chapters: number; total_lines: number }> {
  return invoke("call_sidecar", { method: "save_book", params });
}

/**
 * SQLite emotions 表的一行（字段名是落库列名，注意与 EmotionSpan 的区别：
 * 库侧用 line_start/line_end，内存侧用 line_offset）。
 */
export interface EmotionRow {
  book_id?: string;
  chapter_idx?: number;
  line_start: number;
  line_end: number;
  dutir_top: string | null;
  polarity: number;
  intensity: number;
  weights: Record<string, number>;
  word_spans?: WordSpan[];
}

/** 增量写情感的行载荷（word_spans 落 spans_json，用于重启后字级高亮回放）。 */
export interface EmotionWriteRow {
  line_start: number;
  line_end: number;
  dutir_top: string | null;
  polarity: number;
  intensity: number;
  weights: Record<string, number>;
  word_spans?: WordSpan[];
}

/** 读取某章情感（SQLite 持久化版，避免重复分析）。 */
export async function getChapterEmotions(
  bookId: string,
  chapterIdx: number
): Promise<{ rows: EmotionRow[] }> {
  return invoke("call_sidecar", {
    method: "get_chapter_emotions",
    params: { book_id: bookId, chapter_idx: chapterIdx },
  });
}

/** 整章情感结果写库（增量失效键 = book_id + chapter_idx）。 */
export async function saveChapterEmotions(
  bookId: string,
  chapterIdx: number,
  rows: EmotionWriteRow[]
): Promise<{ saved: number }> {
  return invoke("call_sidecar", {
    method: "save_chapter_emotions",
    params: { book_id: bookId, chapter_idx: chapterIdx, rows },
  });
}

/**
 * 按行增量写情感（幂等，同行覆盖）。
 * 前端是视口驱动、分批分析的，必须用增量写；整章替换会把先到的批次冲掉。
 */
export async function upsertEmotions(
  bookId: string,
  chapterIdx: number,
  rows: EmotionWriteRow[]
): Promise<{ saved: number }> {
  return invoke("call_sidecar", {
    method: "upsert_emotions",
    params: { book_id: bookId, chapter_idx: chapterIdx, rows },
  });
}

/** 书签/高亮/笔记：同书同 kind 同行更新。 */
export async function upsertAnnotation(params: {
  book_id: string;
  kind: "bookmark" | "highlight" | "note";
  chapter_idx: number;
  line_start: number;
  line_end: number;
  text?: string;
  note?: string;
  char_start?: number | null;
  char_end?: number | null;
  color?: string;
}): Promise<{ id: number }> {
  return invoke("call_sidecar", { method: "upsert_annotation", params });
}

export async function listAnnotations(
  bookId: string,
  kind?: string
): Promise<{ annotations: unknown[] }> {
  return invoke("call_sidecar", {
    method: "list_annotations",
    params: { book_id: bookId, kind: kind ?? null },
  });
}

export async function deleteAnnotation(id: number): Promise<{ deleted: number }> {
  return invoke("call_sidecar", { method: "delete_annotation", params: { id } });
}

/** RAG 建索引：分块 + 嵌入 + 写库（首次使用，耗时取决于篇幅）。 */
export async function buildIndex(params: {
  book_id: string;
  text: string;
  chapters: { line: number; title: string }[];
  force?: boolean;
}): Promise<{
  chunks: number;
  embedded: number;
  skipped: boolean;
  vec_ready: boolean;
  model: string;
  dim: number;
  sig: string;
}> {
  return invoke("call_sidecar", { method: "build_index", params });
}

/** 索引现状：判断是否需要重建（避免每次开书都白跑一遍嵌入）。 */
export interface IndexStatus {
  book_id: string;
  chunks: number;
  vectors: number;
  vec_ready: boolean;
  indexed: boolean;
  need_rebuild: boolean;
  sig: string | null;
}

export async function indexStatus(
  bookId: string,
  text?: string,
  chapters?: { line: number; title: string }[]
): Promise<IndexStatus> {
  return invoke("call_sidecar", {
    method: "index_status",
    params: { book_id: bookId, text: text ?? null, chapters: chapters ?? null },
  });
}

/** 语义检索（不含 LLM）。 */
export async function searchRag(
  query: string,
  bookId?: string
): Promise<{
  hits: { id: number; chapter_idx: number; line_start: number; line_end: number; text: string; distance: number }[];
}> {
  return invoke("call_sidecar", {
    method: "search",
    params: { query, book_id: bookId ?? null },
  });
}

/** RAG 问答：检索 + LLM 作答，答案引用带来源锚点。 */
export async function askAi(params: {
  query: string;
  book_id?: string;
  use_rag?: boolean;
}): Promise<{
  answer: string;
  sources: { id: number; chapter_idx: number; line_start: number; line_end: number }[];
}> {
  return invoke("call_sidecar", { method: "ask_ai", params });
}

// ─────────────────── M4：全景分析（事件 / 人物 / 伏笔 / 关系）───────────────────
// 数据来源：既有的 120 章 V3.4 分析报告「回灌」进 SQLite（sidecar import_analysis）。
// 所有条目都带**物理行锚点**，点击即可跳回正文对应行。

/** 事件（level 已由报告三档符号归一为主线/支线/细节）。 */
export interface BookEvent {
  id: number;
  event_uid: string;
  level: "主线" | "支线" | "细节";
  chapter_idx: number;
  line_start: number;
  line_end: number;
  summary: string;
  tone: string;
  /** 锚点精度：quote=引文精确 / cooccur=人物共现近似 / para=段号估计 */
  anchor_precision: "quote" | "cooccur" | "para" | "chapter" | string;
  participants: string[];
  para_raw: string | null;
  char_start: number | null;
  char_end: number | null;
  /** M4.6：报告 §三 新闻六要素表回填（子集覆盖，可为 null） */
  w5h1: EventW5H1 | null;
}

export interface EventW5H1 {
  title: string;
  when: string;
  where: string;
  who: string;
  what: string;
  why: string;
  how: string;
  source: string;
}

export interface EntityRow {
  id: number;
  canonical: string;
  aliases: string[];
  first_chapter: number | null;
  appear_count: number;
}

export interface EntityMention {
  entity_id: number;
  canonical: string;
  chapter_idx: number;
  line_start: number;
  char_start: number;
  char_end: number;
  surface: string;
}

export interface Foreshadow {
  id: number;
  setup_chapter: number;
  setup_line: number;
  payoff_chapter: number | null;
  payoff_line: number | null;
  content: string;
  kind: string;
  status: "open" | "closed";
  anchor_precision: string;
  payoff_raw: string | null;
}

export interface EntityRelation {
  id: number;
  chapter_idx: number;
  entity_a: string;
  entity_b: string;
  relation: string;
  evidence: string;
}

export interface Overview {
  events: number;
  entities: number;
  mentions: number;
  foreshadows: number;
  foreshadows_open: number;
  relations: number;
  chapters_with_events: number;
  events_by_level: Record<string, number>;
  events_by_tone: Record<string, number>;
  anchor_precision: Record<string, number>;
  top_entities: EntityRow[];
}

/** 全景统计（首屏一次拉齐）。 */
export async function overview(bookId: string): Promise<Overview> {
  return invoke("call_sidecar", { method: "overview", params: { book_id: bookId } });
}

/** 回灌既有 V3.4 报告（幂等）。返回写入统计 + 锚点精度分布。 */
export async function importAnalysis(
  bookId: string,
  text: string
): Promise<{
  events: number;
  entities: number;
  mentions: number;
  foreshadows: number;
  relations: number;
  reports: number;
  anchor_precision: Record<string, number>;
}> {
  return invoke("call_sidecar", {
    method: "import_analysis",
    params: { book_id: bookId, text },
  });
}

export async function listEvents(params: {
  book_id: string;
  chapter_from?: number;
  chapter_to?: number;
  level?: string;
  entity?: string;
  limit?: number;
}): Promise<{ events: BookEvent[] }> {
  return invoke("call_sidecar", { method: "list_events", params });
}

export async function listEntities(
  bookId: string,
  minAppear = 1,
  limit = 200
): Promise<{ entities: EntityRow[] }> {
  return invoke("call_sidecar", {
    method: "list_entities",
    params: { book_id: bookId, min_appear: minAppear, limit },
  });
}

export async function getEntity(
  bookId: string,
  canonical: string
): Promise<{
  entity: EntityRow;
  curve: { chapter_idx: number; n: number }[];
  first_lines: EntityMention[];
  relations: EntityRelation[];
}> {
  return invoke("call_sidecar", {
    method: "get_entity",
    params: { book_id: bookId, canonical },
  });
}

export async function listMentions(
  bookId: string,
  chapterIdx?: number,
  entityId?: number,
  limit = 4000
): Promise<{ mentions: EntityMention[] }> {
  return invoke("call_sidecar", {
    method: "list_mentions",
    params: {
      book_id: bookId,
      chapter_idx: chapterIdx ?? null,
      entity_id: entityId ?? null,
      limit,
    },
  });
}

export async function listForeshadows(
  bookId: string,
  status?: "open" | "closed"
): Promise<{ foreshadows: Foreshadow[] }> {
  return invoke("call_sidecar", {
    method: "list_foreshadows",
    params: { book_id: bookId, status: status ?? null },
  });
}

export async function listRelations(
  bookId: string,
  entity?: string,
  limit = 600
): Promise<{ relations: EntityRelation[] }> {
  return invoke("call_sidecar", {
    method: "list_relations",
    params: { book_id: bookId, entity: entity ?? null, limit },
  });
}

/** 正文人物高亮片段：绝对物理行 + 行内字符偏移（0-based，含前导全角空格）。 */
export interface EntitySpan {
  /** 0 基绝对物理行 */
  line: number;
  charStart: number;
  charEnd: number;
  /** 配色类名 ent-c0 … ent-c5（ASCII，Monaco decoration 安全） */
  cls: string;
  /** hover 提示用的人物名 */
  name: string;
}

/** 人物高亮配色类名（与 Reader.vue 的 .ent-cN 一一对应）。 */
export const ENTITY_CLASSES = ["ent-c0", "ent-c1", "ent-c2", "ent-c3", "ent-c4", "ent-c5"];

// ─────────────────── M4.5：全书预处理（分析前置）───────────────────

/** chapter_emotions 表的一行（章级情感汇总）。 */
export interface ChapterEmotionRow {
  chapter_idx: number;
  dutir_top: string | null;
  polarity: number;
  intensity: number;
  weights: Record<string, number>;
  word_count: number;
}

/** 预处理现状：已备章数 / 段落数，以及（给出 total 时）是否已就绪。 */
export interface PrepareStatus {
  book_id: string;
  prepared_chapters: number;
  prepared_lines: number;
  chapters_total: number | null;
  ready: boolean | null;
}

export interface PrepareResult {
  book_id: string;
  chapter_from: number;
  chapter_to: number;
  chapters: number;
  paragraphs: number;
  skipped?: boolean;
  elapsed_ms: number;
  coverage: { lines: number; chapters: number };
}

/** 问预处理现状。开书先问一次，避免重复跑十几秒的全文分析。 */
export async function prepareStatus(
  bookId: string,
  chaptersTotal?: number
): Promise<PrepareStatus> {
  return invoke("call_sidecar", {
    method: "prepare_status",
    params: { book_id: bookId, chapters_total: chaptersTotal },
  });
}

/**
 * 全书预处理：段落级情感 + 章级汇总一次性入库。
 * 幂等且增量 —— 已备的章直接跳过，只补缺口；
 * chapter_from / chapter_to 为 0 基闭区间，可分片调用以显示进度。
 */
export async function prepareBook(params: {
  book_id: string;
  text: string;
  chapters: { line: number }[];
  chapter_from?: number;
  chapter_to?: number;
  force?: boolean;
}): Promise<PrepareResult> {
  return invoke("call_sidecar", { method: "prepare_book", params });
}

/** 读章级情感（目录着色 / 情绪曲线用，命中库不重算）。 */
export async function listChapterEmotions(
  bookId: string
): Promise<ChapterEmotionRow[]> {
  const resp = await invoke<{ rows: ChapterEmotionRow[] }>("call_sidecar", {
    method: "list_chapter_emotions",
    params: { book_id: bookId },
  });
  return resp.rows ?? [];
}
