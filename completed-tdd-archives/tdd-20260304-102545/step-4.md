# Step 4 - Implement to Make Tests Pass

## Implementations Completed

- FR-1: Chinese-first locale infrastructure - `docs/scenario/chinese_first_i18n_infrastructure.md` - Implemented in `frontend/src/i18n/index.tsx`, `frontend/src/i18n/locales/zh-CN.ts`, `frontend/src/i18n/locales/en.ts`, `frontend/src/main.tsx`, `frontend/src/test/utils.tsx`
- FR-2: Replace primary workflow hardcoded copy - `docs/scenario/chinese_first_primary_workflow_copy.md` - Implemented in `frontend/src/features/chat/ChatPage.tsx`, `frontend/src/features/files/FileManagerPage.tsx`, `frontend/src/features/admin/AdminPage.tsx`, `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/features/common/ForbiddenPage.tsx`, `frontend/src/components/OnlyOfficeEditor.tsx`, `frontend/src/app/router.tsx`
- FR-3: Locale switch and verification - `docs/scenario/chinese_first_locale_switch.md` - Implemented in `frontend/src/app/shell/AppShell.tsx` with persisted locale selector and translated navigation labels

All tests now pass. Scenario documents updated.
