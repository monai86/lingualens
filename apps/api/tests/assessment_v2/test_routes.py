from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    ChildSnapshot,
    ConsentPurpose,
    ConsentSnapshot,
    ConsentStatus,
    RecordConsent,
    StartAssessment,
    TransitionAssessment,
)
from app.assessment_v2.services import ClinicalPolicyError
from app.main import app
from app.assessment_v2.dependencies import get_assessment_service


def child() -> ChildSnapshot:
    return ChildSnapshot(
        id="child_opaque_01",
        organization_id="org_alpha",
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context={"primary": "th", "additional": []},
        version=1,
    )


def consent() -> ConsentSnapshot:
    return ConsentSnapshot(
        id="consent_opaque_01",
        organization_id="org_alpha",
        child_id="child_opaque_01",
        purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
        scope_version="clinical-v1",
        status=ConsentStatus.ACTIVE,
        granted_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        withdrawn_at=None,
        recorded_by_user_id="therapist_01",
        version=1,
    )


class FakeAssessmentService:
    def __init__(self) -> None:
        self.child_value = child()
        self.consent_value = consent()
        self.has_consent = False
        self.assessment_value: AssessmentSnapshot | None = None

    def create_child(self, command, correlation_id: str) -> ChildSnapshot:
        return self.child_value

    def get_child(self, child_id: str) -> ChildSnapshot:
        if child_id != self.child_value.id:
            raise ClinicalPolicyError("child_not_found", 404, "Child was not found.")
        return self.child_value

    def list_children(self) -> list[ChildSnapshot]:
        return [self.child_value]

    def grant_consent(self, child_id: str, command: RecordConsent, correlation_id: str) -> ConsentSnapshot:
        self.get_child(child_id)
        self.has_consent = command.status is ConsentStatus.ACTIVE
        self.consent_value = replace(
            self.consent_value,
            purpose=command.purpose,
            scope_version=command.scope_version,
            status=command.status,
            withdrawn_at=None if command.status is ConsentStatus.ACTIVE else datetime.now(timezone.utc),
        )
        return self.consent_value

    def create_assessment(
        self, child_id: str, command: StartAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self.get_child(child_id)
        if not self.has_consent:
            raise ClinicalPolicyError(
                "active_consent_required", 409, "Active clinical-assessment consent is required."
            )
        self.assessment_value = AssessmentSnapshot(
            id="assessment_opaque_01",
            organization_id="org_alpha",
            child_id=child_id,
            purpose=command.purpose,
            state=AssessmentState.DRAFT,
            assigned_clinician_id=command.assigned_clinician_id or "therapist_01",
            version=1,
            age_months=63,
            language_context={"primary": "th", "additional": []},
        )
        return self.assessment_value

    def list_assessments(self, child_id: str) -> list[AssessmentSnapshot]:
        self.get_child(child_id)
        return [self.assessment_value] if self.assessment_value else []

    def get_assessment(self, assessment_id: str) -> AssessmentSnapshot:
        if self.assessment_value is None or self.assessment_value.id != assessment_id:
            raise ClinicalPolicyError("assessment_not_found", 404, "Assessment was not found.")
        return self.assessment_value

    def transition_assessment(
        self, assessment_id: str, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        current = self.get_assessment(assessment_id)
        if command.expected_version != current.version:
            raise ClinicalPolicyError("stale_assessment_version", 409, "The assessment version is stale.")
        if command.target_state is AssessmentState.READY_FOR_CAPTURE:
            raise ClinicalPolicyError(
                "workflow_stage_unavailable", 409, "This workflow stage is not yet available."
            )
        self.assessment_value = replace(
            current, state=command.target_state, version=current.version + 1
        )
        return self.assessment_value


@pytest.fixture
def routed_client() -> tuple[TestClient, FakeAssessmentService]:
    service = FakeAssessmentService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        yield TestClient(app), service
    finally:
        app.dependency_overrides.clear()


def test_assessment_v2_vertical_slice_and_fail_closed_capture(
    routed_client: tuple[TestClient, FakeAssessmentService],
) -> None:
    client, _ = routed_client
    child_payload = {
        "display_code": "LL-0001",
        "birth_year": 2021,
        "birth_month": 6,
        "language_context": {"primary": "th", "additional": []},
    }

    created_child = client.post("/api/v2/children", json=child_payload)
    assert created_child.status_code == 201
    child_id = created_child.json()["id"]
    assert child_id == "child_opaque_01"
    assert "name" not in created_child.json()
    assert client.get("/api/v2/children").status_code == 200
    assert client.get(f"/api/v2/children/{child_id}").status_code == 200

    denied = client.post(
        f"/api/v2/children/{child_id}/assessments",
        json={"purpose": "initial"},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "active_consent_required"

    consent_response = client.post(
        f"/api/v2/children/{child_id}/consents",
        json={
            "purpose": "clinical_assessment",
            "scope_version": "clinical-v1",
            "status": "active",
        },
    )
    assert consent_response.status_code == 201
    assert client.get(f"/api/v2/children/{child_id}/assessments").json() == []

    created_assessment = client.post(
        f"/api/v2/children/{child_id}/assessments",
        json={"purpose": "developmental_follow_up"},
    )
    assert created_assessment.status_code == 201
    assessment_id = created_assessment.json()["id"]
    assert created_assessment.json()["state"] == "draft"
    assert created_assessment.json()["version"] == 1
    assert created_assessment.json()["age_months"] == 63
    assert created_assessment.json()["language_context"] == {"primary": "th", "additional": []}
    assert client.get(f"/api/v2/assessments/{assessment_id}").status_code == 200
    assert client.get(f"/api/v2/children/{child_id}/assessments").status_code == 200

    blocked = client.post(
        f"/api/v2/assessments/{assessment_id}/transitions",
        json={"target_state": "ready_for_capture", "expected_version": 1},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "workflow_stage_unavailable"

    cancelled = client.post(
        f"/api/v2/assessments/{assessment_id}/transitions",
        json={"target_state": "cancelled", "expected_version": 1},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    assert cancelled.json()["version"] == 2

    stale = client.post(
        f"/api/v2/assessments/{assessment_id}/transitions",
        json={"target_state": "ready_for_capture", "expected_version": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_assessment_version"


def test_v2_validation_and_cross_scope_errors_are_safe(
    routed_client: tuple[TestClient, FakeAssessmentService],
) -> None:
    client, _ = routed_client
    malformed = client.post("/api/v2/children", json={"display_code": "LL-0001"})
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "request_validation_failed"
    assert malformed.headers["x-request-id"]

    other_tenant = client.get("/api/v2/children/other-tenant-child")
    out_of_team = client.get("/api/v2/children/out-of-team-child")
    assert other_tenant.status_code == out_of_team.status_code == 404
    assert other_tenant.json()["error"]["code"] == out_of_team.json()["error"]["code"] == "child_not_found"


def test_v1_validation_keeps_existing_fastapi_error_shape(
    routed_client: tuple[TestClient, FakeAssessmentService],
) -> None:
    client, _ = routed_client
    response = client.post("/api/v1/cases", json={})

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "error" not in response.json()
