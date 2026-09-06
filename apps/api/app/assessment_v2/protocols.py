"""Pure, versioned capture-protocol selection for assessment v2."""

from __future__ import annotations

from app.assessment_v2.domain.models import AssessmentPurpose, ProtocolActivity, ProtocolVersion


PROTOCOL_UNAVAILABLE = "protocol_unavailable"


class ProtocolUnavailableError(ValueError):
    """Raised when no research capture protocol matches an assessment."""

    code = PROTOCOL_UNAVAILABLE

    def __init__(self) -> None:
        super().__init__(self.code)


THAI_GUIDED_LANGUAGE_SAMPLE_V0 = ProtocolVersion(
    protocol_version_key="thai_guided_language_sample:v0",
    primary_language="th",
    minimum_age_months=18,
    maximum_age_months=72,
    supported_purposes=tuple(AssessmentPurpose),
    activities=(
        ProtocolActivity(
            activity_key="free_play",
            required=True,
            target_duration_seconds=180,
            minimum_duration_seconds=120,
        ),
        ProtocolActivity(
            activity_key="shared_book",
            required=False,
            target_duration_seconds=120,
            minimum_duration_seconds=60,
        ),
        ProtocolActivity(
            activity_key="turn_taking",
            required=False,
            target_duration_seconds=120,
            minimum_duration_seconds=60,
        ),
    ),
)

PROTOCOL_CATALOG: tuple[ProtocolVersion, ...] = (THAI_GUIDED_LANGUAGE_SAMPLE_V0,)


def select_protocol(
    *,
    primary_language: str,
    additional_languages: tuple[str, ...] | list[str] | None = None,
    age_months: int,
    purpose: AssessmentPurpose | str,
) -> ProtocolVersion:
    """Select the single eligible research capture protocol or fail closed.

    Additional languages are intentionally not an exclusion criterion. They are
    accepted as context but do not change the primary-language eligibility rule.
    """

    del additional_languages
    normalized_language = _normalize_primary_language(primary_language)
    normalized_purpose = _normalize_purpose(purpose)
    if not isinstance(age_months, int) or isinstance(age_months, bool):
        raise ProtocolUnavailableError()

    for protocol in sorted(PROTOCOL_CATALOG, key=lambda item: item.protocol_version_key):
        if (
            normalized_language == protocol.primary_language
            and protocol.minimum_age_months <= age_months <= protocol.maximum_age_months
            and normalized_purpose in protocol.supported_purposes
        ):
            return protocol

    raise ProtocolUnavailableError()


def _normalize_primary_language(primary_language: str) -> str:
    if not isinstance(primary_language, str):
        return ""
    return primary_language.strip().casefold()


def _normalize_purpose(purpose: AssessmentPurpose | str) -> AssessmentPurpose | None:
    try:
        return AssessmentPurpose(purpose)
    except (TypeError, ValueError):
        return None
