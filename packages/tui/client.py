"""LinguaLens TUI API Client with decoupled HTTP and In-Memory Clinical Adapters.

In live mode (`mock_mode=False`), all operations communicate with the backend API or
fail closed with structured exceptions (`LinguaLensApiError`). Local mock data is never
mutated in live mode. Explicit local mode (`mock_mode=True`) is reserved for demos and research.
"""

from __future__ import annotations

import email.utils
import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from packages.tui.adapters.http_adapter import HttpClinicalAdapter
from packages.tui.adapters.memory_adapter import InMemoryClinicalAdapter
from packages.tui.ports import ClinicalDataPort
from packages.tui.validation import (
    LinguaLensValidationError as _BaseValidationError,
    calculate_age_in_months,
    validate_assessment_input,
    validate_child_input,
    validate_consent_input,
)

DEFAULT_API_URL = os.environ.get("LINGUALENS_API_URL", "http://localhost:8000/api/v1")


class LinguaLensApiError(RuntimeError):
    """Base error for LinguaLens API communication failures."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LinguaLensAuthError(LinguaLensApiError):
    """Authentication failure (HTTP 401)."""
    pass


class LinguaLensPermissionError(LinguaLensApiError):
    """Permission denied (HTTP 403)."""
    pass


class LinguaLensConflictError(LinguaLensApiError):
    """Resource state conflict (HTTP 409)."""
    pass


class LinguaLensRateLimitError(LinguaLensApiError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LinguaLensServerError(LinguaLensApiError):
    """Server-side execution failure (HTTP 500+)."""
    pass


class LinguaLensUnsupportedOperationError(LinguaLensApiError):
    """Operation unsupported in current live/local client mode."""
    pass


class LinguaLensValidationError(LinguaLensApiError, _BaseValidationError):
    """Client input failed canonical V2 transport validation."""
    pass


@dataclass(frozen=True)
class ClientSession:
    """Active client authenticated session representation."""
    access_token: str
    organization_id: str | None = None
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generation: int = 1
    created_at: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        tok = self.access_token
        masked = f"{tok[:4]}...{tok[-4:]}" if len(tok) > 8 else "***"
        return f"ClientSession(organization_id={self.organization_id!r}, token_id={self.token_id!r}, generation={self.generation}, access_token='{masked}')"

    def __str__(self) -> str:
        return self.__repr__()


def _get_current_utc_time() -> datetime:
    """Return current UTC time; factored for deterministic clock injection in testing."""
    return datetime.now(timezone.utc)


def _parse_retry_after(retry_header: str | None) -> float | None:
    """Safely parse HTTP Retry-After header supporting delta-seconds and RFC HTTP-date formats."""
    if not retry_header:
        return None
    retry_str = retry_header.strip()
    if not retry_str:
        return None

    try:
        val = float(retry_str)
        if math.isnan(val) or math.isinf(val):
            return None
        return max(0.0, val)
    except (ValueError, TypeError):
        pass

    try:
        dt = email.utils.parsedate_to_datetime(retry_str)
        if dt is not None:
            now = _get_current_utc_time()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta_sec = (dt - now).total_seconds()
            return max(0.0, float(delta_sec))
    except Exception:
        pass

    return None


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents credential and tenant header leakage across origins, and rejects mutation redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req.get_method() in ("POST", "PUT", "PATCH", "DELETE"):
            raise LinguaLensApiError(
                f"HTTP {code} redirect rejected for {req.get_method()} mutation to prevent unintended method conversion or replay."
            )

        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req:
            orig_parsed = urllib.parse.urlparse(req.full_url)
            new_parsed = urllib.parse.urlparse(newurl)
            orig_port = orig_parsed.port or (443 if orig_parsed.scheme == "https" else 80)
            new_port = new_parsed.port or (443 if new_parsed.scheme == "https" else 80)

            is_cross_origin = (orig_parsed.scheme, orig_parsed.hostname, orig_port) != (new_parsed.scheme, new_parsed.hostname, new_port)
            is_https_downgrade = (orig_parsed.scheme == "https" and new_parsed.scheme == "http")

            if is_cross_origin or is_https_downgrade:
                strip_keys = {"authorization", "x-organization-id", "cookie"}
                new_req.headers = {k: v for k, v in new_req.headers.items() if k.lower() not in strip_keys}
                new_req.unredirected_hdrs = {k: v for k, v in new_req.unredirected_hdrs.items() if k.lower() not in strip_keys}
        return new_req


class LinguaLensClient:
    """Client for interacting with LinguaLens Backend API via pluggable adapters."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_URL,
        mock_mode: bool = False,
        seed_demo: bool = False,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.mock_mode = mock_mode
        self._session_lock = threading.Lock()
        self._session_generation: int = 0
        self._session: ClientSession | None = None
        self._opener = urllib.request.build_opener(_SafeRedirectHandler())
        self._clock = clock
        self.__mock_data: dict[str, Any] = self._init_mock_data(seed_demo=seed_demo)

        if self.mock_mode:
            self._adapter: ClinicalDataPort = InMemoryClinicalAdapter(
                seed_demo=seed_demo,
                clock=self._get_now,
            )
            self.__mock_data = self._adapter.mock_data
        else:
            self._adapter = HttpClinicalAdapter(client=self)

    @property
    def _mock_data(self) -> dict[str, Any]:
        if hasattr(self, "_adapter") and hasattr(self._adapter, "mock_data"):
            return self._adapter.mock_data
        return self.__mock_data

    @_mock_data.setter
    def _mock_data(self, val: dict[str, Any]) -> None:
        self.__mock_data = val
        if hasattr(self, "_adapter") and hasattr(self._adapter, "mock_data"):
            self._adapter.mock_data = val

    def _get_now(self) -> datetime:
        """Return current time; honors injected clock for deterministic testing."""
        if callable(getattr(self, "_clock", None)):
            return self._clock()
        return _get_current_utc_time()

    def seed_demo_dataset(self) -> None:
        """Explicitly seed demo cases and transcripts for demonstration or tutorial."""
        if isinstance(self._adapter, InMemoryClinicalAdapter):
            self._adapter.seed_demo_dataset()
            self.__mock_data = self._adapter.mock_data
        else:
            self.__mock_data = self._init_mock_data(seed_demo=True)

    def clear_mock_data(self) -> None:
        """Reset all in-memory mock cases and clinical data to a completely clean state."""
        if isinstance(self._adapter, InMemoryClinicalAdapter):
            self._adapter.clear_mock_data()
            self.__mock_data = self._adapter.mock_data
        else:
            self.__mock_data = self._init_mock_data(seed_demo=False)

    def _init_mock_data(self, seed_demo: bool = False) -> dict[str, Any]:
        """Initialize clean in-memory mock representation."""
        adapter = InMemoryClinicalAdapter(seed_demo=seed_demo, clock=self._get_now)
        return adapter.mock_data

    # Authentication & Session Management
    def set_session(self, access_token: str, organization_id: str | None = None) -> ClientSession:
        with self._session_lock:
            self._session_generation += 1
            sess = ClientSession(
                access_token=access_token,
                organization_id=organization_id,
                generation=self._session_generation,
            )
            self._session = sess
            return sess

    def get_session(self) -> ClientSession | None:
        with self._session_lock:
            return self._session

    def clear_session(self) -> None:
        with self._session_lock:
            self._session = None

    def _handle_auth_failure(self, failed_session_generation: int | None = None, token_used: str | None = None) -> None:
        with self._session_lock:
            if not self._session:
                return
            if failed_session_generation is not None:
                if self._session.generation == failed_session_generation:
                    self._session = None
            elif token_used is not None:
                if self._session.access_token == token_used:
                    self._session = None
            else:
                self._session = None

    def _http_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        if endpoint.startswith("/api/v2"):
            if self.base_url.endswith("/api/v1"):
                url = f"{self.base_url[:-7]}{endpoint}"
            else:
                url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        req_data = json.dumps(data).encode("utf-8") if data is not None else None

        with self._session_lock:
            active_session = self._session

        session_gen: int | None = active_session.generation if active_session else None
        token_used: str | None = active_session.access_token if active_session else None

        if active_session and active_session.access_token:
            base_p = urllib.parse.urlparse(self.base_url)
            req_p = urllib.parse.urlparse(url)
            base_port = base_p.port or (443 if base_p.scheme == "https" else 80)
            req_port = req_p.port or (443 if req_p.scheme == "https" else 80)
            if (base_p.scheme, base_p.hostname, base_port) == (req_p.scheme, req_p.hostname, req_port):
                headers["Authorization"] = f"Bearer {active_session.access_token}"
                if active_session.organization_id:
                    headers["X-Organization-ID"] = active_session.organization_id

        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=3.0) as resp:
                resp_text = resp.read().decode("utf-8")
                if not resp_text:
                    return {}
                try:
                    return json.loads(resp_text)
                except Exception:
                    raise LinguaLensApiError("API request returned malformed JSON response.") from None
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self._handle_auth_failure(failed_session_generation=session_gen, token_used=token_used)
                raise LinguaLensAuthError("Authentication failed: HTTP 401 Session expired or invalid token.") from None
            elif exc.code == 403:
                raise LinguaLensPermissionError("Permission denied: HTTP 403 Action forbidden for current role.") from None
            elif exc.code == 409:
                raise LinguaLensConflictError("Conflict error: HTTP 409 Resource state conflict or concurrent edit.") from None
            elif exc.code == 429:
                retry_val = exc.headers.get("Retry-After") if exc.headers else None
                retry_sec = _parse_retry_after(retry_val)
                raise LinguaLensRateLimitError(
                    "Rate limit exceeded: HTTP 429 Too many requests. Retry later.",
                    retry_after_seconds=retry_sec,
                ) from None
            elif exc.code >= 500:
                raise LinguaLensServerError(f"Server error: HTTP {exc.code} Internal server failure.") from None
            else:
                raise LinguaLensApiError(f"API request failed: HTTP {exc.code}.") from None
        except urllib.error.URLError:
            raise LinguaLensApiError("API connection failed. Service is currently unavailable.") from None
        except LinguaLensApiError:
            raise
        except Exception:
            raise LinguaLensApiError("API request failed unexpectedly.") from None

    def _http_request_bytes(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> bytes:
        if endpoint.startswith("/api/v2"):
            if self.base_url.endswith("/api/v1"):
                url = f"{self.base_url[:-7]}{endpoint}"
            else:
                url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/octet-stream"}

        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        if req_data:
            headers["Content-Type"] = "application/json"

        with self._session_lock:
            active_session = self._session

        session_gen: int | None = active_session.generation if active_session else None
        token_used: str | None = active_session.access_token if active_session else None

        if active_session and active_session.access_token:
            base_p = urllib.parse.urlparse(self.base_url)
            req_p = urllib.parse.urlparse(url)
            base_port = base_p.port or (443 if base_p.scheme == "https" else 80)
            req_port = req_p.port or (443 if req_p.scheme == "https" else 80)
            if (base_p.scheme, base_p.hostname, base_port) == (req_p.scheme, req_p.hostname, req_port):
                headers["Authorization"] = f"Bearer {active_session.access_token}"
                if active_session.organization_id:
                    headers["X-Organization-ID"] = active_session.organization_id

        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=5.0) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self._handle_auth_failure(failed_session_generation=session_gen, token_used=token_used)
                raise LinguaLensAuthError("Authentication failed: HTTP 401 Session expired or invalid token.") from None
            elif exc.code == 403:
                raise LinguaLensPermissionError("Permission denied: HTTP 403 Action forbidden for current role.") from None
            elif exc.code == 409:
                raise LinguaLensConflictError("Conflict error: HTTP 409 Resource state conflict or concurrent edit.") from None
            elif exc.code == 429:
                retry_val = exc.headers.get("Retry-After") if exc.headers else None
                retry_sec = _parse_retry_after(retry_val)
                raise LinguaLensRateLimitError(
                    "Rate limit exceeded: HTTP 429 Too many requests. Retry later.",
                    retry_after_seconds=retry_sec,
                ) from None
            elif exc.code >= 500:
                raise LinguaLensServerError(f"Server error: HTTP {exc.code} Internal server failure.") from None
            else:
                raise LinguaLensApiError(f"API request failed: HTTP {exc.code}.") from None
        except urllib.error.URLError:
            raise LinguaLensApiError("API connection failed. Service is currently unavailable.") from None
        except LinguaLensApiError:
            raise
        except Exception:
            raise LinguaLensApiError("API request failed unexpectedly.") from None

    # Delegated Clinical Domain Operations
    def check_health(self) -> bool:
        """Check if backend API is reachable."""
        return self._adapter.check_health()

    def list_cases(self) -> list[dict[str, Any]]:
        """List all clinical cases."""
        return self._adapter.list_cases()

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
        """Create a clinical case via adapter."""
        return self._adapter.create_case(
            child_code=child_code,
            age_months=age_months,
            language=language,
            notes=notes,
            child_id=child_id,
            birth_year_month=birth_year_month,
            primary_language=primary_language,
        )

    def _create_case_from_birth_year_month(
        self,
        *,
        child_id: str,
        birth_year_month: str,
        primary_language: str,
        notes: str,
    ) -> dict[str, Any]:
        """Backward compatible delegate for legacy case creation."""
        if hasattr(self._adapter, "_create_case_from_birth_year_month"):
            return self._adapter._create_case_from_birth_year_month(
                child_id=child_id,
                birth_year_month=birth_year_month,
                primary_language=primary_language,
                notes=notes,
            )
        return self.create_case(
            child_id=child_id,
            birth_year_month=birth_year_month,
            primary_language=primary_language,
            notes=notes,
        )

    def get_session_detail(self, session_id: str) -> dict[str, Any]:
        """Retrieve clinical therapy session details."""
        return self._adapter.get_session_detail(session_id)

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        """List sessions for a case."""
        return self._adapter.list_sessions(case_id)

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        """Create a session under a case."""
        return self._adapter.create_session(case_id, session_date, notes)

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session transcript."""
        return self._adapter.get_session_transcript(session_id)

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        """Ingest raw dialogue text or CHAT transcript."""
        return self._adapter.ingest_transcript_text(session_id, text)

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Ingest audio/video file."""
        return self._adapter.ingest_audio_file(session_id, audio_path, progress_callback)

    def update_utterance(
        self,
        transcript_id: str,
        utterance_id: str,
        new_text: str,
        new_speaker: str,
    ) -> dict[str, Any]:
        """Update single utterance text and speaker assignment."""
        return self._adapter.update_utterance(transcript_id, utterance_id, new_text, new_speaker)

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        """Automatically refine speaker assignments using clinical dialogue turn-taking rules."""
        return self._adapter.auto_refine_speakers(transcript_id)

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        """Swap two speaker roles across all utterances."""
        return self._adapter.swap_speakers(transcript_id, spk1, spk2)

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        """Attest and sign-off on transcript review."""
        return self._adapter.attest_transcript(transcript_id, therapist_name)

    def get_findings(self, session_id: str) -> dict[str, Any]:
        """Retrieve developmental metrics and guideline links."""
        return self._adapter.get_findings(session_id)

    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        """Draft a clinical evaluation report."""
        return self._adapter.draft_report(session_id, prompt_notes)

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        """Finalize and cryptographically sign off on a clinical report."""
        return self._adapter.sign_off_report(report_id, therapist_name)

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Get report by ID."""
        return self._adapter.get_report(report_id)

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        """Get report for a given session."""
        return self._adapter.get_session_report(session_id)

    # Assessment V2 Endpoints
    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create child profile (V2)."""
        return self._adapter.create_child(display_code, birth_year, birth_month, language_context)

    def get_child(self, child_id: str) -> dict[str, Any]:
        """Retrieve child profile (V2)."""
        return self._adapter.get_child(child_id)

    def list_children(self) -> list[dict[str, Any]]:
        """List all child profiles (V2)."""
        return self._adapter.list_children()

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        """Record consent for a child (V2)."""
        return self._adapter.record_consent(child_id, purpose, scope_version, status)

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        """List consent records for a child (V2)."""
        return self._adapter.list_consents(child_id)

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        """Find active consent for clinical assessment (V2)."""
        return self._adapter.get_active_consent(child_id)

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a clinical assessment (V2)."""
        return self._adapter.create_assessment(child_id, purpose, assigned_clinician_id)

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        """List assessments for a child (V2)."""
        return self._adapter.list_assessments(child_id)

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        """Retrieve assessment details (V2)."""
        return self._adapter.get_assessment(assessment_id)

    def get_waveform_peaks(self, session_id: str) -> bytes:
        """Fetch binary waveform peaks for session audio visualization."""
        return self._adapter.get_waveform_peaks(session_id)

    def get_playback_grant(self, session_id: str) -> dict[str, Any]:
        """Request time-limited consent-gated audio playback grant."""
        return self._adapter.get_playback_grant(session_id)

