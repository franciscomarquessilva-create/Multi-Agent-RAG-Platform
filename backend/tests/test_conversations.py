import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def agent_id(client: AsyncClient):
    r = await client.post("/agents", json={"name": "Orch", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, agent_id):
    slave = await client.post("/agents", json={"name": "S1", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    slave_id = slave.json()["id"]
    resp = await client.post("/conversations", json={"title": "My Convo", "orchestrator_id": agent_id, "agent_ids": [slave_id]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Convo"
    assert data["orchestrator_id"] == agent_id
    assert slave_id in data["agent_ids"]


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, agent_id):
    await client.post("/conversations", json={"title": "C1", "orchestrator_id": agent_id, "agent_ids": []})
    await client.post("/conversations", json={"title": "C2", "orchestrator_id": agent_id, "agent_ids": []})
    resp = await client.get("/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient, agent_id):
    r = await client.post("/conversations", json={"title": "Detail", "orchestrator_id": agent_id, "agent_ids": []})
    conv_id = r.json()["id"]
    resp = await client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == conv_id
    assert "messages" in resp.json()


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, agent_id):
    r = await client.post("/conversations", json={"title": "ToDelete", "orchestrator_id": agent_id, "agent_ids": []})
    conv_id = r.json()["id"]
    resp = await client.delete(f"/conversations/{conv_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/conversations/{conv_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_mediator_conversation_requires_exactly_two_slaves(client: AsyncClient):
    orch = await client.post("/agents", json={
        "name": "Mediator",
        "model": "gpt-4o",
        "api_key": "k1",
        "agent_type": "orchestrator",
        "orchestrator_mode": "mediator",
    })
    slave1 = await client.post("/agents", json={"name": "S1", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    orch_id = orch.json()["id"]
    s1_id = slave1.json()["id"]

    resp = await client.post("/conversations", json={
        "title": "Bad Mediator Convo",
        "orchestrator_id": orch_id,
        "agent_ids": [s1_id],
    })
    assert resp.status_code == 400
    assert "exactly two slave agents" in resp.json()["detail"]
