// Monaco 编辑器 ESM + web worker 初始化（Vite 方式）。
// 纯中文文本阅读只需基础 editor worker，无需 json/css/html 语言 worker。
import * as monaco from "monaco-editor";
// 通过本地桥接文件以相对路径交给 Vite 的 ?worker 打包（monaco 0.56 的 exports
// 不允许裸包深路径直接带 ?worker，详见 src/workers/editor.worker.ts 说明）。
import editorWorker from "../workers/editor.worker?worker";

let configured = false;

export function setupMonaco(): typeof monaco {
  if (configured) return monaco;
  (self as unknown as { MonacoEnvironment: monaco.Environment }).MonacoEnvironment = {
    getWorker() {
      return new editorWorker();
    },
  };

  // 中文阅读主题（明亮）：纸感米黄，正文行高宽松
  monaco.editor.defineTheme("honglou-read", {
    base: "vs",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#fbf8f1",
      "editor.foreground": "#2b2620",
      "editorLineNumber.foreground": "#c9bfa8",
      "editorLineNumber.activeForeground": "#8a6d3b",
      "editorGutter.background": "#f4eee0",
      "editor.lineHighlightBackground": "#f3ead3",
      "editorCursor.foreground": "#8a6d3b",
      "editorIndentGuide.background1": "#ece3cf",
    },
  });

  // 中文阅读主题（暗黑）：仿彩读暗黑配色，暖调纸黑
  monaco.editor.defineTheme("honglou-read-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#1e1c19",
      "editor.foreground": "#cfc6b8",
      "editorLineNumber.foreground": "#5f5749",
      "editorLineNumber.activeForeground": "#c9a35c",
      "editorGutter.background": "#262320",
      "editor.lineHighlightBackground": "#2e2a24",
      "editorCursor.foreground": "#c9a35c",
      "editorIndentGuide.background1": "#33302a",
    },
  });

  configured = true;
  return monaco;
}

export { monaco };
