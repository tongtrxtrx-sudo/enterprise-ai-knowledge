# Scenario: Parsing Pipeline Lifecycle
- Given: An uploaded record exists and background parsing is scheduled
- When: The parser runs with successful and failed embedding provider outcomes
- Then: Markdown/chunks/index metadata are persisted, vector-ready state follows provider outcome, and retry does not duplicate rows

## Test Steps

- Case 1 (happy path): Parsing produces Markdown, chunks, lexical index text, and vectors
- Case 2 (edge case): Embedding failure keeps `vector_ready=false` and retry updates existing rows without duplication

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

**IMPORTANT**: Only update above status when a step is confirmed complete. Do not hallucinate.
