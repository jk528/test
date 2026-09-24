// 最终验证：sticky 已禁用 / 查找栏交互 / page-zones 状态
const list = await (await fetch("http://localhost:9222/json")).json();
const page = list.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const events = [];
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const mid = ++id;
    pending.set(mid, { resolve, reject });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
}
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
  } else if (msg.method) events.push(msg);
};
await new Promise((r) => (ws.onopen = r));
const evalJs = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  return r.result.value;
};

// 1. sticky widget 状态
const sticky = await evalJs(`(() => {
  const w = document.querySelector('.sticky-widget');
  return w ? { display: getComputedStyle(w).display, h: w.clientHeight } : 'none';
})()`);
console.log("sticky widget:", JSON.stringify(sticky));

// 2. page-zones 状态与穿透
const pz = await evalJs(`(() => {
  const c = document.querySelector('.reader-container').getBoundingClientRect();
  const center = document.elementFromPoint(c.left + c.width/2, c.top + c.height/2);
  const left = document.elementFromPoint(c.left + 30, c.top + c.height/2);
  return { centerCls: String(center?.className||center?.tagName), leftCls: String(left?.className||left?.tagName) };
})()`);
console.log("命中测试:", JSON.stringify(pz));

// 3. 顶栏点击 🔍 打开查找栏（通过 DOM click 触发 Vue 事件）
await evalJs(`(() => {
  const btns = [...document.querySelectorAll('header .btn')];
  const find = btns.find(b => b.textContent.includes('🔍'));
  if (find) find.click();
  return !!find;
})()`);
await new Promise((r) => setTimeout(r, 400));
const findBar = await evalJs(`(() => {
  const bar = document.querySelector('.find-bar');
  const inp = bar?.querySelector('input');
  return { shown: !!bar, rect: inp ? JSON.parse(JSON.stringify(inp.getBoundingClientRect())) : null, hit: inp ? (() => { const e = document.elementFromPoint(inp.getBoundingClientRect().x + 50, inp.getBoundingClientRect().y + 10); return e?.tagName + '.' + String(e.className||'').slice(0,30); })() : null };
})()`);
console.log("查找栏:", JSON.stringify(findBar));

// 4. 查找栏输入可交互（输入关键词）
if (findBar.shown) {
  await evalJs(`(() => { const inp = document.querySelector('.find-bar input'); inp.value = '黛玉'; inp.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await new Promise((r) => setTimeout(r, 500));
  const findRes = await evalJs(`(() => {
    const count = document.querySelector('.find-count')?.textContent;
    const matches = document.querySelectorAll('.hl-find-match, .hl-find-current').length;
    return { count, visibleMatches: matches };
  })()`);
  console.log("查找结果:", JSON.stringify(findRes));
  // 关闭查找栏
  await evalJs(`(() => { const close = document.querySelector('.find-bar button:last-child'); close?.click(); return true; })()`);
}

// 5. emotion-legend 图例栏 toggle 可点击（不在 page-zones 覆盖内）
const legend = await evalJs(`(() => {
  const legendEl = document.querySelector('.emotion-legend');
  if (!legendEl) return 'no-legend';
  const r = legendEl.getBoundingClientRect();
  const btn = legendEl.querySelector('button');
  const hit = btn ? document.elementFromPoint(r.x + btn.getBoundingClientRect().width/2, r.y + r.height/2) : null;
  return { legendH: r.height, legendHit: hit?.tagName + '.' + String(hit?.className||'').slice(0,20) };
})()`);
console.log("图例栏:", JSON.stringify(legend));

// 6. 点击翻页热区测试（点击左右热区，观察是否抛 command not found）
await send("Runtime.enable");
events.length = 0;
await evalJs(`(() => { const c = document.querySelector('.reader-container').getBoundingClientRect(); const next = document.querySelector('.page-zone.next'); return !!next; })()`);
const hasPz = await evalJs(`!!document.querySelector('.page-zones.active')`);
console.log("点击翻页热区存在:", hasPz);
if (hasPz) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 1215, y: 400, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 1215, y: 400, button: "left", clickCount: 1 });
  await new Promise((r) => setTimeout(r, 400));
}
const ex = events.filter(e => e.method === "Runtime.exceptionThrown");
console.log("点击热区后异常数:", ex.length, ex[0] ? JSON.stringify(ex[0].params.exceptionDetails?.exception?.description).slice(0,120) : "");

ws.close();
