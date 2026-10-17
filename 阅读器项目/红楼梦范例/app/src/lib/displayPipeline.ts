// 展示行管线：物理行 → 展示行 双向映射
//
// 概念（移植自 ColorTxt readerDisplayPipeline）：
//   物理行 (physical)  = 磁盘原文行号，所有持久化数据（书签/高亮/情感/实体/事件）锚定于此
//   展示行 (display)   = 屏幕上实际显示的行号，经过文本转换后可能增减行
//   双向映射表        = 每条展示行记录它来自哪条物理行、起止字符偏移
//
// 为什么需要两套坐标：
//   文本转换（简繁/替换/硬换行重排/空行压缩）只作用于展示层，
//   不影响物理行号 → 所有标注永远不错位。
//
// Step 1：恒等变换（物理行 ≡ 展示行，1:1 映射）
//   先把管线骨架和 API 跑通，后续加转换不影响上层调用方。

// ==================== 类型定义 ====================

/** 一条展示行 */
export interface DisplayLine {
  /** 来源物理行号（0 基） */
  physicalLine: number;
  /** 在物理行中的起始字符偏移（0 基，含） */
  physStartCol: number;
  /** 在物理行中的结束字符偏移（0 基，不含） */
  physEndCol: number;
  /** 展示文本 */
  text: string;
}

/** 管线结果 */
export interface DisplayPipeline {
  /** 原始物理行数组（0 基） */
  physicalLines: string[];
  /** 展示行数组（0 基） */
  displayLines: DisplayLine[];
  /** 完整展示文本（用 \n 拼接，可直接写入 Monaco） */
  displayText: string;
  /** 物理行 → 第一条展示行的映射（0 基）。物理行无对应展示行时为 -1。 */
  physToFirstDisplay: number[];
}

// ==================== 恒等变换 ====================
// 最基础的管线：物理行与展示行 1:1 对应，文本不变。
// 用于验证管线骨架，以及不需要任何转换时的默认状态。

export function buildIdentityPipeline(physicalLines: string[]): DisplayPipeline {
  const displayLines: DisplayLine[] = [];
  const physToFirstDisplay: number[] = [];

  for (let i = 0; i < physicalLines.length; i++) {
    const line = physicalLines[i]!;
    displayLines.push({
      physicalLine: i,
      physStartCol: 0,
      physEndCol: line.length,
      text: line,
    });
    physToFirstDisplay.push(i);
  }

  return {
    physicalLines,
    displayLines,
    displayText: physicalLines.join("\n"),
    physToFirstDisplay,
  };
}

// ==================== 转换 1：段首空格规范化 ====================
//
// 去掉每行开头的全角空格（U+3000）和半角空格，用 CSS 段首缩进替代。
// 为什么要做：古白话小说原文常用全角空格做段首缩进，
// 但我们已有 decoration 方式控制缩进，原始空格会导致"双重缩进"。
//
// 行映射：1:1（每行对应一行，不增减行）
// 列映射：展示列 = 物理列 - 被移除的前导空格数
//
// 注意：空行和章节标题行不处理（章节标题行的前导空格可能是排版需要）。

/** 匹配行首的全角空格 + 半角空格序列 */
const LEADING_SPACES_RE = /^[\u3000 ]+/;

/**
 * 构建段首空格规范化管线。
 * 去掉每行开头的全角/半角空格，保持 1:1 行映射。
 */
export function buildNormalizedIndentPipeline(
  physicalLines: string[],
): DisplayPipeline {
  const displayLines: DisplayLine[] = [];
  const physToFirstDisplay: number[] = [];

  for (let i = 0; i < physicalLines.length; i++) {
    const line = physicalLines[i]!;
    const match = line.match(LEADING_SPACES_RE);
    if (match) {
      const skipLen = match[0].length;
      displayLines.push({
        physicalLine: i,
        physStartCol: skipLen,
        physEndCol: line.length,
        text: line.slice(skipLen),
      });
    } else {
      // 无前导空格，原样映射
      displayLines.push({
        physicalLine: i,
        physStartCol: 0,
        physEndCol: line.length,
        text: line,
      });
    }
    physToFirstDisplay.push(i); // 1:1 行映射
  }

  return {
    physicalLines,
    displayLines,
    displayText: displayLines.map((d) => d.text).join("\n"),
    physToFirstDisplay,
  };
}

