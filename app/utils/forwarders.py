from __future__ import annotations

from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings
from app.models import Account
from app.utils.crypto import decrypt_api_key


@dataclass
class PreparedStream:
    client: httpx.AsyncClient
    response: httpx.Response
    _iterator: AsyncIterator[bytes] | None = None

    def chunks(self) -> AsyncIterator[bytes]:
        """返回唯一的上游字节流迭代器，避免重复读取响应。"""
        if self._iterator is None:
            self._iterator = self.response.aiter_bytes()
        return self._iterator

    async def first_chunk(self) -> bytes | None:
        """预读首块，用于在向客户端输出前判断是否需要切换账号。"""
        iterator = self.chunks()
        try:
            return await anext(iterator)
        except StopAsyncIteration:
            return None

    async def close(self) -> None:
        """释放上游响应与对应 HTTP 客户端。"""
        await self.response.aclose()
        await self.client.aclose()


def _headers(account: Account, body: dict[str, Any]) -> dict[str, str]:
    """根据账号类型组装上游认证头，不做协议转换。"""
    key = decrypt_api_key(account.api_key_encrypted)
    if account.type == "anthropic":
        return {
            "x-api-key": key,
            "anthropic-version": str(body.get("anthropic_version") or "2023-06-01"),
            "content-type": "application/json",
        }
    return {"Authorization": f"Bearer {key}", "content-type": "application/json"}


def upstream_url(account: Account, endpoint: str) -> str:
    """拼接上游路径，并规避 OpenAI base_url 已带 /v1 时的重复版本号。"""
    base_url = account.base_url.rstrip("/")
    if account.type == "openai" and base_url.endswith("/v1") and endpoint.startswith("/v1/"):
        endpoint = endpoint[3:]
    return f"{base_url}{endpoint}"


def _timeout(settings: Settings) -> httpx.Timeout:
    """构造连接、首字和整体上游请求使用的超时设置。"""
    return httpx.Timeout(
        settings.upstream_timeout_seconds,
        connect=settings.first_token_timeout_seconds,
        read=settings.upstream_timeout_seconds,
    )


async def post(
    account: Account, endpoint: str, body: dict[str, Any], settings: Settings
) -> httpx.Response:
    """执行一次非流式上游 POST 请求。"""
    async with httpx.AsyncClient(timeout=_timeout(settings)) as client:
        return await client.post(
            upstream_url(account, endpoint), json=body, headers=_headers(account, body)
        )


async def open_stream(
    account: Account, endpoint: str, body: dict[str, Any], settings: Settings
) -> PreparedStream:
    """打开流式上游响应，调用方负责读取和关闭。"""
    client = httpx.AsyncClient(timeout=_timeout(settings))
    try:
        request = client.build_request(
            "POST", upstream_url(account, endpoint), json=body, headers=_headers(account, body)
        )
        response = await client.send(request, stream=True)
        return PreparedStream(client=client, response=response)
    except Exception:
        await client.aclose()
        raise
