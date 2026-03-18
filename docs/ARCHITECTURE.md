# Multi-Agent Investigation RAG — Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser (React)                         │
│  ┌──────────────┐  ┌──────────────────────────────────────────┐ │
│  │   Sidebar    │  │              Main Area                   │ │
│  │Conversations │  │  Chat │ AgentManager │ Settings │ Audit  │ │
│  │   + Nav      │  │       │              │ AdminPanel        │ │
│  └──────────────┘  └──────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST + SSE (EventSource)
┌──────────────────────────▼──────────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌────────────┐ ┌──────────────┐ ┌────────┐ ┌───────────────┐  │
│  │  /agents   │ │/conversations│ │ /chat  │ │/logs /settings│  │
│  │  /users    │ │              │ │  SSE   │ │  /settings/   │  │
│  └─────┬──────┘ └──────┬───────┘ └───┬────┘ │  prompts      │  │
│        │               │             │      └───────────────┘  │
│  ┌─────▼───────────────▼─────────────▼──────────────────────┐  │
│  │                     Services Layer                        │  │
│  │  AgentService │ ConversationService │ OrchestratorService │  │
│  │  AuthService  │ UserService         │ SettingsService     │  │
│  │  LLMService   │ LLMLogService       │ VectorStoreService  │  │
│  └──────────────────────────┬──────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │               MCP Agent Layer (per agent)                │   │
│  │  ┌──────────────┐  ┌───────────┐  ┌──────────────────┐  │   │
│  │  │search_memory │  │add_memory │  │generate_response │  │   │
│  │  └──────┬───────┘  └─────┬─────┘  └────────┬─────────┘  │   │
│  │         └────────────────┼─────────────────┘            │   │
│  │                     ┌────▼──────┐                        │   │
│  │                     │ ChromaDB  │ (one collection/agent) │   │
│  │                     └───────────┘                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │                SQLite (SQLAlchemy async)                  │   │
│  │  agents │ users │ conversations │ messages               │   │
│  │  app_settings │ prompt_configs │ llm_logs               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Component Descriptions

### 2.1 Frontend (React + TypeScript + Vite)
- **Sidebar**: Lists all conversations; allows creating new ones; shows user info (email, role, credits).
- **Chat**: Displays messages with SSE streaming; includes a mode toggle (Orchestrator / Broadcast / Mediator).
- **AgentManager**: CRUD UI for agents; creates orchestrator and slave agents with configurable modes.
- **Settings**: Manage available LLM models (add / edit / delete) and configurable prompt templates.
- **Audit**: Displays LLM call logs (model, agent, request/response payloads, errors).
- **AdminPanel**: Admin-only view for managing users (activate, block, adjust credits/agent limits, impersonate).
- **NewConversationModal**: Selects which slave agents participate in a conversation.
- **API Service**: Axios-based HTTP client + `fetch`-based EventSource for SSE streaming.
- **AuthContext**: Reads current-user data from `/users/me`; handles admin impersonation.

### 2.2 Backend (FastAPI)

| Router | Endpoints |
|--------|-----------|
| `/agents` | GET, POST, PUT /{id}, DELETE /{id}, PATCH /{id}/orchestrator |
| `/conversations` | GET, POST, GET /{id}, DELETE /{id}, PATCH /{id}/title |
| `/chat` | POST /send (SSE stream) |
| `/users` | GET /me, GET, GET /{id}, PATCH /{id} |
| `/logs` | GET /llm |
| `/settings` | GET, PUT, GET /models, POST /models, PUT /models, DELETE /models, GET /prompts, PUT /prompts/{key} |

### 2.3 Services Layer
- **AgentService**: CRUD for agents; orchestrator management; API key encrypt/decrypt.
- **ConversationService**: CRUD for conversations and messages.
- **OrchestratorService**: Routes messages to the correct mode handler.
- **AuthService**: Validates Cloudflare Access JWT or falls back to dev-mode email.
- **UserService**: User CRUD; enforces credit deduction and per-user agent limits.
- **SettingsService**: Manages the list of allowed LLM models and configurable prompt templates.
- **LLMLogService**: Records every LLM API call for auditing and debugging.
- **VectorStoreService**: Manages ChromaDB collections (one per agent); handles upsert and similarity search.
- **LLMService**: Calls external LLM APIs via LiteLLM; supports OpenAI and Anthropic-compatible providers.

### 2.4 MCP Agent Layer
Each agent exposes three tools conforming to the Model Context Protocol pattern:
```
search_memory(query: str, n_results: int) → List[str]
add_memory(text: str, metadata: dict)     → None
generate_response(messages: List[dict])   → str (streaming)
```
The orchestrator calls these tools when coordinating slave agents.

### 2.5 Orchestrator Modes

| Mode | Behaviour |
|------|-----------|
| **broadcast** | Sends an explicit broadcast instruction simultaneously to all slave agents; aggregates their individual responses. |
| **orchestrate** | Discovers each slave's speciality, builds a sequential execution plan, and synthesises a final answer. |
| **mediator** | Runs a structured debate between exactly two slave agents; decides speaking order each round; produces a balanced assessment. |

