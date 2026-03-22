# Multi-Agent Investigation RAG - Requirements

## Functional Requirements

### Agent Management
- Create/update/delete agents with model, purpose, instructions, and type.
- First agent for a user is forced to orchestrator.
- Orchestrators support modes: broadcast, orchestrate, mediator.
- Orchestrators select allowed slave agents.
- Routing rules are not part of configuration.
- Agents may use own API key or provider default key.

### Model Catalog and Keys
- Model catalog entries are provider, label, model, enabled.
- Model enable/disable is controlled directly in catalog rows.
- Agent model must be enabled in catalog.
- Default API keys are stored per provider.

### Conversations and Chat
- Conversations bind to a selected orchestrator and selected slave agents.
- Chat is streamed via SSE.
- Broadcast supports separate broadcast and orchestrator instructions.
- Mediator mode requires exactly two slave agents.

### Credits
- Base credits deducted per iteration.
- Additional credits_per_process deducted for successful calls using provider default keys.
- Credits visible in UI for all users.

### Auth and Access
- Production: Cloudflare Access JWT.
- Development fallback email mode when configured.
- Admin user management and impersonation support.

## Non-Functional Requirements
- API key encryption at rest.
- Persistent SQLite and Chroma data.
- Responsive web UI.
- Docker-based deployment.

## Constraints
- LiteLLM provider compatibility based on normalized provider/model naming.
- Security-sensitive actions are enforced server-side, not only in UI.
