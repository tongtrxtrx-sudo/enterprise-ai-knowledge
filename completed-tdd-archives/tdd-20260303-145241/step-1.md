# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Validate upload input safety before persistence
Reject uploads when file size is greater than 10 MB, filename is unsafe, or file content starts with an executable signature.

### FR-2: Enforce checksum deduplication and filename versioning
For the same folder, uploading a file with an identical checksum must return HTTP 409. Uploading same filename with a different checksum must create a new version.

### FR-3: Persist upload metadata with async parse initialization
Successful uploads must persist deterministic object layout metadata and set initial `parse_status` to `processing` while triggering a parse task asynchronously.

## Assumptions

- Unsafe filename means path traversal markers (`..`), path separators (`/`, `\\`), leading dot, or characters outside `[A-Za-z0-9._-]`.
- Executable signatures are identified using common magic numbers (`MZ`, ELF, Mach-O) at file start.
- Upload API uses multipart form fields: `folder`, `filename`, and `file`.
