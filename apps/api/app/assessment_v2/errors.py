"""Safe exception-to-response conversion for assessment v2 routes."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.assessment_v2.schemas import ErrorEnvelope


# Only non-sensitive, finite vocabulary is allowed to cross the error boundary.
_SAFE_DETAIL_KEYS = frozenset({"allowed_states", "allowed_purposes"})


def _safe_details(details: Mapping[str, object] | None) -> dict[str, object]:
    if not details:
        return {}
    safe: dict[str, object] = {}
    for key in _SAFE_DETAIL_KEYS:
        value = details.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            safe[key] = list(value)
    return safe


def assessment_error_response(
    request: Request,
    code: str,
    status_code: int,
    message: str,
    details: Mapping[str, object] | None = None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "request_id", None) or uuid4().hex
    payload = ErrorEnvelope(
        error={
            "code": code,
            "message": message,
            "details": _safe_details(details),
            "correlation_id": correlation_id,
        }
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"x-request-id": correlation_id},
    )
