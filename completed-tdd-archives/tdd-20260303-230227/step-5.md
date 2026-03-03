# Step 5 - Refactor for Maintainability

## Refactorings Completed

- FR-1: Build deterministic parsing and indexing pipeline - `docs/scenario/parsing_pipeline_lifecycle.md` - Extracted chunking/embedding helpers and deterministic upsert helpers in indexing task module.
- FR-2: Provide secure hybrid retrieval with deterministic RRF - `docs/scenario/hybrid_rrf_permission_retrieval.md` - Isolated permission predicate builder to keep SQL assembly explicit and testable.

All tests still pass after refactoring. Scenario documents updated.
