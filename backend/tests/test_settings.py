import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings_returns_provider_catalog(client: AsyncClient):
    resp = await client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    providers = {option["provider"] for option in data["available_models"]}
    assert {"OpenAI", "Anthropic", "Gemini", "Grok"}.issubset(providers)
    assert len(data["allowed_models"]) > 0


@pytest.mark.asyncio
async def test_update_settings_rejects_unknown_model(client: AsyncClient):
    resp = await client.put("/settings", json={"allowed_models": ["unknown/provider-model"]})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_agent_respects_allowed_models(client: AsyncClient):
    update = await client.put("/settings", json={"allowed_models": ["openai/gpt-5.2"]})
    assert update.status_code == 200

    allowed = await client.post("/agents", json={
        "name": "Allowed",
        "model": "GPT-5.2",
        "api_key": "sk-test",
        "agent_type": "orchestrator",
    })
    assert allowed.status_code == 201

    blocked = await client.post("/agents", json={
        "name": "Blocked",
        "model": "claude-3-5-sonnet",
        "api_key": "sk-test-2",
        "agent_type": "slave",
    })
    assert blocked.status_code == 400


@pytest.mark.asyncio
async def test_model_catalog_can_add_edit_delete_and_enable(client: AsyncClient):
    add = await client.post("/settings/models", json={
        "provider": "OpenAI",
        "label": "GPT Test",
        "model": "openai/gpt-test",
    })
    assert add.status_code == 200
    assert any(option["model"] == "openai/gpt-test" for option in add.json()["available_models"])

    enable = await client.put("/settings", json={"allowed_models": ["openai/gpt-test"]})
    assert enable.status_code == 200
    assert enable.json()["allowed_models"] == ["openai/gpt-test"]

    edit = await client.put("/settings/models", json={
        "current_model": "openai/gpt-test",
        "provider": "OpenAI",
        "label": "GPT Test Edited",
        "model": "openai/gpt-test",
    })
    assert edit.status_code == 200
    edited = next(option for option in edit.json()["available_models"] if option["model"] == "openai/gpt-test")
    assert edited["label"] == "GPT Test Edited"

    delete = await client.delete("/settings/models", params={"model": "openai/gpt-test"})
    assert delete.status_code == 200
    assert all(option["model"] != "openai/gpt-test" for option in delete.json()["available_models"])


@pytest.mark.asyncio
async def test_model_catalog_cannot_delete_model_used_by_agent(client: AsyncClient):
    add = await client.post("/settings/models", json={
        "provider": "OpenAI",
        "label": "GPT Keep",
        "model": "openai/gpt-keep",
    })
    assert add.status_code == 200

    update = await client.put("/settings", json={"allowed_models": ["openai/gpt-keep"]})
    assert update.status_code == 200

    agent = await client.post("/agents", json={
        "name": "KeepAgent",
        "model": "openai/gpt-keep",
        "api_key": "sk-keep",
        "agent_type": "orchestrator",
    })
    assert agent.status_code == 201

    delete = await client.delete("/settings/models", params={"model": "openai/gpt-keep"})
    assert delete.status_code == 400
