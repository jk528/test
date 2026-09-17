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

/** 调用 sidecar 的 ping，用于连通性自检。 */
export async function pingSidecar(): Promise<{
  protocol: string;
  version: string;
  python: string;
}> {
  return invoke("call_sidecar", { method: "ping", params: {} });
}
