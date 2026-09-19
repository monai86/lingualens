"""FastAPI dependency composition for the assessment v2 boundary."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.db.session import assessment_session_for
from app.assessment_v2.domain.models import AccessScope
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.assessment_v2.storage import CaptureStorageAdapter, SupabasePrivateStorageAdapter
from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user


def _request_correlation_id(request: Request) -> str:
    correlation_id = getattr(request.state, "request_id", None)
    if correlation_id:
        return correlation_id
    correlation_id = uuid4().hex
    request.state.request_id = correlation_id
    return correlation_id


def get_assessment_session(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Iterator[Session]:
    """Provide one tenant-bound transaction for the complete v2 request."""

    with assessment_session_for(user, settings.assessment_database_url) as session:
        yield session


def get_assessment_repository(
    session: Session = Depends(get_assessment_session),
) -> AssessmentRepository:
    return AssessmentRepository(session)


def get_capture_storage(
    settings: Settings = Depends(get_settings),
) -> CaptureStorageAdapter:
    """Construct the private adapter lazily; provider access happens per operation."""

    return SupabasePrivateStorageAdapter(settings=settings)


def get_assessment_service(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    repository: AssessmentRepository = Depends(get_assessment_repository),
    storage: CaptureStorageAdapter = Depends(get_capture_storage),
) -> AssessmentService:
    """Synchronize identity, then authorize against persisted membership state."""

    correlation_id = _request_correlation_id(request)
    if user.role not in {"therapist", "clinical_supervisor", "org_admin"}:
        raise ClinicalPolicyError(
            "role_not_permitted",
            403,
            "This role is not permitted for the clinical workflow.",
        )
    repository.synchronize_principal(user, correlation_id)
    identity_scope = AccessScope(
        user_id=user.user_id,
        organization_id=user.organization_id,
        role=user.role,
    )
    persisted_role = repository.active_membership_role(identity_scope)
    if persisted_role is None:
        raise ClinicalPolicyError(
            "inactive_membership",
            403,
            "Active organization membership is required.",
        )
    return AssessmentService(
        repository,
        user,
        storage=storage,
        authorized_role=persisted_role,
    )
