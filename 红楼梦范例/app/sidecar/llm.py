#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 问答客户端（M3）—— OpenAI 兼容协议，外部 API 与本地 Ollama 可切换。

- 外部：DeepSeek / OpenAI / 通义 / Moonshot 等任何 OpenAI 兼容端点
- 本地：Ollama（base_url=http://localhost:11434/v1）
均由 .env 的 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 决定。
"""

import json
from typing import Any, Dict, List, Optional

from config import LLMConfig

_SYSTEM_PROMPT = (
    "你是《红楼梦》文本分析助手。基于用户提供的【原文片段】回答问题，"
    "不要编造原文没有的内容。引用原文时给出【片段编号】如 [1][2]。"
    "回答用中文，简明准确。"
)


def _explain(exc: Exception, cfg: LLMConfig) -> str:
    """把 SDK 原始异常翻译成用户能照着做的提示。

    直接把 httpx/openai 的 401 报文丢到界面上，用户只会看到一长串英文 JSON，
    既不知道错在哪、也不知道改哪个文件。这里按错误类别给出定位。
    """
    text = f"{type(exc).__name__}: {exc}"
    low = text.lower()
    if "401" in text or "authenticationerror" in low or "invalid_api_key" in low:
        return (
            f"LLM 鉴权失败（401）：{cfg.base_url} 拒绝了当前 API Key。\n"
            "排查顺序：① 键是否输错/已过期/已被撤销；"
            "② 键与 base_url 是否属于同一家（方舟的键不能用于 DeepSeek 端点，反之亦然）；"
            "③ 方舟需确认已开通对应模型。\n"
            f"当前配置：model={cfg.model}，key={cfg.api_key[:8]}…"
            f"{cfg.api_key[-4:] if len(cfg.api_key) > 12 else ''}"
            "（改 app/sidecar/.env 后重启应用生效）。"
        )
    if "403" in text or "permission" in low:
        return (f"LLM 拒绝访问（403）：Key 有效但无该模型权限。\n"
                f"当前 model={cfg.model}，请确认已开通该模型或改用其他模型。")
    if "404" in text or "notfound" in low or "model_not_found" in low:
        return (f"LLM 模型不存在（404）：{cfg.model} 在该端点不可用。\n"
                "方舟用户注意：LLM_MODEL 需填已创建的推理接入点 ID（ep-…）"
                "或平台支持的模型名。")
    if "429" in text or "rate" in low:
        return "LLM 限流（429）：请求过于频繁或额度用尽，稍后重试。"
    if "timeout" in low or "timed out" in low:
        return (f"LLM 请求超时：{cfg.base_url} 无响应。\n"
                "检查网络/代理，或改用本地 Ollama（LLM_BASE_URL=http://localhost:11434/v1）。")
    if "connect" in low or "connection" in low:
        return (f"LLM 连接失败：无法连上 {cfg.base_url}。\n"
                "检查 base_url 拼写与网络连通性。")
    return f"LLM 调用失败：{text}"


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._client: Optional[Any] = None

    # openai SDK 懒加载：首次 chat 才导入（sidecar 冷启动更快）
    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # type: ignore
            self._client = OpenAI(
                api_key=self.cfg.api_key or "sk-local",
                base_url=self.cfg.base_url,
                timeout=120,
            )
        return self._client

    @property
    def usable(self) -> bool:
        return self.cfg.usable

    def chat(self, messages: List[Dict[str, str]],
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        if not self.usable:
            raise RuntimeError(
                "LLM 未配置：请设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL "
                "（app/sidecar/.env）")
        client = self._get_client()
        try:
            resp = client.chat.completions.create(
                model=self.cfg.model,
                messages=messages,
                temperature=float(temperature if temperature is not None
                                  else self.cfg.temperature),
                max_tokens=int(max_tokens or self.cfg.max_tokens),
            )
        except Exception as e:  # noqa: BLE001 —— 统一翻译成可操作提示
            raise RuntimeError(_explain(e, self.cfg)) from e
        return (resp.choices[0].message.content or "").strip()

    def ask_with_context(self, question: str,
                         contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """RAG 问答：组装带编号片段的上下文，要求引用出处。

        contexts: [{id, chapter_idx, line_start, line_end, text, distance?}]
        返回: {answer, used: [{id, chapter_idx, line_start, line_end}]}
        """
        blocks = []
        for i, ctx in enumerate(contexts, 1):
            loc = f"第{ctx.get('chapter_idx', 0) + 1}章"
            blocks.append(
                f"[{i}]（{loc} 行{ctx.get('line_start')}-{ctx.get('line_end')}）"
                f"\n{ctx['text'][:800]}")
        user_content = (
            "请基于以下原文片段回答问题。\n\n"
            "【原文片段】\n" + "\n\n".join(blocks) + "\n\n"
            f"【问题】{question}\n\n"
            "请给出回答，并在引用处标注 [片段编号]。"
        )
        answer = self.chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ])
        used = [{"id": c.get("id"), "chapter_idx": c.get("chapter_idx"),
                 "line_start": c.get("line_start"),
                 "line_end": c.get("line_end")} for c in contexts]
        return {"answer": answer, "used": used}

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        return self.chat(messages)


# 模块级单例
_client: Optional[LLMClient] = None


def get_llm(cfg: LLMConfig) -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient(cfg)
    return _client


def reset_llm() -> None:
    global _client
    _client = None