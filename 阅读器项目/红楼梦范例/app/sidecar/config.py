#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置加载模块（M3 地基）。

优先级：环境变量 > .env 文件 > 内置默认值。
.env 查找顺序：sidecar 同级 (app/sidecar/.env) → 项目根 (红楼梦范例/.env)。
通过 python-dotenv 加载；未安装 dotenv 时退化为手工解析（仅标准库）。

示例：
    from config import get_cfg, resolve_base_dir
    cfg = get_cfg()
    llm = cfg.llm
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    load_dotenv = None

# 目录定位（保持与 honglou_sidecar.py 一致的相对约定）
HERE = Path(__file__).resolve().parent          # app/sidecar
APP_DIR = HERE.parent                            # app
ROOT_DIR = APP_DIR.parent                        # 红楼梦范例（工作区根）


def _resolve_data_dir() -> Path:
    """运行时数据根目录（SQLite 主库 + 嵌入模型缓存）。

    默认放**同步目录之外**：`%USERPROFILE%\\.honglou`。

    理由与 venv 同理（见工程约定 §8）：本项目位于云盘同步目录，而运行时数据
    ① 含本机绝对路径、② SQLite 有 -wal/-shm 伴随文件、③ 嵌入模型近 100 MB。
    放在同步目录里会带来三个坏处：云盘客户端加锁导致读写 EBUSY、多机互相
    覆盖导致库损坏、上百 MB 模型白占同步流量。

    可用环境变量 HONGLOU_DATA_DIR 覆盖（如指向某个不参与同步的盘）。
    """
    env = os.environ.get("HONGLOU_DATA_DIR", "").strip()
    if env:
        d = Path(env).expanduser()
    else:
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        d = Path(home) / ".honglou"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        # 兜底：极端情况下退回 app/.data，保证功能可用
        d = APP_DIR / ".data"
        d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = _resolve_data_dir()


def _manual_load(env_path: Path) -> None:
    """无 python-dotenv 时的极简 .env 解析（忽略引号/注释/多行）。"""
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


def _load_env_files() -> None:
    candidates = [HERE / ".env", ROOT_DIR / ".env"]
    for p in candidates:
        if not p.is_file():
            continue
        if load_dotenv is not None:
            load_dotenv(p, override=False)
        else:
            _manual_load(p)
        break  # 只取第一个命中的 .env


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int

    @property
    def usable(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


@dataclass(frozen=True)
class RAGConfig:
    embed_model: str
    embed_batch: int
    top_k: int
    chunk_lines: int


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    rag: RAGConfig
    db_path: str
    base_dir: Optional[str] = None
    log_level: str = "INFO"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def get_cfg() -> AppConfig:
    _load_env_files()
    db_path = _env("HONGLOU_DB_PATH")
    if not db_path:
        data_dir = DATA_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(data_dir / "honglou.sqlite")
    return AppConfig(
        llm=LLMConfig(
            base_url=_env("LLM_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=_env("LLM_API_KEY"),
            model=_env("LLM_MODEL", "deepseek-chat"),
            temperature=float(_env("LLM_TEMPERATURE", "0.3") or 0.3),
            max_tokens=int(_env("LLM_MAX_TOKENS", "2000")),
        ),
        rag=RAGConfig(
            embed_model=_env("EMBED_MODEL", "BAAI/bge-small-zh-v1.5"),
            embed_batch=int(_env("EMBED_BATCH", "16")),
            top_k=int(_env("RAG_TOP_K", "6")),
            chunk_lines=int(_env("RAG_CHUNK_LINES", "20")),
        ),
        db_path=db_path,
        base_dir=_env("HONGLOU_BASE_DIR") or None,
        log_level=_env("LOG_LEVEL", "INFO"),
    )


def resolve_base_dir() -> Optional[str]:
    """定位 基础/ 资产目录：环境变量优先，否则相对 sidecar 上溯两级。"""
    env = os.environ.get("HONGLOU_BASE_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    here = HERE
    if str(here).startswith("\\\\?\\"):  # 剥离 Rust canonicalize 的 UNC 前缀
        here = Path(str(here)[4:])
    cand = (here / ".." / ".." / "基础").resolve()
    if cand.is_dir():
        return str(cand)
    return None


def resolve_analysis_dir() -> Optional[str]:
    """定位 `分析结果/` 目录（M4 回灌历史报告的来源）。

    环境变量 HONGLOU_ANALYSIS_DIR 优先；否则相对 sidecar 上溯两级。
    找不到不影响启动：M4 全局面板会显示「未找到分析产物」。
    """
    env = os.environ.get("HONGLOU_ANALYSIS_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    here = HERE
    if str(here).startswith("\\\\?\\"):
        here = Path(str(here)[4:])
    cand = (here / ".." / ".." / "分析结果").resolve()
    if cand.is_dir():
        return str(cand)
    return None


# 模块级快捷单例（sidecar 进程内全局唯一）
cfg: AppConfig = get_cfg()