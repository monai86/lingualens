"""Exercise assessment v2 against a fresh native PostgreSQL database and API process."""

from __future__ import annotations

import os
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
    "assessment_protocol_selections",
    "recordings",
    "processing_runs",
    "recording_quality_results",
    "transcript_revisions",
    "evidence_runs",
    "evidence_feature_values",
    "evidence_domain_profiles",
)


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
        for table_name in TABLES:
            connection.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {} TO {}")
                .format(sql.Identifier(table_name), sql.Identifier(role_name))
            )
        connection.execute(
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}")
            .format(sql.Identifier(role_name))
        )


def _migrate(owner_url: URL) -> None:
    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = owner_url.render_as_string(hide_password=False)
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(1, str(ROOT))

    from app.assessment_v2.db.migrations_runner import upgrade_assessment_database
    from app.core.config import get_settings

    get_settings.cache_clear()
    upgrade_assessment_database()


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
        except (HTTPError, URLError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError(f"Native FastAPI process did not become healthy.\n{_api_logs(log_file)}")


def _probe_v2(port: int) -> None:
    request = Request(
        f"http://127.0.0.1:{port}/api/v2/children",
        method="POST",
        data=(
            '{"display_code":"NATIVE-CHECK-001","birth_year":2021,'
            '"birth_month":6,"language_context":{"primary":"th","additional":[]}}'
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Mock-User-Id": "native-check-therapist",
            "X-Mock-Role": "therapist",
            "X-Organization-Id": "native-check-org",
            "X-Request-Id": "0123456789abcdef0123456789abcdef",
        },
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise RuntimeError(f"Native v2 API probe returned HTTP {response.status}.")


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

    try:
        _create_database(admin_url, database_name)
        _migrate(owner_url)
        _configure_application_role(admin_url, database_name, role_name, role_password)
        _seed_probe_membership(limited_url)

        port = _free_port()
        process, log_file = _start_api(limited_url, port)
        _wait_for_api(process, log_file, port)
        _probe_v2(port)
        _stop_api(process, log_file)
        process = None
        log_file = None

        _run_rls(owner_url)
        print("assessment-v2 native runtime check passed")
        return 0
    finally:
        _stop_api(process, log_file)
        _drop_database(admin_url, database_name, role_name)


if __name__ == "__main__":
    raise SystemExit(main())
