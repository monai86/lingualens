"""Unit tests for assessment v2 generic instrument administration domain model."""

from datetime import datetime, timezone
import pytest

from app.assessment_v2.domain.instruments import (
    InstrumentAdministration,
    InstrumentItemResponse,
    InstrumentRespondentType,
)


def test_valid_instrument_administration():
    now = datetime.now(timezone.utc)
    item1 = InstrumentItemResponse(
        item_key="item_01",
        prompt_label="Social interest in peers",
        response_value=True,
        score=1.0,
        notes="Parent noted interest when at playground",
    )
    item2 = InstrumentItemResponse(
        item_key="item_02",
        prompt_label="Pointing to request or share interest",
        response_value=False,
        score=0.0,
        notes="Points with whole hand rather than index finger",
    )

    admin = InstrumentAdministration(
        administration_id="inst_admin_001",
        organization_id="org_demo",
        assessment_id="asm_123",
        instrument_name="Generic-Comm-Screen-v1",
        instrument_version="1.0.0",
        respondent_type=InstrumentRespondentType.CAREGIVER,
        administered_by_user_id="usr_slp_1",
        administered_at=now,
        licensing_verified=True,
        summary_scores={"total_risk_indicators": 1.0, "raw_score": 1.0},
        items=(item1, item2),
    )

    assert admin.administration_id == "inst_admin_001"
    assert admin.instrument_name == "Generic-Comm-Screen-v1"
    assert admin.licensing_verified is True
    assert len(admin.items) == 2
    d = admin.to_dict()
    assert d["administration_id"] == "inst_admin_001"
    assert d["items"][0]["item_key"] == "item_01"


def test_instrument_validation_constraints():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="administration_id"):
        InstrumentAdministration(
            administration_id="",
            organization_id="org_demo",
            assessment_id="asm_123",
            instrument_name="Screen",
            instrument_version="1.0",
            respondent_type=InstrumentRespondentType.CLINICIAN,
            administered_by_user_id="usr_1",
            administered_at=now,
            licensing_verified=True,
            summary_scores={},
            items=(),
        )

    with pytest.raises(ValueError, match="newlines"):
        InstrumentAdministration(
            administration_id="admin_01\ninjection",
            organization_id="org_demo",
            assessment_id="asm_123",
            instrument_name="Screen",
            instrument_version="1.0",
            respondent_type=InstrumentRespondentType.CLINICIAN,
            administered_by_user_id="usr_1",
            administered_at=now,
            licensing_verified=True,
            summary_scores={},
            items=(),
        )


def test_instrument_timezone_awareness():
    naive_dt = datetime(2026, 9, 12, 11, 0, 0)
    with pytest.raises(ValueError, match="timezone"):
        InstrumentAdministration(
            administration_id="admin_01",
            organization_id="org_demo",
            assessment_id="asm_123",
            instrument_name="Screen",
            instrument_version="1.0",
            respondent_type=InstrumentRespondentType.CLINICIAN,
            administered_by_user_id="usr_1",
            administered_at=naive_dt,
            licensing_verified=True,
            summary_scores={},
            items=(),
        )
