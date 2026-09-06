from __future__ import annotations

from pathlib import Path

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
