# Multi-Agent Investigation RAG - Deployment Guide

## 1. Prerequisites

- Docker Engine/Desktop with Compose v2
- SSH access for remote deployment
- Python available locally for Fernet key generation

## 2. Environment Variables

### Backend (.env)
- `SECRET_KEY` (**required**) — Fernet encryption key. Generate with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `DATABASE_URL` — defaults to `sqlite+aiosqlite:///./data/app.db`
- `CHROMA_PERSIST_DIR` — defaults to `./data/chroma`
- `BACKEND_CORS_ORIGINS` — comma-separated allowed origins; restrict to your frontend URL in production
- `CF_TEAM_DOMAIN` — Cloudflare Access team name; enables JWT validation when set
- `ADMIN_EMAILS` — comma-separated list of emails granted the admin role
- `DEV_USER_EMAIL` — dev-mode fallback user (only active when `CF_TEAM_DOMAIN` is blank)
- `DEFAULT_USER_CREDITS` — credits given to new users
- `DEFAULT_AGENT_LIMIT` — max agents per user (`-1` = unlimited)
- `CREDITS_PER_ITERATION` — credits deducted per chat iteration

### Frontend (.env)
- `VITE_API_BASE_URL` — API base URL; use `/api` when proxied through nginx (default)

## 3. Local Start

1. Configure backend and frontend env files from examples.
2. Set `SECRET_KEY` to a valid Fernet key.
3. Run:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set SECRET_KEY
cp frontend/.env.example frontend/.env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

## 4. Remote Deployment

Use the repository helper script on Windows:

```bat
dp_remote.bat
```

Edit the configuration variables at the top of the script before first use:

| Variable | Description |
|----------|-------------|
| `SERVER` | SSH target (e.g. `user@hostname`) |
| `SERVER_HOST` | Hostname for display output |
| `APP_DIR` | Remote directory for the application |
| `FRONTEND_PORT` | Host port for the frontend container |

The script syncs files and rebuilds the stack. It preserves server `.env` files after first setup.

To override compose settings on the remote server (e.g. add Traefik labels), create a `docker-compose.override.yml` there using `docker-compose.override.example.yml` as a reference.

## 5. Production Checklist

Before exposing to the internet:

- [ ] Set `SECRET_KEY` to a freshly generated Fernet key (see above).
- [ ] Set `CF_TEAM_DOMAIN` to enforce Cloudflare Access JWT validation.
- [ ] Set `BACKEND_CORS_ORIGINS` to your actual frontend domain (no wildcards).
- [ ] Restrict `ADMIN_EMAILS` to the minimum required set.
- [ ] Keep the backend service on an internal Docker network; expose only the frontend or proxy.
- [ ] Enable HTTPS — use Traefik + Cloudflare Tunnel (see `docs/INFRA.md`) or a reverse proxy with a valid certificate.
- [ ] Configure data backups for the `backend_data` Docker volume (contains SQLite DB and ChromaDB).
- [ ] Review the security hardening checklist in `SECURITY.md`.

## 6. Post-Deploy Smoke Checks

```bash
# Backend health
curl -s http://localhost:8000/health

# Settings endpoint
curl -s http://localhost:8000/settings
```

Validate that the settings response includes:
- `available_models` (with enabled flags)
- `credits_per_process`
- `default_key_providers`

## 7. Data Persistence

The `backend_data` Docker volume persists both the SQLite database and ChromaDB across container restarts and upgrades. Back this volume up regularly in production.

## 8. Security Deployment Notes

- Never deploy with an empty `SECRET_KEY`.
- For production, set `CF_TEAM_DOMAIN` to enforce Cloudflare JWT validation.
- Keep the backend internal; expose only the frontend/proxy edge.
- Restrict who can run impersonation operations (admin role only).
- See `SECURITY.md` for the full security hardening checklist.

