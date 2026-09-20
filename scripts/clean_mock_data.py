#!/usr/bin/env python3
"""Script to clean up accumulated mock test cases, audit logs, and dummy audio files in LinguaLens."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def get_clean_snapshot() -> dict:
    """Generate a clean, minimal initial seed state for LinguaLens repositories."""
    return {
        "cases": {
            "case_demo_001": {
                "child_code": "C-1024",
                "organization_id": "pilot_org_001",
                "care_team_user_ids": ["therapist-demo"],
                "primary_therapist_user_id": "therapist-demo",
                "nickname": "Demo child",
                "age_months": 62,
                "language": "English",
                "consent_status": "granted",
                "notes": "",
                "case_id": "case_demo_001",
                "version": 1,
                "latest_session_date": "2026-06-12",
                "latest_session_status": "Needs Review",
                "latest_report_status": "Draft",
                "review_priority": "moderate",
                "created_at": "2026-09-20T12:00:00.000000Z",
                "updated_at": "2026-09-20T12:00:00.000000Z",
            }
        },
        "sessions": {
            "session_demo_001": {
                "session_id": "session_demo_001",
                "case_id": "case_demo_001",
                "organization_id": "pilot_org_001",
                "version": 1,
                "session_date": "2026-06-12",
                "session_type": "therapy_session",
                "notes": "",
                "status": "Needs Review",
                "transcript_id": None,
                "feature_set_id": None,
                "ml_result_id": None,
                "ai_review_id": None,
                "report_id": None,
                "cues_acknowledged_at": None,
                "cues_acknowledged_by": None,
                "created_at": "2026-09-20T12:00:00.000000Z",
                "updated_at": "2026-09-20T12:00:00.000000Z",
            }
        },
        "transcripts": {},
        "features": {},
        "ml_results": {},
        "ai_reviews": {},
        "reports": {},
        "memberships": {},
        "invitations": {},
        "care_team_assignments": {},
        "therapy_goals": {},
        "audio_files": {},
        "jobs": {},
        "privacy_operations": {},
        "organization_settings": {
            "pilot_org_001": {
                "ai_review_enabled": True
            }
        },
        "audit_log": []
    }


def clean_repository(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"cases_removed": 0, "audit_removed": 0, "bytes_freed": 0}

    initial_size = path.stat().st_size
    cases_count = 0
    audit_count = 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cases_count = len(data.get("cases", {}))
        audit_count = len(data.get("audit_log", []))
    except Exception:
        pass

    clean_data = get_clean_snapshot()
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_json = json.dumps(clean_data, indent=2)
    path.write_text(clean_json, encoding="utf-8")
    new_size = path.stat().st_size

    freed = max(0, initial_size - new_size)
    return {
        "cases_removed": max(0, cases_count - 1),
        "audit_removed": audit_count,
        "bytes_freed": freed,
    }


def clean_storage_audio(storage_dir: Path) -> int:
    if not storage_dir.exists():
        return 0
    count = 0
    for file_path in storage_dir.glob("*.wav"):
        try:
            file_path.unlink()
            count += 1
        except OSError:
            pass
    return count


def reload_api_service() -> bool:
    """Kickstart or restart the launchd lingualens-api service if active."""
    uid = os.getuid()
    try:
        res = subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{uid}/lingualens-api"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    repo_paths = [
        repo_root / ".local" / "lingualens-app-repository.json",
        repo_root / "apps" / "api" / ".local" / "lingualens-app-repository.json",
    ]
    audio_dirs = [
        repo_root / ".local" / "storage" / "audio",
        repo_root / "apps" / "api" / ".local" / "storage" / "audio",
    ]

    print("=" * 60)
    print(" LinguaLens Mock Data & Test Cache Cleanup")
    print("=" * 60)

    total_cases_removed = 0
    total_audit_removed = 0
    total_bytes_freed = 0
    total_audio_deleted = 0

    for p in repo_paths:
        if p.exists():
            res = clean_repository(p)
            rel_path = p.relative_to(repo_root)
            print(f"✓ Reset repository: {rel_path}")
            print(f"  - Mock cases purged: {res['cases_removed']:,}")
            print(f"  - Audit logs purged: {res['audit_removed']:,}")
            print(f"  - Disk space freed:  {res['bytes_freed'] / (1024*1024):.2f} MB")
            total_cases_removed += res["cases_removed"]
            total_audit_removed += res["audit_removed"]
            total_bytes_freed += res["bytes_freed"]

    for a in audio_dirs:
        if a.exists():
            deleted = clean_storage_audio(a)
            rel_path = a.relative_to(repo_root)
            print(f"✓ Purged dummy audio files: {rel_path} ({deleted} files removed)")
            total_audio_deleted += deleted

    print("-" * 60)
    print(f"Total mock cases purged:   {total_cases_removed:,}")
    print(f"Total audit logs purged:   {total_audit_removed:,}")
    print(f"Total dummy audio deleted: {total_audio_deleted:,}")
    print(f"Total disk space reclaimed:{total_bytes_freed / (1024*1024):.2f} MB")

    api_reloaded = reload_api_service()
    if api_reloaded:
        print("✓ Restarted background lingualens-api service (reloaded fresh state)")
    else:
        print("ℹ No background launchd service needed restart")

    print("=" * 60)
    print("✅ All mock test data cleaned up successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
