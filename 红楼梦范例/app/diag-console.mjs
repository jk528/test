// 检查 console 错误 + Monaco DOM 尺寸链
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
  } else if (msg.method) {
    events.push(msg);
  }
};
await new Promise((r) => (ws.onopen = r));
const evalJs = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  return r.result.value;
};

// 启用 Runtime/Log，收集重放的错误
await send("Runtime.enable");
await send("Log.enable");
await new Promise((r) => setTimeout(r, 1500));

const errors = events.filter((e) => ["Runtime.exceptionThrown", "Log.entryAdded", "Runtime.consoleAPICalled"].includes(e.method));
console.log("事件数量:", errors.length);
for (const e of errors.slice(0, 20)) {
  if (e.method === "Log.entryAdded") {
    console.log("LOG:", e.params.entry.level, "→", JSON.stringify(e.params.entry.text).slice(0, 300));
  } else if (e.method === "Runtime.consoleAPICalled") {
    const args = (e.params.args || []).map((a) => a.value ?? a.description ?? "").join(" ");
    console.log("CONSOLE:", e.params.type, "→", args.slice(0, 300));
  } else if (e.method === "Runtime.exceptionThrown") {
    console.log("EXCEPTION:", JSON.stringify(e.params.exceptionDetails?.exception?.description || e.params.exceptionDetails?.text).slice(0, 300));
  }
}

// Monaco DOM 尺寸链
const dom = await evalJs(`(() => {
  const q = (sel) => document.querySelector(sel);
  const info = (sel, el) => el ? { sel, h: el.clientHeight, sh: el.scrollHeight } : { sel, missing: true };
  const editor = q('.monaco-editor');
  const lines = q('.lines-content');
  const viewLines = q('.view-lines');
  const editorScrollable = q('.editor-scrollable');
  const overflow = q('.overflow-guard');
  const scrollable = q('.monaco-scrollable-element');
  return {
    editor: info('.monaco-editor', editor),
    overflowGuard: info('.overflow-guard', overflow),
    scrollableEl: info('.monaco-scrollable-element', scrollable),
    editorScrollable: info('.editor-scrollable', editorScrollable),
    linesContent: info('.lines-content', lines),
    viewLines: info('.view-lines', viewLines),
    viewLineCount: document.querySelectorAll('.view-line').length,
    textLen: (editor?.textContent || '').length,
  };
})()`);
console.log("DOM 尺寸链:", JSON.stringify(dom, null, 1));

ws.close();
