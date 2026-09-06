"""Capture V2 processing worker boundary.

The worker is deliberately small and injectable. Durable processing-run state
and retry policy belong to the repository; this module only performs one safe
claimed unit of work at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tempfile
from typing import Protocol

from app.assessment_v2.domain.models import ProcessingRunStage
from app.assessment_v2.quality import (
    MediaProbeError,
    MediaProbeUnavailable,
    MediaQuality,
    QualityDecision,
    SubprocessMediaProbe,
    evaluate_quality,
)
from app.assessment_v2.storage import StorageUnavailableError


@dataclass(frozen=True, slots=True)
class CaptureWorkItem:
    run_id: str
    organization_id: str
    recording_id: str
    stage: ProcessingRunStage
    object_key: str
    declared_checksum: str
    declared_content_type: str
    declared_size_bytes: int
    minimum_duration_seconds: int
    target_duration_seconds: int


@dataclass(frozen=True, slots=True)
class WorkerResult:
    status: str
    run_id: str | None = None


class CaptureWorkerRepository(Protocol):
    def claim_next_processing_run(self) -> CaptureWorkItem | None: ...

    def verify_recording_upload_worker(self, item: CaptureWorkItem, checksum: str) -> bool: ...

    def persist_quality_result(
        self, item: CaptureWorkItem, quality: MediaQuality, decision: QualityDecision
    ) -> bool: ...

    def complete_cleanup(self, item: CaptureWorkItem) -> None: ...

    def fail_processing_run(self, item: CaptureWorkItem, error_code: str) -> None: ...

    def cancel_processing_run(self, item: CaptureWorkItem, error_code: str) -> None: ...


class CaptureWorkerStorage(Protocol):
    def download_object(self, object_key: str) -> bytes: ...

    def delete_object(self, object_key: str) -> object: ...


class CaptureMediaProbe(Protocol):
    def probe(self, media_path: Path) -> MediaQuality: ...


class CaptureProcessingWorker:
    """Process one database-claimed capture run without clinical inference."""

    def __init__(
        self,
        repository: CaptureWorkerRepository,
        storage: CaptureWorkerStorage,
        *,
        probe: CaptureMediaProbe | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.probe = probe or SubprocessMediaProbe()

    def run_once(self) -> WorkerResult:
        item = self.repository.claim_next_processing_run()
        if item is None:
            return WorkerResult("idle")
        try:
            if item.stage is ProcessingRunStage.UPLOAD_VERIFICATION:
                return self._verify_upload(item)
            if item.stage is ProcessingRunStage.QUALITY_ANALYSIS:
                return self._analyze_quality(item)
            if item.stage is ProcessingRunStage.CLEANUP:
                return self._cleanup(item)
            self.repository.fail_processing_run(item, "unsupported_processing_stage")
            return WorkerResult("failed", item.run_id)
        except StorageUnavailableError:
            self.repository.fail_processing_run(item, "storage_unavailable")
            return WorkerResult("failed", item.run_id)
        except (OSError, ValueError):
            self.repository.fail_processing_run(item, "processing_failed")
            return WorkerResult("failed", item.run_id)

    def _verify_upload(self, item: CaptureWorkItem) -> WorkerResult:
        payload = self.storage.download_object(item.object_key)
        if len(payload) != item.declared_size_bytes:
            self.repository.fail_processing_run(item, "upload_verification_failed")
            return WorkerResult("failed", item.run_id)
        computed = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        if computed != item.declared_checksum:
            self.repository.fail_processing_run(item, "upload_verification_failed")
            return WorkerResult("failed", item.run_id)
        verified = self.repository.verify_recording_upload_worker(item, computed)
        return WorkerResult("verified" if verified else "cancelled", item.run_id)

    def _analyze_quality(self, item: CaptureWorkItem) -> WorkerResult:
        payload = self.storage.download_object(item.object_key)
        if len(payload) != item.declared_size_bytes:
            self.repository.fail_processing_run(item, "quality_analysis_failed")
            return WorkerResult("failed", item.run_id)
        with tempfile.NamedTemporaryFile(prefix="lingualens-capture-", suffix=".media") as temporary:
            temporary.write(payload)
            temporary.flush()
            try:
                quality = self.probe.probe(Path(temporary.name))
            except MediaProbeUnavailable:
                quality = MediaQuality(
                    duration_seconds=None,
                    loudness_db=None,
                    silence_ratio=None,
                    decodability=None,
                    unavailable_checks=("duration", "loudness", "silence_ratio", "decodability"),
                )
                decision = evaluate_quality(
                    quality,
                    minimum_duration_seconds=item.minimum_duration_seconds,
                    target_duration_seconds=item.target_duration_seconds,
                )
                persisted = self.repository.persist_quality_result(item, quality, decision)
                return WorkerResult("quality_unavailable" if persisted else "cancelled", item.run_id)
            except MediaProbeError:
                quality = MediaQuality(
                    duration_seconds=None,
                    loudness_db=None,
                    silence_ratio=None,
                    decodability=0.0,
                    unavailable_checks=(),
                )
                persisted = self.repository.persist_quality_result(
                    item,
                    quality,
                    QualityDecision(status="failed", unavailable_checks=()),
                )
                return WorkerResult("quality_failed" if persisted else "cancelled", item.run_id)
        decision = evaluate_quality(
            quality,
            minimum_duration_seconds=item.minimum_duration_seconds,
            target_duration_seconds=item.target_duration_seconds,
        )
        persisted = self.repository.persist_quality_result(item, quality, decision)
        return WorkerResult("quality_recorded" if persisted else "cancelled", item.run_id)

    def _cleanup(self, item: CaptureWorkItem) -> WorkerResult:
        self.storage.delete_object(item.object_key)
        self.repository.complete_cleanup(item)
        return WorkerResult("cleaned", item.run_id)
