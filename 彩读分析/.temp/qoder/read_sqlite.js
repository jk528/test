// 读取 Qoder main.sqlite 的表结构与数据
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync(process.argv[2], { readOnly: true });
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
console.log('=== 表清单 ===');
for (const t of tables) console.log(t.name);
const keyword = process.argv[3];
for (const t of tables) {
  if (keyword && !t.name.toLowerCase().includes(keyword.toLowerCase())) continue;
  const count = db.prepare(`SELECT COUNT(*) c FROM "${t.name}"`).get().c;
  console.log(`\n=== ${t.name} (${count} 行) ===`);
  if (count === 0) continue;
  const cols = db.prepare(`PRAGMA table_info("${t.name}")`).all().map(c => c.name);
  console.log('列: ' + cols.join(', '));
  const rows = db.prepare(`SELECT * FROM "${t.name}" LIMIT 5`).all();
  for (const r of rows) {
    let s = JSON.stringify(r);
    // 脱敏长 token，只留前后片段
    s = s.replace(/([A-Za-z0-9_\-\.]{40,})/g, m => m.slice(0, 12) + '...' + m.slice(-8) + `(${m.length})`);
    console.log(s.substring(0, 600));
  }
}
db.close();
