"""Loopback HTTP transport tests for LinguaLens client."""

from __future__ import annotations

import http.server
import json
import socket
import threading
from typing import Generator
import pytest

from packages.tui.client import (
    LinguaLensClient,
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensPermissionError,
    LinguaLensConflictError,
    LinguaLensRateLimitError,
    LinguaLensServerError,
)


class MockServerHandler(http.server.BaseHTTPRequestHandler):
    status_to_return = 200
    body_to_return = b'{"status": "ok"}'
    headers_to_return = [("Content-Type", "application/json")]
    request_log = []

    def do_GET(self):
        MockServerHandler.request_log.append({"method": "GET", "path": self.path, "headers": dict(self.headers)})
        self._send_response()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        MockServerHandler.request_log.append({"method": "POST", "path": self.path, "body": body, "headers": dict(self.headers)})
        self._send_response()

    def _send_response(self):
        self.send_response(MockServerHandler.status_to_return)
        for h, v in MockServerHandler.headers_to_return:
            self.send_header(h, v)
        self.end_headers()
        self.wfile.write(MockServerHandler.body_to_return)

    def log_message(self, format, *args):
        # Silence standard HTTP request logging in test runs
        pass


@pytest.fixture
def mock_server() -> Generator[tuple[str, type[MockServerHandler]], None, None]:
    MockServerHandler.status_to_return = 200
    MockServerHandler.body_to_return = b'{"status": "ok"}'
    MockServerHandler.headers_to_return = [("Content-Type", "application/json")]
    MockServerHandler.request_log = []

    # Find free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = http.server.HTTPServer(("127.0.0.1", port), MockServerHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    try:
        yield base_url, MockServerHandler
    finally:
        server.shutdown()
        server.server_close()


