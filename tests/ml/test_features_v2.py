import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.parser import parse_cha_file
from packages.features.transcript_features import extract_transcript_features
from scripts.ml import extract_canonical_features_v2 as v2_export
from src.chat_feature_extractor import (
    extract_conversational_features_v2,
    extract_conversational_features_v2_from_turns,
)
from src.clinical_speech.models import NormalizedTranscriptLine
from src.feature_schema import (
    CONVERSATION_V2_FEATURES,
    FEATURE_DOCS,
    FEATURE_SCHEMA_V1_VERSION,
    FEATURE_SCHEMA_V2_VERSION,
    FEATURES,
    FEATURES_V2,
    feature_schema_rows,
)


def test_feature_schema_v2_definitions():
    """Verify schema counts and documentation completeness."""
    assert len(FEATURES) == 14
    assert len(CONVERSATION_V2_FEATURES) == 8
    assert len(FEATURES_V2) == 22
    assert set(FEATURES_V2) == set(FEATURES) | set(CONVERSATION_V2_FEATURES)

    for feat in FEATURES_V2:
        assert feat in FEATURE_DOCS
        doc = FEATURE_DOCS[feat]
        assert len(doc.title) > 0
        assert len(doc.clinical_meaning) > 0

    rows_v1 = feature_schema_rows("v1")
    rows_v2 = feature_schema_rows("v2")
    assert len(rows_v1) == 14
    assert len(rows_v2) == 22


def test_conversational_features_v2_synthetic_cases():
    """Verify mathematical behavior of conversational features on controlled utterances."""
    def make_utt(spk: str, words: list[str]):
        return SimpleNamespace(
            participant=spk,
            tokens=[SimpleNamespace(word=w) for w in words],
            tiers={spk: " ".join(words)},
        )

    utts = [
        make_utt("ADULT", ["look", "here"]),
        make_utt("CHI", ["look", "here"]),
        make_utt("ADULT", ["good"]),
        make_utt("CHI", ["good", "ball"]),
    ]

    conv = extract_conversational_features_v2(utts)
    assert conv["speaker_balance_ratio"] == 0.5  # 2 CHI out of 4 total
    assert conv["turn_alternation_rate"] == 1.0  # 3 transitions out of 3 pairs
    assert conv["child_run_length_mean"] == 1.0  # Runs of length 1, 1
    assert conv["child_response_rate"] == 1.0  # Every adult utterance is followed by a child utterance
    assert conv["partner_repetition_exact_ratio"] == 0.5  # 1 exact echo ("look here") out of 2 responses
    assert 0.0 <= conv["partner_repetition_overlap_mean"] <= 1.0
    assert conv["self_repetition_exact_ratio"] == 0.0  # No CHI->CHI pairs


def test_conversational_response_rates_count_each_utterance_opportunity():
    """Consecutive same-speaker utterances remain non-response opportunities."""
    def make_utt(spk: str, words: list[str]):
        return SimpleNamespace(
            participant=spk,
            tokens=[SimpleNamespace(word=w) for w in words],
            tiers={spk: " ".join(words)},
        )

    # A, A, C, C, A contains one immediate child response across three adult
    # utterances and one immediate adult response across two child utterances.
    utts = [
        make_utt("ADULT", ["wait"]),
        make_utt("ADULT", ["look", "here"]),
        make_utt("CHI", ["look", "here"]),
        make_utt("CHI", ["look", "here"]),
        make_utt("ADULT", ["good"]),
    ]

    conv = extract_conversational_features_v2(utts)

    assert conv["speaker_balance_ratio"] == 0.4
    assert conv["turn_alternation_rate"] == 0.5
    assert conv["child_run_length_mean"] == 2.0
    assert conv["child_response_rate"] == 0.3333
    assert conv["adult_response_rate"] == 0.5
    assert conv["partner_repetition_exact_ratio"] == 1.0
    assert conv["partner_repetition_overlap_mean"] == 1.0
    assert conv["self_repetition_exact_ratio"] == 1.0


