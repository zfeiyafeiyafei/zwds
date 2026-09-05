"""LLM 代理：OpenAI 兼容协议，SSE 流式中继（biz_requirement.md §4.4.4）。

API Key 只存服务端本地库，前端不直连 LLM，避免 webview 泄露与跨域问题。
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx

CHART_CONTEXT_TEMPLATE = "以下是当前命盘的完整 JSON 数据（含排盘结构、格局分析、星曜分析与运限定位），请基于它进行分析：\n```json\n%s\n```"


def build_messages(
    skill_prompt: str,
    chart: dict,
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """组装对话：system=skill 提示词，随后注入命盘 JSON，再接对话历史。

    命盘 JSON 每轮都注入（多轮对话需保持上下文一致，§4.4.3-3）。
    """
    return [
        {"role": "system", "content": skill_prompt},
        {"role": "user", "content": CHART_CONTEXT_TEMPLATE % json.dumps(chart, ensure_ascii=False)},
        {"role": "assistant", "content": "收到，我已阅读此命盘数据。请告诉我分析主题或你的问题。"},
        *history,
    ]


async def stream_chat(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[tuple[str, str], None]:
    """向上游 LLM 发起流式请求，产出 (kind, text)：content=正文增量，reasoning=思考增量。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": messages, "stream": True}
    url = f"{base_url.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", "replace")[:500]
                raise RuntimeError(f"LLM 服务返回 {resp.status_code}：{body}")
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                reasoning = delta.get("reasoning_content")
                # 推理模型先发 reasoning_content：中继给前端展示"思考中"，
                # 否则长推理期间界面像无响应
                if reasoning:
                    yield "reasoning", reasoning
                if content:
                    yield "content", content
