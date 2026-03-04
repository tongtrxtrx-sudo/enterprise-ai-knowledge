# Scenario: Chinese-First Primary Workflow Copy
- Given: chat/files/admin/shared workflows contain hardcoded English copy
- When: components use localized translations
- Then: major user-facing copy appears in Chinese by default across workflows

## Test Steps

- Case 1 (happy path): render chat/files/admin pages and validate Chinese labels and headings
- Case 2 (edge case): render forbidden/auth loading UI and validate Chinese fallback text

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
