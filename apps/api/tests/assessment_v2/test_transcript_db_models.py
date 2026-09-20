from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.assessment_v2.db import models as _models  # noqa: F401
from app.assessment_v2.db.base import AssessmentBase


def test_transcript_revision_table_keeps_tenant_scoped_immutable_content_metadata() -> None:
    table = AssessmentBase.metadata.tables["transcript_revisions"]

    assert set(table.columns.keys()) == {
        "transcript_revision_id",
        "organization_id",
        "assessment_id",
        "revision",
        "source",
        "review_state",
        "content",
        "content_sha256",
        "created_by_user_id",
        "attested_by_user_id",
        "attested_at",
        "version",
        "created_at",
        "updated_at",
    }
    assert {
        ("organization_id", "transcript_revision_id"),
        ("organization_id", "assessment_id", "revision"),
    }.issubset({
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    })
    assert {
        ("organization_id", "assessment_id"),
    }.issubset({
        tuple(constraint.column_keys)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    })
    assert {
        "source IN ('manual', 'asr_draft', 'imported')",
        "review_state IN ('draft', 'attested', 'superseded')",
        "revision >= 1",
        "version >= 1",
    }.issubset({
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    })


def test_fresh_assessment_migration_creates_and_downgrades_transcript_revisions(monkeypatch) -> None:
    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database, upgrade_assessment_database
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-transcript-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-transcript.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database("0005_transcript_revisions")
            with sqlite3.connect(database_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                revision = connection.execute("select version_num from alembic_version").fetchone()
            assert "transcript_revisions" in tables
            assert revision == ("0005_transcript_revisions",)

            downgrade_assessment_database("0004_capture_cleanup_stage")
            with sqlite3.connect(database_path) as connection:
                tables_after_downgrade = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
            assert "transcript_revisions" not in tables_after_downgrade
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()
