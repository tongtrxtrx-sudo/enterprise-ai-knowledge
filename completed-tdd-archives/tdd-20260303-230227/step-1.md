# Step 1 - Understand Intent

## Functional Requirements

### FR-1: Build deterministic parsing and indexing pipeline
Upload parsing must convert source content to Markdown, split into deterministic chunks, and persist `doc_chunks` plus `index_tree` rows from asynchronous background execution.

### FR-2: Provide secure hybrid retrieval with deterministic RRF
Retrieval must combine BM25-style lexical ranking and vector ranking through SQL RRF merge while excluding unauthorized chunks through permission predicates.

## Assumptions

- MarkItDown integration may fall back to a deterministic local parser when the dependency is unavailable in test runtime.
- Vector embeddings are represented as JSON arrays so tests can execute with SQLite while preserving deterministic behavior.
