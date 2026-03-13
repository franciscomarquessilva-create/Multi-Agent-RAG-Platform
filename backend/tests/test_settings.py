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
