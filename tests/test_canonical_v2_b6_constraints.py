"""Focused contract and parity tests for D1 Finding B6: canonical V2 constraints and mock/live parity.

Covers:
1. create_child:
   - canonical schema validation: display_code (1..64), birth_year (1900..2100, strict int),
     birth_month (1..12, strict int), language_context (2-letter codes, normalized).
   - valid boundary inputs succeed and normalize language context.
   - invalid inputs fail closed with zero POST in live mode and zero local mutation in mock mode.
2. record_consent:
   - canonical schema validation: child_id (1..64), purpose in ConsentPurpose,
     scope_version (1..64), status in ConsentStatus.
   - mock mode verifies child existence; non-existent child fails closed.
   - invalid inputs fail closed with zero POST and zero local mutation.
3. create_assessment:
   - canonical schema validation: child_id (1..64), purpose in AssessmentPurpose,
     assigned_clinician_id (optional, 1..128 chars).
   - mock mode verifies child existence.
   - mock mode consent gate: active clinical_assessment consent required; missing or withdrawn
     consent raises LinguaLensConflictError with zero mutation.
   - mock mode canonical age calculation: computed from child's birth date and controllable clock,
     rejecting out of range (< 0 or > 216 months); NEVER hardcoded 48.
   - mock mode language context: inherited directly from child, NEVER fabricated.
4. GUI/TUI input boundary validation:
   - GUI and TUI enforce constraints client-side, showing validation errors without setting
     fabricated active context.
5. Legacy B4 behavior preserved:
   - Legacy /api/v1/cases contract remains intact.
"""

from __future__ import annotations

from datetime import datetime, timezone
import queue
import re
import threading
import tkinter as tk
from typing import Any
import unittest.mock as mock

import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import (
    LinguaLensApiError,
    LinguaLensConflictError,
    LinguaLensClient,
)

try:
    from packages.tui.client import LinguaLensValidationError
