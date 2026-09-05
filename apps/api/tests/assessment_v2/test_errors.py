from __future__ import annotations

import re

from fastapi import Request

from app.assessment_v2.errors import assessment_error_response
from app.assessment_v2.schemas import ErrorEnvelope


def request_with_id(request_id: str | None) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v2/children",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )
    if request_id is not None:
        request.state.request_id = request_id
    return request


def test_error_envelope_is_exact_and_uses_request_correlation_id() -> None:
    response = assessment_error_response(
        request_with_id("req-01"),
        "active_consent_required",
        409,
        "Active clinical-assessment consent is required.",
        {},
    )

    assert response.status_code == 409
    assert response.headers["x-request-id"] == "req-01"
    assert response.body == (
        b'{"error":{"code":"active_consent_required",'
        b'"message":"Active clinical-assessment consent is required.",'
        b'"details":{},"correlation_id":"req-01"}}'
    )
    assert ErrorEnvelope.model_validate_json(response.body).error.details == {}


def test_error_response_generates_correlation_id_without_echoing_exception_text() -> None:
    response = assessment_error_response(
        request_with_id(None),
        "child_not_found",
        404,
        "Child was not found.",
        {"internal": "secret child name and exact date of birth"},
    )

    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", correlation_id)
    assert response.headers["x-request-id"] == correlation_id
    assert b"secret child name" not in response.body
    assert b"exact date of birth" not in response.body
