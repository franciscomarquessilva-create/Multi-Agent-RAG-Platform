import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings_returns_provider_catalog(client: AsyncClient):
    resp = await client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    providers = {option["provider"] for option in data["available_models"]}
    assert {"OpenAI", "Anthropic", "Gemini", "Grok"}.issubset(providers)
    assert all("enabled" in option for option in data["available_models"])


@pytest.mark.asyncio
async def test_update_settings_updates_credits_only(client: AsyncClient):
    resp = await client.put("/settings", json={"credits_per_process": 3})
    assert resp.status_code == 200
    assert resp.json()["credits_per_process"] == 3


@pytest.mark.asyncio
async def test_create_agent_respects_enabled_model_catalog(client: AsyncClient):
    disable = await client.put("/settings/models", json={
        "current_model": "openai/gpt-5.2",
        "provider": "OpenAI",
        "label": "GPT-5.2",
        "model": "openai/gpt-5.2",
        "enabled": False,
    })
    assert disable.status_code == 200

    allowed = await client.post("/agents", json={
        "name": "Allowed",
        "model": "gpt-4o",
        "api_key": "sk-test",
        "agent_type": "orchestrator",
    })
    assert allowed.status_code == 201

    blocked = await client.post("/agents", json={
        "name": "Blocked",
        "model": "gpt-5.2",
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
        "enabled": True,
    })
    assert add.status_code == 200
    assert any(option["model"] == "openai/gpt-test" for option in add.json()["available_models"])

    disable = await client.put("/settings/models", json={
        "current_model": "openai/gpt-test",
        "provider": "OpenAI",
        "label": "GPT Test",
        "model": "openai/gpt-test",
        "enabled": False,
    })
    assert disable.status_code == 200
    disabled = next(option for option in disable.json()["available_models"] if option["model"] == "openai/gpt-test")
    assert disabled["enabled"] is False

    edit = await client.put("/settings/models", json={
        "current_model": "openai/gpt-test",
        "provider": "OpenAI",
        "label": "GPT Test Edited",
        "model": "openai/gpt-test",
        "enabled": True,
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
        "enabled": True,
    })
    assert add.status_code == 200

    agent = await client.post("/agents", json={
        "name": "KeepAgent",
        "model": "openai/gpt-keep",
        "api_key": "sk-keep",
        "agent_type": "orchestrator",
    })
    assert agent.status_code == 201

    delete = await client.delete("/settings/models", params={"model": "openai/gpt-keep"})
    assert delete.status_code == 400


@pytest.mark.asyncio
async def test_default_provider_key_crud(client: AsyncClient):
    set_resp = await client.post("/settings/default-keys", json={"provider": "OpenAI", "api_key": "sk-provider"})
    assert set_resp.status_code == 200
    assert "openai" in set_resp.json()["default_key_providers"]

    delete_resp = await client.delete("/settings/default-keys", params={"provider": "OpenAI"})
    assert delete_resp.status_code == 200
    assert "openai" not in delete_resp.json()["default_key_providers"]
