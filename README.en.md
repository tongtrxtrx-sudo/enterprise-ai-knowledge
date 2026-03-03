# Enterprise AI Knowledge Base (v2.1)

An enterprise AI knowledge base project that delivers the full path from runtime bootstrap and backend capabilities to frontend workflow and production delivery.

## Overview

- Runtime: 7-service Docker Compose stack (nginx, frontend, backend, postgres, redis, minio, onlyoffice)
- Backend: authentication, upload flow, parsing/indexing, permission governance, online editing callback, AI routing, and SSE chat
- Frontend: chat page, file manager, online editing, and admin pages
- Operations: backup/restore scripts, health probes, deployment and incident runbooks, smoke load checks

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PyJWT, MarkItDown
- Frontend: React, TypeScript, Vite, Vitest
- Infra: Docker Compose, Nginx, PostgreSQL, Redis, MinIO, ONLYOFFICE

## Project Structure

```text
.
|- backend/      # Backend services and tests
|- frontend/     # Frontend app and tests
|- infra/        # Docker Compose and nginx config
|- docs/         # Plans, scenarios, runbooks, and release docs
|- tasks.json    # Task execution status
```

## Quick Start

### 1) Start Full Environment (Recommended)

Run from project root:

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Default endpoints:

- Nginx: `http://127.0.0.1:8080`
- Backend Health: `http://127.0.0.1:8000/health`
- MinIO Console: `http://127.0.0.1:9001`
- ONLYOFFICE: `http://127.0.0.1:8082`

### 2) Local Development (Optional)

Backend:

```bash
cd backend
uv run --group dev pytest tests -q
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

## Key Documents

- Release notes: `docs/release-notes-v2.1.md`
- PR description draft: `docs/pr-description-v2.1.md`
- Deployment runbook: `docs/runbooks/deployment-v2.1.md`
- Incident response runbook: `docs/runbooks/incident-response.md`

## Version

- Current version: `v2.1`

## 中文版本

中文文档请查看 `README.md`。
