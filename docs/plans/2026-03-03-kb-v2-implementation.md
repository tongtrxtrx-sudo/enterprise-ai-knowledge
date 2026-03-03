# Enterprise AI Knowledge Base v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a production-ready intranet AI knowledge base system from `technical-proposal.md` with secure auth, file management, hybrid retrieval, and admin governance.

**Architecture:** Build a six-service Docker Compose stack (`nginx`, `frontend`, `backend`, `postgresql`, `redis`, `minio`) with a FastAPI backend and React frontend. Use PostgreSQL (`pgvector`, `tsvector`) as the single persistence and retrieval engine, with Redis for volatile cache only. Implement AI provider routing with retry and failover, strict permission filtering, and SSE chat responses with citations.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/Alembic, PostgreSQL 16 + pgvector + zhparser, Redis 7, MinIO, React 18 + TypeScript + Ant Design 5, Vite 6, Docker Compose, Nginx, `uv`, `pytest`.

---

## Scope and Delivery Rules

- Use TDD for all backend domain logic and security boundaries.
- Keep each task independently shippable with passing tests.
- Use `uv` for Python dependency and command execution.
- Keep public answer cache as exact string match only.
- Keep token blacklist in PostgreSQL, not Redis.

---

### Task 1: Bootstrap Monorepo Skeleton and Runtime Contracts

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/nginx/nginx.conf`
- Create: `backend/pyproject.toml`
- Create: `backend/src/app/main.py`
- Create: `frontend/package.json`
- Create: `frontend/src/main.tsx`
- Create: `.env.example`
- Test: `backend/tests/test_healthcheck.py`

**Step 1: Write the failing test**

Create `backend/tests/test_healthcheck.py` to assert:
- `GET /health` returns `200`
- JSON payload contains service name and version fields

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_healthcheck.py -v`
Expected: FAIL because app and route do not exist.

**Step 3: Write minimal implementation**

- Implement `backend/src/app/main.py` with a FastAPI app.
- Add `/health` route returning static metadata.
- Add local entrypoint and import-safe app factory.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_healthcheck.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add infra/docker-compose.yml infra/nginx/nginx.conf backend frontend .env.example
git commit -m "chore: bootstrap runtime skeleton and healthcheck"
```

---

### Task 2: Implement Authentication and Session Invalidation

**Files:**
- Create: `backend/src/app/auth/schemas.py`
- Create: `backend/src/app/auth/router.py`
- Create: `backend/src/app/auth/service.py`
- Create: `backend/src/app/models/user.py`
- Create: `backend/src/app/models/token_blacklist.py`
- Create: `backend/alembic/versions/0001_auth_tables.py`
- Modify: `backend/src/app/main.py`
- Test: `backend/tests/auth/test_login_refresh_logout.py`

**Step 1: Write failing tests**

Create tests for:
- Login with valid credentials returns access token and refresh cookie.
- Refresh fails if JTI is blacklisted.
- Token with stale `token_version` is rejected.

**Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/auth/test_login_refresh_logout.py -v`
Expected: FAIL with missing routes/models.

**Step 3: Write minimal implementation**

- Implement bcrypt password verification.
- Implement HS256 JWT issuing and verification.
- Persist refresh JTI blacklist records in PostgreSQL.
- Implement logout endpoint that inserts current refresh JTI.

**Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/auth/test_login_refresh_logout.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/app/auth backend/src/app/models backend/alembic
git commit -m "feat: add local auth with postgres token blacklist"
```

---

### Task 3: Implement File Upload Security, Dedup, and Versioning

**Files:**
- Create: `backend/src/app/files/router.py`
- Create: `backend/src/app/files/service.py`
- Create: `backend/src/app/files/validators.py`
- Create: `backend/src/app/models/file.py`
- Create: `backend/src/app/models/file_version.py`
- Create: `backend/src/app/storage/minio_client.py`
- Create: `backend/alembic/versions/0002_files_tables.py`
- Test: `backend/tests/files/test_upload_rules.py`
- Test: `backend/tests/files/test_versioning.py`

**Step 1: Write failing tests**

Create tests for:
- Reject file size greater than 10MB with `413`.
- Reject executable signatures even with fake extension.
- Return `409` for same hash in same folder.
- Create new version for same name with different hash.

**Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/files -v`
Expected: FAIL due missing upload service.