except ImportError:
    class LinguaLensValidationError(LinguaLensApiError, ValueError):  # type: ignore[no-redef]
        pass


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tk_root() -> tk.Tk:
    """Create a headless, withdrawn Tk root."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not available or headless environment without DISPLAY")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def _drain_async_queue(app: LinguaLensGUIApp) -> None:
    while True:
        try:
            callback, _ = app._async_queue.get_nowait()
            callback()
        except queue.Empty:
            break


# ---------------------------------------------------------------------------
# 1. create_child Contract & Parity Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "display_code, birth_year, birth_month, lang_ctx, expected_lang",
    [
        ("C", 1900, 1, {"primary": "th"}, {"primary": "th", "additional": []}),
        ("C" * 64, 2100, 12, {"primary": "EN", "additional": ["TH", "zh"]}, {"primary": "en", "additional": ["th", "zh"]}),
        ("CHILD_001", 2021, 6, None, {"primary": "th", "additional": []}),
    ],
)
def test_create_child_valid_boundaries_and_normalization(
    display_code: str,
    birth_year: int,
    birth_month: int,
    lang_ctx: dict[str, Any] | None,
    expected_lang: dict[str, Any],
) -> None:
    """Valid boundary inputs succeed and normalize language in both mock and live modes."""
    # Mock mode
    client_mock = LinguaLensClient(mock_mode=True)
    child = client_mock.create_child(display_code, birth_year, birth_month, lang_ctx)
    assert child["display_code"] == display_code
    assert child["birth_year"] == birth_year
    assert child["birth_month"] == birth_month
    assert child["language_context"] == expected_lang

    # Live mode (verifying outgoing payload)
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request", return_value={"id": "child-live-01", **child}) as mock_http:
        created = client_live.create_child(display_code, birth_year, birth_month, lang_ctx)
        assert mock_http.call_count == 1
        call_args = mock_http.call_args[0]
        assert call_args[0] == "POST"
        assert call_args[1] == "/api/v2/children"
        payload = call_args[2]
        assert payload["display_code"] == display_code
        assert payload["birth_year"] == birth_year
        assert payload["birth_month"] == birth_month
        assert payload["language_context"] == expected_lang


@pytest.mark.parametrize(
    "bad_code, bad_year, bad_month, bad_lang",
    [
        # Invalid display code
        ("", 2021, 6, None),
        ("   ", 2021, 6, None),
        ("C" * 65, 2021, 6, None),
        (None, 2021, 6, None),
        (123, 2021, 6, None),
        # Invalid birth year (strict type & range)
        ("C01", 1899, 6, None),
        ("C01", 2101, 6, None),
        ("C01", True, 6, None),
        ("C01", False, 6, None),
        ("C01", 2020.5, 6, None),
        ("C01", "2021", 6, None),
        ("C01", None, 6, None),
        # Invalid birth month (strict type & range)
        ("C01", 2021, 0, None),
        ("C01", 2021, 13, None),
        ("C01", 2021, True, None),
        ("C01", 2021, False, None),
        ("C01", 2021, 6.5, None),
        ("C01", 2021, "6", None),
        ("C01", 2021, None, None),
        # Invalid language context
        ("C01", 2021, 6, "th"),
        ("C01", 2021, 6, ["th"]),
        ("C01", 2021, 6, {"primary": "tha"}),  # 3-letter code rejected
        ("C01", 2021, 6, {"primary": "12"}),
        ("C01", 2021, 6, {"primary": ""}),
        ("C01", 2021, 6, {"primary": "th", "additional": "en"}),  # not list
        ("C01", 2021, 6, {"primary": "th", "additional": ["eng"]}),  # 3-letter in additional
        ("C01", 2021, 6, {"primary": "th", "unsupported": True}),  # extra fields
    ],
)
def test_create_child_invalid_inputs_fail_closed_without_mutation_or_network(
    bad_code: Any, bad_year: Any, bad_month: Any, bad_lang: Any
) -> None:
    """Invalid child intake inputs raise validation error without mutating mock state or emitting POST."""
    # Live mode: zero network request
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request") as mock_http:
        with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
            client_live.create_child(bad_code, bad_year, bad_month, bad_lang)
        assert mock_http.call_count == 0

    # Mock mode: zero local mutation
    client_mock = LinguaLensClient(mock_mode=True)
    initial_children = list(client_mock._mock_data.get("children", []))
    with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
        client_mock.create_child(bad_code, bad_year, bad_month, bad_lang)
    assert client_mock._mock_data.get("children", []) == initial_children


# ---------------------------------------------------------------------------
# 2. record_consent Contract & Parity Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "purpose, scope_version, status",
    [
        ("clinical_assessment", "2026.1", "active"),
        ("clinical_assessment", "v" * 64, "withdrawn"),
        ("research_reuse", "1", "active"),
    ],
)
def test_record_consent_valid_boundaries(purpose: str, scope_version: str, status: str) -> None:
    """Valid consent parameters succeed and record accurately."""
    client_mock = LinguaLensClient(mock_mode=True)
    # Register child first in mock mode
    child = client_mock.create_child("C01", 2021, 6)
    child_id = child["id"]

    rec = client_mock.record_consent(child_id, purpose=purpose, scope_version=scope_version, status=status)
    assert rec["child_id"] == child_id
    assert rec["purpose"] == purpose
    assert rec["scope_version"] == scope_version
    assert rec["status"] == status

    # Live mode
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request", return_value={"id": "consent-01", **rec}) as mock_http:
        client_live.record_consent(child_id, purpose=purpose, scope_version=scope_version, status=status)
        assert mock_http.call_count == 1
        assert mock_http.call_args[0][0] == "POST"
        assert mock_http.call_args[0][1] == f"/api/v2/children/{child_id}/consents"


@pytest.mark.parametrize(
    "bad_child_id, bad_purpose, bad_scope, bad_status",
    [
        # Invalid child_id
        ("", "clinical_assessment", "2026.1", "active"),
        ("   ", "clinical_assessment", "2026.1", "active"),
        ("c" * 65, "clinical_assessment", "2026.1", "active"),
        (None, "clinical_assessment", "2026.1", "active"),
        # Invalid purpose (must be in ConsentPurpose: clinical_assessment, research_reuse)
        ("child-01", "invalid_purpose", "2026.1", "active"),
        ("child-01", "initial", "2026.1", "active"),
        ("child-01", "", "2026.1", "active"),
        ("child-01", None, "2026.1", "active"),
        # Invalid status (must be active or withdrawn)
        ("child-01", "clinical_assessment", "2026.1", "pending"),
        ("child-01", "clinical_assessment", "2026.1", "revoked"),
        ("child-01", "clinical_assessment", "2026.1", ""),
        ("child-01", "clinical_assessment", "2026.1", None),
        # Invalid scope_version
        ("child-01", "clinical_assessment", "", "active"),
        ("child-01", "clinical_assessment", "   ", "active"),
        ("child-01", "clinical_assessment", "v" * 65, "active"),
        ("child-01", "clinical_assessment", None, "active"),
    ],
)
def test_record_consent_invalid_inputs_fail_closed_without_mutation_or_network(
    bad_child_id: Any, bad_purpose: Any, bad_scope: Any, bad_status: Any
) -> None:
    """Invalid consent inputs raise validation error without network call or state mutation."""
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request") as mock_http:
        with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
            client_live.record_consent(bad_child_id, purpose=bad_purpose, scope_version=bad_scope, status=bad_status)
        assert mock_http.call_count == 0

    client_mock = LinguaLensClient(mock_mode=True)
    initial_consents = dict(client_mock._mock_data.get("consents", {}))
    with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
        client_mock.record_consent(bad_child_id, purpose=bad_purpose, scope_version=bad_scope, status=bad_status)
    assert client_mock._mock_data.get("consents", {}) == initial_consents


def test_record_consent_for_nonexistent_child_fails_closed_in_mock_mode() -> None:
    """In mock mode, recording consent for non-existent child fails closed."""
    client = LinguaLensClient(mock_mode=True)
    initial_consents = dict(client._mock_data.get("consents", {}))
    with pytest.raises(LinguaLensApiError, match="[Nn]ot found"):
        client.record_consent("child-does-not-exist", purpose="clinical_assessment")
    assert client._mock_data.get("consents", {}) == initial_consents


# ---------------------------------------------------------------------------
# 3. create_assessment Contract, Parity & Canonical Calculation Tests
# ---------------------------------------------------------------------------

def test_create_assessment_canonical_age_and_language_computation() -> None:
    """Mock create_assessment MUST canonically compute age_months from child birth date and inherit child language."""
    # Deterministic clock: 2026-09-13
    fixed_clock = datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc)
    client = LinguaLensClient(mock_mode=True)
    if hasattr(client, "_clock"):
        client._clock = lambda: fixed_clock
    elif hasattr(client, "clock"):
        client.clock = lambda: fixed_clock

    # Child born 2021-06 (in 2026-09, age = (2026-2021)*12 + 9 - 6 = 60 + 3 = 63 months)
    child = client.create_child(
        display_code="CHILD-TEST-AGE",
        birth_year=2021,
        birth_month=6,
        language_context={"primary": "th", "additional": ["en"]},
    )
    child_id = child["id"]
    client.record_consent(child_id, purpose="clinical_assessment", status="active")

    with mock.patch("packages.tui.client._get_current_utc_time", return_value=fixed_clock):
        asmt = client.create_assessment(
            child_id=child_id,
            purpose="initial",
            assigned_clinician_id="clinician-001",
        )

    # CANONICAL ASSERTIONS:
    assert asmt["age_months"] == 63, f"Expected canonically computed 63 months, got {asmt.get('age_months')} (must not be hardcoded 48!)"
    assert asmt["language_context"] == {"primary": "th", "additional": ["en"]}, "Language context must be inherited from child record!"
    assert asmt["purpose"] == "initial"
    assert asmt["assigned_clinician_id"] == "clinician-001"
    assert asmt["state"] == "draft"


def test_create_assessment_consent_gate_enforcement_and_no_bypass() -> None:
    """Direct client.create_assessment call MUST enforce active consent gate; no bypass allowed."""
    client = LinguaLensClient(mock_mode=True)
    child = client.create_child("C-NOCONSENT", 2022, 1)
    child_id = child["id"]

    # 1. Zero consent -> 409 Conflict
    with pytest.raises(LinguaLensConflictError, match="[Cc]onsent"):
        client.create_assessment(child_id, purpose="initial")
    assert child_id not in client._mock_data.get("assessments", {})

    # 2. Withdrawn consent -> 409 Conflict
    client.record_consent(child_id, purpose="clinical_assessment", status="withdrawn")
    with pytest.raises(LinguaLensConflictError, match="[Cc]onsent"):
        client.create_assessment(child_id, purpose="initial")
    assert child_id not in client._mock_data.get("assessments", {})

    # 3. Only research consent -> 409 Conflict (must be clinical_assessment)
    client.record_consent(child_id, purpose="research_reuse", status="active")
    with pytest.raises(LinguaLensConflictError, match="[Cc]onsent"):
        client.create_assessment(child_id, purpose="initial")

    # 4. Now grant active clinical assessment consent -> succeeds!
    client.record_consent(child_id, purpose="clinical_assessment", status="active")
    asmt = client.create_assessment(child_id, purpose="initial")
    assert asmt["id"] is not None
    assert asmt["child_id"] == child_id


@pytest.mark.parametrize(
    "bad_purpose, bad_clinician",
    [
        ("screening", None),  # not in canonical 4 purposes
        ("diagnostic", None),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
        ("initial", ""),  # empty string not permitted (None or 1..128)
        ("initial", "   "),
        ("initial", "c" * 129),  # exceeds 128 chars
    ],
)
def test_create_assessment_invalid_inputs_fail_closed_without_mutation_or_network(
    bad_purpose: Any, bad_clinician: Any
) -> None:
    """Invalid assessment creation inputs fail closed without POST or state mutation."""
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request") as mock_http:
        with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
            client_live.create_assessment("child-01", purpose=bad_purpose, assigned_clinician_id=bad_clinician)
        assert mock_http.call_count == 0

    client_mock = LinguaLensClient(mock_mode=True)
    child = client_mock.create_child("C01", 2021, 6)
    child_id = child["id"]
    client_mock.record_consent(child_id, status="active")
    initial_asmts = dict(client_mock._mock_data.get("assessments", {}))

    with pytest.raises((LinguaLensValidationError, LinguaLensApiError, ValueError)):
        client_mock.create_assessment(child_id, purpose=bad_purpose, assigned_clinician_id=bad_clinician)
    assert client_mock._mock_data.get("assessments", {}) == initial_asmts


def test_create_assessment_age_out_of_range_fails_closed_in_mock_mode() -> None:
    """Child age < 0 or > 216 months fails closed in mock assessment creation."""
    fixed_clock = datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc)
    client = LinguaLensClient(mock_mode=True)

    # 1. Born in future (relative to clock) -> age < 0
    child_future = client.create_child("C-FUTURE", 2027, 1)
    client.record_consent(child_future["id"], status="active")

    with mock.patch("packages.tui.client._get_current_utc_time", return_value=fixed_clock):
        with pytest.raises(LinguaLensApiError, match="[Aa]ge"):
            client.create_assessment(child_future["id"], purpose="initial")

    # 2. Too old (> 216 months = 18 years) -> born 2000-01 (age 320 months)
    child_old = client.create_child("C-OLD", 2000, 1)
    client.record_consent(child_old["id"], status="active")

    with mock.patch("packages.tui.client._get_current_utc_time", return_value=fixed_clock):
        with pytest.raises(LinguaLensApiError, match="[Aa]ge"):
            client.create_assessment(child_old["id"], purpose="initial")


# ---------------------------------------------------------------------------
# 4. GUI & TUI Boundary Validation Tests
# ---------------------------------------------------------------------------

def test_gui_child_intake_validation_rejects_overlong_code_and_strict_types(tk_root: tk.Tk) -> None:
    """GUI _validate_child_intake rejects display_code > 64 chars and non-strict types."""
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(tk_root, client=client)

    # Overlong display code
    assert app._validate_child_intake("C" * 65, 2021, 6) is not None
    # Empty display code
    assert app._validate_child_intake("", 2021, 6) is not None
    assert app._validate_child_intake("   ", 2021, 6) is not None
    # Valid 64 chars
    assert app._validate_child_intake("C" * 64, 2021, 6) is None
    # Valid 1 char
    assert app._validate_child_intake("C", 2021, 6) is None


def test_gui_create_assessment_rejects_overlong_clinician_without_mutating_context(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GUI _submit_create_assessment rejects clinician ID > 128 chars and does not mutate active context."""
    errors_shown = []
    monkeypatch.setattr(
        "tkinter.messagebox.showerror",
        lambda title, msg, **kw: errors_shown.append((title, msg)),
    )

    client = LinguaLensClient(mock_mode=True)
    child = client.create_child("C-GUI-TEST", 2021, 6)
    child_id = child["id"]
    client.record_consent(child_id, status="active")

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = child_id
    app.active_child = child
    app._current_consent_status = "active"
    app.active_consent = {"status": "active"}
    app.active_assessment_id = None
    app.active_assessment = None

    win = mock.MagicMock()
    win._bound_child_id = child_id
    win._bound_session_gen = app._get_current_session_generation()
    win._bound_child_sel_gen = getattr(app, "_child_selection_generation", 0)
    win._is_submitting = False
    win.winfo_exists.return_value = True

    # Try submitting with overlong clinician ID
    t = app._submit_create_assessment(
        win=win,
        purpose="initial",
        clinician_id="c" * 129,
    )
    assert t is None
    assert len(errors_shown) == 1
    assert "Clinician" in errors_shown[0][0] or "Clinician" in errors_shown[0][1]
    # Active assessment context must remain clean
    assert app.active_assessment_id is None
    assert app.active_assessment is None


