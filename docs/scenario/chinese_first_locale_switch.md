# Scenario: Chinese-First Locale Switch
- Given: app defaults to Chinese and includes an English option
- When: user switches language in app shell
- Then: localized labels immediately update and English remains available

## Test Steps

- Case 1 (happy path): switch from Chinese to English and assert nav labels update
- Case 2 (edge case): new render after switching keeps selected locale via local storage

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
