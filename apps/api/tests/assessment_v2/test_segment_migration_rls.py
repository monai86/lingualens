from pathlib import Path


def test_segment_migration_is_additive_and_has_postgres_rls_guards() -> None:
    migration = Path(__file__).parents[2] / "app" / "assessment_v2" / "db" / "migrations" / "versions" / "0008_transcript_segments.py"
    source = migration.read_text()

    assert "down_revision = \"0007_durable_evidence_jobs\"" in source
    assert 'op.create_table(\n        "transcript_segment_sets"' in source
    assert 'op.create_table(\n        "transcript_segments"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.current_organization_id', true)" in source
    assert "DROP POLICY IF EXISTS transcript_segment_sets_organization_isolation" in source
    assert "NO FORCE ROW LEVEL SECURITY" in source
    assert "DISABLE ROW LEVEL SECURITY" in source
    assert "DROP POLICY IF EXISTS transcript_segments_organization_isolation" in source


def test_segment_migration_downgrade_drops_only_new_segment_tables() -> None:
    migration = Path(__file__).parents[2] / "app" / "assessment_v2" / "db" / "migrations" / "versions" / "0008_transcript_segments.py"
    source = migration.read_text()

    downgrade_source = source.split("def downgrade()", 1)[1]
    assert 'op.drop_table("transcript_segments")' in downgrade_source
    assert 'op.drop_table("transcript_segment_sets")' in downgrade_source
    assert 'op.drop_table("transcript_revisions")' not in downgrade_source


def test_segment_migration_refuses_populated_downgrade() -> None:
    migration = Path(__file__).parents[2] / "app" / "assessment_v2" / "db" / "migrations" / "versions" / "0008_transcript_segments.py"
    source = migration.read_text()

    assert "segment_downgrade_blocked" in source
    assert "def _assert_no_segment_rows(bind)" in source
    assert 'for table_name in ("transcript_segment_sets", "transcript_segments")' in source
    assert 'sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name})")' in source


def test_segment_evidence_provenance_migration_is_nullable_and_downgrade_guarded() -> None:
    migration = (
        Path(__file__).parents[2]
        / "app"
        / "assessment_v2"
        / "db"
        / "migrations"
        / "versions"
        / "0009_segment_evidence_provenance.py"
    )
    source = migration.read_text()

    assert 'revision = "0009_segment_evidence_provenance"' in source
    assert 'down_revision = "0008_transcript_segments"' in source
    assert 'sa.Column("segment_set_id", sa.String(length=64), nullable=True)' in source
    assert 'sa.Column("segment_set_sha256", sa.String(length=64), nullable=True)' in source
    assert "segment_evidence_provenance_downgrade_blocked" in source
    assert "fk_processing_runs_segment_set_tenant" in source
    assert "fk_evidence_runs_segment_set_tenant" in source
    assert "_disable_evidence_rls_for_downgrade" in source
    assert "_restore_evidence_rls_after_downgrade" in source