# ---------------------------------------------------------------------------
# 5. Differential Parity Tests (Canonical Pydantic Oracle vs Desktop Validators)
# ---------------------------------------------------------------------------

from pydantic import ValidationError
from app.assessment_v2.schemas import (
    ChildCreateRequest,
    ConsentCreateRequest,
    AssessmentCreateRequest,
    _normalize_language_context as canonical_normalize_language_context,
)
from packages.tui.validation import (
    normalize_language_context,
    validate_child_input,
    validate_consent_input,
    validate_assessment_input,
)


def test_differential_language_additional_none_rejected_by_both() -> None:
    """Explicit additional=None must be rejected by both canonical schema and desktop validator."""
    malformed = {"primary": "th", "additional": None}

    # Canonical oracle
    with pytest.raises(ValueError, match="additional languages must be a list"):
        canonical_normalize_language_context(malformed)

    with pytest.raises(ValidationError):
        ChildCreateRequest(display_code="C1", birth_year=2021, birth_month=6, language_context=malformed)

    # Desktop validator must also reject rather than silently converting None to []
    with pytest.raises(ValueError, match="additional languages must be a list"):
        normalize_language_context(malformed)

    with pytest.raises(ValueError, match="additional languages must be a list"):
        validate_child_input("C1", 2021, 6, malformed)

    # Direct client calls must fail closed without POST or mock mutation
    client_live = LinguaLensClient(mock_mode=False)
    with mock.patch.object(client_live, "_http_request") as mock_http:
        with pytest.raises(LinguaLensValidationError):
            client_live.create_child("C1", 2021, 6, malformed)
        assert mock_http.call_count == 0

    client_mock = LinguaLensClient(mock_mode=True)
    initial_children = list(client_mock._mock_data.get("children", []))
    with pytest.raises(LinguaLensValidationError):
        client_mock.create_child("C1", 2021, 6, malformed)
    assert client_mock._mock_data.get("children", []) == initial_children


