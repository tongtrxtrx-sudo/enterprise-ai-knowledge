# Scenario: AI Router Retry and Failover
- Given: multiple configured providers and retryable provider failures
- When: provider calls fail with timeout, 429, or 5xx responses
- Then: router retries up to three attempts on the current provider and fails over to the next provider

## Test Steps

- Case 1 (happy path): primary provider succeeds on first attempt with no failover
- Case 2 (edge case): primary provider fails with retryable errors for three attempts and secondary provider succeeds
- Case 3 (edge case): non-retryable error fails fast without exhausting retries

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
