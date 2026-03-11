# Multi-Agent Investigation RAG — Requirements

## 1. Overview
A dynamic, AI-native Retrieval-Augmented Generation (RAG) platform where users configure multiple LLM agents, designate one as the main orchestrator, and interact via a ChatGPT-like UI. Each agent maintains its own vector database (MCP architecture), enabling persistent memory of past interactions.

## 2. Functional Requirements

### 2.1 Agent Management
- **FR-01**: The user shall be able to create an agent by providing: a unique name, a model identifier (e.g. `gpt-4o`, `claude-3-5-sonnet`), and an API key.
- **FR-02**: The user shall be able to list all configured agents.
- **FR-03**: The user shall be able to update an agent's name, model, or API key.
- **FR-04**: The user shall be able to delete an agent (with at least one remaining).
- **FR-05**: One agent shall always be designated as the main orchestrator.
- **FR-06**: The user shall be able to change the orchestrator designation to any other existing agent at any time.
- **FR-07**: When a new agent is created, it shall be immediately available for the orchestrator to interact with.

### 2.2 Conversation Management
- **FR-08**: Each conversation shall have a title, creation timestamp, and list of messages.
- **FR-09**: The user shall be able to start a new conversation.
- **FR-10**: The user shall be able to resume any past conversation.
- **FR-11**: All conversations shall be listed in the left sidebar (most recent first).
- **FR-12**: When starting a new conversation the user shall be able to select which slave agents participate.

### 2.3 Chat Interaction
- **FR-13**: The user shall be presented with a chat interface similar to ChatGPT.
- **FR-14**: When composing a message the user shall declare whether the instruction is directed at:
  - **Orchestrator mode**: the main orchestrator resolves the request (may internally query slave agents).
  - **Slave mode**: the orchestrator broadcasts the instruction to all selected slave agents, collects individual responses, and replies to the user with each agent's individual response. The orchestrator stores the aggregated result in its own vector database.
- **FR-15**: In Slave mode the orchestrator shall collect and display each slave agent's response individually.
- **FR-16**: In Orchestrator mode the orchestrator shall independently handle the request, optionally delegating sub-tasks to slave agents.
- **FR-17**: Each agent's response shall be stored in that agent's own vector database.
- **FR-18**: Past interactions stored in the vector database shall be retrieved and provided as context to agents (RAG).

### 2.4 Vector Database (MCP)
- **FR-19**: Each agent shall have its own isolated vector database collection.
- **FR-20**: Each agent shall follow MCP (Model Context Protocol) architecture, exposing tools: `search_memory`, `add_memory`, `generate_response`.
- **FR-21**: Before generating a response, an agent shall retrieve relevant past interactions from its vector store and include them in its context.

### 2.5 Deployment
- **FR-22**: The solution shall be deployable on a remote Linux server via Docker Compose.
- **FR-23**: Deployment shall be achievable by copying files to the server and running `docker compose up -d`.

## 3. Non-Functional Requirements
- **NFR-01**: The backend API shall respond within 30 seconds for LLM interactions.
- **NFR-02**: All sensitive data (API keys) shall be stored encrypted at rest.
- **NFR-03**: The UI shall be responsive and work on modern browsers.
- **NFR-04**: The system shall support at least 10 simultaneous conversations.
- **NFR-05**: Vector databases shall persist across container restarts.

## 4. Constraints
- Agents can use any OpenAI-compatible API endpoint.
- Models supported: any model accessible via the provider's API (e.g. OpenAI, Anthropic via LiteLLM).
- The system does not manage SSH deployment itself; deployment is manual.
