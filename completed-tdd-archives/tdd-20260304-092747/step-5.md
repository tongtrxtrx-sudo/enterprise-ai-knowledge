# Step 5 - Refactor for Maintainability

## Refactorings Completed

- FR-1: Login and session bootstrap from backend auth - `docs/scenario/frontend_login_ui_and_guard.md` - Centralized backend session-to-frontend mapping in `applyAccessToken`
- FR-2: Token persistence and refresh lifecycle - `docs/scenario/frontend_token_refresh_lifecycle.md` - Added reusable `requestWithAuth` and `readJsonOrThrow` helpers
- FR-3: Protected-route and logout behavior - `docs/scenario/frontend_unauthorized_session_handling.md` - Unified unauthorized handling via runtime callback

All tests still pass after refactoring. Scenario documents updated.
