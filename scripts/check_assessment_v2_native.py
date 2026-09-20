"""Exercise assessment v2 against a fresh native PostgreSQL database and API process."""

from __future__ import annotations

import os
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
DEFAULT_ADMIN_URL = "postgresql+psycopg://localhost:5432/postgres"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
TABLES = (
    "organizations",
    "user_profiles",
    "organization_memberships",
    "children",
    "care_team_assignments",
    "consent_records",
    "assessments",
    "audit_events",
    "protocol_versions",
    "protocol_activities",
    "assessment_protocol_selections",
    "recordings",
    "processing_runs",
    "recording_quality_results",
    "transcript_revisions",
    "evidence_runs",
    "evidence_feature_values",
    "evidence_domain_profiles",
    "transcript_segment_sets",
    "transcript_segments",
    "assessment_observations",
    "assessment_instruments",
    "assessment_instrument_items",
    "assessment_comparisons",
    "assessment_comparison_features",
    "assessment_clinical_reviews",
    "assessment_attention_cues",
    "assessment_reports",
)


class NativeHTTPError(RuntimeError):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Native API returned HTTP {status_code}: {body[:500]}")


def _psycopg_url(database_url: URL) -> str:
    return database_url.set(drivername="postgresql").render_as_string(hide_password=False)


def _admin_url() -> URL:
    value = (
        os.getenv("LINGUALENS_NATIVE_ADMIN_DATABASE_URL")
        or os.getenv("LINGUALENS_ASSESSMENT_TEST_DATABASE_URL")
        or DEFAULT_ADMIN_URL
    )
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("Native assessment check requires a PostgreSQL URL.")
    if parsed.host not in ALLOWED_HOSTS:
        raise RuntimeError("Native assessment check only permits an explicit local PostgreSQL host.")
    return parsed.set(database="postgres")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _create_database(admin_url: URL, database_name: str) -> None:
    with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


def _configure_application_role(
    owner_url: URL,
    database_name: str,
    role_name: str,
    role_password: str,
) -> None:
    with psycopg.connect(_psycopg_url(owner_url), autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}")
            .format(sql.Identifier(role_name), sql.Literal(role_password))
        )

    target_url = owner_url.set(database=database_name)
    with psycopg.connect(_psycopg_url(target_url), autocommit=True) as connection:
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
        )
        connection.execute(
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
        )
        for table_name in TABLES:
            connection.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {} TO {}")
                .format(sql.Identifier(table_name), sql.Identifier(role_name))
            )
        connection.execute(
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}")
            .format(sql.Identifier(role_name))
        )


def _migrate(owner_url: URL, revision: str = "head") -> None:
    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = owner_url.render_as_string(hide_password=False)
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(1, str(ROOT))

    from app.assessment_v2.db.migrations_runner import upgrade_assessment_database
    from app.core.config import get_settings

    get_settings.cache_clear()
    upgrade_assessment_database(revision)


def _downgrade(owner_url: URL, revision: str) -> None:
    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = owner_url.render_as_string(hide_password=False)
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(1, str(ROOT))

    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database
    from app.core.config import get_settings

    get_settings.cache_clear()
    downgrade_assessment_database(revision)


def _transfer_assessment_ownership(database_url: URL, role_name: str) -> None:
    """Model the supported deployment where the non-bypass-RLS app role migrates."""

    with psycopg.connect(_psycopg_url(database_url), autocommit=True) as connection:
        for table_name in (*TABLES, "alembic_version"):
            if connection.execute(
                "SELECT to_regclass(%s)",
                (f"public.{table_name}",),
            ).fetchone()[0] is None:
                continue
            connection.execute(
                sql.SQL("ALTER TABLE {} OWNER TO {}")
                .format(sql.Identifier(table_name), sql.Identifier(role_name))
            )


def _processing_run_ids(database_url: URL, organization_id: str) -> list[str]:
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            (organization_id,),
        )
        rows = connection.execute(
            "SELECT processing_run_id FROM processing_runs "
            "WHERE organization_id = %s ORDER BY processing_run_id",
            (organization_id,),
        ).fetchall()
    return [str(row[0]) for row in rows]


