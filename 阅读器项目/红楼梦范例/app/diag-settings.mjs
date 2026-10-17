// 检查阅读设置与 Monaco 行高实际值
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
  out.settingsRaw = localStorage.getItem('honglou.read.settings');
  try { out.settings = JSON.parse(out.settingsRaw); } catch {}
  const vl = document.querySelector('.view-line');
  out.viewLine = vl ? { h: vl.getBoundingClientRect().height, clientH: vl.clientHeight, computedLineHeight: getComputedStyle(vl).lineHeight } : null;
  const vlc = document.querySelector('.view-lines');
  out.viewLinesFont = vl ? getComputedStyle(vl).fontSize : null;
  const first = document.querySelector('.view-line span');
  out.firstSpanFont = first ? getComputedStyle(first).fontSize : null;
  // Monaco model 行数（从 DOM 推断：lines-content 高度 / 行高）
  const lc = document.querySelector('.lines-content');
  out.linesContentH = lc?.clientHeight;
  // 检测是否超长行（单行超宽导致横向滚动）
  const anyLongLine = [...document.querySelectorAll('.view-line')].some(el => el.scrollWidth > el.clientWidth * 2);
  out.anyLongLine = anyLongLine;
  // 编辑器配置探测
  out.editorAttrs = [...document.querySelectorAll('.monaco-editor')][0]?.className || '';
  return out;
})()`);
console.log(JSON.stringify(res, null, 1));

ws.close();
