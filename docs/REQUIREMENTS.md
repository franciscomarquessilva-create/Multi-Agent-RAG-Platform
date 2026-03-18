# Multi-Agent Investigation RAG — Requirements

## 1. Overview
A dynamic, AI-native Retrieval-Augmented Generation (RAG) platform where users configure multiple LLM agents, designate one as the orchestrator, and interact via a ChatGPT-like UI. Each agent maintains its own vector database (MCP architecture), enabling persistent memory of past interactions.

## 2. Functional Requirements

### 2.1 Agent Management
- **FR-01**: The user shall be able to create an agent by providing: a unique name, a model identifier (e.g. `gpt-4o`, `claude-3-5-sonnet`), an API key, an agent type (orchestrator or slave), and optional purpose / instructions text.
- **FR-02**: The user shall be able to list all agents they own.
- **FR-03**: The user shall be able to update an agent's name, model, API key, purpose, instructions, and (for orchestrators) mode and slave configuration.
- **FR-04**: The user shall be able to delete an agent (at least one agent must always remain).
- **FR-05**: An agent designated as orchestrator shall have one of three orchestration modes: **broadcast**, **orchestrate**, or **mediator**.
- **FR-06**: The user shall be able to change the orchestrator designation to any other existing agent at any time.
- **FR-07**: When a new agent is created it shall be immediately available for use in conversations.
- **FR-08**: The first agent created by a user shall automatically be assigned the orchestrator type.
- **FR-09**: Agent API keys shall be stored encrypted at rest using a server-side Fernet key.

### 2.2 Conversation Management
- **FR-10**: Each conversation shall have a title, creation timestamp, and list of messages.
- **FR-11**: The user shall be able to start a new conversation by selecting an orchestrator and optionally choosing which slave agents participate.
- **FR-12**: The user shall be able to resume any past conversation.
- **FR-13**: All conversations shall be listed in the left sidebar (most recent first).
- **FR-14**: The user shall be able to rename (retitle) a conversation.
- **FR-15**: The user shall be able to delete a conversation.
- **FR-16**: A mediator conversation shall require exactly two slave agents.

### 2.3 Chat Interaction
- **FR-17**: The user shall be presented with a chat interface similar to ChatGPT.
- **FR-18**: The user shall be able to send a message in one of three modes:
  - **Broadcast**: The orchestrator sends the broadcast instruction to all selected slave agents simultaneously, collects their individual responses, and displays each one.
  - **Orchestrate**: The orchestrator discovers agent specialities, plans a sequential execution, and synthesises the outputs.
  - **Mediator**: The orchestrator runs a structured debate between exactly two slave agents and produces a balanced assessment.
- **FR-19**: Responses shall be streamed to the UI in real time via Server-Sent Events.
- **FR-20**: In Broadcast mode the user may provide separate orchestrator instructions alongside the broadcast text.
- **FR-21**: Each agent's response shall be stored in that agent's own vector database.
- **FR-22**: Past interactions stored in the vector database shall be retrieved and provided as context to agents (RAG).

### 2.4 Vector Database (MCP)
- **FR-23**: Each agent shall have its own isolated vector database collection.
- **FR-24**: Each agent shall follow MCP (Model Context Protocol) architecture, exposing tools: `search_memory`, `add_memory`, `generate_response`.
- **FR-25**: Before generating a response, an agent shall retrieve relevant past interactions from its vector store and include them in its context.

### 2.5 User Management & Access Control
- **FR-26**: Users shall be authenticated via Cloudflare Access JWT in production, or via a configurable email fallback in development.
- **FR-27**: New users shall start as inactive until an admin approves them (unless their email is in `ADMIN_EMAILS`).
- **FR-28**: Users shall be assigned a credit balance; each chat iteration deducts credits.
- **FR-29**: Users shall be subject to a per-user agent limit; admins can adjust this per user.
- **FR-30**: Admins shall be able to list users, activate/block accounts, adjust credits and agent limits.
- **FR-31**: Admins shall be able to impersonate any user to diagnose issues.
- **FR-32**: Agents and conversations shall be scoped to their owner; admins see all.

### 2.6 Settings & Configuration
- **FR-33**: An admin shall be able to manage the list of allowed LLM models (add, edit, delete).
- **FR-34**: System prompt templates (purposes and instructions for each orchestrator mode) shall be configurable via the Settings UI without code changes.

### 2.7 Audit & Observability
- **FR-35**: Every LLM API call shall be logged with agent name, model, request payload, response payload, and any error.
- **FR-36**: The Audit UI shall display the LLM log with the most recent calls first.

### 2.8 Deployment
- **FR-37**: The solution shall be deployable on a remote Linux server via Docker Compose.
- **FR-38**: Deployment shall be achievable by copying files to the server and running `docker compose up -d`.

## 3. Non-Functional Requirements
- **NFR-01**: The backend API shall respond within 30 seconds for LLM interactions.
- **NFR-02**: All sensitive data (API keys) shall be stored encrypted at rest.
- **NFR-03**: The UI shall be responsive and work on modern browsers.
- **NFR-04**: The system shall support at least 10 simultaneous conversations.
- **NFR-05**: Vector databases and SQLite data shall persist across container restarts.
- **NFR-06**: No secrets, usernames, passwords, or server-specific configuration shall be hard-coded in source files.

## 4. Constraints
- Agents can use any OpenAI-compatible or Anthropic API endpoint (via LiteLLM).
- The system does not manage SSH deployment itself; deployment is performed manually or via the included `dp_remote.bat` helper.