def test_differential_language_additional_omitted_valid_in_both() -> None:
    """Omitted additional field defaults to empty list in both canonical schema and desktop validator."""
    input_ctx = {"primary": "th"}

    canonical_result = canonical_normalize_language_context(input_ctx)
    desktop_result = normalize_language_context(input_ctx)

    assert canonical_result == {"primary": "th", "additional": []}
    assert desktop_result == {"primary": "th", "additional": []}
    assert canonical_result == desktop_result


def test_differential_language_additional_empty_list_valid_in_both() -> None:
    """Empty list for additional field is valid in both."""
    input_ctx = {"primary": "en", "additional": []}

    canonical_result = canonical_normalize_language_context(input_ctx)
    desktop_result = normalize_language_context(input_ctx)

    assert canonical_result == {"primary": "en", "additional": []}
    assert desktop_result == {"primary": "en", "additional": []}
    assert canonical_result == desktop_result


@pytest.mark.parametrize(
    "bad_additional",
    [
        "en",            # string instead of list
        123,             # int instead of list
        {},              # dict instead of list
        ["toolong"],     # code > 2 chars
        ["e"],           # code < 2 chars
        ["12"],          # numeric digits
        ["en", None],    # None inside list
        ["en", 123],     # int inside list
    ],
)
def test_differential_language_additional_wrong_types_rejected_by_both(bad_additional: Any) -> None:
    """Invalid types or entries in additional must be rejected by both."""
    payload = {"primary": "th", "additional": bad_additional}

    with pytest.raises((ValueError, ValidationError)):
        canonical_normalize_language_context(payload)

    with pytest.raises(ValueError):
        normalize_language_context(payload)


