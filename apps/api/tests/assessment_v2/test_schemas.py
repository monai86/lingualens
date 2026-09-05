from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState
from app.assessment_v2.schemas import (
    AssessmentCreateRequest,
    AssessmentResponse,
    AssessmentTransitionRequest,
    ChildCreateRequest,
    ChildResponse,
    ConsentCreateRequest,
    ConsentResponse,
)


def language_context() -> dict[str, object]:
    return {"primary": "TH", "additional": ["en"]}


def test_child_request_is_strict_and_normalizes_language_codes() -> None:
    request = ChildCreateRequest(
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context=language_context(),
    )

    assert request.language_context == {"primary": "th", "additional": ["en"]}

    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context=language_context(),
            name="real child",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "child"},
        {"date_of_birth": "2021-06-01"},
        {"organization_id": "org_alpha"},
        {"state": "finalized"},
    ],
)
def test_request_models_reject_identifiers_dates_organization_and_state(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context=language_context(),
            **payload,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("birth_month", 0),
        ("birth_month", 13),
        ("birth_year", 1899),
        ("birth_year", 2101),
    ],
)
def test_child_birth_fields_are_constrained(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=value if field == "birth_year" else 2021,
            birth_month=value if field == "birth_month" else 6,
            language_context=language_context(),
        )


def test_language_context_requires_two_letter_primary_and_additional_codes() -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "thai", "additional": []},
        )

    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": ["english"]},
        )


def test_consent_request_is_strict_and_has_explicit_enums() -> None:
    request = ConsentCreateRequest(
        purpose="clinical_assessment",
        scope_version="clinical-v1",
        status="active",
    )

    assert request.purpose.value == "clinical_assessment"
    assert request.status.value == "active"

    with pytest.raises(ValidationError):
        ConsentCreateRequest(
            purpose="clinical_assessment",
            scope_version="clinical-v1",
            status="active",
            organization_id="org_alpha",
        )


def test_assessment_create_and_transition_requests_cannot_supply_state_or_negative_version() -> None:
    request = AssessmentCreateRequest(purpose=AssessmentPurpose.INITIAL)
    assert request.assigned_clinician_id is None

    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="not-a-purpose")
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="initial", state="finalized")
    with pytest.raises(ValidationError):
        AssessmentTransitionRequest(target_state=AssessmentState.DRAFT, expected_version=-1)


def test_responses_expose_safe_clinical_fields_without_child_name_or_exact_dob() -> None:
    child_fields = set(ChildResponse.model_fields)
    assessment_fields = set(AssessmentResponse.model_fields)
    consent_fields = set(ConsentResponse.model_fields)

    assert {"display_code", "birth_year", "birth_month", "language_context"} <= child_fields
    assert "name" not in child_fields and "date_of_birth" not in child_fields
    assert "age_months" in assessment_fields and "language_context" in assessment_fields
    assert "name" not in assessment_fields and "date_of_birth" not in assessment_fields
    assert {"purpose", "scope_version", "status", "version"} <= consent_fields

    response = ChildResponse(
        id="child_01",
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context={"primary": "th", "additional": []},
        version=1,
    )
    assert response.model_dump()["display_code"] == "LL-0001"

    assessment = AssessmentResponse(
        id="assessment_01",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=AssessmentState.DRAFT,
        age_months=63,
        language_context={"primary": "th", "additional": []},
        assigned_clinician_id="therapist_01",
        version=1,
    )
    assert assessment.state is AssessmentState.DRAFT

    consent = ConsentResponse(
        id="consent_01",
        child_id="child_01",
        purpose="clinical_assessment",
        scope_version="clinical-v1",
        status="active",
        granted_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        withdrawn_at=None,
        version=1,
    )
    assert consent.status.value == "active"
