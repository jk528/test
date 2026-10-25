// ============================================================
// align_boxes.js — ASCII 框图对齐修复工具（CJK 宽字符感知）
//
// 问题：Markdown 里的 ASCII 框图混入中文后，右边框普遍错位
//   （CJK 字符占 2 列，手工数空格永远数不对）。
// 本工具：扫描文本中的框图块（┌...┐ 顶、│...│ 行、└...┘ 底），
//   按显示宽度重算并补齐每行右边框，使框线重新对齐。
//
// 宽度规则：CJK 统一表意文字 / 全角字符 / CJK 标点 = 2 列，
//   其余字符（含框线字符 ─│┌┐└┘、箭头 →▼、符号 ★√×）= 1 列。
//   与 VS Code / Trae 默认渲染一致。
//
// 识别规则（避免误伤树状图）：
//   只处理「┌─...─┐ 开头、└─...─┘ 结尾、中间行均以 │ 起」的块；
//   树状图（│ ├─ └─► 无封闭顶/底）原样保留。
//
// 用法：
//   node align_boxes.js <file.md>           预览修复结果（输出到 stdout）
//   node align_boxes.js <file.md> --write   就地覆写（UTF-8 无 BOM）
// 也可作为模块复用：
//   const { w, box, alignText } = require('./align_boxes.js');
//   box('标题', ['行1', '行2'])  // 生成新的对齐框
//
// 退出码：0=正常；1=文件读取失败
// ============================================================
'use strict';
const fs = require('fs');

// 显示宽度：CJK/全角 = 2 列，其余 = 1 列
function w(s) {
  let n = 0;
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    n += (cp >= 0x2E80 && cp <= 0x9FFF) ||   // CJK 统一表意文字
         (cp >= 0x3000 && cp <= 0x303F) ||   // CJK 标点
         (cp >= 0xF900 && cp <= 0xFAFF) ||   // CJK 兼容表意文字
         (cp >= 0xFF00 && cp <= 0xFFEF) ? 2 : 1; // 全角形式
  }
  return n;
}

// 生成一个对齐的框（title 可为 '' 表示无标题）
function box(title, lines) {
  const W = Math.max(0, ...lines.map(l => w(l))) + 2;   // 内容区宽（含两侧各 1 空格）
  const out = [];
  if (title) {
    const t = ` ${title} `;
    out.push('┌─' + t + '─'.repeat(Math.max(0, W - 1 - w(t))) + '┐');
  } else {
    out.push('┌' + '─'.repeat(W) + '┐');
  }
  for (const l of lines) {
    out.push(l ? '│ ' + l + ' '.repeat(W - 2 - w(l)) + ' │'
               : '│' + ' '.repeat(W) + '│');
  }
  out.push('└' + '─'.repeat(W) + '┘');
  return out;
}

// 修复一个已存在的框块（block 为原始行数组，indent 为前导空白）
function fixBox(block, indent) {
  const tm = block[0].match(/^\s*┌─*\s*(.*?)\s*─*┐\s*$/);
  const title = tm ? tm[1] : '';
  const contents = block.slice(1, -1).map(L => {
    let c = L.replace(/^\s*│/, '');      // 去左边框
    c = c.replace(/│\s*$/, '');          // 去旧右边框（错位或缺失均可）
    c = c.replace(/\s+$/, '');           // 去旧填充空格
    if (c.startsWith(' ')) c = c.slice(1); // 去统一的内容前导空格
    return c;
  });
  return box(title, contents).map(l => indent + l);
}

// 扫描全文，修复所有框块；返回 { text, boxes, changed }
function alignText(text) {
  const lines = text.split(/\r?\n/);
  const out = [];
  let i = 0, boxes = 0, changed = 0;
  while (i < lines.length) {
    const top = lines[i].match(/^(\s*)┌─.*┐\s*$/);
    if (!top) { out.push(lines[i]); i++; continue; }
    const indent = top[1];
    // 向后收集块：中间行必须以 indent+│ 起，直到 indent+└...┘ 收尾
    const block = [lines[i]];
    let j = i + 1, closed = false;
    while (j < lines.length) {
      const L = lines[j];
      if (L.startsWith(indent + '└') && /┘\s*$/.test(L)) { block.push(L); closed = true; j++; break; }
      if (!L.startsWith(indent + '│')) break;            // 非内容行：不是合法框，放弃
      block.push(L); j++;
    }
    if (!closed || block.length < 3) {                    // 未封闭/无内容：原样输出
      out.push(...block); i = j; continue;
    }
    const fixed = fixBox(block, indent);
    boxes++;
    if (fixed.join('\n') !== block.join('\n')) changed++;
    out.push(...fixed);
    i = j;
  }
  return { text: out.join('\n'), boxes, changed };
}

module.exports = { w, box, alignText };

if (require.main === module) {
  const file = process.argv[2];
  const write = process.argv.includes('--write');
  if (!file) {
    console.error('用法: node align_boxes.js <file> [--write]');
    process.exit(1);
  }
  let src;
  try { src = fs.readFileSync(file, 'utf8'); }
  catch (e) { console.error(`读取失败: ${e.message}`); process.exit(1); }
  const r = alignText(src);
  console.error(`检测到 ${r.boxes} 个框图，其中 ${r.changed} 个已重排对齐`);
  if (write) {
    fs.writeFileSync(file, r.text, 'utf8');               // utf8 默认无 BOM
    console.error(`已覆写: ${file}`);
  } else {
    process.stdout.write(r.text);
  }
}
