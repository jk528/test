#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红楼梦阅读分析一体化 — Python sidecar（M1 骨架）

通信协议：stdio 上的 NDJSON / JSON-RPC 2.0 风格（每行一个 JSON 对象）
  请求：{"id": <int|str>, "method": "<方法名>", "params": {…}}
  成功：{"id": <同请求>, "result": {…}}
  失败：{"id": <同请求>, "error": {"code": <int>, "message": "<说明>"}}
  约定：stdout 只输出响应（保证 NDJSON 干净）；所有日志走 stderr。

M1 仅提供：
  ping             —— 连通性 / 版本自检
  chapter_outline  —— 解析章节目录（规则与前端 TS、splittxt2 VBA 完全一致）

M2 起在此协议上扩展 sentiment / highlight 等方法，不改变传输方式。
仅使用标准库，便于 PyInstaller 打包为单可执行 sidecar。
"""

import json
import re
import sys
import traceback

PROTOCOL = "honglou-sidecar/1"
SIDE_VERSION = "0.1.0-m1"

# 与 split_txt.bas 默认正则 #1、前端 src/lib/chapters.ts 一致
# 标准中文：第 + 数字(阿拉伯/中文,含〇两,含大写中文数字壹贰叁…) + 章/回/节/卷 + 可选空白 + 标题
CHAPTER_RE = re.compile(r"^第([0-9一二三四五六七八九十百千万零〇两壹贰叁肆伍陆柒捌玖拾佰仟]+)(章|回|节|卷)\s*(.*)$")


def log(msg: str) -> None:
    """日志一律走 stderr，避免污染 stdout 的 NDJSON。"""
    print(f"[sidecar] {msg}", file=sys.stderr, flush=True)


def read_text_auto(path: str) -> str:
    """BOM 优先；无 BOM 先 UTF-8 严格解码，失败回退 GBK。与 Rust read_text_file 对齐。"""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk", errors="replace")


def parse_chapters(text: str) -> list:
    """逐行、行首锚定，返回章节列表（行号为 0 基物理行）。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters = []
    for i, raw_line in enumerate(lines):
        m = CHAPTER_RE.match(raw_line)
        if not m:
            continue
        chapters.append(
            {
                "index": len(chapters) + 1,
                "line": i,
                "title": raw_line.strip(),
                "number_text": m.group(1),
                "unit": m.group(2),
                "name": (m.group(3) or "").strip(),
            }
        )
    return chapters, len(lines)


# ---------------- JSON-RPC 方法表 ----------------

def m_ping(_params: dict) -> dict:
    return {"protocol": PROTOCOL, "version": SIDE_VERSION, "python": sys.version.split()[0]}


def m_chapter_outline(params: dict) -> dict:
    """params: {path?: str, text?: str}，二选一。"""
    text = params.get("text")
    source = params.get("source", "inline")
    if text is None:
        path = params.get("path")
        if not path:
            raise ValueError("params 需要 path 或 text")
        text = read_text_auto(path)
        source = path
    chapters, total_lines = parse_chapters(text)
    return {
        "source": source,
        "total_lines": total_lines,
        "chapter_count": len(chapters),
        "chapters": chapters,
    }


METHODS = {
    "ping": m_ping,
    "chapter_outline": m_chapter_outline,
}


def handle(req: dict) -> dict:
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}
    fn = METHODS.get(method)
    if fn is None:
        return {"id": rid, "error": {"code": -32601, "message": f"未知方法: {method}"}}
    try:
        return {"id": rid, "result": fn(params)}
    except Exception as e:  # 业务异常统一回传，不让进程退出
        return {"id": rid, "error": {"code": -32000, "message": str(e)}}


def main() -> int:
    log(f"sidecar 启动 protocol={PROTOCOL} version={SIDE_VERSION}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            resp = {"id": None, "error": {"code": -32700, "message": f"JSON 解析失败: {e}"}}
        else:
            resp = handle(req)
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    log("stdin 关闭，sidecar 退出")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
