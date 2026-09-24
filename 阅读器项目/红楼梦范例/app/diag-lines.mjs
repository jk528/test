// 检查 .lines-content 高度来源与 Monaco 内部滚动状态
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

const res = await evalJs(`(() => {
  const out = {};
  const lc = document.querySelector('.lines-content');
  const vls = document.querySelector('.view-lines');
  const cs = (el) => getComputedStyle(el);
  out.linesContent = { inlineH: lc?.style.height, inlineTransform: lc?.style.transform, clientH: lc?.clientHeight, offsetH: lc?.offsetHeight };
  out.viewLines = { inlineH: vls?.style.height, clientH: vls?.clientHeight };
  // lines-content 的所有子元素
  out.linesChildren = lc ? [...lc.children].map(c => ({ tag: c.tagName, cls: (c.className||'').toString().slice(0,40), h: c.clientHeight, inlineH: c.style.height })) : [];
  // 检查是否所有 view-line 都在 (height 71)
  const vls2 = document.querySelectorAll('.view-line');
  out.sampleViewLines = [...vls2].slice(0, 3).map(el => ({ h: el.clientHeight, text: el.textContent.slice(0, 12) }));
  // 检查 monaco-editor-background / margin 高度
  const bg = document.querySelector('.monaco-editor .monaco-editor-background');
  out.editorBgH = bg?.clientHeight;
  // scrollable 元素的 style
  const sc = document.querySelector('.monaco-scrollable-element');
  out.scrollableStyle = sc ? { transform: sc.style.transform, h: sc.style.height } : null;
  // 编辑器根元素 style
  const ed = document.querySelector('.monaco-editor');
  out.editorStyle = ed ? { h: ed.style.height } : null;
  return out;
})()`);
console.log(JSON.stringify(res, null, 1));

ws.close();
