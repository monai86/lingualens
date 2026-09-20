# Implementation Plan — Task 1: Finish D1 Failure Boundary

## 1. Goal and Overview
Ensure that when `mock_mode=False` (live client), all operations either use verified remote API communication or fail closed with explicit, sanitized generic errors. Under no circumstances may a live operation fall back to local mock data, modify local mock data, or fabricate success. Explicit local mode (`mock_mode=True`) is preserved for demo and research utilities.

## 2. Operation Inventory and Failure Boundary Matrix

| Client Operation | Current Behavior in Live Mode (`mock_mode=False`) | Target Behavior in Live Mode |
|---|---|---|
| `list_cases()` | HTTP `GET /cases` | HTTP `GET /cases`; raises `LinguaLensApiError` on HTTP failure or malformed JSON |
| `create_case(...)` | HTTP `POST /cases` | HTTP `POST /cases`; raises `LinguaLensApiError` on failure |
| `list_sessions(case_id)` | HTTP `GET /cases/{case_id}/sessions` | HTTP `GET /cases/{case_id}/sessions`; raises `LinguaLensApiError` on failure |
| `create_session(...)` | HTTP `POST /cases/{case_id}/sessions` | HTTP `POST /cases/{case_id}/sessions`; raises `LinguaLensApiError` on failure |
| `get_session_transcript(session_id)` | HTTP `GET /sessions/{session_id}/transcript` | HTTP `GET /sessions/{session_id}/transcript`; raises `LinguaLensApiError` on failure |
| `ingest_transcript_text(...)` | **LOCAL ONLY**: parsed and wrote to `_mock_data` | HTTP `POST /sessions/{session_id}/transcripts/upload-cha` (or `/manual`); raises on failure |
| `ingest_audio_file(...)` | **LOCAL ONLY**: ran local pipeline or mock fallback, wrote to `_mock_data` | Raises `LinguaLensUnsupportedOperationError("Audio ingestion requires explicit local mode or backend processing queue.")` before any local audio processing or mutation |
| `update_utterance(...)` | **LOCAL ONLY**: modified `_mock_data` in place | Raises `LinguaLensUnsupportedOperationError` (or calls `PATCH /transcripts/{tr_id}` if supported); strictly NO `_mock_data` mutation |
| `auto_refine_speakers(...)` | **LOCAL ONLY**: applied local rule to `_mock_data` | Raises `LinguaLensUnsupportedOperationError` before any mutation |
| `swap_speakers(...)` | **LOCAL ONLY**: swapped in `_mock_data` | Raises `LinguaLensUnsupportedOperationError` before any mutation |
| `attest_transcript(...)` | HTTP `POST /transcripts/{tr_id}/attest` | HTTP `POST /transcripts/{tr_id}/attest`; raises on failure |
| `get_findings(session_id)` | HTTP `GET /sessions/{session_id}/features` | HTTP `GET /sessions/{session_id}/features`; raises on failure |
| `draft_report(...)` | HTTP `POST /sessions/{session_id}/reports/draft` | HTTP `POST /sessions/{session_id}/reports/draft`; raises on failure |
| `sign_off_report(...)` | HTTP `POST /reports/{report_id}/sign-off` | HTTP `POST /reports/{report_id}/sign-off`; raises on failure |
| `get_session_report(session_id)` | **MISSING**: caused TUI to read `_mock_data["reports"]` | Adds `get_session_report(session_id)` and `get_report(report_id)`; live mode calls HTTP `GET /reports/{report_id}` |

### GUI & TUI Direct `_mock_data` Elimination
- `packages/gui/app.py`: replace `cases_count = len(self.client._mock_data.get("cases", []))` with UI tree item count or client list count.
- `packages/tui/workflow.py`: replace `for r in self.client._mock_data["reports"].values()` with `client.get_session_report(self.active_session_id)` or `client.get_report(...)`.

## 3. Real Loopback Transport Test Suite (`tests/test_tui_transport.py`)
Run real HTTP requests against a `http.server.HTTPServer` on `127.0.0.1`:
1. **200 OK**: parses valid JSON response, returns dict.
2. **401 Unauthorized**: raises `LinguaLensAuthError` (subclass of `LinguaLensApiError`).
3. **403 Forbidden**: raises `LinguaLensPermissionError` (subclass of `LinguaLensApiError`).
4. **409 Conflict**: raises `LinguaLensConflictError` (subclass of `LinguaLensApiError`).
5. **429 Rate Limited**: raises `LinguaLensRateLimitError` (subclass of `LinguaLensApiError`).
6. **500 Internal Server Error**: raises `LinguaLensServerError` (subclass of `LinguaLensApiError`).
7. **Malformed JSON (200 with invalid syntax)**: raises `LinguaLensApiError` without returning fabricated empty dict.
8. **Missing required fields / unparseable body**: raises `LinguaLensApiError`.
9. **Server Unavailable (connection refused / timeout)**: raises `LinguaLensApiError`.
10. **Sanitization assertion**: Error messages must omit raw query URLs, full request payloads, auth tokens, file paths, and child identifiers.

## 4. Parameterized Failure Regression & State Immutability (`tests/test_tui.py`)
- Refactor `test_live_api_errors_never_fall_back_to_local_mock_state` to use `@pytest.mark.parametrize` for each operation:
  - `list_cases`, `create_case`
  - `list_sessions`, `create_session`
  - `get_session_transcript`, `ingest_transcript_text`, `ingest_audio_file`
  - `update_utterance`, `auto_refine_speakers`, `swap_speakers`, `attest_transcript`
  - `get_findings`, `draft_report`, `sign_off_report`, `get_session_report`
- In each test, create a deep copy of `client._mock_data` before the operation.
- Verify `with pytest.raises(LinguaLensApiError): operation()`.
- Assert `client._mock_data == initial_mock_data_copy` (total state immutability across failures).

## 5. GUI & TUI Failure Presentation Tests
- Verify GUI: when API call fails during case creation, session creation, or transcript loading, GUI displays an error message (via `messagebox.showerror` or status banner) without throwing unhandled exceptions, without showing success, and without updating the treeview with fabricated records.
- Verify TUI: workflow handles client errors gracefully, displaying a sanitized red error banner rather than crashing or creating mock artifacts.

## 6. Verification Steps & Commands
1. **RED**:
   - Write `tests/test_tui_transport.py` and new parameterized failure tests in `tests/test_tui.py`.
   - Run: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui_transport.py tests/test_tui.py -q`
   - Observe expected RED failures (e.g. `ingest_audio_file`, `update_utterance`, `auto_refine_speakers`, `swap_speakers` mutating mock data or not raising).
2. **GREEN**:
   - Implement error hierarchy and live-mode guards in `packages/tui/client.py`.
   - Add `get_session_report` and `get_report` to `LinguaLensClient`.
   - Update `packages/tui/workflow.py` and `packages/gui/app.py` to remove direct `_mock_data` access.
   - Run tests to GREEN.
3. **REFACTOR & REGRESSION**:
   - Run `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui.py tests/test_tui_transport.py tests/test_gui.py -v`.
   - Check `git diff --check`.
