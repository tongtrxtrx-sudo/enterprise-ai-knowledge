# Scenario: Chinese-First I18n Infrastructure
- Given: Frontend currently renders static strings directly in components
- When: i18n provider and locale resources are introduced
- Then: app locale defaults to Chinese and exposes translation lookup APIs

## Test Steps

- Case 1 (happy path): render with no stored locale and confirm Chinese text is shown
- Case 2 (edge case): pre-set English locale and confirm English text is shown

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