// ==================== 坐标转换：物理 → 展示 ====================

/**
 * 物理行号 → 第一条展示行号（0 基）。
 * 物理行无对应展示行时返回 -1。
 */
export function physLineToDisplay(
  pipeline: DisplayPipeline,
  physLine: number
): number {
  if (physLine < 0 || physLine >= pipeline.physToFirstDisplay.length) return -1;
  return pipeline.physToFirstDisplay[physLine]!;
}

/**
 * 物理位置（行 + 列，0 基）→ 展示位置（行 + 列，0 基）。
 * 列号在物理行内，若超出该行长度则 clamp 到行尾；
 * 若落在被移除的前导字符内（如规范化掉的空格），则 clamp 到展示行首列（0）。
 *
 * 通用公式：displayCol = physCol - displayLine.physStartCol
 */
export function physPosToDisplay(
  pipeline: DisplayPipeline,
  physLine: number,
  physCol: number
): { line: number; col: number } {
  const firstDisp = physLineToDisplay(pipeline, physLine);
  if (firstDisp < 0) return { line: -1, col: -1 };

  const dl = pipeline.displayLines[firstDisp];
  if (!dl) return { line: -1, col: -1 };

  // 通用公式：展示列 = 物理列 - 该展示行在物理行中的起始偏移
  // 若物理列在前导字符（被移除的部分）中，clamp 到展示行首
  const dispCol = Math.max(0, Math.min(physCol - dl.physStartCol, dl.text.length));
  return { line: firstDisp, col: dispCol };
}

/**
 * 物理区间（行内字符区间，0 基，左闭右开）→ 展示区间数组。
 * 一个物理行内的区间可能跨多条展示行（硬换行重排等场景），
 * 所以返回数组。恒等变换下返回单元素数组。
 */
export function physRangeToDisplay(
  pipeline: DisplayPipeline,
  physLine: number,
  physStartCol: number,
  physEndCol: number
): Array<{ line: number; startCol: number; endCol: number }> {
  const pos = physPosToDisplay(pipeline, physLine, physStartCol);
  const endPos = physPosToDisplay(pipeline, physLine, physEndCol);
  if (pos.line < 0 || endPos.line < 0) return [];

  // 恒等变换：同一条展示行
  if (pos.line === endPos.line) {
    return [{ line: pos.line, startCol: pos.col, endCol: endPos.col }];
  }

  // 跨展示行（恒等变换不会发生，防御性处理）
  const result: Array<{ line: number; startCol: number; endCol: number }> = [];
  for (let l = pos.line; l <= endPos.line; l++) {
    const dl = pipeline.displayLines[l];
    if (!dl) continue;
    const s = l === pos.line ? pos.col : 0;
    const e = l === endPos.line ? endPos.col : dl.text.length;
    result.push({ line: l, startCol: s, endCol: e });
  }
  return result;
}

// ==================== 坐标转换：展示 → 物理 ====================

/**
 * 展示行号 → 物理行号（0 基）。
 * 展示行号越界返回 -1。
 */
export function displayLineToPhys(
  pipeline: DisplayPipeline,
  dispLine: number
): number {
  if (dispLine < 0 || dispLine >= pipeline.displayLines.length) return -1;
  return pipeline.displayLines[dispLine]!.physicalLine;
}

/**
 * 展示位置（行 + 列，0 基）→ 物理位置（行 + 列，0 基）。
 */
export function displayPosToPhys(
  pipeline: DisplayPipeline,
  dispLine: number,
  dispCol: number
): { line: number; col: number } {
  if (dispLine < 0 || dispLine >= pipeline.displayLines.length) {
    return { line: -1, col: -1 };
  }
  const dl = pipeline.displayLines[dispLine]!;
  const clampedCol = Math.max(0, Math.min(dispCol, dl.text.length));
  return { line: dl.physicalLine, col: dl.physStartCol + clampedCol };
}