def test_transport_200_success(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 200
    handler.body_to_return = json.dumps([{"case_id": "case-001", "child_id": "C-101"}]).encode("utf-8")

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    cases = client.list_cases()
    assert len(cases) == 1
    assert cases[0]["case_id"] == "case-001"
    assert len(handler.request_log) == 1
    assert handler.request_log[0]["path"] == "/cases"


def test_transport_401_auth_error(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 401
    handler.body_to_return = b'{"detail": "Session expired or invalid token"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensAuthError) as exc_info:
        client.list_cases()
    assert "Authentication" in str(exc_info.value) or "401" in str(exc_info.value) or "Session expired" in str(exc_info.value)


def test_transport_403_permission_error(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 403
    handler.body_to_return = b'{"detail": "Permission denied"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensPermissionError) as exc_info:
        client.list_cases()
    assert "Permission" in str(exc_info.value) or "403" in str(exc_info.value) or "denied" in str(exc_info.value)


def test_transport_409_conflict_error(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 409
    handler.body_to_return = b'{"detail": "Version conflict"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensConflictError) as exc_info:
        client.create_case(child_code="C-001", age_months=48)
    assert "Conflict" in str(exc_info.value) or "409" in str(exc_info.value) or "conflict" in str(exc_info.value)


def test_transport_429_rate_limit_error(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 429
    handler.body_to_return = b'{"detail": "Too many requests"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensRateLimitError) as exc_info:
        client.list_cases()
    assert "Rate limit" in str(exc_info.value) or "429" in str(exc_info.value) or "Too many requests" in str(exc_info.value)


def test_transport_500_server_error(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 500
    handler.body_to_return = b'{"detail": "Internal database error"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensServerError) as exc_info:
        client.list_cases()
    assert "Server error" in str(exc_info.value) or "500" in str(exc_info.value) or "failed" in str(exc_info.value)


def test_transport_malformed_json(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 200
    handler.body_to_return = b"<!DOCTYPE html><html><body>Error 502 Bad Gateway</body></html>"

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.list_cases()
    assert "JSON" in str(exc_info.value) or "decode" in str(exc_info.value) or "malformed" in str(exc_info.value) or "API request failed" in str(exc_info.value)


def test_transport_server_unavailable():
    # Pick a port guaranteed not to be running
    client = LinguaLensClient(base_url="http://127.0.0.1:59999", mock_mode=False)
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.list_cases()
    assert "failed" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()


def test_transport_sanitization(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 400
    handler.body_to_return = b'{"detail": "Invalid request"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    secret_token = "secret-token-xyz-123"
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.create_case("CHILD-SECRET-NAME-456", 48, notes=f"Private: {secret_token}")
    err_msg = str(exc_info.value)
    # The error message presented to caller should never expose clinical identifiers or secrets
    assert secret_token not in err_msg
    assert "CHILD-SECRET-NAME-456" not in err_msg


def test_list_sessions_raises_api_error_on_malformed_timeline_response(mock_server):
    base_url, handler = mock_server
    handler.status_to_return = 200
    handler.body_to_return = b'{"case_id": "C-001", "child_id": "child-1"}'  # dict instead of timeline event list

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.list_sessions("C-001")
    assert "malformed" in str(exc_info.value).lower() or "timeline" in str(exc_info.value).lower()


def test_transport_exception_chaining_sanitized_no_underlying_url_leak(mock_server):
    import traceback
    base_url, handler = mock_server
    handler.status_to_return = 401
    handler.body_to_return = b'{"detail": "Unauthorized"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensAuthError) as exc_info:
        client.list_cases()
    exc = exc_info.value
    # Ensure chained cause is None to prevent raw urllib HTTPError/URLError url/header leaks
    assert exc.__cause__ is None
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert "HTTP Error 401" not in tb


def test_transport_bearer_token_propagation_to_origin(mock_server):
    """Verify that configured bearer token is sent via Authorization header to base_url origin."""
    base_url, handler = mock_server
    handler.status_to_return = 200
    handler.body_to_return = b"[]"

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    client.set_session(access_token="synthetic-jwt-xyz", organization_id="org-clinic-1")
    client.list_cases()

    last_req = handler.request_log[-1]
    auth_header = last_req["headers"].get("Authorization")
    assert auth_header == "Bearer synthetic-jwt-xyz"


def test_transport_cross_origin_redirect_strips_credentials():
    """Verify that HTTP redirects across different origins or ports strip the Authorization header."""
    class RedirectHandlerA(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # 302 redirect to server B
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{port_b}/redirected")
            self.end_headers()
        def log_message(self, format, *args):
            pass

    server_b_logs = []
    class HandlerB(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            server_b_logs.append({"headers": dict(self.headers)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")
        def log_message(self, format, *args):
            pass

    # Start Server B
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port_b = s.getsockname()[1]
    server_b = http.server.HTTPServer(("127.0.0.1", port_b), HandlerB)
    threading.Thread(target=server_b.serve_forever, daemon=True).start()

    # Start Server A
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port_a = s.getsockname()[1]
    server_a = http.server.HTTPServer(("127.0.0.1", port_a), RedirectHandlerA)
    threading.Thread(target=server_a.serve_forever, daemon=True).start()

    try:
        client = LinguaLensClient(base_url=f"http://127.0.0.1:{port_a}", mock_mode=False)
        client.set_session(access_token="secret-token-do-not-forward")
        client.list_cases()

        assert len(server_b_logs) == 1
        headers_at_b = {k.lower(): v for k, v in server_b_logs[0]["headers"].items()}
        assert "authorization" not in headers_at_b
    finally:
        server_a.shutdown()
        server_a.server_close()
        server_b.shutdown()
        server_b.server_close()


def test_transport_401_invalidates_session_and_prevents_replay(mock_server):
    """Verify HTTP 401 clears active session token immediately and does not send it on subsequent calls."""
    base_url, handler = mock_server
    handler.status_to_return = 401
    handler.body_to_return = b'{"detail": "Session expired"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    client.set_session(access_token="token-expired-123")

    with pytest.raises(LinguaLensAuthError):
        client.list_cases()

    # Active session should be invalidated immediately
    assert client.get_session() is None

    # Subsequent request with 200 should NOT send the stale token
    handler.status_to_return = 200
    handler.body_to_return = b"[]"
    client.list_cases()
    last_req = handler.request_log[-1]
    headers_lower = {k.lower(): v for k, v in last_req["headers"].items()}
    assert "authorization" not in headers_lower


def test_transport_late_401_does_not_clear_new_session(mock_server):
    """Verify that a race condition or delayed 401 with old token does not wipe a newly set session."""
    base_url, handler = mock_server
    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    client.set_session(access_token="token-old-1")

    # Simulate token replacement happening before/during 401 response handling
    old_session = client.get_session()
    client.set_session(access_token="token-new-2")

    # Notify transport of late 401 for old session token
    client._handle_auth_failure(token_used="token-old-1")

    # Active session must remain token-new-2
    assert client.get_session() is not None
    assert client.get_session().access_token == "token-new-2"


def test_transport_403_does_not_clear_session(mock_server):
    """Verify HTTP 403 (forbidden / permission denied) preserves the active session."""
    base_url, handler = mock_server
    handler.status_to_return = 403
    handler.body_to_return = b'{"detail": "Permission denied"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    client.set_session(access_token="valid-therapist-token")

    with pytest.raises(LinguaLensPermissionError):
        client.list_cases()

    # Session must NOT be cleared on 403
    assert client.get_session() is not None
    assert client.get_session().access_token == "valid-therapist-token"


def test_transport_429_parses_retry_after_safely(mock_server):
    """Verify HTTP 429 parses Retry-After header safely for integer seconds and malformed strings."""
    base_url, handler = mock_server
    handler.status_to_return = 429
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", "25")]
    handler.body_to_return = b'{"detail": "Too many requests"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensRateLimitError) as exc_info:
        client.list_cases()
    assert exc_info.value.retry_after_seconds == 25

    # Test malformed Retry-After header
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", "invalid-seconds")]
    with pytest.raises(LinguaLensRateLimitError) as exc_info2:
        client.list_cases()
    assert exc_info2.value.retry_after_seconds is None


def test_transport_mutations_never_auto_retried(mock_server):
    """Verify that clinical mutations (POST) are never replayed upon network or 500 failure."""
    base_url, handler = mock_server
    handler.status_to_return = 500
    handler.body_to_return = b'{"detail": "Server error"}'

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    req_count_before = len(handler.request_log)

    with pytest.raises(LinguaLensServerError):
        client.create_case(child_code="C-099", age_months=42)

    # Strictly 1 attempt, zero automatic retry on mutation
    assert len(handler.request_log) == req_count_before + 1


def test_transport_retry_after_http_date_and_edge_cases(mock_server, monkeypatch):
    """Verify HTTP 429 parses RFC HTTP-date strings, past dates, negative values, and abnormal numbers deterministically."""
    from datetime import datetime, timezone, timedelta
    import email.utils

    base_url, handler = mock_server
    handler.status_to_return = 429

    # Deterministic clock
    fixed_now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Future HTTP date (+45 seconds)
    future_date = fixed_now + timedelta(seconds=45)
    future_http_str = email.utils.format_datetime(future_date)
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", future_http_str)]

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    # Monkeypatch now_fn or clock inside client
    monkeypatch.setattr("packages.tui.client._get_current_utc_time", lambda: fixed_now, raising=False)

    with pytest.raises(LinguaLensRateLimitError) as exc_info:
        client.list_cases()
    assert exc_info.value.retry_after_seconds == pytest.approx(45.0, abs=1.0)

    # 2. Past HTTP date (-30 seconds) -> must normalize to 0.0, never negative
    past_date = fixed_now - timedelta(seconds=30)
    past_http_str = email.utils.format_datetime(past_date)
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", past_http_str)]

    with pytest.raises(LinguaLensRateLimitError) as exc_info_past:
        client.list_cases()
    assert exc_info_past.value.retry_after_seconds == 0.0

    # 3. Negative delta-seconds -> must normalize to 0.0
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", "-15")]
    with pytest.raises(LinguaLensRateLimitError) as exc_info_neg:
        client.list_cases()
    assert exc_info_neg.value.retry_after_seconds == 0.0

    # 4. Abnormal value (e.g. NaN or excessive numbers) -> None or capped safely
    handler.headers_to_return = [("Content-Type", "application/json"), ("Retry-After", "NaN")]
    with pytest.raises(LinguaLensRateLimitError) as exc_info_nan:
        client.list_cases()
    assert exc_info_nan.value.retry_after_seconds is None


def test_transport_session_generation_same_token_race(mock_server):
    """Verify that late 401 does not clear session even if token string is identical, due to generation tracking."""
    base_url, handler = mock_server
    client = LinguaLensClient(base_url=base_url, mock_mode=False)

    client.set_session(access_token="shared-token-val")
    first_session = client.get_session()
    assert first_session is not None
    assert first_session.generation == 1

    # User re-authenticates with identical token string but new generation
    client.set_session(access_token="shared-token-val")
    second_session = client.get_session()
    assert second_session is not None
    assert second_session.generation == 2

    # Late 401 from first session dispatch arrives
    client._handle_auth_failure(failed_session_generation=1)

    # Session generation 2 must NOT be cleared
    assert client.get_session() is not None
    assert client.get_session().generation == 2


def test_transport_concurrent_session_barrier_late_401(mock_server):
    """Verify thread-safe compare-and-clear using barriers without sleeps."""
    base_url, handler = mock_server
    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    client.set_session(access_token="session-1")

    barrier1 = threading.Barrier(2)
    barrier2 = threading.Barrier(2)
    worker_err = []

    def worker_old_request():
        try:
            # Captures gen 1
            gen = getattr(client.get_session(), "generation", 1)
            barrier1.wait(timeout=2.0)  # Wait for main thread to replace session
            barrier2.wait(timeout=2.0)  # Wait before calling compare-and-clear
            client._handle_auth_failure(failed_session_generation=gen)
        except Exception as exc:
            worker_err.append(exc)
            try:
                barrier1.abort()
                barrier2.abort()
            except Exception:
                pass

    t = threading.Thread(target=worker_old_request)
    t.start()

    try:
        barrier1.wait(timeout=2.0)  # Worker captured gen 1, now replace session
        client.set_session(access_token="session-2")
        assert getattr(client.get_session(), "generation", 0) == 2
        barrier2.wait(timeout=2.0)  # Let worker execute _handle_auth_failure
    finally:
        t.join(timeout=2.0)

    assert not worker_err, f"Worker thread encountered: {worker_err}"
    # Active session must remain session-2
    assert client.get_session() is not None
    assert client.get_session().access_token == "session-2"
    assert client.get_session().generation == 2


def test_transport_cross_origin_redirect_strips_organization_context():
    """Verify that HTTP redirects across origins strip both Authorization and X-Organization-ID."""
    class RedirectHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{dest_port}/landed")
            self.end_headers()
        def log_message(self, *args):
            pass

    dest_logs = []
    class DestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            dest_logs.append(dict(self.headers))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")
        def log_message(self, *args):
            pass

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dest_port = s.getsockname()[1]
    dest_srv = http.server.HTTPServer(("127.0.0.1", dest_port), DestHandler)
    threading.Thread(target=dest_srv.serve_forever, daemon=True).start()

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        orig_port = s.getsockname()[1]
    orig_srv = http.server.HTTPServer(("127.0.0.1", orig_port), RedirectHandler)
    threading.Thread(target=orig_srv.serve_forever, daemon=True).start()

    try:
        client = LinguaLensClient(base_url=f"http://127.0.0.1:{orig_port}", mock_mode=False)
        client.set_session(access_token="secret-tok", organization_id="org-private")
        client.list_cases()

        assert len(dest_logs) == 1
        headers_at_dest = {k.lower(): v for k, v in dest_logs[0].items()}
        assert "authorization" not in headers_at_dest
        assert "x-organization-id" not in headers_at_dest
    finally:
        orig_srv.shutdown()
        orig_srv.server_close()
        dest_srv.shutdown()
        dest_srv.server_close()


def test_transport_mutation_redirect_rejected_no_silent_replay():
    """Verify that clinical mutations (POST) encountering a redirect are rejected rather than converted to GET or replayed."""
    class PostRedirectHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(302)
            self.send_header("Location", "/new-target")
            self.end_headers()
        def log_message(self, *args):
            pass

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = http.server.HTTPServer(("127.0.0.1", port), PostRedirectHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    try:
        client = LinguaLensClient(base_url=f"http://127.0.0.1:{port}", mock_mode=False)
        with pytest.raises(LinguaLensApiError) as exc_info:
            client.create_case(child_code="C-MUT-01", age_months=60)
        assert "redirect" in str(exc_info.value).lower() or "mutation" in str(exc_info.value).lower()
    finally:
        srv.shutdown()
        srv.server_close()


def test_client_session_repr_masks_token():
    """Verify that ClientSession repr and str mask sensitive access tokens."""
    from packages.tui.client import ClientSession
    session = ClientSession(access_token="super-secret-token-xyz-987654321", organization_id="org-123")
    repr_str = repr(session)
    str_str = str(session)

    assert "super-secret-token-xyz-987654321" not in repr_str
    assert "super-secret-token-xyz-987654321" not in str_str
    assert "org-123" in repr_str


def test_transport_v2_create_child_and_get_child(mock_server):
    """Verify Stage 1 V2 create_child and get_child transport contract."""
    base_url, handler = mock_server

    child_payload = {
        "id": "child_001",
        "display_code": "LL-001",
        "birth_year": 2021,
        "birth_month": 5,
        "language_context": {"primary": "th", "additional": []},
        "version": 1,
    }
    handler.status_to_return = 201
    handler.body_to_return = json.dumps(child_payload).encode("utf-8")
    handler.request_log.clear()

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    created = client.create_child(
        display_code="LL-001",
        birth_year=2021,
        birth_month=5,
        language_context={"primary": "th", "additional": []},
    )

    assert created["id"] == "child_001"
    assert created["display_code"] == "LL-001"
    assert len(handler.request_log) == 1
    req = handler.request_log[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/v2/children"
    sent_body = json.loads(req["body"].decode("utf-8"))
    assert sent_body["display_code"] == "LL-001"
    assert sent_body["birth_year"] == 2021
    assert sent_body["birth_month"] == 5

    # Test get_child
    handler.status_to_return = 200
    handler.body_to_return = json.dumps(child_payload).encode("utf-8")
    handler.request_log.clear()

    fetched = client.get_child("child_001")
    assert fetched["id"] == "child_001"
    assert len(handler.request_log) == 1
    assert handler.request_log[0]["method"] == "GET"
    assert handler.request_log[0]["path"] == "/api/v2/children/child_001"


def test_transport_v2_record_and_list_consents(mock_server):
    """Verify Stage 1 V2 record_consent and list_consents transport contract."""
    base_url, handler = mock_server

    consent_payload = {
        "id": "consent_001",
        "child_id": "child_001",
        "purpose": "clinical_assessment",
        "scope_version": "2026.1",
        "status": "active",
        "granted_at": "2026-09-12T10:00:00Z",
        "withdrawn_at": None,
        "version": 1,
    }
    handler.status_to_return = 201
    handler.body_to_return = json.dumps(consent_payload).encode("utf-8")
    handler.request_log.clear()

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    created = client.record_consent(
        child_id="child_001",
        purpose="clinical_assessment",
        scope_version="2026.1",
        status="active",
    )

    assert created["id"] == "consent_001"
    assert created["status"] == "active"
    assert len(handler.request_log) == 1
    req = handler.request_log[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/v2/children/child_001/consents"

    # Test list_consents
    handler.status_to_return = 200
    handler.body_to_return = json.dumps([consent_payload]).encode("utf-8")
    handler.request_log.clear()

    consents = client.list_consents("child_001")
    assert len(consents) == 1
    assert consents[0]["id"] == "consent_001"

    # Test get_active_consent
    active = client.get_active_consent("child_001")
    assert active is not None
    assert active["id"] == "consent_001"


def test_transport_v2_create_assessment_without_consent_raises_conflict(mock_server):
    """Verify that backend 409 active_consent_required raises LinguaLensConflictError."""
    base_url, handler = mock_server

    handler.status_to_return = 409
    handler.body_to_return = json.dumps({
        "error": {
            "code": "active_consent_required",
            "message": "Active clinical-assessment consent is required.",
            "details": {},
            "correlation_id": "corr-123",
        }
    }).encode("utf-8")

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensConflictError):
        client.create_assessment("child_001", purpose="initial")


def test_transport_v2_create_and_list_assessments(mock_server):
    """Verify Stage 1 V2 create_assessment and list_assessments transport contract."""
    base_url, handler = mock_server

    assessment_payload = {
        "id": "asmt_001",
        "child_id": "child_001",
        "purpose": "initial",
        "state": "draft",
        "age_months": 52,
        "language_context": {"primary": "th", "additional": []},
        "assigned_clinician_id": "slp_01",
        "version": 1,
    }
    handler.status_to_return = 201
    handler.body_to_return = json.dumps(assessment_payload).encode("utf-8")
    handler.request_log.clear()

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    created = client.create_assessment(
        child_id="child_001",
        purpose="initial",
        assigned_clinician_id="slp_01",
    )

    assert created["id"] == "asmt_001"
    assert created["purpose"] == "initial"
    assert len(handler.request_log) == 1
    req = handler.request_log[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/v2/children/child_001/assessments"

    # Test list_assessments
    handler.status_to_return = 200
    handler.body_to_return = json.dumps([assessment_payload]).encode("utf-8")
    handler.request_log.clear()

    assessments = client.list_assessments("child_001")
    assert len(assessments) == 1
    assert assessments[0]["id"] == "asmt_001"


def test_transport_v2_get_assessment_detail(mock_server):
    """Verify get_assessment detail route GET /api/v2/assessments/{id} and 404 semantics."""
    base_url, handler = mock_server

    assessment_payload = {
        "id": "asmt_001",
        "child_id": "child_001",
        "purpose": "initial",
        "state": "draft",
        "age_months": 52,
        "language_context": {"primary": "th", "additional": []},
        "assigned_clinician_id": "slp_01",
        "version": 1,
    }
    handler.status_to_return = 200
    handler.body_to_return = json.dumps(assessment_payload).encode("utf-8")
    handler.request_log.clear()

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    detail = client.get_assessment("asmt_001")

    assert detail["id"] == "asmt_001"
    assert detail["child_id"] == "child_001"
    assert len(handler.request_log) == 1
    req = handler.request_log[0]
    assert req["method"] == "GET"
    assert req["path"] == "/api/v2/assessments/asmt_001"

    # Test 404 not found
    handler.status_to_return = 404
    handler.body_to_return = json.dumps({
        "error": {
            "code": "assessment_not_found",
            "message": "Assessment was not found.",
            "details": {},
            "correlation_id": "corr-404",
        }
    }).encode("utf-8")

    with pytest.raises(LinguaLensApiError) as exc_info:
        client.get_assessment("asmt_nonexistent")
    assert "404" in str(exc_info.value)




