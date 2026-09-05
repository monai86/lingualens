from pathlib import Path
import subprocess
import sys


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
