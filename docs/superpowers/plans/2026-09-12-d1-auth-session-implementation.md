# Implementation Plan — Task 2: Auth and Session Lifecycle for the Shared Transport

Date: 2026-09-12  
Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`  
Branch: `antigravity/assessment-v2-continuation`  
Base: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`

---

## 1. Goal & Context

Harden the shared transport (`LinguaLensClient` used by both TUI and GUI) with robust session and auth lifecycle management aligned with `docs/SUPABASE_AUTH_CONTRACT.md` and `apps/api/app/auth/`:
1. **Bearer Token Injection & Origin Scoping**: Bearer tokens are sent only to the configured API origin (`base_url`). No tokens are forwarded across cross-origin redirects.
2. **Session Invalidation on 401**: HTTP 401 immediately invalidates the active session token; stale tokens must never be resent. Late 401 responses from past requests must not wipe newly established sessions (token generation / identity check).
3. **Permission Denial on 403**: HTTP 403 indicates permission denial and does *not* clear the active session.
4. **Conflict Handling on 409**: HTTP 409 raises `LinguaLensConflictError` indicating state conflict requiring reload/reconciliation.
5. **Safe Rate Limit on 429**: Parse `Retry-After` header safely (handling missing, integer, or invalid values) without auto-retrying non-idempotent clinical writes (`POST`, `PUT`, `PATCH`, `DELETE`).
6. **No Mutation Replay**: Write operations must never be automatically retried upon timeout, network drop, or token refresh because the server may have already committed the mutation.
7. **GUI / TUI Recovery Awareness**: GUI and TUI recognize auth failures and prompt for re-authentication without false success or local mock fallback.
8. **Synthetic Credentials Only**: Use only synthetic test tokens; zero real secrets in tests, fixtures, logs, or code.

---

## 2. Architecture & File Inventory

### Production Code to Modify
1. `packages/tui/client.py`:
   - Add `ClientSession` dataclass / container holding `access_token`, `organization_id`, `token_id`, `created_at`.
   - Add `set_session(access_token, organization_id=None)` and `clear_session()`.
   - Add `get_session() -> ClientSession | None`.
   - In `_http_request`:
     - Validate that request URL origin matches configured `base_url` origin before adding `Authorization: Bearer <token>`.
     - Intercept cross-origin redirects using a custom `urllib.request.HTTPRedirectHandler` to strip `Authorization` if target origin differs from `base_url`.
     - On HTTP 401: If active session token matches the token used in the failed request, invalidate the session. If session was already replaced by a newer token, preserve the new session.
     - On HTTP 429: Parse `Retry-After` header safely from response headers and attach `retry_after_seconds` to `LinguaLensRateLimitError`.
     - Strict mutation safety: No automatic retry on `POST`, `PUT`, `PATCH`, `DELETE`.
2. `packages/tui/workflow.py`:
   - In `start()` main loop, catch `LinguaLensAuthError` specifically and prompt therapist with clear re-authentication guidance.
3. `packages/gui/app.py`:
   - When `LinguaLensAuthError` occurs in background tasks or sync actions, update status bar to `⚠️ Authentication Required: Session expired. Please re-login.` and present an auth error modal.

### Test Files to Extend
1. `tests/test_tui_transport.py`:
   - `test_transport_bearer_token_propagation_to_origin`: Verifies `Authorization: Bearer <token>` is sent to configured base_url.
   - `test_transport_cross_origin_redirect_strips_credentials`: Verifies that a redirect from `127.0.0.1:portA` to `127.0.0.1:portB` strips the `Authorization` header.
   - `test_transport_401_invalidates_session_and_prevents_replay`: Verifies session is cleared upon 401, subsequent requests do not send the expired token.
   - `test_transport_late_401_does_not_clear_new_session`: Verifies a delayed 401 from token A does not clear active token B.
   - `test_transport_403_does_not_clear_session`: Verifies active session is preserved on permission denial.
   - `test_transport_429_parses_retry_after_safely`: Verifies integer seconds and malformed/missing headers are handled safely.
   - `test_transport_mutations_never_auto_retried`: Verifies POST/PUT/PATCH/DELETE fail closed without retrying.
2. `tests/test_tui.py`:
   - `test_workflow_runner_handles_auth_error_with_reauth_guidance`: Verifies TUI handles 401 with sign-in guidance.
3. `tests/test_gui.py`:
   - `test_gui_handles_auth_error_cleanly`: Verifies GUI updates status bar to auth required state.

---

## 3. TDD Cycle & Observable Seams

### Step 1: RED (Test-First)
1. Add the 7 new transport tests in `tests/test_tui_transport.py`.
2. Add TUI auth error test in `tests/test_tui.py`.
3. Add GUI auth error test in `tests/test_gui.py`.
4. Run:
   ```bash
   PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui_transport.py tests/test_tui.py tests/test_gui.py -k "bearer or redirect or invalidates or late_401 or retry_after or reauth" -v
   ```
5. Observe expected RED failures and capture failure log to `.local/verification/antigravity-d1/red_task2_auth_session.log`.

### Step 2: Minimal GREEN Implementation
1. Implement `ClientSession`, `set_session`, `clear_session`, `get_session` on `LinguaLensClient`.
2. Implement origin verification and redirect credential stripping in `_http_request`.
3. Implement token identity checking on 401 to prevent stale session wipes.
4. Implement safe `Retry-After` header parsing on 429.
5. Update TUI and GUI error handlers.
6. Run tests to GREEN:
   ```bash
   PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui_transport.py tests/test_tui.py tests/test_gui.py -v
   ```

### Step 3: Refactor & Regression Gate
1. Verify no code duplication, verify py_compile, verify git diff whitespace.
2. Run complete test suites:
   - Client tests: `pytest tests/test_tui.py tests/test_tui_transport.py tests/test_gui.py -v`
   - Backend Assessment V2 tests: `pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q`
3. Save receipts and compute SHA-256 hashes.

---

## 4. Assurance & Security Constraints
- **Zero Real Credentials**: Only synthetic tokens (`test-token-uuid-1`, `test-token-uuid-2`).
- **No New Grant System**: No fake login/refresh server endpoints are invented. Existing backend auth contracts are respected; sessions are injected cleanly.
- **A2 Assurance Boundary**: Common git directory ledger `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md` remains untouched (`parent-completed`, budget 3/3 exhausted).
- **Independent Review Capability**: Because external automated reviewer capability for auth/session is bounded by repository policy, record independent review status as pending with transparent audit log.
