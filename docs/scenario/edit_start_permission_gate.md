# Scenario: Edit Start Permission Gate
- Given: file records with owner, department, and optional shared-edit grants
- When: authenticated users call edit start endpoint
- Then: only owner/admin/dept manager(shared department)/shared-edit grantees receive editor config

## Test Steps

- Case 1 (happy path): owner starts edit session and gets token bound to current version
- Case 2 (happy path): admin starts edit session for any file
- Case 3 (happy path): department manager of same department starts edit session
- Case 4 (happy path): shared user with `can_edit=true` starts edit session
- Case 5 (edge case): unauthorized user receives 403

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
