# Scenario: SSE Chat Streaming With Citations
- Given: an authenticated chat request and routed AI answer
- When: client opens the SSE chat endpoint
- Then: response streams chunk events and each chunk includes citation fields

## Test Steps

- Case 1 (happy path): endpoint streams multiple chunk events ending with done event
- Case 2 (edge case): chunk event payload includes citation entries with upload and chunk indexes

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