def test_repetition_denominators_include_empty_token_pairs_as_nonmatches():
    """Punctuation-only adjacent pairs remain denominator opportunities."""
    partner = extract_conversational_features_v2_from_turns(
        [
            ("ADULT", ["x"]),
            ("CHI", ["x"]),
            ("ADULT", []),
            ("CHI", ["y"]),
        ]
    )
    self_repeat = extract_conversational_features_v2_from_turns(
        [("CHI", ["x"]), ("CHI", ["x"]), ("CHI", []), ("CHI", ["y"])]
    )

    assert partner["partner_repetition_exact_ratio"] == 0.5
    assert partner["partner_repetition_overlap_mean"] == 0.5
    assert self_repeat["self_repetition_exact_ratio"] == 0.3333


def test_transcript_features_v2_backward_compatibility():
    """Verify extract_transcript_features preserves v1 structure while exposing v2."""
    lines = [
        NormalizedTranscriptLine(
            session_id="s1",
            speaker_code="MOT",
            speaker_role="parent",
            start_ms=0,
            end_ms=1000,
            text="What is this?",
        ),
        NormalizedTranscriptLine(
            session_id="s1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=1000,
            end_ms=2000,
            text="A big car.",
        ),
        NormalizedTranscriptLine(
            session_id="s1",
            speaker_code="MOT",
            speaker_role="parent",
            start_ms=2000,
            end_ms=3000,
            text="Is it red?",
        ),
        NormalizedTranscriptLine(
            session_id="s1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=3000,
            end_ms=4000,
            text="A big car.",
        ),
    ]

    res = extract_transcript_features(lines, age_months=36.0)

    # v1 backward compatibility
    assert res["feature_schema_version"] == FEATURE_SCHEMA_V1_VERSION
    assert "canonical_features" in res
    assert "core_features" in res
    assert len(res["canonical_features"]) == 14
    assert res["canonical_features"]["age_months"] == 36.0
    assert set(res["canonical_features"]) == set(FEATURES)
    assert set(CONVERSATION_V2_FEATURES).isdisjoint(res["features"])

    # v2 availability
    assert res["feature_schema_version_v2"] == FEATURE_SCHEMA_V2_VERSION
    assert "canonical_features_v2" in res
    assert "conversation_v2_features" in res
    assert "features_v2" in res
    assert len(res["canonical_features_v2"]) == 22
    assert len(res["conversation_v2_features"]) == 8
    assert set(res["canonical_features_v2"]) == set(FEATURES_V2)
    assert set(CONVERSATION_V2_FEATURES).issubset(res["features_v2"])
    assert all(value is not None for value in res["conversation_v2_features"].values())
    assert res["conversation_v2_features"] == {
        "speaker_balance_ratio": 0.5,
        "turn_alternation_rate": 1.0,
        "child_run_length_mean": 1.0,
        "child_response_rate": 1.0,
        "adult_response_rate": 0.5,
        "partner_repetition_exact_ratio": 0.0,
        "partner_repetition_overlap_mean": 0.0,
        "self_repetition_exact_ratio": 0.0,
    }


def test_conversation_v2_is_identical_across_supported_transcript_inputs():
    cha_path = PROJECT_ROOT / "tests" / "fixtures" / "reference_feature_parity" / "english_toyplay.cha"
    parsed = parse_cha_file(cha_path)

    from_path = extract_transcript_features(cha_path, age_months=48.0)
    from_parsed = extract_transcript_features(parsed, age_months=48.0)
    from_lines = extract_transcript_features(parsed.to_normalized_lines(), age_months=48.0)

    assert from_path["conversation_v2_features"] == from_parsed["conversation_v2_features"]
    assert from_path["conversation_v2_features"] == from_lines["conversation_v2_features"]
    for result in (from_path, from_parsed, from_lines):
        assert {
            feature: result["canonical_features_v2"][feature]
            for feature in FEATURES
        } == result["canonical_features"]


def test_conversation_v2_preserves_transcript_order_when_timestamps_are_partial():
    """Missing timestamps must not move an utterance behind later timed lines."""
    lines = [
        NormalizedTranscriptLine(
            session_id="s-order",
            speaker_code="MOT",
            speaker_role="parent",
            line_number=1,
            start_ms=None,
            end_ms=None,
            text="first adult prompt",
        ),
        NormalizedTranscriptLine(
            session_id="s-order",
            speaker_code="CHI",
            speaker_role="child",
            line_number=2,
            start_ms=0,
            end_ms=100,
            text="first child response",
        ),
        NormalizedTranscriptLine(
            session_id="s-order",
            speaker_code="CHI",
            speaker_role="child",
            line_number=3,
            start_ms=None,
            end_ms=None,
            text="child continuation",
        ),
        NormalizedTranscriptLine(
            session_id="s-order",
            speaker_code="MOT",
            speaker_role="parent",
            line_number=4,
            start_ms=None,
            end_ms=None,
            text="terminal adult turn",
        ),
    ]

    result = extract_transcript_features(lines)["conversation_v2_features"]

    assert result["child_response_rate"] == 0.5
    assert result["adult_response_rate"] == 0.5
    assert result["turn_alternation_rate"] == 0.6667


