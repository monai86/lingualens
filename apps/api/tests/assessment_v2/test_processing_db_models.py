from __future__ import annotations

from pathlib import Path

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index

from app.assessment_v2.db import models as _models  # noqa: F401  # register mapped tables
from app.assessment_v2.db.base import AssessmentBase


MIGRATIONS = Path(__file__).parents[2] / "app" / "assessment_v2" / "db" / "migrations" / "versions"


def _constraints(table_name: str) -> set[str]:
    return {
        constraint.name
        for constraint in AssessmentBase.metadata.tables[table_name].constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }


def test_processing_runs_has_durable_evidence_target_and_lease_columns() -> None:
    table = AssessmentBase.metadata.tables["processing_runs"]

    assert {
        "assessment_id",
        "transcript_revision_id",
        "evidence_run_id",
        "max_attempts",
        "lease_token",
        "lease_expires_at",
        "cancel_requested_at",
        "completed_at",
        "pipeline_version",
        "feature_schema_version",
        "version",
    }.issubset(table.columns.keys())
    assert table.c.recording_id.nullable is True
    assert table.c.assessment_id.nullable is True
    assert table.c.transcript_revision_id.nullable is True
    assert table.c.evidence_run_id.nullable is True
    assert table.c.max_attempts.nullable is False
    assert table.c.version.nullable is False
    assert isinstance(table.c.lease_expires_at.type, DateTime)
    assert isinstance(table.c.cancel_requested_at.type, DateTime)
    assert isinstance(table.c.completed_at.type, DateTime)


def test_processing_runs_has_target_constraints_tenant_links_and_claim_indexes() -> None:
    table = AssessmentBase.metadata.tables["processing_runs"]
    foreign_keys = {
        tuple(constraint.column_keys)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    indexes = {
        index.name
        for index in table.indexes
        if isinstance(index, Index) and index.name is not None
    }

    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "transcript_revision_id"),
        ("organization_id", "evidence_run_id"),
    }.issubset(foreign_keys)
    assert {
        "ck_processing_runs_target",
        "ck_processing_runs_max_attempts",
        "ck_processing_runs_version",
    }.issubset(_constraints("processing_runs"))
    assert "ix_processing_runs_organization_stage_state_available" in indexes
    assert "ix_processing_runs_organization_stage_lease" in indexes
    assert all(len(name) <= 63 for name in indexes)


def test_durable_evidence_migration_is_next_and_has_safe_downgrade_guard() -> None:
    migration = MIGRATIONS / "0007_durable_evidence_jobs.py"
    assert migration.exists()
    source = migration.read_text()
    assert 'revision = "0007_durable_evidence_jobs"' in source
    assert 'down_revision = "0006_evidence_profiles"' in source
    assert "evidence_extraction" in source
    assert "evidence jobs exist" in source.lower()
