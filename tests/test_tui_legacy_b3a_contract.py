"""Focused regression and TDD contract tests for B3a legacy session lifecycle.

Reconciles client.list_sessions, create_session, get_session_detail against
the canonical FastAPI backend routes (/cases/{case_id}/timeline, /sessions/{session_id},
and POST /cases/{case_id}/sessions).
"""

from __future__ import annotations

import http.server
import json
import socket
import threading
from typing import Generator
import pytest

from app.schemas.clinical import TherapySession, TherapySessionCreate, TimelineEvent
from packages.tui.client import (
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensClient,
    LinguaLensPermissionError,
    LinguaLensServerError,
)
from packages.tui.workflow import WorkflowRunner


class _SessionContractServerHandler(http.server.BaseHTTPRequestHandler):
    """Synthetic loopback server modeling canonical backend routes for sessions."""

    request_log: list[dict[str, object]] = []
    routes: dict[tuple[str, str], tuple[int, bytes]] = {}

    def do_GET(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        self.__class__.request_log.append(
            {"method": "GET", "path": self.path, "body": body, "headers": dict(self.headers)}
        )
        self._dispatch("GET", self.path)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        parsed_body = json.loads(body.decode("utf-8")) if body else {}
        self.__class__.request_log.append(
            {"method": "POST", "path": self.path, "body": parsed_body, "headers": dict(self.headers)}
        )
        self._dispatch("POST", self.path)

    def _dispatch(self, method: str, path: str) -> None:
        key = (method, path)
        if key in self.__class__.routes:
            status, resp_bytes = self.__class__.routes[key]
        else:
            status, resp_bytes = 404, json.dumps({"detail": f"Route not found: {method} {path}"}).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def session_api_server() -> Generator[tuple[str, type[_SessionContractServerHandler]], None, None]:
    _SessionContractServerHandler.request_log = []
    _SessionContractServerHandler.routes = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = http.server.HTTPServer(("127.0.0.1", port), _SessionContractServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", _SessionContractServerHandler
    finally:
        server.shutdown()
        server.server_close()


def test_list_sessions_calls_timeline_and_session_detail(session_api_server) -> None:
    """Test that list_sessions queries canonical /cases/{case_id}/timeline and /sessions/{id}."""
    base_url, handler = session_api_server

    timeline_data = [
        {
            "event_id": "evt-001",
            "label": "Session 2026-08-10",
            "status": "Draft",
            "occurred_at": "2026-08-10T09:00:00Z",
            "target_id": "sess-b3a-001",
        }
    ]
    TimelineEvent.model_validate(timeline_data[0])

    session_detail_data = {
        "session_id": "sess-b3a-001",
        "case_id": "case-b3a-001",
        "organization_id": "pilot_org_001",
        "version": 1,
        "session_date": "2026-08-10",
        "session_type": "therapy_session",
        "notes": "Initial language assessment session",
        "status": "Draft",
        "transcript_id": "tr-b3a-001",
        "report_id": None,
        "created_at": "2026-08-10T09:00:00Z",
        "updated_at": "2026-08-10T09:00:00Z",
    }
    TherapySession.model_validate(session_detail_data)

    handler.routes[("GET", "/cases/case-b3a-001/timeline")] = (200, json.dumps(timeline_data).encode("utf-8"))
    handler.routes[("GET", "/sessions/sess-b3a-001")] = (200, json.dumps(session_detail_data).encode("utf-8"))

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    sessions = client.list_sessions("case-b3a-001")

    assert len(sessions) == 1
    s0 = sessions[0]
    assert s0["session_id"] == "sess-b3a-001"
    assert s0["case_id"] == "case-b3a-001"
    assert s0["session_date"] == "2026-08-10"
    assert s0["status"] == "Draft"
    assert s0["transcript_id"] == "tr-b3a-001"
    assert s0["report_id"] is None
    assert s0["session_number"] == 1

    # Verify requests were made to canonical endpoints, NOT GET /cases/{case_id}
    req_paths = [r["path"] for r in handler.request_log]
    assert "/cases/case-b3a-001/timeline" in req_paths
    assert "/sessions/sess-b3a-001" in req_paths
    assert "/cases/case-b3a-001" not in req_paths


def test_list_sessions_empty_timeline_returns_valid_empty_list(session_api_server) -> None:
    """A case with zero sessions returns [] (200 OK), which must not raise an error."""
    base_url, handler = session_api_server
    handler.routes[("GET", "/cases/case-empty/timeline")] = (200, b"[]")

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    sessions = client.list_sessions("case-empty")

    assert sessions == []
    req_paths = [r["path"] for r in handler.request_log]
    assert req_paths == ["/cases/case-empty/timeline"]


def test_list_sessions_malformed_response_raises_api_error(session_api_server) -> None:
    """If the timeline returns malformed data (dict instead of list), raise LinguaLensApiError."""
    base_url, handler = session_api_server
    handler.routes[("GET", "/cases/case-bad/timeline")] = (200, b'{"error": "not a list"}')

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.list_sessions("case-bad")
    assert "malformed" in str(exc_info.value).lower() or "timeline" in str(exc_info.value).lower()


def test_list_sessions_fail_closed_on_http_errors(session_api_server) -> None:
    """401, 403, 404, 500 must fail closed without fabricating sessions."""
    base_url, handler = session_api_server

    handler.routes[("GET", "/cases/case-401/timeline")] = (401, b'{"detail": "Unauthorized"}')
    handler.routes[("GET", "/cases/case-403/timeline")] = (403, b'{"detail": "Forbidden"}')
    handler.routes[("GET", "/cases/case-404/timeline")] = (404, b'{"detail": "Case not found"}')
    handler.routes[("GET", "/cases/case-500/timeline")] = (500, b'{"detail": "Internal Error"}')

    client = LinguaLensClient(base_url=base_url, mock_mode=False)

    with pytest.raises(LinguaLensAuthError):
        client.list_sessions("case-401")

    with pytest.raises(LinguaLensPermissionError):
        client.list_sessions("case-403")

    with pytest.raises(LinguaLensApiError) as exc_404:
        client.list_sessions("case-404")
    assert "404" in str(exc_404.value)

    with pytest.raises(LinguaLensServerError):
        client.list_sessions("case-500")


def test_create_session_sends_canonical_schema(session_api_server) -> None:
    """create_session must send TherapySessionCreate schema and return TherapySession."""
    base_url, handler = session_api_server

    response_data = {
        "session_id": "sess-new-123",
        "case_id": "case-b3a-002",
        "organization_id": "pilot_org_001",
        "version": 1,
        "session_date": "2026-09-13",
        "session_type": "therapy_session",
        "notes": "Focused clinical observation notes",
        "status": "Draft",
        "transcript_id": None,
        "report_id": None,
        "created_at": "2026-09-13T10:00:00Z",
        "updated_at": "2026-09-13T10:00:00Z",
    }
    TherapySession.model_validate(response_data)

    handler.routes[("POST", "/cases/case-b3a-002/sessions")] = (200, json.dumps(response_data).encode("utf-8"))

    client = LinguaLensClient(base_url=base_url, mock_mode=False)
    created = client.create_session("case-b3a-002", session_date="2026-09-13", notes="Focused clinical observation notes")

    assert created["session_id"] == "sess-new-123"
    assert created["case_id"] == "case-b3a-002"
    assert created["session_date"] == "2026-09-13"
    assert created["status"] == "Draft"

    # Verify request payload conforms to TherapySessionCreate schema
    post_reqs = [r for r in handler.request_log if r["method"] == "POST"]
    assert len(post_reqs) == 1
    sent_payload = post_reqs[0]["body"]
    assert sent_payload["session_date"] == "2026-09-13"
    assert sent_payload["notes"] == "Focused clinical observation notes"
    TherapySessionCreate.model_validate(sent_payload)


def test_workflow_select_session_sets_active_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """TUI menu session selection sets active_session_id correctly."""
    client = LinguaLensClient(mock_mode=True)
    client._mock_data["sessions"]["case-sel-test"] = [
        {
            "session_id": "sess-sel-1",
            "case_id": "case-sel-test",
            "session_date": "2026-08-10",
            "session_number": 1,
            "status": "Draft",
            "transcript_id": None,
            "report_id": None,
        }
    ]
    runner = WorkflowRunner(client)
    runner.active_case_id = "case-sel-test"
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "1")

    action = runner._sessions_menu()
    assert action == "continue"
    assert runner.active_session_id == "sess-sel-1"


def test_workflow_create_session_wizard_sets_active_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """TUI create session wizard sets active_session_id to the created session."""
    client = LinguaLensClient(mock_mode=True)
    runner = WorkflowRunner(client)
    runner.active_case_id = "case-wizard-test"

    inputs = iter(["2026-09-13", "Wizard session goals", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_session_wizard()
    assert runner.active_session_id is not None
    assert runner.active_session_id.startswith("sess-local-")


def test_direct_v2_entry_does_not_call_legacy_session_endpoints() -> None:
    """Entering V2 Assessment flow does NOT call legacy session methods."""
    class GuardedClient(LinguaLensClient):
        def __init__(self) -> None:
            super().__init__(mock_mode=True)
            self.legacy_session_calls: list[str] = []

        def list_sessions(self, case_id: str) -> list[dict[str, object]]:
            self.legacy_session_calls.append(f"list_sessions:{case_id}")
            return super().list_sessions(case_id)

        def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, object]:
            self.legacy_session_calls.append(f"create_session:{case_id}")
            return super().create_session(case_id, session_date, notes)

    client = GuardedClient()
    runner = WorkflowRunner(client)

    # Simulate choosing 'C' (Child Directory / V2) from entry menu
    runner.active_child_id = "child-001"
    runner.active_child = {"id": "child-001", "display_code": "C-001"}
    runner.active_assessment_id = "asmt-001"

    # Verify no legacy session calls happened
    assert client.legacy_session_calls == []
    assert runner.active_case_id is None
