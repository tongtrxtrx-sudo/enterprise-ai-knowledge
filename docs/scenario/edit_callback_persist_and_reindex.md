# Scenario: Edit Callback Persist and Reindex
- Given: valid active edit session and callback save event
- When: callback status 2/6 is posted with valid token and content
- Then: file version is appended, files.current_version is updated, and reindex is queued immediately

## Test Steps

- Case 1 (happy path): status 2 save appends version and updates current version
- Case 2 (happy path): successful save queues immediate reindex once

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
