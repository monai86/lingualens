from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory


def test_fresh_assessment_database_upgrades_and_downgrades() -> None:
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/check_assessment_v2_migrations.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "assessment-v2 migration smoke passed" in result.stdout


def test_audit_metadata_json_has_empty_object_server_default(monkeypatch) -> None:
    from app.assessment_v2.db.migrations_runner import downgrade_assessment_database, upgrade_assessment_database
    from app.core.config import get_settings

    with TemporaryDirectory(prefix="lingualens-assessment-v2-default-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2.db"
        monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", f"sqlite:///{database_path}")
        get_settings.cache_clear()
        upgrade_assessment_database()
        try:
            with sqlite3.connect(database_path) as connection:
                default = connection.execute("pragma table_info(audit_events)").fetchall()
            metadata_default = next(row[4] for row in default if row[1] == "metadata_json")
            assert metadata_default in {"'{}'", "{}"}
        finally:
            downgrade_assessment_database()
            get_settings.cache_clear()
