# tests/test_asr_provider_registry.py
import pytest
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_providers.mock_provider import MockTranscriptionProvider
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider


# The registry's import-time wiring is the source of truth for which providers
# exist. Declaring the expected sets here keeps adding or removing a provider a
# deliberate, reviewable change instead of a silent edit to that wiring.
EXPECTED_PROVIDER_IDS = frozenset(
    {
        "mock",
        "local_whisper",
        "manual",
        "whisper",
        "faster_whisper",
        "whisperx",
        "batchalign",
    }
)

# Compatibility stubs and manual entry report themselves available on purpose;
# only the dependency-backed provider stays unavailable until installed.
EXPECTED_AVAILABLE_PROVIDER_IDS = frozenset(
    {
        "mock",
        "manual",
        "whisper",
        "faster_whisper",
        "whisperx",
        "batchalign",
    }
)

PLACEHOLDER_PROVIDER_IDS = frozenset({"whisper", "faster_whisper", "whisperx", "batchalign"})


def _supported_ids() -> set[str]:
    return {p["provider_id"] for p in asr_provider_registry.list_supported()}


def test_registry_supports_exactly_the_declared_providers():
    assert _supported_ids() == EXPECTED_PROVIDER_IDS


def test_every_declared_provider_is_retrievable_by_id():
    for provider_id in sorted(EXPECTED_PROVIDER_IDS):
        assert provider_id in asr_provider_registry
        assert asr_provider_registry.get(provider_id).provider_id == provider_id


def test_mock_provider_is_available():
    p = asr_provider_registry.get("mock")
    avail = p.check_availability()
    assert avail.available is True


def test_local_whisper_provider_is_unavailable_by_default():
    p = asr_provider_registry.get("local_whisper")
    avail = p.check_availability()
    assert avail.available is False


def test_get_unknown_provider_raises_key_error():
    with pytest.raises(KeyError, match="not registered"):
        asr_provider_registry.get("nonexistent_xyz")


def test_list_supported_enumerates_the_whole_registry_once_each():
    listed_ids = [p["provider_id"] for p in asr_provider_registry.list_supported()]

    assert len(listed_ids) == len(set(listed_ids))
    assert set(listed_ids) == EXPECTED_PROVIDER_IDS


def test_list_available_matches_the_declared_availability():
    # Stub and manual providers are available by design, so availability is
    # asserted as the full declared set rather than as one provider plus an
    # absence check that other providers can hide behind.
    available_ids = {p["provider_id"] for p in asr_provider_registry.list_available()}

    assert available_ids == EXPECTED_AVAILABLE_PROVIDER_IDS
    assert asr_provider_registry.get("local_whisper").check_availability().available is False


def test_provider_metadata_flags_placeholders_and_only_placeholders():
    by_id = {p["provider_id"]: p for p in asr_provider_registry.list_supported()}

    for provider_id in sorted(PLACEHOLDER_PROVIDER_IDS):
        assert by_id[provider_id]["is_placeholder"] is True
    for provider_id in sorted(EXPECTED_PROVIDER_IDS - PLACEHOLDER_PROVIDER_IDS):
        assert by_id[provider_id].get("is_placeholder", False) is False


def test_mock_provider_transcribe_returns_three_lines():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    assert result.status == "completed"
    assert len(result.transcript_lines) == 3


def test_mock_provider_transcript_has_timestamps():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    for line in result.transcript_lines:
        assert line.start_ms is not None


def test_mock_provider_has_mock_warning():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    assert any("MOCK" in w or "mock" in w.lower() for w in result.warnings)


def test_local_whisper_transcribe_returns_unavailable():
    p = LocalWhisperProvider()
    result = p.transcribe("test-ref")
    assert result.status == "unavailable"
    assert len(result.transcript_lines) == 0


def test_get_default_returns_mock():
    default = asr_provider_registry.get_default()
    assert default.provider_id == "mock"


def test_registry_contains_check():
    assert "mock" in asr_provider_registry
    assert "nonexistent" not in asr_provider_registry
