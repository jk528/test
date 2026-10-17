// 红楼梦阅读分析一体化 — Rust 壳命令
// M1「读起来」：纯读域。提供文本读取（多编码）与默认书目探测。
// 章节识别在前端/sidecar 完成（规则移植自 splittxt2/split_txt.bas）。
// M2「接上析」：新增 sidecar 进程管理 + call_sidecar invoke 命令。

mod sidecar;

use encoding_rs::GBK;
use std::sync::Arc;
use tauri::Manager;
use tauri_plugin_dialog::DialogExt;

/// 读取文本文件并解码为字符串。
/// 与 VBA ReadTextAuto 对齐：BOM 优先，UTF-8 严格解码失败则回退 GBK。
#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    let bytes = std::fs::read(&path).map_err(|e| format!("读取文件失败: {e}"))?;

    // UTF-8 BOM
    if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
        return Ok(String::from_utf8_lossy(&bytes[3..]).into_owned());
    }
    // UTF-16 LE/BE BOM
    if bytes.starts_with(&[0xFF, 0xFE]) || bytes.starts_with(&[0xFE, 0xFF]) {
        let little = bytes[0] == 0xFF;
        let mut u16s: Vec<u16> = Vec::with_capacity((bytes.len() - 2) / 2);
        let mut i = 2;
        while i + 1 < bytes.len() {
            let v = if little {
                u16::from_le_bytes([bytes[i], bytes[i + 1]])
            } else {
                u16::from_be_bytes([bytes[i], bytes[i + 1]])
            };
            u16s.push(v);
            i += 2;
        }
        return Ok(String::from_utf16_lossy(&u16s));
    }

    // 无 BOM：先按 UTF-8 严格解码，失败回退 GBK（中文 Windows ANSI）
    match std::str::from_utf8(&bytes) {
        Ok(s) => Ok(s.to_string()),
        Err(_) => {
            let (cow, _enc, _had_errors) = GBK.decode(&bytes);
            Ok(cow.into_owned())
        }
    }
}

/// 探测默认书目《红楼梦.txt》。
/// - debug 开发态：相对 src-tauri 目录上溯（CARGO_MANIFEST_DIR），免手选；
/// - 环境变量 HONGLOU_BOOK_PATH 可覆盖；
/// - release 态：返回 None，由用户通过文件对话框选择。
#[tauri::command]
fn probe_default_book() -> Option<String> {
    if let Ok(p) = std::env::var("HONGLOU_BOOK_PATH") {
        if !p.is_empty() && std::path::Path::new(&p).is_file() {
            return Some(p);
        }
    }
    #[cfg(debug_assertions)]
    {
        // CARGO_MANIFEST_DIR = .../红楼梦范例/app/src-tauri
        let cand = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("红楼梦.txt");
        if cand.is_file() {
            return cand.canonicalize().ok().map(|p| p.to_string_lossy().into_owned());
        }
    }
    None
}

/// 打开文件选择对话框，返回选中的文本文件路径。
#[tauri::command]
async fn pick_text_file(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let file_path = app
        .dialog()
        .file()
        .add_filter("文本文件", &["txt"])
        .blocking_pick_file();
    Ok(file_path.map(|p| p.to_string()))
}

/// 调用 Python sidecar 方法（通用入口）。同步 IO 放 spawn_blocking，不阻塞 UI 线程。
#[tauri::command]
async fn call_sidecar(
    state: tauri::State<'_, Arc<sidecar::SidecarManager>>,
    method: String,
    params: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let mgr = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || mgr.call(&method, params))
        .await
        .map_err(|e| format!("sidecar 任务失败: {e}"))?
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            app.manage(Arc::new(sidecar::SidecarManager::new()));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            read_text_file,
            probe_default_book,
            pick_text_file,
            call_sidecar
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");
    app.run(|app, event| {
        // 应用退出时清理 sidecar 子进程
        if let tauri::RunEvent::Exit = event {
            if let Some(mgr) = app.try_state::<Arc<sidecar::SidecarManager>>() {
                mgr.shutdown();
            }
        }
    });
}
