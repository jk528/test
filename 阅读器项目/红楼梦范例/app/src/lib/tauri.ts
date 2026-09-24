// Tauri 桥接封装。区分 Tauri 运行时与纯浏览器（vite dev 单独打开时）。
import { invoke } from "@tauri-apps/api/core";

export const isTauri: boolean =
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

/** 读取文本文件（多编码自动处理在 Rust 侧） */
export async function readTextFile(path: string): Promise<string> {
  return invoke<string>("read_text_file", { path });
}

/** 探测默认书目《红楼梦.txt》，无则返回 null */
export async function probeDefaultBook(): Promise<string | null> {
  const p = await invoke<string | null>("probe_default_book");
  return p ?? null;
}

/** 弹出文件选择对话框，取消返回 null */
export async function pickTextFile(): Promise<string | null> {
  const p = await invoke<string | null>("pick_text_file");
  return p ?? null;
}
