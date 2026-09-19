from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
NATIVE_CHECK = ROOT / "scripts" / "check_assessment_v2_native.py"
SETUP_DOCS = (
    ROOT / "DEVELOPER_SETUP.md",
    ROOT / "docs" / "DEVELOPMENT.md",
    ROOT / "README.md",
)


def test_native_runtime_check_exists_and_does_not_depend_on_docker() -> None:
    assert NATIVE_CHECK.is_file(), "native assessment runtime check is missing"

    source = NATIVE_CHECK.read_text()

    assert "docker" not in source.lower()
    assert "subprocess.Popen" in source
    assert "uvicorn" in source
    assert "LINGUALENS_ASSESSMENT_TEST_DATABASE_URL" in source
    assert "assessment-v2 native runtime check passed" in source
    assert "test_postgres_processing_leases.py" in source
    assert "app.assessment_v2.worker_runtime" in source
    assert "/evidence-runs" in source
    assert "status_code != 202" in source
    assert "_wait_for_evidence_success" in source
    assert "not_diagnostic" in source
    assert "decision_support_only" in source
    assert "transcript-segment-sets" in source
    assert "audio-replay-grant" in source
    assert "segment_set_sha256" in source
    assert "second-tenant" in source
    assert "consent denial" in source
    assert "unassigned-role denial" in source


def test_native_runtime_check_uses_an_ephemeral_database_and_cleans_it_up() -> None:
    assert NATIVE_CHECK.is_file(), "native assessment runtime check is missing"

    source = NATIVE_CHECK.read_text()

    assert "CREATE DATABASE" in source
    assert "DROP DATABASE" in source
    assert "_wait_for_api" in source
    assert "_stop_api(worker_process, worker_log_file)" in source
    assert "finally" in source


def test_local_setup_documents_native_runtime_as_the_primary_gate() -> None:
    for document in SETUP_DOCS:
        source = document.read_text()
        assert "check_assessment_v2_native.py" in source
        assert "Docker" in source
        assert "optional" in source.lower()
