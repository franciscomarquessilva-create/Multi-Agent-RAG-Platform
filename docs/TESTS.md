# Multi-Agent Investigation RAG — Test Specifications

## 1. Backend Tests (pytest + pytest-asyncio)

All tests use an in-memory SQLite database and an ASGI test client (`httpx.AsyncClient`).
Authentication is bypassed in tests via the `DEV_USER_EMAIL` environment variable set in `conftest.py`.

### 1.1 Agent Management (`tests/test_agents.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_create_agent` | POST /agents with valid payload | 201, first agent auto-promoted to orchestrator |
| `test_create_agent_duplicate_name` | POST /agents with existing name | 409 Conflict |
| `test_list_agents` | GET /agents | 200, list of agents |
| `test_update_agent` | PUT /agents/{id} | 200, updated agent |
| `test_delete_agent` | DELETE /agents/{id} when > 1 agents exist | 204 |
| `test_delete_last_agent` | DELETE the only agent | 400 Bad Request |
| `test_api_key_encrypted` | Create agent; check DB value ≠ plain key | API key not stored in plain text |

### 1.2 Conversation Management (`tests/test_conversations.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_create_conversation` | POST /conversations with orchestrator and slave | 201, conversation with correct IDs |
| `test_list_conversations` | GET /conversations | 200, list |
| `test_get_conversation` | GET /conversations/{id} | 200, includes messages array |
| `test_delete_conversation` | DELETE /conversations/{id} | 204, then GET returns 404 |
| `test_mediator_conversation_requires_exactly_two_slaves` | POST /conversations with mediator orchestrator and one slave | 400 |

### 1.3 Orchestrator / Vector Store (`tests/test_orchestrator.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_vector_store_add_search` | `add_memory` × 2 then `search_memory` | Correct documents retrieved; ChromaDB mocked |
| `test_agent_server_uses_session_scoped_memory` | `AgentMCPServer` calls `search_memory`/`add_memory` with `session_id` | `session_id` forwarded to store layer |
| `test_session_collection_name_stays_within_chroma_limits` | `_collection_name` with session_id | Name length ≤ 63 characters |
| `test_broadcast_stream_*` | POST /chat/send (mode=slave) with mocked LLM | SSE chunks returned per agent |
| `test_orchestrate_stream_*` | POST /chat/send (mode=orchestrator) with mocked LLM | SSE stream with orchestrator response |

### 1.4 Settings (`tests/test_settings.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_get_settings_returns_provider_catalog` | GET /settings | 200, includes OpenAI/Anthropic/Gemini/Grok providers |
| `test_update_settings_rejects_unknown_model` | PUT /settings with unlisted model | 400 |
| `test_create_agent_respects_allowed_models` | Create agent with non-allowed model | 400 |

### 1.5 LLM Service (`tests/test_llm_service.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_normalize_model_name_for_common_providers` | Various raw model strings | Correct `provider/model` format |
| `test_resolve_anthropic_aliases_to_latest` | Anthropic alias resolution | Correct model name |
| `test_build_completion_kwargs_sets_anthropic_max_tokens` | Anthropic kwargs builder | `max_tokens` present |
| `test_complete_openai_success` | `complete()` with mocked litellm | Returns response text |
| `test_complete_raises_on_error` | `complete()` with litellm raising | HTTPException 502 |

## 2. Frontend Tests (Vitest + React Testing Library)

### 2.1 Agent Manager (`src/components/AgentManager/AgentManager.test.tsx`)

| Test ID | Description |
|---------|-------------|
| `renders_agent_list` | AgentManager renders list of agents |
| `create_agent_form_submit` | Submitting form calls POST /agents |
| `set_orchestrator_button` | Clicking "Set Orchestrator" calls PATCH endpoint |

### 2.2 Chat Interface (`src/components/Chat/Chat.test.tsx`)

| Test ID | Description |
|---------|-------------|
| `renders_empty_chat` | Empty conversation shows placeholder |
| `mode_toggle_switches` | Clicking toggle changes mode label |
| `message_appears_after_send` | User message appears immediately in chat |

### 2.3 Sidebar (`src/components/Sidebar/Sidebar.test.tsx`)

| Test ID | Description |
|---------|-------------|
| `renders_conversations` | Sidebar renders conversation list |
| `click_conversation_selects` | Clicking conversation fires onSelect |
| `new_chat_button_fires_callback` | New Chat button fires onCreate |

## 3. Integration Tests

### 3.1 End-to-End Flow (manual / Playwright optional)
1. Create two agents (Agent A, Agent B); Agent A is auto-promoted to orchestrator type (the default mode is `orchestrate`; you may change it to `broadcast` or `mediator` in Agent Manager).
2. Start a new conversation, select Agent B as slave.
3. Send a message in **Broadcast** mode → verify Agent B response appears alongside the orchestrator's aggregated response.
4. Send a message in **Orchestrate** mode → verify single synthesised response appears.
5. Close browser; reopen and resume conversation → messages persist.
6. Delete Agent B → Agent A remains as orchestrator.

## 4. Running Tests

### Backend
```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm test
```
