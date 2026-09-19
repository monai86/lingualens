"""Process one durable Capture V2 or Evidence V2 run from the assessment DB."""

from __future__ import annotations

import time

from sqlalchemy import select

from app.assessment_v2.db.models import OrganizationRecord
from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.db.session import assessment_session_for, get_assessment_session_factory
from app.assessment_v2.evidence_worker import EvidenceProcessingWorker
from app.assessment_v2.storage import SupabasePrivateStorageAdapter
from app.assessment_v2.worker import CaptureProcessingWorker
from app.core.config import get_settings
from app.core.security import CurrentUser


def _active_organization_ids(session_factory) -> list[str]:
    session = session_factory()
    try:
        return list(
            session.scalars(
                select(OrganizationRecord.organization_id).where(OrganizationRecord.active.is_(True))
            )
        )
    finally:
        session.close()


def _worker_organization_ids(settings, session_factory) -> list[str]:
    """Resolve tenants without performing an unscoped PostgreSQL query.

    Assessment tables use tenant RLS, so a worker cannot discover tenants by
    selecting ``organizations`` through the application role. Production and
    Compose deployments provide an explicit allowlist; SQLite test runtimes
    retain the local discovery fallback.
    """

    configured = getattr(settings, "capture_worker_organization_ids", "")
    organization_ids = list(dict.fromkeys(item.strip() for item in configured.split(",") if item.strip()))
    if organization_ids:
        return organization_ids
    bind = getattr(session_factory, "kw", {}).get("bind")
    dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect_name == "postgresql":
        raise ValueError(
            "LINGUALENS_CAPTURE_WORKER_ORGANIZATION_IDS is required for PostgreSQL RLS polling."
        )
    return _active_organization_ids(session_factory)


def run_capture_worker_once() -> dict[str, str | None]:
    settings = get_settings().validate_runtime_security()
    session_factory = get_assessment_session_factory(settings.assessment_database_url)
    storage = SupabasePrivateStorageAdapter(settings=settings)
    first_non_idle: dict[str, str | None] | None = None
    for organization_id in _worker_organization_ids(settings, session_factory):
        worker_user = CurrentUser(
            user_id="capture-worker",
            role="org_admin",
            display_name="Capture Worker",
            organization_id=organization_id,
        )
        with assessment_session_for(worker_user, settings.assessment_database_url) as session:
            repository = AssessmentRepository(
                session,
                worker_organization_id=organization_id,
                worker_user_id=worker_user.user_id,
            )
            capture_result = CaptureProcessingWorker(
                repository,
                storage,
            ).run_once()
        if capture_result.status != "idle":
            first_non_idle = first_non_idle or {
                "status": capture_result.status,
                "run_id": capture_result.run_id,
            }

        # Keep the evidence transaction separate from capture work. The
        # evidence lease must be committed before transcript extraction so a
        # crash leaves a reclaimable RUNNING job instead of rolling the claim
        # back with unrelated capture work.
        with assessment_session_for(worker_user, settings.assessment_database_url) as session:
            repository = AssessmentRepository(
                session,
                worker_organization_id=organization_id,
                worker_user_id=worker_user.user_id,
            )
            evidence_result = EvidenceProcessingWorker(repository).run_once()
        if evidence_result.status != "idle":
            first_non_idle = first_non_idle or {
                "status": evidence_result.status,
                "run_id": evidence_result.run_id,
            }
    return first_non_idle or {"status": "idle", "run_id": None}


def run_capture_worker_loop(*, idle_sleep_seconds: float = 1.0, max_cycles: int | None = None) -> None:
    """Keep polling until terminated; ``max_cycles`` is reserved for tests."""

    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        result = run_capture_worker_once()
        cycles += 1
        if result["status"] == "idle":
            time.sleep(idle_sleep_seconds)


if __name__ == "__main__":
    run_capture_worker_loop()
