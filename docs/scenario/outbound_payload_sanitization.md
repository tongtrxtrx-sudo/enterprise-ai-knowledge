# Scenario: Outbound Payload Sanitization
- Given: retrieval chunks with rich metadata and potentially sensitive source content
- When: chat service builds outbound provider payload
- Then: payload includes only sanitized snippets and redacted metadata without full content or user identifiers

## Test Steps

- Case 1 (happy path): short chunk content is passed as snippet with safe metadata fields
- Case 2 (edge case): long content is truncated to snippet length
- Case 3 (edge case): user-related metadata fields are removed from payload

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
