# Step 4 - Implement to Make Tests Pass

## Implementations Completed

- FR-1: Login and session bootstrap from backend auth - `docs/scenario/frontend_login_ui_and_guard.md` - Implementation in `frontend/src/lib/state/sessionStore.tsx`, `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/app/router.tsx`
- FR-2: Token persistence and refresh lifecycle - `docs/scenario/frontend_token_refresh_lifecycle.md` - Implementation in `frontend/src/lib/http/client.ts`, `frontend/src/lib/state/sessionStore.tsx`
- FR-3: Protected-route and logout behavior - `docs/scenario/frontend_unauthorized_session_handling.md` - Implementation in `frontend/src/app/router.tsx`, `frontend/src/app/shell/AppShell.tsx`, `frontend/src/lib/http/client.ts`

All tests now pass. Scenario documents updated.
