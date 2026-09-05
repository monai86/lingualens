"""Typed HTTP routes for the additive assessment v2 foundation slice."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    CreateChild,
    RecordConsent,
    StartAssessment,
    TransitionAssessment,
)
from app.assessment_v2.schemas import (
    AssessmentCreateRequest,
    AssessmentResponse,
    AssessmentTransitionRequest,
    ChildCreateRequest,
    ChildResponse,
    ConsentCreateRequest,
    ConsentResponse,
    ErrorEnvelope,
)
from app.assessment_v2.services import AssessmentService


_V2_ERROR_RESPONSES = {
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
}

router = APIRouter(tags=["assessment-v2"])


def _correlation_id(request: Request) -> str:
    return request.state.request_id


def _child_response(value) -> ChildResponse:
    return ChildResponse(
        id=value.id,
        display_code=value.display_code,
        birth_year=value.birth_year,
        birth_month=value.birth_month,
        language_context=value.language_context,
        version=value.version,
    )


def _consent_response(value) -> ConsentResponse:
    return ConsentResponse(
        id=value.id,
        child_id=value.child_id,
        purpose=value.purpose,
        scope_version=value.scope_version,
        status=value.status,
        granted_at=value.granted_at,
        withdrawn_at=value.withdrawn_at,
        version=value.version,
    )


def _assessment_response(value) -> AssessmentResponse:
    return AssessmentResponse(
        id=value.id,
        child_id=value.child_id,
        purpose=value.purpose,
        state=value.state,
        age_months=value.age_months,
        language_context=value.language_context,
        assigned_clinician_id=value.assigned_clinician_id,
        version=value.version,
    )


@router.post(
    "/children",
    response_model=ChildResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_child(
    payload: ChildCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ChildResponse:
    value = service.create_child(
        CreateChild(
            display_code=payload.display_code,
            birth_year=payload.birth_year,
            birth_month=payload.birth_month,
            language_context=payload.language_context,
        ),
        _correlation_id(request),
    )
    return _child_response(value)


@router.get(
    "/children",
    response_model=list[ChildResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_children(
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ChildResponse]:
    return [_child_response(value) for value in service.list_children()]


@router.get(
    "/children/{child_id}",
    response_model=ChildResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_child(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ChildResponse:
    return _child_response(service.get_child(child_id))


@router.post(
    "/children/{child_id}/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_consent(
    child_id: str,
    payload: ConsentCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ConsentResponse:
    value = service.grant_consent(
        child_id,
        RecordConsent(
            purpose=payload.purpose,
            scope_version=payload.scope_version,
            status=payload.status,
        ),
        _correlation_id(request),
    )
    return _consent_response(value)


@router.post(
    "/children/{child_id}/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_assessment(
    child_id: str,
    payload: AssessmentCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    value = service.create_assessment(
        child_id,
        StartAssessment(
            purpose=payload.purpose,
            assigned_clinician_id=payload.assigned_clinician_id,
        ),
        _correlation_id(request),
    )
    return _assessment_response(value)


@router.get(
    "/children/{child_id}/assessments",
    response_model=list[AssessmentResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_assessments(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[AssessmentResponse]:
    return [_assessment_response(value) for value in service.list_assessments(child_id)]


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_assessment(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    return _assessment_response(service.get_assessment(assessment_id))


@router.post(
    "/assessments/{assessment_id}/transitions",
    response_model=AssessmentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def transition_assessment(
    assessment_id: str,
    payload: AssessmentTransitionRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    value = service.transition_assessment(
        assessment_id,
        TransitionAssessment(
            assessment_id=assessment_id,
            target_state=payload.target_state,
            expected_version=payload.expected_version,
        ),
        _correlation_id(request),
    )
    return _assessment_response(value)
