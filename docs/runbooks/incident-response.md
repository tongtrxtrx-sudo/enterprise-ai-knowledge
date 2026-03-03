# Incident Response Run Flow

## Severity and Initial Actions

1. Confirm impact scope (users, APIs, editor, indexing).
2. Freeze high-risk writes if data corruption is suspected.
3. Collect diagnostics:

```bash
docker compose --env-file .env.example -f infra/docker-compose.yml ps
docker compose --env-file .env.example -f infra/docker-compose.yml logs --tail=200 backend
```

4. If service health is degraded, run:

```bash
bash infra/scripts/startup_check.sh
```

## Incident: Failed Indexing

### Indicators

- Upload parse status remains `failed` or `degraded`.
- Retrieval results are stale or missing expected chunks.

### Response Steps

1. Identify failed upload IDs from backend logs.
2. Re-run parse/index job for impacted IDs (application operator command).
3. Verify `/health` and retrieval behavior after reindex.
4. Run smoke checks:

```bash
bash infra/scripts/run_k6_smoke.sh
```

### Rollback for Failed Indexing

1. Restore last good snapshot if reindex keeps failing:

```bash
bash infra/scripts/restore_stack.sh <known-good-backup>
```

2. Confirm object data exists in MinIO and relational rows are restored.
3. Re-run startup and k6 smoke checks.

## Incident: Editor Callback Failures

### Indicators

- Callback endpoint returns repeated errors.
- File versions are not incrementing after save.
- Reindex queue is not populated after editor save.

### Response Steps

1. Confirm `onlyoffice` and `backend` service health.
2. Inspect callback payload/status in backend logs.
3. Retry save workflow with a controlled test document.
4. Validate file version increment and reindex queue side effects.

### Rollback for Editor Callback Incident

1. Disable editor entry point temporarily (maintenance mode at gateway/app).
2. Restore from known-good backup if data divergence is detected:

```bash
bash infra/scripts/restore_stack.sh <known-good-backup>
```

3. Re-enable editor only after callback path is healthy and smoke checks pass.

## Closeout Checklist

1. Record timeline, root cause, and corrective actions.
2. Save backup name/hash used for rollback.
3. Confirm all seven services are healthy.
4. Confirm k6 thresholds (`p95<500ms`, `failed<1%`, `checks>99%`) are met.
