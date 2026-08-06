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


def test_each_type_has_exactly_one_default_after_seeding(settings):
    """种子数据应为每个协议类型各设一个测试默认模型。"""
    client = TestClient(create_app(settings))
    items = client.get("/api/models").json()["items"]
    for model_type in ("openai", "anthropic"):
        defaults = [item for item in items if item["type"] == model_type and item["is_default"] == 1]
        assert len(defaults) == 1, f"{model_type} 应有且仅有一个默认模型"


def test_set_default_clears_other_defaults_of_same_type(settings):
    """设置默认后同类型其他模型的默认标记应被清除，另一类型不受影响。"""
    client = TestClient(create_app(settings))
    openai_models = client.get("/api/models", params={"type": "openai"}).json()["items"]
    # 初始默认是 gpt-5.5，把默认切到 gpt-5.6
    target = next(item for item in openai_models if item["name"] == "gpt-5.6")
    result = client.post(f"/api/models/{target['id']}/set-default")
    assert result.status_code == 200
    assert result.json()["is_default"] == 1
    refreshed = client.get("/api/models", params={"type": "openai"}).json()["items"]
    defaults = [item for item in refreshed if item["is_default"] == 1]
    assert len(defaults) == 1 and defaults[0]["name"] == "gpt-5.6"
    # anthropic 的默认不应被影响
    anthropic_defaults = [
        item for item in client.get("/api/models", params={"type": "anthropic"}).json()["items"]
        if item["is_default"] == 1
    ]
    assert len(anthropic_defaults) == 1