def _insert_migration_probe_processing_run(database_url: URL, assessment_id: str) -> str:
    """Create one valid legacy capture row before the 0007 upgrade probe."""

    recording_id = f"native-migration-recording-{uuid4().hex[:12]}"
    processing_run_id = f"native-migration-run-{uuid4().hex[:12]}"
    checksum = "sha256:" + ("0" * 64)
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        connection.execute(
            "SELECT set_config('app.current_user_id', %s, true)",
            ("native-check-therapist",),
        )
        connection.execute(
            "INSERT INTO recordings "
            "(recording_id, organization_id, assessment_id, protocol_version_key, activity_key, "
            "declared_content_type, declared_size_bytes, declared_checksum, object_key, upload_state, "
            "expires_at, version, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', "
            "CURRENT_TIMESTAMP + INTERVAL '1 hour', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                recording_id,
                "native-check-org",
                assessment_id,
                "thai_guided_language_sample:v0",
                "free_play",
                "audio/wav",
                128,
                checksum,
                f"capture/{recording_id}",
            ),
        )
        connection.execute(
            "INSERT INTO processing_runs "
            "(processing_run_id, organization_id, recording_id, assessment_id, transcript_revision_id, "
            "evidence_run_id, stage, state, idempotency_key, attempt_count, max_attempts, available_at, "
            "version, created_at, updated_at) "
            "VALUES (%s, %s, %s, NULL, NULL, NULL, 'upload_verification', 'queued', %s, 0, 3, "
            "CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                processing_run_id,
                "native-check-org",
                recording_id,
                f"native:migration:{processing_run_id}",
            ),
        )
    return processing_run_id


def _seed_probe_membership(database_url: URL) -> None:
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        connection.execute(
            "INSERT INTO organizations "
            "(organization_id, display_label, active, created_at, updated_at) "
            "VALUES (%s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("native-check-org", "Synthetic Native Check Organization"),
        )
        connection.execute(
            "INSERT INTO user_profiles "
            "(user_id, display_label, created_at, updated_at) "
            "VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("native-check-therapist", "Synthetic Native Check Therapist"),
        )
        connection.execute(
            "INSERT INTO organization_memberships "
            "(membership_id, organization_id, user_id, role, active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                "native-check-membership",
                "native-check-org",
                "native-check-therapist",
                "therapist",
            ),
        )


def _seed_secondary_membership(database_url: URL) -> None:
    """Create an authenticated second tenant for the cross-tenant denial probe."""

    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "INSERT INTO organizations "
            "(organization_id, display_label, active, created_at, updated_at) "
            "VALUES (%s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("native-check-second-org", "Synthetic Second Organization"),
        )
        connection.execute(
            "INSERT INTO user_profiles "
            "(user_id, display_label, created_at, updated_at) "
            "VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("native-check-second-therapist", "Synthetic Second Therapist"),
        )
        connection.execute(
            "INSERT INTO organization_memberships "
            "(membership_id, organization_id, user_id, role, active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                "native-check-second-membership",
                "native-check-second-org",
                "native-check-second-therapist",
                "therapist",
            ),
        )


def _seed_verified_recording(database_url: URL, assessment_id: str) -> str:
    """Seed verified metadata without placing media bytes in the native check."""

    recording_id = f"native-check-recording-{uuid4().hex[:12]}"
    checksum = "sha256:" + ("1" * 64)
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        connection.execute(
            "SELECT set_config('app.current_user_id', %s, true)",
            ("native-check-therapist",),
        )
        connection.execute(
            "INSERT INTO recordings "
            "(recording_id, organization_id, assessment_id, protocol_version_key, activity_key, "
            "declared_content_type, declared_size_bytes, declared_checksum, object_key, upload_state, "
            "expires_at, verified_content_type, verified_size_bytes, verified_checksum, verified_at, "
            "version, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'verified', "
            "CURRENT_TIMESTAMP + INTERVAL '1 hour', %s, %s, %s, CURRENT_TIMESTAMP, 2, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                recording_id,
                "native-check-org",
                assessment_id,
                "thai_guided_language_sample:v0",
                "free_play",
                "audio/wav",
                128,
                checksum,
                f"capture/{recording_id}",
                "audio/wav",
                128,
                checksum,
            ),
        )
    return recording_id


