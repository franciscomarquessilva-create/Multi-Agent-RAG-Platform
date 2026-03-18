@echo off
setlocal EnableExtensions

cd /d "%~dp0"

:: -----------------------------------------------------------------------
:: Configure these three variables before running the script.
:: -----------------------------------------------------------------------
set "SERVER=user@your-server"
set "APP_DIR=~/apps/multi-agent-investigation-rag"
set "FRONTEND_PORT=3000"
set "DEPLOY_MODE=fast"

if /I "%~1"=="--full-backend" set "DEPLOY_MODE=full-backend"
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="-h" goto :usage

where ssh >nul 2>nul
if errorlevel 1 (
    echo [error] OpenSSH client was not found in PATH.
    exit /b 1
)

where scp >nul 2>nul
if errorlevel 1 (
    echo [error] SCP was not found in PATH.
    exit /b 1
)

echo [1/5] Preparing remote directories...
ssh %SERVER% "mkdir -p %APP_DIR%/backend %APP_DIR%/frontend %APP_DIR%/docs && rm -rf %APP_DIR%/backend/app %APP_DIR%/backend/tests %APP_DIR%/frontend/src %APP_DIR%/docs/*"
if errorlevel 1 exit /b 1

echo [2/5] Uploading root files...
scp docker-compose.yml README.md %SERVER%:%APP_DIR%/
if errorlevel 1 exit /b 1

scp docs/ARCHITECTURE.md docs/DEPLOYMENT.md docs/REQUIREMENTS.md docs/TESTS.md %SERVER%:%APP_DIR%/docs/
if errorlevel 1 exit /b 1

echo [3/5] Uploading backend and frontend sources...
scp -r backend/app backend/tests backend/Dockerfile backend/requirements.txt backend/.env.example backend/.gitignore %SERVER%:%APP_DIR%/backend/
if errorlevel 1 exit /b 1

scp -r frontend/src frontend/Dockerfile frontend/index.html frontend/nginx.conf frontend/package.json frontend/package-lock.json frontend/postcss.config.js frontend/tailwind.config.js frontend/tsconfig.json frontend/vite.config.ts frontend/.env.example %SERVER%:%APP_DIR%/frontend/
if errorlevel 1 exit /b 1

echo [4/5] Ensuring remote environment files...
ssh %SERVER% "if [ ! -f %APP_DIR%/backend/.env ]; then KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'); echo SECRET_KEY=$KEY > %APP_DIR%/backend/.env; echo DATABASE_URL=sqlite+aiosqlite:///./data/app.db >> %APP_DIR%/backend/.env; echo CHROMA_PERSIST_DIR=./data/chroma >> %APP_DIR%/backend/.env; echo BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173 >> %APP_DIR%/backend/.env; echo CF_TEAM_DOMAIN= >> %APP_DIR%/backend/.env; echo ADMIN_EMAILS= >> %APP_DIR%/backend/.env; echo DEFAULT_USER_CREDITS=100 >> %APP_DIR%/backend/.env; echo DEFAULT_AGENT_LIMIT=10 >> %APP_DIR%/backend/.env; echo CREDITS_PER_ITERATION=1 >> %APP_DIR%/backend/.env; fi; echo VITE_API_BASE_URL=/api > %APP_DIR%/frontend/.env; echo FRONTEND_PORT=%FRONTEND_PORT% > %APP_DIR%/.env"
if errorlevel 1 exit /b 1

if /I "%DEPLOY_MODE%"=="full-backend" (
    echo [5/5] Full rebuild ^(backend + frontend^) and smoke checks...
    ssh %SERVER% "cd %APP_DIR% && docker compose up --build -d && sleep 5 && curl -fsS http://localhost:8000/health && echo && curl -fsS http://localhost:%FRONTEND_PORT% > /dev/null && docker compose ps"
    if errorlevel 1 exit /b 1
) else (
    echo [5/5] Fast deploy ^(rebuild frontend only^) and smoke checks...
    ssh %SERVER% "cd %APP_DIR% && docker compose build frontend && docker compose up -d --no-deps frontend && sleep 5 && curl -fsS http://localhost:8000/health && echo && curl -fsS http://localhost:%FRONTEND_PORT% > /dev/null && docker compose ps"
    if errorlevel 1 exit /b 1
)

echo Deployment complete.
echo Frontend: http://<your-server>:%FRONTEND_PORT%
echo Backend:  http://<your-server>:8000
if /I "%DEPLOY_MODE%"=="fast" echo Mode: fast ^(frontend rebuild only^)
if /I "%DEPLOY_MODE%"=="full-backend" echo Mode: full-backend ^(backend + frontend rebuild^)

endlocal
exit /b 0

:usage
echo Usage:
echo   dp_remote.bat                ^(fast deploy: rebuild frontend only^)
echo   dp_remote.bat --full-backend ^(full deploy: rebuild backend + frontend^)
endlocal
exit /b 0