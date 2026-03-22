# Contributing to Multi-Agent RAG Platform

Thank you for your interest in contributing! This document describes how to set up your development environment and submit changes.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to uphold it.

## How to Contribute

### Reporting Bugs

1. Search [existing issues](../../issues) to avoid duplicates.
2. Open a new issue with a clear title and description.
3. Include steps to reproduce, expected behaviour, and actual behaviour.
4. Attach logs or screenshots where relevant.

### Suggesting Enhancements

Open an issue with the `enhancement` label describing:
- The problem you are trying to solve
- Your proposed solution
- Alternatives you considered

### Submitting a Pull Request

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feature/my-feature
   ```
2. **Set up your development environment** (see below).
3. **Make your changes** following the coding conventions described below.
4. **Add or update tests** for the behaviour you changed.
5. **Run the test suite** to confirm everything passes (see [Running Tests](#running-tests)).
6. **Commit** with a clear, present-tense commit message (e.g. `Add broadcast mode timeout`).
7. **Push** your branch and open a Pull Request against `main`.
8. Respond to any review feedback.

## Development Setup

### Prerequisites

- Docker & Docker Compose v2
- Python 3.11+ (for backend development without Docker)
- Node.js 20+ (for frontend development without Docker)

### Running with Docker

```bash
cp backend/.env.example backend/.env
# Set SECRET_KEY in backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

### Running Backend Locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY in .env
uvicorn app.main:app --reload --port 8000
```

### Running Frontend Locally

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Running Tests

```bash
# Backend
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v

# Frontend
cd frontend
npm test
```

## Coding Conventions

### Backend (Python)

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
- Use `async`/`await` for all database and I/O operations.
- Add Pydantic schemas for all request and response bodies.
- Use `HTTPException` with appropriate status codes for error responses.
- Add type annotations to all function signatures.

### Frontend (TypeScript / React)

- Use functional components with React hooks.
- Define TypeScript interfaces in `src/types/index.ts`.
- Keep API calls in `src/services/api.ts`.
- Use TailwindCSS utility classes for styling.

## Security

If you discover a security vulnerability, please follow the responsible disclosure process described in [SECURITY.md](SECURITY.md). **Do not open a public issue** for security vulnerabilities.