def _withdraw_probe_consent(database_url: URL, assessment_id: str) -> None:
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        result = connection.execute(
            "UPDATE consent_records "
            "SET status = 'withdrawn', withdrawn_at = CURRENT_TIMESTAMP, "
            "version = version + 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE organization_id = %s "
            "AND child_id = (SELECT child_id FROM assessments WHERE assessment_id = %s) "
            "AND purpose = 'clinical_assessment' AND status = 'active'",
            ("native-check-org", assessment_id),
        )
        if result.rowcount != 1:
            raise RuntimeError("Native consent denial probe could not withdraw the synthetic consent.")


def _api_environment(database_url: URL) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "LINGUALENS_ASSESSMENT_DATABASE_URL": database_url.render_as_string(hide_password=False),
            "LINGUALENS_REPOSITORY_MODE": "json",
            "LINGUALENS_MOCK_MODE": "true",
            "LINGUALENS_AUTH_MODE": "mock",
            "LINGUALENS_RUN_MIGRATIONS_ON_STARTUP": "false",
            "LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP": "false",
            "LINGUALENS_STORAGE_MODE": "metadata_only",
            "PYTHONPATH": os.pathsep.join(
                [str(API_ROOT), str(ROOT / "src"), environment.get("PYTHONPATH", "")]
            ),
        }
    )
    return environment


def _worker_environment(database_url: URL, organization_id: str) -> dict[str, str]:
    environment = _api_environment(database_url)
    environment["LINGUALENS_CAPTURE_WORKER_ORGANIZATION_IDS"] = organization_id
    return environment


def _request_headers(
    *,
    user_id: str = "native-check-therapist",
    role: str = "therapist",
    organization_id: str = "native-check-org",
) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Mock-User-Id": user_id,
        "X-Mock-Role": role,
        "X-Organization-Id": organization_id,
        "X-Request-Id": "0123456789abcdef0123456789abcdef",
    }


