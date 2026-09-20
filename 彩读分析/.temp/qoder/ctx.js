// 上下文提取工具：node ctx.js <文件> <关键词> [前后字符数] [第N个命中]
const fs = require('fs');
const [, , file, keyword, spanArg, nthArg] = process.argv;
const span = parseInt(spanArg || '600', 10);
const nth = parseInt(nthArg || '1', 10);
const text = fs.readFileSync(file, 'utf8');
let idx = -1, count = 0;
while (true) {
  idx = text.indexOf(keyword, idx + 1);
  if (idx === -1) break;
  count++;
  if (count === nth) {
    const start = Math.max(0, idx - span);
    const end = Math.min(text.length, idx + keyword.length + span);
    console.log(`=== 第 ${nth} 处命中 @${idx}（共 ${count}+ 处） ===`);
    console.log(text.slice(start, end).replace(/\n/g, '\\n'));
    process.exit(0);
  }
}
console.error(`仅找到 ${count - 0} 处（请求第 ${nth} 处）`);
// fallthrough: 找到的少于请求的
