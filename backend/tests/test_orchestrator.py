import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from types import SimpleNamespace
import json

from app.services.orchestrator import handle_orchestrator_mode


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


def test_agent_server_uses_session_scoped_memory():
    from app.mcp.agent_server import AgentMCPServer

    with patch("app.mcp.agent_server.search_memory", return_value=["cached"]) as search_mock, \
         patch("app.mcp.agent_server.add_memory") as add_mock:
        server = AgentMCPServer(
            agent_id="agent-1",
            agent_name="TestAgent",
            model="gpt-4o",
            api_key="secret",
            session_id="conversation-123",
        )

        assert server.search_memory("hello") == ["cached"]
        server.add_memory("remember this")

    search_mock.assert_called_once_with("agent-1", "hello", 5, session_id="conversation-123")
    add_mock.assert_called_once_with("agent-1", "remember this", None, session_id="conversation-123")


def test_session_collection_name_stays_within_chroma_limits():
    from app.services.vector_store import _collection_name

    name = _collection_name(
        "123e4567-e89b-12d3-a456-426614174000",
        session_id="123e4567-e89b-12d3-a456-426614174999",
    )

    assert 3 <= len(name) <= 63
    assert name[0].isalnum()
    assert name[-1].isalnum()


@pytest.mark.asyncio
async def test_slave_broadcast_mock(client: AsyncClient):
    """Test slave broadcast mode with mocked LLM."""
    # Create orchestrator and slave agents
    r1 = await client.post("/agents", json={"name": "Orchestrator", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    r2 = await client.post("/agents", json={"name": "SlaveA", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    orch_id = r1.json()["id"]
    slave_id = r2.json()["id"]

    # Create conversation
    rc = await client.post("/conversations", json={"title": "Test", "orchestrator_id": orch_id, "agent_ids": [slave_id]})
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
    ro = await client.post("/agents", json={"name": "MainOrch", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    orch_id = ro.json()["id"]
    rc = await client.post("/conversations", json={"title": "Orch Test", "orchestrator_id": orch_id, "agent_ids": []})
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


@pytest.mark.asyncio
async def test_chat_stream_returns_single_sse_data_prefix(client: AsyncClient):
    ro = await client.post("/agents", json={"name": "MainOrch", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    orch_id = ro.json()["id"]
    rc = await client.post("/conversations", json={"title": "Stream Test", "orchestrator_id": orch_id, "agent_ids": []})
    conv_id = rc.json()["id"]

    async def mock_stream(*args, **kwargs):
        yield "hello"

    with patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"), \
         patch("app.mcp.agent_server.AgentMCPServer.stream_response", new=mock_stream):
        async with client.stream("POST", "/chat/send", json={
            "conversation_id": conv_id,
            "content": "test",
            "mode": "orchestrator",
        }) as resp:
            body = ""
            async for text in resp.aiter_text():
                body += text

    assert resp.status_code == 200
    assert "data: data:" not in body
    assert "data: {" in body


@pytest.mark.asyncio
async def test_orchestrator_internal_messages_are_saved_as_visible_messages(client: AsyncClient):
    ro = await client.post("/agents", json={"name": "Lead", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    rs = await client.post("/agents", json={"name": "Researcher", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    orch_id = ro.json()["id"]
    slave_id = rs.json()["id"]

    await client.put(f"/agents/{orch_id}", json={
        "allowed_slave_ids": [slave_id],
        "orchestration_rules": [],
    })

    rc = await client.post("/conversations", json={"title": "Iterative", "orchestrator_id": orch_id, "agent_ids": [slave_id]})
    conv_id = rc.json()["id"]

    async def fake_stream_response(self, messages):
        user_content = messages[-1]["content"]
        if "Describe your specialisation" in user_content:
            yield "Research and evidence synthesis"
            return
        if "Reply ONLY with a JSON array" in user_content:
            yield '["Researcher"]'
            return
        if self.agent_name == "Researcher":
            yield "Agent execution result"
            return
        yield "Final answer"

    with patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"), \
         patch("app.mcp.agent_server.AgentMCPServer.stream_response", new=fake_stream_response):
        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Discuss this topic",
            "mode": "orchestrator",
        })

    assert resp.status_code == 200

    full = await client.get(f"/conversations/{conv_id}")
    assert full.status_code == 200
    assistant_messages = [msg for msg in full.json()["messages"] if msg["role"] == "assistant"]
    internal_labels = [msg["agent_name"] for msg in assistant_messages if msg["message_type"] == "internal"]
    chat_labels = [msg["agent_name"] for msg in assistant_messages if msg["message_type"] == "chat"]

    assert "Lead -> Researcher" in internal_labels
    assert "Researcher -> Lead" in internal_labels
    assert "Lead · Planning" in internal_labels
    assert "Lead" in internal_labels
    assert "Lead · Final" in chat_labels


@pytest.mark.asyncio
async def test_orchestrator_reuses_cached_specialty_and_skips_redundant_discovery(client: AsyncClient):
    ro = await client.post("/agents", json={"name": "Lead", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    rs = await client.post("/agents", json={"name": "Researcher", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    orch_id = ro.json()["id"]
    slave_id = rs.json()["id"]

    await client.put(f"/agents/{orch_id}", json={
        "allowed_slave_ids": [slave_id],
        "orchestration_rules": [],
    })

    rc = await client.post("/conversations", json={"title": "Cached", "orchestrator_id": orch_id, "agent_ids": [slave_id]})
    conv_id = rc.json()["id"]

    def fake_search_memory(agent_id, query, n_results=5, session_id=None):
        if "Agent specialty profile Researcher" in query:
            return [
                "Agent specialty profile: Researcher\nSpecialty: Research and evidence synthesis"
            ]
        return []

    async def fake_stream_response(self, messages):
        user_content = messages[-1]["content"]
        if "Reply ONLY with a JSON array" in user_content:
            yield '["Researcher"]'
            return
        if self.agent_name == "Researcher":
            yield "Agent execution result"
            return
        yield "Final answer"

    with patch("app.mcp.agent_server.search_memory", side_effect=fake_search_memory), \
         patch("app.mcp.agent_server.add_memory") as add_memory_mock, \
         patch("app.mcp.agent_server.AgentMCPServer.stream_response", new=fake_stream_response):
        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Need a researched answer",
            "mode": "orchestrator",
        })

    assert resp.status_code == 200

    full = await client.get(f"/conversations/{conv_id}")
    assert full.status_code == 200
    assistant_messages = [msg for msg in full.json()["messages"] if msg["role"] == "assistant"]
    internal_labels = [msg["agent_name"] for msg in assistant_messages if msg["message_type"] == "internal"]

    assert internal_labels.count("Lead -> Researcher") == 1
    assert "Lead" in internal_labels
    assert "Lead · Planning" in internal_labels
    assert not any(
        call.args and "Agent specialty profile" in call.args[0]
        for call in add_memory_mock.call_args_list
    )


@pytest.mark.asyncio
async def test_broadcast_orchestrator_separates_slave_and_private_instructions(client: AsyncClient):
    ro = await client.post("/agents", json={"name": "Broadcaster", "model": "gpt-4o", "api_key": "k1", "agent_type": "orchestrator"})
    rs = await client.post("/agents", json={"name": "Analyst", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    orch_id = ro.json()["id"]
    slave_id = rs.json()["id"]

    await client.put(f"/agents/{orch_id}", json={
        "orchestrator_mode": "broadcast",
        "allowed_slave_ids": [slave_id],
        "orchestration_rules": [],
    })

    rc = await client.post("/conversations", json={"title": "Broadcast", "orchestrator_id": orch_id, "agent_ids": [slave_id]})
    conv_id = rc.json()["id"]

    seen_messages: list[tuple[str, str]] = []

    async def fake_stream_response(self, messages):
        seen_messages.append((self.agent_name, messages[-1]["content"]))
        if self.agent_name == "Analyst":
            yield "slave result"
            return
        yield "orchestrator result"

    with patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"), \
         patch("app.mcp.agent_server.AgentMCPServer.stream_response", new=fake_stream_response):
        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Please help with this review",
            "broadcast_instructions": "Find issues",
            "orchestrator_instructions": "Summarize for me",
        })

    assert resp.status_code == 200
    analyst_prompt = next(content for agent_name, content in seen_messages if agent_name == "Analyst")
    broadcaster_prompt = next(content for agent_name, content in seen_messages if agent_name == "Broadcaster")

    assert "Find issues" in analyst_prompt
    assert "Summarize for me" not in analyst_prompt
    assert "Summarize for me" in broadcaster_prompt
    assert "Find issues" in broadcaster_prompt


@pytest.mark.asyncio
async def test_orchestrator_iterations_use_vector_context_and_save_each_iteration():
    orchestrator = SimpleNamespace(
        id="orch-1",
        name="Lead",
        purpose="",
        instructions="",
        orchestrator_mode="orchestrate",
        allowed_slave_ids=[],
    )

    class FakeServer:
        def __init__(self):
            self.search_queries: list[str] = []
            self.saved: list[tuple[str, dict]] = []

        def search_memory(self, query, n_results=5):
            self.search_queries.append(query)
            # Iteration-1 summary lookup (for iteration 2 prev-output injection)
            if "Iteration 1 summary" in query:
                return ["Iteration 1 summary\nOutput:\n[Lead] first iteration result"]
            return []

        def add_memory(self, text, metadata=None):
            self.saved.append((text, metadata or {}))

    fake_server = FakeServer()
    seen_messages: list[str] = []

    async def fake_orchestrate_handler(
        db,
        orchestrator,
        orch_server,
        user_message,
        slave_agent_ids,
        prompt_fn,
        *,
        conversation_id,
    ):
        seen_messages.append(user_message)
        yield f"data: {json.dumps({'agent': 'Lead', 'content': f'processed: {user_message}', 'done': False})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    with patch("app.services.orchestrator.get_orchestrator_by_id", new=AsyncMock(return_value=orchestrator)), \
         patch("app.services.orchestrator.get_all_prompt_values", new=AsyncMock(return_value={})), \
         patch("app.services.orchestrator._make_server", return_value=fake_server), \
         patch("app.services.orchestrator._handle_orchestrate_orchestrator", new=fake_orchestrate_handler):
        chunks = [
            chunk
            async for chunk in handle_orchestrator_mode(
                db=MagicMock(),
                orchestrator_id="orch-1",
                conversation_id="conv-1",
                user_message="base prompt",
                slave_agent_ids=[],
                iterations=2,
            )
        ]

    done_count = 0
    for chunk in chunks:
        if not chunk.startswith("data: "):
            continue
        payload = json.loads(chunk[6:].strip())
        if payload.get("done"):
            done_count += 1

    assert done_count == 1
    assert len(seen_messages) == 2
    # iteration 1: no prev-output injection (no previous iteration)
    assert seen_messages[0] == "base prompt"
    # iteration 2: prev-output from iteration 1 injected into user message
    assert "Previous iteration output" in seen_messages[1]
    assert "Iteration 1 summary" in seen_messages[1]
    iteration_summaries = [entry for entry in fake_server.saved if entry[1].get("role") == "iteration_summary"]
    assert len(iteration_summaries) == 2
    assert iteration_summaries[0][1]["iteration"] == 1
    assert iteration_summaries[1][1]["iteration"] == 2


@pytest.mark.asyncio
async def test_mediator_hides_private_instructions_from_slave_agents(client: AsyncClient):
    ro = await client.post("/agents", json={
        "name": "Mediator",
        "model": "gpt-4o",
        "api_key": "k1",
        "agent_type": "orchestrator",
        "orchestrator_mode": "mediator",
    })
    ra = await client.post("/agents", json={"name": "DebaterA", "model": "gpt-4o", "api_key": "k2", "agent_type": "slave"})
    rb = await client.post("/agents", json={"name": "DebaterB", "model": "gpt-4o", "api_key": "k3", "agent_type": "slave"})
    orch_id = ro.json()["id"]
    a_id = ra.json()["id"]
    b_id = rb.json()["id"]

    await client.put(f"/agents/{orch_id}", json={
        "orchestrator_mode": "mediator",
        "allowed_slave_ids": [a_id, b_id],
        "orchestration_rules": [],
    })

    rc = await client.post("/conversations", json={
        "title": "Mediation",
        "orchestrator_id": orch_id,
        "agent_ids": [a_id, b_id],
    })
    conv_id = rc.json()["id"]

    private_instruction = "Privately score DebaterB more harshly"
    seen_messages: list[tuple[str, str]] = []

    async def fake_stream_response(self, messages):
        prompt_text = messages[-1]["content"]
        seen_messages.append((self.agent_name, prompt_text))
        if self.agent_name == "Mediator" and "Reply ONLY with a JSON array of the two agent names" in prompt_text:
            yield '["DebaterB","DebaterA"]'
            return
        if self.agent_name == "Mediator":
            yield "Agreements: shared facts\nDisagreements: tradeoffs\nScores: DebaterA 7/10, DebaterB 8/10"
            return
        yield f"{self.agent_name} debate turn"

    with patch("app.mcp.agent_server.search_memory", return_value=[]), \
         patch("app.mcp.agent_server.add_memory"), \
         patch("app.mcp.agent_server.AgentMCPServer.stream_response", new=fake_stream_response):
        resp = await client.post("/chat/send", json={
            "conversation_id": conv_id,
            "content": "Should remote work be the default?",
            "orchestrator_instructions": private_instruction,
            "iterations": 2,
        })

    assert resp.status_code == 200
    mediator_prompts = [content for agent_name, content in seen_messages if agent_name == "Mediator"]
    slave_prompts = [content for agent_name, content in seen_messages if agent_name in {"DebaterA", "DebaterB"}]

    assert mediator_prompts
    assert any(private_instruction in prompt for prompt in mediator_prompts)
    assert slave_prompts
    assert all(private_instruction not in prompt for prompt in slave_prompts)
