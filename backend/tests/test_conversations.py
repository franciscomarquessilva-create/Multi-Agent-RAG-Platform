import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def agent_id(client: AsyncClient):
    r = await client.post("/agents", json={"name": "Orch", "model": "gpt-4o", "api_key": "k1"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, agent_id):
    resp = await client.post("/conversations", json={"title": "My Convo", "agent_ids": [agent_id]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Convo"
    assert agent_id in data["agent_ids"]


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, agent_id):
    await client.post("/conversations", json={"title": "C1", "agent_ids": []})
    await client.post("/conversations", json={"title": "C2", "agent_ids": []})
    resp = await client.get("/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient, agent_id):
    r = await client.post("/conversations", json={"title": "Detail", "agent_ids": []})
    conv_id = r.json()["id"]
    resp = await client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == conv_id
    assert "messages" in resp.json()


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, agent_id):
    r = await client.post("/conversations", json={"title": "ToDelete", "agent_ids": []})
    conv_id = r.json()["id"]
    resp = await client.delete(f"/conversations/{conv_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/conversations/{conv_id}")
    assert get_resp.status_code == 404
