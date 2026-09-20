from __future__ import annotations

import pytest

from app.core.config import Settings
from app.tasks import job_queue


def test_production_cannot_silently_fall_back_to_memory_queue(monkeypatch) -> None:
    monkeypatch.setattr(
        job_queue,
        "get_settings",
        lambda: Settings(mock_mode=False, job_queue_mode="memory"),
    )

    with pytest.raises(RuntimeError, match="durable managed queue"):
        job_queue.get_job_queue()
