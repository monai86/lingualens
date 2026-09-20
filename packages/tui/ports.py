"""Port definitions for LinguaLens clinical data access."""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class ClinicalDataPort(Protocol):
    """Abstract port interface for LinguaLens clinical data access.

    Decouples client transport and in-memory mock execution into discrete adapters.
    """

    def check_health(self) -> bool: ...

    def list_cases(self) -> list[dict[str, Any]]: ...

    def create_case(
        self,
        child_code: str | None = None,
        age_months: int | str | None = None,
        language: str = "th",
        notes: str = "",
        *,
        child_id: str | None = None,
        birth_year_month: str | None = None,
        primary_language: str | None = None,
    ) -> dict[str, Any]: ...

    def get_session_detail(self, session_id: str) -> dict[str, Any]: ...

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]: ...

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]: ...

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None: ...

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]: ...

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]: ...

    def update_utterance(
        self,
        transcript_id: str,
        utterance_id: str,
        new_text: str,
        new_speaker: str,
    ) -> dict[str, Any]: ...

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]: ...

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]: ...

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]: ...

    def get_findings(self, session_id: str) -> dict[str, Any]: ...

    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]: ...

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]: ...

    def get_report(self, report_id: str) -> dict[str, Any] | None: ...

    def get_session_report(self, session_id: str) -> dict[str, Any] | None: ...

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def get_child(self, child_id: str) -> dict[str, Any]: ...

    def list_children(self) -> list[dict[str, Any]]: ...

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]: ...

    def list_consents(self, child_id: str) -> list[dict[str, Any]]: ...

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None: ...

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]: ...

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]: ...

    def get_assessment(self, assessment_id: str) -> dict[str, Any]: ...
