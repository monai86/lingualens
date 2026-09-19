"""Canonical integration tests connecting LinguaLensClient to FastAPI Assessment V2 routes.

Verifies end-to-end routing, Pydantic schema validation, domain consent gating,
detail route semantics, error status propagation, and zero mock mutation.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Ensure apps/api is resolvable regardless of PYTHONPATH setting
_apps_api_dir = str(Path(__file__).resolve().parents[1] / "apps" / "api")
if _apps_api_dir not in sys.path:
    sys.path.insert(0, _apps_api_dir)

import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    ChildSnapshot,
    ConsentPurpose,
    ConsentSnapshot,
    ConsentStatus,
    CreateAssessment,
    CreateChild,
    RecordConsent,
    StartAssessment,
)
from app.assessment_v2.services import ClinicalPolicyError
from app.main import app
from packages.tui.client import (
    LinguaLensClient,
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensConflictError,
    LinguaLensPermissionError,
    LinguaLensValidationError,
)


class FastAPITransportHandler(urllib.request.BaseHandler):
    """Urllib transport handler that dispatches directly to FastAPI TestClient."""

    handler_order = 100

    def __init__(self, client: TestClient):
        self.client = client

    def default_open(self, req: urllib.request.Request):
        url = req.full_url
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        method = req.get_method()
        headers = {k: v for k, v in req.headers.items()}
        data = req.data
        resp = self.client.request(
            method=method,
            url=path,
            headers=headers,
            content=data,
            follow_redirects=False,
        )
        fp = io.BytesIO(resp.content)
        res = urllib.response.addinfourl(fp, resp.headers, url, resp.status_code)
        res.code = resp.status_code
        res.msg = resp.reason_phrase
        if resp.status_code >= 400:
            raise urllib.error.HTTPError(
                url=url,
                code=resp.status_code,
                msg=resp.reason_phrase,
                hdrs=resp.headers,
                fp=fp,
            )
        return res


class InMemoryAssessmentService:
    """Synthetic service simulating Assessment V2 repository semantics."""

    def __init__(self) -> None:
        self.children: dict[str, ChildSnapshot] = {}
        self.consents: dict[str, list[ConsentSnapshot]] = {}
        self.assessments: dict[str, AssessmentSnapshot] = {}
        self.scope = AccessScope(user_id="therapist_01", organization_id="org_alpha", role="therapist")

    def create_child(self, command: CreateChild, correlation_id: str) -> ChildSnapshot:
        child_id = f"child_{len(self.children) + 1:03d}"
        snapshot = ChildSnapshot(
            id=child_id,
            organization_id="org_alpha",
            display_code=command.display_code,
            birth_year=command.birth_year,
            birth_month=command.birth_month,
            language_context=dict(command.language_context),
            version=1,
        )
        self.children[child_id] = snapshot
        return snapshot

    def get_child(self, child_id: str) -> ChildSnapshot:
        if child_id not in self.children:
            raise ClinicalPolicyError("child_not_found", 404, "Child profile was not found.")
        return self.children[child_id]

    def list_children(self) -> list[ChildSnapshot]:
        return list(self.children.values())

    def grant_consent(
        self, child_id: str, command: RecordConsent, correlation_id: str
    ) -> ConsentSnapshot:
        self.get_child(child_id)
        if child_id not in self.consents:
            self.consents[child_id] = []
        now = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
        purpose_enum = ConsentPurpose(command.purpose)
        purpose_consents = [c for c in self.consents[child_id] if c.purpose == purpose_enum]
        version = max((c.version for c in purpose_consents), default=0) + 1
        snapshot = ConsentSnapshot(
            id=f"consent_{child_id}_{version:02d}",
            organization_id="org_alpha",
            child_id=child_id,
            purpose=purpose_enum,
            scope_version=command.scope_version,
            status=ConsentStatus(command.status),
            granted_at=now,
            withdrawn_at=now if command.status == "withdrawn" else None,
            recorded_by_user_id="therapist_01",
            version=version,
        )
        self.consents[child_id].append(snapshot)
        return snapshot

    def list_consents(self, child_id: str) -> list[ConsentSnapshot]:
        self.get_child(child_id)
        consents = self.consents.get(child_id, [])
        return sorted(consents, key=lambda c: c.version, reverse=True)

    def create_assessment(
        self, child_id: str, command: StartAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        child = self.get_child(child_id)
        child_consents = [
            c for c in self.consents.get(child_id, [])
            if c.purpose == ConsentPurpose.CLINICAL_ASSESSMENT
        ]
        # Repository semantics: order by version desc, check if latest is active
        sorted_consents = sorted(child_consents, key=lambda c: c.version, reverse=True)
        if not sorted_consents or sorted_consents[0].status != ConsentStatus.ACTIVE:
            raise ClinicalPolicyError("active_consent_required", 409, "Active clinical-assessment consent is required.")

        asmt_id = f"asmt_{len(self.assessments) + 1:03d}"
        asmt = AssessmentSnapshot(
            id=asmt_id,
            organization_id="org_alpha",
            child_id=child_id,
            purpose=AssessmentPurpose(command.purpose),
            state=AssessmentState.DRAFT,
            assigned_clinician_id=command.assigned_clinician_id or "therapist_01",
            version=1,
            age_months=48,
            language_context=dict(child.language_context),
        )
        self.assessments[asmt_id] = asmt
        return asmt

    def get_assessment(self, assessment_id: str) -> AssessmentSnapshot:
        if assessment_id not in self.assessments:
            raise ClinicalPolicyError("assessment_not_found", 404, "Assessment was not found.")
        return self.assessments[assessment_id]

    def list_assessments(self, child_id: str) -> list[AssessmentSnapshot]:
        self.get_child(child_id)
        return [a for a in self.assessments.values() if a.child_id == child_id]


@pytest.fixture
def canonical_client():
    service = InMemoryAssessmentService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    with TestClient(app) as test_client:
        client = LinguaLensClient(base_url="http://testserver/api/v1", mock_mode=False)
        client._opener = urllib.request.build_opener(FastAPITransportHandler(test_client))
        try:
            yield client, service
        finally:
            app.dependency_overrides.clear()


def test_canonical_child_lifecycle(canonical_client):
    client, service = canonical_client

    # 1. Initially empty
    assert client.list_children() == []

    # 2. Create child via POST /api/v2/children
    created = client.create_child(
        display_code="CANON-01",
        birth_year=2021,
        birth_month=4,
        language_context={"primary": "th", "additional": ["en"]},
    )
    assert created["id"] == "child_001"
    assert created["display_code"] == "CANON-01"
    assert created["birth_year"] == 2021
    assert created["birth_month"] == 4
    assert created["language_context"] == {"primary": "th", "additional": ["en"]}

    # 3. Get child via GET /api/v2/children/{id}
    fetched = client.get_child("child_001")
    assert fetched["id"] == "child_001"
    assert fetched["display_code"] == "CANON-01"

    # 4. List children via GET /api/v2/children
    all_children = client.list_children()
    assert len(all_children) == 1
    assert all_children[0]["id"] == "child_001"

    # 5. Nonexistent child returns 404
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.get_child("child_nonexistent")
    assert "404" in str(exc_info.value)


def test_canonical_consent_lifecycle_and_withdrawn_semantics(canonical_client):
    client, service = canonical_client

    # Create child first
    child = client.create_child("CANON-02", 2020, 8)
    child_id = child["id"]

    # 1. No consent initially
    assert client.list_consents(child_id) == []
    assert client.get_active_consent(child_id) is None

    # 2. Record active consent
    c1 = client.record_consent(
        child_id=child_id,
        purpose="clinical_assessment",
        scope_version="2026.1",
        status="active",
    )
    assert c1["id"] == f"consent_{child_id}_01"
    assert c1["status"] == "active"
    assert c1["version"] == 1

    # Active consent found
    active = client.get_active_consent(child_id)
    assert active is not None
    assert active["id"] == c1["id"]

    # 3. Assessment creation succeeds with active consent
    asmt = client.create_assessment(child_id, purpose="initial")
    assert asmt["id"] == "asmt_001"
    assert asmt["child_id"] == child_id

    # 4. Now record consent withdrawal (version 2)
    c2 = client.record_consent(
        child_id=child_id,
        purpose="clinical_assessment",
        scope_version="2026.1",
        status="withdrawn",
    )
    assert c2["status"] == "withdrawn"
    assert c2["version"] == 2

    # Verify list_consents returns both records
    all_consents = client.list_consents(child_id)
    assert len(all_consents) == 2

    # Verify active consent is now None because latest is withdrawn!
    assert client.get_active_consent(child_id) is None

    # 5. Creating a new assessment now MUST fail with LinguaLensConflictError (HTTP 409)
    with pytest.raises(LinguaLensConflictError) as exc_info:
        client.create_assessment(child_id, purpose="initial")
    assert "409" in str(exc_info.value) or "conflict" in str(exc_info.value).lower()


def test_canonical_assessment_detail_and_list(canonical_client):
    client, service = canonical_client

    child = client.create_child("CANON-03", 2022, 1)
    child_id = child["id"]
    client.record_consent(child_id, purpose="clinical_assessment", status="active")

    # Create assessment
    asmt = client.create_assessment(child_id, purpose="initial", assigned_clinician_id="therapist_canon")
    asmt_id = asmt["id"]

    # 1. Detail route: GET /api/v2/assessments/{assessment_id}
    detail = client.get_assessment(asmt_id)
    assert detail["id"] == asmt_id
    assert detail["child_id"] == child_id
    assert detail["state"] == "draft"

    # 2. List assessments: GET /api/v2/children/{child_id}/assessments
    asmts = client.list_assessments(child_id)
    assert len(asmts) == 1
    assert asmts[0]["id"] == asmt_id

    # 3. Not found detail route returns HTTP 404
    with pytest.raises(LinguaLensApiError) as exc_info:
        client.get_assessment("asmt_nonexistent")
    assert "404" in str(exc_info.value)


def test_client_create_child_validation_error_fails_closed_zero_dispatch(canonical_client, monkeypatch):
    """Client-side validation rejects invalid intake input immediately with LinguaLensValidationError and zero network dispatch."""
    client, service = canonical_client

    # Spy on transport dispatch to prove zero HTTP requests are dispatched
    http_calls = []
    real_http_request = client._http_request

    def spy_http_request(*args, **kwargs):
        http_calls.append((args, kwargs))
        return real_http_request(*args, **kwargs)

    monkeypatch.setattr(client, "_http_request", spy_http_request)

    # Invalid birth month (13) must raise LinguaLensValidationError specifically
    with pytest.raises(LinguaLensValidationError) as exc_info:
        client.create_child("INV-01", birth_year=2021, birth_month=13)

    assert exc_info.value.__class__ is LinguaLensValidationError
    assert str(exc_info.value) == "birth_month must be between 1 and 12"

    # Verify zero network transport dispatch (zero POST calls)
    assert len(http_calls) == 0

    # Verify mock data and backend service states were not mutated
    assert len(client._mock_data.get("children", [])) == 0
    assert len(service.children) == 0


def test_canonical_backend_validation_error_422_rejection(canonical_client):
    """Bypassing client-side validation directly to FastAPI route proves backend rejects malformed payload with HTTP 422 without mutating service state."""
    client, service = canonical_client

    # Send malformed payload directly through client's live HTTP transport, bypassing client-side validation
    malformed_payload = {
        "display_code": "INV-01",
        "birth_year": 2021,
        "birth_month": 13,
        "language_context": {"primary": "th", "additional": []},
    }

    initial_service_children = len(service.children)
    initial_mock_children = len(client._mock_data.get("children", []))

    # Expect LinguaLensApiError with HTTP 422 status mapping
    with pytest.raises(LinguaLensApiError) as exc_info:
        client._http_request("POST", "/api/v2/children", malformed_payload)

    assert exc_info.value.__class__ is LinguaLensApiError
    assert "422" in str(exc_info.value)

    # Verify no child was created in backend service or repository state
    assert len(service.children) == initial_service_children
    assert len(client._mock_data.get("children", [])) == initial_mock_children


def test_canonical_absent_consent_blocks_assessment_creation(canonical_client):
    """Verify that creating an assessment for a child with zero consents raises 409 active_consent_required."""
    client, service = canonical_client

    child = client.create_child("NO-CONSENT-01", 2021, 6)
    child_id = child["id"]

    # Child exists, but no consent recorded
    assert client.get_active_consent(child_id) is None
    with pytest.raises(LinguaLensConflictError) as exc_info:
        client.create_assessment(child_id, purpose="initial")
    assert "409" in str(exc_info.value) or "conflict" in str(exc_info.value).lower()


def test_canonical_auth_and_permission_errors_preserve_state(canonical_client):
    """Verify that HTTP 401 and 403 errors map to typed exceptions without fallback or mock mutation."""
    import copy
    client, service = canonical_client

    # Snapshot initial mock state
    initial_mock_state = copy.deepcopy(client._mock_data)

    # Simulate 401 Unauthorized via service policy error
    def raise_401(*args, **kwargs):
        raise ClinicalPolicyError("unauthorized", 401, "Session expired or invalid token.")

    service.list_children = raise_401  # type: ignore[assignment]
    with pytest.raises(LinguaLensAuthError):
        client.list_children()
    assert client._mock_data == initial_mock_state

    # Simulate 403 Forbidden via service policy error
    def raise_403(*args, **kwargs):
        raise ClinicalPolicyError("forbidden", 403, "Action forbidden for current role.")

    service.list_children = raise_403  # type: ignore[assignment]
    with pytest.raises(LinguaLensPermissionError):
        client.list_children()
    assert client._mock_data == initial_mock_state


def test_canonical_v1_v2_url_resolution(canonical_client):
    """Verify that a client configured with base_url ending in /api/v1 resolves /api/v2 endpoints cleanly."""
    client, service = canonical_client
    assert client.base_url.endswith("/api/v1")

    # Calling Stage 1 V2 method cleanly strips /api/v1 and routes to /api/v2/children
    res = client.create_child("URL-RES-01", 2022, 3)
    assert res["id"] == "child_001"
    assert res["display_code"] == "URL-RES-01"


def test_canonical_consent_versioning_per_purpose_and_child_isolation(canonical_client) -> None:
    """Verify consent version increment per purpose, active consent derivation, and child isolation."""
    client, service = canonical_client
    child_1 = client.create_child("LL-SEQ-01", 2021, 6)["id"]
    child_2 = client.create_child("LL-SEQ-02", 2021, 7)["id"]

    # 1. Child 1: clinical active -> version 1
    c1 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c1["version"] == 1
    assert c1["purpose"] == "clinical_assessment"

    # 2. Child 1: research active -> version 1 (isolated by purpose!)
    c2 = client.record_consent(child_1, purpose="research_reuse", status="active")
    assert c2["version"] == 1
    assert c2["purpose"] == "research_reuse"

    # 3. Child 1: clinical withdrawn -> version 2
    c3 = client.record_consent(child_1, purpose="clinical_assessment", status="withdrawn")
    assert c3["version"] == 2
    assert c3["purpose"] == "clinical_assessment"

    # Active clinical consent should now be None
    assert client.get_active_consent(child_1) is None

    # 4. Child 1: clinical active -> version 3
    c4 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c4["version"] == 3
    assert c4["purpose"] == "clinical_assessment"

    # Active consent derivation
    active = client.get_active_consent(child_1)
    assert active is not None
    assert active["version"] == 3
    assert active["status"] == "active"

    # Child 2 isolation: Child 2 gets clinical active -> version 1
    c2_1 = client.record_consent(child_2, purpose="clinical_assessment", status="active")
    assert c2_1["version"] == 1
    assert c2_1["child_id"] == child_2


