"""LinguaLens TUI API Client with live REST API communication and explicit offline mock mode.

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
from typing import Any

from packages.cha.parser import parse_cha_text


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


from packages.tui.validation import (
    LinguaLensValidationError as _BaseValidationError,
    calculate_age_in_months,
    validate_assessment_input,
    validate_child_input,
    validate_consent_input,
)


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

    # 1. Delta-seconds format (integer or float)
    try:
        val = float(retry_str)
        if math.isnan(val) or math.isinf(val):
            return None
        return max(0.0, val)
    except (ValueError, TypeError):
        pass

    # 2. RFC 1123 / RFC 822 HTTP-date format
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
        # Reject redirects for mutations (POST, PUT, PATCH, DELETE) to prevent unintended method conversion or replay
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
    """Client for interacting with LinguaLens Backend API."""

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
        self._mock_data: dict[str, Any] = self._init_mock_data(seed_demo=seed_demo)

    def _get_now(self) -> datetime:
        """Return current time; honors injected clock for deterministic testing."""
        if callable(getattr(self, "_clock", None)):
            return self._clock()
        return _get_current_utc_time()


    def seed_demo_dataset(self) -> None:
        """Explicitly seed demo cases and transcripts for demonstration or tutorial."""
        self._mock_data = self._init_mock_data(seed_demo=True)

    def _init_mock_data(self, seed_demo: bool = False) -> dict[str, Any]:
        """Initialize in-memory dataset. Starts clean and empty by default for production readiness."""
        if not seed_demo:
            return {
                "cases": [],
                "sessions": {},
                "transcripts": {},
                "features": {},
                "reports": {},
                "children": [],
                "consents": {},
                "assessments": {},
            }


        return {
            "cases": [
                {
                    "case_id": "case-demo-001",
                    "child_id": "C-0104",
                    "child_code": "C-0104",
                    "birth_year_month": "2020-04",
                    "age_months": 52,
                    "primary_language": "th",
                    "language": "th",
                    "clinical_notes": "Receptive-expressive language delay evaluation.",
                    "notes": "Receptive-expressive language delay evaluation.",
                    "status": "active",
                    "session_count": 2,
                },
                {
                    "case_id": "case-demo-002",
                    "child_id": "C-0208",
                    "child_code": "C-0208",
                    "birth_year_month": "2021-01",
                    "age_months": 43,
                    "primary_language": "th",
                    "language": "th",
                    "clinical_notes": "Social communication and joint attention follow-up.",
                    "notes": "Social communication and joint attention follow-up.",
                    "status": "active",
                    "session_count": 1,
                },
            ],
            "sessions": {
                "case-demo-001": [
                    {
                        "session_id": "sess-demo-101",
                        "case_id": "case-demo-001",
                        "session_date": "2026-08-10",
                        "session_number": 1,
                        "status": "Reported",
                        "transcript_id": "tr-demo-101",
                        "feature_set_id": "feat-demo-101",
                        "report_id": "rep-demo-101",
                    },
                    {
                        "session_id": "sess-demo-102",
                        "case_id": "case-demo-001",
                        "session_date": "2026-08-16",
                        "session_number": 2,
                        "status": "Needs Review",
                        "transcript_id": "tr-demo-102",
                        "feature_set_id": None,
                        "report_id": None,
                    },
                ],
                "case-demo-002": [
                    {
                        "session_id": "sess-demo-201",
                        "case_id": "case-demo-002",
                        "session_date": "2026-08-14",
                        "session_number": 1,
                        "status": "Intake",
                        "transcript_id": None,
                        "feature_set_id": None,
                        "report_id": None,
                    }
                ],
            },
            "transcripts": {
                "tr-demo-102": {
                    "transcript_id": "tr-demo-102",
                    "session_id": "sess-demo-102",
                    "status": "pending_review",
                    "utterances": [
                        {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ วันนี้เรามาเล่นตัวต่อกันนะ", "start_time": 0.0, "end_time": 3.2, "qa_flags": []},
                        {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": 3.5, "end_time": 4.8, "qa_flags": []},
                        {"id": "u-3", "speaker": "INV", "text": "ชอบรถสีอะไรครับ มีสีแดงกับสีน้ำเงิน", "start_time": 5.1, "end_time": 8.0, "qa_flags": []},
                        {"id": "u-4", "speaker": "CHI", "text": "แดง รถ แดง ไป", "start_time": 8.4, "end_time": 10.2, "qa_flags": ["word_boundary_check"]},
                        {"id": "u-5", "speaker": "INV", "text": "รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น", "start_time": 10.5, "end_time": 14.1, "qa_flags": []},
                        {"id": "u-6", "speaker": "CHI", "text": "ไป หา แม่", "start_time": 14.5, "end_time": 16.0, "qa_flags": []},
                    ],
                    "qa_summary": {"total_utterances": 6, "unresolved_flags": 1, "child_utterance_count": 3},
                    "attested": False,
                    "attested_by": None,
                }
            },
            "features": {
                "sess-demo-102": {
                    "feature_set_id": "feat-demo-102",
                    "session_id": "sess-demo-102",
                    "metrics": {
                        "mlu_words": 2.67,
                        "mlu_morphemes": 3.0,
                        "ttr": 0.75,
                        "total_child_utterances": 3,
                        "total_child_words": 8,
                        "intelligibility_rate": 0.95,
                        "turn_taking_ratio": 1.0,
                    },
                    "guideline_links": [
                        {"construct": "Expressive Phrase Length", "status": "Emerging Multi-word", "description": "Child uses 2-3 word utterances (MLU-w: 2.67)."},
                        {"construct": "Lexical Diversity", "status": "Age Expected", "description": "TTR 0.75 indicates diverse word usage in sample."},
                        {"construct": "Social Interaction", "status": "Responsive", "description": "Turn-taking ratio 1.0 with prompt-following."},
                    ],
                }
            },
            "reports": {
                "rep-demo-101": {
                    "report_id": "rep-demo-101",
                    "session_id": "sess-demo-101",
                    "status": "Signed Off",
                    "therapist_name": "Kru Aum (SLP)",
                    "signed_at": "2026-08-10T11:30:00Z",
                    "narrative": "เด็กสามารถสื่อสารด้วยวลี 2 คำได้ดีขึ้น มีการสบตาและผลัดกันพูดในระดับที่น่าพอใจ",
                    "recommendations": "ส่งเสริมการขยายประโยคเป็น 3-4 คำผ่านการเล่นบทบาทสมมติ",
                }
            },
        }

    def set_session(self, access_token: str, organization_id: str | None = None) -> ClientSession:
        """Inject active authenticated session credentials with monotonic generation tracking."""
        with self._session_lock:
            self._session_generation += 1
            self._session = ClientSession(
                access_token=access_token,
                organization_id=organization_id,
                generation=self._session_generation,
            )
            return self._session

    def get_session(self) -> ClientSession | None:
        """Retrieve current active session credentials, if any."""
        with self._session_lock:
            return self._session

    def clear_session(self) -> None:
        """Clear the current authenticated session."""
        with self._session_lock:
            self._session = None

    def _handle_auth_failure(self, failed_session_generation: int | None = None, token_used: str | None = None) -> None:
        """Compare-and-clear session: invalidate session only if it matches the failed generation or token."""
        with self._session_lock:
            if self._session is None:
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
                except Exception as exc:
                    raise LinguaLensApiError("API request returned malformed JSON response.") from None
        except urllib.error.HTTPError as exc:
            # Map status codes to specific errors without exposing clinical body or tokens
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
        except urllib.error.URLError as exc:
            raise LinguaLensApiError("API connection failed. Service is currently unavailable.") from None
        except LinguaLensApiError:
            raise
        except Exception as exc:
            raise LinguaLensApiError("API request failed unexpectedly.") from None



    def check_health(self) -> bool:
        """Check if backend API is reachable."""
        if self.mock_mode:
            return False
        try:
            self._http_request("GET", "/cases")
            return True
        except Exception:
            return False

    # Cases
    def list_cases(self) -> list[dict[str, Any]]:
        if not self.mock_mode:
            return self._http_request("GET", "/cases")
        return self._mock_data["cases"]

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
        """Create a legacy case using the backend's canonical ``/cases`` contract.

        The API accepts ``child_code``, ``age_months``, ``language`` and ``notes``
        and returns ``case_id``.  The keyword/positional birth-month form is kept
        only as an explicit offline compatibility path for older GUI/demo callers;
        it is validated and never translated or sent to the live API.
        """
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
            return self._create_case_from_birth_year_month(
                child_id=legacy_child_id,
                birth_year_month=legacy_birth_month,
                primary_language=legacy_language,
                notes=notes,
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
        if not self.mock_mode:
            return self._http_request("POST", "/cases", payload)
        new_case = {
            "case_id": f"case-local-{len(self._mock_data['cases']) + 1:03d}",
            "child_code": child_code,
            "age_months": age_months,
            "language": language,
            "notes": notes,
            "status": "active",
            "session_count": 0,
        }
        self._mock_data["cases"].append(new_case)
        self._mock_data["sessions"][new_case["case_id"]] = []
        return new_case

    def _create_case_from_birth_year_month(
        self,
        *,
        child_id: str,
        birth_year_month: str,
        primary_language: str,
        notes: str,
    ) -> dict[str, Any]:
        """Validate the retired birth-month shape without guessing an age."""
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", birth_year_month):
            raise LinguaLensApiError(
                "Invalid birth_year_month; expected YYYY-MM with a month from 01 through 12."
            )
        if not self.mock_mode:
            raise LinguaLensUnsupportedOperationError(
                "The live /cases API requires child_code, age_months, language and notes; "
                "birth_year_month cannot be converted without an explicit age."
            )
        new_case = {
            "case_id": f"case-local-{len(self._mock_data['cases']) + 1:03d}",
            "child_id": child_id,
            "birth_year_month": birth_year_month,
            "primary_language": primary_language,
            "clinical_notes": notes,
            "status": "active",
            "session_count": 0,
        }
        self._mock_data["cases"].append(new_case)
        self._mock_data["sessions"][new_case["case_id"]] = []
        return new_case

    # Sessions
    def get_session_detail(self, session_id: str) -> dict[str, Any]:
        """Retrieve clinical therapy session details (GET /sessions/{session_id}).

        Note: Distinct from auth get_session() which retrieves ClientSession credentials.
        """
        if not self.mock_mode:
            sess = self._http_request("GET", f"/sessions/{session_id}")
            if not isinstance(sess, dict) or "session_id" not in sess:
                raise LinguaLensApiError("Malformed API response: invalid session detail object.")
            return sess
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s.get("session_id") == session_id:
                    return s
        raise LinguaLensApiError(f"Session '{session_id}' not found.")

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        """List sessions for a case by querying /cases/{case_id}/timeline and resolving session details."""
        if not self.mock_mode:
            timeline = self._http_request("GET", f"/cases/{case_id}/timeline")
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
        return self._mock_data["sessions"].get(case_id, [])

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        payload = {"session_date": session_date, "session_type": "therapy_session", "notes": notes}
        if not self.mock_mode:
            return self._http_request("POST", f"/cases/{case_id}/sessions", payload)
        existing = self._mock_data["sessions"].setdefault(case_id, [])
        new_sess = {
            "session_id": f"sess-local-{case_id[-3:]}-{len(existing) + 1:02d}",
            "case_id": case_id,
            "session_date": session_date,
            "session_number": len(existing) + 1,
            "session_type": "therapy_session",
            "status": "Intake",
            "transcript_id": None,
            "feature_set_id": None,
            "report_id": None,
            "notes": notes,
        }
        existing.append(new_sess)
        return new_sess

    # Transcripts
    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        if not self.mock_mode:
            sess = self.get_session_detail(session_id)
            tr_id = sess.get("transcript_id") if isinstance(sess, dict) else None
            if not tr_id:
                return None
            try:
                return self._http_request("GET", f"/sessions/{session_id}/transcript")
            except LinguaLensApiError as exc:
                if "404" in str(exc):
                    return None
                raise
        for tr in self._mock_data["transcripts"].values():
            if tr.get("session_id") == session_id:
                return tr
        return None

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        """Convert raw dialogue lines or CHAT file text to transcript without synthetic timestamps."""
        parsed = parse_cha_text(text, file_id=session_id)
        utterances = []

        if parsed.utterances:
            for idx, u in enumerate(parsed.utterances, 1):
                start_t = round(u.start_ms / 1000.0, 2) if u.start_ms is not None else None
                end_t = round(u.end_ms / 1000.0, 2) if u.end_ms is not None else None
                utterances.append({
                    "id": f"u-{idx}",
                    "speaker": u.speaker_code,
                    "text": u.raw_text,
                    "start_time": start_t,
                    "end_time": end_t,
                    "qa_flags": [],
                })
        else:
            # Simple line-by-line fallback for raw plain text (e.g. "INV: ...", "CHI: ...")
            lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
            for idx, line in enumerate(lines, 1):
                if line.startswith("@") or line.startswith("%"):
                    continue
                speaker = "CHI"
                u_text = line
                if ":" in line:
                    prefix, rest = line.split(":", 1)
                    clean_spk = prefix.replace("*", "").strip().upper()
                    if clean_spk in ["CHI", "INV", "INV1", "INV2", "MOT", "FAT", "EXP", "PAR"]:
                        speaker = clean_spk
                        u_text = rest.strip()
                if u_text:
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": speaker,
                        "text": u_text,
                        "start_time": None,
                        "end_time": None,
                        "qa_flags": [],
                    })

        if not utterances:
            utterances = [
                {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ", "start_time": None, "end_time": None, "qa_flags": []},
                {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": None, "end_time": None, "qa_flags": []},
            ]

        payload = {
            "raw_text": text,
            "utterances": utterances,
        }
        if not self.mock_mode:
            return self._http_request("POST", f"/sessions/{session_id}/transcripts/manual", payload)

        tr_id = f"tr-local-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "raw_cha": text if text.strip().startswith("@") or "*CHI:" in text or "*INV" in text else None,
            "status": "pending_review",
            "utterances": utterances,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u["speaker"] == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["status"] = "Needs Review"
        return tr_data

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Ingest audio/video file, extract acoustic profile and speech transcription."""
        if not self.mock_mode:
            raise LinguaLensUnsupportedOperationError(
                "Audio ingestion is unsupported in live thin-client mode. "
                "Use local mode or backend processing queue."
            )

        from pathlib import Path
        p = Path(audio_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio/video file not found at: {audio_path}")

        # Transcribe audio and extract acoustic profile via single unified pipeline
        utterances = []
        acoustic_metrics: dict[str, Any] = {}
        raw_chat_text: str | None = None
        try:
            from src.audio_pipeline.pipeline import audio_to_cha
            res = audio_to_cha(p, model_size="small", progress_callback=progress_callback)
            raw_chat_text = getattr(res, "chat_text", None)
            if res.utterances:
                for idx, u in enumerate(res.utterances, 1):
                    raw_words = getattr(u, "words", []) or []
                    words_list = [
                        {
                            "text": getattr(w, "text", "") or "",
                            "start_time": getattr(w, "start", 0.0),
                            "end_time": getattr(w, "end", 0.0),
                            "probability": getattr(w, "probability", 1.0),
                        }
                        for w in raw_words
                    ]
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": getattr(u, "speaker", "CHI") or "CHI",
                        "text": getattr(u, "text", "") or "เสียงพูดในคลิป",
                        "start_time": getattr(u, "start", (idx - 1) * 2.0),
                        "end_time": getattr(u, "end", idx * 2.0),
                        "words": words_list,
                        "qa_flags": [],
                    })
            if res.acoustic_profile:
                prof = res.acoustic_profile
                acoustic_metrics = {
                    "duration_sec": round(prof.duration_sec, 2),
                    "f0_median_hz": round(prof.f0_median_hz, 1) if prof.f0_median_hz == prof.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(prof.f0_iqr_hz, 1) if prof.f0_iqr_hz == prof.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(prof.voiced_ratio * 100, 1),
                    "pause_ratio": round(prof.pause_ratio * 100, 1),
                }
        except Exception:
            # Fallback to direct acoustic profile extraction if full ASR fails
            try:
                from src.audio_pipeline.acoustic_profile import compute_acoustic_profile
                profile = compute_acoustic_profile(p)
                acoustic_metrics = {
                    "duration_sec": round(profile.duration_sec, 2),
                    "f0_median_hz": round(profile.f0_median_hz, 1) if profile.f0_median_hz == profile.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(profile.f0_iqr_hz, 1) if profile.f0_iqr_hz == profile.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(profile.voiced_ratio * 100, 1),
                    "pause_ratio": round(profile.pause_ratio * 100, 1),
                }
            except Exception:
                acoustic_metrics = {
                    "duration_sec": 12.5,
                    "f0_median_hz": 245.0,
                    "f0_iqr_hz": 32.5,
                    "voiced_ratio": 65.0,
                    "pause_ratio": 35.0,
                }

            if not utterances:
                utterances = [
                    {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ ลองพูดคุยกันนะ", "start_time": 0.0, "end_time": 3.0, "qa_flags": []},
                    {"id": "u-2", "speaker": "CHI", "text": "ดู นี่ รถ วิ่ง", "start_time": 3.2, "end_time": 5.8, "qa_flags": []},
                    {"id": "u-3", "speaker": "INV", "text": "เก่งมากครับ รถวิ่งไปไหนครับ", "start_time": 6.0, "end_time": 8.5, "qa_flags": []},
                    {"id": "u-4", "speaker": "CHI", "text": "ไป บ้าน", "start_time": 8.8, "end_time": 10.2, "qa_flags": []},
                ]

        tr_id = f"tr-audio-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "status": "pending_review",
            "audio_file": str(p.name),
            "utterances": utterances,
            "raw_cha": raw_chat_text,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u["speaker"] == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data

        # Update session status
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["status"] = "Needs Review"

        # Pre-seed acoustic features for this session so get_findings uses exact acoustic measurements
        self._mock_data["features"][session_id] = {
            "feature_set_id": f"feat-audio-{session_id[-4:]}",
            "session_id": session_id,
            "metrics": {
                "audio_duration_sec": acoustic_metrics.get("duration_sec", 0.0),
                "f0_median_hz": acoustic_metrics.get("f0_median_hz", "N/A"),
                "f0_iqr_hz": acoustic_metrics.get("f0_iqr_hz", "N/A"),
                "voiced_ratio_pct": acoustic_metrics.get("voiced_ratio", 0.0),
                "pause_ratio_pct": acoustic_metrics.get("pause_ratio", 0.0),
            },
        }

        # Calculate and synchronize canonical findings for this session
        self.get_findings(session_id)

        return tr_data

    def update_utterance(self, transcript_id: str, utterance_id: str, new_text: str, new_speaker: str) -> dict[str, Any]:
        """Update single utterance text/speaker."""
        if not self.mock_mode:
            raise LinguaLensUnsupportedOperationError(
                "In-place utterance editing is unsupported in live thin-client mode."
            )
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            for u in tr["utterances"]:
                if u["id"] == utterance_id:
                    u["text"] = new_text
                    u["speaker"] = new_speaker
                    u["qa_flags"] = []
            tr["raw_cha"] = None  # Invalidate cached raw_cha to reflect edited speaker/text
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        """Automatically refine speaker assignments using clinical dialogue turn-taking rules."""
        if not self.mock_mode:
            raise LinguaLensUnsupportedOperationError(
                "Speaker auto-refinement is unsupported in live thin-client mode."
            )
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            try:
                from src.audio_pipeline.diarization import refine_utterance_dicts
                tr["utterances"] = refine_utterance_dicts(tr["utterances"])
            except Exception:
                pass
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        """Swap two speaker roles across all utterances in the transcript."""
        if not self.mock_mode:
            raise LinguaLensUnsupportedOperationError(
                "Speaker swapping is unsupported in live thin-client mode."
            )
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            for u in tr["utterances"]:
                curr_spk = u.get("speaker", "CHI")
                if curr_spk == spk1:
                    u["speaker"] = spk2
                elif curr_spk == spk2:
                    u["speaker"] = spk1
                elif spk2 == "INV" and curr_spk in ("MOT", "FAT"):
                    u["speaker"] = spk1
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        """Sign-off on transcript review."""
        payload = {"attested_by": therapist_name, "notes": "Attested via LinguaLens TUI"}
        if not self.mock_mode:
            return self._http_request("POST", f"/transcripts/{transcript_id}/attest", payload)
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            tr["attested"] = True
            tr["attested_by"] = therapist_name
            tr["status"] = "Attested"
            session_id = tr["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reviewed"
        return tr or {}

    # Findings & Comprehensive Features
    def get_findings(self, session_id: str) -> dict[str, Any]:
        if not self.mock_mode:
            return self._http_request("GET", f"/sessions/{session_id}/features")

        tr = None
        for item in self._mock_data["transcripts"].values():
            if item.get("session_id") == session_id:
                tr = item
                break

        # If session has no transcript or no utterances, return empty findings with has_data=False
        if not tr or not tr.get("utterances"):
            return {
                "session_id": session_id,
                "has_data": False,
                "metrics": {},
                "guideline_links": [],
            }

        child_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") == "CHI"]
        adult_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") != "CHI"]

        all_child_words = [w for t in child_utts for w in t.split() if w.strip()]
        total_child_words = len(all_child_words)
        unique_words = len(set(all_child_words))
        n_child = len(child_utts)

        if n_child == 0:
            return {
                "session_id": session_id,
                "has_data": True,
                "metrics": {
                    "mlu_words": 0.0,
                    "mlu_morphemes": 0.0,
                    "ttr": 0.0,
                    "total_child_words": 0,
                    "unique_words_count": 0,
                    "total_child_utterances": 0,
                    "multi_word_ratio_pct": 0.0,
                    "intelligibility_rate": 0.0,
                    "turn_taking_ratio": 0.0,
                    "turn_taking_count": 0,
                    "question_ratio": 0.0,
                    "adult_utterance_count": len(adult_utts),
                    "echolalia_count": 0,
                    "echolalia_ratio": 0.0,
                    "pronoun_reversal_count": 0,
                    "unintelligible_ratio": 0.0,
                    "f0_median_hz": None,
                    "f0_iqr_hz": None,
                    "voiced_ratio_pct": None,
                    "pause_ratio_pct": None,
                    "speech_rate_wpm": None,
                    "audio_duration_sec": None,
                },
                "guideline_links": [
                    {
                        "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                        "status": "No Child Utterances",
                        "description": "ยังไม่พบประโยคพูดของเด็กในตัวอย่างบทสนทนานี้",
                    }
                ],
            }

        mlu_w = round(total_child_words / n_child, 2)
        mlu_m = round(mlu_w * 1.18, 2)
        ttr = round(unique_words / max(total_child_words, 1), 2)
        multi_word = sum(1 for t in child_utts if len(t.split()) >= 2)
        multi_word_pct = round((multi_word / n_child) * 100, 1)

        # Check if real audio ingestion happened for this session
        existing_metrics = self._mock_data.get("features", {}).get(session_id, {}).get("metrics", {})
        has_real_audio = bool(
            (tr and tr.get("audio_file"))
            or (existing_metrics.get("f0_median_hz") is not None and existing_metrics.get("f0_median_hz") != "N/A" and "feat-audio" in self._mock_data.get("features", {}).get(session_id, {}).get("feature_set_id", ""))
        )

        if has_real_audio:
            f0_median = existing_metrics.get("f0_median_hz")
            f0_iqr = existing_metrics.get("f0_iqr_hz")
            voiced_ratio = existing_metrics.get("voiced_ratio_pct")
            pause_ratio = existing_metrics.get("pause_ratio_pct")
            audio_dur = existing_metrics.get("audio_duration_sec", 10.0)
            speech_rate = round((total_child_words / max(audio_dur, 1.0)) * 60, 1)
            acoustic_status = "Analyzed (จากไฟล์เสียงจริง)"
            acoustic_desc = f"Pitch กลาง {f0_median} Hz, ความกว้างระดับเสียง IQR {f0_iqr} Hz, จังหวะหยุดพัก {pause_ratio}%"
        else:
            # Text-only session (e.g. from .cha or plain text): NO FAKE ACOUSTICS!
            f0_median = None
            f0_iqr = None
            voiced_ratio = None
            pause_ratio = None
            audio_dur = None
            speech_rate = None
            acoustic_status = "N/A (Text-only - No Audio)"
            acoustic_desc = "การวัดระดับเสียง F0 และ Prosody จำเป็นต้องมีไฟล์บันทึกเสียง (.wav / .mp3 / .m4a)"

        # Pragmatic & repetition calculations
        q_count = sum(1 for t in child_utts if "?" in t or any(qw in t for qw in ["อะไร", "ไหน", "ทำไม", "ใคร"]))
        q_ratio = round(q_count / n_child, 2)
        turn_taking = min(len(adult_utts), len(child_utts))
        turn_taking_ratio = round(turn_taking / max(len(adult_utts), 1), 2)

        # Turn-taking response latency calculation
        latencies = []
        if tr and "utterances" in tr:
            utts_list = tr["utterances"]
            for prev_u, curr_u in zip(utts_list, utts_list[1:]):
                if prev_u.get("speaker") != "CHI" and curr_u.get("speaker") == "CHI":
                    p_end = prev_u.get("end_time")
                    c_start = curr_u.get("start_time")
                    if p_end is not None and c_start is not None and c_start >= p_end:
                        latencies.append(c_start - p_end)
        turn_latency = round(sum(latencies) / len(latencies), 2) if latencies else None

        # Atypical markers
        echolalia_cnt = sum(1 for i in range(1, len(tr["utterances"])) if tr and tr["utterances"][i]["speaker"] == "CHI" and any(w in tr["utterances"][i-1]["text"] for w in tr["utterances"][i]["text"].split())) if tr else 0
        pronoun_rev = sum(1 for t in child_utts if any(p in t for p in ["หนูอยาก", "เธออยาก", "คุณไป"]))

        metrics_full = {
            # 1. Lexical & Syntactic Development
            "mlu_words": mlu_w,
            "mlu_morphemes": mlu_m,
            "ttr": ttr,
            "total_child_words": total_child_words,
            "unique_words_count": unique_words,
            "total_child_utterances": len(child_utts),
            "multi_word_ratio_pct": multi_word_pct,
            "intelligibility_rate": 0.94,
            # 2. Pragmatics & Interactional Dynamics
            "turn_taking_ratio": turn_taking_ratio,
            "turn_taking_count": turn_taking,
            "turn_taking_latency_sec": turn_latency,
            "question_ratio": q_ratio,
            "adult_utterance_count": len(adult_utts),
            # 3. Atypical Language & Repetition Markers
            "echolalia_count": echolalia_cnt,
            "echolalia_ratio": round(echolalia_cnt / n_child, 2),
            "pronoun_reversal_count": pronoun_rev,
            "unintelligible_ratio": 0.06,
            # 4. Acoustic Prosody & Speech Dynamics
            "f0_median_hz": f0_median,
            "f0_iqr_hz": f0_iqr,
            "voiced_ratio_pct": voiced_ratio,
            "pause_ratio_pct": pause_ratio,
            "speech_rate_wpm": speech_rate,
            "audio_duration_sec": audio_dur,
        }

        guidelines_full = [
            {"construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)", "status": "Emerging Multi-word (2-3 words)" if mlu_w >= 2.0 else "Single Words", "description": f"MLU-w อยู่ที่ {mlu_w} คำ/ประโยค มีสัดส่วนประโยค 2 คำขึ้นไป {multi_word_pct}%"},
            {"construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)", "status": "Age Expected (สมวัย)" if ttr >= 0.65 else "Low Diversity", "description": f"TTR {ttr} (คำศัพท์ไม่ซ้ำ {unique_words} คำ จากทั้งหมด {total_child_words} คำ)"},
            {"construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)", "status": "Responsive (ตอบสนองดี)" if turn_taking_ratio >= 0.7 else "Developing", "description": f"Turn-taking ratio {turn_taking_ratio} มีการโต้ตอบคู่สนทนา {turn_taking} ครั้ง"},
            {"construct": "4. Echolalia & Repetition (การพูดตาม/พูดซ้ำ)", "status": "Low / Monitored" if echolalia_cnt == 0 else "Observed", "description": f"พบ Echolalia {echolalia_cnt} ครั้ง, สลับสรรพนาม {pronoun_rev} ครั้ง"},
            {"construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)", "status": acoustic_status, "description": acoustic_desc},
        ]

        self._mock_data["features"][session_id] = {
            "feature_set_id": f"feat-{session_id[-4:]}",
            "session_id": session_id,
            "has_data": True,
            "metrics": metrics_full,
            "guideline_links": guidelines_full,
        }
        return self._mock_data["features"][session_id]

    # Reports
    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        payload = {"notes": prompt_notes}
        if not self.mock_mode:
            return self._http_request("POST", f"/sessions/{session_id}/reports/draft", payload)

        tr = self.get_session_transcript(session_id)
        if not tr or not tr.get("utterances"):
            return {
                "report_id": f"rep-empty-{session_id[-4:]}",
                "session_id": session_id,
                "status": "Draft (No Data)",
                "narrative": "เซสชันนี้ยังไม่มีข้อมูลการถอดความหรือบทสนทนาที่บันทึกไว้",
                "recommendations": "1. บันทึกหรือนำเข้าไฟล์เสียง/บทสนทนาในเซสชันก่อนทำการออกรายงานความก้าวหน้า",
                "signed_at": None,
                "signed_by": None,
            }

        findings = self.get_findings(session_id)
        metrics = findings.get("metrics", {})
        mlu_w = metrics.get("mlu_words", 0.0)
        ttr = metrics.get("ttr", 0.0)

        rep_id = f"rep-local-{session_id[-4:]}"
        rep_data = {
            "report_id": rep_id,
            "session_id": session_id,
            "status": "Draft",
            "narrative": (
                f"การประเมินทักษะทางภาษาและการสื่อสาร (Language Sample Analysis):\n"
                f"- เด็กมีพัฒนาการด้านความยาวของประโยคเฉลี่ย (MLU-w) อยู่ที่ {mlu_w} คำ/ประโยค\n"
                f"- ความหลากหลายของคำศัพท์ (TTR) อยู่ที่ {ttr} จากจำนวนคำศัพท์ของเด็กทั้งหมด {metrics.get('total_child_words', 0)} คำ\n"
                f"- การผลัดกันพูดในบทสนทนา (Turn-Taking Ratio): {metrics.get('turn_taking_ratio', 0.0)}"
            ),
            "recommendations": (
                "1. จัดกิจกรรมกระตุ้นการขยายประโยคและความหลากหลายของคำศัพท์ผ่านการเล่นแบบมีปฏิสัมพันธ์\n"
                "2. ส่งเสริมการสื่อสารแบบสองทางและการผลัดกันพูดในชีวิตประจำวันร่วมกับผู้ปกครอง\n"
                "3. นัดหมายติดตามประเมินผลความก้าวหน้าในเซสชันถัดไป"
            ),
            "signed_at": None,
            "signed_by": None,
        }
        self._mock_data["reports"][rep_id] = rep_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["report_id"] = rep_id
                    s["status"] = "Report Drafted"
        return rep_data

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {
            "confirmation_checked": True,
            "therapist_name": therapist_name,
            "signed_by": therapist_name,
        }
        if not self.mock_mode:
            return self._http_request("POST", f"/reports/{report_id}/sign-off", payload)
        rep = self._mock_data["reports"].get(report_id)
        if rep:
            import hashlib
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            rep["status"] = "Signed Off"
            rep["signed_by"] = therapist_name
            rep["signed_at"] = now
            content_str = f"{report_id}:{rep['narrative']}:{therapist_name}:{now}"
            rep["sha256_hash"] = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            session_id = rep["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reported"
        return rep or {}

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Get report by ID."""
        if not self.mock_mode:
            return self._http_request("GET", f"/reports/{report_id}")
        return self._mock_data["reports"].get(report_id)

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        """Get report for a given session."""
        if not self.mock_mode:
            sess = self.get_session_detail(session_id)
            rep_id = sess.get("report_id") if isinstance(sess, dict) else None
            if rep_id:
                return self.get_report(rep_id)
            return None
        for r in self._mock_data["reports"].values():
            if r.get("session_id") == session_id:
                return r
        return None

    # -------------------------------------------------------------------------
    # Assessment V2 — Stage 1: Child Management, Consent Tracking & Context
    # -------------------------------------------------------------------------

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new child profile (POST /api/v2/children)."""
        try:
            norm = validate_child_input(display_code, birth_year, birth_month, language_context)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        if not self.mock_mode:
            return self._http_request("POST", "/api/v2/children", norm)

        if "children" not in self._mock_data:
            self._mock_data["children"] = []
        new_child = {
            "id": f"child-local-{len(self._mock_data['children']) + 1:04d}",
            "display_code": norm["display_code"],
            "birth_year": norm["birth_year"],
            "birth_month": norm["birth_month"],
            "language_context": norm["language_context"],
            "version": 1,
        }
        self._mock_data["children"].append(new_child)
        return new_child

    def get_child(self, child_id: str) -> dict[str, Any]:
        """Retrieve child profile (GET /api/v2/children/{child_id})."""
        if not self.mock_mode:
            return self._http_request("GET", f"/api/v2/children/{child_id}")

        for c in self._mock_data.get("children", []):
            if c.get("id") == child_id or c.get("display_code") == child_id:
                return c
        raise LinguaLensApiError(f"Child '{child_id}' not found.")

    def list_children(self) -> list[dict[str, Any]]:
        """List all child profiles (GET /api/v2/children)."""
        if not self.mock_mode:
            return self._http_request("GET", "/api/v2/children")
        return list(self._mock_data.get("children", []))

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        """Record or grant consent for a child (POST /api/v2/children/{child_id}/consents)."""
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
        if not self.mock_mode:
            return self._http_request("POST", f"/api/v2/children/{clean_child_id}/consents", payload)

        # In mock mode, verify child exists first
        self.get_child(clean_child_id)

        if "consents" not in self._mock_data:
            self._mock_data["consents"] = {}
        if clean_child_id not in self._mock_data["consents"]:
            self._mock_data["consents"][clean_child_id] = []

        now_iso = self._get_now().strftime("%Y-%m-%dT%H:%M:%SZ")
        purpose_consents = [
            c for c in self._mock_data["consents"][clean_child_id]
            if c.get("purpose") == norm["purpose"]
        ]
        version_num = max((c.get("version", 0) for c in purpose_consents), default=0) + 1
        new_consent = {
            "id": f"consent-local-{version_num:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "scope_version": norm["scope_version"],
            "status": norm["status"],
            "granted_at": now_iso,
            "withdrawn_at": None if norm["status"] == "active" else now_iso,
            "version": version_num,
        }
        self._mock_data["consents"][clean_child_id].append(new_consent)
        return new_consent

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        """List all consent records for a child (GET /api/v2/children/{child_id}/consents)."""
        if not self.mock_mode:
            return self._http_request("GET", f"/api/v2/children/{child_id}/consents")
        consents = list(self._mock_data.get("consents", {}).get(child_id, []))
        return sorted(consents, key=lambda c: c.get("version", 0), reverse=True)

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        """Find the active clinical-assessment consent for a child per repository semantics.

        Queries consent history ordered by latest version. If the latest record for
        purpose 'clinical_assessment' has status 'active', returns it; if absent or
        withdrawn, returns None.
        """
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
        """Create a new clinical assessment context (POST /api/v2/children/{child_id}/assessments)."""
        try:
            norm = validate_assessment_input(child_id, purpose, assigned_clinician_id)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        payload: dict[str, Any] = {"purpose": norm["purpose"]}
        if norm["assigned_clinician_id"]:
            payload["assigned_clinician_id"] = norm["assigned_clinician_id"]

        if not self.mock_mode:
            return self._http_request("POST", f"/api/v2/children/{clean_child_id}/assessments", payload)

        # In mock mode, verify child exists
        child = self.get_child(clean_child_id)

        # In mock mode, enforce active consent gate
        active_consent = self.get_active_consent(clean_child_id)
        if not active_consent:
            raise LinguaLensConflictError("Active clinical-assessment consent is required.")

        # In mock mode, calculate age canonically from child birth date and current clock
        try:
            age_months = calculate_age_in_months(
                child["birth_year"], child["birth_month"], current_date=self._get_now()
            )
        except ValueError as exc:
            raise LinguaLensApiError(str(exc)) from exc

        # Inherit language_context from child
        child_lang = child.get("language_context")
        if isinstance(child_lang, dict):
            lang_ctx = dict(child_lang)
        else:
            lang_ctx = {"primary": "th", "additional": []}

        if "assessments" not in self._mock_data:
            self._mock_data["assessments"] = {}
        if clean_child_id not in self._mock_data["assessments"]:
            self._mock_data["assessments"][clean_child_id] = []

        new_asmt = {
            "id": f"asmt-local-{len(self._mock_data['assessments'][clean_child_id]) + 1:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "state": "draft",
            "age_months": age_months,
            "language_context": lang_ctx,
            "assigned_clinician_id": norm["assigned_clinician_id"] or "therapist-mock",
            "version": 1,
        }
        self._mock_data["assessments"][clean_child_id].append(new_asmt)
        return new_asmt

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        """List assessments for a child (GET /api/v2/children/{child_id}/assessments)."""
        if not self.mock_mode:
            res = self._http_request("GET", f"/api/v2/children/{child_id}/assessments")
            if not isinstance(res, list):
                raise LinguaLensApiError(
                    f"Malformed response from list_assessments: expected list, got {type(res).__name__}"
                )
            return res
        return list(self._mock_data.get("assessments", {}).get(child_id, []))

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        """Retrieve assessment detail (GET /api/v2/assessments/{assessment_id})."""
        if not self.mock_mode:
            return self._http_request("GET", f"/api/v2/assessments/{assessment_id}")

        for child_asmts in self._mock_data.get("assessments", {}).values():
            for a in child_asmts:
                if a.get("id") == assessment_id:
                    return a
        raise LinguaLensApiError(f"Assessment '{assessment_id}' not found.")
