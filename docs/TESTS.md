# Multi-Agent Investigation RAG - Test Specifications

## Backend

### Settings and Catalog
- GET /settings returns available_models with enabled flag.
- PUT /settings updates credits_per_process.
- Model add/update/delete flows validated.
- Disabled model cannot be used to create/update agents.
- Provider default key set/delete flows validated.

### Agents
- CRUD agent lifecycle and ownership constraints.
- API key encrypted at rest.
- First agent auto-orchestrator behavior.

### Conversations and Orchestration
- Conversation CRUD.
- Mediator requires two slaves.
- Broadcast/orchestrate/mediator SSE behaviors validated.

## Frontend

### AgentManager
- Renders list and supports create/update actions.
- Uses enabled model list from model catalog.

### Chat
- Empty and populated states render correctly.
- Internal messages render in details boxes.
- Instruction target and user target labels are removed.

### Sidebar
- Conversation list interactions.
- Credits display and impersonation-aware navigation behavior.

## How to Run

Backend:
- cd backend
- pytest tests -v

Frontend:
- cd frontend
- npm test
