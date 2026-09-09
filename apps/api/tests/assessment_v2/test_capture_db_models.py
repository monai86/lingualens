from __future__ import annotations

import inspect
from importlib import import_module
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, UniqueConstraint

from app.assessment_v2.db import models as _models  # noqa: F401  # register mapped tables
from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.domain.models import RecordingQualityStatus
from app.assessment_v2.protocols import PROTOCOL_CATALOG


CAPTURE_TABLES = {
    "protocol_versions",
    "protocol_activities",
    "assessment_protocol_selections",
    "recordings",
    "processing_runs",
    "recording_quality_results",
}


def _unique_columns(table_name: str) -> set[tuple[str, ...]]:
    table = AssessmentBase.metadata.tables[table_name]
    return {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_key_columns(table_name: str) -> set[tuple[str, ...]]:
    table = AssessmentBase.metadata.tables[table_name]
    return {
        tuple(constraint.column_keys)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_capture_metadata_defines_exact_tables_and_essential_columns() -> None:
    capture_tables = set(AssessmentBase.metadata.tables) - {
        "organizations",
        "user_profiles",
        "organization_memberships",
        "children",
        "care_team_assignments",
        "consent_records",
        "assessments",
        "audit_events",
        "transcript_revisions",
        "evidence_runs",
        "evidence_feature_values",
        "evidence_domain_profiles",
    }

    assert capture_tables == CAPTURE_TABLES
    assert set(AssessmentBase.metadata.tables["protocol_versions"].columns.keys()) == {
        "protocol_version_key",
        "primary_language",
        "minimum_age_months",
        "maximum_age_months",
        "supported_purposes",
        "created_at",
    }
    assert set(AssessmentBase.metadata.tables["protocol_activities"].columns.keys()) == {
        "protocol_version_key",
        "activity_key",
        "required",
        "target_duration_seconds",
        "minimum_duration_seconds",
        "sort_order",
        "created_at",
    }
    assert set(AssessmentBase.metadata.tables["assessment_protocol_selections"].columns.keys()) == {
        "assessment_protocol_selection_id",
        "organization_id",
        "assessment_id",
        "protocol_version_key",
        "selected_by_user_id",
        "selected_at",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(AssessmentBase.metadata.tables["recordings"].columns.keys()) == {
        "recording_id",
        "organization_id",
        "assessment_id",
        "protocol_version_key",
        "activity_key",
        "declared_content_type",
        "declared_size_bytes",
        "declared_checksum",
        "object_key",
        "upload_state",
        "expires_at",
        "verified_content_type",
        "verified_size_bytes",
        "verified_checksum",
        "verified_at",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(AssessmentBase.metadata.tables["processing_runs"].columns.keys()) == {
        "processing_run_id",
        "organization_id",
        "recording_id",
        "assessment_id",
        "transcript_revision_id",
        "evidence_run_id",
        "stage",
        "state",
        "idempotency_key",
        "attempt_count",
        "max_attempts",
        "available_at",
        "error_code",
        "lease_token",
        "lease_expires_at",
        "cancel_requested_at",
        "completed_at",
        "pipeline_version",
        "feature_schema_version",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(AssessmentBase.metadata.tables["recording_quality_results"].columns.keys()) == {
        "recording_quality_result_id",
        "organization_id",
        "recording_id",
        "status",
        "measured_duration_seconds",
        "measured_loudness_db",
        "measured_silence_ratio",
        "measured_decodability",
        "unavailable_checks_json",
        "provenance",
        "evaluated_at",
        "version",
        "created_at",
        "updated_at",
    }


def test_capture_constraint_names_fit_postgresql_identifier_limit() -> None:
    for table in AssessmentBase.metadata.tables.values():
        for constraint in table.constraints:
            if constraint.name is not None:
                assert len(constraint.name) <= 63, (table.name, constraint.name)


def test_capture_metadata_has_uniqueness_tenant_foreign_keys_and_mutable_versions() -> None:
    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "assessment_id", "protocol_version_key"),
    }.issubset(_unique_columns("assessment_protocol_selections"))
    assert {
        ("organization_id", "recording_id"),
        ("object_key",),
    }.issubset(_unique_columns("recordings"))
    assert ("organization_id", "idempotency_key") in _unique_columns("processing_runs")
    assert ("organization_id", "recording_id") in _unique_columns("recording_quality_results")

    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "selected_by_user_id"),
    }.issubset(_foreign_key_columns("assessment_protocol_selections"))
    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "assessment_id", "protocol_version_key"),
        ("protocol_version_key", "activity_key"),
    }.issubset(_foreign_key_columns("recordings"))
    assert ("organization_id", "recording_id") in _foreign_key_columns("processing_runs")
    assert ("organization_id", "recording_id") in _foreign_key_columns("recording_quality_results")

    for table_name in (
        "assessment_protocol_selections",
        "recordings",
        "recording_quality_results",
    ):
        table = AssessmentBase.metadata.tables[table_name]
        assert isinstance(table.c.created_at.type, DateTime)
        assert table.c.created_at.type.timezone is True
        assert any(
            isinstance(constraint, CheckConstraint) and "version >= 1" in str(constraint.sqltext)
            for constraint in table.constraints
        )


