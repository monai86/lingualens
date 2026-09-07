"""Exercise the fresh v2 Compose database through the running API container."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "lingualens-assessment-v2-check"
API_PORT = 8002
DATABASE_PORT = 5434
COMPOSE = [
    "docker",
    "compose",
    "--project-name",
    PROJECT,
    "--file",
    "docker-compose.yml",
    "--file",
    "docker-compose.assessment-check.yml",
]


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*COMPOSE, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def _wait_for_postgres(timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = _run("ps", "--format", "json", "postgres", check=False)
        if "healthy" in (state.stdout + state.stderr).lower():
            return
        time.sleep(1)
    logs = _run("logs", "postgres", check=False)
    raise RuntimeError(f"Compose PostgreSQL did not become healthy.\n{logs.stdout}\n{logs.stderr}")


def _wait_for_api(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (HTTPError, URLError, OSError):
            pass
        time.sleep(1)
    logs = _run("logs", "api", check=False)
    raise RuntimeError(f"Compose API did not become healthy.\n{logs.stdout}\n{logs.stderr}")


def _assert_runtime_role() -> None:
    with psycopg.connect(
        "postgresql://lingualens_assessment_app:local-assessment-only"
        f"@127.0.0.1:{DATABASE_PORT}/lingualens_assessment_v2"
    ) as connection:
        current_user, is_superuser, bypasses_rls = connection.execute(
            "SELECT current_user, rolsuper, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
    if current_user != "lingualens_assessment_app" or is_superuser or bypasses_rls:
        raise RuntimeError("Compose assessment runtime role must not bypass PostgreSQL RLS.")


def _seed_probe_membership() -> None:
    """Provision only the synthetic membership needed by the mock API probe."""

    with psycopg.connect(
        "postgresql://lingualens_assessment_app:local-assessment-only"
        f"@127.0.0.1:{DATABASE_PORT}/lingualens_assessment_v2"
    ) as connection:
        connection.execute(
            "INSERT INTO organizations (organization_id, display_label, active) "
            "VALUES (%s, %s, true) ON CONFLICT (organization_id) DO NOTHING",
            ("compose-check-org", "Synthetic Compose Check Organization"),
        )
        connection.execute(
            "INSERT INTO user_profiles (user_id, display_label) VALUES (%s, %s) "
            "ON CONFLICT (user_id) DO NOTHING",
            ("compose-check-therapist", "Synthetic Compose Check Therapist"),
        )
        connection.execute(
            "INSERT INTO organization_memberships "
            "(membership_id, organization_id, user_id, role, active) "
            "VALUES (%s, %s, %s, %s, true) ON CONFLICT (organization_id, user_id) DO NOTHING",
            (
                "compose-check-membership",
                "compose-check-org",
                "compose-check-therapist",
                "therapist",
            ),
        )


def _probe_v2() -> None:
    request = Request(
        f"http://127.0.0.1:{API_PORT}/api/v2/children",
        method="POST",
        data=json.dumps(
            {
                "display_code": "COMPOSE-CHECK-001",
                "birth_year": 2021,
                "birth_month": 6,
                "language_context": {"primary": "th", "additional": []},
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Mock-User-Id": "compose-check-therapist",
            "X-Mock-Role": "therapist",
            "X-Organization-Id": "compose-check-org",
            "X-Request-Id": "0123456789abcdef0123456789abcdef",
        },
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise RuntimeError(f"Compose v2 API probe returned HTTP {response.status}.")
        payload = json.loads(response.read().decode())
    if payload.get("display_code") != "COMPOSE-CHECK-001":
        raise RuntimeError(f"Compose v2 API probe returned an unexpected response: {payload!r}")


def _start_host_api() -> subprocess.Popen[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(ROOT / "apps" / "api"),
            "LINGUALENS_MOCK_MODE": "true",
            "LINGUALENS_ASSESSMENT_DATABASE_URL": (
                "postgresql+psycopg://lingualens_assessment_app:local-assessment-only"
                f"@127.0.0.1:{DATABASE_PORT}/lingualens_assessment_v2"
            ),
            "LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP": "true",
        }
    )
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=ROOT / "apps" / "api",
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> int:
    api_process: subprocess.Popen[str] | None = None
    try:
        _run("down", "--volumes", "--remove-orphans", check=False)
        _run("up", "-d", "--force-recreate", "postgres")
        _wait_for_postgres()
        _assert_runtime_role()
        api_process = _start_host_api()
        _wait_for_api()
        _seed_probe_membership()
        _probe_v2()
        print("assessment-v2 Compose runtime check passed")
        return 0
    finally:
        if api_process is not None:
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()
                api_process.wait()
        _run("down", "--volumes", "--remove-orphans", check=False)


if __name__ == "__main__":
    raise SystemExit(main())
