from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.assessment_v2.domain.models import ProcessingRunStage
from app.assessment_v2.quality import MediaProbeError, MediaProbeUnavailable, MediaQuality, QualityDecision
from app.assessment_v2.worker import CaptureProcessingWorker, CaptureWorkItem


CHECKSUM = "sha256:" + "a" * 64


@dataclass
class _Repo:
    items: list[CaptureWorkItem]

    def __post_init__(self) -> None:
        self.verified: list[tuple[str, str]] = []
        self.qualities: list[tuple[str, str]] = []
        self.completed_cleanup: list[str] = []
        self.failures: list[tuple[str, str]] = []
        self.cancelled: list[tuple[str, str]] = []

    def claim_next_processing_run(self) -> CaptureWorkItem | None:
        return self.items.pop(0) if self.items else None

    def verify_recording_upload_worker(self, item: CaptureWorkItem, checksum: str) -> bool:
        self.verified.append((item.run_id, checksum))
        return True

    def persist_quality_result(
        self, item: CaptureWorkItem, quality: MediaQuality, decision: QualityDecision
    ) -> bool:
        self.qualities.append((item.run_id, decision.status))
        return True

    def complete_cleanup(self, item: CaptureWorkItem) -> None:
        self.completed_cleanup.append(item.run_id)

    def fail_processing_run(self, item: CaptureWorkItem, error_code: str) -> None:
        self.failures.append((item.run_id, error_code))

    def cancel_processing_run(self, item: CaptureWorkItem, error_code: str) -> None:
        self.cancelled.append((item.run_id, error_code))


class _Storage:
    def __init__(self, payload: bytes = b"capture") -> None:
        self.payload = payload
        self.downloads: list[str] = []
        self.deletes: list[str] = []

    def download_object(self, object_key: str) -> bytes:
        self.downloads.append(object_key)
        return self.payload

    def delete_object(self, object_key: str) -> None:
        self.deletes.append(object_key)


class _Probe:
    def __init__(self, quality: MediaQuality) -> None:
        self.quality = quality
        self.paths: list[Path] = []

    def probe(self, path: Path) -> MediaQuality:
        self.paths.append(path)
        assert path.exists()
        return self.quality


def _item(stage: ProcessingRunStage, checksum: str = CHECKSUM) -> CaptureWorkItem:
    return CaptureWorkItem(
        run_id="run_opaque_01",
        organization_id="org_opaque_01",
        recording_id="recording_opaque_01",
        stage=stage,
        object_key="capture/opaque-object",
        declared_checksum=checksum,
        declared_content_type="audio/webm",
        declared_size_bytes=7,
        minimum_duration_seconds=120,
        target_duration_seconds=180,
    )


def test_upload_worker_computes_server_checksum_before_verifying() -> None:
    payload = b"capture"
    checksum = "sha256:" + __import__("hashlib").sha256(payload).hexdigest()
    repo = _Repo([_item(ProcessingRunStage.UPLOAD_VERIFICATION, checksum)])

    result = CaptureProcessingWorker(repo, _Storage(payload)).run_once()

    assert result.status == "verified"
    assert repo.verified == [("run_opaque_01", checksum)]
    assert repo.failures == []


def test_upload_worker_rejects_checksum_mismatch_without_verifying() -> None:
    repo = _Repo([_item(ProcessingRunStage.UPLOAD_VERIFICATION)])

    result = CaptureProcessingWorker(repo, _Storage(b"wrong")).run_once()

    assert result.status == "failed"
    assert repo.verified == []
    assert repo.failures == [("run_opaque_01", "upload_verification_failed")]


def test_quality_worker_persists_observable_quality_only() -> None:
    repo = _Repo([_item(ProcessingRunStage.QUALITY_ANALYSIS)])
    probe = _Probe(MediaQuality(135.0, -24.0, 0.1, 1.0, ()))

    result = CaptureProcessingWorker(repo, _Storage(), probe=probe).run_once()

    assert result.status == "quality_recorded"
    assert repo.qualities == [("run_opaque_01", "usable")]
    assert probe.paths == [probe.paths[0]]


def test_quality_worker_records_unavailable_when_media_tools_are_missing() -> None:
    repo = _Repo([_item(ProcessingRunStage.QUALITY_ANALYSIS)])

    class _UnavailableProbe:
        def probe(self, _path: Path) -> MediaQuality:
            raise MediaProbeUnavailable("missing ffprobe")

    result = CaptureProcessingWorker(repo, _Storage(), probe=_UnavailableProbe()).run_once()

    assert result.status == "quality_unavailable"
    assert repo.qualities == [("run_opaque_01", "unavailable")]
    assert repo.failures == []


def test_quality_worker_records_probe_failure_without_fabricating_measurements() -> None:
    repo = _Repo([_item(ProcessingRunStage.QUALITY_ANALYSIS)])

    class _FailedProbe:
        def probe(self, _path: Path) -> MediaQuality:
            raise MediaProbeError("undecodable")

    result = CaptureProcessingWorker(repo, _Storage(), probe=_FailedProbe()).run_once()

    assert result.status == "quality_failed"
    assert repo.qualities == [("run_opaque_01", "failed")]
    assert repo.failures == []


def test_cleanup_worker_is_idempotent_at_storage_boundary() -> None:
    repo = _Repo([_item(ProcessingRunStage.CLEANUP)])
    storage = _Storage()
    worker = CaptureProcessingWorker(repo, storage)

    result = worker.run_once()

    assert result.status == "cleaned"
    assert storage.deletes == ["capture/opaque-object"]
    assert repo.completed_cleanup == ["run_opaque_01"]
