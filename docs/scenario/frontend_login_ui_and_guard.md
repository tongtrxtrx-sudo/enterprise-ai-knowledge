# Scenario: Frontend login UI and protected route access
- Given: user has no authenticated session in frontend state
- When: user submits valid credentials from login page
- Then: frontend stores access token, hydrates session from backend, and allows protected pages

## Test Steps

- Case 1 (happy path): login flow hydrates session with backend profile
- Case 2 (guard path): protected route requires authenticated session

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
