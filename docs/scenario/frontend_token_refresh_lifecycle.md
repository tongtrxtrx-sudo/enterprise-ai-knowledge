# Scenario: Frontend retries unauthorized API calls after token refresh
- Given: frontend access token has expired but refresh cookie is still valid
- When: protected API request receives 401
- Then: frontend refreshes access token and retries request successfully

## Test Steps

- Case 1 (happy path): request succeeds after one refresh and retry
- Case 2 (edge path): second 401 after refresh clears session

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
