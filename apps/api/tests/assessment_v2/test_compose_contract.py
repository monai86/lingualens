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
    assert '"8002:8000"' in check_override
    assert "ports: !override" in check_override


def test_canonical_api_runtimes_expose_the_repository_root_for_analysis_contract_imports():
    compose = (ROOT / "docker-compose.yml").read_text()
    render_runbook = (ROOT / "docs/RENDER_BACKEND_STAGING_RUNBOOK.md").read_text()
    api_service = compose.split("\n  worker:", 1)[0]

    assert "PYTHONPATH=/workspace/apps/api:/workspace" in compose
    assert 'pip install -r requirements.txt && uvicorn app.main:app' in api_service
    assert 'pip install -r ../../requirements.txt -r requirements.txt' not in api_service
    assert "Root Directory: ." in render_runbook
    assert "PYTHONPATH=apps/api:.:src" in render_runbook


def test_compose_runtime_check_exercises_the_api_service_not_a_host_substitute():
    check_script = (ROOT / "scripts/check_assessment_v2_compose.py").read_text()

    assert '_run("up", "-d", "--force-recreate", "postgres", "api")' in check_script
    assert "_start_host_api" not in check_script
