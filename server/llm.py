"""LLM 代理：OpenAI 兼容协议，SSE 流式中继（biz_requirement.md §4.4.4）。

API Key 只存服务端本地库，前端不直连 LLM，避免 webview 泄露与跨域问题。
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
import logging

import httpx
import ssl

CHART_CONTEXT_TEMPLATE = "以下是当前命盘的完整 JSON 数据（含排盘结构、格局分析、星曜分析与运限定位），请基于它进行分析：\n```json\n%s\n```"
logger = logging.getLogger("zwds")
# 国内 LLM 服务直连：走代理节点（尤其免费线路）长连接流式易被中间设备截断，
# 出现 SSL BAD_RECORD_MAC 等错误；这些主机国内直连更快更稳
DIRECT_HOSTS = (
    "api.deepseek.com",
    "api.moonshot.cn",
    "dashscope.aliyuncs.com",
    "open.bigmodel.cn",
)


def _client(timeout: httpx.Timeout, base_url: str) -> httpx.AsyncClient:
    host = httpx.URL(base_url).host or ""
    # trust_env=False = 忽略 ALL_PROXY 等环境变量，直连
    trust_env = not any(host == h or host.endswith("." + h) for h in DIRECT_HOSTS)
    if trust_env:
        return httpx.AsyncClient(timeout=timeout)
    # 实测：到 EdgeOne CDN（api.deepseek.com 等）的 TLS 1.3 连接被链路中间设备
    # 随机篡改（SSLV3_ALERT_BAD_RECORD_MAC），TLS 1.2 稳定。直连时锁定 1.2。
    ctx = ssl.create_default_context()
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return httpx.AsyncClient(timeout=timeout, trust_env=False, verify=ctx)


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

    # 到 LLM 的链路可能随机断流（SSL BAD_RECORD_MAC 等）；只要还没产出任何
    # 内容，重试是安全的（上游未开始生成或生成未送达，无副作用）。
    # 一旦已产出增量则不再重试，避免重复正文。
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        produced = False
        try:
            async with _client(httpx.Timeout(120.0, connect=15.0), base_url) as client:
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
                            produced = True
                            yield "reasoning", reasoning
                        if content:
                            produced = True
                            yield "content", content
            if attempt > 1:
                logger.info("stream_chat 第 %d 次尝试成功", attempt)
            return
        except Exception as e:
            # 非 200 是上游明确拒绝（鉴权/参数/限流），不重试
            if isinstance(e, RuntimeError) or produced:
                raise
            last_exc = e
            logger.warning("stream_chat 第 %d 次尝试失败（未产出内容，将重试）: %r", attempt, e)
    assert last_exc is not None
    raise last_exc



async def list_models(base_url: str, api_key: str | None) -> list[str]:
    """查询上游可用模型 id 列表（OpenAI 兼容 GET /models）。"""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = f"{base_url.rstrip('/')}/models"
    async with _client(httpx.Timeout(30.0, connect=10.0), base_url) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM 服务返回 {resp.status_code}：{resp.text[:300]}")
        data = resp.json()
        return sorted(m["id"] for m in data.get("data", []) if "id" in m)