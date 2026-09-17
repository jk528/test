#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红楼梦阅读分析一体化 — Python sidecar（M1 骨架）

通信协议：stdio 上的 NDJSON / JSON-RPC 2.0 风格（每行一个 JSON 对象）
  请求：{"id": <int|str>, "method": "<方法名>", "params": {…}}
  成功：{"id": <同请求>, "result": {…}}
  失败：{"id": <同请求>, "error": {"code": <int>, "message": "<说明>"}}
  约定：stdout 只输出响应（保证 NDJSON 干净）；所有日志走 stderr。

M1 提供：
  ping             —— 连通性 / 版本自检
  chapter_outline  —— 解析章节目录（规则与前端 TS、splittxt2 VBA 完全一致）

M2 新增：
  analyze_sentiment —— 段落级（物理行级）情感分析，复用 基础/emotion_analysis.py 的
                        EmotionAnalyzer（DUTIR 七类）+ jieba 分词（红楼梦分词词典）。

仅使用标准库 + jieba（venv 内），便于后续 PyInstaller 打包为单可执行 sidecar。
"""

import json
import os
import re
import sys
import traceback

PROTOCOL = "honglou-sidecar/1"
SIDE_VERSION = "0.2.0-m2"

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


# ---------------- 基础目录与引擎懒加载 ----------------

# DUTIR 七类情绪顺序（与 emotion_analysis.py EmotionAnalyzer 一致）
EMOTION_ORDER = ["好", "乐", "哀", "怒", "惧", "恶", "惊"]


def _resolve_base_dir():
    """定位 基础/ 目录：环境变量优先，否则相对 sidecar.py 上溯两级。"""
    env = os.environ.get("HONGLOU_BASE_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    # sidecar.py 位于 app/sidecar/honglou_sidecar.py，基础在 ../../基础/
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(here, "..", "..", "基础")
    if os.path.isdir(cand):
        return os.path.abspath(cand)
    return None


BASE_DIR = _resolve_base_dir()
_engine = None  # 懒加载：首次调 analyze_sentiment 时初始化


def _get_engine():
    """加载 jieba（红楼梦分词词典）+ EmotionAnalyzer（DUTIR 七类）。"""
    global _engine
    if _engine is not None:
        return _engine
    if not BASE_DIR:
        raise RuntimeError("基础目录未找到（HONGLOU_BASE_DIR 未设且相对路径无效）")
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from emotion_analysis import EmotionAnalyzer  # noqa: E402
    import jieba  # noqa: E402
    seg_dict = os.path.join(BASE_DIR, "红楼梦分词词典.txt")
    if os.path.isfile(seg_dict):
        jieba.load_userdict(seg_dict)
    analyzer = EmotionAnalyzer()
    _engine = {"jieba": jieba, "analyzer": analyzer}
    log(f"分析引擎已加载 BASE_DIR={BASE_DIR}")
    return _engine


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


def m_analyze_sentiment(params: dict) -> dict:
    """段落级（物理行级）情感分析。

    params: {text: str}  —— 章内文本（按 \\n 分行；line_offset 为章内 0 基相对行号）
    返回:   {paragraphs: [{line_offset, dutir_top, polarity, intensity, weights}]}
            dutir_top 为 None 表示该行无情感词（不着色）。
    """
    text = params.get("text")
    if not isinstance(text, str):
        raise ValueError("params 需要 text (string)")
    eng = _get_engine()
    jieba = eng["jieba"]
    analyzer = eng["analyzer"]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    paragraphs = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        words = jieba.lcut(stripped)
        result = analyzer.analyze_words(words)
        counts = result["emotion_counts"]
        total = result["total_emotion_words"]
        if total == 0:
            paragraphs.append({
                "line_offset": i,
                "dutir_top": None,
                "polarity": 0.0,
                "intensity": 0.0,
                "weights": {},
            })
            continue
        # 主导情绪：七类计数最大者
        top = max(EMOTION_ORDER, key=lambda e: counts.get(e, 0))
        # 极性：(正面 - 负面) / 总情感词数，归一化到 -1~1
        polarity = round(
            (result["positive_emotion_count"] - result["negative_emotion_count"])
            / total, 3
        )
        # 强度：情感词密度 = 总情感词数 / 分词数
        intensity = round(total / max(len(words), 1), 3)
        weights = {e: counts.get(e, 0) for e in EMOTION_ORDER}
        paragraphs.append({
            "line_offset": i,
            "dutir_top": top,
            "polarity": polarity,
            "intensity": intensity,
            "weights": weights,
        })
    return {"paragraphs": paragraphs}


METHODS = {
    "ping": m_ping,
    "chapter_outline": m_chapter_outline,
    "analyze_sentiment": m_analyze_sentiment,
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
