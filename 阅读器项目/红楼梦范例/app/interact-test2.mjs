// 细化验证：注入 wheel 监听确认事件到达；检查 Monaco 自带查找
const list = await (await fetch("http://localhost:9222/json")).json();
const page = list.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
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
  }
};
await new Promise((r) => (ws.onopen = r));
const evalJs = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  return r.result.value;
};

// 注入 wheel 监听器 + 重置滚动位置
await evalJs(`(() => {
  window.__wheelLog = [];
  document.addEventListener('wheel', (e) => {
    window.__wheelLog.push({ target: e.target?.className?.toString?.().slice(0,60) || e.target?.tagName, dy: e.deltaY, defaultPrevented: e.defaultPrevented });
  }, true);
  const s = document.querySelector('.monaco-scrollable-element');
  if (s) { s.scrollTop = 0; }
  return true;
})()`);

const c = await evalJs(`(() => { const r = document.querySelector('.reader-container').getBoundingClientRect(); return { cx: r.left + r.width/2, cy: r.top + r.height/2 }; })()`);

// 派发滚轮（两次小步）
for (let i = 0; i < 3; i++) {
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: c.cx, y: c.cy, deltaX: 0, deltaY: 200 });
  await new Promise((r) => setTimeout(r, 300));
}

const res = await evalJs(`(() => {
  const s = document.querySelector('.monaco-scrollable-element');
  return { scrollTop: s.scrollTop, wheelLog: window.__wheelLog.slice(0, 6) };
})()`);
console.log("滚轮结果:", JSON.stringify(res, null, 1));

// 检查 Monaco 自带 find widget 状态
const fw = await evalJs(`(() => {
  const w = document.querySelector('.find-widget');
  return w ? { shown: w.style.display !== 'none', rect: JSON.parse(JSON.stringify(w.getBoundingClientRect())) } : 'no-find-widget';
})()`);
console.log("Monaco find widget:", JSON.stringify(fw));

// 测试直接调用自定义查找（暴露的 doFind）验证查找功能本身
const findTest = await evalJs(`(() => {
  // 通过 Vue 组件内部方法不可直接访问，改为检查 view 层
  const view = document.querySelector('.view-lines');
  return { textHasChapter: (view?.textContent||'').includes('甄士隐') };
})()`);
console.log("正文包含关键词:", findTest.textHasChapter);

ws.close();
