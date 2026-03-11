import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vector_store_add_search():
    """Test that add_memory and search_memory call chromadb correctly."""
    import uuid
    from app.services.vector_store import add_memory, search_memory

    agent_id = str(uuid.uuid4())
    mock_collection = MagicMock()
    mock_collection.count.return_value = 2
    mock_collection.query.return_value = {
        "documents": [["The sky is blue and beautiful today"]],
    }

    with patch("app.services.vector_store.get_or_create_collection", return_value=mock_collection):
        add_memory(agent_id, "The sky is blue and beautiful today", {"source": "test"})
        add_memory(agent_id, "Machine learning is a field of AI", {"source": "test"})

        results = search_memory(agent_id, "what color is the sky", n_results=1)
        assert len(results) == 1
        assert "sky" in results[0].lower() or "blue" in results[0].lower()
        assert mock_collection.upsert.call_count == 2
        mock_collection.query.assert_called_once()


@pytest.mark.asyncio
async def test_slave_broadcast_mock(client: AsyncClient):
    """Test slave broadcast mode with mocked LLM."""
    # Create orchestrator and slave agents
    r1 = await client.post("/agents", json={"name": "Orchestrator", "model": "gpt-4o", "api_key": "k1"})
    r2 = await client.post("/agents", json={"name": "SlaveA", "model": "gpt-4o", "api_key": "k2"})
    slave_id = r2.json()["id"]

    # Create conversation
    rc = await client.post("/conversations", json={"title": "Test", "agent_ids": [slave_id]})
    conv_id = rc.json()["id"]

    # Mock the LLM and vector store (patch at agent_server level since it imports directly)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Mock slave response"

    with patch("app.services.llm_service.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response), \
         patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"):

        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Analyze this topic",
            "mode": "slave",
            "agent_ids": [slave_id],
        })
        # SSE response
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_orchestrator_mode_mock(client: AsyncClient):
    """Test orchestrator mode with mocked LLM."""
    await client.post("/agents", json={"name": "MainOrch", "model": "gpt-4o", "api_key": "k1"})
    rc = await client.post("/conversations", json={"title": "Orch Test", "agent_ids": []})
    conv_id = rc.json()["id"]

    async def mock_stream(*args, **kwargs):
        class FakeDelta:
            content = "streamed "
        class FakeChoice:
            delta = FakeDelta()
        class FakeChunkObj:
            choices = [FakeChoice()]
        yield FakeChunkObj()

    with patch("app.services.llm_service.litellm.acompletion", return_value=mock_stream()), \
         patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"):

        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Hello orchestrator",
            "mode": "orchestrator",
        })
        assert resp.status_code == 200
