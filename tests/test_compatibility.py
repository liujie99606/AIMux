from __future__ import annotations

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.main import create_app


def test_extended_openai_routes_and_compatible_headers(settings, monkeypatch):
    """OpenAI 扩展端点应保留路径并只透传受支持的协议头。"""
    calls: list[dict] = []

    async def fake_forward(**kwargs):
        calls.append(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr("app.controller.openai_api.forward_non_stream", fake_forward)
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/embeddings",
        headers={"OpenAI-Beta": "assistants=v2", "Idempotency-Key": "request-1", "X-Ignore": "no"},
        json={"model": "text-embedding-3-small", "input": "hello"},
    )
    assert response.status_code == 200
    assert calls[0]["endpoint"] == "/v1/embeddings"
    assert calls[0]["upstream_headers"] == {"openai-beta": "assistants=v2", "idempotency-key": "request-1"}
    assert client.post("/v1/images/generations", content=b"not-json").status_code == 415


def test_anthropic_extended_routes_and_compatible_headers(settings, monkeypatch):
    """Anthropic 扩展端点应原样转发，不混入 OpenAI 专属请求头。"""
    calls: list[dict] = []

    async def fake_forward(**kwargs):
        calls.append(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr("app.controller.anthropic_api.forward_non_stream", fake_forward)
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/messages/count_tokens",
        headers={"anthropic-beta": "token-counting-2024-11-01", "OpenAI-Beta": "ignored"},
        json={"model": "claude-test", "messages": []},
    )
    assert response.status_code == 200
    assert calls[0]["endpoint"] == "/v1/messages/count_tokens"
    assert calls[0]["upstream_headers"] == {"anthropic-beta": "token-counting-2024-11-01"}
