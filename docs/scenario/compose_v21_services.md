# Scenario: Compose v2.1 Services
- Given: the runtime scaffold files are present
- When: the compose file is inspected
- Then: services include nginx, frontend, backend, postgres, redis, minio, and onlyoffice

## Test Steps

- Case 1 (happy path): verify all required service keys exist in compose services map
- Case 2 (edge case): verify no required service is omitted

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
