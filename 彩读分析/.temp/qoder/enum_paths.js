// 枚举 JS 中所有 API 路径字符串
const fs = require('fs');
const t = fs.readFileSync(process.argv[2], 'utf8');
const re = /["'`](\/[a-zA-Z0-9\/_\-\.]{4,80})["'`]/g;
const set = new Map();
let m;
while ((m = re.exec(t))) {
  const p = m[1];
  if (/api|campaign|sash|credit|claim|growth|task|activity|point|sign/i.test(p)) set.set(p, (set.get(p) || 0) + 1);
}
for (const [k, v] of set) console.log(`${v}x ${k}`);