def test_differential_language_normalization_and_casing() -> None:
    """Both normalize primary and additional to stripped lowercase."""
    input_ctx = {"primary": "  TH  ", "additional": ["  EN  ", "JA"]}

    canonical_result = canonical_normalize_language_context(input_ctx)
    desktop_result = normalize_language_context(input_ctx)

    assert canonical_result == {"primary": "th", "additional": ["en", "ja"]}
    assert desktop_result == {"primary": "th", "additional": ["en", "ja"]}
    assert canonical_result == desktop_result


def test_differential_language_unknown_fields_rejected_by_both() -> None:
    """Unknown fields in language_context must be rejected by both."""
    payload = {"primary": "th", "dialect": "north"}

    with pytest.raises(ValueError):
        canonical_normalize_language_context(payload)

    with pytest.raises(ValueError):
        normalize_language_context(payload)


def test_differential_whitespace_stripping_and_field_parity() -> None:
    """Whitespace stripping parity across string/enum fields between canonical models and desktop validators."""
    # 1. ChildCreateRequest
    c_req = ChildCreateRequest(
        display_code="  C-0101  ",
        birth_year=2022,
        birth_month=5,
        language_context={"primary": "th", "additional": ["en"]},
    )
    d_val = validate_child_input(
        "  C-0101  ",
        2022,
        5,
        {"primary": "th", "additional": ["en"]},
    )
    assert c_req.display_code == "C-0101"
    assert d_val["display_code"] == "C-0101"

    # 2. ConsentCreateRequest
    consent_req = ConsentCreateRequest(
        purpose="clinical_assessment",  # type: ignore[arg-type]
        scope_version="  2026.1  ",
        status="active",  # type: ignore[arg-type]
    )
    consent_val = validate_consent_input(
        child_id="  child-01  ",
        purpose="clinical_assessment",
        scope_version="  2026.1  ",
        status="active",
    )
    assert consent_req.purpose.value == "clinical_assessment"
    assert consent_val["purpose"] == "clinical_assessment"
    assert consent_req.scope_version == "2026.1"
    assert consent_val["scope_version"] == "2026.1"
    assert consent_req.status.value == "active"
    assert consent_val["status"] == "active"

    # 3. AssessmentCreateRequest
    asmt_req = AssessmentCreateRequest(
        purpose="initial",  # type: ignore[arg-type]
        assigned_clinician_id="  clinician-123  ",
    )
    asmt_val = validate_assessment_input(
        child_id="  child-01  ",
        purpose="initial",
        assigned_clinician_id="  clinician-123  ",
    )
    assert asmt_req.purpose.value == "initial"
    assert asmt_val["purpose"] == "initial"
    assert asmt_req.assigned_clinician_id == "clinician-123"
    assert asmt_val["assigned_clinician_id"] == "clinician-123"


