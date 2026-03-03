# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Compose runtime includes all v2.1 services
Create a Docker Compose scaffold that defines exactly the seven required services: nginx, frontend, backend, postgres, redis, minio, and onlyoffice.

### FR-2: Backend health contract endpoint
Expose `GET /health` from the backend application, returning HTTP 200 and a JSON payload containing `service_name` and `version` fields.

### FR-3: Environment validation on container startup
Frontend and backend containers must validate required environment variables before starting their runtime commands.

### FR-4: Runtime scaffold config artifacts
Provide a reverse proxy config and an environment schema artifact that describe/enable the runtime contract.

## Assumptions

- A minimal scaffold is acceptable; containers do not need full application logic beyond startup and health contract.
- Environment schema can be provided as `.env.example` plus machine-readable schema (`infra/env.schema.json`).
- Health endpoint response values can be static defaults for scaffold stage.