def test_recording_quality_status_contract_is_exact_and_defaults_to_usable() -> None:
    quality = AssessmentBase.metadata.tables["recording_quality_results"]

    assert tuple(status.value for status in RecordingQualityStatus) == (
        "usable",
        "needs_additional_sample",
        "unavailable",
        "failed",
    )
    assert quality.c.status.default.arg == "usable"
    assert quality.c.status.server_default.arg.text == "'usable'"
    assert {
        str(constraint.sqltext)
        for constraint in quality.constraints
        if isinstance(constraint, CheckConstraint)
    } >= {
        "status IN ('usable', 'needs_additional_sample', 'unavailable', 'failed')"
    }


def test_capture_migration_seeds_catalog_and_reverses_to_0002(monkeypatch) -> None:
    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database, upgrade_assessment_database
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-capture-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-capture.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database("0002_assessment_tenant_integrity")
            with sqlite3.connect(database_path) as connection:
                tables_at_0002 = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
            assert CAPTURE_TABLES.isdisjoint(tables_at_0002)

            upgrade_assessment_database()
            with sqlite3.connect(database_path) as connection:
                tables_at_head = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                protocol_rows = connection.execute(
                    "select protocol_version_key, primary_language, minimum_age_months, "
                    "maximum_age_months, supported_purposes from protocol_versions"
                ).fetchall()
                activity_rows = connection.execute(
                    "select activity_key, required, target_duration_seconds, minimum_duration_seconds "
                    "from protocol_activities order by sort_order"
                ).fetchall()
                quality_columns = connection.execute(
                    "pragma table_info(recording_quality_results)"
                ).fetchall()
                quality_ddl = connection.execute(
                    "select sql from sqlite_master where type = 'table' and name = 'recording_quality_results'"
                ).fetchone()[0]
                revision = connection.execute("select version_num from alembic_version").fetchone()

            assert CAPTURE_TABLES.issubset(tables_at_head)
            assert revision == ("0007_durable_evidence_jobs",)

            with sqlite3.connect(database_path) as connection:
                for statement in (
                    "update protocol_versions set primary_language = 'en' "
                    "where protocol_version_key = 'thai_guided_language_sample:v0'",
                    "delete from protocol_versions "
                    "where protocol_version_key = 'thai_guided_language_sample:v0'",
                    "update protocol_activities set required = 0 "
                    "where protocol_version_key = 'thai_guided_language_sample:v0' "
                    "and activity_key = 'free_play'",
                    "delete from protocol_activities "
                    "where protocol_version_key = 'thai_guided_language_sample:v0' "
                    "and activity_key = 'free_play'",
                ):
                    with pytest.raises(sqlite3.IntegrityError):
                        connection.execute(statement)
                    connection.rollback()

            assert protocol_rows == [
                (
                    "thai_guided_language_sample:v0",
                    "th",
                    18,
                    72,
                    "initial,developmental_follow_up,post_intervention_follow_up,additional_evidence",
                )
            ]
            assert activity_rows == [
                ("free_play", 1, 180, 120),
                ("shared_book", 0, 120, 60),
                ("turn_taking", 0, 120, 60),
            ]
            quality_status_default = next(row[4] for row in quality_columns if row[1] == "status")
            assert quality_status_default in {"'usable'", "usable"}
            normalized_quality_ddl = " ".join(quality_ddl.split())
            assert "status IN ('usable', 'needs_additional_sample', 'unavailable', 'failed')" in normalized_quality_ddl
            assert "'pending'" not in normalized_quality_ddl
            assert "'available'" not in normalized_quality_ddl

            # RLS policies are PostgreSQL-only and intentionally guarded by the migration dialect check.
            downgrade_assessment_database("0002_assessment_tenant_integrity")
            with sqlite3.connect(database_path) as connection:
                tables_after_downgrade = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                trigger_names = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'trigger'"
                    )
                }
            assert CAPTURE_TABLES.isdisjoint(tables_after_downgrade)
            assert "assessments" in tables_after_downgrade
            assert not {
                "protocol_versions_immutable_update",
                "protocol_versions_immutable_delete",
                "protocol_activities_immutable_update",
                "protocol_activities_immutable_delete",
            }.intersection(trigger_names)
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()