def _request_json(
    port: int,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = _request_headers()
    if headers is not None:
        request_headers.update(headers)
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=body,
        headers=request_headers,
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise NativeHTTPError(error.code, body) from error


def _expect_denied(
    port: int,
    path: str,
    *,
    status_code: int,
    expected_code: str | None = None,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    try:
        _request_json(
            port,
            path,
            method=method,
            payload=payload,
            headers=headers,
        )
    except NativeHTTPError as error:
        if error.status_code != status_code:
            raise RuntimeError(
                f"Expected HTTP {status_code} for {path}, got {error.status_code}: {error.body[:300]}"
            ) from error
        if expected_code is not None and expected_code not in error.body:
            raise RuntimeError(
                f"Expected error code {expected_code} for {path}, got {error.body[:300]}"
            ) from error
        return
    raise RuntimeError(f"Expected denied request for {path}, but it succeeded.")


def _start_api(database_url: URL, port: int):
    log_file = tempfile.TemporaryFile(mode="w+b")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=_api_environment(database_url),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process, log_file


def _api_logs(log_file) -> str:
    log_file.seek(0)
    return log_file.read().decode("utf-8", errors="replace")


def _wait_for_api(process, log_file, port: int, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Native FastAPI process exited with code {process.returncode}.\n{_api_logs(log_file)}"
            )
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (NativeHTTPError, URLError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError(f"Native FastAPI process did not become healthy.\n{_api_logs(log_file)}")


def _prepare_transcript_state(database_url: URL, assessment_id: str) -> None:
    """Move synthetic capture data to the review queue before transcript creation."""

    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        connection.execute(
            "SELECT set_config('app.current_user_id', %s, true)",
            ("native-check-therapist",),
        )
        result = connection.execute(
            "UPDATE assessments "
            "SET state = %s, version = version + 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE organization_id = %s AND assessment_id = %s",
            ("review_required", "native-check-org", assessment_id),
        )
        if result.rowcount != 1:
            raise RuntimeError("Native v2 synthetic assessment was not found.")


def _set_probe_care_team_role(database_url: URL, assessment_id: str, role: str) -> None:
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        connection.execute(
            "SELECT set_config('app.current_organization_id', %s, true)",
            ("native-check-org",),
        )
        connection.execute(
            "SELECT set_config('app.current_user_id', %s, true)",
            ("native-check-therapist",),
        )
        result = connection.execute(
            "UPDATE care_team_assignments "
            "SET role = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE organization_id = %s "
            "AND child_id = (SELECT child_id FROM assessments WHERE assessment_id = %s) "
            "AND user_id = %s AND active = true",
            (role, "native-check-org", assessment_id, "native-check-therapist"),
        )
        if result.rowcount != 1:
            raise RuntimeError("Native care-team role probe could not update the synthetic assignment.")


def _probe_v2(port: int, database_url: URL) -> str:
    status_code, child = _request_json(
        port,
        "/api/v2/children",
        method="POST",
        payload={
            "display_code": "NATIVE-CHECK-001",
            "birth_year": 2021,
            "birth_month": 6,
            "language_context": {"primary": "th", "additional": []},
        },
    )
    if status_code != 201 or not isinstance(child, dict):
        raise RuntimeError(f"Native v2 child probe returned HTTP {status_code}.")
    child_id = child["id"]

    status_code, _ = _request_json(
        port,
        f"/api/v2/children/{child_id}/consents",
        method="POST",
        payload={
            "purpose": "clinical_assessment",
            "scope_version": "clinical-v1",
            "status": "active",
        },
    )
    if status_code != 201:
        raise RuntimeError(f"Native v2 consent probe returned HTTP {status_code}.")

    status_code, assessment = _request_json(
        port,
        f"/api/v2/children/{child_id}/assessments",
        method="POST",
        payload={
            "purpose": "initial",
            "assigned_clinician_id": "native-check-therapist",
        },
    )
    if status_code != 201 or not isinstance(assessment, dict):
        raise RuntimeError(f"Native v2 assessment probe returned HTTP {status_code}.")
    assessment_id = assessment["id"]

    status_code, _ = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/protocol-selection",
        method="POST",
        payload={},
    )
    if status_code != 200:
        raise RuntimeError(f"Native v2 protocol probe returned HTTP {status_code}.")
    status_code, _ = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/capture/start",
        method="POST",
        payload={},
    )
    if status_code != 200:
        raise RuntimeError(f"Native v2 capture probe returned HTTP {status_code}.")
    _prepare_transcript_state(database_url, assessment_id)
    status_code, transcript = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript-revisions",
        method="POST",
        payload={
            "source": "manual",
            "content": "@UTF8\\n@Begin\\n*CHI:\\thello .\\n@End\\n",
            "expected_revision": None,
            "expected_version": None,
        },
    )
    if status_code != 201 or not isinstance(transcript, dict):
        raise RuntimeError(f"Native v2 transcript creation returned HTTP {status_code}.")
    transcript_id = transcript["id"]
    _expect_denied(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript-segment-sets",
        status_code=409,
        expected_code="transcript_not_reviewable",
        method="POST",
        payload={
            "transcript_revision_id": transcript_id,
            "source": "manual",
            "segments": [
                {
                    "ordinal": 1,
                    "start_ms": 0,
                    "end_ms": 900,
                    "speaker_role": "child",
                    "text": "draft .",
                    "confidence": 0.9,
                    "uncertainty_reason": "none",
                }
            ],
        },
    )
    status_code, attested = _request_json(
        port,
        f"/api/v2/transcript-revisions/{transcript_id}/attest",
        method="POST",
        payload={"expected_version": transcript["version"]},
    )
    if status_code != 200 or not isinstance(attested, dict) or attested["review_state"] != "attested":
        raise RuntimeError(f"Native v2 transcript attestation returned HTTP {status_code}.")
    return assessment_id


