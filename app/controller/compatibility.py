from __future__ import annotations

from fastapi import Request


def passthrough_headers(request: Request, allowed: set[str]) -> dict[str, str]:
    """仅透传协议约定的兼容头，禁止客户端覆盖本地账号认证信息。"""
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() in allowed
    }
