# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Edit start permission gate
Only owner, admin, department manager (same department), and shared users with edit grant can start ONLYOFFICE edit sessions.

### FR-2: Callback version safety and idempotency
Callback accepts ONLYOFFICE status 2/6 save events only when edit token and bound source version are current; stale version tokens and duplicate save callbacks are rejected.

### FR-3: Persist new version and trigger immediate reindex
Successful callback save appends a new record in `file_versions`, updates `files.current_version`, and queues immediate reindex.

## Assumptions

- Edit callback payload includes `token`, `status`, and `content` fields and uses `status` in `{2, 6}` to represent successful save events.
- Existing backend has no `files`/`file_versions` schema yet, so this task introduces minimal models required for acceptance criteria without changing unrelated upload pipeline behavior.
