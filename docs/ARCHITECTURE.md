# Multi-Agent Investigation RAG — Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (React)                       │
│  ┌─────────────┐   ┌────────────────────────────────────┐   │
│  │  Left Pane  │   │           Chat Interface            │   │
│  │ Conversation│   │  ┌──────────────────────────────┐  │   │
│  │  History    │   │  │  Message + Mode Toggle       │  │   │
│  │             │   │  │  (Orchestrator / Slave)      │  │   │
│  └─────────────┘   │  └──────────────────────────────┘  │   │
│                    └────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │  REST API / WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │  Agents    │  │Conversations│  │   Chat / Orchestr. │   │
│  │  Router    │  │   Router    │  │      Router        │   │
│  └─────┬──────┘  └──────┬──────┘  └─────────┬──────────┘   │
│        │                │                    │               │
│  ┌─────▼────────────────▼────────────────────▼──────────┐   │
│  │                   Services Layer                      │   │
│  │  AgentService │ ConversationService │ Orchestrator   │   │
│  └─────────────────────────┬──────────────────────────┘   │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐   │
│  │           MCP Agent Layer (per agent)               │   │
│  │   ┌─────────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │   │search_memory│  │add_memory│  │  gen_response│  │   │
│  │   └──────┬──────┘  └────┬─────┘  └──────┬───────┘  │   │
│  │          └──────────────┼────────────────┘          │   │
│  │                    ┌────▼─────┐                      │   │
│  │                    │ChromaDB  │ (one collection/agent)│   │
│  │                    └──────────┘                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐   │
│  │                  SQLite (SQLAlchemy)                 │   │
│  │     agents │ conversations │ messages                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 2. Component Descriptions

### 2.1 Frontend (React + TypeScript + Vite)
- **Sidebar**: Lists all conversations; allows creating new ones.
- **ChatWindow**: Displays messages; includes a mode toggle (Orchestrator / Slave broadcast).
- **AgentManager**: CRUD UI for agents; designate orchestrator.
- **NewConversationModal**: Selects which slave agents to include.
- **API Service**: Axios-based HTTP client; EventSource for SSE streaming.

### 2.2 Backend (FastAPI)

| Router | Endpoints |
|--------|-----------|
| `/agents` | GET, POST, PUT, DELETE, PATCH /orchestrator |
| `/conversations` | GET, POST, GET /{id}, DELETE /{id} |
| `/chat` | POST /send (SSE stream) |

### 2.3 Services Layer
- **AgentService**: CRUD for agents, orchestrator management, API key encryption.
- **ConversationService**: CRUD for conversations and messages.
- **OrchestratorService**: Routes messages; in Slave mode fans out to each agent's MCP server; in Orchestrator mode the main agent resolves the request.
- **VectorStoreService**: Manages ChromaDB collections (one per agent); handles upsert and similarity search.
- **LLMService**: Calls external LLM APIs via LiteLLM; supports all OpenAI-compatible providers.

### 2.4 MCP Agent Layer
Each agent exposes three tools conforming to the Model Context Protocol pattern:
```
search_memory(query: str, n_results: int) → List[str]
add_memory(text: str, metadata: dict)     → None
generate_response(messages: List[dict])   → str (streaming)
```
The orchestrator calls these tools when coordinating slave agents.

### 2.5 Data Models

**Agent**
```
id          UUID  PK
name        str   unique
model       str
api_key     str   (encrypted)
is_orchestrator  bool
created_at  datetime
```

**Conversation**
```
id          UUID  PK
title       str
agent_ids   JSON  (list of participating agent IDs)
created_at  datetime
updated_at  datetime
```

**Message**
```
id          UUID  PK
conversation_id  UUID  FK
role        str   (user/assistant/system)
content     str
mode        str   (orchestrator/slave)
agent_id    UUID  FK nullable (which agent produced this)
created_at  datetime
```

### 2.6 Vector Store
- **Engine**: ChromaDB (embedded, persistent)
- **Collections**: one per agent, named `agent_{agent_id}`
- **Embedding**: `all-MiniLM-L6-v2` (sentence-transformers, local)
- **Documents**: stored as `{role}: {content}` pairs

### 2.7 Security
- Agent API keys are encrypted at rest using `cryptography.fernet` with a server-side secret key.
- The secret key is provided via the `SECRET_KEY` environment variable.

## 3. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Axios |
| Backend | Python 3.11, FastAPI, SQLAlchemy, Pydantic v2 |
| LLM Integration | LiteLLM |
| Vector DB | ChromaDB (embedded) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Relational DB | SQLite |
| Containerisation | Docker, Docker Compose |

## 4. Data Flow

### 4.1 Slave Broadcast Mode
```
User → POST /chat/send (mode=slave)
  → OrchestratorService.broadcast(message, slave_agent_ids)
    → For each slave agent:
        AgentMCP.search_memory(message)          # retrieve context
        AgentMCP.generate_response(ctx+message)  # call LLM
        AgentMCP.add_memory(message + response)  # persist
      → collect all responses
  → OrchestratorMCP.add_memory(aggregated)       # orchestrator stores summary
  → Stream SSE chunks to frontend
```

### 4.2 Orchestrator Mode
```
User → POST /chat/send (mode=orchestrator)
  → OrchestratorService.resolve(message)
    → OrchestratorMCP.search_memory(message)     # retrieve orchestrator context
    → (Optional) delegate sub-tasks to slave agents
    → OrchestratorMCP.generate_response(ctx)     # main LLM call
    → OrchestratorMCP.add_memory(exchange)       # persist
  → Stream SSE chunks to frontend
```
