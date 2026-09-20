"""Recreate and exercise only the explicitly named assessment-v2 test database."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


ROOT = Path(__file__).resolve().parents[1]
TARGET_DATABASE = "lingualens_assessment_v2_test"
DEFAULT_TEST_URL = (
    "postgresql+psycopg://therapist:therapist@localhost:5432/lingualens_assessment_v2_test"
)
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


def _database_url() -> URL:
    value = os.getenv("LINGUALENS_ASSESSMENT_TEST_DATABASE_URL", DEFAULT_TEST_URL)
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("Assessment PostgreSQL check requires a PostgreSQL URL.")
    if parsed.database != TARGET_DATABASE:
        raise RuntimeError(
            f"Refusing to recreate database {parsed.database!r}; expected {TARGET_DATABASE!r}."
        )
    if parsed.host not in ALLOWED_HOSTS:
        raise RuntimeError("Assessment PostgreSQL check only permits an explicit local test host.")
    return parsed


def _compose_postgres_is_healthy() -> bool:
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json", "postgres"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        payload = records[0] if len(records) == 1 else records
    records = payload if isinstance(payload, list) else [payload]
    for record in records:
        if not isinstance(record, dict):
            continue
        health = str(record.get("Health") or record.get("health") or "").lower()
        state = str(record.get("State") or record.get("state") or "").lower()
        if health == "healthy" or (state == "running" and not health):
            return True
    return False


def _wait_for_postgres(timeout_seconds: int = 60) -> None:
    subprocess.run(["docker", "compose", "up", "-d", "postgres"], cwd=ROOT, check=True)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _compose_postgres_is_healthy():
            return
        time.sleep(1)
    raise RuntimeError("Compose PostgreSQL did not become healthy before the timeout.")


def _recreate_target_database(database_url: URL) -> None:
    admin_url = database_url.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database AND pid <> pg_backend_pid()"
                ),
                {"database": TARGET_DATABASE},
            )
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {TARGET_DATABASE}")
            connection.exec_driver_sql(f"CREATE DATABASE {TARGET_DATABASE}")
    finally:
        engine.dispose()


def main() -> int:
    database_url = _database_url()
    _wait_for_postgres()
    _recreate_target_database(database_url)

    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = database_url.render_as_string(hide_password=False)
    os.environ["LINGUALENS_ASSESSMENT_TEST_DATABASE_URL"] = database_url.render_as_string(hide_password=False)
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "apps" / "api"), str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]
    )
    from app.core.config import get_settings
    from app.assessment_v2.db.migrations_runner import upgrade_assessment_database

    get_settings.cache_clear()
    upgrade_assessment_database()
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
        env=os.environ.copy(),
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
