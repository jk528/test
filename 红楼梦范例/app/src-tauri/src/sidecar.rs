// Python sidecar 进程管理：长驻 stdio JSON-RPC 子进程。
// 懒启动：首次 call 时才 spawn，失败不影响 M1 阅读功能。
// 通信：stdin 写一行 NDJSON 请求，stdout 读一行响应（stderr 继承给父进程看日志）。

use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;

struct SidecarInner {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    next_id: u64,
}

pub struct SidecarManager {
    inner: Mutex<Option<SidecarInner>>,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(None),
        }
    }

    fn ensure_started(&self) -> Result<(), String> {
        let mut guard = self.inner.lock().map_err(|e| format!("sidecar 锁失败: {e}"))?;
        if guard.is_some() {
            return Ok(());
        }
        let python_path = resolve_python();
        let sidecar_path = resolve_sidecar_path();
        let mut child = Command::new(&python_path)
            .arg(&sidecar_path)
            .env("PYTHONIOENCODING", "utf-8") // 强制 Python stdio 用 UTF-8，避免 Windows GBK
            .env("PYTHONUTF8", "1") // PEP 540: UTF-8 模式
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit()) // sidecar 日志走 stderr，继承给父进程
            .spawn()
            .map_err(|e| {
                format!("拉起 sidecar 失败 (python={python_path}, script={sidecar_path}): {e}")
            })?;
        let stdin = child.stdin.take().ok_or("无法获取 sidecar stdin")?;
        let stdout = child.stdout.take().ok_or("无法获取 sidecar stdout")?;
        *guard = Some(SidecarInner {
            child,
            stdin,
            stdout: BufReader::new(stdout),
            next_id: 1,
        });
        Ok(())
    }

    /// 调用 sidecar 方法：写一行 NDJSON 请求，读一行响应。
    /// 同步阻塞 IO，调用方应放在 spawn_blocking 中。
    pub fn call(&self, method: &str, params: Value) -> Result<Value, String> {
        self.ensure_started()?;
        let mut guard = self.inner.lock().map_err(|e| format!("sidecar 锁失败: {e}"))?;
        let inner = guard.as_mut().ok_or("sidecar 未启动")?;
        let id = inner.next_id;
        inner.next_id += 1;
        let req = serde_json::json!({"id": id, "method": method, "params": params});
        let mut line = serde_json::to_string(&req).map_err(|e| format!("序列化请求失败: {e}"))?;
        line.push('\n');
        inner
            .stdin
            .write_all(line.as_bytes())
            .map_err(|e| format!("写入 sidecar stdin 失败: {e}"))?;
        inner
            .stdin
            .flush()
            .map_err(|e| format!("flush sidecar stdin 失败: {e}"))?;
        let mut buf = String::new();
        let n = inner
            .stdout
            .read_line(&mut buf)
            .map_err(|e| format!("读取 sidecar stdout 失败: {e}"))?;
        if n == 0 {
            return Err("sidecar 已关闭 stdout".into());
        }
        let resp: Value =
            serde_json::from_str(&buf).map_err(|e| format!("解析 sidecar 响应失败: {e}"))?;
        if let Some(err) = resp.get("error") {
            let msg = err
                .get("message")
                .and_then(|m| m.as_str())
                .map(|s| s.to_string())
                .unwrap_or_else(|| err.to_string());
            return Err(format!("sidecar 错误: {msg}"));
        }
        resp.get("result")
            .cloned()
            .ok_or_else(|| "sidecar 响应缺少 result 字段".into())
    }

    /// 应用退出时清理：kill 子进程。sidecar 无持久状态，kill 无损失。
    pub fn shutdown(&self) {
        let mut guard = match self.inner.lock() {
            Ok(g) => g,
            Err(_) => return,
        };
        if let Some(mut inner) = guard.take() {
            let _ = inner.child.kill();
            let _ = inner.child.wait();
        }
    }
}

/// 定位 Python 解释器：环境变量 HONGLOU_PYTHON 优先，否则用项目 venv。
fn resolve_python() -> String {
    if let Ok(p) = std::env::var("HONGLOU_PYTHON") {
        if !p.is_empty() && std::path::Path::new(&p).is_file() {
            return p;
        }
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        let venv = format!("{}\\.venvs\\honglou\\Scripts\\python.exe", home);
        if std::path::Path::new(&venv).is_file() {
            return venv;
        }
    }
    "python".to_string()
}

/// 定位 sidecar.py：dev 态相对 CARGO_MANIFEST_DIR 上溯到 app/sidecar/。
/// 注意：不使用 canonicalize —— 它在 Windows 上会产生 \\?\ UNC 前缀，
/// 该前缀下 Windows 跳过路径解析，导致 Python 里 os.path.join(..., "..", ..) 的 .. 不被解析。
/// 保留带 .. 的路径交给 Python，Python 的 os.path.abspath/normpath 会正确解析。
fn resolve_sidecar_path() -> String {
    let cand = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("sidecar")
        .join("honglou_sidecar.py");
    if cand.is_file() {
        return cand.to_string_lossy().into_owned();
    }
    "honglou_sidecar.py".to_string()
}
