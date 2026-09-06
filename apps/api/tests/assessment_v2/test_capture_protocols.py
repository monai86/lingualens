from __future__ import annotations

import pytest

from app.assessment_v2.domain.models import AssessmentPurpose
from app.assessment_v2.protocols import (
    PROTOCOL_UNAVAILABLE,
    THAI_GUIDED_LANGUAGE_SAMPLE_V0,
    ProtocolUnavailableError,
    select_protocol,
)


@pytest.mark.parametrize("purpose", list(AssessmentPurpose))
def test_selects_the_thai_capture_protocol_for_every_supported_purpose(
    purpose: AssessmentPurpose,
) -> None:
    selected = select_protocol(
        primary_language=" TH ",
        additional_languages=("en", "km"),
        age_months=18,
        purpose=purpose,
    )

    assert selected == THAI_GUIDED_LANGUAGE_SAMPLE_V0
    assert selected.protocol_version_key == "thai_guided_language_sample:v0"
    assert [
        (
            activity.activity_key,
            activity.required,
            activity.target_duration_seconds,
            activity.minimum_duration_seconds,
        )
        for activity in selected.activities
    ] == [
        ("free_play", True, 180, 120),
        ("shared_book", False, 120, 60),
        ("turn_taking", False, 120, 60),
    ]


@pytest.mark.parametrize(
    ("primary_language", "age_months", "purpose"),
    [
        ("th-TH", 18, AssessmentPurpose.INITIAL),
        ("th", 17, AssessmentPurpose.INITIAL),
        ("th", 73, AssessmentPurpose.INITIAL),
        ("th", "18", AssessmentPurpose.INITIAL),
        ("th", 36, "unsupported"),
    ],
)
def test_rejects_unavailable_protocol_inputs_with_a_stable_code(
    primary_language: str,
    age_months: object,
    purpose: AssessmentPurpose | str,
) -> None:
    with pytest.raises(ProtocolUnavailableError) as error:
        select_protocol(
            primary_language=primary_language,
            additional_languages=("en",),
            age_months=age_months,
            purpose=purpose,
        )

    assert error.value.code == PROTOCOL_UNAVAILABLE
    assert str(error.value) == PROTOCOL_UNAVAILABLE
