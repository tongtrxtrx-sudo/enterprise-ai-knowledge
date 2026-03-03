# Scenario: Frontend and Backend Environment Validation
- Given: frontend and backend service definitions exist in compose
- When: service startup command/entrypoint is reviewed
- Then: each container validates mandatory environment variables before starting app process

## Test Steps

- Case 1 (happy path): backend startup script fails if required env is missing
- Case 2 (happy path): frontend startup script fails if required env is missing
- Case 3 (edge case): both scripts allow startup when vars are present

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
