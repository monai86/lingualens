"""Unit tests for assessment v2 observations domain model."""

from datetime import datetime, timezone
import pytest

from app.assessment_v2.domain.observations import (
    ObservationCategory,
    ObservationRecordValue,
    ObservationSource,
)


def test_valid_observation_creation():
    now = datetime.now(timezone.utc)
    obs = ObservationRecordValue(
        observation_id="obs_001",
        organization_id="org_demo",
        assessment_id="asm_123",
        category=ObservationCategory.COMMUNICATION,
        source=ObservationSource.CLINICIAN,
        observer_name="Dr. Taylor",
        observer_role="speech_language_pathologist",
        observed_at=now,
        activity_context="Semi-structured block play",
        notes="Child responded to name on 2nd prompt; used single words to request items.",
        structured_flags=("single_word_requests", "delayed_name_response"),
    )
    assert obs.observation_id == "obs_001"
    assert obs.category == ObservationCategory.COMMUNICATION
    assert obs.source == ObservationSource.CLINICIAN
    assert obs.version == 1
    assert not obs.is_amendment
    assert obs.amends_observation_id is None
    d = obs.to_dict()
    assert d["observation_id"] == "obs_001"
    assert d["structured_flags"] == ["single_word_requests", "delayed_name_response"]


def test_observation_validation_requires_text_and_no_newlines():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="observation_id"):
        ObservationRecordValue(
            observation_id="",
            organization_id="org_demo",
            assessment_id="asm_123",
            category=ObservationCategory.PLAY_BEHAVIOR,
            source=ObservationSource.CAREGIVER,
            observer_name="Parent",
            observer_role="mother",
            observed_at=now,
            activity_context="Home",
            notes="Child lined up cars.",
        )

    with pytest.raises(ValueError, match="newlines"):
        ObservationRecordValue(
            observation_id="obs_001\nmalicious",
            organization_id="org_demo",
            assessment_id="asm_123",
            category=ObservationCategory.PLAY_BEHAVIOR,
            source=ObservationSource.CAREGIVER,
            observer_name="Parent",
            observer_role="mother",
            observed_at=now,
            activity_context="Home",
            notes="Child lined up cars.",
        )


def test_observation_timezone_awareness_required():
    naive_dt = datetime(2026, 9, 12, 10, 0, 0)
    with pytest.raises(ValueError, match="timezone"):
        ObservationRecordValue(
            observation_id="obs_001",
            organization_id="org_demo",
            assessment_id="asm_123",
            category=ObservationCategory.COMMUNICATION,
            source=ObservationSource.CLINICIAN,
            observer_name="Dr. Taylor",
            observer_role="slp",
            observed_at=naive_dt,
            activity_context="Play",
            notes="Observed turn taking.",
        )


def test_observation_amendment_contract():
    now = datetime.now(timezone.utc)
    # Valid amendment
    amendment = ObservationRecordValue(
        observation_id="obs_002",
        organization_id="org_demo",
        assessment_id="asm_123",
        category=ObservationCategory.COMMUNICATION,
        source=ObservationSource.CLINICIAN,
        observer_name="Dr. Taylor",
        observer_role="slp",
        observed_at=now,
        activity_context="Semi-structured play",
        notes="Correction: child used 2-word phrases during block activity, not single words.",
        is_amendment=True,
        amends_observation_id="obs_001",
        version=2,
    )
    assert amendment.is_amendment is True
    assert amendment.amends_observation_id == "obs_001"
    assert amendment.version == 2

    # Invalid amendment: is_amendment True but amends_observation_id missing
    with pytest.raises(ValueError, match="amendment"):
        ObservationRecordValue(
            observation_id="obs_003",
            organization_id="org_demo",
            assessment_id="asm_123",
            category=ObservationCategory.COMMUNICATION,
            source=ObservationSource.CLINICIAN,
            observer_name="Dr. Taylor",
            observer_role="slp",
            observed_at=now,
            activity_context="Play",
            notes="Correction note",
            is_amendment=True,
            amends_observation_id=None,
            version=2,
        )

    # Invalid amendment: is_amendment True but version is 1
    with pytest.raises(ValueError, match="version"):
        ObservationRecordValue(
            observation_id="obs_004",
            organization_id="org_demo",
            assessment_id="asm_123",
            category=ObservationCategory.COMMUNICATION,
            source=ObservationSource.CLINICIAN,
            observer_name="Dr. Taylor",
            observer_role="slp",
            observed_at=now,
            activity_context="Play",
            notes="Correction note",
            is_amendment=True,
            amends_observation_id="obs_001",
            version=1,
        )
