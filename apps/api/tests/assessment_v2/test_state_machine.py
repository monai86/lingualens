from dataclasses import replace

import pytest

from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentSnapshot, AssessmentState
from app.assessment_v2.domain.transitions import InvalidAssessmentTransition, transition_assessment


def assessment(state: AssessmentState = AssessmentState.DRAFT, version: int = 1) -> AssessmentSnapshot:
    return AssessmentSnapshot(
        id="assessment_01",
        organization_id="org_alpha",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=state,
        assigned_clinician_id="therapist_01",
        version=version,
        age_months=63,
        language_context={"primary": "th", "additional": []},
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (AssessmentState.DRAFT, AssessmentState.READY_FOR_CAPTURE),
        (AssessmentState.READY_FOR_CAPTURE, AssessmentState.CAPTURING),
        (AssessmentState.CAPTURING, AssessmentState.PROCESSING),
        (AssessmentState.PROCESSING, AssessmentState.REVIEW_REQUIRED),
        (AssessmentState.REVIEW_REQUIRED, AssessmentState.READY_FOR_CLINICIAN),
        (AssessmentState.READY_FOR_CLINICIAN, AssessmentState.FINALIZED),
    ],
)
def test_allows_forward_workflow(source: AssessmentState, target: AssessmentState) -> None:
    updated = transition_assessment(assessment(source, version=4), target, expected_version=4)

    assert updated.state is target
    assert updated.version == 5


@pytest.mark.parametrize(
    "source",
    [
        AssessmentState.DRAFT,
        AssessmentState.READY_FOR_CAPTURE,
        AssessmentState.CAPTURING,
        AssessmentState.PROCESSING,
        AssessmentState.REVIEW_REQUIRED,
        AssessmentState.READY_FOR_CLINICIAN,
    ],
)
def test_allows_cancellation_before_finalization(source: AssessmentState) -> None:
    updated = transition_assessment(assessment(source, version=4), AssessmentState.CANCELLED, expected_version=4)

    assert updated.state is AssessmentState.CANCELLED
    assert updated.version == 5


@pytest.mark.parametrize(
    ("terminal", "target"),
    [
        (AssessmentState.FINALIZED, AssessmentState.REVIEW_REQUIRED),
        (AssessmentState.FINALIZED, AssessmentState.CANCELLED),
        (AssessmentState.CANCELLED, AssessmentState.REVIEW_REQUIRED),
        (AssessmentState.CANCELLED, AssessmentState.CANCELLED),
    ],
)
def test_rejects_transition_from_terminal_state(terminal: AssessmentState, target: AssessmentState) -> None:
    with pytest.raises(InvalidAssessmentTransition) as error:
        transition_assessment(assessment(terminal), target, 1)

    assert error.value.code == "invalid_assessment_transition"


def test_rejects_skipped_state() -> None:
    with pytest.raises(InvalidAssessmentTransition) as error:
        transition_assessment(assessment(), AssessmentState.PROCESSING, 1)

    assert error.value.code == "invalid_assessment_transition"


def test_rejects_backward_state() -> None:
    with pytest.raises(InvalidAssessmentTransition) as error:
        transition_assessment(assessment(AssessmentState.PROCESSING), AssessmentState.CAPTURING, 1)

    assert error.value.code == "invalid_assessment_transition"


def test_rejects_stale_version() -> None:
    with pytest.raises(InvalidAssessmentTransition, match="stale_assessment_version") as error:
        transition_assessment(replace(assessment(), version=3), AssessmentState.READY_FOR_CAPTURE, 2)

    assert error.value.code == "stale_assessment_version"
