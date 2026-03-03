# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Provider Router Retries Then Fails Over
The AI provider router must retry a provider request up to three attempts when failures are retryable (timeout, HTTP 429, or HTTP 5xx). If all attempts fail for a provider, routing must fail over to the next provider.

### FR-2: Outbound Payload Is Sanitized
Outbound provider payloads must contain only sanitized text snippets and safe context metadata. Full file content and user-identifying metadata must never be included.

### FR-3: SSE Chat Streams Chunks With Citations
The chat endpoint must stream Server-Sent Events (SSE) chunks and each chunk payload must include citation fields.

### FR-4: Public Query Exact-Match Cache Path
Public query answers must support an exact-match cache path so repeated identical public queries return cached responses.

## Assumptions

- "Retry up to three times" is implemented as three attempts per provider (initial attempt plus two retries) before failover.
- "User identifiers" means user-related metadata fields such as `user_id`, `owner_id`, `email`, `username`, and tokens; document identifiers like `upload_id` and `chunk_index` are allowed for citations.
- Skill routing is represented as deterministic server-side selection of a `skill` label included in outbound payload.
