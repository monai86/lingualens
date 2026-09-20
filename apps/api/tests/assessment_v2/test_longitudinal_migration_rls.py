from pathlib import Path


def test_longitudinal_migration_is_additive_and_has_postgres_rls() -> None:
    migration = (
        Path(__file__).parents[2]
        / "app"
        / "assessment_v2"
        / "db"
        / "migrations"
        / "versions"
        / "0011_longitudinal_comparisons.py"
    )
    assert migration.exists(), "Migration 0011_longitudinal_comparisons.py must exist"
    source = migration.read_text()

    assert 'revision = "0011_longitudinal_comparisons"' in source
    assert 'down_revision = "0010_observations_instruments"' in source
    assert 'op.create_table(\n        "assessment_comparisons"' in source
    assert 'op.create_table(\n        "assessment_comparison_features"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.current_organization_id', true)" in source
    assert "DROP POLICY IF EXISTS assessment_comparisons_organization_isolation" in source
    assert "DROP POLICY IF EXISTS assessment_comparison_features_organization_isolation" in source
