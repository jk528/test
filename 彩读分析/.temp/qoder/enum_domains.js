// 枚举所有 openapi 域名配置
const fs = require('fs');
const t = fs.readFileSync(process.argv[2], 'utf8');
const s = new Set();
let m;
const re = /https:\/\/[a-z\-]*openapi\.qoder\.[a-z\.]+/g;
while ((m = re.exec(t))) s.add(m[0]);
console.log([...s].join('\n'));
console.log('--- openApiBaseUrl 配置 ---');
const re2 = /openApiBaseUrl:"[^"]+"/g;
const s2 = new Set();
while ((m = re2.exec(t))) s2.add(m[0]);
console.log([...s2].join('\n'));
