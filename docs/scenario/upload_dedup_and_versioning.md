# Scenario: Upload Deduplication and Versioning
- Given: existing uploads already persisted in the same folder
- When: client uploads same checksum or same name with new checksum
- Then: duplicate checksum returns HTTP 409 and same name with new checksum creates incremented version

## Test Steps

- Case 1 (edge case): same folder + same checksum returns HTTP 409 duplicate response
- Case 2 (happy path): same folder + same filename + different checksum creates new version

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
