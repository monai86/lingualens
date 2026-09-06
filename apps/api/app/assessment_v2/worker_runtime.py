"""Process one durable Capture V2 run from the configured assessment database."""

from __future__ import annotations

import time

from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.db.session import get_assessment_session_factory
from app.assessment_v2.storage import SupabasePrivateStorageAdapter
from app.assessment_v2.worker import CaptureProcessingWorker
from app.core.config import get_settings


def run_capture_worker_once() -> dict[str, str | None]:
    settings = get_settings().validate_runtime_security()
    session = get_assessment_session_factory(settings.assessment_database_url)()
    try:
        result = CaptureProcessingWorker(
            AssessmentRepository(session),
            SupabasePrivateStorageAdapter(settings=settings),
        ).run_once()
        session.commit()
        return {"status": result.status, "run_id": result.run_id}
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


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
