# Production Pre-Launch Checklist

## Purpose

Use this checklist before first production launch or any major cutover.

## 1) Secrets and Environment

- Copy `.env.production.example` to `.env.production` and replace every `<...>` placeholder.
- Confirm `APP_ENV=production`.
- Confirm `JWT_SECRET`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, and `ONLYOFFICE_JWT_SECRET` are deployment-specific values.
- Confirm `ONLYOFFICE_JWT_ENABLED=true`.
- Validate startup guardrails:

```bash
docker compose --env-file .env.production -f infra/docker-compose.yml run --rm backend python /app/scripts/validate_env.py backend
docker compose --env-file .env.production -f infra/docker-compose.yml run --rm frontend python /app/scripts/validate_env.py frontend
```

## 2) Storage and Data Protection

- Ensure persistent volumes are available for PostgreSQL, Redis, and MinIO.
- Confirm backup folder `infra/backups/` is writable by operators.
- Generate a baseline snapshot before go-live:

```bash
bash infra/scripts/backup_stack.sh prelaunch-baseline
```

## 3) Authentication Bootstrap

- Initialize the first admin account before opening public traffic:

```bash
cd backend
uv run python scripts/bootstrap_admin.py --username admin --password '<STRONG_PASSWORD>' --department platform
```

- If admin already exists and password rotation is required:

```bash
cd backend
uv run python scripts/bootstrap_admin.py --username admin --password '<NEW_STRONG_PASSWORD>' --department platform --rotate-password
```

## 4) Observability and Health

- Confirm health endpoints return success: nginx `/health`, backend `/health`, MinIO live check, ONLYOFFICE healthcheck.
- Verify container health status shows `healthy` for all seven services.
- Ensure audit trail is writable by checking new entries in `audit_logs` after admin bootstrap.
- Run smoke checks and confirm thresholds pass:

```bash
bash infra/scripts/run_k6_smoke.sh
```

## 5) Rollback Basics

- Trigger rollback if startup validation, auth bootstrap, or smoke checks fail.
- Restore the latest known-good snapshot:

```bash
bash infra/scripts/restore_stack.sh <known-good-backup>
```

- Re-run health and smoke checks after restore.
- Record failure reason, rollback timestamp, and backup name in the operation log.