def test_differential_enum_whitespace_rejected_by_both() -> None:
    """Whitespace-padded enum values are rejected by both canonical schemas and desktop validators."""
    with pytest.raises(ValidationError):
        ConsentCreateRequest(purpose="  clinical_assessment  ", scope_version="2026.1", status="active")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_consent_input("child-01", "  clinical_assessment  ", "2026.1", "active")

    with pytest.raises(ValidationError):
        ConsentCreateRequest(purpose="clinical_assessment", scope_version="2026.1", status="  active  ")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_consent_input("child-01", "clinical_assessment", "2026.1", "  active  ")

    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="  initial  ")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_assessment_input("child-01", "  initial  ")



def test_differential_optional_assigned_clinician_id() -> None:
    """assigned_clinician_id handles None, valid strings, and rejects whitespace-only or overlong."""
    # None
    req_none = AssessmentCreateRequest(purpose="initial", assigned_clinician_id=None)
    val_none = validate_assessment_input("c1", "initial", None)
    assert req_none.assigned_clinician_id is None
    assert val_none["assigned_clinician_id"] is None

    # Whitespace-only string -> fails min_length=1
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="initial", assigned_clinician_id="   ")
    with pytest.raises(ValueError):
        validate_assessment_input("c1", "initial", "   ")

    # Boundary 128 chars
    req_128 = AssessmentCreateRequest(purpose="initial", assigned_clinician_id="c" * 128)
    val_128 = validate_assessment_input("c1", "initial", "c" * 128)
    assert req_128.assigned_clinician_id == "c" * 128
    assert val_128["assigned_clinician_id"] == "c" * 128

    # Exceeds 128 chars
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="initial", assigned_clinician_id="c" * 129)
    with pytest.raises(ValueError):
        validate_assessment_input("c1", "initial", "c" * 129)


def test_client_convenience_default_vs_malformed_nested() -> None:
    """Documented convenience default language_context=None succeeds; explicit malformed nested value fails closed."""
    client = LinguaLensClient(mock_mode=True)

    # 1. Calling create_child without language_context (or language_context=None)
    # uses documented convenience default {"primary": "th", "additional": []}
    child1 = client.create_child("C-DEFAULT-1", 2021, 6)
    assert child1["language_context"] == {"primary": "th", "additional": []}

    child2 = client.create_child("C-DEFAULT-2", 2021, 6, language_context=None)
    assert child2["language_context"] == {"primary": "th", "additional": []}

    # 2. Calling with explicit malformed nested dict must NOT be quietly fixed to valid input
    with pytest.raises(LinguaLensValidationError):
        client.create_child("C-BAD", 2021, 6, language_context={"primary": "th", "additional": None})
