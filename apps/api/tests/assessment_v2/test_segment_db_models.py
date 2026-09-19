from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.assessment_v2.db import models as _models  # noqa: F401
from app.assessment_v2.db.base import AssessmentBase


def test_transcript_segment_tables_are_tenant_scoped_and_immutable_snapshots() -> None:
    segment_sets = AssessmentBase.metadata.tables["transcript_segment_sets"]
    segments = AssessmentBase.metadata.tables["transcript_segments"]

    assert set(segment_sets.columns.keys()) == {
        "transcript_segment_set_id",
        "organization_id",
        "assessment_id",
        "transcript_revision_id",
        "transcript_content_sha256",
        "recording_id",
        "revision",
        "source",
        "review_state",
        "segments_sha256",
        "created_by_user_id",
        "attested_by_user_id",
        "attested_at",
        "version",
        "created_at",
        "updated_at",
    }
    assert set(segments.columns.keys()) == {
        "transcript_segment_id",
        "organization_id",
        "transcript_segment_set_id",
        "ordinal",
        "start_ms",
        "end_ms",
        "speaker_role",
        "text",
        "confidence",
        "uncertainty_reason",
        "created_at",
    }
    assert {
        ("organization_id", "assessment_id", "revision"),
        ("organization_id", "transcript_segment_set_id"),
    }.issubset(
        {
            tuple(constraint.columns.keys())
            for constraint in segment_sets.constraints
            if isinstance(constraint, UniqueConstraint)
        }
    )
    assert {
        ("organization_id", "transcript_segment_set_id", "ordinal"),
        ("organization_id", "transcript_segment_id"),
    }.issubset(
        {
            tuple(constraint.columns.keys())
            for constraint in segments.constraints
            if isinstance(constraint, UniqueConstraint)
        }
    )
    assert {
        ("organization_id", "assessment_id"),
        ("organization_id", "transcript_revision_id"),
    }.issubset(
        {
            tuple(constraint.column_keys)
            for constraint in segment_sets.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        }
    )
    assert {
        ("organization_id", "transcript_segment_set_id"),
    }.issubset(
        {
            tuple(constraint.column_keys)
            for constraint in segments.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        }
    )
    assert {
        "revision >= 1",
        "version >= 1",
        "length(segments_sha256) = 64",
        "length(transcript_content_sha256) = 64",
        "source IN ('manual', 'asr_draft', 'imported')",
        "review_state IN ('draft', 'attested', 'superseded')",
    }.issubset(
        {
            str(constraint.sqltext)
            for constraint in segment_sets.constraints
            if isinstance(constraint, CheckConstraint)
        }
    )
    assert {
        "ordinal >= 1",
        "start_ms >= 0",
        "end_ms > start_ms",
        "length(text) > 0",
        "confidence IS NULL OR confidence BETWEEN 0 AND 1",
    }.issubset(
        {
            str(constraint.sqltext)
            for constraint in segments.constraints
            if isinstance(constraint, CheckConstraint)
        }
    )


def test_segment_migration_creates_and_downgrades_without_removing_transcripts(monkeypatch) -> None:
    from app.assessment_v2.db.migrations_runner import (
        downgrade_assessment_database,
        upgrade_assessment_database,
    )
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-segments-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-segments.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database("0008_transcript_segments")
            with sqlite3.connect(database_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                revision = connection.execute("select version_num from alembic_version").fetchone()
            assert {"transcript_revisions", "transcript_segment_sets", "transcript_segments"}.issubset(
                tables
            )
            assert revision == ("0008_transcript_segments",)

            downgrade_assessment_database("0007_durable_evidence_jobs")
            with sqlite3.connect(database_path) as connection:
                tables_after_downgrade = {
                    row[0]
                    for row in connection.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
            assert "transcript_revisions" in tables_after_downgrade
            assert "transcript_segment_sets" not in tables_after_downgrade
            assert "transcript_segments" not in tables_after_downgrade
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()


def test_populated_segment_set_blocks_full_downgrade_after_provenance_downgrade(
    monkeypatch,
) -> None:
    from app.assessment_v2.db.migrations_runner import (
        downgrade_assessment_database,
        upgrade_assessment_database,
    )
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-segment-guard-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2-segment-guard.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        try:
            upgrade_assessment_database()
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO transcript_segment_sets (
                        transcript_segment_set_id, organization_id, assessment_id,
                        transcript_revision_id, transcript_content_sha256, recording_id,
                        revision, source, review_state, segments_sha256,
                        created_by_user_id, attested_by_user_id, attested_at,
                        version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "segment_set_guard_01",
                        "org_guard_01",
                        "assessment_guard_01",
                        "transcript_guard_01",
                        "a" * 64,
                        None,
                        1,
                        "manual",
                        "draft",
                        "b" * 64,
                        "therapist_guard_01",
                        None,
                        None,
                        1,
                        "2026-09-09 00:00:00",
                        "2026-09-09 00:00:00",
                    ),
                )
                connection.commit()

            # 0009 has no segment-bound evidence to guard, but 0008 must still
            # refuse to remove the populated immutable segment snapshot.
            downgrade_assessment_database("0008_transcript_segments")
            with pytest.raises(RuntimeError, match="segment_downgrade_blocked"):
                downgrade_assessment_database("0007_durable_evidence_jobs")

            with sqlite3.connect(database_path) as connection:
                remaining = connection.execute(
                    "SELECT count(*) FROM transcript_segment_sets"
                ).fetchone()
                assert remaining == (1,)
                connection.execute("DELETE FROM transcript_segment_sets")
                connection.commit()

            downgrade_assessment_database("0007_durable_evidence_jobs")
        finally:
            get_settings.cache_clear()
