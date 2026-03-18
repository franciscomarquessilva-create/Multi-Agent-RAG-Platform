# Multi-Agent Investigation RAG — Deployment Guide

## 1. Prerequisites

### Local machine
- Docker Desktop ≥ 24 **or** Docker Engine ≥ 24 + Docker Compose plugin v2
- Git
- OpenSSH client (`ssh`, `scp`) if deploying from Windows with `dp_remote.bat`

### Remote Linux server
- Ubuntu 22.04 / Debian 12 (recommended)
- Docker Engine ≥ 24
- Docker Compose plugin v2
- SSH access (key-based recommended)
- For Cloudflare Tunnel + Traefik deployments, no inbound app ports need to be opened on the server

## 2. Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Fernet key for encrypting agent API keys (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) | *required* |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./data/app.db` |
| `CHROMA_PERSIST_DIR` | ChromaDB persistence directory | `./data/chroma` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |

Copy `frontend/.env.example` to `frontend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Frontend API base URL (same-origin path) | `/api` |

## 3. Local Development

```bash
# Clone the repository
git clone <repo-url>
cd multi-agent-investigation-rag

# Generate a secret key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env and set SECRET_KEY

# Configure frontend
cp frontend/.env.example frontend/.env

# Start all services
docker compose up --build
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## 4. Remote Deployment (SSH)

### 4.1 First-Time Setup

```bash
# On the remote server — install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 4.2 Deploy / Update

For this repository on Windows, use the included helper:

```bat
dp_remote.bat
```

The script targets `francis@fraserver01`, deploys into `~/apps/multi-agent-investigation-rag`, keeps the backend `.env` if it already exists, and publishes the frontend on port `3002` to avoid the existing service already bound to `3000` on that server.

Manual deployment remains available if you need a different target or want to adapt the process:

```bash
# On your LOCAL machine — copy files to remote server
SERVER=user@your-server-ip
APP_DIR=/opt/multi-agent-rag

# Create directory on server
ssh $SERVER "mkdir -p $APP_DIR"

# Copy application files
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  --exclude='backend/data' \
  . $SERVER:$APP_DIR/

# SSH into server and start/update
ssh $SERVER "
  cd $APP_DIR

  # First time only: create .env files
  if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    KEY=\$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
    sed -i \"s/SECRET_KEY=/SECRET_KEY=\$KEY/\" backend/.env
  fi

  if [ ! -f frontend/.env ]; then
    cp frontend/.env.example frontend/.env
    # Keep same-origin API path for reverse-proxy setups
    sed -i 's|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=/api|g' frontend/.env
  fi

  # Pull latest and restart
  docker compose pull || true
  docker compose up --build -d

  echo 'Deployment complete'
"
```

### 4.3 Check Status

```bash
ssh $SERVER "cd /opt/multi-agent-rag && docker compose ps && docker compose logs --tail=50"
```

### 4.4 Stop / Remove

```bash
ssh $SERVER "cd /opt/multi-agent-rag && docker compose down"
# To also remove volumes (data):
ssh $SERVER "cd /opt/multi-agent-rag && docker compose down -v"
```

## 5. Data Persistence
Volumes are defined in `docker-compose.yml`:
- `backend_data`: SQLite database and ChromaDB files

Data survives `docker compose restart` and `docker compose up -d` but is removed by `docker compose down -v`.

## 6. Updating the Application

```bash
# On local machine
git pull
# Make changes
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  --exclude='backend/data' \
  . $SERVER:$APP_DIR/
ssh $SERVER "cd $APP_DIR && docker compose up --build -d"
```

## 7. Logs

```bash
ssh $SERVER "cd /opt/multi-agent-rag && docker compose logs -f backend"
ssh $SERVER "cd /opt/multi-agent-rag && docker compose logs -f frontend"
```
