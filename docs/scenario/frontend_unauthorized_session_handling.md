# Scenario: Unauthorized requests clear session and force re-authentication
- Given: frontend has an expired or invalid access token
- When: authenticated API request returns unauthorized and refresh is unavailable
- Then: frontend clears session state and user must log in again

## Test Steps

- Case 1 (edge path): unauthorized request with failed refresh triggers session clear callback
- Case 2 (guard path): no active session cannot access protected route

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
