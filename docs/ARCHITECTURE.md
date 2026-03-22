# Multi-Agent Investigation RAG - Architecture

## 1. High-Level Architecture

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy (async)
- Persistence: SQLite + ChromaDB
- LLM access: LiteLLM wrappers and direct Anthropic streaming path
- Transport: REST + SSE for streaming chat

## 2. Core Domains

### 2.1 Agent Domain
- Agent types: orchestrator, slave
- Orchestrator modes: broadcast, orchestrate, mediator
- Agent fields include model, purpose, instructions, allowed_slave_ids, use_default_key
- Routing rules were removed from configuration and API payloads

### 2.2 Model Catalog Domain
- Global catalog in app settings with entries:
  - provider
  - label
  - model
  - enabled
- Enabled/disabled is controlled directly per catalog row
- Agent creation/update requires selected model to be enabled

### 2.3 Key Management Domain
- Agent can use:
  - own key (stored encrypted per agent)
  - provider default key (stored encrypted in app settings)
- Provider default keys are keyed by provider (openai, anthropic, gemini, xai)
- Provider key resolution is derived from the agent model provider prefix

### 2.4 Credits Domain
- credits_per_iteration: charged at chat request level
- credits_per_process: charged per successful LLM call only when agent uses provider default key
- Credits are visible in sidebar for all users

## 3. API Surface (selected)

- /agents
  - POST, GET, PUT /{id}, DELETE /{id}, PATCH /{id}/orchestrator
- /conversations
  - POST, GET, GET /{id}, DELETE /{id}, PATCH /{id}/title
- /chat
  - POST /send (SSE)
- /settings
  - GET, PUT
  - GET/POST/PUT/DELETE /models
  - POST/DELETE /default-keys
  - GET /prompts, PUT /prompts/{key}
- /users
  - /me, list, patch
- /logs
  - /llm

## 4. Data Model Notes

### 4.1 app_settings
- available_models_json: model catalog with enabled flag
- credits_per_process: integer >= 0
- default_api_keys_json: encrypted provider key map

### 4.2 agents
- use_default_key: boolean
- allowed_slave_ids_json: orchestrator target constraints
- orchestration_rules_json exists for backward compatibility but is no longer used by API/UI

## 5. Chat UX Notes

- Removed from UI:
  - Instruction target: Orchestrator
  - To: Orchestrator: <name>
- Chat still shows orchestrator name in conversation header context

## 6. Security Highlights

- API keys encrypted at rest with Fernet derived from SECRET_KEY
- Provider default keys validated against known providers from model catalog
- Admin-only impersonation, enforced server-side
- Production auth via Cloudflare Access JWT (when CF_TEAM_DOMAIN is configured)
