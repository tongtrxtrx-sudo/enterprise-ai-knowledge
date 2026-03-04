# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Chinese-first locale infrastructure
Introduce a reusable i18n layer in the frontend with locale resource files for `zh-CN` and `en`, and default locale behavior set to Chinese.

### FR-2: Replace primary workflow hardcoded copy
Replace hardcoded UI copy in chat, files, admin, and shared/auth shell pages with localized resource lookups so Chinese is rendered by default.

### FR-3: Locale switch and verification
Provide a visible locale switch so users can switch to English, and add tests verifying default Chinese rendering plus runtime locale switching behavior.

## Assumptions

- "Major pages" covers login, app shell, chat, files, admin, forbidden page, and auth guard loading text.
- "Optional English switch" is implemented as a UI language selector in the app shell and persisted in local storage.
- "No major hardcoded English strings" is interpreted as removing user-facing static English copy from primary workflows, while API data values may still come from backend and can be translated when known.
