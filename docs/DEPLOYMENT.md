# Multi-Agent Investigation RAG - Deployment Guide

## 1. Prerequisites

- Docker Engine/Desktop with Compose v2
- SSH access for remote deployment
- Python available locally for Fernet key generation

## 2. Environment Variables

### Backend (.env)
- SECRET_KEY (required)
- DATABASE_URL
- CHROMA_PERSIST_DIR
- BACKEND_CORS_ORIGINS
- CF_TEAM_DOMAIN
- ADMIN_EMAILS
- DEV_USER_EMAIL
- DEFAULT_USER_CREDITS
- DEFAULT_AGENT_LIMIT
- CREDITS_PER_ITERATION

### Frontend (.env)
- VITE_API_BASE_URL

## 3. Local Start

1. Configure backend and frontend env files from examples.
2. Set SECRET_KEY to a valid Fernet key.
3. Run:

```bash
docker compose up --build
```

## 4. Remote Deployment

Use the repository helper:

```bat
dp_remote.bat
```

The script syncs files and rebuilds the stack. It is expected to preserve server env files after first setup.

## 5. Post-Deploy Smoke Checks

- Backend health/basic endpoint:

```bash
curl -s http://localhost:8000/settings
```

Validate response includes:
- available_models (with enabled flags)
- credits_per_process
- default_key_providers

## 6. Data Persistence

Docker volume persists SQLite and Chroma data across restarts.

## 7. Security Deployment Notes

- Never deploy with empty SECRET_KEY.
- For production, set CF_TEAM_DOMAIN to enforce Cloudflare JWT validation.
- Keep backend internal; expose only frontend/proxy edge.
- Restrict who can run impersonation operations (admin role only).