def _probe_segment_workflow(
    port: int,
    database_url: URL,
    assessment_id: str,
    recording_id: str,
) -> dict[str, str]:
    """Exercise immutable segment revisions, bounded replay and evidence provenance inputs."""

    status_code, transcript = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript",
    )
    if status_code != 200 or not isinstance(transcript, dict):
        raise RuntimeError(f"Native transcript read returned HTTP {status_code}.")

    first_segments = [
        {
            "ordinal": 1,
            "start_ms": 0,
            "end_ms": 1200,
            "speaker_role": "child",
            "text": "red car .",
            "confidence": 0.98,
            "uncertainty_reason": "none",
        },
        {
            "ordinal": 2,
            "start_ms": 1200,
            "end_ms": 2200,
            "speaker_role": "unknown",
            "text": "red .",
            "confidence": 0.42,
            "uncertainty_reason": "speaker_uncertain",
        },
    ]
    status_code, draft_v1 = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript-segment-sets",
        method="POST",
        payload={
            "transcript_revision_id": transcript["id"],
            "source": "manual",
            "segments": first_segments,
        },
    )
    if (
        status_code != 201
        or not isinstance(draft_v1, dict)
        or draft_v1.get("revision") != 1
        or draft_v1.get("review_state") != "draft"
    ):
        raise RuntimeError(f"Native segment draft v1 returned HTTP {status_code}.")

    _set_probe_care_team_role(database_url, assessment_id, "observer")
    try:
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-segment-sets",
            status_code=403,
            expected_code="segment_role_not_permitted",
            method="POST",
            payload={
                "transcript_revision_id": transcript["id"],
                "source": "manual",
                "segments": first_segments,
            },
        )
    finally:
        _set_probe_care_team_role(database_url, assessment_id, "assigned_clinician")

    status_code, attested_v1 = _request_json(
        port,
        f"/api/v2/transcript-segment-sets/{draft_v1['id']}/attest",
        method="POST",
        payload={"expected_version": draft_v1["version"]},
    )
    if (
        status_code != 200
        or not isinstance(attested_v1, dict)
        or attested_v1.get("review_state") != "attested"
    ):
        raise RuntimeError(f"Native segment attestation v1 returned HTTP {status_code}.")

    status_code, replay = _request_json(
        port,
        f"/api/v2/transcript-segments/{attested_v1['segments'][0]['id']}/audio-replay-grant",
        method="POST",
    )
    if (
        status_code != 200
        or not isinstance(replay, dict)
        or replay.get("available") is not False
        or replay.get("start_ms") != 0
        or replay.get("end_ms") != 1200
        or replay.get("url") is not None
    ):
        raise RuntimeError("Native replay grant did not fail closed for unavailable audio.")

    edited_segments = [
        {**first_segments[0]},
        {
            **first_segments[1],
            "speaker_role": "child",
            "uncertainty_reason": "none",
        },
    ]
    status_code, draft_v2 = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript-segment-sets",
        method="POST",
        payload={
            "transcript_revision_id": transcript["id"],
            "source": "manual",
            "recording_id": recording_id,
            "expected_revision": draft_v1["revision"],
            "expected_version": attested_v1["version"],
            "segments": edited_segments,
        },
    )
    if (
        status_code != 201
        or not isinstance(draft_v2, dict)
        or draft_v2.get("revision") != 2
        or draft_v2.get("recording_id") != recording_id
        or draft_v2.get("segments", [None, None])[1]["uncertainty_reason"] != "none"
    ):
        raise RuntimeError(f"Native segment edit v2 returned HTTP {status_code}.")

    status_code, attested_v2 = _request_json(
        port,
        f"/api/v2/transcript-segment-sets/{draft_v2['id']}/attest",
        method="POST",
        payload={"expected_version": draft_v2["version"]},
    )
    if (
        status_code != 200
        or not isinstance(attested_v2, dict)
        or attested_v2.get("review_state") != "attested"
    ):
        raise RuntimeError(f"Native segment attestation v2 returned HTTP {status_code}.")

    status_code, current = _request_json(
        port,
        f"/api/v2/assessments/{assessment_id}/transcript-segment-set",
    )
    if (
        status_code != 200
        or not isinstance(current, dict)
        or current.get("id") != draft_v2["id"]
        or current.get("review_state") != "attested"
    ):
        raise RuntimeError(f"Native current segment set returned HTTP {status_code}.")
    return {
        "id": str(current["id"]),
        "sha256": str(current["segments_sha256"]),
        "transcript_id": str(transcript["id"]),
    }