**Step 3: Write minimal implementation**

- Add upload endpoint `POST /api/v1/upload`.
- Validate size, magic bytes, and filename sanitization.
- Compute SHA-256 server-side.
- Implement dedup and versioning logic with row-level consistency.

**Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/files -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/app/files backend/src/app/storage backend/alembic
git commit -m "feat: implement secure upload, dedup, and file versioning"
```

---

### Task 4: Implement Parsing Pipeline and Hybrid Retrieval Storage

**Files:**
- Create: `backend/src/app/indexing/tasks.py`
- Create: `backend/src/app/indexing/chunker.py`
- Create: `backend/src/app/indexing/embedding.py`
- Create: `backend/src/app/indexing/retrieval.py`
- Create: `backend/src/app/models/doc_chunk.py`
- Create: `backend/src/app/models/index_tree.py`
- Create: `backend/alembic/versions/0003_indexing_tables.py`
- Test: `backend/tests/indexing/test_pipeline_lifecycle.py`
- Test: `backend/tests/retrieval/test_rrf_query.py`

**Step 1: Write failing tests**

Add tests for:
- Background task updates parse lifecycle states.
- `vector_ready` remains false when embedding fails.
- RRF merge returns deterministic Top-N ordering.
- Retrieval query excludes unauthorized chunks.

**Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/indexing tests/retrieval -v`
Expected: FAIL because pipeline and SQL are missing.

**Step 3: Write minimal implementation**

- Add Background Task orchestration for parse -> chunk -> embed -> metadata.
- Persist `content`, `content_tsv`, and `content_vector`.
- Implement BM25 + vector SQL retrieval with RRF merge (`k=60`).
- Enforce permission filter in retrieval SQL where clause.

**Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/indexing tests/retrieval -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/app/indexing backend/src/app/models backend/alembic
git commit -m "feat: add indexing pipeline and hybrid retrieval storage"
```

---

### Task 5: Implement AI Routing, Failover, and SSE Chat API

**Files:**
- Create: `backend/src/app/ai/router.py`
- Create: `backend/src/app/ai/providers.py`
- Create: `backend/src/app/chat/router.py`
- Create: `backend/src/app/chat/service.py`
- Create: `backend/src/app/chat/cache.py`
- Create: `backend/src/app/models/chat_message.py`
- Create: `backend/tests/ai/test_failover_policy.py`
- Create: `backend/tests/chat/test_sse_response.py`

**Step 1: Write failing tests**

Add tests for:
- Retry exactly three times for timeout, 429, and 5xx.
- Switch to backup provider after retry budget exhaustion.
- Stream SSE response chunks with citation payload.
- Return exact-match cache hit for repeated public query string.

**Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/ai tests/chat -v`
Expected: FAIL because provider router and SSE handler are missing.

**Step 3: Write minimal implementation**

- Implement provider map for indexing, embedding, and QA.
- Implement retry and backup switch rules.
- Implement `/api/v1/chat/stream` with SSE output and citations.
- Implement exact-match public cache in Redis with 1-hour TTL.

**Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/ai tests/chat -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/app/ai backend/src/app/chat backend/tests
git commit -m "feat: add AI failover routing and SSE chat streaming"
```

---

### Task 6: Implement Permission Governance and Admin APIs

**Files:**
- Create: `backend/src/app/permissions/router.py`
- Create: `backend/src/app/permissions/service.py`
- Create: `backend/src/app/admin/router.py`
- Create: `backend/src/app/audit/router.py`
- Create: `backend/src/app/models/folder_permission.py`
- Create: `backend/src/app/models/audit_log.py`
- Test: `backend/tests/permissions/test_grant_revoke.py`
- Test: `backend/tests/admin/test_role_guard.py`

**Step 1: Write failing tests**

Add tests for:
- Default isolation exposes only personal + granted + public data.
- Grant and revoke operations update retrieval visibility.
- Non-admin user cannot access admin endpoints.
- Mutating operations create audit log records.

**Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/permissions tests/admin -v`
Expected: FAIL due missing services and role guards.

**Step 3: Write minimal implementation**

- Implement folder grant/revoke APIs.
- Synchronize `doc_chunks.read_allow` on permission updates.
- Add admin route guards for role restrictions.
- Add audit log writer for auth, file, permission, and AI events.

**Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/permissions tests/admin -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/app/permissions backend/src/app/admin backend/src/app/audit
git commit -m "feat: add permission governance and admin audit apis"
```

---

### Task 7: Deliver Frontend MVP (Chat + File Manager + Admin)

**Files:**
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/features/chat/ChatPage.tsx`
- Create: `frontend/src/features/files/FileManagerPage.tsx`
- Create: `frontend/src/features/admin/AdminPage.tsx`
- Create: `frontend/src/lib/http/client.ts`
- Create: `frontend/src/lib/state/sessionStore.ts`
- Create: `frontend/src/lib/state/queryClient.ts`
- Test: `frontend/src/features/chat/ChatPage.test.tsx`
- Test: `frontend/src/features/files/FileUpload.test.tsx`

**Step 1: Write failing tests**

Add tests for:
- Chat page renders SSE stream chunks and citations.
- File upload UI shows progress and error states.
- Unauthorized admin route redirects to forbidden page.

**Step 2: Run tests to verify failure**

Run: `cd frontend && npm test -- --runInBand`
Expected: FAIL due missing components.

**Step 3: Write minimal implementation**

- Build route shell with auth guard.
- Implement chat panel + side file tree interaction.
- Implement upload UI with progress polling.
- Implement basic admin table pages.

**Step 4: Run tests to verify pass**

Run: `cd frontend && npm test -- --runInBand`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: deliver frontend mvp for chat file and admin modules"
```

---

### Task 8: Production Hardening, SLO Verification, and Release Docs

**Files:**
- Create: `tests/e2e/test_main_flows.md`
- Create: `tests/load/k6_smoke.js`
- Create: `ops/backup/backup.sh`
- Create: `ops/backup/restore.sh`
- Create: `docs/runbooks/deploy.md`
- Create: `docs/runbooks/incident-response.md`
- Modify: `infra/docker-compose.yml`

**Step 1: Write failing verification checks**

Define checks for:
- 30 concurrent users baseline.
- Chat first-byte <= 2 seconds target under representative load.
- File retrieval <= 3 seconds target.
- Backup and restore pass RPO/RTO objectives.

**Step 2: Run checks to verify initial failure**

Run:
- `docker compose -f infra/docker-compose.yml up -d`
- `k6 run tests/load/k6_smoke.js`
Expected: FAIL or partial due missing tuning and scripts.

**Step 3: Write minimal hardening implementation**

- Add service health checks and startup ordering.
- Add backup and restore scripts for PostgreSQL, MinIO, and Redis.
- Add release runbooks and incident handling guides.

**Step 4: Run checks to verify pass**

Run:
- `docker compose -f infra/docker-compose.yml up -d`
- `k6 run tests/load/k6_smoke.js`
Expected: PASS for defined smoke thresholds.

**Step 5: Commit**

```bash
git add tests ops docs infra/docker-compose.yml
git commit -m "chore: add production hardening checks and release runbooks"
```

---

## Dependency Install Checklist

- Backend: `cd backend && uv sync`
- Frontend: `cd frontend && npm install`
- Local tooling: `docker`, `docker compose`, `k6`, `psql` client

---

## Risks and Mitigations

- AI provider instability: enforce retry and deterministic failover with explicit degraded mode response.
- Permission leakage risk: keep retrieval filtering in SQL layer and add negative integration tests for unauthorized access.
- Background task inconsistency: persist parse states and run idempotent retries keyed by `file_id` and `version`.
- Small-team delivery risk: keep strict phase boundaries and avoid optional features before core acceptance criteria are met.

---

## Done Criteria

- All phase acceptance criteria from `technical-proposal.md` are traceable to automated tests or operational checks.
- API security and permission boundaries are covered by unit and integration tests.
- Runtime stack starts reproducibly with `docker compose`.
- Release docs are sufficient for on-call operations with no tribal knowledge.

---

Plan complete and saved to `docs/plans/2026-03-03-kb-v2-implementation.md`.

Two execution options:

1. Subagent-Driven (this session) - I dispatch a fresh subagent per task, review between tasks, and iterate quickly.
2. Parallel Session (separate) - Open a new session with `executing-plans` for batched implementation with checkpoints.
