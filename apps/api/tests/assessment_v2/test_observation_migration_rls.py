from pathlib import Path


def test_observation_migration_is_additive_and_has_postgres_rls() -> None:
    migration = (
        Path(__file__).parents[2]
        / "app"
        / "assessment_v2"
        / "db"
        / "migrations"
        / "versions"
        / "0010_observations_instruments.py"
    )
    source = migration.read_text()

    assert 'revision = "0010_observations_instruments"' in source
    assert 'down_revision = "0009_segment_evidence_provenance"' in source
    assert 'op.create_table(\n        "assessment_observations"' in source
    assert 'op.create_table(\n        "assessment_instruments"' in source
    assert 'op.create_table(\n        "assessment_instrument_items"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.current_organization_id', true)" in source
    assert "DROP POLICY IF EXISTS assessment_observations_organization_isolation" in source
    assert "DROP POLICY IF EXISTS assessment_instruments_organization_isolation" in source
    assert "DROP POLICY IF EXISTS assessment_instrument_items_organization_isolation" in source
