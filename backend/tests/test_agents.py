import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient):
    resp = await client.post("/agents", json={"name": "Alpha", "model": "gpt-4o", "api_key": "sk-test", "agent_type": "slave"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alpha"
    assert "id" in data
    assert data["is_orchestrator"] is True  # first agent auto-orchestrator
    assert data["agent_type"] == "orchestrator"


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client: AsyncClient):
    await client.post("/agents", json={"name": "Alpha", "model": "gpt-4o", "api_key": "sk-test", "agent_type": "orchestrator"})
    resp = await client.post("/agents", json={"name": "Alpha", "model": "gpt-4o", "api_key": "sk-test2", "agent_type": "slave"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    await client.post("/agents", json={"name": "A1", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    await client.post("/agents", json={"name": "A2", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    resp = await client.get("/agents")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient):
    r = await client.post("/agents", json={"name": "OldName", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    agent_id = r.json()["id"]
    resp = await client.put(f"/agents/{agent_id}", json={"name": "NewName"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewName"


@pytest.mark.asyncio
async def test_delete_last_agent(client: AsyncClient):
    r = await client.post("/agents", json={"name": "Only", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    agent_id = r.json()["id"]
    resp = await client.delete(f"/agents/{agent_id}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient):
    await client.post("/agents", json={"name": "A1", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    r2 = await client.post("/agents", json={"name": "A2", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    agent_id = r2.json()["id"]
    resp = await client.delete(f"/agents/{agent_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_set_orchestrator(client: AsyncClient):
    r1 = await client.post("/agents", json={"name": "A1", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    r2 = await client.post("/agents", json={"name": "A2", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    a1_id = r1.json()["id"]
    a2_id = r2.json()["id"]
    assert r1.json()["is_orchestrator"] is True

    resp = await client.patch(f"/agents/{a2_id}/orchestrator")
    assert resp.status_code == 200
    assert resp.json()["is_orchestrator"] is True

    r1_again = await client.get(f"/agents/{a1_id}")
    assert r1_again.json()["is_orchestrator"] is True


@pytest.mark.asyncio
async def test_multiple_orchestrators_allowed(client: AsyncClient):
    r1 = await client.post("/agents", json={"name": "Orch1", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    r2 = await client.post("/agents", json={"name": "Orch2", "model": "gpt-4o", "api_key": "k2", "agent_type": "orchestrator"})

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["agent_type"] == "orchestrator"
    assert r2.json()["agent_type"] == "orchestrator"


@pytest.mark.asyncio
async def test_create_agent_requires_non_empty_model_and_api_key(client: AsyncClient):
    resp = await client.post("/agents", json={"name": "Broken", "model": "   ", "api_key": "   ", "agent_type": "slave"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_key_encrypted(client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.agent import Agent

    plain_key = "sk-plaintext-secret"
    await client.post("/agents", json={"name": "SecAgent", "model": "gpt-4o", "api_key": plain_key, "agent_type": "orchestrator"})

    result = await db_session.execute(select(Agent).where(Agent.name == "SecAgent"))
    agent = result.scalar_one()
    assert agent.api_key_encrypted != plain_key
    assert plain_key not in agent.api_key_encrypted


@pytest.mark.asyncio
async def test_create_mediator_agent(client: AsyncClient):
    resp = await client.post("/agents", json={
        "name": "Mediator",
        "model": "gpt-4o",
        "api_key": "sk-test",
        "agent_type": "orchestrator",
        "orchestrator_mode": "mediator",
    })
    assert resp.status_code == 201
    assert resp.json()["orchestrator_mode"] == "mediator"
