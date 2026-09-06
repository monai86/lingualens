import pytest

from app.core.config import DEFAULT_ASSESSMENT_DATABASE_URL, Settings


def _production_values() -> dict[str, object]:
    return {
        "mock_mode": False,
        "auth_mode": "supabase",
        "supabase_jwt_secret": "test-supabase-jwt-secret",
        "supabase_jwt_issuer": "https://project-ref.supabase.co/auth/v1",
        "cors_allowed_origins": "https://clinic.example",
        "repository_mode": "sql",
        "database_url": "postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        "sql_create_schema": False,
        "storage_mode": "private",
        "job_queue_mode": "redis",
        "redis_url": "rediss://redis.example:6379/0",
        "observability_enabled": True,
        "observability_provider": "sentry",
        "critical_alert_route": "pagerduty-critical",
        "secret_store_provider": "aws_secrets_manager",
        "credential_rotation_runbook": "docs/SECRET_ROTATION_RUNBOOK.md",
    }


def _supabase_private_production_values() -> dict[str, object]:
    values = _production_values()
    values.update(
        {
            "storage_mode": "supabase_private",
            "assessment_database_url": "postgresql+psycopg://v2_writer:synthetic@v2.example/assessment_v2",
            "supabase_storage_url": "https://project-ref.supabase.co",
            "supabase_storage_service_role_key": "synthetic-service-role-key",
            "supabase_storage_bucket": "capture-private",
            "supabase_storage_tus_endpoint": "https://project-ref.supabase.co/storage/v1/upload/resumable",
        }
    )
    return values


def test_assessment_database_uses_dedicated_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", "postgresql+psycopg://v2.example/test")

    settings = Settings.from_env()

    assert settings.assessment_database_url == "postgresql+psycopg://v2.example/test"
    assert settings.assessment_api_prefix == "/api/v2"


def test_assessment_database_defaults_to_isolated_url() -> None:
    settings = Settings()

    assert settings.assessment_database_url == DEFAULT_ASSESSMENT_DATABASE_URL
    assert settings.assessment_api_prefix == "/api/v2"
    assert settings.run_assessment_migrations_on_startup is False


def test_assessment_migration_startup_flag_uses_dedicated_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP", "true")

    settings = Settings.from_env()

    assert settings.run_assessment_migrations_on_startup is True


def test_capture_supabase_storage_configuration_uses_server_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_URL", "https://project-ref.supabase.co")
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_SERVICE_ROLE_KEY", "synthetic-service-role-key")
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_BUCKET", "capture-private")
    monkeypatch.setenv(
        "LINGUALENS_SUPABASE_STORAGE_TUS_ENDPOINT",
        "https://project-ref.supabase.co/storage/v1/upload/resumable",
    )
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_SIGNED_UPLOAD_TTL_SECONDS", "7200")
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_SIGNED_DOWNLOAD_TTL_SECONDS", "900")
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_TUS_CHUNK_SIZE_BYTES", str(6 * 1024 * 1024))
    monkeypatch.setenv("LINGUALENS_SUPABASE_STORAGE_MAX_UPLOAD_SIZE_BYTES", str(250 * 1024 * 1024))

    settings = Settings.from_env()

    assert settings.supabase_storage_url == "https://project-ref.supabase.co"
    assert settings.supabase_storage_service_role_key == "synthetic-service-role-key"
    assert settings.supabase_storage_bucket == "capture-private"
    assert settings.supabase_storage_tus_endpoint.endswith("/storage/v1/upload/resumable")
    assert settings.supabase_storage_signed_upload_ttl_seconds == 7200
    assert settings.supabase_storage_signed_download_ttl_seconds == 900
    assert settings.supabase_storage_tus_chunk_size_bytes == 6 * 1024 * 1024
    assert settings.capture_max_upload_size_bytes == 250 * 1024 * 1024


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("supabase_storage_url", "http://project-ref.supabase.co"),
        ("supabase_storage_service_role_key", ""),
        ("supabase_storage_bucket", "capture/private"),
        ("supabase_storage_tus_endpoint", "https://project-ref.supabase.co/not-tus"),
    ),
)
def test_production_supabase_private_storage_rejects_missing_or_invalid_configuration(
    field: str,
    invalid_value: object,
) -> None:
    values = _supabase_private_production_values()
    values[field] = invalid_value

    with pytest.raises(ValueError, match="Supabase private storage"):
        Settings(**values).validate_runtime_security()


def test_production_supabase_private_storage_accepts_explicit_private_tus_configuration() -> None:
    settings = Settings(**_supabase_private_production_values()).validate_runtime_security()

    assert settings.storage_mode == "supabase_private"
    assert settings.supabase_storage_tus_chunk_size_bytes == 6 * 1024 * 1024
    assert settings.capture_max_upload_size_bytes == 250 * 1024 * 1024


def test_production_rejects_default_assessment_database_url() -> None:
    with pytest.raises(ValueError, match="assessment database URL"):
        Settings(**_production_values()).validate_runtime_security()


def test_production_rejects_assessment_schema_creation() -> None:
    settings = Settings(
        **_production_values(),
        assessment_database_url="postgresql+psycopg://v2.example/assessment",
        run_assessment_migrations_on_startup=True,
    )

    with pytest.raises(ValueError, match="assessment.*migrations"):
        settings.validate_runtime_security()


def test_production_accepts_managed_assessment_database_with_migrations_disabled() -> None:
    settings = Settings(
        **_production_values(),
        assessment_database_url="postgresql+psycopg://v2.example/assessment",
    ).validate_runtime_security()

    assert settings.assessment_api_prefix == "/api/v2"
    assert settings.run_assessment_migrations_on_startup is False


def test_production_rejects_reusing_the_v1_database_for_assessment_v2() -> None:
    shared_url = "postgresql+psycopg://prod_user:prod_password@db.example/shared"

    with pytest.raises(ValueError, match="different"):
        values = _production_values()
        values.update(database_url=shared_url, assessment_database_url=shared_url)
        Settings(**values).validate_runtime_security()


def test_production_rejects_assessment_database_target_shared_with_v1_despite_url_variants() -> None:
    values = _production_values()
    values.update(
        database_url="postgresql+psycopg://v1_reader:synthetic@DB.EXAMPLE/isolated_database",
        assessment_database_url=(
            "postgresql://v2_writer:synthetic@db.example:5432/isolated_database?sslmode=require"
        ),
    )

    with pytest.raises(ValueError, match="different"):
        Settings(**values).validate_runtime_security()


@pytest.mark.parametrize(
    "assessment_database_url",
    (
        "sqlite:////managed/assessment-v2.db",
        "mysql+pymysql://assessment_user:synthetic@db.example/assessment_v2",
    ),
)
def test_production_rejects_non_postgresql_assessment_database_urls(
    assessment_database_url: str,
) -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(
            **_production_values(),
            assessment_database_url=assessment_database_url,
        ).validate_runtime_security()


def test_production_keeps_distinct_v1_postgresql_driver_configuration_compatible() -> None:
    values = _production_values()
    values.update(
        database_url="postgresql+asyncpg://v1_reader:synthetic@db.example/therapist_app_v1",
        assessment_database_url="postgresql+psycopg://v2_writer:synthetic@db.example/assessment_v2",
    )

    settings = Settings(**values).validate_runtime_security()

    assert settings.database_url.startswith("postgresql+asyncpg://")
