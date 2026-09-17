// Worker 桥接入口（相对路径，供 Vite 的 ?worker 打包）。
// 注意：monaco-editor 0.56 的 package.json "exports" 将 "./*" 映射到 "./esm/vs/*.js"，
// 因此正确的裸包子路径是 "monaco-editor/editor/editor.worker.js"，
// 不要再写 "monaco-editor/esm/vs/editor/editor.worker.js"（会重复 esm/vs 而解析失败）。
import "monaco-editor/editor/editor.worker.js";
