"""Programmatic runner for the isolated assessment v2 Alembic history."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


API_ROOT = Path(__file__).resolve().parents[3]
ASSESSMENT_ALEMBIC_INI = API_ROOT / "alembic-assessment.ini"
ASSESSMENT_MIGRATIONS = API_ROOT / "app" / "assessment_v2" / "db" / "migrations"


def _config() -> Config:
    settings = get_settings()
    config = Config(str(ASSESSMENT_ALEMBIC_INI))
    config.set_main_option("script_location", str(ASSESSMENT_MIGRATIONS))
    config.set_main_option("sqlalchemy.url", settings.assessment_database_url)
    return config


def upgrade_assessment_database(revision: str = "head") -> None:
    command.upgrade(_config(), revision)


def downgrade_assessment_database(revision: str = "base") -> None:
    command.downgrade(_config(), revision)