def test_fresh_sqlite_migration_catalog_matches_python_protocol_catalog(monkeypatch) -> None:
    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database, upgrade_assessment_database
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-catalog-parity-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-catalog.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database()
            with sqlite3.connect(database_path) as connection:
                version_rows = connection.execute(
                    "select protocol_version_key, primary_language, minimum_age_months, "
                    "maximum_age_months, supported_purposes from protocol_versions"
                ).fetchall()
                activity_rows = connection.execute(
                    "select protocol_version_key, activity_key, required, "
                    "target_duration_seconds, minimum_duration_seconds, sort_order "
                    "from protocol_activities order by protocol_version_key, sort_order"
                ).fetchall()

            expected_versions = [
                (
                    protocol.protocol_version_key,
                    protocol.primary_language,
                    protocol.minimum_age_months,
                    protocol.maximum_age_months,
                    ",".join(purpose.value for purpose in protocol.supported_purposes),
                )
                for protocol in sorted(PROTOCOL_CATALOG, key=lambda item: item.protocol_version_key)
            ]
            expected_activities = [
                (
                    protocol.protocol_version_key,
                    activity.activity_key,
                    int(activity.required),
                    activity.target_duration_seconds,
                    activity.minimum_duration_seconds,
                    sort_order,
                )
                for protocol in sorted(PROTOCOL_CATALOG, key=lambda item: item.protocol_version_key)
                for sort_order, activity in enumerate(protocol.activities, start=1)
            ]

            assert version_rows == expected_versions
            assert activity_rows == expected_activities
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()


def test_postgres_catalog_downgrade_contract_removes_immutability_guards() -> None:
    """Keep the PostgreSQL trigger/function cleanup in the migration contract."""

    migration = import_module(
        "app.assessment_v2.db.migrations.versions.0003_capture_protocols_recordings"
    )
    cleanup_source = inspect.getsource(migration._remove_catalog_immutability_guards)
    downgrade_source = inspect.getsource(migration.downgrade)

    assert "DROP TRIGGER IF EXISTS protocol_versions_immutable_mutation ON protocol_versions" in cleanup_source
    assert "DROP TRIGGER IF EXISTS protocol_activities_immutable_mutation ON protocol_activities" in cleanup_source
    assert "DROP FUNCTION IF EXISTS assessment_v2_reject_catalog_mutation()" in cleanup_source
    assert "_remove_catalog_immutability_guards()" in downgrade_source
