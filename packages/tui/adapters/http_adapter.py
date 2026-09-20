"""HTTP Transport Adapter implementing ClinicalDataPort for live API server."""

from __future__ import annotations

import re
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from packages.tui.client import LinguaLensClient


class HttpClinicalAdapter:
    """Clinical data adapter delegating all calls to live LinguaLens FastAPI endpoints."""

    def __init__(self, client: LinguaLensClient) -> None:
        self._client = client

    def check_health(self) -> bool:
        """Check if backend API is reachable."""
        try:
            self._client._http_request("GET", "/cases")
            return True
        except Exception:
            return False

    def list_cases(self) -> list[dict[str, Any]]:
        return self._client._http_request("GET", "/cases")

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
    ) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError, LinguaLensUnsupportedOperationError

        legacy_shape = (
            child_id is not None
            or birth_year_month is not None
            or primary_language is not None
            or isinstance(age_months, str)
        )
        if legacy_shape:
            legacy_child_id = child_id if child_id is not None else child_code
            legacy_birth_month = birth_year_month if birth_year_month is not None else age_months
            legacy_language = primary_language if primary_language is not None else language
            if not isinstance(legacy_child_id, str) or not isinstance(legacy_birth_month, str):
                raise LinguaLensApiError(
                    "Legacy case creation requires child_id and birth_year_month; no age conversion was performed."
                )
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", legacy_birth_month):
                raise LinguaLensApiError(
                    "Invalid birth_year_month; expected YYYY-MM with a month from 01 through 12."
                )
            raise LinguaLensUnsupportedOperationError(
                "The live /cases API requires child_code, age_months, language and notes; "
                "birth_year_month cannot be converted without an explicit age."
            )

        if not isinstance(child_code, str) or not child_code.strip():
            raise LinguaLensApiError("Case creation requires a non-empty child_code.")
        if not isinstance(age_months, int) or isinstance(age_months, bool) or not 0 <= age_months <= 240:
            raise LinguaLensApiError("Case creation requires age_months as an integer from 0 through 240.")
        if not isinstance(language, str) or not language.strip():
            raise LinguaLensApiError("Case creation requires a non-empty language.")
        if not isinstance(notes, str):
            raise LinguaLensApiError("Case creation notes must be text.")

        payload = {
            "child_code": child_code,
            "age_months": age_months,
            "language": language,
            "notes": notes,
        }
        return self._client._http_request("POST", "/cases", payload)

    def get_session_detail(self, session_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        sess = self._client._http_request("GET", f"/sessions/{session_id}")
        if not isinstance(sess, dict) or "session_id" not in sess:
            raise LinguaLensApiError("Malformed API response: invalid session detail object.")
        return sess

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        from packages.tui.client import LinguaLensApiError
        timeline = self._client._http_request("GET", f"/cases/{case_id}/timeline")
        if not isinstance(timeline, list):
            raise LinguaLensApiError("Malformed API response: expected list from case timeline.")
        sessions = []
        for idx, event in enumerate(timeline, 1):
            if not isinstance(event, dict) or "target_id" not in event:
                continue
            session_id = event["target_id"]
            sess = self.get_session_detail(session_id)
            sess_copy = dict(sess)
            sess_copy.setdefault("session_number", idx)
            sessions.append(sess_copy)
        return sessions

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        payload = {"session_date": session_date, "session_type": "therapy_session", "notes": notes}
        return self._client._http_request("POST", f"/cases/{case_id}/sessions", payload)

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        from packages.tui.client import LinguaLensApiError
        sess = self.get_session_detail(session_id)
        tr_id = sess.get("transcript_id") if isinstance(sess, dict) else None
        if not tr_id:
            return None
        try:
            return self._client._http_request("GET", f"/sessions/{session_id}/transcript")
        except LinguaLensApiError as exc:
            if "404" in str(exc):
                return None
            raise

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        return self._client._http_request("POST", f"/sessions/{session_id}/transcript", {"text": text})

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        from packages.tui.client import LinguaLensUnsupportedOperationError
        raise LinguaLensUnsupportedOperationError(
            "Audio ingestion is unsupported in live thin-client mode. "
            "Use local mode or backend processing queue."
        )

    def update_utterance(
        self,
        transcript_id: str,
        utterance_id: str,
        new_text: str,
        new_speaker: str,
    ) -> dict[str, Any]:
        from packages.tui.client import LinguaLensUnsupportedOperationError
        raise LinguaLensUnsupportedOperationError(
            "In-place utterance editing is unsupported in live thin-client mode."
        )

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensUnsupportedOperationError
        raise LinguaLensUnsupportedOperationError(
            "Speaker auto-refinement is unsupported in live thin-client mode."
        )

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        from packages.tui.client import LinguaLensUnsupportedOperationError
        raise LinguaLensUnsupportedOperationError(
            "Speaker swapping is unsupported in live thin-client mode."
        )

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {"attested_by": therapist_name, "notes": "Attested via LinguaLens TUI"}
        return self._client._http_request("POST", f"/transcripts/{transcript_id}/attest", payload)

    def get_findings(self, session_id: str) -> dict[str, Any]:
        return self._client._http_request("GET", f"/sessions/{session_id}/features")

    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        payload = {"notes": prompt_notes}
        return self._client._http_request("POST", f"/sessions/{session_id}/reports/draft", payload)

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {
            "confirmation_checked": True,
            "therapist_name": therapist_name,
            "signed_by": therapist_name,
        }
        return self._client._http_request("POST", f"/reports/{report_id}/sign-off", payload)

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self._client._http_request("GET", f"/reports/{report_id}")

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        sess = self.get_session_detail(session_id)
        rep_id = sess.get("report_id") if isinstance(sess, dict) else None
        if rep_id:
            return self.get_report(rep_id)
        return None

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_child_input
        from packages.tui.client import LinguaLensValidationError
        try:
            norm = validate_child_input(display_code, birth_year, birth_month, language_context)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc
        return self._client._http_request("POST", "/api/v2/children", norm)

    def get_child(self, child_id: str) -> dict[str, Any]:
        return self._client._http_request("GET", f"/api/v2/children/{child_id}")

    def list_children(self) -> list[dict[str, Any]]:
        return self._client._http_request("GET", "/api/v2/children")

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_consent_input
        from packages.tui.client import LinguaLensValidationError
        try:
            norm = validate_consent_input(child_id, purpose, scope_version, status)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        payload = {
            "purpose": norm["purpose"],
            "scope_version": norm["scope_version"],
            "status": norm["status"],
        }
        return self._client._http_request("POST", f"/api/v2/children/{clean_child_id}/consents", payload)

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        return self._client._http_request("GET", f"/api/v2/children/{child_id}/consents")

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        consents = self.list_consents(child_id)
        if not consents:
            return None
        matching = [c for c in consents if c.get("purpose") == "clinical_assessment"]
        if not matching:
            return None
        sorted_consents = sorted(
            enumerate(matching),
            key=lambda item: (item[1].get("version", 0), item[0]),
            reverse=True,
        )
        latest = sorted_consents[0][1]
        if latest.get("status") == "active":
            return latest
        return None

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_assessment_input
        from packages.tui.client import LinguaLensValidationError
        try:
            norm = validate_assessment_input(child_id, purpose, assigned_clinician_id)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        payload: dict[str, Any] = {"purpose": norm["purpose"]}
        if norm["assigned_clinician_id"]:
            payload["assigned_clinician_id"] = norm["assigned_clinician_id"]
        return self._client._http_request("POST", f"/api/v2/children/{clean_child_id}/assessments", payload)

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        from packages.tui.client import LinguaLensApiError
        res = self._client._http_request("GET", f"/api/v2/children/{child_id}/assessments")
        if not isinstance(res, list):
            raise LinguaLensApiError(
                f"Malformed response from list_assessments: expected list, got {type(res).__name__}"
            )
        return res

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        return self._client._http_request("GET", f"/api/v2/assessments/{assessment_id}")
