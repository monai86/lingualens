from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.assessment_v2 import worker_runtime


ROOT = Path(__file__).resolve().parents[4]


def test_capture_worker_runtime_build_includes_ffmpeg_and_ffprobe() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "ffmpeg" in dockerfile
    assert "capture-worker:" in compose
    assert "python -m app.assessment_v2.worker_runtime" in compose
    assert "ffprobe -version" in compose


def test_capture_worker_uses_durable_database_polling_without_redis_contract() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()
    capture_worker = compose.split("  capture-worker:", 1)[1].split("\n  frontend:", 1)[0]

    assert "LINGUALENS_ASSESSMENT_DATABASE_URL" in capture_worker
    assert "LINGUALENS_STORAGE_MODE=supabase_private" in capture_worker
    assert "LINGUALENS_SUPABASE_STORAGE_SERVICE_ROLE_KEY" in capture_worker
    assert "LINGUALENS_CAPTURE_WORKER_ORGANIZATION_IDS" in capture_worker
    assert "LINGUALENS_JOB_QUEUE_MODE" not in capture_worker
    assert "REDIS_URL" not in capture_worker
    assert "      redis:" not in capture_worker


def test_capture_worker_runtime_can_be_bounded_for_supervised_tests(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        worker_runtime,
        "run_capture_worker_once",
        lambda: calls.append("tick") or {"status": "idle", "run_id": None},
    )

    worker_runtime.run_capture_worker_loop(idle_sleep_seconds=0, max_cycles=2)

    assert calls == ["tick", "tick"]


def test_capture_worker_runtime_scopes_each_tenant_before_polling(monkeypatch) -> None:
    scoped_organizations: list[str] = []

    class FakeSession:
        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeScope:
        def __init__(self, organization_id: str):
            self.organization_id = organization_id

        def __enter__(self):
            scoped_organizations.append(self.organization_id)
            return FakeSession()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker_runtime, "_active_organization_ids", lambda _factory: ["org_a", "org_b"])
    monkeypatch.setattr(
        worker_runtime,
        "assessment_session_for",
        lambda user, _database_url: FakeScope(user.organization_id),
    )
    monkeypatch.setattr(
        worker_runtime,
        "get_settings",
        lambda: SimpleNamespace(
            assessment_database_url="sqlite://",
            validate_runtime_security=lambda: SimpleNamespace(assessment_database_url="sqlite://"),
        ),
    )
    monkeypatch.setattr(worker_runtime, "get_assessment_session_factory", lambda _url: lambda: FakeSession())
    monkeypatch.setattr(worker_runtime, "SupabasePrivateStorageAdapter", lambda settings: object())
    monkeypatch.setattr(
        worker_runtime,
        "CaptureProcessingWorker",
        lambda _repository, _storage: SimpleNamespace(run_once=lambda: SimpleNamespace(status="idle", run_id=None)),
    )
    monkeypatch.setattr(
        worker_runtime,
        "EvidenceProcessingWorker",
        lambda _repository: SimpleNamespace(run_once=lambda: SimpleNamespace(status="idle", run_id=None)),
    )

    result = worker_runtime.run_capture_worker_once()

    assert result == {"status": "idle", "run_id": None}
    assert scoped_organizations == ["org_a", "org_a", "org_b", "org_b"]


def test_worker_runtime_runs_one_capture_and_one_evidence_job_per_tenant(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSession:
        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeScope:
        def __init__(self, organization_id: str):
            self.organization_id = organization_id

        def __enter__(self):
            return FakeSession()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker_runtime, "_active_organization_ids", lambda _factory: ["org_a", "org_b"])
    monkeypatch.setattr(
        worker_runtime,
        "assessment_session_for",
        lambda user, _database_url: FakeScope(user.organization_id),
    )
    monkeypatch.setattr(
        worker_runtime,
        "get_settings",
        lambda: SimpleNamespace(
            assessment_database_url="sqlite://",
            validate_runtime_security=lambda: SimpleNamespace(assessment_database_url="sqlite://"),
        ),
    )
    monkeypatch.setattr(worker_runtime, "get_assessment_session_factory", lambda _url: lambda: FakeSession())
    monkeypatch.setattr(worker_runtime, "SupabasePrivateStorageAdapter", lambda settings: object())
    monkeypatch.setattr(
        worker_runtime,
        "CaptureProcessingWorker",
        lambda _repository, _storage: SimpleNamespace(
            run_once=lambda: calls.append("capture") or SimpleNamespace(status="idle", run_id=None)
        ),
    )
    monkeypatch.setattr(
        worker_runtime,
        "EvidenceProcessingWorker",
        lambda _repository: SimpleNamespace(
            run_once=lambda: calls.append("evidence") or SimpleNamespace(status="idle", run_id=None)
        ),
    )

    result = worker_runtime.run_capture_worker_once()

    assert result == {"status": "idle", "run_id": None}
    assert calls == ["capture", "evidence", "capture", "evidence"]


def test_worker_runtime_does_not_starve_evidence_or_later_tenants_when_capture_is_busy(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSession:
        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeScope:
        def __init__(self, organization_id: str):
            self.organization_id = organization_id

        def __enter__(self):
            return FakeSession()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker_runtime, "_active_organization_ids", lambda _factory: ["org_a", "org_b"])
    monkeypatch.setattr(
        worker_runtime,
        "assessment_session_for",
        lambda user, _database_url: FakeScope(user.organization_id),
    )
    monkeypatch.setattr(
        worker_runtime,
        "get_settings",
        lambda: SimpleNamespace(
            assessment_database_url="sqlite://",
            validate_runtime_security=lambda: SimpleNamespace(assessment_database_url="sqlite://"),
        ),
    )
    monkeypatch.setattr(worker_runtime, "get_assessment_session_factory", lambda _url: lambda: FakeSession())
    monkeypatch.setattr(worker_runtime, "SupabasePrivateStorageAdapter", lambda settings: object())
    monkeypatch.setattr(
        worker_runtime,
        "CaptureProcessingWorker",
        lambda repository, _storage: SimpleNamespace(
            run_once=lambda: calls.append(f"capture:{repository._worker_organization_id}")
            or SimpleNamespace(
                status="running" if repository._worker_organization_id == "org_a" else "idle",
                run_id="capture_a" if repository._worker_organization_id == "org_a" else None,
            )
        ),
    )
    monkeypatch.setattr(
        worker_runtime,
        "EvidenceProcessingWorker",
        lambda repository: SimpleNamespace(
            run_once=lambda: calls.append(f"evidence:{repository._worker_organization_id}")
            or SimpleNamespace(status="idle", run_id=None)
        ),
    )

    result = worker_runtime.run_capture_worker_once()

    assert result == {"status": "running", "run_id": "capture_a"}
    assert calls == ["capture:org_a", "evidence:org_a", "capture:org_b", "evidence:org_b"]


def test_capture_worker_uses_explicit_tenant_allowlist_for_postgres_polling() -> None:
    settings = SimpleNamespace(capture_worker_organization_ids="org_a, org_b,org_a")

    assert worker_runtime._worker_organization_ids(settings, object()) == ["org_a", "org_b"]
