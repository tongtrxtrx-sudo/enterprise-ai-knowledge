# Release Notes - v2.1

## Overview

This release delivers the complete v2.1 runtime, backend, frontend, and operations baseline for the Enterprise AI Knowledge Base.

## Major Deliverables

### Runtime Bootstrap
- Added a runnable Docker Compose stack with seven services: nginx, frontend, backend, postgres, redis, minio, and onlyoffice.
- Added reverse proxy configuration and environment validation contracts for frontend and backend startup.
- Added backend health endpoint and health contract tests.

### Authentication Core
- Implemented local account authentication with JWT access and refresh tokens.
- Added refresh token rotation, token version checks, and PostgreSQL-backed refresh token blacklist invalidation.
- Enforced role-based access guards with secure cookie settings in auth flows.

### Secure Uploading
- Added upload validation for file size, executable signatures, and unsafe filenames.
- Implemented checksum deduplication and deterministic versioning behavior.
- Added asynchronous parse trigger with initial `parse_status=processing` persistence.

### Parsing and Retrieval Pipeline
- Added MarkItDown-based parsing, chunking, and vectorization pipeline.
- Persisted parsing artifacts into `doc_chunks` and `index_tree` via background tasks.
- Implemented BM25 + vector RRF retrieval with permission predicates.
- Added deterministic vector failure handling and retry-safe behavior.

### Online Editing
- Implemented ONLYOFFICE single-user edit session start and callback workflow.
- Added stale token/version checks and duplicate-save idempotency protections.
- Added callback persistence to file versions and immediate reindex queueing.

### Permission Governance
- Implemented folder permission management with default editable sharing.
- Synchronized permission grants into retrieval visibility fields.
- Added admin-only control endpoints and audit logging for permission mutations.
- Enforced owned/granted/public visibility boundaries in retrieval and listing.

### AI Routing and Chat Streaming
- Implemented provider retry and failover with a 3-attempt strategy.
- Added outbound payload sanitization to prevent full-content and user-identifier leakage.
- Implemented SSE chat streaming with citations.
- Added exact-match cache path for repeated public queries.

### Frontend Workflow
- Delivered auth-aware route shell and permission-aware side navigation.
- Added chat page with SSE streaming and citation rendering.
- Added file manager with upload, tree browsing, and version actions.
- Embedded ONLYOFFICE iframe flow for edit sessions.
- Added admin pages for users, departments, permissions, and audit states.

### Production Delivery
- Added backup and restore scripts for PostgreSQL, Redis, and MinIO.
- Added health probes and startup dependency constraints for service orchestration.
- Published deployment and incident response runbooks.
- Added and executed smoke load checks for latency and throughput baseline.

## Validation Summary

- Backend test suites were expanded and executed across runtime, auth, upload, parsing, editing, permissions, AI routing, and delivery artifacts.
- Frontend workflow includes unit tests for streaming chat, file permissions, and admin route guards.
- Build and smoke checks were completed as part of task acceptance execution.

## Upgrade Notes

- Ensure production secrets and credentials are configured before deployment.
- Run backup and restore scripts in staging before first production rollout.
- Verify external provider credentials and timeout policies for AI routing failover behavior.
