# Deployment Runbook v2.1

## Scope

- Services: `nginx`, `frontend`, `backend`, `postgres`, `redis`, `minio`, `onlyoffice`
- Environment file: `.env.example` (replace with production values before deployment)
- Compose file: `infra/docker-compose.yml`

## Prerequisites

1. Docker Engine and Docker Compose v2 are installed.
2. Runtime variables are prepared in a deployment `.env` file.
3. Operator has shell access on the deployment host.

## Deployment Steps

1. Validate compose syntax:

```bash
docker compose --env-file .env.example -f infra/docker-compose.yml config
```

2. Start the stack with clean volumes for reproducible bootstrap:

```bash
bash infra/scripts/startup_check.sh
```

3. Verify service health summary:

```bash
docker compose --env-file .env.example -f infra/docker-compose.yml ps
```

4. Run latency and throughput smoke checks:

```bash
bash infra/scripts/run_k6_smoke.sh
```

5. Capture baseline backup after deployment is healthy:

```bash
bash infra/scripts/backup_stack.sh deploy-baseline
```

## Backup Procedure

1. Trigger backup snapshot:

```bash
bash infra/scripts/backup_stack.sh <backup-name>
```

2. Validate generated artifacts under `infra/backups/<backup-name>/`:
   - `postgres.dump` (schema + relational data)
   - `redis.rdb` (cache snapshot)
   - `minio-data/` (object data snapshot)

## Restore Procedure

1. Ensure stack is running (`docker compose ... up -d`).
2. Restore from snapshot:

```bash
bash infra/scripts/restore_stack.sh <backup-name>
```

3. Re-run startup and smoke checks:

```bash
bash infra/scripts/startup_check.sh
bash infra/scripts/run_k6_smoke.sh
```

## Rollback

1. Pick the most recent known-good backup.
2. Execute restore:

```bash
bash infra/scripts/restore_stack.sh <known-good-backup>
```

3. Confirm health and k6 thresholds pass.
4. Keep incident notes and backup name in operation log.
