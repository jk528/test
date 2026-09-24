// 精简滚轮验证：先确保编辑器有焦点，再测试 PageDown / WheelEvent / CDP wheel
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
const st = `(() => { const s = document.querySelector('.monaco-scrollable-element'); return s ? s.scrollTop : -1; })()`;

// 0. 点击编辑器获得焦点（点击正文中间）
const c = await evalJs(`(() => { const r = document.querySelector('.reader-container').getBoundingClientRect(); return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()`);
await send("Input.dispatchMouseEvent", { type: "mousePressed", x: c.x, y: c.y + 200, button: "left", clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: c.x, y: c.y + 200, button: "left", clickCount: 1 });
await new Promise((r) => setTimeout(r, 500));
console.log("点击后 scrollTop:", await evalJs(st));

// 1. PageDown 键
await send("Input.dispatchKeyEvent", { type: "keyDown", key: "PageDown", code: "PageDown", windowsVirtualKeyCode: 34 });
await send("Input.dispatchKeyEvent", { type: "keyUp", key: "PageDown", code: "PageDown", windowsVirtualKeyCode: 34 });
await new Promise((r) => setTimeout(r, 800));
console.log("PageDown 后 scrollTop:", await evalJs(st));

// 2. 页面内构造 WheelEvent 派发到 scrollable-element
await evalJs(`(() => {
  const s = document.querySelector('.monaco-scrollable-element');
  const ev = new WheelEvent('wheel', { deltaY: 400, bubbles: true, cancelable: true });
  s.dispatchEvent(ev);
  return true;
})()`);
await new Promise((r) => setTimeout(r, 800));
console.log("scrollable 直接 wheel 后 scrollTop:", await evalJs(st));

// 3. CDP mouseWheel（焦点已在编辑器）
for (let i = 0; i < 2; i++) {
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: c.x, y: c.y + 200, deltaX: 0, deltaY: 300 });
  await new Promise((r) => setTimeout(r, 400));
}
console.log("CDP wheel 后 scrollTop:", await evalJs(st));

// 4. 滚动条滑块拖动模拟（点击右侧滚动条中间位置）
const sc = await evalJs(`(() => {
  const s = document.querySelector('.scrollbar.vertical .slider');
  const r = document.querySelector('.scrollbar.vertical');
  return s && r ? { sliderRect: JSON.parse(JSON.stringify(s.getBoundingClientRect())), barRect: JSON.parse(JSON.stringify(r.getBoundingClientRect())) } : null;
})()`);
console.log("滚动条:", JSON.stringify(sc));

ws.close();
