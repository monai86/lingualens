from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.assessment_v2.db import models as _models  # noqa: F401
from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DomainProfileStatus,
    EvidenceSource,
    EvidenceState,
)


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


def test_evidence_tables_store_tenant_scoped_runs_features_and_domains() -> None:
    assert set(AssessmentBase.metadata.tables) >= {
        "evidence_runs",
        "evidence_feature_values",
        "evidence_domain_profiles",
    }
    assert set(AssessmentBase.metadata.tables["evidence_runs"].columns.keys()) == {
        "evidence_run_id",
        "organization_id",
        "assessment_id",
        "transcript_revision_id",
        "state",
        "input_ref",
        "input_sha256",
        "protocol_version_key",
        "extractor",
        "pipeline_version",
        "feature_schema_version",
        "limitations_json",
        "generated_at",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(AssessmentBase.metadata.tables["evidence_feature_values"].columns.keys()) == {
        "evidence_feature_id",
        "organization_id",
        "evidence_run_id",
        "feature_key",
        "value_json",
        "unit",
        "source",
        "state",
        "limitation",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(AssessmentBase.metadata.tables["evidence_domain_profiles"].columns.keys()) == {
        "domain_profile_id",
        "organization_id",
        "evidence_run_id",
        "domain",
        "status",
        "summary",
        "feature_keys_json",
        "supporting_features_json",
        "conflicting_features_json",
        "limitations_json",
        "version",
        "created_at",
        "updated_at",
    }


def test_evidence_tables_require_tenant_composite_links_and_enum_checks() -> None:
    assert {
        ("organization_id", "evidence_run_id"),
        (
            "organization_id",
            "assessment_id",
            "transcript_revision_id",
            "pipeline_version",
            "feature_schema_version",
        ),
    }.issubset(_unique_columns("evidence_runs"))
    assert ("organization_id", "evidence_run_id", "feature_key") in _unique_columns(
        "evidence_feature_values"
    )
    assert ("organization_id", "evidence_run_id", "domain") in _unique_columns(
        "evidence_domain_profiles"
    )

    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "transcript_revision_id"),
    }.issubset(_foreign_key_columns("evidence_runs"))
    assert {("organization_id", "evidence_run_id")} <= _foreign_key_columns(
        "evidence_feature_values"
    )
    assert {("organization_id", "evidence_run_id")} <= _foreign_key_columns(
        "evidence_domain_profiles"
    )

    run_checks = {
        str(constraint.sqltext)
        for constraint in AssessmentBase.metadata.tables["evidence_runs"].constraints
        if isinstance(constraint, CheckConstraint)
    }
    feature_checks = {
        str(constraint.sqltext)
        for constraint in AssessmentBase.metadata.tables["evidence_feature_values"].constraints
        if isinstance(constraint, CheckConstraint)
    }
    domain_checks = {
        str(constraint.sqltext)
        for constraint in AssessmentBase.metadata.tables["evidence_domain_profiles"].constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert f"state IN ({', '.join(repr(value.value) for value in EvidenceState)})" in run_checks
    assert f"source IN ({', '.join(repr(value.value) for value in EvidenceSource)})" in feature_checks
    assert f"state IN ({', '.join(repr(value.value) for value in EvidenceState)})" in feature_checks
    assert f"domain IN ({', '.join(repr(value.value) for value in DevelopmentalDomain)})" in domain_checks
    assert f"status IN ({', '.join(repr(value.value) for value in DomainProfileStatus)})" in domain_checks
    assert any("value_json IS NOT NULL" in check for check in feature_checks)
    assert any("length(limitation) > 0" in check for check in feature_checks)


def test_evidence_migration_creates_and_downgrades_its_three_tables(monkeypatch) -> None:
    import sqlite3
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from app.assessment_v2.db.migrations_runner import (
        downgrade_assessment_database,
        upgrade_assessment_database,
    )
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-evidence-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-evidence.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database()
            with sqlite3.connect(database_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                revision = connection.execute("select version_num from alembic_version").fetchone()
            assert {"evidence_runs", "evidence_feature_values", "evidence_domain_profiles"} <= tables
            assert revision == ("0006_evidence_profiles",)

            downgrade_assessment_database("0005_transcript_revisions")
            with sqlite3.connect(database_path) as connection:
                tables_after_downgrade = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
            assert {"evidence_runs", "evidence_feature_values", "evidence_domain_profiles"}.isdisjoint(
                tables_after_downgrade
            )
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()
