from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_compose_uses_a_migrated_non_superuser_assessment_runtime():
    compose = (ROOT / "docker-compose.yml").read_text()
    init_sql = (ROOT / "scripts/postgres/init-assessment-v2.sql").read_text()

    assert "LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP=true" in compose
    assert "lingualens_assessment_app" in compose
    assert "condition: service_healthy" in compose
    assert "CREATE ROLE lingualens_assessment_app" in init_sql
    assert "NOSUPERUSER" in init_sql
    assert "NOBYPASSRLS" in init_sql
    assert "OWNER lingualens_assessment_app" in init_sql

    check_override = (ROOT / "docker-compose.assessment-check.yml").read_text()
    assert '"5434:5432"' in check_override
    assert "ports: !override" in check_override
