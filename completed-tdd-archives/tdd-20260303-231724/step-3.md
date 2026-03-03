# Step 3 - Write Failing Test

## Failing Tests Created

- FR-1: Edit start permission gate - `docs/scenario/edit_start_permission_gate.md` - `tests/editing/test_onlyoffice_editing.py`
- FR-2: Callback version safety and idempotency - `docs/scenario/edit_callback_version_safety.md` - `tests/editing/test_onlyoffice_editing.py`
- FR-3: Persist new version and trigger immediate reindex - `docs/scenario/edit_callback_persist_and_reindex.md` - `tests/editing/test_onlyoffice_editing.py`

Initial RED run:

- Command: `uv run --group dev pytest tests/editing/test_onlyoffice_editing.py -q`
- Result: failed as expected before implementation (`department` field and editing models/endpoints not implemented)
