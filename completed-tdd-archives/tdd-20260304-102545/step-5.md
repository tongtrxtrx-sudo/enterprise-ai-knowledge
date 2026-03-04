# Step 5 - Refactor for Maintainability

## Refactorings Completed

- FR-1: Chinese-first locale infrastructure - `docs/scenario/chinese_first_i18n_infrastructure.md` - Centralized locale persistence and message formatting in `frontend/src/i18n/index.tsx` to avoid duplicated translation logic in components
- FR-2: Replace primary workflow hardcoded copy - `docs/scenario/chinese_first_primary_workflow_copy.md` - Replaced repeated literal status text branches with translation key mapping in chat/files/admin pages
- FR-3: Locale switch and verification - `docs/scenario/chinese_first_locale_switch.md` - Unified route test rendering through `I18nProvider` in `frontend/src/test/utils.tsx` and aligned related component tests

All tests still pass after refactoring. Scenario documents updated.
