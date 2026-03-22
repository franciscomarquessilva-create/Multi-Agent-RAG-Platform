# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added
- Three orchestration modes: Broadcast, Orchestrate, and Mediator
- Per-agent persistent memory using ChromaDB vector store (RAG)
- Real-time streaming responses via Server-Sent Events (SSE)
- Cloudflare Access JWT authentication for production; email-based dev fallback
- Per-user credit system with configurable costs per iteration and per LLM call
- Full LLM audit log capturing every request and response payload
- Configurable model catalog and system prompt templates via Settings UI
- Admin panel with user management and impersonation support
- Agent API key encryption at rest using Fernet (AES-128)
- Multi-provider LLM support via LiteLLM (OpenAI, Anthropic, Gemini, xAI)
- Docker Compose setup with persistent volumes and health checks
- Traefik + Cloudflare Tunnel integration (optional)
- Windows remote deployment helper script (`dp_remote.bat`)