### 2.6 Data Models

**Agent**
```
id                    UUID  PK
owner_id              UUID  FK → users (nullable)
name                  str   unique per owner
model                 str
api_key_encrypted     str   (Fernet-encrypted)
agent_type            str   (orchestrator | slave)
orchestrator_mode     str   (broadcast | orchestrate | mediator)
is_orchestrator       bool
purpose               text
instructions          text
allowed_slave_ids     JSON  (orchestrators only)
orchestration_rules   JSON  (orchestrators only)
created_at            datetime
```

**User**
```
id            UUID  PK
email         str   unique
role          str   (user | admin)
credits       int
agent_limit   int   (-1 = unlimited)
is_active     bool
is_blocked    bool
created_at    datetime
last_seen_at  datetime
```

**Conversation**
```
id               UUID  PK
owner_id         UUID  FK → users
orchestrator_id  UUID  FK → agents
title            str
agent_ids        JSON  (list of participating slave agent IDs)
created_at       datetime
updated_at       datetime
```

**Message**
```
id               UUID  PK
conversation_id  UUID  FK → conversations
role             str   (user | assistant | system)
content          str
mode             str   (orchestrator | slave | mediator | …)
agent_id         UUID  FK → agents (nullable)
created_at       datetime
```

**AppSettings**
```
id               UUID  PK
allowed_models   JSON  (list of ModelOption objects)
updated_at       datetime
```

**PromptConfig**
```
key          str  PK  (e.g. broadcast_default_purpose)
value        text
description  text
updated_at   datetime
```

**LLMLog**
```
id                UUID  PK
agent_id          UUID  FK → agents (nullable)
agent_name        str
model             str
request_payload   text  (JSON)
response_payload  text  (JSON, nullable)
error             text  (nullable)
created_at        datetime
```

### 2.7 Vector Store
- **Engine**: ChromaDB (embedded, persistent)
- **Collections**: one per agent, named `agent_{agent_id}`
- **Embedding**: `all-MiniLM-L6-v2` (sentence-transformers, local)
- **Documents**: stored as `{role}: {content}` pairs; scoped optionally by `session_id`

### 2.8 Authentication & Access Control
- **Production**: Cloudflare Access issues a signed JWT (`CF_Authorization` cookie / `Cf-Access-Jwt-Assertion` header). The backend validates the JWT when `CF_TEAM_DOMAIN` is set.
- **Development**: When `CF_TEAM_DOMAIN` is blank, the backend accepts an `X-Dev-User-Email` header or falls back to `DEV_USER_EMAIL`.
- **Roles**: `admin` (full access, unlimited credits) and `user` (limited by credits and agent count). New users are inactive until an admin approves them (unless they match `ADMIN_EMAILS`).
- **Impersonation**: Admins can impersonate any user via the `X-Impersonate-User-Id` header (enforced server-side).

### 2.9 Security
- Agent API keys are encrypted at rest using `cryptography.fernet` with a server-side `SECRET_KEY`.
- All sensitive configuration is supplied via environment variables; no secrets are stored in source code.

## 3. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Axios |
| Backend | Python 3.11, FastAPI, SQLAlchemy (async), Pydantic v2 |
| LLM Integration | LiteLLM |
| Vector DB | ChromaDB (embedded) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Relational DB | SQLite (async via `aiosqlite`) |
| Containerisation | Docker, Docker Compose |
| Auth (production) | Cloudflare Access JWT |

## 4. Data Flow

### 4.1 Broadcast Mode
```
User → POST /chat/send (mode=slave, broadcast_instructions=…)
  → OrchestratorService.broadcast(message, slave_agent_ids)
    → For each slave agent (parallel):
        AgentMCP.search_memory(message)           # retrieve context
        AgentMCP.generate_response(ctx+message)   # call LLM
        AgentMCP.add_memory(message + response)   # persist
      → collect all responses
  → OrchestratorMCP.add_memory(aggregated)        # orchestrator stores summary
  → Stream SSE chunks to frontend
```

### 4.2 Orchestrate Mode
```
User → POST /chat/send (mode=orchestrator)
  → OrchestratorService.orchestrate(message, orchestrator_instructions)
    → Discover slave specialities
    → Build sequential execution plan
    → For each relevant slave agent (in order):
        AgentMCP.search_memory(message)
        AgentMCP.generate_response(ctx+prev_output)
        AgentMCP.add_memory(exchange)
    → OrchestratorMCP.generate_response(all_outputs)  # synthesise
    → OrchestratorMCP.add_memory(exchange)
  → Stream SSE chunks to frontend
```

### 4.3 Mediator Mode
```
User → POST /chat/send (mode=mediator, orchestrator_instructions=…)
  → OrchestratorService.mediate(topic, two_slave_agents, mediator_instructions)
    → Multiple rounds:
        Decide speaking order based on current debate state
        SlaveA.generate_response(context) or SlaveB.generate_response(context)
        Accumulate exchange
    → OrchestratorMCP.generate_response(full_debate)  # final assessment
  → Stream SSE chunks to frontend
```
