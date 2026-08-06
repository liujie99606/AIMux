from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_model_catalog_seeds_defaults_and_supports_crud(settings):
    """新库应填充默认版本，并能从模型管理 API 完成增删改查。"""
    client = TestClient(create_app(settings))
    initial = client.get("/api/models")
    assert initial.status_code == 200
    assert {(item["type"], item["name"]) for item in initial.json()["items"]} == {
        ("openai", "gpt-5.5"),
        ("openai", "gpt-5.5-pro"),
        ("openai", "gpt-5.6"),
        ("openai", "gpt-5.6-sol"),
        ("openai", "gpt-5.6-terra"),
        ("openai", "gpt-5.6-luna"),
        ("anthropic", "claude-opus-4-8"),
        ("anthropic", "claude-sonnet-4-8"),
        ("anthropic", "claude-haiku-4-8"),
    }
    created = client.post("/api/models", json={"type": "openai", "name": "gpt-6-preview"})
    assert created.status_code == 200
    model_id = created.json()["id"]
    assert [item["name"] for item in client.get("/api/models", params={"type": "openai"}).json()["items"]][-1] == "gpt-6-preview"
    assert client.put(f"/api/models/{model_id}", json={"type": "anthropic", "name": "claude-5-preview"}).json()["type"] == "anthropic"
    assert client.post("/api/models", json={"type": "anthropic", "name": "claude-5-preview"}).status_code == 409
    assert client.delete(f"/api/models/{model_id}").status_code == 204
    assert "claude-5-preview" not in {item["name"] for item in client.get("/api/models").json()["items"]}
