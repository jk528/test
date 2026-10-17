// 临时 CDP 诊断脚本：检查阅读区交互/遮挡/Monaco 状态
const list = await (await fetch("http://localhost:9222/json")).json();
const page = list.find((t) => t.type === "page");
if (!page) throw new Error("未找到页面");
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

const diag = `(() => {
  const out = {};
  const container = document.querySelector('.reader-container');
  out.readerContainer = container ? { rect: JSON.parse(JSON.stringify(container.getBoundingClientRect())), cw: container.clientWidth, ch: container.clientHeight } : null;
  const overflow = document.querySelector('.monaco-editor .overflow-guard');
  out.overflow = overflow ? { rect: JSON.parse(JSON.stringify(overflow.getBoundingClientRect())), scrollH: overflow.scrollHeight, clientH: overflow.clientHeight } : null;
  const scrollable = document.querySelector('.monaco-scrollable-element');
  out.scrollable = scrollable ? { scrollH: scrollable.scrollHeight, clientH: scrollable.clientHeight, scrollTop: scrollable.scrollTop } : null;
  if (container) {
    const r = container.getBoundingClientRect();
    const pts = { center: [r.left+r.width/2, r.top+r.height/2], topLeft: [r.left+10, r.top+10], topRight: [r.right-10, r.top+10], bottomCenter: [r.left+r.width/2, r.bottom-10] };
    out.hitTest = {};
    for (const [k,[x,y]] of Object.entries(pts)) {
      const el = document.elementFromPoint(x,y);
      out.hitTest[k] = el ? { tag: el.tagName, cls: String(el.className||'').slice(0,140), ptr: getComputedStyle(el).pointerEvents, z: getComputedStyle(el).zIndex } : null;
    }
  }
  const topEls = [...document.querySelectorAll('body *')].filter(e => {
    const s = getComputedStyle(e); return s.position !== 'static' && s.zIndex !== 'auto' && e.getBoundingClientRect().width > 0;
  }).sort((a,b)=>+getComputedStyle(b).zIndex - +getComputedStyle(a).zIndex).slice(0,15).map(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return { tag: e.tagName, cls: String(e.className||'').slice(0,70), z: s.zIndex, pos: s.position, pe: s.pointerEvents, rect: [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)] };
  });
  out.topZ = topEls;
  const sticky = document.querySelector('.sticky-widget');
  out.sticky = sticky ? { display: getComputedStyle(sticky).display, pe: getComputedStyle(sticky).pointerEvents, h: sticky.clientHeight, rect: JSON.parse(JSON.stringify(sticky.getBoundingClientRect())) } : 'none';
  const viewLines = document.querySelectorAll('.view-line');
  out.monaco = { viewLines: viewLines.length, firstText: (viewLines[0]?.textContent||'').slice(0,30), lineCount: document.querySelectorAll('.view-line').length };
  out.errorBanner = document.querySelector('.error-banner')?.textContent || null;
  out.hasPlaceholder = !!document.querySelector('.placeholder');
  out.bodyOverflow = getComputedStyle(document.body).overflow;
  return JSON.stringify(out, null, 1);
})()`;

await send("Runtime.enable");
await send("Log.enable");
const res = await send("Runtime.evaluate", { expression: diag, returnByValue: true });
console.log(res.result.value);
ws.close();
