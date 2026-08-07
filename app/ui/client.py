from __future__ import annotations

from typing import Any

import httpx


def local_api_base_url(host: str, port: int) -> str:
    """生成桌面端访问本机 API 的地址，避免将通配监听地址当作目标地址。"""
    if host == "0.0.0.0":
        host = "127.0.0.1"
    elif host == "::":
        host = "[::1]"
    return f"http://{host}:{port}"


class ApiClient:
    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = httpx.request(method, f"{self.base_url}{path}", headers=self._headers(), timeout=30, **kwargs)
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)
