"""Database-backed worker for descriptive Evidence V2 extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.assessment_v2.db.repositories import EvidenceWorkItem, RepositoryError
from app.assessment_v2.evidence_adapter import AdaptedEvidence, adapt_analysis_result
from app.assessment_v2.reviewed_transcript_worker import extract_reviewed_segment_set


@dataclass(frozen=True, slots=True)
class EvidenceWorkerResult:
    status: str
    run_id: str | None = None


class EvidenceWorkerRepository(Protocol):
    def claim_next_evidence_processing_run(self) -> EvidenceWorkItem | None: ...

    def commit_transaction(self) -> None: ...

    def complete_evidence_processing_run(
        self, item: EvidenceWorkItem, adapted: AdaptedEvidence
    ) -> object | None: ...

    def fail_evidence_processing_run(
        self,
        item: EvidenceWorkItem,
        error_code: str,
        *,
        retryable: bool,
    ) -> object: ...


class EvidenceProcessingWorker:
    """Process one leased transcript without making a clinical conclusion."""

    def __init__(self, repository: EvidenceWorkerRepository) -> None:
        self.repository = repository

    def run_once(self) -> EvidenceWorkerResult:
        item = self.repository.claim_next_evidence_processing_run()
        if item is None:
            return EvidenceWorkerResult("idle")
        commit_transaction = getattr(self.repository, "commit_transaction", None)
        if callable(commit_transaction):
            commit_transaction()
        try:
            if item.segment_set is None:
                raise RepositoryError("segment_provenance_missing")
            analysis = extract_reviewed_segment_set(
                item.transcript,
                item.segment_set,
                protocol_version_key=item.protocol_version_key,
            )
            adapted = adapt_analysis_result(
                analysis,
                input_sha256=item.transcript.content_sha256,
                protocol_version_key=item.protocol_version_key,
                expected_feature_schema_version=item.feature_schema_version,
            )
            saved = self.repository.complete_evidence_processing_run(item, adapted)
            return EvidenceWorkerResult(
                "evidence_recorded" if saved is not None else "cancelled",
                item.run_id,
            )
        except (OSError, RuntimeError, TimeoutError):
            self.repository.fail_evidence_processing_run(
                item,
                "evidence_processing_failed",
                retryable=True,
            )
            return EvidenceWorkerResult("failed", item.run_id)
        except (RepositoryError, ValueError):
            self.repository.fail_evidence_processing_run(
                item,
                "evidence_processing_invalid",
                retryable=False,
            )
            return EvidenceWorkerResult("failed", item.run_id)
