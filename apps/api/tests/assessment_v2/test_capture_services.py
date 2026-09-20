from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from importlib import import_module

import pytest

from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentSnapshot, AssessmentState
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.core.security import CurrentUser


def _assessment(primary_language: str = "th") -> AssessmentSnapshot:
    return AssessmentSnapshot(
        id="assessment_opaque_01",
        organization_id="org_alpha",
        child_id="child_opaque_01",
        purpose=AssessmentPurpose.INITIAL,
        state=AssessmentState.DRAFT,
        assigned_clinician_id="therapist_01",
        version=1,
        age_months=36,
        language_context={"primary": primary_language, "additional": []},
    )


class _ProtocolSelectionRepository:
    def __init__(self, primary_language: str = "th") -> None:
        self.assessment = _assessment(primary_language)
        self.selection = None

    def get_assessment(self, scope, assessment_id: str):
        assert assessment_id == self.assessment.id
        return self.assessment

    def select_protocol_and_ready(self, scope, command, correlation_id: str):
        domain = import_module("app.assessment_v2.domain.models")
        self.selection = domain.ProtocolSelectionSnapshot(
            assessment_id=command.assessment_id,
            protocol_version_key=command.protocol_version_key,
            selected_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
            version=1,
        )
        self.assessment = replace(
            self.assessment,
            state=AssessmentState.READY_FOR_CAPTURE,
            version=self.assessment.version + 1,
        )
        return domain.CaptureSnapshot(
            assessment=self.assessment,
            protocol_selection=self.selection,
            activities=(),
            recordings=(),
            quality_results=(),
        )


def _service(repository: _ProtocolSelectionRepository) -> AssessmentService:
    return AssessmentService(
        repository,
        CurrentUser(
            user_id="therapist_01",
            organization_id="org_alpha",
            role="therapist",
            display_name="Synthetic Therapist",
        ),
    )


def test_protocol_selection_uses_assessment_context_and_returns_ready_capture_snapshot() -> None:
    assert hasattr(AssessmentService, "select_protocol")
    repository = _ProtocolSelectionRepository()

    capture = _service(repository).select_protocol("assessment_opaque_01", "0123456789abcdef0123456789abcdef")

    assert capture.assessment.state is AssessmentState.READY_FOR_CAPTURE
    assert capture.assessment.version == 2
    assert capture.protocol_selection is not None
    assert capture.protocol_selection.protocol_version_key == "thai_guided_language_sample:v0"


def test_protocol_selection_fails_closed_when_context_has_no_catalog_match() -> None:
    assert hasattr(AssessmentService, "select_protocol")
    repository = _ProtocolSelectionRepository(primary_language="en")

    with pytest.raises(ClinicalPolicyError) as raised:
        _service(repository).select_protocol("assessment_opaque_01", "0123456789abcdef0123456789abcdef")

    assert raised.value.code == "protocol_unavailable"
    assert repository.selection is None
