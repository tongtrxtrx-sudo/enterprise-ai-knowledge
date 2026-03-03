# Scenario: Upload Validation Safety
- Given: a client sends multipart upload payload to `/uploads`
- When: file is too large, filename is unsafe, or file has executable signature
- Then: endpoint returns deterministic reject response and does not persist file record

## Test Steps

- Case 1 (edge case): file size greater than 10 MB returns HTTP 413
- Case 2 (edge case): unsafe filename returns HTTP 400
- Case 3 (edge case): executable magic header returns HTTP 400

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
