"""Smoke-check the isolated assessment v2 migration history on fresh SQLite."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

EXPECTED_TABLES = {
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
}
HEAD_REVISION = "0003_capture_protocols_recordings"
PROTOCOL_VERSION_KEY = "thai_guided_language_sample:v0"
EXPECTED_PURPOSES = "initial,developmental_follow_up,post_intervention_follow_up,additional_evidence"


def _clear_settings_cache() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()


def _tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("select name from sqlite_master where type = 'table'").fetchall()
    return {row[0] for row in rows}


def _columns(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _revision(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("select version_num from alembic_version").fetchone()
    if row is None:
        raise RuntimeError("assessment-v2 migration smoke did not record a revision")
    return str(row[0])


def _query(database_path: Path, statement: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(statement).fetchall()


def run_smoke(database_path: Path) -> None:
    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database, upgrade_assessment_database

    previous = os.environ.get("LINGUALENS_ASSESSMENT_DATABASE_URL")
    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = f"sqlite:///{database_path}"
    try:
        _clear_settings_cache()
        upgrade_assessment_database()
        tables = _tables(database_path)
        if not EXPECTED_TABLES.issubset(tables):
            raise RuntimeError(f"assessment-v2 migration smoke missing tables: {sorted(EXPECTED_TABLES - tables)}")
        if _revision(database_path) != HEAD_REVISION:
            raise RuntimeError("assessment-v2 migration smoke reached an unexpected revision")
        if "organization_id" not in _columns(database_path, "assessments"):
            raise RuntimeError("assessment-v2 migration smoke missing tenant column")
        protocol_rows = _query(
            database_path,
            "select protocol_version_key, primary_language, minimum_age_months, "
            "maximum_age_months, supported_purposes from protocol_versions",
        )
        if protocol_rows != [
            (
                PROTOCOL_VERSION_KEY,
                "th",
                18,
                72,
                EXPECTED_PURPOSES,
            )
        ]:
            raise RuntimeError("assessment-v2 migration smoke seeded an unexpected protocol catalog")
        activity_rows = _query(
            database_path,
            "select activity_key, required, target_duration_seconds, minimum_duration_seconds "
            "from protocol_activities order by sort_order",
        )
        if activity_rows != [
            ("free_play", 1, 180, 120),
            ("shared_book", 0, 120, 60),
            ("turn_taking", 0, 120, 60),
        ]:
            raise RuntimeError("assessment-v2 migration smoke seeded unexpected protocol activities")
        downgrade_assessment_database()
        remaining = _tables(database_path) - {"alembic_version"}
        if remaining:
            raise RuntimeError(f"assessment-v2 migration smoke left tables after downgrade: {sorted(remaining)}")
    finally:
        if previous is None:
            os.environ.pop("LINGUALENS_ASSESSMENT_DATABASE_URL", None)
        else:
            os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = previous
        _clear_settings_cache()


def main() -> int:
    with TemporaryDirectory(prefix="lingualens-assessment-v2-migration-") as temp_dir:
        run_smoke(Path(temp_dir) / "assessment-v2.db")
    print("assessment-v2 migration smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
