// 章节解析 —— 规则移植自 语料与文本/四大名著/通用分析/splittxt2/split_txt.bas
// 默认正则（VBA 预设 #1，标准中文，含阿拉伯/中文数字与〇/两，含大写中文数字壹贰叁…）：
//   ^第([0-9一二三四五六七八九十百千万零〇两壹贰叁肆伍陆柒捌玖拾佰仟]+)(章|回|节|卷)\s*(.*)$
// 与《红楼梦.txt》的 "第1章 甄士隐梦幻识通灵 贾雨村…" 完全匹配，
// 保证 App 切出的章节与 红楼梦_拆分/ 的 120 个文件一致。
// 大写中文数字用于《道诡异仙》等书的卷标题（第壹卷/第贰卷…）。

export interface Chapter {
  /** 1 基章序号（按出现顺序，非标题中的数字） */
  index: number;
  /** 0 基物理行号（split(/\r?\n/) 的下标） */
  line: number;
  /** 标题原文（去首尾空白的整行） */
  title: string;
  /** 标题中的数字原文，如 "1" / "一百二十" */
  numberText: string;
  /** 单位词：章/回/节/卷 */
  unit: string;
  /** 去掉 "第N章 " 前缀后的回目名 */
  name: string;
}

// VBA 默认正则（含〇、两、万、大写中文数字壹贰叁…）。JS 正则不加 u 标志，中文按 UTF-16 码元在 BMP 内可直接匹配。
const CHAPTER_RE =
  /^第([0-9一二三四五六七八九十百千万零〇两壹贰叁肆伍陆柒捌玖拾佰仟]+)(章|回|节|卷)\s*(.*)$/;

/** 把全文按物理行切开（兼容 CRLF / LF / CR） */
export function splitPhysicalLines(text: string): string[] {
  return text.replace(/\r\n?/g, "\n").split("\n");
}

/**
 * 扫描全部章节。逐行、行首锚定（与 VBA ScanChapters 行为一致）。
 * 返回章节数组；每章范围为 [line, 下一章 line) 或文末。
 */
export function parseChapters(text: string): Chapter[] {
  const lines = splitPhysicalLines(text);
  const chapters: Chapter[] = [];
  for (let i = 0; i < lines.length; i++) {
    // 严格对齐 VBA：对原始物理行做行首锚定，不做 trim，
    // 避免把 "　　……第一回也" 这类含章节字样的正文误判为标题。
    const m = CHAPTER_RE.exec(lines[i]);
    if (!m) continue;
    chapters.push({
      index: chapters.length + 1,
      line: i,
      title: lines[i].trim(),
      numberText: m[1],
      unit: m[2],
      name: (m[3] || "").trim(),
    });
  }
  return chapters;
}

/** 返回某章结束行（0 基，含），末章到全文最后一行 */
export function chapterEndLine(chapters: Chapter[], index: number, totalLines: number): number {
  const cur = chapters[index];
  if (!cur) return totalLines - 1;
  const next = chapters[index + 1];
  return next ? next.line - 1 : totalLines - 1;
}

/** 根据 0 基物理行号反查所属章序号（1 基），未落在任何章返回 0 */
// OPT-4: 二分查找 O(log n)，替代原先的线性扫描 O(n)
// chapters 按 line 升序排列（行扫描得到），可直接二分
export function chapterAtLine(chapters: Chapter[], line: number): number {
  let lo = 0;
  let hi = chapters.length - 1;
  let ans = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (chapters[mid]!.line <= line) {
      ans = chapters[mid]!.index;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}
