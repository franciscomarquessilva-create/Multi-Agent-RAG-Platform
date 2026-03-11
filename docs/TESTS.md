# Multi-Agent Investigation RAG — Test Specifications

## 1. Backend Tests (pytest)

### 1.1 Agent Management (`tests/test_agents.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_create_agent` | POST /agents with valid payload | 201, agent returned with id |
| `test_create_agent_duplicate_name` | POST /agents with existing name | 409 Conflict |
| `test_list_agents` | GET /agents | 200, list of agents |
| `test_update_agent` | PUT /agents/{id} | 200, updated agent |
| `test_delete_agent` | DELETE /agents/{id} | 204 |
| `test_delete_last_agent` | DELETE the only agent | 400 Bad Request |
| `test_set_orchestrator` | PATCH /agents/{id}/orchestrator | 200, is_orchestrator=true on target; false on previous |
| `test_api_key_encrypted` | Create agent; check DB value ≠ plain key | API key not stored in plain text |

### 1.2 Conversation Management (`tests/test_conversations.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_create_conversation` | POST /conversations | 201, conversation returned |
| `test_list_conversations` | GET /conversations | 200, list |
| `test_get_conversation` | GET /conversations/{id} | 200, with messages |
| `test_delete_conversation` | DELETE /conversations/{id} | 204 |

### 1.3 Chat / Orchestrator (`tests/test_orchestrator.py`)

| Test ID | Description | Expected |
|---------|-------------|----------|
| `test_slave_broadcast_mock` | POST /chat/send (mode=slave) with mocked LLM | Returns individual responses per agent |
| `test_orchestrator_mode_mock` | POST /chat/send (mode=orchestrator) with mocked LLM | Returns single orchestrator response |
| `test_rag_context_included` | After storing memory, new query retrieves context | Context appears in prompt |
| `test_vector_store_add_search` | add_memory then search_memory | Correct documents retrieved |

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
1. Create two agents (Agent A, Agent B); set Agent A as orchestrator.
2. Start a new conversation, select Agent B as slave.
3. Send a message in **Slave mode** → verify both Agent A and Agent B responses appear.
4. Send a message in **Orchestrator mode** → verify single response appears.
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
