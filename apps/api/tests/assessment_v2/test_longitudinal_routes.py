"""Route and service tests for assessment v2 longitudinal comparisons."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.db.models import (
    AssessmentComparisonFeatureRecord,
    AssessmentComparisonRecord,
)
from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    ChildSnapshot,
)
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DevelopmentalEvidenceProfile,
    DomainProfile,
    DomainProfileStatus,
    EvidenceProvenance,
    EvidenceRunSnapshot,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.longitudinal import (
    CompatibilityStatus,
    IncompatibilityReason,
    NumericalTrend,
)
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.main import app


class FakeLongitudinalService:
    """Mock AssessmentService implementing longitudinal comparison methods."""

    def __init__(self) -> None:
        self.comparisons: dict[str, AssessmentComparisonRecord] = {}
        self.history: list[dict[str, Any]] = []
        self.child_org_map: dict[str, str] = {}
        self.active_consents: set[str] = set()

    def compare_assessments(
        self,
        assessment_id: str,
        baseline_assessment_id: str,
        policy_version: str,
        correlation_id: str,
    ) -> AssessmentComparisonRecord:
        if assessment_id == "asmt_child_a" and baseline_assessment_id == "asmt_child_b":
            raise ClinicalPolicyError("different_child", 400, "Assessments belong to different children.")
        if assessment_id == "asmt_other_org":
            raise ClinicalPolicyError("tenant_mismatch", 403, "Assessments must belong to caller organization.")
        if assessment_id == "asmt_no_consent":
            raise ClinicalPolicyError("active_consent_required", 409, "Active clinical assessment consent required.")

        comp_id = f"comp_{uuid4().hex[:8]}"
        is_zero_base = baseline_assessment_id == "asmt_zero_base"
        is_mismatch = baseline_assessment_id == "asmt_mismatched_protocol"

        if is_mismatch:
            feat_rec = AssessmentComparisonFeatureRecord(
                comparison_feature_id=uuid4().hex,
                organization_id="org_1",
                comparison_id=comp_id,
                feature_key="mlu_words",
                unit="morphemes_per_utterance",
                status=CompatibilityStatus.NOT_COMPARABLE.value,
                incompatibility_reasons_json=[IncompatibilityReason.PROTOCOL_INCOMPATIBLE.value],
                baseline_value=3.0,
                current_value=4.5,
                absolute_delta=None,
                percent_change=None,
                percent_change_limitation=None,
                numerical_trend=NumericalTrend.INDETERMINATE.value,
                clinical_interpretation="indeterminate",
                created_at=datetime.now(timezone.utc),
            )
            status = CompatibilityStatus.NOT_COMPARABLE.value
        elif is_zero_base:
            feat_rec = AssessmentComparisonFeatureRecord(
                comparison_feature_id=uuid4().hex,
                organization_id="org_1",
                comparison_id=comp_id,
                feature_key="consonant_inventory_size",
                unit="count",
                status=CompatibilityStatus.COMPATIBLE.value,
                incompatibility_reasons_json=[],
                baseline_value=0.0,
                current_value=5.0,
                absolute_delta=5.0,
                percent_change=None,
                percent_change_limitation="zero_baseline",
                numerical_trend=NumericalTrend.INCREASED.value,
                clinical_interpretation="indeterminate",
                created_at=datetime.now(timezone.utc),
            )
            status = CompatibilityStatus.COMPATIBLE.value
        else:
            feat_rec = AssessmentComparisonFeatureRecord(
                comparison_feature_id=uuid4().hex,
                organization_id="org_1",
                comparison_id=comp_id,
                feature_key="mlu_words",
                unit="morphemes_per_utterance",
                status=CompatibilityStatus.COMPATIBLE.value,
                incompatibility_reasons_json=[],
                baseline_value=2.5,
                current_value=3.5,
                absolute_delta=1.0,
                percent_change=40.0,
                percent_change_limitation=None,
                numerical_trend=NumericalTrend.INCREASED.value,
                clinical_interpretation="indeterminate",
                created_at=datetime.now(timezone.utc),
            )
            status = CompatibilityStatus.COMPATIBLE.value

        rec = AssessmentComparisonRecord(
            comparison_id=comp_id,
            organization_id="org_1",
            child_id="child_1",
            baseline_assessment_id=baseline_assessment_id,
            current_assessment_id=assessment_id,
            baseline_evidence_run_id=f"run_{baseline_assessment_id}",
            current_evidence_run_id=f"run_{assessment_id}",
            baseline_evidence_sha256="a" * 64,
            current_evidence_sha256="b" * 64,
            policy_version=policy_version,
            status=status,
            is_stale=False,
            compatible_feature_count=1 if status == CompatibilityStatus.COMPATIBLE.value else 0,
            incompatible_feature_count=0 if status == CompatibilityStatus.COMPATIBLE.value else 1,
            compared_by_user_id="user_1",
            created_at=datetime.now(timezone.utc),
        )
        rec.features = [feat_rec]
        self.comparisons[comp_id] = rec
        return rec

    def list_assessment_comparisons(self, assessment_id: str) -> list[AssessmentComparisonRecord]:
        return [
            r for r in self.comparisons.values()
            if r.current_assessment_id == assessment_id or r.baseline_assessment_id == assessment_id
        ]

    def get_assessment_comparison(self, assessment_id: str, comparison_id: str) -> AssessmentComparisonRecord:
        comp = self.comparisons.get(comparison_id)
        if comp is None or (comp.current_assessment_id != assessment_id and comp.baseline_assessment_id != assessment_id):
            raise ClinicalPolicyError("comparison_not_found", 404, "Comparison not found.")
        return comp

    def list_child_assessment_history(self, child_id: str) -> list[dict[str, Any]]:
        return self.history


@pytest.fixture
def longitudinal_client() -> Iterator[tuple[TestClient, FakeLongitudinalService]]:
    service = FakeLongitudinalService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        yield TestClient(app), service
    finally:
        app.dependency_overrides.clear()


def test_create_comparison_rejects_different_child(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, _ = longitudinal_client
    resp = client.post(
        "/api/v2/assessments/asmt_child_a/comparisons",
        json={"baseline_assessment_id": "asmt_child_b", "policy_version": "longitudinal_v1"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "different_child"


def test_create_comparison_rejects_tenant_mismatch(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, _ = longitudinal_client
    resp = client.post(
        "/api/v2/assessments/asmt_other_org/comparisons",
        json={"baseline_assessment_id": "asmt_base", "policy_version": "longitudinal_v1"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "tenant_mismatch"


def test_create_comparison_rejects_withdrawn_consent(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, _ = longitudinal_client
    resp = client.post(
        "/api/v2/assessments/asmt_no_consent/comparisons",
        json={"baseline_assessment_id": "asmt_base", "policy_version": "longitudinal_v1"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "active_consent_required"


def test_create_comparison_success_with_zero_baseline_and_indeterminate_interpretation(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, _ = longitudinal_client
    resp = client.post(
        "/api/v2/assessments/asmt_curr_1/comparisons",
        json={"baseline_assessment_id": "asmt_zero_base", "policy_version": "longitudinal_v1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "compatible"
    assert data["is_stale"] is False
    assert len(data["features"]) == 1

    feat = data["features"][0]
    assert feat["feature_key"] == "consonant_inventory_size"
    assert feat["baseline_value"] == 0.0
    assert feat["current_value"] == 5.0
    assert feat["absolute_delta"] == 5.0
    assert feat["percent_change"] is None
    assert feat["percent_change_limitation"] == "zero_baseline"
    assert feat["numerical_trend"] == "increased"
    # Mandatory safety rule: Never classify as improved or stable without approved clinical policy!
    assert feat["clinical_interpretation"] == "indeterminate"


def test_create_comparison_with_protocol_mismatch_marks_not_comparable(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, _ = longitudinal_client
    resp = client.post(
        "/api/v2/assessments/asmt_curr_1/comparisons",
        json={"baseline_assessment_id": "asmt_mismatched_protocol", "policy_version": "longitudinal_v1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "not_comparable"
    feat = data["features"][0]
    assert feat["status"] == "not_comparable"
    assert "protocol_incompatible" in feat["incompatibility_reasons"]
    assert feat["absolute_delta"] is None
    assert feat["percent_change"] is None
    assert feat["clinical_interpretation"] == "indeterminate"


def test_list_and_get_comparisons_and_child_history(
    longitudinal_client: tuple[TestClient, FakeLongitudinalService],
) -> None:
    client, service = longitudinal_client

    # 1. Create a comparison
    create_resp = client.post(
        "/api/v2/assessments/asmt_curr_1/comparisons",
        json={"baseline_assessment_id": "asmt_base_1", "policy_version": "longitudinal_v1"},
    )
    assert create_resp.status_code == 201
    comp_id = create_resp.json()["comparison_id"]

    # 2. List comparisons for this assessment
    list_resp = client.get("/api/v2/assessments/asmt_curr_1/comparisons")
    assert list_resp.status_code == 200
    comps = list_resp.json()
    assert len(comps) == 1
    assert comps[0]["comparison_id"] == comp_id

    # 3. Get specific comparison
    get_resp = client.get(f"/api/v2/assessments/asmt_curr_1/comparisons/{comp_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["comparison_id"] == comp_id

    # 4. Child history endpoint
    now = datetime.now(timezone.utc)
    service.history = [
        {
            "assessment_id": "asmt_base_1",
            "created_at": now.isoformat(),
            "purpose": "initial",
            "state": "finalized",
            "age_months": 36,
            "protocol_version_key": "thai_guided_language_sample:v0",
            "language": "th",
            "evidence_run_id": "run_base_1",
            "is_comparable": True,
        },
        {
            "assessment_id": "asmt_curr_1",
            "created_at": now.isoformat(),
            "purpose": "developmental_follow_up",
            "state": "finalized",
            "age_months": 42,
            "protocol_version_key": "thai_guided_language_sample:v0",
            "language": "th",
            "evidence_run_id": "run_curr_1",
            "is_comparable": True,
        },
    ]
    hist_resp = client.get("/api/v2/children/child_1/assessments/history")
    assert hist_resp.status_code == 200
    history_items = hist_resp.json()
    assert len(history_items) == 2
    assert history_items[0]["assessment_id"] == "asmt_base_1"
    assert history_items[0]["is_comparable"] is True
