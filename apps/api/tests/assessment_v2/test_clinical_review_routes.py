"""Route tests for assessment v2 clinical review and attention cues (Slice C1)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    ClinicalReviewSession,
    ClinicianFeedback,
    CueStatus,
    FollowUpPlan,
)
from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.services import ClinicalPolicyError
from app.main import app


class FakeClinicalReviewService:
    def __init__(self) -> None:
        self.session = ClinicalReviewSession(
            review_id="rev_101",
            assessment_id="asmt_001",
            tenant_id="tenant_a",
            child_id="child_001",
            evidence_run_id="ev_run_001",
            version=1,
            cues=[
                AttentionCue(
                    cue_id="cue_lex_01",
                    assessment_id="asmt_001",
                    cue_type=AttentionCueType.LEXICAL_DIVERSITY,
                    title="ความหลากหลายของคำศัพท์จำกัด",
                    description="ค่า TTR ต่ำกว่าเกณฑ์",
                    policy_version="cues-v2.0",
                    evidence_run_id="ev_run_001",
                    supporting_feature_keys=["type_token_ratio"],
                    conflicting_feature_keys=[],
                    limitations=[],
                    status=CueStatus.PENDING_REVIEW,
                )
            ],
            disposition=None,
            disposition_notes=None,
            follow_up=None,
            reviewed_by=None,
            reviewed_at=None,
            is_stale=False,
        )

    def get_or_create_clinical_review(self, assessment_id: str) -> ClinicalReviewSession:
        if assessment_id == "asmt_not_found":
            raise ClinicalPolicyError("assessment_not_found", 404, "Assessment was not found.")
        return self.session

    def review_attention_cue(
        self,
        assessment_id: str,
        cue_id: str,
        status: CueStatus,
        rationale: str | None = None,
    ) -> AttentionCue:
        cue = next((c for c in self.session.cues if c.cue_id == cue_id), None)
        if cue is None:
            raise ClinicalPolicyError("attention_cue_not_found", 404, "Attention cue was not found.")
        cue.apply_feedback(
            reviewer_id="clinician_01",
            status=status,
            rationale=rationale,
            reviewed_at=datetime.now(timezone.utc),
        )
        return cue

    def update_clinical_disposition(
        self,
        assessment_id: str,
        disposition: ClinicalDispositionType,
        disposition_notes: str | None = None,
        follow_up: FollowUpPlan | None = None,
        expected_version: int | None = None,
    ) -> ClinicalReviewSession:
        if expected_version is not None and expected_version != self.session.version:
            raise ClinicalPolicyError("stale_assessment_version", 409, "The review version is stale.")
        self.session.disposition = disposition
        self.session.disposition_notes = disposition_notes
        self.session.follow_up = follow_up
        self.session.version += 1
        self.session.reviewed_by = "clinician_01"
        self.session.reviewed_at = datetime.now(timezone.utc)
        return self.session


@pytest.fixture
def fake_service() -> FakeClinicalReviewService:
    return FakeClinicalReviewService()


@pytest.fixture
def client(fake_service: FakeClinicalReviewService) -> Iterator[TestClient]:
    app.dependency_overrides[get_assessment_service] = lambda: fake_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_clinical_review(client: TestClient):
    resp = client.get("/api/v2/assessments/asmt_001/clinical-review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_id"] == "rev_101"
    assert data["version"] == 1
    assert len(data["cues"]) == 1
    assert data["cues"][0]["status"] == "pending_review"


def test_review_attention_cue(client: TestClient):
    resp = client.post(
        "/api/v2/assessments/asmt_001/clinical-review/cues/cue_lex_01",
        json={"status": "acknowledged", "rationale": "ตรวจพบ TTR ต่ำในกิจกรรมเล่นอิสระ"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cue_id"] == "cue_lex_01"
    assert data["status"] == "acknowledged"
    assert data["rationale"] == "ตรวจพบ TTR ต่ำในกิจกรรมเล่นอิสระ"


def test_update_clinical_disposition_and_concurrency(client: TestClient):
    # 1. Successful update
    resp = client.put(
        "/api/v2/assessments/asmt_001/clinical-review/disposition",
        json={
            "disposition": "continue_monitoring",
            "disposition_notes": "นัดติดตามพัฒนาการต่อเนื่องใน 3 เดือน",
            "follow_up_plan": {
                "target_date": "2026-12-01",
                "recommended_protocol": "story_retell",
                "focus_areas": ["turn_taking"],
                "monitoring_notes": "กระตุ้นคำศัพท์ที่บ้าน",
            },
            "expected_version": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["disposition"] == "continue_monitoring"
    assert data["version"] == 2

    # 2. Concurrency conflict with stale version
    resp_stale = client.put(
        "/api/v2/assessments/asmt_001/clinical-review/disposition",
        json={
            "disposition": "targeted_speech_therapy",
            "expected_version": 1,  # Stale!
        },
    )
    assert resp_stale.status_code == 409