def _start_worker(database_url: URL, organization_id: str):
    log_file = tempfile.TemporaryFile(mode="w+b")
    process = subprocess.Popen(
        [sys.executable, "-m", "app.assessment_v2.worker_runtime"],
        cwd=ROOT,
        env=_worker_environment(database_url, organization_id),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process, log_file


def _wait_for_evidence_success(port: int, processing_run_id: str, timeout_seconds: int = 60) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            status_code, payload = _request_json(
                port,
                f"/api/v2/processing-runs/{processing_run_id}",
            )
            if status_code != 200 or not isinstance(payload, dict):
                raise RuntimeError(f"Native processing status returned HTTP {status_code}.")
            state = payload.get("state")
            if state == "succeeded":
                return payload
            if state in {"failed", "cancelled"}:
                raise RuntimeError(f"Native evidence worker ended in state {state}.")
        except (HTTPError, URLError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError("Native evidence worker did not finish within the timeout.")


def _stop_api(process, log_file) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    if log_file is not None:
        log_file.close()


def _run_rls(owner_url: URL) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "LINGUALENS_ASSESSMENT_TEST_DATABASE_URL": owner_url.render_as_string(hide_password=False),
            "LINGUALENS_ASSESSMENT_DATABASE_URL": owner_url.render_as_string(hide_password=False),
            "PYTHONPATH": os.pathsep.join(
                [str(API_ROOT), str(ROOT / "src"), environment.get("PYTHONPATH", "")]
            ),
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "assessment_postgres",
            "apps/api/tests/assessment_v2/test_postgres_rls.py",
            "apps/api/tests/assessment_v2/test_postgres_processing_leases.py",
            "-q",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Native PostgreSQL RLS verification failed.")


def _drop_database(admin_url: URL, database_name: str, role_name: str) -> None:
    with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database_name,),
        )
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
        )
        connection.execute(
            sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name))
        )


