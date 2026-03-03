# Scenario: Backend Health Contract
- Given: backend application is running via test client
- When: client sends GET request to `/health`
- Then: response status is 200 and payload contains `service_name` and `version`

## Test Steps

- Case 1 (happy path): endpoint returns status 200
- Case 2 (edge case): endpoint payload includes required keys regardless of extra fields

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