def test_canonical_features_v2_dataset_integrity():
    """Verify exported canonical_features_v2 parquet dataset integrity."""
    parquet_path = PROJECT_ROOT / "data" / "ml" / "canonical_features_v2.parquet"
    if not parquet_path.exists():
        pytest.skip("Local research dataset not present in environment")

    df = pd.read_parquet(parquet_path)

    assert len(df) == 1961
    assert df["participant_uid"].nunique() == 1144
    assert "source_participant_id" not in df.columns
    assert "source_file" not in df.columns
    assert df["participant_uid"].map(
        lambda value: bool(re.fullmatch(r"research-participant-[0-9a-f]{16}", str(value)))
    ).all()
    assert df["session_id"].map(
        lambda value: bool(re.fullmatch(r"research-session-[0-9a-f]{16}", str(value)))
    ).all()

    # Schema v2 is additive: the published v1-named values must remain exactly
    # equal to the frozen canonical v1 export for every analysis-ready row.
    v1_df = pd.read_parquet(PROJECT_ROOT / "data" / "ml" / "canonical_features.parquet")
    assert_frame_equal(
        df[FEATURES].reset_index(drop=True),
        v1_df[FEATURES].reset_index(drop=True),
        check_dtype=False,
        check_exact=True,
    )

    # Check that all v2 feature columns exist and have zero nulls
    for feat in FEATURES_V2:
        if feat == "age_months":
            continue
        assert feat in df.columns
        assert df[feat].isna().sum() == 0, f"Feature {feat} contains NaN values"

    # Check bounded ratios
    bounded_feats = [
        "speaker_balance_ratio",
        "turn_alternation_rate",
        "child_response_rate",
        "adult_response_rate",
        "partner_repetition_exact_ratio",
        "self_repetition_exact_ratio",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_ratio",
    ]
    for b_feat in bounded_feats:
        assert (df[b_feat] >= 0.0).all(), f"{b_feat} has values < 0"
        assert (df[b_feat] <= 1.0).all(), f"{b_feat} has values > 1"


def test_v2_export_uses_stable_non_source_linked_research_ids():
    first = v2_export.pseudonymous_research_id("participant", "Ambrose", "01DM")
    second = v2_export.pseudonymous_research_id("participant", "Ambrose", "01DM")

    assert first == second
    assert re.fullmatch(r"research-participant-[0-9a-f]{16}", first)
    assert "Ambrose" not in first
    assert "01DM" not in first


def test_v2_export_fails_before_publish_when_source_is_missing(tmp_path, monkeypatch):
    registry_path = tmp_path / "participant_registry.csv"
    pd.DataFrame([_ready_registry_row(source_file="missing.cha", curated_path="also-missing.cha")]).to_csv(
        registry_path,
        index=False,
    )
    _patch_v2_export_paths(monkeypatch, tmp_path, registry_path)

    with pytest.raises(FileNotFoundError, match="missing analysis-ready transcript") as error:
        v2_export.extract_all_canonical_features_v2()

    assert "missing.cha" not in str(error.value)
    assert "Corpus::Child01" not in str(error.value)
    assert not (tmp_path / "canonical_features_v2.parquet").exists()


def test_v2_export_fails_before_publish_on_extraction_error(tmp_path, monkeypatch):
    transcript = tmp_path / "input.cha"
    transcript.write_text("synthetic fixture", encoding="utf-8")
    registry_path = tmp_path / "participant_registry.csv"
    pd.DataFrame([_ready_registry_row(source_file="input.cha", curated_path="input.cha")]).to_csv(
        registry_path,
        index=False,
    )
    _patch_v2_export_paths(monkeypatch, tmp_path, registry_path)

    def fail_extraction(*_args, **_kwargs):
        raise ValueError("synthetic extraction failure")

    monkeypatch.setattr(v2_export, "extract_transcript_features", fail_extraction)
    with pytest.raises(RuntimeError, match="feature extraction failed") as error:
        v2_export.extract_all_canonical_features_v2()

    assert "input.cha" not in str(error.value)
    assert "Corpus::Child01" not in str(error.value)
    assert not (tmp_path / "canonical_features_v2.parquet").exists()


