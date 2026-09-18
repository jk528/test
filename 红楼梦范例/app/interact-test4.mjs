// 正确测试 Monaco 滚动：检查 .lines-content 的 transform 平移量 + 视口文本变化
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
const state = `(() => {
  const lc = document.querySelector('.lines-content');
  const first = document.querySelector('.view-line');
  return { transform: lc?.style.transform, firstText: first?.textContent.slice(0, 16) };
})()`;

console.log("初始:", JSON.stringify(await evalJs(state)));

// 点击获得焦点
const c = await evalJs(`(() => { const r = document.querySelector('.reader-container').getBoundingClientRect(); return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()`);
await send("Input.dispatchMouseEvent", { type: "mousePressed", x: c.x, y: c.y + 300, button: "left", clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: c.x, y: c.y + 300, button: "left", clickCount: 1 });
await new Promise((r) => setTimeout(r, 400));

// CDP wheel 向下滚 5 次
for (let i = 0; i < 5; i++) {
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: c.x, y: c.y + 300, deltaX: 0, deltaY: 300 });
  await new Promise((r) => setTimeout(r, 350));
}
console.log("wheel 后:", JSON.stringify(await evalJs(state)));

// 拖动滚动条：拖到中间
await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 1210, y: 132, button: "left", clickCount: 1 });
for (let yy = 132; yy < 450; yy += 30) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1210, y: yy, button: "left", buttons: 1 });
  await new Promise((r) => setTimeout(r, 80));
}
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 1210, y: 450, button: "left", clickCount: 1 });
await new Promise((r) => setTimeout(r, 600));
console.log("拖滚动条后:", JSON.stringify(await evalJs(state)));

// 检查当前是否有 chapter 标题装饰（说明确实能滚动）
const deco = await evalJs(`(() => {
  const hls = [...document.querySelectorAll('.hl-chapter-title')].slice(0,3);
  return { chapterTitles: hls.map(h => h.parentElement?.textContent?.slice(0,15)) };
})()`);
console.log("章节标题装饰:", JSON.stringify(deco));

ws.close();
