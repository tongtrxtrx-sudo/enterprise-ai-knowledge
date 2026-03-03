## Summary

- Deliver v2.1 end-to-end runtime and product workflow across backend, frontend, infrastructure, and operations.
- Implement security, permission, and reliability controls for auth, upload, parsing, editing, retrieval, and AI routing.
- Add production hardening assets including backup/restore scripts, health constraints, runbooks, and smoke checks.

## Key Changes

- Runtime bootstrap with seven-service Compose stack and health contract checks.
- Authentication with token rotation, token version validation, and PostgreSQL-backed logout invalidation.
- Secure upload flow with validation, deduplication, deterministic versioning, and async parse kickoff.
- Parsing and retrieval pipeline with MarkItDown, chunk/vector persistence, and permission-aware RRF retrieval.
- ONLYOFFICE online editing with callback idempotency and immediate reindex enqueue.
- Folder permission governance, admin-only controls, and audit logging.
- AI routing with retry/failover, payload sanitization, SSE chat streaming, and citations.
- Frontend delivery for chat, file manager, online editing, and admin management workflows.
- Production delivery hardening with runbooks and smoke validation.

## Validation

- [ ] Backend unit/integration tests pass
- [ ] Frontend tests pass
- [ ] Frontend build passes
- [ ] Smoke/load checks pass in target environment
- [ ] Deployment runbook dry-run reviewed

## Risks and Rollback

- Risk: External provider timeout and quota instability during failover.
  - Mitigation: Keep retry budget and provider order configurable.
- Risk: Permission model regression leaking unauthorized data.
  - Mitigation: Re-run permission isolation tests and role guard tests before release.
- Risk: Callback or indexing incident during online editing.
  - Mitigation: Follow incident runbook rollback steps for callback/index recovery.

## Deployment Notes

- Confirm environment variables and secrets are set for all seven services.
- Run backup script and verify restore in staging before production rollout.
- Monitor health probes, callback queue, and retrieval latency immediately after deployment.