def test_annotation_template_contains_only_explicitly_synthetic_text():
    sample = pd.read_csv(
        PROJECT_ROOT / "data" / "ml" / "validation" / "feature_v2_annotation_sample.csv"
    )

    assert sample["is_synthetic"].eq(True).all()
    assert {"participant_uid", "session_id", "corpus"}.isdisjoint(sample.columns)
    assert sample["synthetic_case_id"].str.startswith("synthetic-dialogue-").all()


def _ready_registry_row(**overrides):
    row = {
        "participant_uid": "Corpus::Child01",
        "source_participant_id": "Child01",
        "session_id": "session-01",
        "session_order": 1,
        "corpus": "Corpus",
        "diagnostic_group": "TD",
        "age_months": 48.0,
        "sex": "unknown",
        "language": "eng",
        "task_type": "synthetic",
        "recording_context": "synthetic",
        "source_file": "input.cha",
        "curated_path": "input.cha",
        "qc_pass": True,
    }
    row.update(overrides)
    return row


def _patch_v2_export_paths(monkeypatch, tmp_path, registry_path):
    monkeypatch.setattr(v2_export, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(v2_export, "REGISTRY_PATH", registry_path)
    monkeypatch.setattr(v2_export, "OUTPUT_PARQUET", tmp_path / "canonical_features_v2.parquet")
    monkeypatch.setattr(v2_export, "OUTPUT_CSV", tmp_path / "canonical_features_v2.csv")
    monkeypatch.setattr(v2_export, "OUTPUT_XLSX", tmp_path / "canonical_features_v2.xlsx")
    monkeypatch.setattr(v2_export, "OUTPUT_MANIFEST", tmp_path / "canonical_features_v2.manifest.json")


def test_canonical_features_v2_exports_match_bound_manifest():
    data_dir = PROJECT_ROOT / "data" / "ml"
    parquet_path = data_dir / "canonical_features_v2.parquet"
    if not parquet_path.exists():
        pytest.skip("Local research dataset not present in environment")
    manifest_path = data_dir / "canonical_features_v2.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))


    assert manifest["schema_version"] == FEATURE_SCHEMA_V2_VERSION
    assert manifest["row_count"] == 1961
    assert manifest["participant_count"] == 1144
    assert manifest["features"] == FEATURES_V2

    frames = {}
    for artifact in manifest["artifacts"]:
        path = PROJECT_ROOT / artifact["path"]
        assert path.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        if path.suffix == ".parquet":
            frames[path.suffix] = pd.read_parquet(path)
        elif path.suffix == ".csv":
            frames[path.suffix] = pd.read_csv(path)
        elif path.suffix == ".xlsx":
            frames[path.suffix] = pd.read_excel(path, sheet_name="Features_v2")

    expected_columns = frames[".parquet"].columns.tolist()
    assert frames[".csv"].columns.tolist() == expected_columns
    assert frames[".xlsx"].columns.tolist() == expected_columns
    assert len(frames[".csv"]) == len(frames[".parquet"]) == len(frames[".xlsx"]) == 1961

    # Hashes catch a single stale artifact; value parity catches synchronized
    # but semantically divergent exporters or format-specific coercion.
    metadata_columns = [column for column in expected_columns if column not in FEATURES_V2]
    numeric_columns = [column for column in FEATURES_V2 if column in expected_columns]
    for suffix in (".csv", ".xlsx"):
        assert_frame_equal(
            frames[suffix][numeric_columns].reset_index(drop=True),
            frames[".parquet"][numeric_columns].reset_index(drop=True),
            check_dtype=False,
            rtol=1e-7,
            atol=1e-7,
        )
        assert_frame_equal(
            frames[suffix][metadata_columns].fillna("").astype(str).reset_index(drop=True),
            frames[".parquet"][metadata_columns].fillna("").astype(str).reset_index(drop=True),
            check_dtype=False,
        )
