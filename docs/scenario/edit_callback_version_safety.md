# Scenario: Edit Callback Version Safety
- Given: active edit session token bound to a file and a source version
- When: callback receives save status updates
- Then: stale source version or duplicate save callback is rejected and no extra version is created

## Test Steps

- Case 1 (edge case): callback with stale session source version returns error and writes nothing
- Case 2 (edge case): duplicate callback for already saved session returns error and does not append a duplicate version

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
