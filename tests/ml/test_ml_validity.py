"""Automated verification tests for ML validity, domain-controlled experiments, and reports."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "ml"
RESULTS_DIR = DATA_DIR / "results"
REPORTS_DIR = PROJECT_ROOT / "reports" / "ml"


def test_participant_registry_integrity():
    registry_path = DATA_DIR / "participant_registry.csv"
    if not registry_path.exists():
        pytest.skip("participant_registry.csv is a local research dataset")
    df = pd.read_csv(registry_path)

    # Check required columns
    required_cols = [
        "participant_uid",
        "source_participant_id",
        "participant_id",
        "corpus",
        "diagnostic_group",
        "transcript_available",
        "qc_pass",
        "feature_extraction_pass",
    ]
    for col in required_cols:
        assert col in df.columns, f"Column {col} missing in participant registry"

    # Analysis-ready rows must have unique diagnostic group per participant_uid
    ready_df = df[(df["transcript_available"] == True) & (df["qc_pass"] == True) & (df["feature_extraction_pass"] == True)]
    group_counts = ready_df.groupby("participant_uid")["diagnostic_group"].nunique()
    assert (group_counts == 1).all(), "Found participant_uid assigned to multiple diagnostic groups"


def test_canonical_features_integrity():
    parquet_path = DATA_DIR / "canonical_features.parquet"
    if not parquet_path.exists():
        pytest.skip("canonical_features.parquet is a local research dataset")
    csv_path = DATA_DIR / "canonical_features.csv"
    xlsx_path = DATA_DIR / "canonical_features.xlsx"


    assert parquet_path.exists()
    assert csv_path.exists()
    assert xlsx_path.exists()

    df = pd.read_parquet(parquet_path)
    assert len(df) == 1961, f"Expected 1,961 analysis-ready rows, got {len(df)}"
    assert "participant_uid" in df.columns
    assert "source_participant_id" in df.columns


def test_domain_controlled_results_exist():
    master_path = RESULTS_DIR / "master_primary_results.csv"
    assert master_path.exists(), "master_primary_results.csv must exist"

    df = pd.read_csv(master_path)
    experiments = set(df["experiment"].unique())

    expected_experiments = {
        "Eigsti Within-Corpus",
        "Nadig Within-Corpus",
        "Eigsti ASD vs DD",
        "Eigsti TD vs DD",
        "Cross-Corpus Eigsti->Nadig",
        "Cross-Corpus Nadig->Eigsti",
    }
    assert expected_experiments.issubset(experiments), f"Missing experiments: {expected_experiments - experiments}"


def test_all_reports_generated():
    required_reports = [
        "DATASET_AUDIT.md",
        "LEAKAGE_AND_CONFOUNDING_AUDIT.md",
        "DOMAIN_CONTROLLED_COHORTS.md",
        "DOMAIN_CONTROLLED_RESULTS.md",
        "CROSS_CORPUS_RESULTS.md",
        "FEATURE_ABLATION_RESULTS.md",
        "IMBALANCE_COMPARISON.md",
        "MODEL_RESULTS.md",
        "ML_VALIDITY_DECISION.md",
    ]
    for report_name in required_reports:
        p = REPORTS_DIR / report_name
        assert p.exists(), f"Report {report_name} missing in reports/ml/"
        assert p.stat().st_size > 200, f"Report {report_name} is too small / empty"
