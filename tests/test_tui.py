"""Unit tests for LinguaLens Interactive Terminal UI."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from packages.tui.client import LinguaLensClient


def test_tui_client_cases_and_sessions():
    client = LinguaLensClient(mock_mode=True)
    
    # 1. Clean default starts empty
    cases = client.list_cases()
    assert len(cases) == 0

    # Explicit demo seeding works when requested
    client.seed_demo_dataset()
    demo_cases = client.list_cases()
    assert len(demo_cases) >= 2
    assert "case-demo-001" in [c["case_id"] for c in demo_cases]

    # Create new case
    new_case = client.create_case(child_id="C-TEST-99", birth_year_month="2022-01", notes="Test case")
    assert new_case["child_id"] == "C-TEST-99"
    assert new_case["case_id"].startswith("case-local-")

    # 2. Sessions
    sessions = client.list_sessions(new_case["case_id"])
    assert len(sessions) == 0

    new_sess = client.create_session(new_case["case_id"], session_date="2026-08-16", notes="Test session")
    assert new_sess["session_id"].startswith("sess-local-")
    assert new_sess["status"] == "Intake"

    updated_sessions = client.list_sessions(new_case["case_id"])
    assert len(updated_sessions) == 1


def test_tui_transcript_ingestion_and_review():
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-test-888"

    raw_dialogue = (
        "INV: สวัสดีครับ มาเล่นกันนะ\n"
        "CHI: เล่น บอล\n"
        "INV: โยนบอลมาสิครับ\n"
        "CHI: โยน บอล ไป"
    )

    tr = client.ingest_transcript_text(session_id, raw_dialogue)
    assert tr["status"] == "pending_review"
    assert len(tr["utterances"]) == 4
    assert tr["utterances"][1]["speaker"] == "CHI"
    assert tr["utterances"][1]["text"] == "เล่น บอล"

    # Edit utterance
    tr_id = tr["transcript_id"]
    updated_tr = client.update_utterance(tr_id, "u-2", "เล่น ลูกบอล", "CHI")
    assert updated_tr["utterances"][1]["text"] == "เล่น ลูกบอล"

    # Attest / Sign-off
    attested_tr = client.attest_transcript(tr_id, therapist_name="Kru Joy (SLP)")
    assert attested_tr["attested"] is True
    assert attested_tr["attested_by"] == "Kru Joy (SLP)"
    assert attested_tr["status"] == "Attested"


def test_tui_findings_and_report_signoff(tmp_path: Path):
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-test-999"

    # 1. Before ingestion: No fake findings!
    empty_findings = client.get_findings(session_id)
    assert empty_findings["has_data"] is False
    assert empty_findings["metrics"] == {}

    # Ingest real dialogue
    raw_dialogue = (
        "INV: วันนี้เรามาเล่นกันนะ\n"
        "CHI: เล่น รถ สี แดง\n"
        "INV: รถวิ่งเร็วไหมครับ\n"
        "CHI: เร็ว มาก เลย"
    )
    client.ingest_transcript_text(session_id, raw_dialogue)

    # 2. After ingestion: Genuine findings calculated
    findings = client.get_findings(session_id)
    assert findings["has_data"] is True
    assert "metrics" in findings
    assert "guideline_links" in findings
    assert findings["metrics"]["mlu_words"] > 0
    assert findings["metrics"]["total_child_utterances"] == 2

    # Draft report
    report = client.draft_report(session_id, prompt_notes="Child showed good engagement")
    assert report["status"] == "Draft"
    assert "การประเมินทักษะทางภาษา" in report["narrative"]

    # Sign-off report
    signed_report = client.sign_off_report(report["report_id"], therapist_name="Kru Joy (SLP)")
    assert signed_report["status"] == "Signed Off"
    assert signed_report["signed_by"] == "Kru Joy (SLP)"
    assert "sha256_hash" in signed_report
    assert len(signed_report["sha256_hash"]) == 64


def test_tui_audio_ingestion_and_acoustic_features(tmp_path: Path):
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-audio-123"

    # Create dummy audio file
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFFdummyWAVEfmt ")

    tr = client.ingest_audio_file(session_id, str(dummy_wav))
    assert tr["status"] == "pending_review"
    assert tr["audio_file"] == "sample.wav"
    assert len(tr["utterances"]) > 0

    findings = client.get_findings(session_id)
    assert "f0_median_hz" in findings["metrics"]
    assert "voiced_ratio_pct" in findings["metrics"]
    assert "audio_duration_sec" in findings["metrics"]


from packages.tui.client import (
    LinguaLensClient,
    LinguaLensApiError,
    LinguaLensConflictError,
    LinguaLensUnsupportedOperationError,
)
import copy


LIVE_OPERATIONS = [
    ("list_cases", lambda c: c.list_cases()),
    ("create_case", lambda c: c.create_case("child-code", "2021-01")),
    ("list_sessions", lambda c: c.list_sessions("case-demo-001")),
    ("create_session", lambda c: c.create_session("case-demo-001", "2026-09-12")),
    ("get_session_transcript", lambda c: c.get_session_transcript("sess-demo-102")),
    ("ingest_transcript_text", lambda c: c.ingest_transcript_text("sess-demo-102", "INV: Hello\nCHI: Car")),
    ("attest_transcript", lambda c: c.attest_transcript("tr-demo-001", "Therapist")),
    ("get_findings", lambda c: c.get_findings("sess-demo-102")),
    ("draft_report", lambda c: c.draft_report("sess-demo-102")),
    ("sign_off_report", lambda c: c.sign_off_report("rep-demo-101", "Therapist")),
    ("get_report", lambda c: c.get_report("rep-demo-101")),
    ("get_session_report", lambda c: c.get_session_report("sess-demo-101")),
    ("create_child", lambda c: c.create_child("LL-01", 2021, 5)),
    ("get_child", lambda c: c.get_child("child-01")),
    ("list_children", lambda c: c.list_children()),
    ("record_consent", lambda c: c.record_consent("child-01")),
    ("list_consents", lambda c: c.list_consents("child-01")),
    ("create_assessment", lambda c: c.create_assessment("child-01")),
    ("list_assessments", lambda c: c.list_assessments("child-01")),
    ("get_assessment", lambda c: c.get_assessment("asmt-01")),
]



@pytest.mark.parametrize("op_name,op_func", LIVE_OPERATIONS)
def test_live_api_errors_never_fall_back_to_local_mock_state(op_name, op_func, monkeypatch):
    """Every live operation independently raises on network/server error and preserves local state."""
    client = LinguaLensClient(mock_mode=False, seed_demo=True)
    initial_mock_state = copy.deepcopy(client._mock_data)

    def fail_request(*args, **kwargs):
        raise LinguaLensApiError("API request failed: offline")

    monkeypatch.setattr(client, "_http_request", fail_request)

    with pytest.raises(LinguaLensApiError):
        op_func(client)

    # Assert entire mock state is completely untouched and identical
    assert client._mock_data == initial_mock_state


LOCAL_ONLY_UNSUPPORTED_OPERATIONS = [
    ("ingest_audio_file", lambda c, tmp: c.ingest_audio_file("sess-demo-101", str(tmp / "fake.wav"))),
    ("update_utterance", lambda c, tmp: c.update_utterance("tr-demo-001", "u-1", "new text", "CHI")),
    ("auto_refine_speakers", lambda c, tmp: c.auto_refine_speakers("tr-demo-001")),
    ("swap_speakers", lambda c, tmp: c.swap_speakers("tr-demo-001", "CHI", "INV")),
]


@pytest.mark.parametrize("op_name,op_func", LOCAL_ONLY_UNSUPPORTED_OPERATIONS)
def test_live_client_rejects_unsupported_local_only_operations(op_name, op_func, tmp_path):
    """When mock_mode=False, operations without backend API equivalents must fail explicitly before mutation."""
    client = LinguaLensClient(mock_mode=False, seed_demo=True)
    initial_mock_state = copy.deepcopy(client._mock_data)

    # Create dummy audio file for ingest_audio_file
    fake_wav = tmp_path / "fake.wav"
    fake_wav.write_bytes(b"RIFFdummyWAVEfmt ")

    with pytest.raises(LinguaLensUnsupportedOperationError) as exc_info:
        op_func(client, tmp_path)

    assert "unsupported" in str(exc_info.value).lower() or "local mode" in str(exc_info.value).lower()
    assert client._mock_data == initial_mock_state


def test_workflow_runner_recovers_from_api_error_in_main_loop(monkeypatch):
    """Verify that an API error inside WorkflowRunner.start() does not abort the loop without recovery."""
    from packages.tui.workflow import WorkflowRunner
    client = LinguaLensClient(mock_mode=False)
    runner = WorkflowRunner(client)

    calls = 0
    def failing_list_cases():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LinguaLensApiError("API service unreachable")
        return []

    monkeypatch.setattr(client, "list_cases", failing_list_cases)
    monkeypatch.setattr(client, "check_health", lambda: False)

    # First prompt ask is from error handler "Press Enter to continue", second is "q" to quit
    inputs = iter(["", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    # Should not raise LinguaLensApiError out of start()
    runner.start()


def test_workflow_runner_handles_auth_error_with_reauth_guidance(monkeypatch):
    """Verify that an HTTP 401 auth error inside WorkflowRunner provides explicit sign-in/re-auth guidance."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensAuthError
    client = LinguaLensClient(mock_mode=False)
    runner = WorkflowRunner(client)

    calls = 0
    def auth_failed_list_cases():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LinguaLensAuthError("Authentication failed: HTTP 401 Session expired or invalid token.")
        return []

    monkeypatch.setattr(client, "list_cases", auth_failed_list_cases)
    monkeypatch.setattr(client, "check_health", lambda: False)

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    inputs = iter(["", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner.start()

    # Verify sign-in / re-authentication guidance was rendered
    full_output = " ".join(printed_lines)
    assert "sign-in" in full_output.lower() or "re-authenticate" in full_output.lower() or "session expired" in full_output.lower() or "auth" in full_output.lower()


def test_tui_client_v2_mock_stage1_flow():
    """Verify Stage 1 V2 mock mode operations: child creation, consent tracking, and gated assessment."""
    client = LinguaLensClient(mock_mode=True)

    # 1. Starts empty
    assert client.list_children() == []

    # 2. Create child
    child = client.create_child(
        display_code="CHI-MOCK-01",
        birth_year=2021,
        birth_month=5,
        language_context={"primary": "th", "additional": []},
    )
    assert child["display_code"] == "CHI-MOCK-01"
    assert child["birth_year"] == 2021
    assert child["birth_month"] == 5
    assert "id" in child

    child_id = child["id"]
    children = client.list_children()
    assert len(children) == 1
    assert children[0]["id"] == child_id

    fetched = client.get_child(child_id)
    assert fetched["id"] == child_id

    # 3. Create assessment without consent fails with LinguaLensConflictError
    with pytest.raises(LinguaLensConflictError):
        client.create_assessment(child_id, purpose="initial")

    # 4. Record consent
    consent = client.record_consent(
        child_id=child_id,
        purpose="clinical_assessment",
        scope_version="2026.1",
        status="active",
    )
    assert consent["child_id"] == child_id
    assert consent["status"] == "active"
    assert "id" in consent

    consents = client.list_consents(child_id)
    assert len(consents) == 1
    assert consents[0]["id"] == consent["id"]

    active_consent = client.get_active_consent(child_id)
    assert active_consent is not None
    assert active_consent["id"] == consent["id"]

    # 5. Now create assessment succeeds
    assessment = client.create_assessment(child_id, purpose="initial", assigned_clinician_id="therapist_mock")
    assert assessment["child_id"] == child_id
    assert assessment["purpose"] == "initial"
    assert assessment["state"] == "draft"
    assert "id" in assessment

    assessments = client.list_assessments(child_id)
    assert len(assessments) == 1
    assert assessments[0]["id"] == assessment["id"]

    # 6. Get assessment detail by assessment_id
    detail = client.get_assessment(assessment["id"])
    assert detail["id"] == assessment["id"]
    assert detail["child_id"] == child_id

    # 7. Nonexistent assessment raises LinguaLensApiError
    with pytest.raises(LinguaLensApiError):
        client.get_assessment("asmt_nonexistent")

    # 8. Record consent withdrawal and verify active consent becomes None
    withdrawal = client.record_consent(
        child_id=child_id,
        purpose="clinical_assessment",
        scope_version="2026.1",
        status="withdrawn",
    )
    assert withdrawal["status"] == "withdrawn"
    assert client.get_active_consent(child_id) is None

    # Creating another assessment now fails due to withdrawn consent
    with pytest.raises(LinguaLensConflictError):
        client.create_assessment(child_id, purpose="developmental_follow_up")


def test_mock_consent_versioning_per_purpose_and_child_isolation() -> None:
    """Failing regression test: Consent versions must increment per purpose, not per child total.

    Sequence:
    1. Child 1: clinical active -> version 1
    2. Child 1: research active -> version 1 (isolated purpose sequence)
    3. Child 1: clinical withdrawn -> version 2 (clinical sequence: 1 -> 2)
    4. Child 1: clinical active -> version 3 (clinical sequence: 1 -> 2 -> 3)
    Verify active consent derivation and child isolation.
    """
    client = LinguaLensClient(base_url="http://localhost:8000", mock_mode=True)
    child_1 = "child_alpha"
    child_2 = "child_beta"
    client.create_child(child_1, 2021, 6, {"primary": "th"})
    client.create_child(child_2, 2021, 6, {"primary": "th"})

    # Step 1: clinical active -> version 1
    c1 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c1["version"] == 1
    assert c1["purpose"] == "clinical_assessment"
    assert c1["status"] == "active"

    # Step 2: research active -> version 1 (isolated by purpose!)
    c2 = client.record_consent(child_1, purpose="research_reuse", status="active")
    assert c2["version"] == 1
    assert c2["purpose"] == "research_reuse"
    assert c2["status"] == "active"

    # Step 3: clinical withdrawn -> version 2 (clinical purpose version increases from 1 to 2)
    c3 = client.record_consent(child_1, purpose="clinical_assessment", status="withdrawn")
    assert c3["version"] == 2
    assert c3["purpose"] == "clinical_assessment"
    assert c3["status"] == "withdrawn"

    # Active consent derivation: latest clinical consent is withdrawn, so None
    assert client.get_active_consent(child_1) is None

    # Step 4: clinical active -> version 3 (clinical purpose version increases from 2 to 3)
    c4 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c4["version"] == 3
    assert c4["purpose"] == "clinical_assessment"
    assert c4["status"] == "active"

    # Active consent derivation: latest clinical consent is now version 3 active
    active = client.get_active_consent(child_1)
    assert active is not None
    assert active["version"] == 3
    assert active["status"] == "active"

    # Child isolation: Child 2 gets clinical active -> version 1 (not 4)
    c2_1 = client.record_consent(child_2, purpose="clinical_assessment", status="active")
    assert c2_1["version"] == 1
    assert c2_1["child_id"] == child_2


def test_tui_child_intake_and_selection():
    """WorkflowRunner tracks active_child_id and flushes context on switch."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient

    client = LinguaLensClient(mock_mode=True)
    runner = WorkflowRunner(client)

    # Initial state
    assert runner.active_child_id is None
    assert runner.active_child is None
    child_1 = client.create_child("C-TEST-01", 2021, 3)
    child_2 = client.create_child("C-TEST-02", 2022, 5)

    # Select child 1 in runner
    runner._set_active_child(child_1["id"])
    assert runner.active_child_id == child_1["id"]
    assert runner.active_child["display_code"] == "C-TEST-01"

    # Set mock assessment
    runner.active_assessment_id = "asmt-001"

    # Switch to child 2 -> flushes assessment ID
    runner._set_active_child(child_2["id"])
    assert runner.active_child_id == child_2["id"]
    assert runner.active_child["display_code"] == "C-TEST-02"
    assert runner.active_assessment_id is None


def test_tui_set_active_child_failure_never_fabricates_child():
    """WorkflowRunner._set_active_child must not fabricate a child dictionary upon API failure."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensApiError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.get_child.side_effect = LinguaLensApiError("Child not found")
    runner = WorkflowRunner(client)

    runner._set_active_child("nonexistent")
    assert runner.active_child_id is None
    assert runner.active_child is None


def test_tui_set_active_child_401_clears_clinical_context():
    """When get_child raises 401, WorkflowRunner clears active clinical context."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.get_child.side_effect = LinguaLensAuthError("401 Unauthorized")
    runner = WorkflowRunner(client)
    runner.active_child_id = "prev-c"
    runner.active_child = {"id": "prev-c"}

    runner._set_active_child("c1")
    assert runner.active_child_id is None
    assert runner.active_child is None


def test_tui_main_loop_reaches_children_menu_and_create_wizard(monkeypatch):
    """WorkflowRunner.start() main loop offers Child Directory [C] and creates a child via wizard."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient

    client = LinguaLensClient(mock_mode=True)
    runner = WorkflowRunner(client)

    # Sequence of user prompts:
    # 1. Main cases menu: choose 'c' to open Child Directory
    # 2. Children menu: choose 'n' to create new child
    # 3. Wizard prompt: display_code -> "C-TUI-WIZARD"
    # 4. Wizard prompt: birth_year -> "2021"
    # 5. Wizard prompt: birth_month -> "8"
    # 6. Wizard prompt: language -> "th"
    # 7. Wizard prompt: press enter to continue
    # 8. Children menu: choose 'b' to go back
    # 9. Main cases menu: choose 'q' to quit
    inputs = iter(["c", "n", "C-TUI-WIZARD", "2021", "8", "th", "", "b", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))
    monkeypatch.setattr(client, "check_health", lambda: True)

    runner.start()

    # Verify that child was created in client and selected in runner
    children = client.list_children()
    matching = [c for c in children if c.get("display_code") == "C-TUI-WIZARD"]
    assert len(matching) == 1
    assert matching[0]["birth_year"] == 2021
    assert matching[0]["birth_month"] == 8
    assert matching[0]["language_context"]["primary"] == "th"
    # Runner active child was set
    assert runner.active_child_id == matching[0]["id"]
    # Legacy active_case_id must not be set
    assert runner.active_case_id is None


def test_tui_main_loop_reaches_v2_when_legacy_list_cases_fails(monkeypatch):
    """WorkflowRunner allows entering V2 Child Directory even if legacy list_cases fails."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensApiError

    client = LinguaLensClient(mock_mode=True)
    # Configure legacy list_cases to raise 500 error
    list_cases_calls = 0
    def failing_list_cases():
        nonlocal list_cases_calls
        list_cases_calls += 1
        raise LinguaLensApiError("500 Legacy Database Unavailable")

    monkeypatch.setattr(client, "list_cases", failing_list_cases)
    monkeypatch.setattr(client, "check_health", lambda: True)

    runner = WorkflowRunner(client)

    # User enters 'c' to open Child Directory on error recovery, creates child via 'n', then 'q' to quit
    inputs = iter(["c", "n", "C-V2-ISOLATED", "2022", "3", "th", "", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner.start()

    # Verify that child was created and active_child_id was set in V2 context
    children = client.list_children()
    matching = [c for c in children if c.get("display_code") == "C-V2-ISOLATED"]
    assert len(matching) == 1
    assert runner.active_child_id == matching[0]["id"]
    assert runner.active_case_id is None
    # Confirm V2 navigation did not call legacy list_cases even once
    assert list_cases_calls == 0


def test_tui_main_loop_auth_error_wipes_v2_and_legacy_contexts(monkeypatch):
    """Main-loop 401 must wipe both V2 and legacy clinical contexts and clear session."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError
    from unittest.mock import MagicMock

    client = LinguaLensClient(mock_mode=True)
    client.clear_session = MagicMock()
    runner = WorkflowRunner(client)
    # Populate both legacy and V2 contexts
    runner.active_case_id = "CASE-LEGACY-01"
    runner.active_session_id = "SESS-01"
    runner.active_transcript = {"utterances": []}
    runner.active_child_id = "CHILD-V2-01"
    runner.active_child = {"id": "CHILD-V2-01"}
    runner.active_consent = {"consent_id": "CON-01"}
    runner.active_assessment_id = "ASM-01"
    runner.active_assessment = {"assessment_id": "ASM-01"}

    client.get_session_transcript = MagicMock(side_effect=LinguaLensAuthError("HTTP 401 Session Expired"))
    monkeypatch.setattr(client, "check_health", lambda: True)

    inputs = iter(["", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner.start()

    # All contexts must be cleared!
    assert runner.active_case_id is None
    assert runner.active_session_id is None
    assert runner.active_transcript is None
    assert runner.active_child_id is None
    assert runner.active_child is None
    assert runner.active_consent is None
    assert runner.active_assessment_id is None
    assert runner.active_assessment is None
    client.clear_session.assert_called_once()


def test_tui_main_loop_direct_v2_route_never_calls_legacy_list_cases(monkeypatch):
    """Selecting V2 at entry must never invoke legacy list_cases even once."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensApiError
    from unittest.mock import MagicMock

    client = LinguaLensClient(mock_mode=True)
    # If list_cases is called, it fails the test immediately
    client.list_cases = MagicMock(side_effect=LinguaLensApiError("CRITICAL: Legacy list_cases was called on V2 route!"))
    monkeypatch.setattr(client, "check_health", lambda: True)

    runner = WorkflowRunner(client)

    # 1. Entry menu: choose 'c' to enter Child Directory directly
    # 2. Child directory: choose 'b' to go back (or 'q' to quit)
    # 3. Entry menu: choose 'q' to quit
    inputs = iter(["c", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    # Run main loop: must not raise LinguaLensApiError from list_cases
    runner.start()

    # Legacy list_cases must have ZERO calls!
    client.list_cases.assert_not_called()


def test_tui_v2_list_children_api_failure_contained_allows_clean_exit(monkeypatch):
    """When list_children fails with API error, error is contained and allows clean exit via [Q]uit."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensApiError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.list_children.side_effect = LinguaLensApiError("503 Gateway Timeout")

    runner = WorkflowRunner(client)

    # 1. Entry menu: choose 'c' to go to Child Directory
    # 2. Error boundary prompt: choose 'q' to quit
    inputs = iter(["c", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    # Must NOT crash with unhandled exception
    runner.start()


def test_tui_v2_401_and_403_lifecycle_in_main_error_boundary(monkeypatch):
    """V2 401 clears context and session; V2 403 shows denial and preserves session without logout."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError, LinguaLensPermissionError
    from unittest.mock import MagicMock

    # Part 1: 401 on V2
    client_401 = MagicMock(spec=LinguaLensClient)
    client_401.check_health.return_value = True
    client_401.list_children.side_effect = LinguaLensAuthError("401 Token Expired")

    runner_401 = WorkflowRunner(client_401)
    runner_401.active_child_id = "c-will-be-cleared"
    runner_401.active_child = {"id": "c-will-be-cleared"}

    # 1. 'c' (V2 route), 2. Enter (re-auth acknowledge), 3. 'q' (quit)
    inputs_401 = iter(["c", "", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_401))

    runner_401.start()
    assert runner_401.active_child_id is None
    assert runner_401.active_child is None
    client_401.clear_session.assert_called_once()

    # Part 2: 403 on V2
    client_403 = MagicMock(spec=LinguaLensClient)
    client_403.check_health.return_value = True
    client_403.list_children.side_effect = LinguaLensPermissionError("403 Forbidden Organization")

    runner_403 = WorkflowRunner(client_403)
    runner_403.active_child_id = "c-keep-403"
    runner_403.active_child = {"id": "c-keep-403"}

    inputs_403 = iter(["c", "", "q"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_403))

    runner_403.start()
    # 403 MUST NOT clear session / logout!
    client_403.clear_session.assert_not_called()


# =============================================================================
# Subtask B: TUI Consent Display & Explicit Wizard Tests
# =============================================================================

def test_tui_child_workspace_displays_consent_states(monkeypatch):
    """TUI renders distinct consent states (active, withdrawn, no-record, error) in child workspace."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensApiError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    # Test 1: Active
    client.list_consents.return_value = [
        {"id": "con-1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]
    status_active, rec_active = runner._resolve_consent_state("c1")
    assert status_active == "active"
    assert rec_active["version"] == 1

    # Test 2: Withdrawn
    client.list_consents.return_value = [
        {"id": "con-1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1},
        {"id": "con-2", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "withdrawn", "version": 2},
    ]
    status_withdrawn, rec_withdrawn = runner._resolve_consent_state("c1")
    assert status_withdrawn == "withdrawn"
    assert rec_withdrawn["version"] == 2

    # Test 3: No Record
    client.list_consents.return_value = []
    status_norec, rec_norec = runner._resolve_consent_state("c1")
    assert status_norec == "no-record"
    assert rec_norec is None

    # Test 4: Error
    client.list_consents.side_effect = LinguaLensApiError("API offline")
    status_err, rec_err = runner._resolve_consent_state("c1")
    assert status_err == "error"
    assert rec_err is None


def test_tui_record_consent_wizard_active_and_withdrawn_explicit_confirmation(monkeypatch):
    """TUI record consent wizard requires explicit confirmation before mutation for active and withdrawn."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.record_consent.return_value = {
        "id": "con-w", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }
    client.list_consents.return_value = []

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    # Wizard flow 1: Choose active ("1"), scope ("2026.1"), confirm ("y"), enter to finish
    inputs1 = iter(["1", "2026.1", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs1))

    runner._record_consent_wizard()
    client.record_consent.assert_called_once_with("c1", "clinical_assessment", "2026.1", "active")

    # Wizard flow 2: Choose withdrawn ("2"), scope ("2026.1"), confirm ("y"), enter to finish
    client.record_consent.reset_mock()
    inputs2 = iter(["2", "2026.1", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs2))

    runner._record_consent_wizard()
    client.record_consent.assert_called_once_with("c1", "clinical_assessment", "2026.1", "withdrawn")


def test_tui_record_consent_cancel_does_not_call_api(monkeypatch):
    """Cancelling in TUI record consent wizard makes zero calls to record_consent."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    # Case 1: Cancel at action prompt ("c")
    inputs_c = iter(["c"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_c))
    runner._record_consent_wizard()
    client.record_consent.assert_not_called()

    # Case 2: Reject confirmation ("n")
    inputs_n = iter(["1", "2026.1", "n"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_n))
    runner._record_consent_wizard()
    client.record_consent.assert_not_called()


def test_tui_record_consent_401_and_403_handling(monkeypatch):
    """Wizard bubbles 401 to main error boundary and handles 403 by showing denial."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError, LinguaLensPermissionError
    from unittest.mock import MagicMock
    import pytest

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    # 401 should be raised out of wizard so main loop error boundary catches it
    client.record_consent.side_effect = LinguaLensAuthError("401 Token Expired")
    inputs_401 = iter(["1", "2026.1", "y"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_401))
    with pytest.raises(LinguaLensAuthError):
        runner._record_consent_wizard()

    # 403 should be caught or raised to error boundary
    client.record_consent.side_effect = LinguaLensPermissionError("403 Forbidden")
    inputs_403 = iter(["1", "2026.1", "y"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs_403))
    with pytest.raises(LinguaLensPermissionError):
        runner._record_consent_wizard()


def test_tui_record_consent_409_conflict_shows_guidance(monkeypatch):
    """409 Conflict displays clear guidance and triggers consent history refresh without crash."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensConflictError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.record_consent.side_effect = LinguaLensConflictError("409 Conflict: Scope version mismatch")
    client.list_consents.return_value = []

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    inputs = iter(["1", "2026.1", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    # Must NOT crash with unhandled exception
    runner._record_consent_wizard()

    # Must have triggered refresh of consents
    client.list_consents.assert_called()
    output = " ".join(printed_lines)
    assert "conflict" in output.lower() or "409" in output


def test_tui_record_consent_wizard_blank_scope_version_rejected(monkeypatch):
    """Empty scope version is rejected client-side in wizard without calling record_consent."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    # Action 1 (active), then empty scope version ("")
    inputs = iter(["1", "   ", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._record_consent_wizard()
    client.record_consent.assert_not_called()
    output = " ".join(printed_lines)
    assert "required" in output.lower() or "empty" in output.lower()


def test_tui_record_consent_wizard_post_mutation_refresh_401_not_swallowed(monkeypatch):
    """When mutation succeeds but refresh returns 401, 401 is NOT swallowed and bubbles to error boundary."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError
    from unittest.mock import MagicMock
    import pytest

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.record_consent.return_value = {
        "id": "con-ok", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }
    client.list_consents.side_effect = LinguaLensAuthError("401 Session Expired on Refresh")

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    inputs = iter(["1", "2026.1", "y"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    # Must raise LinguaLensAuthError rather than silently swallowing it with except Exception: pass
    with pytest.raises(LinguaLensAuthError):
        runner._record_consent_wizard()


def test_tui_record_consent_wizard_post_mutation_refresh_403_shows_warning_no_crash(monkeypatch):
    """When mutation succeeds but refresh returns 403, permission denial is displayed without crash or raising unhandled."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensPermissionError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.record_consent.return_value = {
        "id": "con-ok", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }
    client.list_consents.side_effect = LinguaLensPermissionError("403 Forbidden to list consents")

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    inputs = iter(["1", "2026.1", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._record_consent_wizard()
    output = " ".join(printed_lines)
    assert "denied" in output.lower() or "403" in output or "permission" in output.lower()


def test_tui_record_consent_wizard_409_refresh_401_not_swallowed(monkeypatch):
    """When mutation returns 409 and authoritative refresh returns 401, 401 is NOT swallowed."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensConflictError, LinguaLensAuthError
    from unittest.mock import MagicMock
    import pytest

    client = MagicMock(spec=LinguaLensClient)
    client.check_health.return_value = True
    client.record_consent.side_effect = LinguaLensConflictError("409 Conflict")
    client.list_consents.side_effect = LinguaLensAuthError("401 Unauthorized during conflict refresh")

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    inputs = iter(["1", "2026.1", "y"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    with pytest.raises(LinguaLensAuthError):
        runner._record_consent_wizard()


# ============================================================================
# Subtask C: Assessment Creation & Safe Desktop Context Transition (TUI)
# ============================================================================

def test_tui_create_assessment_wizard_requires_active_consent(monkeypatch):
    """When consent is not active (no-record or withdrawn), wizard warns and aborts without calling create_assessment."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "withdrawn", "version": 1}
    ]

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "")

    runner._create_assessment_wizard()

    output = " ".join(printed_lines)
    assert "consent" in output.lower()
    client.create_assessment.assert_not_called()
    assert runner.active_assessment_id is None


def test_tui_create_assessment_wizard_canonical_payload_and_state_isolation(monkeypatch):
    """When consent is active, wizard prompts for purpose & clinician, calls client, and isolates assessment state."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}
    ]
    created_asmt = {
        "id": "asmt-tui-001",
        "child_id": "c1",
        "purpose": "initial",
        "state": "draft",
        "age_months": 36,
        "language_context": {"primary": "th", "additional": []},
        "assigned_clinician_id": "clinician-tui",
        "version": 1,
    }
    client.create_assessment.return_value = created_asmt

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    # Inputs: Purpose choice "1" (initial), Clinician ID "clinician-tui", Confirmation "y", Continue ""
    inputs = iter(["1", "clinician-tui", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_assessment_wizard()

    client.create_assessment.assert_called_once_with(
        "c1",
        purpose="initial",
        assigned_clinician_id="clinician-tui",
    )
    assert runner.active_assessment_id == "asmt-tui-001"
    assert runner.active_assessment == created_asmt
    # Session state must remain untouched
    assert runner.active_session_id is None


def test_tui_create_assessment_wizard_409_conflict_handling(monkeypatch):
    """When create_assessment returns 409 conflict, displays conflict message, re-checks consent, no active assessment."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient, LinguaLensConflictError
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    # First consent check returns active, second check (after 409) returns withdrawn
    client.list_consents.side_effect = [
        [{"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}],
        [{"id": "con-2", "child_id": "c1", "purpose": "clinical_assessment", "status": "withdrawn", "version": 2}],
    ]
    client.create_assessment.side_effect = LinguaLensConflictError("409 Conflict: Active consent required.")

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    # Purpose "1", Clinician "", Confirmation "y", Continue ""
    inputs = iter(["1", "", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_assessment_wizard()

    output = " ".join(printed_lines)
    assert "conflict" in output.lower() or "409" in output or "consent" in output.lower()
    assert runner.active_assessment_id is None
    # No retry
    assert client.create_assessment.call_count == 1


def test_tui_create_assessment_wizard_rejects_invalid_purpose(monkeypatch):
    """When an invalid purpose is entered, TUI displays a validation error and does NOT call create_assessment."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}
    ]

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    printed_lines = []
    monkeypatch.setattr("rich.console.Console.print", lambda self, *args, **kwargs: printed_lines.append(" ".join(str(a) for a in args)))

    # User enters "9" (invalid choice), then enters "" to continue
    inputs = iter(["9", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_assessment_wizard()

    client.create_assessment.assert_not_called()
    output = " ".join(printed_lines)
    assert "invalid" in output.lower() or "purpose" in output.lower()


@pytest.mark.parametrize("choice_input,expected_purpose", [
    ("1", "initial"),
    ("2", "developmental_follow_up"),
    ("3", "post_intervention_follow_up"),
    ("4", "additional_evidence"),
])
def test_tui_create_assessment_wizard_all_canonical_purposes(monkeypatch, choice_input, expected_purpose):
    """All 4 canonical purposes in TUI menu map correctly to backend enum."""
    from packages.tui.workflow import WorkflowRunner
    from packages.tui.client import LinguaLensClient
    from unittest.mock import MagicMock

    client = MagicMock(spec=LinguaLensClient)
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}
    ]
    created_asmt = {
        "id": f"asmt-{expected_purpose}",
        "child_id": "c1",
        "purpose": expected_purpose,
        "state": "draft",
        "version": 1,
    }
    client.create_assessment.return_value = created_asmt

    runner = WorkflowRunner(client)
    runner.active_child_id = "c1"
    runner.active_child = {"id": "c1", "display_code": "C-TUI-01"}

    inputs = iter([choice_input, "", "y", ""])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(inputs))

    runner._create_assessment_wizard()

    client.create_assessment.assert_called_once_with(
        "c1",
        purpose=expected_purpose,
        assigned_clinician_id=None,
    )
    assert runner.active_assessment_id == f"asmt-{expected_purpose}"

