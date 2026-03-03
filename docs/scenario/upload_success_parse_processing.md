# Scenario: Upload Success Parse Processing
- Given: valid upload payload with non-duplicate checksum
- When: client uploads file successfully
- Then: metadata is persisted with deterministic MinIO object key, parse status starts as `processing`, and parse task is triggered asynchronously

## Test Steps

- Case 1 (happy path): successful upload returns deterministic success payload with object key
- Case 2 (edge case): parse status is persisted as `processing` immediately after response
- Case 3 (edge case): background parse task trigger function is invoked asynchronously

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
