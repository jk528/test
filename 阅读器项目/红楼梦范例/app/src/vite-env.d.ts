/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

// monaco 的 worker 自执行入口无类型声明，仅作副作用导入
declare module "monaco-editor/editor/editor.worker.js";
