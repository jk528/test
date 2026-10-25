// ============================================================
// md_links.js - Markdown 链接校验与修复工具（2026-10-25 沉淀）
//
// 用法:
//   node md_links.js check <目录>   校验全部 md 相对链接（默认模式）
//   node md_links.js fix   <目录>   将含中文的链接目标转为 URL 百分号编码
//
// 背景：Gitee 等平台对未编码的 CJK 链接会 404；本地文件系统检查
//       通过 ≠ 渲染端可跳转。fix 后的编码链接在 Gitee/GitHub/VS Code
//       均可正常跳转。
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');

const mode = process.argv[2] || 'check';
const base = path.resolve(process.argv[3] || '.');
const linkRe = /(\[[^\]]*\]\()([^)\s]+)(\))/g;

let checked = 0, broken = 0, changed = 0;

function encodeTarget(t) {
  const [p, frag] = t.split('#');
  const enc = p.split('/').map(s => encodeURIComponent(s)).join('/');
  return frag ? enc + '#' + frag : enc;
}

function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    if (!e.name.endsWith('.md')) continue;
    const text = fs.readFileSync(p, 'utf8');

    if (mode === 'check') {
      for (const m of text.matchAll(linkRe)) {
        const target = m[2];
        if (/^(https?:|mailto:|#)/i.test(target)) continue;
        const noFrag = target.split('#')[0];
        if (!noFrag) continue;
        checked++;
        const abs = path.resolve(path.dirname(p), decodeURIComponent(noFrag));
        if (!fs.existsSync(abs)) {
          broken++;
          console.log(`BROKEN | ${p.slice(base.length)} | ${target}`);
        }
      }
    } else if (mode === 'fix') {
      let dirty = false;
      const out = text.replace(linkRe, (all, pre, target, post) => {
        if (/^(https?:|mailto:|#)/i.test(target)) return all;
        if (target.includes('%')) return all;        // 已编码
        if (!/[^\x00-\x7F]/.test(target)) return all; // 纯 ASCII 无需处理
        dirty = true;
        return pre + encodeTarget(target) + post;
      });
      if (dirty) {
        fs.writeFileSync(p, out, 'utf8');
        changed++;
        console.log('encoded:', p.slice(base.length));
      }
    } else {
      console.error(`未知模式: ${mode}（可用: check | fix）`);
      process.exit(2);
    }
  }
}

walk(base);
console.log('----');
if (mode === 'check') {
  console.log(`checked: ${checked}, broken: ${broken}`);
  if (broken > 0) process.exitCode = 1;
} else {
  console.log(`files changed: ${changed}`);
}
