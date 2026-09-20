"""Focused regression tests for the TUI legacy case contract (review finding B4)."""

from __future__ import annotations

import copy
import http.server
import io
import json
import socket
import threading
from typing import Generator

import pytest
from rich.console import Console

from packages.tui.client import LinguaLensApiError, LinguaLensClient
from packages.tui.workflow import WorkflowRunner
from packages.tui.ui import render_cases_table


def test_legacy_case_selection_uses_canonical_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LinguaLensClient(mock_mode=True)
    client._mock_data["cases"] = [
        {
            "case_id": "case-b4-select",
            "child_code": "child-b4-select",
            "age_months": 36,
            "language": "th",
            "notes": "synthetic B4 selection fixture",
            "session_count": 0,
        }
    ]
    runner = WorkflowRunner(client)
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "1")

    assert runner._cases_menu() == "sessions"
    assert runner.active_case_id == "case-b4-select"


def test_legacy_case_creation_uses_canonical_payload_and_enters_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecordingClient(LinguaLensClient):
        def __init__(self) -> None:
            super().__init__(mock_mode=True)
            self.session_case_ids: list[str | None] = []

        def list_sessions(self, case_id: str | None) -> list[dict[str, object]]:
            self.session_case_ids.append(case_id)
            return super().list_sessions(case_id)

    client = RecordingClient()
    runner = WorkflowRunner(client)
    inputs = iter(["1", "n", "child-b4-create", "36", "th", "synthetic notes", "", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner.start()

    assert client.session_case_ids == ["case-local-001"]
    assert runner.active_case_id == "case-local-001"
    created = client.list_cases()[0]
    assert created["case_id"] == "case-local-001"
    assert created["child_code"] == "child-b4-create"
    assert created["age_months"] == 36
    assert created["language"] == "th"
    assert created["notes"] == "synthetic notes"


class _CaseCreateHandler(http.server.BaseHTTPRequestHandler):
    request_log: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.__class__.request_log.append(
            {"method": "POST", "path": self.path, "body": json.loads(body)}
        )
        response = {
            "case_id": "case-b4-api",
            "child_code": "child-b4-api",
            "age_months": 36,
            "language": "th",
            "notes": "synthetic API response",
        }
        response_bytes = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def case_create_server() -> Generator[tuple[str, type[_CaseCreateHandler]], None, None]:
    _CaseCreateHandler.request_log = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = http.server.HTTPServer(("127.0.0.1", port), _CaseCreateHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", _CaseCreateHandler
    finally:
        server.shutdown()
        server.server_close()


def test_client_create_case_sends_actual_legacy_api_schema(case_create_server) -> None:
    from app.schemas.clinical import ChildCaseCreate

    base_url, handler = case_create_server
    client = LinguaLensClient(base_url=base_url, mock_mode=False)

    response = client.create_case(
        child_code="child-b4-api",
        age_months=36,
        language="th",
        notes="synthetic API request",
    )

    assert response["case_id"] == "case-b4-api"
    assert handler.request_log == [
        {
            "method": "POST",
            "path": "/cases",
            "body": {
                "child_code": "child-b4-api",
                "age_months": 36,
                "language": "th",
                "notes": "synthetic API request",
            },
        }
    ]
    ChildCaseCreate.model_validate(handler.request_log[0]["body"])


def test_invalid_birth_year_month_fails_closed_without_local_mutation() -> None:
    client = LinguaLensClient(mock_mode=True)
    before = copy.deepcopy(client._mock_data)

    with pytest.raises(LinguaLensApiError):
        client.create_case(
            child_id="child-b4-invalid",
            birth_year_month="2022-13",
            primary_language="th",
            notes="synthetic invalid date",
        )

    assert client._mock_data == before


def test_api_failure_does_not_create_fabricated_active_case(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient(LinguaLensClient):
        def create_case(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise LinguaLensApiError("synthetic API failure")

    client = FailingClient(mock_mode=True)
    before = copy.deepcopy(client._mock_data)
    runner = WorkflowRunner(client)
    inputs = iter(["child-b4-failure", "36", "th", "synthetic notes", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_case_wizard()

    assert runner.active_case_id is None
    assert client._mock_data == before


def test_cases_table_renders_canonical_response_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    output_stream = io.StringIO()
    monkeypatch.setattr("packages.tui.ui.console", Console(file=output_stream, width=160))
    render_cases_table(
        [
            {
                "case_id": "case-b4-render",
                "child_code": "child-b4-render",
                "age_months": 48,
                "language": "th",
                "notes": "canonical notes",
                "session_count": 2,
            }
        ]
    )
    output = output_stream.getvalue()
    assert "case-b4-render" in output
    assert "child-b4-render" in output
    assert "canonical notes" in output
