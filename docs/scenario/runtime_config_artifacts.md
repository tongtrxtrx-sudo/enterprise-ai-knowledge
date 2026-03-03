# Scenario: Runtime Config Artifacts
- Given: scaffold configuration files are generated
- When: runtime config files are inspected
- Then: reverse proxy config and environment schema files are present and reference backend/frontend routing and required variables

## Test Steps

- Case 1 (happy path): nginx config exists and has upstream/proxy rules
- Case 2 (happy path): environment schema file exists and defines required frontend/backend variables

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
