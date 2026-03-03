# Scenario: Public Query Exact-Match Cache
- Given: a public query request that has already been answered once
- When: the same normalized query is requested again as public query
- Then: service returns cached answer path and avoids an additional provider invocation

## Test Steps

- Case 1 (happy path): first public query stores cache entry
- Case 2 (edge case): second exact-match public query returns cached answer and preserves citations

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
