# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Login and session bootstrap from backend auth
Frontend must provide a real login page, call backend auth endpoints, and bootstrap user session state from backend response data.

### FR-2: Token persistence and refresh lifecycle
Frontend must persist access token, recover from expired access token using refresh flow, and keep authenticated requests working after refresh.

### FR-3: Protected-route and logout behavior
Protected pages must require authenticated session; invalid sessions must redirect to login and support recovery via refresh or manual re-login.

## Assumptions

- Existing backend `/auth/login`, `/auth/refresh`, and `/auth/logout` contracts are source of truth.
- Frontend permissions can be derived from backend session payload rather than hardcoded demo defaults.
