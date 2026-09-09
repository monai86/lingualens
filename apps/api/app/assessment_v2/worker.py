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
from contextlib import contextmanager
from collections.abc import Iterator
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
from app.core.config import MAX_CAPTURE_UPLOAD_SIZE_BYTES


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
    lease_token: str = ""


@dataclass(frozen=True, slots=True)
class WorkerResult:
    status: str
    run_id: str | None = None


class CaptureWorkerRepository(Protocol):
    def claim_next_processing_run(self) -> CaptureWorkItem | None: ...

    def commit_transaction(self) -> None: ...

    def verify_recording_upload_worker(self, item: CaptureWorkItem, checksum: str) -> bool: ...

    def persist_quality_result(
        self, item: CaptureWorkItem, quality: MediaQuality, decision: QualityDecision
    ) -> bool: ...

    def complete_cleanup(self, item: CaptureWorkItem) -> None: ...

    def fail_processing_run(self, item: CaptureWorkItem, error_code: str) -> None: ...

    def cancel_processing_run(self, item: CaptureWorkItem, error_code: str) -> None: ...


class CaptureWorkerStorage(Protocol):
    def download_object(self, object_key: str) -> bytes: ...

    def download_object_to_path(self, object_key: str, destination: str) -> None: ...

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
        commit_transaction = getattr(self.repository, "commit_transaction", None)
        if callable(commit_transaction):
            commit_transaction()
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
        if item.declared_size_bytes <= 0 or item.declared_size_bytes > MAX_CAPTURE_UPLOAD_SIZE_BYTES:
            self.repository.fail_processing_run(item, "upload_verification_failed")
            return WorkerResult("failed", item.run_id)
        with self._materialized_media(item) as media_path:
            size, digest = self._hash_file(media_path)
        if size != item.declared_size_bytes:
            self.repository.fail_processing_run(item, "upload_verification_failed")
            return WorkerResult("failed", item.run_id)
        computed = f"sha256:{digest}"
        if computed != item.declared_checksum:
            self.repository.fail_processing_run(item, "upload_verification_failed")
            return WorkerResult("failed", item.run_id)
        verified = self.repository.verify_recording_upload_worker(item, computed)
        return WorkerResult("verified" if verified else "cancelled", item.run_id)

    def _analyze_quality(self, item: CaptureWorkItem) -> WorkerResult:
        if item.declared_size_bytes <= 0 or item.declared_size_bytes > MAX_CAPTURE_UPLOAD_SIZE_BYTES:
            self.repository.fail_processing_run(item, "quality_analysis_failed")
            return WorkerResult("failed", item.run_id)
        with self._materialized_media(item) as media_path:
            if media_path.stat().st_size != item.declared_size_bytes:
                self.repository.fail_processing_run(item, "quality_analysis_failed")
                return WorkerResult("failed", item.run_id)
            try:
                quality = self.probe.probe(media_path)
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

    @contextmanager
    def _materialized_media(self, item: CaptureWorkItem) -> Iterator[Path]:
        with tempfile.NamedTemporaryFile(prefix="lingualens-capture-", suffix=".media") as temporary:
            destination = Path(temporary.name)
            download_to_path = getattr(self.storage, "download_object_to_path", None)
            if callable(download_to_path):
                download_to_path(item.object_key, temporary.name)
            else:
                payload = self.storage.download_object(item.object_key)
                if len(payload) > MAX_CAPTURE_UPLOAD_SIZE_BYTES:
                    raise StorageUnavailableError()
                temporary.write(payload)
                temporary.flush()
            yield destination

    @staticmethod
    def _hash_file(path: Path) -> tuple[int, str]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
        return size, digest.hexdigest()

    def _cleanup(self, item: CaptureWorkItem) -> WorkerResult:
        self.storage.delete_object(item.object_key)
        self.repository.complete_cleanup(item)
        return WorkerResult("cleaned", item.run_id)
