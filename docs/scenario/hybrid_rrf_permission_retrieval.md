# Scenario: Hybrid RRF Retrieval with Permission Filter
- Given: Chunk rows exist with lexical data, vectors, and permission markers
- When: Hybrid retrieval executes BM25 plus vector SQL RRF merge for a query
- Then: Unauthorized chunks are excluded and result ordering is deterministic for repeated calls

## Test Steps

- Case 1 (happy path): Authorized principals receive only allowed chunks
- Case 2 (edge case): Same inputs return stable top ordering across repeated calls

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

**IMPORTANT**: Only update above status when a step is confirmed complete. Do not hallucinate.
