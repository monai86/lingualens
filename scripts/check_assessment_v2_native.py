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


def _request_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Mock-User-Id": "native-check-therapist",
        "X-Mock-Role": "therapist",
        "X-Organization-Id": "native-check-org",
        "X-Request-Id": "0123456789abcdef0123456789abcdef",
    }


def _request_json(
    port: int,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=body,
        headers=_request_headers(),
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise NativeHTTPError(error.code, body) from error


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
    status_code, attested = _request_json(
        port,
        f"/api/v2/transcript-revisions/{transcript_id}/attest",
        method="POST",
        payload={"expected_version": transcript["version"]},
    )
    if status_code != 200 or not isinstance(attested, dict) or attested["review_state"] != "attested":
        raise RuntimeError(f"Native v2 transcript attestation returned HTTP {status_code}.")
    return assessment_id


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
        ):
            raise RuntimeError(f"Native evidence read returned HTTP {status_code} or an unsafe profile.")

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

        _stop_api(worker_process, worker_log_file)
        worker_process = None
        worker_log_file = None
        _stop_api(process, log_file)
        process = None
        log_file = None

        _run_rls(owner_url)
        print(
            "assessment-v2 native runtime check passed "
            "(migrations=0007, enqueue=202, worker=evidence_recorded, "
            "evidence=200, idempotency=202, rls=passed, cleanup=passed)"
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
