from __future__ import annotations

from dataclasses import replace

from app.assessment_v2.domain.models import AssessmentSnapshot, AssessmentState


STALE_ASSESSMENT_VERSION = "stale_assessment_version"
INVALID_ASSESSMENT_TRANSITION = "invalid_assessment_transition"


class InvalidAssessmentTransition(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


ALLOWED_TRANSITIONS: dict[AssessmentState, frozenset[AssessmentState]] = {
    AssessmentState.DRAFT: frozenset({AssessmentState.READY_FOR_CAPTURE, AssessmentState.CANCELLED}),
    AssessmentState.READY_FOR_CAPTURE: frozenset({AssessmentState.CAPTURING, AssessmentState.CANCELLED}),
    AssessmentState.CAPTURING: frozenset({AssessmentState.PROCESSING, AssessmentState.CANCELLED}),
    AssessmentState.PROCESSING: frozenset({AssessmentState.CANCELLED}),
    AssessmentState.REVIEW_REQUIRED: frozenset({AssessmentState.CANCELLED}),
    AssessmentState.READY_FOR_CLINICIAN: frozenset({AssessmentState.CANCELLED}),
    AssessmentState.FINALIZED: frozenset(),
    AssessmentState.CANCELLED: frozenset(),
}


def transition_assessment(
    current: AssessmentSnapshot,
    target: AssessmentState,
    expected_version: int,
) -> AssessmentSnapshot:
    if current.version != expected_version:
        raise InvalidAssessmentTransition(STALE_ASSESSMENT_VERSION)

    if target not in ALLOWED_TRANSITIONS[current.state]:
        raise InvalidAssessmentTransition(INVALID_ASSESSMENT_TRANSITION)

    return replace(current, state=target, version=current.version + 1)