def main() -> int:
    admin_url = _admin_url()
    database_name = f"lingualens_assessment_v2_native_{uuid4().hex[:12]}"
    role_name = f"lingualens_native_{uuid4().hex[:12]}"
    role_password = uuid4().hex
    owner_url = admin_url.set(database=database_name)
    limited_url = owner_url.set(username=role_name, password=role_password)
    process = None
    log_file = None
    worker_process = None
    worker_log_file = None

    try:
        _create_database(admin_url, database_name)
        _migrate(owner_url)
        _configure_application_role(admin_url, database_name, role_name, role_password)
        _transfer_assessment_ownership(owner_url, role_name)
        _seed_probe_membership(limited_url)
        _seed_secondary_membership(owner_url)

        port = _free_port()
        process, log_file = _start_api(limited_url, port)
        _wait_for_api(process, log_file, port)
        assessment_id = _probe_v2(port, limited_url)
        migration_probe_run_id = _insert_migration_probe_processing_run(limited_url, assessment_id)
        preserved_processing_run_ids = _processing_run_ids(limited_url, "native-check-org")
        if migration_probe_run_id not in preserved_processing_run_ids:
            raise RuntimeError("Native migration probe did not create a capture processing run.")

        _stop_api(process, log_file)
        process = None
        log_file = None
        _downgrade(owner_url, "0006_evidence_profiles")
        _transfer_assessment_ownership(owner_url, role_name)
        _migrate(limited_url)
        if _processing_run_ids(limited_url, "native-check-org") != preserved_processing_run_ids:
            raise RuntimeError(
                "Native migration probe lost processing rows while upgrading as the RLS app role."
            )

        port = _free_port()
        process, log_file = _start_api(limited_url, port)
        _wait_for_api(process, log_file, port)

        recording_id = _seed_verified_recording(limited_url, assessment_id)
        segment_context = _probe_segment_workflow(port, limited_url, assessment_id, recording_id)

        status_code, queued = _request_json(
            port,
            f"/api/v2/assessments/{assessment_id}/evidence-runs",
            method="POST",
            payload={},
        )
        if status_code != 202 or not isinstance(queued, dict):
            raise RuntimeError(f"Native evidence enqueue returned HTTP {status_code}.")
        queued_run = queued.get("processing_run")
        if not isinstance(queued_run, dict) or queued_run.get("state") != "queued":
            raise RuntimeError("Native evidence enqueue did not return a queued processing run.")
        processing_run_id = queued_run["id"]

        worker_process, worker_log_file = _start_worker(limited_url, "native-check-org")
        succeeded = _wait_for_evidence_success(port, processing_run_id)
        if succeeded.get("result_available") is not True:
            raise RuntimeError("Native evidence processing succeeded without a result link.")

        status_code, evidence = _request_json(
            port,
            f"/api/v2/assessments/{assessment_id}/evidence",
        )
        if (
            status_code != 200
            or not isinstance(evidence, dict)
            or evidence.get("not_diagnostic") is not True
            or evidence.get("decision_support_only") is not True
            or evidence.get("segment_set_id") != segment_context["id"]
            or evidence.get("segment_set_sha256") != segment_context["sha256"]
        ):
            raise RuntimeError(
                f"Native evidence read returned HTTP {status_code}, unsafe profile, or missing segment provenance."
            )

        status_code, repeated = _request_json(
            port,
            f"/api/v2/assessments/{assessment_id}/evidence-runs",
            method="POST",
            payload={},
        )
        if (
            status_code != 202
            or not isinstance(repeated, dict)
            or not isinstance(repeated.get("processing_run"), dict)
            or repeated["processing_run"].get("id") != processing_run_id
        ):
            raise RuntimeError("Native evidence enqueue was not idempotent.")

        # second-tenant denial: an authenticated therapist from another tenant
        # must not learn whether this assessment has a current segment set.
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-segment-set",
            status_code=404,
            headers=_request_headers(
                user_id="native-check-second-therapist",
                organization_id="native-check-second-org",
            ),
        )
        # unassigned-role denial: a non-clinical role is rejected before data access.
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-segment-set",
            status_code=403,
            expected_code="forbidden",
            headers=_request_headers(role="observer"),
        )

        status_code, current_transcript = _request_json(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript",
        )
        if status_code != 200 or not isinstance(current_transcript, dict):
            raise RuntimeError(f"Native current transcript read returned HTTP {status_code}.")
        status_code, superseded = _request_json(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-revisions",
            method="POST",
            payload={
                "source": "manual",
                "content": "@UTF8\n@Begin\n*CHI:\tred .\n@End\n",
                "expected_revision": current_transcript["revision"],
                "expected_version": current_transcript["version"],
            },
        )
        if status_code != 201 or not isinstance(superseded, dict) or superseded.get("review_state") != "draft":
            raise RuntimeError(f"Native transcript supersession returned HTTP {status_code}.")
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-segment-set",
            status_code=404,
            expected_code="segment_set_not_found",
        )
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/evidence-runs",
            status_code=409,
            expected_code="transcript_not_reviewable",
            method="POST",
            payload={},
        )

        _withdraw_probe_consent(limited_url, assessment_id)
        # consent denial: revocation blocks the current segment read even for the assigned therapist.
        _expect_denied(
            port,
            f"/api/v2/assessments/{assessment_id}/transcript-segment-set",
            status_code=409,
            expected_code="consent_revoked",
        )

        _stop_api(worker_process, worker_log_file)
        worker_process = None
        worker_log_file = None
        _stop_api(process, log_file)
        process = None
        log_file = None

        _run_rls(owner_url)
        print(
            "assessment-v2 native runtime check passed "
            "(migrations=0012, segments=v2-attested, replay=bounded-unavailable, "
            "enqueue=202, worker=evidence_recorded, provenance=bound, idempotency=202, "
            "staleness=blocked, tenant=denied, consent=denied, role=denied, rls=passed, cleanup=passed)"
        )
        return 0
    except Exception:
        if log_file is not None:
            print(_api_logs(log_file), file=sys.stderr)
        if worker_log_file is not None:
            print(_api_logs(worker_log_file), file=sys.stderr)
        raise
    finally:
        _stop_api(worker_process, worker_log_file)
        _stop_api(process, log_file)
        _drop_database(admin_url, database_name, role_name)


if __name__ == "__main__":
    raise SystemExit(main())
