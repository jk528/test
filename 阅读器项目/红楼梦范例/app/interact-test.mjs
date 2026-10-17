// 交互验证脚本：用 CDP Input 派发真实鼠标事件测试滚动与点击
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

// 读取阅读区中心坐标
const c = await evalJs(`(() => {
  const r = document.querySelector('.reader-container').getBoundingClientRect();
  const s = document.querySelector('.monaco-scrollable-element');
  return { cx: r.left + r.width/2, cy: r.top + r.height/2, scrollTop: s.scrollTop, scrollH: s.scrollHeight, clientH: s.clientHeight };
})()`);
console.log("滚动前:", JSON.stringify(c));

// 1. 滚轮测试（向下滚动 600px）
await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: c.cx, y: c.cy, deltaX: 0, deltaY: 600 });
await new Promise((r) => setTimeout(r, 600));
const after = await evalJs(`document.querySelector('.monaco-scrollable-element').scrollTop`);
console.log("滚动后 scrollTop:", after, "→", after > c.scrollTop ? "✅ 滚动成功" : "❌ 滚动无效");

// 2. 点击测试（点击正文中间位置，应选中/定位光标）
await send("Input.dispatchMouseEvent", { type: "mousePressed", x: c.cx, y: c.cy + 100, button: "left", clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: c.cx, y: c.cy + 100, button: "left", clickCount: 1 });
await new Promise((r) => setTimeout(r, 400));
const pos = await evalJs(`(() => {
  const ta = document.querySelector('.monaco-editor textarea.inputarea');
  return { hasFocus: document.activeElement === ta || document.activeElement?.closest?.('.monaco-editor') !== null, active: document.activeElement?.className?.toString().slice(0,60) };
})()`);
console.log("点击后:", JSON.stringify(pos), pos.hasFocus ? "✅ 焦点已到编辑器" : "⚠️ 焦点未到编辑器");

// 3. Ctrl+F 查找栏测试
await send("Input.dispatchKeyEvent", { type: "keyDown", modifiers: 2, key: "f", code: "KeyF", windowsVirtualKeyCode: 70 });
await send("Input.dispatchKeyEvent", { type: "keyUp", modifiers: 2, key: "f", code: "KeyF", windowsVirtualKeyCode: 70 });
await new Promise((r) => setTimeout(r, 400));
const find = await evalJs(`(() => {
  const bar = document.querySelector('.find-bar');
  const inp = bar ? bar.querySelector('input') : null;
  return { barShown: !!bar, inputRect: inp ? JSON.parse(JSON.stringify(inp.getBoundingClientRect())) : null, focused: document.activeElement === inp };
})()`);
console.log("查找栏:", JSON.stringify(find));

// 4. find-bar 输入框位置 hit-test（确认不被遮挡）
if (find.inputRect) {
  const x = find.inputRect.x + find.inputRect.width / 2;
  const y = find.inputRect.y + find.inputRect.height / 2;
  const hit = await evalJs(`(() => { const e = document.elementFromPoint(${x}, ${y}); return e ? e.tagName + '.' + String(e.className||'').slice(0,60) : 'null'; })()`);
  console.log("查找栏输入框 hit-test:", hit);
}

ws.close();
